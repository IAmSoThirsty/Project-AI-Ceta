"""Real SQLite event journal, under the still-open unified operating contract.

Mechanical persistence only: authenticated writer access, kernel decisions,
protected process composition and effect admission remain separate obligations.
Unknown/corrupt stores are preserved and rejected, never reset or regenerated.
"""
import ctypes
from ctypes import wintypes
import hashlib
import os
from pathlib import Path
import threading

from ceta.contracts.events import EventContract, StreamPosition
from ceta.contracts.history import JournalCommit, JournalEntry
from ceta.contracts.store_transactions import (STORE_PROFILE, StoreChange, StoreCommit,
    StoreExpectation, StoreKey, StorePosition)
from ceta.contracts.wire import ContractError, RecordCodec
from .sqlite_runtime import load_sqlite, runtime_identity
from .state import SCHEMA as STATE_SCHEMA, TransactionState
from .projections import ProjectionReducer, MAX_PROJECTION_EVENTS, MAX_PROJECTION_BYTES

_PROFILE = "ceta-sqlite-journal-v1"
_SCHEMA = {
    "history_meta": "CREATE TABLE history_meta (id INTEGER PRIMARY KEY CHECK(id=1), profile TEXT NOT NULL)",
    "history_scopes": "CREATE TABLE history_scopes (scope_id TEXT PRIMARY KEY, next_sequence INTEGER NOT NULL, head TEXT)",
    "history_events": "CREATE TABLE history_events (scope_id TEXT NOT NULL, sequence INTEGER NOT NULL, event_id TEXT NOT NULL, event_wire BLOB NOT NULL, payload_wire BLOB NOT NULL, event_head TEXT NOT NULL, original_event_sha256 TEXT NOT NULL, original_payload_sha256 TEXT NOT NULL, PRIMARY KEY(scope_id,sequence), UNIQUE(scope_id,event_id), FOREIGN KEY(scope_id) REFERENCES history_scopes(scope_id))",
}


def _digest(wire):
    return hashlib.sha256(wire).hexdigest()


def _location(root):
    root = Path(root)
    if not root.is_absolute() or not root.is_dir():
        raise ContractError("JOURNAL_EXISTING_ABSOLUTE_ROOT_REQUIRED")
    path = root / "history.sqlite3"
    for parent in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm"), Path(str(path) + "-journal"), *path.parents):
        if parent.is_symlink() or parent.is_junction():
            raise ContractError("JOURNAL_PATH_LINK_REJECTED")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetDriveTypeW.argtypes = [wintypes.LPCWSTR]
    kernel.GetDriveTypeW.restype = wintypes.UINT
    drive = root.anchor
    if kernel.GetDriveTypeW(drive) != 3:
        raise ContractError("JOURNAL_LOCAL_FIXED_FILESYSTEM_REQUIRED")
    kernel.GetVolumeInformationW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
        wintypes.LPWSTR, wintypes.DWORD]
    kernel.GetVolumeInformationW.restype = wintypes.BOOL
    filesystem = ctypes.create_unicode_buffer(64)
    if not kernel.GetVolumeInformationW(drive, None, 0, None, None, None, filesystem, len(filesystem)):
        raise ContractError("JOURNAL_FILESYSTEM_UNAVAILABLE")
    if filesystem.value != "NTFS":
        raise ContractError("JOURNAL_FILESYSTEM_NOT_SELECTED")
    return path.resolve()


class SqliteJournal:
    """Serialized append/CAS implementation of HistoryPort in an owned root.

    Scope registration is fixed at construction. Authentication is the eventual
    owner/process boundary's responsibility; this class has no authority verdict.
    before_commit is an injected infrastructure fault hook, never wire data.
    """

    def __init__(self, root, codec, scopes, *, create=False, before_commit=None, profile=_PROFILE, read_only=False,
                 outcome_runtime=None):
        if type(codec) is not RecordCodec:
            raise ContractError("JOURNAL_RECORD_CODEC_REQUIRED")
        if (type(scopes) is not tuple or not 1 <= len(scopes) <= 1024
                or any(type(scope) is not str for scope in scopes)
                or len(set(scopes)) != len(scopes)):
            raise ContractError("JOURNAL_SCOPE_REGISTRY_REQUIRED")
        for scope in scopes:
            StreamPosition(scope, 0, None)
        if type(create) is not bool or (before_commit is not None and not callable(before_commit)):
            raise ContractError("JOURNAL_CONSTRUCTION_INVALID")
        if type(profile) is not str or profile not in (_PROFILE, STORE_PROFILE):
            raise ContractError("JOURNAL_PROFILE_UNSUPPORTED")
        if type(read_only) is not bool or (read_only and (create or before_commit is not None)):
            raise ContractError("JOURNAL_READ_ONLY_CONSTRUCTION_INVALID")
        if outcome_runtime is not None:
            from .outcome_capacity import OutcomeCapacityRuntime
            if type(outcome_runtime) is not OutcomeCapacityRuntime or read_only:
                raise ContractError("JOURNAL_OUTCOME_RUNTIME_INVALID")
        self._read_only = read_only
        self._profile = profile
        self._schema = {**_SCHEMA, **STATE_SCHEMA} if profile == STORE_PROFILE else _SCHEMA
        self._sqlite = load_sqlite()
        self.path = _location(root)
        # A recovered historical store is never an implicitly reactivated writer.
        if not read_only and any((self.path.parent / name).exists() for name in
                ("ceta-backup-intent.json", "ceta-restore-intent.json",
                 "ceta-backup-complete.json", "ceta-restore-complete.json")):
            raise ContractError("JOURNAL_RECOVERY_READ_ONLY_REQUIRED")
        self._codec, self._events = codec, EventContract(codec)
        self._scopes = tuple(sorted(scopes))
        self._lock = threading.RLock()
        self._fault = before_commit
        self._capacity_vfs = self._capacity_active = None
        self._connection = None
        self._constructor_close_state = "ABSENT"
        self._constructor_failed = False
        self._connection_close_state = "ABSENT"
        self._connection_close_error = None
        self._transaction_cleanup_state = "READY"
        self._rollback_error = None
        self._closed = True
        if create:
            if any(Path(str(self.path) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")):
                raise ContractError("JOURNAL_UNKNOWN_COMPANION_PRESERVED")
            try:
                descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(descriptor)
            except FileExistsError as exc:
                raise ContractError("JOURNAL_EXISTING_FILE_PRESERVED") from exc
        elif not self.path.is_file():
            raise ContractError("JOURNAL_MISSING_PRESERVED_RECOVERY_REQUIRED")
        try:
            if outcome_runtime is not None:
                self._capacity_vfs = outcome_runtime._create()
            self._connection = self._sqlite.connect(self._connection_uri("rw" if create else "ro"), uri=True,
                timeout=5, isolation_level=None, check_same_thread=False)
            self._constructor_close_state = "OPEN"
            self._connection_close_state = "OPEN"
            self._closed = False
            self._state = TransactionState(self._connection, codec, self._scopes) if profile == STORE_PROFILE else None
            self._connection.setconfig(self._sqlite.SQLITE_DBCONFIG_DEFENSIVE, True)
            self._connection.setconfig(self._sqlite.SQLITE_DBCONFIG_TRUSTED_SCHEMA, False)
            self._connection.enable_load_extension(False)
            for pragma in ("foreign_keys=ON", "trusted_schema=OFF", "synchronous=FULL",
                           "busy_timeout=5000", "locking_mode=NORMAL", "wal_autocheckpoint=1000"):
                self._connection.execute("PRAGMA " + pragma)
            if create:
                if self._connection.execute("PRAGMA journal_mode=WAL").fetchone()[0] != "wal":
                    raise ContractError("JOURNAL_STORAGE_PROFILE_MISMATCH")
                self._connection.execute("BEGIN IMMEDIATE")
                for sql in self._schema.values():
                    self._connection.execute(sql)
                self._connection.execute("INSERT INTO history_meta VALUES(1,?)", (self._profile,))
                self._connection.executemany("INSERT INTO history_scopes VALUES(?,0,NULL)", [(scope,) for scope in self._scopes])
                self._connection.execute("COMMIT")
            elif self._connection.execute("PRAGMA journal_mode").fetchone()[0] != "wal":
                raise ContractError("JOURNAL_STORAGE_PROFILE_MISMATCH")
            self.validate()
            if not create and not read_only:
                # Inspect unknown/corrupt history through a read-only connection
                # before opening the owner writer. Recheck after acquiring it.
                self._close_constructor_connection()
                self._connection = self._sqlite.connect(self._connection_uri("rw"), uri=True,
                    timeout=5, isolation_level=None, check_same_thread=False)
                self._constructor_close_state = "OPEN"
                self._connection_close_state = "OPEN"
                self._closed = False
                self._state = TransactionState(self._connection, codec, self._scopes) if profile == STORE_PROFILE else None
                self._connection.setconfig(self._sqlite.SQLITE_DBCONFIG_DEFENSIVE, True)
                self._connection.setconfig(self._sqlite.SQLITE_DBCONFIG_TRUSTED_SCHEMA, False)
                self._connection.enable_load_extension(False)
                for pragma in ("foreign_keys=ON", "trusted_schema=OFF", "synchronous=FULL",
                               "busy_timeout=5000", "locking_mode=NORMAL", "wal_autocheckpoint=1000"):
                    self._connection.execute("PRAGMA " + pragma)
                self.validate()
        except BaseException as primary:
            self._constructor_failed = True
            cleanup_error = None
            if self._connection is not None and self._constructor_close_state == "OPEN":
                try:
                    self._close_constructor_connection()
                except BaseException as secondary:
                    cleanup_error = secondary
            # Trusted BaseException storage bypasses user diagnostic setters,
            # note getters and traceback assignment. Bare raise keeps primary.
            data = BaseException.__dict__["__dict__"].__get__(primary)
            dict.update(data, journal_custody=self, journal_connection=self._connection,
                        journal_cleanup_state=self._constructor_close_state,
                        journal_cleanup_error=cleanup_error)
            if self._capacity_vfs is not None and self._constructor_close_state in ("ABSENT", "CLOSED"):
                try:
                    self._capacity_vfs.close()
                except BaseException as secondary:
                    dict.update(data, outcome_capacity_cleanup_error=secondary,
                                outcome_capacity_custody=self._capacity_vfs)
            self._retain_failure(primary)
            raise

    def _connection_uri(self, mode):
        if self._capacity_vfs is not None:
            return self._capacity_vfs.uri(self.path, mode)
        return self.path.as_uri() + "?mode=" + mode

    def reserve_outcome_capacity(self, budget):
        """Retain one measured allocation on this journal, before an effect."""
        from .outcome_capacity import OutcomeCapacityLease
        self._require_writable()
        return OutcomeCapacityLease(self, budget)

    def _capacity_commit(self, entries, result, retained):
        # Capture the reservation under the writer lock. A later reservation
        # must not acquire an earlier completed transaction's callback.
        if retained is not None:
            retained._after_commit(entries, result)
        return result

    def _close_constructor_connection(self):
        # An invocation/response failure cannot prove that close did not happen.
        # Record uncertainty before method lookup/call; never automatically replay.
        self._constructor_close_state = "UNCERTAIN"
        self._connection_close_state = "UNCERTAIN"
        response = self._connection.close()
        if response is not None:
            raise ContractError("JOURNAL_CLOSE_RESULT_INVALID")
        self._constructor_close_state = "CLOSED"
        self._connection_close_state = "CLOSED"
        self._closed = True

    def _require_open(self):
        if self._constructor_failed:
            raise ContractError("JOURNAL_CONSTRUCTION_FAILED")
        if self._connection_close_state == "UNCERTAIN":
            denied = ContractError("JOURNAL_CLOSE_UNCERTAIN")
            self._retain_failure(denied)
            raise denied
        if self._transaction_cleanup_state == "UNCERTAIN":
            denied = ContractError("JOURNAL_TRANSACTION_CLEANUP_UNCERTAIN")
            self._retain_failure(denied)
            raise denied
        if self._closed:
            raise ContractError("JOURNAL_CLOSED")

    def _retain_failure(self, primary):
        data = BaseException.__dict__["__dict__"].__get__(primary)
        dict.update(data, journal_custody=self, journal_connection=self._connection,
                    journal_close_state=self._connection_close_state,
                    journal_close_error=self._connection_close_error,
                    journal_transaction_state=self._transaction_cleanup_state,
                    journal_rollback_error=self._rollback_error)
        return data

    def _rollback_after_error(self, primary, *, projection=False):
        # A getter, invocation or response failure cannot prove rollback. Poison
        # further operations, but retain the distinct right to close this owner.
        self._transaction_cleanup_state = "UNCERTAIN"
        self._rollback_error = None
        try:
            active = self._connection.in_transaction
            if type(active) is not bool:
                raise ContractError("JOURNAL_TRANSACTION_STATE_INVALID")
            if active:
                response = self._connection.execute("ROLLBACK")
                if type(response) is not self._sqlite.Cursor:
                    raise ContractError("JOURNAL_ROLLBACK_RESULT_INVALID")
                inactive = self._connection.in_transaction
                if inactive is not False:
                    raise ContractError("JOURNAL_ROLLBACK_UNOBSERVED")
            self._transaction_cleanup_state = "READY"
        except BaseException as secondary:
            self._rollback_error = secondary
        data = self._retain_failure(primary)
        if projection and self._rollback_error is not None:
            # Preserve the established diagnostic without invoking exception
            # getters, setters, add_note overrides or untrusted note methods.
            try:
                if not dict.__contains__(data, "__notes__"):
                    dict.__setitem__(data, "__notes__", ["JOURNAL_PROJECTION_ROLLBACK_UNOBSERVED"])
                else:
                    notes = dict.__getitem__(data, "__notes__")
                    if type(notes) is list and all(type(note) is str for note in notes):
                        list.append(notes, "JOURNAL_PROJECTION_ROLLBACK_UNOBSERVED")
            except BaseException:
                pass

    def _require_writable(self):
        self._require_open()
        if self._read_only:
            raise ContractError("JOURNAL_READ_ONLY")
        if self._capacity_active is not None:
            self._capacity_active.require_current()

    def _require_scope(self, scope):
        if type(scope) is not str or scope not in self._scopes:
            raise ContractError("JOURNAL_SCOPE_NOT_REGISTERED")

    def _verify(self, checkpoints=(), state_checkpoint=None):
        if self._connection.execute("PRAGMA journal_mode").fetchone()[0] != "wal":
            raise ContractError("JOURNAL_STORAGE_PROFILE_MISMATCH")
        if self._connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ContractError("JOURNAL_PHYSICAL_INTEGRITY_FAILURE")
        schema = self._connection.execute("SELECT name,type,sql FROM sqlite_schema WHERE name NOT GLOB 'sqlite_*'").fetchall()
        if {name: sql for name, kind, sql in schema if kind == "table"} != self._schema or len(schema) != len(self._schema):
            raise ContractError("JOURNAL_SCHEMA_MISMATCH")
        if self._connection.execute("SELECT * FROM history_meta").fetchall() != [(1, self._profile)]:
            raise ContractError("JOURNAL_PROFILE_MISMATCH")
        rows = self._connection.execute("SELECT scope_id,next_sequence,head FROM history_scopes ORDER BY scope_id").fetchall()
        if tuple(row[0] for row in rows) != self._scopes:
            raise ContractError("JOURNAL_SCOPE_REGISTRY_MISMATCH")
        if self._connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise ContractError("JOURNAL_FOREIGN_KEY_CORRUPTION")
        positions = {scope: StreamPosition(scope, 0, None) for scope in self._scopes}
        if (type(checkpoints) is not tuple or any(type(point) is not StreamPosition for point in checkpoints)
                or len({point.scope_id for point in checkpoints}) != len(checkpoints)):
            raise ContractError("JOURNAL_CHECKPOINT_SET_INVALID")
        anchors = {point.scope_id: point for point in checkpoints}
        for scope in anchors:
            self._require_scope(scope)
        matched = {scope for scope, point in anchors.items() if point == positions[scope]}
        cursor = self._connection.execute("SELECT scope_id,sequence,event_id,event_wire,payload_wire,event_head,original_event_sha256,original_payload_sha256 FROM history_events ORDER BY scope_id,sequence")
        for scope, sequence, event_id, event_wire, payload_wire, head, event_sha, payload_sha in cursor:
            if scope not in positions or type(event_wire) is not bytes or type(payload_wire) is not bytes:
                raise ContractError("JOURNAL_INVALID_ROW")
            event = self._events.require_successor(event_wire, positions[scope])
            self._events.require_payload(event_wire, payload_wire)
            if (sequence != positions[scope].next_sequence or event.record.record_id != event_id
                    or head != event.head or _digest(event_wire) != event_sha or _digest(payload_wire) != payload_sha):
                raise ContractError("JOURNAL_PREFIX_MISMATCH")
            positions[scope] = StreamPosition(scope, sequence + 1, event.head)
            if anchors.get(scope) == positions[scope]:
                matched.add(scope)
        for scope, sequence, head in rows:
            if StreamPosition(scope, sequence, head) != positions[scope]:
                raise ContractError("JOURNAL_POSITION_MISMATCH")
        if set(anchors) != matched:
            raise ContractError("JOURNAL_CHECKPOINT_MISMATCH")
        if self._state is not None:
            self._state.verify(state_checkpoint)
        elif state_checkpoint is not None:
            raise ContractError("STORE_PROFILE_REQUIRED")
        return tuple(positions[scope] for scope in self._scopes)

    def validate(self, checkpoints=()):
        """Rehash the complete prefix; checkpoints are inputs, not trust proofs."""
        with self._lock:
            self._require_open()
            try:
                self._connection.execute("BEGIN")
                result = self._verify(checkpoints)
                self._connection.execute("COMMIT")
                return result
            except BaseException as primary:
                self._rollback_after_error(primary)
                raise

    def position(self, scope_id):
        self._require_scope(scope_id)
        return next(point for point in self.validate() if point.scope_id == scope_id)

    def append(self, expected, entries, *, checkpoints=()):
        self._require_writable()
        if type(expected) is not StreamPosition:
            raise ContractError("JOURNAL_EXPECTED_POSITION_REQUIRED")
        self._require_scope(expected.scope_id)
        if (type(entries) is not tuple or not 1 <= len(entries) <= 128
                or any(type(entry) is not JournalEntry for entry in entries)):
            raise ContractError("JOURNAL_BOUNDED_BATCH_REQUIRED")
        prepared, after = [], expected
        for entry in entries:
            event = self._events.require_successor(entry.event_wire, after)
            self._events.require_payload(entry.event_wire, entry.payload_wire)
            prepared.append((entry, event))
            after = StreamPosition(expected.scope_id, after.next_sequence + 1, event.head)
        if self._state is not None:
            result = self.commit((expected,), entries, checkpoints=checkpoints)
            return result.history[0]
        with self._lock:
            self._require_writable()
            retained_capacity = self._capacity_active
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                current = next(point for point in self._verify(checkpoints) if point.scope_id == expected.scope_id)
                if current != expected:
                    raise ContractError("JOURNAL_REVISION_CONFLICT")
                for entry, event in prepared:
                    value = event.record.as_dict()
                    self._connection.execute("INSERT INTO history_events VALUES(?,?,?,?,?,?,?,?)", (
                        expected.scope_id, value["sequence"], event.record.record_id, entry.event_wire,
                        entry.payload_wire, event.head, _digest(entry.event_wire), _digest(entry.payload_wire)))
                self._connection.execute("UPDATE history_scopes SET next_sequence=?,head=? WHERE scope_id=?", (
                    after.next_sequence, after.head, expected.scope_id))
                if self._fault is not None:
                    self._fault()
                self._connection.execute("COMMIT")
            except BaseException as primary:
                self._rollback_after_error(primary)
                raise
        return self._capacity_commit(entries,
            JournalCommit(expected, after, tuple(event.record.record_id for _, event in prepared)), retained_capacity)

    def commit(self, expected, entries, *, checks=(), changes=(), checkpoints=(), state_checkpoint=None, guard=None):
        self._require_writable()
        """One owner transaction; cells and status fields confer no authority."""
        if self._state is None:
            raise ContractError("STORE_PROFILE_REQUIRED")
        if guard is not None and not callable(guard):
            raise ContractError("STORE_COMMIT_GUARD_INVALID")
        if (type(expected) is not tuple or not 1 <= len(expected) <= 128
                or any(type(point) is not StreamPosition for point in expected)
                or len({point.scope_id for point in expected}) != len(expected)):
            raise ContractError("STORE_EXPECTED_SCOPES_REQUIRED")
        if (type(entries) is not tuple or not 1 <= len(entries) <= 128
                or any(type(entry) is not JournalEntry for entry in entries)):
            raise ContractError("JOURNAL_BOUNDED_BATCH_REQUIRED")
        if (type(checks) is not tuple or len(checks) > 128
                or any(type(check) is not StoreExpectation for check in checks)
                or len({check.key for check in checks}) != len(checks)):
            raise ContractError("STORE_CHECK_SET_INVALID")
        if (type(changes) is not tuple or len(changes) > 128
                or any(type(change) is not StoreChange for change in changes)
                or len({change.expected.key for change in changes}) != len(changes)):
            raise ContractError("STORE_CHANGE_SET_INVALID")
        after = {point.scope_id: point for point in expected}
        for scope in after:
            self._require_scope(scope)
        prepared, event_ids = [], {scope: [] for scope in after}
        for entry in entries:
            scope = self._events.preimages(entry.event_wire).record.as_dict()["scope_id"]
            if scope not in after:
                raise ContractError("STORE_EVENT_SCOPE_NOT_EXPECTED")
            event = self._events.require_successor(entry.event_wire, after[scope])
            self._events.require_payload(entry.event_wire, entry.payload_wire)
            after[scope] = StreamPosition(scope, after[scope].next_sequence + 1, event.head)
            prepared.append((entry, event))
            event_ids[scope].append(event.record.record_id)
        if any(not identifiers for identifiers in event_ids.values()):
            raise ContractError("STORE_EXPECTED_SCOPE_WITHOUT_EVENT")
        with self._lock:
            self._require_writable()
            retained_capacity = self._capacity_active
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                current = {point.scope_id: point for point in self._verify(checkpoints, state_checkpoint)}
                if any(current[point.scope_id] != point for point in expected):
                    raise ContractError("JOURNAL_REVISION_CONFLICT")
                for entry, event in prepared:
                    value = event.record.as_dict()
                    self._connection.execute("INSERT INTO history_events VALUES(?,?,?,?,?,?,?,?)", (
                        value["scope_id"], value["sequence"], event.record.record_id, entry.event_wire,
                        entry.payload_wire, event.head, _digest(entry.event_wire), _digest(entry.payload_wire)))
                position, cells = self._state.insert(prepared, checks, changes)
                for point in after.values():
                    self._connection.execute("UPDATE history_scopes SET next_sequence=?,head=? WHERE scope_id=?",
                        (point.next_sequence, point.head, point.scope_id))
                if self._fault is not None:
                    self._fault()
                if guard is not None:
                    guard()
                self._connection.execute("COMMIT")
            except BaseException as primary:
                self._rollback_after_error(primary)
                raise
        return self._capacity_commit(entries,
            StoreCommit(tuple(JournalCommit(point, after[point.scope_id], tuple(event_ids[point.scope_id]))
                                 for point in expected), position, cells), retained_capacity)

    def snapshot(self, keys, *, state_checkpoint=None):
        if self._state is None:
            raise ContractError("STORE_PROFILE_REQUIRED")
        if (type(keys) is not tuple or not 1 <= len(keys) <= 128
                or any(type(key) is not StoreKey for key in keys) or len(set(keys)) != len(keys)):
            raise ContractError("STORE_SNAPSHOT_KEYS_REQUIRED")
        for key in keys:
            self._require_scope(key.scope_id)
        with self._lock:
            self._require_open()
            try:
                self._connection.execute("BEGIN")
                self._verify(state_checkpoint=state_checkpoint)
                result = tuple(self._state.read(key) for key in keys)
                self._connection.execute("COMMIT")
                return result
            except BaseException as primary:
                self._rollback_after_error(primary)
                raise

    def store_position(self):
        if self._state is None:
            raise ContractError("STORE_PROFILE_REQUIRED")
        with self._lock:
            self._require_open()
            try:
                self._connection.execute("BEGIN")
                self._verify()
                result = self._state.position()
                self._connection.execute("COMMIT")
                return result
            except BaseException as primary:
                self._rollback_after_error(primary)
                raise

    def replay(self, scope_id, start=0, limit=128, *, checkpoints=()):
        self._require_scope(scope_id)
        if type(start) is not int or not 0 <= start <= 2**53 - 1 or type(limit) is not int or not 1 <= limit <= 128:
            raise ContractError("JOURNAL_READ_BOUND_REQUIRED")
        with self._lock:
            self._require_open()
            try:
                self._connection.execute("BEGIN")
                self._verify(checkpoints)
                rows = self._connection.execute("SELECT event_wire,payload_wire FROM history_events WHERE scope_id=? AND sequence>=? ORDER BY sequence LIMIT ?", (scope_id, start, limit)).fetchall()
                self._connection.execute("COMMIT")
                return tuple(JournalEntry(*row) for row in rows)
            except BaseException as primary:
                self._rollback_after_error(primary)
                raise

    def projection(self, scope_id, *, expected_position=None, checkpoints=(), registrations=()):
        """Read one scope's derivable references in a validated SQLite snapshot.

        This internal owner query confers no permission. Unknown event semantics
        reject the view, preserving journal and store bytes. No projection table,
        normal-profile read, external callback or new writer is introduced.
        """
        self._require_scope(scope_id)
        if expected_position is not None and type(expected_position) is not StreamPosition:
            raise ContractError("JOURNAL_PROJECTION_POSITION_REQUIRED")
        if expected_position is not None:
            expected_position = StreamPosition(expected_position.scope_id,
                expected_position.next_sequence, expected_position.head)
        if type(checkpoints) is not tuple or any(type(point) is not StreamPosition for point in checkpoints):
            raise ContractError("JOURNAL_CHECKPOINT_SET_INVALID")
        checkpoints = tuple(StreamPosition(point.scope_id, point.next_sequence, point.head) for point in checkpoints)
        reducer = ProjectionReducer(self._codec, registrations=registrations)
        with self._lock:
            self._require_open()
            try:
                self._connection.execute("BEGIN")
                current = next(point for point in self._verify(checkpoints) if point.scope_id == scope_id)
                if expected_position is not None and expected_position != current:
                    raise ContractError("JOURNAL_PROJECTION_REVISION_CONFLICT")
                entries, byte_count = [], 0
                cursor = self._connection.execute("SELECT event_wire,payload_wire FROM history_events WHERE scope_id=? ORDER BY sequence", (scope_id,))
                for event_wire, payload_wire in cursor:
                    byte_count += len(event_wire) + len(payload_wire)
                    if len(entries) >= MAX_PROJECTION_EVENTS or byte_count > MAX_PROJECTION_BYTES:
                        raise ContractError("JOURNAL_PROJECTION_BOUND_EXCEEDED")
                    entries.append(JournalEntry(event_wire, payload_wire))
                result = reducer.rebuild(scope_id, tuple(entries), expected_position=current)
                self._connection.execute("COMMIT")
                return result
            except BaseException as primary:
                self._rollback_after_error(primary, projection=True)
                raise

    def backup(self, destination_root, *, checkpoints=(), state_checkpoint=None,
               pages_per_step=128, timeout_seconds=60, progress=None):
        """Create an independently validated, non-overwriting online snapshot."""
        from .backups import BackupManager
        return BackupManager(self).snapshot(destination_root, checkpoints=checkpoints,
            state_checkpoint=state_checkpoint, pages_per_step=pages_per_step,
            timeout_seconds=timeout_seconds, progress=progress)

    def storage_identity(self):
        with self._lock:
            self._require_open()
            values = {name: self._connection.execute("PRAGMA " + name).fetchone()[0]
                      for name in ("journal_mode", "synchronous", "foreign_keys", "busy_timeout", "locking_mode", "wal_autocheckpoint")}
            return {"runtime": runtime_identity(), "path": str(self.path), "settings": values,
                    "filesystem": "LOCAL_FIXED_NTFS", "power_loss_qualification": "NOT_RUN",
                    "protected_writer_or_independent_anchor": "NOT_ESTABLISHED", "read_only": self._read_only}

    def close(self):
        with self._lock:
            if self._capacity_active is not None:
                denied = ContractError("JOURNAL_OUTCOME_CAPACITY_RETAINED")
                data = self._retain_failure(denied)
                dict.update(data, outcome_capacity_custody=self._capacity_active)
                raise denied
            if self._constructor_close_state == "UNCERTAIN":
                raise ContractError("JOURNAL_CONSTRUCTOR_CLOSE_UNCERTAIN")
            if self._connection_close_state == "UNCERTAIN":
                denied = ContractError("JOURNAL_CLOSE_UNCERTAIN")
                self._retain_failure(denied)
                raise denied
            if not self._closed:
                self._connection_close_state = "UNCERTAIN"
                try:
                    response = self._connection.close()
                    if response is not None:
                        raise ContractError("JOURNAL_CLOSE_RESULT_INVALID")
                except BaseException as primary:
                    self._connection_close_error = primary
                    self._retain_failure(primary)
                    raise
                self._connection_close_state = "CLOSED"
                self._closed = True
            if self._capacity_vfs is not None:
                self._capacity_vfs.close()
