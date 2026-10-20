"""RE-T27 wiring: real kernel/journal/lease, explicitly controlled OS origins.

Default cases use the approved deterministic VFS-state fixture. The separately
selected native cases use the pinned VFS and real disposable Windows files.
Neither cohort starts a process, invokes Hello, or executes native CPU Set.
The approved owner fixture's authentication/producer/provenance are CONTROLLED.
"""
import copy
from dataclasses import replace
import os
from pathlib import Path
import pickle
from types import SimpleNamespace
import threading
import unittest
from unittest.mock import patch

from ceta.contracts.wire import ContractError, strict_loads
from ceta.identity.native_owner_view import NativeOwnerView
from ceta.identity.cpu_outcome_capacity import _RetainedCpuOutcomeCapacity
from ceta.kernel import cpu_execution
from ceta.store.journal import SqliteJournal
from ceta.store import outcome_capacity as capacity
import test_native_owner_execution as owner_fixture
import test_native_owner_preparation as preparation
import test_cpu_execution_admission as admission
from test_outcome_capacity import ControlledFunctions

ROOT = Path(__file__).resolve().parents[2]
FACTS = []


class Fixture(owner_fixture.Fixture):
    """Reuse approved controlled owner facts; use the real capacity adapter."""
    def __init__(self, schema, runtime=None):
        if runtime is None:
            super().__init__(schema)
            self.native = ControlledFunctions()
            functions = {name: self.native.method(name) for name in ('reserve', 'state', 'measure', 'release')}
            functions['destroy'] = lambda token: 0  # No registration exists in this controlled fixture.
            self.store._capacity_vfs = capacity._CapacityVfs(SimpleNamespace(_functions=functions), 'controlled_connection', 1)
        else:
            original = preparation.SqliteJournal
            def create(*args, **kwargs):
                return original(*args, **kwargs, outcome_runtime=runtime)
            with patch.object(preparation, 'SqliteJournal', create):
                super().__init__(schema)
            self.native = None
        self.native_runtime = runtime
        self.view._outcome_budget = capacity.OutcomeCapacityBudget(8*1024*1024, 8*1024*1024, 65536, 32768)
        self.owner._execution_capacity = NativeOwnerView.retain_owned_cpu_outcome_capacity.__get__(self.view)
        self.original_controlled_capacity = self.capacity
        self.commit_calls = []

    def fence(self, lease):
        # Controlled driver invocation of the actual kernel dispatch fence.
        # No Windows effect method is invoked, and no native success is claimed.
        lease._called = lease._dispatching = True
        try: lease.dispatch_fence()
        finally: lease._dispatching = False
        self.mark_controlled_dispatch(lease)

    def capture_commit(self):
        original = SqliteJournal.commit
        def commit(journal, expected, entries, **keywords):
            if journal is self.store and journal._capacity_active is not None:
                held = journal._capacity_active
                self.commit_calls.append(dict(entries=entries, staged=held.retained_payloads(),
                    may_have_executed=held.may_have_executed, durable_before=held.durable,
                    expected=expected, keywords=keywords))
            return original(journal, expected, entries, **keywords)
        return patch.object(SqliteJournal, 'commit', commit)

    def close(self):
        store = getattr(self, 'store', None)
        if store is None: return
        held = getattr(store, '_capacity_active', None)
        row = dict(root=str(self.root), controlled_owner_provenance=True,
            native_CPU_Set_calls=0, physical_VFS=getattr(self, 'native_runtime', None) is not None)
        if held is not None:
            row.update(before_fixture_retirement=dict(state=held.state, durable=held.durable,
                may_have_executed=held.may_have_executed,
                retained_lengths=[len(wire) for wire in held.retained_payloads()]))
            # This fixture invoked no Set. Explicitly retire only its exact
            # reservation; never label this fixture disposal as reconciliation.
            held._release()
            row['explicit_no_effect_fixture_retirement'] = True
        session = getattr(self, 'session', None)
        if session is not None: session._closed = True
        coordinator = getattr(getattr(self, 'kernel', None), '_cpu_execution', None)
        if coordinator is not None and coordinator.active is not None:
            row['fixture_liveness_release'] = True
            coordinator.release_liveness(coordinator.active)
        store.close()
        row.update(sqlite_closed=store._closed, connection_state=store._connection_close_state,
            vfs_closed=store._capacity_vfs is None or store._capacity_vfs.closed)
        FACTS.append(row)


class CapacityConnectionTests(unittest.TestCase):
    runtime = None

    @classmethod
    def setUpClass(cls):
        cls.schema = strict_loads((ROOT/'contracts/schemas/records.schema.json').read_bytes())

    def fixture(self):
        value = object.__new__(Fixture)
        self.addCleanup(value.close)
        Fixture.__init__(value, self.schema, self.runtime)
        return value

    def test_capacity_reserved_before_consume_and_attempt_with_same_writer(self):
        f = self.fixture()
        with f.capture_commit(), f.lease() as execution:
            binding = execution._outcome_capacity
            self.assertIs(type(binding), _RetainedCpuOutcomeCapacity)
            self.assertIs(binding.journal, f.store)
            self.assertIs(f.store._capacity_active, binding.lease)
            self.assertIs(binding.context, f.context)
            self.assertFalse(f.store._connection.in_transaction)
            self.assertEqual(f.status(), 'CONSUMED')
            self.assertEqual(execution._attempt.as_dict()['state'], 'ATTEMPT_COMMITTED')
            self.assertGreaterEqual(len(f.commit_calls), 2)
            self.assertTrue(all(row['staged'] == () and not row['may_have_executed'] for row in f.commit_calls))
            self.assertEqual(binding.lease.budget.memory_bytes, f.request.required_outcome_bytes)
        self.assertIsNone(f.store._capacity_active)
        self.assertEqual(binding.lease.state, 'CLOSED')

    def test_exact_final_outcome_payloads_are_staged_before_real_commit(self):
        f = self.fixture()
        with f.lease() as execution:
            binding = execution._outcome_capacity
            f.fence(execution)
            self.assertTrue(binding.lease.may_have_executed)
            with f.capture_commit():
                result = execution.record_outcome(*f.evidence())
            self.assertEqual(result.as_dict()['state'], 'SETTLED_OBSERVED')
            row = f.commit_calls[-1]
            self.assertEqual(row['staged'], tuple(entry.payload_wire for entry in row['entries']))
            self.assertTrue(row['may_have_executed'])
            self.assertFalse(row['durable_before'])
            self.assertTrue(binding.lease.durable)
            self.assertIsNotNone(binding.lease.commit)
            self.assertEqual(binding.lease.retained_payloads(), row['staged'])
        self.assertEqual(binding.lease.state, 'CLOSED')
        self.assertIsNone(f.store._capacity_active)

    def test_exact_outcome_retry_keeps_same_commit_and_slot(self):
        f = self.fixture()
        with f.lease() as execution:
            f.fence(execution)
            evidence = f.evidence(observation=False)
            first = execution.record_outcome(*evidence)
            position = f.store.store_position()
            payloads = execution._outcome_capacity.lease.retained_payloads()
            second = execution.record_outcome(*evidence)
            self.assertEqual(first, second)
            self.assertEqual(f.store.store_position(), position)
            self.assertEqual(execution._outcome_capacity.lease.retained_payloads(), payloads)

    def test_advancing_reconciliation_needs_a_new_qualified_reservation(self):
        f = self.fixture()
        with f.lease() as execution:
            f.fence(execution)
            receipt, absent, proof = f.evidence(observation=False)
            first = execution.record_outcome(receipt, absent, proof)
            self.assertEqual(first.as_dict()['state'], 'UNCERTAIN')
            position = f.store.store_position()
            payloads = execution._outcome_capacity.lease.retained_payloads()
            observed = owner_fixture.outcomes.OutcomeTransactionsTests().observation(f)
            next_proof = object()
            f.proofs[next_proof] = (f.request.canonical_wire, f.permit, receipt, observed.canonical_wire)
            with self.assertRaisesRegex(ContractError, 'RECONCILIATION_RESERVATION_REQUIRED'):
                execution.record_outcome(receipt, observed.canonical_wire, next_proof)
            self.assertEqual(f.store.store_position(), position)
            self.assertEqual(execution._outcome_capacity.lease.retained_payloads(), payloads)
            self.assertTrue(execution._outcome_capacity.lease.durable)

    def test_failed_commit_keeps_exact_primary_slot_and_journal_custody(self):
        f = self.fixture()
        primary = KeyboardInterrupt('controlled rollback after final staging')
        def fail(): raise primary
        with self.assertRaises(KeyboardInterrupt) as caught:
            with f.lease() as execution:
                f.fence(execution)
                binding = execution._outcome_capacity
                f.fault = fail
                with f.capture_commit(): execution.record_outcome(*f.evidence())
        f.fault = None
        self.assertIs(caught.exception, primary)
        self.assertIs(primary.owned_cpu_capacity, binding)
        self.assertIs(primary.outcome_capacity_custody, binding.lease)
        self.assertIs(f.store._capacity_active, binding.lease)
        self.assertEqual(binding.lease.state, 'PENDING')
        self.assertFalse(binding.lease.durable)
        self.assertEqual(binding.lease.retained_payloads(), f.commit_calls[-1]['staged'])
        self.assertTrue(binding.lease.retained_payloads())
        self.assertFalse(f.store._connection.in_transaction)
        with self.assertRaisesRegex(ContractError, 'CAPACITY_RETAINED'): f.store.close()

    def test_missing_configuration_and_short_memory_deny_before_consumption(self):
        for budget, code in ((None, 'CONFIGURATION_REQUIRED'),
                (capacity.OutcomeCapacityBudget(65536,65536,65536,4096), 'FULL_OUTCOME_SLOT')):
            f = self.fixture(); f.view._outcome_budget = budget
            with self.assertRaisesRegex(ContractError, code): f.lease().__enter__()
            self.assertEqual(f.status(), 'PREPARED')
            self.assertIsNone(f.store._capacity_active)

    def test_missing_provenance_stays_denied_with_real_capacity_factory(self):
        f = self.fixture(); f.owner._execution_provenance = None
        with self.assertRaisesRegex(ContractError, 'PROVENANCE_UNAVAILABLE'): f.lease().__enter__()
        self.assertEqual(f.status(), 'PREPARED')
        self.assertIsNone(f.store._capacity_active)

    def test_mutated_configuration_is_rejected_before_dispatch(self):
        f = self.fixture()
        with f.lease() as execution:
            binding = execution._outcome_capacity
            old = binding.budget.memory_bytes
            object.__setattr__(binding.budget, 'memory_bytes', old + 1)
            try:
                with self.assertRaisesRegex(ContractError, 'STORE_CHANGED'): f.fence(execution)
                self.assertFalse(binding.lease.may_have_executed)
                self.assertFalse(execution._dispatch)
            finally: object.__setattr__(binding.budget, 'memory_bytes', old)

    def test_cached_native_calls_finish_before_final_dispatch_decision(self):
        f = self.fixture(); calls = []
        with f.lease() as execution:
            original = capacity._CapacityVfs.call
            def observe(vfs, operation, *args):
                if vfs is f.store._capacity_vfs:
                    calls.append((operation, execution._dispatch, f.kernel._cpu_execution.decision.locked()))
                return original(vfs, operation, *args)
            with patch.object(capacity._CapacityVfs, 'call', observe): f.fence(execution)
            self.assertTrue(calls)
            self.assertTrue(all(row == ('state', False, False) for row in calls))
            execution.record_outcome(*f.evidence())

    def test_owner_stop_after_dispatch_keeps_outcome_bookkeeping_available(self):
        f = self.fixture()
        with f.lease() as execution:
            f.fence(execution)
            f.owner.request_stop()
            self.assertFalse(f.approval_proof.active)
            result = execution.record_outcome(*f.evidence(observation=False))
            self.assertEqual(result.as_dict()['state'], 'UNCERTAIN')
            self.assertTrue(execution._outcome_capacity.lease.durable)
            with self.assertRaises(ContractError): execution.driver_arguments()

    def test_capacity_mark_time_is_charged_before_dispatch(self):
        f = self.fixture()
        original = capacity.OutcomeCapacityLease.mark_may_have_executed
        offset = [0]
        timer = cpu_execution.time.perf_counter_ns
        def mark(lease):
            original(lease)
            offset[0] += cpu_execution.MAXIMUM_CHECK_NS + 1
        with self.assertRaisesRegex(ContractError, 'OWNER_TOO_SLOW') as caught:
            with f.lease() as execution:
                bound = execution._outcome_capacity
                with patch.object(capacity.OutcomeCapacityLease, 'mark_may_have_executed', mark), \
                        patch.object(cpu_execution.time, 'perf_counter_ns', lambda: timer() + offset[0]):
                    f.fence(execution)
        self.assertEqual(caught.exception.owned_cpu_timing['phase'], 'DISPATCH')
        self.assertTrue(bound.lease.may_have_executed)
        self.assertFalse(execution._dispatch)
        self.assertEqual(bound.lease.state, 'PENDING')

    def test_unconfigured_journal_denies_before_consumption(self):
        f = self.fixture(); vfs = f.store._capacity_vfs
        f.store._capacity_vfs = None
        try:
            with self.assertRaisesRegex(ContractError, 'NOT_CONFIGURED'): f.lease().__enter__()
            self.assertEqual(f.status(), 'PREPARED')
            self.assertIsNone(f.store._capacity_active)
        finally: f.store._capacity_vfs = vfs

    def test_foreign_context_request_coordinator_and_store_rejected(self):
        f = self.fixture()
        with f.lease() as execution:
            bound = execution._outcome_capacity
            for args in ((bound.request, execution._permit, object(), bound.coordinator),
                         (replace(bound.request, maximum_duration_ns=bound.request.maximum_duration_ns-1), execution._permit, f.context, bound.coordinator),
                         (bound.request, execution._permit, f.context, object())):
                with self.assertRaisesRegex(ContractError, 'INPUT_CHANGED'):
                    bound.require_current('READY', *args)
            original = f.view._store
            f.view._store = object()
            try:
                with self.assertRaisesRegex(ContractError, 'STORE_CHANGED'):
                    bound.require_current('READY', bound.request, execution._permit, f.context, bound.coordinator)
            finally: f.view._store = original

    def test_competing_thread_cannot_write_check_or_retire(self):
        f = self.fixture(); errors = []
        with f.lease() as execution:
            binding = execution._outcome_capacity
            def other():
                for operation in (lambda: binding.require_current('READY', binding.request, execution._permit, f.context, binding.coordinator),
                                  f.store._require_writable, lambda: binding.__exit__(None,None,None)):
                    try: operation()
                    except ContractError as error: errors.append(error.code)
            thread = threading.Thread(target=other); thread.start(); thread.join(5)
            self.assertFalse(thread.is_alive())
            self.assertEqual(len(errors), 3)
            self.assertTrue(all('ORIGINAL_THREAD_REQUIRED' in code for code in errors))
            self.assertEqual(binding.lease.state, 'ACTIVE')

    def test_copy_pickle_and_reentry_cannot_duplicate_capability(self):
        f = self.fixture()
        with f.lease() as execution:
            binding = execution._outcome_capacity
            for operation in (copy.copy, copy.deepcopy, pickle.dumps):
                with self.assertRaises(ContractError): operation(binding)
            with self.assertRaisesRegex(ContractError, 'SINGLE_USE'): binding.__enter__()

    def test_stop_before_mark_preserves_consumed_liability_and_retires_storage(self):
        f = self.fixture()
        with f.lease() as execution:
            binding = execution._outcome_capacity
            execution.cancel()
            with self.assertRaisesRegex(ContractError, 'STOPPED'): f.fence(execution)
            self.assertFalse(binding.lease.may_have_executed)
            self.assertFalse(execution._dispatch)
            self.assertEqual(f.status(), 'CONSUMED')
        self.assertEqual(binding.lease.state, 'CLOSED')

    def test_stop_after_mark_precedes_dispatch_and_preserves_uncertainty(self):
        f = self.fixture()
        original = capacity.OutcomeCapacityLease.mark_may_have_executed
        def stop(lease):
            original(lease)
            f.kernel._cpu_execution.cancel()
        with self.assertRaisesRegex(ContractError, 'STOPPED'):
            with f.lease() as execution:
                binding = execution._outcome_capacity
                with patch.object(capacity.OutcomeCapacityLease, 'mark_may_have_executed', stop):
                    f.fence(execution)
        self.assertTrue(binding.lease.may_have_executed)
        self.assertFalse(execution._dispatch)
        self.assertEqual(binding.lease.state, 'PENDING')
        self.assertFalse(binding.lease.durable)
        self.assertIs(f.kernel._cpu_execution.active, execution)
        self.assertTrue(f.owner._execution.pending)
        with self.assertRaisesRegex(ContractError, 'DURABLE_RECONCILIATION_REQUIRED'):
            binding.lease.finish_reconciliation()
        with self.assertRaises(ContractError): execution.record_outcome(b'', None, None)
        self.assertIs(f.store._capacity_active, binding.lease)

    def test_generic_owner_cannot_borrow_another_physical_reservation(self):
        f = self.fixture()
        generic = admission.CpuExecutionAdmissionTests()
        generic.schema = self.schema
        self.addCleanup(generic.doCleanups)
        for borrow_adapter in (False, True):
            g = generic.fixture()
            with f.lease() as native_execution:
                bound = native_execution._outcome_capacity
                with generic.lease(g) as execution:
                    g.store._capacity_active = bound.lease
                    execution._outcome_capacity = bound if borrow_adapter else None
                    execution._called = execution._dispatching = True
                    try:
                        with self.assertRaises(ContractError): execution.dispatch_fence()
                        self.assertFalse(execution._dispatch)
                        self.assertFalse(bound.lease.may_have_executed)
                    finally:
                        execution._dispatching = False
                        execution._outcome_capacity = None
                        g.store._capacity_active = None
            if not borrow_adapter: f = self.fixture()

    def test_dispatch_cannot_use_unbound_controlled_capacity(self):
        f = self.fixture()
        with f.lease() as execution:
            binding = execution._outcome_capacity
            execution._outcome_capacity = None
            try:
                with self.assertRaisesRegex(ContractError, 'LEASE_CHANGED'):
                    f.fence(execution)
                self.assertFalse(binding.lease.may_have_executed)
                self.assertFalse(execution._dispatch)
            finally: execution._outcome_capacity = binding

    def test_native_owner_rejects_mismatched_adapter_before_dispatch(self):
        f = self.fixture()
        with f.lease() as execution:
            bound = execution._outcome_capacity
            execution._outcome_capacity = object.__new__(_RetainedCpuOutcomeCapacity)
            try:
                with self.assertRaisesRegex(ContractError, 'LEASE_CHANGED'): f.fence(execution)
                self.assertFalse(bound.lease.may_have_executed)
                self.assertFalse(execution._dispatch)
            finally: execution._outcome_capacity = bound


@unittest.skipUnless(os.environ.get('CETA_CPU_CAPACITY_NATIVE') == '1',
    'Requires Root release for real disposable native VFS allocations')
class NativeCapacityConnectionTests(CapacityConnectionTests):
    """Same capacity wiring on real VFS; CPU/authentication still CONTROLLED."""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.runtime = capacity.OutcomeCapacityRuntime(os.environ['CETA_OUTCOME_CAPACITY_HELPER'],
            os.environ['CETA_OUTCOME_CAPACITY_SHA256'])
