"""Privacy-bounded telemetry and deterministic performance summaries."""
from collections import deque
from dataclasses import dataclass, replace
import hashlib
import hmac
import json
import secrets
from statistics import fmean
import threading

from ceta.contracts.resource_management import (
    MAX_OBSERVATION_AGE_NS, QuantityObservation, TelemetrySample, TelemetrySourceBinding,
    digest, identifier, require,
)

MAX_DIAGNOSTIC_SAMPLES = 8192
# Explicit projection policy. Other producer text never enters the retained
# buffer; the original numeric/state/time observations remain unchanged.
SAFE_TELEMETRY_METHODS = frozenset({
    "fixture", "windows:os.cpu_count", "windows:DXGI.EnumAdapters:GetDesc",
    "windows:GlobalMemoryStatusEx", "python:shutil.disk_usage",
    "windows:IsProcessInJob", "windows:GetSystemTimes", "METHOD_REDACTED",
})
SAFE_TELEMETRY_REASONS = frozenset({
    "NOT_OBSERVED", "WINDOWS_REQUIRED", "CPU_COUNT_UNAVAILABLE", "ACCELERATOR_QUERY_FAILED",
    "ACCELERATOR_QUERY_INVALID", "ACCELERATOR_NOT_FOUND", "ACCELERATOR_RUNTIME_AVAILABILITY_NOT_OBSERVED",
    "MEMORY_QUERY_FAILED", "STORAGE_QUERY_FAILED", "ISOLATION_QUERY_FAILED",
    "AVAILABILITY_REQUIRES_RUNTIME_SAMPLE", "CPU_QUERY_UNAVAILABLE", "CPU_QUERY_FAILED",
    "CPU_BASELINE_REQUIRED", "REASON_REDACTED",
})


@dataclass(frozen=True, slots=True)
class PerformanceEnvelope:
    maximum_p95_latency_ms: int
    maximum_cpu_milli: int
    maximum_memory_bytes: int

    def __post_init__(self) -> None:
        for value in (self.maximum_p95_latency_ms, self.maximum_cpu_milli, self.maximum_memory_bytes):
            require(type(value) is int and value >= 0, "RESOURCE_PERFORMANCE_ENVELOPE_INVALID")


@dataclass(frozen=True, slots=True)
class PerformanceAnalysis:
    sample_count: int
    mean_latency_ms: float | None
    p95_latency_ms: int | None
    peak_cpu_milli: int | None
    peak_memory_bytes: int | None
    within_envelope: bool
    findings: tuple[str, ...]
    measurement_state: str = "HISTORICAL_UNQUALIFIED"


@dataclass(frozen=True, slots=True)
class WorkloadComparisonInput:
    """Pinned, repeatable workload identity and two measurement sets."""
    workload_id: str
    workload_digest: str
    baseline: tuple[TelemetrySample, ...]
    candidate: tuple[TelemetrySample, ...]

    def __post_init__(self) -> None:
        identifier(self.workload_id, "RESOURCE_WORKLOAD_IDENTIFIER_INVALID")
        digest(self.workload_digest, "RESOURCE_WORKLOAD_DIGEST_INVALID")
        require(type(self.baseline) is tuple and type(self.candidate) is tuple
                and 1 <= len(self.baseline) <= MAX_DIAGNOSTIC_SAMPLES
                and 1 <= len(self.candidate) <= MAX_DIAGNOSTIC_SAMPLES
                and all(type(sample) is TelemetrySample for sample in self.baseline + self.candidate),
                "RESOURCE_COMPARISON_SAMPLES_INVALID")


@dataclass(frozen=True, slots=True)
class CurrentComparisonContext:
    """One declared monotonic source epoch and disjoint before/after windows.

    Values must come from the canonical source owner; this pure context cannot
    authenticate them, create task authority, or qualify a hardware workload.
    """
    now_monotonic_ns: int
    maximum_age_ns: int
    scope_digest: str
    environment_digest: str
    source_digest: str
    source_generation: int
    baseline_start_ns: int
    baseline_end_ns: int
    candidate_start_ns: int
    candidate_end_ns: int

    def __post_init__(self) -> None:
        for value in (self.now_monotonic_ns, self.source_generation, self.baseline_start_ns,
                      self.baseline_end_ns, self.candidate_start_ns, self.candidate_end_ns):
            require(type(value) is int and 0 <= value <= 2**63 - 1, "RESOURCE_COMPARISON_CONTEXT_INVALID")
        require(type(self.maximum_age_ns) is int and 1 <= self.maximum_age_ns <= MAX_OBSERVATION_AGE_NS,
                "RESOURCE_COMPARISON_CONTEXT_INVALID")
        for value in (self.scope_digest, self.environment_digest, self.source_digest):
            digest(value, "RESOURCE_COMPARISON_CONTEXT_DIGEST_INVALID")


@dataclass(frozen=True, slots=True)
class MeasurementDelta:
    metric: str
    baseline: int | None
    candidate: int | None
    state: str


@dataclass(frozen=True, slots=True)
class WorkloadComparisonResult:
    workload_id: str
    workload_digest: str
    state: str
    reproducible: bool
    baseline_scope_digest: str | None
    baseline_environment_digest: str | None
    candidate_scope_digest: str | None
    candidate_environment_digest: str | None
    baseline: PerformanceAnalysis
    candidate: PerformanceAnalysis
    deltas: tuple[MeasurementDelta, ...]
    findings: tuple[str, ...]


class ResourceTelemetryRecorder:
    """Bounded safe projections, deduplicated only while an ID is retained.

    Unknown observation text becomes an explicit redaction code. Caller IDs
    become recorder-local keyed tokens in both returned samples and bookkeeping.
    Keyed payload fingerprints detect conflicting same-ID delivery without
    retaining raw identifiers or method/reason strings. The ephemeral key is
    not exported or persisted; these tokens grant no source authenticity and
    provide no anonymity against access to this recorder's process memory.
    Eviction also evicts deduplication bookkeeping. This is not a durable cursor,
    canonical ledger, or authenticated source owner.
    """
    def __init__(self, *, maximum_samples: int = 1024) -> None:
        require(type(maximum_samples) is int and 1 <= maximum_samples <= 8192, "RESOURCE_TELEMETRY_BOUND_INVALID")
        self._samples: deque[TelemetrySample] = deque(maxlen=maximum_samples)
        self._retained_payloads: dict[str, str] = {}
        self._projection_key = secrets.token_bytes(32)
        self._lock = threading.Lock()

    def record(self, sample: TelemetrySample) -> int:
        require(type(sample) is TelemetrySample, "RESOURCE_TELEMETRY_SAMPLE_REQUIRED")
        sample.__post_init__()
        observations = (sample.cpu_milli, sample.memory_bytes, sample.storage_bytes, sample.latency_ms)
        for observation in observations:
            observation.__post_init__()
        if sample.source is not None:
            sample.source.__post_init__()
        payload = [sample.sample_id, sample.scope_digest, sample.environment_digest, sample.observed_monotonic_ns,
                   [[x.state.value, x.value, x.observed_monotonic_ns, x.method, x.reason] for x in observations],
                   None if sample.source is None else [sample.source.source_digest, sample.source.source_generation,
                                                       sample.source.sequence, sample.source.workload_digest]]
        sample_id = "telemetry:" + hmac.new(
            self._projection_key, b"sample-id\0" + sample.sample_id.encode("ascii"), hashlib.sha256).hexdigest()
        payload_digest = hmac.new(
            self._projection_key,
            b"sample-payload\0" + json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("ascii"),
            hashlib.sha256).hexdigest()
        projected = tuple(QuantityObservation(x.state, x.value, x.observed_monotonic_ns,
                          x.method if x.method in SAFE_TELEMETRY_METHODS else "METHOD_REDACTED",
                          None if x.reason is None else x.reason if x.reason in SAFE_TELEMETRY_REASONS else "REASON_REDACTED")
                          for x in observations)
        safe_sample = TelemetrySample(sample_id, sample.scope_digest, sample.environment_digest,
                                      sample.observed_monotonic_ns, *projected,
                                      None if sample.source is None else replace(sample.source))
        with self._lock:
            previous = self._retained_payloads.get(sample_id)
            if previous is not None:
                require(previous == payload_digest, "RESOURCE_TELEMETRY_SAMPLE_ID_CONFLICT")
                return 0
            dropped = int(len(self._samples) == self._samples.maxlen)
            if dropped:
                del self._retained_payloads[self._samples.popleft().sample_id]
            self._samples.append(safe_sample)
            self._retained_payloads[sample_id] = payload_digest
            return dropped

    def recent(self, *, now_monotonic_ns: int, maximum_age_ns: int, scope_digest: str) -> tuple[TelemetrySample, ...]:
        require(type(now_monotonic_ns) is int and now_monotonic_ns >= 0 and type(maximum_age_ns) is int and maximum_age_ns >= 0,
                "RESOURCE_TELEMETRY_TIME_INVALID")
        digest(scope_digest, "RESOURCE_SCOPE_DIGEST_INVALID")
        with self._lock:
            return tuple(sample for sample in self._samples
                         if sample.scope_digest == scope_digest and now_monotonic_ns >= sample.observed_monotonic_ns
                         and now_monotonic_ns - sample.observed_monotonic_ns <= maximum_age_ns)


class PerformanceDiagnostics:
    def analyze(self, samples: tuple[TelemetrySample, ...], envelope: PerformanceEnvelope) -> PerformanceAnalysis:
        """Summarize retained values only; envelope fit implies no current proof."""
        require(type(samples) is tuple and all(type(sample) is TelemetrySample for sample in samples)
                and len(samples) <= MAX_DIAGNOSTIC_SAMPLES
                and type(envelope) is PerformanceEnvelope, "RESOURCE_DIAGNOSTIC_INPUT_INVALID")
        latency = sorted(item.latency_ms.value for item in samples if item.latency_ms.measured)
        cpu = [item.cpu_milli.value for item in samples if item.cpu_milli.measured]
        memory = [item.memory_bytes.value for item in samples if item.memory_bytes.measured]
        p95 = None if not latency else latency[(len(latency) * 95 + 99) // 100 - 1]
        peak_cpu, peak_memory = (max(cpu) if cpu else None), (max(memory) if memory else None)
        findings = []
        if len(latency) != len(samples): findings.append("LATENCY_UNAVAILABLE")
        if len(cpu) != len(samples): findings.append("CPU_UNAVAILABLE")
        if len(memory) != len(samples): findings.append("MEMORY_UNAVAILABLE")
        if p95 is not None and p95 > envelope.maximum_p95_latency_ms: findings.append("P95_LATENCY_EXCEEDED")
        if peak_cpu is not None and peak_cpu > envelope.maximum_cpu_milli: findings.append("CPU_PEAK_EXCEEDED")
        if peak_memory is not None and peak_memory > envelope.maximum_memory_bytes: findings.append("MEMORY_PEAK_EXCEEDED")
        return PerformanceAnalysis(len(samples), None if not latency else fmean(latency), p95, peak_cpu, peak_memory,
                                   not findings, tuple(findings))

    def analyze_current(self, samples: tuple[TelemetrySample, ...], envelope: PerformanceEnvelope, *,
                        now_monotonic_ns: int, maximum_age_ns: int, scope_digest: str,
                        environment_digest: str) -> PerformanceAnalysis:
        """Analyze one current, identity-bound telemetry set without partial fallback.

        ``analyze`` remains available for retained historical comparison.  A
        decision about current performance must not silently calculate from a
        stale, future-dated, mixed-scope, or mixed-environment subset.
        """
        require(type(samples) is tuple and all(type(sample) is TelemetrySample for sample in samples)
                and type(envelope) is PerformanceEnvelope and type(now_monotonic_ns) is int
                 and len(samples) <= MAX_DIAGNOSTIC_SAMPLES
                 and 0 <= now_monotonic_ns <= 2**63 - 1 and type(maximum_age_ns) is int
                 and 1 <= maximum_age_ns <= MAX_OBSERVATION_AGE_NS,
                "RESOURCE_CURRENT_DIAGNOSTIC_INPUT_INVALID")
        digest(scope_digest, "RESOURCE_SCOPE_DIGEST_INVALID")
        digest(environment_digest, "RESOURCE_ENVIRONMENT_DIGEST_INVALID")
        findings: list[str] = []
        if not samples:
            findings.append("TELEMETRY_EMPTY")
        for sample in samples:
            if sample.scope_digest != scope_digest:
                findings.append("TELEMETRY_SCOPE_MISMATCH")
            if sample.environment_digest != environment_digest:
                findings.append("TELEMETRY_ENVIRONMENT_MISMATCH")
            if (now_monotonic_ns < sample.observed_monotonic_ns
                    or now_monotonic_ns - sample.observed_monotonic_ns > maximum_age_ns):
                findings.append("TELEMETRY_STALE_OR_FUTURE")
            # A sample wrapper does not make an older constituent observation
            # current.  Analyze each actual resource/latency observation so a
            # newly assembled record cannot conceal stale capacity or timing.
            for observation in (sample.cpu_milli, sample.memory_bytes,
                                sample.storage_bytes, sample.latency_ms):
                if (now_monotonic_ns < observation.observed_monotonic_ns
                        or now_monotonic_ns - observation.observed_monotonic_ns > maximum_age_ns):
                    findings.append("TELEMETRY_OBSERVATION_STALE_OR_FUTURE")
        if findings:
            return PerformanceAnalysis(len(samples), None, None, None, None, False,
                                       tuple(dict.fromkeys(findings)), "CURRENT_INPUT_REJECTED")
        return replace(self.analyze(samples, envelope), measurement_state="CURRENT_IDENTITY_AND_TIME_BOUND")

    def compare(self, comparison: WorkloadComparisonInput, envelope: PerformanceEnvelope) -> WorkloadComparisonResult:
        """Historical differences, never a current/reproducible verdict."""
        require(type(comparison) is WorkloadComparisonInput and type(envelope) is PerformanceEnvelope,
                "RESOURCE_COMPARISON_INPUT_INVALID")
        baseline, candidate = self.analyze(comparison.baseline, envelope), self.analyze(comparison.candidate, envelope)
        return self._comparison_result(comparison, baseline, candidate)

    def compare_current(self, comparison: WorkloadComparisonInput, envelope: PerformanceEnvelope, *,
                        context: CurrentComparisonContext) -> WorkloadComparisonResult:
        """Compare distinct, ordered, fresh observations in one declared epoch.

        This validates supplied domain facts only; it does not authenticate a
        source, prove a causal bottleneck, or independently qualify repetition.
        """
        require(type(comparison) is WorkloadComparisonInput and type(envelope) is PerformanceEnvelope
                and type(context) is CurrentComparisonContext, "RESOURCE_CURRENT_COMPARISON_INPUT_INVALID")
        comparison.__post_init__(); context.__post_init__()
        findings = []
        windows = ((context.baseline_start_ns, context.baseline_end_ns),
                   (context.candidate_start_ns, context.candidate_end_ns))
        if not (windows[0][0] <= windows[0][1] < windows[1][0] <= windows[1][1]):
            findings.append("COMPARISON_WINDOWS_NOT_ORDERED")
        if any(context.now_monotonic_ns < value or context.now_monotonic_ns - value > context.maximum_age_ns
               for window in windows for value in window):
            findings.append("COMPARISON_WINDOW_STALE_OR_FUTURE")
        samples = comparison.baseline + comparison.candidate
        if len({sample.sample_id for sample in samples}) != len(samples):
            findings.append("COMPARISON_SAMPLE_REUSED_OR_DUPLICATED")
        sequences = []
        for side, window in zip((comparison.baseline, comparison.candidate), windows):
            for sample in side:
                sample.__post_init__()
                if not window[0] <= sample.observed_monotonic_ns <= window[1]:
                    findings.append("COMPARISON_SAMPLE_OUTSIDE_WINDOW")
                for observation in (sample.cpu_milli, sample.memory_bytes, sample.storage_bytes, sample.latency_ms):
                    observation.__post_init__()
                    if not window[0] <= observation.observed_monotonic_ns <= sample.observed_monotonic_ns:
                        findings.append("COMPARISON_OBSERVATION_OUTSIDE_WINDOW")
                if sample.source is None:
                    findings.append("COMPARISON_SOURCE_CONTEXT_MISSING")
                    continue
                sample.source.__post_init__()
                if sample.source.source_digest != context.source_digest:
                    findings.append("COMPARISON_SOURCE_MISMATCH")
                if sample.source.source_generation != context.source_generation:
                    findings.append("COMPARISON_SOURCE_GENERATION_MISMATCH")
                if sample.source.workload_digest != comparison.workload_digest:
                    findings.append("COMPARISON_WORKLOAD_MISMATCH")
                sequences.append(sample.source.sequence)
        if any(after <= before for before, after in zip(sequences, sequences[1:])):
            findings.append("COMPARISON_SEQUENCE_NOT_ORDERED")
        if any(after > before + 1 for before, after in zip(sequences, sequences[1:])):
            findings.append("COMPARISON_SEQUENCE_GAP")
        if any(after.observed_monotonic_ns < before.observed_monotonic_ns
               for before, after in zip(samples, samples[1:])):
            findings.append("COMPARISON_SAMPLE_TIME_NOT_ORDERED")
        analyses = tuple(self.analyze_current(side, envelope, now_monotonic_ns=context.now_monotonic_ns,
                        maximum_age_ns=context.maximum_age_ns, scope_digest=context.scope_digest,
                        environment_digest=context.environment_digest)
                        for side in (comparison.baseline, comparison.candidate))
        for analysis in analyses:
            if analysis.measurement_state == "CURRENT_INPUT_REJECTED":
                findings.extend(analysis.findings)
        if findings:
            analyses = tuple(PerformanceAnalysis(len(side), None, None, None, None, False,
                             tuple(dict.fromkeys(findings)), "CURRENT_INPUT_REJECTED")
                             for side in (comparison.baseline, comparison.candidate))
        return self._comparison_result(comparison, *analyses, current=True,
                                       context_findings=tuple(dict.fromkeys(findings)))

    def _comparison_result(self, comparison: WorkloadComparisonInput, baseline: PerformanceAnalysis,
                           candidate: PerformanceAnalysis, *, current: bool = False,
                           context_findings: tuple[str, ...] = ()) -> WorkloadComparisonResult:
        baseline_scope, baseline_environment, baseline_identity_findings = self._measurement_identity(comparison.baseline, "BASELINE")
        candidate_scope, candidate_environment, candidate_identity_findings = self._measurement_identity(comparison.candidate, "CANDIDATE")
        metrics = (("P95_LATENCY_MS", baseline.p95_latency_ms, candidate.p95_latency_ms),
                   ("PEAK_CPU_MILLI", baseline.peak_cpu_milli, candidate.peak_cpu_milli),
                   ("PEAK_MEMORY_BYTES", baseline.peak_memory_bytes, candidate.peak_memory_bytes))
        deltas = tuple(MeasurementDelta(name, before, after, "MEASURED" if before is not None and after is not None else "UNKNOWN")
                       for name, before, after in metrics)
        unknown = tuple(delta.metric for delta in deltas if delta.state == "UNKNOWN")
        reproducible = (current and not context_findings and not unknown
                        and not baseline_identity_findings and not candidate_identity_findings
                        and baseline_scope == candidate_scope and baseline_environment == candidate_environment)
        findings = (("MEASURED_DIFFERENCE_ONLY_NO_CAUSAL_CLAIM",)
                     + (("CALLER_BOUND_CONTEXT_NOT_AUTHENTICATED_SOURCE_PROOF",) if current
                        else ("COMPARISON_CONTEXT_REQUIRED",)) + context_findings
                    + baseline_identity_findings + candidate_identity_findings
                    + (() if baseline_scope == candidate_scope else ("COMPARISON_SCOPE_MISMATCH",))
                    + (() if baseline_environment == candidate_environment else ("COMPARISON_ENVIRONMENT_MISMATCH",))
                    + tuple("COMPARISON_UNKNOWN_" + metric for metric in unknown))
        state = ("COMPARISON_CONTEXT_REJECTED" if context_findings else
                 "MEASURED_REPRODUCIBLE_COMPARISON" if reproducible else
                 "HISTORICAL_UNQUALIFIED_COMPARISON" if not current and not unknown
                 and not baseline_identity_findings and not candidate_identity_findings
                 and baseline_scope == candidate_scope and baseline_environment == candidate_environment
                 else "INCOMPLETE_MEASUREMENTS")
        return WorkloadComparisonResult(comparison.workload_id, comparison.workload_digest, state, reproducible,
                                        baseline_scope, baseline_environment, candidate_scope, candidate_environment,
                                        baseline, candidate, deltas, findings)

    @staticmethod
    def _measurement_identity(samples: tuple[TelemetrySample, ...], side: str) -> tuple[str | None, str | None, tuple[str, ...]]:
        scopes, environments = {sample.scope_digest for sample in samples}, {sample.environment_digest for sample in samples}
        findings = ()
        if len(scopes) != 1: findings += (side + "_SCOPE_MIXED",)
        if len(environments) != 1: findings += (side + "_ENVIRONMENT_MIXED",)
        return (next(iter(scopes)) if len(scopes) == 1 else None,
                next(iter(environments)) if len(environments) == 1 else None, findings)

