"""Pure budget checks and admission preparation through the canonical port."""
from dataclasses import dataclass
import hashlib
import time

from ceta.contracts.resource_management import (
    AdmissionState, BudgetEnvelope, PressureLevel, ReservationPort, ReservationRequest, ReservationResult,
    ResourceVector, digest, identifier, require,
)
from ceta.contracts.wire import canonical_bytes
from ceta.contracts.temporal import ClockSample, Deadline, require_clock_progress
from ceta.contracts.wire import ContractError
from ceta.resource.budget import aggregate_checks, ExecutionTimeBudgetController, project_workload_budget


MAXIMUM_PLANNING_WORKLOADS = 256
_VECTOR_FIELDS = ("cpu_milli", "memory_bytes", "storage_bytes", "wall_time_ms")


@dataclass(frozen=True, slots=True)
class WorkloadShape:
    """Exact measured input shape; this is neither a scaling model nor authority."""
    workload_class: str
    model_revision: str
    configuration_digest: str
    input_units: int
    input_unit: str
    concurrency: int

    def __post_init__(self) -> None:
        identifier(self.workload_class, "RESOURCE_WORKLOAD_CLASS_INVALID")
        digest(self.model_revision, "RESOURCE_MODEL_REVISION_INVALID")
        digest(self.configuration_digest, "RESOURCE_CONFIGURATION_DIGEST_INVALID")
        identifier(self.input_unit, "RESOURCE_INPUT_UNIT_INVALID")
        require(type(self.input_units) is int and 0 <= self.input_units <= 2**63 - 1
                and type(self.concurrency) is int and 1 <= self.concurrency <= 256,
                "RESOURCE_WORKLOAD_SHAPE_INVALID")

    @property
    def commitment(self) -> str:
        payload = [self.workload_class, self.model_revision, self.configuration_digest,
                   self.input_units, self.input_unit, self.concurrency]
        return "sha256:" + hashlib.sha256(
            b"CETA:workload-shape:v1\0" + canonical_bytes(payload)).hexdigest()


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
    workload_shape: WorkloadShape | None = None
    steady_requirements: ResourceVector | None = None

    def __post_init__(self) -> None:
        identifier(self.workload_id, "RESOURCE_WORKLOAD_IDENTIFIER_INVALID")
        require(type(self.uncertainty_milli) is int and 0 <= self.uncertainty_milli <= 1000
                and type(self.source) is str and 1 <= len(self.source) <= 160
                and type(self.state) is str and self.state in {"MEASURED", "UNRESOLVED"}
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
        require(self.workload_shape is None or type(self.workload_shape) is WorkloadShape,
                "RESOURCE_WORKLOAD_SHAPE_INVALID")
        require(self.steady_requirements is None or (self.state == "MEASURED"
                and type(self.steady_requirements) is ResourceVector
                and self.steady_requirements.fits_within(self.requirements)),
                "RESOURCE_WORKLOAD_STEADY_INVALID")

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
        values = tuple(value + (value * self.uncertainty_milli + 999) // 1000
                       for value in (getattr(self.requirements, field) for field in _VECTOR_FIELDS))
        require(all(value <= 2**63 - 1 for value in values), "RESOURCE_ESTIMATE_BOUND_EXCEEDED")
        return ResourceVector(*values)


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
    workload_shape: WorkloadShape | None = None
    steady_samples: tuple[ResourceVector, ...] | None = None

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
        require(self.workload_shape is None or type(self.workload_shape) is WorkloadShape,
                "RESOURCE_WORKLOAD_SHAPE_INVALID")
        require(self.steady_samples is None or (type(self.steady_samples) is tuple
                and len(self.steady_samples) == len(self.samples)
                and all(type(steady) is ResourceVector and steady.fits_within(peak)
                        for steady, peak in zip(self.steady_samples, self.samples))),
                "RESOURCE_WORKLOAD_STEADY_INVALID")

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
        prefix = b"CETA:resource-profile-snapshot:v1\0"
        if self.workload_shape is not None or self.steady_samples is not None:
            payload["workload_shape"] = self.workload_shape.commitment if self.workload_shape is not None else None
            payload["steady_samples"] = ([list(getattr(sample, field) for field in _VECTOR_FIELDS)
                                         for sample in self.steady_samples]
                                        if self.steady_samples is not None else None)
            prefix = b"CETA:resource-profile-snapshot:v2\0"
        return "sha256:" + hashlib.sha256(prefix + canonical_bytes(payload)).hexdigest()


@dataclass(frozen=True, slots=True)
class ObservedWorkloadUsage:
    """One exact, identity-bound resource observation supplied by the owner."""
    workload_id: str
    profile_id: str
    profile_revision: str
    source_digest: str
    observed_monotonic_ns: int
    usage: ResourceVector
    workload_shape: WorkloadShape | None = None
    steady_usage: ResourceVector | None = None

    def __post_init__(self) -> None:
        identifier(self.workload_id, "RESOURCE_WORKLOAD_IDENTIFIER_INVALID")
        identifier(self.profile_id, "RESOURCE_PROFILE_IDENTIFIER_INVALID")
        digest(self.profile_revision, "RESOURCE_PROFILE_REVISION_INVALID")
        digest(self.source_digest, "RESOURCE_PROFILE_SOURCE_DIGEST_INVALID")
        require(type(self.observed_monotonic_ns) is int and self.observed_monotonic_ns >= 0
                and type(self.usage) is ResourceVector, "RESOURCE_WORKLOAD_OBSERVATION_INVALID")
        require(self.workload_shape is None or type(self.workload_shape) is WorkloadShape,
                "RESOURCE_WORKLOAD_SHAPE_INVALID")
        require(self.steady_usage is None or (type(self.steady_usage) is ResourceVector
                and self.steady_usage.fits_within(self.usage)), "RESOURCE_WORKLOAD_STEADY_INVALID")


@dataclass(frozen=True, slots=True)
class WorkloadPeakComparison:
    state: str
    expected_conservative: ResourceVector | None
    observed: ResourceVector
    exceeded_dimensions: tuple[str, ...]

    def __post_init__(self) -> None:
        require(type(self.state) is str and self.state in {"MEASURED", "UNAVAILABLE"} and type(self.observed) is ResourceVector
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
        require(type(self.state) is str and self.state in {"MEASURED", "UNAVAILABLE"} and type(self.comparison) is WorkloadPeakComparison,
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

    def estimate(self, workload_id: str, *, expected_profile_revision: str | None = None,
                 expected_workload_shape: WorkloadShape | None = None) -> WorkloadEstimate:
        identifier(workload_id, "RESOURCE_WORKLOAD_IDENTIFIER_INVALID")
        if expected_profile_revision is not None:
            digest(expected_profile_revision, "RESOURCE_PROFILE_REVISION_INVALID")
        require(expected_workload_shape is None or type(expected_workload_shape) is WorkloadShape,
                "RESOURCE_WORKLOAD_SHAPE_INVALID")
        profile = self._profiles.get(workload_id)
        if profile is None:
            return WorkloadEstimate(workload_id, None, 1000, "PROFILE_UNAVAILABLE", "UNRESOLVED",
                                    confidence_milli=0, reason_code="PROFILE_UNKNOWN")
        if expected_profile_revision is None:
            return self._unresolved(profile, "PROFILE_REVISION_REQUIRED")
        if expected_profile_revision is not None and expected_profile_revision != profile.profile_revision:
            return self._unresolved(profile, "PROFILE_REVISION_STALE")
        if profile.workload_shape is not None and expected_workload_shape is None:
            return self._unresolved(profile, "WORKLOAD_SHAPE_REQUIRED")
        if expected_workload_shape != profile.workload_shape:
            return self._unresolved(profile, "WORKLOAD_SHAPE_UNQUALIFIED")
        now_ns = self._clock()
        require(type(now_ns) is int and now_ns >= 0, "RESOURCE_ESTIMATOR_CLOCK_INVALID")
        if now_ns < profile.observed_monotonic_ns or now_ns - profile.observed_monotonic_ns > self._maximum_age_ns:
            return self._unresolved(profile, "PROFILE_STALE")
        peaks = ResourceVector(*(max(getattr(sample, field) for sample in profile.samples)
                                 for field in _VECTOR_FIELDS))
        steady = (ResourceVector(*(max(getattr(sample, field) for sample in profile.steady_samples)
                                   for field in _VECTOR_FIELDS))
                  if profile.steady_samples is not None else None)
        estimate = WorkloadEstimate(profile.workload_id, peaks, self._headroom_milli, "MEASURED_PROFILE",
                                "MEASURED", profile.profile_id, profile.profile_revision, profile.source_digest,
                                profile.confidence_milli, profile.observed_monotonic_ns, None,
                                profile.snapshot_commitment, profile.workload_shape, steady)
        try:
            estimate.conservative_requirements
        except ContractError as error:
            if error.code != "RESOURCE_ESTIMATE_BOUND_EXCEEDED":
                raise
            return self._unresolved(profile, "ESTIMATE_BOUND_EXCEEDED")
        return estimate

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
        require(base.calibration_count < 2**31 - 1, "RESOURCE_PROFILE_CALIBRATION_BOUND_EXCEEDED")
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
                                          base.calibration_count + 1, base.workload_shape,
                                          (base.steady_samples + (observation.steady_usage,)
                                           if base.steady_samples is not None and observation.steady_usage is not None
                                           else None))
        return WorkloadProfileCalibration("MEASURED", comparison, updated, None)

    @staticmethod
    def _require_profile_identity(profile: MeasuredWorkloadProfile, observation: ObservedWorkloadUsage) -> None:
        require((profile.workload_id, profile.profile_id, profile.profile_revision, profile.source_digest)
                == (observation.workload_id, observation.profile_id, observation.profile_revision,
                    observation.source_digest), "RESOURCE_PROFILE_IDENTITY_MISMATCH")
        require(profile.workload_shape == observation.workload_shape, "RESOURCE_WORKLOAD_SHAPE_MISMATCH")

    def _estimate_matches(self, estimate: WorkloadEstimate, observation: ObservedWorkloadUsage,
                          base: MeasuredWorkloadProfile) -> bool:
        peaks = ResourceVector(*(max(getattr(sample, field) for sample in base.samples) for field in _VECTOR_FIELDS))
        steady = (ResourceVector(*(max(getattr(sample, field) for sample in base.steady_samples)
                                   for field in _VECTOR_FIELDS)) if base.steady_samples is not None else None)
        return (estimate.admission_ready and estimate.profile_id == observation.profile_id
                and estimate.profile_revision == observation.profile_revision
                and estimate.source_digest == observation.source_digest
                and estimate.workload_id == observation.workload_id
                and estimate.workload_shape == base.workload_shape
                and estimate.requirements == peaks and estimate.steady_requirements == steady
                and estimate.observed_monotonic_ns == base.observed_monotonic_ns
                and estimate.confidence_milli == base.confidence_milli
                and estimate.uncertainty_milli == self._headroom_milli
                and estimate.profile_snapshot_commitment == base.snapshot_commitment)

    @staticmethod
    def _unresolved(profile: MeasuredWorkloadProfile, reason_code: str) -> WorkloadEstimate:
        return WorkloadEstimate(profile.workload_id, None, 1000, "MEASURED_PROFILE", "UNRESOLVED",
                                profile.profile_id, profile.profile_revision, profile.source_digest,
                                profile.confidence_milli, profile.observed_monotonic_ns, reason_code,
                                workload_shape=profile.workload_shape)


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
                 maximum_observation_age_ns: int = 30_000_000_000,
                 maximum_profile_age_ns: int = 300_000_000_000,
                 minimum_confidence_milli: int = 1) -> None:
        require(callable(clock) and type(maximum_observation_age_ns) is int
                and 1 <= maximum_observation_age_ns <= 300_000_000_000,
                "RESOURCE_ADMISSION_CLOCK_INVALID")
        require(type(maximum_profile_age_ns) is int and 1 <= maximum_profile_age_ns <= 300_000_000_000
                and type(minimum_confidence_milli) is int and 1 <= minimum_confidence_milli <= 1000,
                "RESOURCE_ADMISSION_PROFILE_POLICY_INVALID")
        require(callable(getattr(reservations, "reserve", None)), "RESOURCE_RESERVATION_PORT_REQUIRED")
        self._reservations, self._clock, self._maximum_age_ns = reservations, clock, maximum_observation_age_ns
        self._maximum_profile_age_ns, self._minimum_confidence_milli = maximum_profile_age_ns, minimum_confidence_milli

    def admit(self, request: AdmissionRequest) -> ReservationResult:
        require(type(request) is AdmissionRequest, "RESOURCE_ADMISSION_REQUEST_REQUIRED")
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
        profile_time = request.estimate.observed_monotonic_ns
        if now_ns < profile_time or now_ns - profile_time > self._maximum_profile_age_ns:
            return ReservationResult(AdmissionState.STALE, None, None, ("WORKLOAD_PROFILE_STALE",))
        if request.estimate.confidence_milli < self._minimum_confidence_milli:
            return ReservationResult(AdmissionState.UNCERTAIN, None, None, ("WORKLOAD_PROFILE_CONFIDENCE_INSUFFICIENT",))
        try:
            requirements = request.estimate.conservative_requirements
        except ContractError as error:
            if error.code != "RESOURCE_ESTIMATE_BOUND_EXCEEDED":
                raise
            return ReservationResult(AdmissionState.UNCERTAIN, None, None, ("WORKLOAD_ESTIMATE_BOUND_EXCEEDED",))
        require(type(requirements) is ResourceVector, "RESOURCE_WORKLOAD_ESTIMATE_INVALID")
        ok, codes = assess_budget(request.budget, requirements)
        if not ok:
            return ReservationResult(AdmissionState.REJECTED, None, None, codes)
        # Sampling again closes elapsed-time gaps during preparation; the owner
        # still revalidates generation/currentness atomically when reserving.
        dispatch_ns = self._clock()
        require(type(dispatch_ns) is int and dispatch_ns >= 0, "RESOURCE_ADMISSION_CLOCK_INVALID")
        if (dispatch_ns < now_ns or dispatch_ns < request.observation_monotonic_ns
                or dispatch_ns - request.observation_monotonic_ns > self._maximum_age_ns
                or dispatch_ns < profile_time or dispatch_ns - profile_time > self._maximum_profile_age_ns):
            return ReservationResult(AdmissionState.STALE, None, None, ("ADMISSION_INPUT_EXPIRED_DURING_PREPARATION",))
        result = self._reservations.reserve(ReservationRequest(request.request_id, request.budget.budget_id,
            request.budget.generation, requirements, request.observation_sequence, request.observation_monotonic_ns))
        # A malformed response occurs after possible dispatch. Raise without
        # retry, release, or invented rollback; reconciliation belongs to owner.
        require(type(result) is ReservationResult, "RESOURCE_RESERVATION_RESULT_REQUIRED")
        result.__post_init__()
        return result


def plan_concurrency(estimates: tuple[WorkloadEstimate, ...], capacity: ResourceVector,
                     *, control_reserve: ResourceVector) -> tuple[WorkloadEstimate, ...]:
    """Return a FIFO prefix that fits after an explicit resource reserve is held."""
    require(type(estimates) is tuple and len(estimates) <= MAXIMUM_PLANNING_WORKLOADS
            and all(type(item) is WorkloadEstimate for item in estimates)
            and type(capacity) is ResourceVector and type(control_reserve) is ResourceVector
            and control_reserve.fits_within(capacity),
            "RESOURCE_PLAN_INPUT_INVALID")
    require(len({item.workload_id for item in estimates}) == len(estimates), "RESOURCE_PLAN_DUPLICATE_WORKLOAD")
    admitted, used, allocatable = [], ResourceVector(0, 0, 0, 0), capacity.subtract(control_reserve)
    for estimate in estimates:
        if not estimate.admission_ready:
            break
        try:
            requirements = estimate.conservative_requirements
        except ContractError as error:
            if error.code != "RESOURCE_ESTIMATE_BOUND_EXCEEDED":
                raise
            break
        # Compare before addition so a rejected sum cannot overflow the vector.
        if not requirements.fits_within(allocatable.subtract(used)):
            break
        admitted.append(estimate)
        used = used.add(requirements)
    return tuple(admitted)


@dataclass(frozen=True, slots=True)
class ConcurrentWorkloadPlan:
    admitted: tuple[WorkloadEstimate, ...]
    used: ResourceVector
    control_reserve: ResourceVector
    awaiting_owner_inputs: tuple[str, ...]

    def __post_init__(self) -> None:
        require(type(self.admitted) is tuple and len(self.admitted) <= MAXIMUM_PLANNING_WORKLOADS
                and all(type(item) is WorkloadEstimate and item.admission_ready for item in self.admitted)
                and len({item.workload_id for item in self.admitted}) == len(self.admitted)
                and type(self.used) is ResourceVector and type(self.control_reserve) is ResourceVector
                and type(self.awaiting_owner_inputs) is tuple and len(self.awaiting_owner_inputs) <= 16
                and all(type(code) is str and 1 <= len(code) <= 96 for code in self.awaiting_owner_inputs),
                "RESOURCE_PLAN_RESULT_INVALID")
        total = ResourceVector(0, 0, 0, 0)
        for item in self.admitted:
            total = total.add(item.conservative_requirements)
        require(total == self.used, "RESOURCE_PLAN_RESULT_INVALID")


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


@dataclass(frozen=True, slots=True)
class WorkloadPlanningFacts:
    """Declared owner snapshot for a proposal; readiness is never an authority grant.

    File keys are opaque canonical conflict identities, not interpreted paths.
    Unknown readiness/conflicts remain explicit. A changed owner generation or
    estimate snapshot invalidates the derived decision.
    """
    workload_id: str
    profile_snapshot_commitment: str
    owner_generation: int
    queued_monotonic_ns: int
    priority: int
    authority_ready: bool | None
    shared_file_keys: tuple[str, ...] | None
    cancelled: bool
    deadline: Deadline | None = None

    def __post_init__(self) -> None:
        identifier(self.workload_id, "RESOURCE_WORKLOAD_IDENTIFIER_INVALID")
        digest(self.profile_snapshot_commitment, "RESOURCE_PROFILE_SNAPSHOT_COMMITMENT_INVALID")
        require(type(self.owner_generation) is int and 0 <= self.owner_generation <= 2**63 - 1
                and type(self.queued_monotonic_ns) is int and 0 <= self.queued_monotonic_ns <= 2**63 - 1
                and type(self.priority) is int and -1000 <= self.priority <= 1000
                and (self.authority_ready is None or type(self.authority_ready) is bool)
                and type(self.cancelled) is bool
                and (self.deadline is None or type(self.deadline) is Deadline),
                "RESOURCE_PLANNING_FACTS_INVALID")
        if self.shared_file_keys is not None:
            require(type(self.shared_file_keys) is tuple and len(self.shared_file_keys) <= 64,
                    "RESOURCE_PLANNING_FILE_KEYS_INVALID")
            for key in self.shared_file_keys:
                identifier(key, "RESOURCE_PLANNING_FILE_KEYS_INVALID")
            require(len(set(self.shared_file_keys)) == len(self.shared_file_keys),
                    "RESOURCE_PLANNING_FILE_KEYS_INVALID")


@dataclass(frozen=True, slots=True)
class WorkloadPlanningDecision:
    workload_id: str
    state: str
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        identifier(self.workload_id, "RESOURCE_WORKLOAD_IDENTIFIER_INVALID")
        require(type(self.state) is str and self.state in {"PROPOSED", "BLOCKED", "STALE", "DEFERRED", "CANCELLED", "UNRESOLVED"}
                and type(self.reason_codes) is tuple and len(self.reason_codes) <= 4
                and all(type(code) is str and 1 <= len(code) <= 96 for code in self.reason_codes)
                and (not self.reason_codes if self.state == "PROPOSED" else bool(self.reason_codes)),
                "RESOURCE_PLANNING_DECISION_INVALID")


@dataclass(frozen=True, slots=True)
class BudgetConcurrentWorkloadPlan:
    """Pure plan pinned to budget and owner generations, without reservations."""
    budget: BudgetEnvelope
    expected_budget_generation: int
    owner_generation: int
    selected: tuple[WorkloadEstimate, ...]
    estimated_use: ResourceVector
    remaining: ResourceVector
    decisions: tuple[WorkloadPlanningDecision, ...]

    def __post_init__(self) -> None:
        require(type(self.budget) is BudgetEnvelope
                and type(self.expected_budget_generation) is int and 0 <= self.expected_budget_generation <= 2**63 - 1
                and type(self.owner_generation) is int and 0 <= self.owner_generation <= 2**63 - 1
                and type(self.selected) is tuple and len(self.selected) <= MAXIMUM_PLANNING_WORKLOADS
                and all(type(item) is WorkloadEstimate for item in self.selected)
                and type(self.estimated_use) is ResourceVector and type(self.remaining) is ResourceVector
                and type(self.decisions) is tuple and len(self.decisions) <= MAXIMUM_PLANNING_WORKLOADS
                and all(type(item) is WorkloadPlanningDecision for item in self.decisions),
                "RESOURCE_BUDGET_PLAN_INVALID")
        selected_ids = tuple(item.workload_id for item in self.selected)
        require(len(set(selected_ids)) == len(selected_ids)
                and len({item.workload_id for item in self.decisions}) == len(self.decisions)
                and set(selected_ids) == {item.workload_id for item in self.decisions if item.state == "PROPOSED"},
                "RESOURCE_BUDGET_PLAN_INVALID")
        total = ResourceVector(0, 0, 0, 0)
        for estimate in self.selected:
            require(estimate.admission_ready, "RESOURCE_BUDGET_PLAN_INVALID")
            total = total.add(estimate.conservative_requirements)
        require(total == self.estimated_use and total.fits_within(self.budget.allocatable)
                and self.remaining == self.budget.allocatable.subtract(total)
                and (not self.selected or self.expected_budget_generation == self.budget.generation),
                "RESOURCE_BUDGET_PLAN_CONSERVATION_FAILED")


def plan_budget_concurrency(estimates: tuple[WorkloadEstimate, ...], budget: BudgetEnvelope, *,
                            expected_budget_generation: int, facts: tuple[WorkloadPlanningFacts, ...],
                            expected_owner_generation: int, previous_clock: ClockSample,
                            current_clock: ClockSample, maximum_profile_age_ns: int = 300_000_000_000,
                            minimum_confidence_milli: int = 1) -> BudgetConcurrentWorkloadPlan:
    """Deterministic fair proposal from pinned owner facts and current measured profiles.

    Oldest eligible workload precedes newer work. Equal queue times use priority,
    deadline then exact identity. A capacity-blocked eligible head defers the tail
    rather than continually letting smaller newcomers bypass it. Cancelled,
    unready, stale or conflicting entries get explicit decisions. Actual queue
    mutation, admission, fairness aging and launch stay with canonical owners.
    """
    require(type(estimates) is tuple and len(estimates) <= MAXIMUM_PLANNING_WORKLOADS
            and all(type(item) is WorkloadEstimate for item in estimates)
            and type(budget) is BudgetEnvelope
            and type(expected_budget_generation) is int and 0 <= expected_budget_generation <= 2**63 - 1
            and type(facts) is tuple and len(facts) == len(estimates)
            and all(type(item) is WorkloadPlanningFacts for item in facts)
            and type(expected_owner_generation) is int and 0 <= expected_owner_generation <= 2**63 - 1
            and type(previous_clock) is ClockSample and type(current_clock) is ClockSample
            and type(maximum_profile_age_ns) is int and 1 <= maximum_profile_age_ns <= 300_000_000_000
            and type(minimum_confidence_milli) is int and 1 <= minimum_confidence_milli <= 1000,
            "RESOURCE_BUDGET_PLAN_INPUT_INVALID")
    require(len({item.workload_id for item in estimates}) == len(estimates), "RESOURCE_PLAN_DUPLICATE_WORKLOAD")
    require(len({item.workload_id for item in facts}) == len(facts)
            and {item.workload_id for item in facts} == {item.workload_id for item in estimates},
            "RESOURCE_PLAN_FACT_MEMBERSHIP_INVALID")
    zero = ResourceVector(0, 0, 0, 0)
    def blocked(state: str, code: str) -> BudgetConcurrentWorkloadPlan:
        decisions = tuple(WorkloadPlanningDecision(item.workload_id, state, (code,)) for item in estimates)
        return BudgetConcurrentWorkloadPlan(budget, expected_budget_generation, expected_owner_generation,
                                            (), zero, budget.allocatable, decisions)
    if budget.generation != expected_budget_generation:
        return blocked("STALE", "BUDGET_GENERATION_STALE")
    if any(item.owner_generation != expected_owner_generation for item in facts):
        return blocked("STALE", "PLANNING_OWNER_GENERATION_STALE")
    try:
        require_clock_progress(previous_clock, current_clock)
    except ContractError as error:
        return blocked("STALE", error.code)
    by_id = {item.workload_id: item for item in estimates}
    ordered = sorted(facts, key=lambda item: (item.queued_monotonic_ns, -item.priority,
                     item.deadline.expires_monotonic_ns if item.deadline is not None else 2**63 - 1,
                     item.workload_id))
    selected, decisions, used, file_keys = [], [], zero, set()
    capacity_head_blocked = False
    for item in ordered:
        estimate = by_id[item.workload_id]
        state, reasons = "PROPOSED", ()
        if item.cancelled:
            state, reasons = "CANCELLED", ("WORKLOAD_CANCELLED",)
        elif item.queued_monotonic_ns > current_clock.monotonic_ns:
            state, reasons = "STALE", ("PLANNING_QUEUE_TIME_IN_FUTURE",)
        elif not estimate.admission_ready:
            state, reasons = "UNRESOLVED", ("WORKLOAD_ESTIMATE_UNRESOLVED",)
        elif item.profile_snapshot_commitment != estimate.profile_snapshot_commitment:
            state, reasons = "STALE", ("PLANNING_PROFILE_SNAPSHOT_MISMATCH",)
        elif item.authority_ready is not True:
            state, reasons = "BLOCKED", ("OWNER_AUTHORITY_NOT_READY" if item.authority_ready is False
                                        else "AWAITING_OWNER_AUTHORITY_READINESS_INPUT",)
        elif item.shared_file_keys is None:
            state, reasons = "BLOCKED", ("AWAITING_OWNER_SHARED_FILE_CONFLICT_INPUT",)
        elif (current_clock.monotonic_ns < estimate.observed_monotonic_ns
              or current_clock.monotonic_ns - estimate.observed_monotonic_ns > maximum_profile_age_ns):
            state, reasons = "STALE", ("WORKLOAD_PROFILE_STALE",)
        elif estimate.confidence_milli < minimum_confidence_milli:
            state, reasons = "UNRESOLVED", ("WORKLOAD_PROFILE_CONFIDENCE_INSUFFICIENT",)
        else:
            try:
                requirements = estimate.conservative_requirements
            except ContractError as error:
                if error.code != "RESOURCE_ESTIMATE_BOUND_EXCEEDED":
                    raise
                state, reasons = "UNRESOLVED", ("WORKLOAD_ESTIMATE_BOUND_EXCEEDED",)
            if not reasons and item.deadline is not None:
                check = ExecutionTimeBudgetController().assess_deadline(budget, requirements.wall_time_ms,
                        deadline=item.deadline, previous_clock=previous_clock, current_clock=current_clock)
                if not check.accepted:
                    state, reasons = "BLOCKED", check.reason_codes
            if not reasons and file_keys.intersection(item.shared_file_keys):
                state, reasons = "DEFERRED", ("SHARED_FILE_CONFLICT",)
            if not reasons and capacity_head_blocked:
                state, reasons = "DEFERRED", ("OLDER_WORKLOAD_AWAITS_CAPACITY",)
            if not reasons and not requirements.fits_within(budget.allocatable.subtract(used)):
                state, reasons = "DEFERRED", ("WORKLOAD_CAPACITY_EXHAUSTED",)
                capacity_head_blocked = True
            if not reasons:
                selected.append(estimate)
                used = used.add(requirements)
                file_keys.update(item.shared_file_keys)
        decisions.append(WorkloadPlanningDecision(item.workload_id, state, reasons))
    projection = project_workload_budget(budget, used, expected_generation=expected_budget_generation)
    require(projection.accepted, "RESOURCE_BUDGET_PLAN_CONSERVATION_FAILED")
    return BudgetConcurrentWorkloadPlan(budget, expected_budget_generation, expected_owner_generation,
                                       tuple(selected), used, projection.remaining, tuple(decisions))
