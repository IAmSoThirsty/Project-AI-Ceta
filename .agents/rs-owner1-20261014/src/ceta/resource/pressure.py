"""Explicit pressure classification with recovery hysteresis."""
from dataclasses import dataclass
import threading
import time

from ceta.contracts.resource_management import CapacitySnapshot, PressureLevel, digest, identifier, require


@dataclass(frozen=True, slots=True)
class PressureThresholds:
    elevated_milli: int = 800
    critical_milli: int = 925
    recover_milli: int = 650
    recovery_samples: int = 3

    def __post_init__(self) -> None:
        require(all(type(v) is int for v in (self.elevated_milli, self.critical_milli, self.recover_milli, self.recovery_samples))
                and 0 <= self.recover_milli < self.elevated_milli < self.critical_milli <= 1000
                and 1 <= self.recovery_samples <= 64, "RESOURCE_PRESSURE_THRESHOLDS_INVALID")


@dataclass(frozen=True, slots=True)
class PressureDecision:
    level: PressureLevel
    admission_open: bool
    observed_milli: int | None
    recovery_samples_remaining: int
    reason: str


@dataclass(frozen=True, slots=True)
class TaskAuthorityBinding:
    """Pinned identity for an owner-facing recommendation, never authority itself."""
    task_id: str
    task_revision: str
    authority_generation: int
    authority_digest: str

    def __post_init__(self) -> None:
        identifier(self.task_id, "RESOURCE_THROTTLE_TASK_IDENTIFIER_INVALID")
        digest(self.task_revision, "RESOURCE_THROTTLE_TASK_REVISION_INVALID")
        require(type(self.authority_generation) is int and self.authority_generation >= 0,
                "RESOURCE_THROTTLE_AUTHORITY_GENERATION_INVALID")
        digest(self.authority_digest, "RESOURCE_THROTTLE_AUTHORITY_DIGEST_INVALID")


@dataclass(frozen=True, slots=True)
class ThrottleRequest:
    binding: TaskAuthorityBinding
    pressure: PressureLevel
    action: str
    current_limit: int
    proposed_limit: int
    preserves_verification: bool
    preserves_evidence: bool
    preserves_stop_capacity: bool
    preserves_recovery_capacity: bool
    current_authority_generation: int
    cancelled: bool = False

    def __post_init__(self) -> None:
        require(type(self.binding) is TaskAuthorityBinding and type(self.pressure) is PressureLevel
                and self.action in {"OPTIONAL_BACKGROUND_PAUSE", "CONCURRENCY_LIMIT", "STREAM_RATE_LIMIT", "BATCH_SIZE_LIMIT"}
                and type(self.current_limit) is int and type(self.proposed_limit) is int
                and 0 <= self.proposed_limit <= self.current_limit <= 2**31 - 1
                and all(type(value) is bool for value in (self.preserves_verification, self.preserves_evidence,
                    self.preserves_stop_capacity, self.preserves_recovery_capacity, self.cancelled))
                and type(self.current_authority_generation) is int and self.current_authority_generation >= 0,
                "RESOURCE_THROTTLE_REQUEST_INVALID")


@dataclass(frozen=True, slots=True)
class ThrottleRecommendation:
    state: str
    binding: TaskAuthorityBinding
    action: str | None
    proposed_limit: int | None
    reason_codes: tuple[str, ...]


class WorkloadThrottlingController:
    """Produces pure recommendations; no scheduler, worker or state owner exists here."""
    def recommend(self, request: ThrottleRequest) -> ThrottleRecommendation:
        require(type(request) is ThrottleRequest, "RESOURCE_THROTTLE_REQUEST_REQUIRED")
        if request.cancelled:
            return ThrottleRecommendation("CANCELLED", request.binding, None, None, ("CANCELLATION_OBSERVED",))
        if request.binding.authority_generation != request.current_authority_generation:
            return ThrottleRecommendation("STALE", request.binding, None, None, ("AUTHORITY_GENERATION_STALE",))
        safeguards = (request.preserves_verification, request.preserves_evidence,
                      request.preserves_stop_capacity, request.preserves_recovery_capacity)
        if not all(safeguards):
            return ThrottleRecommendation("BLOCKED", request.binding, None, None, ("REQUIRED_GUARDRAIL_WEAKENED",))
        if request.pressure not in {PressureLevel.ELEVATED, PressureLevel.CRITICAL}:
            return ThrottleRecommendation("NO_CHANGE", request.binding, None, None, ("PRESSURE_NOT_ACTIONABLE",))
        if request.proposed_limit >= request.current_limit:
            return ThrottleRecommendation("NO_CHANGE", request.binding, None, None, ("NO_EFFECTIVE_REDUCTION",))
        return ThrottleRecommendation("RECOMMEND", request.binding, request.action, request.proposed_limit,
                                      ("OPTIONAL_CAPABILITY_REDUCTION",))


@dataclass(frozen=True, slots=True)
class ReducedResourceMode:
    mode_id: str
    mode_digest: str
    prequalified: bool
    preserves_verification: bool
    preserves_evidence: bool
    preserves_stop_capacity: bool
    preserves_recovery_capacity: bool
    changes_quality: bool
    changes_scope: bool

    def __post_init__(self) -> None:
        identifier(self.mode_id, "RESOURCE_DEGRADATION_MODE_IDENTIFIER_INVALID")
        digest(self.mode_digest, "RESOURCE_DEGRADATION_MODE_DIGEST_INVALID")
        require(all(type(value) is bool for value in (self.prequalified, self.preserves_verification,
                self.preserves_evidence, self.preserves_stop_capacity, self.preserves_recovery_capacity,
                self.changes_quality, self.changes_scope)), "RESOURCE_DEGRADATION_MODE_INVALID")


@dataclass(frozen=True, slots=True)
class DegradationRequest:
    binding: TaskAuthorityBinding
    mode: ReducedResourceMode
    current_authority_generation: int
    new_decision_id: str | None = None
    cancelled: bool = False

    def __post_init__(self) -> None:
        require(type(self.binding) is TaskAuthorityBinding and type(self.mode) is ReducedResourceMode
                and type(self.current_authority_generation) is int and self.current_authority_generation >= 0
                and type(self.cancelled) is bool, "RESOURCE_DEGRADATION_REQUEST_INVALID")
        if self.new_decision_id is not None:
            identifier(self.new_decision_id, "RESOURCE_DEGRADATION_DECISION_IDENTIFIER_INVALID")


@dataclass(frozen=True, slots=True)
class DegradationPlan:
    state: str
    binding: TaskAuthorityBinding
    mode_id: str | None
    decision_required: bool
    reason_codes: tuple[str, ...]


class GracefulDegradationCoordinator:
    """Selects a prequalified mode only; effect and state application stay injected."""
    def plan(self, request: DegradationRequest) -> DegradationPlan:
        require(type(request) is DegradationRequest, "RESOURCE_DEGRADATION_REQUEST_REQUIRED")
        if request.cancelled:
            return DegradationPlan("CANCELLED", request.binding, None, False, ("CANCELLATION_OBSERVED",))
        if request.binding.authority_generation != request.current_authority_generation:
            return DegradationPlan("STALE", request.binding, None, False, ("AUTHORITY_GENERATION_STALE",))
        mode = request.mode
        safeguards = (mode.preserves_verification, mode.preserves_evidence,
                      mode.preserves_stop_capacity, mode.preserves_recovery_capacity)
        if not mode.prequalified:
            return DegradationPlan("BLOCKED", request.binding, None, False, ("MODE_NOT_PREQUALIFIED",))
        if not all(safeguards):
            return DegradationPlan("BLOCKED", request.binding, None, False, ("REQUIRED_GUARDRAIL_WEAKENED",))
        needs_decision = mode.changes_quality or mode.changes_scope
        if needs_decision:
            reason_codes = ("QUALITY_OR_SCOPE_CHANGED", "CANONICAL_DECISION_VERIFICATION_REQUIRED")
            if request.new_decision_id is not None:
                reason_codes += ("DECISION_CORRELATION_UNVERIFIED",)
            return DegradationPlan("DECISION_REQUIRED", request.binding, None, True, reason_codes)
        return DegradationPlan("PLAN", request.binding, mode.mode_id, needs_decision,
                               ("PREQUALIFIED_REDUCED_MODE",))


class ResourcePressureDetector:
    """Derived pressure for one ordered kind/method stream, with bounded replay state.

    The caller creates a fresh detector when replacing a sampler. The shared
    snapshot has no authenticated physical-resource identity or producer epoch;
    canonical source binding and pressure publication remain outside this unit.
    """
    def __init__(self, thresholds: PressureThresholds = PressureThresholds(), *, clock=time.monotonic_ns,
                 maximum_observation_age_ns: int = 30_000_000_000) -> None:
        require(callable(clock) and type(maximum_observation_age_ns) is int
                and 1 <= maximum_observation_age_ns <= 300_000_000_000,
                "RESOURCE_PRESSURE_CLOCK_INVALID")
        self._thresholds = thresholds
        self._clock, self._maximum_age_ns = clock, maximum_observation_age_ns
        self._level = PressureLevel.NORMAL
        self._stable = 0
        self._stream = None
        self._last_snapshot: CapacitySnapshot | None = None
        self._last_seen_snapshot: CapacitySnapshot | None = None
        self._last_clock_ns = -1
        self._lock = threading.Lock()

    def _close(self, value: int | None, reason: str) -> PressureDecision:
        # Invalid observations never erase the accepted stream/order high-water.
        self._level, self._stable = PressureLevel.UNKNOWN, 0
        return PressureDecision(self._level, False, value, self._thresholds.recovery_samples, reason)

    def observe(self, snapshot: CapacitySnapshot, *, current: bool) -> PressureDecision:
        require(type(snapshot) is CapacitySnapshot and type(current) is bool, "RESOURCE_PRESSURE_INPUT_INVALID")
        value = snapshot.utilization_milli.value if snapshot.utilization_milli.measured else None
        with self._lock:
            now_ns = self._clock()
            require(type(now_ns) is int and now_ns >= 0, "RESOURCE_PRESSURE_CLOCK_INVALID")
            observations = (snapshot.total, snapshot.free, snapshot.reservable, snapshot.utilization_milli)
            stream = (snapshot.kind, tuple(item.method for item in observations))
            if self._stream is not None and stream != self._stream:
                return self._close(value, "OBSERVATION_STREAM_CHANGED")
            self._stream = stream
            seen = self._last_seen_snapshot
            duplicate = seen is not None and snapshot == seen
            if seen is not None:
                if snapshot.sequence < seen.sequence:
                    return self._close(value, "OBSERVATION_ORDER_INVALID")
                if snapshot.sequence == seen.sequence and not duplicate:
                    return self._close(value, "OBSERVATION_IDENTITY_CONFLICT")
            if not duplicate:
                # Remember rejected currentness/availability too: relabelling a
                # cached input as current cannot become a new recovery sample.
                self._last_seen_snapshot = snapshot
            if now_ns < self._last_clock_ns:
                return self._close(value, "OBSERVATION_CLOCK_ROLLBACK")
            self._last_clock_ns = now_ns
            if not current or not snapshot.is_recent(now_ns, self._maximum_age_ns) or value is None:
                return self._close(value, "OBSERVATION_UNAVAILABLE_OR_STALE")
            if len({item.observed_monotonic_ns for item in observations}) != 1:
                return self._close(value, "OBSERVATION_INCOHERENT")
            if duplicate:
                remaining = 0 if self._level is PressureLevel.NORMAL else self._thresholds.recovery_samples - self._stable
                return PressureDecision(self._level, self._level is PressureLevel.NORMAL, value,
                                        remaining, "DUPLICATE_OBSERVATION")
            previous = self._last_snapshot
            if previous is not None:
                prior_observations = (previous.total, previous.free, previous.reservable, previous.utilization_milli)
                if snapshot.sequence < previous.sequence or any(
                        item.observed_monotonic_ns <= prior.observed_monotonic_ns
                        for item, prior in zip(observations, prior_observations)):
                    return self._close(value, "OBSERVATION_ORDER_INVALID")
            self._last_snapshot = snapshot
            if value >= self._thresholds.critical_milli:
                self._level, self._stable = PressureLevel.CRITICAL, 0
                return PressureDecision(self._level, False, value, self._thresholds.recovery_samples, "CRITICAL_PRESSURE")
            if value >= self._thresholds.elevated_milli:
                self._level, self._stable = PressureLevel.ELEVATED, 0
                return PressureDecision(self._level, False, value, self._thresholds.recovery_samples, "ELEVATED_PRESSURE")
            if self._level in (PressureLevel.CRITICAL, PressureLevel.ELEVATED, PressureLevel.UNKNOWN):
                if value <= self._thresholds.recover_milli:
                    self._stable += 1
                    if self._stable >= self._thresholds.recovery_samples:
                        self._level, self._stable = PressureLevel.NORMAL, 0
                        return PressureDecision(self._level, True, value, 0, "RECOVERED_AFTER_HYSTERESIS")
                else:
                    self._stable = 0
                return PressureDecision(self._level, False, value, self._thresholds.recovery_samples - self._stable,
                                        "RECOVERY_HYSTERESIS")
            return PressureDecision(PressureLevel.NORMAL, True, value, 0, "NORMAL")

