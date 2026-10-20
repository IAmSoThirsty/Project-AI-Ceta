"""Separate-process native CPU policy observation through retained query objects.

This trusted composition owns no authority, scheduler or ledger. The native
observer and parent share Windows/kernel assumptions. A clock at the beginning
of the measured interval is retained as the conservative freshness bound; it is
an actual NC2 sample, never a caller-created trusted timestamp.
"""
from dataclasses import dataclass
from pathlib import Path
import ctypes as C
import copy
import hashlib
import secrets
import re
import struct
import threading
import time

from ceta.contracts.kernel_transactions import commitment, require
from ceta.contracts.real_effect import CpuEffectObservation, OwnedCpuRequest
from ceta.contracts.resource_management import ObservationState
from ceta.contracts.temporal import require_clock_progress, require_deadline_current
from ceta.contracts.wire import ContractError, MAX_INTEGER
from ceta.contracts.workload_throttling import CpuRateLimit
from ceta.identity.native_clock import NativeSessionClock
from ceta.supervisor.service import _ControlApi, controlled_environment
from ceta.supervisor.windows_jobs import WindowsOwnedProcess, DWORD, HANDLE, _API, _open_image, _hash_image

REQUEST = struct.Struct('<8sIQQQ32s32s32s32sIQ32s32s')
RESPONSE = struct.Struct('<8sIQ32s32s32s32sIQ32sIQ32sIIIIIQQQII')
require(REQUEST.size == 240 and RESPONSE.size == 288, 'OBSERVER_PROTOCOL_LAYOUT_INVALID')
MAX_DIAGNOSTIC = 1024
_REASONS = {1:'OBSERVER_TARGET_NATIVE_UNAVAILABLE',2:'OBSERVER_TARGET_IMAGE_UNAVAILABLE',
    3:'OBSERVER_TARGET_EXITED',4:'OBSERVER_TARGET_NOT_IN_JOB',5:'OBSERVER_POLICY_QUERY_UNAVAILABLE',
    6:'OBSERVER_POLICY_SIZE_INVALID',7:'OBSERVER_TARGET_CHANGED'}

def observer_code_commitment(image_sha256, python_sha256):
    require(all(type(value) is str and re.fullmatch('[0-9a-f]{64}',value)
        for value in (image_sha256,python_sha256)), 'OBSERVER_IMAGE_HASH_REQUIRED')
    return 'sha256:'+hashlib.sha256(b'CETA-OBSERVER-CODE-V1\0'+bytes.fromhex(image_sha256)+bytes.fromhex(python_sha256)).hexdigest()

def _expose_source_custody(primary, owner, cleanup_error):
    try:
        note = getattr(primary, 'add_note', None)
        if callable(note): note('Observer source-file custody is retained; explicit cleanup is required.')
    except BaseException:
        pass
    BaseException.__dict__['__dict__'].__get__(primary).update(
        source_hash_custody=owner, close_cleanup=owner.close, source_hash_cleanup_error=cleanup_error)


class _SourcePin:
    """Read-only file ownership with a duplicate object fence for close retry."""
    def __init__(self):
        self.api, self.handle, self.guard = _API(), None, HANDLE()
        self.guard_state, self.closed = 'ABSENT', False
        self._lock = threading.RLock()
        self._compare = C.WinDLL('kernelbase',use_last_error=True,winmode=0x800).CompareObjectHandles
        self._compare.argtypes,self._compare.restype = [HANDLE,HANDLE],C.c_int32

    def _guard(self):
        if self.guard_state == 'PENDING': return
        require(self.guard_state == 'ABSENT', 'OBSERVER_SOURCE_GUARD_ALLOCATION_UNCERTAIN')
        self.guard_state = 'QUERYING'
        try:
            current = self.api.GetCurrentProcess()
            ok = self.api.DuplicateHandle(current,self.handle,current,C.byref(self.guard),0,False,2)
            self.guard_state = 'PENDING' if ok and self.guard.value else 'UNCERTAIN' if self.guard.value else 'ABSENT'
            require(ok and self.guard.value, 'OBSERVER_SOURCE_GUARD_UNAVAILABLE')
        except BaseException:
            if self.guard_state == 'QUERYING': self.guard_state = 'UNCERTAIN'
            raise

    def open(self):
        with self._lock:
            require(self.handle is None and not self.closed, 'OBSERVER_SOURCE_PIN_ALREADY_OPEN')
            self.handle = _open_image(self.api,str(Path(__file__).resolve(strict=True)))
            self._guard()

    def close(self):
        with self._lock:
            if self.closed: return
            if self.handle is not None:
                self._guard()
                if not self._compare(self.handle,self.guard.value):
                    self.handle = None
                else:
                    try:
                        self.api.close(self.handle)
                    except BaseException as primary:
                        try:
                            if not self._compare(self.handle,self.guard.value): self.handle = None
                        except BaseException as secondary:
                            BaseException.__dict__['__dict__'].__get__(primary)['source_pin_observation_error'] = secondary
                        raise
                    require(not self._compare(self.handle,self.guard.value), 'OBSERVER_SOURCE_CLOSE_NOT_OBSERVED')
                    self.handle = None
            if self.guard.value:
                require(self.guard_state == 'PENDING', 'OBSERVER_SOURCE_GUARD_CLOSE_UNCERTAIN')
                self.guard_state = 'UNCERTAIN'
                require(self.api.close(self.guard.value) is None, 'OBSERVER_SOURCE_GUARD_CLOSE_RESPONSE_INVALID')
                require(not self._compare(self.guard.value,self.guard.value), 'OBSERVER_SOURCE_GUARD_CLOSE_NOT_OBSERVED')
                self.guard.value = None
                self.guard_state = 'ABSENT'
            require(self.guard_state == 'ABSENT', 'OBSERVER_SOURCE_GUARD_ALLOCATION_UNCERTAIN')
            self.closed = True

    def pending_native_resources(self):
        with self._lock:
            return () if self.closed else ({'kind':'source_file','handle':self.handle,
                'guard_handle':self.guard.value,'guard_state':self.guard_state},)


def _source_hash():
    owner, primary = _SourcePin(), None
    try:
        owner.open()
        return _hash_image(owner.api,owner.handle)[0]
    except BaseException as error:
        primary = error
        raise
    finally:
        try: owner.close()
        except BaseException as cleanup_error:
            _expose_source_custody(primary if primary is not None else cleanup_error,owner,cleanup_error)
            if primary is None: raise

class NativeObserverError(ContractError):
    """Expose unresolved exact process/channel/query custody for explicit recovery."""
    def __init__(self, code, custody, primary):
        super().__init__(code)
        self.observer_custody, self.primary_error = custody, primary
    def close_cleanup(self): self.observer_custody.close()


def _expose_observer_custody(primary, custody, diagnostic_error=None):
    try:
        note = getattr(primary, 'add_note', None)
        if callable(note): note('Observer native custody remains explicitly available.')
    except BaseException:
        pass
    BaseException.__dict__['__dict__'].__get__(primary).update(
        observer_custody=custody, close_observer_cleanup=custody.close,
        observer_diagnostic_error=diagnostic_error)


def _failure_kind(error):
    if error is None: return None
    try: return type(error).__name__
    except BaseException: return 'UNKNOWN_EXCEPTION_CLASS'

class _Custody:
    def __init__(self):
        self.api = _ControlApi()
        self.process, self.lease, self.launch_error = None, None, None
        self.handles, self.uncertain_handles = [], set()
        self.cleanup_errors = []
        self.retirement_samples = []
        self.transport_state = None
        self.closed = False

    def pipe(self, child_reads):
        try:
            parent, child = self.api.pipe(child_reads=child_reads)
        except BaseException as error:
            self.handles.extend(getattr(error, 'control_handles', ()))
            raise
        self.handles.extend((parent, child))
        return parent, child

    def close_handle(self, handle):
        if handle not in self.handles: return
        require(handle not in self.uncertain_handles, 'OBSERVER_HANDLE_CLOSE_UNCERTAIN')
        self.uncertain_handles.add(handle)
        returned = self.api.CloseHandle(handle)
        if not returned:
            self.uncertain_handles.discard(handle)
            raise ContractError('OBSERVER_HANDLE_CLOSE_REFUSED')
        self.handles.remove(handle)
        self.uncertain_handles.discard(handle)

    def close(self):
        if self.closed: return
        errors = []
        if self.process is not None and not self.process.lifetime_closed:
            try:
                if self.process.poll() is None: self.process.terminate(125)
                require(self.process.wait(2), 'OBSERVER_RETIREMENT_UNOBSERVED')
                end = time.monotonic_ns()+2_000_000_000
                while True:
                    active = self.process.active_process_count()
                    self.retirement_samples.append(active)
                    if active == 0: break
                    require(time.monotonic_ns() < end, 'OBSERVER_JOB_NOT_EMPTY')
                    time.sleep(.001)
                require(self.process.poll() is not None,'OBSERVER_EXIT_UNOBSERVED')
                self.process.close()
            except BaseException as error: errors.append(error)
        if self.launch_error is not None:
            try:
                self.launch_error.close_cleanup()
                self.launch_error = None
            except BaseException as error: errors.append(error)
        for handle in tuple(self.handles):
            try: self.close_handle(handle)
            except BaseException as error: errors.append(error)
        if self.lease is not None:
            try:
                if self.process is None and self.launch_error is None and not self.lease.closed:
                    self.lease.launch_failed_without_observer()
                self.lease.close()
            except BaseException as error: errors.append(error)
        self.cleanup_errors = tuple(errors)
        self.closed = (not self.handles and self.launch_error is None
            and (self.process is None or self.process.lifetime_closed)
            and (self.lease is None or self.lease.closed))
        if errors: raise errors[0]

    def evidence(self):
        return {'observer_identity':None if self.process is None else {
            'pid':self.process.pid,'creation_time':self.process.creation_time,'image_sha256':self.process.image_sha256},
            'observer_lifetime_closed':self.process is None or self.process.lifetime_closed,
            'pending_channel_handles':tuple(self.handles),'uncertain_channel_handles':tuple(sorted(self.uncertain_handles)),
            'pending_query_handles':() if self.lease is None else self.lease.pending_handles(),
            'query_lease_closed':self.lease is None or self.lease.closed,'closed':self.closed,
            'retirement_active_process_samples':tuple(self.retirement_samples),
            'transport_state':copy.deepcopy(self.transport_state),
            'cleanup_errors':tuple(type(error).__name__ for error in self.cleanup_errors)}

@dataclass(frozen=True, slots=True)
class _NativeFacts:
    sequence: int
    nonce: bytes
    request_commitment: bytes
    job_digest: bytes
    observer_commitment: bytes
    observer_pid: int
    observer_creation: int
    observer_image: bytes
    target_pid: int
    target_creation: int
    target_image: bytes
    state: int
    reason: int
    member: int
    exit_available: int
    exit_code: int
    qpc_start: int
    qpc_end: int
    qpc_frequency: int
    flags: int
    value: int

def _decode(payload):
    require(type(payload) is bytes and len(payload) == RESPONSE.size, 'OBSERVER_OUTPUT_SIZE_INVALID')
    magic, version, *fields = RESPONSE.unpack(payload)
    require(magic == b'CETAOR1\0' and version == 1, 'OBSERVER_OUTPUT_PROFILE_INVALID')
    facts = _NativeFacts(*fields)
    require(facts.state in (0,1) and facts.member in (0,1) and facts.exit_available in (0,1)
            and facts.qpc_frequency > 0 and facts.qpc_start <= facts.qpc_end,
            'OBSERVER_NATIVE_FACTS_INVALID')
    require(facts.state == 1 and facts.reason == 0 or facts.state == 0 and facts.reason in _REASONS,
            'OBSERVER_NATIVE_REASON_INVALID')
    require(facts.state == 1 or facts.flags == facts.value == 0, 'OBSERVER_UNAVAILABLE_HAS_POLICY_BITS')
    return facts

@dataclass(frozen=True, slots=True)
class _ObservationOrigin:
    owner: object
    target: WindowsOwnedProcess
    request_wire: bytes
    observation: CpuEffectObservation
    observation_wire: bytes
    sequence: int


class NativeCpuEffectObserver:
    def __init__(self, executable, expected_image_sha256, observer_commitment, *, clock):
        require(type(clock) is NativeSessionClock, 'OBSERVER_NATIVE_CLOCK_REQUIRED')
        require(type(expected_image_sha256) is str and re.fullmatch('[0-9a-f]{64}',expected_image_sha256),
                'OBSERVER_IMAGE_HASH_REQUIRED')
        commitment(observer_commitment)
        self._executable = str(Path(executable).resolve(strict=True))
        self._image, self._commitment, self._clock = expected_image_sha256, observer_commitment, clock
        self._driver_sha = _source_hash()
        require(observer_commitment == observer_code_commitment(expected_image_sha256,self._driver_sha),
                'OBSERVER_CODE_COMMITMENT_MISMATCH')
        self._lock, self._sequence = threading.Lock(), 0
        self._custody, self._last_evidence = None, None
        self._origin = None

    @property
    def last_evidence(self): return copy.deepcopy(self._last_evidence)

    def require_observation_origin(self, request, target, observation):
        """Check retained local provenance; permission, freshness and outcome are separate."""
        require(type(request) is OwnedCpuRequest and type(observation) is CpuEffectObservation,
                'OBSERVER_ORIGIN_INPUT_REQUIRED')
        require(self._lock.acquire(blocking=False), 'OBSERVER_BUSY')
        try:
            origin = self._origin
            require(origin is not None and origin.owner is self, 'OBSERVER_ORIGIN_UNAVAILABLE')
            require(target is origin.target and observation is origin.observation
                and self._sequence == origin.sequence == observation.sequence,
                'OBSERVER_ORIGIN_BINDING_MISMATCH')
            require(request.canonical_wire == origin.request_wire
                and observation.canonical_wire == origin.observation_wire,
                'OBSERVER_ORIGIN_BYTES_CHANGED')
            return None
        finally:
            self._lock.release()

    def close_cleanup(self):
        require(self._lock.acquire(blocking=False), 'OBSERVER_BUSY')
        try:
            if self._custody is not None:
                custody = self._custody
                try:
                    custody.close()
                except BaseException as primary:
                    _expose_observer_custody(primary,custody)
                    raise
                if custody.closed: self._custody = None
                try:
                    cleanup = custody.evidence()
                except BaseException as primary:
                    _expose_observer_custody(primary,custody,primary)
                    raise
                self._last_evidence = dict(self._last_evidence or {}, cleanup=cleanup)
        finally: self._lock.release()

    def _exchange(self, custody, frame, cancelled, deadline_ns):
        parent_input, child_input = custody.pipe(True)
        parent_output, child_output = custody.pipe(False)
        parent_error, child_error = custody.pipe(False)
        lease = custody.lease
        lease.require_observer()
        try:
            custody.process = WindowsOwnedProcess.launch(self._executable, ('observe-v1',),
                cwd=str(Path(self._executable).parent), environment=controlled_environment(Path(self._executable).parent),
                inherited_handles=lease.inherited_handles,
                standard_handles=(child_input,child_output,child_error), expected_image_sha256=self._image)
        except BaseException as error:
            custody.process = getattr(error,'owned_process',None)
            if callable(getattr(error,'close_cleanup',None)): custody.launch_error = error
            if custody.process is not None: lease.bind_observer(custody.process)
            raise
        lease.bind_observer(custody.process)
        for handle in (child_input,child_output,child_error): custody.close_handle(handle)
        sent = DWORD(); body = C.create_string_buffer(frame)
        require(custody.api.WriteFile(parent_input,body,len(frame),C.byref(sent),None)
            and sent.value == len(frame), 'OBSERVER_INPUT_WRITE_FAILED')
        custody.close_handle(parent_input)
        buffers, eof = {parent_output:b'',parent_error:b''}, set()
        bounds = {parent_output:RESPONSE.size,parent_error:MAX_DIAGNOSTIC}
        custody.transport_state = {'stdout_bytes':0,'stderr_bytes':0,'stdout_available':0,
            'stderr_available':0,'exit_code':None,'poll_count':0}
        while True:
            require(cancelled is None or not cancelled.is_set(), 'OBSERVER_CANCELLED')
            require(time.monotonic_ns() < deadline_ns, 'OBSERVER_PROCESS_TIMEOUT')
            for handle in buffers:
                if handle in eof: continue
                available = DWORD()
                if not custody.api.PeekNamedPipe(handle,None,0,None,C.byref(available),None):
                    require(C.get_last_error() == 109, 'OBSERVER_PIPE_OBSERVATION_FAILED')
                    eof.add(handle); continue
                label = 'stdout' if handle == parent_output else 'stderr'
                custody.transport_state[label+'_available'] = available.value
                if available.value:
                    require(len(buffers[handle])+available.value <= bounds[handle], 'OBSERVER_OUTPUT_OVERLONG')
                    data = C.create_string_buffer(available.value); received = DWORD()
                    require(custody.api.ReadFile(handle,data,len(data),C.byref(received),None)
                        and 0 < received.value <= len(data), 'OBSERVER_PIPE_READ_FAILED')
                    buffers[handle] += data.raw[:received.value]
                    custody.transport_state[label+'_bytes'] = len(buffers[handle])
            exit_code = custody.process.poll()
            custody.transport_state['exit_code'] = exit_code
            custody.transport_state['poll_count'] += 1
            if exit_code is not None and len(eof) == 2:
                return buffers[parent_output],buffers[parent_error],exit_code
            time.sleep(.001)

    def observe(self, request, target, *, cancelled=None):
        require(type(request) is OwnedCpuRequest and isinstance(target,WindowsOwnedProcess),
                'OBSERVER_REQUEST_AND_OWNED_TARGET_REQUIRED')
        request.__post_init__()
        require(cancelled is None or type(cancelled) is threading.Event, 'OBSERVER_CANCEL_EVENT_REQUIRED')
        require(request.observer_commitment == self._commitment, 'OBSERVER_REQUEST_CODE_MISMATCH')
        custody, primary, value, origin = None, None, None, None
        evidence = {}
        require(self._lock.acquire(blocking=False), 'OBSERVER_BUSY')
        try:
            # Admission to this attempt retires the prior origin, including on failure.
            self._origin = None
            request_wire = request.canonical_wire
            evidence = {'request_commitment':request.input_commitment,'operation_id':request.request_id,
                'observer_commitment':self._commitment,'native_image_sha256':self._image,'python_sha256':self._driver_sha}
            require(self._custody is None, 'OBSERVER_UNRESOLVED_CUSTODY')
            require(_source_hash() == self._driver_sha, 'OBSERVER_DRIVER_CHANGED')
            require(self._sequence < MAX_INTEGER, 'OBSERVER_SEQUENCE_EXHAUSTED')
            self._sequence += 1
            sequence = self._sequence
            previous, started = self._clock.clock()
            require_deadline_current(request.deadline,previous,started)
            require(cancelled is None or not cancelled.is_set(), 'OBSERVER_CANCELLED')
            require(target.resource_identity == request.process_identity, 'OBSERVER_TARGET_IDENTITY_MISMATCH')
            before = target.cpu_rate_observation(request.process_identity,maximum_duration_ns=request.maximum_duration_ns)
            require(before.state is ObservationState.MEASURED and before.job_digest == request.job_digest,
                    'OBSERVER_PARENT_TARGET_UNAVAILABLE')
            custody = _Custody(); self._custody = custody
            try: custody.lease = target.export_cpu_query_handles(request.process_identity)
            except BaseException as error:
                custody.lease = getattr(error,'cpu_query_custody',None)
                raise
            nonce = secrets.token_bytes(32)
            process_handle,job_handle = custody.lease.inherited_handles
            frame = REQUEST.pack(b'CETAOB1\0',1,sequence,process_handle,job_handle,nonce,
                bytes.fromhex(request.input_commitment[7:]),bytes.fromhex(request.job_digest[7:]),bytes.fromhex(self._commitment[7:]),
                request.process_identity.pid,request.process_identity.creation_time,
                bytes.fromhex(request.process_identity.image_digest[7:]),bytes.fromhex(self._image))
            raw,diagnostic,exit_code = self._exchange(custody,frame,cancelled,
                time.monotonic_ns()+request.maximum_duration_ns)
            evidence.update(sequence=sequence,raw_sha256=hashlib.sha256(raw).hexdigest(),raw_bytes=raw,
                diagnostic_bytes=diagnostic,exit_code=exit_code)
            require(exit_code == 0 and not diagnostic, 'OBSERVER_PROCESS_OR_DIAGNOSTIC_FAILURE')
            facts = _decode(raw)
            identity = custody.process.resource_identity
            require(facts.sequence == sequence and facts.nonce == nonce
                and facts.request_commitment == bytes.fromhex(request.input_commitment[7:])
                and facts.job_digest == bytes.fromhex(request.job_digest[7:])
                and facts.observer_commitment == bytes.fromhex(self._commitment[7:]), 'OBSERVER_RESPONSE_BINDING_MISMATCH')
            require((facts.observer_pid,facts.observer_creation,'sha256:'+facts.observer_image.hex()) ==
                (identity.pid,identity.creation_time,identity.image_digest), 'OBSERVER_PROCESS_IDENTITY_MISMATCH')
            require((facts.target_pid,facts.target_creation,'sha256:'+facts.target_image.hex()) ==
                (request.process_identity.pid,request.process_identity.creation_time,request.process_identity.image_digest),
                'OBSERVER_NATIVE_TARGET_IDENTITY_MISMATCH')
            after = target.cpu_rate_observation(request.process_identity,maximum_duration_ns=request.maximum_duration_ns)
            custody.close()
            _, finished = self._clock.clock()
            require_deadline_current(request.deadline,started,finished)
            require_clock_progress(started,finished)
            require(finished.monotonic_ns-started.monotonic_ns <= request.maximum_duration_ns,
                    'OBSERVER_SAMPLE_OVERLONG')
            frequency = C.c_int64()
            function = C.WinDLL('kernel32',use_last_error=True,winmode=0x800).QueryPerformanceFrequency
            function.argtypes,function.restype = [C.POINTER(C.c_int64)],C.c_int32
            require(function(C.byref(frequency)) and frequency.value == facts.qpc_frequency,
                    'OBSERVER_NATIVE_CLOCK_CALIBRATION_MISMATCH')
            native_start = facts.qpc_start*1_000_000_000//facts.qpc_frequency
            native_end = (facts.qpc_end*1_000_000_000+facts.qpc_frequency-1)//facts.qpc_frequency
            require(started.monotonic_ns-started.uncertainty_ns <= native_start <= native_end
                <= finished.monotonic_ns+finished.uncertainty_ns,'OBSERVER_NATIVE_CLOCK_OUTSIDE_BRACKET')
            evidence.update(native_qpc=(facts.qpc_start,facts.qpc_end,facts.qpc_frequency),
                parent_clock_before=started,parent_clock_after=finished,parent_before=before,parent_after=after)
            state,limit,reason,target_state = ObservationState.UNAVAILABLE,None,_REASONS.get(facts.reason),'UNAVAILABLE'
            if facts.reason == 3: target_state = 'EXITED'
            elif facts.reason == 4: target_state = 'NOT_IN_OWNED_JOB'
            if facts.state == 1:
                require(facts.member == 1 and facts.exit_available == 1 and facts.exit_code == 259,
                        'OBSERVER_NATIVE_LIFETIME_DISAGREEMENT')
                limit = CpuRateLimit(facts.flags,facts.value)
                require(after.state is ObservationState.MEASURED and before.limit == limit == after.limit
                    and before.version == after.version,'OBSERVER_PARENT_POLICY_DISAGREEMENT')
                state,reason,target_state = ObservationState.MEASURED,None,'LIVE_IN_OWNED_JOB'
            require(cancelled is None or not cancelled.is_set(), 'OBSERVER_CANCELLED')
            value = CpuEffectObservation(request.input_commitment,request.request_id,request.process_identity,
                request.job_digest,identity,self._commitment,sequence,started,state,limit,target_state,reason)
            require(request.canonical_wire == request_wire, 'OBSERVER_REQUEST_CHANGED')
            origin = _ObservationOrigin(self,target,request_wire,value,value.canonical_wire,sequence)
            return value
        except BaseException as error:
            primary = error
            raise
        finally:
            cleanup_error = diagnostic_error = None
            try:
                try:
                    if custody is not None:
                        try: custody.close()
                        except BaseException as error: cleanup_error = error
                        if custody.closed: self._custody = None
                        elif cleanup_error is None:
                            cleanup_error = ContractError('OBSERVER_CUSTODY_UNRESOLVED')
                        try: evidence['cleanup'] = custody.evidence()
                        except BaseException as error: diagnostic_error = error
                    evidence['accepted'] = primary is None and value is not None and cleanup_error is None and diagnostic_error is None
                    evidence['failure'] = _failure_kind(primary if primary is not None else cleanup_error
                        if cleanup_error is not None else diagnostic_error)
                    if diagnostic_error is not None: evidence['diagnostic_failure'] = _failure_kind(diagnostic_error)
                    self._last_evidence = evidence
                    if primary is None and origin is not None and cleanup_error is None and diagnostic_error is None:
                        require(origin is not None and custody is not None and custody.closed and self._custody is None,
                                'OBSERVER_ORIGIN_CUSTODY_PENDING')
                        require(request.canonical_wire == origin.request_wire
                            and value.canonical_wire == origin.observation_wire
                            and self._sequence == origin.sequence, 'OBSERVER_ORIGIN_CHANGED')
                        # Diagnostics are complete; mutable last_evidence is never proof.
                        self._origin = origin
                finally:
                    self._lock.release()
                if primary is not None:
                    if custody is not None and (cleanup_error is not None or diagnostic_error is not None):
                        _expose_observer_custody(primary,custody,diagnostic_error)
                elif cleanup_error is not None:
                    raise NativeObserverError('OBSERVER_CUSTODY_UNRESOLVED',custody,cleanup_error) from cleanup_error
                elif diagnostic_error is not None:
                    _expose_observer_custody(diagnostic_error,custody,diagnostic_error)
                    raise diagnostic_error
            except BaseException as error:
                evidence['accepted'] = False
                evidence['failure'] = _failure_kind(primary if primary is not None else error)
                if self._origin is origin: self._origin = None
                raise
