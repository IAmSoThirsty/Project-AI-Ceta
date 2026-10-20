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


@dataclass(frozen=True, slots=True)
class SamplingPolicy:
    maximum_age_ns: int = 30_000_000_000
    minimum_interval_ns: int = 100_000_000
    control_cpu_milli: int = 50
    control_memory_bytes: int = 64 * 1024 * 1024
    control_storage_bytes: int = 64 * 1024 * 1024

    def __post_init__(self) -> None:
        require(type(self.maximum_age_ns) is int and 1 <= self.maximum_age_ns <= 300_000_000_000
                and type(self.minimum_interval_ns) is int and 1 <= self.minimum_interval_ns <= self.maximum_age_ns,
                "RESOURCE_MAXIMUM_AGE_INVALID")
        for value in (self.control_cpu_milli, self.control_memory_bytes, self.control_storage_bytes):
            require(type(value) is int and value >= 0, "RESOURCE_CONTROL_RESERVE_INVALID")


class WindowsHardwareProfiler:
    """Native local observations with no subprocesses or capacity guesses."""
    def __init__(self, *, clock=time.monotonic_ns, storage_path: Path | None = None,
                 policy: SamplingPolicy = SamplingPolicy(), accelerator_memory_reader=None) -> None:
        require(callable(clock) and type(policy) is SamplingPolicy
                and (accelerator_memory_reader is None or callable(accelerator_memory_reader)),
                "RESOURCE_HARDWARE_PROFILER_INPUT_INVALID")
        self._clock, self._path, self._policy = clock, storage_path or Path.cwd(), policy
        self._accelerator_memory_reader = accelerator_memory_reader or self._dedicated_video_memory
        self._sequence = 0
        self._lock = threading.Lock()

    def profile(self, profile_id: str) -> HardwareProfile:
        # Reject an invalid caller-supplied identity before asking Windows or
        # the filesystem for any observation.  The resulting profile still
        # validates this field at construction as a defense in depth.
        identifier(profile_id, "RESOURCE_PROFILE_IDENTIFIER_INVALID")
        with self._lock:
            self._sequence += 1
            sequence = self._sequence
        now_ns = self._clock()
        cpu_total = os.cpu_count()
        # Logical processor count is a physical capability, never a claim that
        # those units are currently free.  WindowsComputeAvailabilityMonitor
        # supplies an actual availability measurement separately.
        cpu = (_hardware_cpu_capacity(cpu_total * 1000, now_ns, "windows:os.cpu_count", sequence)
               if type(cpu_total) is int and cpu_total > 0 else
               _unavailable_capacity(ResourceKind.CPU, now_ns, "windows:os.cpu_count", "CPU_COUNT_UNAVAILABLE", sequence))
        memory = self._memory(now_ns, sequence)
        storage = self._storage(now_ns, sequence)
        accelerators = self._accelerators(now_ns, sequence)
        isolation = self._isolation(now_ns)
        return HardwareProfile(profile_id, cpu, memory, storage, accelerators, isolation, now_ns,
                               platform.system() + ":" + platform.release())

    def _accelerators(self, now_ns: int, sequence: int) -> tuple[CapacitySnapshot, ...]:
        method = "windows:DXGI.EnumAdapters:GetDesc"
        if os.name != "nt":
            return (_unavailable_capacity(ResourceKind.ACCELERATOR, now_ns, method, "WINDOWS_REQUIRED", sequence),)
        try:
            memories = self._accelerator_memory_reader()
        except Exception:
            return (_unavailable_capacity(ResourceKind.ACCELERATOR, now_ns, method, "ACCELERATOR_QUERY_FAILED", sequence),)
        if type(memories) is not tuple or len(memories) > 16 or any(type(value) is not int or value < 0 for value in memories):
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
            ok = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
        except (AttributeError, OSError):
            ok = False
        if not ok:
            return _unavailable_capacity(ResourceKind.MEMORY, now_ns, "windows:GlobalMemoryStatusEx", "MEMORY_QUERY_FAILED", sequence)
        return _capacity(ResourceKind.MEMORY, int(status.ullTotalPhys), int(status.ullAvailPhys),
                         max(0, int(status.ullAvailPhys) - self._policy.control_memory_bytes),
                         int(status.dwMemoryLoad) * 10, now_ns, "windows:GlobalMemoryStatusEx", sequence)

    def _storage(self, now_ns: int, sequence: int) -> CapacitySnapshot:
        try:
            usage = shutil.disk_usage(self._path)
        except OSError:
            return _unavailable_capacity(ResourceKind.STORAGE, now_ns, "python:shutil.disk_usage", "STORAGE_QUERY_FAILED", sequence)
        utilization = 0 if usage.total == 0 else ((usage.total - usage.free) * 1000) // usage.total
        return _capacity(ResourceKind.STORAGE, usage.total, usage.free,
                         max(0, usage.free - self._policy.control_storage_bytes), utilization, now_ns,
                         "python:shutil.disk_usage", sequence)

    @staticmethod
    def _isolation(now_ns: int) -> QuantityObservation:
        if os.name != "nt":
            return _unavailable(now_ns, "windows:IsProcessInJob", "WINDOWS_REQUIRED")
        flag = ctypes.c_int()
        try:
            ok = ctypes.windll.kernel32.IsProcessInJob(ctypes.windll.kernel32.GetCurrentProcess(), None, ctypes.byref(flag))
        except (AttributeError, OSError):
            return _unavailable(now_ns, "windows:IsProcessInJob", "ISOLATION_QUERY_FAILED")
        if not ok:
            return _unavailable(now_ns, "windows:IsProcessInJob", "ISOLATION_QUERY_FAILED")
        return _measured(int(bool(flag.value)), now_ns, "windows:IsProcessInJob")


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
        self._clock, self._policy = clock, policy
        self._system_times_reader, self._processor_count = system_times or self._system_times, processor_count
        self._previous: tuple[int, int] | None = None
        self._sequence = 0
        self._cached: CapacitySnapshot | None = None
        self._lock = threading.Lock()

    def sample(self) -> CapacitySnapshot:
        now_ns = self._clock()
        with self._lock:
            if self._cached is not None and now_ns - self._cached.total.observed_monotonic_ns < self._policy.minimum_interval_ns:
                return self._cached
            self._sequence += 1
            sequence = self._sequence
            total_capacity = self._processor_count()
            if os.name != "nt" or type(total_capacity) is not int or total_capacity <= 0:
                self._cached = _unavailable_capacity(ResourceKind.CPU, now_ns, "windows:GetSystemTimes", "CPU_QUERY_UNAVAILABLE", sequence)
                return self._cached
            times = self._system_times_reader()
            if times is None:
                self._cached = _unavailable_capacity(ResourceKind.CPU, now_ns, "windows:GetSystemTimes", "CPU_QUERY_FAILED", sequence)
                return self._cached
            previous, self._previous = self._previous, times
            if previous is None or times[0] <= previous[0]:
                self._cached = _unavailable_capacity(ResourceKind.CPU, now_ns, "windows:GetSystemTimes", "CPU_BASELINE_REQUIRED", sequence)
                return self._cached
            elapsed, idle = times[0] - previous[0], times[1] - previous[1]
            available_milli = min(total_capacity * 1000, max(0, idle * total_capacity * 1000 // elapsed))
            utilization = 1000 - (available_milli * 1000 // (total_capacity * 1000))
            self._cached = _capacity(ResourceKind.CPU, total_capacity * 1000, available_milli,
                                     max(0, available_milli - self._policy.control_cpu_milli), utilization, now_ns,
                                     "windows:GetSystemTimes", sequence)
            return self._cached

    @staticmethod
    def _system_times() -> tuple[int, int] | None:
        class FileTime(ctypes.Structure):
            _fields_ = [("dwLowDateTime", ctypes.c_ulong), ("dwHighDateTime", ctypes.c_ulong)]
        idle, kernel, user = FileTime(), FileTime(), FileTime()
        try:
            ok = ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user))
        except (AttributeError, OSError):
            return None
        if not ok:
            return None
        def value(item: FileTime) -> int:
            return (int(item.dwHighDateTime) << 32) | int(item.dwLowDateTime)
        return value(kernel) + value(user), value(idle)


class StorageCapacityMonitor:
    def __init__(self, *, path: Path | None = None, clock=time.monotonic_ns,
                 policy: SamplingPolicy = SamplingPolicy(), disk_usage=shutil.disk_usage) -> None:
        self._path, self._clock, self._policy, self._disk_usage = path or Path.cwd(), clock, policy, disk_usage
        self._cached: CapacitySnapshot | None = None
        self._sequence = 0
        self._lock = threading.Lock()

    def sample(self) -> CapacitySnapshot:
        now_ns = self._clock()
        with self._lock:
            if self._cached is not None and now_ns - self._cached.total.observed_monotonic_ns < self._policy.minimum_interval_ns:
                return self._cached
            self._sequence += 1
            sequence = self._sequence
            try:
                usage = self._disk_usage(self._path)
            except OSError:
                self._cached = _unavailable_capacity(ResourceKind.STORAGE, now_ns, "python:shutil.disk_usage", "STORAGE_QUERY_FAILED", sequence)
                return self._cached
            utilization = 0 if usage.total == 0 else ((usage.total - usage.free) * 1000) // usage.total
            self._cached = _capacity(ResourceKind.STORAGE, usage.total, usage.free,
                                     max(0, usage.free - self._policy.control_storage_bytes), utilization, now_ns,
                                     "python:shutil.disk_usage", sequence)
            return self._cached


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

