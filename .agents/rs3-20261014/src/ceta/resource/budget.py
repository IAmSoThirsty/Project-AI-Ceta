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
