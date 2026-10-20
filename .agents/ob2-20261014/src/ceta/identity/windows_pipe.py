"""Windows x64 development ingress, with native peer evidence and closed authority.

This module does not install a service or establish component isolation against
an unrestricted same-account process, administrator, transferred pipe handle,
process injection or changed Python modules. Executable-file hashes identify the
held file, not every byte executing in a process. Registration is a trusted local
composition action; requests cannot register themselves or choose their identity.
Pipe freshness observations are not the trusted authority clock.

Executable byte reads use overlapped I/O and the actual request deadline. Native
process/token/file-metadata queries and initial handle opens are still synchronous
Windows calls; deadline checks detect late completion but cannot preempt a hung
metadata call. Supervisor containment/qualification for those calls remains open.
Windows also documents that an overlapped ReadFile can behave synchronously while
blocked. The bounded pending-I/O wait/drain is not proof of preempting every native
call or filesystem driver; that supervisor qualification remains open as well.
"""
from __future__ import annotations

import ctypes as C
from dataclasses import dataclass
import hashlib
import math
import os
import re
import secrets
import struct
import sys
import threading
import time

from ceta.contracts.kernel_transactions import PeerIdentity, require
from ceta.contracts.local_ipc import IngressState, LocalMessage, OPERATIONS, decode_message
from ceta.contracts.store_transactions import identifier
from ceta.contracts.wire import canonical_bytes, ContractError, MAX_WIRE_BYTES, RecordCodec

DWORD = C.c_uint32
BOOL = C.c_int32
HANDLE = C.c_void_p
ULONG_PTR = C.c_size_t
INVALID_HANDLE = C.c_void_p(-1).value
ERROR_IO_PENDING = 997
ERROR_MORE_DATA = 234
ERROR_PIPE_CONNECTED = 535
ERROR_PIPE_BUSY = 231
ERROR_FILE_NOT_FOUND = 2
ERROR_NOT_FOUND = 1168
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 258
PIPE_PREFIX = "\\\\.\\pipe\\CETA-"
MAX_TOKEN_BYTES = 1024 * 1024  # Explicit defensive query bound; unsupported sizes deny.
CANCEL_DRAIN_SECONDS = 5.0  # Engineering cleanup bound, not an authority deadline.
IDENTITY_CAPTURE_SECONDS = 5.0  # Finite engineering capture bound, not a source threshold.


class FILETIME(C.Structure):
    _fields_ = [("low", DWORD), ("high", DWORD)]


class LUID(C.Structure):
    _fields_ = [("low", DWORD), ("high", C.c_int32)]


class SID_AND_ATTRIBUTES(C.Structure):
    _fields_ = [("sid", C.c_void_p), ("attributes", DWORD)]


class TOKEN_GROUPS_ONE(C.Structure):
    _fields_ = [("count", DWORD), ("groups", SID_AND_ATTRIBUTES * 1)]


class TOKEN_STATISTICS(C.Structure):
    _fields_ = [("token_id", LUID), ("authentication_id", LUID), ("expiration", C.c_int64),
                ("token_type", DWORD), ("impersonation_level", DWORD), ("dynamic_charged", DWORD),
                ("dynamic_available", DWORD), ("group_count", DWORD), ("privilege_count", DWORD),
                ("modified_id", LUID)]


class SECURITY_ATTRIBUTES(C.Structure):
    _fields_ = [("length", DWORD), ("descriptor", C.c_void_p), ("inherit", BOOL)]


class OVERLAPPED(C.Structure):
    _fields_ = [("internal", ULONG_PTR), ("internal_high", ULONG_PTR),
                ("offset", DWORD), ("offset_high", DWORD), ("event", HANDLE)]


class FILE_INFORMATION(C.Structure):
    _fields_ = [("attributes", DWORD), ("creation", FILETIME), ("access", FILETIME),
                ("write", FILETIME), ("volume", DWORD), ("size_high", DWORD), ("size_low", DWORD),
                ("links", DWORD), ("index_high", DWORD), ("index_low", DWORD)]


def _error(code, error=None):
    if error is None:
        error = C.get_last_error()
    raise ContractError(code + ":" + str(error))


class _Api:
    def __init__(self):
        require(sys.platform == "win32" and C.sizeof(C.c_void_p) == 8, "WINDOWS_X64_REQUIRED")
        self.kernel = C.WinDLL("kernel32.dll", use_last_error=True, winmode=0x800)
        self.advapi = C.WinDLL("advapi32.dll", use_last_error=True, winmode=0x800)
        p = C.POINTER
        definitions = (
            (self.kernel, "CreateNamedPipeW", HANDLE, [C.c_wchar_p, DWORD, DWORD, DWORD, DWORD, DWORD, DWORD, p(SECURITY_ATTRIBUTES)]),
            (self.kernel, "CreateFileW", HANDLE, [C.c_wchar_p, DWORD, DWORD, p(SECURITY_ATTRIBUTES), DWORD, DWORD, HANDLE]),
            (self.kernel, "ConnectNamedPipe", BOOL, [HANDLE, p(OVERLAPPED)]),
            (self.kernel, "DisconnectNamedPipe", BOOL, [HANDLE]),
            (self.kernel, "SetNamedPipeHandleState", BOOL, [HANDLE, p(DWORD), p(DWORD), p(DWORD)]),
            (self.kernel, "ReadFile", BOOL, [HANDLE, C.c_void_p, DWORD, p(DWORD), p(OVERLAPPED)]),
            (self.kernel, "WriteFile", BOOL, [HANDLE, C.c_void_p, DWORD, p(DWORD), p(OVERLAPPED)]),
            (self.kernel, "GetOverlappedResult", BOOL, [HANDLE, p(OVERLAPPED), p(DWORD), BOOL]),
            (self.kernel, "CancelIoEx", BOOL, [HANDLE, p(OVERLAPPED)]),
            (self.kernel, "CreateEventW", HANDLE, [p(SECURITY_ATTRIBUTES), BOOL, BOOL, C.c_wchar_p]),
            (self.kernel, "WaitForSingleObject", DWORD, [HANDLE, DWORD]),
            (self.kernel, "CloseHandle", BOOL, [HANDLE]),
            (self.kernel, "GetCurrentProcess", HANDLE, []),
            (self.kernel, "GetCurrentThread", HANDLE, []),
            (self.kernel, "GetCurrentThreadId", DWORD, []),
            (self.kernel, "GetProcessId", DWORD, [HANDLE]),
            (self.kernel, "OpenProcess", HANDLE, [DWORD, BOOL, DWORD]),
            (self.kernel, "GetProcessTimes", BOOL, [HANDLE, p(FILETIME), p(FILETIME), p(FILETIME), p(FILETIME)]),
            (self.kernel, "QueryFullProcessImageNameW", BOOL, [HANDLE, DWORD, C.c_wchar_p, p(DWORD)]),
            (self.kernel, "GetNamedPipeClientProcessId", BOOL, [HANDLE, p(DWORD)]),
            (self.kernel, "GetNamedPipeClientSessionId", BOOL, [HANDLE, p(DWORD)]),
            (self.kernel, "GetNamedPipeServerProcessId", BOOL, [HANDLE, p(DWORD)]),
            (self.kernel, "GetNamedPipeServerSessionId", BOOL, [HANDLE, p(DWORD)]),
            (self.kernel, "GetFileInformationByHandle", BOOL, [HANDLE, p(FILE_INFORMATION)]),
            (self.kernel, "GetDriveTypeW", DWORD, [C.c_wchar_p]),
            (self.kernel, "LocalFree", C.c_void_p, [C.c_void_p]),
            (self.kernel, "TerminateProcess", BOOL, [HANDLE, DWORD]),
            (self.advapi, "OpenProcessToken", BOOL, [HANDLE, DWORD, p(HANDLE)]),
            (self.advapi, "OpenThreadToken", BOOL, [HANDLE, DWORD, BOOL, p(HANDLE)]),
            (self.advapi, "GetTokenInformation", BOOL, [HANDLE, DWORD, C.c_void_p, DWORD, p(DWORD)]),
            (self.advapi, "IsValidSid", BOOL, [C.c_void_p]),
            (self.advapi, "GetLengthSid", DWORD, [C.c_void_p]),
            (self.advapi, "ConvertSidToStringSidW", BOOL, [C.c_void_p, p(C.c_void_p)]),
            (self.advapi, "ConvertStringSecurityDescriptorToSecurityDescriptorW", BOOL, [C.c_wchar_p, DWORD, p(C.c_void_p), p(DWORD)]),
            (self.advapi, "ImpersonateNamedPipeClient", BOOL, [HANDLE]),
            (self.advapi, "RevertToSelf", BOOL, []),
        )
        try:
            for library, name, restype, argtypes in definitions:
                function = getattr(library, name)
                function.restype, function.argtypes = restype, argtypes
                setattr(self, name, function)
        except AttributeError as error:
            raise ContractError("WINDOWS_API_UNAVAILABLE") from error

    def close_handle(self, handle):
        if handle not in (None, 0, INVALID_HANDLE):
            if not self.CloseHandle(handle):
                _error("WINDOWS_HANDLE_CLOSE_FAILED")

    def fatal(self):
        # A failed revert or undrained I/O cannot safely return to Python callers.
        try:
            self.TerminateProcess(self.GetCurrentProcess(), 125)
        finally:
            os._exit(125)


def _deadline(timeout_seconds):
    require(type(timeout_seconds) in (int, float) and math.isfinite(timeout_seconds)
            and timeout_seconds > 0, "WINDOWS_TIMEOUT_REQUIRED")
    end = time.monotonic() + timeout_seconds
    require(math.isfinite(end), "WINDOWS_TIMEOUT_REQUIRED")
    return end


def _wait(api, event, deadline):
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        milliseconds = min(0xFFFFFFFE, max(1, math.ceil(remaining * 1000)))
        result = api.WaitForSingleObject(event, milliseconds)
        if result == WAIT_OBJECT_0:
            return True
        if result != WAIT_TIMEOUT:
            _error("WINDOWS_WAIT_FAILED")


def _cancel_and_drain(api, handle, overlapped):
    if not api.CancelIoEx(handle, C.byref(overlapped)):
        error = C.get_last_error()
        if error != ERROR_NOT_FOUND:  # Completion can win the cancellation race.
            api.fatal()
    transferred = DWORD()
    complete = api.GetOverlappedResult(handle, C.byref(overlapped), C.byref(transferred), False)
    if not complete:
        error = C.get_last_error()
        if error in (ERROR_IO_PENDING, 996):
            try:
                signaled = _wait(api, overlapped.event, time.monotonic() + CANCEL_DRAIN_SECONDS)
            except BaseException:
                api.fatal()
            if not signaled:
                api.fatal()
            complete = api.GetOverlappedResult(handle, C.byref(overlapped), C.byref(transferred), False)
            error = 0 if complete else C.get_last_error()
        if not complete and error not in (995, ERROR_MORE_DATA, 109, 232, 233):
            # Unknown errors do not establish that native ownership has ended.
            api.fatal()
    return transferred.value


def _io(api, operation, handle, deadline, buffer=None, count=0, *, offset=None):
    require(time.monotonic() < deadline, "WINDOWS_PIPE_TIMEOUT")
    if offset is not None:
        require(type(offset) is int and 0 <= offset <= 0xFFFFFFFFFFFFFFFF, "WINDOWS_IO_OFFSET_REQUIRED")
    event = api.CreateEventW(None, True, False, None)
    if not event:
        _error("WINDOWS_EVENT_CREATE_FAILED")
    overlapped = OVERLAPPED()
    overlapped.event = event
    if offset is not None:
        overlapped.offset, overlapped.offset_high = offset & 0xFFFFFFFF, offset >> 32
    pending = False
    try:
        require(time.monotonic() < deadline, "WINDOWS_PIPE_TIMEOUT")
        # Conservatively retain storage if a Python interruption occurs as the
        # native call returns, before its completion status can be inspected.
        pending = True
        if operation == "connect":
            ok = api.ConnectNamedPipe(handle, C.byref(overlapped))
        else:
            call = api.ReadFile if operation == "read" else api.WriteFile
            ok = call(handle, buffer, count, None, C.byref(overlapped))
        error = 0 if ok else C.get_last_error()
        if operation == "connect" and error == ERROR_PIPE_CONNECTED:
            pending = False
            return 0, False
        if not ok and error not in (ERROR_IO_PENDING, ERROR_MORE_DATA):
            pending = False
            _error("WINDOWS_PIPE_" + operation.upper() + "_FAILED", error)
        if not ok and error == ERROR_IO_PENDING:
            pending = True
            if not _wait(api, event, deadline):
                raise ContractError("WINDOWS_PIPE_TIMEOUT")
        transferred = DWORD()
        complete = api.GetOverlappedResult(handle, C.byref(overlapped), C.byref(transferred), False)
        error = 0 if complete else C.get_last_error()
        if error in (ERROR_IO_PENDING, 996):
            pending = True
            _error("WINDOWS_PIPE_INCOMPLETE", error)
        pending = False
        if not complete and not (operation == "read" and error == ERROR_MORE_DATA):
            _error("WINDOWS_PIPE_" + operation.upper() + "_COMPLETION_FAILED", error)
        require(time.monotonic() < deadline, "WINDOWS_PIPE_TIMEOUT")
        return transferred.value, error == ERROR_MORE_DATA
    except BaseException:
        if pending:
            _cancel_and_drain(api, handle, overlapped)
            pending = False
        raise
    finally:
        # Buffer, OVERLAPPED and event stay alive until actual completion/drain.
        if pending:
            api.fatal()
        api.close_handle(event)


def _query(api, token, information_class):
    needed = DWORD()
    ok = api.GetTokenInformation(token, information_class, None, 0, C.byref(needed))
    error = 0 if ok else C.get_last_error()
    require(not ok and error == 122 and 1 <= needed.value <= MAX_TOKEN_BYTES, "WINDOWS_TOKEN_QUERY_SIZE")
    buffer = C.create_string_buffer(needed.value)
    if not api.GetTokenInformation(token, information_class, buffer, needed.value, C.byref(needed)):
        _error("WINDOWS_TOKEN_QUERY_FAILED")
    # Do not parse allocation padding as returned token data. A size change
    # between these two native queries is unsupported and fails closed.
    require(needed.value == C.sizeof(buffer), "WINDOWS_TOKEN_QUERY_SIZE")
    return buffer


def _sid(api, pointer, buffer):
    address = pointer if type(pointer) is int else C.cast(pointer, C.c_void_p).value
    start, end = C.addressof(buffer), C.addressof(buffer) + C.sizeof(buffer)
    require(address is not None and start <= address and address + 8 <= end, "WINDOWS_SID_BUFFER")
    require(bool(api.IsValidSid(address)), "WINDOWS_SID_INVALID")
    length = api.GetLengthSid(address)
    require(8 <= length <= 68 and address + length <= end, "WINDOWS_SID_BUFFER")
    return C.string_at(address, length)


def _sid_groups(api, buffer):
    require(C.sizeof(buffer) >= C.sizeof(DWORD), "WINDOWS_GROUPS_BUFFER")
    count = DWORD.from_buffer(buffer).value
    if count == 0:
        return ()
    offset = TOKEN_GROUPS_ONE.groups.offset
    require(offset + count * C.sizeof(SID_AND_ATTRIBUTES) <= C.sizeof(buffer), "WINDOWS_GROUPS_BUFFER")
    result = []
    for index in range(count):
        item = SID_AND_ATTRIBUTES.from_buffer(buffer, offset + index * C.sizeof(SID_AND_ATTRIBUTES))
        result.append((_sid(api, item.sid, buffer), item.attributes))
    require(len(result) == len(set(result)), "WINDOWS_DUPLICATE_TOKEN_GROUP")
    return tuple(sorted(result))


def _scalar(api, token, information_class):
    buffer = _query(api, token, information_class)
    require(C.sizeof(buffer) == C.sizeof(DWORD), "WINDOWS_TOKEN_SCALAR")
    return DWORD.from_buffer(buffer).value


def _restriction_flag(api, token):
    # Class 21 only: documented DWORD, or the one-byte BOOLEAN actually observed
    # on the reviewed Windows build 26300. Other scalar classes stay exact DWORD.
    buffer = _query(api, token, 21)
    size = C.sizeof(buffer)
    require(size in (1, C.sizeof(DWORD)), "WINDOWS_TOKEN_RESTRICTION_LAYOUT")
    value = buffer.raw[0] if size == 1 else DWORD.from_buffer(buffer).value
    require(value in (0, 1), "WINDOWS_TOKEN_RESTRICTION_FLAG")
    return value


def _luid(value):
    return value.low, value.high


@dataclass(frozen=True)
class _TokenFacts:
    user_sid: bytes
    logon_sid: bytes
    authentication_id: tuple[int, int]
    terminal_session: int
    has_restrictions: int
    restricted_sids: tuple
    integrity_sid: bytes
    integrity_attributes: int
    elevation_type: int
    ui_access: int
    token_id: tuple[int, int]
    modified_id: tuple[int, int]
    token_type: int
    impersonation_level: int

    def authorization_facts(self):
        # A duplicated impersonation token has a distinct token-object identity.
        return (self.user_sid, self.logon_sid, self.authentication_id, self.terminal_session,
                self.has_restrictions, self.restricted_sids, self.integrity_sid,
                self.integrity_attributes, self.elevation_type, self.ui_access)


def _token_facts(api, token, expected_type):
    first = _query(api, token, 10)
    require(C.sizeof(first) == C.sizeof(TOKEN_STATISTICS), "WINDOWS_TOKEN_STATISTICS")
    statistics = TOKEN_STATISTICS.from_buffer_copy(first)
    require(statistics.token_type == expected_type, "WINDOWS_TOKEN_TYPE")
    if expected_type == 2:
        require(statistics.impersonation_level == 2, "WINDOWS_IMPERSONATION_LEVEL_UNSUPPORTED")
    require(_scalar(api, token, 29) == 0, "WINDOWS_APPCONTAINER_UNSUPPORTED")
    user = _query(api, token, 1)
    require(C.sizeof(user) >= C.sizeof(SID_AND_ATTRIBUTES), "WINDOWS_TOKEN_USER")
    user_sid = _sid(api, SID_AND_ATTRIBUTES.from_buffer(user).sid, user)
    groups = _sid_groups(api, _query(api, token, 28))
    require(len(groups) == 1 and groups[0][1] & 0xC0000000 == 0xC0000000, "WINDOWS_LOGON_SID_UNSUPPORTED")
    integrity = _query(api, token, 25)
    require(C.sizeof(integrity) >= C.sizeof(SID_AND_ATTRIBUTES), "WINDOWS_INTEGRITY_BUFFER")
    label = SID_AND_ATTRIBUTES.from_buffer(integrity)
    integrity_sid = _sid(api, label.sid, integrity)
    require(integrity_sid[0:2] == b"\x01\x01" and integrity_sid[2:8] == b"\x00\x00\x00\x00\x00\x10",
            "WINDOWS_INTEGRITY_SID_UNSUPPORTED")
    restricted = _sid_groups(api, _query(api, token, 11))
    has_restrictions = _restriction_flag(api, token)
    elevation, ui_access = _scalar(api, token, 18), _scalar(api, token, 26)
    terminal_session = _scalar(api, token, 12)
    require(has_restrictions in (0, 1) and elevation in (1, 2, 3) and ui_access in (0, 1), "WINDOWS_TOKEN_FACTS_UNSUPPORTED")
    last = _query(api, token, 10)
    require(bytes(first) == bytes(last), "WINDOWS_TOKEN_CHANGED_DURING_QUERY")
    return _TokenFacts(user_sid, groups[0][0], _luid(statistics.authentication_id), terminal_session,
                       has_restrictions, restricted, integrity_sid, label.attributes, elevation, ui_access,
                       _luid(statistics.token_id), _luid(statistics.modified_id), statistics.token_type,
                       statistics.impersonation_level if expected_type == 2 else 0)


def _process_facts(api, process):
    token = HANDLE()
    try:
        if not api.OpenProcessToken(process, 0x0008, C.byref(token)):
            _error("WINDOWS_PROCESS_TOKEN_UNAVAILABLE")
        return _token_facts(api, token, 1)
    finally:
        api.close_handle(token.value)


def _message_facts(api, pipe):
    token = HANDLE()
    prior = HANDLE()
    thread_id = api.GetCurrentThreadId()
    if api.OpenThreadToken(api.GetCurrentThread(), 0x0008, True, C.byref(prior)):
        api.close_handle(prior.value)
        raise ContractError("WINDOWS_PREEXISTING_THREAD_TOKEN_UNSUPPORTED")
    if C.get_last_error() != 1008:  # ERROR_NO_TOKEN is the required server state.
        _error("WINDOWS_INITIAL_THREAD_TOKEN_UNAVAILABLE")
    try:
        if not api.ImpersonateNamedPipeClient(pipe):
            _error("WINDOWS_PIPE_IMPERSONATION_FAILED")
        if not api.OpenThreadToken(api.GetCurrentThread(), 0x0008, True, C.byref(token)):
            _error("WINDOWS_MESSAGE_TOKEN_UNAVAILABLE")
        return _token_facts(api, token, 2)
    finally:
        # No arbitrary Python handler or async scheduling runs in this interval.
        # The initial no-token check makes unconditional revert safe even if
        # impersonation failed, or an interruption preceded its Python result.
        try:
            if api.GetCurrentThreadId() != thread_id:
                api.fatal()
            reverted = api.RevertToSelf()
        except BaseException:
            api.fatal()
        if not reverted:
            api.fatal()
        api.close_handle(token.value)


def _creation(api, process):
    values = [FILETIME() for _ in range(4)]
    if not api.GetProcessTimes(process, *(C.byref(value) for value in values)):
        _error("WINDOWS_PROCESS_LIFETIME_UNAVAILABLE")
    return values[0].low | values[0].high << 32


def _image_name(api, process):
    buffer = C.create_unicode_buffer(32768)
    count = DWORD(len(buffer))
    if not api.QueryFullProcessImageNameW(process, 0, buffer, C.byref(count)):
        _error("WINDOWS_PROCESS_IMAGE_UNAVAILABLE")
    value = buffer.value
    require(0 < count.value < len(buffer) and len(value) == count.value
            and re.match(r"^[A-Za-z]:\\", value) is not None
            and api.GetDriveTypeW(value[:3]) == 3, "WINDOWS_LOCAL_IMAGE_REQUIRED")
    return value


def _file_information(api, handle):
    value = FILE_INFORMATION()
    if not api.GetFileInformationByHandle(handle, C.byref(value)):
        _error("WINDOWS_IMAGE_INFORMATION_UNAVAILABLE")
    require(not value.attributes & (0x400 | 0x10), "WINDOWS_IMAGE_REPARSE_OR_DIRECTORY")
    # Access time can change merely by reading; it is not an image identity.
    return (value.attributes, value.volume, value.index_high, value.index_low, value.size_high, value.size_low,
            value.creation.high, value.creation.low, value.write.high, value.write.low)


def _file_hash(api, handle, deadline):
    require(time.monotonic() < deadline, "WINDOWS_PIPE_TIMEOUT")
    before = _file_information(api, handle)
    expected_size = before[4] << 32 | before[5]
    require(time.monotonic() < deadline, "WINDOWS_PIPE_TIMEOUT")
    buffer = C.create_string_buffer(min(1024 * 1024, max(1, expected_size)))
    digest, size = hashlib.sha256(), 0
    while size < expected_size:
        requested = min(len(buffer), expected_size - size)
        # No shared file cursor: each overlapped operation binds an explicit byte
        # offset and drains pending cancellation before its storage is released.
        count, more = _io(api, "read", handle, deadline, buffer, requested, offset=size)
        require(0 < count <= requested and not more, "WINDOWS_IMAGE_READ_SIZE")
        size += count
        digest.update(buffer.raw[:count])
    require(size == expected_size and _file_information(api, handle) == before, "WINDOWS_IMAGE_CHANGED")
    require(time.monotonic() < deadline, "WINDOWS_PIPE_TIMEOUT")
    return digest.hexdigest(), before


@dataclass(frozen=True)
class WindowsPeerRegistration:
    pid: int
    principal_id: str
    session_id: str
    allowed_operations: frozenset[str]
    allowed_scopes: frozenset[str]
    image_path: str
    image_sha256: str
    process_creation: int
    token_facts: _TokenFacts


@dataclass
class _Registered:
    registration: WindowsPeerRegistration
    process: int
    image: int
    image_information: tuple


@dataclass(frozen=True)
class _Active:
    entry: _Registered
    pipe: int
    thread_id: int
    message: LocalMessage
    message_facts: tuple
    monotonic_deadline: float


class WindowsPeerRegistry:
    """Server-owned registration and opaque request contexts, not runtime grants."""
    def __init__(self):
        self._api = _Api()
        self._entries = {}
        self._active = {}
        self._lock = threading.RLock()
        self._closed = False

    def register(self, pid, principal_id, session_id, *, allowed_operations, allowed_scopes,
                 expected_image_sha256, expected_creation_time):
        identifier(principal_id)
        identifier(session_id)
        require(type(pid) is int and 0 < pid <= 0xFFFFFFFF, "WINDOWS_PID_REQUIRED")
        require(type(expected_creation_time) is int and 0 < expected_creation_time <= 0xFFFFFFFFFFFFFFFF,
                "WINDOWS_PEER_CREATION_TIME_REQUIRED")
        require(type(allowed_operations) in (set, frozenset, tuple, list) and allowed_operations
                and all(type(value) is str and value in OPERATIONS for value in allowed_operations), "WINDOWS_REGISTERED_OPERATIONS")
        require(type(allowed_scopes) in (set, frozenset, tuple, list) and allowed_scopes, "WINDOWS_REGISTERED_SCOPES")
        for value in allowed_scopes:
            identifier(value)
        require(type(expected_image_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", expected_image_sha256), "WINDOWS_IMAGE_DIGEST_REQUIRED")
        deadline = _deadline(IDENTITY_CAPTURE_SECONDS)
        with self._lock:
            require(not self._closed and pid not in self._entries, "WINDOWS_REGISTRY_CLOSED_OR_DUPLICATE")
            process = self._api.OpenProcess(0x1000 | 0x00100000, False, pid)
            if not process:
                _error("WINDOWS_REGISTERED_PROCESS_UNAVAILABLE")
            image = None
            try:
                require(self._api.WaitForSingleObject(process, 0) == WAIT_TIMEOUT
                        and self._api.GetProcessId(process) == pid, "WINDOWS_REGISTERED_PROCESS_NOT_LIVE")
                creation = _creation(self._api, process)
                # The parent-selected lifetime must match before identity/routes
                # are assigned; matching PID and image cannot defeat PID reuse.
                require(creation == expected_creation_time, "WINDOWS_PEER_CREATION_MISMATCH")
                image_path = _image_name(self._api, process)
                # Retain a noninheritable local file handle denying write/delete sharing.
                image = self._api.CreateFileW(image_path, 0x0001 | 0x0080, 0x0001, None, 3,
                                               0x00200000 | 0x40000000, None)
                if image in (None, 0, INVALID_HANDLE):
                    _error("WINDOWS_PINNED_IMAGE_UNAVAILABLE")
                digest, information = _file_hash(self._api, image, deadline)
                require(digest == expected_image_sha256, "WINDOWS_IMAGE_DIGEST_MISMATCH")
                facts = _process_facts(self._api, process)
                registration = WindowsPeerRegistration(pid, principal_id, session_id, frozenset(allowed_operations),
                                                       frozenset(allowed_scopes), image_path, digest, creation, facts)
                entry = _Registered(registration, process, image, information)
                self._revalidate(entry, deadline)
                self._entries[pid] = entry
                return registration
            except BaseException:
                self._api.close_handle(image)
                self._api.close_handle(process)
                raise

    def _revalidate(self, entry, deadline):
        require(time.monotonic() < deadline, "WINDOWS_PIPE_TIMEOUT")
        require(not self._closed and self._api.WaitForSingleObject(entry.process, 0) == WAIT_TIMEOUT,
                "WINDOWS_REGISTERED_PROCESS_NOT_LIVE")
        registration = entry.registration
        require(self._api.GetProcessId(entry.process) == registration.pid
                and _creation(self._api, entry.process) == registration.process_creation
                and _image_name(self._api, entry.process) == registration.image_path, "WINDOWS_PROCESS_LIFETIME_OR_IMAGE_CHANGED")
        digest, information = _file_hash(self._api, entry.image, deadline)
        require(digest == registration.image_sha256 and information == entry.image_information, "WINDOWS_PINNED_IMAGE_CHANGED")
        require(_process_facts(self._api, entry.process) == registration.token_facts, "WINDOWS_PROCESS_TOKEN_CHANGED")
        require(self._api.WaitForSingleObject(entry.process, 0) == WAIT_TIMEOUT, "WINDOWS_REGISTERED_PROCESS_NOT_LIVE")
        require(time.monotonic() < deadline, "WINDOWS_PIPE_TIMEOUT")

    def _pipe_peer(self, pipe, deadline):
        require(time.monotonic() < deadline, "WINDOWS_PIPE_TIMEOUT")
        pid, session = DWORD(), DWORD()
        if not self._api.GetNamedPipeClientProcessId(pipe, C.byref(pid)):
            _error("WINDOWS_PIPE_PID_UNAVAILABLE")
        if not self._api.GetNamedPipeClientSessionId(pipe, C.byref(session)):
            _error("WINDOWS_PIPE_SESSION_UNAVAILABLE")
        entry = self._entries.get(pid.value)
        require(entry is not None, "WINDOWS_PIPE_CLIENT_UNREGISTERED")
        self._revalidate(entry, deadline)
        require(session.value == entry.registration.token_facts.terminal_session, "WINDOWS_PIPE_PROCESS_SESSION_MISMATCH")
        facts = _message_facts(self._api, pipe)
        require(facts.authorization_facts() == entry.registration.token_facts.authorization_facts(), "WINDOWS_MESSAGE_TOKEN_MISMATCH")
        self._revalidate(entry, deadline)
        return entry, facts.authorization_facts()

    def _header_peer(self, pipe, deadline):
        with self._lock:
            require(not self._closed, "WINDOWS_REGISTRY_CLOSED")
            return self._pipe_peer(pipe, deadline)

    def _activate(self, pipe, entry, message, facts, deadline):
        with self._lock:
            current, current_facts = self._pipe_peer(pipe, deadline)
            require(current is entry and current_facts == facts, "WINDOWS_PIPE_PEER_CHANGED")
            context = object()
            self._active[context] = _Active(entry, pipe, self._api.GetCurrentThreadId(), message, facts, deadline)
            return context

    def _checked(self, context):
        require(not self._closed, "WINDOWS_REGISTRY_CLOSED")
        try:
            active = self._active.get(context)
        except TypeError:
            active = None
        require(active is not None and active.thread_id == self._api.GetCurrentThreadId(), "WINDOWS_REQUEST_CONTEXT_UNAVAILABLE")
        require(time.monotonic() < active.monotonic_deadline, "WINDOWS_REQUEST_CONTEXT_EXPIRED")
        message = active.message
        require(message.issued_at_ms <= time.time_ns() // 1_000_000 < message.expires_at_ms, "IPC_MESSAGE_EXPIRED_OR_FUTURE")
        entry, facts = self._pipe_peer(active.pipe, active.monotonic_deadline)
        require(entry is active.entry and facts == active.message_facts, "WINDOWS_ACTIVE_PEER_CHANGED")
        # Native image/token queries can consume the remaining validity window.
        # Their completion cannot renew either transport or envelope validity.
        require(time.monotonic() < active.monotonic_deadline, "WINDOWS_REQUEST_CONTEXT_EXPIRED")
        require(message.issued_at_ms <= time.time_ns() // 1_000_000 < message.expires_at_ms,
                "IPC_MESSAGE_EXPIRED_OR_FUTURE")
        return active

    def authenticate(self, context):
        with self._lock:
            active = self._checked(context)
            registration = active.entry.registration
            return PeerIdentity(registration.principal_id, registration.session_id)

    def task_owner_binding(self, context):
        """Stable account/principal custody for task content, never session authority."""
        with self._lock:
            active = self._checked(context)
            registration = active.entry.registration
            body = {"principal_id": registration.principal_id,
                    "user_sid_hex": registration.token_facts.user_sid.hex()}
            return "sha256:" + hashlib.sha256(b"CETA:task-owner:v1\0" + canonical_bytes(body)).hexdigest()

    def require_message(self, context, message):
        with self._lock:
            active = self._checked(context)
            require(type(message) is LocalMessage and message == active.message
                    and message.original_message == active.message.original_message, "WINDOWS_REQUEST_MESSAGE_BINDING")
            registration = active.entry.registration
            require(message.sender_session == registration.session_id
                    and message.operation in registration.allowed_operations
                    and message.scope_id in registration.allowed_scopes, "IPC_CALLER_SCOPE_DENIED")

    def _invalidate(self, context):
        if context is not None:
            with self._lock:
                self._active.pop(context, None)

    def _security_descriptor(self, *, duplex=False):
        with self._lock:
            require(not self._closed, "WINDOWS_REGISTRY_CLOSED")
            server = _process_facts(self._api, self._api.GetCurrentProcess())
            sids = {entry.registration.token_facts.user_sid for entry in self._entries.values()}
            def sid_text(wire):
                buffer = C.create_string_buffer(wire, len(wire))
                value = C.c_void_p()
                if not self._api.ConvertSidToStringSidW(buffer, C.byref(value)):
                    _error("WINDOWS_SID_CONVERSION_FAILED")
                try:
                    return C.wstring_at(value)
                finally:
                    if self._api.LocalFree(value) is not None:
                        _error("WINDOWS_LOCAL_FREE_FAILED")
            owner = sid_text(server.user_sid)
            # A SID ACL cannot distinguish two unrestricted processes of one user.
            sddl = "D:P(A;;0x001f01ff;;;" + owner + ")(A;;0x001f01ff;;;SY)"
            for sid in sorted(sids):
                if sid != server.user_sid:
                    rights = "0x00100183" if duplex else "0x00100082"
                    sddl += "(A;;" + rights + ";;;" + sid_text(sid) + ")"
            descriptor = C.c_void_p()
            if not self._api.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, C.byref(descriptor), None):
                _error("WINDOWS_PIPE_DACL_INVALID")
            require(descriptor.value is not None, "WINDOWS_PIPE_DACL_INVALID")
            return descriptor

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._active.clear()
            entries, self._entries = tuple(self._entries.values()), {}
            error = None
            for entry in entries:
                for handle in (entry.image, entry.process):
                    try:
                        self._api.close_handle(handle)
                    except BaseException as failure:
                        if error is None:
                            error = failure
            if error is not None:
                raise error


def _pipe_name(value):
    require(type(value) is str and value.startswith(PIPE_PREFIX), "WINDOWS_PIPE_NAMESPACE_REQUIRED")
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", value[len(PIPE_PREFIX):]), "WINDOWS_PIPE_INSTANCE_REQUIRED")
    return value


class WindowsServerBinding:
    """Client-owned pin from trusted parent selection, never pipe discovery.

    The selected creation time is mandatory: a PID obtained from an untrusted
    name or selected before process reuse cannot substitute for this lifetime.
    This binds a development process and held executable file; it does not
    qualify that process's loaded Python code or protection against injection.
    """
    def __init__(self, pid, *, expected_creation_time, expected_image_sha256):
        require(type(pid) is int and 0 < pid <= 0xFFFFFFFF, "WINDOWS_SERVER_PID_REQUIRED")
        require(type(expected_creation_time) is int and 0 < expected_creation_time <= 0xFFFFFFFFFFFFFFFF,
                "WINDOWS_SERVER_CREATION_TIME_REQUIRED")
        require(type(expected_image_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", expected_image_sha256),
                "WINDOWS_SERVER_IMAGE_DIGEST_REQUIRED")
        deadline = _deadline(IDENTITY_CAPTURE_SECONDS)
        self._api = _Api()
        self._lock = threading.Lock()
        self._closed = False
        self._process = self._image = None
        self._pid, self._creation_time = pid, expected_creation_time
        self._expected_image_sha256 = expected_image_sha256
        try:
            self._process = self._api.OpenProcess(0x1000 | 0x00100000, False, pid)
            if not self._process:
                _error("WINDOWS_SELECTED_SERVER_UNAVAILABLE")
            require(self._api.WaitForSingleObject(self._process, 0) == WAIT_TIMEOUT
                    and self._api.GetProcessId(self._process) == pid, "WINDOWS_SELECTED_SERVER_NOT_LIVE")
            require(_creation(self._api, self._process) == expected_creation_time, "WINDOWS_SERVER_CREATION_MISMATCH")
            self._image_path = _image_name(self._api, self._process)
            self._image = self._api.CreateFileW(self._image_path, 0x0001 | 0x0080, 0x0001,
                                                None, 3, 0x00200000 | 0x40000000, None)
            if self._image in (None, 0, INVALID_HANDLE):
                _error("WINDOWS_SELECTED_SERVER_IMAGE_UNAVAILABLE")
            digest, self._image_information = _file_hash(self._api, self._image, deadline)
            require(digest == expected_image_sha256, "WINDOWS_SERVER_IMAGE_DIGEST_MISMATCH")
            self._token_facts = _process_facts(self._api, self._process)
            self._revalidate(deadline)
        except BaseException:
            try:
                self._api.close_handle(self._image)
            finally:
                self._api.close_handle(self._process)
                self._closed = True
            raise

    def _revalidate(self, deadline):
        require(time.monotonic() < deadline, "WINDOWS_PIPE_TIMEOUT")
        require(not self._closed and self._api.WaitForSingleObject(self._process, 0) == WAIT_TIMEOUT,
                "WINDOWS_SELECTED_SERVER_NOT_LIVE")
        require(self._api.GetProcessId(self._process) == self._pid
                and _creation(self._api, self._process) == self._creation_time
                and _image_name(self._api, self._process) == self._image_path,
                "WINDOWS_SELECTED_SERVER_LIFETIME_OR_IMAGE_CHANGED")
        digest, information = _file_hash(self._api, self._image, deadline)
        require(digest == self._expected_image_sha256 and information == self._image_information,
                "WINDOWS_SELECTED_SERVER_IMAGE_CHANGED")
        require(_process_facts(self._api, self._process) == self._token_facts, "WINDOWS_SELECTED_SERVER_TOKEN_CHANGED")
        require(self._api.WaitForSingleObject(self._process, 0) == WAIT_TIMEOUT, "WINDOWS_SELECTED_SERVER_NOT_LIVE")
        require(time.monotonic() < deadline, "WINDOWS_PIPE_TIMEOUT")

    def _require_pipe(self, pipe, deadline):
        self._revalidate(deadline)
        pid, session = DWORD(), DWORD()
        if not self._api.GetNamedPipeServerProcessId(pipe, C.byref(pid)):
            _error("WINDOWS_PIPE_SERVER_PID_UNAVAILABLE")
        if not self._api.GetNamedPipeServerSessionId(pipe, C.byref(session)):
            _error("WINDOWS_PIPE_SERVER_SESSION_UNAVAILABLE")
        require(pid.value == self._pid and session.value == self._token_facts.terminal_session,
                "WINDOWS_PIPE_DESTINATION_MISMATCH")
        self._revalidate(deadline)

    def close(self):
        require(self._lock.acquire(blocking=False), "WINDOWS_SERVER_BINDING_BUSY")
        try:
            if not self._closed:
                self._closed = True
                try:
                    self._api.close_handle(self._image)
                finally:
                    self._api.close_handle(self._process)
                    self._image = self._process = None
        finally:
            self._lock.release()


class WindowsPipeServer:
    """Serial one-message receiver; return values stay local and confer no effects."""
    def __init__(self, pipe_name, registry, handler, codec, *, response_encoder=None):
        self._name = _pipe_name(pipe_name)
        require(type(registry) is WindowsPeerRegistry and callable(handler) and type(codec) is RecordCodec,
                "WINDOWS_PIPE_DEPENDENCIES_REQUIRED")
        self._registry, self._handler, self._codec = registry, handler, codec
        require(response_encoder is None or callable(response_encoder), "WINDOWS_RESPONSE_ENCODER_REQUIRED")
        self._response_encoder = response_encoder
        # A reconstructed receiver cannot reuse a generation with an empty replay
        # set. This nonce is owned here, never selected by a caller or request.
        self._ingress = IngressState(secrets.token_hex(32))
        self._api = registry._api
        self._lock = threading.Lock()
        self._closed = False
        self._pipe = None
        descriptor = registry._security_descriptor() if response_encoder is None else registry._security_descriptor(duplex=True)
        try:
            attributes = SECURITY_ATTRIBUTES(C.sizeof(SECURITY_ATTRIBUTES), descriptor, False)
            # Inbound, overlapped, first-instance; message type/read mode, local-only.
            direction = 0x00000001 if response_encoder is None else 0x00000003
            self._pipe = self._api.CreateNamedPipeW(self._name, direction | 0x40000000 | 0x00080000,
                                                  0x00000004 | 0x00000002 | 0x00000008,
                                                  1, 4096, 4096, 0, C.byref(attributes))
            if self._pipe in (None, 0, INVALID_HANDLE):
                self._pipe = None
                _error("WINDOWS_PIPE_OWNERSHIP_UNAVAILABLE")
        finally:
            if self._api.LocalFree(descriptor) is not None:
                self._api.close_handle(self._pipe)
                self._pipe = None
                _error("WINDOWS_LOCAL_FREE_FAILED")

    @property
    def receiver_generation(self):
        return self._ingress.generation

    def receive_once(self, timeout_seconds):
        deadline = _deadline(timeout_seconds)
        require(self._lock.acquire(blocking=False), "WINDOWS_PIPE_RECEIVER_BUSY")
        context = None
        connection_attempted = False
        try:
            require(not self._closed and self._pipe is not None, "WINDOWS_PIPE_SERVER_CLOSED")
            connection_attempted = True
            _io(self._api, "connect", self._pipe, deadline)
            header = C.create_string_buffer(4)
            count, more = _io(self._api, "read", self._pipe, deadline, header, 4)
            require(count == 4 and more, "WINDOWS_PIPE_HEADER_OR_SHORT_MESSAGE")
            entry, facts = self._registry._header_peer(self._pipe, deadline)
            require(time.monotonic() < deadline, "WINDOWS_PIPE_TIMEOUT")
            length = struct.unpack(">I", header.raw)[0]
            require(1 <= length <= MAX_WIRE_BYTES, "IPC_MESSAGE_SIZE_OR_CODEC")
            # No attacker-declared body allocation occurs before native identity.
            body = C.create_string_buffer(length)
            count, more = _io(self._api, "read", self._pipe, deadline, body, length)
            require(count == length and not more, "WINDOWS_PIPE_SHORT_OR_TRAILING_MESSAGE")
            message = decode_message(body.raw, self._codec)
            registration = entry.registration
            self._ingress.accept(message, authenticated_session=registration.session_id,
                                 allowed_operations=registration.allowed_operations,
                                 allowed_scopes=registration.allowed_scopes,
                                 now_ms=time.time_ns() // 1_000_000)
            # Replay is consumed before dispatch, even if the kernel later denies.
            context = self._registry._activate(self._pipe, entry, message, facts, deadline)
            self._registry.require_message(context, message)
            if self._response_encoder is None:
                return self._handler(message, context)
            try:
                result = self._handler(message, context)
            except ContractError as denial:
                # A denial can follow durable COMMIT. Its response must preserve
                # uncertainty; it cannot assert that no transition occurred.
                result = denial
            self._registry.require_message(context, message)
            response = self._response_encoder(message, result, self._codec)
            require(type(response) is bytes and 1 <= len(response) <= MAX_WIRE_BYTES,
                    "WINDOWS_RESPONSE_SIZE_OR_CODEC")
            framed = struct.pack(">I", len(response)) + response
            outgoing = C.create_string_buffer(framed, len(framed))
            count, more = _io(self._api, "write", self._pipe, deadline, outgoing, len(framed))
            require(count == len(framed) and not more, "WINDOWS_PIPE_RESPONSE_SHORT_WRITE")
            # Avoid unbounded FlushFileBuffers and avoid disconnect discarding
            # an unread reply. This bounded receipt is transport cleanup only.
            acknowledgment = C.create_string_buffer(32)
            count, more = _io(self._api, "read", self._pipe, deadline, acknowledgment, 32)
            require(count == 32 and not more and acknowledgment.raw == hashlib.sha256(response).digest(),
                    "WINDOWS_PIPE_RESPONSE_RECEIPT_INVALID")
            self._registry.require_message(context, message)
            return result
        finally:
            try:
                self._registry._invalidate(context)
            finally:
                try:
                    if connection_attempted:
                        if not self._api.DisconnectNamedPipe(self._pipe):
                            error = C.get_last_error()
                            # Reset even if a connect completed concurrently with
                            # cancellation. No old connection is reused next time.
                            if error not in (233, 232, 109):
                                self._closed = True
                                try:
                                    self._api.close_handle(self._pipe)
                                finally:
                                    self._pipe = None
                                _error("WINDOWS_PIPE_DISCONNECT_FAILED", error)
                finally:
                    self._lock.release()

    def close(self):
        # Active receives have a finite timeout. Never close a handle under pending
        # I/O or a callback; the supervisor must join that receive before closing.
        require(self._lock.acquire(blocking=False), "WINDOWS_PIPE_RECEIVER_BUSY")
        try:
            if not self._closed:
                self._closed = True
                self._api.close_handle(self._pipe)
                self._pipe = None
        finally:
            self._lock.release()


def send_pipe_message(pipe_name, message_wire, timeout_seconds=5.0, *, expected_server):
    """Submit to the verified development endpoint; no acknowledgment or authority.

    A post-write denial cannot retract submitted bytes. Neither a completed write
    nor this process/file binding establishes accepted work or completed effects.
    """
    name = _pipe_name(pipe_name)
    require(type(message_wire) is bytes and 1 <= len(message_wire) <= MAX_WIRE_BYTES, "IPC_MESSAGE_SIZE_OR_CODEC")
    require(type(expected_server) is WindowsServerBinding, "WINDOWS_EXPECTED_SERVER_BINDING_REQUIRED")
    deadline = _deadline(timeout_seconds)
    require(expected_server._lock.acquire(blocking=False), "WINDOWS_SERVER_BINDING_BUSY")
    api = expected_server._api
    pipe = None
    try:
        expected_server._revalidate(deadline)
        while True:
            require(time.monotonic() < deadline, "WINDOWS_PIPE_TIMEOUT")
            # Only data-write access; no create-instance, DACL or owner rights.
            # Explicit identification/impersonation SQOS and noninheritable handle.
            pipe = api.CreateFileW(name, 0x0002, 0, None, 3, 0x40000000 | 0x00100000 | 0x00020000, None)
            if pipe not in (None, 0, INVALID_HANDLE):
                break
            error = C.get_last_error()
            pipe = None
            if error not in (ERROR_PIPE_BUSY, ERROR_FILE_NOT_FOUND):
                _error("WINDOWS_PIPE_CLIENT_OPEN_FAILED", error)
            # A bounded retry is local transport waiting, never permit renewal.
            time.sleep(min(0.005, max(0.0, deadline - time.monotonic())))
        expected_server._require_pipe(pipe, deadline)
        require(time.monotonic() < deadline, "WINDOWS_PIPE_TIMEOUT")
        wire = struct.pack(">I", len(message_wire)) + message_wire
        buffer = C.create_string_buffer(wire, len(wire))
        require(time.monotonic() < deadline, "WINDOWS_PIPE_TIMEOUT")
        count, more = _io(api, "write", pipe, deadline, buffer, len(wire))
        require(count == len(wire) and not more, "WINDOWS_PIPE_CLIENT_SHORT_WRITE")
        # The held connection was bound before its write; the receiver may now
        # disconnect without an acknowledgment. Recheck the same selected process
        # lifetime/file/token, without requiring the closed connection to respond.
        expected_server._revalidate(deadline)
        require(time.monotonic() < deadline, "WINDOWS_PIPE_TIMEOUT")
        return None
    finally:
        try:
            api.close_handle(pipe)
        finally:
            expected_server._lock.release()


def send_pipe_request(pipe_name, message_wire, codec, timeout_seconds=5.0, *, expected_server):
    """Exchange one bound request/result with the selected duplex service.

    Call from an owned client process: synchronous native metadata/API entry can
    still occupy this stack. A transport exception after submission requires
    reconciliation and is never evidence that the kernel did not commit.
    """
    from ceta.contracts.local_results import decode_response
    name = _pipe_name(pipe_name)
    request = decode_message(message_wire, codec)
    require(type(expected_server) is WindowsServerBinding, "WINDOWS_EXPECTED_SERVER_BINDING_REQUIRED")
    deadline = _deadline(timeout_seconds)
    require(expected_server._lock.acquire(blocking=False), "WINDOWS_SERVER_BINDING_BUSY")
    api, pipe = expected_server._api, None
    try:
        expected_server._revalidate(deadline)
        while True:
            require(time.monotonic() < deadline, "WINDOWS_PIPE_TIMEOUT")
            # Exact data read/write and mode-change rights, no server-instance,
            # DACL, ownership, inherited handle or caller-selected resource.
            pipe = api.CreateFileW(name, 0x0001 | 0x0002 | 0x0100, 0, None, 3,
                                   0x40000000 | 0x00100000 | 0x00020000, None)
            if pipe not in (None, 0, INVALID_HANDLE):
                break
            error, pipe = C.get_last_error(), None
            if error not in (ERROR_PIPE_BUSY, ERROR_FILE_NOT_FOUND):
                _error("WINDOWS_PIPE_CLIENT_OPEN_FAILED", error)
            time.sleep(min(0.005, max(0.0, deadline - time.monotonic())))
        expected_server._require_pipe(pipe, deadline)
        mode = DWORD(0x00000002)
        if not api.SetNamedPipeHandleState(pipe, C.byref(mode), None, None):
            _error("WINDOWS_PIPE_CLIENT_MESSAGE_MODE_FAILED")
        framed = struct.pack(">I", len(message_wire)) + message_wire
        outgoing = C.create_string_buffer(framed, len(framed))
        count, more = _io(api, "write", pipe, deadline, outgoing, len(framed))
        require(count == len(framed) and not more, "WINDOWS_PIPE_CLIENT_SHORT_WRITE")
        header = C.create_string_buffer(4)
        count, more = _io(api, "read", pipe, deadline, header, 4)
        require(count == 4 and more, "WINDOWS_PIPE_RESPONSE_HEADER_INVALID")
        # Verify the selected actual destination before declared body allocation.
        expected_server._require_pipe(pipe, deadline)
        length = struct.unpack(">I", header.raw)[0]
        require(1 <= length <= MAX_WIRE_BYTES, "WINDOWS_RESPONSE_SIZE_OR_CODEC")
        body = C.create_string_buffer(length)
        count, more = _io(api, "read", pipe, deadline, body, length)
        require(count == length and not more, "WINDOWS_PIPE_RESPONSE_SHORT_OR_TRAILING")
        response = decode_response(body.raw, request, codec)
        expected_server._require_pipe(pipe, deadline)
        require(request.issued_at_ms <= time.time_ns() // 1_000_000 < request.expires_at_ms,
                "IPC_MESSAGE_EXPIRED_OR_FUTURE")
        receipt = hashlib.sha256(body.raw).digest()
        outgoing = C.create_string_buffer(receipt, len(receipt))
        count, more = _io(api, "write", pipe, deadline, outgoing, len(receipt))
        require(count == len(receipt) and not more, "WINDOWS_PIPE_RESPONSE_RECEIPT_SHORT_WRITE")
        expected_server._revalidate(deadline)
        require(time.monotonic() < deadline, "WINDOWS_PIPE_TIMEOUT")
        return response
    finally:
        try:
            api.close_handle(pipe)
        finally:
            expected_server._lock.release()
