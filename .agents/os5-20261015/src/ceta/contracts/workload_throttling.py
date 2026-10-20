"""Exact workload throttle data and captured execution-owner ports.

These records describe effects; constructing them never grants admission.
The execution owner must retain current authority and durable evidence through
native observation. Native job ownership supplies containment, not authority.
"""
from dataclasses import dataclass
from typing import ContextManager, Protocol

from .resource_management import (BudgetEnvelope, CapacitySnapshot, ObservationState,
    ProcessResourceIdentity, QuantityObservation, ResourceVector, digest, identifier, require)
from .resource_reservations import ResourceLease, vector_value
from .wire import canonical_bytes


def bounded_time(value: int, code: str) -> None:
    require(type(value) is int and 0 <= value <= 2**63 - 1, code)


@dataclass(frozen=True, slots=True)
class CpuRateLimit:
    """Exact Windows CPU policy DWORDs, including the original union bits."""
    control_flags: int
    value: int

    def __post_init__(self) -> None:
        flags, value = self.control_flags, self.value
        require(type(flags) is int and type(value) is int and 0 <= flags <= 31
                and 0 <= value <= 0xFFFFFFFF, "CPU_RATE_LIMIT_INVALID")
        if flags == 0:
            return  # Disabled union bits are retained exactly, never treated as a cap.
        require(flags & 1 and not (flags & 2 and flags & (4 | 16))
                and not (flags & 4 and flags & 16), "CPU_RATE_FLAGS_UNSUPPORTED")
        if flags & 2:
            require(1 <= value <= 9, "CPU_RATE_WEIGHT_INVALID")
        elif flags & 16:
            minimum, maximum = value & 0xFFFF, value >> 16
            require(0 <= minimum <= maximum <= 10000 and maximum > 0, "CPU_RATE_RANGE_INVALID")
        else:
            require(1 <= value <= 10000, "CPU_RATE_VALUE_INVALID")

    @classmethod
    def hard_cap(cls, cycles_per_10000: int) -> "CpuRateLimit":
        return cls(5, cycles_per_10000)

    @property
    def hard_cap_rate(self) -> int | None:
        return self.value if self.control_flags in (5, 13) else None


@dataclass(frozen=True, slots=True)
class CpuRateObservation:
    identity: ProcessResourceIdentity
    job_digest: str
    state: ObservationState
    limit: CpuRateLimit | None
    version: int
    observed_monotonic_ns: int
    reason: str | None = None

    def __post_init__(self) -> None:
        require(type(self.identity) is ProcessResourceIdentity, "CPU_RATE_IDENTITY_REQUIRED")
        self.identity.__post_init__(); digest(self.job_digest, "CPU_RATE_JOB_REQUIRED")
        bounded_time(self.version, "CPU_RATE_VERSION_INVALID")
        bounded_time(self.observed_monotonic_ns, "CPU_RATE_TIME_INVALID")
        require(type(self.state) is ObservationState, "CPU_RATE_OBSERVATION_STATE_INVALID")
        if self.state is ObservationState.MEASURED:
            require(type(self.limit) is CpuRateLimit and self.reason is None, "CPU_RATE_OBSERVATION_INVALID")
            self.limit.__post_init__()
        else:
            require(self.limit is None, "CPU_RATE_UNAVAILABLE_HAS_VALUE")
            identifier(self.reason, "CPU_RATE_UNAVAILABLE_REASON_REQUIRED")


@dataclass(frozen=True, slots=True)
class CpuRateChange:
    operation_id: str
    identity: ProcessResourceIdentity
    job_digest: str
    before: CpuRateLimit
    intended: CpuRateLimit
    observed: CpuRateObservation | None
    state: str
    reason: str
    restoration_id: str | None = None

    def __post_init__(self) -> None:
        identifier(self.operation_id, "CPU_RATE_OPERATION_REQUIRED")
        require(type(self.identity) is ProcessResourceIdentity, "CPU_RATE_IDENTITY_REQUIRED")
        self.identity.__post_init__(); digest(self.job_digest, "CPU_RATE_JOB_REQUIRED")
        require(type(self.before) is CpuRateLimit and type(self.intended) is CpuRateLimit,
                "CPU_RATE_CHANGE_LIMIT_REQUIRED")
        self.before.__post_init__(); self.intended.__post_init__()
        require(type(self.state) is str and self.state in {
            "APPLIED", "NOT_APPLIED", "UNCERTAIN", "CONFLICT", "RESTORED"}, "CPU_RATE_CHANGE_STATE_INVALID")
        identifier(self.reason, "CPU_RATE_CHANGE_REASON_REQUIRED")
        if self.restoration_id is not None:
            identifier(self.restoration_id, "CPU_RATE_RESTORATION_REQUIRED")
        if self.observed is not None:
            require(type(self.observed) is CpuRateObservation, "CPU_RATE_OBSERVATION_REQUIRED")
            self.observed.__post_init__()
            require(self.observed.identity == self.identity and self.observed.job_digest == self.job_digest,
                    "CPU_RATE_CHANGE_BINDING_MISMATCH")
        if self.state in ('APPLIED', 'RESTORED', 'NOT_APPLIED'):
            require(self.observed is not None and self.observed.state is ObservationState.MEASURED
                    and self.observed.limit == (self.intended if self.state == 'APPLIED' else self.before),
                    "CPU_RATE_CHANGE_OBSERVATION_MISMATCH")


@dataclass(frozen=True, slots=True)
class WorkloadThrottleIntent:
    operation_id: str
    proposal_digest: str
    task_revision: str
    lease: ResourceLease
    budget: BudgetEnvelope
    process_identity: ProcessResourceIdentity
    expected_limit: CpuRateObservation
    proposed_limit: CpuRateLimit
    pressure: CapacitySnapshot
    required_control_reserve: ResourceVector
    deadline_monotonic_ns: int
    maximum_age_ns: int = 1_000_000_000
    preserves_verification: bool = True
    preserves_evidence: bool = True
    preserves_stop: bool = True
    preserves_recovery: bool = True
    restoration_of: str | None = None

    def __post_init__(self) -> None:
        identifier(self.operation_id, "THROTTLE_OPERATION_REQUIRED")
        digest(self.proposal_digest, "THROTTLE_PROPOSAL_DIGEST_REQUIRED")
        digest(self.task_revision, "THROTTLE_TASK_REVISION_REQUIRED")
        for value, cls, code in ((self.lease, ResourceLease, "THROTTLE_LEASE_REQUIRED"),
                (self.budget, BudgetEnvelope, "THROTTLE_BUDGET_REQUIRED"),
                (self.process_identity, ProcessResourceIdentity, "THROTTLE_PROCESS_REQUIRED"),
                (self.expected_limit, CpuRateObservation, "THROTTLE_LIMIT_OBSERVATION_REQUIRED"),
                (self.proposed_limit, CpuRateLimit, "THROTTLE_LIMIT_REQUIRED"),
                (self.pressure, CapacitySnapshot, "THROTTLE_PRESSURE_REQUIRED"),
                (self.required_control_reserve, ResourceVector, "THROTTLE_CONTROL_RESERVE_REQUIRED")):
            require(type(value) is cls, code); value.__post_init__()
        for value in (self.budget.limit, self.budget.control_reserve,
                      self.budget.measured_use, self.budget.reserved_use):
            value.__post_init__()
        for value in (self.pressure.total, self.pressure.free, self.pressure.reservable,
                      self.pressure.utilization_milli):
            require(type(value) is QuantityObservation, "THROTTLE_PRESSURE_REQUIRED")
            value.__post_init__()
        require(self.expected_limit.identity == self.process_identity, "THROTTLE_PROCESS_BINDING_MISMATCH")
        require(self.budget.budget_id == self.lease.request.budget_id, "THROTTLE_BUDGET_BINDING_MISMATCH")
        bounded_time(self.deadline_monotonic_ns, "THROTTLE_DEADLINE_INVALID")
        require(type(self.maximum_age_ns) is int and 1 <= self.maximum_age_ns <= 60_000_000_000,
                "THROTTLE_MAXIMUM_AGE_INVALID")
        require(all(type(value) is bool for value in (self.preserves_verification,
                self.preserves_evidence, self.preserves_stop, self.preserves_recovery)),
                "THROTTLE_SAFEGUARD_INVALID")
        if self.restoration_of is not None:
            identifier(self.restoration_of, "THROTTLE_RESTORATION_REQUIRED")
            require(self.operation_id != self.restoration_of, "THROTTLE_RESTORATION_ID_REUSED")

    @property
    def input_commitment(self) -> str:
        """Canonical complete data binding, with no currentness or truth claim."""
        self.__post_init__()
        def observation(item):
            return {name: (value.value if type(value) is ObservationState else value)
                    for name in item.__dataclass_fields__ for value in (getattr(item, name),)}
        budget = {name: (vector_value(value) if type(value) is ResourceVector else value)
                  for name in self.budget.__dataclass_fields__ for value in (getattr(self.budget, name),)}
        limit = self.expected_limit
        wire = canonical_bytes({'profile': 'ceta-workload-throttle-v1',
            'operation_id': self.operation_id, 'proposal_digest': self.proposal_digest,
            'task_revision': self.task_revision, 'lease_wire': self.lease.canonical_wire.decode('utf8'),
            'budget': budget, 'process_identity': {name: getattr(self.process_identity, name)
                for name in self.process_identity.__dataclass_fields__},
            'job_digest': limit.job_digest, 'limit_state': limit.state.value, 'limit_version': limit.version,
            'limit_time': limit.observed_monotonic_ns, 'limit_reason': limit.reason,
            'before_limit': None if limit.limit is None else {'flags': limit.limit.control_flags, 'value': limit.limit.value},
            'proposed_limit': {'flags': self.proposed_limit.control_flags, 'value': self.proposed_limit.value},
            'pressure': {'kind': self.pressure.kind.value, 'sequence': self.pressure.sequence,
                **{name: observation(getattr(self.pressure, name)) for name in
                   ('total', 'free', 'reservable', 'utilization_milli')}},
            'control_reserve': vector_value(self.required_control_reserve),
            'deadline': self.deadline_monotonic_ns, 'maximum_age': self.maximum_age_ns,
            'safeguards': [self.preserves_verification, self.preserves_evidence, self.preserves_stop, self.preserves_recovery],
            'restoration_of': self.restoration_of})
        from hashlib import sha256
        return 'sha256:' + sha256(wire).hexdigest()


@dataclass(frozen=True, slots=True)
class WorkloadThrottleResult:
    operation_id: str
    input_commitment: str
    state: str
    reason_codes: tuple[str, ...]
    change: CpuRateChange | None = None

    def __post_init__(self) -> None:
        identifier(self.operation_id, "THROTTLE_OPERATION_REQUIRED"); digest(self.input_commitment, "THROTTLE_INPUT_REQUIRED")
        require(type(self.state) is str and self.state in {
            'PLANNED', 'NO_CHANGE', 'BLOCKED', 'STALE', 'CANCELLED', 'APPLIED', 'RESTORED', 'UNCERTAIN'},
            "THROTTLE_RESULT_STATE_INVALID")
        require(type(self.reason_codes) is tuple and 1 <= len(self.reason_codes) <= 8, "THROTTLE_REASONS_REQUIRED")
        for reason in self.reason_codes: identifier(reason, "THROTTLE_REASON_INVALID")
        if self.change is not None:
            require(type(self.change) is CpuRateChange, "CPU_RATE_CHANGE_REQUIRED"); self.change.__post_init__()


class RetainedThrottleExecution(Protocol):
    """Canonical owner-created lease; DTOs and fixture callbacks are not issuers.

    The owner retains authenticated context, cancellation/revocation, resource
    and evidence capacity, and durable single-use intent through observation.
    Missing evidence prevents entry. Current checks return exactly None or a
    typed denial, never a permissive Boolean. Outcome recording is durable.
    Restoration requires a separately admitted exact operation.
    """
    operation_id: str
    input_commitment: str
    intent_ref: str
    evidence_ref: str
    def require_current(self, intent: WorkloadThrottleIntent, owned_process: object) -> None: ...
    def record_outcome(self, intent: WorkloadThrottleIntent, change: CpuRateChange) -> None: ...


class ThrottleExecutionOwner(Protocol):
    """Supplied by canonical execution composition; no implementation here.

    Context entry durably admits the exact operation at most once, retaining
    current protected prerequisites through native apply/observation and exit.
    It uses the original opaque context and exact owned lifetime/job. It must
    never suppress primary control exceptions or revive an earlier admission.
    CMP02 currently denies runtime admission, so production wiring is pending.
    """
    def admit_throttle(self, original_context: object, intent: WorkloadThrottleIntent,
                       owned_process: object) -> ContextManager[RetainedThrottleExecution]: ...
