"""Retain measured source/environment objects for trusted local composition.

These observations do not approve code or issue authority. The composition
supplies its reviewed finite manifest. Ordinary Windows writes, replacement and
ancestor renames remain excluded while the read-only handles are retained.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import ctypes as C
import hashlib
from pathlib import Path
import re
import threading

from ceta.contracts.kernel_transactions import require
from ceta.contracts.wire import ContractError, canonical_bytes
from ceta.supervisor.isolated_worker import _IsolationAPI
from ceta.supervisor.windows_jobs import DWORD, HANDLE, INVALID_HANDLE, _path, _hash_image, _file_identity

MAXIMUM_FILES = 8192
MAXIMUM_FILE_BYTES = 1_073_741_824
MAXIMUM_TOTAL_BYTES = 4_294_967_296


@dataclass(frozen=True, slots=True)
class CodePin:
    group: str
    logical_name: str
    path: str
    sha256: str

    def __post_init__(self):
        require(type(self.group) is str and self.group in ('source', 'environment'), 'CODE_BINDING_GROUP_INVALID')
        require(type(self.logical_name) is str and 0 < len(self.logical_name) <= 512
            and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/-]*', self.logical_name)
            and all(part not in ('', '.', '..') and not part.endswith('.')
                for part in self.logical_name.split('/')), 'CODE_BINDING_NAME_INVALID')
        require(type(self.path) is str and type(self.sha256) is str
            and re.fullmatch('[0-9a-f]{64}', self.sha256), 'CODE_BINDING_PIN_INVALID')


class _FileId(C.Structure):
    _fields_ = [('volume', C.c_uint64), ('identifier', C.c_ubyte * 16)]


class _AttributeTag(C.Structure):
    _fields_ = [('attributes', DWORD), ('tag', DWORD)]


class _BindingAPI(_IsolationAPI):
    def __init__(self):
        super().__init__()
        call = self.dll.GetFileInformationByHandleEx
        call.argtypes, call.restype = [HANDLE, C.c_int, C.c_void_p, DWORD], C.c_int32
        self.GetFileInformationByHandleEx = call

    def facts(self, handle, directory):
        identifier, attributes, flags = _FileId(), _AttributeTag(), DWORD()
        require(self.GetFileInformationByHandleEx(handle, 9, C.byref(attributes), C.sizeof(attributes))
            and self.GetFileInformationByHandleEx(handle, 18, C.byref(identifier), C.sizeof(identifier)),
            'CODE_BINDING_NATIVE_FACTS_UNAVAILABLE')
        require(not attributes.attributes & 0x400 and attributes.tag == 0
            and bool(attributes.attributes & 0x10) == directory, 'CODE_BINDING_OBJECT_INVALID')
        require(self.GetHandleInformation(handle, C.byref(flags)) and not flags.value & 1,
            'CODE_BINDING_INHERITABLE_HANDLE')
        return (self.native_volume_path(handle), format(identifier.volume, '016x'),
            bytes(identifier.identifier).hex(), attributes.attributes)


def _expose(primary, owner):
    try:
        note = getattr(primary, 'add_note', None)
        if callable(note): note('Retained native code bindings require explicit close/recovery.')
    except BaseException:
        pass
    BaseException.__dict__['__dict__'].__get__(primary).update(
        native_code_binding=owner, close_cleanup=owner.close)


class _RetainedBinding:
    __slots__ = ('_owner', '_thread', '_active')

    def __init__(self, owner):
        self._owner, self._thread, self._active = owner, threading.get_ident(), True

    def require_current(self):
        # Pure final fence: handles and ancestors remain pinned, and the exact
        # owner retains its lock for the whole lease. No I/O, clock or issuer.
        owner = self._owner
        require(self._active and owner._lease is self and self._thread == threading.get_ident()
            and not owner._closing.is_set() and not owner._closed, 'CODE_BINDING_LEASE_INVALID')


class NativeCodeBinding:
    """Measured immutable file objects; canonical authority remains elsewhere."""
    def __init__(self, pins):
        self._lock = threading.RLock()
        self._closing, self._closed, self._lease = threading.Event(), False, None
        self._api, self._files, self._ancestors = _BindingAPI(), [], []
        try:
            require(type(pins) is tuple and 2 <= len(pins) <= MAXIMUM_FILES
                and all(type(pin) is CodePin for pin in pins), 'CODE_BINDING_MANIFEST_REQUIRED')
            for pin in pins: pin.__post_init__()
            require({pin.group for pin in pins} == {'source', 'environment'}, 'CODE_BINDING_BOTH_GROUPS_REQUIRED')
            require(len({(pin.group, pin.logical_name.casefold()) for pin in pins}) == len(pins),
                'CODE_BINDING_DUPLICATE_NAME')
            paths = [(pin, Path(_path(pin.path, directory=False))) for pin in pins]
            require(len({str(path).casefold() for _, path in paths}) == len(paths), 'CODE_BINDING_DUPLICATE_PATH')
            ancestors = sorted({item for _, path in paths for item in path.parents}, key=lambda path:(len(path.parts),str(path)))
            require(len(ancestors) <= MAXIMUM_FILES * 16, 'CODE_BINDING_ANCESTOR_BOUND')
            for path in ancestors:
                self._retain(path, directory=True, group=None, logical=None)
            total = 0
            for pin, path in sorted(paths, key=lambda pair:(pair[0].group,pair[0].logical_name)):
                row = self._retain(path, directory=False, group=pin.group, logical=pin.logical_name)
                size = _file_identity(self._api, row['handle'])
                byte_count = (size[3] << 32) | size[4]
                total += byte_count
                require(byte_count <= MAXIMUM_FILE_BYTES and total <= MAXIMUM_TOTAL_BYTES, 'CODE_BINDING_BYTES_BOUND')
                actual, file_identity = _hash_image(self._api, row['handle'])
                require(actual == pin.sha256, 'CODE_BINDING_HASH_MISMATCH')
                row.update(sha256=actual, bytes=byte_count, file_identity=file_identity)
            self.source_commitment = self._commitment('source')
            self.environment_commitment = self._commitment('environment')
            self.require_current()
        except BaseException as primary:
            try: self.close()
            except BaseException: pass
            _expose(primary, self)
            raise

    def _retain(self, path, *, directory, group, logical):
        flags = 0x00200000 | (0x02000000 if directory else 0x80)
        handle = self._api.CreateFileW(str(path), 0x80 if directory else 0x80000000,
            3 if directory else 1, None, 3, flags, None)
        require(handle not in (None, 0, INVALID_HANDLE), 'CODE_BINDING_NATIVE_OPEN_FAILED')
        self._api.queue_handle(handle)
        row = {'path':str(path), 'handle':handle, 'directory':directory,
            'group':group, 'logical_name':logical, 'facts':self._api.facts(handle,directory)}
        (self._ancestors if directory else self._files).append(row)
        return row

    def _commitment(self, group):
        digest = hashlib.sha256(b'CETA-NATIVE-CODE-BINDING-V1\0'+group.encode('ascii')+b'\0')
        for row in self._files:
            if row['group'] != group: continue
            raw = canonical_bytes(dict(name=row['logical_name'], sha256=row['sha256'], bytes=row['bytes'],
                native_path=row['facts'][0], volume=row['facts'][1], file_id=row['facts'][2]))
            digest.update(len(raw).to_bytes(8,'big'));digest.update(raw)
        return 'sha256:'+digest.hexdigest()

    @property
    def closed(self): return self._closed

    @property
    def pending_native_resources(self): return self._api.pending_native_resources()

    def snapshot(self):
        with self._lock:
            self.require_current()
            return tuple((row['group'],row['logical_name'],row['sha256'],row['bytes'],row['facts']) for row in self._files)

    def require_current(self):
        with self._lock:
            require(not self._closed and not self._closing.is_set(), 'CODE_BINDING_CLOSED')
            for row in self._ancestors + self._files:
                require(self._api.facts(row['handle'],row['directory']) == row['facts'], 'CODE_BINDING_IDENTITY_CHANGED')
                if not row['directory']:
                    require(_file_identity(self._api,row['handle']) == row['file_identity'], 'CODE_BINDING_FILE_CHANGED')

    @contextmanager
    def retained(self):
        with self._lock:
            self.require_current()
            require(self._lease is None, 'CODE_BINDING_LEASE_ACTIVE')
            lease = self._lease = _RetainedBinding(self)
            try:
                lease.require_current()
                yield lease
            finally:
                lease._active = False
                self._lease = None

    def close(self):
        self._closing.set()
        require(self._lock.acquire(blocking=False), 'CODE_BINDING_BUSY')
        try:
            if self._closed: return
            require(self._lease is None, 'CODE_BINDING_LEASE_ACTIVE')
            try:
                self._api.retry_cleanup(kinds=('handles',))
                require(not self.pending_native_resources, 'CODE_BINDING_CLEANUP_PENDING')
            except BaseException as primary:
                _expose(primary,self)
                raise
            self._closed = True
        finally:
            self._lock.release()

    def __enter__(self):
        self.require_current()
        return self

    def __exit__(self, kind, primary, trace):
        try: self.close()
        except BaseException:
            if primary is None: raise
            _expose(primary,self)
        return False
