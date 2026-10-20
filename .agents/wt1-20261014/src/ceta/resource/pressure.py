"""Explicit pressure classification with recovery hysteresis."""
from dataclasses import dataclass
import math
import threading
import time

from ceta.contracts.wire import ContractError
from ceta.contracts.resource_management import (CapacitySnapshot, ObservationState, PressureLevel,
    QuantityObservation, ResourceKind, digest, identifier, require)
from ceta.contracts.workload_throttling import (CpuRateChange, WorkloadThrottleIntent,
    WorkloadThrottleResult, bounded_time)


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
    """Pure recommendations and explicitly composed retained execution.

    No default owner grants admission. The canonical execution owner must
    durably admit and fence the exact intent, evidence and original context.
    Native enforcement remains on the existing owned-process interface.
    """
    def __init__(self, execution_owner=None, *, clock=time.monotonic_ns,
                 maximum_decision_duration_ns=100_000_000, clock_resolution_ns=None):
        require(callable(clock) and type(maximum_decision_duration_ns) is int
                and 1 <= maximum_decision_duration_ns <= 1_000_000_000, "THROTTLE_CONTROLLER_BOUNDS_INVALID")
        if clock_resolution_ns is None:
            clock_resolution_ns = math.ceil(time.get_clock_info('monotonic').resolution * 1_000_000_000) if clock is time.monotonic_ns else 0
        require(type(clock_resolution_ns) is int and 0 <= clock_resolution_ns <= 1_000_000_000,
                "THROTTLE_CLOCK_RESOLUTION_INVALID")
        self._execution_owner, self._clock = execution_owner, clock
        self._decision_limit, self._clock_margin = maximum_decision_duration_ns, clock_resolution_ns
        self._throttle_lock = threading.RLock()
        self._stop_event = threading.Event()
        self._clock_highwater, self._clock_invalid, self._stopping = 0, False, False
        self._pressure = ResourcePressureDetector(clock=clock, maximum_observation_age_ns=60_000_000_000)

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

    def stop(self) -> None:
        """Close this controller's new admission; native work stays owner-held."""
        self._stop_event.set()

    def _throttle_now(self):
        now = self._clock()
        bounded_time(now, 'THROTTLE_CLOCK_INVALID')
        if now < self._clock_highwater:
            self._clock_invalid = True
        self._clock_highwater = max(now, self._clock_highwater)
        require(not self._clock_invalid, 'THROTTLE_CLOCK_ROLLBACK')
        return now

    @staticmethod
    def _throttle_result(intent, state, reason, change=None):
        return WorkloadThrottleResult(intent.operation_id, intent.input_commitment, state, (reason,), change)

    def _plan_at(self, intent, now, cancelled):
        if cancelled or self._stopping or self._stop_event.is_set():
            return self._throttle_result(intent, 'CANCELLED', 'THROTTLE_CANCELLED')
        if now + self._clock_margin >= intent.deadline_monotonic_ns:
            return self._throttle_result(intent, 'STALE', 'THROTTLE_DEADLINE_EXPIRED')
        if not all((intent.preserves_verification, intent.preserves_evidence,
                    intent.preserves_stop, intent.preserves_recovery)):
            return self._throttle_result(intent, 'BLOCKED', 'THROTTLE_REQUIRED_GUARDRAIL_WEAKENED')
        lease, budget = intent.lease, intent.budget
        if lease.state != 'HELD' or budget.generation < lease.allocated_generation:
            return self._throttle_result(intent, 'STALE', 'THROTTLE_RESOURCE_LEASE_STALE')
        if not intent.required_control_reserve.fits_within(budget.control_reserve):
            return self._throttle_result(intent, 'BLOCKED', 'THROTTLE_CONTROL_RESERVE_UNAVAILABLE')
        if not lease.request.requirements.fits_within(budget.reserved_use):
            return self._throttle_result(intent, 'STALE', 'THROTTLE_RESERVATION_UNACCOUNTED')
        limit = intent.expected_limit
        if limit.state is not ObservationState.MEASURED or not 0 <= now - limit.observed_monotonic_ns:
            return self._throttle_result(intent, 'STALE', 'THROTTLE_LIMIT_UNAVAILABLE_OR_FUTURE')
        if now - limit.observed_monotonic_ns + self._clock_margin > intent.maximum_age_ns:
            return self._throttle_result(intent, 'STALE', 'THROTTLE_LIMIT_STALE')
        snapshot = intent.pressure
        observations = (snapshot.total, snapshot.free, snapshot.reservable, snapshot.utilization_milli)
        if (snapshot.kind is not ResourceKind.CPU or any(not item.measured for item in observations)
                or len({item.observed_monotonic_ns for item in observations}) != 1
                or not snapshot.is_recent(now + self._clock_margin, intent.maximum_age_ns)):
            return self._throttle_result(intent, 'STALE', 'THROTTLE_PRESSURE_UNAVAILABLE_OR_STALE')
        decision = self._pressure.observe(snapshot, current=True)
        if decision.level is PressureLevel.UNKNOWN:
            return self._throttle_result(intent, 'STALE', 'THROTTLE_PRESSURE_STREAM_INVALID')
        if intent.restoration_of is not None:
            return self._throttle_result(intent, 'PLANNED', 'THROTTLE_DISTINCT_RESTORATION_REQUIRES_ADMISSION')
        if decision.level not in (PressureLevel.ELEVATED, PressureLevel.CRITICAL):
            return self._throttle_result(intent, 'NO_CHANGE', 'THROTTLE_PRESSURE_NOT_ACTIONABLE')
        ceiling = 10000 if limit.limit.control_flags == 0 else limit.limit.hard_cap_rate
        if intent.proposed_limit.control_flags not in (5, 13) or ceiling is None:
            return self._throttle_result(intent, 'BLOCKED', 'THROTTLE_NATIVE_POLICY_UNSUPPORTED')
        if intent.proposed_limit.control_flags & 8 != limit.limit.control_flags & 8:
            return self._throttle_result(intent, 'BLOCKED', 'THROTTLE_NOTIFICATION_PRESERVATION_REQUIRED')
        if intent.proposed_limit.value >= ceiling:
            return self._throttle_result(intent, 'NO_CHANGE', 'THROTTLE_NO_EFFECTIVE_REDUCTION')
        return self._throttle_result(intent, 'PLANNED', 'THROTTLE_EXACT_REDUCTION_REQUIRES_ADMISSION')

    def plan(self, intent: WorkloadThrottleIntent, *, cancelled=False) -> WorkloadThrottleResult:
        require(type(intent) is WorkloadThrottleIntent and type(cancelled) is bool, 'THROTTLE_INTENT_REQUIRED')
        intent.__post_init__()
        with self._throttle_lock:
            started = time.perf_counter_ns()
            try:
                result = self._plan_at(intent, self._throttle_now(), cancelled)
                now = self._throttle_now()
                if time.perf_counter_ns() - started > self._decision_limit:
                    return self._throttle_result(intent, 'STALE', 'THROTTLE_DECISION_TOO_SLOW')
                if now + self._clock_margin >= intent.deadline_monotonic_ns:
                    return self._throttle_result(intent, 'STALE', 'THROTTLE_DEADLINE_EXPIRED')
                return result
            except (OSError, ContractError) as failure:
                if type(failure) is not ContractError or failure.code.startswith('THROTTLE_CLOCK'):
                    self._clock_invalid = True
                return self._throttle_result(intent, 'BLOCKED', failure.code if type(failure) is ContractError else 'THROTTLE_CLOCK_UNAVAILABLE')
            except BaseException:
                self._stopping = True
                raise

    def _retained_call(self, callback, *args):
        require(callable(callback), 'THROTTLE_OWNER_METHOD_UNAVAILABLE')
        started = time.perf_counter_ns()
        result = callback(*args)
        require(result is None, 'THROTTLE_OWNER_DECISION_MALFORMED')
        require(time.perf_counter_ns() - started <= self._decision_limit, 'THROTTLE_OWNER_CHECK_TOO_SLOW')

    def _execution_time_fence(self, intent, started):
        now = self._throttle_now()
        elapsed = time.perf_counter_ns() - started[1]
        require(0 <= elapsed <= self._decision_limit, 'THROTTLE_EXECUTION_WINDOW_EXCEEDED')
        require(max(now, started[0] + elapsed) + self._clock_margin < intent.deadline_monotonic_ns,
                'THROTTLE_EXECUTION_DEADLINE_EXPIRED')

    def execute(self, intent: WorkloadThrottleIntent, owned_process: object, original_context: object,
                *, cancelled=False) -> WorkloadThrottleResult:
        """Perform one exact effect only inside a retained canonical admission.

        Controlled owners qualify interface behavior only. This module creates
        no durable intent, authenticated context, permission or evidence store.
        """
        with self._throttle_lock:
            plan = self.plan(intent, cancelled=cancelled)
            if plan.state != 'PLANNED':
                return plan
            admit = getattr(self._execution_owner, 'admit_throttle', None)
            if not callable(admit):
                return self._throttle_result(intent, 'BLOCKED', 'THROTTLE_EXECUTION_OWNER_UNAVAILABLE')
            manager, retained, entered, change, primary = None, None, False, None, None
            attempted = False
            result = None
            commitment = intent.input_commitment
            execution_started = (self._clock_highwater, time.perf_counter_ns())
            try:
                started = time.perf_counter_ns()
                manager = admit(original_context, intent, owned_process)
                require(callable(getattr(manager, '__enter__', None)) and callable(getattr(manager, '__exit__', None)),
                        'THROTTLE_RETAINED_ADMISSION_REQUIRED')
                retained = manager.__enter__(); entered = True
                require(time.perf_counter_ns() - started <= self._decision_limit, 'THROTTLE_ADMISSION_TOO_SLOW')
                require(getattr(retained, 'operation_id', None) == intent.operation_id
                        and getattr(retained, 'input_commitment', None) == intent.input_commitment,
                        'THROTTLE_ADMISSION_BINDING_MISMATCH')
                identifier(getattr(retained, 'intent_ref', None), 'THROTTLE_DURABLE_INTENT_REQUIRED')
                identifier(getattr(retained, 'evidence_ref', None), 'THROTTLE_EVIDENCE_CAPACITY_REQUIRED')
                require(callable(getattr(retained, 'record_outcome', None)), 'THROTTLE_EVIDENCE_WRITER_UNAVAILABLE')
                self._retained_call(getattr(retained, 'require_current', None), intent, owned_process)
                require(intent.input_commitment == commitment, 'THROTTLE_INPUT_CHANGED')
                fresh = self.plan(intent, cancelled=cancelled)
                require(fresh.state == 'PLANNED', 'THROTTLE_PRE_EFFECT_INPUT_STALE')
                self._execution_time_fence(intent, execution_started)
                if intent.restoration_of is None:
                    apply = getattr(owned_process, 'apply_cpu_rate_limit', None)
                    require(callable(apply), 'THROTTLE_NATIVE_OWNER_UNAVAILABLE')
                    attempted = True
                    change = apply(intent.operation_id, intent.process_identity, intent.expected_limit, intent.proposed_limit,
                        deadline_monotonic_ns=intent.deadline_monotonic_ns, maximum_age_ns=intent.maximum_age_ns,
                        maximum_duration_ns=self._decision_limit)
                else:
                    restore = getattr(owned_process, 'restore_cpu_rate_limit', None)
                    require(callable(restore), 'THROTTLE_NATIVE_OWNER_UNAVAILABLE')
                    attempted = True
                    change = restore(intent.operation_id, intent.restoration_of, intent.process_identity, intent.expected_limit, intent.proposed_limit,
                        deadline_monotonic_ns=intent.deadline_monotonic_ns, maximum_age_ns=intent.maximum_age_ns,
                        maximum_duration_ns=self._decision_limit)
                require(type(change) is CpuRateChange, 'THROTTLE_NATIVE_RESULT_MALFORMED'); change.__post_init__()
                require(change.identity == intent.process_identity and change.job_digest == intent.expected_limit.job_digest
                        and (change.operation_id == intent.operation_id if intent.restoration_of is None else
                             change.operation_id == intent.restoration_of and change.restoration_id == intent.operation_id)
                        and (change.intended == intent.proposed_limit if intent.restoration_of is None else
                             change.before == intent.proposed_limit), 'THROTTLE_NATIVE_RESULT_BINDING_MISMATCH')
                self._retained_call(retained.require_current, intent, owned_process)
                require(intent.input_commitment == commitment, 'THROTTLE_INPUT_CHANGED')
                self._retained_call(retained.record_outcome, intent, change)
                require(intent.input_commitment == commitment, 'THROTTLE_INPUT_CHANGED')
                self._execution_time_fence(intent, execution_started)
                now = self._throttle_now()
                require(now + self._clock_margin < intent.deadline_monotonic_ns, 'THROTTLE_POST_EFFECT_DEADLINE_EXPIRED')
                expected_state = 'RESTORED' if intent.restoration_of is not None else 'APPLIED'
                state = expected_state if change.state == expected_state else 'UNCERTAIN'
                result = self._throttle_result(intent, state, 'THROTTLE_EFFECT_RECORDED' if state != 'UNCERTAIN' else
                                               'THROTTLE_EFFECT_REQUIRES_RECONCILIATION', change)
            except (OSError, ContractError) as failure:
                primary = failure  # Let retained owner exit reconcile this exact denial/uncertainty.
                result = self._throttle_result(intent, 'UNCERTAIN' if attempted else 'BLOCKED',
                    failure.code if type(failure) is ContractError else 'THROTTLE_OWNER_UNAVAILABLE',
                    change if type(change) is CpuRateChange else None)
            except BaseException as failure:
                primary = failure; self._stopping = True
                raise
            finally:
                if entered:
                    try:
                        suppressed = manager.__exit__(type(primary) if primary else None, primary,
                                                      primary.__traceback__ if primary else None)
                        require(suppressed is None or suppressed is False, 'THROTTLE_EXCEPTION_SUPPRESSION_DENIED')
                    except BaseException as secondary:
                        if primary is not None:
                            try: primary.add_note('Retained throttle owner exit failed: ' + type(secondary).__name__)
                            except BaseException: pass
                        else:
                            result = self._throttle_result(intent, 'UNCERTAIN' if attempted else 'BLOCKED',
                                'THROTTLE_RETAINED_OWNER_EXIT_UNAVAILABLE', change if type(change) is CpuRateChange else None)
            if result.state in ('APPLIED', 'RESTORED'):
                try:
                    self._execution_time_fence(intent, execution_started)
                except (OSError, ContractError):
                    result = self._throttle_result(intent, 'UNCERTAIN', 'THROTTLE_RETURN_WINDOW_EXCEEDED', change)
            return result


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
        require(type(thresholds) is PressureThresholds, "RESOURCE_PRESSURE_THRESHOLDS_INVALID")
        thresholds.__post_init__()
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
        # Keep the shared schema owner's validation; nominal type alone cannot
        # qualify a reconstructed or corrupted nested record before clock work.
        observations = tuple(getattr(snapshot, name, None) for name in ("total", "free", "reservable", "utilization_milli"))
        require(all(type(item) is QuantityObservation for item in observations), "RESOURCE_CAPACITY_OBSERVATION_REQUIRED")
        for observation in observations:
            observation.__post_init__()
        snapshot.__post_init__()
        value = snapshot.utilization_milli.value if snapshot.utilization_milli.measured else None
        with self._lock:
            try:
                now_ns = self._clock()
                require(type(now_ns) is int and 0 <= now_ns <= 2**63 - 1, "RESOURCE_PRESSURE_CLOCK_INVALID")
            except BaseException:
                # Invalid or interrupted time cannot preserve a prior allow.
                # Retain stream/sequence/clock bounds and the primary exception.
                self._close(value, "OBSERVATION_CLOCK_UNAVAILABLE")
                raise
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
                if self._level is PressureLevel.CRITICAL:
                    self._stable = 0
                    return PressureDecision(self._level, False, value, self._thresholds.recovery_samples, "CRITICAL_HYSTERESIS")
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

