"""Real fresh SQLite fixtures, including competing writers and process crashes."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts.events import EventContract, StreamPosition
from ceta.contracts.history import JournalEntry
from ceta.contracts.wire import ContractError, RecordCodec, PROFILE, canonical_bytes, strict_loads
from ceta.store.journal import SqliteJournal
from ceta.store.sqlite_runtime import load_sqlite


def codec():
    return RecordCodec(strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes()))


def entry(contract, position, identifier):
    fixture = strict_loads((ROOT / "contracts/examples/observation_shape_valid.json").read_bytes())["instance"]
    fixture.update(scope_id=position.scope_id, record_id="observation:" + identifier)
    payload = canonical_bytes(fixture)
    event = {"record_type": "EventRecord", "schema_version": "1", "record_id": "event:" + identifier,
        "scope_id": position.scope_id, "causation_ref": None, "sequence": position.next_sequence,
        "event_type": "observation.accepted", "actor_id": "observer:fixture", "actor_session": "session:fixture",
        "recorded_at": "2026-10-08T10:00:00Z", "previous_head": position.head,
        "payload_ref": fixture["record_id"], "payload_commitment": contract.decode(payload).commitment,
        "canonicalization_profile": PROFILE, "signer_key_ref": None, "signature_ref": None}
    return JournalEntry(canonical_bytes(event), payload)


def fresh_root():
    path = ROOT / ".agents/fixtures/history-20" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    return path


class HistoryPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.codec = codec()
        cls.sqlite = load_sqlite()

    def setUp(self):
        self.root = fresh_root()
        self.journal = SqliteJournal(self.root, self.codec, ("project:fixture",), create=True)

    def tearDown(self):
        self.journal.close()

    def reject(self, code, action, *args):
        with self.assertRaises(ContractError) as caught:
            action(*args)
        self.assertEqual(caught.exception.code, code)

    def append_one(self, identifier="one"):
        before = self.journal.position("project:fixture")
        row = entry(self.codec, before, identifier)
        return row, self.journal.append(before, (row,))

    def test_real_append_reopen_exact_original_bytes_and_replay(self):
        row, committed = self.append_one()
        self.assertEqual(committed.before.next_sequence, 0)
        self.assertEqual(committed.after.next_sequence, 1)
        self.journal.close()
        self.journal = SqliteJournal(self.root, self.codec, ("project:fixture",))
        self.assertEqual(self.journal.position("project:fixture"), committed.after)
        self.assertEqual(self.journal.replay("project:fixture"), (row,))

    def test_loaded_engine_and_actual_sqlite_settings(self):
        identity = self.journal.storage_identity()
        self.assertEqual(identity["runtime"]["version"], "3.53.4")
        self.assertEqual(identity["settings"], {"journal_mode": "wal", "synchronous": 2,
            "foreign_keys": 1, "busy_timeout": 5000, "locking_mode": "normal", "wal_autocheckpoint": 1000})

    def test_stale_writer_is_denied_and_preserves_first_commit(self):
        stale = self.journal.position("project:fixture")
        _, commit = self.append_one()
        self.reject("JOURNAL_REVISION_CONFLICT", self.journal.append, stale, (entry(self.codec, stale, "stale"),))
        self.assertEqual(self.journal.position("project:fixture"), commit.after)

    def test_two_actual_connections_race_same_position_only_one_commit(self):
        other = SqliteJournal(self.root, self.codec, ("project:fixture",))
        expected = self.journal.position("project:fixture")
        barrier = threading.Barrier(2)
        def run(journal, identifier):
            row = entry(self.codec, expected, identifier)
            barrier.wait(timeout=5)
            try:
                journal.append(expected, (row,))
                return "COMMITTED"
            except ContractError as error:
                return error.code
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(run, self.journal, "race1"), pool.submit(run, other, "race2")]
                results = [future.result(timeout=15) for future in futures]
            self.assertCountEqual(results, ["COMMITTED", "JOURNAL_REVISION_CONFLICT"])
            self.assertEqual(self.journal.position("project:fixture").next_sequence, 1)
        finally:
            other.close()

    def test_injected_exception_after_inserts_rolls_back_entire_batch(self):
        def interrupt():
            raise RuntimeError("owned fixture interruption")
        other = SqliteJournal(self.root, self.codec, ("project:fixture",), before_commit=interrupt)
        before = other.position("project:fixture")
        try:
            with self.assertRaisesRegex(RuntimeError, "owned fixture interruption"):
                other.append(before, (entry(self.codec, before, "interrupt"),))
            self.assertEqual(self.journal.position("project:fixture"), before)
            self.assertEqual(self.journal.replay("project:fixture"), ())
        finally:
            other.close()

    def test_duplicate_event_id_rolls_back_without_advancing_position(self):
        _, commit = self.append_one("duplicate")
        duplicate = entry(self.codec, commit.after, "duplicate")
        with self.assertRaises(self.sqlite.IntegrityError):
            self.journal.append(commit.after, (duplicate,))
        self.assertEqual(self.journal.position("project:fixture"), commit.after)

    def test_baseexception_unwind_rolls_back_and_connection_remains_usable(self):
        for exception_type in (KeyboardInterrupt, SystemExit):
            with self.subTest(exception=exception_type.__name__):
                before = self.journal.position("project:fixture")
                def interrupt():
                    raise exception_type("owned fixture cancellation")
                self.journal._fault = interrupt
                try:
                    with self.assertRaises(exception_type):
                        self.journal.append(before, (entry(self.codec, before, exception_type.__name__),))
                finally:
                    self.journal._fault = None
                self.assertFalse(self.journal._connection.in_transaction)
                self.assertEqual(self.journal.position("project:fixture"), before)
                self.journal.append(before, (entry(self.codec, before, "after" + exception_type.__name__),))

    def test_full_prefix_tamper_is_detected_with_unchanged_stored_tail(self):
        first, _ = self.append_one("first")
        self.append_one("tail")
        altered = strict_loads(first.payload_wire)
        altered["record_id"] = "observation:tampered"
        raw = self.sqlite.connect(self.journal.path)
        try:
            raw.execute("UPDATE history_events SET payload_wire=? WHERE sequence=0", (canonical_bytes(altered),))
            raw.commit()
        finally:
            raw.close()
        with self.assertRaises(ContractError):
            self.journal.validate()
        with self.assertRaises(ContractError):
            self.journal.replay("project:fixture")

    def test_checkpoint_detects_consistent_tail_rollback_under_retained_input(self):
        _, first = self.append_one("first")
        _, tail = self.append_one("tail")
        raw = self.sqlite.connect(self.journal.path)
        try:
            raw.execute("DELETE FROM history_events WHERE sequence=1")
            raw.execute("UPDATE history_scopes SET next_sequence=?,head=?", (first.after.next_sequence, first.after.head))
            raw.commit()
        finally:
            raw.close()
        self.assertEqual(self.journal.validate(), (first.after,))
        self.reject("JOURNAL_CHECKPOINT_MISMATCH", self.journal.validate, (tail.after,))

    def test_checkpoint_validates_prefix_with_later_tail(self):
        _, first = self.append_one("first")
        _, tail = self.append_one("tail")
        self.assertEqual(self.journal.validate((first.after,)), (tail.after,))
        self.assertEqual(len(self.journal.replay("project:fixture", checkpoints=(first.after,))), 2)
        row = entry(self.codec, tail.after, "later")
        self.assertEqual(self.journal.append(tail.after, (row,), checkpoints=(first.after,)).after.next_sequence, 3)

    def test_replay_checks_retained_checkpoint_in_its_own_transaction(self):
        _, first = self.append_one("first")
        _, tail = self.append_one("tail")
        self.journal.validate((tail.after,))
        raw = self.sqlite.connect(self.journal.path)
        try:
            raw.execute("DELETE FROM history_events WHERE sequence=1")
            raw.execute("UPDATE history_scopes SET next_sequence=?,head=?", (first.after.next_sequence, first.after.head))
            raw.commit()
        finally:
            raw.close()
        # A prior successful validation cannot bind a later read transaction.
        self.assertEqual(len(self.journal.replay("project:fixture")), 1)
        with self.assertRaises(ContractError) as caught:
            self.journal.replay("project:fixture", checkpoints=(tail.after,))
        self.assertEqual(caught.exception.code, "JOURNAL_CHECKPOINT_MISMATCH")

    def test_append_checks_other_scope_checkpoint_before_committing(self):
        journal = SqliteJournal(fresh_root(), self.codec, ("project:fixture", "project:other"), create=True)
        try:
            start = journal.position("project:fixture")
            committed = journal.append(start, (entry(self.codec, start, "anchor"),))
            other_start = journal.position("project:other")
            raw = self.sqlite.connect(journal.path)
            try:
                raw.execute("DELETE FROM history_events WHERE scope_id=?", (start.scope_id,))
                raw.execute("UPDATE history_scopes SET next_sequence=0,head=NULL WHERE scope_id=?", (start.scope_id,))
                raw.commit()
            finally:
                raw.close()
            with self.assertRaises(ContractError) as caught:
                journal.append(other_start, (entry(self.codec, other_start, "denied"),), checkpoints=(committed.after,))
            self.assertEqual(caught.exception.code, "JOURNAL_CHECKPOINT_MISMATCH")
            self.assertEqual(journal.position("project:other"), other_start)
        finally:
            journal.close()

    def test_wal_profile_denial_survives_optimized_python(self):
        result = subprocess.run([sys.executable, "-O", "-B", "-X", "utf8", str(Path(__file__)), "--wal-denial"],
                                capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout.decode(errors="replace") + result.stderr.decode(errors="replace"))
        self.assertEqual(result.stdout.strip(), b"JOURNAL_STORAGE_PROFILE_MISMATCH")

    def test_writer_reopen_rechecks_actual_storage_profile(self):
        self.journal.close()
        sqlite = self.sqlite
        original_connect = sqlite.connect
        target = self.root / "history.sqlite3"
        class RuntimeProxy:
            calls = 0
            def __getattr__(self, name):
                return getattr(sqlite, name)
            def connect(self, *args, **kwargs):
                self.calls += 1
                if self.calls == 2:
                    # Alter the actual fixture after read-only validation closes.
                    raw = original_connect(target)
                    try:
                        if raw.execute("PRAGMA journal_mode=DELETE").fetchone()[0] != "delete":
                            raise RuntimeError("fixture profile switch failed")
                    finally:
                        raw.close()
                return original_connect(*args, **kwargs)
        with patch("ceta.store.journal.load_sqlite", return_value=RuntimeProxy()):
            with self.assertRaises(ContractError) as caught:
                opened = SqliteJournal(self.root, self.codec, ("project:fixture",))
                opened.close()
        self.assertEqual(caught.exception.code, "JOURNAL_STORAGE_PROFILE_MISMATCH")

    def test_nonreserved_sqlite_like_trigger_is_not_hidden_from_schema_check(self):
        before = self.journal.position("project:fixture")
        row = entry(self.codec, before, "trigger")
        raw = self.sqlite.connect(self.journal.path)
        try:
            raw.execute("CREATE TRIGGER sqliteXcorrupt AFTER INSERT ON history_events BEGIN "
                        "UPDATE history_events SET payload_wire=X'00' "
                        "WHERE scope_id=NEW.scope_id AND sequence=NEW.sequence; END")
            raw.commit()
        finally:
            raw.close()
        self.reject("JOURNAL_SCHEMA_MISMATCH", self.journal.append, before, (row,))
        raw = self.sqlite.connect(self.journal.path)
        try:
            self.assertEqual(raw.execute("SELECT count(*) FROM history_events").fetchone()[0], 0)
        finally:
            raw.close()

    def test_unknown_scope_and_unbounded_replay_are_denied(self):
        self.reject("JOURNAL_SCOPE_NOT_REGISTERED", self.journal.position, "project:other")
        for start, limit in ((True, 1), (-1, 1), (0, 0), (0, 129), (0, True)):
            self.reject("JOURNAL_READ_BOUND_REQUIRED", self.journal.replay, "project:fixture", start, limit)

    def test_entry_is_immutable_and_rejects_mutable_bytes(self):
        row = entry(self.codec, self.journal.position("project:fixture"), "immutable")
        with self.assertRaises(FrozenInstanceError):
            row.event_wire = b"different"
        for event_wire in (bytearray(b"data"), b"", "data"):
            self.reject("JOURNAL_ENTRY_BYTES_REQUIRED", JournalEntry, event_wire, b"data")

    def test_missing_store_does_not_create_replacement(self):
        root = fresh_root()
        self.reject("JOURNAL_MISSING_PRESERVED_RECOVERY_REQUIRED", SqliteJournal, root, self.codec, ("project:fixture",))
        self.assertFalse((root / "history.sqlite3").exists())

    def test_unknown_profile_is_rejected_before_writer_without_changing_db_bytes(self):
        self.journal.close()
        raw = self.sqlite.connect(self.root / "history.sqlite3")
        raw.execute("UPDATE history_meta SET profile='unsupported-profile'")
        raw.commit()
        raw.close()
        target = self.root / "history.sqlite3"
        before = hashlib.sha256(target.read_bytes()).hexdigest()
        self.reject("JOURNAL_PROFILE_MISMATCH", SqliteJournal, self.root, self.codec, ("project:fixture",))
        self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), before)

    def test_existing_file_and_unknown_companion_are_preserved(self):
        root = fresh_root()
        target = root / "history.sqlite3"
        target.write_bytes(b"unknown existing fixture bytes")
        with self.assertRaisesRegex(ContractError, "JOURNAL_EXISTING_FILE_PRESERVED"):
            SqliteJournal(root, self.codec, ("project:fixture",), create=True)
        self.assertEqual(target.read_bytes(), b"unknown existing fixture bytes")
        root2 = fresh_root()
        companion = root2 / "history.sqlite3-wal"
        companion.write_bytes(b"unknown companion fixture")
        with self.assertRaisesRegex(ContractError, "JOURNAL_UNKNOWN_COMPANION_PRESERVED"):
            SqliteJournal(root2, self.codec, ("project:fixture",), create=True)
        self.assertFalse((root2 / "history.sqlite3").exists())
        self.assertEqual(companion.read_bytes(), b"unknown companion fixture")

    def test_actual_junction_root_is_rejected(self):
        target = fresh_root()
        parent = fresh_root()
        junction = parent / "junction"
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(target)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.reject("JOURNAL_PATH_LINK_REJECTED", SqliteJournal, junction, self.codec, ("project:fixture",))

    def test_real_process_crash_before_and_after_commit(self):
        for phase, expected_count in (("before", 0), ("after", 1)):
            root = fresh_root()
            journal = SqliteJournal(root, self.codec, ("project:fixture",), create=True)
            journal.close()
            result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(Path(__file__)), "--crash", phase, str(root)], capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 71 if phase == "before" else 72, result.stderr.decode(errors="replace"))
            reopened = SqliteJournal(root, self.codec, ("project:fixture",))
            try:
                self.assertEqual(reopened.position("project:fixture").next_sequence, expected_count)
            finally:
                reopened.close()

    def test_real_sqlite_full_error_preserves_empty_committed_stream(self):
        before = self.journal.position("project:fixture")
        pages = self.journal._connection.execute("PRAGMA page_count").fetchone()[0]
        self.journal._connection.execute("PRAGMA max_page_count=" + str(pages))
        rows, point = [], before
        events = EventContract(self.codec)
        for number in range(128):
            row = entry(self.codec, point, "diskfull" + str(number))
            rows.append(row)
            head = events.preimages(row.event_wire).head
            point = StreamPosition(point.scope_id, point.next_sequence + 1, head)
        with self.assertRaises(self.sqlite.DatabaseError) as caught:
            self.journal.append(before, tuple(rows))
        self.assertEqual(caught.exception.sqlite_errorcode, self.sqlite.SQLITE_FULL)
        self.assertEqual(self.journal.position("project:fixture"), before)


if __name__ == "__main__":
    if sys.argv[1:] == ["--wal-denial"]:
        sqlite = load_sqlite()
        class ConnectionProxy:
            def __init__(self, connection):
                self.connection = connection
            def __getattr__(self, name):
                return getattr(self.connection, name)
            def execute(self, sql, *args):
                # Fault the actual connection's WAL request, preserving DELETE.
                if sql == "PRAGMA journal_mode=WAL":
                    sql = "PRAGMA journal_mode"
                return self.connection.execute(sql, *args)
        class RuntimeProxy:
            def __getattr__(self, name):
                return getattr(sqlite, name)
            def connect(self, *args, **kwargs):
                return ConnectionProxy(sqlite.connect(*args, **kwargs))
        with patch("ceta.store.journal.load_sqlite", return_value=RuntimeProxy()):
            try:
                journal = SqliteJournal(fresh_root(), codec(), ("project:fixture",), create=True)
            except ContractError as error:
                if error.code != "JOURNAL_STORAGE_PROFILE_MISMATCH":
                    raise
                print(error.code)
                sys.exit(0)
            else:
                journal.close()
                raise RuntimeError("WAL profile refusal was accepted under optimization")
    if len(sys.argv) == 4 and sys.argv[1] == "--crash":
        phase, root = sys.argv[2:]
        contract = codec()
        def crash():
            os._exit(71)
        journal = SqliteJournal(Path(root), contract, ("project:fixture",), before_commit=crash if phase == "before" else None)
        before = journal.position("project:fixture")
        journal.append(before, (entry(contract, before, "crash"),))
        os._exit(72)
    unittest.main()
