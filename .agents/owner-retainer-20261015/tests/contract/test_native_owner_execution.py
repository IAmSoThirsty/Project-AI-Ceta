"""Canonical SQLite and retained owner logic; ALL native/capacity facts CONTROLLED.

No process, Hello, profile, Set or physical storage/provenance guarantee runs.
The real owner methods, kernel coordinator and SQLite transitions are exercised.
"""
import copy
from dataclasses import replace
from pathlib import Path
from types import MethodType, SimpleNamespace
import threading
import unittest
from unittest.mock import patch

from ceta.contracts.kernel_transactions import basis_key
from ceta.contracts.wire import ContractError, strict_loads
from ceta.effects.native_cpu_binding import CpuDriverArguments
from ceta.identity import owner_session as module
from ceta.identity.native_approval import NativeApprovalResult, NativeApprovalSession
from ceta.supervisor.windows_jobs import WindowsOwnedProcess
import test_native_owner_preparation as preparation
import test_owner_authority_transactions as data
import test_owned_cpu_outcome_transactions as outcomes

ROOT = Path(__file__).resolve().parents[2]
FACTS = []
raw = lambda error: BaseException.__dict__['__dict__'].__get__(error)


class ControlledCapacity:
    """Domain fixture only; never accepted as a physical-storage proof."""
    def __init__(self, fixture):
        self.f = fixture
        self.calls, self.exits = [], []
        self.entry_error = self.exit_error = self.check_error = None
        self.result = self.exit_result = None
        self.on_check = None

    def __enter__(self):
        self.f.events.append(('capacity-enter', self.f.store._connection.in_transaction))
        if self.entry_error is not None: raise self.entry_error
        return self

    def require_current(self, phase, request, permit, context, coordinator):
        assert request.canonical_wire == self.f.request.canonical_wire
        assert context is self.f.context and coordinator is self.f.kernel._cpu_execution
        self.calls.append((phase, self.f.store._connection.in_transaction))
        if self.on_check is not None: self.on_check(phase)
        if self.check_error is not None: raise self.check_error
        return self.result

    def __exit__(self, kind, primary, trace):
        self.exits.append((kind, primary, trace))
        if self.exit_error is not None: raise self.exit_error
        return self.exit_result


class Fixture(preparation.Fixture):
    def __init__(self, schema):
        original = data.effect_request
        enrollment = replace(data.enrollment_request(), authority_budget=data.budget(max_bytes_written=65536),
            recovery_budget=data.budget(1, wall_time_ms=5000, max_bytes_read=8192, max_bytes_written=32768),
            evidence_reserve_bytes=32768)
        def effect(enrollment, **kwargs):
            return original(enrollment, required_outcome_bytes=32768,
                operation_budget=data.budget(1, wall_time_ms=5000, max_bytes_read=8192, max_bytes_written=32768), **kwargs)
        with patch.object(data, 'enrollment_request', return_value=enrollment), patch.object(data, 'effect_request', effect):
            super().__init__(schema)
        self.context, self.events = self.control.context, []
        self.owners = self.control  # Existing outcome helper's explicit fixture alias.
        self.owner._execution = None
        old = self.binding._target
        target = object.__new__(WindowsOwnedProcess)
        target.__dict__.update(old.__dict__)
        target._lock = threading.RLock()
        self.binding._target = self.owner._effect.target = target
        self.binding._lock = threading.RLock()
        self.binding._lifetime = self.binding._target_fields()
        registry = SimpleNamespace(_closed=False, _lock=threading.RLock(), _active={self.context: object()})
        self.owner._registry = self.view._registry = registry
        self.capacity = ControlledCapacity(self)
        self.proofs, self.provenance_result, self.provenance_error, self.on_provenance = {}, None, None, None
        def capacity(view, request, prepared, context, coordinator):
            self.events.append(('capacity-factory', self.store._connection.in_transaction))
            assert view is self.view and context is self.context and coordinator is self.kernel._cpu_execution
            assert request.canonical_wire == self.request.canonical_wire
            assert prepared.canonical_wire == self.kernel._decode(self.prepared, 'OperationPermit').canonical_wire
            return self.capacity
        def provenance(view, request, permit, receipt, observation, proof, peer, context, retained):
            self.events.append(('provenance', self.store._connection.in_transaction))
            if self.on_provenance is not None: self.on_provenance()
            if self.provenance_error is not None: raise self.provenance_error
            expected = (request.canonical_wire, permit.canonical_wire, receipt.canonical_wire,
                None if observation is None else observation.canonical_wire)
            if self.proofs.get(proof) != expected or context is not self.context or peer != self.control.peer:
                raise ContractError('CONTROLLED_ORIGIN_NOT_RETAINED')
            assert retained.lease._target is target
            return self.provenance_result
        self.owner._execution_capacity = MethodType(capacity, self.view)
        self.owner._execution_provenance = MethodType(provenance, self.view)
        self.prepared = self.prepare().record_wire
        basis = self.cell(basis_key(data.PROJECT, self.request.proposal_id)).value_wire
        self.control.prepared[self.request.proposal_id] = basis
        self.owner.require_admission = self.control.require_admission  # Explicit CONTROLLED protected-resource port.
        self.binding.driver_arguments = lambda capture, request: CpuDriverArguments(request.process_identity,
            request.expected_limit, request.deadline.expires_monotonic_ns, request.maximum_observation_age_ns,
            request.maximum_duration_ns, 1, request.input_commitment)
        session = object.__new__(NativeApprovalSession)
        session._owner = self.owner._approval
        session.mode, session._enrollment, session._closed = 'interactive', False, False
        session._stop = threading.Event()
        session._bound_context, session._context = self.context, self.context
        session._bound_request_wire = self.request.canonical_wire
        session._native_exited = True
        session.native_facts = dict(empty_job=True, exit_code=0)
        session.helper_evidence = object()
        transcript = data.effect_transcript(self.enrollment, self.request)
        session._result = NativeApprovalResult('VERIFIED', transcript.challenge_id, transcript.ceremony_nonce,
            'interactive', self.request.input_commitment, transcript.displayed_commitment, True, 0,
            True, True, 0, 0, session.helper_evidence, 1, 2, 1000, None, False)
        self.session = self.owner._approval._active = session
        native_lease = module._NativeEffectApprovalLease(self.owner, self.owner._effect, session, self.context)
        native_lease.helper = session.helper_evidence
        session._lease = self.owner._effect_lease = native_lease
        self.approval_proof = self.owner._effect_proof = module._NativeEffectWitness(
            self.owner._effect, session, self.context, transcript.canonical_wire)

    def lease(self):
        return self.kernel.owned_cpu_execution(self.request.canonical_wire, self.prepared,
            self.binding, self.capture, self.approval_proof, self.context)

    def status(self): return self.kernel.recover_permit(self.prepared, self.context).as_dict()['status']

    def mark_controlled_dispatch(self, lease):
        # Injected domain fact only. No dispatch/native function is invoked.
        lease._dispatch = lease._called = True
        self.binding._target._cpu_version += 1
        self.binding._target._cpu_policy = self.request.target_limit
        self.effect, self.permit = self.request, lease._permit.canonical_wire

    def evidence(self, *, observation=True):
        helper = outcomes.OutcomeTransactionsTests()
        wire = helper.receipt(self)
        observed = helper.observation(self) if observation else None
        proof = object()
        self.proofs[proof] = (self.request.canonical_wire, self.permit, wire,
            None if observed is None else observed.canonical_wire)
        return wire, None if observed is None else observed.canonical_wire, proof

    def close(self):
        session = getattr(self, 'session', None)
        if session is not None: session._closed = True
        store = getattr(self, 'store', None)
        if store is None: return
        store.close()
        FACTS.append(dict(root=str(self.root), sqlite_closed=self.store._closed,
            retained_owner_pending=getattr(self.owner, '_execution', None) is not None,
            capacity_exits=len(self.capacity.exits) if hasattr(self, 'capacity') else 0,
            controlled_capacity_and_native_facts=True,
            capacity_checks=list(self.capacity.calls) if hasattr(self, 'capacity') else []))


class NativeOwnerExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.schema = strict_loads((ROOT / 'contracts/schemas/records.schema.json').read_bytes())

    def fixture(self):
        # Register exact own custody before any constructor can raise.
        f = object.__new__(Fixture)
        self.addCleanup(f.close)
        Fixture.__init__(f, self.schema)
        return f

    def test_missing_capacity_or_provenance_denies_before_consumption(self):
        for field, code in (('_execution_capacity', 'PHYSICAL_CAPACITY_UNAVAILABLE'),
                            ('_execution_provenance', 'PROVENANCE_UNAVAILABLE')):
            f = self.fixture(); setattr(f.owner, field, None)
            with self.assertRaisesRegex(ContractError, code): f.lease().__enter__()
            self.assertEqual(f.status(), 'PREPARED')
            self.assertEqual(f.events, [])

    def test_domain_lease_uses_one_real_store_without_sql_over_yield(self):
        f = self.fixture()
        with f.lease() as lease:
            self.assertEqual(f.status(), 'CONSUMED')
            self.assertEqual(lease._attempt.as_dict()['state'], 'ATTEMPT_COMMITTED')
            self.assertFalse(f.store._connection.in_transaction)
            self.assertIs(f.owner._execution.kernel, f.kernel)
            self.assertIs(f.owner._execution.lease, lease)
        self.assertIsNone(f.owner._execution)
        self.assertEqual(len(f.capacity.exits), 1)
        self.assertEqual(f.events[:2], [('capacity-factory', False), ('capacity-enter', False)])
        self.assertIn(('ATTEMPT', True), f.capacity.calls)

    def test_boolean_capacity_result_is_not_a_success_decision(self):
        for value in (True, False, 0, {}, ''):
            f = self.fixture(); f.capacity.result = value
            with self.assertRaisesRegex(ContractError, 'CAPACITY_DECISION_INVALID'): f.lease().__enter__()
            self.assertEqual(f.status(), 'PREPARED')
            self.assertEqual(len(f.capacity.exits), 1)

    def test_non_view_bound_factories_are_not_production_dependencies(self):
        f = self.fixture(); f.owner._execution_capacity = lambda *args: f.capacity
        with self.assertRaisesRegex(ContractError, 'PHYSICAL_CAPACITY_UNAVAILABLE'): f.lease().__enter__()
        self.assertEqual(f.status(), 'PREPARED')

    def test_equal_but_distinct_capture_context_or_witness_is_denied(self):
        for field, replacement in (('_capture', object()), ('_context', object()), ('_proof', object())):
            f = self.fixture(); lease = f.lease(); setattr(lease, field, replacement)
            with self.assertRaises(ContractError): lease.__enter__()
            self.assertEqual(f.status(), 'PREPARED')

    def test_capacity_refusal_preserves_exact_control_exception(self):
        for kind in (KeyboardInterrupt, SystemExit):
            f = self.fixture(); primary = kind('CONTROLLED capacity refusal'); f.capacity.check_error = primary
            try: f.lease().__enter__()
            except BaseException as actual: self.assertIs(actual, primary)
            else: self.fail('Expected exact primary')
            self.assertEqual(f.status(), 'PREPARED')
            self.assertEqual(len(f.capacity.exits), 1)
            self.assertIs(f.capacity.exits[0][1], primary)

    def test_failed_capacity_entry_retains_uncertain_owner_and_never_exits_it(self):
        f = self.fixture(); primary = KeyboardInterrupt('CONTROLLED entry uncertainty')
        f.capacity.entry_error = primary
        try: f.lease().__enter__()
        except BaseException as actual: self.assertIs(actual, primary)
        else: self.fail('Expected exact primary')
        retained = raw(primary)['native_owner_execution']
        self.assertTrue(retained.pending)
        self.assertIs(f.owner._execution, retained)
        self.assertEqual(f.capacity.exits, [])
        self.assertEqual(f.status(), 'PREPARED')

    def test_simultaneous_body_and_exit_failures_keep_exact_primary_secondary(self):
        f = self.fixture(); primary = KeyboardInterrupt('CONTROLLED body')
        secondary = OSError('CONTROLLED capacity exit refusal'); f.capacity.exit_error = secondary
        try:
            with f.lease(): raise primary
        except BaseException as actual: self.assertIs(actual, primary)
        else: self.fail('Expected primary')
        retained = raw(primary)['native_owner_execution']
        self.assertIs(raw(primary)['native_owner_execution_cleanup_error'], secondary)
        self.assertTrue(retained.pending)
        self.assertIs(retained.cleanup_error, secondary)
        self.assertEqual(len(f.capacity.exits), 1)
        self.assertEqual(f.status(), 'CONSUMED')

    def test_exit_false_is_uncertain_and_a_second_exit_does_not_retry(self):
        f = self.fixture(); f.capacity.exit_result = False
        with self.assertRaisesRegex(ContractError, 'CAPACITY_EXIT_INVALID') as actual:
            with f.lease(): pass
        retained = raw(actual.exception)['native_owner_execution']
        with self.assertRaisesRegex(ContractError, 'EXIT_ONCE_REQUIRED'):
            retained.__exit__(None, None, None)
        self.assertEqual(len(f.capacity.exits), 1)

    def test_foreign_thread_and_copies_cannot_use_the_retained_current_view(self):
        f = self.fixture()
        with f.lease() as lease:
            retained = f.owner._execution
            for copier in (copy.copy, copy.deepcopy):
                with self.assertRaisesRegex(ContractError, 'COPY_FORBIDDEN'): copier(retained)
            errors = []
            def foreign():
                try: retained.require_current('READY', lease._request, lease._permit, lease._attempt,
                    f.binding, f.capture, f.approval_proof, f.control.peer, f.context)
                except BaseException as error: errors.append(error)
            thread = threading.Thread(target=foreign); thread.start(); thread.join(2)
            self.assertFalse(thread.is_alive()); self.assertEqual(len(errors), 1)
            self.assertIn('ORIGINAL_THREAD', str(errors[0]))

    def test_capacity_callback_context_invalidation_is_rechecked_before_return(self):
        f = self.fixture()
        f.capacity.on_check = lambda phase: f.owner._registry._active.pop(f.context, None)
        with self.assertRaisesRegex(ContractError, 'CONTEXT_CHANGED'): f.lease().__enter__()
        self.assertEqual(f.status(), 'PREPARED')

    def test_concurrent_stop_in_capacity_denies_before_consume_and_joins_own_thread(self):
        f = self.fixture(); threads = []
        def stop(phase):
            thread = threading.Thread(target=f.kernel._cpu_execution.cancel)
            threads.append(thread); thread.start(); thread.join(2)
            self.assertFalse(thread.is_alive())
        f.capacity.on_check = stop
        with self.assertRaisesRegex(ContractError, 'STOPPED'): f.lease().__enter__()
        self.assertEqual(f.status(), 'PREPARED'); self.assertEqual(len(threads), 1)

    def test_owner_cancellation_latches_the_same_kernel_final_decision(self):
        f = self.fixture()
        f.capacity.on_check = lambda phase: f.owner.request_stop()
        with self.assertRaisesRegex(ContractError, 'STOPPED'): f.lease().__enter__()
        self.assertTrue(f.kernel._cpu_execution.stopped.is_set())
        self.assertEqual(f.status(), 'PREPARED')

    def test_policy_version_resume_and_code_withdrawal_deny_current_view(self):
        for mutate in (lambda f: setattr(f.binding._target, '_cpu_version', 99),
                       lambda f: setattr(f.clock, '_resume', 99),
                       lambda f: setattr(f.owner._code, '_closed', True)):
            f = self.fixture()
            f.capacity.on_check = lambda phase: mutate(f)
            with self.assertRaises(ContractError): f.lease().__enter__()
            self.assertEqual(f.status(), 'PREPARED')

    def test_changed_cpu_policy_can_record_real_sqlite_outcome_but_cannot_redispatch(self):
        f = self.fixture()
        with f.lease() as lease:
            f.mark_controlled_dispatch(lease)
            receipt, observation, proof = f.evidence()
            result = lease.record_outcome(receipt, observation, proof)
            self.assertEqual(result.as_dict()['state'], 'SETTLED_OBSERVED')
            self.assertIn(('OUTCOME', True), f.capacity.calls)
            with self.assertRaisesRegex(ContractError, 'PHASE_CHANGED'):
                f.owner._execution.require_current('READY', lease._request, lease._permit, lease._attempt,
                    f.binding, f.capture, f.approval_proof, f.control.peer, f.context)
            self.assertEqual(f.status(), 'CONSUMED')

    def test_stop_after_controlled_dispatch_allows_only_bookkeeping_with_frozen_proof(self):
        f = self.fixture()
        with f.lease() as lease:
            f.mark_controlled_dispatch(lease)
            f.owner.request_stop()
            self.assertFalse(f.approval_proof.active)
            receipt, observation, proof = f.evidence(observation=False)
            result = lease.record_outcome(receipt, observation, proof)
            self.assertEqual(result.as_dict()['state'], 'UNCERTAIN')
            with self.assertRaises(ContractError): lease.driver_arguments()

    def test_fabricated_observer_proof_and_boolean_origin_decisions_cannot_commit(self):
        for mode in ('unknown-proof', 'boolean'):
            f = self.fixture()
            with f.lease() as lease:
                f.mark_controlled_dispatch(lease)
                receipt, observation, proof = f.evidence()
                if mode == 'unknown-proof': proof = object()
                else: f.provenance_result = True
                before = f.store.store_position()
                with self.assertRaises(ContractError): lease.record_outcome(receipt, observation, proof)
                self.assertEqual(f.store.store_position(), before)
                self.assertEqual(f.status(), 'CONSUMED')

    def test_native_origin_control_error_remains_exact_and_rolls_back(self):
        f = self.fixture()
        with f.lease() as lease:
            f.mark_controlled_dispatch(lease)
            receipt, observation, proof = f.evidence()
            primary = SystemExit('CONTROLLED provenance refusal'); f.provenance_error = primary
            before = f.store.store_position()
            try: lease.record_outcome(receipt, observation, proof)
            except BaseException as actual: self.assertIs(actual, primary)
            else: self.fail('Expected exact primary')
            self.assertEqual(f.store.store_position(), before)

    def test_final_provenance_callback_cannot_substitute_original_context(self):
        f = self.fixture()
        with f.lease() as lease:
            f.mark_controlled_dispatch(lease)
            receipt, observation, proof = f.evidence()
            f.on_provenance = lambda: f.owner._registry._active.clear()
            before = f.store.store_position()
            with self.assertRaisesRegex(ContractError, 'CONTEXT_CHANGED'):
                lease.record_outcome(receipt, observation, proof)
            self.assertEqual(f.store.store_position(), before)

    def test_default_constructor_captures_absent_capabilities_without_signature_change(self):
        view = SimpleNamespace()
        def base(owner, *args, **kwargs): owner._view = view
        with patch.object(module.NativeOwnerSession, '__init__', base):
            owner = module.NativeCpuOwnerSession('existing-positional', existing_keyword=1)
        self.assertIsNone(owner._execution_capacity)
        self.assertIsNone(owner._execution_provenance)
        self.assertIsNone(owner._execution)

