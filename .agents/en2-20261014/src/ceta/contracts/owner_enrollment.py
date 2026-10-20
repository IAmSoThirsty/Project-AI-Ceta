"""Bounded owner-enrollment DATA_ONLY values; no native observation or authority.

The captured canonical owner supplies expected values and clock samples. Pure
equality/currentness checks cannot authenticate them or consume a challenge.
"""
from dataclasses import dataclass, fields
import re
import uuid

from .kernel_transactions import (BUDGET_FIELDS, BudgetVector, bound_generation,
    commitment, deadline_wire, digest, identifier, require)
from .real_effect import (REAL_EFFECT_PROFILE, CAP_OPERATION, RESTORE_OPERATION,
    NativeApprovalTranscript, decode_native_approval_transcript)
from .resource_management import ProcessResourceIdentity, ResourceVector
from .temporal import ClockSample, Deadline, require_clock_progress, require_deadline_current
from .wire import ContractError, MAX_INTEGER, canonical_bytes, strict_loads

ENROLLMENT_PROFILE = 'ceta-owner-enrollment-data-v1'
ENROLLMENT_KIND = 'OWNER_ENROLLMENT_REQUEST'
ENROLLMENT_TRANSCRIPT_KIND = 'OWNER_ENROLLMENT_NATIVE_TRANSCRIPT'
MAX_ENROLLMENT_BYTES = 32768
MAX_SESSION_NS = 300_000_000_000
MAX_CLOCK_UNCERTAINTY_NS = 250_000_000
MAXIMUM_WORKERS = 1
MAXIMUM_EFFECTS = 2
_RESERVED = re.compile(r'(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', re.I)


def _integer(value, minimum, maximum, code):
    require(type(value) is int and minimum <= value <= maximum, code)


def _hex(value, digits, code):
    require(type(value) is str and re.fullmatch('[0-9a-f]{'+str(digits)+'}', value) is not None, code)


def _nonce(value):
    _hex(value, 32, 'ENROLLMENT_NONCE_INVALID')
    require(value != '0'*32, 'ENROLLMENT_NONCE_INVALID')


def _shape(value, names, code):
    require(type(value) is dict and set(value) == set(names), code)
    return value


def _native_path(value):
    require(type(value) is str and 1 <= len(value) <= 2048, 'ENROLLMENT_NATIVE_PATH_INVALID')
    match = re.fullmatch(r'\\\\\?\\Volume\{([0-9a-f-]{36})\}\\(.+)', value)
    require(match is not None, 'ENROLLMENT_NATIVE_PATH_INVALID')
    try: canonical = str(uuid.UUID(match[1]))
    except ValueError as error:
        raise ContractError('ENROLLMENT_NATIVE_PATH_INVALID') from error
    require(canonical == match[1], 'ENROLLMENT_NATIVE_PATH_INVALID')
    components = match[2].split('\\')
    require(1 <= len(components) <= 16, 'ENROLLMENT_NATIVE_PATH_INVALID')
    for component in components:
        require(re.fullmatch(r'[A-Za-z0-9.][A-Za-z0-9._ -]{0,63}', component) is not None
                and component[-1] not in '. ' and not _RESERVED.fullmatch(component),
                'ENROLLMENT_NATIVE_PATH_INVALID')


def _sid(value):
    require(type(value) is str and 7 <= len(value) <= 184, 'ENROLLMENT_SID_INVALID')
    parts = value.split('-')
    require(4 <= len(parts) <= 18 and parts[:2] == ['S', '1'], 'ENROLLMENT_SID_INVALID')
    for index, part in enumerate(parts[2:]):
        require(re.fullmatch(r'0|[1-9][0-9]{0,14}', part) is not None, 'ENROLLMENT_SID_INVALID')
        require(int(part) <= (2**48-1 if index == 0 else 2**32-1), 'ENROLLMENT_SID_INVALID')


def _process(value):
    require(type(value) is ProcessResourceIdentity, 'ENROLLMENT_PROCESS_REQUIRED')
    value.__post_init__()
    _integer(value.creation_time, 1, MAX_INTEGER, 'ENROLLMENT_PROCESS_WIRE_RANGE')


def _record(value):
    return {field.name: getattr(value, field.name) for field in fields(value)}


@dataclass(frozen=True, slots=True)
class NativeObjectIdentity:
    path: str
    kind: str
    volume_serial_hex: str
    file_id_hex: str

    def __post_init__(self):
        _native_path(self.path)
        require(type(self.kind) is str and self.kind in ('directory', 'file'), 'ENROLLMENT_OBJECT_KIND_INVALID')
        _hex(self.volume_serial_hex, 16, 'ENROLLMENT_VOLUME_ID_INVALID')
        _hex(self.file_id_hex, 32, 'ENROLLMENT_FILE_ID_INVALID')

    def as_dict(self):
        self.__post_init__()
        return _record(self)


@dataclass(frozen=True, slots=True)
class OwnerTokenFacts:
    process_identity: ProcessResourceIdentity
    user_sid: str
    logon_sid: str
    authentication_luid_hex: str
    terminal_session: int
    token_id_hex: str
    modified_id_hex: str
    token_type: int
    impersonation_level: int
    integrity_sid: str
    integrity_attributes: int
    elevation_type: int
    ui_access: int
    has_restrictions: int
    restricted_sids: tuple[str, ...]

    def __post_init__(self):
        _process(self.process_identity)
        for name in ('user_sid', 'logon_sid', 'integrity_sid'): _sid(getattr(self, name))
        require(re.fullmatch(r'S-1-5-5-[0-9]+-[0-9]+', self.logon_sid) is not None
                and re.fullmatch(r'S-1-16-[0-9]+', self.integrity_sid) is not None
                and self.user_sid != self.logon_sid, 'ENROLLMENT_TOKEN_SID_ROLE_INVALID')
        for name in ('authentication_luid_hex', 'token_id_hex', 'modified_id_hex'):
            _hex(getattr(self, name), 16, 'ENROLLMENT_LUID_INVALID')
        for name in ('terminal_session', 'integrity_attributes'):
            _integer(getattr(self, name), 0, 2**32-1, 'ENROLLMENT_TOKEN_INTEGER_INVALID')
        _integer(self.token_type, 1, 2, 'ENROLLMENT_TOKEN_TYPE_INVALID')
        _integer(self.impersonation_level, 0, 3, 'ENROLLMENT_IMPERSONATION_LEVEL_INVALID')
        _integer(self.elevation_type, 1, 3, 'ENROLLMENT_ELEVATION_TYPE_INVALID')
        for name in ('ui_access', 'has_restrictions'):
            _integer(getattr(self, name), 0, 1, 'ENROLLMENT_TOKEN_FLAG_INVALID')
        require(type(self.restricted_sids) is tuple and len(self.restricted_sids) <= 16,
                'ENROLLMENT_RESTRICTED_SIDS_INVALID')
        for sid in self.restricted_sids: _sid(sid)
        require(self.restricted_sids == tuple(sorted(set(self.restricted_sids)))
                and (self.has_restrictions != 0 or not self.restricted_sids), 'ENROLLMENT_RESTRICTED_SIDS_INVALID')

    def as_dict(self):
        self.__post_init__()
        return dict(_record(self), process_identity=_record(self.process_identity), restricted_sids=list(self.restricted_sids))


@dataclass(frozen=True, slots=True)
class EnrollmentRequest:
    request_id: str
    installation_id: str
    scope_id: str
    principal_id: str
    actor_session: str
    owner_session_nonce: str
    clock_session_nonce: str
    challenge_id: str
    ceremony_nonce: str
    private_root: NativeObjectIdentity
    database: NativeObjectIdentity
    owner_facts: OwnerTokenFacts
    helper_identity: ProcessResourceIdentity
    ui_identity: ProcessResourceIdentity
    policy_generation: int
    authority_generation: int
    policy_commitment: str
    source_commitment: str
    environment_commitment: str
    helper_commitment: str
    ui_commitment: str
    adapter_commitment: str
    worker_image_commitment: str
    authority_budget: BudgetVector
    recovery_budget: BudgetVector
    resource_limit: ResourceVector
    evidence_reserve_bytes: int
    maximum_session_ns: int
    maximum_effect_duration_ns: int
    maximum_observation_age_ns: int
    deadline: Deadline

    def __post_init__(self):
        for name in ('request_id', 'installation_id', 'scope_id', 'principal_id', 'actor_session', 'challenge_id'):
            identifier(getattr(self, name))
        for name in ('owner_session_nonce', 'clock_session_nonce', 'ceremony_nonce'): _nonce(getattr(self, name))
        for identity in (self.private_root, self.database):
            require(type(identity) is NativeObjectIdentity, 'ENROLLMENT_NATIVE_OBJECT_REQUIRED'); identity.__post_init__()
        root, database = self.private_root, self.database
        require(root.kind == 'directory' and database.kind == 'file'
                and database.path == root.path+'\\history.sqlite3'
                and root.volume_serial_hex == database.volume_serial_hex
                and root.file_id_hex != database.file_id_hex, 'ENROLLMENT_PRIVATE_DATABASE_BINDING')
        require(type(self.owner_facts) is OwnerTokenFacts, 'ENROLLMENT_OWNER_FACTS_REQUIRED'); self.owner_facts.__post_init__()
        for identity in (self.helper_identity, self.ui_identity): _process(identity)
        identities = (self.owner_facts.process_identity, self.helper_identity, self.ui_identity)
        require(all(a.pid != b.pid or a == b for a in identities for b in identities), 'ENROLLMENT_PROCESS_ALIAS_CONFLICT')
        bound_generation(self.policy_generation); bound_generation(self.authority_generation)
        for name in ('policy_commitment', 'source_commitment', 'environment_commitment', 'helper_commitment',
                     'ui_commitment', 'adapter_commitment', 'worker_image_commitment'): commitment(getattr(self, name))
        _integer(self.maximum_session_ns, 1_000_000, MAX_SESSION_NS, 'ENROLLMENT_SESSION_BOUND_INVALID')
        _integer(self.maximum_effect_duration_ns, 1, 1_000_000_000, 'ENROLLMENT_EFFECT_BOUND_INVALID')
        _integer(self.maximum_observation_age_ns, 1, 5_000_000_000, 'ENROLLMENT_OBSERVATION_BOUND_INVALID')
        _integer(self.evidence_reserve_bytes, 8192, 1048576, 'ENROLLMENT_EVIDENCE_BOUND_INVALID')
        duration_ms = (self.maximum_effect_duration_ns+999_999)//1_000_000
        maximum_ms = self.maximum_session_ns//1_000_000
        for budget, effects, minimum_ms in ((self.authority_budget, 2, 2*duration_ms), (self.recovery_budget, 1, duration_ms)):
            require(type(budget) is BudgetVector, 'ENROLLMENT_BUDGET_REQUIRED'); budget.__post_init__()
            values = budget.as_dict()
            require(values['max_effects'] == effects and values['max_model_calls'] == values['max_input_tokens'] == values['max_output_tokens'] == 0
                    and minimum_ms <= values['wall_time_ms'] <= maximum_ms
                    and values['max_bytes_read'] <= 16*1024*1024 and values['max_bytes_written'] <= 1048576,
                    'ENROLLMENT_BUDGET_LIMIT_INVALID')
        require(self.authority_budget.contains(self.recovery_budget)
                and self.authority_budget.as_dict()['max_bytes_written'] >= self.evidence_reserve_bytes
                and self.recovery_budget.as_dict()['max_bytes_written'] >= 4096, 'ENROLLMENT_RECOVERY_EVIDENCE_INSUFFICIENT')
        available = self.authority_budget.subtract(self.recovery_budget).as_dict()
        require(available['max_bytes_written'] >= 4096 and available['wall_time_ms'] >= duration_ms,
                'ENROLLMENT_CAP_RESERVE_INSUFFICIENT')
        require(type(self.resource_limit) is ResourceVector, 'ENROLLMENT_RESOURCE_REQUIRED'); self.resource_limit.__post_init__()
        limit = self.resource_limit
        require(1 <= limit.cpu_milli <= 1000 and 1 <= limit.memory_bytes <= 64*1024*1024
                and 8192 <= limit.storage_bytes <= 16*1024*1024 and 2*duration_ms <= limit.wall_time_ms <= maximum_ms
                and limit.storage_bytes >= self.evidence_reserve_bytes, 'ENROLLMENT_RESOURCE_LIMIT_INVALID')
        require(type(self.deadline) is Deadline, 'DEADLINE_REQUIRED'); self.deadline.__post_init__()
        require(self.deadline.expires_monotonic_ns-self.deadline.issued_monotonic_ns <= self.maximum_session_ns
                and self.deadline.expires_wall_ns-self.deadline.issued_earliest_wall_ns <= self.maximum_session_ns+2*MAX_CLOCK_UNCERTAINTY_NS,
                'ENROLLMENT_DEADLINE_BOUND_INVALID')
        boot = re.fullmatch(r'boot:([0-9a-f-]{36}):session:([0-9a-f]{32})', self.deadline.boot_id)
        require(boot is not None and boot[2] == self.clock_session_nonce, 'ENROLLMENT_CLOCK_SESSION_MISMATCH')
        try: boot_guid = uuid.UUID(boot[1])
        except ValueError as error:
            raise ContractError('ENROLLMENT_BOOT_WITNESS_INVALID') from error
        require(str(boot_guid) == boot[1] and boot_guid.int != 0, 'ENROLLMENT_BOOT_WITNESS_INVALID')

    def as_dict(self):
        self.__post_init__()
        return dict(_record(self), profile=ENROLLMENT_PROFILE, kind=ENROLLMENT_KIND, assurance='DATA_ONLY',
            runtime_profile=REAL_EFFECT_PROFILE, allowed_operations=[CAP_OPERATION, RESTORE_OPERATION],
            maximum_workers=MAXIMUM_WORKERS, maximum_effects=MAXIMUM_EFFECTS,
            operation_limits={CAP_OPERATION: 1, RESTORE_OPERATION: 1},
            approval_mode='SEPARATE_CANONICAL_APPROVAL_PER_EFFECT',
            private_root=self.private_root.as_dict(), database=self.database.as_dict(), owner_facts=self.owner_facts.as_dict(),
            helper_identity=_record(self.helper_identity), ui_identity=_record(self.ui_identity),
            authority_budget=self.authority_budget.as_dict(), recovery_budget=self.recovery_budget.as_dict(),
            resource_limit=_record(self.resource_limit), deadline=deadline_wire(self.deadline))

    @property
    def canonical_wire(self):
        wire = canonical_bytes(self.as_dict())
        require(len(wire) <= MAX_ENROLLMENT_BYTES, 'ENROLLMENT_WIRE_SIZE')
        return wire

    @property
    def input_commitment(self):
        return digest('owner-enrollment-input-v1', self.as_dict())


_ENVELOPE = {'profile': ENROLLMENT_PROFILE, 'kind': ENROLLMENT_KIND, 'assurance': 'DATA_ONLY',
             'runtime_profile': REAL_EFFECT_PROFILE, 'allowed_operations': [CAP_OPERATION, RESTORE_OPERATION],
             'maximum_workers': MAXIMUM_WORKERS, 'maximum_effects': MAXIMUM_EFFECTS,
             'operation_limits': {CAP_OPERATION: 1, RESTORE_OPERATION: 1},
             'approval_mode': 'SEPARATE_CANONICAL_APPROVAL_PER_EFFECT'}


def _decode(wire):
    require(type(wire) is bytes and 1 <= len(wire) <= MAX_ENROLLMENT_BYTES, 'ENROLLMENT_WIRE_SIZE')
    value = strict_loads(wire)
    require(canonical_bytes(value) == wire, 'ENROLLMENT_NONCANONICAL')
    return value


def _typed(value, kind):
    _shape(value, (field.name for field in fields(kind)), 'ENROLLMENT_NESTED_FIELDS')
    return kind(**value)


def decode_enrollment_request(wire):
    value = _decode(wire)
    _shape(value, set(_ENVELOPE) | {field.name for field in fields(EnrollmentRequest)}, 'ENROLLMENT_REQUEST_FIELDS')
    require(all(type(value[name]) is type(expected) and value[name] == expected for name, expected in _ENVELOPE.items()),
            'ENROLLMENT_PROFILE_INVALID')
    require(all(type(count) is int for count in value['operation_limits'].values()), 'ENROLLMENT_PROFILE_INVALID')
    args = {name: item for name, item in value.items() if name not in _ENVELOPE}
    facts = dict(_shape(args['owner_facts'], (field.name for field in fields(OwnerTokenFacts)), 'ENROLLMENT_TOKEN_FIELDS'))
    require(type(facts['restricted_sids']) is list, 'ENROLLMENT_RESTRICTED_SIDS_INVALID')
    facts.update(process_identity=_typed(facts['process_identity'], ProcessResourceIdentity), restricted_sids=tuple(facts['restricted_sids']))
    args.update(private_root=_typed(args['private_root'], NativeObjectIdentity), database=_typed(args['database'], NativeObjectIdentity),
        owner_facts=OwnerTokenFacts(**facts), helper_identity=_typed(args['helper_identity'], ProcessResourceIdentity),
        ui_identity=_typed(args['ui_identity'], ProcessResourceIdentity), authority_budget=BudgetVector.from_dict(args['authority_budget']),
        recovery_budget=BudgetVector.from_dict(args['recovery_budget']), resource_limit=_typed(args['resource_limit'], ResourceVector),
        deadline=_typed(args['deadline'], Deadline))
    result = EnrollmentRequest(**args)
    require(result.canonical_wire == wire, 'ENROLLMENT_ROUNDTRIP_MISMATCH')
    return result


def enrollment_display_bytes(request):
    require(type(request) is EnrollmentRequest, 'ENROLLMENT_REQUEST_REQUIRED')
    return canonical_bytes({'display_profile': 'ceta-owner-enrollment-display-v1', 'assurance': 'DATA_ONLY',
        'request': request.as_dict(), 'input_commitment': request.input_commitment})


def enrollment_display_commitment(request):
    return digest('owner-enrollment-display-v1', strict_loads(enrollment_display_bytes(request)))


def require_enrollment_current(request, expected, previous_clock, current_clock):
    """DATA binding only: expected/current clocks must come from captured owners."""
    require(type(request) is EnrollmentRequest and type(expected) is EnrollmentRequest, 'ENROLLMENT_REQUEST_REQUIRED')
    for sample in (previous_clock, current_clock):
        require(type(sample) is ClockSample, 'CLOCK_SAMPLE_REQUIRED')
        sample.__post_init__()
    require(request.canonical_wire == expected.canonical_wire, 'ENROLLMENT_EXPECTED_BINDING_MISMATCH')
    require_deadline_current(request.deadline, previous_clock, current_clock)
    require(current_clock.uncertainty_ns <= MAX_CLOCK_UNCERTAINTY_NS
            and previous_clock.uncertainty_ns <= MAX_CLOCK_UNCERTAINTY_NS
            and current_clock.monotonic_ns-previous_clock.monotonic_ns <= request.maximum_observation_age_ns,
            'ENROLLMENT_CLOCK_BOUND_INVALID')


def enrollment_transcript_bytes(transcript):
    require(type(transcript) is NativeApprovalTranscript, 'ENROLLMENT_TRANSCRIPT_REQUIRED')
    wire = canonical_bytes({'profile': ENROLLMENT_PROFILE, 'kind': ENROLLMENT_TRANSCRIPT_KIND,
                           'assurance': 'DATA_ONLY', 'transcript': transcript.as_dict()})
    require(len(wire) <= MAX_ENROLLMENT_BYTES, 'ENROLLMENT_WIRE_SIZE')
    return wire


def enrollment_transcript_commitment(transcript):
    return digest('owner-enrollment-native-transcript-v1', strict_loads(enrollment_transcript_bytes(transcript)))


def decode_enrollment_transcript(wire):
    value = _shape(_decode(wire), ('profile', 'kind', 'assurance', 'transcript'), 'ENROLLMENT_TRANSCRIPT_FIELDS')
    require(value['profile'] == ENROLLMENT_PROFILE and value['kind'] == ENROLLMENT_TRANSCRIPT_KIND
            and value['assurance'] == 'DATA_ONLY', 'ENROLLMENT_TRANSCRIPT_DOMAIN_INVALID')
    transcript = decode_native_approval_transcript(canonical_bytes(value['transcript']))
    require(enrollment_transcript_bytes(transcript) == wire, 'ENROLLMENT_ROUNDTRIP_MISMATCH')
    return transcript


def require_enrollment_transcript_binding(request, expected, transcript, previous_clock, current_clock):
    """Declared data/result equality is never an authenticated enrollment event."""
    require_enrollment_current(request, expected, previous_clock, current_clock)
    require(type(transcript) is NativeApprovalTranscript, 'ENROLLMENT_TRANSCRIPT_REQUIRED'); transcript.__post_init__()
    require(transcript.challenge_id == request.challenge_id and transcript.ceremony_nonce == request.ceremony_nonce
            and transcript.request_commitment == request.input_commitment
            and transcript.displayed_commitment == enrollment_display_commitment(request), 'ENROLLMENT_TRANSCRIPT_REQUEST_MISMATCH')
    require(transcript.principal_id == request.principal_id and transcript.actor_session == request.actor_session
            and transcript.helper_identity == request.helper_identity and transcript.ui_identity == request.ui_identity
            and transcript.helper_commitment == request.helper_commitment and transcript.ui_commitment == request.ui_commitment,
            'ENROLLMENT_TRANSCRIPT_OWNER_MISMATCH')
    require(transcript.reported_outcome == 'REPORTED_VERIFIED', 'ENROLLMENT_REPORTED_VERIFIED_REQUIRED')
    require_clock_progress(previous_clock, transcript.observed_clock)
    require_clock_progress(transcript.observed_clock, current_clock)
    require(transcript.observed_clock.uncertainty_ns <= MAX_CLOCK_UNCERTAINTY_NS
            and transcript.observed_clock.monotonic_ns >= request.deadline.issued_monotonic_ns
            and current_clock.monotonic_ns-transcript.observed_clock.monotonic_ns <= request.maximum_observation_age_ns,
            'ENROLLMENT_TRANSCRIPT_STALE')
