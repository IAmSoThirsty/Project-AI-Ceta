"""Pure projections for the three resource-budgeting controllers.

These assess a pinned ``BudgetEnvelope`` only.  Canonical reservation, charge,
release and lease fencing remain operations of the injected state owner.
"""
from dataclasses import dataclass

from ceta.contracts.resource_management import BudgetEnvelope, ResourceVector, identifier, require
from ceta.contracts.temporal import ClockSample, Deadline, require_deadline_current
from ceta.contracts.wire import ContractError


@dataclass(frozen=True, slots=True)
class BudgetCheck:
    accepted: bool
    reason_codes: tuple[str, ...]
    available: int
    requested: int
    budget_generation: int


@dataclass(frozen=True, slots=True)
class ChildBudgetRequest:
    """A pure child-envelope proposal; canonical allocation remains external."""
    child_budget_id: str
    parent: BudgetEnvelope
    expected_parent_generation: int
    limit: ResourceVector
    control_reserve: ResourceVector
    measured_use: ResourceVector
    reserved_use: ResourceVector

    def __post_init__(self) -> None:
        identifier(self.child_budget_id, "RESOURCE_CHILD_BUDGET_IDENTIFIER_INVALID")
        require(type(self.parent) is BudgetEnvelope and type(self.expected_parent_generation) is int
                and self.expected_parent_generation >= 0
                and all(type(value) is ResourceVector for value in
                        (self.limit, self.control_reserve, self.measured_use, self.reserved_use)),
                "RESOURCE_CHILD_BUDGET_INPUT_INVALID")
        # Reuse the canonical envelope conservation rule for the proposed child.
        BudgetEnvelope(self.child_budget_id, self.limit, self.control_reserve,
                       self.measured_use, self.reserved_use, self.expected_parent_generation)


@dataclass(frozen=True, slots=True)
class ChildBudgetAssessment:
    accepted: bool
    child_budget: BudgetEnvelope | None
    parent_budget_id: str
    expected_parent_generation: int
    observed_parent_generation: int
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DeadlineBudgetCheck:
    accepted: bool
    reason_codes: tuple[str, ...]
    available: int
    requested: int
    budget_generation: int
    remaining_deadline_ms: int | None


@dataclass(frozen=True, slots=True)
class WorkloadBudgetProjection:
    """Immutable capacity proposal, preserving distinct canonical quantities."""
    accepted: bool
    reason_codes: tuple[str, ...]
    budget_id: str
    expected_generation: int
    observed_generation: int
    limit: ResourceVector
    control_reserve: ResourceVector
    measured_use: ResourceVector
    reserved_use: ResourceVector
    estimated_use: ResourceVector
    remaining: ResourceVector | None

    def __post_init__(self) -> None:
        identifier(self.budget_id, "RESOURCE_BUDGET_IDENTIFIER_INVALID")
        require(type(self.accepted) is bool and type(self.reason_codes) is tuple
                and len(self.reason_codes) <= 4
                and all(type(code) is str and 1 <= len(code) <= 96 for code in self.reason_codes)
                and type(self.expected_generation) is int and 0 <= self.expected_generation <= 2**63 - 1
                and type(self.observed_generation) is int and 0 <= self.observed_generation <= 2**63 - 1
                and all(type(item) is ResourceVector for item in
                        (self.limit, self.control_reserve, self.measured_use, self.reserved_use, self.estimated_use)),
                "RESOURCE_WORKLOAD_BUDGET_PROJECTION_INVALID")
        envelope = BudgetEnvelope(self.budget_id, self.limit, self.control_reserve,
                                  self.measured_use, self.reserved_use, self.observed_generation)
        if self.accepted:
            require(not self.reason_codes and self.expected_generation == self.observed_generation
                    and type(self.remaining) is ResourceVector
                    and self.estimated_use.fits_within(envelope.allocatable)
                    and self.remaining == envelope.allocatable.subtract(self.estimated_use),
                    "RESOURCE_WORKLOAD_BUDGET_PROJECTION_INVALID")
        else:
            require(bool(self.reason_codes) and self.remaining is None,
                    "RESOURCE_WORKLOAD_BUDGET_PROJECTION_INVALID")


def project_workload_budget(budget: BudgetEnvelope, estimated_use: ResourceVector, *,
                            expected_generation: int) -> WorkloadBudgetProjection:
    """Assess a proposal without charging estimates or modifying reservations."""
    require(type(budget) is BudgetEnvelope and type(estimated_use) is ResourceVector
            and type(expected_generation) is int and 0 <= expected_generation <= 2**63 - 1,
            "RESOURCE_WORKLOAD_BUDGET_INPUT_INVALID")
    remaining, reasons = None, ()
    if expected_generation != budget.generation:
        reasons = ("BUDGET_GENERATION_STALE",)
    elif not estimated_use.fits_within(budget.allocatable):
        fields = ("cpu_milli", "memory_bytes", "storage_bytes", "wall_time_ms")
        codes = ("COMPUTE_BUDGET_EXHAUSTED", "MEMORY_BUDGET_EXHAUSTED", "STORAGE_BUDGET_EXHAUSTED",
                 "EXECUTION_TIME_BUDGET_EXHAUSTED")
        reasons = tuple(code for field, code in zip(fields, codes)
                        if getattr(estimated_use, field) > getattr(budget.allocatable, field))
    else:
        remaining = budget.allocatable.subtract(estimated_use)
    return WorkloadBudgetProjection(not reasons, reasons, budget.budget_id, expected_generation,
                                    budget.generation, budget.limit, budget.control_reserve,
                                    budget.measured_use, budget.reserved_use, estimated_use, remaining)


def _check(budget: BudgetEnvelope, *, requested: int, available: int, code: str) -> BudgetCheck:
    require(type(budget) is BudgetEnvelope and type(requested) is int and requested >= 0
            and type(available) is int and available >= 0, "RESOURCE_BUDGET_INPUT_INVALID")
    return BudgetCheck(requested <= available, () if requested <= available else (code,), available,
                       requested, budget.generation)


def assess_child_budget(request: ChildBudgetRequest) -> ChildBudgetAssessment:
    """Check a child proposal against one pinned parent snapshot.

    This cannot allocate capacity: the owner must still atomically reserve the
    accepted proposal with the returned expected generation.
    """
    require(type(request) is ChildBudgetRequest, "RESOURCE_CHILD_BUDGET_REQUEST_REQUIRED")
    parent = request.parent
    if request.expected_parent_generation != parent.generation:
        return ChildBudgetAssessment(False, None, parent.budget_id, request.expected_parent_generation,
                                     parent.generation, ("PARENT_BUDGET_GENERATION_STALE",))
    if not request.limit.fits_within(parent.allocatable):
        return ChildBudgetAssessment(False, None, parent.budget_id, request.expected_parent_generation,
                                     parent.generation, ("CHILD_BUDGET_EXCEEDS_PARENT_REMAINING",))
    child = BudgetEnvelope(request.child_budget_id, request.limit, request.control_reserve,
                           request.measured_use, request.reserved_use, parent.generation)
    return ChildBudgetAssessment(True, child, parent.budget_id, request.expected_parent_generation,
                                 parent.generation, ())


class ComputeBudgetController:
    def assess(self, budget: BudgetEnvelope, requested_cpu_milli: int) -> BudgetCheck:
        return _check(budget, requested=requested_cpu_milli, available=budget.allocatable.cpu_milli,
                      code="COMPUTE_BUDGET_EXHAUSTED")

    def assess_child(self, request: ChildBudgetRequest) -> ChildBudgetAssessment:
        return assess_child_budget(request)


class MemoryBudgetController:
    def assess(self, budget: BudgetEnvelope, requested_memory_bytes: int) -> BudgetCheck:
        return _check(budget, requested=requested_memory_bytes, available=budget.allocatable.memory_bytes,
                      code="MEMORY_BUDGET_EXHAUSTED")

    def assess_child(self, request: ChildBudgetRequest) -> ChildBudgetAssessment:
        return assess_child_budget(request)


class ExecutionTimeBudgetController:
    def assess(self, budget: BudgetEnvelope, requested_wall_time_ms: int) -> BudgetCheck:
        return _check(budget, requested=requested_wall_time_ms, available=budget.allocatable.wall_time_ms,
                      code="EXECUTION_TIME_BUDGET_EXHAUSTED")

    def assess_deadline(self, budget: BudgetEnvelope, requested_wall_time_ms: int, *, deadline: Deadline,
                        previous_clock: ClockSample, current_clock: ClockSample) -> DeadlineBudgetCheck:
        """Assess one request against the canonical trusted monotonic deadline."""
        base = self.assess(budget, requested_wall_time_ms)
        require(type(deadline) is Deadline and type(previous_clock) is ClockSample
                and type(current_clock) is ClockSample, "RESOURCE_DEADLINE_INPUT_INVALID")
        try:
            require_deadline_current(deadline, previous_clock, current_clock)
        except ContractError as error:
            return DeadlineBudgetCheck(False, (error.code,), base.available, base.requested,
                                       budget.generation, None)
        remaining_ms = (deadline.expires_monotonic_ns - current_clock.monotonic_ns) // 1_000_000
        if not base.accepted:
            return DeadlineBudgetCheck(False, base.reason_codes, base.available, base.requested,
                                       budget.generation, remaining_ms)
        if requested_wall_time_ms > remaining_ms:
            return DeadlineBudgetCheck(False, ("DEADLINE_BUDGET_EXCEEDED",), base.available, base.requested,
                                       budget.generation, remaining_ms)
        return DeadlineBudgetCheck(True, (), base.available, base.requested, budget.generation, remaining_ms)


def aggregate_checks(budget: BudgetEnvelope, requirements: ResourceVector) -> tuple[BudgetCheck, ...]:
    require(type(requirements) is ResourceVector, "RESOURCE_VECTOR_REQUIRED")
    return (ComputeBudgetController().assess(budget, requirements.cpu_milli),
            MemoryBudgetController().assess(budget, requirements.memory_bytes),
            ExecutionTimeBudgetController().assess(budget, requirements.wall_time_ms))
