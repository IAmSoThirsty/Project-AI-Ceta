"""Real canonical admission and capacity adapter; native observations CONTROLLED.

No worker, Hello, AppContainer, profile, native helper, CPU policy effect or live
identity acceptance is supplied. SQLite/kernel/retainer/admission code is real;
the same approved deterministic VFS and peer/capture fixtures supply OS facts.
The canonical store loads its real pinned SQLite runtime on disposable files.
"""
from dataclasses import replace
from pathlib import Path
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ceta.contracts.kernel_transactions import (PeerIdentity, basis_key, budget_key,
    read_budget, ZERO_BUDGET)
from ceta.contracts.local_ipc import LocalMessage
from ceta.contracts.wire import ContractError, canonical_bytes, strict_loads
from ceta.identity import owner_session as owner_module
from ceta.identity.cpu_outcome_capacity import _RetainedCpuOutcomeCapacity
from ceta.identity.owners import WindowsIdentityOwners
from ceta.identity.windows_pipe import (WindowsPeerRegistry, WindowsPeerRegistration,
    _Active, _Registered)
from ceta.kernel.owner_authority import grant_key_for
from ceta.store.outcome_capacity import OutcomeCapacityLease
import test_cpu_capacity_connection as capacity_fixture
import test_native_owner_execution as execution_fixture
import test_owner_authority_transactions as data

ROOT = Path(__file__).resolve().parents[2]
FACTS = []


class Fixture(capacity_fixture.Fixture):
    """Remove the older test's controlled admission; retain the real predicate."""
    def __init__(self, schema):
        super().__init__(schema)
        self.kernel._admission_check = owner_module.NativeCpuOwnerSession.require_admission.__get__(self.owner)
        self.registry = object.__new__(WindowsPeerRegistry)
        self.registry._closed, self.registry._lock = False, threading.RLock()
        registration = WindowsPeerRegistration(101, self.control.peer.principal_id,
            self.control.peer.session_id, frozenset(('kernel.consume',)),
            frozenset((self.request.scope_id,)), 'CONTROLLED-NO-NATIVE-IMAGE', 'a'*64, 100, None)
        self.registration = registration
        now = time.time_ns()//1_000_000
        message = LocalMessage('message:controlled-admission', self.control.peer.session_id,
            'generation:controlled-admission', 'kernel.consume', self.request.scope_id,
            now-1, now+29_000, self.codec.decode(self.prepared), None,
            b'CONTROLLED-ORIGINAL-ENVELOPE-NO-LIVE-IPC')
        self.active = _Active(_Registered(registration, 1, 2, ()), 3,
            threading.get_native_id(), message, (), time.monotonic()+29)
        self.registry._active = {self.context: self.active}
        self.owner._registry = self.view._registry = self.registry
        self.actual_admissions = []

    def current_budget(self):
        key = budget_key(grant_key_for(self.enrollment))
        return read_budget(self.cell(key).value_wire, key)

    def replace_context(self, **changes):
        self.active = replace(self.active, **changes)
        self.registry._active[self.context] = self.active

    def close(self):
        super().close()
        if hasattr(self, 'actual_admissions'):
            FACTS.append(dict(root=str(self.root), admissions=list(self.actual_admissions),
                sqlite_closed=self.store._closed,
                actual_native_calls=0, actual_cpu_effects=0, actual_profile_operations=0))


class NativeOwnerAdmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = strict_loads((ROOT/'contracts/schemas/records.schema.json').read_bytes())

    def fixture(self):
        value = object.__new__(Fixture)
        self.addCleanup(value.close)
        Fixture.__init__(value, self.schema)
        return value

    def watch(self, fixture, callback=None):
        original = owner_module._NativeCpuExecutionRetainer.require_admission
        def require(retained, permit, basis, peer):
            fixture.actual_admissions.append(dict(in_transaction=fixture.store._connection.in_transaction,
                status=permit.as_dict()['status'], consumption_attempted=retained.lease._consumption_attempted,
                consumed_result_available=retained.lease._permit is not None))
            if callback is not None: callback(retained, permit, basis, peer)
            return original(retained, permit, basis, peer)
        return patch.object(owner_module._NativeCpuExecutionRetainer, 'require_admission', require)

    def no_consumption(self, fixture):
        self.assertEqual(fixture.status(), 'PREPARED')
        self.assertEqual(fixture.current_budget()[2:], (fixture.request.operation_budget, ZERO_BUDGET))
        self.assertFalse(fixture.store._connection.in_transaction)
        self.assertIsNone(fixture.kernel._cpu_execution.active)
        self.assertIsNone(fixture.owner._execution)

    def test_real_admission_consumes_and_reserves_attempt_without_dispatch(self):
        f = self.fixture()
        with self.watch(f), f.lease() as execution:
            self.assertEqual(f.status(), 'CONSUMED')
            self.assertEqual(execution._attempt.as_dict()['state'], 'ATTEMPT_COMMITTED')
            self.assertFalse(execution._called)
            self.assertFalse(execution._dispatch)
            self.assertFalse(execution._outcome_capacity.lease.may_have_executed)
            self.assertEqual(f.current_budget()[2:], (ZERO_BUDGET, f.request.operation_budget))
            self.assertIs(execution._outcome_capacity, f.owner._execution.capacity)
        self.assertEqual(len(f.actual_admissions), 5)
        self.assertEqual([row['in_transaction'] for row in f.actual_admissions], [False, True, True, False, False])
        self.assertTrue(all(row['status'] == 'PREPARED' and row['consumption_attempted']
            and not row['consumed_result_available'] for row in f.actual_admissions))
        self.assertIsNone(f.kernel._cpu_execution.active)
        self.assertIsNone(f.store._capacity_active)

    def test_default_owner_and_unretained_native_calls_remain_closed(self):
        f = self.fixture()
        with self.assertRaisesRegex(ContractError, 'PROTECTED_RESOURCE_OWNER_UNAVAILABLE'):
            WindowsIdentityOwners(object()).require_admission(None, b'{}', f.control.peer)
        for call in (lambda: f.owner.require_admission(None, b'{}', f.control.peer),
                lambda: f.kernel.consume(f.prepared, f.context)):
            with self.assertRaisesRegex(ContractError, 'RETAINED_EXECUTION_REQUIRED'): call()
        self.no_consumption(f)

    def test_kernel_captures_concrete_port_and_ignores_instance_allow_substitution(self):
        f = self.fixture()
        f.owner.require_admission = lambda *args: None
        f.replace_context(monotonic_deadline=0.0)
        with self.assertRaisesRegex(ContractError, 'CONTEXT_EXPIRED'): f.lease().__enter__()
        self.no_consumption(f)

    def test_wrong_prepared_permit_basis_or_peer_cannot_borrow_retained_authority(self):
        original = owner_module._NativeCpuExecutionRetainer.require_admission
        for change in ('permit', 'basis', 'peer'):
            with self.subTest(change=change):
                f = self.fixture()
                def wrong(retained, permit, basis, peer):
                    if change == 'permit':
                        value = permit.as_dict(); value['nonce'] = 'nonce:substituted'
                        permit = f.codec.decode(canonical_bytes(value))
                    elif change == 'basis': basis = b'{}'
                    else: peer = PeerIdentity('owner:other', peer.session_id)
                    return original(retained, permit, basis, peer)
                with patch.object(owner_module._NativeCpuExecutionRetainer, 'require_admission', wrong):
                    with self.assertRaisesRegex(ContractError, 'INPUT_CHANGED'): f.lease().__enter__()
                self.no_consumption(f)

    def test_expired_context_envelope_and_wrong_registered_peer_deny(self):
        for change, code in (('deadline', 'CONTEXT_EXPIRED'), ('envelope', 'IPC_MESSAGE_EXPIRED'),
                ('peer', 'ORIGINAL_CONTEXT_REQUIRED'), ('thread', 'ORIGINAL_CONTEXT_REQUIRED'),
                ('operation', 'ORIGINAL_CONTEXT_REQUIRED'), ('scope', 'ORIGINAL_CONTEXT_REQUIRED')):
            with self.subTest(change=change):
                f = self.fixture()
                if change == 'deadline': f.replace_context(monotonic_deadline=0.0)
                elif change == 'envelope':
                    f.replace_context(message=replace(f.active.message, expires_at_ms=1))
                elif change == 'peer':
                    f.replace_context(entry=_Registered(replace(f.registration, principal_id='owner:other'), 1, 2, ()))
                elif change == 'thread': f.replace_context(thread_id=0)
                elif change == 'operation':
                    f.replace_context(entry=_Registered(replace(f.registration, allowed_operations=frozenset()), 1, 2, ()))
                else:
                    f.replace_context(entry=_Registered(replace(f.registration, allowed_scopes=frozenset()), 1, 2, ()))
                with self.assertRaisesRegex(ContractError, code): f.lease().__enter__()
                self.no_consumption(f)

    def test_predicates_do_not_issue_sql_or_repeat_native_observation(self):
        f = self.fixture(); queries, native, active = [], [], [False]
        original = owner_module._NativeCpuExecutionRetainer.require_admission
        def authorizer(*arguments):
            if active[0]: queries.append(arguments)
            return f.store._sqlite.SQLITE_OK
        def admission(retained, permit, basis, peer):
            active[0] = True; before = list(f.native_calls)
            try: return original(retained, permit, basis, peer)
            finally:
                native.append((before, list(f.native_calls)))
                active[0] = False
        f.store._connection.set_authorizer(authorizer)
        with patch.object(owner_module._NativeCpuExecutionRetainer, 'require_admission', admission), f.lease(): pass
        f.store._connection.set_authorizer(None)
        self.assertEqual(queries, [])
        self.assertEqual(len(native), 5)
        self.assertTrue(all(before == after for before, after in native))

    def test_capacity_callback_stop_is_seen_before_consumption(self):
        f = self.fixture(); original = _RetainedCpuOutcomeCapacity.require_current; workers = []
        def check(binding, phase, *arguments):
            result = original(binding, phase, *arguments)
            if phase == 'ADMISSION':
                worker = threading.Thread(target=f.kernel._cpu_execution.cancel)
                workers.append(worker); worker.start(); worker.join(2)
                self.assertFalse(worker.is_alive())
            return result
        with patch.object(_RetainedCpuOutcomeCapacity, 'require_current', check):
            with self.assertRaisesRegex(ContractError, 'STOPPED'): f.lease().__enter__()
        self.no_consumption(f)
        self.assertEqual(len(workers), 1)

    def test_registry_replacement_after_capacity_does_not_reconstruct_context_custody(self):
        f = self.fixture(); original = _RetainedCpuOutcomeCapacity.require_current
        def check(binding, phase, *arguments):
            result = original(binding, phase, *arguments)
            if phase == 'ADMISSION':
                registry = object.__new__(WindowsPeerRegistry)
                registry._closed, registry._lock = False, threading.RLock()
                registry._active = dict(f.registry._active)
                f.owner._registry = f.view._registry = registry
            return result
        with patch.object(_RetainedCpuOutcomeCapacity, 'require_current', check):
            with self.assertRaisesRegex(ContractError, 'OWNER_CHANGED|STORE_CHANGED'): f.lease().__enter__()
        # Retirement validates the original capacity owners and retains custody
        # while they are replaced. Restore this test's exact borrowed registry
        # before explicit no-effect fixture retirement in Fixture.close.
        f.owner._registry = f.view._registry = f.registry
        self.assertEqual(f.status(), 'PREPARED')
        self.assertIsNotNone(f.kernel._cpu_execution.active)

    def test_boolean_capacity_answer_does_not_become_native_admission(self):
        for answer in (True, False):
            with self.subTest(answer=answer):
                f = self.fixture(); original = _RetainedCpuOutcomeCapacity.require_current
                def check(binding, phase, *arguments):
                    result = original(binding, phase, *arguments)
                    return answer if phase == 'ADMISSION' else result
                with patch.object(_RetainedCpuOutcomeCapacity, 'require_current', check):
                    with self.assertRaisesRegex(ContractError, 'CAPACITY_DECISION_INVALID'): f.lease().__enter__()
                self.no_consumption(f)

    def test_owner_closure_at_precommit_denies_without_consumption(self):
        f = self.fixture(); f.fault = lambda: setattr(f.owner, '_closed', True)
        with self.assertRaisesRegex(ContractError, 'CUSTODY_CHANGED|STOPPED'): f.lease().__enter__()
        f.fault = None
        self.no_consumption(f)

    def test_rollback_elapsed_deadline_and_observation_age_are_denied(self):
        original = owner_module._NativeCpuExecutionRetainer.require_admission
        for kind, offset, code in (('rollback', -1, 'TIMER_INVALID'),
                ('deadline', 6_000_000_000, 'DEADLINE_ELAPSED'),
                ('stale', 1_000_000_000, 'OBSERVATION_STALE')):
            with self.subTest(kind=kind):
                effect = data.effect_request
                def request(enrollment, **kwargs):
                    return effect(enrollment, maximum_observation_age_ns=1_000_000_000, **kwargs)
                with patch.object(data, 'effect_request', request): f = self.fixture()
                def check(retained, permit, basis, peer):
                    tick = (retained.admission_last_tick-1 if offset == -1
                        else time.perf_counter_ns()+offset)
                    with patch.object(owner_module.time, 'perf_counter_ns', return_value=tick):
                        return original(retained, permit, basis, peer)
                with patch.object(owner_module._NativeCpuExecutionRetainer, 'require_admission', check):
                    with self.assertRaisesRegex(ContractError, code): f.lease().__enter__()
                self.no_consumption(f)

    def test_last_precommit_clock_callback_stop_rolls_back_consumption(self):
        f = self.fixture(); calls = []
        def clock():
            if f.store._connection.in_transaction:
                calls.append('writer-clock')
                if len(calls) == 2: f.owner.request_stop()
        f.control.on_clock = clock
        with self.assertRaisesRegex(ContractError, 'STOPPED'): f.lease().__enter__()
        self.assertEqual(calls, ['writer-clock', 'writer-clock'])
        f.control.on_clock = None
        self.no_consumption(f)

    def test_postcommit_stop_retains_burned_permit_without_returning_a_lease(self):
        f = self.fixture(); entered = [False]
        f.fault = lambda: entered.__setitem__(0, True)
        def clock():
            if entered[0] and not f.store._connection.in_transaction: f.owner.request_stop()
        f.control.on_clock = clock
        lease = f.lease()
        with self.assertRaisesRegex(ContractError, 'STOPPED'): lease.__enter__()
        f.control.on_clock = f.fault = None
        self.assertEqual(f.status(), 'CONSUMED')
        self.assertEqual(f.current_budget()[2:], (ZERO_BUDGET, f.request.operation_budget))
        self.assertFalse(lease._called)
        self.assertFalse(lease._dispatch)
        self.assertIsNotNone(lease._permit)
        self.assertIsNotNone(lease._consumption)

    def test_transaction_fault_rolls_back_without_replaying_consumption(self):
        f = self.fixture(); primary = KeyboardInterrupt('CONTROLLED admission writer interruption')
        def fail(): raise primary
        f.fault = fail
        try: f.lease().__enter__()
        except BaseException as actual: self.assertIs(actual, primary)
        else: self.fail('Expected exact interruption')
        f.fault = None
        self.no_consumption(f)

    def test_context_invalidation_inside_final_capacity_callback_denies(self):
        f = self.fixture(); original = _RetainedCpuOutcomeCapacity.require_current
        def check(binding, phase, *arguments):
            result = original(binding, phase, *arguments)
            if phase == 'ADMISSION': f.registry._active.pop(f.context, None)
            return result
        with patch.object(_RetainedCpuOutcomeCapacity, 'require_current', check):
            with self.assertRaisesRegex(ContractError, 'CONTEXT_CHANGED'): f.lease().__enter__()
        self.no_consumption(f)

    def test_native_target_change_at_final_clock_denies_before_commit(self):
        f = self.fixture(); calls = []
        def clock():
            if f.store._connection.in_transaction:
                calls.append(1)
                if len(calls) == 2: f.binding._target._cpu_version += 1
        f.control.on_clock = clock
        with self.assertRaisesRegex(ContractError, 'NATIVE_TARGET_CHANGED'): f.lease().__enter__()
        f.control.on_clock = None
        self.no_consumption(f)

    def test_admission_phase_is_not_the_preconsumption_capacity_phase(self):
        f = self.fixture(); original = _RetainedCpuOutcomeCapacity.require_current; seen = []
        def check(binding, phase, *arguments):
            if phase == 'ADMISSION':
                seen.append((binding.execution._consumption_attempted, binding.execution._permit))
                with self.assertRaisesRegex(ContractError, 'PHASE_CHANGED'):
                    original(binding, 'CAPACITY', binding.request, None, binding.context, binding.coordinator)
            return original(binding, phase, *arguments)
        with patch.object(_RetainedCpuOutcomeCapacity, 'require_current', check), f.lease() as lease:
            with self.assertRaisesRegex(ContractError, 'PHASE_CHANGED'):
                original(lease._outcome_capacity, 'ADMISSION', lease._request,
                    f.codec.decode(f.prepared), f.context, f.kernel._cpu_execution)
        self.assertEqual(seen, [(True, None)]*5)

    def test_replacing_captured_predicate_at_final_clock_cannot_remove_final_fence(self):
        f = self.fixture(); calls = []
        def clock():
            if f.store._connection.in_transaction:
                calls.append(1)
                if len(calls) == 2: f.kernel._admission_check = None
        f.control.on_clock = clock
        with self.assertRaisesRegex(ContractError, 'CONSUMING_LEASE_REQUIRED'): f.lease().__enter__()
        f.control.on_clock = None
        self.no_consumption(f)

    def test_a_replayed_permit_never_acquires_another_execution(self):
        f = self.fixture()
        with f.lease(): pass
        with self.assertRaisesRegex(ContractError, 'PREPARATION_CHANGED'): f.lease().__enter__()
        self.assertEqual(f.status(), 'CONSUMED')

    def test_foreign_thread_and_competing_lease_do_not_consume_winner(self):
        f = self.fixture(); failures = []
        original = owner_module._NativeCpuExecutionRetainer.require_admission
        def check(retained, permit, basis, peer):
            if not failures and threading.get_ident() == f.owner._dispatch[1]:
                def compete():
                    try: f.owner.require_admission(permit, basis, peer)
                    except BaseException as error: failures.append(error)
                worker = threading.Thread(target=compete)
                worker.start(); worker.join(2)
                self.assertFalse(worker.is_alive())
            return original(retained, permit, basis, peer)
        with patch.object(owner_module._NativeCpuExecutionRetainer, 'require_admission', check), f.lease() as lease:
            self.assertEqual(len(failures), 1)
            self.assertIn('ORIGINAL_THREAD', str(failures[0]))
            with self.assertRaisesRegex(ContractError, 'STOPPED_OR_BUSY'): f.lease().__enter__()
            self.assertIs(f.kernel._cpu_execution.active, lease)


if __name__ == '__main__': unittest.main()
