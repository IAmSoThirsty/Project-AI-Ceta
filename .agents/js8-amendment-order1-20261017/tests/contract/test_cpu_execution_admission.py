"""Actual SQLite admission; positive native-owner/capacity providers are controlled.

No Hello, profile, production approval, physical capacity guarantee or governed
runtime activation is established by these private object registry fixtures.
"""
import copy
from dataclasses import replace
import json
from pathlib import Path
import pickle
import threading
import time
import unittest
from unittest.mock import patch

from ceta.contracts.kernel_transactions import budget_key, intent_key, read_budget
from ceta.contracts.wire import ContractError
from ceta.effects.native_cpu_binding import CpuDriverArguments
from ceta.kernel.transactions import KernelTransactions
from ceta.supervisor.windows_jobs import WindowsOwnedProcess
import test_owner_authority_transactions as authority
import test_owned_cpu_outcome_transactions as outcomes

ROOT = Path(__file__).resolve().parents[2]
ADMISSION_OBSERVATIONS = []
NATIVE_ADMISSION_RECEIPTS = []


class _FixtureRetirement:
    """Test-custody helper: each non-idempotent native teardown is attempted once."""
    def __init__(self, fixture):
        self.fixture,self.state,self.calls = fixture,'OPEN',0
        self.primary = None

    def __call__(self):
        if self.state == 'RETIRED': return None
        if self.state != 'OPEN':
            raise ContractError('CONTROLLED_FIXTURE_RETIREMENT_UNCERTAIN')
        self.state = 'ATTEMPTED'; self.calls += 1
        try:
            result = self.fixture.tearDown()
            if result is not None: raise ContractError('CONTROLLED_FIXTURE_RETIREMENT_RESPONSE_INVALID')
        except BaseException as primary:
            self.state,self.primary = 'UNCERTAIN',primary
            dict.update(BaseException.__dict__['__dict__'].__get__(primary),
                owned_fixture=self.fixture,fixture_retirement=self)
            raise
        self.state = 'RETIRED'
        return None


class _RefusingExceptionStorage(dict):
    def __init__(self, trap):
        dict.__init__(self, __notes__=[])
        self.trap, self.calls = trap, []

    def _refuse(self, *args, **kwargs):
        self.calls.append('overridable-dictionary-operation')
        raise self.trap

    update = get = __getitem__ = __setitem__ = __contains__ = _refuse


class ControlledBinding:
    def __init__(self, request, target=None):
        self.request = request
        self._target = object.__new__(WindowsOwnedProcess) if target is None else target
        self.capture = object()
        self.calls = []
        self.on_check = None

    def require_current(self, capture, request):
        self.calls.append('current')
        if capture is not self.capture or request.canonical_wire != self.request.canonical_wire:
            raise ContractError('CONTROLLED_BINDING_DENIED')
        if self.on_check is not None: self.on_check()
        return None

    def driver_arguments(self, capture, request):
        self.require_current(capture, request)
        return CpuDriverArguments(request.process_identity,request.expected_limit,
            request.deadline.expires_monotonic_ns,request.maximum_observation_age_ns,
            request.maximum_duration_ns,1,request.input_commitment)


class ControlledRetainer:
    def __init__(self, owners, request, permit, binding, capture, proof, peer, context, coordinator):
        self.owners,self.request,self.permit = owners,request,permit
        self.binding,self.capture,self.proof = binding,capture,proof
        self.peer,self.context,self.coordinator = peer,context,coordinator
        self.locked = False

    def __enter__(self):
        self.owners.execution_lock.acquire(); self.locked = True
        if self.owners.entry_error is not None: raise self.owners.entry_error
        return self

    def require_current(self, phase, request, permit, attempt, binding, capture, proof, peer, context):
        owner = self.owners
        owner.execution_calls.append(phase)
        if owner.on_execution is not None: owner.on_execution(phase)
        if (not self.locked or request.canonical_wire != self.request.canonical_wire
                or binding is not self.binding or capture is not self.capture
                or proof is not self.proof or context is not self.context
                or owner.authenticate(context) != peer or peer != self.peer
                or coordinator_for(owner) is not self.coordinator):
            raise ContractError('CONTROLLED_EXECUTION_BINDING_DENIED')
        if not owner.physical_capacity: raise ContractError('CONTROLLED_PHYSICAL_CAPACITY_UNAVAILABLE')
        if phase == 'CONSUMED':
            owner.outcome_proofs[proof] = ('ATTEMPT',request.canonical_wire,permit.canonical_wire,None,None)
        return owner.execution_return

    def __exit__(self, kind, primary, traceback):
        self.owners.exit_calls += 1
        if self.owners.exit_error is not None: raise self.owners.exit_error
        self.recover_cleanup()
        return self.owners.exit_return

    def recover_cleanup(self):
        # Explicit controlled owner recovery, not replay of kernel dispatch.
        if self.locked:
            self.locked = False; self.owners.execution_lock.release()


def coordinator_for(owner):
    return owner.captured_coordinator


class ControlledExecutionOwners(outcomes.ControlledOutcomeOwners):
    def __init__(self, request):
        super().__init__(request)
        self.execution_proof = object()
        self.execution_calls = []; self.execution_return = None
        self.physical_capacity = True; self.on_execution = None
        self.entry_error = self.exit_error = None
        self.exit_return = None; self.exit_calls = 0
        self.captured_coordinator = None
        self.retain_calls = 0; self.managers = []
        self.execution_lock = threading.RLock()
        self.stop_contexts = {}

    def authenticate(self, context):
        # Original private-context rights; short auth lock is separate from
        # retained execution custody and refuses contention without waiting.
        if not self.lock.acquire(blocking=False):raise ContractError('CONTROLLED_AUTH_BUSY')
        try:
            if context in self.stop_contexts:
                if self.stop_contexts[context]!=threading.get_ident() or not self.current:
                    raise ContractError('CONTROLLED_STOP_CONTEXT_THREAD_REQUIRED')
                return self.peer
            return super().authenticate(context)
        finally:self.lock.release()

    def issue_stop_context(self):
        # Private controlled issuer only; original receiver-thread identity is
        # retained. This is not a production context minting interface.
        if not self.lock.acquire(blocking=False):raise ContractError('CONTROLLED_AUTH_BUSY')
        try:
            context=object();self.stop_contexts[context]=threading.get_ident();return context
        finally:self.lock.release()

    def require_owner_authority_current(self, *args):
        if not self.lock.acquire(blocking=False):raise ContractError('CONTROLLED_AUTH_BUSY')
        try:return super().require_owner_authority_current(*args)
        finally:self.lock.release()

    def require_revocation(self, grant, peer, reason):
        if self.authenticate(self.context)!=peer or reason!='reason:owner-revoke':
            raise ContractError('CONTROLLED_REVOCATION_DENIED')
        return None

    def retain_owned_cpu_execution(self, request, permit, binding, capture, proof, peer, context, coordinator):
        if proof is not self.execution_proof or self.authenticate(context) != peer:
            raise ContractError('CONTROLLED_EXECUTION_PROOF_DENIED')
        if self.captured_coordinator is not None and self.captured_coordinator is not coordinator:
            raise ContractError('CONTROLLED_CROSS_KERNEL_DENIED')
        self.captured_coordinator = coordinator
        self.retain_calls += 1
        manager = ControlledRetainer(self,request,permit,binding,capture,proof,peer,context,coordinator)
        self.managers.append(manager)
        return manager


class CpuExecutionAdmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((ROOT/'contracts/schemas/records.schema.json').read_text())

    def fixture(self, *, reserve=32768, wall_time_ms=5000):
        enrollment = replace(authority.enrollment_request(),
            authority_budget=authority.budget(max_bytes_written=65536),
            recovery_budget=authority.budget(1,wall_time_ms=5000,max_bytes_read=8192,max_bytes_written=32768),
            evidence_reserve_bytes=32768)
        with patch.object(authority,'ControlledOwners',ControlledExecutionOwners), \
                patch.object(authority,'enrollment_request',return_value=enrollment):
            f = authority.Fixture(self.schema)
        self.addCleanup(f.close); f.begin(); f.enroll()
        f.effect = authority.effect_request(f.request,required_outcome_bytes=reserve,
            operation_budget=authority.budget(1,wall_time_ms=wall_time_ms,max_bytes_read=8192,max_bytes_written=reserve))
        f.approve(f.effect); f.proposal = f.allow_basis()
        f.prepared = f.kernel.prepare(f.proposal,f.owners.context).record_wire
        f.binding = ControlledBinding(f.effect)
        return f

    def lease(self, f, **changes):
        values = dict(request_wire=f.effect.canonical_wire,prepared_permit_wire=f.prepared,
            native_binding=f.binding,capture=f.binding.capture,native_proof=f.owners.execution_proof,
            request_context=f.owners.context)
        values.update(changes)
        return f.kernel.owned_cpu_execution(**values)

    def status(self, f):
        return f.kernel.recover_permit(f.prepared,f.owners.context).as_dict()['status']

    def arm_domain_fence(self, lease):
        # Tests the pure final decision, not a public effect or native Set.
        lease._dispatching = True
        self.addCleanup(setattr,lease,'_dispatching',False)
        return lease.dispatch_fence()

    def test_entry_durably_consumes_and_reserves_exact_attempt_without_sql_over_yield(self):
        f = self.fixture()
        with self.lease(f) as lease:
            data = lease.inspection(); self.assertIsNotNone(data['consumption'])
            self.assertEqual(data['attempt'].as_dict()['state'],'ATTEMPT_COMMITTED')
            self.assertFalse(f.store._connection.in_transaction)
            self.assertFalse(data['dispatch_admitted'])
            self.assertEqual(self.status(f),'CONSUMED')
            self.assertEqual(lease.driver_arguments().request_commitment,f.effect.input_commitment)
        self.assertTrue(lease.inspection()['closed']); self.assertEqual(f.owners.exit_calls,1)

    def test_missing_captured_native_owner_denies_before_consumption(self):
        f = self.fixture(); f.kernel._cpu_execution.retain = None
        with self.assertRaisesRegex(ContractError,'NATIVE_OWNER_UNAVAILABLE'): self.lease(f).__enter__()
        self.assertEqual(self.status(f),'PREPARED')

    def test_boolean_owner_and_missing_physical_capacity_deny_before_consumption(self):
        for value in (True,False,0,''):
            with self.subTest(value=value):
                f = self.fixture(); f.owners.execution_return = value
                with self.assertRaisesRegex(ContractError,'OWNER_DECISION_INVALID'): self.lease(f).__enter__()
                self.assertEqual(self.status(f),'PREPARED')
        f = self.fixture(); f.owners.physical_capacity = False
        with self.assertRaisesRegex(ContractError,'PHYSICAL_CAPACITY_UNAVAILABLE'): self.lease(f).__enter__()
        self.assertEqual(self.status(f),'PREPARED')

    def test_wrong_request_capture_proof_and_context_cannot_enter(self):
        for changes in ({'capture':object()},{'native_proof':object()},{'request_context':object()}):
            with self.subTest(changes=list(changes)):
                f = self.fixture()
                with self.assertRaises(ContractError): self.lease(f,**changes).__enter__()
                self.assertEqual(self.status(f),'PREPARED')
        f = self.fixture()
        with self.assertRaisesRegex(ContractError,'REQUEST_BINDING_MISMATCH'):
            self.lease(f,request_wire=replace(f.effect,proposal_id='proposal:other').canonical_wire)

    def test_private_lease_cannot_be_copied_serialized_or_entered_twice(self):
        f = self.fixture(); lease = self.lease(f)
        for function in (copy.copy,copy.deepcopy,pickle.dumps):
            with self.subTest(function=function.__name__):
                with self.assertRaises(ContractError): function(lease)
        with lease: pass
        with self.assertRaisesRegex(ContractError,'SINGLE_USE'): lease.__enter__()
        with self.assertRaises(ContractError): lease.dispatch()

    def test_original_thread_is_required_for_entry_and_continuation(self):
        f = self.fixture(); lease = self.lease(f); failures = []
        def attempt():
            try: lease.__enter__()
            except BaseException as error: failures.append(error)
        thread = threading.Thread(target=attempt); thread.start(); thread.join(2)
        self.assertFalse(thread.is_alive()); self.assertEqual(len(failures),1)
        self.assertEqual(failures[0].code,'CPU_EXECUTION_ORIGINAL_THREAD_REQUIRED')
        with lease:
            thread = threading.Thread(target=lambda: self.record_failure(lease.dispatch_fence,failures))
            thread.start(); thread.join(2); self.assertFalse(thread.is_alive())
        self.assertEqual(failures[-1].code,'CPU_EXECUTION_ORIGINAL_THREAD_REQUIRED')

    @staticmethod
    def record_failure(callback, failures):
        try: callback()
        except BaseException as error: failures.append(error)

    def test_exposed_fence_cannot_be_borrowed_for_an_unbound_dispatch(self):
        f = self.fixture()
        with self.lease(f) as lease:
            with self.assertRaisesRegex(ContractError,'FENCE_NOT_ARMED'): lease.dispatch_fence()
            self.assertFalse(lease.inspection()['dispatch_admitted'])

    def test_stop_during_last_owner_callback_wins_final_domain_admission(self):
        f = self.fixture()
        with self.lease(f) as lease:
            f.owners.on_execution = lambda phase: lease.cancel() if phase == 'DISPATCH' else None
            with self.assertRaisesRegex(ContractError,'STOPPED'): self.arm_domain_fence(lease)
            self.assertFalse(lease.inspection()['dispatch_admitted'])
        self.assertEqual(self.status(f),'CONSUMED')

    def test_stop_in_final_elapsed_callback_wins_after_all_owner_callbacks(self):
        from ceta.kernel import cpu_execution as module
        f = self.fixture()
        with self.lease(f) as lease:
            real = module.time.perf_counter_ns
            checks = [0]
            def elapsed():
                checks[0] += 1
                if checks[0] == 3: lease.cancel()
                return real()
            # Exact total-start/callback-start/final-return endpoints. Native
            # callback occupancy and total canonical audit have separate bounds.
            with patch.object(module.time,'perf_counter_ns',side_effect=elapsed):
                with self.assertRaisesRegex(ContractError,'STOPPED'): self.arm_domain_fence(lease)
            self.assertFalse(lease.inspection()['dispatch_admitted'])

    def test_barrier_stop_does_not_wait_on_held_authority_or_target_lock(self):
        f = self.fixture(); stopped = threading.Event()
        with self.lease(f) as lease:
            def stop(): lease.cancel(); stopped.set()
            thread = threading.Thread(target=stop); thread.start()
            self.assertTrue(stopped.wait(1)); thread.join(1); self.assertFalse(thread.is_alive())
            with self.assertRaisesRegex(ContractError,'STOPPED'): self.arm_domain_fence(lease)

    def test_later_stop_keeps_admitted_attempt_and_consumed_liability(self):
        f = self.fixture()
        with self.lease(f) as lease:
            self.arm_domain_fence(lease); lease.cancel()
            self.assertTrue(lease.inspection()['dispatch_admitted'])
            self.assertEqual(lease.inspection()['native_effect'],'UNESTABLISHED_BY_ADMISSION')
            self.assertEqual(self.status(f),'CONSUMED')
        self.assertEqual(self.status(f),'CONSUMED')

    def test_reentrant_mutation_is_denied_and_stop_latch_remains_observable(self):
        f = self.fixture()
        with self.lease(f) as lease:
            with self.assertRaisesRegex(ContractError,'MUTATION_BUSY'):
                f.kernel.approve_owned_cpu(f.request.request_id,f.effect.canonical_wire,b'',object(),f.owners.context)
            with self.assertRaisesRegex(ContractError,'CONTROL_DURABLE_PENDING'):
                f.kernel.stop_owner_authority(f.request.request_id,f.owners.context,'stop:fixture')
            self.assertTrue(lease.inspection()['stopped'])
            with self.assertRaisesRegex(ContractError,'STOPPED'): self.arm_domain_fence(lease)

    def test_canonical_generation_change_denies_dispatch_without_refund(self):
        f = self.fixture()
        with self.lease(f) as lease:
            f.controlled_control_change(fence_generation=1)
            with self.assertRaises(ContractError): self.arm_domain_fence(lease)
            self.assertFalse(lease.inspection()['dispatch_admitted'])
        self.assertEqual(self.status(f),'CONSUMED')

    def test_consumption_commit_then_throw_keeps_burned_canonical_state(self):
        f = self.fixture(); primary = KeyboardInterrupt('consume-result-lost')
        def after(): f.store.after_commit = None; raise primary
        f.owners.on_execution = lambda phase: setattr(f.store,'after_commit',after) if phase == 'CAPACITY' else None
        lease = self.lease(f)
        with self.assertRaises(KeyboardInterrupt) as raised: lease.__enter__()
        self.assertIs(raised.exception,primary); self.assertIs(primary.owned_cpu_execution,lease)
        self.assertEqual(self.status(f),'CONSUMED'); self.assertFalse(lease.inspection()['dispatch_admitted'])
        self.assertIsNotNone(lease.inspection()['consumption'])
        with self.assertRaises(ContractError): self.lease(f).__enter__()

    def test_attempt_commit_then_throw_retains_durable_attempt_without_reexecution(self):
        f = self.fixture(); primary = SystemExit('attempt-result-lost')
        def after(): f.store.after_commit = None; raise primary
        f.owners.on_execution = lambda phase: setattr(f.store,'after_commit',after) if phase == 'CONSUMED' else None
        lease = self.lease(f)
        with self.assertRaises(SystemExit) as raised: lease.__enter__()
        self.assertIs(raised.exception,primary)
        self.assertEqual(lease.inspection()['attempt'].as_dict()['state'],'ATTEMPT_COMMITTED')
        self.assertFalse(lease.inspection()['dispatch_admitted'])
        self.assertEqual(self.status(f),'CONSUMED')

    def test_failed_entry_and_exit_expose_exact_pending_native_owner(self):
        for during_entry in (True,False):
            with self.subTest(during_entry=during_entry):
                f = self.fixture(); primary = KeyboardInterrupt('primary')
                lease = self.lease(f)
                if during_entry:
                    f.owners.entry_error = primary
                    with self.assertRaises(KeyboardInterrupt) as raised: lease.__enter__()
                else:
                    lease.__enter__(); f.owners.exit_error = OSError('close-refused')
                    raised = None
                    lease.__exit__(KeyboardInterrupt,primary,None)
                self.assertIs(primary.owned_cpu_execution,lease)
                self.assertTrue(lease.inspection()['pending_cleanup'])
                manager = lease.inspection()['entry_manager']
                self.assertIs(manager,f.owners.managers[-1]); self.assertTrue(manager.locked)
                manager.recover_cleanup(); self.assertFalse(manager.locked)
                with self.assertRaises(ContractError): self.lease(f).__enter__()

    def test_primary_with_refused_hooks_keeps_canonical_custody(self):
        class Refusing(KeyboardInterrupt):
            def __setattr__(self,name,value): raise SystemExit('setter-refused')
            @property
            def add_note(self): raise SystemExit('note-getter-refused')
        f = self.fixture(); primary = Refusing('primary'); lease = self.lease(f)
        lease.__enter__(); f.owners.exit_error = OSError('pending')
        lease.__exit__(Refusing,primary,None)
        data = BaseException.__dict__['__dict__'].__get__(primary)
        self.assertIs(data['owned_cpu_execution'],lease)
        self.assertIs(data['owned_process'],f.binding._target)
        self.assertTrue(lease.inspection()['pending_cleanup'])
        f.owners.managers[-1].recover_cleanup()

    def test_copied_driver_arguments_cannot_change_the_retained_original(self):
        f = self.fixture()
        with self.lease(f) as lease:
            returned = lease.driver_arguments()
            object.__setattr__(returned,'deadline_monotonic_ns',1)
            self.assertNotEqual(lease.driver_arguments().deadline_monotonic_ns,1)
            object.__setattr__(lease._native_arguments,'maximum_age_ns',1)
            with self.assertRaisesRegex(ContractError,'ARGUMENTS_CHANGED'): lease.driver_arguments()

    def test_missing_capacity_at_final_check_and_clock_rollback_deny(self):
        f = self.fixture()
        with self.lease(f) as lease:
            f.owners.physical_capacity = False
            with self.assertRaisesRegex(ContractError,'PHYSICAL_CAPACITY_UNAVAILABLE'): self.arm_domain_fence(lease)
        f = self.fixture()
        with self.lease(f) as lease:
            f.owners.samples = (authority.clock(1_000_000_000),authority.clock(1_090_000_000))
            with self.assertRaises(ContractError): self.arm_domain_fence(lease)

    def test_closed_default_runtime_and_historical_attempt_never_create_authority(self):
        f = self.fixture()
        with self.assertRaisesRegex(ContractError,'RUNTIME_AUTHORITY_OWNERS_UNAVAILABLE'):
            f.kernel.require_runtime_admission()
        with self.lease(f): pass
        recovered = f.kernel.recover_permit(f.prepared,f.owners.context)
        with self.assertRaisesRegex(ContractError,'PREPARED_PERMIT_REQUIRED'):
            self.lease(f,prepared_permit_wire=recovered.canonical_wire)
        before = f.store.store_position()
        state = f.kernel.recover_owned_cpu_outcome(f.effect.canonical_wire,recovered.canonical_wire,f.owners.context)
        self.assertEqual(state.as_dict()['state'],'ATTEMPT_COMMITTED')
        self.assertEqual(before,f.store.store_position())

    def test_cross_kernel_retainer_cannot_issue_a_second_authority(self):
        f = self.fixture()
        with self.lease(f): pass
        second = KernelTransactions(f.store,f.codec,authority.INSTALLATION,f.owners)
        with self.assertRaises(ContractError):
            second.owned_cpu_execution(f.effect.canonical_wire,f.prepared,f.binding,f.binding.capture,
                f.owners.execution_proof,f.owners.context).__enter__()

    def test_slow_final_owner_denies_and_elapsed_rollback_does_not_reset(self):
        from ceta.kernel import cpu_execution as module
        f = self.fixture()
        with self.lease(f) as lease:
            f.owners.on_execution = lambda phase: time.sleep(0.06) if phase == 'DISPATCH' else None
            with self.assertRaisesRegex(ContractError,'OWNER_TOO_SLOW'): self.arm_domain_fence(lease)
            f.owners.on_execution = None
            previous = f.kernel._cpu_execution.elapsed_highwater
            with patch.object(module.time,'perf_counter_ns',return_value=previous-1):
                with self.assertRaisesRegex(ContractError,'ELAPSED_INVALID'): self.arm_domain_fence(lease)
            self.assertGreaterEqual(f.kernel._cpu_execution.elapsed_highwater,previous)

    def test_immutable_native_function_capture_and_second_dispatch_denial(self):
        f = self.fixture()
        original = f.binding._target.apply_cpu_rate_limit
        f.binding._target.apply_cpu_rate_limit = lambda *args,**kwargs: None
        with self.assertRaisesRegex(ContractError,'NATIVE_EFFECT_UNAVAILABLE'): self.lease(f).__enter__()
        self.assertEqual(self.status(f),'CONSUMED')
        self.assertFalse(f.kernel._cpu_execution.active)
        # Ambiguous native entry cannot be retried, even if its failure precedes
        # the fence. No actual Windows handle was allocated by this domain case.
        f = self.fixture()
        with self.lease(f) as lease:
            with self.assertRaises(AttributeError): lease.dispatch()
            with self.assertRaisesRegex(ContractError,'SINGLE_DISPATCH'): lease.dispatch()

    def test_pending_exit_never_suppresses_primary_and_closed_cancel_cannot_revive(self):
        f = self.fixture(); lease = self.lease(f)
        with lease: pass
        with self.assertRaisesRegex(ContractError,'NOT_OWNED'): lease.cancel()
        f = self.fixture(); lease = self.lease(f); lease.__enter__()
        f.owners.exit_return = True
        with self.assertRaisesRegex(ContractError,'EXIT_DECISION_INVALID') as raised:
            lease.__exit__(None,None,None)
        self.assertIs(raised.exception.owned_cpu_execution,lease)
        self.assertTrue(lease.inspection()['pending_cleanup'])

    def test_resource_helpers_created_before_and_during_lease_share_mutation_fence(self):
        f = self.fixture()
        old = f.kernel.resource_reservations(f.proposal,f.owners.context)
        with self.lease(f):
            new = f.kernel.resource_reservations(f.proposal,f.owners.context)
            for helper in (old,new):
                for method,args in ((helper.reserve,(object(),)),(helper.cancel,(object(),'reason:test')),
                                    (helper.release,('request:test','reason:test'))):
                    with self.subTest(method=method.__name__):
                        with self.assertRaisesRegex(ContractError,'MUTATION_BUSY'): method(*args)
        # The retained adapter is usable again; original input validation runs.
        with self.assertRaises(ContractError) as raised: old.reserve(object())
        self.assertNotEqual(raised.exception.code,'CPU_EXECUTION_MUTATION_BUSY')

    def test_concurrent_resource_release_is_denied_without_waiting_on_native_owner(self):
        f = self.fixture(); helper = f.kernel.resource_reservations(f.proposal,f.owners.context)
        failures=[]
        with self.lease(f):
            thread=threading.Thread(target=lambda:self.record_failure(lambda:helper.release('request:x','reason:x'),failures))
            thread.start();thread.join(1);self.assertFalse(thread.is_alive())
        self.assertEqual(len(failures),1);self.assertEqual(failures[0].code,'CPU_EXECUTION_MUTATION_BUSY')

    def test_resource_mutation_in_flight_prevents_admission_until_it_has_settled(self):
        from ceta.contracts.resource_management import ReservationRequest,ResourceVector
        f = self.fixture(); helper = f.kernel.resource_reservations(f.proposal,f.owners.context)
        entered,release=threading.Event(),threading.Event();failures=[]
        def blocked(*args):
            entered.set()
            if not release.wait(2):raise AssertionError('resource release timed out')
            raise ContractError('CONTROLLED_RESOURCE_CURRENT_DENIED')
        helper._current=blocked
        request=ReservationRequest('request:resource','budget:resource',0,ResourceVector(0,0,0,0),1,1)
        thread=threading.Thread(target=lambda:self.record_failure(lambda:helper.reserve(request),failures))
        thread.start();self.assertTrue(entered.wait(1))
        try:
            with self.assertRaisesRegex(ContractError,'STOPPED_OR_BUSY'): self.lease(f).__enter__()
            self.assertEqual(self.status(f),'PREPARED')
        finally:
            release.set();thread.join(2)
        self.assertFalse(thread.is_alive());self.assertEqual(failures[0].code,'CONTROLLED_RESOURCE_CURRENT_DENIED')
        with self.lease(f):pass

    def test_second_kernel_and_other_owner_on_same_store_deny_before_blocking_authentication(self):
        for shared_owner in (True,False):
            with self.subTest(shared_owner=shared_owner):
                f = self.fixture()
                other = f.owners if shared_owner else ControlledExecutionOwners(f.request)
                # A new kernel does not inherit the first kernel's issuer/liveness.
                second=KernelTransactions(f.store,f.codec,authority.INSTALLATION,other)
                failures=[]
                with self.lease(f):
                    def attempt():
                        second.owned_cpu_execution(f.effect.canonical_wire,f.prepared,f.binding,f.binding.capture,
                            other.execution_proof,other.context).__enter__()
                    thread=threading.Thread(target=lambda:self.record_failure(attempt,failures))
                    thread.start();thread.join(1);self.assertFalse(thread.is_alive())
                    self.assertEqual(failures[0].code,'CPU_EXECUTION_OTHER_KERNEL_ACTIVE')

    def test_receipt_fixture_retirement_is_once_even_after_close_response_loss(self):
        class Fixture:
            def __init__(self, error=None): self.close_count,self.error = 0,error
            def tearDown(self):
                self.close_count += 1
                if self.error is not None: raise self.error
        good=Fixture();retire=_FixtureRetirement(good)
        retire();retire();self.assertEqual(good.close_count,1);self.assertEqual(retire.state,'RETIRED')
        primary=KeyboardInterrupt('controlled-close-succeeded-response-lost')
        lost=Fixture(primary);retire=_FixtureRetirement(lost)
        with self.assertRaises(KeyboardInterrupt) as raised:retire()
        self.assertIs(raised.exception,primary);self.assertEqual(retire.state,'UNCERTAIN')
        self.assertIs(primary.owned_fixture,lost);self.assertIs(primary.fixture_retirement,retire)
        with self.assertRaisesRegex(ContractError,'RETIREMENT_UNCERTAIN'):retire()
        self.assertEqual(lost.close_count,1);self.assertEqual(retire.calls,1)

    def test_nested_admission_and_recursive_dispatch_cannot_steal_outer_custody(self):
        f=self.fixture()
        with self.lease(f) as lease:
            with self.assertRaisesRegex(ContractError,'STOPPED_OR_BUSY'):self.lease(f).__enter__()
            self.assertIs(f.kernel._cpu_execution.active,lease)
            lease._dispatching=True
            with self.assertRaisesRegex(ContractError,'SINGLE_DISPATCH'):lease.dispatch()
            lease._dispatching=False
            self.assertFalse(lease.inspection()['closed'])


    def test_canonical_intent_expiry_and_equality_deny_even_when_request_is_later(self):
        for delta in (0,1):
            with self.subTest(delta=delta):
                f=self.fixture()
                with self.lease(f) as lease:
                    consumed=f.codec.decode(lease.inspection()['consumed_permit'])
                    metadata=authority.strict_loads(f.cell(intent_key(f.effect.scope_id,consumed.record_id)).value_wire)
                    expiry=metadata['deadline']['expires_monotonic_ns']
                    self.assertLess(expiry,f.effect.deadline.expires_monotonic_ns)
                    f.owners.samples=(authority.clock(1_000_000_000),authority.clock(expiry+delta))
                    with self.assertRaisesRegex(ContractError,'DEADLINE'):self.arm_domain_fence(lease)
                    self.assertFalse(lease.inspection()['dispatch_admitted'])

    def test_overlong_initial_native_retainer_is_measured_and_denied_before_consume(self):
        from ceta.kernel import cpu_execution as module
        f=self.fixture();clock=[module.time.perf_counter_ns()]
        original=f.kernel._cpu_execution.retain
        def now():clock[0]+=1000;return clock[0]
        def overlong(*args):
            clock[0]+=module.MAXIMUM_CHECK_NS+1_000_000
            return original(*args)
        f.kernel._cpu_execution.retain=overlong
        lease=self.lease(f)
        with patch.object(module.time,'perf_counter_ns',side_effect=now):
            try:
                with self.assertRaisesRegex(ContractError,'ENTRY_TOO_SLOW'):lease.__enter__()
            finally:
                if f.kernel._cpu_execution.active is lease and not lease.inspection()['pending_cleanup']:
                    lease.__exit__(None,None,None)
        self.assertEqual(self.status(f),'PREPARED')

    def test_final_callback_cannot_cross_either_canonical_intent_deadline_domain(self):
        from ceta.kernel import cpu_execution as module
        for domain in ('monotonic','wall'):
            with self.subTest(domain=domain):
                f=self.fixture()
                with self.lease(f) as lease:
                    deadline=lease._intent_deadline
                    fresh=authority.clock(deadline.expires_monotonic_ns-1_000_000 if domain=='monotonic' else 1_110_000_000)
                    if domain=='wall': fresh=replace(fresh,wall_time_ns=deadline.expires_wall_ns-1_000_000-fresh.uncertainty_ns)
                    f.owners.samples=(authority.clock(1_000_000_000),fresh)
                    counter=[f.kernel._cpu_execution.elapsed_highwater]
                    def now(): counter[0]+=100; return counter[0]
                    def advance(phase):
                        if phase=='DISPATCH':counter[0]+=1_000_000
                    f.owners.on_execution=advance
                    with patch.object(module.time,'perf_counter_ns',side_effect=now):
                        with self.assertRaisesRegex(ContractError,'DEADLINE_ELAPSED'):self.arm_domain_fence(lease)
                    self.assertFalse(lease.inspection()['dispatch_admitted'])
                self.assertEqual(self.status(f),'CONSUMED')

    def test_cumulative_retained_time_cannot_reset_with_each_fresh_check(self):
        from ceta.kernel import cpu_execution as module
        f=self.fixture()
        with self.lease(f) as lease:
            expired=lease._admission_started+f.effect.operation_budget.values[0]*1_000_000+1
            with patch.object(module.time,'perf_counter_ns',return_value=expired):
                with self.assertRaisesRegex(ContractError,'ADMISSION_WINDOW_EXCEEDED'):self.arm_domain_fence(lease)
            self.assertFalse(lease.inspection()['dispatch_admitted'])
        self.assertEqual(self.status(f),'CONSUMED')

    def test_overlong_manager_entry_retires_exact_retainer_without_consuming(self):
        from ceta.kernel import cpu_execution as module
        f=self.fixture(); counter=[module.time.perf_counter_ns()]
        original=ControlledRetainer.__enter__
        def now():counter[0]+=100;return counter[0]
        def enter(manager):
            value=original(manager);counter[0]+=module.MAXIMUM_CHECK_NS+1_000_000;return value
        with patch.object(module.time,'perf_counter_ns',side_effect=now),patch.object(ControlledRetainer,'__enter__',enter):
            with self.assertRaisesRegex(ContractError,'ENTRY_TOO_SLOW') as raised:self.lease(f).__enter__()
        lease=raised.exception.owned_cpu_execution
        self.assertTrue(lease.inspection()['closed']);self.assertFalse(lease.inspection()['pending_cleanup'])
        self.assertFalse(f.owners.managers[-1].locked);self.assertEqual(f.owners.exit_calls,1)
        self.assertEqual(self.status(f),'PREPARED')


    def test_operation_wall_budget_bounds_total_admission_separately_from_native_duration(self):
        from ceta.kernel import cpu_execution as module
        f=self.fixture(wall_time_ms=5000)
        with self.lease(f) as lease:
            # RC2's maximum_duration_ns bounds a native call/check. The already
            # charged operation wall budget separately bounds total admission.
            after_native_window=lease._admission_started+f.effect.maximum_duration_ns+1_000_000
            with patch.object(module.time,'perf_counter_ns',return_value=after_native_window):
                self.arm_domain_fence(lease)
            self.assertTrue(lease.inspection()['dispatch_admitted'])
        f=self.fixture(wall_time_ms=5000)
        with self.lease(f) as lease:
            after_wall_budget=lease._admission_started+5_000_000_000+1
            with patch.object(module.time,'perf_counter_ns',return_value=after_wall_budget):
                with self.assertRaisesRegex(ContractError,'ADMISSION_WINDOW_EXCEEDED'):self.arm_domain_fence(lease)
            self.assertFalse(lease.inspection()['dispatch_admitted'])


    def test_exact_secondary_cleanup_failure_survives_primary_and_refused_hooks(self):
        class Interrupt(KeyboardInterrupt):
            def __setattr__(self,name,value):raise SystemExit('setter-refused')
            @property
            def add_note(self):raise SystemExit('note-refused')
        for primary in (Interrupt('primary'),SystemExit('primary')):
            with self.subTest(primary_type=type(primary).__name__):
                f=self.fixture();secondary=OSError('retained-owner-exit-refused')
                f.owners.exit_error=secondary;lease=self.lease(f)
                try:
                    with self.assertRaises(BaseException) as raised:
                        with lease:raise primary
                    self.assertIs(raised.exception,primary)
                    data=BaseException.__dict__['__dict__'].__get__(primary)
                    self.assertIs(data.get('owned_cpu_cleanup_failure'),secondary)
                    self.assertIs(lease.inspection().get('cleanup_failure'),secondary)
                    self.assertTrue(lease.inspection()['pending_cleanup'])
                finally:
                    for manager in f.owners.managers:manager.recover_cleanup()

    def test_denied_revocation_has_no_selected_stop_authority(self):
        for active in (False,True):
            with self.subTest(active=active):
                f=self.fixture()
                def denied(*args):raise ContractError('CONTROLLED_REVOCATION_DENIED')
                f.owners.require_revocation=denied
                wire=f.cell(authority.grant_key_for(f.request)).value_wire
                before=f.store.store_position()
                if active:
                    with self.lease(f) as lease:
                        before=f.store.store_position()
                        with self.assertRaises(ContractError):f.kernel.revoke(wire,f.owners.context,'reason:denied')
                        self.assertFalse(lease.inspection()['stopped'])
                        self.assertEqual(before,f.store.store_position())
                        self.arm_domain_fence(lease)
                else:
                    with self.assertRaisesRegex(ContractError,'CONTROLLED_REVOCATION_DENIED'):
                        f.kernel.revoke(wire,f.owners.context,'reason:denied')
                    self.assertFalse(f.kernel._cpu_execution.stopped.is_set())
                    self.assertEqual(before,f.store.store_position())
                    with self.lease(f):pass

    def test_matching_threaded_canonical_stop_and_revoke_cancel_then_complete_durably(self):
        for operation in ('stop_owner_authority','revoke_owner_authority','revoke'):
            with self.subTest(operation=operation):
                f=self.fixture();failures=[]
                target=f.cell(authority.grant_key_for(f.request)).value_wire if operation=='revoke' else f.request.request_id
                reason='reason:owner-revoke' if operation=='revoke' else 'reason:owner-stop'
                with self.lease(f) as lease:
                    before=f.store.store_position()
                    def stop():
                        context=f.owners.issue_stop_context()
                        self.record_failure(lambda:getattr(f.kernel,operation)(target,context,reason),failures)
                    thread=threading.Thread(target=stop)
                    thread.start();thread.join(1);self.assertFalse(thread.is_alive())
                    self.assertEqual(len(failures),1);self.assertEqual(failures[0].code,'CPU_EXECUTION_CONTROL_DURABLE_PENDING')
                    facts=BaseException.__dict__['__dict__'].__get__(failures[0])
                    self.assertIs(facts['owned_cpu_execution'],lease)
                    self.assertTrue(facts['immediate_cancellation']);self.assertFalse(facts['durable_completed'])
                    self.assertFalse(facts['dispatch_already_admitted']);self.assertEqual(before,f.store.store_position())
                    with self.assertRaisesRegex(ContractError,'STOPPED'):self.arm_domain_fence(lease)
                getattr(f.kernel,operation)(target,f.owners.context,reason)
                self.assertEqual(self.status(f),'CONSUMED')
                self.assertEqual(f.codec.decode(f.cell(authority.grant_key_for(f.request)).value_wire).as_dict()['status'],'REVOKED')

    def test_wrong_target_reason_context_and_denied_native_owner_do_not_cancel(self):
        for kind in ('enrollment','grant','reason','context','threadcontext','owner'):
            with self.subTest(kind=kind):
                f=self.fixture()
                with self.lease(f) as lease:
                    before=f.store.store_position()
                    if kind=='owner':f.owners.return_value=True
                    foreign=[]
                    if kind=='threadcontext':
                        thread=threading.Thread(target=lambda:foreign.append(f.owners.issue_stop_context()))
                        thread.start();thread.join(1);self.assertFalse(thread.is_alive())
                    try:
                        with self.assertRaises(ContractError):
                            if kind=='grant':f.kernel.revoke(b'{}',f.owners.context,'reason:owner-revoke')
                            else:f.kernel.stop_owner_authority('enrollment:other' if kind=='enrollment' else f.request.request_id,
                                object() if kind=='context' else (foreign[0] if kind=='threadcontext' else f.owners.context),'' if kind=='reason' else 'reason:owner-stop')
                        self.assertFalse(lease.inspection()['stopped']);self.assertEqual(before,f.store.store_position())
                    finally:f.owners.return_value=None
                    self.arm_domain_fence(lease)

    def test_stop_preflight_refuses_auth_and_store_lock_contention_without_wait(self):
        for kind in ('auth','store'):
            with self.subTest(kind=kind):
                f=self.fixture();entered,release=threading.Event(),threading.Event()
                lock=f.owners.lock if kind=='auth' else f.store._lock
                def holder():
                    with lock:entered.set();release.wait(2)
                with self.lease(f) as lease:
                    thread=threading.Thread(target=holder);thread.start();self.assertTrue(entered.wait(1))
                    try:
                        started=time.perf_counter_ns()
                        with self.assertRaisesRegex(ContractError,'AUTH_BUSY|STOP_STATE_BUSY'):
                            f.kernel.stop_owner_authority(f.request.request_id,f.owners.context,'reason:owner-stop')
                        self.assertLess(time.perf_counter_ns()-started,250_000_000)
                        self.assertFalse(lease.inspection()['stopped'])
                    finally:release.set();thread.join(1)
                    self.assertFalse(thread.is_alive())


    def test_captured_canonical_store_and_stop_lock_cannot_be_replaced(self):
        f=self.fixture();original=f.store._lock
        f.store._lock=object()
        try:
            with self.assertRaisesRegex(ContractError,'STOP_STORE_UNAVAILABLE'):self.lease(f).__enter__()
        finally:f.store._lock=original
        self.assertEqual(self.status(f),'PREPARED')
        with self.lease(f) as lease:
            f.kernel._store=object()
            try:
                with self.assertRaisesRegex(ContractError,'STORE_REPLACED'):self.arm_domain_fence(lease)
            finally:f.kernel._store=f.store
            f.store._lock=object()
            try:
                with self.assertRaisesRegex(ContractError,'STORE_REPLACED'):self.arm_domain_fence(lease)
            finally:f.store._lock=original
            self.assertFalse(lease.inspection()['dispatch_admitted'])


    def test_hostile_exception_dictionary_preserves_entry_exit_primary_and_secondary(self):
        for primary_type in (KeyboardInterrupt, SystemExit):
            for during_entry in (True, False):
                with self.subTest(primary=primary_type.__name__, during_entry=during_entry):
                    f = self.fixture(); primary = primary_type('hostile-dictionary-primary')
                    trap = RuntimeError('overridden-dictionary-hook')
                    storage = _RefusingExceptionStorage(trap)
                    BaseException.__dict__['__dict__'].__set__(primary, storage)
                    secondary = OSError('exact-retained-cleanup-failure')
                    lease = self.lease(f); actual = None
                    try:
                        if during_entry: f.owners.entry_error = primary
                        else: f.owners.exit_error = secondary
                        try:
                            with lease: raise primary
                        except BaseException as failure:
                            actual = failure
                        self.assertIs(actual, primary)
                        self.assertIs(BaseException.__dict__['__dict__'].__get__(primary), storage)
                        self.assertIs(dict.__getitem__(storage, 'owned_cpu_execution'), lease)
                        self.assertIs(dict.__getitem__(storage, 'owned_process'), f.binding._target)
                        self.assertTrue(lease.inspection()['pending_cleanup'])
                        self.assertIs(lease.inspection()['entry_manager'], f.owners.managers[-1])
                        self.assertTrue(f.owners.managers[-1].locked)
                        if not during_entry:
                            self.assertIs(dict.__getitem__(storage, 'owned_cpu_cleanup_failure'), secondary)
                            self.assertIs(lease.inspection()['cleanup_failure'], secondary)
                        self.assertEqual(storage.calls, [])
                        self.assertGreaterEqual(len(dict.__getitem__(storage, '__notes__')), 1)
                    finally:
                        for manager in f.owners.managers: manager.recover_cleanup()
                    self.assertTrue(all(not manager.locked for manager in f.owners.managers))

    def test_hostile_exception_dictionary_keeps_one_shot_fixture_retirement_custody(self):
        for primary_type in (KeyboardInterrupt, SystemExit):
            with self.subTest(primary=primary_type.__name__):
                primary = primary_type('fixture-close-response-lost')
                storage = _RefusingExceptionStorage(RuntimeError('fixture-dictionary-hook'))
                BaseException.__dict__['__dict__'].__set__(primary, storage)
                class Fixture:
                    calls = 0
                    def tearDown(self):
                        self.calls += 1
                        raise primary
                fixture = Fixture(); retire = _FixtureRetirement(fixture)
                with self.assertRaises(BaseException) as raised: retire()
                self.assertIs(raised.exception, primary)
                self.assertIs(dict.__getitem__(storage, 'owned_fixture'), fixture)
                self.assertIs(dict.__getitem__(storage, 'fixture_retirement'), retire)
                self.assertIs(retire.primary, primary)
                self.assertEqual(retire.state, 'UNCERTAIN')
                self.assertEqual(storage.calls, [])
                with self.assertRaisesRegex(ContractError, 'FIXTURE_RETIREMENT_UNCERTAIN'): retire()
                self.assertEqual(fixture.calls, 1); self.assertEqual(retire.calls, 1)


    def test_matching_canonical_stop_before_consumption_cancels_selected_admission(self):
        from ceta.kernel import cpu_execution as cpu_module
        for operation in ('stop_owner_authority','revoke_owner_authority','revoke'):
            with self.subTest(operation=operation):
                # Pure target and actual SQLite; deterministic domain elapsed time.
                value=[cpu_module.time.perf_counter_ns()]
                def tick():value[0]+=1000;return value[0]
                with patch.object(cpu_module.time,'perf_counter_ns',side_effect=tick):
                    f=self.fixture();lease=self.lease(f);stop_errors=[];entry_errors=[]
                    before=f.store.store_position();armed=[]
                    target=f.cell(authority.grant_key_for(f.request)).value_wire if operation=='revoke' else f.request.request_id
                    reason='reason:owner-revoke' if operation=='revoke' else 'reason:owner-stop'
                    def request_stop(phase):
                        if phase!='CAPACITY':return
                        try:getattr(f.kernel,operation)(target,f.owners.context,reason)
                        except BaseException as failure:stop_errors.append(failure)
                    f.owners.on_execution=request_stop
                    try:
                        with lease:
                            self.arm_domain_fence(lease);armed.append(True)
                    except BaseException as failure:entry_errors.append(failure)
                    self.assertEqual([e.code for e in stop_errors],['CPU_EXECUTION_CONTROL_DURABLE_PENDING'])
                    self.assertEqual([e.code for e in entry_errors],['CPU_EXECUTION_STOPPED'])
                    self.assertTrue(lease.inspection()['stopped'])
                    self.assertFalse(lease.inspection()['dispatch_admitted']);self.assertEqual(armed,[])
                    self.assertEqual(self.status(f),'PREPARED');self.assertEqual(f.store.store_position(),before)
                    facts=BaseException.__dict__['__dict__'].__get__(stop_errors[0])
                    self.assertIs(dict.__getitem__(facts,'owned_cpu_execution'),lease)
                    self.assertTrue(dict.__getitem__(facts,'immediate_cancellation'))
                    self.assertFalse(dict.__getitem__(facts,'durable_completed'))
                    self.assertTrue(lease.inspection()['closed'])
                    self.assertFalse(lease.inspection()['pending_cleanup'])
                    self.assertTrue(all(not manager.locked for manager in f.owners.managers))

    def test_denied_preconsumption_stop_cannot_cancel_or_change_prepared_target(self):
        from ceta.kernel import cpu_execution as cpu_module
        for kind in ('target','reason','context','owner'):
            with self.subTest(kind=kind):
                value=[cpu_module.time.perf_counter_ns()]
                def tick():value[0]+=1000;return value[0]
                with patch.object(cpu_module.time,'perf_counter_ns',side_effect=tick):
                    f=self.fixture();errors=[];positions=[]
                    def denied_stop(phase):
                        if phase!='CAPACITY':return
                        before=f.store.store_position()
                        if kind=='owner':f.owners.return_value=True
                        try:
                            f.kernel.stop_owner_authority('enrollment:other' if kind=='target' else f.request.request_id,
                                object() if kind=='context' else f.owners.context,
                                '' if kind=='reason' else 'reason:owner-stop')
                        except BaseException as failure:errors.append(failure)
                        finally:f.owners.return_value=None
                        positions.append(f.store.store_position()==before)
                    f.owners.on_execution=denied_stop
                    with self.lease(f) as lease:
                        self.assertEqual(len(errors),1);self.assertIsInstance(errors[0],ContractError)
                        self.assertEqual(positions,[True]);self.assertFalse(lease.inspection()['stopped'])
                        self.arm_domain_fence(lease)
                    self.assertEqual(self.status(f),'CONSUMED')


class NativeCpuExecutionAdmissionTests(unittest.TestCase):
    """Actual owned Windows job/NC3/CPB1, with controlled canonical approval."""
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((ROOT/'contracts/schemas/records.schema.json').read_text())

    def fixture(self):
        from ceta.identity.native_clock import NativeSessionClock
        from ceta.effects.native_cpu_binding import NativeCpuBinding
        from ceta.contracts.temporal import Deadline
        import test_windows_jobs as jobs
        fixture = jobs.WindowsJobTests(); fixture.setUp()
        retire_fixture_once = _FixtureRetirement(fixture)
        self.addCleanup(retire_fixture_once)
        target,release,_ = fixture.simple()
        clock = NativeSessionClock(7); self.addCleanup(clock.close)
        binding = NativeCpuBinding(target,clock,maximum_capture_ns=500_000_000)
        self.addCleanup(binding.close)
        capture = binding.capture(); now = capture.native_after
        deadline = Deadline(now.boot_id,now.durable_epoch,now.resume_generation,
            now.monotonic_ns,now.monotonic_ns+60_000_000_000,now.earliest_wall_ns,now.latest_wall_ns+60_000_000_000)
        enrollment = replace(authority.enrollment_request(),clock_session_nonce=clock._session,
            worker_image_commitment=target.resource_identity.image_digest,deadline=deadline,
            authority_budget=authority.budget(max_bytes_written=65536),
            recovery_budget=authority.budget(1,wall_time_ms=5000,max_bytes_read=8192,max_bytes_written=32768),
            evidence_reserve_bytes=32768)
        with patch.object(authority,'ControlledOwners',ControlledExecutionOwners), \
                patch.object(authority,'enrollment_request',return_value=enrollment):
            f = authority.Fixture(self.schema)
        self.addCleanup(f.close)
        # Retain the actual pre-ceremony anchor, as OS1's consent owner does;
        # repeatedly sampled native "previous" must not erase that anchor.
        f.owners.on_clock = lambda: setattr(f.owners,'samples',(now,clock.clock()[1]))
        f.begin()
        transcript = replace(authority.enrollment_transcript(enrollment),observed_clock=clock.clock()[1])
        proof = f.owners.proof('ENROLL',None,transcript)
        f.kernel.enroll_owner(enrollment.canonical_wire,authority.enrollment_transcript_bytes(transcript),proof,f.owners.context)
        f.effect = replace(authority.effect_request(enrollment),process_identity=capture.observation.identity,
            job_digest=capture.observation.job_digest,expected_limit=capture.observation,
            original_limit=capture.observation.limit,required_outcome_bytes=32768,
            operation_budget=authority.budget(1,wall_time_ms=5000,max_bytes_read=8192,max_bytes_written=32768))
        f.binding,f.clock,f.target,f.fixture,f.capture = binding,clock,target,fixture,capture
        f.retire_fixture = retire_fixture_once
        self.approve(f,f.effect)
        return f

    def approve(self, f, request):
        transcript = replace(authority.effect_transcript(f.request,request),observed_clock=f.clock.clock()[1])
        f.approve(request,transcript=transcript)
        proposal = f.allow_basis('cap_approval' if request.operation == 'owned-worker.cpu-cap' else 'restore_approval')
        f.prepared = f.kernel.prepare(proposal,f.owners.context).record_wire

    def lease(self, f):
        return f.kernel.owned_cpu_execution(f.effect.canonical_wire,f.prepared,f.binding,
            f.capture,f.owners.execution_proof,f.owners.context)

    def retain_receipt(self, f, **facts):
        self.addCleanup(self.observe_retired,f,facts)

    def observe_retired(self, f, facts):
        f.binding.close(); f.clock.close(); f.retire_fixture()
        row=dict(test_id=self.id(),pid=f.target.pid,creation=f.target.creation_time,
            image=f.target.resource_identity.image_digest,process_closed=f.target._process is None,
            thread_closed=f.target._thread is None,job_closed=f.target._job is None,
            lifetime_closed=f.target.lifetime_closed,clock_state=f.clock.status().state,
            clock_sampler_alive=f.clock.status().sampler_alive,
            fixture_retirement_state=f.retire_fixture.state,fixture_teardown_calls=f.retire_fixture.calls,
            qualification='Actual native owned workload/CPU enforcement; owner approval and physical outcome capacity are controlled.',**facts)
        NATIVE_ADMISSION_RECEIPTS.append(row)
        self.assertTrue(row['lifetime_closed'] and row['process_closed'] and row['thread_closed'] and row['job_closed'])
        self.assertEqual(row['clock_state'],'CLOSED'); self.assertFalse(row['clock_sampler_alive'])
        self.assertEqual(row['fixture_retirement_state'],'RETIRED');self.assertEqual(row['fixture_teardown_calls'],1)

    def test_actual_kernel_retained_apply_then_separate_approved_restore(self):
        from ceta.contracts.real_effect import RESTORE_OPERATION
        f = self.fixture(); cap = f.effect
        with self.lease(f) as lease:
            self.assertFalse(f.store._connection.in_transaction)
            applied = lease.dispatch(); self.assertEqual(applied.state,'APPLIED')
            self.assertTrue(lease.inspection()['dispatch_admitted'])
            with self.assertRaisesRegex(ContractError,'SINGLE_DISPATCH'): lease.dispatch()
            f.permit = lease.inspection()['consumed_permit']
            receipt = outcomes.OutcomeTransactionsTests.receipt(self,f)
            observation = replace(outcomes.OutcomeTransactionsTests.observation(self,f),clock=f.clock.clock()[1])
            proof = f.owners.native_proof('OUTCOME',f.effect,f.permit,receipt,observation)
            self.assertEqual(lease.record_outcome(receipt,observation.canonical_wire,proof).as_dict()['state'],
                'SETTLED_OBSERVED')
        f.capture = f.binding.capture()
        f.effect = replace(authority.effect_request(f.request,restore=cap),
            process_identity=f.capture.observation.identity,job_digest=f.capture.observation.job_digest,
            expected_limit=f.capture.observation,original_limit=cap.original_limit,
            required_outcome_bytes=32768,
            operation_budget=authority.budget(1,wall_time_ms=5000,max_bytes_read=8192,max_bytes_written=32768))
        self.assertEqual(f.effect.operation,RESTORE_OPERATION); self.approve(f,f.effect)
        with self.lease(f) as restore:
            restored = restore.dispatch(); self.assertEqual(restored.state,'RESTORED')
        self.assertEqual(f.target.cpu_rate_observation(f.target.resource_identity).limit,cap.original_limit)
        self.retain_receipt(f,applied=applied.state,restored=restored.state,
            restored_flags=cap.original_limit.control_flags,restored_value=cap.original_limit.value,
            canonical_settlement_proof='CONTROLLED, not an actual independent observer')

    def test_actual_last_owner_stop_denies_every_native_set(self):
        f = self.fixture(); calls=[]; original=f.target._api.SetInformationJobObject
        def setter(job,kind,*args):
            if kind==15:calls.append(kind)
            return original(job,kind,*args)
        f.target._api.SetInformationJobObject=setter
        before=f.target.cpu_rate_observation(f.target.resource_identity)
        with self.lease(f) as lease:
            f.owners.on_execution=lambda phase: lease.cancel() if phase=='DISPATCH' else None
            with self.assertRaisesRegex(ContractError,'STOPPED'): lease.dispatch()
            self.assertFalse(lease.inspection()['dispatch_admitted'])
        after=f.target.cpu_rate_observation(f.target.resource_identity)
        self.assertEqual(calls,[]); self.assertEqual(after.limit,before.limit); self.assertEqual(after.version,before.version)
        self.retain_receipt(f,class15_calls=calls,before_flags=before.limit.control_flags,after_flags=after.limit.control_flags)

    def test_actual_set_then_primary_exception_burns_attempt_and_preserves_recovery(self):
        f = self.fixture(); primary=KeyboardInterrupt('actual-set-return-lost'); calls=[]
        real=f.target._api.SetInformationJobObject
        def setter(job,kind,*args):
            result=real(job,kind,*args)
            if kind==15:
                calls.append(kind); raise primary
            return result
        f.target._api.SetInformationJobObject=setter
        with self.lease(f) as lease:
            with self.assertRaises(KeyboardInterrupt) as raised: lease.dispatch()
            self.assertIs(raised.exception,primary); self.assertIs(primary.owned_cpu_execution,lease)
            self.assertTrue(lease.inspection()['dispatch_admitted'])
            self.assertEqual(lease.inspection()['native_change'].state,'UNCERTAIN')
            with self.assertRaisesRegex(ContractError,'SINGLE_DISPATCH'): lease.dispatch()
        f.target._api.SetInformationJobObject=real
        reconciled=f.target.reconcile_cpu_rate_limit(f.target.resource_identity)
        self.assertEqual(reconciled.state,'APPLIED'); self.assertEqual(calls,[15])
        expected=f.target.cpu_rate_observation(f.target.resource_identity)
        # Explicit authorized disposable-fixture cleanup via the library. This
        # is not authority revival or a canonical governed restoration claim.
        restored=f.target.restore_cpu_rate_limit('fixture:restore-after-lost-return',f.effect.request_id,
            f.target.resource_identity,expected,f.effect.original_limit,
            deadline_monotonic_ns=time.monotonic_ns()+1_000_000_000)
        self.assertEqual(restored.state,'RESTORED')
        self.retain_receipt(f,actual_set_calls=1,primary_identity=True,after_ambiguity='UNCERTAIN',
            reconciliation=reconciled.state,fixture_cleanup_restoration=restored.state)


    def test_actual_matching_threaded_stop_wins_last_owner_barrier_before_set(self):
        f=self.fixture();calls=[];failures=[];entered,done=threading.Event(),threading.Event()
        real=f.target._api.SetInformationJobObject
        def setter(job,kind,*args):
            if kind==15:calls.append(kind)
            return real(job,kind,*args)
        f.target._api.SetInformationJobObject=setter
        with self.lease(f) as lease:
            before=f.store.store_position()
            def stop():
                if not entered.wait(2):failures.append(AssertionError('dispatch callback not entered'));return
                try:f.kernel.stop_owner_authority(f.request.request_id,f.owners.issue_stop_context(),'reason:owner-stop')
                except BaseException as error:failures.append(error)
                finally:done.set()
            original_clock=f.owners.on_clock;receiver=threading.get_ident()
            def clock_barrier():
                original_clock()  # Real native QPC clock; no injected timing.
                if threading.get_ident()==receiver:
                    entered.set()
                    if not done.wait(1):raise AssertionError('canonical Stop blocked behind retained execution')
            thread=threading.Thread(target=stop);thread.start();f.owners.on_clock=clock_barrier
            try:
                with self.assertRaisesRegex(ContractError,'STOPPED'):lease.dispatch()
            finally:entered.set();thread.join(2);f.owners.on_clock=original_clock
            self.assertFalse(thread.is_alive());self.assertEqual(failures[0].code,'CPU_EXECUTION_CONTROL_DURABLE_PENDING')
            self.assertEqual(calls,[]);self.assertEqual(before,f.store.store_position())
        f.kernel.stop_owner_authority(f.request.request_id,f.owners.context,'reason:owner-stop')
        self.retain_receipt(f,class15_calls=calls,canonical_stop='DURABLE_COMPLETED_AFTER_LEASE_RELEASE',
            stop_before_admission=True,genuine_owner_approval=False,
            stop_preflight_elapsed_ns=BaseException.__dict__['__dict__'].__get__(failures[0])['stop_preflight_elapsed_ns'])

    def test_actual_canonical_revocation_after_dispatch_keeps_effect_and_consumed_liability(self):
        f=self.fixture();failures=[]
        wire=f.cell(authority.grant_key_for(f.request)).value_wire
        with self.lease(f) as lease:
            applied=lease.dispatch();self.assertEqual(applied.state,'APPLIED')
            before=f.store.store_position()
            def stop():
                try:f.kernel.revoke(wire,f.owners.issue_stop_context(),'reason:owner-revoke')
                except BaseException as error:failures.append(error)
            thread=threading.Thread(target=stop);thread.start();thread.join(1);self.assertFalse(thread.is_alive())
            self.assertEqual(failures[0].code,'CPU_EXECUTION_CONTROL_DURABLE_PENDING')
            data=BaseException.__dict__['__dict__'].__get__(failures[0])
            self.assertTrue(data['dispatch_already_admitted']);self.assertEqual(before,f.store.store_position())
            self.assertEqual(f.target.cpu_rate_observation(f.target.resource_identity).limit,f.effect.target_limit)
        f.kernel.revoke(wire,f.owners.context,'reason:owner-revoke')
        self.assertEqual(f.kernel.recover_permit(f.prepared,f.owners.context).as_dict()['status'],'CONSUMED')
        expected=f.target.cpu_rate_observation(f.target.resource_identity)
        restored=f.target.restore_cpu_rate_limit('fixture:restore-after-authorized-stop',f.effect.request_id,
            f.target.resource_identity,expected,f.effect.original_limit,
            deadline_monotonic_ns=time.monotonic_ns()+1_000_000_000)
        self.assertEqual(restored.state,'RESTORED')
        self.retain_receipt(f,after_dispatch_cancellation=True,canonical_revocation='DURABLE_COMPLETED',
            consumed_liability_preserved=True,fixture_cleanup_restoration='RESTORED',
            stop_preflight_elapsed_ns=data['stop_preflight_elapsed_ns'])

    def test_actual_set_with_hostile_exception_dictionary_retains_exact_change_and_primary(self):
        for primary_type in (KeyboardInterrupt, SystemExit):
            with self.subTest(primary=primary_type.__name__):
                f = self.fixture(); primary = primary_type('actual-native-return-lost')
                storage = _RefusingExceptionStorage(RuntimeError('native-dictionary-hook'))
                BaseException.__dict__['__dict__'].__set__(primary, storage)
                calls = []; real = f.target._api.SetInformationJobObject
                def setter(job, kind, *args):
                    result = real(job, kind, *args)
                    if kind == 15:
                        calls.append(kind); raise primary
                    return result
                f.target._api.SetInformationJobObject = setter
                actual = None; lease = self.lease(f); snapshot = None
                try:
                    with lease:
                        try: lease.dispatch()
                        except BaseException as failure: actual = failure
                        snapshot = lease.inspection()
                        with self.assertRaisesRegex(ContractError, 'SINGLE_DISPATCH'): lease.dispatch()
                finally:
                    f.target._api.SetInformationJobObject = real
                    if calls:
                        reconciled = f.target.reconcile_cpu_rate_limit(f.target.resource_identity)
                        self.assertEqual(reconciled.state, 'APPLIED')
                        expected = f.target.cpu_rate_observation(f.target.resource_identity)
                        restored = f.target.restore_cpu_rate_limit('fixture:hostile-dict-restoration',
                            f.effect.request_id, f.target.resource_identity, expected, f.effect.original_limit,
                            deadline_monotonic_ns=time.monotonic_ns()+1_000_000_000)
                        self.assertEqual(restored.state, 'RESTORED')
                        reconciliation, restoration = reconciled.state, restored.state
                    else:
                        reconciliation, restoration = 'NO_NATIVE_SET', 'UNCHANGED'
                    self.assertEqual(f.target.cpu_rate_observation(f.target.resource_identity).limit,
                        f.effect.original_limit)
                    self.retain_receipt(f, actual_set_calls=len(calls), primary_type=primary_type.__name__,
                        primary_identity=actual is primary, overridden_dictionary_calls=len(storage.calls),
                        reconciliation=reconciliation, fixture_cleanup_restoration=restoration)
                self.assertIs(actual, primary)
                self.assertIs(dict.__getitem__(storage, 'owned_cpu_execution'), lease)
                self.assertIs(dict.__getitem__(storage, 'owned_process'), f.target)
                self.assertEqual(storage.calls, [])
                self.assertTrue(snapshot['dispatch_admitted'])
                self.assertEqual(snapshot['native_change'].state, 'UNCERTAIN')
                self.assertIs(snapshot['native_change'], dict.__getitem__(storage, 'cpu_rate_change'))
                self.assertEqual(calls, [15])

    def test_actual_canonical_stop_during_capacity_keeps_prepared_permit_and_zero_set(self):
        f=self.fixture();calls=[];stop_errors=[];real=f.target._api.SetInformationJobObject
        def setter(job,kind,*args):
            if kind==15:calls.append(kind)
            return real(job,kind,*args)
        f.target._api.SetInformationJobObject=setter
        before=f.target.cpu_rate_observation(f.target.resource_identity);lease=self.lease(f)
        def request_stop(phase):
            if phase!='CAPACITY':return
            try:f.kernel.stop_owner_authority(f.request.request_id,f.owners.context,'reason:owner-stop')
            except BaseException as failure:stop_errors.append(failure)
        f.owners.on_execution=request_stop
        try:
            with self.assertRaisesRegex(ContractError,'CPU_EXECUTION_STOPPED'):lease.__enter__()
        finally:
            f.target._api.SetInformationJobObject=real
            self.retain_receipt(f,class15_calls=list(calls),stop_codes=[getattr(e,'code',None) for e in stop_errors],
                controlled_canonical_Stop=True,preconsumption=True)
        self.assertEqual([e.code for e in stop_errors],['CPU_EXECUTION_CONTROL_DURABLE_PENDING'])
        self.assertEqual(calls,[]);self.assertTrue(lease.inspection()['stopped'])
        self.assertFalse(lease.inspection()['dispatch_admitted'])
        self.assertEqual(f.kernel.recover_permit(f.prepared,f.owners.context).as_dict()['status'],'PREPARED')
        after=f.target.cpu_rate_observation(f.target.resource_identity)
        self.assertEqual(after.limit,before.limit);self.assertEqual(after.version,before.version)
        self.assertTrue(lease.inspection()['closed']);self.assertFalse(lease.inspection()['pending_cleanup'])
