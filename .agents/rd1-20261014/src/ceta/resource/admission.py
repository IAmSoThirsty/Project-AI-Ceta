"""Pure budget checks and admission preparation through the canonical port."""
from dataclasses import dataclass
import hashlib
import time

from ceta.contracts.resource_management import (
    AdmissionState, BudgetEnvelope, PressureLevel, ReservationPort, ReservationRequest, ReservationResult,
    ResourceVector, digest, identifier, require,
)
from ceta.contracts.wire import canonical_bytes
from ceta.resource.budget import aggregate_checks


def assess_budget(budget: BudgetEnvelope, requirements: ResourceVector) -> tuple[bool, tuple[str, ...]]:
    require(type(budget) is BudgetEnvelope and type(requirements) is ResourceVector, "RESOURCE_BUDGET_INPUT_INVALID")
    checks = aggregate_checks(budget, requirements)
    codes = tuple(code for check in checks for code in check.reason_codes)
    # Storage is held separately because no current time/controller check owns it.
    if requirements.storage_bytes > budget.allocatable.storage_bytes:
        codes += ("STORAGE_BUDGET_EXHAUSTED",)
    return (not codes, codes)


@dataclass(frozen=True, slots=True)
class WorkloadEstimate:
    workload_id: str
    requirements: ResourceVector | None
    uncertainty_milli: int
    source: str
    state: str = "MEASURED"
    profile_id: str | None = None
    profile_revision: str | None = None
    source_digest: str | None = None
    confidence_milli: int = 1000
    observed_monotonic_ns: int | None = None
    reason_code: str | None = None
    profile_snapshot_commitment: str | None = None

    def __post_init__(self) -> None:
        identifier(self.workload_id, "RESOURCE_WORKLOAD_IDENTIFIER_INVALID")
        require(type(self.uncertainty_milli) is int and 0 <= self.uncertainty_milli <= 1000
                and type(self.source) is str and 1 <= len(self.source) <= 160
                and self.state in {"MEASURED", "UNRESOLVED"}
                and type(self.confidence_milli) is int and 0 <= self.confidence_milli <= 1000,
                "RESOURCE_WORKLOAD_ESTIMATE_INVALID")
        if self.state == "MEASURED":
            require(type(self.requirements) is ResourceVector and self.reason_code is None
                    and all(value is not None for value in
                            (self.profile_id, self.profile_revision, self.source_digest,
                             self.observed_monotonic_ns, self.profile_snapshot_commitment)),
                    "RESOURCE_WORKLOAD_ESTIMATE_INVALID")
        else:
            require(self.requirements is None and type(self.reason_code) is str and 1 <= len(self.reason_code) <= 96,
                    "RESOURCE_WORKLOAD_ESTIMATE_INVALID")
        for value, code in ((self.profile_id, "RESOURCE_PROFILE_IDENTIFIER_INVALID"),):
            if value is not None:
                identifier(value, code)
        for value, code in ((self.profile_revision, "RESOURCE_PROFILE_REVISION_INVALID"),
                            (self.source_digest, "RESOURCE_PROFILE_SOURCE_DIGEST_INVALID")):
            if value is not None:
                digest(value, code)
        if self.observed_monotonic_ns is not None:
            require(type(self.observed_monotonic_ns) is int and self.observed_monotonic_ns >= 0,
                    "RESOURCE_PROFILE_TIME_INVALID")
        if self.profile_snapshot_commitment is not None:
            digest(self.profile_snapshot_commitment, "RESOURCE_PROFILE_SNAPSHOT_COMMITMENT_INVALID")

    @property
    def admission_ready(self) -> bool:
        return (self.state == "MEASURED" and type(self.requirements) is ResourceVector
                and all(value is not None for value in
                        (self.profile_id, self.profile_revision, self.source_digest,
                         self.observed_monotonic_ns, self.profile_snapshot_commitment)))

    @property
    def conservative_requirements(self) -> ResourceVector | None:
        if not self.admission_ready:
            return None
        def add_margin(value: int) -> int: return value + (value * self.uncertainty_milli + 999) // 1000
        return ResourceVector(*(add_margin(value) for value in (self.requirements.cpu_milli, self.requirements.memory_bytes,
                                                                 self.requirements.storage_bytes, self.requirements.wall_time_ms)))


@dataclass(frozen=True, slots=True)
class MeasuredWorkloadProfile:
    """Bounded measured history for one exact workload class/profile revision."""
    workload_id: str
    profile_id: str
    profile_revision: str
    source_digest: str
    observed_monotonic_ns: int
    samples: tuple[ResourceVector, ...]
    confidence_milli: int
    calibration_count: int = 0

    def __post_init__(self) -> None:
        identifier(self.workload_id, "RESOURCE_WORKLOAD_IDENTIFIER_INVALID")
        identifier(self.profile_id, "RESOURCE_PROFILE_IDENTIFIER_INVALID")
        for value, code in ((self.profile_revision, "RESOURCE_PROFILE_REVISION_INVALID"),
                            (self.source_digest, "RESOURCE_PROFILE_SOURCE_DIGEST_INVALID")):
            digest(value, code)
        require(type(self.observed_monotonic_ns) is int and self.observed_monotonic_ns >= 0
                and type(self.samples) is tuple and 1 <= len(self.samples) <= 64
                and all(type(sample) is ResourceVector for sample in self.samples)
                and type(self.confidence_milli) is int and 0 <= self.confidence_milli <= 1000
                and type(self.calibration_count) is int and 0 <= self.calibration_count <= 2**31 - 1,
                "RESOURCE_WORKLOAD_PROFILE_INVALID")

    @property
    def snapshot_commitment(self) -> str:
        """A deterministic binding to the exact immutable profile snapshot."""
        payload = {
            "workload_id": self.workload_id,
            "profile_id": self.profile_id,
            "profile_revision": self.profile_revision,
            "source_digest": self.source_digest,
            "observed_monotonic_ns": self.observed_monotonic_ns,
            "samples": [
                [sample.cpu_milli, sample.memory_bytes, sample.storage_bytes, sample.wall_time_ms]
                for sample in self.samples
            ],
            "confidence_milli": self.confidence_milli,
            "calibration_count": self.calibration_count,
        }
        return "sha256:" + hashlib.sha256(
            b"CETA:resource-profile-snapshot:v1\0" + canonical_bytes(payload)
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class ObservedWorkloadUsage:
    """One exact, identity-bound resource observation supplied by the owner."""
    workload_id: str
    profile_id: str
    profile_revision: str
    source_digest: str
    observed_monotonic_ns: int
    usage: ResourceVector

    def __post_init__(self) -> None:
        identifier(self.workload_id, "RESOURCE_WORKLOAD_IDENTIFIER_INVALID")
        identifier(self.profile_id, "RESOURCE_PROFILE_IDENTIFIER_INVALID")
        digest(self.profile_revision, "RESOURCE_PROFILE_REVISION_INVALID")
        digest(self.source_digest, "RESOURCE_PROFILE_SOURCE_DIGEST_INVALID")
        require(type(self.observed_monotonic_ns) is int and self.observed_monotonic_ns >= 0
                and type(self.usage) is ResourceVector, "RESOURCE_WORKLOAD_OBSERVATION_INVALID")


@dataclass(frozen=True, slots=True)
class WorkloadPeakComparison:
    state: str
    expected_conservative: ResourceVector | None
    observed: ResourceVector
    exceeded_dimensions: tuple[str, ...]

    def __post_init__(self) -> None:
        require(self.state in {"MEASURED", "UNAVAILABLE"} and type(self.observed) is ResourceVector
                and type(self.exceeded_dimensions) is tuple
                and all(value in {"CPU", "MEMORY", "STORAGE", "WALL_TIME"} for value in self.exceeded_dimensions),
                "RESOURCE_PEAK_COMPARISON_INVALID")
        if self.state == "MEASURED":
            require(type(self.expected_conservative) is ResourceVector, "RESOURCE_PEAK_COMPARISON_INVALID")
        else:
            require(self.expected_conservative is None and not self.exceeded_dimensions,
                    "RESOURCE_PEAK_COMPARISON_INVALID")


@dataclass(frozen=True, slots=True)
class WorkloadProfileCalibration:
    state: str
    comparison: WorkloadPeakComparison
    profile: MeasuredWorkloadProfile | None
    reason_code: str | None

    def __post_init__(self) -> None:
        require(self.state in {"MEASURED", "UNAVAILABLE"} and type(self.comparison) is WorkloadPeakComparison,
                "RESOURCE_PROFILE_CALIBRATION_INVALID")
        if self.state == "MEASURED":
            require(type(self.profile) is MeasuredWorkloadProfile and self.reason_code is None
                    and self.comparison.state == "MEASURED", "RESOURCE_PROFILE_CALIBRATION_INVALID")
        else:
            require(self.profile is None and type(self.reason_code) is str and 1 <= len(self.reason_code) <= 96
                    and self.comparison.state == "UNAVAILABLE", "RESOURCE_PROFILE_CALIBRATION_INVALID")


class WorkloadRequirementEstimator:
    """Derives only bounded, conservative estimates from injected measured profiles."""
    def __init__(self, profiles: tuple[MeasuredWorkloadProfile, ...], *, clock=time.monotonic_ns,
                 maximum_profile_age_ns: int = 300_000_000_000, headroom_milli: int = 100) -> None:
        require(type(profiles) is tuple and len(profiles) <= 256
                and all(type(profile) is MeasuredWorkloadProfile for profile in profiles)
                and len({profile.workload_id for profile in profiles}) == len(profiles)
                and callable(clock) and type(maximum_profile_age_ns) is int and 1 <= maximum_profile_age_ns <= 300_000_000_000
                and type(headroom_milli) is int and 0 <= headroom_milli <= 1000,
                "RESOURCE_ESTIMATOR_INPUT_INVALID")
        self._profiles = {profile.workload_id: profile for profile in profiles}
        self._clock, self._maximum_age_ns, self._headroom_milli = clock, maximum_profile_age_ns, headroom_milli

    def estimate(self, workload_id: str, *, expected_profile_revision: str | None = None) -> WorkloadEstimate:
        identifier(workload_id, "RESOURCE_WORKLOAD_IDENTIFIER_INVALID")
        if expected_profile_revision is not None:
            digest(expected_profile_revision, "RESOURCE_PROFILE_REVISION_INVALID")
        profile = self._profiles.get(workload_id)
        if profile is None:
            return WorkloadEstimate(workload_id, None, 1000, "PROFILE_UNAVAILABLE", "UNRESOLVED",
                                    confidence_milli=0, reason_code="PROFILE_UNKNOWN")
        if expected_profile_revision is None:
            return self._unresolved(profile, "PROFILE_REVISION_REQUIRED")
        if expected_profile_revision is not None and expected_profile_revision != profile.profile_revision:
            return self._unresolved(profile, "PROFILE_REVISION_STALE")
        now_ns = self._clock()
        require(type(now_ns) is int and now_ns >= 0, "RESOURCE_ESTIMATOR_CLOCK_INVALID")
        if now_ns < profile.observed_monotonic_ns or now_ns - profile.observed_monotonic_ns > self._maximum_age_ns:
            return self._unresolved(profile, "PROFILE_STALE")
        peaks = ResourceVector(*(max(getattr(sample, field) for sample in profile.samples)
                                 for field in ("cpu_milli", "memory_bytes", "storage_bytes", "wall_time_ms")))
        return WorkloadEstimate(profile.workload_id, peaks, self._headroom_milli, "MEASURED_PROFILE",
                                "MEASURED", profile.profile_id, profile.profile_revision, profile.source_digest,
                                profile.confidence_milli, profile.observed_monotonic_ns, None,
                                profile.snapshot_commitment)

    def calibrate(self, observation: ObservedWorkloadUsage, preceding_estimate: WorkloadEstimate, *,
                  profile: MeasuredWorkloadProfile | None = None,
                  bootstrap_profile: MeasuredWorkloadProfile | None = None) -> WorkloadProfileCalibration:
        """Return a new bounded profile; no profile registry is mutated here."""
        require(type(observation) is ObservedWorkloadUsage and type(preceding_estimate) is WorkloadEstimate
                and (profile is None or type(profile) is MeasuredWorkloadProfile),
                "RESOURCE_PROFILE_CALIBRATION_INPUT_INVALID")
        require(bootstrap_profile is None or type(bootstrap_profile) is MeasuredWorkloadProfile,
                "RESOURCE_PROFILE_CALIBRATION_INPUT_INVALID")
        require(not (profile is not None and bootstrap_profile is not None),
                "RESOURCE_PROFILE_CALIBRATION_AMBIGUOUS_BASE")
        base = profile or bootstrap_profile or self._profiles.get(observation.workload_id)
        require(type(base) is MeasuredWorkloadProfile, "RESOURCE_PROFILE_UNKNOWN")
        self._require_profile_identity(base, observation)
        now_ns = self._clock()
        require(type(now_ns) is int and now_ns >= 0, "RESOURCE_ESTIMATOR_CLOCK_INVALID")
        require(now_ns >= base.observed_monotonic_ns
                and now_ns - base.observed_monotonic_ns <= self._maximum_age_ns
                and now_ns >= observation.observed_monotonic_ns
                and now_ns - observation.observed_monotonic_ns <= self._maximum_age_ns,
                "RESOURCE_PROFILE_OR_OBSERVATION_STALE")
        require(observation.observed_monotonic_ns > base.observed_monotonic_ns,
                "RESOURCE_PROFILE_OBSERVATION_NON_MONOTONIC")
        require(len(base.samples) < 64, "RESOURCE_PROFILE_HISTORY_BOUND_EXCEEDED")
        if not self._estimate_matches(preceding_estimate, observation, base):
            comparison = WorkloadPeakComparison("UNAVAILABLE", None, observation.usage, ())
            return WorkloadProfileCalibration("UNAVAILABLE", comparison, None,
                                              "PRECEDING_ESTIMATE_UNAVAILABLE")
        expected = preceding_estimate.conservative_requirements
        require(type(expected) is ResourceVector, "RESOURCE_WORKLOAD_ESTIMATE_INVALID")
        names = ("CPU", "MEMORY", "STORAGE", "WALL_TIME")
        actual_values = (observation.usage.cpu_milli, observation.usage.memory_bytes,
                         observation.usage.storage_bytes, observation.usage.wall_time_ms)
        expected_values = (expected.cpu_milli, expected.memory_bytes, expected.storage_bytes, expected.wall_time_ms)
        comparison = WorkloadPeakComparison("MEASURED", expected, observation.usage,
                                            tuple(name for name, actual, bound in zip(names, actual_values, expected_values)
                                                  if actual > bound))
        updated = MeasuredWorkloadProfile(base.workload_id, base.profile_id, base.profile_revision,
                                          base.source_digest, observation.observed_monotonic_ns,
                                          base.samples + (observation.usage,), base.confidence_milli,
                                          base.calibration_count + 1)
        return WorkloadProfileCalibration("MEASURED", comparison, updated, None)

    @staticmethod
    def _require_profile_identity(profile: MeasuredWorkloadProfile, observation: ObservedWorkloadUsage) -> None:
        require((profile.workload_id, profile.profile_id, profile.profile_revision, profile.source_digest)
                == (observation.workload_id, observation.profile_id, observation.profile_revision,
                    observation.source_digest), "RESOURCE_PROFILE_IDENTITY_MISMATCH")

    @staticmethod
    def _estimate_matches(estimate: WorkloadEstimate, observation: ObservedWorkloadUsage,
                          base: MeasuredWorkloadProfile) -> bool:
        return (estimate.admission_ready and estimate.profile_id == observation.profile_id
                and estimate.profile_revision == observation.profile_revision
                and estimate.source_digest == observation.source_digest
                and estimate.workload_id == observation.workload_id
                and estimate.profile_snapshot_commitment == base.snapshot_commitment)

    @staticmethod
    def _unresolved(profile: MeasuredWorkloadProfile, reason_code: str) -> WorkloadEstimate:
        return WorkloadEstimate(profile.workload_id, None, 1000, "MEASURED_PROFILE", "UNRESOLVED",
                                profile.profile_id, profile.profile_revision, profile.source_digest,
                                profile.confidence_milli, profile.observed_monotonic_ns, reason_code)


@dataclass(frozen=True, slots=True)
class AdmissionRequest:
    request_id: str
    budget: BudgetEnvelope
    estimate: WorkloadEstimate
    observation_sequence: int
    observation_monotonic_ns: int
    observation_current: bool
    pressure: PressureLevel

    def __post_init__(self) -> None:
        identifier(self.request_id, "RESOURCE_ADMISSION_IDENTIFIER_INVALID")
        require(type(self.budget) is BudgetEnvelope and type(self.estimate) is WorkloadEstimate
                and type(self.observation_sequence) is int and self.observation_sequence >= 0
                and type(self.observation_monotonic_ns) is int and self.observation_monotonic_ns >= 0
                and type(self.observation_current) is bool and type(self.pressure) is PressureLevel,
                "RESOURCE_ADMISSION_REQUEST_INVALID")


class WorkloadAdmissionController:
    """Does not launch workloads. Atomic reservation remains with ``ReservationPort``."""
    def __init__(self, reservations: ReservationPort, *, clock=time.monotonic_ns,
                 maximum_observation_age_ns: int = 30_000_000_000) -> None:
        require(callable(clock) and type(maximum_observation_age_ns) is int
                and 1 <= maximum_observation_age_ns <= 300_000_000_000,
                "RESOURCE_ADMISSION_CLOCK_INVALID")
        self._reservations, self._clock, self._maximum_age_ns = reservations, clock, maximum_observation_age_ns

    def admit(self, request: AdmissionRequest) -> ReservationResult:
        now_ns = self._clock()
        require(type(now_ns) is int and now_ns >= 0, "RESOURCE_ADMISSION_CLOCK_INVALID")
        stale = now_ns < request.observation_monotonic_ns or now_ns - request.observation_monotonic_ns > self._maximum_age_ns
        if not request.observation_current or stale:
            return ReservationResult(AdmissionState.STALE, None, None, ("CAPACITY_OBSERVATION_STALE",))
        if request.pressure is not PressureLevel.NORMAL:
            return ReservationResult(AdmissionState.BLOCKED, None, None, ("PRESSURE_ADMISSION_CLOSED",))
        if not request.estimate.admission_ready:
            reason = request.estimate.reason_code or "WORKLOAD_ESTIMATE_UNRESOLVED"
            return ReservationResult(AdmissionState.UNCERTAIN, None, None,
                                     ("WORKLOAD_ESTIMATE_UNRESOLVED", reason))
        requirements = request.estimate.conservative_requirements
        require(type(requirements) is ResourceVector, "RESOURCE_WORKLOAD_ESTIMATE_INVALID")
        ok, codes = assess_budget(request.budget, requirements)
        if not ok:
            return ReservationResult(AdmissionState.REJECTED, None, None, codes)
        return self._reservations.reserve(ReservationRequest(request.request_id, request.budget.budget_id,
            request.budget.generation, requirements, request.observation_sequence, request.observation_monotonic_ns))


def plan_concurrency(estimates: tuple[WorkloadEstimate, ...], capacity: ResourceVector,
                     *, control_reserve: ResourceVector) -> tuple[WorkloadEstimate, ...]:
    """Return a FIFO prefix that fits after an explicit resource reserve is held."""
    require(type(estimates) is tuple and all(type(item) is WorkloadEstimate for item in estimates)
            and type(capacity) is ResourceVector and type(control_reserve) is ResourceVector
            and control_reserve.fits_within(capacity),
            "RESOURCE_PLAN_INPUT_INVALID")
    admitted, used, allocatable = [], ResourceVector(0, 0, 0, 0), capacity.subtract(control_reserve)
    for estimate in estimates:
        if not estimate.admission_ready:
            break
        candidate = used.add(estimate.conservative_requirements)
        if candidate.fits_within(allocatable):
            admitted.append(estimate); used = candidate
        else:
            break
    return tuple(admitted)


@dataclass(frozen=True, slots=True)
class ConcurrentWorkloadPlan:
    admitted: tuple[WorkloadEstimate, ...]
    used: ResourceVector
    control_reserve: ResourceVector
    awaiting_owner_inputs: tuple[str, ...]


def plan_concurrency_with_facts(estimates: tuple[WorkloadEstimate, ...], capacity: ResourceVector,
                                *, control_reserve: ResourceVector) -> ConcurrentWorkloadPlan:
    """Describe capacity-only planning and label inputs this namespace does not own."""
    admitted = plan_concurrency(estimates, capacity, control_reserve=control_reserve)
    used = ResourceVector(0, 0, 0, 0)
    for estimate in admitted:
        requirements = estimate.conservative_requirements
        require(type(requirements) is ResourceVector, "RESOURCE_WORKLOAD_ESTIMATE_INVALID")
        used = used.add(requirements)
    return ConcurrentWorkloadPlan(admitted, used, control_reserve,
                                  ("AWAITING_OWNER_FAIRNESS_INPUT", "AWAITING_OWNER_AUTHORITY_READINESS_INPUT",
                                   "AWAITING_OWNER_SHARED_FILE_CONFLICT_INPUT"))
