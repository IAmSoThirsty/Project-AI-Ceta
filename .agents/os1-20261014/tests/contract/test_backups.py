"""Actual SQLite snapshots and historical recovery in fresh, retained T: roots.

SPEC-07, B014 and POL-16/17 supply the consistency, preservation and recovery
oracles. Progress/disk/cleanup faults below are controlled injections around
actual SQLite and actual owned files; they are not power-loss qualification,
authenticated history, protected writer custody or normal-profile cutover.
"""
from dataclasses import FrozenInstanceError
import hashlib
import os
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts.events import StreamPosition
from ceta.contracts.history import JournalEntry
from ceta.contracts.store_transactions import (STORE_PROFILE, StoreChange,
    StoreExpectation, StoreKey)
from ceta.contracts.wire import (ContractError, PROFILE, RecordCodec,
    canonical_bytes, strict_loads)
from ceta.store import backups as backup_module
from ceta.store.backups import (BACKUP_PROFILE, RESTORE_PROFILE, BackupManager,
    BackupProgress, BackupSnapshot)
from ceta.store.journal import SqliteJournal
from ceta.store.sqlite_runtime import load_sqlite
import test_all_records as record_fixtures

SCOPES = ("project:backup-a", "project:backup-b")
JOURNAL_PROFILE = "ceta-sqlite-journal-v1"
BACKUP_MANIFEST = "ceta-backup-complete.json"
BACKUP_INTENT = "ceta-backup-intent.json"
RESTORE_MANIFEST = "ceta-restore-complete.json"
RESTORE_INTENT = "ceta-restore-intent.json"


class _Interrupted(BaseException):
    """A controlled callback interruption, never an OS process-death claim."""


class _HostileInterrupted(_Interrupted):
    def add_note(self, note):
        raise RuntimeError("hostile diagnostic hook")


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


class NativeBackupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = strict_loads(
            (ROOT / "contracts/schemas/records.schema.json").read_bytes())
        cls.codec = RecordCodec(cls.schema)
        cls.sqlite = load_sqlite()

    def setUp(self):
        self.case_root = (ROOT / ".agents/fixtures" / "backups-cmp03"
                          / uuid.uuid4().hex)
        self.case_root.mkdir(parents=True, exist_ok=False)
        self.journal = self.new_journal()
        self.rows = tuple(self.append(self.journal, "before-" + str(index), scope)
                          for index, scope in enumerate(SCOPES))
        self.manager = BackupManager(self.journal)

    def directory(self, label):
        root = self.case_root / (label + "-" + uuid.uuid4().hex)
        root.mkdir(exist_ok=False)
        return root

    def new_journal(self, profile=JOURNAL_PROFILE):
        journal = SqliteJournal(self.directory("source"), self.codec, SCOPES,
                                create=True, profile=profile)
        self.addCleanup(journal.close)
        return journal

    def append(self, journal, label, scope=SCOPES[0], *, key=None, value=None):
        point = journal.position(scope)
        if value is None:
            value = strict_loads((ROOT / "contracts/examples"
                / "observation_shape_valid.json").read_bytes())["instance"]
            value.update(scope_id=scope, record_id="observation:" + label)
        payload = canonical_bytes(value)
        record = self.codec.decode(payload)
        event = {"record_type": "EventRecord", "schema_version": "1",
            "record_id": "event:" + label, "scope_id": scope,
            "causation_ref": None, "sequence": point.next_sequence,
            "event_type": "fixture.backup", "actor_id": "owner:fixture",
            "actor_session": "session:fixture",
            "recorded_at": "2026-10-11T18:30:00Z", "previous_head": point.head,
            "payload_ref": record.record_id,
            "payload_commitment": record.commitment,
            "canonicalization_profile": PROFILE,
            "signer_key_ref": None, "signature_ref": None}
        row = JournalEntry(canonical_bytes(event), payload)
        if journal._profile == STORE_PROFILE:
            changes = ()
            if key is not None:
                cell = journal.snapshot((key,))[0]
                changes = (StoreChange(StoreExpectation(key, cell.revision),
                                       payload, event["record_id"]),)
            journal.commit((point,), (row,), changes=changes)
        else:
            journal.append(point, (row,))
        return row

    def reject(self, code, action, *args, **kwargs):
        with self.assertRaises(ContractError) as caught:
            action(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def raw_state(self, root):
        """Independent SQL rows/bytes, rather than the completion claim."""
        connection = self.sqlite.connect(
            (Path(root) / "history.sqlite3").as_uri() + "?mode=ro",
            uri=True, isolation_level=None)
        try:
            connection.execute("BEGIN")
            result = {
                "scopes": connection.execute(
                    "SELECT scope_id,next_sequence,head FROM history_scopes "
                    "ORDER BY scope_id").fetchall(),
                "events": connection.execute(
                    "SELECT scope_id,sequence,event_id,event_wire,payload_wire,"
                    "event_head,original_event_sha256,original_payload_sha256 "
                    "FROM history_events ORDER BY scope_id,sequence").fetchall()}
            tables = {row[0] for row in connection.execute(
                "SELECT name FROM sqlite_schema WHERE type='table'")}
            if "store_cells" in tables:
                result["cells"] = connection.execute(
                    "SELECT collection,scope_id,record_id,generation,value_wire,"
                    "revision FROM store_cells "
                    "ORDER BY collection,scope_id,record_id").fetchall()
                result["commits"] = connection.execute(
                    "SELECT sequence,commit_wire,head FROM store_commits "
                    "ORDER BY sequence").fetchall()
                result["changes"] = connection.execute(
                    "SELECT commit_sequence,change_index,value_wire "
                    "FROM store_changes ORDER BY commit_sequence,change_index").fetchall()
            connection.execute("COMMIT")
            return result
        finally:
            connection.close()

    def checked_snapshot(self, manager=None):
        manager = manager or self.manager
        destination = self.directory("backup")
        result = manager.snapshot(destination, pages_per_step=1)
        return destination, result

    def document_path(self, snapshot):
        name = (BACKUP_MANIFEST if snapshot.as_dict()["profile"] == BACKUP_PROFILE
                else RESTORE_MANIFEST)
        return Path(snapshot.root) / name

    def edit_document(self, snapshot, changes):
        document = snapshot.as_dict()
        document.update(changes)
        self.document_path(snapshot).write_bytes(canonical_bytes(document))

    def bind_mutated_database(self, snapshot):
        raw = (Path(snapshot.root) / "history.sqlite3").read_bytes()
        self.edit_document(snapshot, {"database_sha256": _sha(raw),
                                      "database_bytes": len(raw)})

    def mutate_sql(self, root, sql):
        connection = self.sqlite.connect(
            (Path(root) / "history.sqlite3").as_uri() + "?mode=rw",
            uri=True, isolation_level=None)
        try:
            connection.execute(sql)
            self.assertEqual(connection.execute(
                "PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0], 0)
        finally:
            connection.close()

    def assert_incomplete(self, destination, intent=BACKUP_INTENT):
        self.assertTrue((destination / intent).is_file())
        self.assertTrue((destination / "history.sqlite3").is_file())
        self.assertFalse((destination / BACKUP_MANIFEST).exists())
        self.assertFalse((destination / RESTORE_MANIFEST).exists())
        self.reject("BACKUP_INCOMPLETE_OR_AMBIGUOUS", self.manager.inspect,
                    destination)

    def test_journal_backup_public_caller_binds_actual_bytes_and_all_scopes(self):
        before = self.raw_state(self.journal.path.parent)
        points = self.journal.validate()
        destination = self.directory("backup")
        result = self.journal.backup(destination, checkpoints=points,
                                     pages_per_step=1)
        self.assertIs(type(result), BackupSnapshot)
        self.assertEqual(self.raw_state(destination), before)
        self.assertEqual([(row[3], row[4]) for row in before["events"]],
            [(row.event_wire, row.payload_wire) for row in self.rows])
        document = result.as_dict()
        database = (destination / "history.sqlite3").read_bytes()
        intent = (destination / BACKUP_INTENT).read_bytes()
        self.assertEqual(document["database_sha256"], _sha(database))
        self.assertEqual(document["database_bytes"], len(database))
        self.assertEqual(document["intent_sha256"], _sha(intent))
        self.assertEqual(document["schema_sha256"],
                         _sha(canonical_bytes(self.schema)))
        self.assertEqual(document["scopes"], list(SCOPES))
        self.assertEqual(result.positions, points)
        self.assertIsNone(result.store_position)
        self.assertEqual(document["profile"], BACKUP_PROFILE)
        self.assertEqual(document["authority"],
                         "HISTORICAL_ONLY_REVALIDATION_REQUIRED")
        self.assertEqual(document["power_loss_qualification"], "NOT_ESTABLISHED")
        self.assertEqual(self.manager.inspect(destination).manifest_wire,
                         result.manifest_wire)
        self.assertEqual(self.raw_state(self.journal.path.parent), before)
        detached = result.as_dict()
        detached["positions"].clear()
        self.assertEqual(result.positions, points)
        with self.assertRaises(FrozenInstanceError):
            result.root = str(self.case_root)

    def test_store_backup_preserves_real_event_cell_and_commit_provenance(self):
        journal = self.new_journal(STORE_PROFILE)
        key = StoreKey("grant", SCOPES[0], "grant:historical-fixture")
        grant = record_fixtures.example(self.schema["$defs"]["StandingGrant"])
        grant.update(record_id=key.record_id, scope_id=key.scope_id)
        self.append(journal, "historical-grant", key=key, value=grant)
        self.append(journal, "other-scope", SCOPES[1])
        cells, point = journal.snapshot((key,)), journal.store_position()
        before = self.raw_state(journal.path.parent)
        manager = BackupManager(journal)
        destination = self.directory("store-backup")
        result = manager.snapshot(destination, state_checkpoint=point)
        self.assertEqual(self.raw_state(destination), before)
        self.assertEqual(result.store_position, point)
        recovered = SqliteJournal(destination, self.codec, SCOPES,
                                  profile=STORE_PROFILE, read_only=True)
        self.addCleanup(recovered.close)
        self.assertEqual(recovered.snapshot((key,)), cells)
        self.assertEqual(recovered.store_position(), point)
        self.assertEqual(manager.inspect(destination).sha256, result.sha256)
        self.assertEqual(self.raw_state(journal.path.parent), before)

    def test_progress_callback_live_commit_does_not_move_pinned_backup_prefix(self):
        for profile in (JOURNAL_PROFILE, STORE_PROFILE):
            with self.subTest(profile=profile):
                writer = self.new_journal(profile)
                self.append(writer, "early-a", SCOPES[0])
                self.append(writer, "early-b", SCOPES[1])
                earlier = self.raw_state(writer.path.parent)
                earlier_points = writer.validate()
                earlier_store = (writer.store_position()
                                 if profile == STORE_PROFILE else None)
                progress, committed = [], []
                def during_copy(observation):
                    progress.append(observation)
                    if not committed:
                        self.assertGreater(observation.remaining_pages, 0)
                        committed.append(self.append(writer, "during-copy"))
                destination = self.directory("concurrent")
                result = writer.backup(destination, pages_per_step=1,
                                       progress=during_copy)
                self.assertEqual(len(committed), 1)
                self.assertTrue(progress)
                self.assertTrue(all(type(item) is BackupProgress
                                    and item.phase == "SNAPSHOT"
                                    for item in progress))
                self.assertEqual(self.raw_state(destination), earlier)
                self.assertEqual(result.positions, earlier_points)
                self.assertEqual(result.store_position, earlier_store)
                later = self.raw_state(writer.path.parent)
                self.assertEqual(len(later["events"]), len(earlier["events"]) + 1)
                self.assertIn((committed[0].event_wire, committed[0].payload_wire),
                              [(row[3], row[4]) for row in later["events"]])
                self.append(writer, "after-copy")
                self.assertEqual(len(self.raw_state(writer.path.parent)["events"]),
                                 len(earlier["events"]) + 2)

    def test_restore_exact_journal_into_fresh_historical_read_only_root(self):
        source_before = self.raw_state(self.journal.path.parent)
        backup, snapshot = self.checked_snapshot()
        backup_bytes = (backup / "history.sqlite3").read_bytes()
        destination = self.directory("restore")
        restored = self.manager.restore(backup, destination, pages_per_step=1)
        self.assertEqual(restored.as_dict()["profile"], RESTORE_PROFILE)
        self.assertEqual(restored.as_dict()["parent_manifest_sha256"], snapshot.sha256)
        self.assertEqual(self.raw_state(destination), source_before)
        self.assertEqual((backup / "history.sqlite3").read_bytes(), backup_bytes)
        self.assertEqual(self.raw_state(self.journal.path.parent), source_before)
        self.assertEqual(self.manager.inspect(destination).manifest_wire,
                         restored.manifest_wire)
        reader = SqliteJournal(destination, self.codec, SCOPES, read_only=True)
        self.addCleanup(reader.close)
        self.assertTrue(reader.storage_identity()["read_only"])
        self.assertEqual(reader.replay(SCOPES[0]), (self.rows[0],))
        self.reject("JOURNAL_READ_ONLY", reader.append, None, ())
        self.reject("JOURNAL_RECOVERY_READ_ONLY_REQUIRED", SqliteJournal,
                    destination, self.codec, SCOPES)
        unused = self.directory("second-restore")
        self.reject("RESTORE_ORIGINAL_BACKUP_REQUIRED", self.manager.restore,
                    destination, unused)
        self.assertEqual(list(unused.iterdir()), [])

    def test_restore_store_keeps_grant_bytes_historical_and_blocks_commit(self):
        journal = self.new_journal(STORE_PROFILE)
        key = StoreKey("grant", SCOPES[0], "grant:old")
        grant = record_fixtures.example(self.schema["$defs"]["StandingGrant"])
        grant.update(record_id=key.record_id, scope_id=key.scope_id)
        self.append(journal, "old-grant", key=key, value=grant)
        manager = BackupManager(journal)
        backup, snapshot = self.checked_snapshot(manager)
        before = self.raw_state(journal.path.parent)
        destination = self.directory("restore-store")
        restored = manager.restore(backup, destination)
        reader = SqliteJournal(destination, self.codec, SCOPES,
                               profile=STORE_PROFILE, read_only=True)
        self.addCleanup(reader.close)
        self.assertEqual(self.raw_state(destination), before)
        self.assertEqual(reader.snapshot((key,)), journal.snapshot((key,)))
        self.assertEqual(restored.store_position, snapshot.store_position)
        self.assertEqual(restored.as_dict()["authority"],
                         "HISTORICAL_ONLY_REVALIDATION_REQUIRED")
        self.reject("JOURNAL_READ_ONLY", reader.commit, (), ())
        self.reject("JOURNAL_RECOVERY_READ_ONLY_REQUIRED", SqliteJournal,
                    destination, self.codec, SCOPES, profile=STORE_PROFILE)
        self.assertEqual(self.raw_state(journal.path.parent), before)

    def test_newer_trusted_checkpoint_refuses_older_backup_and_restore(self):
        backup, _ = self.checked_snapshot()
        self.append(self.journal, "later")
        current = self.journal.validate()
        before = (backup / "history.sqlite3").read_bytes()
        self.reject("JOURNAL_CHECKPOINT_MISMATCH", self.manager.inspect,
                    backup, checkpoints=current)
        destination = self.directory("old-restore")
        self.reject("JOURNAL_CHECKPOINT_MISMATCH", self.manager.restore,
                    backup, destination, checkpoints=current)
        self.assertEqual(list(destination.iterdir()), [])
        self.assertEqual((backup / "history.sqlite3").read_bytes(), before)

    def test_newer_store_checkpoint_refuses_older_store_snapshot(self):
        journal = self.new_journal(STORE_PROFILE)
        self.append(journal, "store-old")
        manager = BackupManager(journal)
        backup, _ = self.checked_snapshot(manager)
        self.append(journal, "store-new")
        self.reject("STORE_CHECKPOINT_MISMATCH", manager.inspect, backup,
                    state_checkpoint=journal.store_position())

    def test_unknown_destination_and_companions_are_preserved(self):
        before = self.raw_state(self.journal.path.parent)
        for name in ("owner-note.txt", "history.sqlite3", "history.sqlite3-wal",
                     "history.sqlite3-shm", "history.sqlite3-journal"):
            with self.subTest(name=name):
                destination = self.directory("occupied")
                path = destination / name
                raw = ("unknown owner bytes: " + name).encode()
                path.write_bytes(raw)
                self.reject("BACKUP_DESTINATION_NOT_EMPTY", self.manager.snapshot,
                            destination)
                self.assertEqual({item.name for item in destination.iterdir()}, {name})
                self.assertEqual(path.read_bytes(), raw)
        self.reject("BACKUP_SOURCE_DESTINATION_EQUAL", self.manager.snapshot,
                    self.journal.path.parent)
        self.assertEqual(self.raw_state(self.journal.path.parent), before)

    def test_interrupted_online_copy_preserves_partial_and_primary_identity(self):
        before = self.raw_state(self.journal.path.parent)
        destination = self.directory("interrupted")
        primary = _HostileInterrupted("controlled progress cancellation")
        seen = []
        def interrupt(observation):
            seen.append(observation)
            raise primary
        with self.assertRaises(_Interrupted) as caught:
            self.journal.backup(destination, pages_per_step=1, progress=interrupt)
        self.assertIs(caught.exception, primary)
        self.assertTrue(seen)
        self.assert_incomplete(destination)
        partial = {path.name: path.read_bytes() for path in destination.iterdir()
                   if path.is_file()}
        self.reject("JOURNAL_RECOVERY_READ_ONLY_REQUIRED", SqliteJournal,
                    destination, self.codec, SCOPES)
        self.assertEqual({path.name: path.read_bytes()
                          for path in destination.iterdir() if path.is_file()}, partial)
        self.assertEqual(self.raw_state(self.journal.path.parent), before)
        self.append(self.journal, "after-interruption")
        self.assertEqual(len(self.raw_state(self.journal.path.parent)["events"]),
                         len(before["events"]) + 1)

    def test_interrupted_restore_preserves_original_and_unactivated_partial(self):
        backup, snapshot = self.checked_snapshot()
        before = (backup / "history.sqlite3").read_bytes()
        destination = self.directory("interrupted-restore")
        primary = _Interrupted("controlled restore interruption")
        def interrupt(observation):
            self.assertEqual(observation.phase, "RESTORE")
            raise primary
        with self.assertRaises(_Interrupted) as caught:
            self.manager.restore(backup, destination, pages_per_step=1,
                                 progress=interrupt)
        self.assertIs(caught.exception, primary)
        self.assert_incomplete(destination, RESTORE_INTENT)
        self.assertEqual((backup / "history.sqlite3").read_bytes(), before)
        self.assertEqual(self.manager.inspect(backup).sha256, snapshot.sha256)
        self.reject("JOURNAL_RECOVERY_READ_ONLY_REQUIRED", SqliteJournal,
                    destination, self.codec, SCOPES)

    def _secondary_verifier_close(self, phase):
        """Only an actually opened fixture verifier is faulted and then closed."""
        if phase == "SNAPSHOT":
            destination = self.directory("close-failure")
            action = lambda: self.manager.snapshot(destination)
        else:
            destination, _ = self.checked_snapshot()
            action = lambda: self.manager.inspect(destination)
        primary = _HostileInterrupted("primary verified-prefix interruption")
        real_prefix = BackupManager._validated_prefix
        real_close = SqliteJournal.close
        faults = []
        def verified_then_interrupt(manager, reader, checkpoints, state_checkpoint):
            result = real_prefix(manager, reader, checkpoints, state_checkpoint)
            if reader.path.parent == destination:
                raise primary
            return result
        def closed_then_fail(reader):
            real_close(reader)
            if reader.path.parent == destination:
                faults.append(reader.path)
                raise OSError("controlled secondary verifier close failure")
        with patch.object(BackupManager, "_validated_prefix",
                          verified_then_interrupt), \
                patch.object(SqliteJournal, "close", closed_then_fail):
            with self.assertRaises(_Interrupted) as caught:
                action()
        self.assertIs(caught.exception, primary)
        self.assertTrue(faults, "The secondary cleanup fault was not reached")
        if phase == "SNAPSHOT":
            self.assert_incomplete(destination)

    def test_snapshot_verifier_secondary_close_keeps_primary_interruption(self):
        self._secondary_verifier_close("SNAPSHOT")

    def test_inspection_verifier_secondary_close_keeps_primary_interruption(self):
        self._secondary_verifier_close("INSPECT")

    def test_late_intent_change_cannot_return_an_accepted_complete_snapshot(self):
        destination = self.directory("late-intent-change")
        real_runtime = backup_module.runtime_identity
        seen = []
        def drift_before_publication():
            identity = real_runtime()
            path = destination / BACKUP_INTENT
            self.assertTrue(path.is_file())
            path.write_bytes(path.read_bytes() + b"\n")
            seen.append(path)
            return identity
        with patch.object(backup_module, "runtime_identity",
                          drift_before_publication):
            with self.assertRaises(ContractError):
                self.manager.snapshot(destination)
        self.assertEqual(len(seen), 1)
        with self.assertRaises(ContractError):
            self.manager.inspect(destination)

    def test_late_database_change_cannot_return_an_accepted_complete_snapshot(self):
        destination = self.directory("late-database-change")
        real_runtime = backup_module.runtime_identity
        seen = []
        def drift_before_publication():
            identity = real_runtime()
            path = destination / "history.sqlite3"
            with path.open("ab") as stream:
                stream.write(b"controlled after-hash fixture mutation")
                stream.flush()
                os.fsync(stream.fileno())
            seen.append(path)
            return identity
        with patch.object(backup_module, "runtime_identity",
                          drift_before_publication):
            with self.assertRaises(ContractError):
                self.manager.snapshot(destination)
        self.assertEqual(len(seen), 1)
        with self.assertRaises(ContractError):
            self.manager.inspect(destination)

    def test_complete_marker_without_intent_never_becomes_writable(self):
        backup, snapshot = self.checked_snapshot()
        restored_root = self.directory("restore-without-intent")
        restored = self.manager.restore(backup, restored_root)
        for root, result, intent_name in ((backup, snapshot, BACKUP_INTENT),
                                          (restored_root, restored, RESTORE_INTENT)):
            with self.subTest(profile=result.as_dict()["profile"]):
                intent = root / intent_name
                # Preserve the missing intent as an explicitly moved test-owned
                # artifact instead of deleting any source or evidence.
                intent.rename(root / (intent_name + ".retained"))
                database = (root / "history.sqlite3").read_bytes()
                manifest = self.document_path(result).read_bytes()
                with self.assertRaises(ContractError):
                    self.manager.inspect(root)
                writer = None
                try:
                    with self.assertRaises(ContractError) as caught:
                        writer = SqliteJournal(root, self.codec, SCOPES)
                    self.assertEqual(caught.exception.code,
                                     "JOURNAL_RECOVERY_READ_ONLY_REQUIRED")
                finally:
                    if writer is not None:
                        writer.close()
                self.assertEqual((root / "history.sqlite3").read_bytes(), database)
                self.assertEqual(self.document_path(result).read_bytes(), manifest)

    def test_partial_manifest_write_is_retained_but_not_admitted(self):
        destination = self.directory("manifest-write-failure")
        target = destination / BACKUP_MANIFEST
        real_open = Path.open
        primary = OSError("controlled manifest disk-write failure")
        touched = []
        class FaultingWriter:
            def __init__(self, stream):
                self.stream = stream
            def __enter__(self):
                self.stream.__enter__()
                return self
            def __exit__(self, *args):
                return self.stream.__exit__(*args)
            def write(self, raw):
                touched.append(len(raw))
                self.stream.write(raw[:17])
                self.stream.flush()
                raise primary
        def selected_open(path, mode="r", *args, **kwargs):
            stream = real_open(path, mode, *args, **kwargs)
            return (FaultingWriter(stream)
                    if Path(path) == target and mode == "xb" else stream)
        source_before = self.raw_state(self.journal.path.parent)
        with patch.object(Path, "open", selected_open):
            with self.assertRaises(OSError) as caught:
                self.manager.snapshot(destination)
        self.assertIs(caught.exception, primary)
        self.assertEqual(len(touched), 1)
        self.assertEqual(target.stat().st_size, 17)
        self.assertEqual(self.raw_state(destination), source_before)
        self.reject("MALFORMED_JSON", self.manager.inspect, destination)
        self.assertEqual(self.raw_state(self.journal.path.parent), source_before)

    def test_invalid_completion_claims_and_noncanonical_manifest_are_rejected(self):
        destination, snapshot = self.checked_snapshot()
        path = self.document_path(snapshot)
        original = path.read_bytes()
        mutations = (
            ({"authority": "ACTIVE"}, "BACKUP_CLAIM_UNSUPPORTED"),
            ({"power_loss_qualification": "PASSED"}, "BACKUP_CLAIM_UNSUPPORTED"),
            ({"state": "IN_PROGRESS"}, "BACKUP_CLAIM_UNSUPPORTED"),
            ({"database_bytes": True}, "BACKUP_DATABASE_BOUND_OR_ALIAS"),
            ({"unexpected_owner_authority": True}, "BACKUP_MANIFEST_FIELDS"))
        for changes, code in mutations:
            with self.subTest(changes=changes):
                try:
                    self.edit_document(snapshot, changes)
                    self.reject(code, self.manager.inspect, destination)
                finally:
                    path.write_bytes(original)
        try:
            path.write_bytes(original + b"\n")
            self.reject("BACKUP_MANIFEST_NOT_CANONICAL", self.manager.inspect,
                        destination)
        finally:
            path.write_bytes(original)
        self.assertEqual(self.manager.inspect(destination).sha256, snapshot.sha256)

    def test_changed_database_fails_raw_hash_without_modifying_corruption(self):
        destination, _ = self.checked_snapshot()
        path = destination / "history.sqlite3"
        corrupted = path.read_bytes() + b"fixture appended bytes"
        path.write_bytes(corrupted)
        self.reject("BACKUP_DATABASE_MISMATCH", self.manager.inspect, destination)
        self.assertEqual(path.read_bytes(), corrupted)
        self.assertEqual(self.journal.replay(SCOPES[0]), (self.rows[0],))

    def test_rehashed_history_corruption_still_fails_full_prefix_validation(self):
        destination, snapshot = self.checked_snapshot()
        self.mutate_sql(destination,
            "UPDATE history_events SET original_payload_sha256='" + "0" * 64 + "'")
        self.bind_mutated_database(snapshot)
        corrupted = (destination / "history.sqlite3").read_bytes()
        self.reject("JOURNAL_PREFIX_MISMATCH", self.manager.inspect, destination)
        self.assertEqual((destination / "history.sqlite3").read_bytes(), corrupted)

    def test_rehashed_store_cell_corruption_does_not_bypass_commit_history(self):
        journal = self.new_journal(STORE_PROFILE)
        key = StoreKey("projection", SCOPES[0], "projection:fixture")
        self.append(journal, "stored-observation", key=key)
        manager = BackupManager(journal)
        destination, snapshot = self.checked_snapshot(manager)
        self.mutate_sql(destination,
            "UPDATE store_cells SET revision='sha256:" + "0" * 64 + "'")
        self.bind_mutated_database(snapshot)
        corrupted = (destination / "history.sqlite3").read_bytes()
        self.reject("STORE_CELL_REVISION_MISMATCH", manager.inspect, destination)
        self.assertEqual((destination / "history.sqlite3").read_bytes(), corrupted)

    def test_rehashed_unknown_schema_or_profile_is_preserved_and_refused(self):
        for sql, code in (
            ("CREATE TABLE unknown_legacy_evidence (value BLOB)",
             "JOURNAL_SCHEMA_MISMATCH"),
            ("UPDATE history_meta SET profile='unknown'",
             "JOURNAL_PROFILE_MISMATCH")):
            with self.subTest(sql=sql):
                destination, snapshot = self.checked_snapshot()
                self.mutate_sql(destination, sql)
                self.bind_mutated_database(snapshot)
                corrupted = (destination / "history.sqlite3").read_bytes()
                self.reject(code, self.manager.inspect, destination)
                self.assertEqual((destination / "history.sqlite3").read_bytes(),
                                 corrupted)

    def test_schema_runtime_and_scope_receipts_bind_the_selected_manager(self):
        destination, snapshot = self.checked_snapshot()
        original = self.document_path(snapshot).read_bytes()
        mutations = (
            ({"schema_sha256": "0" * 64}, "BACKUP_CONTRACT_MISMATCH"),
            ({"sqlite_dll_sha256": "0" * 64}, "BACKUP_RUNTIME_MISMATCH"),
            ({"sqlite_version": "0.0.0"}, "BACKUP_RUNTIME_MISMATCH"))
        for changes, code in mutations:
            with self.subTest(changes=changes):
                try:
                    self.edit_document(snapshot, changes)
                    self.reject(code, self.manager.inspect, destination)
                finally:
                    self.document_path(snapshot).write_bytes(original)
        other = SqliteJournal(self.directory("different-scope"), self.codec,
                              ("project:other",), create=True)
        self.addCleanup(other.close)
        self.reject("BACKUP_CONTRACT_MISMATCH", BackupManager(other).inspect,
                    destination)
        self.assertEqual(self.document_path(snapshot).read_bytes(), original)

    def test_nonempty_recovery_wal_or_rollback_companion_is_preserved_and_refused(self):
        for suffix in ("-wal", "-journal"):
            with self.subTest(suffix=suffix):
                destination, _ = self.checked_snapshot()
                path = Path(str(destination / "history.sqlite3") + suffix)
                raw = b"unknown noncheckpointed companion"
                path.write_bytes(raw)
                self.reject("BACKUP_UNCHECKPOINTED_COMPANION",
                            self.manager.inspect, destination)
                self.assertEqual(path.read_bytes(), raw)

    def test_hardlinked_backup_database_and_manifest_are_rejected(self):
        for name, code in (("history.sqlite3", "BACKUP_DATABASE_BOUND_OR_ALIAS"),
                           (BACKUP_MANIFEST, "BACKUP_FILE_BOUND_OR_ALIAS")):
            with self.subTest(name=name):
                destination, _ = self.checked_snapshot()
                source = destination / name
                alias = self.directory("hardlink") / name
                raw = source.read_bytes()
                os.link(source, alias)
                self.assertGreater(source.stat().st_nlink, 1)
                self.reject(code, self.manager.inspect, destination)
                self.assertEqual(alias.read_bytes(), raw)
                self.assertEqual(source.read_bytes(), raw)

    def test_real_directory_symlink_cannot_select_backup_source_or_destination(self):
        link = self.case_root / "source-link"
        try:
            os.symlink(self.journal.path.parent, link, target_is_directory=True)
        except OSError as exc:
            self.skipTest("Actual Windows directory symlink creation unavailable: "
                          + str(exc))
        self.reject("JOURNAL_PATH_LINK_REJECTED", SqliteJournal,
                    link, self.codec, SCOPES, read_only=True)
        destination = self.directory("link-target")
        destination_link = self.case_root / "destination-link"
        os.symlink(destination, destination_link, target_is_directory=True)
        self.reject("JOURNAL_PATH_LINK_REJECTED", self.manager.snapshot,
                    destination_link)
        self.assertEqual(list(destination.iterdir()), [])
        self.assertTrue(link.is_symlink())
        self.assertTrue(destination_link.is_symlink())

    def test_read_only_and_copy_bounds_refuse_before_creating_artifacts(self):
        destination = self.directory("invalid-arguments")
        for kwargs, code in (
            ({"pages_per_step": True}, "BACKUP_PAGE_BOUND"),
            ({"pages_per_step": 0}, "BACKUP_PAGE_BOUND"),
            ({"pages_per_step": 4097}, "BACKUP_PAGE_BOUND"),
            ({"timeout_seconds": True}, "BACKUP_TIME_BOUND"),
            ({"timeout_seconds": 0}, "BACKUP_TIME_BOUND"),
            ({"progress": "not callable"}, "BACKUP_PROGRESS_CALLBACK")):
            with self.subTest(kwargs=kwargs):
                self.reject(code, self.manager.snapshot, destination, **kwargs)
                self.assertEqual(list(destination.iterdir()), [])
        self.reject("JOURNAL_READ_ONLY_CONSTRUCTION_INVALID", SqliteJournal,
                    destination, self.codec, SCOPES, create=True, read_only=True)
        self.assertEqual(list(destination.iterdir()), [])
        for args in (("SNAPSHOT", True, 0, 1), ("SNAPSHOT", 0, 2, 1),
                     ("UNKNOWN", 0, 0, 0)):
            with self.subTest(args=args), self.assertRaises(ContractError):
                BackupProgress(*args)

    def test_missing_live_wal_cannot_satisfy_later_trusted_checkpoint(self):
        self.assertEqual(self.journal._connection.execute(
            "PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0], 0)
        self.append(self.journal, "wal-only-later")
        trusted = self.journal.validate()
        live_wal = Path(str(self.journal.path) + "-wal")
        self.assertGreater(live_wal.stat().st_size, 0)
        incomplete = self.directory("missing-live-wal")
        shutil.copyfile(self.journal.path, incomplete / "history.sqlite3")
        original = (incomplete / "history.sqlite3").read_bytes()
        historical = SqliteJournal(incomplete, self.codec, SCOPES, read_only=True)
        self.addCleanup(historical.close)
        self.reject("JOURNAL_CHECKPOINT_MISMATCH", historical.validate, trusted)
        partial = self.directory("refused-missing-wal-backup")
        self.reject("JOURNAL_CHECKPOINT_MISMATCH",
                    BackupManager(historical).snapshot, partial,
                    checkpoints=trusted)
        self.assert_incomplete(partial)
        self.assertEqual((incomplete / "history.sqlite3").read_bytes(), original)
        self.assertEqual(self.journal.validate(), trusted)

    def test_restore_never_overwrites_occupied_destination_or_original_source(self):
        backup, snapshot = self.checked_snapshot()
        source = self.raw_state(self.journal.path.parent)
        backup_before = (backup / "history.sqlite3").read_bytes()
        for name in ("owner-note", "history.sqlite3", "history.sqlite3-wal"):
            with self.subTest(name=name):
                destination = self.directory("occupied-restore")
                path = destination / name
                raw = b"unknown destination owner bytes"
                path.write_bytes(raw)
                self.reject("BACKUP_DESTINATION_NOT_EMPTY", self.manager.restore,
                            backup, destination)
                self.assertEqual({item.name for item in destination.iterdir()}, {name})
                self.assertEqual(path.read_bytes(), raw)
        self.reject("BACKUP_DESTINATION_NOT_EMPTY", self.manager.restore, backup,
                    self.journal.path.parent)
        self.assertEqual(self.raw_state(self.journal.path.parent), source)
        self.assertEqual((backup / "history.sqlite3").read_bytes(), backup_before)
        self.assertEqual(self.manager.inspect(backup).sha256, snapshot.sha256)

    def test_deadline_after_actual_progress_rejects_and_keeps_partial(self):
        destination = self.directory("deadline")
        clock, seen = [10.0], []
        def expire_after_progress(observation):
            seen.append(observation)
            clock[0] = 12.0
        with patch.object(backup_module.time, "monotonic", lambda: clock[0]):
            self.reject("BACKUP_DEADLINE_EXCEEDED", self.journal.backup,
                        destination, pages_per_step=1, timeout_seconds=1,
                        progress=expire_after_progress)
        self.assertTrue(seen)
        self.assert_incomplete(destination)
        self.assertEqual(self.journal.replay(SCOPES[0]), (self.rows[0],))


if __name__ == "__main__":
    unittest.main()
