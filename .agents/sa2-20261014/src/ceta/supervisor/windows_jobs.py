"""Owned Windows x64 processes with atomic job membership, development only.

Trusted composition infrastructure, never an arbitrary-command IPC endpoint.
Job ownership is lifecycle containment, not filesystem/network/token isolation.
Executable/path inspection, CreateProcess and other startup native calls are
synchronous: this module does not claim to bound their whole native occupancy.
OS/kernel/driver behavior remains an assumption. A termination request is not
an observed exit, and an unobserved lifetime must retain its owning object.
There is no destructor that silently closes/kills live work.
"""
import ctypes as C
from ctypes import wintypes as W
import hashlib
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import threading

from ceta.contracts.wire import ContractError

DWORD = C.c_uint32
SIZE_T = C.c_size_t
HANDLE = C.c_void_p
WAIT_OBJECT_0, WAIT_TIMEOUT = 0, 258
KILL_ON_JOB_CLOSE = 0x2000
JOB_LIST, HANDLE_LIST = 0x2000D, 0x20002
INVALID_HANDLE = C.c_void_p(-1).value


class STARTUPINFO(C.Structure):
    _fields_ = [("cb", DWORD), ("reserved", W.LPWSTR), ("desktop", W.LPWSTR),
                ("title", W.LPWSTR), ("x", DWORD), ("y", DWORD),
                ("x_size", DWORD), ("y_size", DWORD), ("x_chars", DWORD),
                ("y_chars", DWORD), ("fill", DWORD), ("flags", DWORD),
                ("show", C.c_uint16), ("reserved_size", C.c_uint16),
                ("reserved_bytes", C.c_void_p), ("stdin", HANDLE),
                ("stdout", HANDLE), ("stderr", HANDLE)]


class STARTUPINFOEX(C.Structure):
    _fields_ = [("startup", STARTUPINFO), ("attributes", C.c_void_p)]


class PROCESS_INFORMATION(C.Structure):
    _fields_ = [("process", HANDLE), ("thread", HANDLE), ("pid", DWORD), ("tid", DWORD)]


class BASIC_LIMIT(C.Structure):
    _fields_ = [("process_time", C.c_int64), ("job_time", C.c_int64),
                ("flags", DWORD), ("minimum_ws", SIZE_T), ("maximum_ws", SIZE_T),
                ("active_limit", DWORD), ("affinity", SIZE_T),
                ("priority", DWORD), ("scheduling", DWORD)]


class IO_COUNTERS(C.Structure):
    _fields_ = [(name, C.c_uint64) for name in
                ("read_operations", "write_operations", "other_operations", "read_bytes", "write_bytes", "other_bytes")]


class EXTENDED_LIMIT(C.Structure):
    _fields_ = [("basic", BASIC_LIMIT), ("io", IO_COUNTERS),
                ("process_memory", SIZE_T), ("job_memory", SIZE_T),
                ("peak_process_memory", SIZE_T), ("peak_job_memory", SIZE_T)]


class ACCOUNTING(C.Structure):
    _fields_ = [("total_user", C.c_int64), ("total_kernel", C.c_int64),
                ("period_user", C.c_int64), ("period_kernel", C.c_int64),
                ("page_faults", DWORD), ("total_processes", DWORD),
                ("active_processes", DWORD), ("terminated_processes", DWORD)]


class FILE_INFORMATION(C.Structure):
    _fields_ = [("attributes", DWORD), ("created", W.FILETIME),
                ("accessed", W.FILETIME), ("written", W.FILETIME),
                ("volume", DWORD), ("size_high", DWORD), ("size_low", DWORD),
                ("links", DWORD), ("index_high", DWORD), ("index_low", DWORD)]


def _require(condition, code):
    if not condition:
        raise ContractError(code)


def _failed(code):
    raise ContractError(code + ":" + str(C.get_last_error()))


class WindowsLaunchError(ContractError):
    """Failure retaining unresolved native ownership for the caller to manage."""
    def __init__(self, code, owned_process, *, cleanup_api=None, cleanup_handles=()):
        super().__init__(code)
        self.owned_process = owned_process
        self._cleanup_api, self._cleanup_handles = cleanup_api, list(cleanup_handles)

    def close_cleanup(self):
        """Explicit retry; a retained live owner still rejects close."""
        if self.owned_process is not None:
            self.owned_process.close()
            return
        while self._cleanup_handles:
            self._cleanup_api.close(self._cleanup_handles[0])
            del self._cleanup_handles[0]


class _API:
    def __init__(self):
        _require(os.name == "nt" and struct.calcsize("P") == 8, "WINDOWS_JOBS_X64_REQUIRED")
        _require((C.sizeof(STARTUPINFOEX), C.sizeof(PROCESS_INFORMATION), C.sizeof(EXTENDED_LIMIT), C.sizeof(ACCOUNTING))
                 == (112, 24, 144, 48), "WINDOWS_JOBS_LAYOUT_UNSUPPORTED")
        # Installed Windows system directory only, never PATH/current-directory DLLs.
        self.dll = C.WinDLL("kernel32", use_last_error=True, winmode=0x800)
        declarations = {
            "CreateJobObjectW": ([C.c_void_p, W.LPCWSTR], HANDLE),
            "SetInformationJobObject": ([HANDLE, C.c_int, C.c_void_p, DWORD], W.BOOL),
            "QueryInformationJobObject": ([HANDLE, C.c_int, C.c_void_p, DWORD, C.POINTER(DWORD)], W.BOOL),
            "GetHandleInformation": ([HANDLE, C.POINTER(DWORD)], W.BOOL),
            "SetHandleInformation": ([HANDLE, DWORD, DWORD], W.BOOL),
            "InitializeProcThreadAttributeList": ([C.c_void_p, DWORD, DWORD, C.POINTER(SIZE_T)], W.BOOL),
            "UpdateProcThreadAttribute": ([C.c_void_p, DWORD, SIZE_T, C.c_void_p, SIZE_T, C.c_void_p, C.c_void_p], W.BOOL),
            "DeleteProcThreadAttributeList": ([C.c_void_p], None),
            "CreateProcessW": ([W.LPCWSTR, W.LPWSTR, C.c_void_p, C.c_void_p, W.BOOL, DWORD,
                                C.c_void_p, W.LPCWSTR, C.POINTER(STARTUPINFOEX), C.POINTER(PROCESS_INFORMATION)], W.BOOL),
            "ResumeThread": ([HANDLE], DWORD),
            "GetProcessTimes": ([HANDLE, C.POINTER(W.FILETIME), C.POINTER(W.FILETIME), C.POINTER(W.FILETIME), C.POINTER(W.FILETIME)], W.BOOL),
            "GetProcessId": ([HANDLE], DWORD),
            "IsProcessInJob": ([HANDLE, HANDLE, C.POINTER(W.BOOL)], W.BOOL),
            "QueryFullProcessImageNameW": ([HANDLE, DWORD, W.LPWSTR, C.POINTER(DWORD)], W.BOOL),
            "WaitForSingleObject": ([HANDLE, DWORD], DWORD),
            "GetExitCodeProcess": ([HANDLE, C.POINTER(DWORD)], W.BOOL),
            "TerminateJobObject": ([HANDLE, DWORD], W.BOOL),
            "GetCurrentProcess": ([], HANDLE),
            "DuplicateHandle": ([HANDLE, HANDLE, HANDLE, C.POINTER(HANDLE), DWORD, W.BOOL, DWORD], W.BOOL),
            "CreateFileW": ([W.LPCWSTR, DWORD, DWORD, C.c_void_p, DWORD, DWORD, HANDLE], HANDLE),
            "GetFileInformationByHandle": ([HANDLE, C.POINTER(FILE_INFORMATION)], W.BOOL),
            "ReadFile": ([HANDLE, C.c_void_p, DWORD, C.POINTER(DWORD), C.c_void_p], W.BOOL),
            "CloseHandle": ([HANDLE], W.BOOL),
        }
        for name, (arguments, result) in declarations.items():
            function = getattr(self.dll, name)
            function.argtypes, function.restype = arguments, result
            setattr(self, name, function)

    def close(self, handle):
        if handle not in (None, 0, INVALID_HANDLE) and not self.CloseHandle(handle):
            _failed("WINDOWS_HANDLE_CLOSE_FAILED")


def _path(value, *, directory):
    _require(type(value) is str and value and "\x00" not in value and len(value) < 32767,
             "WINDOWS_LAUNCH_PATH_REQUIRED")
    path = Path(value)
    _require(path.is_absolute() and not value.startswith(("\\\\", "//")), "WINDOWS_LAUNCH_LOCAL_PATH_REQUIRED")
    _require(all(":" not in part for part in path.parts[1:]), "WINDOWS_LAUNCH_STREAM_REJECTED")
    _require(path.is_dir() if directory else path.is_file(), "WINDOWS_LAUNCH_PATH_UNAVAILABLE")
    for item in (path, *path.parents):
        _require(not item.is_symlink() and not item.is_junction(), "WINDOWS_LAUNCH_PATH_LINK_REJECTED")
    return str(path.resolve(strict=True))


def _environment(values):
    _require(type(values) is dict and len(values) <= 1024, "WINDOWS_LAUNCH_ENVIRONMENT_REQUIRED")
    seen, entries = set(), []
    for key, value in values.items():
        _require(type(key) is str and key and "=" not in key and "\x00" not in key
                 and type(value) is str and "\x00" not in value, "WINDOWS_LAUNCH_ENVIRONMENT_INVALID")
        _require(key.upper() not in seen, "WINDOWS_LAUNCH_ENVIRONMENT_DUPLICATE")
        seen.add(key.upper())
        entries.append((key, value))
    text = "\x00".join(key + "=" + value for key, value in sorted(entries, key=lambda entry: entry[0].upper())) + "\x00\x00"
    _require(len(text) <= 32767, "WINDOWS_LAUNCH_ENVIRONMENT_TOO_LARGE")
    return C.create_unicode_buffer(text)


def _timeout(seconds):
    _require(type(seconds) in (int, float) and 0 <= seconds <= 86400 and math.isfinite(seconds),
             "WINDOWS_PROCESS_TIMEOUT_REQUIRED")
    return math.ceil(seconds * 1000)


def _file_identity(api, handle):
    information = FILE_INFORMATION()
    if not api.GetFileInformationByHandle(handle, C.byref(information)):
        _failed("WINDOWS_LAUNCH_FILE_IDENTITY_UNAVAILABLE")
    _require(not information.attributes & (0x10 | 0x400), "WINDOWS_LAUNCH_REGULAR_IMAGE_REQUIRED")
    return (information.volume, information.index_high, information.index_low,
            information.size_high, information.size_low, information.written.dwHighDateTime, information.written.dwLowDateTime)


def _open_image(api, path):
    # Pin against ordinary write/delete replacement for the launch interval.
    handle = api.CreateFileW(path, 0x80000000, 1, None, 3, 0x80, None)
    if handle in (None, 0, INVALID_HANDLE):
        _failed("WINDOWS_LAUNCH_IMAGE_OPEN_FAILED")
    return handle


def _hash_image(api, handle):
    before = _file_identity(api, handle)
    digest, count = hashlib.sha256(), 0
    buffer = C.create_string_buffer(1024 * 1024)
    while True:
        transferred = DWORD()
        if not api.ReadFile(handle, buffer, len(buffer), C.byref(transferred), None):
            _failed("WINDOWS_LAUNCH_IMAGE_READ_FAILED")
        if transferred.value == 0:
            break
        count += transferred.value
        digest.update(buffer.raw[:transferred.value])
    _require(before == _file_identity(api, handle) and count == (before[3] << 32 | before[4]),
             "WINDOWS_LAUNCH_IMAGE_CHANGED")
    return digest.hexdigest(), before


class WindowsOwnedProcess:
    """Retain one primary lifetime and its job. poll/wait observe the primary.

    Descendants are owned through the same job; close additionally requires an
    empty job. wait duplicates the process handle so terminate is not blocked
    behind a wait lock and close cannot invalidate a concurrent native wait.
    """
    def __init__(self, api, job, information, image_sha256):
        self._api, self._job, self._process = api, job, information.process
        self._thread = information.thread
        self._pid, self._image_sha256 = information.pid, image_sha256
        self._creation_time = None
        self._closed, self._termination_requested = False, False
        self._exit_code, self._cleanup_handles = None, []
        self._lock = threading.RLock()

    @classmethod
    def launch(cls, executable, arguments, *, cwd, environment, inherited_handles=(), standard_handles=None,
               expected_image_sha256=None):
        executable, cwd = _path(executable, directory=False), _path(cwd, directory=True)
        _require(type(arguments) is tuple and len(arguments) <= 256
                 and all(type(arg) is str and "\x00" not in arg and len(arg) < 32767 for arg in arguments),
                 "WINDOWS_LAUNCH_ARGUMENTS_REQUIRED")
        command = subprocess.list2cmdline((executable, *arguments))
        _require(len(command) < 32767, "WINDOWS_LAUNCH_COMMAND_TOO_LARGE")
        environment_buffer = _environment(environment)
        _require(expected_image_sha256 is None or (type(expected_image_sha256) is str
                 and re.fullmatch(r"[0-9a-f]{64}", expected_image_sha256)), "WINDOWS_LAUNCH_IMAGE_HASH_REQUIRED")
        _require(type(inherited_handles) is tuple and len(inherited_handles) <= 64, "WINDOWS_LAUNCH_HANDLE_LIST_REQUIRED")
        _require(standard_handles is None or (type(standard_handles) is tuple and len(standard_handles) == 3),
                 "WINDOWS_LAUNCH_STANDARD_HANDLES_REQUIRED")
        candidates = inherited_handles + (standard_handles or ())
        _require(all(type(h) is int and 0 < h < INVALID_HANDLE for h in candidates),
                 "WINDOWS_LAUNCH_HANDLE_INVALID")
        selected = tuple(dict.fromkeys(candidates))
        _require(len(selected) <= 64, "WINDOWS_LAUNCH_HANDLE_LIST_REQUIRED")
        api = _API()
        for handle in selected:
            flags = DWORD()
            _require(api.GetHandleInformation(handle, C.byref(flags)) and flags.value & 1,
                     "WINDOWS_LAUNCH_CHILD_HANDLE_NOT_INHERITABLE")
        image, actual_image, job, attributes = None, None, None, None
        owned = None
        try:
            image = _open_image(api, executable)
            digest, identity = _hash_image(api, image)
            _require(expected_image_sha256 is None or digest == expected_image_sha256, "WINDOWS_LAUNCH_IMAGE_HASH_MISMATCH")
            job = api.CreateJobObjectW(None, None)
            if not job:
                _failed("WINDOWS_JOB_CREATE_FAILED")
            if not api.SetHandleInformation(job, 1, 0):
                _failed("WINDOWS_JOB_INHERITANCE_FAILED")
            limit = EXTENDED_LIMIT()
            limit.basic.flags = KILL_ON_JOB_CLOSE
            if not api.SetInformationJobObject(job, 9, C.byref(limit), C.sizeof(limit)):
                _failed("WINDOWS_JOB_LIMIT_FAILED")
            size = SIZE_T()
            count = 1 + bool(selected)
            C.set_last_error(0)
            initial = api.InitializeProcThreadAttributeList(None, count, 0, C.byref(size))
            _require(not initial and C.get_last_error() == 122 and 0 < size.value <= 65536,
                     "WINDOWS_ATTRIBUTES_SIZE_UNAVAILABLE")
            storage = C.create_string_buffer(size.value)
            if not api.InitializeProcThreadAttributeList(storage, count, 0, C.byref(size)):
                _failed("WINDOWS_ATTRIBUTES_CREATE_FAILED")
            attributes = storage
            jobs = (HANDLE * 1)(job)
            if not api.UpdateProcThreadAttribute(storage, 0, JOB_LIST, jobs, C.sizeof(jobs), None, None):
                _failed("WINDOWS_ATOMIC_JOB_MEMBERSHIP_UNAVAILABLE")
            if selected:
                handles = (HANDLE * len(selected))(*selected)
                if not api.UpdateProcThreadAttribute(storage, 0, HANDLE_LIST, handles, C.sizeof(handles), None, None):
                    _failed("WINDOWS_HANDLE_LIST_UNAVAILABLE")
            startup = STARTUPINFOEX()
            startup.startup.cb, startup.attributes = C.sizeof(startup), C.cast(storage, C.c_void_p)
            if standard_handles is not None:
                startup.startup.flags = 0x100  # STARTF_USESTDHANDLES
                startup.startup.stdin, startup.startup.stdout, startup.startup.stderr = standard_handles
            information = PROCESS_INFORMATION()
            flags = 0x4 | 0x400 | 0x80000 | 0x08000000  # suspended/unicode/extended/no window, no breakaway
            command_buffer = C.create_unicode_buffer(command)
            if not api.CreateProcessW(executable, command_buffer, None, None, bool(selected), flags,
                                      environment_buffer, cwd, C.byref(startup), C.byref(information)):
                _failed("WINDOWS_PROCESS_CREATE_FAILED")
            owned = cls(api, job, information, digest)
            job = None  # ownership transferred before any further fallible observation
            _require(api.GetProcessId(owned._process) == owned.pid, "WINDOWS_PROCESS_IDENTITY_MISMATCH")
            created, exited, kernel, user = (W.FILETIME() for _ in range(4))
            if not api.GetProcessTimes(owned._process, C.byref(created), C.byref(exited), C.byref(kernel), C.byref(user)):
                _failed("WINDOWS_PROCESS_CREATION_UNAVAILABLE")
            owned._creation_time = created.dwHighDateTime << 32 | created.dwLowDateTime
            _require(owned.creation_time > 0, "WINDOWS_PROCESS_CREATION_UNAVAILABLE")
            member = W.BOOL()
            _require(api.IsProcessInJob(owned._process, owned._job, C.byref(member)) and member.value,
                     "WINDOWS_ATOMIC_JOB_MEMBERSHIP_UNAVAILABLE")
            job_flags = DWORD()
            _require(api.GetHandleInformation(owned._job, C.byref(job_flags)) and not job_flags.value & 1,
                     "WINDOWS_JOB_INHERITED")
            name, capacity = C.create_unicode_buffer(32768), DWORD(32768)
            if not api.QueryFullProcessImageNameW(owned._process, 0, name, C.byref(capacity)):
                _failed("WINDOWS_PROCESS_IMAGE_UNAVAILABLE")
            _require(os.path.normcase(name.value) == os.path.normcase(executable), "WINDOWS_PROCESS_IMAGE_MISMATCH")
            actual_image = _open_image(api, name.value)
            _require(_file_identity(api, actual_image) == identity, "WINDOWS_PROCESS_IMAGE_REPLACED")
            resumed = api.ResumeThread(owned._thread)
            _require(resumed == 1, "WINDOWS_PROCESS_RESUME_FAILED")
            api.close(owned._thread)
            owned._thread = None
            return owned
        except BaseException as failure:
            if owned is not None:
                try:
                    owned.terminate(125)
                    _require(owned.wait(5), "WINDOWS_LAUNCH_CLEANUP_UNRESOLVED")
                    owned.close()
                except BaseException:
                    raise WindowsLaunchError("WINDOWS_LAUNCH_CLEANUP_UNRESOLVED", owned) from failure
            raise
        finally:
            if attributes is not None:
                api.DeleteProcThreadAttributeList(attributes)
            failed_handles, cleanup_failure = [], None
            for handle in (actual_image, image, job):
                try:
                    api.close(handle)
                except BaseException as failure:
                    failed_handles.append(handle)
                    cleanup_failure = failure
            if failed_handles:
                if owned is not None:
                    owned._cleanup_handles.extend(failed_handles)
                raise WindowsLaunchError("WINDOWS_LAUNCH_FINALIZATION_UNRESOLVED", owned,
                    cleanup_api=api, cleanup_handles=failed_handles) from cleanup_failure

    @property
    def pid(self):
        return self._pid

    @property
    def creation_time(self):
        return self._creation_time

    @property
    def image_sha256(self):
        return self._image_sha256

    @property
    def termination_requested(self):
        return self._termination_requested

    @property
    def lifetime_closed(self):
        """Observe lifetime closure; residual startup handles may still need cleanup."""
        with self._lock:
            return self._closed

    def _require_open(self):
        _require(not self._closed, "WINDOWS_OWNED_PROCESS_CLOSED")

    def _duplicate(self):
        with self._lock:
            self._require_open()
            process, result = self._api.GetCurrentProcess(), HANDLE()
            if not self._api.DuplicateHandle(process, self._process, process, C.byref(result), 0, False, 2):
                _failed("WINDOWS_PROCESS_OBSERVATION_HANDLE_FAILED")
            return result.value

    def poll(self):
        with self._lock:
            self._require_open()
            if self._process is None:
                _require(self._exit_code is not None, "WINDOWS_PROCESS_EXIT_UNAVAILABLE")
                return self._exit_code
        handle = self._duplicate()
        try:
            observed = self._api.WaitForSingleObject(handle, 0)
            if observed == WAIT_TIMEOUT:
                return None
            _require(observed == WAIT_OBJECT_0, "WINDOWS_PROCESS_WAIT_FAILED")
            code = DWORD()
            if not self._api.GetExitCodeProcess(handle, C.byref(code)):
                _failed("WINDOWS_PROCESS_EXIT_UNAVAILABLE")
            self._exit_code = code.value
            return code.value  # 259 is a legal exit code after exit is observed.
        finally:
            self._api.close(handle)

    def wait(self, timeout_seconds):
        milliseconds = _timeout(timeout_seconds)
        with self._lock:
            self._require_open()
            if self._process is None:
                _require(self._exit_code is not None, "WINDOWS_PROCESS_EXIT_UNAVAILABLE")
                return True
        handle = self._duplicate()
        try:
            observed = self._api.WaitForSingleObject(handle, milliseconds)
            _require(observed in (WAIT_OBJECT_0, WAIT_TIMEOUT), "WINDOWS_PROCESS_WAIT_FAILED")
            return observed == WAIT_OBJECT_0
        finally:
            self._api.close(handle)

    def active_process_count(self):
        with self._lock:
            self._require_open()
            accounting = ACCOUNTING()
            if not self._api.QueryInformationJobObject(self._job, 1, C.byref(accounting), C.sizeof(accounting), None):
                _failed("WINDOWS_JOB_OBSERVATION_FAILED")
            return accounting.active_processes

    def terminate(self, exit_code=125):
        _require(type(exit_code) is int and 0 <= exit_code <= 0xFFFFFFFF, "WINDOWS_TERMINATION_CODE_REQUIRED")
        with self._lock:
            self._require_open()
            if not self._api.TerminateJobObject(self._job, exit_code):
                _failed("WINDOWS_JOB_TERMINATION_FAILED")
            self._termination_requested = True

    def close(self):
        with self._lock:
            if self._closed:
                while self._cleanup_handles:
                    self._api.close(self._cleanup_handles[0])
                    del self._cleanup_handles[0]
                return
            _require(self.poll() is not None and self.active_process_count() == 0, "WINDOWS_OWNED_LIFETIME_UNRESOLVED")
            while self._cleanup_handles:
                self._api.close(self._cleanup_handles[0])
                del self._cleanup_handles[0]
            self._api.close(self._thread)
            self._thread = None
            self._api.close(self._process)
            self._process = None
            self._api.close(self._job)
            self._job = None
            self._closed = True
