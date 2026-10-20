"""Actual canonical SQLite accounting with explicitly controlled owner fixtures.

Native principal authentication, physical approval/provisioning, dispatched work,
verified live cleanup and production admission are not established by fixtures.
The existing kernel, store and resource admission consumer execute unchanged.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts.kernel_transactions import (PeerIdentity, control_wire, digest, read_basis, resource_key,
    resource_wire, task_key, task_wire)
from ceta.contracts.resource_management import (AdmissionState, BudgetEnvelope, PressureLevel, ReservationRequest, ResourceVector)
from ceta.contracts.resource_reservations import (ResourceBudgetBinding, ResourceLease, ZERO_RESOURCES,
    read_resource_budget, request_value, resource_budget_key, resource_budget_wire, resource_lease_key)
from ceta.contracts.temporal import issue_deadline
from ceta.contracts.store_transactions import STORE_PROFILE
from ceta.contracts.wire import ContractError, canonical_bytes, strict_loads
from ceta.kernel.transactions import KernelTransactions
from ceta.resource.admission import (AdmissionRequest, MeasuredWorkloadProfile, WorkloadAdmissionController, WorkloadRequirementEstimator)
from ceta.resource.hardware import StorageCapacityMonitor
from test_kernel_transactions import (CommitBarrierJournal, KernelFixture, INSTALLATION, PROJECT, POLICY, ENVIRONMENT, CHANGED, SCOPES)

NATIVE_RECEIPTS = []


class ResourceFixture(KernelFixture):
    """Same captured owners object, explicit allowlists, no native authority claim."""
    def __init__(self, schema):
        super().__init__(schema)
        self.allowed = {}
        self.resource_available = self.cleanup_available = True
        self.resource_calls = self.cleanup_calls = 0
        self.resource_hook = self.cleanup_hook = None
        self.current_lock = threading.RLock()
        self.current_calls = 0
        self.current_hook = None
        self.owners.require_resource_reservation = self.require_resources
        self.owners.require_resource_cleanup = self.require_cleanup
        self.owners.require_resource_current = self.require_current
        basis, grant, read_set = read_basis(self.basis, self.codec)
        p = self.codec.decode(self.proposal_wire)
        self.binding = ResourceBudgetBinding(PROJECT, self.proposal["task_id"], self.owners.worker.principal_id,
            self.owners.worker.session_id, p.commitment, digest("resource-basis", basis), grant,
            self.codec.decode(self.grant_wire).commitment, read_set.authority_generation, read_set.fence_generation,
            read_set.policy_commitment, read_set.environment_commitment,
            issue_deadline(self.grant["expires_at"], 10_000_000_000, *self.owners.samples))
        self.original_budget = BudgetEnvelope("budget:resource-fixture", ResourceVector(1000, 10000, 10000, 10000),
            ResourceVector(100, 100, 100, 100), ResourceVector(100, 100, 100, 100), ZERO_RESOURCES, 1)
        self.bkey = resource_budget_key(PROJECT, self.original_budget.budget_id)
        self.seed({self.bkey: resource_budget_wire(self.binding, self.original_budget)})
        self.bind()

    def bind(self, **kwargs):
        self.kernel = KernelTransactions(self.store, self.codec, INSTALLATION, owners=self.owners)
        self.port = self.kernel.resource_reservations(self.proposal_wire, self.owners.worker_context, **kwargs)

    def request(self, request_id="request:resource-fixture", *, requirements=None,
                generation=None, at=None):
        budget = self.read_budget()
        requirements = ResourceVector(100, 1000, 1000, 1000) if requirements is None else requirements
        value = ReservationRequest(request_id, budget.budget_id, budget.generation if generation is None else generation,
            requirements, 7, self.owners.samples[1].monotonic_ns if at is None else at)
        self.allow_request(value)
        return value

    def allow_request(self, request):
        self.allowed[request.request_id] = request_value(request)

    def read_budget(self):
        return read_resource_budget(self.cell(self.bkey).value_wire, self.bkey)[1]

    def require_resources(self, proposal, basis_wire, budget_wire, request, peer):
        self.resource_calls += 1
        if self.resource_hook is not None:
            self.resource_hook()
        binding, budget = read_resource_budget(budget_wire, self.bkey)
        if (not self.resource_available or proposal.original_wire != self.proposal_wire or basis_wire != self.basis
                or peer != self.owners.worker or binding != self.binding
                or budget.limit != self.original_budget.limit or budget.control_reserve != self.original_budget.control_reserve
                or budget.measured_use != self.original_budget.measured_use
                or self.allowed.get(request.request_id) != request_value(request)):
            raise ContractError("FIXTURE_RESOURCE_APPROVAL_DENIED")

    def require_cleanup(self, proposal, lease_wire, peer):
        self.cleanup_calls += 1
        if self.cleanup_hook is not None:
            self.cleanup_hook()
        value = strict_loads(lease_wire)
        key = resource_lease_key(PROJECT, value["request"]["request_id"])
        lease = ResourceLease.from_wire(lease_wire, key)
        if (not self.cleanup_available or peer != self.owners.worker or proposal.original_wire != self.proposal_wire
                or lease.binding != self.binding or lease.state != "HELD"):
            raise ContractError("FIXTURE_RESOURCE_CLEANUP_DENIED")

    def require_current(self, proposal, basis_wire, budget_wire, request, peer, request_context):
        """Controlled coordinated view; no native authentication/approval proof.

        Coordinated test writers take current_lock and never call the store
        while holding it. Older direct fault injections stay explicitly
        uncoordinated; their writes precede this final view. No owner callback
        runs inside this view: all compared values belong to the same fixture.
        """
        with self.current_lock:
            self.current_calls += 1
            if self.current_hook is not None:
                self.current_hook()
            if request_context is not self.owners.worker_context or peer != self.owners.worker:
                raise ContractError("FIXTURE_AUTHENTICATION_DENIED")
            if self.owners.prepared.get(proposal.record_id) != (proposal.commitment, basis_wire):
                raise ContractError("FIXTURE_PREPARATION_DENIED")
            budget_id = strict_loads(budget_wire)["budget"]["budget_id"] if request is None else request.budget_id
            binding, budget = read_resource_budget(budget_wire, resource_budget_key(PROJECT, budget_id))
            if (proposal.original_wire != self.proposal_wire or basis_wire != self.basis or binding != self.binding
                    or budget.limit != self.original_budget.limit
                    or budget.control_reserve != self.original_budget.control_reserve
                    or budget.measured_use != self.original_budget.measured_use):
                raise ContractError("FIXTURE_RESOURCE_APPROVAL_DENIED")
            if request is not None and (not self.resource_available
                    or self.allowed.get(request.request_id) != request_value(request)):
                raise ContractError("FIXTURE_RESOURCE_APPROVAL_DENIED")

    def cut_resources(self, *requests):
        keys = (self.bkey,) + tuple(resource_lease_key(PROJECT, r.request_id) for r in requests)
        return self.cut(keys)

    def close_with_receipt(self, test_id):
        position = self.store.store_position()
        self.store.close()
        artifacts = [{"path": str(path), "bytes": path.stat().st_size,
                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                     for path in sorted(self.root.iterdir()) if path.is_file()]
        NATIVE_RECEIPTS.append({"test_id": test_id, "fixture_root": str(self.root), "closed": True,
            "commits": position.next_commit, "head": position.head, "artifacts": artifacts,
            "owner_qualification": "Controlled allowlists and seeded budget; real SqliteJournal, no native principal/cleanup proof"})


class ResourceReservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes())

    def setUp(self):
        self.f = ResourceFixture(self.schema)
        self.addCleanup(self.f.close_with_receipt, self.id())

    def denied_unchanged(self, request, action, code):
        before = self.f.cut_resources(request)
        with self.assertRaises(ContractError) as error:
            action()
        self.assertEqual(error.exception.code, code)
        self.assertEqual(self.f.cut_resources(request), before)

    def test_real_atomic_reservation_keeps_control_and_measured_use_distinct(self):
        f = self.f; request = f.request()
        previous = f.store.store_position()
        operation_budget = f.budget()
        issuance = f.cell(f.issuance_key())
        result = f.port.reserve(request)
        self.assertEqual(result.state, AdmissionState.ADMITTED)
        self.assertEqual(result.generation, 2)
        self.assertEqual(f.store.store_position().next_commit, previous.next_commit + 1)
        self.assertEqual(f.budget(), operation_budget)
        self.assertEqual(f.cell(f.issuance_key()), issuance)
        budget = f.read_budget()
        self.assertEqual(budget.reserved_use, request.requirements)
        self.assertEqual(budget.control_reserve, f.original_budget.control_reserve)
        self.assertEqual(budget.measured_use, f.original_budget.measured_use)
        lease = f.port.recover(request.request_id)
        self.assertEqual(lease.reservation_ref, result.reservation_ref)
        self.assertEqual(lease.state, "HELD")
        row = f.store.replay(PROJECT)[-1]
        self.assertEqual(strict_loads(row.event_wire)["event_type"], "kernel.resource.reserved")
        self.assertEqual(row.payload_wire, f.codec.decode(f.proposal_wire).canonical_wire)
        self.assertEqual(f.kernel.require_runtime_admission.__name__, "require_runtime_admission")
        with self.assertRaises(ContractError) as error:
            f.kernel.require_runtime_admission()
        self.assertEqual(error.exception.code, "RUNTIME_AUTHORITY_OWNERS_UNAVAILABLE")

    def test_exact_retry_returns_same_lease_without_another_commit(self):
        f = self.f; request = f.request()
        first = f.port.reserve(request); before = f.cut_resources(request)
        self.assertEqual(f.port.reserve(request), first)
        self.assertEqual(f.cut_resources(request), before)

    def test_changed_arguments_cannot_reuse_request_identity(self):
        f = self.f; request = f.request(); f.port.reserve(request)
        changed = replace(request, requirements=ResourceVector(200, 1000, 1000, 1000)); f.allow_request(changed)
        self.denied_unchanged(request, lambda: f.port.reserve(changed), "RESOURCE_RESERVATION_REQUEST_CONFLICT")

    def test_changed_expected_generation_cannot_replay_identity(self):
        f = self.f; request = f.request(); f.port.reserve(request)
        changed = replace(request, expected_generation=2); f.allow_request(changed)
        self.denied_unchanged(request, lambda: f.port.reserve(changed), "RESOURCE_RESERVATION_REQUEST_CONFLICT")

    def test_changed_observation_cannot_replay_identity(self):
        f = self.f; request = f.request(); f.port.reserve(request)
        changed = replace(request, observation_sequence=8); f.allow_request(changed)
        self.denied_unchanged(request, lambda: f.port.reserve(changed), "RESOURCE_RESERVATION_REQUEST_CONFLICT")

    def test_stale_generation_never_dispatches_a_second_write(self):
        f = self.f; first = f.request(); f.port.reserve(first)
        second = f.request("request:second", generation=1); before = f.cut_resources(first, second)
        result = f.port.reserve(second)
        self.assertEqual(result.reason_codes, ("RESOURCE_BUDGET_GENERATION_CHANGED",))
        self.assertEqual(f.cut_resources(first, second), before)

    def test_all_resource_dimensions_retain_control_reserve(self):
        f = self.f
        for index, name in enumerate(ResourceVector.__dataclass_fields__):
            with self.subTest(dimension=name):
                values = [0, 0, 0, 0]; values[index] = getattr(f.read_budget().allocatable, name) + 1
                request = f.request("request:exhausted-" + name, requirements=ResourceVector(*values))
                before = f.cut_resources(request); result = f.port.reserve(request)
                self.assertEqual(result.reason_codes, ("RESOURCE_BUDGET_EXHAUSTED",))
                self.assertEqual(f.cut_resources(request), before)

    def test_unapproved_exact_shaped_request_is_denied_before_mutation(self):
        request = self.f.request(); self.f.allowed.clear()
        self.denied_unchanged(request, lambda: self.f.port.reserve(request), "FIXTURE_RESOURCE_APPROVAL_DENIED")

    def test_missing_resource_predicate_denies_existing_owners(self):
        request = self.f.request(); del self.f.owners.require_resource_reservation
        self.denied_unchanged(request, lambda: self.f.port.reserve(request), "RESOURCE_AUTHORITY_OWNER_UNAVAILABLE")

    def test_default_kernel_without_owners_denies(self):
        f = self.f; request = f.request()
        port = KernelTransactions(f.store, f.codec, INSTALLATION).resource_reservations(f.proposal_wire, object())
        self.denied_unchanged(request, lambda: port.reserve(request), "KERNEL_OWNERS_UNAVAILABLE")

    def test_caller_boolean_and_other_authenticated_subject_do_not_supply_authority(self):
        f = self.f; request = f.request()
        for context, code in (({"validated": True}, "FIXTURE_AUTHENTICATION_DENIED"),
                              (f.owners.owner_context, "FIXTURE_PREPARATION_DENIED")):
            with self.subTest(code=code):
                port = f.kernel.resource_reservations(f.proposal_wire, context)
                self.denied_unchanged(request, lambda: port.reserve(request), code)

    def test_expired_future_and_rollback_observations_are_denied(self):
        f = self.f
        for at in (f.owners.samples[1].monotonic_ns + 1, f.owners.samples[1].monotonic_ns - 2_000_000_001):
            if at < 0:
                continue
            request = f.request("request:observation-" + str(at), at=at)
            self.denied_unchanged(request, lambda: f.port.reserve(request), "RESOURCE_RESERVATION_OBSERVATION_STALE")
        f.bind(maximum_observation_age_ns=1)
        request = f.request("request:old-observation", at=f.owners.samples[1].monotonic_ns - 2)
        self.denied_unchanged(request, lambda: f.port.reserve(request), "RESOURCE_RESERVATION_OBSERVATION_STALE")

    def test_expired_budget_and_changed_clock_epoch_do_not_reserve(self):
        f = self.f; request = f.request()
        original = f.owners.samples
        for change, code in (({"monotonic_ns": f.binding.deadline.expires_monotonic_ns}, "DEADLINE_EXPIRED_OR_UNCERTAIN"),
                              ({"boot_id": "boot:changed"}, "BOOT_CHANGED"),
                              ({"durable_epoch": 2}, "TIME_EPOCH_CHANGED"),
                              ({"resume_generation": 2}, "RESUME_GENERATION_CHANGED")):
            with self.subTest(code=code):
                f.owners.samples = (replace(original[0], **change), replace(original[1], **change))
                self.denied_unchanged(request, lambda: f.port.reserve(request), code)
        f.owners.samples = original

    def test_malformed_nested_quantity_is_denied_before_owner_or_store_use(self):
        f = self.f; request = f.request(); before_calls = f.resource_calls
        object.__setattr__(request.requirements, "memory_bytes", True)
        self.denied_unchanged(request, lambda: f.port.reserve(request), "RESOURCE_VECTOR_INVALID")
        self.assertEqual(f.resource_calls, before_calls)

    def test_policy_task_and_resource_generation_changes_invalidate_the_budget(self):
        f = self.f; request = f.request()
        cases = ((f.control_key, control_wire(INSTALLATION, 2, 1, POLICY, ENVIRONMENT)),
                 (task_key(PROJECT, f.proposal["task_id"]), task_wire(PROJECT, f.proposal["task_id"], CHANGED)),
                 (resource_key(PROJECT, "resource:target"), resource_wire(PROJECT, "resource:target", CHANGED)))
        for key, changed in cases:
            original = f.cell(key).value_wire; f.put(key, changed)
            before = f.cut_resources(request)
            with self.assertRaises(ContractError):
                f.port.reserve(request)
            self.assertEqual(f.cut_resources(request), before)
            f.put(key, original)

    def test_revoked_grant_cannot_replay_an_existing_held_lease(self):
        f = self.f; request = f.request(); f.port.reserve(request)
        grant = dict(f.grant, status="REVOKED", revocation_generation=1); f.put(f.grant_key, canonical_bytes(grant))
        self.denied_unchanged(request, lambda: f.port.reserve(request), "KERNEL_GRANT_NOT_ACTIVE")

    def test_budget_cannot_be_rebound_to_another_task_or_principal(self):
        f = self.f; request = f.request()
        binding = replace(f.binding, task_id="task:other")
        f.put(f.bkey, resource_budget_wire(binding, replace(f.original_budget, generation=2)))
        self.denied_unchanged(request, lambda: f.port.reserve(request), "RESOURCE_RESERVATION_SUBJECT_MISMATCH")

    def test_budget_record_generation_must_match_the_actual_store_cell(self):
        f = self.f; request = f.request()
        f.put(f.bkey, resource_budget_wire(f.binding, f.original_budget))
        self.denied_unchanged(request, lambda: f.port.reserve(request), "RESOURCE_BUDGET_GENERATION_MISMATCH")

    def test_failure_after_real_sql_inserts_rolls_back_budget_lease_and_event(self):
        f = self.f; request = f.request(); before = f.cut_resources(request)
        f.fail_commit = True
        with self.assertRaisesRegex(RuntimeError, "after all writer inserts"):
            f.port.reserve(request)
        f.fail_commit = False
        self.assertEqual(f.cut_resources(request), before)
        self.assertEqual(f.port.reserve(request).state, AdmissionState.ADMITTED)

    def test_owner_denial_at_commit_boundary_rolls_back_without_hold(self):
        f = self.f; request = f.request()
        f.before_commit_action = lambda: setattr(f, "resource_available", False)
        self.denied_unchanged(request, lambda: f.port.reserve(request), "FIXTURE_RESOURCE_APPROVAL_DENIED")
        f.before_commit_action = None; f.resource_available = True

    def test_control_exception_in_owner_guard_preserves_primary_and_rolls_back(self):
        f = self.f; request = f.request(); primary = KeyboardInterrupt("fixture cancellation")
        def interrupted():
            if f.resource_calls == 2:
                raise primary
        f.resource_hook = interrupted; before = f.cut_resources(request)
        with self.assertRaises(KeyboardInterrupt) as error:
            f.port.reserve(request)
        self.assertIs(error.exception, primary)
        self.assertEqual(f.cut_resources(request), before)
        f.resource_hook = None

    def test_post_commit_owner_denial_retains_hold_for_coherent_recovery(self):
        f = self.f; request = f.request(); before = f.store.store_position()
        f.store.after_commit = lambda: setattr(f, "resource_available", False)
        with self.assertRaises(ContractError) as error:
            f.port.reserve(request)
        self.assertEqual(error.exception.code, "FIXTURE_RESOURCE_APPROVAL_DENIED")
        self.assertEqual(f.store.store_position().next_commit, before.next_commit + 1)
        self.assertEqual(f.port.recover(request.request_id).state, "HELD")
        f.store.after_commit = None; f.resource_available = True
        recovered = f.port.reserve(request)
        self.assertEqual(recovered.generation, 2)
        self.assertEqual(f.store.store_position().next_commit, before.next_commit + 1)

    def test_lost_result_reopen_preserves_exact_lease_and_idempotent_retry(self):
        f = self.f; request = f.request(); first = f.port.reserve(request)
        before = f.cut_resources(request); f.reopen(); f.bind()
        self.assertEqual(f.port.reserve(request), first)
        self.assertEqual(f.cut_resources(request), before)

    def test_concurrent_duplicate_requests_commit_only_one_lease(self):
        f = self.f; request = f.request(); before = f.store.store_position()
        f.store.commit_barrier = threading.Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: f.port.reserve(request), range(2)))
        f.store.commit_barrier = None
        self.assertEqual(results[0], results[1])
        self.assertEqual(f.read_budget().reserved_use, request.requirements)
        self.assertEqual(f.store.store_position().next_commit, before.next_commit + 1)

    def test_concurrent_distinct_requests_cannot_allocate_same_capacity_twice(self):
        f = self.f; need = f.read_budget().allocatable
        first = f.request("request:parallel-first", requirements=need)
        second = f.request("request:parallel-second", requirements=need)
        before = f.store.store_position(); f.store.commit_barrier = threading.Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(f.port.reserve, (first, second)))
        f.store.commit_barrier = None
        self.assertEqual(sorted(r.state.value for r in results), sorted((AdmissionState.ADMITTED.value, AdmissionState.BLOCKED.value)))
        self.assertEqual(f.read_budget().reserved_use, need)
        self.assertEqual(f.store.store_position().next_commit, before.next_commit + 1)

    def test_release_requires_same_captured_owner_verified_cleanup(self):
        f = self.f; request = f.request(); f.port.reserve(request)
        f.cleanup_available = False
        self.denied_unchanged(request, lambda: f.port.release(request.request_id, "reason:cleanup"), "FIXTURE_RESOURCE_CLEANUP_DENIED")
        f.cleanup_available = True
        released = f.port.release(request.request_id, "reason:cleanup")
        self.assertEqual(released.state, "RELEASED")
        self.assertEqual(released.terminal_generation, 3)
        self.assertEqual(f.read_budget().reserved_use, ZERO_RESOURCES)
        self.assertGreaterEqual(f.cleanup_calls, 3)

    def test_missing_cleanup_capability_keeps_all_held_capacity(self):
        f = self.f; request = f.request(); f.port.reserve(request)
        del f.owners.require_resource_cleanup
        self.denied_unchanged(request, lambda: f.port.release(request.request_id, "reason:cleanup"), "RESOURCE_AUTHORITY_OWNER_UNAVAILABLE")

    def test_cleanup_lost_before_commit_rolls_back_terminal_state_and_refund(self):
        f = self.f; request = f.request(); f.port.reserve(request)
        f.before_commit_action = lambda: setattr(f, "cleanup_available", False)
        self.denied_unchanged(request, lambda: f.port.release(request.request_id, "reason:cleanup"), "FIXTURE_RESOURCE_CLEANUP_DENIED")
        f.before_commit_action = None; f.cleanup_available = True

    def test_release_after_revocation_is_cleanup_without_reviving_admission(self):
        f = self.f; request = f.request(); f.port.reserve(request)
        f.put(f.grant_key, canonical_bytes(dict(f.grant, status="REVOKED", revocation_generation=1)))
        result = f.port.release(request.request_id, "reason:cleanup")
        self.assertEqual(result.state, "RELEASED")
        self.assertEqual(f.read_budget().reserved_use, ZERO_RESOURCES)
        self.denied_unchanged(request, lambda: f.port.reserve(request), "KERNEL_GRANT_NOT_ACTIVE")

    def test_exact_release_retry_does_not_refund_twice_and_replay_stays_fenced(self):
        f = self.f; request = f.request(); f.port.reserve(request)
        released = f.port.release(request.request_id, "reason:cleanup"); before = f.cut_resources(request)
        self.assertEqual(f.port.release(request.request_id, "reason:cleanup"), released)
        self.assertEqual(f.cut_resources(request), before)
        result = f.port.reserve(request)
        self.assertEqual(result.reason_codes, ("RESOURCE_RESERVATION_TERMINAL",))
        self.assertEqual(f.cut_resources(request), before)

    def test_pending_cancel_persists_tombstone_without_reserving_or_refunding(self):
        f = self.f; request = f.request(); original = f.read_budget()
        cancelled = f.port.cancel(request, "reason:cancel")
        self.assertEqual(cancelled.state, "CANCELLED")
        self.assertIsNone(cancelled.allocated_generation)
        self.assertEqual(f.read_budget(), original)
        self.assertEqual(f.port.reserve(request).reason_codes, ("RESOURCE_RESERVATION_TERMINAL",))
        before = f.cut_resources(request)
        self.assertEqual(f.port.cancel(request, "reason:cancel"), cancelled)
        self.assertEqual(f.cut_resources(request), before)

    def test_unapproved_request_cannot_create_a_pending_tombstone(self):
        f = self.f; request = f.request(); f.allowed.clear()
        self.denied_unchanged(request, lambda: f.port.cancel(request, "reason:cancel"), "FIXTURE_RESOURCE_APPROVAL_DENIED")

    def test_pending_cancel_revalidates_approval_inside_commit(self):
        f = self.f; request = f.request()
        f.before_commit_action = lambda: setattr(f, "resource_available", False)
        self.denied_unchanged(request, lambda: f.port.cancel(request, "reason:cancel"), "FIXTURE_RESOURCE_APPROVAL_DENIED")
        f.before_commit_action = None; f.resource_available = True

    def test_cancelled_identity_remains_fenced_after_restart(self):
        f = self.f; request = f.request(); f.port.cancel(request, "reason:cancel")
        before = f.cut_resources(request); f.reopen(); f.bind()
        self.assertEqual(f.port.recover(request.request_id).state, "CANCELLED")
        self.assertEqual(f.port.reserve(request).state, AdmissionState.BLOCKED)
        self.assertEqual(f.cut_resources(request), before)

    def test_cancel_held_reservation_requires_cleanup_and_preserves_tombstone(self):
        f = self.f; request = f.request(); f.port.reserve(request)
        f.cleanup_available = False
        self.denied_unchanged(request, lambda: f.port.cancel(request, "reason:cancel"), "FIXTURE_RESOURCE_CLEANUP_DENIED")
        f.cleanup_available = True
        self.assertEqual(f.port.cancel(request, "reason:cancel").state, "CANCELLED")
        self.assertEqual(f.read_budget().reserved_use, ZERO_RESOURCES)
        self.assertEqual(f.port.reserve(request).state, AdmissionState.BLOCKED)

    def test_reason_change_cannot_silently_rewrite_terminal_history(self):
        f = self.f; request = f.request(); f.port.cancel(request, "reason:cancel")
        self.denied_unchanged(request, lambda: f.port.cancel(request, "reason:other"), "RESOURCE_RESERVATION_TERMINAL_CONFLICT")

    def test_other_subject_cannot_recover_or_cleanup_lease(self):
        f = self.f; request = f.request(); f.port.reserve(request)
        port = f.kernel.resource_reservations(f.proposal_wire, f.owners.owner_context)
        self.denied_unchanged(request, lambda: port.recover(request.request_id), "RESOURCE_RESERVATION_SUBJECT_MISMATCH")
        self.denied_unchanged(request, lambda: port.release(request.request_id, "reason:cleanup"), "RESOURCE_RESERVATION_SUBJECT_MISMATCH")

    def test_budget_read_is_coherent_and_allocates_nothing(self):
        f = self.f; request = f.request(); before = f.cut_resources(request)
        self.assertEqual(f.port.budget(request.budget_id), f.read_budget())
        self.assertEqual(f.cut_resources(request), before)

    def test_overlong_resource_owner_return_is_rejected_without_publication(self):
        f = self.f; request = f.request(); f.bind(maximum_owner_check_ns=1_000_000)
        f.resource_hook = lambda: time.sleep(0.005)
        self.denied_unchanged(request, lambda: f.port.reserve(request), "RESOURCE_OWNER_CHECK_TOO_LONG")
        self.assertGreater(f.resource_calls, 0)
        f.resource_hook = None

    def test_owner_boolean_allow_is_rejected(self):
        f = self.f; request = f.request(); f.owners.require_resource_reservation = lambda *args: True
        self.denied_unchanged(request, lambda: f.port.reserve(request), "KERNEL_OWNER_DECISION_INVALID")

    def test_overlong_clock_owner_return_is_rejected_before_mutation(self):
        f = self.f; request = f.request(); f.bind(maximum_owner_check_ns=1_000_000)
        original = f.owners.clock
        observed = []
        def delayed_clock():
            observed.append(True)
            time.sleep(0.005)
            return original()
        f.owners.clock = delayed_clock
        self.denied_unchanged(request, lambda: f.port.reserve(request), "RESOURCE_OWNER_CHECK_TOO_LONG")
        self.assertEqual(observed, [True])

    def test_owner_oserror_is_typed_unavailable_without_mutation(self):
        f = self.f; request = f.request()
        def unavailable(*args):
            raise OSError("controlled owner observation unavailable")
        f.owners.require_resource_reservation = unavailable
        self.denied_unchanged(request, lambda: f.port.reserve(request), "RESOURCE_AUTHORITY_OWNER_UNAVAILABLE")

    def test_delayed_final_snapshot_cannot_return_stale_admitted_result(self):
        f = self.f; request = f.request(); f.bind(maximum_observation_age_ns=1_000_000)
        original = f.store.snapshot; held_reads = 0; actual_delay = None
        key = resource_lease_key(PROJECT, request.request_id)
        def delayed_snapshot(keys, **kwargs):
            nonlocal held_reads, actual_delay
            cells = original(keys, **kwargs)
            if any(cell.key == key and cell.value_wire is not None for cell in cells):
                held_reads += 1
                if held_reads == 2:
                    started = time.perf_counter_ns(); time.sleep(0.005)
                    actual_delay = time.perf_counter_ns() - started
                    f.owners.samples = tuple(replace(sample, monotonic_ns=sample.monotonic_ns + actual_delay,
                                                     wall_time_ns=sample.wall_time_ns + actual_delay)
                                             for sample in f.owners.samples)
            return cells
        f.store.snapshot = delayed_snapshot
        with self.assertRaises(ContractError) as error:
            f.port.reserve(request)
        self.assertEqual(error.exception.code, "RESOURCE_RESERVATION_OBSERVATION_STALE")
        self.assertGreater(actual_delay, 1_000_000)
        self.assertEqual(f.read_budget().reserved_use, request.requirements)
        self.assertEqual(f.port.recover(request.request_id).state, "HELD")
        NATIVE_RECEIPTS.append({"test_id": self.id(), "actual_delayed_snapshot_ns": actual_delay,
            "maximum_observation_age_ns": 1_000_000, "held_snapshot_reads": held_reads,
            "qualification": "Real SQLite snapshot and injected native scheduling delay; clock samples advance by measured delay under controlled owner"})

    def test_missing_canonical_budget_never_uses_caller_quantity_as_provisioning(self):
        f = self.f; request = replace(f.request(), budget_id="budget:never-provisioned")
        f.allow_request(request)
        self.denied_unchanged(request, lambda: f.port.reserve(request), "KERNEL_REQUIRED_STATE_MISSING")

    def test_strict_budget_profile_and_unknown_fields_are_rejected(self):
        f = self.f; request = f.request()
        original = strict_loads(f.cell(f.bkey).value_wire)
        for changed in (dict(original, profile="unsupported-resource-profile"), dict(original, private_authority=True)):
            f.put(f.bkey, canonical_bytes(changed))
            self.denied_unchanged(request, lambda: f.port.reserve(request), "KERNEL_METADATA_INVALID")

    def test_typed_lease_cannot_forge_terminal_refund_or_change_key(self):
        f = self.f; request = f.request(); f.port.reserve(request)
        lease = f.port.recover(request.request_id); key = resource_lease_key(PROJECT, request.request_id)
        original = strict_loads(lease.canonical_wire)
        for changed, code in ((dict(original, state="RUNNING"), "RESOURCE_LEASE_STATE_INVALID"),
                               (dict(original, state="RELEASED"), "KERNEL_GENERATION_INVALID"),
                               (dict(original, reservation_ref="reservation:other"), "RESOURCE_LEASE_KEY_MISMATCH")):
            with self.subTest(code=code):
                with self.assertRaises(ContractError) as error:
                    ResourceLease.from_wire(canonical_bytes(changed), key)
                self.assertEqual(error.exception.code, code)

    def test_simultaneous_cleanup_cannot_refund_twice(self):
        f = self.f; request = f.request(); f.port.reserve(request)
        before = f.store.store_position(); f.store.commit_barrier = threading.Barrier(2)
        def release_once(_):
            try:
                return f.port.release(request.request_id, "reason:cleanup")
            except ContractError as error:
                return error.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(release_once, range(2)))
        f.store.commit_barrier = None
        self.assertEqual(sum(type(result) is ResourceLease for result in results), 1)
        self.assertIn("JOURNAL_REVISION_CONFLICT", results)
        self.assertEqual(f.read_budget().reserved_use, ZERO_RESOURCES)
        self.assertEqual(f.store.store_position().next_commit, before.next_commit + 1)
        current = f.port.recover(request.request_id)
        self.assertEqual(current.state, "RELEASED")
        self.assertEqual(f.port.release(request.request_id, "reason:cleanup"), current)

    def test_cancel_racing_reservation_yields_held_or_terminal_without_double_capacity(self):
        f = self.f; request = f.request(); f.store.commit_barrier = threading.Barrier(2)
        def attempt(cancel):
            try:
                return f.port.cancel(request, "reason:cancel") if cancel else f.port.reserve(request)
            except ContractError as error:
                return error.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, (False, True)))
        f.store.commit_barrier = None
        current = f.port.recover(request.request_id)
        self.assertIn(current.state, {"HELD", "CANCELLED"})
        self.assertEqual(f.read_budget().reserved_use, request.requirements if current.state == "HELD" else ZERO_RESOURCES)
        if current.state == "HELD":
            self.assertIn("JOURNAL_REVISION_CONFLICT", results)
            f.port.cancel(request, "reason:cancel")
        self.assertEqual(f.port.reserve(request).state, AdmissionState.BLOCKED)
        self.assertEqual(f.read_budget().reserved_use, ZERO_RESOURCES)

    def test_cleanup_denial_after_commit_keeps_terminal_observation_without_second_refund(self):
        f = self.f; request = f.request(); f.port.reserve(request)
        f.store.after_commit = lambda: setattr(f, "cleanup_available", False)
        with self.assertRaises(ContractError) as error:
            f.port.release(request.request_id, "reason:cleanup")
        self.assertEqual(error.exception.code, "FIXTURE_RESOURCE_CLEANUP_DENIED")
        self.assertEqual(f.port.recover(request.request_id).state, "RELEASED")
        self.assertEqual(f.read_budget().reserved_use, ZERO_RESOURCES)
        f.store.after_commit = None; before = f.cut_resources(request)
        self.assertEqual(f.port.release(request.request_id, "reason:cleanup").state, "RELEASED")
        self.assertEqual(f.cut_resources(request), before)

    def test_actual_windows_process_crash_reconstructs_whole_resource_transaction(self):
        f = self.f
        for phase, expected_exit in (("before", 71), ("after", 72)):
            with self.subTest(phase=phase):
                root = ROOT / ".agents/fixtures/resource-reservation-crash" / uuid.uuid4().hex
                root.mkdir(parents=True, exist_ok=False)
                command = [sys.executable, "-B", "-X", "utf8", str(Path(__file__)), "--reservation-crash", phase, str(root)]
                with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NO_WINDOW, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")) as child:
                    try:
                        stdout, stderr = child.communicate(timeout=20)
                    except subprocess.TimeoutExpired:
                        child.kill(); child.communicate(); raise
                    self.assertEqual(child.returncode, expected_exit)
                    self.assertEqual(stderr, b"")
                    process_id = child.pid
                selected = strict_loads((root / "selected-root.json").read_bytes())
                target = Path(selected["sqlite_root"])
                self.assertTrue(target.is_relative_to(ROOT / ".agents/fixtures/kernel-22"))
                store = CommitBarrierJournal(target, f.codec, SCOPES, profile=STORE_PROFILE)
                try:
                    kernel = KernelTransactions(store, f.codec, INSTALLATION, owners=f.owners)
                    port = kernel.resource_reservations(f.proposal_wire, f.owners.worker_context)
                    request = f.request(generation=1)
                    budget = read_resource_budget(store.snapshot((f.bkey,))[0].value_wire, f.bkey)[1]
                    lease_cell = store.snapshot((resource_lease_key(PROJECT, request.request_id),))[0]
                    if phase == "before":
                        self.assertEqual(budget.reserved_use, ZERO_RESOURCES)
                        self.assertIsNone(lease_cell.value_wire)
                        self.assertEqual(budget.generation, 1)
                    else:
                        self.assertEqual(budget.reserved_use, request.requirements)
                        self.assertEqual(budget.generation, 2)
                        self.assertEqual(port.recover(request.request_id).state, "HELD")
                        before = store.store_position()
                        self.assertEqual(port.reserve(request).state, AdmissionState.ADMITTED)
                        self.assertEqual(store.store_position(), before)
                    position = store.store_position()
                finally:
                    store.close()
                NATIVE_RECEIPTS.append({"test_id": self.id(), "phase": phase, "command_argv": command,
                    "process_id": process_id, "actual_exit": expected_exit, "process_waited": True,
                    "stdout_sha256": hashlib.sha256(stdout).hexdigest(), "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
                    "sqlite_root": str(target), "closed": True, "commits": position.next_commit,
                    "qualification": "Actual disposable Windows child and SQLite crash; stdlib direct-child custody, controlled owners; native Job/effect authority unqualified"})

    def test_actual_admission_consumer_reaches_real_canonical_store(self):
        f = self.f; request = f.request(); now = request.observation_monotonic_ns
        profile = MeasuredWorkloadProfile("workload:fixture", "profile:fixture", POLICY, ENVIRONMENT, now,
            (request.requirements,), 900)
        estimate = WorkloadRequirementEstimator((profile,), clock=lambda: now, headroom_milli=0).estimate(
            profile.workload_id, expected_profile_revision=profile.profile_revision)
        controller = WorkloadAdmissionController(f.port, clock=lambda: now)
        value = AdmissionRequest(request.request_id, f.port.budget(request.budget_id), estimate,
            request.observation_sequence, now, True, PressureLevel.NORMAL)
        result = controller.admit(value)
        self.assertEqual(result.state, AdmissionState.ADMITTED)
        self.assertEqual(f.port.recover(request.request_id).reservation_ref, result.reservation_ref)
        self.assertEqual(f.read_budget().reserved_use, request.requirements)

    def test_actual_windows_storage_observation_is_not_an_authority_proof(self):
        f = self.f
        monitor = StorageCapacityMonitor(path=f.root)
        observation = monitor.sample()
        self.assertIsNotNone(observation.total.value)
        self.assertEqual(observation.total.method, "python:shutil.disk_usage")
        now = observation.total.observed_monotonic_ns
        original = f.owners.samples
        f.owners.samples = (replace(original[0], monotonic_ns=now), replace(original[1], monotonic_ns=now))
        f.binding = replace(f.binding, deadline=issue_deadline(f.grant["expires_at"], 10_000_000_000, *f.owners.samples))
        updated = replace(f.original_budget, generation=2)
        f.put(f.bkey, resource_budget_wire(f.binding, updated))
        request = f.request(at=now)
        self.assertEqual(f.port.reserve(request).state, AdmissionState.ADMITTED)
        self.assertTrue(observation.total.method.startswith("python:"))
        NATIVE_RECEIPTS.append({"test_id": self.id(), "native_observation": {"method": observation.total.method,
            "sequence": observation.sequence, "total": observation.total.value, "free": observation.free.value,
            "observed_monotonic_ns": now}, "qualification": "Real Windows volume query; owner wall/epoch/provisioning remain controlled"})


class ResourceReturnBoundaryTests(unittest.TestCase):
    """Currentness under actual threads, with controlled authority and time."""
    @classmethod
    def setUpClass(cls):
        cls.schema = strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes())

    def setUp(self):
        self.f = ResourceFixture(self.schema)
        self.addCleanup(self.f.close_with_receipt, self.id())

    def clock_change(self, at, change):
        f = self.f; original = f.owners.clock; calls = 0; observations = []
        def clock():
            nonlocal calls
            calls += 1
            if calls == at:
                entered = threading.Event(); finished = threading.Event(); errors = []
                def changed():
                    try:
                        if not entered.wait(timeout=1):
                            raise AssertionError("clock observation did not start")
                        change()
                    except BaseException as error:
                        errors.append(error)
                    finally:
                        finished.set()
                worker = threading.Thread(target=changed, name="resource-return-" + str(at))
                started = time.perf_counter_ns(); worker.start(); entered.set()
                try:
                    self.assertTrue(finished.wait(timeout=1))
                finally:
                    worker.join(timeout=1)
                self.assertFalse(worker.is_alive())
                if errors:
                    raise errors[0]
                observations.append({"clock_call": calls, "thread_ident": worker.ident,
                    "native_thread_id": worker.native_id, "elapsed_ns": time.perf_counter_ns() - started,
                    "joined": True, "qualification": "Explicit alternate-thread scheduling and controlled owner change"})
            return original()
        f.owners.clock = clock
        NATIVE_RECEIPTS.append({"test_id": self.id(), "clock_boundary": observations})
        return observations

    def test_final_reservation_clock_rechecks_prepared_basis(self):
        f = self.f; request = f.request(); before = f.store.store_position()
        observed = self.clock_change(5, f.owners.prepared.clear)
        with self.assertRaises(ContractError) as error:
            f.port.reserve(request)
        self.assertEqual(error.exception.code, "FIXTURE_PREPARATION_DENIED")
        self.assertTrue(observed)
        self.assertEqual(f.store.store_position().next_commit, before.next_commit + 1)
        self.assertEqual(f.port.recover(request.request_id).state, "HELD")
        self.assertEqual(f.read_budget().reserved_use, request.requirements)

    def test_final_budget_clock_rechecks_prepared_basis_without_mutation(self):
        f = self.f; request = f.request(); before = f.cut_resources(request)
        observed = self.clock_change(1, f.owners.prepared.clear)
        with self.assertRaises(ContractError) as error:
            f.port.budget(request.budget_id)
        self.assertEqual(error.exception.code, "FIXTURE_PREPARATION_DENIED")
        self.assertTrue(observed)
        self.assertEqual(f.cut_resources(request), before)

    def test_commit_clock_peer_revocation_rolls_back_real_transaction(self):
        f = self.f; request = f.request(); before = f.cut_resources(request)
        observed = self.clock_change(3, lambda: setattr(f.owners, "worker_context", object()))
        with self.assertRaises(ContractError) as error:
            f.port.reserve(request)
        self.assertEqual(error.exception.code, "FIXTURE_AUTHENTICATION_DENIED")
        self.assertTrue(observed)
        self.assertEqual(f.cut_resources(request), before)
        self.assertEqual(f.read_budget().reserved_use, ZERO_RESOURCES)

    def test_commit_clock_resource_withdrawal_rolls_back_real_transaction(self):
        f = self.f; request = f.request(); before = f.cut_resources(request)
        observed = self.clock_change(3, lambda: setattr(f, "resource_available", False))
        with self.assertRaises(ContractError) as error:
            f.port.reserve(request)
        self.assertEqual(error.exception.code, "FIXTURE_RESOURCE_APPROVAL_DENIED")
        self.assertTrue(observed)
        self.assertEqual(f.cut_resources(request), before)
        self.assertEqual(f.read_budget().reserved_use, ZERO_RESOURCES)

    def test_final_clock_oserror_preserves_committed_hold_and_cause(self):
        f = self.f; request = f.request(); original = f.owners.clock; calls = 0
        primary = OSError("controlled final clock unavailable")
        def clock():
            nonlocal calls
            calls += 1
            if calls == 5:
                raise primary
            return original()
        f.owners.clock = clock
        with self.assertRaises(ContractError) as error:
            f.port.reserve(request)
        self.assertEqual(error.exception.code, "RESOURCE_AUTHORITY_OWNER_UNAVAILABLE")
        self.assertIs(error.exception.__cause__, primary)
        self.assertEqual(calls, 5)
        self.assertEqual(f.port.recover(request.request_id).state, "HELD")
        self.assertEqual(f.read_budget().reserved_use, request.requirements)

    def test_final_clock_cancellation_keeps_exact_primary_and_committed_hold(self):
        f = self.f; request = f.request(); original = f.owners.clock; calls = 0
        primary = KeyboardInterrupt("controlled final return cancellation")
        def clock():
            nonlocal calls
            calls += 1
            if calls == 5:
                raise primary
            return original()
        f.owners.clock = clock
        with self.assertRaises(KeyboardInterrupt) as error:
            f.port.reserve(request)
        self.assertIs(error.exception, primary)
        self.assertEqual(calls, 5)
        self.assertEqual(f.port.recover(request.request_id).state, "HELD")
        self.assertEqual(f.read_budget().reserved_use, request.requirements)

    def test_return_denial_then_context_recovery_replays_without_second_allocation(self):
        f = self.f; request = f.request(); original_context = f.owners.worker_context
        self.clock_change(5, lambda: setattr(f.owners, "worker_context", object()))
        with self.assertRaises(ContractError) as error:
            f.port.reserve(request)
        self.assertEqual(error.exception.code, "FIXTURE_AUTHENTICATION_DENIED")
        position = f.store.store_position()
        f.owners.worker_context = original_context
        lease = f.port.recover(request.request_id)
        replay = f.port.reserve(request)
        self.assertEqual(replay.state, AdmissionState.ADMITTED)
        self.assertEqual(replay.reservation_ref, lease.reservation_ref)
        self.assertEqual(replay.generation, 2)
        self.assertEqual(f.store.store_position(), position)
        self.assertEqual(f.read_budget().reserved_use, request.requirements)

    def test_bounded_final_approval_still_consumes_observation_age_margin(self):
        f = self.f; request = f.request(); f.bind(maximum_observation_age_ns=2_000_000)
        delays = []
        def delayed():
            if f.resource_calls == 4:
                started = time.perf_counter_ns(); time.sleep(.005)
                delays.append(time.perf_counter_ns() - started)
        f.resource_hook = delayed
        with self.assertRaises(ContractError) as error:
            f.port.reserve(request)
        self.assertEqual(error.exception.code, "RESOURCE_RESERVATION_OBSERVATION_STALE")
        self.assertEqual(len(delays), 1)
        self.assertGreater(delays[0], 2_000_000)
        self.assertLess(delays[0], 50_000_000)
        self.assertEqual(f.port.recover(request.request_id).state, "HELD")
        self.assertEqual(f.read_budget().reserved_use, request.requirements)
        NATIVE_RECEIPTS.append({"test_id": self.id(), "callback_delay_ns": delays[0],
            "age_margin_ns": 2_000_000, "owner_bound_ns": 50_000_000,
            "qualification": "Actual injected delay and local elapsed bound; controlled static authenticated-time fixture"})

    def budget_tail_deadline(self, wall):
        f = self.f; request = f.request(); sample = f.owners.samples[1]
        field = "expires_wall_ns" if wall else "expires_monotonic_ns"
        origin = sample.latest_wall_ns if wall else sample.monotonic_ns
        f.binding = replace(f.binding, deadline=replace(f.binding.deadline, **{field: origin + 2_000_000}))
        f.put(f.bkey, resource_budget_wire(f.binding, replace(f.original_budget, generation=2)))
        before = f.cut_resources(request); original = f.owners.require_prepared_basis; calls = 0; delays = []
        def prepared(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                started = time.perf_counter_ns(); time.sleep(.005)
                delays.append(time.perf_counter_ns() - started)
            return original(*args)
        f.owners.require_prepared_basis = prepared
        with self.assertRaises(ContractError) as error:
            f.port.budget(request.budget_id)
        self.assertEqual(error.exception.code, "DEADLINE_EXPIRED_OR_UNCERTAIN")
        self.assertEqual(len(delays), 1)
        self.assertGreater(delays[0], 2_000_000)
        self.assertLess(delays[0], 50_000_000)
        self.assertEqual(f.cut_resources(request), before)
        NATIVE_RECEIPTS.append({"test_id": self.id(), "deadline_field": field, "callback_delay_ns": delays[0],
            "remaining_slack_ns": 2_000_000, "owner_bound_ns": 50_000_000,
            "qualification": "Measured local elapsed consumes existing deadline slack; no authenticated sample/epoch constructed"})

    def test_bounded_budget_check_consumes_monotonic_deadline_margin(self):
        self.budget_tail_deadline(False)

    def test_bounded_budget_check_consumes_uncertain_wall_deadline_margin(self):
        self.budget_tail_deadline(True)


class ResourceCurrentViewTests(unittest.TestCase):
    """Executable locked provider composition, explicitly controlled authority."""
    @classmethod
    def setUpClass(cls):
        cls.schema = strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes())

    def setUp(self):
        self.f = ResourceFixture(self.schema)
        self.addCleanup(self.f.close_with_receipt, self.id())

    def test_missing_or_noncallable_current_capability_denies_before_mutation(self):
        f = self.f; request = f.request(); before = f.cut_resources(request)
        for value in (None, True, object()):
            f.owners.require_resource_current = value
            with self.assertRaises(ContractError) as error:
                f.port.reserve(request)
            self.assertEqual(error.exception.code, "RESOURCE_AUTHORITY_OWNER_UNAVAILABLE")
            with self.assertRaises(ContractError) as error:
                f.port.budget(request.budget_id)
            self.assertEqual(error.exception.code, "RESOURCE_AUTHORITY_OWNER_UNAVAILABLE")
            self.assertEqual(f.cut_resources(request), before)

    def test_current_capability_boolean_never_supplies_approval(self):
        f = self.f; request = f.request(); before = f.cut_resources(request)
        for value in (True, False):
            f.owners.require_resource_current = lambda *args: value
            for action in (lambda: f.port.reserve(request), lambda: f.port.budget(request.budget_id)):
                with self.assertRaises(ContractError) as error:
                    action()
                self.assertEqual(error.exception.code, "KERNEL_OWNER_DECISION_INVALID")
                self.assertEqual(f.cut_resources(request), before)

    def test_controlled_current_view_binds_original_context_basis_budget_and_request(self):
        f = self.f; request = f.request(); proposal = f.codec.decode(f.proposal_wire)
        budget_wire = f.cell(f.bkey).value_wire; before = f.cut_resources(request)
        args = (proposal, f.basis, budget_wire, request, f.owners.worker, f.owners.worker_context)
        self.assertIsNone(f.require_current(*args))
        altered_budget = replace(f.original_budget, limit=ResourceVector(2000, 10000, 10000, 10000))
        for position, value, code in (
                (5, object(), "FIXTURE_AUTHENTICATION_DENIED"),
                (1, b"{}", "FIXTURE_PREPARATION_DENIED"),
                (2, resource_budget_wire(f.binding, altered_budget), "FIXTURE_RESOURCE_APPROVAL_DENIED"),
                (3, replace(request, observation_sequence=8), "FIXTURE_RESOURCE_APPROVAL_DENIED")):
            with self.subTest(argument=position):
                changed = list(args); changed[position] = value
                with self.assertRaises(ContractError) as error:
                    f.require_current(*changed)
                self.assertEqual(error.exception.code, code)
                self.assertEqual(f.cut_resources(request), before)

    def test_budget_none_current_view_discloses_without_allocation_approval(self):
        f = self.f; request = f.request(); before = f.cut_resources(request)
        f.resource_available = False; f.allowed.clear()
        self.assertEqual(f.port.budget(request.budget_id), f.read_budget())
        self.assertGreater(f.current_calls, 0)
        with self.assertRaises(ContractError) as error:
            f.port.reserve(request)
        self.assertEqual(error.exception.code, "FIXTURE_RESOURCE_APPROVAL_DENIED")
        self.assertEqual(f.cut_resources(request), before)

    def test_budget_last_authentication_preparation_withdrawal_is_denied(self):
        f = self.f; request = f.request(); before = f.cut_resources(request)
        original = f.owners.authenticate; calls = 0; observed = []
        def authenticate(context):
            nonlocal calls
            peer = original(context); calls += 1
            if calls == 3:
                def withdrawn():
                    with f.current_lock:
                        f.owners.prepared.clear()
                worker = threading.Thread(target=withdrawn, name="resource-budget-authentication-withdrawal")
                started = time.perf_counter_ns(); worker.start()
                try:
                    worker.join(timeout=1)
                finally:
                    worker.join(timeout=1)
                self.assertFalse(worker.is_alive())
                observed.append({"peer_call": calls, "native_thread_id": worker.native_id,
                    "thread_ident": worker.ident, "joined": True, "elapsed_ns": time.perf_counter_ns() - started})
            return peer
        f.owners.authenticate = authenticate
        with self.assertRaises(ContractError) as error:
            f.port.budget(request.budget_id)
        self.assertEqual(error.exception.code, "FIXTURE_PREPARATION_DENIED")
        self.assertTrue(observed)
        self.assertEqual(f.cut_resources(request), before)
        NATIVE_RECEIPTS.append({"test_id": self.id(), "authentication_boundary": observed,
            "qualification": "Actual joined thread withdraws controlled prepared state under the provider's lock before final current-view decision"})

    def test_final_combined_callback_consumes_remaining_observation_margin(self):
        f = self.f; request = f.request(); f.bind(maximum_observation_age_ns=2_000_000); delays = []
        def current_delay():
            if f.current_calls == 4:
                started = time.perf_counter_ns(); time.sleep(.005)
                delays.append(time.perf_counter_ns() - started)
        f.current_hook = current_delay
        with self.assertRaises(ContractError) as error:
            f.port.reserve(request)
        self.assertEqual(error.exception.code, "RESOURCE_RESERVATION_OBSERVATION_STALE")
        self.assertEqual(len(delays), 1)
        self.assertGreater(delays[0], 2_000_000)
        self.assertLess(delays[0], 50_000_000)
        self.assertEqual(f.port.recover(request.request_id).state, "HELD")
        self.assertEqual(f.read_budget().reserved_use, request.requirements)
        NATIVE_RECEIPTS.append({"test_id": self.id(), "combined_callback_delay_ns": delays[0],
            "age_margin_ns": 2_000_000, "qualification": "Injected actual delay in controlled locked provider; no physical clock/authority qualification"})

    def test_overlong_combined_callback_denies_without_hold(self):
        f = self.f; request = f.request(); f.bind(maximum_owner_check_ns=10_000_000)
        before = f.cut_resources(request); f.current_hook = lambda: time.sleep(.03)
        with self.assertRaises(ContractError) as error:
            f.port.reserve(request)
        self.assertEqual(error.exception.code, "RESOURCE_OWNER_CHECK_TOO_LONG")
        self.assertGreater(f.current_calls, 0)
        self.assertEqual(f.cut_resources(request), before)

    def test_coordinated_withdrawal_wins_before_locked_current_decision(self):
        f = self.f; request = f.request(); before = f.cut_resources(request)
        entered = threading.Event(); original = f.owners.require_resource_current; result = {}
        def current(*args):
            entered.set()
            return original(*args)
        def reserve():
            try:
                result["returned"] = f.port.reserve(request)
            except BaseException as error:
                result["error"] = error
        f.owners.require_resource_current = current
        worker = threading.Thread(target=reserve, name="resource-coordinated-current-view")
        f.current_lock.acquire(); started = time.perf_counter_ns()
        try:
            worker.start()
            self.assertTrue(entered.wait(timeout=1))
            f.resource_available = False
        finally:
            f.current_lock.release()
            worker.join(timeout=1)
        self.assertFalse(worker.is_alive())
        self.assertNotIn("returned", result)
        self.assertIsInstance(result.get("error"), ContractError)
        self.assertEqual(result["error"].code, "FIXTURE_RESOURCE_APPROVAL_DENIED")
        self.assertEqual(f.cut_resources(request), before)
        NATIVE_RECEIPTS.append({"test_id": self.id(), "native_thread_id": worker.native_id,
            "thread_ident": worker.ident, "joined": True, "elapsed_ns": time.perf_counter_ns() - started,
            "qualification": "Actual SQLite path and alternate thread; one controlled provider RLock coordinates withdrawal before its final current decision"})


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--reservation-crash":
        phase, output = sys.argv[2], Path(sys.argv[3]).resolve(strict=True)
        if phase not in {"before", "after"} or not output.is_relative_to(ROOT / ".agents/fixtures/resource-reservation-crash"):
            raise SystemExit("invalid crash fixture")
        schema = strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes())
        fixture = ResourceFixture(schema)
        with (output / "selected-root.json").open("xb") as selected:
            selected.write(canonical_bytes({"sqlite_root": str(fixture.root), "phase": phase}))
            selected.flush(); os.fsync(selected.fileno())
        request = fixture.request(generation=1)
        if phase == "before":
            fixture.before_commit_action = lambda: os._exit(71)
        else:
            fixture.store.after_commit = lambda: os._exit(72)
        fixture.port.reserve(request)
        raise SystemExit("crash boundary was not reached")
    unittest.main(verbosity=2)
