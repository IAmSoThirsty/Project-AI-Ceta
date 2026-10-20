"""Bounded Windows hardware and capacity observations."""
from __future__ import annotations

import ctypes
from dataclasses import dataclass
import os
from pathlib import Path
import platform
import shutil
import threading
import time

from ceta.contracts.resource_management import (
    CapacitySnapshot, HardwareProfile, ObservationState, QuantityObservation, ResourceKind,
    ResourceVector, identifier, require,
)


def _measured(value: int, now_ns: int, method: str) -> QuantityObservation:
    return QuantityObservation(ObservationState.MEASURED, value, now_ns, method)


def _unavailable(now_ns: int, method: str, reason: str) -> QuantityObservation:
    return QuantityObservation(ObservationState.UNAVAILABLE, None, now_ns, method, reason)


def _unavailable_capacity(kind: ResourceKind, now_ns: int, method: str, reason: str,
                          sequence: int = 0) -> CapacitySnapshot:
    unknown = _unavailable(now_ns, method, reason)
    return CapacitySnapshot(kind, unknown, unknown, unknown, unknown, sequence)


class _MemoryStatus(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


class _Guid(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort), ("Data4", ctypes.c_ubyte * 8)]


class _Luid(ctypes.Structure):
    _fields_ = [("LowPart", ctypes.c_ulong), ("HighPart", ctypes.c_long)]


class _DxgiAdapterDesc(ctypes.Structure):
    _fields_ = [("Description", ctypes.c_wchar * 128), ("VendorId", ctypes.c_uint),
                ("DeviceId", ctypes.c_uint), ("SubSysId", ctypes.c_uint),
                ("Revision", ctypes.c_uint), ("DedicatedVideoMemory", ctypes.c_size_t),
                ("DedicatedSystemMemory", ctypes.c_size_t), ("SharedSystemMemory", ctypes.c_size_t),
                ("AdapterLuid", _Luid)]


_IID_IDXGI_FACTORY1 = _Guid(0x770AAE78, 0xF26F, 0x4DBA,
                            (ctypes.c_ubyte * 8)(0xA8, 0x29, 0x25, 0x3C, 0x83, 0xD1, 0xB3, 0x87))
_DXGI_ERROR_NOT_FOUND = -2005270526  # HRESULT 0x887A0002
_MAX_QUANTITY = (1 << 63) - 1
_DEFAULT_CLOCK = time.monotonic_ns


@dataclass(frozen=True, slots=True)
class SamplingPolicy:
    maximum_age_ns: int = 30_000_000_000
    minimum_interval_ns: int = 100_000_000
    control_cpu_milli: int = 50
    control_memory_bytes: int = 64 * 1024 * 1024
    control_storage_bytes: int = 64 * 1024 * 1024
    maximum_probe_window_ns: int | None = None
    maximum_sampling_interval_ns: int | None = None

    def __post_init__(self) -> None:
        require(type(self.maximum_age_ns) is int and 1 <= self.maximum_age_ns <= 300_000_000_000
                and type(self.minimum_interval_ns) is int and 1 <= self.minimum_interval_ns <= self.maximum_age_ns,
                "RESOURCE_MAXIMUM_AGE_INVALID")
        for value in (self.control_cpu_milli, self.control_memory_bytes, self.control_storage_bytes):
            require(type(value) is int and 0 <= value <= _MAX_QUANTITY, "RESOURCE_CONTROL_RESERVE_INVALID")
        probe = self.maximum_probe_window_ns
        interval = self.maximum_sampling_interval_ns
        require(probe is None or type(probe) is int and 1 <= probe <= self.maximum_age_ns,
                "RESOURCE_PROBE_WINDOW_INVALID")
        require(interval is None or type(interval) is int
                and self.minimum_interval_ns <= interval <= self.maximum_age_ns,
                "RESOURCE_SAMPLING_INTERVAL_INVALID")

    @property
    def probe_window_ns(self) -> int:
        return min(self.maximum_age_ns, 1_000_000_000) if self.maximum_probe_window_ns is None else self.maximum_probe_window_ns

    @property
    def sampling_interval_ns(self) -> int:
        return self.maximum_age_ns if self.maximum_sampling_interval_ns is None else self.maximum_sampling_interval_ns


class _ObservationClock:
    """Constant-size monotonic high-water, used only under its owner's lock."""
    def __init__(self, clock, policy: SamplingPolicy) -> None:
        self._clock, self._policy, self._high_water = clock, policy, 0
        # Keep public timestamps in their existing monotonic domain. On the
        # native default path independently measure elapsed time with QPC;
        # GetTickCount64's coarse ticks cannot establish small physical bounds.
        self._elapsed_clock = time.perf_counter_ns if clock is _DEFAULT_CLOCK else None
        self._started_elapsed_ns = self._finished_elapsed_ns = self._published_elapsed_ns = None
        self._current_elapsed_ns = None
        self._elapsed_high_water = 0

    def _elapsed(self) -> tuple[int | None, str | None]:
        if self._elapsed_clock is None:
            return None, None
        value = self._elapsed_clock()
        require(type(value) is int and 0 <= value <= _MAX_QUANTITY, "RESOURCE_ELAPSED_CLOCK_INVALID")
        if value < self._elapsed_high_water:
            return self._elapsed_high_water, "RESOURCE_ELAPSED_CLOCK_ROLLBACK"
        self._elapsed_high_water = value
        return value, None

    def begin(self) -> tuple[int, str | None]:
        self._started_elapsed_ns, elapsed_reason = self._elapsed()
        now_ns, reason = self.read()
        # Check elapsed age after the public-clock lookup too: scheduling or
        # a delayed lookup must not return a cache qualified by an earlier time.
        self._current_elapsed_ns, current_reason = self._elapsed()
        return now_ns, reason or elapsed_reason or current_reason

    def read(self) -> tuple[int, str | None]:
        now_ns = self._clock()
        require(type(now_ns) is int and 0 <= now_ns <= _MAX_QUANTITY, "RESOURCE_CLOCK_INVALID")
        if now_ns < self._high_water:
            return self._high_water, "RESOURCE_CLOCK_ROLLBACK"
        self._high_water = now_ns
        return now_ns, None

    def finish(self, started_ns: int) -> tuple[int, str | None]:
        ended_ns, reason = self.read()
        self._finished_elapsed_ns, elapsed_reason = self._elapsed()
        reason = reason or elapsed_reason
        elapsed = (self._finished_elapsed_ns - self._started_elapsed_ns
                   if self._started_elapsed_ns is not None else 0)
        if reason is None and max(ended_ns - started_ns, elapsed) > self._policy.probe_window_ns:
            reason = "RESOURCE_PROBE_WINDOW_EXCEEDED"
        return ended_ns, reason

    def cache_is_recent(self, snapshot: CapacitySnapshot, now_ns: int) -> bool:
        maximum = min(self._policy.maximum_age_ns, self._policy.sampling_interval_ns)
        return snapshot.is_recent(now_ns, maximum) and (
            self._current_elapsed_ns is None or self._published_elapsed_ns is not None
            and 0 <= self._current_elapsed_ns - self._published_elapsed_ns <= maximum)

    def minimum_interval_pending(self, snapshot: CapacitySnapshot, now_ns: int) -> bool:
        age = (self._current_elapsed_ns - self._published_elapsed_ns
               if self._current_elapsed_ns is not None and self._published_elapsed_ns is not None
               else now_ns - snapshot.total.observed_monotonic_ns)
        return age < self._policy.minimum_interval_ns

    def interval_exceeded(self, previous_elapsed_ns: int | None) -> bool:
        return (previous_elapsed_ns is not None and self._finished_elapsed_ns is not None
                and self._finished_elapsed_ns - previous_elapsed_ns > self._policy.sampling_interval_ns)

    def publish(self) -> None:
        self._published_elapsed_ns = self._started_elapsed_ns


def _storage_capacity(usage, now_ns: int, sequence: int, policy: SamplingPolicy) -> CapacitySnapshot:
    method = "python:shutil.disk_usage"
    try:
        total, free = usage.total, usage.free
        valid = all(type(value) is int and 0 <= value <= _MAX_QUANTITY for value in (total, free)) and free <= total
        # Older declared reader ports supply total/free only. If a reader also
        # supplies used bytes, require all three readings to agree.
        if hasattr(usage, "used"):
            used = usage.used
            valid = valid and type(used) is int and 0 <= used <= _MAX_QUANTITY and used + free == total
    except Exception:
        valid = False
    if not valid:
        return _unavailable_capacity(ResourceKind.STORAGE, now_ns, method, "STORAGE_QUERY_INVALID", sequence)
    utilization = 0 if total == 0 else ((total - free) * 1000) // total
    return _capacity(ResourceKind.STORAGE, total, free, max(0, free - policy.control_storage_bytes),
                     utilization, now_ns, method, sequence)


class WindowsHardwareProfiler:
    """Native local observations with no subprocesses or capacity guesses."""
    def __init__(self, *, clock=time.monotonic_ns, storage_path: Path | None = None,
                 policy: SamplingPolicy = SamplingPolicy(), accelerator_memory_reader=None) -> None:
        require(callable(clock) and type(policy) is SamplingPolicy
                and (storage_path is None or isinstance(storage_path, Path))
                and (accelerator_memory_reader is None or callable(accelerator_memory_reader)),
                "RESOURCE_HARDWARE_PROFILER_INPUT_INVALID")
        self._path, self._policy = (Path.cwd() if storage_path is None else storage_path).absolute(), policy
        self._timeline = _ObservationClock(clock, policy)
        self._accelerator_memory_reader = self._dedicated_video_memory if accelerator_memory_reader is None else accelerator_memory_reader
        self._sequence = 0
        self._lock = threading.Lock()

    def profile(self, profile_id: str) -> HardwareProfile:
        # Reject an invalid caller-supplied identity before asking Windows or
        # the filesystem for any observation.  The resulting profile still
        # validates this field at construction as a defense in depth.
        identifier(profile_id, "RESOURCE_PROFILE_IDENTIFIER_INVALID")
        with self._lock:
            require(self._sequence < _MAX_QUANTITY, "RESOURCE_SEQUENCE_EXHAUSTED")
            self._sequence += 1
            sequence = self._sequence
            now_ns, reason = self._timeline.begin()
            if reason is None:
                try:
                    cpu_total = os.cpu_count()
                except Exception:
                    cpu_total = None
                # Global processor count describes capability, not idle capacity.
                cpu = (_hardware_cpu_capacity(cpu_total * 1000, now_ns, "windows:os.cpu_count", sequence)
                       if type(cpu_total) is int and 1 <= cpu_total <= _MAX_QUANTITY // 1000 else
                       _unavailable_capacity(ResourceKind.CPU, now_ns, "windows:os.cpu_count", "CPU_COUNT_UNAVAILABLE", sequence))
                memory = self._memory(now_ns, sequence)
                storage = self._storage(now_ns, sequence)
                accelerators = self._accelerators(now_ns, sequence)
                isolation = self._isolation(now_ns)
                platform_name = platform.system() + ":" + platform.release()
                ended_ns, reason = self._timeline.finish(now_ns)
            else:
                ended_ns = now_ns
                platform_name = platform.system() + ":" + platform.release()
            if reason is not None:
                cpu = _unavailable_capacity(ResourceKind.CPU, ended_ns, "windows:os.cpu_count", reason, sequence)
                memory = _unavailable_capacity(ResourceKind.MEMORY, ended_ns, "windows:GlobalMemoryStatusEx", reason, sequence)
                storage = _unavailable_capacity(ResourceKind.STORAGE, ended_ns, "python:shutil.disk_usage", reason, sequence)
                accelerators = (_unavailable_capacity(ResourceKind.ACCELERATOR, ended_ns, "windows:DXGI.EnumAdapters:GetDesc", reason, sequence),)
                isolation = _unavailable(ended_ns, "windows:IsProcessInJob", reason)
            return HardwareProfile(profile_id, cpu, memory, storage, accelerators, isolation, ended_ns,
                                   platform_name)

    def _accelerators(self, now_ns: int, sequence: int) -> tuple[CapacitySnapshot, ...]:
        method = "windows:DXGI.EnumAdapters:GetDesc"
        if os.name != "nt":
            return (_unavailable_capacity(ResourceKind.ACCELERATOR, now_ns, method, "WINDOWS_REQUIRED", sequence),)
        try:
            memories = self._accelerator_memory_reader()
        except Exception:
            return (_unavailable_capacity(ResourceKind.ACCELERATOR, now_ns, method, "ACCELERATOR_QUERY_FAILED", sequence),)
        if type(memories) is not tuple or len(memories) > 16 or any(type(value) is not int or not 0 <= value <= _MAX_QUANTITY for value in memories):
            return (_unavailable_capacity(ResourceKind.ACCELERATOR, now_ns, method, "ACCELERATOR_QUERY_INVALID", sequence),)
        if not memories:
            return (_unavailable_capacity(ResourceKind.ACCELERATOR, now_ns, method, "ACCELERATOR_NOT_FOUND", sequence),)
        unavailable = _unavailable(now_ns, method, "ACCELERATOR_RUNTIME_AVAILABILITY_NOT_OBSERVED")
        return tuple(CapacitySnapshot(ResourceKind.ACCELERATOR, _measured(value, now_ns, method), unavailable,
                                      unavailable, unavailable, sequence)
                     for value in memories)

    @staticmethod
    def _com_method(instance: ctypes.c_void_p, index: int, restype, *argtypes):
        vtable = ctypes.cast(instance, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        return ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)(vtable[index])

    @classmethod
    def _dedicated_video_memory(cls) -> tuple[int, ...]:
        """Enumerate physical adapter memory through the vendor-neutral DXGI API."""
        if os.name != "nt":
            raise OSError("WINDOWS_REQUIRED")
        try:
            create_factory = ctypes.WinDLL("dxgi", use_last_error=True).CreateDXGIFactory1
        except (AttributeError, OSError):
            raise OSError("DXGI_UNAVAILABLE") from None
        create_factory.argtypes = (ctypes.POINTER(_Guid), ctypes.POINTER(ctypes.c_void_p))
        create_factory.restype = ctypes.c_long
        factory = ctypes.c_void_p()
        if create_factory(ctypes.byref(_IID_IDXGI_FACTORY1), ctypes.byref(factory)) < 0 or not factory.value:
            raise OSError("DXGI_FACTORY_CREATION_FAILED")
        try:
            enum_adapters = cls._com_method(factory, 7, ctypes.c_long, ctypes.c_uint,
                                            ctypes.POINTER(ctypes.c_void_p))
            memories: list[int] = []
            for index in range(16):
                adapter = ctypes.c_void_p()
                status = enum_adapters(factory, index, ctypes.byref(adapter))
                if status == _DXGI_ERROR_NOT_FOUND:
                    break
                if status < 0 or not adapter.value:
                    raise OSError("DXGI_ADAPTER_ENUMERATION_FAILED")
                try:
                    description = _DxgiAdapterDesc()
                    get_desc = cls._com_method(adapter, 8, ctypes.c_long, ctypes.POINTER(_DxgiAdapterDesc))
                    if get_desc(adapter, ctypes.byref(description)) < 0:
                        raise OSError("DXGI_ADAPTER_DESCRIPTION_FAILED")
                    memories.append(int(description.DedicatedVideoMemory))
                finally:
                    cls._com_method(adapter, 2, ctypes.c_ulong)(adapter)
            return tuple(memories)
        finally:
            cls._com_method(factory, 2, ctypes.c_ulong)(factory)

    def _memory(self, now_ns: int, sequence: int) -> CapacitySnapshot:
        if os.name != "nt":
            return _unavailable_capacity(ResourceKind.MEMORY, now_ns, "windows:GlobalMemoryStatusEx", "WINDOWS_REQUIRED", sequence)
        status = _MemoryStatus(); status.dwLength = ctypes.sizeof(status)
        try:
            query = ctypes.WinDLL("kernel32", use_last_error=True).GlobalMemoryStatusEx
            query.argtypes, query.restype = (ctypes.POINTER(_MemoryStatus),), ctypes.c_int
            ok = query(ctypes.byref(status))
        except (AttributeError, OSError):
            ok = False
        if not ok:
            return _unavailable_capacity(ResourceKind.MEMORY, now_ns, "windows:GlobalMemoryStatusEx", "MEMORY_QUERY_FAILED", sequence)
        total, free, load = int(status.ullTotalPhys), int(status.ullAvailPhys), int(status.dwMemoryLoad)
        if not 0 <= free <= total <= _MAX_QUANTITY or not 0 <= load <= 100:
            return _unavailable_capacity(ResourceKind.MEMORY, now_ns, "windows:GlobalMemoryStatusEx", "MEMORY_QUERY_INVALID", sequence)
        return _capacity(ResourceKind.MEMORY, total, free, max(0, free - self._policy.control_memory_bytes),
                         load * 10, now_ns, "windows:GlobalMemoryStatusEx", sequence)

    def _storage(self, now_ns: int, sequence: int) -> CapacitySnapshot:
        try:
            usage = shutil.disk_usage(self._path)
        except Exception:
            return _unavailable_capacity(ResourceKind.STORAGE, now_ns, "python:shutil.disk_usage", "STORAGE_QUERY_FAILED", sequence)
        return _storage_capacity(usage, now_ns, sequence, self._policy)

    @staticmethod
    def _isolation(now_ns: int) -> QuantityObservation:
        if os.name != "nt":
            return _unavailable(now_ns, "windows:IsProcessInJob", "WINDOWS_REQUIRED")
        flag = ctypes.c_int()
        try:
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            current = kernel.GetCurrentProcess
            current.argtypes, current.restype = (), ctypes.c_void_p
            query = kernel.IsProcessInJob
            query.argtypes, query.restype = (ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)), ctypes.c_int
            ok = query(current(), None, ctypes.byref(flag))
        except (AttributeError, OSError):
            return _unavailable(now_ns, "windows:IsProcessInJob", "ISOLATION_QUERY_FAILED")
        if not ok:
            return _unavailable(now_ns, "windows:IsProcessInJob", "ISOLATION_QUERY_FAILED")
        if flag.value not in (0, 1):
            return _unavailable(now_ns, "windows:IsProcessInJob", "ISOLATION_QUERY_INVALID")
        return _measured(flag.value, now_ns, "windows:IsProcessInJob")


def _capacity(kind: ResourceKind, total: int, free: int, reservable: int, utilization: int,
              now_ns: int, method: str, sequence: int = 0) -> CapacitySnapshot:
    return CapacitySnapshot(kind, _measured(total, now_ns, method), _measured(free, now_ns, method),
                            _measured(reservable, now_ns, method), _measured(utilization, now_ns, method), sequence)


def _hardware_cpu_capacity(total: int, now_ns: int, method: str, sequence: int) -> CapacitySnapshot:
    unavailable = _unavailable(now_ns, method, "AVAILABILITY_REQUIRES_RUNTIME_SAMPLE")
    return CapacitySnapshot(ResourceKind.CPU, _measured(total, now_ns, method), unavailable,
                            unavailable, unavailable, sequence)


class WindowsComputeAvailabilityMonitor:
    """A bounded, lock-protected CPU sampler. First use establishes a baseline."""
    def __init__(self, *, clock=time.monotonic_ns, policy: SamplingPolicy = SamplingPolicy(),
                 system_times=None, processor_count=os.cpu_count) -> None:
        require(callable(clock) and type(policy) is SamplingPolicy and callable(processor_count)
                and (system_times is None or callable(system_times)), "RESOURCE_COMPUTE_MONITOR_INPUT_INVALID")
        self._policy, self._timeline = policy, _ObservationClock(clock, policy)
        self._native_reader = system_times is None
        self._system_times_reader = self._system_times if system_times is None else system_times
        self._processor_count = processor_count
        self._previous: tuple[int, int, int, int, int | None] | None = None
        self._sequence = 0
        self._cached: CapacitySnapshot | None = None
        self._lock = threading.Lock()

    def sample(self) -> CapacitySnapshot:
        with self._lock:
            try:
                now_ns, reason = self._timeline.begin()
                if reason is None and self._cached is not None and self._timeline.cache_is_recent(self._cached, now_ns) \
                        and self._timeline.minimum_interval_pending(self._cached, now_ns):
                    return self._cached
                require(self._sequence < _MAX_QUANTITY, "RESOURCE_SEQUENCE_EXHAUSTED")
                self._sequence += 1
                sequence = self._sequence
                if reason is None:
                    try:
                        times, count, reason = self._read_counters()
                    except Exception:
                        times, count, reason = None, None, "CPU_QUERY_FAILED"
                    ended_ns, timing_reason = self._timeline.finish(now_ns)
                    reason = timing_reason or reason
                else:
                    ended_ns, times, count = now_ns, None, None
                if reason is not None:
                    self._previous = None
                    self._cached = _unavailable_capacity(ResourceKind.CPU, ended_ns, "windows:GetSystemTimes", reason, sequence)
                else:
                    previous = self._previous
                    if previous is None or previous[3] != count or ended_ns - previous[2] > self._policy.sampling_interval_ns \
                            or self._timeline.interval_exceeded(previous[4]):
                        self._previous = (times[0], times[1], now_ns, count, self._timeline._started_elapsed_ns)
                        self._cached = _unavailable_capacity(ResourceKind.CPU, now_ns, "windows:GetSystemTimes", "CPU_BASELINE_REQUIRED", sequence)
                    else:
                        elapsed, idle = times[0] - previous[0], times[1] - previous[1]
                        if elapsed <= 0 or idle < 0 or idle > elapsed:
                            # Corrupt/nonadvancing frames cannot become the next baseline.
                            self._previous = None
                            self._cached = _unavailable_capacity(ResourceKind.CPU, now_ns, "windows:GetSystemTimes", "CPU_COUNTER_DELTA_INVALID", sequence)
                        else:
                            self._previous = (times[0], times[1], now_ns, count, self._timeline._started_elapsed_ns)
                            available_milli = idle * count * 1000 // elapsed
                            utilization = 1000 - (available_milli * 1000 // (count * 1000))
                            self._cached = _capacity(ResourceKind.CPU, count * 1000, available_milli,
                                max(0, available_milli - self._policy.control_cpu_milli), utilization,
                                now_ns, "windows:GetSystemTimes", sequence)
                self._timeline.publish()
                return self._cached
            except BaseException:
                # Invalid clocks and process-control interruption invalidate any
                # derived baseline; KeyboardInterrupt/SystemExit still propagate.
                self._previous, self._cached = None, None
                raise

    def _read_counters(self):
        count = self._processor_count()
        if os.name != "nt" or type(count) is not int or not 1 <= count <= _MAX_QUANTITY // 1000:
            return None, None, "CPU_QUERY_UNAVAILABLE"
        if self._native_reader and self._native_processor_scope() != (1, count):
            return None, None, "CPU_PROCESSOR_GROUP_SCOPE_UNAVAILABLE"
        times = self._system_times_reader()
        if times is None:
            return None, None, "CPU_QUERY_FAILED"
        if type(times) is not tuple or len(times) != 2 or any(type(value) is not int for value in times) \
                or not 0 <= times[0] <= (1 << 65) - 2 or not 0 <= times[1] <= (1 << 64) - 1 \
                or times[1] > times[0]:
            return None, None, "CPU_QUERY_INVALID"
        final_count = self._processor_count()
        if type(final_count) is not int or final_count != count \
                or self._native_reader and self._native_processor_scope() != (1, count):
            return None, None, "CPU_PROCESSOR_SCOPE_CHANGED"
        return times, count, None

    @staticmethod
    def _native_processor_scope() -> tuple[int, int] | None:
        """GetSystemTimes is global only when exactly one group is observed."""
        if os.name != "nt":
            return None
        try:
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            groups = kernel.GetActiveProcessorGroupCount
            groups.argtypes, groups.restype = (), ctypes.c_ushort
            count = kernel.GetActiveProcessorCount
            count.argtypes, count.restype = (ctypes.c_ushort,), ctypes.c_ulong
            group_count = int(groups())
            if group_count != 1:
                return None
            processors = int(count(0))
            return (group_count, processors) if 1 <= processors <= 64 else None
        except (AttributeError, OSError):
            return None

    @staticmethod
    def _system_times() -> tuple[int, int] | None:
        class FileTime(ctypes.Structure):
            _fields_ = [("dwLowDateTime", ctypes.c_ulong), ("dwHighDateTime", ctypes.c_ulong)]
        idle, kernel, user = FileTime(), FileTime(), FileTime()
        try:
            query = ctypes.WinDLL("kernel32", use_last_error=True).GetSystemTimes
            query.argtypes, query.restype = (ctypes.POINTER(FileTime),) * 3, ctypes.c_int
            ok = query(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user))
        except (AttributeError, OSError):
            return None
        if not ok:
            return None
        def value(item: FileTime) -> int:
            return (int(item.dwHighDateTime) << 32) | int(item.dwLowDateTime)
        idle_value, kernel_value, user_value = value(idle), value(kernel), value(user)
        if idle_value > kernel_value:
            return None
        return kernel_value + user_value, idle_value


class StorageCapacityMonitor:
    def __init__(self, *, path: Path | None = None, clock=time.monotonic_ns,
                 policy: SamplingPolicy = SamplingPolicy(), disk_usage=shutil.disk_usage) -> None:
        require((path is None or isinstance(path, Path)) and callable(clock) and callable(disk_usage)
                and type(policy) is SamplingPolicy, "RESOURCE_STORAGE_MONITOR_INPUT_INVALID")
        self._path = (Path.cwd() if path is None else path).absolute()
        self._timeline, self._policy, self._disk_usage = _ObservationClock(clock, policy), policy, disk_usage
        self._cached: CapacitySnapshot | None = None
        self._sequence = 0
        self._lock = threading.Lock()

    def sample(self) -> CapacitySnapshot:
        with self._lock:
            try:
                now_ns, reason = self._timeline.begin()
                if reason is None and self._cached is not None and self._timeline.cache_is_recent(self._cached, now_ns) \
                        and self._timeline.minimum_interval_pending(self._cached, now_ns):
                    return self._cached
                require(self._sequence < _MAX_QUANTITY, "RESOURCE_SEQUENCE_EXHAUSTED")
                self._sequence += 1
                sequence = self._sequence
                if reason is None:
                    try:
                        result = _storage_capacity(self._disk_usage(self._path), now_ns, sequence, self._policy)
                    except Exception:
                        result = _unavailable_capacity(ResourceKind.STORAGE, now_ns, "python:shutil.disk_usage", "STORAGE_QUERY_FAILED", sequence)
                    ended_ns, reason = self._timeline.finish(now_ns)
                else:
                    ended_ns = now_ns
                self._cached = (_unavailable_capacity(ResourceKind.STORAGE, ended_ns, "python:shutil.disk_usage", reason, sequence)
                                if reason is not None else result)
                self._timeline.publish()
                return self._cached
            except BaseException:
                self._cached = None
                raise


def available_capacity(snapshot: CapacitySnapshot, reservations: ResourceVector, now_ns: int,
                       maximum_age_ns: int) -> int | None:
    """Return only this snapshot's usable quantity, never invented dimensions."""
    require(type(snapshot) is CapacitySnapshot and type(reservations) is ResourceVector,
            "RESOURCE_CAPACITY_INPUT_INVALID")
    if not snapshot.is_recent(now_ns, maximum_age_ns) or not snapshot.reservable.measured:
        return None
    if snapshot.kind is ResourceKind.CPU:
        return max(0, snapshot.reservable.value - reservations.cpu_milli)
    if snapshot.kind is ResourceKind.MEMORY:
        return max(0, snapshot.reservable.value - reservations.memory_bytes)
    if snapshot.kind is ResourceKind.STORAGE:
        return max(0, snapshot.reservable.value - reservations.storage_bytes)
    return None

