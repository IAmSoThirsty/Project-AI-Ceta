"""Explicit no-capabilities AppContainer launch on canonical Windows job custody.

Trusted composition library, not an authority issuer or arbitrary-command IPC
endpoint. It creates no persistent AppContainer profile or host configuration.
The controller must provision/pin the exact assets and scratch ACLs and qualify
their actual access. System/administrator and Windows AppContainer assumptions
remain explicit. No restrictive failure falls back to an unrestricted launch.
Synchronous native occupancy is not preempted by an observation deadline.
"""
import ctypes as C
from ctypes import wintypes as W
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import threading
import time

from ceta.contracts.wire import ContractError
from .windows_jobs import (
    WindowsOwnedProcess, WindowsLaunchError, _API, _require, _failed, _path,
    _environment, _open_image, _hash_image, _file_identity, HANDLE, DWORD,
    SIZE_T, INVALID_HANDLE, KILL_ON_JOB_CLOSE, JOB_LIST, HANDLE_LIST,
    EXTENDED_LIMIT, STARTUPINFOEX, PROCESS_INFORMATION,
    FILE_INFORMATION,
)

SECURITY_CAPABILITIES_ATTRIBUTE = 0x00020009
CHILD_PROCESS_POLICY_ATTRIBUTE = 0x0002000E
CHILD_PROCESS_RESTRICTED = 1
ACTIVE_PROCESS_LIMIT = 8
MAX_TOKEN_BYTES = 65536


class SECURITY_CAPABILITIES(C.Structure):
    _fields_ = [('appcontainer_sid', C.c_void_p), ('capabilities', C.c_void_p),
                ('capability_count', DWORD), ('reserved', DWORD)]


class SID_AND_ATTRIBUTES(C.Structure):
    _fields_ = [('sid', C.c_void_p), ('attributes', DWORD)]


class _KnownFolderId(C.Structure):
    _fields_ = [('data1', DWORD), ('data2', C.c_uint16), ('data3', C.c_uint16),
                ('data4', C.c_ubyte * 8)]


@dataclass(frozen=True, slots=True)
class IsolationTokenFacts:
    appcontainer_sid: str
    is_appcontainer: bool
    capability_count: int
    integrity_rid: int
    restricted: bool
    observed_monotonic_ns: int

    def __post_init__(self):
        _require(type(self.appcontainer_sid) is str and
                 re.fullmatch(r'S-1-15-2(?:-[0-9]{1,10}){1,15}', self.appcontainer_sid),
                 'ISOLATION_APPCONTAINER_SID_REQUIRED')
        _require(type(self.is_appcontainer) is bool and self.is_appcontainer
                 and type(self.capability_count) is int and self.capability_count == 0
                 and type(self.integrity_rid) is int and self.integrity_rid == 4096
                 and type(self.restricted) is bool and self.restricted
                 and type(self.observed_monotonic_ns) is int and self.observed_monotonic_ns >= 0,
                 'ISOLATION_TOKEN_NOT_QUALIFIED')


class _IsolationAPI(_API):
    def __init__(self):
        super().__init__()
        _require(C.sizeof(SECURITY_CAPABILITIES) == 24 and C.sizeof(SID_AND_ATTRIBUTES) == 16,
                 'ISOLATION_X64_LAYOUT_UNSUPPORTED')
        self.security = C.WinDLL('advapi32', use_last_error=True, winmode=0x800)
        self.userenv = C.WinDLL('userenv', use_last_error=True, winmode=0x800)
        self.kernelbase = C.WinDLL('kernelbase', use_last_error=True, winmode=0x800)
        self.shell = C.WinDLL('shell32', use_last_error=True, winmode=0x800)
        self.ole = C.WinDLL('ole32', use_last_error=True, winmode=0x800)
        declarations = {
            'OpenProcessToken': (self.security, [HANDLE, DWORD, C.POINTER(HANDLE)], W.BOOL),
            'GetTokenInformation': (self.security, [HANDLE, C.c_int, C.c_void_p, DWORD, C.POINTER(DWORD)], W.BOOL),
            'IsValidSid': (self.security, [C.c_void_p], W.BOOL),
            'GetLengthSid': (self.security, [C.c_void_p], DWORD),
            'EqualSid': (self.security, [C.c_void_p, C.c_void_p], W.BOOL),
            'IsTokenRestricted': (self.security, [HANDLE], W.BOOL),
            'ConvertSidToStringSidW': (self.security, [C.c_void_p, C.POINTER(C.c_void_p)], W.BOOL),
            'FreeSid': (self.security, [C.c_void_p], C.c_void_p),
            'DeriveAppContainerSidFromAppContainerName': (self.userenv, [W.LPCWSTR, C.POINTER(C.c_void_p)], C.c_int32),
            'LocalFree': (self.dll, [C.c_void_p], C.c_void_p),
            'GetWindowsDirectoryW': (self.dll, [W.LPWSTR, DWORD], DWORD),
            'GetFinalPathNameByHandleW': (self.dll, [HANDLE, W.LPWSTR, DWORD, DWORD], DWORD),
            'CompareObjectHandles': (self.kernelbase, [HANDLE, HANDLE], W.BOOL),
            'SHGetKnownFolderPath': (self.shell, [C.POINTER(_KnownFolderId), DWORD, HANDLE,
                                                C.POINTER(C.c_void_p)], C.c_int32),
            'CoTaskMemFree': (self.ole, [C.c_void_p], None),
        }
        for name, (dll, args, result) in declarations.items():
            function = getattr(dll, name)
            function.argtypes, function.restype = args, result
            setattr(self, name, function)
        self.pending_sids = []
        self._uncertain_sids = set()
        self._pending_handles = []
        self._pending_strings = []
        self._pending_attributes = []
        self._pending_token_outputs = []
        self._pending_known_folders = []
        self._cleanup_lock = threading.RLock()

    def derive(self, name):
        _require(type(name) is str and re.fullmatch(r'CETA\.[A-Za-z0-9.-]{1,100}', name),
                 'ISOLATION_CONTAINER_NAME_INVALID')
        result = C.c_void_p()
        status = self.DeriveAppContainerSidFromAppContainerName(name, C.byref(result))
        _require(status == 0 and result.value, 'ISOLATION_SID_DERIVATION_UNAVAILABLE')
        self.pending_sids.append(result.value)
        _require(self.IsValidSid(result) and 8 <= self.GetLengthSid(result) <= 68,
                 'ISOLATION_DERIVED_SID_INVALID')
        return result.value

    def release_sids(self):
        failures = []
        with self._cleanup_lock:
            for pointer in tuple(self.pending_sids):
                try:
                    _require(pointer not in self._uncertain_sids, 'ISOLATION_SID_RELEASE_UNCERTAIN')
                    self._uncertain_sids.add(pointer)
                    result = self.FreeSid(pointer)
                    _require(result is None or type(result) is int and result == pointer,
                             'ISOLATION_SID_RELEASE_RESPONSE_INVALID')
                    if result is not None: self._uncertain_sids.discard(pointer)
                    _require(result is None, 'ISOLATION_SID_RELEASE_UNRESOLVED')
                    self.pending_sids.remove(pointer)
                    self._uncertain_sids.discard(pointer)
                except BaseException as error: failures.append(error)
        if failures: raise failures[0]

    def queue_handle(self, handle):
        if handle in (None, 0, INVALID_HANDLE): return
        with self._cleanup_lock:
            if not any(row['handle'] == handle for row in self._pending_handles):
                self._pending_handles.append({'handle': handle, 'guard': HANDLE(), 'guard_uncertain': False})

    def _release_handle(self, row):
        """A retained duplicate fences retry against handle-value reuse."""
        handle, guard = row['handle'], row['guard']
        _require(not row['guard_uncertain'], 'ISOLATION_HANDLE_GUARD_RELEASE_UNCERTAIN')
        if handle is not None:
            if not guard.value:
                current = self.GetCurrentProcess()
                row['guard_uncertain'] = True
                duplicated = self.DuplicateHandle(current, handle, current, C.byref(guard), 0, False, 2)
                row['guard_uncertain'] = not bool(duplicated) and bool(guard.value)
                _require(duplicated, 'ISOLATION_CLEANUP_HANDLE_PIN_UNAVAILABLE')
            if not self.CompareObjectHandles(handle, guard.value):
                # The old numeric slot is closed/reused. Never close its new
                # occupant. The retained duplicate still owns the old object.
                row['handle'] = None
            else:
                try:
                    _require(self.close(handle) is None, 'ISOLATION_HANDLE_CLOSE_RESPONSE_INVALID')
                    _require(not self.CompareObjectHandles(handle, guard.value), 'ISOLATION_HANDLE_CLOSE_NOT_OBSERVED')
                except BaseException as primary:
                    # A callback can close then raise. Recheck the object, not
                    # just whether this integer is currently a valid handle.
                    try:
                        if not self.CompareObjectHandles(handle, guard.value): row['handle'] = None
                    except BaseException as secondary:
                        try: primary.cleanup_observation_error = secondary
                        except BaseException: pass
                    raise
                row['handle'] = None
        if guard.value:
            row['guard_uncertain'] = True
            try:
                _require(self.CloseHandle(guard.value), 'ISOLATION_HANDLE_GUARD_CLOSE_UNRESOLVED')
            except BaseException:
                row['guard_uncertain'] = True
                raise
            guard.value = None
            row['guard_uncertain'] = False
        self._pending_handles.remove(row)

    def register_attributes(self, storage):
        with self._cleanup_lock:
            self._pending_attributes.append({'storage': storage, 'state': 'INITIALIZING'})

    def attributes_ready(self, storage):
        with self._cleanup_lock:
            next(row for row in self._pending_attributes if row['storage'] is storage)['state'] = 'PENDING'

    def retry_cleanup(self, *, kinds=('attributes', 'handles', 'strings', 'sids', 'folders')):
        """Try each independent known operation once; uncertain frees stay held."""
        failures = []
        with self._cleanup_lock:
            for row in tuple(self._pending_attributes) if 'attributes' in kinds else ():
                try:
                    _require(row['state'] == 'PENDING', 'ISOLATION_ATTRIBUTES_RELEASE_UNCERTAIN')
                    row['state'] = 'UNCERTAIN'
                    _require(self.DeleteProcThreadAttributeList(row['storage']) is None,
                             'ISOLATION_ATTRIBUTES_RELEASE_RESPONSE_INVALID')
                    self._pending_attributes.remove(row)
                except BaseException as error: failures.append(error)
            for row in tuple(self._pending_handles) if 'handles' in kinds else ():
                try: self._release_handle(row)
                except BaseException as error: failures.append(error)
            for row in tuple(self._pending_strings) if 'strings' in kinds else ():
                try:
                    _require(row['state'] == 'PENDING', 'ISOLATION_SID_TEXT_RELEASE_UNCERTAIN')
                    row['state'] = 'UNCERTAIN'
                    result = self.LocalFree(row['pointer'])
                    _require(result is None or type(result) is int and result == row['pointer'].value,
                             'ISOLATION_SID_TEXT_RELEASE_RESPONSE_INVALID')
                    if result is not None: row['state'] = 'PENDING'
                    _require(result is None, 'ISOLATION_SID_TEXT_RELEASE_UNRESOLVED')
                    self._pending_strings.remove(row)
                except BaseException as error: failures.append(error)
            for row in tuple(self._pending_known_folders) if 'folders' in kinds else ():
                try:
                    _require(row['state'] == 'PENDING', 'ISOLATION_KNOWN_FOLDER_RELEASE_UNCERTAIN')
                    if row['output'].value:
                        row['state'] = 'UNCERTAIN'
                        _require(self.CoTaskMemFree(row['output']) is None,
                                 'ISOLATION_KNOWN_FOLDER_RELEASE_RESPONSE_INVALID')
                    self._pending_known_folders.remove(row)
                except BaseException as error: failures.append(error)
            if 'sids' in kinds:
                try: self.release_sids()
                except BaseException as error: failures.append(error)
            if 'handles' in kinds and self._pending_token_outputs:
                failures.append(ContractError('ISOLATION_TOKEN_ALLOCATION_UNCERTAIN'))
            self.last_cleanup_failures = tuple(failures)
        if failures: raise failures[0]

    def pending_native_resources(self):
        with self._cleanup_lock:
            return tuple(
                [{'kind': 'handle', 'handle': row['handle'], 'guard_handle': row['guard'].value,
                  'retry': 'UNCERTAIN' if row['guard_uncertain'] else 'PENDING'} for row in self._pending_handles] +
                [{'kind': 'sid', 'address': pointer,
                  'retry': 'UNCERTAIN' if pointer in self._uncertain_sids else 'PENDING'} for pointer in self.pending_sids] +
                [{'kind': 'sid_text', 'address': row['pointer'].value, 'retry': row['state']} for row in self._pending_strings] +
                [{'kind': 'attributes', 'address': C.addressof(row['storage']), 'retry': row['state']}
                 for row in self._pending_attributes] +
                [{'kind': 'token_output', 'handle': token.value, 'retry': 'UNCERTAIN'} for token in self._pending_token_outputs] +
                [{'kind': 'known_folder_path', 'address': row['output'].value, 'retry': row['state']}
                 for row in self._pending_known_folders])

    def token_data(self, token, information_class):
        size = DWORD()
        C.set_last_error(0)
        ok = self.GetTokenInformation(token, information_class, None, 0, C.byref(size))
        _require(not ok and C.get_last_error() == 122 and 0 < size.value <= MAX_TOKEN_BYTES,
                 'ISOLATION_TOKEN_QUERY_SIZE_UNAVAILABLE')
        storage = C.create_string_buffer(size.value)
        returned = DWORD(size.value)
        _require(self.GetTokenInformation(token, information_class, storage, size.value, C.byref(returned))
                 and returned.value == size.value, 'ISOLATION_TOKEN_QUERY_UNAVAILABLE')
        return storage

    def sid_text(self, pointer):
        _require(pointer and self.IsValidSid(pointer) and 8 <= self.GetLengthSid(pointer) <= 68,
                 'ISOLATION_TOKEN_SID_INVALID')
        result = C.c_void_p()
        row = {'pointer': result, 'state': 'ALLOCATING'}
        self._pending_strings.append(row)
        primary = None
        try:
            if not self.ConvertSidToStringSidW(pointer, C.byref(result)):
                if not result.value: self._pending_strings.remove(row)
                _failed('ISOLATION_SID_TEXT_UNAVAILABLE')
            row['state'] = 'PENDING'
            return C.wstring_at(result)
        except BaseException as error:
            primary = error
            if not result.value and row in self._pending_strings: self._pending_strings.remove(row)
            raise
        finally:
            _finish_cleanup(self, primary, kinds=('strings',))

    def token_facts(self, process, expected_sid):
        token = HANDLE()
        self._pending_token_outputs.append(token)
        primary, known = None, False
        try:
            if not self.OpenProcessToken(process, 8, C.byref(token)):
                _failed('ISOLATION_PROCESS_TOKEN_UNAVAILABLE')
            known = True
            self._pending_token_outputs.remove(token)
            app = self.token_data(token, 29)
            _require(len(app) == 4, 'ISOLATION_APPCONTAINER_QUERY_SIZE_INVALID')
            is_app = DWORD.from_buffer(app).value
            sid = self.token_data(token, 31)
            _require(len(sid) >= C.sizeof(C.c_void_p), 'ISOLATION_APPCONTAINER_QUERY_SIZE_INVALID')
            actual_sid = C.c_void_p.from_buffer(sid).value
            _require(actual_sid and self.EqualSid(actual_sid, expected_sid), 'ISOLATION_APPCONTAINER_SID_MISMATCH')
            capabilities = self.token_data(token, 30)
            _require(len(capabilities) >= 4, 'ISOLATION_CAPABILITY_QUERY_SIZE_INVALID')
            count = DWORD.from_buffer(capabilities).value
            integrity = self.token_data(token, 25)
            _require(len(integrity) >= C.sizeof(SID_AND_ATTRIBUTES), 'ISOLATION_INTEGRITY_QUERY_SIZE_INVALID')
            pointer = SID_AND_ATTRIBUTES.from_buffer(integrity).sid
            integrity_text = self.sid_text(pointer)
            _require(re.fullmatch(r'S-1-16-[0-9]{1,10}', integrity_text), 'ISOLATION_INTEGRITY_SID_INVALID')
            facts = IsolationTokenFacts(self.sid_text(actual_sid), is_app == 1, count,
                int(integrity_text.rsplit('-', 1)[1]), bool(self.IsTokenRestricted(token)), time.monotonic_ns())
            return facts
        except BaseException as error:
            primary = error
            if not token.value and token in self._pending_token_outputs: self._pending_token_outputs.remove(token)
            raise
        finally:
            if known: self.queue_handle(token.value)
            _finish_cleanup(self, primary, kinds=('handles',))

    def environment(self, scratch):
        buffer = C.create_unicode_buffer(32768)
        count = self.GetWindowsDirectoryW(buffer, len(buffer))
        _require(0 < count < len(buffer), 'ISOLATION_SYSTEM_DIRECTORY_UNAVAILABLE')
        windows = _path(buffer.value, directory=True)
        return {'SystemRoot': windows, 'WINDIR': windows,
                'PATH': str(Path(windows) / 'System32'), 'TEMP': scratch, 'TMP': scratch,
                'LOCALAPPDATA': self._local_appdata()}

    def _local_appdata(self):
        """Read one current-user known folder without creating or initializing it."""
        folder = _KnownFolderId(0xF1B32785, 0x6FBA, 0x4FCF,
            (C.c_ubyte * 8)(0x9D, 0x55, 0x7B, 0x8E, 0x7F, 0x15, 0x70, 0x91))
        _require(C.sizeof(folder) == 16, 'ISOLATION_KNOWN_FOLDER_LAYOUT_UNSUPPORTED')
        row = {'output': C.c_void_p(), 'state': 'QUERYING'}
        primary = None
        with self._cleanup_lock:
            self._pending_known_folders.append(row)
            try:
                status = self.SHGetKnownFolderPath(C.byref(folder), 0x4000, None,
                                                   C.byref(row['output']))
                # Even a failing HRESULT can return an allocation to be freed.
                row['state'] = 'PENDING'
                _require(type(status) is int, 'ISOLATION_LOCALAPPDATA_RESPONSE_INVALID')
                _require(status == 0 and row['output'].value,
                         'ISOLATION_LOCALAPPDATA_UNAVAILABLE')
                value = C.wstring_at(row['output'])
                _require(0 < len(value) < 32767, 'ISOLATION_LOCALAPPDATA_PATH_BOUND')
                return _path(value, directory=True)
            except BaseException as error:
                primary = error
                if row['state'] == 'QUERYING': row['state'] = 'UNCERTAIN'
                raise
            finally:
                _finish_cleanup(self, primary, kinds=('folders',))

    def native_volume_path(self, handle):
        buffer = C.create_unicode_buffer(32768)
        size = self.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 1)
        _require(0 < size < len(buffer) and re.match(r'^\\\\\?\\Volume\{[0-9a-fA-F-]{36}\}\\', buffer.value),
                 'ISOLATION_VOLUME_PATH_UNAVAILABLE')
        return buffer.value


class IsolatedLaunchError(WindowsLaunchError):
    """Keep exact canonical process custody plus residual SID allocation cleanup."""
    def __init__(self, code, owned_process, isolation_api, **kwargs):
        super().__init__(code, owned_process, **kwargs)
        self.isolation_api = isolation_api

    def close_cleanup(self):
        primary = None
        if self.owned_process is not None:
            try: self.owned_process.close()
            except BaseException as error: primary = error
        try:
            self.isolation_api.retry_cleanup()
        except BaseException as error:
            if primary is None: primary = error
        self._cleanup_handles = [row['handle'] for row in self.isolation_api._pending_handles
                                 if row['handle'] is not None]
        if primary is not None:
            _attach_cleanup(primary, self)
            raise primary

    @property
    def pending_native_resources(self):
        return self.isolation_api.pending_native_resources()


def _attach_cleanup(primary, cleanup):
    # Diagnostics must never replace the original control/error object.
    for name, value in (('isolation_cleanup', cleanup), ('owned_process', cleanup.owned_process)):
        try: setattr(primary, name, value)
        except BaseException: pass
    try: primary.add_note('Exact isolated native cleanup remains retained; explicit recovery is required.')
    except BaseException: pass


def _finish_cleanup(api, primary, owned=None, *, kinds=('attributes', 'handles', 'strings', 'sids', 'folders')):
    try:
        api.retry_cleanup(kinds=kinds)
    except BaseException as secondary:
        cleanup = IsolatedLaunchError('ISOLATION_FINALIZATION_UNRESOLVED', owned, api,
            cleanup_api=api, cleanup_handles=[row['handle'] for row in api._pending_handles
                                             if row['handle'] is not None])
        if primary is not None:
            _attach_cleanup(primary, cleanup)
        elif isinstance(secondary, (KeyboardInterrupt, SystemExit)):
            _attach_cleanup(secondary, cleanup)
            raise
        else:
            raise cleanup from secondary


def appcontainer_sid(name):
    """Derive a profile SID without installing a profile or changing host state."""
    api = _IsolationAPI()
    primary = None
    try:
        return api.sid_text(api.derive(name))
    except BaseException as error:
        primary = error
        raise
    finally:
        _finish_cleanup(api, primary)


class IsolatedWindowsWorker(WindowsOwnedProcess):
    """Use the canonical job/process owner with explicitly restricted creation."""
    @classmethod
    def launch(cls, executable, arguments, *, cwd, scratch_root, expected_image_sha256,
               appcontainer_name, inherited_handles=(), standard_handles=None):
        executable, cwd = _path(executable, directory=False), _path(cwd, directory=True)
        scratch = _path(scratch_root, directory=True)
        _require(type(expected_image_sha256) is str and re.fullmatch(r'[0-9a-f]{64}', expected_image_sha256),
                 'ISOLATION_IMAGE_PIN_REQUIRED')
        _require(type(arguments) is tuple and len(arguments) <= 32 and
                 all(type(arg) is str and '\x00' not in arg and len(arg) <= 4096 for arg in arguments),
                 'ISOLATION_ARGUMENTS_INVALID')
        _require(type(inherited_handles) is tuple and len(inherited_handles) <= 8,
                 'ISOLATION_HANDLE_LIST_INVALID')
        _require(standard_handles is None or type(standard_handles) is tuple and len(standard_handles) == 3,
                 'ISOLATION_STANDARD_HANDLES_INVALID')
        candidates = inherited_handles + (standard_handles or ())
        _require(all(type(h) is int and 0 < h < INVALID_HANDLE for h in candidates),
                 'ISOLATION_HANDLE_LIST_INVALID')
        selected = tuple(dict.fromkeys(candidates))
        _require(len(selected) <= 8, 'ISOLATION_HANDLE_LIST_INVALID')
        command = subprocess.list2cmdline((executable, *arguments))
        _require(len(command) < 32767, 'ISOLATION_COMMAND_TOO_LARGE')
        api = _IsolationAPI()
        image = actual_image = directory = job = attributes = None
        owned = None
        primary = None
        try:
            sid = api.derive(appcontainer_name)
            environment = api.environment(scratch)
            environment_buffer = _environment(environment)
            for handle in selected:
                flags = DWORD()
                _require(api.GetHandleInformation(handle, C.byref(flags)) and flags.value & 1,
                         'ISOLATION_CHILD_HANDLE_NOT_INHERITABLE')
            image = _open_image(api, executable)
            digest, identity = _hash_image(api, image)
            _require(digest == expected_image_sha256, 'ISOLATION_IMAGE_PIN_MISMATCH')
            native_executable = api.native_volume_path(image)
            directory = api.CreateFileW(cwd, 0x80, 3, None, 3, 0x02000000 | 0x00200000, None)
            if directory in (None, 0, INVALID_HANDLE): _failed('ISOLATION_DIRECTORY_PIN_UNAVAILABLE')
            directory_info = FILE_INFORMATION()
            _require(api.GetFileInformationByHandle(directory, C.byref(directory_info))
                     and directory_info.attributes & 0x10 and not directory_info.attributes & 0x400,
                     'ISOLATION_DIRECTORY_PIN_INVALID')
            native_directory = api.native_volume_path(directory)
            job = api.CreateJobObjectW(None, None)
            if not job: _failed('ISOLATION_JOB_CREATE_FAILED')
            if not api.SetHandleInformation(job, 1, 0): _failed('ISOLATION_JOB_INHERITANCE_FAILED')
            limit = EXTENDED_LIMIT()
            limit.basic.flags, limit.basic.active_limit = KILL_ON_JOB_CLOSE | ACTIVE_PROCESS_LIMIT, 1
            if not api.SetInformationJobObject(job, 9, C.byref(limit), C.sizeof(limit)):
                _failed('ISOLATION_JOB_LIMIT_FAILED')
            size = SIZE_T()
            count = 3 + bool(selected)
            C.set_last_error(0)
            initial = api.InitializeProcThreadAttributeList(None, count, 0, C.byref(size))
            _require(not initial and C.get_last_error() == 122 and 0 < size.value <= 65536,
                     'ISOLATION_ATTRIBUTES_SIZE_UNAVAILABLE')
            storage = C.create_string_buffer(size.value)
            api.register_attributes(storage)
            if not api.InitializeProcThreadAttributeList(storage, count, 0, C.byref(size)):
                _failed('ISOLATION_ATTRIBUTES_CREATE_FAILED')
            api.attributes_ready(storage)
            attributes = storage
            jobs = (HANDLE * 1)(job)
            capabilities = SECURITY_CAPABILITIES(sid, None, 0, 0)
            child_policy = DWORD(CHILD_PROCESS_RESTRICTED)
            for name, value in ((JOB_LIST, jobs), (SECURITY_CAPABILITIES_ATTRIBUTE, capabilities),
                                (CHILD_PROCESS_POLICY_ATTRIBUTE, child_policy)):
                if not api.UpdateProcThreadAttribute(storage, 0, name, C.byref(value), C.sizeof(value), None, None):
                    _failed('ISOLATION_ATTRIBUTE_UNAVAILABLE')
            if selected:
                handles = (HANDLE * len(selected))(*selected)
                if not api.UpdateProcThreadAttribute(storage, 0, HANDLE_LIST, handles, C.sizeof(handles), None, None):
                    _failed('ISOLATION_HANDLE_LIST_UNAVAILABLE')
            startup = STARTUPINFOEX()
            startup.startup.cb, startup.attributes = C.sizeof(startup), C.cast(storage, C.c_void_p)
            if standard_handles is not None:
                startup.startup.flags = 0x100
                startup.startup.stdin, startup.startup.stdout, startup.startup.stderr = standard_handles
            information = PROCESS_INFORMATION()
            flags = 0x4 | 0x400 | 0x80000 | 0x08000000
            native_command = subprocess.list2cmdline((native_executable, *arguments))
            _require(len(native_command) < 32767, 'ISOLATION_COMMAND_TOO_LARGE')
            buffer = C.create_unicode_buffer(native_command)
            if not api.CreateProcessW(native_executable, buffer, None, None, bool(selected), flags,
                                      environment_buffer, native_directory, C.byref(startup), C.byref(information)):
                _failed('ISOLATION_RESTRICTED_CREATE_FAILED')
            owned = cls(api, job, information, digest); job = None
            _require(api.GetProcessId(owned._process) == owned.pid, 'ISOLATION_PROCESS_ID_MISMATCH')
            times = [W.FILETIME() for _ in range(4)]
            if not api.GetProcessTimes(owned._process, *(C.byref(item) for item in times)):
                _failed('ISOLATION_CREATION_TIME_UNAVAILABLE')
            owned._creation_time = times[0].dwHighDateTime << 32 | times[0].dwLowDateTime
            _require(owned.creation_time > 0, 'ISOLATION_CREATION_TIME_UNAVAILABLE')
            member = W.BOOL()
            _require(api.IsProcessInJob(owned._process, owned._job, C.byref(member)) and member.value,
                     'ISOLATION_ATOMIC_JOB_MEMBERSHIP_UNAVAILABLE')
            owned.launch_token_facts = api.token_facts(owned._process, sid)
            owned.launch_environment = tuple(sorted(environment.items()))
            owned.appcontainer_name = appcontainer_name
            image_name, capacity = C.create_unicode_buffer(32768), DWORD(32768)
            if not api.QueryFullProcessImageNameW(owned._process, 0, image_name, C.byref(capacity)):
                _failed('ISOLATION_IMAGE_QUERY_UNAVAILABLE')
            actual_image = _open_image(api, image_name.value)
            _require(_file_identity(api, actual_image) == identity, 'ISOLATION_IMAGE_REPLACED')
            _require(api.ResumeThread(owned._thread) == 1, 'ISOLATION_PROCESS_RESUME_FAILED')
            api.close(owned._thread); owned._thread = None
            return owned
        except BaseException as error:
            primary = error
            if owned is not None:
                try:
                    owned.terminate(125)
                    _require(owned.wait(5), 'ISOLATION_LAUNCH_CLEANUP_UNRESOLVED')
                    owned.close()
                except BaseException as secondary:
                    cleanup = IsolatedLaunchError('ISOLATION_LAUNCH_CLEANUP_UNRESOLVED', owned, api)
                    if isinstance(primary, (KeyboardInterrupt, SystemExit)):
                        _attach_cleanup(primary, cleanup)
                        raise primary
                    raise cleanup from primary
            raise
        finally:
            for handle in (actual_image, image, directory, job):
                api.queue_handle(handle)
            _finish_cleanup(api, primary, owned)
