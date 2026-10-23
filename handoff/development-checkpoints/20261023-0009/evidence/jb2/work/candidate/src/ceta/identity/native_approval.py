"""Owned Windows desktop consent transport, selected only by trusted composition.

Availability and hidden-display inspection never request authentication. The
interactive path needs a retained canonical-owner/clock integration which is not
implemented by this library. Its defaults deny. A native result is evidence data;
the canonical kernel must authenticate its origin and consume the challenge.
This is not isolation from an unrestricted same-account process or administrator.
"""
from __future__ import annotations

import ctypes as C
from dataclasses import dataclass
import hashlib
import math
import os
from pathlib import Path
import re
import secrets
import struct
import threading
import time

from ceta.contracts.kernel_transactions import commitment, digest, identifier, require
from ceta.contracts.real_effect import (OwnedCpuRequest, NativeApprovalTranscript,
    approval_display_bytes, approval_display_commitment, decode_owned_cpu_request)
from ceta.contracts.owner_enrollment import (EnrollmentRequest, decode_enrollment_request,
    enrollment_display_bytes, enrollment_display_commitment, require_enrollment_current)
from ceta.contracts.resource_management import ProcessResourceIdentity
from ceta.contracts.temporal import ClockSample, require_clock_progress, require_deadline_current
from ceta.contracts.wire import ContractError, canonical_bytes, strict_loads
from ceta.supervisor.service import _ControlApi, _Attributes, controlled_environment
from ceta.supervisor.windows_jobs import (WindowsOwnedProcess, _API, _open_image,
    _hash_image, _file_identity, _path)
from .windows_pipe import _Api as _TokenApi, _token_facts

PROTOCOL = 'ceta-native-owner-approval-v1'
MAX_INPUT = 40960
MAX_OUTPUT = 16384
_REQUEST_MAGIC = b'CETAAP01'
_RESPONSE_MAGIC = b'CETAAO01'
_MODES = {'availability': 1, 'inspect': 2, 'interactive': 3, 'cancel': 4}
_STATUSES = frozenset(('AVAILABLE', 'UNAVAILABLE', 'DISPLAY_BOUND_UNSHOWN',
    'CANCELLED', 'TIMED_OUT', 'VERIFIED', 'DENIED'))
_HASH = re.compile(r'[0-9a-f]{64}')
_ENROLLMENT_PREPARATION = 'prepare-enrollment-v1'
DWORD, BOOL, HANDLE = C.c_uint32, C.c_int32, C.c_void_p


def _integer(value, minimum, maximum, code):
    require(type(value) is int and minimum <= value <= maximum, code)


def _timeout(value):
    _integer(value, 20, 300000, 'APPROVAL_TIMEOUT_INVALID')
    return value


def _exception_data(error):
    # BaseException owns this real dictionary even when a subclass refuses
    # attribute assignment or supplies a throwing diagnostic property.
    return BaseException.__dict__['__dict__'].__get__(error)


def _display_bytes(request):
    return enrollment_display_bytes(request) if type(request) is EnrollmentRequest else approval_display_bytes(request)


def _display_commitment(request):
    return enrollment_display_commitment(request) if type(request) is EnrollmentRequest else approval_display_commitment(request)


def _sid_text(raw):
    """Lossless SID representation of already measured, bounded token bytes."""
    require(type(raw) is bytes and len(raw) >= 8 and raw[0] == 1
        and len(raw) == 8 + raw[1] * 4, 'APPROVAL_SID_INVALID')
    return 'S-1-' + str(int.from_bytes(raw[2:8], 'big')) + ''.join(
        '-' + str(int.from_bytes(raw[at:at + 4], 'little')) for at in range(8, len(raw), 4))


@dataclass(frozen=True, slots=True)
class NativeProcessEvidence:
    identity: ProcessResourceIdentity
    user_sid: str
    logon_sid: str
    authentication_id: tuple[int, int]
    terminal_session: int
    restricted: bool
    restricted_sid_count: int
    integrity_sid: str
    integrity_attributes: int
    elevation_type: int
    ui_access: int
    token_id: tuple[int, int]
    modified_id: tuple[int, int]

    def __post_init__(self):
        require(type(self.identity) is ProcessResourceIdentity, 'APPROVAL_PROCESS_REQUIRED')
        self.identity.__post_init__()
        for value in (self.user_sid, self.logon_sid, self.integrity_sid):
            require(type(value) is str and re.fullmatch(r'S-1-[0-9]+(?:-[0-9]+){0,15}', value),
                    'APPROVAL_SID_INVALID')
        for value in (self.authentication_id, self.token_id, self.modified_id):
            require(type(value) is tuple and len(value) == 2, 'APPROVAL_LUID_INVALID')
            _integer(value[0], 0, 0xFFFFFFFF, 'APPROVAL_LUID_INVALID')
            _integer(value[1], -2147483648, 2147483647, 'APPROVAL_LUID_INVALID')
        _integer(self.terminal_session, 0, 0xFFFFFFFF, 'APPROVAL_SESSION_INVALID')
        require(type(self.restricted) is bool, 'APPROVAL_RESTRICTION_INVALID')
        _integer(self.restricted_sid_count, 0, 4096, 'APPROVAL_RESTRICTION_INVALID')
        _integer(self.integrity_attributes, 0, 0xFFFFFFFF, 'APPROVAL_INTEGRITY_INVALID')
        _integer(self.elevation_type, 1, 3, 'APPROVAL_ELEVATION_INVALID')
        _integer(self.ui_access, 0, 1, 'APPROVAL_UI_ACCESS_INVALID')

    def as_dict(self):
        self.__post_init__()
        return {'pid': self.identity.pid, 'creation_time': self.identity.creation_time,
            'image_digest': self.identity.image_digest, 'user_sid': self.user_sid,
            'logon_sid': self.logon_sid, 'authentication_low': self.authentication_id[0],
            'authentication_high': self.authentication_id[1], 'terminal_session': self.terminal_session,
            'restricted': self.restricted, 'restricted_sid_count': self.restricted_sid_count,
            'integrity_sid': self.integrity_sid, 'integrity_attributes': self.integrity_attributes,
            'elevation_type': self.elevation_type, 'ui_access': self.ui_access,
            'token_id_low': self.token_id[0], 'token_id_high': self.token_id[1],
            'modified_id_low': self.modified_id[0], 'modified_id_high': self.modified_id[1]}


def _evidence(identity, facts):
    return NativeProcessEvidence(identity, _sid_text(facts.user_sid), _sid_text(facts.logon_sid),
        facts.authentication_id, facts.terminal_session, bool(facts.has_restrictions),
        len(facts.restricted_sids), _sid_text(facts.integrity_sid), facts.integrity_attributes,
        facts.elevation_type, facts.ui_access, facts.token_id, facts.modified_id)


@dataclass(frozen=True, slots=True)
class NativeApprovalResult:
    """Private-channel observations, not a grant or externally signed approval."""
    status: str
    challenge_id: str
    ceremony_nonce: str
    mode: str
    request_commitment: str
    display_commitment: str
    display_exact: bool
    availability: int | None
    authentication_invoked: bool
    hardware_click: bool
    native_hresult: int
    native_result: int | None
    helper: NativeProcessEvidence
    started_qpc: int
    finished_qpc: int
    qpc_frequency: int
    interop_module: str | None
    effective_cancelled: bool

    @property
    def reported_verified(self):
        return (self.mode == 'interactive' and self.status == 'VERIFIED'
            and self.authentication_invoked and self.hardware_click and self.display_exact
            and self.native_hresult == 0 and self.native_result == 0 and not self.effective_cancelled)


@dataclass(frozen=True, slots=True)
class NativeEnrollmentBinding:
    """Measured preparation data; no request, grant or approval is inferred."""
    challenge_id: str
    ceremony_nonce: str
    helper: NativeProcessEvidence
    ui_identity: ProcessResourceIdentity
    helper_commitment: str
    ui_commitment: str
    interop_module: str
    interop_sha256: str
    availability: int

    def __post_init__(self):
        identifier(self.challenge_id)
        require(type(self.ceremony_nonce) is str and re.fullmatch(r'[0-9a-f]{32}', self.ceremony_nonce)
            and self.ceremony_nonce != '0' * 32, 'APPROVAL_ENROLLMENT_NONCE_INVALID')
        require(type(self.helper) is NativeProcessEvidence, 'APPROVAL_PROCESS_REQUIRED')
        self.helper.__post_init__()
        require(type(self.ui_identity) is ProcessResourceIdentity and self.ui_identity == self.helper.identity,
                'APPROVAL_ENROLLMENT_UI_PROCESS_MISMATCH')
        for value in (self.helper_commitment, self.ui_commitment): commitment(value)
        require(self.helper_commitment == self.ui_commitment, 'APPROVAL_ENROLLMENT_UI_CODE_MISMATCH')
        require(type(self.interop_module) is str and 1 <= len(self.interop_module) <= 32767,
                'APPROVAL_INTEROP_MODULE_INVALID')
        require(type(self.interop_sha256) is str and _HASH.fullmatch(self.interop_sha256),
                'APPROVAL_INTEROP_MODULE_INVALID')
        _integer(self.availability, 0, 4, 'APPROVAL_AVAILABILITY_INVALID')


def _frame(mode, challenge_id, nonce, request, timeout_ms, *, enrollment=False):
    require(type(mode) is str and mode in _MODES, 'APPROVAL_MODE_UNAVAILABLE')
    require(type(enrollment) is bool, 'APPROVAL_REQUEST_DOMAIN_INVALID')
    identifier(challenge_id)
    require(type(nonce) is bytes and len(nonce) == 32 and any(nonce), 'APPROVAL_NONCE_INVALID')
    _timeout(timeout_ms)
    if mode == 'availability':
        require(request is None, 'APPROVAL_AVAILABILITY_HAS_REQUEST')
        body, request_hash, display_hash = b'', '', ''
    else:
        require(type(request) is (EnrollmentRequest if enrollment else OwnedCpuRequest),
                'APPROVAL_DECLARED_BODY_REQUIRED')
        # Decode a byte-frozen copy. Nested frozen objects can otherwise be
        # changed by privileged Python code between a validation and its use.
        request = (decode_enrollment_request if enrollment else decode_owned_cpu_request)(request.canonical_wire)
        if enrollment:
            require(request.challenge_id == challenge_id, 'APPROVAL_ENROLLMENT_CHALLENGE_MISMATCH')
        body, request_hash = request.canonical_wire, request.input_commitment
        display_hash = _display_commitment(request)
    def text(raw):
        return struct.pack('<I', len(raw)) + raw
    wire = (_REQUEST_MAGIC + struct.pack('<II', _MODES[mode], timeout_ms)
        + text(challenge_id.encode('ascii')) + nonce + text(body)
        + text(request_hash.encode('ascii')) + text(display_hash.encode('ascii')))
    require(len(wire) <= MAX_INPUT, 'APPROVAL_INPUT_BOUND')
    return wire, request


def _response(wire, *, mode, challenge_id, nonce, request, helper, cancelled):
    """Strict data parser. Calling it alone establishes no native origin."""
    require(type(wire) is bytes and 12 <= len(wire) <= MAX_OUTPUT + 12
        and wire[:8] == _RESPONSE_MAGIC, 'APPROVAL_RESPONSE_FRAME')
    length = struct.unpack('<I', wire[8:12])[0]
    require(0 < length <= MAX_OUTPUT and len(wire) == 12 + length, 'APPROVAL_RESPONSE_FRAME')
    value = strict_loads(wire[12:])
    require(type(value) is dict and canonical_bytes(value) == wire[12:], 'APPROVAL_RESPONSE_CANONICAL')
    if value.get('status') == 'ERROR':
        require(set(value) in ({'error', 'status', 'provenance'},
            {'error', 'status', 'native_hresult', 'provenance'}), 'APPROVAL_ERROR_FIELDS')
        require(type(value['error']) is str and value['error'] in
            ('NATIVE_WINRT_UNAVAILABLE', 'NATIVE_PROTOCOL_OR_RUNTIME_REJECTED'), 'APPROVAL_ERROR_CODE')
        require(value['provenance'] == helper.as_dict()
            and canonical_bytes(value['provenance']) == canonical_bytes(helper.as_dict()),
            'APPROVAL_HELPER_PROVENANCE_MISMATCH')
        if 'native_hresult' in value:
            _integer(value['native_hresult'], -2147483648, -1, 'APPROVAL_HRESULT_INVALID')
        raise ContractError('APPROVAL_NATIVE_REJECTED:' + value['error'])
    expected = {'authentication_invoked', 'availability', 'body_sha256', 'challenge_id',
        'display_commitment', 'display_exact', 'display_sha256', 'hardware_click', 'mode',
        'native_hresult', 'native_result', 'nonce', 'protocol', 'request_commitment', 'status',
        'started_qpc', 'finished_qpc', 'qpc_frequency', 'provenance'}
    require(set(value) == expected or set(value) == expected | {'interop_module'}, 'APPROVAL_RESPONSE_FIELDS')
    require(type(value['protocol']) is str and value['protocol'] == PROTOCOL
        and type(value['status']) is str and value['status'] in _STATUSES, 'APPROVAL_RESPONSE_PROFILE')
    _integer(value['mode'], 1, 4, 'APPROVAL_RESPONSE_MODE')
    require(value['mode'] == _MODES[mode] and type(value['challenge_id']) is str
        and value['challenge_id'] == challenge_id and type(value['nonce']) is str
        and value['nonce'] == nonce.hex(), 'APPROVAL_CHALLENGE_MISMATCH')
    for name in ('display_exact', 'hardware_click', 'authentication_invoked'):
        require(type(value[name]) is bool, 'APPROVAL_RESPONSE_BOOLEAN')
    _integer(value['native_hresult'], -2147483648, 0, 'APPROVAL_HRESULT_INVALID')
    if value['native_result'] is not None:
        _integer(value['native_result'], 0, 6, 'APPROVAL_NATIVE_RESULT_INVALID')
        require(value['native_hresult'] == 0 and value['authentication_invoked'], 'APPROVAL_RESULT_WITHOUT_AUTH')
    if value['availability'] is not None:
        _integer(value['availability'], 0, 4, 'APPROVAL_AVAILABILITY_INVALID')
    for name in ('started_qpc', 'finished_qpc', 'qpc_frequency'):
        _integer(value[name], 1, 0x7FFFFFFFFFFFFFFF, 'APPROVAL_NATIVE_TIME_INVALID')
    require(value['finished_qpc'] >= value['started_qpc'], 'APPROVAL_NATIVE_TIME_ROLLBACK')
    require(type(value['provenance']) is dict and
        canonical_bytes(value['provenance']) == canonical_bytes(helper.as_dict()),
        'APPROVAL_HELPER_PROVENANCE_MISMATCH')
    body = b'' if request is None else request.canonical_wire
    if type(request) is EnrollmentRequest:
        require(request.challenge_id == challenge_id
            and request.helper_identity == request.ui_identity == helper.identity,
            'APPROVAL_ENROLLMENT_HELPER_BINDING_MISMATCH')
    display = b'' if request is None else _display_bytes(request)
    request_hash = '' if request is None else request.input_commitment
    display_hash = '' if request is None else _display_commitment(request)
    require(value['request_commitment'] == request_hash and value['display_commitment'] == display_hash
        and value['body_sha256'] == hashlib.sha256(body).hexdigest()
        and value['display_sha256'] == hashlib.sha256(display).hexdigest(), 'APPROVAL_BODY_OR_DISPLAY_MISMATCH')
    if mode != 'interactive':
        require(not value['authentication_invoked'] and not value['hardware_click']
            and value['native_result'] is None and value['status'] not in ('VERIFIED', 'DENIED'),
            'APPROVAL_NONINTERACTIVE_AUTHENTICATION')
    if value['status'] == 'VERIFIED':
        require(value['authentication_invoked'] and value['hardware_click'] and value['display_exact']
            and value['native_result'] == 0 and value['native_hresult'] == 0
            and value['availability'] == 0, 'APPROVAL_VERIFIED_RESULT_INVALID')
    if value['authentication_invoked']:
        require(mode == 'interactive' and value['hardware_click'] and value['display_exact']
            and value['availability'] == 0, 'APPROVAL_AUTH_WITHOUT_DISPLAY_OR_INPUT')
    require(value['status'] != 'DISPLAY_BOUND_UNSHOWN' or
        mode == 'inspect' and value['display_exact'] and value['availability'] == 0,
        'APPROVAL_HIDDEN_DISPLAY_INVALID')
    require(value['status'] != 'AVAILABLE' or mode == 'availability' and value['availability'] == 0,
            'APPROVAL_AVAILABILITY_RESULT_INVALID')
    require(value['status'] != 'DENIED' or mode == 'interactive' and value['authentication_invoked']
        and value['native_hresult'] == 0 and type(value['native_result']) is int
        and 1 <= value['native_result'] <= 6, 'APPROVAL_DENIAL_RESULT_INVALID')
    module = value.get('interop_module')
    require(module is None or type(module) is str and 1 <= len(module) <= 32767,
            'APPROVAL_INTEROP_MODULE_INVALID')
    ceremony_nonce = request.ceremony_nonce if type(request) is EnrollmentRequest else nonce.hex()
    return NativeApprovalResult(value['status'], challenge_id, ceremony_nonce, mode, request_hash,
        display_hash, value['display_exact'], value['availability'], value['authentication_invoked'],
        value['hardware_click'], value['native_hresult'], value['native_result'], helper,
        value['started_qpc'], value['finished_qpc'], value['qpc_frequency'], module, bool(cancelled))


class NativeApprovalError(ContractError):
    def __init__(self, code, session, primary, cleanup_errors=()):
        super().__init__(code)
        self.owned_session = session
        self.owned_process = session.process
        self.primary_error = primary
        self.cleanup_errors = tuple(cleanup_errors)

    def close_cleanup(self):
        self.owned_session.close()


class _NativeApi(_ControlApi):
    def __init__(self):
        super().__init__()
        library = C.WinDLL('kernel32.dll', use_last_error=True, winmode=0x800)
        kernelbase = C.WinDLL('kernelbase.dll', use_last_error=True, winmode=0x800)
        p = C.POINTER
        for name, restype, args in (
            ('CreateEventW', HANDLE, [C.c_void_p, BOOL, BOOL, C.c_wchar_p]),
            ('GetCurrentProcess', HANDLE, []),
            ('DuplicateHandle', BOOL, [HANDLE, HANDLE, HANDLE, p(HANDLE), DWORD, BOOL, DWORD]),
            ('SetEvent', BOOL, [HANDLE]),
            ('WaitForSingleObject', DWORD, [HANDLE, DWORD]),
        ):
            function = getattr(library, name)
            function.restype, function.argtypes = restype, args
            setattr(self, name, function)
        self.CompareObjectHandles = kernelbase.CompareObjectHandles
        self.CompareObjectHandles.restype, self.CompareObjectHandles.argtypes = BOOL, [HANDLE, HANDLE]


class NativeApprovalOwner:
    """Explicit trusted composition; captured integrations cannot be request fields.

    `retain_native_approval`/`require_current` is a proposed canonical integration,
    not supplied here. Passing a callable is not proof that it is that owner.
    The actual NativeSessionClock interface is clock() -> (previous, current).
    No database transaction is held over the human wait.
    """
    def __init__(self, helper_path, helper_sha256, *, temporary_root,
                 canonical_owner=None, clock_owner=None, helper_source_commitment=None):
        require(type(helper_sha256) is str and _HASH.fullmatch(helper_sha256), 'APPROVAL_HELPER_HASH_REQUIRED')
        self.helper_path = _path(str(helper_path), directory=False)
        self.temporary_root = _path(str(temporary_root), directory=True)
        self.helper_sha256 = helper_sha256
        if helper_source_commitment is not None:
            commitment(helper_source_commitment)
        self.helper_source_commitment = helper_source_commitment
        self._canonical_owner, self._clock_owner = canonical_owner, clock_owner
        self._retain = getattr(canonical_owner, 'retain_native_approval', None)
        self._retain_enrollment = getattr(canonical_owner, 'retain_native_enrollment', None)
        self._clock = getattr(clock_owner, 'clock', None)
        self._lock = threading.RLock()
        self._active = None

    def availability(self, *, timeout_ms=5000):
        return self._begin('availability', None, None, timeout_ms)

    def inspect_request(self, request, *, timeout_ms=5000):
        return self._begin('inspect', request, None, timeout_ms)

    def cancel_without_prompt(self, request, *, timeout_ms=5000):
        return self._begin('cancel', request, None, timeout_ms)

    def begin_interactive(self, request, *, original_context, timeout_ms=120000):
        require(self._canonical_owner is not None and self._clock_owner is not None
            and callable(self._retain) and callable(self._clock)
            and original_context is not None and self.helper_source_commitment is not None,
            'APPROVAL_CANONICAL_INTEGRATION_UNAVAILABLE')
        return self._begin('interactive', request, original_context, timeout_ms)

    def prepare_enrollment(self, *, timeout_ms=120000):
        require(self.helper_source_commitment is not None,
                'APPROVAL_ENROLLMENT_PREPARATION_UNAVAILABLE')
        _timeout(timeout_ms)
        # An inert measured child is not admission. Its gate stays closed until
        # an exact declared body and the selected owner capability are bound.
        frame, _ = _frame('availability', 'enrollment-' + secrets.token_hex(16),
            secrets.token_bytes(32), None, timeout_ms)
        session = NativeApprovalSession(self, 'prepared', None, None, timeout_ms, frame)
        session._enrollment = True
        session.ceremony_nonce = secrets.token_hex(16)
        return self._start_session(session)

    def begin_enrollment(self, request, *, prepared=None, original_context=None):
        require(type(prepared) is NativeApprovalSession and prepared._owner is self,
                'APPROVAL_ENROLLMENT_BODY_AND_KERNEL_UNAVAILABLE')
        return prepared.begin_enrollment(request, original_context=original_context)

    def cancel_current(self):
        with self._lock:
            session = self._active
        if session is not None:
            session.cancel()

    def _begin(self, mode, request, original_context, timeout_ms):
        frame, frozen = _frame(mode, 'approval-' + secrets.token_hex(16), secrets.token_bytes(32), request, timeout_ms)
        session = NativeApprovalSession(self, mode, frozen, original_context, timeout_ms, frame)
        return self._start_session(session)

    def _start_session(self, session):
        with self._lock:
            require(self._active is None, 'APPROVAL_CEREMONY_ALREADY_OWNED')
            self._active = session  # Publish custody before any fallible native call.
        try:
            session._launch()
            return session
        except BaseException as primary:
            session._launching = False
            session._child_handles.extend(_exception_data(primary).get('control_handles', ()))
            session._adopt_pending_slots()
            errors = session._cleanup_after_failure()
            session._expose(primary, errors)
            if isinstance(primary, (KeyboardInterrupt, SystemExit)):
                raise
            raise NativeApprovalError('APPROVAL_START_FAILED', session, primary, errors) from primary


class NativeApprovalSession:
    def __init__(self, owner, mode, request, original_context, timeout_ms, frame):
        self._owner, self.mode, self.request = owner, mode, request
        self._context, self.timeout_ms, self._frame = original_context, timeout_ms, frame
        self._bound_context = original_context
        self._bound_request_wire = None if request is None else request.canonical_wire
        # Values are the exact frame commitment; no public request can choose a nonce.
        count = struct.unpack('<I', frame[16:20])[0]
        self.challenge_id = frame[20:20 + count].decode('ascii')
        self._nonce = frame[20 + count:52 + count]
        self.ceremony_nonce = self._nonce.hex()
        self._enrollment = False
        self._enrollment_binding = None
        self._api = self._image_api = self._token_api = None
        self._handles, self._child_handles = {}, []
        self._image = self._token = self._interop_image = None
        self._pending_slots = []
        self._closing_handles = {}
        self.process = self.helper_evidence = None
        self._launch_error = None
        self._lease_cm = self._lease = self._current = None
        self._lease_entered = False
        self._stop, self._io_lock, self._event_lock = threading.Event(), threading.RLock(), threading.RLock()
        self._launching, self._closed = True, False
        self._response_bytes, self._result = b'', None
        self._started_at = time.perf_counter_ns()
        # The caller's allowance includes startup, binding, gate and waiting.
        # Neither opening the gate nor polling can issue another allowance.
        self._deadline_at = self._started_at + timeout_ms*1_000_000
        self._elapsed_last, self._elapsed_failure = self._started_at, None
        self._elapsed_resolution = max(1,math.ceil(time.get_clock_info('perf_counter').resolution*1_000_000_000))
        self._first_clock = self._last_clock = None
        self._native_exited = False
        self._gate_may_open = False
        self.native_facts = {}

    def _fail_budget(self, primary):
        errors = []
        try: self.cancel()
        except BaseException as secondary: errors.append(secondary)
        self._expose(primary,errors)
        raise primary

    def _remaining_budget(self):
        if self._elapsed_failure is not None:
            raise self._elapsed_failure
        try:
            current = time.perf_counter_ns()
            require(current >= self._elapsed_last,'APPROVAL_ELAPSED_ROLLBACK')
        except BaseException as primary:
            self._elapsed_failure = primary
            self._fail_budget(primary)
        self._elapsed_last = current
        remaining = self._deadline_at-current-2*self._elapsed_resolution
        self.native_facts['budget'] = dict(started_perf_ns=self._started_at,
            original_deadline_perf_ns=self._deadline_at,observed_perf_ns=current,
            resolution_ns=self._elapsed_resolution,remaining_ns=remaining)
        return remaining

    def _gate_frame(self,mode,request,*,enrollment=False):
        milliseconds = min(self.timeout_ms,self._remaining_budget()//1_000_000)
        if milliseconds < 20:
            self._fail_budget(ContractError('APPROVAL_JOINT_BUDGET_EXPIRED'))
        return _frame(mode,self.challenge_id,self._nonce,request,milliseconds,enrollment=enrollment)

    def _require_gate_budget(self):
        if self._remaining_budget() <= 0:
            self._fail_budget(ContractError('APPROVAL_JOINT_BUDGET_EXPIRED'))

    def _cancel_expired_budget(self):
        if self._remaining_budget() <= 0 and not self._stop.is_set():
            try: self.cancel()
            except BaseException as secondary:
                primary = ContractError('APPROVAL_JOINT_BUDGET_EXPIRED')
                self._expose(primary,(secondary,))
                raise primary

    def _expose(self, primary, errors):
        # Control exceptions keep their exact identity and recoverable custody.
        try:
            note = getattr(primary, 'add_note', None)
            if errors and callable(note):
                note('Native approval cleanup is retained on owned_session; ' + str(len(errors)) + ' attempt(s) failed.')
        except BaseException:
            pass
        data = _exception_data(primary)
        previous = dict.get(data,'cleanup_errors',())
        if type(previous) is not tuple: previous = ()
        combined = previous+tuple(error for error in errors if not any(error is old for old in previous))
        dict.update(data,owned_session=self,owned_process=self.process,
            cleanup_errors=combined,close_cleanup=self.close)

    def _clock_current(self):
        pair = self._owner._clock()
        require(type(pair) is tuple and len(pair) == 2 and all(type(item) is ClockSample for item in pair),
                'APPROVAL_CANONICAL_CLOCK_PAIR_REQUIRED')
        previous, current = pair
        previous.__post_init__(); current.__post_init__()
        require_clock_progress(previous, current)
        if self._last_clock is not None:
            require_clock_progress(self._last_clock, current)
        require_deadline_current(self.request.deadline, previous, current)
        if self._enrollment:
            require_enrollment_current(self.request, self.request, previous, current)
        if self._first_clock is None:
            self._first_clock = previous
        self._last_clock = current
        return current

    def _require_current(self):
        require(callable(self._current) and self.helper_evidence is not None,
                'APPROVAL_CANONICAL_LEASE_UNAVAILABLE')
        require(self.request.canonical_wire == self._bound_request_wire and self._context is self._bound_context,
                'APPROVAL_FROZEN_REQUEST_OR_CONTEXT_CHANGED')
        self._clock_current()
        require(self._current(self.request.canonical_wire, self.challenge_id, self.ceremony_nonce,
            self.helper_evidence, self._context) is None, 'APPROVAL_CANONICAL_LEASE_REJECTED')
        return self._clock_current()

    def _code_commitment(self):
        require(self.helper_evidence is not None and self._owner.helper_source_commitment is not None
            and 'interop_library' in self.native_facts, 'APPROVAL_CODE_BINDING_UNAVAILABLE')
        return digest('native-owner-approval-build-v1', {
            'image_digest': self.helper_evidence.identity.image_digest,
            'source_commitment': self._owner.helper_source_commitment, 'protocol': PROTOCOL,
            'interop_library_sha256': self.native_facts['interop_library']['sha256']})

    @property
    def enrollment_binding(self):
        require(self._enrollment and self._enrollment_binding is not None and not self._closed,
                'APPROVAL_ENROLLMENT_PREPARATION_REQUIRED')
        return self._enrollment_binding

    def _receive_preparation(self):
        # Enrollment-only executable mode emits this observation without a
        # request, visible window or UserConsentVerifier verification call.
        while True:
            require(not self._stop.is_set(), 'APPROVAL_CANCELLED_BEFORE_GATE')
            self._require_gate_budget()
            require(time.perf_counter_ns() - self._started_at < 8_000_000_000,
                    'APPROVAL_STARTUP_WINDOW_EXPIRED')
            self._read()
            if len(self._response_bytes) >= 12:
                raw = self._response_bytes
                require(raw[:8] == _RESPONSE_MAGIC, 'APPROVAL_PREPARATION_FRAME')
                count = struct.unpack('<I', raw[8:12])[0]
                require(0 < count <= MAX_OUTPUT, 'APPROVAL_PREPARATION_FRAME')
                if len(raw) >= count + 12:
                    require(len(raw) == count + 12, 'APPROVAL_PREPARATION_TRAILING')
                    value = strict_loads(raw[12:])
                    require(type(value) is dict and canonical_bytes(value) == raw[12:],
                            'APPROVAL_PREPARATION_NONCANONICAL')
                    if value.get('status') == 'ERROR':
                        _response(raw, mode='availability', challenge_id=self.challenge_id,
                            nonce=self._nonce, request=None, helper=self.helper_evidence, cancelled=self._stop.is_set())
                    require(type(value) is dict and set(value) == {'protocol', 'phase', 'authentication_invoked',
                        'availability', 'interop_module', 'provenance', 'started_qpc', 'finished_qpc', 'qpc_frequency'},
                        'APPROVAL_PREPARATION_FIELDS')
                    require(value['protocol'] == PROTOCOL and value['phase'] == 'PREPARED'
                        and value['authentication_invoked'] is False, 'APPROVAL_PREPARATION_PROFILE')
                    require(type(value['provenance']) is dict and canonical_bytes(value['provenance']) ==
                        canonical_bytes(self.helper_evidence.as_dict()), 'APPROVAL_HELPER_PROVENANCE_MISMATCH')
                    _integer(value['availability'], 0, 4, 'APPROVAL_AVAILABILITY_INVALID')
                    for name in ('started_qpc', 'finished_qpc', 'qpc_frequency'):
                        _integer(value[name], 1, 0x7FFFFFFFFFFFFFFF, 'APPROVAL_NATIVE_TIME_INVALID')
                    require(value['finished_qpc'] >= value['started_qpc'], 'APPROVAL_NATIVE_TIME_ROLLBACK')
                    self._pin_interop(value['interop_module'])
                    code = self._code_commitment()
                    self._enrollment_binding = NativeEnrollmentBinding(self.challenge_id, self.ceremony_nonce,
                        self.helper_evidence, self.helper_evidence.identity, code, code,
                        value['interop_module'], self.native_facts['interop_library']['sha256'], value['availability'])
                    self.native_facts['preparation'] = value
                    self.native_facts['body_bound'] = False
                    self._response_bytes = b''
                    return
            require(self.process.poll() is None, 'APPROVAL_HELPER_EXITED_BEFORE_PREPARATION')
            time.sleep(0.005)

    def inspect_enrollment(self, request):
        return self._bind_enrollment('inspect', request, None)

    def cancel_enrollment(self, request):
        return self._bind_enrollment('cancel', request, None)

    def begin_enrollment(self, request, *, original_context):
        owner = self._owner
        require(owner._canonical_owner is not None and owner._clock_owner is not None
            and callable(owner._retain_enrollment) and callable(owner._clock) and original_context is not None,
            'APPROVAL_ENROLLMENT_CANONICAL_INTEGRATION_UNAVAILABLE')
        return self._bind_enrollment('interactive', request, original_context)

    def _bind_enrollment(self, mode, request, original_context):
        with self._io_lock:
            require(self._enrollment and self.mode == 'prepared' and not self._closed and not self._launching,
                    'APPROVAL_ENROLLMENT_ALREADY_BOUND_OR_CLOSED')
            require(type(request) is EnrollmentRequest, 'APPROVAL_DECLARED_BODY_REQUIRED')
            frozen = decode_enrollment_request(request.canonical_wire)
            binding = self.enrollment_binding
            require(frozen.challenge_id == self.challenge_id and frozen.ceremony_nonce == self.ceremony_nonce
                and frozen.helper_identity == frozen.ui_identity == binding.helper.identity
                and frozen.helper_commitment == frozen.ui_commitment == binding.helper_commitment,
                'APPROVAL_ENROLLMENT_PREPARATION_MISMATCH')
            frame, frozen = self._gate_frame(mode,frozen,enrollment=True)
            require(not self._stop.is_set(), 'APPROVAL_CANCELLED_BEFORE_GATE')
            try:
                require(self.process.poll() is None and not self._stop.is_set(), 'APPROVAL_CANCELLED_BEFORE_GATE')
                self._measure_helper()
                self._pin_interop(binding.interop_module)
                require(self._code_commitment() == binding.helper_commitment, 'APPROVAL_CODE_BINDING_CHANGED')
                require(not self._stop.is_set(), 'APPROVAL_CANCELLED_BEFORE_GATE')
                # Adopt the immutable body only after every measured identity
                # is matched. All native observations retain cleanup custody.
                self.mode, self.request, self._context, self._frame = mode, frozen, original_context, frame
                self._bound_context, self._bound_request_wire = original_context, frozen.canonical_wire
                if mode == 'interactive':
                    self._lease_cm = self._owner._retain_enrollment(frozen.canonical_wire, original_context)
                    require(callable(getattr(self._lease_cm, '__enter__', None))
                        and callable(getattr(self._lease_cm, '__exit__', None)), 'APPROVAL_RETAINED_CONTEXT_REQUIRED')
                    self._lease = self._lease_cm.__enter__(); self._lease_entered = True
                    self._current = getattr(self._lease, 'require_current', None)
                    require(callable(self._current), 'APPROVAL_CANONICAL_LEASE_UNAVAILABLE')
                    self._require_current()
                require(time.perf_counter_ns() - self._started_at < 8_000_000_000,
                        'APPROVAL_STARTUP_WINDOW_EXPIRED')
                frame,frozen = self._gate_frame(mode,frozen,enrollment=True)
                self._frame = frame
                buffer, count = C.create_string_buffer(frame, len(frame)), DWORD()
                require(self._api.WriteFile(self._handles['input'], buffer, len(frame), C.byref(count), None)
                    and count.value == len(frame), 'APPROVAL_INPUT_WRITE_FAILED')
                self._close_named('input')
                with self._event_lock:
                    require(not self._stop.is_set(), 'APPROVAL_CANCELLED_BEFORE_GATE')
                    if mode == 'interactive': self._require_current()
                    self._require_gate_budget()
                    self._gate_may_open = True
                    require(self._api.SetEvent(self._handles['gate']), 'APPROVAL_START_GATE_FAILED')
                self.native_facts['body_bound'] = True
                self.native_facts['helper_evidence'] = self.helper_evidence.as_dict()
                return self
            except BaseException as primary:
                errors = self._cleanup_after_failure()
                self._expose(primary, errors)
                if isinstance(primary, (KeyboardInterrupt, SystemExit)):
                    raise
                raise NativeApprovalError('APPROVAL_ENROLLMENT_BIND_FAILED', self, primary, errors) from primary

    def _event(self, name):
        value = self._api.CreateEventW(None, True, False, None)
        require(value, 'APPROVAL_EVENT_CREATE_FAILED')
        self._handles[name] = value
        duplicate = HANDLE()
        self._pending_slots.append(duplicate)
        process = self._api.GetCurrentProcess()
        require(self._api.DuplicateHandle(process, value, process, C.byref(duplicate), 0, True, 2),
                'APPROVAL_EVENT_DUPLICATE_FAILED')
        self._adopt_pending_slots()
        return duplicate.value

    def _adopt_pending_slots(self):
        # Keep output storage reachable before the API can raise or CPython can
        # deliver a control exception after it has populated native out handles.
        for slot in self._pending_slots:
            if slot.value and slot.value not in self._child_handles:
                self._child_handles.append(slot.value)
        self._pending_slots.clear()

    def _pipe(self, name, *, child_reads):
        read, write = HANDLE(), HANDLE()
        self._pending_slots.extend((read, write))
        attributes = _Attributes(C.sizeof(_Attributes), None, True)
        require(self._api.CreatePipe(C.byref(read), C.byref(write), C.byref(attributes), 65536),
                'APPROVAL_PIPE_CREATE_FAILED')
        self._adopt_pending_slots()
        parent, child = (write.value, read.value) if child_reads else (read.value, write.value)
        require(self._api.SetHandleInformation(parent, 1, 0), 'APPROVAL_PARENT_INHERITANCE_FAILED')
        self._handles[name] = parent
        self._child_handles.remove(parent)
        return child

    def _measure_helper(self):
        require(self.process.poll() is None, 'APPROVAL_HELPER_EXITED_BEFORE_GATE')
        self._token_api = _TokenApi()
        self._token_slot = HANDLE()
        try:
            opened = self._token_api.OpenProcessToken(self.process._process, 8, C.byref(self._token_slot))
        finally:
            self._token = self._token_slot.value
        require(opened,
                'APPROVAL_HELPER_TOKEN_OPEN_FAILED')
        facts = _token_facts(self._token_api, self._token, 1)
        evidence = _evidence(self.process.resource_identity, facts)
        require(evidence.identity.image_digest == 'sha256:' + self._owner.helper_sha256,
                'APPROVAL_HELPER_IMAGE_MISMATCH')
        require(self.helper_evidence is None or self.helper_evidence == evidence,
                'APPROVAL_HELPER_PROVENANCE_CHANGED')
        self.helper_evidence = evidence
        self._close_owned_handle(self._token, self._token_api.close_handle)
        self._token = None

    def _launch(self):
        self._api, self._image_api = _NativeApi(), _API()
        self._image = _open_image(self._image_api, self._owner.helper_path)
        actual, self._image_identity = _hash_image(self._image_api, self._image)
        require(actual == self._owner.helper_sha256, 'APPROVAL_HELPER_IMAGE_MISMATCH')
        if self.mode == 'interactive':
            self._lease_cm = self._owner._retain(self.request.canonical_wire, self._context)
            require(callable(getattr(self._lease_cm, '__enter__', None))
                and callable(getattr(self._lease_cm, '__exit__', None)), 'APPROVAL_RETAINED_CONTEXT_REQUIRED')
            self._lease = self._lease_cm.__enter__()
            self._lease_entered = True
            self._current = getattr(self._lease, 'require_current', None)
            require(callable(self._current), 'APPROVAL_CANONICAL_LEASE_UNAVAILABLE')
        child_input = self._pipe('input', child_reads=True)
        child_output = self._pipe('output', child_reads=False)
        child_cancel, child_gate = self._event('cancel'), self._event('gate')
        handles = (child_input, child_output, child_cancel, child_gate)
        try:
            arguments = tuple(map(str, handles)) + ((_ENROLLMENT_PREPARATION,) if self._enrollment else ())
            self.process = WindowsOwnedProcess.launch(self._owner.helper_path, arguments,
                cwd=self._owner.temporary_root, environment=controlled_environment(self._owner.temporary_root),
                inherited_handles=handles, expected_image_sha256=self._owner.helper_sha256)
        except BaseException as primary:
            self.process = _exception_data(primary).get('owned_process')
            if callable(_exception_data(primary).get('close_cleanup')):
                self._launch_error = primary
            raise
        self.native_facts.update(pid=self.process.pid, creation_time=self.process.creation_time,
            image_sha256=self.process.image_sha256, inherited_handles=4, prompt_mode=self.mode)
        errors = self._close_children()
        if errors:
            raise errors[0]
        self._measure_helper()
        if self._enrollment:
            self._receive_preparation()
            self._launching = False
            return
        if self.mode == 'interactive':
            self._require_current()
        require(not self._stop.is_set(), 'APPROVAL_CANCELLED_BEFORE_GATE')
        require(time.perf_counter_ns() - self._started_at < 8_000_000_000,
                'APPROVAL_STARTUP_WINDOW_EXPIRED')
        self._frame,self.request = self._gate_frame(self.mode,self.request)
        # Gate prevents the real child from authenticating before lifetime/token
        # capture. One bounded write fits the explicitly created 64 KiB pipe.
        buffer, count = C.create_string_buffer(self._frame, len(self._frame)), DWORD()
        require(self._api.WriteFile(self._handles['input'], buffer, len(self._frame), C.byref(count), None)
            and count.value == len(self._frame), 'APPROVAL_INPUT_WRITE_FAILED')
        self._close_named('input')  # Exact EOF is part of the native protocol.
        with self._event_lock:
            require(not self._stop.is_set(), 'APPROVAL_CANCELLED_BEFORE_GATE')
            if self.mode == 'interactive': self._require_current()
            self._require_gate_budget()
            self._gate_may_open = True  # Custody precedes a possibly completed SetEvent.
            require(self._api.SetEvent(self._handles['gate']), 'APPROVAL_START_GATE_FAILED')
        self._launching = False
        self.native_facts['helper_evidence'] = self.helper_evidence.as_dict()

    def cancel(self):
        self._stop.set()  # Logical Stop never waits for native work or a poll lock.
        with self._event_lock:
            handle = self._handles.get('cancel')
            if handle is not None:
                require(self._api.SetEvent(handle), 'APPROVAL_CANCEL_SIGNAL_FAILED')

    def _read(self):
        handle = self._handles.get('output')
        require(handle is not None, 'APPROVAL_OUTPUT_UNAVAILABLE')
        available = DWORD()
        if not self._api.PeekNamedPipe(handle, None, 0, None, C.byref(available), None):
            require(C.get_last_error() == 109, 'APPROVAL_OUTPUT_PEEK_FAILED')
            return
        require(len(self._response_bytes) + available.value <= MAX_OUTPUT + 12, 'APPROVAL_OUTPUT_BOUND')
        if available.value:
            buffer, count = C.create_string_buffer(available.value), DWORD()
            require(self._api.ReadFile(handle, buffer, available.value, C.byref(count), None)
                and 0 < count.value <= available.value, 'APPROVAL_OUTPUT_READ_FAILED')
            self._response_bytes += buffer.raw[:count.value]

    def poll(self):
        try:
            return self._poll()
        except BaseException as primary:
            self._expose(primary, ())
            raise

    def _pin_interop(self, module):
        if module is None:
            return
        path = Path(_path(module, directory=False))
        system32 = Path(os.environ['SystemRoot']) / 'System32'
        require(os.path.normcase(str(path.parent)) == os.path.normcase(str(system32))
            and path.name.casefold() == 'windows.security.credentials.ui.userconsentverifier.dll',
            'APPROVAL_INTEROP_MODULE_UNQUALIFIED')
        if self._interop_image is not None:
            require('interop_library' in self.native_facts and
                self.native_facts['interop_library']['path'] == str(path) and
                _file_identity(self._image_api, self._interop_image) == self._interop_identity,
                'APPROVAL_INTEROP_OBSERVATION_PENDING')
            return
        self._interop_image = _open_image(self._image_api, str(path))
        value, identity = _hash_image(self._image_api, self._interop_image)
        self._interop_identity = identity
        self.native_facts['interop_library'] = {'path': str(path), 'sha256': value,
            'native_file_identity': identity}

    def _poll(self):
        with self._io_lock:
            require(not self._closed and not self._launching and self.process is not None,
                    'APPROVAL_SESSION_NOT_READY')
            require(self.mode != 'prepared', 'APPROVAL_ENROLLMENT_BINDING_REQUIRED')
            self._cancel_expired_budget()
            if self._result is not None:
                # Cancellation after a result cannot be converted back into an
                # authorizing outcome by polling the cached result.
                if self._stop.is_set() and not self._result.effective_cancelled:
                    from dataclasses import replace
                    self._result = replace(self._result, effective_cancelled=True)
                return self._result
            self._read()
            exit_code = self.process.poll()
            if exit_code is None:
                return None
            require(self.process.active_process_count() == 0, 'APPROVAL_HELPER_JOB_NOT_EMPTY')
            self._native_exited = True
            self._read()
            self.native_facts.update(exit_code=exit_code, empty_job=True)
            require(exit_code == 0, 'APPROVAL_HELPER_EXIT_FAILURE')
            require(_file_identity(self._image_api, self._image) == self._image_identity,
                    'APPROVAL_HELPER_FILE_CHANGED')
            result = _response(self._response_bytes, mode=self.mode, challenge_id=self.challenge_id,
                nonce=self._nonce, request=self.request, helper=self.helper_evidence,
                cancelled=self._stop.is_set())
            self._pin_interop(result.interop_module)
            if self.mode == 'interactive':
                self._require_current()
            self._cancel_expired_budget()
            if self._stop.is_set() and not result.effective_cancelled:
                from dataclasses import replace
                result = replace(result,effective_cancelled=True)
            self._result = result
            return result

    def wait(self, timeout_seconds):
        require(type(timeout_seconds) in (int, float) and math.isfinite(timeout_seconds)
            and 0 <= timeout_seconds <= 360, 'APPROVAL_WAIT_INVALID')
        end = min(self._deadline_at,time.perf_counter_ns()+math.floor(timeout_seconds*1_000_000_000))
        while True:
            result = self.poll()
            if result is not None:
                return result
            if time.perf_counter_ns() >= end:
                return None  # Caller retains the real session and process.
            time.sleep(min(0.01, max(0, (end - time.perf_counter_ns()) / 1_000_000_000)))

    def transcript(self):
        try:
            with self._io_lock:
                # Consuming a cached result is an authorization boundary too.
                # poll() need not have been called since verification completed.
                self._require_gate_budget()
                require(self.mode == 'interactive' and not self._closed and self._result is not None
                    and self._result.reported_verified and not self._stop.is_set(), 'APPROVAL_VERIFIED_CEREMONY_REQUIRED')
                current = self._require_current()
                self._require_gate_budget()  # All native/currentness work is charged.
                require(not self._stop.is_set(), 'APPROVAL_CANCELLED')
                helper = self.helper_evidence.identity
                code = digest('native-owner-approval-build-v1', {'image_digest': helper.image_digest,
                    'source_commitment': self._owner.helper_source_commitment, 'protocol': PROTOCOL,
                    'interop_library_sha256': self.native_facts['interop_library']['sha256']})
                if self._enrollment:
                    require(code == self.request.helper_commitment == self.request.ui_commitment,
                            'APPROVAL_ENROLLMENT_CODE_BINDING_CHANGED')
                transcript = NativeApprovalTranscript(self.challenge_id, self.ceremony_nonce, self.request.input_commitment,
                    _display_commitment(self.request), self.request.principal_id, self.request.actor_session,
                    helper, code, helper, code, current, self._result.native_hresult, self._result.native_result)
                self._require_gate_budget()  # No newly computed authorizing value after expiry.
                require(not self._stop.is_set(), 'APPROVAL_CANCELLED')
                return transcript
        except BaseException as primary:
            self._expose(primary,())
            raise

    def _close_children(self):
        errors = []
        for handle in tuple(self._child_handles):
            try:
                self._close_owned_handle(handle)
                self._child_handles.remove(handle)
            except BaseException as error:
                errors.append(error)
        return errors

    def _close_named(self, name):
        handle = self._handles.get(name)
        if handle is not None:
            self._close_owned_handle(handle)
            del self._handles[name]

    @property
    def pending_native_cleanup(self):
        return tuple({'handle': row['handle'], 'guard': row['guard'].value,
            'guard_uncertain': row['guard_uncertain']} for row in self._closing_handles.values())

    def _close_owned_handle(self, handle, closer=None):
        """AC2's retained-duplicate retry fence, reused without authority semantics.

        A missing/reused raw slot is never closed. If the last duplicate's own
        release is interrupted, retain its uncertainty and refuse blind retry.
        """
        row = self._closing_handles.setdefault(handle,
            {'handle': handle, 'guard': HANDLE(), 'guard_uncertain': False})
        original, guard = row['handle'], row['guard']
        require(not row['guard_uncertain'], 'APPROVAL_HANDLE_GUARD_RELEASE_UNCERTAIN')
        if original is not None:
            if not guard.value:
                current = self._api.GetCurrentProcess()
                row['guard_uncertain'] = True
                duplicated = self._api.DuplicateHandle(current, original, current, C.byref(guard), 0, False, 2)
                row['guard_uncertain'] = not bool(duplicated) and bool(guard.value)
                require(duplicated, 'APPROVAL_CLEANUP_HANDLE_PIN_UNAVAILABLE')
            if not self._api.CompareObjectHandles(original, guard.value):
                row['handle'] = None
            else:
                try:
                    require((closer or self._api.close)(original) is None, 'APPROVAL_HANDLE_CLOSE_RESPONSE_INVALID')
                    require(not self._api.CompareObjectHandles(original, guard.value),
                            'APPROVAL_HANDLE_CLOSE_NOT_OBSERVED')
                except BaseException as primary:
                    try:
                        if not self._api.CompareObjectHandles(original, guard.value):
                            row['handle'] = None
                    except BaseException as secondary:
                        _exception_data(primary)['cleanup_observation_error'] = secondary
                    raise
                row['handle'] = None
        if guard.value:
            row['guard_uncertain'] = True
            require(self._api.CloseHandle(guard.value), 'APPROVAL_HANDLE_GUARD_CLOSE_UNRESOLVED')
            guard.value = None
            row['guard_uncertain'] = False
        del self._closing_handles[handle]

    def _cleanup_after_failure(self):
        errors = []
        try:
            self.cancel()
        except BaseException as error:
            errors.append(error)
        if self.process is not None and not self.process.lifetime_closed:
            try:
                # Once the interactive gate might have opened, only cancellation
                # plus observed settlement can retire it. Killing a helper is not
                # proof that a separate OS authentication operation has settled.
                if self.mode != 'interactive' or not self._gate_may_open:
                    self.process.terminate(125)
                require(self.process.wait(5) and self.process.active_process_count() == 0,
                        'APPROVAL_STARTUP_CLEANUP_PENDING')
                self.native_facts.update(exit_code=self.process.poll(), empty_job=True)
            except BaseException as error:
                errors.append(error)
        try:
            self.close()
        except BaseException as error:
            errors.append(error)
        return errors

    def close(self):
        with self._io_lock:
            if self._closed:
                return
            require(not self._launching, 'APPROVAL_STARTUP_STILL_OWNED')
            errors = []
            if self.process is not None and not self.process.lifetime_closed:
                exit_code = self.process.poll()
                require(exit_code is not None and self.process.active_process_count() == 0,
                        'APPROVAL_NATIVE_LIFETIME_PENDING')
                self.native_facts.update(exit_code=exit_code, empty_job=True)
                try:
                    self.process.close()
                except BaseException as error:
                    errors.append(error)
            if self._launch_error is not None:
                try:
                    self._launch_error.close_cleanup()
                    self._launch_error = None
                except BaseException as error:
                    errors.append(error)
            if self._token is not None:
                try:
                    self._close_owned_handle(self._token, self._token_api.close_handle)
                    self._token = None
                except BaseException as error:
                    errors.append(error)
            errors.extend(self._close_children())
            # Cancellation and close have the same short handle-custody lock;
            # cancellation never waits for process/native I/O observation.
            with self._event_lock:
                for name in tuple(self._handles):
                    try:
                        self._close_named(name)
                    except BaseException as error:
                        errors.append(error)
            if self._image is not None:
                try:
                    self._close_owned_handle(self._image, self._image_api.close)
                    self._image = None
                except BaseException as error:
                    errors.append(error)
            if self._interop_image is not None:
                try:
                    self._close_owned_handle(self._interop_image, self._image_api.close)
                    self._interop_image = None
                except BaseException as error:
                    errors.append(error)
            if self._lease_entered:
                try:
                    released = self._lease_cm.__exit__(None, None, None)
                    require(released is None or released is False,
                            'APPROVAL_CANONICAL_RELEASE_INVALID')
                    self._lease_entered = False
                except BaseException as error:
                    errors.append(error)
            if errors:
                primary = errors[0]
                self._expose(primary, errors)
                raise primary
            self._closed = True
            self.native_facts['closed'] = True
            with self._owner._lock:
                if self._owner._active is self:
                    self._owner._active = None
