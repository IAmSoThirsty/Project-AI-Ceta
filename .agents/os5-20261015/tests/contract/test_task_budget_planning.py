"""Pure task-budget planning on real mapped controllers and neighboring types.

Controlled budgets/time/revisions are data; no principal authentication, physical
provisioning, native resource reservation or effect execution is qualified here.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import threading
import unittest

from ceta.contracts.resource_management import BudgetEnvelope, ResourceVector, ReservationRequest
from ceta.contracts.temporal import ClockSample, Deadline
from ceta.contracts.wire import ContractError
from ceta.resource.budget import (ChildBudgetRequest, ComputeBudgetController, MemoryBudgetController,
    ExecutionTimeBudgetController, TaskBudgetProposal, TaskBudgetPlan, plan_task_budgets, project_workload_budget)

REVISION = "sha256:" + "1" * 64
THREAD_RECEIPTS = []


def vector(value):
    return ResourceVector(value, value, value, value)


class TaskBudgetPlanningTests(unittest.TestCase):
    def parent(self):
        return BudgetEnvelope("budget.parent", vector(1000), vector(100), vector(100), vector(100), 7)

    def proposal(self, parent, index, *, limit=None, task_id=None, budget_id=None):
        return TaskBudgetProposal(task_id or "task.child." + str(index), "sha256:" + f"{index + 2:064x}",
            ChildBudgetRequest(budget_id or "budget.child." + str(index), parent, parent.generation,
                vector(100) if limit is None else limit, vector(10), vector(10), vector(10)))

    def clocks(self):
        return (ClockSample("boot.budget", 1, 1, 1_000_000_000, 1_000_000_000, 0, True),
                ClockSample("boot.budget", 1, 1, 1_100_000_000, 1_100_000_000, 0, True))

    def plan(self, parent, proposals, **changes):
        previous, current = self.clocks()
        args = dict(expected_parent_generation=parent.generation,
                    deadline=Deadline("boot.budget", 1, 1, 1_000_000_000, 11_000_000_000, 1_000_000_000, 11_000_000_000),
                    previous_clock=previous, current_clock=current)
        args.update(changes)
        return plan_task_budgets("task.parent", REVISION, parent, proposals, **args)

    def test_all_sibling_limits_share_parent_with_both_control_reserves_preserved(self):
        parent = self.parent(); children = tuple(self.proposal(parent, index) for index in range(4))
        result = self.plan(parent, children)
        self.assertEqual(result.state, "PROPOSED")
        self.assertEqual(result.proposed_limits, vector(400))
        self.assertEqual(result.remaining, vector(300))
        self.assertEqual(result.parent, parent)
        self.assertEqual(parent.control_reserve, vector(100))
        self.assertEqual(tuple(child.control_reserve for child in result.child_budgets), (vector(10),) * 4)
        self.assertEqual(tuple(child.allocatable for child in result.child_budgets), (vector(70),) * 4)
        self.assertEqual(tuple(child.generation for child in result.child_budgets), (7,) * 4)

    def test_two_individually_fitting_children_cannot_exceed_shared_parent(self):
        parent = self.parent(); children = tuple(self.proposal(parent, index, limit=vector(400)) for index in range(2))
        self.assertTrue(all(ComputeBudgetController().assess_child(proposal.child).accepted for proposal in children))
        result = self.plan(parent, children)
        self.assertEqual(result.state, "BLOCKED")
        self.assertEqual(result.reason_codes, ("COMPUTE_BUDGET_EXHAUSTED", "MEMORY_BUDGET_EXHAUSTED",
                                              "STORAGE_BUDGET_EXHAUSTED", "EXECUTION_TIME_BUDGET_EXHAUSTED"))
        self.assertEqual(result.child_budgets, ())
        self.assertEqual(result.proposed_limits, vector(0))
        self.assertIsNone(result.remaining)

    def test_each_resource_dimension_is_bounded_independently(self):
        parent = self.parent()
        codes = ("COMPUTE_BUDGET_EXHAUSTED", "MEMORY_BUDGET_EXHAUSTED", "STORAGE_BUDGET_EXHAUSTED", "EXECUTION_TIME_BUDGET_EXHAUSTED")
        for index, code in enumerate(codes):
            with self.subTest(dimension=tuple(ResourceVector.__dataclass_fields__)[index]):
                values = [100, 100, 100, 100]; values[index] = 701
                result = self.plan(parent, (self.proposal(parent, index, limit=ResourceVector(*values)),))
                self.assertEqual(result.reason_codes, (code,))
                self.assertEqual(result.state, "BLOCKED")

    def test_exact_capacity_boundary_keeps_control_and_existing_quantities_distinct(self):
        parent = self.parent(); result = self.plan(parent, (self.proposal(parent, 0, limit=vector(700)),))
        self.assertEqual(result.state, "PROPOSED")
        self.assertEqual(result.remaining, vector(0))
        self.assertEqual((result.parent.measured_use, result.parent.reserved_use, result.parent.control_reserve),
                         (vector(100), vector(100), vector(100)))

    def test_stale_parent_generation_never_creates_child_proposals(self):
        parent = self.parent(); result = self.plan(parent, (self.proposal(parent, 0),), expected_parent_generation=6)
        self.assertEqual(result.state, "BLOCKED")
        self.assertEqual(result.reason_codes, ("PARENT_BUDGET_GENERATION_STALE",))
        self.assertEqual(result.child_budgets, ())

    def test_full_parent_snapshot_must_match_not_only_generation(self):
        parent = self.parent(); other = replace(parent, measured_use=vector(200))
        result = self.plan(parent, (self.proposal(other, 0),))
        self.assertEqual(result.reason_codes, ("TASK_BUDGET_PARENT_MISMATCH",))
        self.assertEqual(result.state, "BLOCKED")

    def test_each_child_expected_parent_generation_is_bound(self):
        parent = self.parent(); child = self.proposal(parent, 0)
        child = replace(child, child=replace(child.child, expected_parent_generation=6))
        self.assertEqual(self.plan(parent, (child,)).reason_codes, ("TASK_BUDGET_PARENT_MISMATCH",))

    def test_duplicate_child_budget_and_task_identities_are_blocked(self):
        parent = self.parent(); first = self.proposal(parent, 0)
        for second in (self.proposal(parent, 1, task_id=first.task_id),
                       self.proposal(parent, 1, budget_id=first.child.child_budget_id)):
            with self.subTest(task=second.task_id, budget=second.child.child_budget_id):
                self.assertEqual(self.plan(parent, (first, second)).reason_codes, ("TASK_BUDGET_DUPLICATE_CHILD",))

    def test_parent_task_and_budget_cannot_be_their_own_child(self):
        parent = self.parent()
        self.assertEqual(self.plan(parent, (self.proposal(parent, 0, task_id="task.parent"),)).reason_codes,
                         ("TASK_BUDGET_TASK_IDENTITY_CONFLICT",))
        child = self.proposal(parent, 0, budget_id=parent.budget_id)
        self.assertEqual(self.plan(parent, (child,)).reason_codes, ("CHILD_BUDGET_IDENTITY_CONFLICT",))
        self.assertEqual(MemoryBudgetController().assess_child(child.child).reason_codes, ("CHILD_BUDGET_IDENTITY_CONFLICT",))

    def test_cancellation_returns_no_proposed_children_or_capacity(self):
        parent = self.parent(); before = replace(parent)
        result = self.plan(parent, (self.proposal(parent, 0),), cancelled=True)
        self.assertEqual((result.state, result.reason_codes, result.child_budgets),
                         ("CANCELLED", ("TASK_BUDGET_PLAN_CANCELLED",), ()))
        self.assertEqual(result.proposed_limits, vector(0)); self.assertEqual(parent, before)
        with self.assertRaises(ContractError) as error:
            result.parent_reservation_request("request.cancelled", observation_sequence=1, observation_monotonic_ns=1)
        self.assertEqual(error.exception.code, "RESOURCE_TASK_BUDGET_PLAN_NOT_PROPOSED")

    def test_missing_physical_accelerator_and_inference_capabilities_are_explicit(self):
        parent = self.parent(); names = ("PHYSICAL_PROVISIONING", "ACCELERATOR_ACCOUNTING", "INFERENCE_ACCOUNTING")
        result = self.plan(parent, (self.proposal(parent, 0),), required_capabilities=names)
        self.assertEqual(result.state, "UNAVAILABLE")
        self.assertEqual(result.reason_codes, tuple(name + "_UNAVAILABLE" for name in names))
        self.assertEqual(result.child_budgets, ())

    def test_unhashable_unknown_or_duplicate_capability_input_has_typed_error(self):
        parent = self.parent()
        for names in (([],), ("UNKNOWN",), ("PHYSICAL_PROVISIONING", "PHYSICAL_PROVISIONING"), ["PHYSICAL_PROVISIONING"]):
            with self.subTest(names=names):
                with self.assertRaises(ContractError) as error:
                    self.plan(parent, (), required_capabilities=names)
                self.assertEqual(error.exception.code, "RESOURCE_TASK_BUDGET_INPUT_INVALID")

    def test_child_count_is_bounded_before_work(self):
        parent = self.parent(); children = tuple(self.proposal(parent, index, limit=vector(30)) for index in range(129))
        with self.assertRaises(ContractError) as error:
            self.plan(parent, children)
        self.assertEqual(error.exception.code, "RESOURCE_TASK_BUDGET_INPUT_INVALID")

    def test_unsigned_sum_overflow_is_denied_without_wrap_or_saturation(self):
        limit = ResourceVector(2**63 - 1, 1000, 1000, 1000)
        parent = BudgetEnvelope("budget.large", limit, vector(0), vector(0), vector(0), 7)
        child_limit = ResourceVector(2**63 - 1, 100, 100, 100)
        result = self.plan(parent, (self.proposal(parent, 0, limit=child_limit), self.proposal(parent, 1, limit=child_limit)))
        self.assertEqual(result.state, "BLOCKED")
        self.assertEqual(result.reason_codes, ("COMPUTE_BUDGET_EXHAUSTED",))

    def test_task_revision_and_identifiers_are_checked_without_becoming_authority(self):
        parent = self.parent()
        with self.assertRaises(ContractError):
            TaskBudgetProposal("task.child", "claimed-approved", self.proposal(parent, 0).child)
        with self.assertRaises(ContractError):
            TaskBudgetProposal("bad task", REVISION, self.proposal(parent, 0).child)
        result = self.plan(parent, (self.proposal(parent, 0),))
        self.assertEqual(result.parent_task_revision, REVISION)
        self.assertEqual(result.state, "PROPOSED")

    def test_detached_snapshot_does_not_alias_original_mutable_nested_values(self):
        parent = self.parent(); child = self.proposal(parent, 0); result = self.plan(parent, (child,))
        object.__setattr__(parent.limit, "cpu_milli", 999)
        object.__setattr__(child.child.limit, "memory_bytes", 999)
        self.assertEqual(result.parent.limit, vector(1000))
        self.assertEqual(result.proposed_limits, vector(100))
        result.__post_init__()

    def test_mutated_nested_boolean_is_rejected_before_planning(self):
        parent = self.parent(); child = self.proposal(parent, 0)
        object.__setattr__(child.child.limit, "cpu_milli", True)
        with self.assertRaises(ContractError) as error:
            self.plan(parent, (child,))
        self.assertEqual(error.exception.code, "RESOURCE_VECTOR_INVALID")

    def test_mutated_plan_is_revalidated_before_constructing_reservation_selector(self):
        parent = self.parent(); result = self.plan(parent, (self.proposal(parent, 0),))
        object.__setattr__(result.remaining, "cpu_milli", True)
        with self.assertRaises(ContractError) as error:
            result.parent_reservation_request("request.mutated", observation_sequence=1, observation_monotonic_ns=1)
        self.assertEqual(error.exception.code, "RESOURCE_VECTOR_INVALID")

    def test_real_neighbor_projection_and_request_types_consume_exact_aggregate(self):
        parent = self.parent(); result = self.plan(parent, (self.proposal(parent, 0), self.proposal(parent, 1)))
        projection = project_workload_budget(result.parent, result.proposed_limits, expected_generation=7)
        self.assertTrue(projection.accepted); self.assertEqual(projection.remaining, result.remaining)
        request = result.parent_reservation_request("request.parent-plan", observation_sequence=3, observation_monotonic_ns=100)
        self.assertIs(type(request), ReservationRequest)
        self.assertEqual((request.budget_id, request.expected_generation, request.requirements),
                         (parent.budget_id, 7, vector(200)))
        self.assertEqual(parent.reserved_use, vector(100))

    def test_concurrent_evaluation_is_deterministic_without_allocating_capacity(self):
        parent = self.parent(); children = (self.proposal(parent, 0), self.proposal(parent, 1))
        barrier = threading.Barrier(8)
        def evaluate(_):
            barrier.wait(timeout=2)
            THREAD_RECEIPTS.append({"test_id": self.id(), "native_thread_id": threading.get_native_id(),
                                    "thread_ident": threading.get_ident(), "work": "bounded pure projection"})
            return self.plan(parent, children)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(evaluate, range(8)))
        self.assertEqual(results, [results[0]] * 8)
        self.assertEqual(parent.reserved_use, vector(100))
        self.assertEqual(results[0].proposed_limits, vector(200))

    def test_reconstruction_rechecks_changed_parent_and_never_revives_allocation(self):
        parent = self.parent(); child = self.proposal(parent, 0); first = self.plan(parent, (child,))
        reconstructed = self.plan(replace(parent), (replace(child),))
        self.assertEqual(first, reconstructed)
        changed = replace(parent, generation=8)
        stale = self.plan(changed, (child,), expected_parent_generation=7)
        self.assertEqual(stale.state, "BLOCKED")
        self.assertEqual(stale.reason_codes, ("PARENT_BUDGET_GENERATION_STALE",))
        self.assertEqual(changed.reserved_use, vector(100))

    def test_task_group_respects_uncertain_wall_deadline_and_rounds_down(self):
        parent = self.parent(); previous, current = self.clocks()
        current = replace(current, uncertainty_ns=1_000_000)
        deadline = Deadline("boot.budget", 1, 1, 1_000_000_000, 11_000_000_000, 1_000_000_000, 1_111_999_999)
        result = self.plan(parent, (self.proposal(parent, 0),), deadline=deadline, previous_clock=previous, current_clock=current)
        self.assertEqual(result.state, "BLOCKED")
        self.assertEqual(result.reason_codes, ("DEADLINE_BUDGET_EXCEEDED",))
        self.assertEqual(result.remaining_deadline_ms, 10)

    def test_untrusted_clock_and_new_epoch_close_task_projection(self):
        parent = self.parent(); previous, current = self.clocks()
        for sample, code in ((replace(current, wall_trusted=False), "TRUSTED_TIME_UNAVAILABLE"),
                             (replace(current, durable_epoch=2), "TIME_EPOCH_CHANGED")):
            with self.subTest(code=code):
                result = self.plan(parent, (self.proposal(parent, 0),), previous_clock=previous, current_clock=sample)
                self.assertEqual((result.state, result.reason_codes), ("BLOCKED", (code,)))

    def test_empty_plan_has_zero_projection_and_no_child_artifacts(self):
        parent = self.parent(); result = self.plan(parent, ())
        self.assertEqual((result.state, result.proposed_limits, result.remaining, result.child_budgets),
                         ("PROPOSED", vector(0), parent.allocatable, ()))

    def test_malformed_budget_and_oversized_controller_input_have_typed_errors(self):
        for controller in (ComputeBudgetController(), MemoryBudgetController(), ExecutionTimeBudgetController()):
            with self.assertRaises(ContractError) as error:
                controller.assess(None, 1)
            self.assertEqual(error.exception.code, "RESOURCE_BUDGET_INPUT_INVALID")
            with self.assertRaises(ContractError) as error:
                controller.assess(self.parent(), 2**63)
            self.assertEqual(error.exception.code, "RESOURCE_BUDGET_INPUT_INVALID")

    def test_forged_proposed_plan_cannot_change_aggregate_or_child_generation(self):
        parent = self.parent(); result = self.plan(parent, (self.proposal(parent, 0),))
        with self.assertRaises(ContractError):
            replace(result, proposed_limits=vector(101))
        with self.assertRaises(ContractError):
            replace(result, child_budgets=(replace(result.child_budgets[0], generation=8),))


if __name__ == "__main__":
    unittest.main(verbosity=2)
