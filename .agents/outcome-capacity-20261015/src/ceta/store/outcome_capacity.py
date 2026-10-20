"""Physical capacity on the selected journal's own DB, WAL and SHM files.

The VFS bounds actual writes into measured allocations. This is a storage
prerequisite, not permission to execute or a promise against device failure.
Only the composition root may select a qualified native helper.
"""
from __future__ import annotations

import ctypes
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import threading
from types import TracebackType
import uuid

from ceta.contracts.wire import ContractError
from .sqlite_runtime import DLL_PATH, load_sqlite

MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_MEMORY_BYTES = 1024 * 1024
ALIGNMENT = 65536
_IDLE, _ALLOCATING, _RETAINED, _FAILED, _CLOSED = range(5)
_ABSENT, _OPEN, _UNCERTAIN, _RETIRED = range(4)


def _require(condition, code):
    if condition is not True:
        raise ContractError(code)


def _expose(primary, owner, secondary=None):
    data = BaseException.__dict__["__dict__"].__get__(primary)
    dict.update(data, outcome_capacity_custody=owner,
                outcome_capacity_cleanup_error=secondary)


@dataclass(frozen=True)
class OutcomeCapacityBudget:
    """Absolute per-file ceilings, plus one bounded in-memory outcome slot."""
    database_bytes: int
    wal_bytes: int
    shm_bytes: int
    memory_bytes: int = 262144

    def __post_init__(self):
        amounts = (self.database_bytes, self.wal_bytes, self.shm_bytes)
        _require(all(type(n) is int and ALIGNMENT <= n <= MAX_FILE_BYTES
                     and n % ALIGNMENT == 0 for n in amounts)
                 and sum(amounts) <= MAX_FILE_BYTES, "OUTCOME_CAPACITY_FILE_BOUNDS")
        _require(type(self.memory_bytes) is int and 1 <= self.memory_bytes <= MAX_MEMORY_BYTES,
                 "OUTCOME_CAPACITY_MEMORY_BOUND")


class _FileFacts(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint64) for name in
                ("handle", "volume", "allocation", "eof", "limit")] + [
        ("identifier", ctypes.c_ubyte * 16)] + [(name, ctypes.c_uint32) for name in
        ("close_state", "close_error", "post_close_error", "attributes")]


class _Snapshot(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint32) for name in ("version", "state", "reason", "winerror")] + [
        (name, ctypes.c_uint64) for name in ("generation", "write_calls", "sync_calls",
        "db_highwater", "wal_highwater", "shm_highwater")] + [
        ("open_files", ctypes.c_uint32), ("winerror_known", ctypes.c_uint32),
        ("files", _FileFacts * 3), ("mapped_shm_probe", _FileFacts)]


def _facts(value):
    def file(row):
        return {name: (bytes(row.identifier).hex() if name == "identifier" else getattr(row, name))
                for name, _ in _FileFacts._fields_}
    return {**{name: getattr(value, name) for name, _ in _Snapshot._fields_
               if name not in ("files", "mapped_shm_probe")},
            "files": tuple(file(row) for row in value.files),
            "mapped_shm_probe": file(value.mapped_shm_probe)}


class OutcomeCapacityRuntime:
    """Pinned native VFS implementation; does not select itself by discovery."""
    def __init__(self, helper_path, helper_sha256):
        _require(os.name == "nt" and ctypes.sizeof(ctypes.c_void_p) == 8,
                 "OUTCOME_CAPACITY_WINDOWS_X64_REQUIRED")
        _require(type(helper_sha256) is str and len(helper_sha256) == 64
                 and all(c in "0123456789abcdef" for c in helper_sha256),
                 "OUTCOME_CAPACITY_HELPER_DIGEST_REQUIRED")
        path = Path(helper_path)
        _require(path.is_absolute() and path.is_file(), "OUTCOME_CAPACITY_HELPER_REQUIRED")
        for part in (path, *path.parents):
            _require(not part.is_symlink() and not part.is_junction(),
                     "OUTCOME_CAPACITY_HELPER_LINK_REJECTED")
        path = path.resolve(strict=True)
        _require(hashlib.sha256(path.read_bytes()).hexdigest() == helper_sha256,
                 "OUTCOME_CAPACITY_HELPER_BYTES_MISMATCH")
        load_sqlite()
        self.path, self.sha256 = path, helper_sha256
        self._library = ctypes.CDLL(str(path), winmode=0x100 | 0x1000)
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32]
        kernel.GetModuleFileNameW.restype = ctypes.c_uint32
        loaded = ctypes.create_unicode_buffer(32768)
        count = kernel.GetModuleFileNameW(self._library._handle, loaded, len(loaded))
        _require(0 < count < len(loaded) and Path(loaded.value).resolve(strict=True) == path,
                 'OUTCOME_CAPACITY_LOADED_HELPER_MISMATCH')
        # Bind the exports by their declared cdecl ABI. No Python connection
        # layout, private SQLite pointer or alternate SQLite engine is used.
        exports = {
            "abi": ([ctypes.POINTER(ctypes.c_uint32)] * 2),
            "create": [ctypes.c_wchar_p, ctypes.c_char_p, ctypes.POINTER(ctypes.c_uint64)],
            "state": [ctypes.c_uint64, ctypes.POINTER(_Snapshot)],
            "reserve": [ctypes.c_uint64] * 4 + [ctypes.POINTER(_Snapshot)],
            "measure": [ctypes.c_uint64, ctypes.POINTER(_Snapshot)],
            "release": [ctypes.c_uint64, ctypes.POINTER(_Snapshot)],
            "destroy": [ctypes.c_uint64],
        }
        self._functions = {}
        for name, arguments in exports.items():
            method = getattr(self._library, "ceta_capacity_" + name)
            method.argtypes, method.restype = arguments, ctypes.c_int
            self._functions[name] = method
        version, size = ctypes.c_uint32(), ctypes.c_uint32()
        rc = self._functions["abi"](ctypes.byref(version), ctypes.byref(size))
        _require(rc == 0 and version.value == 1 and size.value == ctypes.sizeof(_Snapshot),
                 "OUTCOME_CAPACITY_HELPER_ABI_MISMATCH")
        _require(hashlib.sha256(path.read_bytes()).hexdigest() == helper_sha256,
                 "OUTCOME_CAPACITY_HELPER_CHANGED_DURING_LOAD")

    def _create(self):
        name = "ceta_capacity_" + uuid.uuid4().hex
        token = ctypes.c_uint64()
        rc = self._functions["create"](str(DLL_PATH), name.encode("ascii"), ctypes.byref(token))
        _require(rc == 0 and token.value > 0, "OUTCOME_CAPACITY_VFS_UNAVAILABLE")
        return _CapacityVfs(self, name, token.value)


class _CapacityVfs:
    def __init__(self, runtime, name, token):
        self.runtime, self.name, self.token = runtime, name, token
        self.closed, self.close_attempted = False, False
        self.last_snapshot = None
        self._state_buffer = _Snapshot()
        self._state_pointer = ctypes.byref(self._state_buffer)

    def uri(self, path, mode):
        _require(not self.closed and mode in ("ro", "rw"), "OUTCOME_CAPACITY_VFS_CLOSED")
        return path.as_uri() + "?mode=" + mode + "&vfs=" + self.name

    def call(self, operation, *amounts):
        _require(not self.closed, "OUTCOME_CAPACITY_VFS_CLOSED")
        value = self._state_buffer if operation == 'state' else _Snapshot()
        value.version = 0
        pointer = self._state_pointer if operation == 'state' else ctypes.byref(value)
        rc = self.runtime._functions[operation](self.token, *amounts, pointer)
        self.last_snapshot = value if value.version == 1 else None
        if rc != 0:
            error = ContractError("OUTCOME_CAPACITY_NATIVE_" + operation.upper() + "_FAILED")
            data = BaseException.__dict__["__dict__"].__get__(error)
            dict.update(data, sqlite_result=rc, capacity_snapshot=None if self.last_snapshot is None else _facts(value))
            _expose(error, self)
            raise error
        _require(value.version == 1, "OUTCOME_CAPACITY_NATIVE_SNAPSHOT_INVALID")
        return value

    def close(self):
        if self.closed:
            return
        _require(not self.close_attempted, "OUTCOME_CAPACITY_VFS_CLOSE_UNCERTAIN")
        self.close_attempted = True
        rc = self.runtime._functions["destroy"](self.token)
        _require(rc == 0, "OUTCOME_CAPACITY_VFS_CLOSE_FAILED")
        self.closed = True


class OutcomeCapacityLease:
    """A single same-journal capacity reservation; no held SQL transaction.

    The trusted effect path must call mark_may_have_executed before dispatch,
    stage the exact canonical outcome payloads, and commit those payloads on
    this journal. A missing or failed commit retains the slot and reservation.
    """
    def __init__(self, journal, budget):
        _require(type(budget) is OutcomeCapacityBudget, "OUTCOME_CAPACITY_BUDGET_REQUIRED")
        budget.__post_init__()
        self.journal, self.budget = journal, budget
        self.vfs = journal._capacity_vfs
        _require(type(self.vfs) is _CapacityVfs, "OUTCOME_CAPACITY_NOT_CONFIGURED")
        self.state, self.thread, self.generation = "NEW", threading.get_ident(), None
        self._slot, self._lengths, self._used = None, (), 0
        self.may_have_executed = self.durable = self.release_attempted = False
        self.commit = self.cleanup_error = self.entry_error = None
        self.reservation_snapshot = self.retirement_snapshot = None

    def _owned(self):
        _require(threading.get_ident() == self.thread, "OUTCOME_CAPACITY_ORIGINAL_THREAD_REQUIRED")
        _require(self.journal._capacity_active is self and self.journal._capacity_vfs is self.vfs
                 and self.state in ("ACTIVE", "PENDING"), "OUTCOME_CAPACITY_OWNER_CHANGED")

    def __enter__(self):
        _require(self.state == "NEW", "OUTCOME_CAPACITY_SINGLE_USE_REQUIRED")
        _require(threading.get_ident() == self.thread, "OUTCOME_CAPACITY_ORIGINAL_THREAD_REQUIRED")
        self.state = "ENTERING"
        try:
            self._slot = bytearray(self.budget.memory_bytes)
            with self.journal._lock:
                self.journal._require_writable()
                _require(self.journal._capacity_active is None and not self.journal._connection.in_transaction,
                         "OUTCOME_CAPACITY_WRITER_BUSY")
                self.journal._capacity_active = self
                value = self.vfs.call("reserve", self.budget.database_bytes,
                                      self.budget.wal_bytes, self.budget.shm_bytes)
                _require(value.state == _RETAINED and value.open_files == 2,
                         "OUTCOME_CAPACITY_NOT_RETAINED")
                self.generation = value.generation
                self.reservation_snapshot = _facts(value)
                self.state = "ACTIVE"
                self.require_current()
            return self
        except BaseException as primary:
            self.entry_error = primary
            if self.journal._capacity_active is self:
                self._release(primary)
            else:
                self.state, self._slot = "CLOSED", None
            _expose(primary, self, self.cleanup_error)
            raise

    def require_current(self):
        """Cached native-state check: no SQL, physical query, native allocation or wait."""
        self._owned()
        _require(not self.journal._closed and self.journal._connection_close_state == "OPEN"
                 and self.journal._transaction_cleanup_state == "READY",
                 "OUTCOME_CAPACITY_JOURNAL_UNAVAILABLE")
        value = self.vfs.call("state")
        _require(value.state == _RETAINED and value.generation == self.generation
                 and value.open_files == 2, "OUTCOME_CAPACITY_LOST")
        return None

    def measure(self):
        """Explicit physical readback outside SQL/authority guards."""
        self.require_current()
        _require(not self.journal._connection.in_transaction, "OUTCOME_CAPACITY_QUERY_INSIDE_TRANSACTION")
        return _facts(self.vfs.call("measure"))

    def mark_may_have_executed(self):
        self.require_current()
        _require(not self.may_have_executed and self.state == "ACTIVE",
                 "OUTCOME_CAPACITY_DISPATCH_ONCE_REQUIRED")
        self.may_have_executed = True

    def stage_outcome(self, payloads):
        self._owned()
        _require(self.may_have_executed and not self.durable and not self._lengths,
                 "OUTCOME_CAPACITY_OUTCOME_ONCE_REQUIRED")
        _require(type(payloads) is tuple and 1 <= len(payloads) <= 128
                 and all(type(wire) is bytes and len(wire) > 0 for wire in payloads),
                 "OUTCOME_CAPACITY_PAYLOADS_REQUIRED")
        total = sum(len(wire) for wire in payloads)
        _require(total <= self.budget.memory_bytes, "OUTCOME_CAPACITY_MEMORY_EXHAUSTED")
        offset = 0
        for wire in payloads:
            self._slot[offset:offset + len(wire)] = wire
            offset += len(wire)
        self._used, self._lengths = total, tuple(len(wire) for wire in payloads)

    def _after_commit(self, entries, result):
        # This method is called only after this journal's real COMMIT returned.
        # Matching payload bytes, not a caller success flag, retire the slot.
        self._owned()
        if not self.may_have_executed or not self._lengths or self.durable:
            return
        if len(entries) != len(self._lengths):
            return
        offset = 0
        for entry, size in zip(entries, self._lengths):
            if len(entry.payload_wire) != size or self._slot[offset:offset + size] != entry.payload_wire:
                return
            offset += size
        self.commit, self.durable = result, True

    def retained_payloads(self):
        """Bounded recovery copy; retained bytes are observations, not authority."""
        self._owned()
        result, offset = [], 0
        for size in self._lengths:
            result.append(bytes(self._slot[offset:offset + size])); offset += size
        return tuple(result)

    def _release(self, primary=None):
        if self.release_attempted:
            error = ContractError("OUTCOME_CAPACITY_RELEASE_UNCERTAIN")
            if primary is not None:
                _expose(primary, self, error)
                raise primary
            raise error
        self.release_attempted = True
        try:
            value = self.vfs.call("state")
            if value.state != _IDLE:
                value = self.vfs.call("release")
            _require(value.state == _IDLE and all(row.close_state in (_ABSENT, _RETIRED)
                for row in value.files) and value.mapped_shm_probe.close_state in (_ABSENT, _RETIRED),
                "OUTCOME_CAPACITY_RETIREMENT_UNOBSERVED")
            self.retirement_snapshot = _facts(value)
            self.state, self._slot = "CLOSED", None
            if self.journal._capacity_active is self:
                self.journal._capacity_active = None
        except BaseException as secondary:
            self.state, self.cleanup_error = "PENDING", secondary
            if primary is None:
                _expose(secondary, self)
                raise
            _expose(primary, self, secondary)
            raise primary

    def finish_reconciliation(self):
        self._owned()
        _require(self.state == "PENDING" and self.durable and not self.release_attempted,
                 "OUTCOME_CAPACITY_DURABLE_RECONCILIATION_REQUIRED")
        self._release()

    def __exit__(self, kind, primary, trace):
        self._owned()
        _require((primary is None and kind is None and trace is None) or
                 (isinstance(primary, BaseException) and kind is type(primary)
                  and (trace is None or type(trace) is TracebackType)),
                 "OUTCOME_CAPACITY_EXCEPTION_ARGUMENTS_INVALID")
        if self.may_have_executed and not self.durable:
            self.state = "PENDING"
            pending = ContractError("OUTCOME_CAPACITY_DURABLE_OUTCOME_PENDING")
            if primary is not None:
                _expose(primary, self, pending)
                raise primary
            _expose(pending, self)
            raise pending
        else:
            self._release(primary)
        return None

    def __copy__(self): raise ContractError("OUTCOME_CAPACITY_COPY_FORBIDDEN")
    def __deepcopy__(self, memo): raise ContractError("OUTCOME_CAPACITY_COPY_FORBIDDEN")
    def __reduce_ex__(self, protocol): raise ContractError("OUTCOME_CAPACITY_SERIALIZATION_FORBIDDEN")
