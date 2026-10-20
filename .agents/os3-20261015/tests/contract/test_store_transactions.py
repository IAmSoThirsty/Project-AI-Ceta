"""Actual atomic SQLite mechanics; synthetic state is never effect authority."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import threading
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts.events import StreamPosition
from ceta.contracts.history import JournalEntry
from ceta.contracts.store_transactions import (STORE_PROFILE, StoreCell, StoreChange,
    StoreCommit, StoreExpectation, StoreKey, StorePosition)
from ceta.contracts.wire import ContractError, PROFILE, RecordCodec, canonical_bytes, strict_loads
from ceta.store.journal import SqliteJournal
from ceta.store.sqlite_runtime import load_sqlite
from test_all_records import example

SCOPES = ("installation:fixture", "project:a", "project:b")


def fresh_root():
    root = ROOT / ".agents/fixtures/transactions-21" / uuid.uuid4().hex
    root.mkdir(parents=True, exist_ok=False)
    return root


def codec():
    return RecordCodec(strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes()))


def entry(contract, point, identifier, payload=None):
    if payload is None:
        value = strict_loads((ROOT / "contracts/examples/observation_shape_valid.json").read_bytes())["instance"]
        value.update(scope_id=point.scope_id, record_id="observation:" + identifier)
        payload = canonical_bytes(value)
    decoded = contract.decode(payload)
    event = {"record_type": "EventRecord", "schema_version": "1", "record_id": "event:" + identifier,
        "scope_id": point.scope_id, "causation_ref": None, "sequence": point.next_sequence,
        "event_type": "fixture.storage", "actor_id": "owner:fixture", "actor_session": "session:fixture",
        "recorded_at": "2026-10-08T10:00:00Z", "previous_head": point.head,
        "payload_ref": decoded.record_id, "payload_commitment": decoded.commitment,
        "canonicalization_profile": PROFILE, "signer_key_ref": None, "signature_ref": None}
    return JournalEntry(canonical_bytes(event), payload)


def expected(cell):
    return StoreExpectation(cell.key, cell.revision)


class AtomicStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes())
        cls.codec = RecordCodec(cls.schema)
        cls.sqlite = load_sqlite()

    def setUp(self):
        self.root = fresh_root()
        self.journal = SqliteJournal(self.root, self.codec, SCOPES, create=True, profile=STORE_PROFILE)
        self.key = StoreKey("budget", "installation:fixture", "budget:fixture")

    def tearDown(self):
        self.journal.close()

    def reject(self, code, action, *args, **kwargs):
        with self.assertRaises(ContractError) as caught:
            action(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def cell(self, key=None):
        return self.journal.snapshot((key or self.key,))[0]

    def put(self, identifier, value, key=None):
        key = key or self.key
        point = self.journal.position(key.scope_id)
        row = entry(self.codec, point, identifier)
        return self.journal.commit((point,), (row,), changes=(StoreChange(expected(self.cell(key)), value, "event:" + identifier),))

    def test_all_seven_namespaces_commit_with_events_and_exact_reopen(self):
        namespaces = ("grant", "budget", "reservation", "permit", "intent", "queue", "projection")
        rows, changes, point = [], [], self.journal.position("installation:fixture")
        types = {"grant": "StandingGrant", "permit": "OperationPermit", "queue": "QueueItem"}
        for namespace in namespaces:
            key = StoreKey(namespace, point.scope_id, namespace + ":fixture")
            if namespace in types:
                value = example(self.schema["$defs"][types[namespace]])
                value.update(record_id=key.record_id, scope_id=key.scope_id)
                wire = canonical_bytes(value)
                row = entry(self.codec, point, namespace, wire)
            else:
                wire = canonical_bytes({"schema_version": "1", "fixture_only": True, "value": 10})
                row = entry(self.codec, point, namespace)
            rows.append(row)
            changes.append(StoreChange(expected(StoreCell(key, 0, None)), wire, "event:" + namespace))
            event = self.journal._events.preimages(row.event_wire)
            point = StreamPosition(point.scope_id, point.next_sequence + 1, event.head)
        commit = self.journal.commit((StreamPosition(point.scope_id, 0, None),), tuple(rows), changes=tuple(changes))
        self.assertEqual(len(commit.cells), 7)
        self.assertEqual(commit.position.next_commit, 1)
        self.journal.close()
        self.journal = SqliteJournal(self.root, self.codec, SCOPES, profile=STORE_PROFILE)
        self.assertEqual(self.journal.replay(point.scope_id), tuple(rows))
        self.assertEqual(self.journal.snapshot(tuple(cell.key for cell in commit.cells)), commit.cells)
        self.assertEqual(self.journal.store_position(), commit.position)

    def test_multi_scope_transaction_and_consistent_snapshot(self):
        points = tuple(self.journal.position(scope) for scope in SCOPES)
        rows = tuple(entry(self.codec, point, str(index)) for index, point in enumerate(points))
        keys = tuple(StoreKey("projection", scope, "view:fixture") for scope in SCOPES)
        changes = tuple(StoreChange(expected(StoreCell(key, 0, None)), canonical_bytes({"value": index}), "event:" + str(index))
                        for index, key in enumerate(keys))
        commit = self.journal.commit(points, rows, changes=changes)
        self.assertEqual([item.after.next_sequence for item in commit.history], [1, 1, 1])
        self.assertEqual(self.journal.snapshot(keys), commit.cells)

    def test_fault_after_all_writes_rolls_back_every_scope_cell_and_commit(self):
        points = tuple(self.journal.position(scope) for scope in SCOPES)
        rows = tuple(entry(self.codec, point, str(index)) for index, point in enumerate(points))
        change = StoreChange(expected(self.cell()), canonical_bytes({"reserved": 10}), "event:0")
        def fail():
            raise RuntimeError("after all store writes")
        self.journal._fault = fail
        try:
            with self.assertRaisesRegex(RuntimeError, "after all store writes"):
                self.journal.commit(points, rows, changes=(change,))
        finally:
            self.journal._fault = None
        self.assertEqual(tuple(self.journal.position(scope) for scope in SCOPES), points)
        self.assertEqual(self.cell().generation, 0)
        self.assertEqual(self.journal.store_position(), StorePosition(0, None))

    def test_baseexception_rolls_back_v2_and_preserves_same_connection(self):
        point = self.journal.position(self.key.scope_id)
        def stop():
            raise KeyboardInterrupt("owned cancellation")
        self.journal._fault = stop
        try:
            with self.assertRaises(KeyboardInterrupt):
                self.journal.commit((point,), (entry(self.codec, point, "stop"),),
                    changes=(StoreChange(expected(self.cell()), canonical_bytes({"reserved": 1}), "event:stop"),))
        finally:
            self.journal._fault = None
        self.assertFalse(self.journal._connection.in_transaction)
        self.assertEqual(self.cell().generation, 0)
        self.put("afterstop", canonical_bytes({"reserved": 1}))

    def test_shared_key_read_conflicts_even_when_project_stream_head_is_current(self):
        self.put("initial", canonical_bytes({"remaining": 10}))
        stale = expected(self.cell())
        project_point = self.journal.position("project:a")
        self.put("revoked", canonical_bytes({"remaining": 0}))
        self.reject("STORE_REVISION_CONFLICT", self.journal.commit, (project_point,),
            (entry(self.codec, project_point, "prepare"),), checks=(stale,))
        self.assertEqual(self.journal.position("project:a"), project_point)

    def test_two_connections_same_stream_race_one_commit_one_conflict(self):
        self.put("initial", canonical_bytes({"remaining": 10}))
        shared = expected(self.cell())
        other = SqliteJournal(self.root, self.codec, SCOPES, profile=STORE_PROFILE)
        barrier = threading.Barrier(2)
        def run(journal, identifier):
            point = journal.position(self.key.scope_id)
            row = entry(self.codec, point, identifier)
            barrier.wait(timeout=5)
            try:
                journal.commit((point,), (row,), changes=(StoreChange(shared, canonical_bytes({"remaining": 0}), "event:" + identifier),))
                return "committed"
            except ContractError as error:
                return error.code
        try:
            with ThreadPoolExecutor(2) as pool:
                futures = [pool.submit(run, journal, name) for journal, name in ((self.journal, "a"), (other, "b"))]
                results = [future.result(timeout=10) for future in futures]
            self.assertEqual(sorted(results), sorted(["committed", "JOURNAL_REVISION_CONFLICT"]))
            self.assertEqual(self.cell().generation, 2)
        finally:
            other.close()

    def test_delete_recreate_tombstone_prevents_aba(self):
        first = self.put("first", canonical_bytes({"value": 1})).cells[0]
        deleted = self.put("delete", None).cells[0]
        recreated = self.put("recreate", first.value_wire).cells[0]
        self.assertEqual((first.generation, deleted.generation, recreated.generation), (1, 2, 3))
        self.assertIsNone(deleted.value_wire)
        self.assertNotEqual(first.revision, recreated.revision)
        point = self.journal.position(self.key.scope_id)
        self.reject("STORE_REVISION_CONFLICT", self.journal.commit, (point,),
            (entry(self.codec, point, "stale"),), checks=(expected(first),))

    def test_wire_cell_must_bind_key_type_and_exact_event_payload(self):
        key = StoreKey("grant", self.key.scope_id, "grant:fixture")
        value = example(self.schema["$defs"]["StandingGrant"])
        value.update(record_id=key.record_id, scope_id=key.scope_id)
        wire = canonical_bytes(value)
        point = self.journal.position(key.scope_id)
        row = entry(self.codec, point, "wrong-payload")
        self.reject("STORE_EVENT_VALUE_MISMATCH", self.journal.commit, (point,), (row,),
            changes=(StoreChange(expected(StoreCell(key, 0, None)), wire, "event:wrong-payload"),))
        value["scope_id"] = "project:a"
        self.reject("STORE_RECORD_KEY_MISMATCH", self.journal.commit, (point,), (row,),
            changes=(StoreChange(expected(StoreCell(key, 0, None)), canonical_bytes(value), "event:wrong-payload"),))
        self.assertEqual(self.journal.store_position(), StorePosition(0, None))

    def test_missing_or_other_scope_change_event_denies_whole_batch(self):
        point = self.journal.position("project:a")
        self.reject("STORE_CHANGE_EVENT_REQUIRED", self.journal.commit, (point,), (entry(self.codec, point, "project"),),
            changes=(StoreChange(expected(self.cell()), canonical_bytes({"remaining": 1}), "event:project"),))
        self.assertEqual(self.journal.position("project:a"), point)

    def test_duplicate_keys_absent_delete_and_unknown_scope_are_denied(self):
        point = self.journal.position(self.key.scope_id)
        row = entry(self.codec, point, "invalid")
        change = StoreChange(expected(self.cell()), canonical_bytes({"value": 1}), "event:invalid")
        self.reject("STORE_CHANGE_SET_INVALID", self.journal.commit, (point,), (row,), changes=(change, change))
        self.reject("STORE_ABSENT_DELETE_REJECTED", self.journal.commit, (point,), (row,),
            changes=(StoreChange(expected(self.cell()), None, "event:invalid"),))
        self.reject("JOURNAL_SCOPE_NOT_REGISTERED", self.journal.snapshot, (StoreKey("budget", "unknown:scope", "budget:fixture"),))

    def test_current_projection_and_original_change_tamper_are_detected(self):
        for table in ("store_cells", "store_changes"):
            root = fresh_root()
            journal = SqliteJournal(root, self.codec, SCOPES, create=True, profile=STORE_PROFILE)
            try:
                point = journal.position(self.key.scope_id)
                journal.commit((point,), (entry(self.codec, point, "one"),), changes=(
                    StoreChange(expected(StoreCell(self.key, 0, None)), canonical_bytes({"value": 1}), "event:one"),))
                raw = self.sqlite.connect(journal.path)
                try:
                    raw.execute("UPDATE " + table + " SET value_wire=?", (canonical_bytes({"value": 2}),))
                    raw.commit()
                finally:
                    raw.close()
                with self.subTest(table=table), self.assertRaises(ContractError):
                    journal.validate()
            finally:
                journal.close()

    def test_deleting_transaction_metadata_cannot_leave_accepted_events_unbound(self):
        self.put("one", canonical_bytes({"value": 1}))
        raw = self.sqlite.connect(self.journal.path)
        try:
            raw.execute("DELETE FROM store_changes")
            raw.execute("DELETE FROM store_cells")
            raw.execute("DELETE FROM store_commits")
            raw.commit()
        finally:
            raw.close()
        self.reject("STORE_UNASSOCIATED_EVENT", self.journal.validate)

    def test_separate_state_checkpoint_rejects_wrong_head_and_accepts_older_prefix(self):
        first = self.put("first", canonical_bytes({"value": 1}))
        anchor = self.put("tail", canonical_bytes({"value": 2})).position
        # A retained full-transaction anchor, unlike an event-only anchor, binds
        # mutation metadata. Authentication of the supplied anchor is separate.
        self.reject("STORE_CHECKPOINT_MISMATCH", self.journal.snapshot, (self.key,),
            state_checkpoint=StorePosition(anchor.next_commit, "sha256:" + "0" * 64))
        self.assertEqual(self.journal.snapshot((self.key,), state_checkpoint=first.position)[0].generation, 2)

    def test_retained_state_checkpoint_detects_actual_consistent_tail_removal(self):
        first = self.put("first", canonical_bytes({"value": 1}))
        retained = self.put("tail", canonical_bytes({"value": 2})).position
        raw = self.sqlite.connect(self.journal.path)
        try:
            raw.execute("DELETE FROM store_changes WHERE commit_sequence=1")
            raw.execute("DELETE FROM store_commits WHERE sequence=1")
            raw.execute("DELETE FROM history_events WHERE sequence=1")
            point = first.history[0].after
            raw.execute("UPDATE history_scopes SET next_sequence=?,head=? WHERE scope_id=?", (point.next_sequence, point.head, point.scope_id))
            cell = first.cells[0]
            raw.execute("UPDATE store_cells SET generation=?,value_wire=?,revision=?", (cell.generation, cell.value_wire, cell.revision))
            raw.commit()
        finally:
            raw.close()
        # Complete local replacement is self-consistent without a retained
        # anchor. The retained transaction prefix detects the removed tail.
        self.journal.validate()
        self.assertEqual(self.cell(), first.cells[0])
        self.reject("STORE_CHECKPOINT_MISMATCH", self.journal.snapshot, (self.key,), state_checkpoint=retained)

    def test_competing_project_reader_and_installation_writer_enforce_shared_key_cas(self):
        self.put("initial", canonical_bytes({"remaining": 10}))
        stale = expected(self.cell())
        project_point = self.journal.position("project:a")
        other = SqliteJournal(self.root, self.codec, SCOPES, profile=STORE_PROFILE)
        ready = threading.Barrier(2)
        changed = threading.Event()
        def writer():
            ready.wait(timeout=5)
            try:
                self.put("changed", canonical_bytes({"remaining": 0}))
            finally:
                changed.set()
        def reader():
            ready.wait(timeout=5)
            if not changed.wait(timeout=5):
                raise RuntimeError("writer did not finish")
            self.assertEqual(other.position("project:a"), project_point)
            try:
                other.commit((project_point,), (entry(self.codec, project_point, "project-read"),), checks=(stale,))
            except ContractError as error:
                return error.code
            return "unexpected-commit"
        try:
            with ThreadPoolExecutor(2) as pool:
                write = pool.submit(writer)
                read = pool.submit(reader)
                write.result(timeout=10)
                self.assertEqual(read.result(timeout=10), "STORE_REVISION_CONFLICT")
            self.assertEqual(other.position("project:a"), project_point)
        finally:
            other.close()

    def test_unrelated_events_do_not_invalidate_relevant_state_revision(self):
        self.put("initial", canonical_bytes({"remaining": 10}))
        current = expected(self.cell())
        point = self.journal.position(self.key.scope_id)
        self.journal.append(point, (entry(self.codec, point, "telemetry"),))
        project_point = self.journal.position("project:a")
        committed = self.journal.commit((project_point,), (entry(self.codec, project_point, "project"),), checks=(current,))
        self.assertEqual(committed.history[0].after.next_sequence, 1)
        self.assertEqual(self.cell().revision, current.revision)

    def test_v1_append_compatibility_and_profile_mismatch_preserve_database_bytes(self):
        root = fresh_root()
        v1 = SqliteJournal(root, self.codec, SCOPES, create=True)
        point = v1.position("project:a")
        row = entry(self.codec, point, "v1")
        commit = v1.append(point, (row,))
        self.reject("STORE_PROFILE_REQUIRED", v1.commit, (commit.after,), (entry(self.codec, commit.after, "v1-denied"),))
        v1.close()
        before = hashlib.sha256((root / "history.sqlite3").read_bytes()).hexdigest()
        self.reject("JOURNAL_SCHEMA_MISMATCH", SqliteJournal, root, self.codec, SCOPES, profile=STORE_PROFILE)
        self.assertEqual(hashlib.sha256((root / "history.sqlite3").read_bytes()).hexdigest(), before)
        reopened = SqliteJournal(root, self.codec, SCOPES)
        try:
            self.assertEqual(reopened.replay("project:a"), (row,))
        finally:
            reopened.close()

    def test_event_only_append_in_v2_uses_same_transaction_provenance(self):
        point = self.journal.position("project:a")
        row = entry(self.codec, point, "telemetry")
        commit = self.journal.append(point, (row,))
        self.assertEqual(commit.after.next_sequence, 1)
        self.assertEqual(self.journal.store_position().next_commit, 1)
        self.assertEqual(self.cell().generation, 0)

    def test_existing_append_denial_codes_match_across_explicit_profiles(self):
        root = fresh_root()
        v1 = SqliteJournal(root, self.codec, SCOPES, create=True)
        try:
            for journal in (v1, self.journal):
                point = journal.position("project:a")
                row = entry(self.codec, point, "valid")
                self.reject("JOURNAL_EXPECTED_POSITION_REQUIRED", journal.append, True, (row,))
                self.reject("JOURNAL_BOUNDED_BATCH_REQUIRED", journal.append, point, [row])
                other = entry(self.codec, journal.position("project:b"), "other")
                self.reject("EVENT_SCOPE_MISMATCH", journal.append, point, (other,))
        finally:
            v1.close()

    def test_actual_sqlite_full_rolls_back_events_and_every_state_table(self):
        point = self.journal.position(self.key.scope_id)
        pages = self.journal._connection.execute("PRAGMA page_count").fetchone()[0]
        self.journal._connection.execute("PRAGMA max_page_count=" + str(pages))
        huge = canonical_bytes({"data": "x" * 65536})
        with self.assertRaises(self.sqlite.DatabaseError) as caught:
            self.journal.commit((point,), (entry(self.codec, point, "full"),),
                changes=(StoreChange(expected(self.cell()), huge, "event:full"),))
        self.assertEqual(caught.exception.sqlite_errorcode, self.sqlite.SQLITE_FULL)
        self.assertEqual(self.cell().generation, 0)
        self.assertEqual(self.journal.store_position(), StorePosition(0, None))
        self.assertEqual(self.journal.position(self.key.scope_id), point)

    def test_process_crash_before_or_after_commit_reopens_as_whole_transaction(self):
        for phase, expected_count in (("before", 0), ("after", 1)):
            root = fresh_root()
            journal = SqliteJournal(root, self.codec, SCOPES, create=True, profile=STORE_PROFILE)
            journal.close()
            result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(Path(__file__)), "--crash", phase, str(root)], capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 71 if phase == "before" else 72, result.stderr.decode(errors="replace"))
            reopened = SqliteJournal(root, self.codec, SCOPES, profile=STORE_PROFILE)
            try:
                self.assertEqual([reopened.position(scope).next_sequence for scope in SCOPES], [expected_count] * 3)
                self.assertEqual(reopened.snapshot((self.key,))[0].generation, expected_count)
                self.assertEqual(reopened.store_position().next_commit, expected_count)
            finally:
                reopened.close()

    def test_values_are_immutable_bounded_canonical_and_not_wire_records(self):
        cell = StoreCell(self.key, 1, canonical_bytes({"value": 1}))
        with self.assertRaises(FrozenInstanceError):
            cell.generation = 2
        for value in (True, -1, 2**53):
            self.reject("STORE_GENERATION_INVALID", StoreCell, self.key, value, None)
        self.reject("STORE_CANONICAL_OBJECT_REQUIRED", StoreCell, self.key, 1, b'{"value": 1}')
        self.reject("STORE_COLLECTION_UNSUPPORTED", StoreKey, "sql", self.key.scope_id, "fixture")
        with self.assertRaises(ContractError):
            self.codec.decode(canonical_bytes({"contract_type": "StoreCell", "value": 1}))

    def rewrite_metadata(self, transform):
        raw = self.sqlite.connect(self.journal.path)
        try:
            rows = raw.execute("SELECT sequence,commit_wire FROM store_commits ORDER BY sequence").fetchall()
            values = [strict_loads(row[1]) for row in rows]
            transform(values)
            previous = None
            for sequence, value in enumerate(values):
                value["previous_head"] = previous
                wire = canonical_bytes(value)
                previous = "sha256:" + hashlib.sha256(b"CETA:store-transaction:v2\0" + wire).hexdigest()
                raw.execute("UPDATE store_commits SET commit_wire=?,head=? WHERE sequence=?", (wire, previous, sequence))
            raw.commit()
        finally:
            raw.close()

    def append_two_event_only(self):
        for identifier in ("first", "second"):
            point = self.journal.position("project:a")
            self.journal.append(point, (entry(self.codec, point, identifier),))

    def test_transaction_associations_preserve_per_scope_event_chronology(self):
        self.append_two_event_only()
        def reverse(values):
            values[0]["events"], values[1]["events"] = values[1]["events"], values[0]["events"]
        self.rewrite_metadata(reverse)
        self.reject("STORE_EVENT_ORDER_MISMATCH", self.journal.validate)

    def test_persisted_boolean_sequence_is_rejected_despite_integer_equality(self):
        self.append_two_event_only()
        def change(values):
            values[1]["sequence"] = True
            values[1]["events"][0]["sequence"] = True
        self.rewrite_metadata(change)
        self.reject("STORE_TRANSACTION_METADATA_INVALID", self.journal.validate)

    def test_commit_result_rejects_mutable_containers_and_invalid_position(self):
        valid = self.put("constructor", canonical_bytes({"value": 1}))
        for history, position, cells in ((list(valid.history), valid.position, valid.cells),
                (valid.history, valid.position, list(valid.cells)), (valid.history, None, valid.cells)):
            with self.subTest(history=type(history).__name__, cells=type(cells).__name__, position=type(position).__name__):
                self.reject("STORE_COMMIT_RESULT_INVALID", StoreCommit, history, position, cells)

    def test_persisted_event_boolean_sequence_is_rejected_independently(self):
        self.append_two_event_only()
        def change(values):
            values[1]["events"][0]["sequence"] = True
        self.rewrite_metadata(change)
        self.reject("STORE_EVENT_ASSOCIATION_INVALID", self.journal.validate)


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--crash":
        phase, root = sys.argv[2:]
        def crash():
            os._exit(71)
        contract = codec()
        journal = SqliteJournal(Path(root), contract, SCOPES, profile=STORE_PROFILE,
            before_commit=crash if phase == "before" else None)
        points = tuple(journal.position(scope) for scope in SCOPES)
        rows = tuple(entry(contract, point, str(index)) for index, point in enumerate(points))
        key = StoreKey("budget", SCOPES[0], "budget:fixture")
        change = StoreChange(expected(StoreCell(key, 0, None)), canonical_bytes({"reserved": 10}), "event:0")
        journal.commit(points, rows, changes=(change,))
        os._exit(72)
    unittest.main()
