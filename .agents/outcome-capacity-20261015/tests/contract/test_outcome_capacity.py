"""Controlled custody contracts and separate actual Windows SQLite witnesses.

The controlled backend is explicitly not native allocation evidence. Native
cases require the pinned helper and a designated create-only fixture root.
"""
import copy
import ctypes
import hashlib
import os
from pathlib import Path
import pickle
import sys
import threading
from types import SimpleNamespace
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from ceta.contracts.wire import ContractError
from ceta.contracts.store_transactions import STORE_PROFILE
from ceta.store import outcome_capacity as product

NATIVE_RECEIPTS = []


class ControlledFunctions:
    """Deterministic state-only faults, never a qualified VFS."""
    def __init__(self):
        self.state, self.generation = product._IDLE, 0
        self.calls, self.release_error = [], None

    def action(self, name, token, *args):
        self.calls.append(name)
        if name == 'release' and self.release_error is not None:
            raise self.release_error
        if name == 'reserve':
            self.state, self.generation = product._RETAINED, self.generation + 1
        if name == 'release':
            self.state = product._IDLE
        value = ctypes.cast(args[-1], ctypes.POINTER(product._Snapshot)).contents
        value.version, value.state, value.generation, value.open_files = 1, self.state, self.generation, 2
        for row in value.files:
            row.close_state = product._OPEN if self.state == product._RETAINED else product._RETIRED
        value.mapped_shm_probe.close_state = product._RETIRED
        return 0

    def method(self, name):
        return lambda token, *args: self.action(name, token, *args)


class ControlledCapacityTests(unittest.TestCase):
    def fixture(self):
        native = ControlledFunctions()
        runtime = SimpleNamespace(_functions={name: native.method(name)
            for name in ('reserve', 'state', 'measure', 'release')})
        vfs = product._CapacityVfs(runtime, 'controlled_not_native', 1)
        journal = SimpleNamespace(_capacity_vfs=vfs, _capacity_active=None,
            _connection=SimpleNamespace(in_transaction=False), _closed=False,
            _connection_close_state='OPEN', _transaction_cleanup_state='READY', _lock=threading.RLock())
        journal._require_writable = lambda: None
        lease = product.OutcomeCapacityLease(journal, product.OutcomeCapacityBudget(65536, 65536, 65536, 128))
        return journal, lease, native

    def test_budget_rejects_boolean_unaligned_overflow_and_unbounded_memory(self):
        for args in ((True,65536,65536), (65537,65536,65536), (64*1024*1024,65536,65536),
                     (65536,65536,65536,True), (65536,65536,65536,1048577)):
            with self.subTest(args=args), self.assertRaises(ContractError):
                product.OutcomeCapacityBudget(*args)

    def test_ordinary_entry_exit_is_single_use_and_retires_once(self):
        journal, lease, native = self.fixture()
        with lease:
            self.assertIs(journal._capacity_active, lease)
            self.assertIsNone(lease.require_current())
        self.assertIsNone(journal._capacity_active)
        self.assertEqual(native.calls.count('release'), 1)
        with self.assertRaisesRegex(ContractError, 'SINGLE_USE'):
            lease.__enter__()

    def test_capacity_check_uses_only_nonblocking_cached_state_method(self):
        journal, lease, native = self.fixture()
        with lease:
            native.calls.clear()
            journal._connection.in_transaction = True
            self.assertIsNone(lease.require_current())
            self.assertEqual(native.calls, ['state'])
            with self.assertRaisesRegex(ContractError, 'QUERY_INSIDE_TRANSACTION'):
                lease.measure()
            journal._connection.in_transaction = False

    def test_other_thread_cannot_use_or_retire_original_reservation(self):
        _, lease, _ = self.fixture()
        errors = []
        with lease:
            def other():
                for call in (lease.require_current, lambda: lease.__exit__(None,None,None)):
                    try: call()
                    except ContractError as error: errors.append(error.code)
            worker = threading.Thread(target=other)
            worker.start(); worker.join(5)
            self.assertFalse(worker.is_alive())
            self.assertEqual(errors, ['OUTCOME_CAPACITY_ORIGINAL_THREAD_REQUIRED'] * 2)

    def test_copy_and_serialization_cannot_duplicate_reservation(self):
        _, lease, _ = self.fixture()
        for call in (copy.copy, copy.deepcopy, pickle.dumps):
            with self.assertRaises(ContractError): call(lease)

    def test_staging_requires_dispatch_and_exact_bounded_bytes(self):
        _, lease, _ = self.fixture()
        with lease:
            with self.assertRaisesRegex(ContractError, 'OUTCOME_ONCE'):
                lease.stage_outcome((b'x',))
            lease.mark_may_have_executed()
            with self.assertRaisesRegex(ContractError, 'MEMORY_EXHAUSTED'):
                lease.stage_outcome((b'x' * 129,))
            lease.stage_outcome((b'actual-receipt', b'actual-observation'))
            with self.assertRaisesRegex(ContractError, 'OUTCOME_ONCE'):
                lease.stage_outcome((b'replacement',))
            result = object()
            lease._after_commit(tuple(SimpleNamespace(payload_wire=v)
                for v in (b'actual-receipt', b'actual-observation')), result)
            self.assertIs(lease.commit, result)

    def test_unrelated_committed_payload_does_not_release_outcome(self):
        journal, lease, _ = self.fixture()
        with self.assertRaisesRegex(ContractError, 'DURABLE_OUTCOME_PENDING'):
            with lease:
                lease.mark_may_have_executed(); lease.stage_outcome((b'needed',))
                lease._after_commit((SimpleNamespace(payload_wire=b'wrong'),), object())
        self.assertIs(journal._capacity_active, lease)
        self.assertFalse(lease.durable)
        self.assertEqual(lease.retained_payloads(), (b'needed',))
        lease._after_commit((SimpleNamespace(payload_wire=b'needed'),), object())
        lease.finish_reconciliation()
        self.assertEqual(lease.state, 'CLOSED')

    def test_post_effect_exception_preserves_original_and_pending_bytes(self):
        _, lease, native = self.fixture()
        primary = KeyboardInterrupt('controlled interruption')
        with self.assertRaises(KeyboardInterrupt) as caught:
            with lease:
                lease.mark_may_have_executed(); lease.stage_outcome((b'evidence',))
                raise primary
        self.assertIs(caught.exception, primary)
        self.assertIs(primary.outcome_capacity_custody, lease)
        self.assertEqual(lease.retained_payloads(), (b'evidence',))
        self.assertNotIn('release', native.calls)
        lease._after_commit((SimpleNamespace(payload_wire=b'evidence'),), object())
        lease.finish_reconciliation()

    def test_failed_retirement_preserves_primary_and_never_retries_close(self):
        journal, lease, native = self.fixture()
        primary, secondary = ValueError('primary'), OSError('controlled release failure')
        native.release_error = secondary
        with self.assertRaises(ValueError) as caught:
            with lease: raise primary
        self.assertIs(caught.exception, primary)
        self.assertIs(primary.outcome_capacity_cleanup_error, secondary)
        self.assertIs(journal._capacity_active, lease)
        with self.assertRaisesRegex(ContractError, 'RELEASE_UNCERTAIN'):
            lease._release()
        self.assertEqual(native.calls.count('release'), 1)

    def test_lost_generation_or_native_failure_denies_currentness(self):
        _, lease, native = self.fixture()
        with lease:
            native.generation += 1
            with self.assertRaisesRegex(ContractError, 'CAPACITY_LOST'):
                lease.require_current()

    def test_missing_native_configuration_is_explicitly_unavailable(self):
        with self.assertRaisesRegex(ContractError, 'NOT_CONFIGURED'):
            product.OutcomeCapacityLease(SimpleNamespace(_capacity_vfs=None),
                product.OutcomeCapacityBudget(65536,65536,65536))

    def test_exit_signals_pending_to_explicit_owner_caller_and_preserves_body_error(self):
        for failure in ('missing_commit', 'release'):
            with self.subTest(failure=failure):
                journal, lease, native = self.fixture()
                lease.__enter__()
                primary = KeyboardInterrupt('original body error')
                if failure == 'missing_commit': lease.mark_may_have_executed()
                else: native.release_error = OSError('controlled close uncertainty')
                with self.assertRaises(KeyboardInterrupt) as caught:
                    lease.__exit__(type(primary), primary, None)
                self.assertIs(caught.exception, primary)
                self.assertIs(primary.outcome_capacity_custody, lease)
                self.assertIs(journal._capacity_active, lease)
                self.assertEqual(lease.state, 'PENDING')


@unittest.skipUnless(os.environ.get('CETA_OUTCOME_CAPACITY_NATIVE') == '1',
                     'Actual native test requires the sequenced pinned helper and disposable fixture root')
class NativeOutcomeCapacityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from test_history import codec
        cls.codec = codec()
        cls.runtime = product.OutcomeCapacityRuntime(os.environ['CETA_OUTCOME_CAPACITY_HELPER'],
                                                     os.environ['CETA_OUTCOME_CAPACITY_SHA256'])
        cls.fixtures = Path(os.environ['CETA_OUTCOME_CAPACITY_FIXTURES'])
        cls.fixtures.mkdir(parents=False, exist_ok=False)

    def setUp(self):
        from ceta.store.journal import SqliteJournal
        self.root = self.fixtures / uuid.uuid4().hex
        self.root.mkdir()
        self.journal = SqliteJournal(self.root,self.codec,('project:fixture',),create=True,
                                    profile=STORE_PROFILE,outcome_runtime=self.runtime)
        self.lease = None
        self.budget = product.OutcomeCapacityBudget(2*1024*1024,4*1024*1024,65536)
        self.observations = []

    def tearDown(self):
        # Preserve unresolved state; never clear an uncertain product flag to
        # manufacture cleanup. Any pending lease is reported as a test failure.
        active = self.journal._capacity_active
        if active is not None:
            NATIVE_RECEIPTS.append(dict(test=self.id(), root=str(self.root), pending=active.state,
                                       snapshot=active.reservation_snapshot))
            self.fail('Native test left a retained capacity; inspect exact custody before recovery')
        self.journal.close()
        NATIVE_RECEIPTS.append(dict(test=self.id(), root=str(self.root),
            reservation=None if self.lease is None else self.lease.reservation_snapshot,
            retirement=None if self.lease is None else self.lease.retirement_snapshot,
            observations=self.observations, connection_closed=self.journal._connection_close_state,
            vfs_closed=self.journal._capacity_vfs.closed,
            files={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                   for p in self.root.iterdir() if p.is_file()}))

    def row(self, name):
        from test_history import entry
        position = self.journal.position('project:fixture')
        return position, entry(self.codec, position, name)

    def test_actual_allocation_exact_commit_retirement_checkpoint_and_reopen(self):
        from ceta.store.journal import SqliteJournal
        before, row = self.row('retained')
        self.lease = self.journal.reserve_outcome_capacity(self.budget)
        with self.lease:
            facts = self.lease.measure(); self.observations.append(facts)
            self.assertFalse(self.journal._connection.in_transaction)
            for file, amount in zip(facts['files'], (2097152,4194304,65536)):
                self.assertGreaterEqual(file['allocation'], amount)
                self.assertLessEqual(file['eof'], amount)
                self.assertNotEqual(file['identifier'], '0'*32)
            self.assertEqual(facts['files'][2]['identifier'], facts['mapped_shm_probe']['identifier'])
            self.lease.mark_may_have_executed()
            self.lease.stage_outcome((row.payload_wire,))
            committed = self.journal.append(before, (row,))
            self.assertTrue(self.lease.durable); self.assertIs(self.lease.commit.history[0], committed)
            self.observations.append(self.lease.measure())
        self.journal._connection.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        self.journal.close()
        self.journal = SqliteJournal(self.root,self.codec,('project:fixture',),
                                    profile=STORE_PROFILE,outcome_runtime=self.runtime)
        self.assertEqual(self.journal.replay('project:fixture'), (row,))

    def test_concurrent_writer_and_close_cannot_consume_reserved_capacity(self):
        before, row = self.row('other')
        self.lease = self.journal.reserve_outcome_capacity(self.budget)
        errors = []
        with self.lease:
            def other():
                try: self.journal.append(before,(row,))
                except ContractError as error: errors.append(error.code)
            worker=threading.Thread(target=other); worker.start(); worker.join(5)
            self.assertFalse(worker.is_alive())
            self.assertEqual(errors,['OUTCOME_CAPACITY_ORIGINAL_THREAD_REQUIRED'])
            with self.assertRaisesRegex(ContractError,'CAPACITY_RETAINED'):
                self.journal.close()
            self.assertEqual(self.journal.position('project:fixture'), before)
        # A committed writer delayed just before its post-commit notification
        # must not be attributed to a reservation acquired by a later thread.
        original = self.journal._capacity_commit
        committed, resume = threading.Event(), threading.Event()
        responses = []
        def delayed(entries, result, retained):
            committed.set()
            if not resume.wait(5): raise RuntimeError('test rendezvous timed out')
            return original(entries, result, retained)
        self.journal._capacity_commit = delayed
        def earlier():
            try: responses.append(self.journal.append(before, (row,)))
            except BaseException as error: responses.append(error)
        worker=threading.Thread(target=earlier);worker.start()
        self.assertTrue(committed.wait(5))
        try:
            with self.journal.reserve_outcome_capacity(self.budget):
                resume.set();worker.join(5)
                self.assertFalse(worker.is_alive())
                self.assertEqual(len(responses),1)
                self.assertNotIsInstance(responses[0],BaseException)
        finally:
            resume.set();worker.join(5);self.journal._capacity_commit=original

    def test_commit_failure_retains_exact_bytes_until_real_reconciliation(self):
        before, row = self.row('reconciliation')
        self.lease = self.journal.reserve_outcome_capacity(self.budget)
        primary = RuntimeError('controlled pre-commit fault on real SQLite')
        def fail(): raise primary
        with self.assertRaises(RuntimeError) as caught:
            with self.lease:
                self.lease.mark_may_have_executed()
                self.lease.stage_outcome((row.payload_wire,))
                self.journal._fault = fail
                self.journal.append(before,(row,))
        self.assertIs(caught.exception, primary)
        self.assertEqual(self.journal.position('project:fixture'), before)
        self.assertEqual(self.lease.retained_payloads(), (row.payload_wire,))
        self.assertEqual(self.lease.state,'PENDING')
        self.journal._fault = None
        self.journal.append(before,(row,))
        self.lease.finish_reconciliation()
        self.assertEqual(self.journal.replay('project:fixture'), (row,))

    def test_native_wal_ceiling_refuses_growth_and_keeps_prior_commits(self):
        existing = Path(str(self.journal.path)+'-wal').stat().st_size
        ceiling = ((existing + 65535)//65536 + 1)*65536
        self.lease = self.journal.reserve_outcome_capacity(product.OutcomeCapacityBudget(1048576,ceiling,65536))
        committed = []
        with self.lease:
            for number in range(32):
                before,row = self.row('bounded'+str(number))
                try: self.journal.append(before,(row,))
                except self.journal._sqlite.DatabaseError:
                    self.observations.append(product._facts(self.journal._capacity_vfs.call('state')))
                    break
                committed.append(row)
            else: self.fail('Expected actual WAL write bound was not reached')
        self.assertEqual(self.journal.replay('project:fixture'), tuple(committed))
        self.assertEqual(self.lease.retirement_snapshot['state'], product._IDLE)


if __name__ == '__main__':
    unittest.main()
