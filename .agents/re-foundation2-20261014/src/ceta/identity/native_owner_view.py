"""Native request-owner and private-store observations for trusted composition.

Observations are data. This module never enrolls an owner, consumes a challenge,
issues a grant or changes the journal. Retained ordinary file objects prevent
normal replacement while SQLite may continue writing its existing database.
Unrestricted same-account/admin modification is outside this observation claim.
"""
from dataclasses import dataclass
import ctypes as C
from pathlib import Path
import re
import threading
import time
import uuid

from ceta.contracts.kernel_transactions import PeerIdentity, require
from ceta.contracts.owner_enrollment import (EnrollmentRequest, NativeObjectIdentity,
    OwnerTokenFacts, require_enrollment_current)
from ceta.contracts.resource_management import ProcessResourceIdentity
from ceta.contracts.temporal import ClockSample
from ceta.contracts.wire import ContractError
from ceta.identity.native_clock import NativeSessionClock
from ceta.identity.windows_pipe import WindowsPeerRegistry, WindowsPeerRegistration
from ceta.supervisor.isolated_worker import _IsolationAPI
from ceta.supervisor.windows_jobs import HANDLE, DWORD, INVALID_HANDLE, _path

MAXIMUM_OBSERVATION_NS = 2_000_000_000


class _FileId(C.Structure):
    _fields_ = [('volume', C.c_uint64), ('identifier', C.c_ubyte * 16)]


class _AttributeTag(C.Structure):
    _fields_ = [('attributes', DWORD), ('tag', DWORD)]


class _ViewAPI(_IsolationAPI):
    def __init__(self):
        super().__init__()
        call = self.dll.GetFileInformationByHandleEx
        call.argtypes = [HANDLE, C.c_int, C.c_void_p, DWORD]
        call.restype = C.c_int32
        self.GetFileInformationByHandleEx = call


def _sid_text(raw):
    require(type(raw) is bytes and len(raw) >= 8 and raw[0] == 1
        and len(raw) == 8 + raw[1] * 4, 'OWNER_VIEW_SID_INVALID')
    return 'S-1-' + str(int.from_bytes(raw[2:8], 'big')) + ''.join(
        '-' + str(int.from_bytes(raw[index:index + 4], 'little'))
        for index in range(8, len(raw), 4))


def _luid_hex(pair):
    require(type(pair) is tuple and len(pair) == 2
        and type(pair[0]) is int and 0 <= pair[0] <= 0xFFFFFFFF
        and type(pair[1]) is int and -2147483648 <= pair[1] <= 2147483647,
        'OWNER_VIEW_LUID_INVALID')
    return format(((pair[1] & 0xFFFFFFFF) << 32) | pair[0], '016x')


def registration_token_facts(registration):
    """Encode the existing native registry's measured facts without losing zero."""
    require(type(registration) is WindowsPeerRegistration, 'OWNER_VIEW_REGISTRATION_REQUIRED')
    facts = registration.token_facts
    identity = ProcessResourceIdentity(registration.pid, registration.process_creation,
        'sha256:' + registration.image_sha256)
    return OwnerTokenFacts(identity, _sid_text(facts.user_sid), _sid_text(facts.logon_sid),
        _luid_hex(facts.authentication_id), facts.terminal_session,
        _luid_hex(facts.token_id), _luid_hex(facts.modified_id), facts.token_type,
        facts.impersonation_level, _sid_text(facts.integrity_sid), facts.integrity_attributes,
        facts.elevation_type, facts.ui_access, facts.has_restrictions,
        tuple(sorted(set(_sid_text(row[0]) for row in facts.restricted_sids))))


def _expose(primary, owner):
    # Annotation is optional; recoverable custody is attached after annotation
    # through BaseException's real storage, bypassing overridable attributes.
    try:
        note = getattr(primary, 'add_note', None)
        if callable(note): note('Native owner-view custody is retained; explicit close/recovery required.')
    except BaseException:
        pass
    BaseException.__dict__['__dict__'].__get__(primary).update(
        native_owner_view=owner, close_cleanup=owner.close)


class NativeStoreBinding:
    """Read-only retained file identities, not a second database/state owner."""
    def __init__(self, private_root, *, expected_root=None, expected_database=None):
        self._lock = threading.RLock()
        self._closed = False
        self._api = _ViewAPI()
        self._pins = []
        self._root_path = Path(_path(str(private_root), directory=True))
        self._database_path = self._root_path / 'history.sqlite3'
        try:
            ancestors = tuple(reversed(self._root_path.parents)) + (self._root_path, self._database_path)
            for path in ancestors:
                handle = self._api.CreateFileW(str(path), 0x80, 3, None, 3,
                    0x00200000 | 0x02000000, None)
                require(handle not in (None, 0, INVALID_HANDLE), 'OWNER_VIEW_NATIVE_OPEN_FAILED')
                self._api.queue_handle(handle)
                row = {'path': path, 'handle': handle, 'identity': None}
                self._pins.append(row)
                row['identity'] = self._read(row)
            self.private_root = self._pins[-2]['identity']
            self.database = self._pins[-1]['identity']
            require(self.private_root.kind == 'directory' and self.database.kind == 'file'
                and self.database.path == self.private_root.path + '\\history.sqlite3'
                and self.private_root.volume_serial_hex == self.database.volume_serial_hex
                and self.private_root.file_id_hex != self.database.file_id_hex,
                'OWNER_VIEW_PRIVATE_STORE_BINDING')
            for actual, expected in ((self.private_root, expected_root), (self.database, expected_database)):
                require(expected is None or type(expected) is NativeObjectIdentity and actual == expected,
                    'OWNER_VIEW_EXPECTED_OBJECT_MISMATCH')
            self.require_current()
        except BaseException as primary:
            try: self.close()
            except BaseException: pass
            _expose(primary, self)
            raise

    def _read(self, row):
        api, handle = self._api, row['handle']
        attributes, identifier = _AttributeTag(), _FileId()
        require(api.GetFileInformationByHandleEx(handle, 9, C.byref(attributes), C.sizeof(attributes)),
            'OWNER_VIEW_ATTRIBUTES_UNAVAILABLE')
        require(not attributes.attributes & 0x400 and attributes.tag == 0,
            'OWNER_VIEW_REPARSE_OBJECT_DENIED')
        require(api.GetFileInformationByHandleEx(handle, 18, C.byref(identifier), C.sizeof(identifier)),
            'OWNER_VIEW_FILE_ID_UNAVAILABLE')
        flags = DWORD()
        require(api.GetHandleInformation(handle, C.byref(flags)) and not flags.value & 1,
            'OWNER_VIEW_INHERITABLE_FILE_DENIED')
        path = api.native_volume_path(handle)
        match = re.fullmatch(r'\\\\\?\\Volume\{([0-9a-fA-F-]{36})\}\\(.*)', path)
        require(match is not None, 'OWNER_VIEW_NATIVE_PATH_UNAVAILABLE')
        suffix = match[2]
        canonical = '\\\\?\\Volume{' + str(uuid.UUID(match[1])) + '}\\' + suffix
        # Volume roots are retained ancestors, not declared enrollment objects.
        if not suffix:
            return ('volume-root', canonical, format(identifier.volume, '016x'), bytes(identifier.identifier).hex())
        return NativeObjectIdentity(canonical, 'directory' if attributes.attributes & 0x10 else 'file',
            format(identifier.volume, '016x'), bytes(identifier.identifier).hex())

    @property
    def pending_native_resources(self):
        return self._api.pending_native_resources()

    @property
    def closed(self):
        return self._closed

    def require_current(self):
        with self._lock:
            require(not self._closed, 'OWNER_VIEW_CLOSED')
            started = time.monotonic_ns()
            for row in self._pins:
                require(self._read(row) == row['identity'], 'OWNER_VIEW_NATIVE_IDENTITY_CHANGED')
            elapsed = time.monotonic_ns() - started
            require(0 <= elapsed <= MAXIMUM_OBSERVATION_NS, 'OWNER_VIEW_OBSERVATION_STALE')

    def close(self):
        with self._lock:
            if self._closed: return
            try:
                self._api.retry_cleanup(kinds=('handles',))
                require(not self.pending_native_resources, 'OWNER_VIEW_CLEANUP_PENDING')
            except BaseException as primary:
                _expose(primary, self)
                raise
            self._closed = True

    def __enter__(self):
        self.require_current()
        return self

    def __exit__(self, kind, primary, trace):
        try: self.close()
        except BaseException:
            if primary is None: raise
            _expose(primary, self)
        return False


@dataclass(frozen=True, slots=True)
class NativeOwnerObservation:
    peer: PeerIdentity
    owner_facts: OwnerTokenFacts
    private_root: NativeObjectIdentity
    database: NativeObjectIdentity
    previous_clock: ClockSample
    current_clock: ClockSample
    elapsed_ns: int


class NativeOwnerView:
    """Fresh original-context observation on the existing concrete peer owner."""
    def __init__(self, registry, clock_owner, store_binding):
        require(type(registry) is WindowsPeerRegistry, 'OWNER_VIEW_NATIVE_REGISTRY_REQUIRED')
        require(type(clock_owner) is NativeSessionClock, 'OWNER_VIEW_NATIVE_CLOCK_REQUIRED')
        require(type(store_binding) is NativeStoreBinding, 'OWNER_VIEW_NATIVE_STORE_REQUIRED')
        self._registry, self._clock, self._store = registry, clock_owner, store_binding

    def observe(self, original_context):
        started = time.monotonic_ns()
        with self._registry._lock:
            active = self._registry._checked(original_context)
            self._registry.require_message(original_context, active.message)
            registration = active.entry.registration
            owner = registration_token_facts(registration)
            peer = PeerIdentity(registration.principal_id, registration.session_id)
        previous, current = self._clock.clock()
        self._store.require_current()
        with self._registry._lock:
            again = self._registry._checked(original_context)
            require(again is active and again.entry.registration == registration,
                'OWNER_VIEW_REQUEST_CHANGED')
        elapsed = time.monotonic_ns() - started
        require(0 <= elapsed <= MAXIMUM_OBSERVATION_NS, 'OWNER_VIEW_OBSERVATION_STALE')
        return NativeOwnerObservation(peer, owner, self._store.private_root, self._store.database,
            previous, current, elapsed)

    def require_enrollment_current(self, enrollment, original_context):
        require(type(enrollment) is EnrollmentRequest, 'ENROLLMENT_REQUEST_REQUIRED')
        observed = self.observe(original_context)
        require((observed.peer.principal_id, observed.peer.session_id) ==
            (enrollment.principal_id, enrollment.actor_session)
            and observed.owner_facts == enrollment.owner_facts
            and observed.private_root == enrollment.private_root
            and observed.database == enrollment.database, 'OWNER_VIEW_ENROLLMENT_NATIVE_MISMATCH')
        require_enrollment_current(enrollment, enrollment, observed.previous_clock, observed.current_clock)
        require(observed.elapsed_ns <= enrollment.maximum_observation_age_ns,
            'OWNER_VIEW_ENROLLMENT_OBSERVATION_STALE')
        return observed
