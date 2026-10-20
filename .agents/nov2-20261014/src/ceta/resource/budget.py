"""Pure projections for the three resource-budgeting controllers.

These assess a pinned ``BudgetEnvelope`` only.  Canonical reservation, charge,
release and lease fencing remain operations of the injected state owner.
"""
from dataclasses import dataclass

from ceta.contracts.resource_management import BudgetEnvelope, ResourceVector, identifier, require
from ceta.contracts.store_transactions import commitment
from ceta.contracts.temporal import ClockSample, Deadline, require_deadline_current
from ceta.contracts.wire import ContractError


def _vector(value: ResourceVector) -> ResourceVector:
    require(type(value) is ResourceVector, "RESOURCE_VECTOR_REQUIRED")
    value.__post_init__()
    return value


def _envelope(value: BudgetEnvelope) -> BudgetEnvelope:
    require(type(value) is BudgetEnvelope, "RESOURCE_BUDGET_INPUT_INVALID")
    for vector in (value.limit, value.control_reserve, value.measured_use, value.reserved_use):
        _vector(vector)
    value.__post_init__()
    return value


def _copy_vector(value: ResourceVector) -> ResourceVector:
    _vector(value)
    return ResourceVector(value.cpu_milli, value.memory_bytes, value.storage_bytes, value.wall_time_ms)


def _copy_envelope(value: BudgetEnvelope) -> BudgetEnvelope:
    _envelope(value)
    return BudgetEnvelope(value.budget_id, _copy_vector(value.limit), _copy_vector(value.control_reserve),
                          _copy_vector(value.measured_use), _copy_vector(value.reserved_use), value.generation)


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
        _envelope(self.parent)
        for value in (self.limit, self.control_reserve, self.measured_use, self.reserved_use):
            _vector(value)
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
        _vector(self.estimated_use)
        envelope = _envelope(BudgetEnvelope(self.budget_id, self.limit, self.control_reserve,
                                           self.measured_use, self.reserved_use, self.observed_generation))
        if self.accepted:
            _vector(self.remaining)
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
    _envelope(budget); _vector(estimated_use)
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
    require(type(budget) is BudgetEnvelope and type(requested) is int and 0 <= requested <= 2**63 - 1
            and type(available) is int and available >= 0, "RESOURCE_BUDGET_INPUT_INVALID")
    return BudgetCheck(requested <= available, () if requested <= available else (code,), available,
                       requested, budget.generation)


def assess_child_budget(request: ChildBudgetRequest) -> ChildBudgetAssessment:
    """Check a child proposal against one pinned parent snapshot.

    This cannot allocate capacity: the owner must still atomically reserve the
    accepted proposal with the returned expected generation.
    """
    require(type(request) is ChildBudgetRequest, "RESOURCE_CHILD_BUDGET_REQUEST_REQUIRED")
    request.__post_init__()
    parent = request.parent
    if request.expected_parent_generation != parent.generation:
        return ChildBudgetAssessment(False, None, parent.budget_id, request.expected_parent_generation,
                                     parent.generation, ("PARENT_BUDGET_GENERATION_STALE",))
    if request.child_budget_id == parent.budget_id:
        return ChildBudgetAssessment(False, None, parent.budget_id, request.expected_parent_generation,
                                     parent.generation, ("CHILD_BUDGET_IDENTITY_CONFLICT",))
    if not request.limit.fits_within(parent.allocatable):
        return ChildBudgetAssessment(False, None, parent.budget_id, request.expected_parent_generation,
                                     parent.generation, ("CHILD_BUDGET_EXCEEDS_PARENT_REMAINING",))
    child = BudgetEnvelope(request.child_budget_id, request.limit, request.control_reserve,
                           request.measured_use, request.reserved_use, parent.generation)
    return ChildBudgetAssessment(True, child, parent.budget_id, request.expected_parent_generation,
                                 parent.generation, ())


class ComputeBudgetController:
    def assess(self, budget: BudgetEnvelope, requested_cpu_milli: int) -> BudgetCheck:
        _envelope(budget)
        return _check(budget, requested=requested_cpu_milli, available=budget.allocatable.cpu_milli,
                      code="COMPUTE_BUDGET_EXHAUSTED")

    def assess_child(self, request: ChildBudgetRequest) -> ChildBudgetAssessment:
        return assess_child_budget(request)


class MemoryBudgetController:
    def assess(self, budget: BudgetEnvelope, requested_memory_bytes: int) -> BudgetCheck:
        _envelope(budget)
        return _check(budget, requested=requested_memory_bytes, available=budget.allocatable.memory_bytes,
                      code="MEMORY_BUDGET_EXHAUSTED")

    def assess_child(self, request: ChildBudgetRequest) -> ChildBudgetAssessment:
        return assess_child_budget(request)


class ExecutionTimeBudgetController:
    def assess(self, budget: BudgetEnvelope, requested_wall_time_ms: int) -> BudgetCheck:
        _envelope(budget)
        return _check(budget, requested=requested_wall_time_ms, available=budget.allocatable.wall_time_ms,
                      code="EXECUTION_TIME_BUDGET_EXHAUSTED")

    def assess_deadline(self, budget: BudgetEnvelope, requested_wall_time_ms: int, *, deadline: Deadline,
                        previous_clock: ClockSample, current_clock: ClockSample) -> DeadlineBudgetCheck:
        """Assess one request against the canonical trusted monotonic deadline."""
        base = self.assess(budget, requested_wall_time_ms)
        require(type(deadline) is Deadline and type(previous_clock) is ClockSample
                and type(current_clock) is ClockSample, "RESOURCE_DEADLINE_INPUT_INVALID")
        deadline.__post_init__(); previous_clock.__post_init__(); current_clock.__post_init__()
        try:
            require_deadline_current(deadline, previous_clock, current_clock)
        except ContractError as error:
            return DeadlineBudgetCheck(False, (error.code,), base.available, base.requested,
                                       budget.generation, None)
        remaining_ms = min(deadline.expires_monotonic_ns - current_clock.monotonic_ns,
                           deadline.expires_wall_ns - current_clock.latest_wall_ns) // 1_000_000
        if not base.accepted:
            return DeadlineBudgetCheck(False, base.reason_codes, base.available, base.requested,
                                       budget.generation, remaining_ms)
        if requested_wall_time_ms > remaining_ms:
            return DeadlineBudgetCheck(False, ("DEADLINE_BUDGET_EXCEEDED",), base.available, base.requested,
                                       budget.generation, remaining_ms)
        return DeadlineBudgetCheck(True, (), base.available, base.requested, budget.generation, remaining_ms)


def aggregate_checks(budget: BudgetEnvelope, requirements: ResourceVector) -> tuple[BudgetCheck, ...]:
    require(type(requirements) is ResourceVector, "RESOURCE_VECTOR_REQUIRED")
    _vector(requirements)
    return (ComputeBudgetController().assess(budget, requirements.cpu_milli),
            MemoryBudgetController().assess(budget, requirements.memory_bytes),
            ExecutionTimeBudgetController().assess(budget, requirements.wall_time_ms))


MAXIMUM_TASK_CHILDREN = 128
UNAVAILABLE_TASK_CAPABILITIES = frozenset({"PHYSICAL_PROVISIONING", "ACCELERATOR_ACCOUNTING", "INFERENCE_ACCOUNTING"})


@dataclass(frozen=True, slots=True)
class TaskBudgetProposal:
    """Exact task/revision selectors plus a child proposal; never authority."""
    task_id: str
    task_revision: str
    child: ChildBudgetRequest

    def __post_init__(self) -> None:
        identifier(self.task_id, "RESOURCE_TASK_BUDGET_IDENTIFIER_INVALID")
        commitment(self.task_revision)
        require(type(self.child) is ChildBudgetRequest, "RESOURCE_CHILD_BUDGET_REQUEST_REQUIRED")
        self.child.__post_init__()


@dataclass(frozen=True, slots=True)
class TaskBudgetPlan:
    """Detached capacity projection; canonical owners must approve/reserve it."""
    parent_task_id: str
    parent_task_revision: str
    parent: BudgetEnvelope
    expected_parent_generation: int
    proposals: tuple[TaskBudgetProposal, ...]
    state: str
    reason_codes: tuple[str, ...]
    child_budgets: tuple[BudgetEnvelope, ...]
    proposed_limits: ResourceVector
    remaining: ResourceVector | None
    remaining_deadline_ms: int | None

    def __post_init__(self) -> None:
        identifier(self.parent_task_id, "RESOURCE_TASK_BUDGET_IDENTIFIER_INVALID")
        commitment(self.parent_task_revision)
        _envelope(self.parent); _vector(self.proposed_limits)
        require(type(self.expected_parent_generation) is int and 0 <= self.expected_parent_generation <= 2**63 - 1
                and type(self.proposals) is tuple and len(self.proposals) <= MAXIMUM_TASK_CHILDREN
                and all(type(proposal) is TaskBudgetProposal for proposal in self.proposals)
                and type(self.state) is str and self.state in {"PROPOSED", "BLOCKED", "CANCELLED", "UNAVAILABLE"}
                and type(self.reason_codes) is tuple and len(self.reason_codes) <= 4
                and all(type(code) is str and 1 <= len(code) <= 96 for code in self.reason_codes)
                and type(self.child_budgets) is tuple
                and (self.remaining_deadline_ms is None or type(self.remaining_deadline_ms) is int
                     and 0 <= self.remaining_deadline_ms <= 2**63 - 1), "RESOURCE_TASK_BUDGET_PLAN_INVALID")
        for proposal in self.proposals:
            proposal.__post_init__()
        if self.state != "PROPOSED":
            require(bool(self.reason_codes) and self.child_budgets == () and self.remaining is None
                    and self.proposed_limits == ResourceVector(0, 0, 0, 0), "RESOURCE_TASK_BUDGET_PLAN_INVALID")
            return
        require(not self.reason_codes and self.expected_parent_generation == self.parent.generation
                and type(self.remaining) is ResourceVector and type(self.remaining_deadline_ms) is int
                and len(self.child_budgets) == len(self.proposals), "RESOURCE_TASK_BUDGET_PLAN_INVALID")
        _vector(self.remaining)
        require(len({proposal.task_id for proposal in self.proposals}) == len(self.proposals)
                and len({proposal.child.child_budget_id for proposal in self.proposals}) == len(self.proposals)
                and all(proposal.task_id != self.parent_task_id and proposal.child.child_budget_id != self.parent.budget_id
                        and proposal.child.parent == self.parent
                        and proposal.child.expected_parent_generation == self.expected_parent_generation
                        for proposal in self.proposals), "RESOURCE_TASK_BUDGET_PLAN_INVALID")
        total = ResourceVector(0, 0, 0, 0)
        for proposal, child in zip(self.proposals, self.child_budgets):
            _envelope(child)
            request = proposal.child
            require(child == BudgetEnvelope(request.child_budget_id, request.limit, request.control_reserve,
                                             request.measured_use, request.reserved_use, self.parent.generation),
                    "RESOURCE_TASK_BUDGET_PLAN_INVALID")
            total = total.add(child.limit)
        require(total == self.proposed_limits and total.fits_within(self.parent.allocatable)
                and total.wall_time_ms <= self.remaining_deadline_ms
                and self.remaining == self.parent.allocatable.subtract(total), "RESOURCE_TASK_BUDGET_PLAN_INVALID")

    def parent_reservation_request(self, request_id: str, *, observation_sequence: int,
                                   observation_monotonic_ns: int):
        """Construct a selector for existing owner approval; execute no call."""
        from ceta.contracts.resource_management import ReservationRequest
        self.__post_init__()
        require(self.state == "PROPOSED", "RESOURCE_TASK_BUDGET_PLAN_NOT_PROPOSED")
        return ReservationRequest(request_id, self.parent.budget_id, self.expected_parent_generation,
                                  _copy_vector(self.proposed_limits), observation_sequence, observation_monotonic_ns)


def plan_task_budgets(parent_task_id: str, parent_task_revision: str, parent: BudgetEnvelope,
                      proposals: tuple[TaskBudgetProposal, ...], *, expected_parent_generation: int,
                      deadline: Deadline, previous_clock: ClockSample, current_clock: ClockSample,
                      cancelled: bool = False, required_capabilities: tuple[str, ...] = ()) -> TaskBudgetPlan:
    """Bound all sibling limits together; preserve controls and source quantities.

    This is not allocation, dispatch or task-reference authentication. Independent
    projections of one parent cannot prevent concurrent owner allocations; the
    returned reservation selector still requires current canonical owner approval.
    """
    identifier(parent_task_id, "RESOURCE_TASK_BUDGET_IDENTIFIER_INVALID")
    commitment(parent_task_revision); _envelope(parent)
    require(type(expected_parent_generation) is int and 0 <= expected_parent_generation <= 2**63 - 1
            and type(proposals) is tuple and len(proposals) <= MAXIMUM_TASK_CHILDREN
            and all(type(proposal) is TaskBudgetProposal for proposal in proposals)
            and type(cancelled) is bool and type(required_capabilities) is tuple
            and len(required_capabilities) <= len(UNAVAILABLE_TASK_CAPABILITIES)
            and all(type(name) is str and name in UNAVAILABLE_TASK_CAPABILITIES for name in required_capabilities)
            and len(set(required_capabilities)) == len(required_capabilities),
            "RESOURCE_TASK_BUDGET_INPUT_INVALID")
    require(type(deadline) is Deadline and type(previous_clock) is ClockSample
            and type(current_clock) is ClockSample, "RESOURCE_DEADLINE_INPUT_INVALID")
    deadline.__post_init__(); previous_clock.__post_init__(); current_clock.__post_init__()
    snapshot = _copy_envelope(parent)
    copied = []
    for proposal in proposals:
        proposal.__post_init__(); request = proposal.child
        copied.append(TaskBudgetProposal(proposal.task_id, proposal.task_revision,
            ChildBudgetRequest(request.child_budget_id, _copy_envelope(request.parent), request.expected_parent_generation,
                               _copy_vector(request.limit), _copy_vector(request.control_reserve),
                               _copy_vector(request.measured_use), _copy_vector(request.reserved_use))))
    pinned = tuple(copied)
    def denied(state, reasons, remaining_ms=None):
        return TaskBudgetPlan(parent_task_id, parent_task_revision, snapshot, expected_parent_generation,
                              pinned, state, reasons, (), ResourceVector(0, 0, 0, 0), None, remaining_ms)
    if cancelled:
        return denied("CANCELLED", ("TASK_BUDGET_PLAN_CANCELLED",))
    if required_capabilities:
        return denied("UNAVAILABLE", tuple(name + "_UNAVAILABLE" for name in required_capabilities))
    if expected_parent_generation != snapshot.generation:
        return denied("BLOCKED", ("PARENT_BUDGET_GENERATION_STALE",))
    if any(proposal.child.parent != snapshot or proposal.child.expected_parent_generation != expected_parent_generation
           for proposal in pinned):
        return denied("BLOCKED", ("TASK_BUDGET_PARENT_MISMATCH",))
    if any(proposal.task_id == parent_task_id for proposal in pinned):
        return denied("BLOCKED", ("TASK_BUDGET_TASK_IDENTITY_CONFLICT",))
    if any(proposal.child.child_budget_id == snapshot.budget_id for proposal in pinned):
        return denied("BLOCKED", ("CHILD_BUDGET_IDENTITY_CONFLICT",))
    if (len({proposal.task_id for proposal in pinned}) != len(pinned)
            or len({proposal.child.child_budget_id for proposal in pinned}) != len(pinned)):
        return denied("BLOCKED", ("TASK_BUDGET_DUPLICATE_CHILD",))
    fields = ("cpu_milli", "memory_bytes", "storage_bytes", "wall_time_ms")
    totals = tuple(sum(getattr(proposal.child.limit, name) for proposal in pinned) for name in fields)
    available = snapshot.allocatable
    codes = ("COMPUTE_BUDGET_EXHAUSTED", "MEMORY_BUDGET_EXHAUSTED", "STORAGE_BUDGET_EXHAUSTED", "EXECUTION_TIME_BUDGET_EXHAUSTED")
    exceeded = tuple(code for name, quantity, code in zip(fields, totals, codes) if quantity > getattr(available, name))
    if exceeded:
        return denied("BLOCKED", exceeded)
    total = ResourceVector(*totals)
    time_check = ExecutionTimeBudgetController().assess_deadline(snapshot, total.wall_time_ms, deadline=deadline,
                                                               previous_clock=previous_clock, current_clock=current_clock)
    if not time_check.accepted:
        return denied("BLOCKED", time_check.reason_codes, time_check.remaining_deadline_ms)
    children = tuple(BudgetEnvelope(proposal.child.child_budget_id, proposal.child.limit,
        proposal.child.control_reserve, proposal.child.measured_use, proposal.child.reserved_use, snapshot.generation)
        for proposal in pinned)
    return TaskBudgetPlan(parent_task_id, parent_task_revision, snapshot, expected_parent_generation, pinned,
                          "PROPOSED", (), children, total, available.subtract(total), time_check.remaining_deadline_ms)
