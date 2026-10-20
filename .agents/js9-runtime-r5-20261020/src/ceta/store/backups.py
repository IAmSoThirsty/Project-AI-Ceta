"""Consistent SQLite snapshots and preserved, read-only recovery copies.

The online backup API copies an actual pinned SQLite read transaction. A final
manifest is published only after the destination's complete history and store
prefix have been validated. Interrupted directories remain inspectable and
cannot be used as complete backups. Restore never activates an authority writer.

This owner-side adapter assumes its directories are under the application's
existing filesystem custody. Endpoint identity checks detect observed changes;
they do not establish a hostile-process filesystem exclusion boundary.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import time
import uuid

from ceta.contracts.events import StreamPosition
from ceta.contracts.store_transactions import STORE_PROFILE, StorePosition, commitment
from ceta.contracts.wire import ContractError, RecordCodec, canonical_bytes, strict_loads
from .journal import SqliteJournal, _location
from .sqlite_runtime import load_sqlite, runtime_identity


BACKUP_PROFILE = "ceta-sqlite-backup-v1"
RESTORE_PROFILE = "ceta-sqlite-recovery-copy-v1"
_MANIFEST = "ceta-backup-complete.json"
_RESTORED = "ceta-restore-complete.json"
_INTENT = "ceta-backup-intent.json"
_RESTORE_INTENT = "ceta-restore-intent.json"
_JOURNAL_PROFILE = "ceta-sqlite-journal-v1"
_MAX_MANIFEST = 1024 * 1024
_MAX_DATABASE = 1024 * 1024 * 1024 * 1024
_DOCUMENT_KEYS = frozenset({"profile", "operation_id", "created_at_utc", "intent_sha256",
    "database_sha256", "database_bytes", "schema_sha256", "journal_profile", "scopes",
    "positions", "store_position", "sqlite_version", "sqlite_dll_sha256", "parent_manifest_sha256",
    "state", "authority", "power_loss_qualification"})


def _require(value, code):
    if value is not True:
        raise ContractError(code)


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _utc():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _identity(path):
    value = path.stat()
    return value.st_dev, value.st_ino


def _read(path, limit):
    _require(path.is_file() and not path.is_symlink() and not path.is_junction(),
        "BACKUP_REGULAR_FILE_REQUIRED")
    before = path.stat()
    _require(before.st_nlink == 1 and 0 < before.st_size <= limit, "BACKUP_FILE_BOUND_OR_ALIAS")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        raw = stream.read(limit + 1)
        after_open = os.fstat(stream.fileno())
    after = path.stat()
    signature = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
    _require(signature(before) == signature(opened) == signature(after_open) == signature(after)
        and len(raw) == before.st_size, "BACKUP_FILE_CHANGED")
    return raw


def _database_identity(path):
    _require(path.is_file() and not path.is_symlink() and not path.is_junction(),
        "BACKUP_DATABASE_REQUIRED")
    before = path.stat()
    _require(before.st_nlink == 1 and 0 < before.st_size <= _MAX_DATABASE, "BACKUP_DATABASE_BOUND_OR_ALIAS")
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        while block := stream.read(1024 * 1024):
            size += len(block)
            _require(size <= _MAX_DATABASE, "BACKUP_DATABASE_BOUND_OR_ALIAS")
            digest.update(block)
        after_open = os.fstat(stream.fileno())
    after = path.stat()
    signature = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
    _require(signature(before) == signature(opened) == signature(after_open) == signature(after)
        and size == before.st_size, "BACKUP_DATABASE_CHANGED")
    return digest.hexdigest(), size


def _write_new(path, raw):
    with path.open("xb") as stream:
        written = stream.write(raw)
        _require(written == len(raw), "BACKUP_SHORT_WRITE")
        stream.flush()
        os.fsync(stream.fileno())
    _require(_read(path, max(len(raw), 1)) == raw, "BACKUP_NEW_FILE_READBACK_MISMATCH")


def _companions(path):
    # A sealed standalone snapshot must not depend on unapplied WAL/journal data.
    # SQLite may create an empty WAL and an SHM index during read-only validation.
    for suffix in ("-wal", "-journal", "-shm"):
        companion = Path(str(path) + suffix)
        if companion.exists():
            _require(not companion.is_symlink() and not companion.is_junction()
                and companion.is_file() and companion.stat().st_nlink == 1, "BACKUP_COMPANION_ALIAS")
            if suffix != "-shm":
                _require(companion.stat().st_size == 0, "BACKUP_UNCHECKPOINTED_COMPANION")


def _positions(values):
    _require(type(values) is tuple and 1 <= len(values) <= 1024, "BACKUP_POSITIONS_REQUIRED")
    result = []
    for item in values:
        _require(type(item) is StreamPosition, "BACKUP_POSITION_TYPE")
        result.append(StreamPosition(item.scope_id, item.next_sequence, item.head))
    _require(tuple(item.scope_id for item in result) == tuple(sorted({item.scope_id for item in result})),
        "BACKUP_POSITION_ORDER_OR_DUPLICATE")
    return tuple(result)


def _point_wire(point):
    return {"scope_id": point.scope_id, "next_sequence": point.next_sequence, "head": point.head}


def _store_wire(point):
    return None if point is None else {"next_commit": point.next_commit, "head": point.head}


def _close(resource, primary=None):
    if resource is None:
        return
    try:
        resource.close()
    except BaseException:
        if primary is None:
            raise
        try:
            BaseException.add_note(primary, "BACKUP_CLOSE_UNOBSERVED")
        except BaseException:
            pass


@dataclass(frozen=True, slots=True)
class BackupProgress:
    phase: str
    sqlite_status: int
    remaining_pages: int
    total_pages: int

    def __post_init__(self):
        _require(type(self.phase) is str and self.phase in {"SNAPSHOT", "RESTORE"}, "BACKUP_PROGRESS_PHASE")
        _require(all(type(value) is int and value >= 0 for value in
            (self.sqlite_status, self.remaining_pages, self.total_pages))
            and self.remaining_pages <= self.total_pages, "BACKUP_PROGRESS_VALUES")


@dataclass(frozen=True, slots=True)
class BackupSnapshot:
    """An immutable inspected manifest, not a capability to activate the store."""
    root: str
    manifest_wire: bytes

    def __post_init__(self):
        _require(type(self.root) is str and Path(self.root).is_absolute(), "BACKUP_ROOT_REQUIRED")
        _require(type(self.manifest_wire) is bytes and 0 < len(self.manifest_wire) <= _MAX_MANIFEST,
            "BACKUP_MANIFEST_WIRE_REQUIRED")
        document = strict_loads(self.manifest_wire)
        _validate_document(document)
        _require(canonical_bytes(document) == self.manifest_wire, "BACKUP_MANIFEST_NOT_CANONICAL")

    @property
    def sha256(self):
        return _sha(self.manifest_wire)

    def as_dict(self):
        return strict_loads(self.manifest_wire)

    @property
    def positions(self):
        return tuple(StreamPosition(**row) for row in self.as_dict()["positions"])

    @property
    def store_position(self):
        value = self.as_dict()["store_position"]
        return None if value is None else StorePosition(**value)


def _validate_document(value):
    _require(type(value) is dict and set(value) == _DOCUMENT_KEYS, "BACKUP_MANIFEST_FIELDS")
    _require(type(value["profile"]) is str and value["profile"] in {BACKUP_PROFILE, RESTORE_PROFILE},
        "BACKUP_PROFILE_UNSUPPORTED")
    _require(type(value["operation_id"]) is str and len(value["operation_id"]) == 32
        and all(character in "0123456789abcdef" for character in value["operation_id"]), "BACKUP_OPERATION_ID")
    stamp = value["created_at_utc"]
    _require(type(stamp) is str and len(stamp) == 27 and stamp.endswith("Z"), "BACKUP_TIMESTAMP")
    try:
        parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError as error:
        raise ContractError("BACKUP_TIMESTAMP") from error
    _require(parsed.isoformat(timespec="microseconds").replace("+00:00", "Z") == stamp, "BACKUP_TIMESTAMP")
    for name in ("intent_sha256", "database_sha256", "schema_sha256", "sqlite_dll_sha256"):
        _require(type(value[name]) is str, "BACKUP_HASH_TYPE")
        commitment("sha256:" + value[name])
    parent = value["parent_manifest_sha256"]
    if parent is not None:
        _require(type(parent) is str, "BACKUP_PARENT_HASH_TYPE")
        commitment("sha256:" + parent)
    _require((value["profile"] == BACKUP_PROFILE) == (parent is None), "BACKUP_PARENT_PROFILE")
    _require(type(value["database_bytes"]) is int and 0 < value["database_bytes"] <= _MAX_DATABASE,
        "BACKUP_DATABASE_BOUND_OR_ALIAS")
    _require(type(value["journal_profile"]) is str
        and value["journal_profile"] in {_JOURNAL_PROFILE, STORE_PROFILE}, "BACKUP_JOURNAL_PROFILE")
    _require(type(value["scopes"]) is list and type(value["positions"]) is list, "BACKUP_SCOPE_FIELDS")
    points = []
    for row in value["positions"]:
        _require(type(row) is dict and set(row) == {"scope_id", "next_sequence", "head"}, "BACKUP_POSITION_FIELDS")
        points.append(StreamPosition(**row))
    points = _positions(tuple(points))
    _require(value["scopes"] == [point.scope_id for point in points], "BACKUP_SCOPE_BINDING")
    state = value["store_position"]
    if state is not None:
        _require(type(state) is dict and set(state) == {"next_commit", "head"}, "BACKUP_STORE_POSITION_FIELDS")
        StorePosition(**state)
    _require((value["journal_profile"] == STORE_PROFILE) == (state is not None), "BACKUP_STORE_POSITION_PROFILE")
    _require(type(value["sqlite_version"]) is str and 1 <= len(value["sqlite_version"]) <= 64,
        "BACKUP_SQLITE_VERSION")
    _require(value["state"] == "COMPLETE" and value["authority"] == "HISTORICAL_ONLY_REVALIDATION_REQUIRED"
        and value["power_loss_qualification"] == "NOT_ESTABLISHED", "BACKUP_CLAIM_UNSUPPORTED")


class BackupManager:
    """The store owner's bounded online backup and non-activating restore seam.

    Source and destination connections are distinct. The pinned source read
    transaction fixes which prefix is copied while another WAL writer continues.
    ``progress`` is a trusted local cancellation/telemetry callback, never IPC
    input, and receives no database handle. Raising interrupts the copy.
    """
    def __init__(self, journal):
        _require(type(journal) is SqliteJournal, "BACKUP_JOURNAL_REQUIRED")
        with journal._lock:
            journal._require_open()
            self._root = journal.path.parent
            self._scopes = journal._scopes
            self._profile = journal._profile
            self._schema = canonical_bytes(journal._codec._schema)
        self._codec = RecordCodec(strict_loads(self._schema))
        self._sqlite = load_sqlite()

    def _reader(self, root):
        return SqliteJournal(root, self._codec, self._scopes, profile=self._profile, read_only=True)

    def _validated_prefix(self, reader, checkpoints, state_checkpoint):
        points = _positions(reader._verify(checkpoints, state_checkpoint))
        state = reader._state.position() if reader._state is not None else None
        return points, state

    def _copy(self, source_root, destination_root, *, phase, parent=None, checkpoints=(),
              state_checkpoint=None, pages_per_step=128, timeout_seconds=60, progress=None):
        _require(type(pages_per_step) is int and 1 <= pages_per_step <= 4096, "BACKUP_PAGE_BOUND")
        _require(type(timeout_seconds) is int and 1 <= timeout_seconds <= 3600, "BACKUP_TIME_BOUND")
        _require(progress is None or callable(progress), "BACKUP_PROGRESS_CALLBACK")
        _require(type(checkpoints) is tuple, "BACKUP_CHECKPOINT_SET")
        checkpoints = tuple(StreamPosition(point.scope_id, point.next_sequence, point.head)
            if type(point) is StreamPosition else self._invalid_checkpoint() for point in checkpoints)
        if state_checkpoint is not None:
            _require(type(state_checkpoint) is StorePosition, "BACKUP_STORE_CHECKPOINT")
            state_checkpoint = StorePosition(state_checkpoint.next_commit, state_checkpoint.head)
        source_path = _location(source_root)
        target = _location(destination_root)
        _require(source_path != target and source_path.parent != target.parent,
            "BACKUP_SOURCE_DESTINATION_EQUAL")
        _require(not any(target.parent.iterdir()), "BACKUP_DESTINATION_NOT_EMPTY")
        source_identity, directory_identity = _identity(source_path), _identity(target.parent)
        operation_id = uuid.uuid4().hex
        intent_name, final_name = (_INTENT, _MANIFEST) if phase == "SNAPSHOT" else (_RESTORE_INTENT, _RESTORED)
        intent = canonical_bytes({"profile": BACKUP_PROFILE if phase == "SNAPSHOT" else RESTORE_PROFILE,
            "operation_id": operation_id, "source_database": str(source_path), "phase": phase,
            "schema_sha256": _sha(self._schema), "parent_manifest_sha256": parent})
        intent_path = target.parent / intent_name
        _write_new(intent_path, intent)
        _require({item.name for item in target.parent.iterdir()} == {intent_name}, "BACKUP_DESTINATION_CHANGED")
        descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        destination_identity = _identity(target)
        deadline = time.monotonic() + timeout_seconds
        source, destination = None, None
        primary = None

        def current():
            _require(time.monotonic() < deadline, "BACKUP_DEADLINE_EXCEEDED")
            _require(_location(source_path.parent) == source_path and _identity(source_path) == source_identity
                and _location(target.parent) == target and _identity(target.parent) == directory_identity
                and _identity(target) == destination_identity, "BACKUP_PATH_IDENTITY_CHANGED")
            _require(_read(intent_path, _MAX_MANIFEST) == intent, "BACKUP_INTENT_CHANGED")

        def step(status, remaining, total):
            current()
            observation = BackupProgress(phase, status, remaining, total)
            if progress is not None:
                progress(observation)
            current()

        try:
            current()
            source = self._reader(source_path.parent)
            source._connection.execute("BEGIN")
            points, state = self._validated_prefix(source, checkpoints, state_checkpoint)
            current()
            destination = self._sqlite.connect(target.as_uri() + "?mode=rw", uri=True,
                isolation_level=None, timeout=0.1)
            destination.setconfig(self._sqlite.SQLITE_DBCONFIG_DEFENSIVE, True)
            destination.setconfig(self._sqlite.SQLITE_DBCONFIG_TRUSTED_SCHEMA, False)
            destination.enable_load_extension(False)
            destination.execute("PRAGMA synchronous=FULL")
            source._connection.backup(destination, pages=pages_per_step, progress=step, sleep=0.01)
            current()
            source._connection.execute("COMMIT")
            _require(destination.execute("PRAGMA journal_mode=WAL").fetchone() == ("wal",),
                "BACKUP_STORAGE_PROFILE_MISMATCH")
            checkpointed = destination.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            _require(checkpointed is not None and checkpointed[0] == 0, "BACKUP_CHECKPOINT_INCOMPLETE")
            # Relinquish each local close attempt before invoking it. A close
            # exception must not cause an unobserved second close in finally.
            closed_destination, destination = destination, None
            _close(closed_destination)
            closed_source, source = source, None
            _close(closed_source)
            current()
            _companions(target)
            verifier = self._reader(target.parent)
            verifier_primary = None
            try:
                verifier._connection.execute("BEGIN")
                actual_points, actual_state = self._validated_prefix(verifier, points, state)
                _require(actual_points == points and actual_state == state, "BACKUP_PREFIX_DIVERGENCE")
                verifier._connection.execute("COMMIT")
            except BaseException as error:
                verifier_primary = error
                raise
            finally:
                _close(verifier, verifier_primary)
            _companions(target)
            # Windows FlushFileBuffers requires a writable handle. This is
            # the exclusively created destination, never the source journal.
            with target.open("r+b") as durable:
                opened = os.fstat(durable.fileno())
                _require((opened.st_dev, opened.st_ino) == destination_identity
                    and opened.st_nlink == 1, "BACKUP_PATH_IDENTITY_CHANGED")
                os.fsync(durable.fileno())
            database_sha, database_bytes = _database_identity(target)
            current()
            runtime = runtime_identity()
            document = {"profile": BACKUP_PROFILE if phase == "SNAPSHOT" else RESTORE_PROFILE,
                "operation_id": operation_id, "created_at_utc": _utc(), "intent_sha256": _sha(intent),
                "database_sha256": database_sha, "database_bytes": database_bytes,
                "schema_sha256": _sha(self._schema), "journal_profile": self._profile,
                "scopes": list(self._scopes), "positions": [_point_wire(point) for point in points],
                "store_position": _store_wire(state), "sqlite_version": runtime["version"],
                "sqlite_dll_sha256": runtime["dll_sha256"], "parent_manifest_sha256": parent,
                "state": "COMPLETE", "authority": "HISTORICAL_ONLY_REVALIDATION_REQUIRED",
                "power_loss_qualification": "NOT_ESTABLISHED"}
            manifest = canonical_bytes(document)
            result = BackupSnapshot(str(target.parent), manifest)
            # Runtime identity and manifest construction are callbacks/boundaries.
            # Recheck the retained intent and validated bytes before completion.
            current()
            _companions(target)
            _require(_database_identity(target) == (database_sha, database_bytes),
                "BACKUP_DATABASE_CHANGED")
            _write_new(target.parent / final_name, manifest)
            current()
            _companions(target)
            _require(_database_identity(target) == (database_sha, database_bytes),
                "BACKUP_DATABASE_CHANGED")
            return result
        except BaseException as error:
            primary = error
            raise
        finally:
            _close(destination, primary)
            _close(source, primary)

    @staticmethod
    def _invalid_checkpoint():
        raise ContractError("BACKUP_CHECKPOINT_TYPE")

    def snapshot(self, destination_root, *, checkpoints=(), state_checkpoint=None,
                 pages_per_step=128, timeout_seconds=60, progress=None):
        return self._copy(self._root, destination_root, phase="SNAPSHOT", checkpoints=checkpoints,
            state_checkpoint=state_checkpoint, pages_per_step=pages_per_step,
            timeout_seconds=timeout_seconds, progress=progress)

    def inspect(self, root, *, checkpoints=(), state_checkpoint=None):
        """Re-read completion bytes and the entire accepted prefix, without activation."""
        database = _location(root)
        choices = [(name, intent) for name, intent in ((_MANIFEST, _INTENT), (_RESTORED, _RESTORE_INTENT))
            if (database.parent / name).exists()]
        _require(len(choices) == 1, "BACKUP_INCOMPLETE_OR_AMBIGUOUS")
        name, intent_name = choices[0]
        raw = _read(database.parent / name, _MAX_MANIFEST)
        result = BackupSnapshot(str(database.parent), raw)
        document = result.as_dict()
        _require((name == _MANIFEST) == (document["profile"] == BACKUP_PROFILE), "BACKUP_MANIFEST_PROFILE")
        _require(document["schema_sha256"] == _sha(self._schema)
            and document["journal_profile"] == self._profile and document["scopes"] == list(self._scopes),
            "BACKUP_CONTRACT_MISMATCH")
        runtime = runtime_identity()
        _require(document["sqlite_version"] == runtime["version"]
            and document["sqlite_dll_sha256"] == runtime["dll_sha256"], "BACKUP_RUNTIME_MISMATCH")
        intent_wire = _read(database.parent / intent_name, _MAX_MANIFEST)
        _require(_sha(intent_wire) == document["intent_sha256"], "BACKUP_INTENT_MISMATCH")
        intent = strict_loads(intent_wire)
        _require(type(intent) is dict and set(intent) == {"profile", "operation_id", "source_database", "phase",
            "schema_sha256", "parent_manifest_sha256"} and canonical_bytes(intent) == intent_wire,
            "BACKUP_INTENT_FIELDS")
        _require(intent["operation_id"] == document["operation_id"] and intent["profile"] == document["profile"]
            and intent["schema_sha256"] == document["schema_sha256"]
            and intent["parent_manifest_sha256"] == document["parent_manifest_sha256"]
            and intent["phase"] == ("SNAPSHOT" if name == _MANIFEST else "RESTORE")
            and type(intent["source_database"]) is str and Path(intent["source_database"]).is_absolute(),
            "BACKUP_INTENT_BINDING")
        _companions(database)
        expected_database = document["database_sha256"], document["database_bytes"]
        _require(_database_identity(database) == expected_database, "BACKUP_DATABASE_MISMATCH")
        reader = self._reader(database.parent)
        reader_primary = None
        try:
            reader._connection.execute("BEGIN")
            points, state = self._validated_prefix(reader, checkpoints, state_checkpoint)
            _require(points == result.positions and state == result.store_position, "BACKUP_MANIFEST_PREFIX_MISMATCH")
            reader._connection.execute("COMMIT")
        except BaseException as error:
            reader_primary = error
            raise
        finally:
            _close(reader, reader_primary)
        _companions(database)
        _require(_database_identity(database) == expected_database
            and _read(database.parent / name, _MAX_MANIFEST) == raw
            and _read(database.parent / intent_name, _MAX_MANIFEST) == intent_wire, "BACKUP_CHANGED_DURING_INSPECTION")
        return result

    def restore(self, backup_root, destination_root, *, checkpoints=(), state_checkpoint=None,
                pages_per_step=128, timeout_seconds=60, progress=None):
        """Copy into a fresh historical recovery root; no prior store is replaced."""
        accepted = self.inspect(backup_root, checkpoints=checkpoints, state_checkpoint=state_checkpoint)
        _require(accepted.as_dict()["profile"] == BACKUP_PROFILE, "RESTORE_ORIGINAL_BACKUP_REQUIRED")
        result = self._copy(accepted.root, destination_root, phase="RESTORE", parent=accepted.sha256,
            checkpoints=accepted.positions, state_checkpoint=accepted.store_position,
            pages_per_step=pages_per_step, timeout_seconds=timeout_seconds, progress=progress)
        # A source modified during restore makes the result unavailable to the
        # caller even if it reached a mechanically complete recovery-copy state.
        current = self.inspect(backup_root, checkpoints=accepted.positions,
            state_checkpoint=accepted.store_position)
        _require(current.manifest_wire == accepted.manifest_wire, "RESTORE_SOURCE_CHANGED")
        return result


__all__ = ["BACKUP_PROFILE", "RESTORE_PROFILE", "BackupProgress", "BackupSnapshot", "BackupManager"]
