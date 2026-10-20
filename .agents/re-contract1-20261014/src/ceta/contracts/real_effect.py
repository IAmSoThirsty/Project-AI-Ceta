"""Exact data commitments for the selected owner-directed native CPU profile.

Decoding these values authenticates no user, observer, native handle or result.
The captured canonical owners must resolve every reference before admission.
"""
from dataclasses import dataclass, fields

from .kernel_transactions import (BUDGET_FIELDS, BudgetVector, bound_generation,
    commitment, deadline_wire, digest, identifier, require)
from .resource_management import ObservationState, ProcessResourceIdentity
from .temporal import ClockSample, Deadline, require_clock_progress, require_deadline_current
from .wire import MAX_INTEGER, canonical_bytes, strict_loads
from .workload_throttling import CpuRateLimit, CpuRateObservation

REAL_EFFECT_PROFILE = 'ceta-owned-real-effect-v1'
CAP_OPERATION = 'owned-worker.cpu-cap'
RESTORE_OPERATION = 'owned-worker.cpu-restore'
OBSERVATION_METHOD = 'windows:QueryInformationJobObject:15'
INDEPENDENCE_CLASS = 'SEPARATE_PROCESS_SHARED_OS'
MAX_REQUEST_BYTES = 32768


def _shape(value, names, code):
    require(type(value) is dict and set(value) == set(names), code)
    return value


def _integer(value, minimum, maximum, code):
    require(type(value) is int and minimum <= value <= maximum, code)


def _process(value):
    _shape(value, ('pid', 'creation_time', 'image_digest'), 'EFFECT_PROCESS_FIELDS')
    return ProcessResourceIdentity(**value)


def _limit(value):
    _shape(value, ('control_flags', 'value'), 'EFFECT_LIMIT_FIELDS')
    return CpuRateLimit(**value)


def _process_value(value):
    return {field.name: getattr(value, field.name) for field in fields(ProcessResourceIdentity)}


def _limit_value(value):
    return {'control_flags': value.control_flags, 'value': value.value}


def _sample_value(sample):
    return {field.name: getattr(sample, field.name) for field in fields(ClockSample)}


def _clock(value):
    _shape(value, (field.name for field in fields(ClockSample)), 'EFFECT_CLOCK_FIELDS')
    return ClockSample(**value)


@dataclass(frozen=True, slots=True)
class OwnedCpuRequest:
    request_id: str
    scope_id: str
    task_id: str
    proposal_id: str
    principal_id: str
    actor_session: str
    owner_session_nonce: str
    operation: str
    process_identity: ProcessResourceIdentity
    job_digest: str
    expected_limit: CpuRateObservation
    target_limit: CpuRateLimit
    original_limit: CpuRateLimit
    task_revision: str
    policy_commitment: str
    adapter_commitment: str
    environment_commitment: str
    source_commitment: str
    observer_commitment: str
    operation_budget: BudgetVector
    required_outcome_bytes: int
    deadline: Deadline
    maximum_observation_age_ns: int
    maximum_duration_ns: int
    consequences: tuple[str, ...]
    restoration_of: str | None = None
    original_request_commitment: str | None = None

    def __post_init__(self):
        for name in ('request_id', 'scope_id', 'task_id', 'proposal_id', 'principal_id',
                     'actor_session', 'owner_session_nonce'):
            identifier(getattr(self, name))
        require(type(self.operation) is str and self.operation in (CAP_OPERATION, RESTORE_OPERATION),
                'EFFECT_OPERATION_UNAVAILABLE')
        require(type(self.process_identity) is ProcessResourceIdentity, 'EFFECT_PROCESS_REQUIRED')
        self.process_identity.__post_init__()
        _integer(self.process_identity.creation_time, 1, MAX_INTEGER, 'EFFECT_PROCESS_WIRE_RANGE')
        commitment(self.job_digest)
        require(type(self.expected_limit) is CpuRateObservation, 'EFFECT_EXPECTED_LIMIT_REQUIRED')
        self.expected_limit.__post_init__()
        require(self.expected_limit.state is ObservationState.MEASURED and self.expected_limit.reason is None,
                'EFFECT_MEASURED_PRECONDITION_REQUIRED')
        require(self.expected_limit.identity == self.process_identity and self.expected_limit.job_digest == self.job_digest,
                'EFFECT_TARGET_BINDING_MISMATCH')
        for limit in (self.target_limit, self.original_limit):
            require(type(limit) is CpuRateLimit, 'EFFECT_LIMIT_REQUIRED'); limit.__post_init__()
        for name in ('task_revision', 'policy_commitment', 'adapter_commitment',
                     'environment_commitment', 'source_commitment', 'observer_commitment'):
            commitment(getattr(self, name))
        require(type(self.operation_budget) is BudgetVector, 'EFFECT_OPERATION_BUDGET_REQUIRED')
        self.operation_budget.__post_init__()
        require(self.operation_budget.values[BUDGET_FIELDS.index('max_effects')] == 1,
                'EFFECT_EXACT_SINGLE_EFFECT_BUDGET_REQUIRED')
        _integer(self.required_outcome_bytes, 4096, 1048576, 'EFFECT_OUTCOME_CAPACITY_INVALID')
        require(self.operation_budget.values[BUDGET_FIELDS.index('max_bytes_written')] >= self.required_outcome_bytes,
                'EFFECT_OUTCOME_BUDGET_INSUFFICIENT')
        require(type(self.deadline) is Deadline, 'DEADLINE_REQUIRED'); self.deadline.__post_init__()
        _integer(self.maximum_observation_age_ns, 1, 5_000_000_000, 'EFFECT_OBSERVATION_AGE_INVALID')
        _integer(self.maximum_duration_ns, 1, 1_000_000_000, 'EFFECT_DURATION_INVALID')
        require(self.operation_budget.values[BUDGET_FIELDS.index('wall_time_ms')] * 1_000_000 >= self.maximum_duration_ns,
                'EFFECT_WALL_BUDGET_INSUFFICIENT')
        require(type(self.consequences) is tuple and 1 <= len(self.consequences) <= 16, 'EFFECT_CONSEQUENCES_REQUIRED')
        for consequence in self.consequences: identifier(consequence)
        require(len(set(self.consequences)) == len(self.consequences), 'EFFECT_CONSEQUENCES_REQUIRED')
        if self.operation == CAP_OPERATION:
            require(self.restoration_of is None and self.original_request_commitment is None,
                    'EFFECT_UNEXPECTED_RESTORATION_LINK')
            require(self.original_limit == self.expected_limit.limit, 'EFFECT_ORIGINAL_LIMIT_MISMATCH')
            prior = self.expected_limit.limit
            require(prior.control_flags == 0 or prior.hard_cap_rate is not None, 'EFFECT_ORIGINAL_POLICY_UNSUPPORTED')
            require(self.target_limit.hard_cap_rate is not None and
                    self.target_limit.control_flags & 8 == prior.control_flags & 8,
                    'EFFECT_TARGET_HARD_CAP_REQUIRED')
            require(self.target_limit.hard_cap_rate < (prior.hard_cap_rate or 10000), 'EFFECT_REDUCTION_REQUIRED')
        else:
            identifier(self.restoration_of); commitment(self.original_request_commitment)
            require(self.restoration_of != self.request_id, 'EFFECT_RESTORATION_ID_REUSED')
            require(self.target_limit == self.original_limit, 'EFFECT_EXACT_RESTORATION_REQUIRED')

    def as_dict(self):
        self.__post_init__()
        value = {field.name: getattr(self, field.name) for field in fields(self)}
        expected = self.expected_limit
        value.update(profile=REAL_EFFECT_PROFILE, process_identity=_process_value(self.process_identity),
            expected_limit={'identity': _process_value(expected.identity), 'job_digest': expected.job_digest,
                'state': expected.state.value, 'limit': _limit_value(expected.limit), 'version': expected.version,
                'observed_monotonic_ns': expected.observed_monotonic_ns, 'reason': expected.reason},
            target_limit=_limit_value(self.target_limit), original_limit=_limit_value(self.original_limit),
            operation_budget=self.operation_budget.as_dict(), deadline=deadline_wire(self.deadline),
            consequences=list(self.consequences))
        return value

    @property
    def canonical_wire(self):
        wire = canonical_bytes(self.as_dict())
        require(len(wire) <= MAX_REQUEST_BYTES, 'EFFECT_REQUEST_SIZE')
        return wire

    @property
    def input_commitment(self):
        return digest('owned-cpu-request-v1', self.as_dict())


def decode_owned_cpu_request(wire):
    require(type(wire) is bytes and 1 <= len(wire) <= MAX_REQUEST_BYTES, 'EFFECT_REQUEST_SIZE')
    value = strict_loads(wire)
    _shape(value, {'profile'} | {field.name for field in fields(OwnedCpuRequest)}, 'EFFECT_REQUEST_FIELDS')
    require(value['profile'] == REAL_EFFECT_PROFILE and canonical_bytes(value) == wire, 'EFFECT_REQUEST_PROFILE_OR_CANONICAL')
    expected = _shape(value['expected_limit'], {field.name for field in fields(CpuRateObservation)}, 'EFFECT_EXPECTED_FIELDS')
    require(expected['state'] == ObservationState.MEASURED.value and expected['reason'] is None,
            'EFFECT_MEASURED_PRECONDITION_REQUIRED')
    parsed_expected = CpuRateObservation(_process(expected['identity']), expected['job_digest'], ObservationState.MEASURED,
        _limit(expected['limit']), expected['version'], expected['observed_monotonic_ns'], expected['reason'])
    _shape(value['deadline'], (field.name for field in fields(Deadline)), 'EFFECT_DEADLINE_FIELDS')
    require(type(value['consequences']) is list, 'EFFECT_CONSEQUENCES_REQUIRED')
    args = {name: item for name, item in value.items() if name != 'profile'}
    args.update(process_identity=_process(value['process_identity']), expected_limit=parsed_expected,
        target_limit=_limit(value['target_limit']), original_limit=_limit(value['original_limit']),
        operation_budget=BudgetVector.from_dict(value['operation_budget']), deadline=Deadline(**value['deadline']),
        consequences=tuple(value['consequences']))
    result = OwnedCpuRequest(**args)
    require(result.canonical_wire == wire, 'EFFECT_REQUEST_ROUNDTRIP_MISMATCH')
    return result


def require_restoration_link(original, restoration):
    require(type(original) is OwnedCpuRequest and type(restoration) is OwnedCpuRequest, 'EFFECT_REQUEST_REQUIRED')
    original.__post_init__(); restoration.__post_init__()
    require(original.operation == CAP_OPERATION and restoration.operation == RESTORE_OPERATION,
            'EFFECT_RESTORATION_PARENT_INVALID')
    require(restoration.restoration_of == original.request_id and
            restoration.original_request_commitment == original.input_commitment, 'EFFECT_RESTORATION_LINK_MISMATCH')
    require(all(getattr(original, name) == getattr(restoration, name) for name in
                ('scope_id', 'task_id', 'principal_id', 'process_identity', 'job_digest', 'original_limit')),
            'EFFECT_RESTORATION_TARGET_MISMATCH')


def approval_display_bytes(request):
    """Exact complete renderable request data; genuine consent requires its native owner."""
    require(type(request) is OwnedCpuRequest, 'EFFECT_REQUEST_REQUIRED')
    return canonical_bytes({'display_profile': 'ceta-owned-cpu-approval-display-v1',
                            'request': request.as_dict(), 'request_commitment': request.input_commitment})


def approval_display_commitment(request):
    return digest('owned-cpu-approval-display-v1', strict_loads(approval_display_bytes(request)))


@dataclass(frozen=True, slots=True)
class NativeApprovalTranscript:
    """Attributable native result data; a captured native owner must authenticate it."""
    challenge_id: str
    ceremony_nonce: str
    request_commitment: str
    displayed_commitment: str
    principal_id: str
    actor_session: str
    ui_identity: ProcessResourceIdentity
    ui_commitment: str
    helper_identity: ProcessResourceIdentity
    helper_commitment: str
    observed_clock: ClockSample
    native_hresult: int
    native_result: int | None
    native_method: str = 'windows:UserConsentVerifier:RequestVerificationForWindowAsync'

    def __post_init__(self):
        for value in (self.challenge_id, self.ceremony_nonce, self.principal_id, self.actor_session): identifier(value)
        for value in (self.request_commitment, self.displayed_commitment, self.ui_commitment, self.helper_commitment): commitment(value)
        for identity in (self.ui_identity, self.helper_identity):
            require(type(identity) is ProcessResourceIdentity, 'EFFECT_APPROVAL_PROCESS_REQUIRED'); identity.__post_init__()
            _integer(identity.creation_time, 1, MAX_INTEGER, 'EFFECT_PROCESS_WIRE_RANGE')
        require(type(self.observed_clock) is ClockSample, 'CLOCK_SAMPLE_REQUIRED'); self.observed_clock.__post_init__()
        _integer(self.native_hresult, -2147483648, 0, 'EFFECT_APPROVAL_HRESULT_INVALID')
        if self.native_hresult == 0:
            _integer(self.native_result, 0, 6, 'EFFECT_APPROVAL_NATIVE_RESULT_REQUIRED')
        else:
            require(self.native_result is None, 'EFFECT_APPROVAL_ERROR_HAS_RESULT')
        require(type(self.native_method) is str and
                self.native_method == 'windows:UserConsentVerifier:RequestVerificationForWindowAsync',
                'EFFECT_APPROVAL_METHOD_INVALID')

    @property
    def reported_outcome(self):
        self.__post_init__()
        if self.native_hresult == 0 and self.native_result == 0:
            return 'REPORTED_VERIFIED'
        if self.native_hresult == 0 and self.native_result == 6:
            return 'REPORTED_CANCELLED'
        return 'REPORTED_UNAVAILABLE'

    def as_dict(self):
        self.__post_init__()
        value = {field.name: getattr(self, field.name) for field in fields(self)}
        value.update(profile=REAL_EFFECT_PROFILE, ui_identity=_process_value(self.ui_identity),
            helper_identity=_process_value(self.helper_identity), observed_clock=_sample_value(self.observed_clock))
        return value

    @property
    def canonical_wire(self):
        return canonical_bytes(self.as_dict())

    @property
    def transcript_commitment(self):
        return digest('owned-cpu-native-approval-transcript-v1', self.as_dict())


def decode_native_approval_transcript(wire):
    require(type(wire) is bytes and 1 <= len(wire) <= MAX_REQUEST_BYTES, 'EFFECT_APPROVAL_WIRE_SIZE')
    value = strict_loads(wire)
    _shape(value, {'profile'} | {field.name for field in fields(NativeApprovalTranscript)}, 'EFFECT_APPROVAL_FIELDS')
    require(value['profile'] == REAL_EFFECT_PROFILE and canonical_bytes(value) == wire, 'EFFECT_APPROVAL_PROFILE_OR_CANONICAL')
    args = {name: item for name, item in value.items() if name != 'profile'}
    args.update(ui_identity=_process(value['ui_identity']), helper_identity=_process(value['helper_identity']),
                observed_clock=_clock(value['observed_clock']))
    result = NativeApprovalTranscript(**args)
    require(result.canonical_wire == wire, 'EFFECT_APPROVAL_ROUNDTRIP_MISMATCH')
    return result


def require_approval_binding(request, transcript, previous_clock, current_clock):
    """Check declared data/currentness; this predicate cannot authenticate a ceremony."""
    require(type(request) is OwnedCpuRequest and type(transcript) is NativeApprovalTranscript,
            'EFFECT_APPROVAL_BINDING_INPUT_REQUIRED')
    request.__post_init__(); transcript.__post_init__()
    require(transcript.request_commitment == request.input_commitment and
            transcript.displayed_commitment == approval_display_commitment(request), 'EFFECT_APPROVAL_DISPLAY_MISMATCH')
    require(transcript.principal_id == request.principal_id and transcript.actor_session == request.actor_session,
            'EFFECT_APPROVAL_PRINCIPAL_SESSION_MISMATCH')
    require(transcript.reported_outcome == 'REPORTED_VERIFIED', 'EFFECT_APPROVAL_VERIFIED_RESULT_REQUIRED')
    require_deadline_current(request.deadline, previous_clock, current_clock)
    require_clock_progress(previous_clock, transcript.observed_clock)
    require_clock_progress(transcript.observed_clock, current_clock)
    require(transcript.observed_clock.monotonic_ns >= request.deadline.issued_monotonic_ns,
            'EFFECT_APPROVAL_PRECEDES_REQUEST')


@dataclass(frozen=True, slots=True)
class CpuEffectObservation:
    request_commitment: str
    operation_id: str
    identity: ProcessResourceIdentity
    job_digest: str
    observer_identity: ProcessResourceIdentity
    observer_commitment: str
    sequence: int
    clock: ClockSample
    state: ObservationState
    limit: CpuRateLimit | None
    target_state: str
    reason: str | None = None
    method: str = OBSERVATION_METHOD
    independence_class: str = INDEPENDENCE_CLASS

    def __post_init__(self):
        commitment(self.request_commitment); identifier(self.operation_id); commitment(self.job_digest)
        commitment(self.observer_commitment); bound_generation(self.sequence)
        for identity in (self.identity, self.observer_identity):
            require(type(identity) is ProcessResourceIdentity, 'EFFECT_PROCESS_REQUIRED'); identity.__post_init__()
        require(self.identity.pid != self.observer_identity.pid, 'EFFECT_SEPARATE_OBSERVER_REQUIRED')
        require(type(self.target_state) is str and self.target_state in
                ('LIVE_IN_OWNED_JOB', 'EXITED', 'NOT_IN_OWNED_JOB', 'UNAVAILABLE'), 'EFFECT_TARGET_STATE_INVALID')
        require(type(self.clock) is ClockSample, 'CLOCK_SAMPLE_REQUIRED'); self.clock.__post_init__()
        require(type(self.state) is ObservationState and type(self.method) is str and self.method == OBSERVATION_METHOD and
                type(self.independence_class) is str and self.independence_class == INDEPENDENCE_CLASS,
                'EFFECT_OBSERVATION_PROFILE_INVALID')
        if self.state is ObservationState.MEASURED:
            require(type(self.limit) is CpuRateLimit and self.reason is None, 'EFFECT_OBSERVATION_VALUE_INVALID')
            self.limit.__post_init__()
        else:
            require(self.limit is None, 'EFFECT_UNAVAILABLE_HAS_VALUE'); identifier(self.reason)

    def as_dict(self):
        self.__post_init__()
        value = {field.name: getattr(self, field.name) for field in fields(self)}
        value.update(profile=REAL_EFFECT_PROFILE, identity=_process_value(self.identity),
            observer_identity=_process_value(self.observer_identity), clock=_sample_value(self.clock),
            state=self.state.value, limit=None if self.limit is None else _limit_value(self.limit))
        return value

    @property
    def observation_commitment(self):
        return digest('owned-cpu-observation-v1', self.as_dict())

    @property
    def canonical_wire(self):
        return canonical_bytes(self.as_dict())


def decode_cpu_effect_observation(wire):
    require(type(wire) is bytes and 1 <= len(wire) <= MAX_REQUEST_BYTES, 'EFFECT_OBSERVATION_WIRE_SIZE')
    value = strict_loads(wire)
    _shape(value, {'profile'} | {field.name for field in fields(CpuEffectObservation)}, 'EFFECT_OBSERVATION_FIELDS')
    require(value['profile'] == REAL_EFFECT_PROFILE and canonical_bytes(value) == wire, 'EFFECT_OBSERVATION_PROFILE_OR_CANONICAL')
    require(type(value['state']) is str and value['state'] in (ObservationState.MEASURED.value, ObservationState.UNAVAILABLE.value),
            'EFFECT_OBSERVATION_STATE_INVALID')
    args = {name: item for name, item in value.items() if name != 'profile'}
    args.update(identity=_process(value['identity']), observer_identity=_process(value['observer_identity']),
        clock=_clock(value['clock']), state=ObservationState(value['state']),
        limit=None if value['limit'] is None else _limit(value['limit']))
    result = CpuEffectObservation(**args)
    require(result.canonical_wire == wire, 'EFFECT_OBSERVATION_ROUNDTRIP_MISMATCH')
    return result


def compare_cpu_observation(request, observation, previous_clock, current_clock, *, minimum_sequence):
    """Pure semantic comparison; current captured owners authenticate these inputs."""
    require(type(request) is OwnedCpuRequest and type(observation) is CpuEffectObservation,
            'EFFECT_COMPARISON_INPUT_REQUIRED')
    request.__post_init__(); observation.__post_init__(); bound_generation(minimum_sequence)
    require(observation.request_commitment == request.input_commitment and observation.operation_id == request.request_id
            and observation.identity == request.process_identity and observation.job_digest == request.job_digest
            and observation.observer_commitment == request.observer_commitment, 'EFFECT_OBSERVATION_BINDING_MISMATCH')
    require(observation.sequence >= minimum_sequence, 'EFFECT_OBSERVATION_REPLAY')
    require_deadline_current(request.deadline, previous_clock, current_clock)
    require_clock_progress(previous_clock, observation.clock); require_clock_progress(observation.clock, current_clock)
    require(observation.clock.monotonic_ns >= request.deadline.issued_monotonic_ns and
            current_clock.monotonic_ns - observation.clock.monotonic_ns <= request.maximum_observation_age_ns,
            'EFFECT_OBSERVATION_STALE')
    if observation.state is ObservationState.UNAVAILABLE or observation.target_state != 'LIVE_IN_OWNED_JOB':
        return 'UNAVAILABLE'
    return 'VERIFIED_MATCH' if observation.limit == request.target_limit else 'DISCREPANCY'
