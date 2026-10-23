"""Real SQLite cooperative read limits; fixture files only, no native processes."""
from dataclasses import replace
from pathlib import Path
import threading
import time
import unittest
from unittest.mock import patch
import uuid

from ceta.contracts.store_transactions import STORE_PROFILE
from ceta.contracts.wire import ContractError, RecordCodec, strict_loads
from ceta.store import journal as owner
from ceta.store.journal import JournalReadBudget, SqliteJournal
from test_store_transactions import entry

ROOT = Path(__file__).resolve().parents[2]
SCOPES = ("installation:read-budget", "project:read-budget")
LONG_QUERY = "WITH RECURSIVE n(x) AS (SELECT 0 UNION ALL SELECT x+1 FROM n WHERE x<100000000) SELECT sum(x) FROM n"


class ConnectionFault:
    """Failure injection around a real connection; no replacement database."""
    def __init__(self, actual, *, remove=None, close=None, install=None, rollback=None):
        self.actual, self.remove_error, self.close_error = actual, remove, close
        self.install_error, self.rollback_error = install, rollback
        self.removals = self.closes = 0
    def __getattr__(self, name): return getattr(self.actual, name)
    def set_progress_handler(self, callback, steps):
        if callback is None:
            self.removals += 1
            if self.remove_error is not None: raise self.remove_error
        result = self.actual.set_progress_handler(callback, steps)
        if callback is not None and self.install_error is not None: raise self.install_error
        return result
    def execute(self, sql, *args):
        if sql == "ROLLBACK" and self.rollback_error is not None: raise self.rollback_error
        return self.actual.execute(sql, *args)
    def close(self):
        self.closes += 1
        self.actual.close()
        if self.close_error is not None: raise self.close_error


class JournalReadBudgetTests(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / ".agents/fixtures/read-budget" / uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.codec = RecordCodec(strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes()))
        self.writer = SqliteJournal(self.root, self.codec, SCOPES, create=True, profile=STORE_PROFILE)
    def tearDown(self): self.writer.close()
    def budget(self, **kwargs):
        return JournalReadBudget(time.monotonic_ns() + 5_000_000_000, **kwargs)
    def reader(self, budget=None):
        return SqliteJournal(self.root, self.codec, SCOPES, read_only=True, profile=STORE_PROFILE,
                             read_budget=self.budget() if budget is None else budget)
    def costly_validation(self, reader):
        original = SqliteJournal._verify
        def costly(instance, *args, **kwargs):
            instance._connection.execute(LONG_QUERY).fetchone()
            return original(instance, *args, **kwargs)
        with patch.object(SqliteJournal, "_verify", new=costly): reader.validate()
    def close_after_budget_failure(self, reader, primary=None):
        try: reader.close()
        except BaseException as error:
            if primary is not None: self.assertIs(error, primary)
        self.assertTrue(reader._closed)
        reader.close()

    def test_malformed_budget_refused_before_runtime_or_filesystem(self):
        for kwargs in ({"deadline_monotonic_ns": True}, {"deadline_monotonic_ns": -1},
                       {"deadline_monotonic_ns": 1, "clock": 3},
                       {"deadline_monotonic_ns": 1, "cancelled": False},
                       {"deadline_monotonic_ns": 1, "maximum_vm_steps": True},
                       {"deadline_monotonic_ns": 1, "maximum_checks": 0}):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ContractError, "JOURNAL_READ_BUDGET_INVALID"):
                JournalReadBudget(**kwargs)
        forged = self.budget()
        object.__setattr__(forged, "maximum_checks", True)
        with patch.object(owner, "load_sqlite", side_effect=AssertionError("runtime touched")), \
             patch.object(owner, "_location", side_effect=AssertionError("filesystem touched")):
            for budget in (object(), forged):
                with self.assertRaisesRegex(ContractError, "JOURNAL_READ_BUDGET_INVALID"): self.reader(budget)
            with self.assertRaisesRegex(ContractError, "JOURNAL_READ_BUDGET_INVALID"):
                SqliteJournal(self.root, self.codec, SCOPES, read_budget=self.budget())

    def test_original_configuration_mutation_cannot_disable_progress_checks(self):
        budget = self.budget(maximum_vm_steps=10_000)
        original = owner.replace
        def copy_then_mutate(specification):
            pinned = original(specification)
            object.__setattr__(specification, "maximum_vm_steps", 0)
            return pinned
        with patch.object(owner, "replace", side_effect=copy_then_mutate): reader = self.reader(budget)
        self.assertEqual(reader._read_budget.interval, 1000)
        self.assertEqual(reader._read_budget.specification.maximum_vm_steps, 10_000)
        with self.assertRaisesRegex(ContractError, "JOURNAL_READ_BUDGET_EXHAUSTED") as caught:
            self.costly_validation(reader)
        self.close_after_budget_failure(reader, caught.exception)

    def test_compatibility_writer_unbudgeted_reader_and_nonblocking_budget(self):
        plain = SqliteJournal(self.root, self.codec, SCOPES, read_only=True, profile=STORE_PROFILE)
        limited = self.reader()
        try:
            self.assertEqual(plain._connection.execute("PRAGMA busy_timeout").fetchone()[0], 5000)
            self.assertEqual(limited._connection.execute("PRAGMA busy_timeout").fetchone()[0], 0)
            self.assertEqual(self.writer._connection.execute("PRAGMA busy_timeout").fetchone()[0], 5000)
            self.assertEqual(plain.validate(), limited.validate())
            self.assertEqual(plain.store_position(), limited.store_position())
            with self.assertRaisesRegex(ContractError, "JOURNAL_READ_ONLY"):
                limited.append(limited.position(SCOPES[0]), ())
        finally: plain.close(); limited.close()

    def test_exact_callback_control_exceptions_survive_sqlite_interrupt_and_rollback(self):
        for primary in (KeyboardInterrupt("VM callback"), SystemExit(31)):
            armed, callbacks = [False], [0]
            def cancel():
                callbacks[0] += 1
                if armed[0] and callbacks[0] > 30: raise primary
                return False
            reader = self.reader(self.budget(cancelled=cancel))
            armed[0] = True
            try:
                with self.assertRaises(type(primary)) as caught: self.costly_validation(reader)
                self.assertIs(caught.exception, primary)
                self.assertFalse(reader._connection.in_transaction)
                self.assertEqual(reader._transaction_cleanup_state, "READY")
                self.assertIs(primary.journal_custody, reader)
            finally: self.close_after_budget_failure(reader, primary)
        fresh = self.reader()
        self.assertEqual(fresh.position(SCOPES[0]).next_sequence, 0)
        fresh.close()

    def test_cancel_and_exact_bool_contract_inside_real_vm_query(self):
        for value, code in ((True, "JOURNAL_READ_CANCELLED"), (1, "JOURNAL_READ_CANCELLATION_INVALID")):
            armed = [False]
            reader = self.reader(self.budget(cancelled=lambda: value if armed[0] else False))
            armed[0] = True
            # Delay cancellation until the actual progress callback.
            original_check = reader._check_read_budget
            with patch.object(reader, "_check_read_budget", return_value=None):
                with self.assertRaisesRegex(ContractError, code) as caught: self.costly_validation(reader)
            self.assertGreater(reader._read_budget.vm_steps, 0)
            self.close_after_budget_failure(reader, caught.exception)

    def test_frozen_clock_vm_steps_and_python_check_count_are_finite(self):
        reader = self.reader(JournalReadBudget(6_000_000_000, clock=lambda: 1_000_000_000, maximum_vm_steps=10_000))
        with self.assertRaisesRegex(ContractError, "JOURNAL_READ_BUDGET_EXHAUSTED") as caught:
            self.costly_validation(reader)
        self.assertEqual(reader._read_budget.vm_steps, 10_000)
        self.close_after_budget_failure(reader, caught.exception)
        reader = self.reader(JournalReadBudget(6_000_000_000, clock=lambda: 1_000_000_000,
                                               maximum_vm_steps=65_537, maximum_checks=100_000))
        with self.assertRaisesRegex(ContractError, "JOURNAL_READ_BUDGET_EXHAUSTED") as caught:
            self.costly_validation(reader)
        self.assertEqual(reader._read_budget.vm_steps, 65_537)
        self.close_after_budget_failure(reader, caught.exception)
        reader = self.reader(self.budget(maximum_checks=100))
        with self.assertRaisesRegex(ContractError, "JOURNAL_READ_BUDGET_EXHAUSTED") as caught:
            for _ in range(101): reader.position(SCOPES[0])
        self.close_after_budget_failure(reader, caught.exception)

    def test_clock_rollback_and_deadline_expire_during_vm(self):
        now = [1_000_000_000]
        reader = self.reader(JournalReadBudget(6_000_000_000, clock=lambda: now[0]))
        now[0] -= 1
        with self.assertRaisesRegex(ContractError, "JOURNAL_READ_CLOCK_INVALID") as caught: reader.validate()
        self.close_after_budget_failure(reader, caught.exception)
        now = [1_000_000_000]
        armed = [False]
        def clock():
            if armed[0]: now[0] += 50_000_000
            return now[0]
        reader = self.reader(JournalReadBudget(2_000_000_000, clock=clock))
        armed[0] = True
        with self.assertRaisesRegex(ContractError, "JOURNAL_READ_DEADLINE_EXCEEDED") as caught:
            self.costly_validation(reader)
        self.assertGreater(reader._read_budget.vm_steps, 0)
        self.close_after_budget_failure(reader, caught.exception)

    def test_constructor_vm_callback_exception_retains_failed_owner_and_closes(self):
        primary, calls = KeyboardInterrupt("constructor VM"), [0]
        def cancel():
            calls[0] += 1
            if calls[0] > 20: raise primary
            return False
        original = SqliteJournal._verify
        def costly(instance, *args, **kwargs):
            instance._connection.execute(LONG_QUERY).fetchone()
            return original(instance, *args, **kwargs)
        with patch.object(SqliteJournal, "_verify", new=costly):
            with self.assertRaises(KeyboardInterrupt) as caught: self.reader(self.budget(cancelled=cancel))
        self.assertIs(caught.exception, primary)
        self.assertTrue(primary.journal_custody._closed)
        self.assertEqual(primary.journal_custody._progress_state, "REMOVED")

    def test_python_history_verification_checkpoint_cancels_without_dropping_rows(self):
        for _ in range(12):
            point = self.writer.position(SCOPES[0])
            self.writer.commit((point,), (entry(self.codec, point, uuid.uuid4().hex),))
        rows = [0]
        reader = self.reader(self.budget(cancelled=lambda: rows[0] >= 3))
        original = reader._events.require_successor
        def inspect(*args, **kwargs):
            rows[0] += 1
            return original(*args, **kwargs)
        with patch.object(reader._events, "require_successor", side_effect=inspect):
            with self.assertRaisesRegex(ContractError, "JOURNAL_READ_CANCELLED") as caught:
                reader.validate()
        self.assertEqual(rows[0], 3)
        self.close_after_budget_failure(reader, caught.exception)
        self.assertEqual(self.writer.position(SCOPES[0]).next_sequence, 12)

    def test_deadline_after_slow_close_is_observed_without_replaying_close(self):
        now = [1_000_000_000]
        reader = self.reader(JournalReadBudget(2_000_000_000, clock=lambda: now[0]))
        actual = reader._connection
        wrapped = ConnectionFault(actual)
        def close():
            wrapped.closes += 1
            actual.close()
            now[0] = 2_000_000_000
        wrapped.close = close
        reader._connection = wrapped
        with self.assertRaisesRegex(ContractError, "JOURNAL_READ_DEADLINE_EXCEEDED") as caught:
            reader.close()
        self.assertTrue(reader._closed)
        self.assertEqual(caught.exception.journal_close_state, "CLOSED")
        reader.close()
        self.assertEqual(wrapped.closes, 1)

    def test_constructor_handler_install_failure_cleanup_preserves_primary(self):
        sqlite = self.writer._sqlite
        real_connect = sqlite.connect
        primary = SystemExit(37)
        connections = []
        def connect(*args, **kwargs):
            wrapped = ConnectionFault(real_connect(*args, **kwargs), install=primary)
            connections.append(wrapped)
            return wrapped
        with patch.object(sqlite, "connect", side_effect=connect), self.assertRaises(SystemExit) as caught:
            self.reader()
        self.assertIs(caught.exception, primary)
        self.assertEqual((connections[0].removals, connections[0].closes), (1, 1))
        self.assertTrue(primary.journal_custody._closed)

    def test_rollback_and_handler_connection_cleanup_failures_keep_primary_custody(self):
        armed = [False]
        primary = KeyboardInterrupt("query interrupted")
        def cancel():
            if armed[0]: raise primary
            return False
        reader = self.reader(self.budget(cancelled=cancel))
        remove, close, rollback = RuntimeError("remove"), RuntimeError("close"), RuntimeError("rollback")
        wrapped = ConnectionFault(reader._connection, remove=remove, close=close, rollback=rollback)
        reader._connection = wrapped
        armed[0] = True
        with patch.object(reader, "_check_read_budget", return_value=None):
            with self.assertRaises(KeyboardInterrupt) as caught: self.costly_validation(reader)
        self.assertIs(caught.exception, primary)
        self.assertIs(primary.journal_rollback_error, rollback)
        with self.assertRaises(KeyboardInterrupt) as caught: reader.close()
        self.assertIs(caught.exception, primary)
        self.assertIs(primary.journal_progress_error, remove)
        self.assertIs(primary.journal_close_error, close)
        self.assertEqual((wrapped.removals, wrapped.closes), (1, 1))
        with self.assertRaisesRegex(ContractError, "JOURNAL_CLOSE_UNCERTAIN"): reader.close()
        self.assertEqual(wrapped.closes, 1)

    def test_handler_remove_only_failure_is_not_success_and_not_retried(self):
        reader = self.reader()
        primary = RuntimeError("handler removal")
        wrapped = ConnectionFault(reader._connection, remove=primary)
        reader._connection = wrapped
        with self.assertRaises(RuntimeError) as caught: reader.close()
        self.assertIs(caught.exception, primary)
        self.assertTrue(reader._closed)
        self.assertEqual((wrapped.removals, wrapped.closes), (1, 1))
        reader.close()
        self.assertEqual(wrapped.removals, 1)

    def test_real_sqlite_exclusive_lock_refuses_without_five_second_wait(self):
        self.writer._connection.execute("PRAGMA locking_mode=EXCLUSIVE")
        self.writer._connection.execute("BEGIN EXCLUSIVE")
        started = time.perf_counter()
        try:
            with self.assertRaisesRegex(ContractError, "JOURNAL_READ_BUDGET_BUSY"):
                self.reader()
            self.assertLess(time.perf_counter() - started, .5)
        finally:
            self.writer._connection.execute("ROLLBACK")
        self.writer._connection.execute("PRAGMA locking_mode=NORMAL")

    def test_closed_and_uncertain_owner_precede_expired_or_cancelled_callbacks(self):
        for uncertain in (False, True):
            for cancelled_after in (False, True):
                with self.subTest(uncertain=uncertain, cancelled=cancelled_after):
                    now, stop, calls = [1_000_000_000], [False], [0]
                    def cancel(): calls[0] += 1; return stop[0]
                    reader = self.reader(JournalReadBudget(2_000_000_000, clock=lambda: now[0], cancelled=cancel))
                    if uncertain:
                        reader._connection = ConnectionFault(reader._connection, close=RuntimeError("close uncertain"))
                        with self.assertRaises(RuntimeError): reader.close()
                    else: reader.close()
                    before = calls[0]
                    now[0], stop[0] = 2_000_000_000, cancelled_after
                    code = "JOURNAL_CLOSE_UNCERTAIN" if uncertain else "JOURNAL_CLOSED"
                    for read in (reader.validate, lambda: reader.position(SCOPES[0]), reader.store_position):
                        with self.assertRaisesRegex(ContractError, code) as caught: read()
                        if uncertain: self.assertIs(caught.exception.journal_custody, reader)
                    self.assertEqual(calls[0], before)

    def test_shared_python_lock_refused_and_concurrent_readers_preserve_store(self):
        reader = self.reader()
        held, release = threading.Event(), threading.Event()
        def hold():
            with reader._lock: held.set(); release.wait(5)
        thread = threading.Thread(target=hold); thread.start(); self.assertTrue(held.wait(5))
        try:
            with self.assertRaisesRegex(ContractError, "JOURNAL_READ_BUDGET_BUSY"): reader.validate()
        finally: release.set(); thread.join(5); reader.close()
        outputs, errors = [], []
        def read():
            try:
                local = self.reader()
                try: outputs.append(local.store_position())
                finally: local.close()
            except BaseException as error: errors.append(error)
        threads = [threading.Thread(target=read) for _ in range(4)]
        for thread in threads: thread.start()
        for thread in threads: thread.join(5); self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(len(outputs), 4)
        self.assertTrue(all(x == self.writer.store_position() for x in outputs))


if __name__ == "__main__": unittest.main()
