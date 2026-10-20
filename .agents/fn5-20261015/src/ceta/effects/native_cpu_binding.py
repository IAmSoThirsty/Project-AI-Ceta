"""Observation-only bridge between one retained Windows job and NC2 time.

Driver observations keep their original GetTickCount64 timestamps. A distinct
native observation uses an actually measured QPC bracket. Returned arguments
are bounded data for the existing driver CAS, never authority to call Set.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import math
import os
import threading
import time
from types import MappingProxyType

from ceta.contracts.real_effect import OwnedCpuRequest, decode_owned_cpu_request
from ceta.contracts.resource_management import ObservationState, ProcessResourceIdentity
from ceta.contracts.temporal import ClockSample, require_clock_progress, require_deadline_current
from ceta.contracts.wire import ContractError, MAX_INTEGER, canonical_bytes
from ceta.contracts.workload_throttling import CpuRateLimit, CpuRateObservation
from ceta.identity.native_clock import NativeSessionClock
from ceta.supervisor.windows_jobs import WindowsOwnedProcess

DRIVER_DOMAIN = 'windows:GetTickCount64:python-monotonic-ns'
NATIVE_DOMAIN = 'windows:QueryPerformanceCounter:NC2-native-ns'


def _require(value, code):
    if not value: raise ContractError(code)


def _integer(value, minimum=0, maximum=MAX_INTEGER):
    _require(type(value) is int and minimum <= value <= maximum, 'CPU_BINDING_INTEGER_INVALID')
    return value


def _sample(value):
    _require(type(value) is ClockSample, 'CPU_BINDING_NATIVE_CLOCK_REQUIRED')
    return ClockSample(value.boot_id, value.durable_epoch, value.resume_generation,
        value.monotonic_ns, value.wall_time_ns, value.uncertainty_ns, value.wall_trusted)


def _observation(value):
    _require(type(value) is CpuRateObservation, 'CPU_BINDING_DRIVER_OBSERVATION_REQUIRED')
    value.__post_init__()
    identity = value.identity
    return CpuRateObservation(ProcessResourceIdentity(identity.pid, identity.creation_time, identity.image_digest),
        value.job_digest, value.state, None if value.limit is None else
        CpuRateLimit(value.limit.control_flags, value.limit.value), value.version,
        value.observed_monotonic_ns, value.reason)


def _observation_value(value):
    value = _observation(value)
    return dict(identity=dict(pid=value.identity.pid,creation_time=value.identity.creation_time,
        image_digest=value.identity.image_digest),job_digest=value.job_digest,state=value.state.value,
        limit=None if value.limit is None else dict(control_flags=value.limit.control_flags,value=value.limit.value),
        version=value.version,observed_monotonic_ns=value.observed_monotonic_ns,reason=value.reason)


@dataclass(frozen=True, slots=True)
class NativeCpuCapture:
    observation: CpuRateObservation
    native_before: ClockSample
    native_after: ClockSample
    original_driver_timestamp_ns: int
    driver_bracket_start_ns: int
    driver_bracket_end_ns: int
    driver_resolution_ns: int
    elapsed_resolution_ns: int
    acquisition_ns: int
    sequence: int
    driver_domain: str = DRIVER_DOMAIN
    native_domain: str = NATIVE_DOMAIN


def _capture_wire(value):
    _require(type(value) is NativeCpuCapture, 'CPU_BINDING_CAPTURE_REQUIRED')
    before, after = _sample(value.native_before), _sample(value.native_after)
    require_clock_progress(before, after)
    integers = {name:_integer(getattr(value,name),1 if name in ('sequence','driver_resolution_ns',
        'elapsed_resolution_ns','acquisition_ns') else 0) for name in (
        'original_driver_timestamp_ns','driver_bracket_start_ns','driver_bracket_end_ns',
        'driver_resolution_ns','elapsed_resolution_ns','acquisition_ns','sequence')}
    _require(type(value.driver_domain) is str and value.driver_domain == DRIVER_DOMAIN
        and type(value.native_domain) is str and value.native_domain == NATIVE_DOMAIN,
        'CPU_BINDING_DOMAIN_CHANGED')
    return canonical_bytes(dict(observation=_observation_value(value.observation),
        before=vars(before),after=vars(after),**integers,driver_domain=DRIVER_DOMAIN,native_domain=NATIVE_DOMAIN))


@dataclass(frozen=True, slots=True)
class CpuDriverArguments:
    identity: ProcessResourceIdentity
    expected: CpuRateObservation
    deadline_monotonic_ns: int
    maximum_age_ns: int
    maximum_duration_ns: int
    capture_sequence: int
    request_commitment: str
    driver_domain: str = DRIVER_DOMAIN

    @property
    def keyword_arguments(self):
        return MappingProxyType(dict(deadline_monotonic_ns=self.deadline_monotonic_ns,
            maximum_age_ns=self.maximum_age_ns,maximum_duration_ns=self.maximum_duration_ns))


@dataclass(frozen=True, slots=True)
class _Measurement:
    original: CpuRateObservation
    before: ClockSample
    after: ClockSample
    driver_start: int
    driver_end: int
    native_lower: int
    native_upper: int
    offset_low: int
    offset_high: int
    acquisition: int
    elapsed_end: int


@dataclass(frozen=True, slots=True)
class _RetainedCapture:
    public: NativeCpuCapture
    public_wire: bytes
    measurement: _Measurement
    sequence: int


class NativeCpuBinding:
    """Borrow the exact owners; close/cancel only this binding's local state.

    Lock order: binding (nonblocking) -> existing target lifecycle (nonblocking)
    -> clock's existing acquisition -> short clock-condition publication fence.
    No authority/journal callback or native policy mutation is performed here.
    Native synchronous occupancy is measured and rejected, not preempted.
    """
    def __init__(self, owned_process, clock, *, maximum_capture_ns=100_000_000, cancel_event=None):
        _require(os.name == 'nt' and isinstance(owned_process,WindowsOwnedProcess)
            and type(clock) is NativeSessionClock, 'CPU_BINDING_NATIVE_OWNERS_REQUIRED')
        _integer(maximum_capture_ns,1,1_000_000_000)
        _require(cancel_event is None or type(cancel_event) is threading.Event,
            'CPU_BINDING_CANCELLATION_EVENT_REQUIRED')
        mono, perf = time.get_clock_info('monotonic'), time.get_clock_info('perf_counter')
        _require(mono.implementation == 'GetTickCount64()' and perf.implementation == 'QueryPerformanceCounter()'
            and mono.monotonic and perf.monotonic and not mono.adjustable and not perf.adjustable,
            'CPU_BINDING_CLOCK_DOMAIN_UNQUALIFIED')
        resolutions = []
        for info in (mono,perf):
            _require(type(info.resolution) in (int,float) and math.isfinite(info.resolution)
                and 0 < info.resolution <= 0.1, 'CPU_BINDING_RESOLUTION_UNAVAILABLE')
            resolutions.append(max(1,math.ceil(info.resolution*1_000_000_000)))
        self._target,self._clock = owned_process,clock
        self._maximum,self._driver_resolution,self._elapsed_resolution = maximum_capture_ns,*resolutions
        self._driver_now,self._elapsed_now = time.monotonic_ns,time.perf_counter_ns
        self._identity = owned_process.resource_identity
        self._identity.__post_init__()
        self._lifetime = self._target_fields()
        self._session = clock._session
        self._lock = threading.RLock()
        self._cancelled,self._external_cancel = threading.Event(),cancel_event
        self._closed,self._busy,self._reason = False,False,None
        self._current,self._sequence,self._last_clock = None,0,None
        self._last_driver,self._last_elapsed = -1,-1

    def _target_fields(self):
        target = self._target
        return (target._process,target._job,target._pid,target._creation_time,target._image_sha256,
                target._cpu_job_digest)

    def _veto(self):
        # Last publication check reads exact Event state, not an injected callback.
        _require(not self._closed,'CPU_BINDING_CLOSED')
        _require(not self._cancelled._flag and (self._external_cancel is None
            or self._external_cancel._flag is False),'CPU_BINDING_CANCELLED')
        _require(self._reason is None,self._reason or 'CPU_BINDING_UNAVAILABLE')

    @contextmanager
    def _clock_fence(self):
        _require(self._clock._condition.acquire(blocking=False),'CPU_BINDING_CLOCK_BUSY')
        try: yield
        finally: self._clock._condition.release()

    @contextmanager
    def _owned(self):
        _require(self._lock.acquire(blocking=False),'CPU_BINDING_BUSY')
        target_locked = marked_busy = False
        try:
            self._veto(); _require(not self._busy,'CPU_BINDING_REENTRANT')
            self._busy = marked_busy = True
            target_locked = self._target._lock.acquire(blocking=False)
            _require(target_locked,'CPU_BINDING_TARGET_BUSY')
            yield
        finally:
            if target_locked: self._target._lock.release()
            if marked_busy: self._busy = False
            self._lock.release()

    def _tick(self, kind):
        value = _integer(self._driver_now() if kind == 'driver' else self._elapsed_now())
        field = '_last_driver' if kind == 'driver' else '_last_elapsed'
        if value < getattr(self,field):
            self._reason = 'CPU_BINDING_CLOCK_ROLLBACK'
            self._current = None
            raise ContractError(self._reason)
        setattr(self,field,value)
        return value

    def _clock_sample(self):
        try:
            pair = self._clock.clock()
            _require(type(pair) is tuple and len(pair)==2,'CPU_BINDING_NATIVE_PAIR_REQUIRED')
            previous,current = _sample(pair[0]),_sample(pair[1])
            require_clock_progress(previous,current)
            if self._last_clock is not None: require_clock_progress(self._last_clock,current)
            self._last_clock = current
            return current
        except (ContractError,OSError):
            self._reason = 'CPU_BINDING_NATIVE_CLOCK_UNAVAILABLE'
            self._current = None
            raise
        except BaseException:
            self._reason = 'CPU_BINDING_NATIVE_CLOCK_INTERRUPTED'
            self._current = None
            raise

    def _pure_fence(self, sample, observed):
        target,clock = self._target,self._clock
        _require(self._target_fields()==self._lifetime and not target._closed
            and not target._termination_requested and target._exit_code is None
            and not target._cpu_lifetime_unavailable and target._process is not None
            and target._job is not None, 'CPU_BINDING_LIFETIME_CHANGED')
        _require(target._cpu_version == observed.version and target._cpu_policy == observed.limit,
            'CPU_BINDING_POLICY_CHANGED')
        _require(clock._state=='ACTIVE' and clock._reason is None and clock._registration is not None
            and clock._session==self._session and clock._epoch==sample.durable_epoch
            and clock._resume==sample.resume_generation,'CPU_BINDING_CLOCK_SESSION_CHANGED')
        self._veto()

    def _measure(self):
        started = self._tick('elapsed')
        before = self._clock_sample()
        driver_start = self._tick('driver')
        observed = _observation(self._target.cpu_rate_observation(self._identity,
            maximum_duration_ns=self._maximum))
        driver_end = self._tick('driver')
        _require(observed.state is ObservationState.MEASURED,'CPU_BINDING_POLICY_UNAVAILABLE')
        _require(observed.identity==self._identity and observed.job_digest==self._lifetime[-1],
            'CPU_BINDING_TARGET_CHANGED')
        _require(driver_start <= observed.observed_monotonic_ns <= driver_end,
            'CPU_BINDING_DRIVER_TIMESTAMP_OUTSIDE_BRACKET')
        after = self._clock_sample()
        require_clock_progress(before,after)
        _require(self._target._cpu_member_current(self._identity),'CPU_BINDING_MEMBERSHIP_UNAVAILABLE')
        ended = self._tick('elapsed')
        lower = _integer(before.monotonic_ns-before.uncertainty_ns)
        upper = _integer(after.monotonic_ns+after.uncertainty_ns)
        acquisition = max(ended-started+2*self._elapsed_resolution,upper-lower)
        _require(0 < acquisition <= self._maximum,'CPU_BINDING_OBSERVATION_TOO_SLOW')
        measurement = _Measurement(observed,before,after,driver_start,driver_end,lower,upper,
            lower-(driver_end+self._driver_resolution),
            upper-max(0,driver_start-self._driver_resolution),acquisition,ended)
        # No fallible/native/time callback follows this final current-state/veto check.
        with self._clock_fence(): self._pure_fence(after,observed)
        return measurement

    def capture(self):
        with self._owned():
            # A failed replacement cannot leave an older capture current.
            self._current = None
            measurement = self._measure()
            _require(self._sequence < MAX_INTEGER,'CPU_BINDING_SEQUENCE_EXHAUSTED')
            sequence = self._sequence+1
            original = measurement.original
            native = _observation(CpuRateObservation(original.identity,original.job_digest,original.state,original.limit,
                original.version,measurement.native_lower))
            value = NativeCpuCapture(native,_sample(measurement.before),_sample(measurement.after),original.observed_monotonic_ns,
                measurement.driver_start,measurement.driver_end,self._driver_resolution,self._elapsed_resolution,
                measurement.acquisition,sequence)
            record = _RetainedCapture(value,_capture_wire(value),measurement,sequence)
            with self._clock_fence():
                ended = self._tick('elapsed')
                _require(measurement.acquisition+ended-measurement.elapsed_end+2*self._elapsed_resolution
                    <= self._maximum,'CPU_BINDING_PUBLICATION_TOO_SLOW')
                self._pure_fence(measurement.after,original)
                self._sequence,self._current = sequence,record
            return value

    def _request(self, capture, request):
        record = self._current
        _require(record is not None and capture is record.public,'CPU_BINDING_CAPTURE_NOT_OWNED')
        _require(_capture_wire(capture)==record.public_wire,'CPU_BINDING_CAPTURE_CHANGED')
        _require(type(request) is OwnedCpuRequest,'CPU_BINDING_REQUEST_REQUIRED')
        request = decode_owned_cpu_request(request.canonical_wire)
        expected = _observation_value(request.expected_limit)
        original = record.measurement.original
        private_native = CpuRateObservation(original.identity,original.job_digest,original.state,original.limit,
            original.version,record.measurement.native_lower)
        _require(expected==_observation_value(private_native)
            and request.process_identity==self._identity and request.job_digest==self._lifetime[-1],
            'CPU_BINDING_REQUEST_CAPTURE_MISMATCH')
        return record,request

    def _arguments(self, record, request):
        fresh = self._measure()
        old = record.measurement
        _require(fresh.original.identity==old.original.identity and fresh.original.job_digest==old.original.job_digest
            and fresh.original.version==old.original.version and fresh.original.limit==old.original.limit,
            'CPU_BINDING_POLICY_CHANGED')
        require_clock_progress(old.after,fresh.after)
        require_deadline_current(request.deadline,fresh.before,fresh.after)
        commitment = request.input_commitment
        _require(_capture_wire(record.public)==record.public_wire,'CPU_BINDING_CAPTURE_CHANGED')
        # Separate absolute epochs: bound N-D by the actual enclosing interval.
        # Charge both driver endpoints, both elapsed endpoints and full uncertain
        # acquisition; no equality of absolute QPC/Python epochs is assumed.
        identity = ProcessResourceIdentity(self._identity.pid,self._identity.creation_time,self._identity.image_digest)
        expected = _observation(old.original)
        with self._clock_fence():
            ended = self._tick('elapsed')
            charge = fresh.acquisition+ended-fresh.elapsed_end+2*self._elapsed_resolution
            native_age = fresh.native_upper-old.native_lower+charge
            _require(0 <= native_age <= request.maximum_observation_age_ns,'CPU_BINDING_CAPTURE_STALE')
            remaining = min(request.deadline.expires_monotonic_ns-fresh.native_upper,
                request.deadline.expires_wall_ns-fresh.after.latest_wall_ns)-charge
            deadline = _integer(max(0,fresh.driver_start-self._driver_resolution)+remaining)
            age_offset = max(0,old.original.observed_monotonic_ns+fresh.offset_high-old.native_lower)
            age = request.maximum_observation_age_ns-age_offset-charge
            duration = min(request.maximum_duration_ns-charge-2*self._driver_resolution,
                remaining-2*self._driver_resolution)
            _require(deadline > fresh.driver_end+self._driver_resolution and 1 <= age <= 60_000_000_000
                and 1 <= duration <= 1_000_000_000,'CPU_BINDING_TRANSLATION_UNAVAILABLE')
            arguments = CpuDriverArguments(identity,expected,deadline,age,duration,record.sequence,commitment)
            _require(self._current is record,'CPU_BINDING_CAPTURE_REPLACED')
            self._pure_fence(fresh.after,fresh.original)
        return arguments

    def require_current(self, capture, request):
        with self._owned():
            record,request = self._request(capture,request)
            self._arguments(record,request)
        return None

    def driver_arguments(self, capture, request):
        with self._owned():
            record,request = self._request(capture,request)
            return self._arguments(record,request)

    def cancel(self):
        self._cancelled.set()

    def close(self):
        self._closed = True
        self._cancelled.set()
