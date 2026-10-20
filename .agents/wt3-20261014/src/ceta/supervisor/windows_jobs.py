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
import time

from ceta.contracts.wire import ContractError
from ceta.contracts.resource_management import (
    ObservationState, ProcessResourceCounters, ProcessResourceIdentity, ProcessUsageMeasurements, QuantityObservation,
)
from ceta.contracts.workload_throttling import (
    CpuRateChange, CpuRateLimit, CpuRateObservation, bounded_time,
)

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


class PROCESS_MEMORY_COUNTERS_EX(C.Structure):
    _fields_ = [("cb", DWORD), ("page_faults", DWORD)] + [(name, SIZE_T) for name in
        ("peak_working_set", "working_set", "quota_peak_paged", "quota_paged", "quota_peak_nonpaged",
         "quota_nonpaged", "pagefile", "peak_pagefile", "private_usage")]


class EXTENDED_LIMIT(C.Structure):
    _fields_ = [("basic", BASIC_LIMIT), ("io", IO_COUNTERS),
                ("process_memory", SIZE_T), ("job_memory", SIZE_T),
                ("peak_process_memory", SIZE_T), ("peak_job_memory", SIZE_T)]


class ACCOUNTING(C.Structure):
    _fields_ = [("total_user", C.c_int64), ("total_kernel", C.c_int64),
                ("period_user", C.c_int64), ("period_kernel", C.c_int64),
                ("page_faults", DWORD), ("total_processes", DWORD),
                ("active_processes", DWORD), ("terminated_processes", DWORD)]


class CPU_RATE_CONTROL(C.Structure):
    # The second DWORD retains all union bits (CpuRate/Weight/MinRate+MaxRate).
    _fields_ = [("control_flags", DWORD), ("value", DWORD)]


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
        _require(C.sizeof(PROCESS_MEMORY_COUNTERS_EX) == 80 and C.sizeof(IO_COUNTERS) == 48,
                 "WINDOWS_RESOURCE_COUNTER_LAYOUT_UNSUPPORTED")
        _require(C.sizeof(CPU_RATE_CONTROL) == 8, "WINDOWS_CPU_RATE_LAYOUT_UNSUPPORTED")
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
            "K32GetProcessMemoryInfo": ([HANDLE, C.POINTER(PROCESS_MEMORY_COUNTERS_EX), DWORD], W.BOOL),
            "GetProcessIoCounters": ([HANDLE, C.POINTER(IO_COUNTERS)], W.BOOL),
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
        # This fallible nonce is created before launch creates any native handles.
        self.job_identity_nonce = "sha256:" + hashlib.sha256(os.urandom(32)).hexdigest()

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
        self._cpu_job_digest = api.job_identity_nonce
        self._cpu_version, self._cpu_policy, self._cpu_change = 0, None, None
        self._cpu_clock_highwater, self._cpu_perf_highwater = 0, 0
        self._cpu_clock_fault = False

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

    @property
    def resource_identity(self):
        return ProcessResourceIdentity(self.pid, self.creation_time, "sha256:" + self.image_sha256)

    def _resource_current(self, identity):
        if self._closed or self._process is None or identity != self.resource_identity:
            return False
        if self._api.GetProcessId(self._process) != identity.pid:
            return False
        values = [W.FILETIME() for _ in range(4)]
        return (self._api.GetProcessTimes(self._process, *(C.byref(item) for item in values))
                and (values[0].dwHighDateTime << 32 | values[0].dwLowDateTime) == identity.creation_time
                and self._api.WaitForSingleObject(self._process, 0) == WAIT_TIMEOUT)

    def resource_observation_current(self, identity):
        _require(type(identity) is ProcessResourceIdentity, "WINDOWS_RESOURCE_IDENTITY_REQUIRED")
        with self._lock:
            return bool(self._resource_current(identity))

    def resource_counters(self):
        """Read one retained handle under its lifecycle lock; no PID reopen or effect."""
        with self._lock:
            self._require_open()
            identity = self.resource_identity
            started = time.monotonic_ns()
            def quantity(value, at, method, reason):
                if value is not None and not 0 <= value <= 2**63 - 1:
                    value, reason = None, "PROCESS_COUNTER_OUT_OF_RANGE"
                return QuantityObservation(ObservationState.UNAVAILABLE if value is None else ObservationState.MEASURED,
                    value, at, method, reason if value is None else None)
            def unavailable(reason):
                at = time.monotonic_ns()
                return ProcessResourceCounters(identity, at,
                    quantity(None, at, "windows:K32GetProcessMemoryInfo", reason),
                    ProcessUsageMeasurements(started, quantity(None, at, "windows:GetProcessTimes", reason),
                        quantity(None, at, "windows:K32GetProcessMemoryInfo", reason),
                        quantity(None, at, "windows:GetProcessIoCounters", reason),
                        quantity(None, at, "windows:GetProcessIoCounters", reason)))
            if not self._resource_current(identity):
                return unavailable("PROCESS_LIFETIME_UNAVAILABLE")
            times = [W.FILETIME() for _ in range(4)]
            cpu_ok = bool(self._api.GetProcessTimes(self._process, *(C.byref(item) for item in times)))
            if cpu_ok and (times[0].dwHighDateTime << 32 | times[0].dwLowDateTime) != identity.creation_time:
                return unavailable("PROCESS_IDENTITY_CHANGED")
            cpu = sum(item.dwHighDateTime << 32 | item.dwLowDateTime for item in times[2:]) if cpu_ok else None
            memory, io = PROCESS_MEMORY_COUNTERS_EX(), IO_COUNTERS()
            memory.cb = C.sizeof(memory)
            memory_ok = bool(self._api.K32GetProcessMemoryInfo(self._process, C.byref(memory), C.sizeof(memory)))
            io_ok = bool(self._api.GetProcessIoCounters(self._process, C.byref(io)))
            if not self._resource_current(identity):
                return unavailable("PROCESS_SOURCE_CHANGED_DURING_SAMPLE")
            at = time.monotonic_ns()
            return ProcessResourceCounters(identity, at,
                quantity(memory.working_set if memory_ok else None, at, "windows:K32GetProcessMemoryInfo", "PROCESS_MEMORY_QUERY_FAILED"),
                ProcessUsageMeasurements(started,
                    quantity(cpu, at, "windows:GetProcessTimes", "PROCESS_CPU_QUERY_FAILED"),
                    quantity(memory.private_usage if memory_ok else None, at, "windows:K32GetProcessMemoryInfo", "PROCESS_MEMORY_QUERY_FAILED"),
                    quantity(io.read_bytes if io_ok else None, at, "windows:GetProcessIoCounters", "PROCESS_IO_QUERY_FAILED"),
                    quantity(io.write_bytes if io_ok else None, at, "windows:GetProcessIoCounters", "PROCESS_IO_QUERY_FAILED")))

    def _cpu_now(self):
        """Both clocks are sampled under the existing lifecycle lock."""
        try:
            mono, elapsed = time.monotonic_ns(), time.perf_counter_ns()
            _require(type(mono) is int and type(elapsed) is int and 0 <= mono <= 2**63 - 1
                     and 0 <= elapsed <= 2**63 - 1, "WINDOWS_CPU_CLOCK_INVALID")
        except BaseException:
            self._cpu_clock_fault = True
            raise
        if mono < self._cpu_clock_highwater or elapsed < self._cpu_perf_highwater:
            self._cpu_clock_fault = True
        self._cpu_clock_highwater = max(mono, self._cpu_clock_highwater)
        self._cpu_perf_highwater = max(elapsed, self._cpu_perf_highwater)
        _require(not self._cpu_clock_fault, "WINDOWS_CPU_CLOCK_ROLLBACK")
        return mono, elapsed

    @staticmethod
    def _cpu_bounds(maximum_duration_ns, maximum_age_ns=None, deadline_monotonic_ns=None):
        _require(type(maximum_duration_ns) is int and 1 <= maximum_duration_ns <= 1_000_000_000,
                 "WINDOWS_CPU_DURATION_INVALID")
        if maximum_age_ns is not None:
            _require(type(maximum_age_ns) is int and 1 <= maximum_age_ns <= 60_000_000_000,
                     "WINDOWS_CPU_AGE_INVALID")
        if deadline_monotonic_ns is not None:
            bounded_time(deadline_monotonic_ns, "WINDOWS_CPU_DEADLINE_INVALID")

    def _cpu_window(self, started, maximum_duration_ns, deadline=None):
        now, elapsed = self._cpu_now()
        margin = math.ceil(time.get_clock_info("monotonic").resolution * 1_000_000_000)
        _require(elapsed - started[1] <= maximum_duration_ns, "WINDOWS_CPU_OBSERVATION_TOO_SLOW")
        _require(deadline is None or max(now, started[0] + elapsed - started[1]) + margin < deadline,
                 "WINDOWS_CPU_DEADLINE_EXPIRED")
        return now

    def _cpu_member_current(self, identity):
        if not self._resource_current(identity) or self._termination_requested or self._job is None:
            return False
        member = W.BOOL()
        return bool(self._api.IsProcessInJob(self._process, self._job, C.byref(member)) and member.value)

    def _cpu_read(self, identity, started, maximum_duration_ns, deadline=None):
        def unavailable(reason):
            return CpuRateObservation(identity, self._cpu_job_digest, ObservationState.UNAVAILABLE,
                                      None, self._cpu_version, started[0], reason)
        try:
            if not self._cpu_member_current(identity):
                return unavailable("WINDOWS_CPU_LIFETIME_UNAVAILABLE")
            information, length = CPU_RATE_CONTROL(), DWORD()
            if not self._api.QueryInformationJobObject(self._job, 15, C.byref(information),
                                                       C.sizeof(information), C.byref(length)):
                return unavailable("WINDOWS_CPU_QUERY_UNAVAILABLE")
            if length.value != C.sizeof(information):
                return unavailable("WINDOWS_CPU_QUERY_SIZE_INVALID")
            limit = CpuRateLimit(information.control_flags, information.value)
            if not self._cpu_member_current(identity):
                return unavailable("WINDOWS_CPU_SOURCE_CHANGED")
            self._cpu_window(started, maximum_duration_ns, deadline)
            if self._cpu_policy is not None and self._cpu_policy != limit:
                _require(self._cpu_version < 2**63 - 1, "WINDOWS_CPU_VERSION_EXHAUSTED")
                self._cpu_version += 1
            self._cpu_policy = limit
            return CpuRateObservation(identity, self._cpu_job_digest, ObservationState.MEASURED,
                                      limit, self._cpu_version, started[0])
        except (OSError, ContractError) as failure:
            reason = failure.code if type(failure) is ContractError else "WINDOWS_CPU_NATIVE_UNAVAILABLE"
            return unavailable(reason)

    def cpu_rate_observation(self, identity, *, maximum_duration_ns=100_000_000):
        """Observe the exact owned job, without reopening a PID or changing limits.

        High-resolution elapsed rejection bounds accepted results, not native
        synchronous occupancy. An unavailable observation never means zero.
        """
        _require(type(identity) is ProcessResourceIdentity, "WINDOWS_CPU_IDENTITY_REQUIRED")
        identity.__post_init__(); self._cpu_bounds(maximum_duration_ns)
        with self._lock:
            self._require_open()
            started = self._cpu_now()
            return self._cpu_read(identity, started, maximum_duration_ns)

    def _cpu_expected(self, identity, expected, started, maximum_age_ns, maximum_duration_ns, deadline):
        _require(type(identity) is ProcessResourceIdentity and type(expected) is CpuRateObservation,
                 "WINDOWS_CPU_EXPECTATION_REQUIRED")
        identity.__post_init__(); expected.__post_init__()
        expected = CpuRateObservation(expected.identity, expected.job_digest, expected.state,
            None if expected.limit is None else CpuRateLimit(expected.limit.control_flags, expected.limit.value),
            expected.version, expected.observed_monotonic_ns, expected.reason)
        _require(expected.identity == identity and identity == self.resource_identity
                 and expected.job_digest == self._cpu_job_digest, "WINDOWS_CPU_TARGET_MISMATCH")
        margin = math.ceil(time.get_clock_info("monotonic").resolution * 1_000_000_000)
        _require(expected.state is ObservationState.MEASURED
                 and 0 <= started[0] - expected.observed_monotonic_ns
                 and started[0] - expected.observed_monotonic_ns + margin <= maximum_age_ns,
                 "WINDOWS_CPU_EXPECTATION_STALE")
        current = self._cpu_read(identity, started, maximum_duration_ns, deadline)
        _require(current.state is ObservationState.MEASURED, "WINDOWS_CPU_OBSERVATION_UNAVAILABLE")
        _require(current.version == expected.version and current.limit == expected.limit,
                 "WINDOWS_CPU_LIMIT_CONFLICT")
        ended = self._cpu_window(started, maximum_duration_ns, deadline)
        conservative_age = max(ended - expected.observed_monotonic_ns,
            started[0] - expected.observed_monotonic_ns + time.perf_counter_ns() - started[1]) + margin
        _require(conservative_age <= maximum_age_ns, "WINDOWS_CPU_EXPECTATION_STALE")
        return current

    def _cpu_publish_change(self, prior, state, reason, observed, restoration_id=None):
        self._cpu_change = CpuRateChange(prior.operation_id, prior.identity, prior.job_digest,
            prior.before, prior.intended, observed, state, reason,
            restoration_id if restoration_id is not None else prior.restoration_id)
        return self._cpu_change

    def _cpu_set(self, prior, target, started, maximum_duration_ns, deadline, restoration_id=None,
                 dispatch_fence=None):
        """Retain reconciliation facts before the only native effect call."""
        _require(self._cpu_version < 2**63 - 1, "WINDOWS_CPU_VERSION_EXHAUSTED")
        version, policy, change = self._cpu_version, self._cpu_policy, self._cpu_change
        pending = CpuRateChange(prior.operation_id, prior.identity, prior.job_digest, prior.before, prior.intended,
            None, "UNCERTAIN", "WINDOWS_CPU_EFFECT_UNOBSERVED",
            restoration_id if restoration_id is not None else prior.restoration_id)
        information = CPU_RATE_CONTROL(target.control_flags, target.value)
        setter = self._api.SetInformationJobObject
        arguments = (self._job, 15, C.byref(information), C.sizeof(information))
        _require(callable(setter), "WINDOWS_CPU_SET_UNAVAILABLE")
        if dispatch_fence is not None:
            _require(callable(dispatch_fence), "WINDOWS_CPU_DISPATCH_FENCE_INVALID")
            _require(dispatch_fence() is None, "WINDOWS_CPU_DISPATCH_DECISION_MALFORMED")
        # Callbacks are finished. Retained native identity/state must still be
        # exact; callback reentry cannot silently change this prepared operation.
        _require(not self._closed and not self._termination_requested
                 and self._job == arguments[0] and self._cpu_version == version
                 and self._cpu_policy == policy and self._cpu_change is change, "WINDOWS_CPU_DISPATCH_STATE_CHANGED")
        self._cpu_version = version + 1
        self._cpu_policy = None  # An admitted attempt remains spent on interruption.
        self._cpu_change = pending
        try:
            succeeded = bool(setter(*arguments))
            observed = self._cpu_read(prior.identity, started, maximum_duration_ns, deadline)
            if observed.state is not ObservationState.MEASURED:
                return self._cpu_publish_change(prior, "UNCERTAIN", "WINDOWS_CPU_EFFECT_UNOBSERVED", observed, restoration_id)
            if succeeded and observed.limit == target:
                state = "RESTORED" if restoration_id is not None else "APPLIED"
                return self._cpu_publish_change(prior, state, "WINDOWS_CPU_LIMIT_OBSERVED", observed, restoration_id)
            state = "NOT_APPLIED" if not succeeded and observed.limit == prior.before and restoration_id is None else "UNCERTAIN"
            return self._cpu_publish_change(prior, state, "WINDOWS_CPU_EFFECT_NOT_CONFIRMED", observed, restoration_id)
        except (OSError, ContractError):
            return self._cpu_publish_change(prior, "UNCERTAIN", "WINDOWS_CPU_NATIVE_UNAVAILABLE", None, restoration_id)
        except BaseException as failure:
            # Keep the original control exception and expose exact retained custody.
            try:
                failure.cpu_rate_change = self._cpu_change
                failure.owned_process = self
            except BaseException:
                pass
            raise

    def apply_cpu_rate_limit(self, operation_id, identity, expected, limit, *,
                             deadline_monotonic_ns, maximum_age_ns=1_000_000_000,
                             maximum_duration_ns=100_000_000, dispatch_fence=None):
        """Trusted-owner library CAS; composition must supply current admission.

        Only a hard-cap reduction is supported here. The owner retains one
        outstanding original policy; new effects wait for observed recovery.
        This volatile record does not replace canonical durable intent/history.
        """
        from ceta.contracts.resource_management import identifier
        identifier(operation_id, "WINDOWS_CPU_OPERATION_REQUIRED")
        _require(type(limit) is CpuRateLimit and limit.control_flags in (5, 13), "WINDOWS_CPU_HARD_CAP_REQUIRED")
        limit.__post_init__()
        limit = CpuRateLimit(limit.control_flags, limit.value)
        self._cpu_bounds(maximum_duration_ns, maximum_age_ns, deadline_monotonic_ns)
        with self._lock:
            self._require_open(); started = self._cpu_now()
            current = self._cpu_expected(identity, expected, started, maximum_age_ns, maximum_duration_ns, deadline_monotonic_ns)
            prior = self._cpu_change
            if prior is not None and prior.state not in ("RESTORED", "NOT_APPLIED"):
                _require(prior.operation_id == operation_id and prior.intended == limit
                         and prior.identity == identity, "WINDOWS_CPU_RECOVERY_REQUIRED")
                _require(prior.state == "APPLIED" and current.limit == prior.intended,
                         "WINDOWS_CPU_UNCERTAIN_RECONCILIATION_REQUIRED")
                return prior  # No second Set call, including concurrent duplicate delivery.
            _require(prior is None or prior.operation_id != operation_id, "WINDOWS_CPU_OPERATION_ALREADY_SETTLED")
            before = current.limit
            ceiling = 10000 if before.control_flags == 0 else before.hard_cap_rate
            _require(ceiling is not None and limit.value < ceiling, "WINDOWS_CPU_REDUCTION_REQUIRED")
            _require(limit.control_flags & 8 == before.control_flags & 8, "WINDOWS_CPU_NOTIFICATION_PRESERVATION_REQUIRED")
            prior = CpuRateChange(operation_id, identity, self._cpu_job_digest, before, limit,
                                  current, "UNCERTAIN", "WINDOWS_CPU_EFFECT_NOT_STARTED")
            self._cpu_window(started, maximum_duration_ns, deadline_monotonic_ns)
            return self._cpu_set(prior, limit, started, maximum_duration_ns, deadline_monotonic_ns,
                                 dispatch_fence=dispatch_fence)

    def reconcile_cpu_rate_limit(self, identity, *, maximum_duration_ns=100_000_000):
        """Read-only current reconciliation; never retries or restores a limit."""
        with self._lock:
            observation = self.cpu_rate_observation(identity, maximum_duration_ns=maximum_duration_ns)
            prior = self._cpu_change
            if prior is None:
                return None
            _require(prior.identity == identity, "WINDOWS_CPU_TARGET_MISMATCH")
            if observation.state is not ObservationState.MEASURED:
                return self._cpu_publish_change(prior, "UNCERTAIN", "WINDOWS_CPU_RECONCILIATION_UNAVAILABLE", observation)
            if observation.limit == prior.intended:
                return self._cpu_publish_change(prior, "APPLIED", "WINDOWS_CPU_LIMIT_RECONCILED", observation)
            if observation.limit == prior.before:
                state = "RESTORED" if prior.restoration_id is not None else "NOT_APPLIED"
                return self._cpu_publish_change(prior, state, "WINDOWS_CPU_ORIGINAL_RECONCILED", observation)
            return self._cpu_publish_change(prior, "CONFLICT", "WINDOWS_CPU_UNEXPECTED_LIMIT", observation)

    def restore_cpu_rate_limit(self, operation_id, change_id, identity, expected, original_limit, *,
                               deadline_monotonic_ns, maximum_age_ns=1_000_000_000,
                               maximum_duration_ns=100_000_000, dispatch_fence=None):
        """Distinct, currently authorized compensation supplied by composition."""
        from ceta.contracts.resource_management import identifier
        identifier(operation_id, "WINDOWS_CPU_OPERATION_REQUIRED"); identifier(change_id, "WINDOWS_CPU_CHANGE_REQUIRED")
        _require(operation_id != change_id, "WINDOWS_CPU_RESTORATION_ID_REUSED")
        _require(type(original_limit) is CpuRateLimit, "WINDOWS_CPU_ORIGINAL_LIMIT_REQUIRED")
        original_limit.__post_init__()
        original_limit = CpuRateLimit(original_limit.control_flags, original_limit.value)
        self._cpu_bounds(maximum_duration_ns, maximum_age_ns, deadline_monotonic_ns)
        with self._lock:
            self._require_open(); started = self._cpu_now()
            current = self._cpu_expected(identity, expected, started, maximum_age_ns, maximum_duration_ns, deadline_monotonic_ns)
            prior = self._cpu_change
            _require(prior is not None and prior.operation_id == change_id and prior.identity == identity,
                     "WINDOWS_CPU_CHANGE_NOT_OWNED")
            _require(prior.before == original_limit, "WINDOWS_CPU_RESTORATION_TARGET_MISMATCH")
            if prior.state == "RESTORED":
                _require(prior.restoration_id == operation_id and current.limit == prior.before,
                         "WINDOWS_CPU_RESTORATION_CONFLICT")
                return prior
            _require(prior.state == "APPLIED" and current.limit == prior.intended
                     and (prior.restoration_id is None or prior.restoration_id == operation_id),
                     "WINDOWS_CPU_UNCERTAIN_RECONCILIATION_REQUIRED")
            self._cpu_window(started, maximum_duration_ns, deadline_monotonic_ns)
            return self._cpu_set(prior, prior.before, started, maximum_duration_ns, deadline_monotonic_ns,
                                 operation_id, dispatch_fence)

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
