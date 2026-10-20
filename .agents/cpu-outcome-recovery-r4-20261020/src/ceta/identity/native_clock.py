"""Trusted-composition Windows session clock; no issuer, epoch reset or UTC attestation.

The system wall is an explicit trusted-host assumption. Boot information class90
is an empirically checked native x64 ABI, not a documented portable guarantee.
Existing unqualified owners remain closed. A model/worker must never construct
this provider or supply its canonical-owner durable epoch. Native calls cannot
be preempted by Python deadlines; overlong returns are rejected with custody kept.
"""
import ctypes as C
from ctypes import wintypes as W
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import secrets
import threading
import time
import uuid

from ceta.contracts.temporal import ClockSample
from ceta.contracts.wire import ContractError, MIN_INTEGER, MAX_INTEGER

NS = 1_000_000_000
FILETIME_UNIX_OFFSET = 116_444_736_000_000_000
BOOT_INFORMATION_CLASS = 90
BOOT_PROFILE = 'EMPIRICALLY_OBSERVED_NATIVE_ABI'
WALL_ASSUMPTION = 'TRUSTED_HOST_SYSTEM_WALL_NO_EXTERNAL_UTC_ATTESTATION'
PLATFORM_QUALIFICATION = 'CETA-NC3-WINDOWS-10.0.26300-20261015'
_NC1_WINDOWS_VERSION = (10, 0, 26300)
_NC1_SYSTEM_DLL_SHA256 = (
    ('kernel32.dll', 'e132eba4166256e2f414b91fe7d5386590bc5ea8626aee5af9c9738383cf2ae1'),
    ('ntdll.dll', '651ac9041af8e6b5ebd331d53163244c0a27d36d1433f0f15cac1f28c5f2e82c'),
    ('powrprof.dll', '096b3c77ad7fece122be0362c72530b1edc024fe7107d1d40d8bcd8fa5428a0e'),
    ('kernelbase.dll', '5c29b73622ce0976e1ada566f31f2197ba0f8beaea89c3ec033366126172c3d0'),
)


def _require(condition, code):
    if not condition:
        raise ContractError(code)


def _integer(value, minimum=0, maximum=MAX_INTEGER):
    _require(type(value) is int and minimum <= value <= maximum, 'CLOCK_INTEGER_INVALID')
    return value


def _ceil(value, divisor):
    return (value + divisor - 1) // divisor


class NativeClockUnavailable(ContractError):
    def __init__(self, code, *, native_status=None):
        super().__init__(code)
        self.native_status = native_status


@dataclass(frozen=True, slots=True)
class ClockBounds:
    sampling_interval_ns: int = 50_000_000
    maximum_gap_ns: int = 2_000_000_000
    maximum_acquisition_ns: int = 50_000_000
    sleep_tolerance_ns: int = 50_000_000
    maximum_wall_drift_ns: int = 100_000_000
    close_timeout_ns: int = 2_000_000_000

    def __post_init__(self):
        for value in (self.sampling_interval_ns, self.maximum_gap_ns,
                      self.maximum_acquisition_ns, self.sleep_tolerance_ns,
                      self.maximum_wall_drift_ns, self.close_timeout_ns):
            _integer(value, 1_000_000, 10 * NS)
        _require(self.sampling_interval_ns < self.maximum_gap_ns
                 and self.maximum_acquisition_ns < self.maximum_gap_ns,
                 'CLOCK_BOUNDS_INVALID')


class _BootEnvironment(C.Structure):
    _fields_ = [('guid', C.c_ubyte * 16), ('firmware_type', W.ULONG),
                ('boot_flags', C.c_uint64)]


class _Version(C.Structure):
    _fields_ = [('size', W.ULONG), ('major', W.ULONG), ('minor', W.ULONG),
                ('build', W.ULONG), ('platform', W.ULONG), ('service_pack', W.WCHAR * 128)]


_PowerCallback = C.WINFUNCTYPE(W.ULONG, C.c_void_p, W.ULONG, C.c_void_p)


class _PowerSubscription(C.Structure):
    _fields_ = [('callback', _PowerCallback), ('context', C.c_void_p)]


@dataclass(frozen=True, slots=True)
class NativeClockPlatform:
    windows_version: tuple[int, int, int]
    dll_sha256: tuple[tuple[str, str], ...]
    boot_profile: str
    boot_structure_bytes: int
    subscription_bytes: int
    wall_assumption: str


@dataclass(frozen=True, slots=True)
class _NativeFrame:
    boot_guid: str
    boot_guid_after: str
    boot_return_length: int
    firmware_type: int
    qpc_frequency: int
    qpc_start: int
    qpc_end: int
    wall_start_ns: int
    wall_end_ns: int
    interrupt_start_ns: int
    interrupt_end_ns: int
    unbiased_start_ns: int
    unbiased_end_ns: int
    resolution_ns: int


class _NativeClockAPI:
    def __init__(self):
        _require(os.name == 'nt' and C.sizeof(C.c_void_p) == 8, 'CLOCK_WINDOWS_X64_REQUIRED')
        _require(C.sizeof(_BootEnvironment) == 32 and _BootEnvironment.boot_flags.offset == 24
                 and C.sizeof(_PowerSubscription) == 16 and C.sizeof(_Version) == 276,
                 'CLOCK_NATIVE_ABI_UNSUPPORTED')
        self.kernel = C.WinDLL('kernel32', use_last_error=True, winmode=0x800)
        self.ntdll = C.WinDLL('ntdll', use_last_error=True, winmode=0x800)
        self.power = C.WinDLL('powrprof', use_last_error=True, winmode=0x800)
        # Installed realtimeapiset.h declares the precise-time contract. On
        # this host it resolves to System32 KernelBase, not a Kernel32 export.
        self.realtime = C.WinDLL('api-ms-win-core-realtime-l1-1-2', use_last_error=True, winmode=0x800)
        declarations = {
            'QueryPerformanceCounter': (self.kernel, [C.POINTER(C.c_int64)], W.BOOL),
            'QueryPerformanceFrequency': (self.kernel, [C.POINTER(C.c_int64)], W.BOOL),
            'GetSystemTimePreciseAsFileTime': (self.kernel, [C.POINTER(W.FILETIME)], None),
            'QueryInterruptTimePrecise': (self.realtime, [C.POINTER(C.c_uint64)], None),
            'QueryUnbiasedInterruptTimePrecise': (self.realtime, [C.POINTER(C.c_uint64)], None),
            'GetSystemTimeAdjustment': (self.kernel, [C.POINTER(W.DWORD), C.POINTER(W.DWORD), C.POINTER(W.BOOL)], W.BOOL),
            'GetSystemDirectoryW': (self.kernel, [W.LPWSTR, W.UINT], W.UINT),
            'GetModuleFileNameW': (self.kernel, [W.HMODULE, W.LPWSTR, W.DWORD], W.DWORD),
            'NtQuerySystemInformation': (self.ntdll, [W.ULONG, C.c_void_p, W.ULONG, C.POINTER(W.ULONG)], C.c_int32),
            'RtlGetVersion': (self.ntdll, [C.POINTER(_Version)], C.c_int32),
            'PowerRegisterSuspendResumeNotification': (self.power, [W.DWORD, C.c_void_p, C.POINTER(W.HANDLE)], W.DWORD),
            'PowerUnregisterSuspendResumeNotification': (self.power, [W.HANDLE], W.DWORD),
        }
        for name, (dll, arguments, result) in declarations.items():
            try:
                function = getattr(dll, name)
            except AttributeError as error:
                raise NativeClockUnavailable('CLOCK_NATIVE_API_UNAVAILABLE') from error
            function.argtypes, function.restype = arguments, result
            setattr(self, name, function)
        system = C.create_unicode_buffer(32768)
        size = self.GetSystemDirectoryW(system, len(system))
        _require(0 < size < len(system), 'CLOCK_SYSTEM_DIRECTORY_UNAVAILABLE')
        images = []
        for name, dll in (('kernel32.dll', self.kernel), ('ntdll.dll', self.ntdll),
                          ('powrprof.dll', self.power), ('kernelbase.dll', self.realtime)):
            buffer = C.create_unicode_buffer(32768)
            size = self.GetModuleFileNameW(dll._handle, buffer, len(buffer))
            expected = Path(system.value) / name
            _require(0 < size < len(buffer) and os.path.normcase(buffer.value) == os.path.normcase(str(expected)),
                     'CLOCK_SYSTEM_IMAGE_PATH_MISMATCH')
            with expected.open('rb') as stream:
                image_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
            images.append((name, image_hash))
        version = _Version()
        version.size = C.sizeof(version)
        status = self.RtlGetVersion(C.byref(version))
        _require(status == 0 and version.major == 10, 'CLOCK_NATIVE_OS_UNSUPPORTED')
        self.platform = NativeClockPlatform((version.major, version.minor, version.build),
            tuple(images), BOOT_PROFILE, C.sizeof(_BootEnvironment), C.sizeof(_PowerSubscription), WALL_ASSUMPTION)
        _require(self.platform.windows_version == _NC1_WINDOWS_VERSION
                 and self.platform.dll_sha256 == _NC1_SYSTEM_DLL_SHA256,
                 'CLOCK_NATIVE_PLATFORM_PIN_MISMATCH')

    def _qpc(self):
        value = C.c_int64(-1)
        if not self.QueryPerformanceCounter(C.byref(value)) or value.value < 0:
            raise NativeClockUnavailable('CLOCK_QPC_UNAVAILABLE', native_status=C.get_last_error())
        return value.value

    def _boot(self):
        value, size = _BootEnvironment(), W.ULONG()
        status = self.NtQuerySystemInformation(BOOT_INFORMATION_CLASS, C.byref(value), C.sizeof(value), C.byref(size))
        if status != 0 or size.value != C.sizeof(value) or not any(value.guid) or value.firmware_type not in (1, 2):
            raise NativeClockUnavailable('CLOCK_BOOT_WITNESS_UNAVAILABLE', native_status=status)
        return str(uuid.UUID(bytes_le=bytes(value.guid))), size.value, value.firmware_type

    def _wall(self):
        value = W.FILETIME()
        self.GetSystemTimePreciseAsFileTime(C.byref(value))
        ticks = value.dwHighDateTime << 32 | value.dwLowDateTime
        return _integer((ticks - FILETIME_UNIX_OFFSET) * 100, MIN_INTEGER)

    @staticmethod
    def _counter(function):
        value = C.c_uint64(2**64 - 1)
        function(C.byref(value))
        return _integer(value.value * 100)

    def acquire(self):
        q0 = self._qpc()
        frequency = C.c_int64(-1)
        if not self.QueryPerformanceFrequency(C.byref(frequency)) or frequency.value <= 0:
            raise NativeClockUnavailable('CLOCK_QPC_FREQUENCY_UNAVAILABLE', native_status=C.get_last_error())
        adjustment, increment, disabled = W.DWORD(), W.DWORD(), W.BOOL()
        if not self.GetSystemTimeAdjustment(C.byref(adjustment), C.byref(increment), C.byref(disabled)):
            raise NativeClockUnavailable('CLOCK_RESOLUTION_UNAVAILABLE', native_status=C.get_last_error())
        _require(0 < increment.value <= 10_000_000, 'CLOCK_RESOLUTION_UNAVAILABLE')
        boot0, length, firmware = self._boot()
        i0 = self._counter(self.QueryInterruptTimePrecise)
        u0 = self._counter(self.QueryUnbiasedInterruptTimePrecise)
        w0 = self._wall()
        w1 = self._wall()
        u1 = self._counter(self.QueryUnbiasedInterruptTimePrecise)
        i1 = self._counter(self.QueryInterruptTimePrecise)
        boot1, length1, firmware1 = self._boot()
        q1 = self._qpc()
        _require(length == length1 and firmware == firmware1, 'CLOCK_BOOT_WITNESS_CHANGED')
        return _NativeFrame(boot0, boot1, length, firmware, frequency.value, q0, q1,
                            w0, w1, i0, i1, u0, u1, max(1000, increment.value * 100))

    def register(self, subscription):
        handle = W.HANDLE()
        status = self.PowerRegisterSuspendResumeNotification(2, C.byref(subscription), C.byref(handle))
        if status != 0 or not handle.value:
            error = NativeClockUnavailable('CLOCK_POWER_REGISTRATION_UNAVAILABLE', native_status=status)
            error.registration = handle.value
            raise error
        return handle.value

    def unregister(self, handle):
        status = self.PowerUnregisterSuspendResumeNotification(handle)
        if status != 0:
            raise NativeClockUnavailable('CLOCK_POWER_UNREGISTER_UNRESOLVED', native_status=status)


@dataclass(frozen=True, slots=True)
class NativeClockStatus:
    state: str
    reason: str | None
    session_nonce: str
    boot_guid: str | None
    durable_epoch: int
    resume_generation: int
    accepted_sequence: int
    registration_owned: bool
    callbacks_active: int
    sampler_alive: bool
    sampler_native_id: int | None
    platform: NativeClockPlatform


class NativeSessionClock:
    def __init__(self, durable_epoch: int, *, bounds: ClockBounds = ClockBounds()):
        _integer(durable_epoch)
        _require(type(bounds) is ClockBounds, 'CLOCK_BOUNDS_REQUIRED')
        self._bounds, self._epoch = bounds, durable_epoch
        self._session = secrets.token_hex(16)
        self._condition = threading.Condition(threading.RLock())
        self._measure_lock, self._close_lock = threading.Lock(), threading.Lock()
        self._stop = threading.Event()
        self._state, self._reason = 'STARTING', None
        self._resume, self._sequence, self._callbacks = 0, 0, 0
        self._last, self._frame, self._thread = None, None, None
        self._registration = None
        try:
            self._api = _NativeClockAPI()
        except OSError as error:
            raise NativeClockUnavailable('CLOCK_NATIVE_PLATFORM_UNAVAILABLE',
                native_status=getattr(error, 'winerror', None)) from error
        self._callback = _PowerCallback(self._on_power)
        self._subscription = _PowerSubscription(self._callback, None)
        try:
            self._registration = self._api.register(self._subscription)
            with self._condition:
                if self._reason is None:
                    self._state = 'ACTIVE'
            self._take_sample()
            self._thread = threading.Thread(target=self._sample_loop,
                name='CETA-native-clock-' + self._session[:12], daemon=False)
            self._thread.start()
        except BaseException as primary:
            if self._registration is None:
                self._registration = getattr(primary, 'registration', None)
            try:
                self.close()
            except BaseException:
                try:
                    primary.add_note('Native clock cleanup unresolved; exact callback/thread owner retained.')
                except BaseException:
                    pass
                # Retain after diagnostics, bypassing subclass setters/accessors
                # through BaseException's own exact recovery dictionary.
                BaseException.__dict__['__dict__'].__get__(primary)['clock_custody'] = self
            raise

    def _latch_locked(self, reason):
        if self._reason is None:
            self._reason = reason
        if self._state not in ('CLOSING', 'CLOSED'):
            self._state = 'LATCHED'
        self._stop.set()
        self._condition.notify_all()

    def _on_power(self, context, event, setting):
        # Called by Windows: no native read, user callback, authority or store call.
        try:
            with self._condition:
                self._callbacks += 1
                try:
                    if self._state != 'CLOSED':
                        self._resume += 1
                        self._latch_locked('CLOCK_POWER_TRANSITION' if event in (4, 7, 18)
                                           else 'CLOCK_POWER_WITNESS_INVALID')
                finally:
                    self._callbacks -= 1
                    self._condition.notify_all()
        except BaseException:
            # Exceptions cannot safely cross the native callback ABI.
            self._stop.set()
            self._reason = self._reason or 'CLOCK_CALLBACK_FAILURE'
        return 0

    def _open_locked(self):
        if self._state != 'ACTIVE' or self._reason is not None or self._registration is None:
            raise NativeClockUnavailable(self._reason or 'CLOCK_SESSION_CLOSED')

    def _derive_locked(self, frame, acquisition_ns):
        _require(type(frame) is _NativeFrame, 'CLOCK_NATIVE_FRAME_INVALID')
        for name in ('qpc_frequency', 'qpc_start', 'qpc_end', 'interrupt_start_ns', 'interrupt_end_ns',
                     'unbiased_start_ns', 'unbiased_end_ns', 'resolution_ns', 'boot_return_length', 'firmware_type'):
            _integer(getattr(frame, name))
        _integer(frame.wall_start_ns, MIN_INTEGER)
        _integer(frame.wall_end_ns, MIN_INTEGER)
        _require(type(frame.boot_guid) is str and type(frame.boot_guid_after) is str
                 and frame.boot_guid == str(uuid.UUID(frame.boot_guid))
                 and uuid.UUID(frame.boot_guid).int != 0 and frame.boot_guid_after == frame.boot_guid
                 and frame.boot_return_length == 32 and frame.firmware_type in (1, 2),
                 'CLOCK_BOOT_WITNESS_UNAVAILABLE')
        _require(frame.qpc_frequency > 0 and 1000 <= frame.resolution_ns <= NS,
                 'CLOCK_NATIVE_FRAME_INVALID')
        _require(frame.qpc_end >= frame.qpc_start
                 and frame.interrupt_end_ns >= frame.interrupt_start_ns
                 and frame.unbiased_end_ns >= frame.unbiased_start_ns,
                 'CLOCK_MONOTONIC_ROLLBACK')
        _require(frame.wall_end_ns >= frame.wall_start_ns, 'CLOCK_WALL_ROLLBACK')
        start = frame.qpc_start * NS // frame.qpc_frequency
        end = _ceil(frame.qpc_end * NS, frame.qpc_frequency)
        span = end - start
        _require(span <= self._bounds.maximum_acquisition_ns, 'CLOCK_ACQUISITION_TOO_SLOW')
        quantum = _ceil(NS, frame.qpc_frequency)
        tolerance = 2 * frame.resolution_ns + span
        _require(abs((frame.interrupt_end_ns - frame.interrupt_start_ns)
                     - (frame.unbiased_end_ns - frame.unbiased_start_ns)) <= tolerance,
                 'CLOCK_SLEEP_DISCONTINUITY')
        wall = (frame.wall_start_ns + frame.wall_end_ns) // 2
        uncertainty = (_ceil(frame.wall_end_ns - frame.wall_start_ns, 2) + span
                       + acquisition_ns + frame.resolution_ns + quantum)
        monotonic = (start + end) // 2
        if self._frame is not None:
            old = self._frame
            _require(frame.boot_guid == old.boot_guid, 'CLOCK_BOOT_CHANGED')
            _require(frame.qpc_frequency == old.qpc_frequency and frame.resolution_ns == old.resolution_ns,
                     'CLOCK_CALIBRATION_CHANGED')
            _require(frame.qpc_start >= old.qpc_end
                     and frame.interrupt_start_ns >= old.interrupt_end_ns
                     and frame.unbiased_start_ns >= old.unbiased_end_ns,
                     'CLOCK_MONOTONIC_ROLLBACK')
            _require(frame.qpc_end > old.qpc_end, 'CLOCK_STALE_SAMPLE')
            gap = _ceil((frame.qpc_start - old.qpc_end) * NS, frame.qpc_frequency)
            _require(gap <= self._bounds.maximum_gap_ns, 'CLOCK_SAMPLING_GAP')
            _require(frame.wall_end_ns >= old.wall_start_ns, 'CLOCK_WALL_ROLLBACK')
            biased = frame.interrupt_start_ns - old.interrupt_end_ns
            active = frame.unbiased_start_ns - old.unbiased_end_ns
            tolerance += 2 * old.resolution_ns + self._last.uncertainty_ns
            _require(abs(biased - active) <= self._bounds.sleep_tolerance_ns + tolerance,
                     'CLOCK_SLEEP_DISCONTINUITY')
            _require(abs(gap - biased) <= self._bounds.sleep_tolerance_ns + tolerance,
                     'CLOCK_WITNESS_DISCONTINUITY')
            wall_gap = frame.wall_start_ns - old.wall_end_ns
            _require(abs(wall_gap - gap) <= self._bounds.maximum_wall_drift_ns + tolerance,
                     'CLOCK_WALL_DISCONTINUITY')
        sample = ClockSample('boot:' + frame.boot_guid + ':session:' + self._session,
            self._epoch, self._resume, _integer(monotonic), wall, _integer(uncertainty), True)
        previous = self._last or sample
        self._frame, self._last = frame, sample
        self._sequence += 1
        return previous, sample

    def _take_sample(self):
        if not self._measure_lock.acquire(timeout=self._bounds.maximum_acquisition_ns / NS):
            with self._condition:
                self._latch_locked('CLOCK_SAMPLE_BUSY')
            raise NativeClockUnavailable('CLOCK_SAMPLE_BUSY')
        try:
            with self._condition:
                self._open_locked()
                generation = self._resume
            probe_start = time.monotonic_ns()
            frame = self._api.acquire()
            with self._condition:
                self._open_locked()
                _require(generation == self._resume, 'CLOCK_POWER_TRANSITION')
                acquisition = time.monotonic_ns() - probe_start
                # A reentrant notification during the final local clock read
                # must win before pure sample validation/publication begins.
                self._open_locked()
                _require(generation == self._resume, 'CLOCK_POWER_TRANSITION')
                _require(acquisition >= 0, 'CLOCK_MONOTONIC_ROLLBACK')
                _require(acquisition <= self._bounds.maximum_acquisition_ns, 'CLOCK_ACQUISITION_TOO_SLOW')
                return self._derive_locked(frame, acquisition)
        except (ContractError, OSError, ValueError, TypeError) as error:
            code = error.code if isinstance(error, ContractError) else 'CLOCK_NATIVE_READ_UNAVAILABLE'
            with self._condition:
                self._latch_locked(code)
            if isinstance(error, NativeClockUnavailable):
                raise
            raise NativeClockUnavailable(code) from error
        except BaseException:
            with self._condition:
                self._latch_locked('CLOCK_CONTROL_INTERRUPTION')
            raise
        finally:
            self._measure_lock.release()

    def _sample_loop(self):
        while not self._stop.wait(self._bounds.sampling_interval_ns / NS):
            try:
                self._take_sample()
            except BaseException:
                # _take_sample retained the first failure and invalidated session.
                return

    def clock(self) -> tuple[ClockSample, ClockSample]:
        """Fresh serialized native pair; previous samples are owner-retained only."""
        return self._take_sample()

    def status(self):
        with self._condition:
            thread = self._thread
            return NativeClockStatus(self._state, self._reason, self._session,
                self._frame.boot_guid if self._frame else None, self._epoch,
                self._resume, self._sequence, self._registration is not None,
                self._callbacks, bool(thread and thread.is_alive()),
                thread.native_id if thread else None, self._api.platform)

    def close(self):
        timeout = self._bounds.close_timeout_ns
        end = time.monotonic_ns() + timeout
        if not self._close_lock.acquire(timeout=timeout / NS):
            raise NativeClockUnavailable('CLOCK_CLOSE_BUSY')
        try:
            with self._condition:
                if self._state == 'CLOSED':
                    return
                self._state = 'CLOSING'
                self._stop.set()
            # Never hold callback lock across native unregistration or join.
            if self._registration is not None:
                self._api.unregister(self._registration)
                self._registration = None
            thread = self._thread
            if thread is threading.current_thread():
                raise NativeClockUnavailable('CLOCK_CLOSE_ON_SAMPLER')
            if thread is not None and thread.ident is not None:
                thread.join(max(0, end - time.monotonic_ns()) / NS)
                if thread.is_alive():
                    raise NativeClockUnavailable('CLOCK_SAMPLER_RETIREMENT_UNRESOLVED')
            remaining = max(0, end - time.monotonic_ns()) / NS
            if not self._measure_lock.acquire(timeout=remaining):
                raise NativeClockUnavailable('CLOCK_PROBE_RETIREMENT_UNRESOLVED')
            self._measure_lock.release()
            with self._condition:
                while self._callbacks:
                    remaining = end - time.monotonic_ns()
                    if remaining <= 0:
                        raise NativeClockUnavailable('CLOCK_CALLBACK_RETIREMENT_UNRESOLVED')
                    self._condition.wait(remaining / NS)
                _require(time.monotonic_ns() <= end, 'CLOCK_CLOSE_TOO_SLOW')
                self._state = 'CLOSED'
                # Keep callback/subscription objects reachable for this owner's
                # lifetime, even after Windows canceled the registration.
                self._condition.notify_all()
        finally:
            self._close_lock.release()
