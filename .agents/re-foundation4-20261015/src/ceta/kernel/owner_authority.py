"""Canonical owner-enrollment transitions on the captured kernel/store.

The optional native-owner predicate authenticates origin/currentness; values,
transcripts and positive test providers are not production authority. No method
waits for consent, dispatches an effect, or opens default runtime admission.
"""
from dataclasses import dataclass
import math
import time
import uuid

from ceta.contracts.events import StreamPosition
from ceta.contracts.kernel_transactions import (KernelResult, KERNEL_PROFILE,
    ZERO_BUDGET, basis_key, bound_generation, budget_key, budget_wire, control_wire,
    deadline_text, digest, encode_basis, identifier, intent_key, logical_key, object_value,
    read_budget, read_intent, require, resource_key, resource_wire, task_key, task_wire)
from ceta.contracts.owner_enrollment import (EnrollmentRequest, decode_enrollment_request,
    decode_enrollment_transcript, enrollment_transcript_bytes, enrollment_transcript_commitment,
    require_enrollment_current, require_enrollment_transcript_binding)
from ceta.contracts.read_sets import ReadSet, ResourceRevision
from ceta.contracts.real_effect import (CAP_OPERATION, RESTORE_OPERATION,
    OwnedCpuRequest, decode_native_approval_transcript, decode_owned_cpu_request,
    require_approval_binding, require_restoration_link)
from ceta.contracts.store_transactions import StoreChange, StoreKey
from ceta.contracts.temporal import ClockSample, require_clock_progress
from ceta.contracts.wire import ContractError, MAX_INTEGER, canonical_bytes, strict_loads

OWNER_PROFILE = 'ceta-kernel-owner-authority-v1'
ADAPTER_ID = 'adapter:owned-cpu-v1'
ADAPTER_VERSION = '1'
MAXIMUM_OWNER_CHECK_NS = 50_000_000
_PHASES = ('CHALLENGE', 'ENROLL', 'APPROVE_CAP', 'APPROVE_RESTORE', 'STOP', 'REVOKE', 'RECOVER')
_ROW_FIELDS = ('scope_id', 'enrollment_id', 'request_wire', 'state', 'authority_generation', 'fence_generation',
    'policy_generation', 'challenge_event_ref', 'enrollment_event_ref', 'enrollment_transcript_wire', 'grant_key',
    'cap_approval', 'restore_approval', 'stop_reason_ref')


def enrollment_key(installation, enrollment_id):
    return logical_key('projection', installation, 'owner-enrollment', enrollment_id)


def owner_profile_key(installation):
    return StoreKey('projection', installation, 'owner-authority-profile')


def ceremony_key(installation, kind, value):
    require(kind in ('challenge', 'nonce'), 'OWNER_CEREMONY_KIND_INVALID')
    return logical_key('projection', installation, 'owner-'+kind, value)


def grant_key_for(enrollment):
    return logical_key('grant', enrollment.installation_id, 'owner-grant', enrollment.request_id)


def worker_resource(request):
    return 'worker:'+digest('owned-cpu-worker', {'process': request.as_dict()['process_identity'],
                                               'job': request.job_digest})[7:]


def resource_revision(request):
    return digest('owned-cpu-resource', {'identity': request.as_dict()['process_identity'],
        'job': request.job_digest, 'expected_limit': request.as_dict()['expected_limit']})


def owned_cpu_proposal(codec, request):
    """Deterministic ActionProposal data; only the canonical transition approves."""
    require(type(request) is OwnedCpuRequest, 'OWNER_EFFECT_REQUEST_REQUIRED')
    request.__post_init__()
    record = dict(record_type='ActionProposal', schema_version='1', record_id=request.proposal_id,
        scope_id=request.scope_id, causation_ref=request.request_id, task_id=request.task_id,
        request_ref=request.request_id, proposal_revision=request.input_commitment,
        adapter_id=ADAPTER_ID, adapter_version=ADAPTER_VERSION, operation=request.operation,
        arguments_ref=request.request_id, arguments_commitment=request.input_commitment,
        resources=[dict(resource_id=worker_resource(request), revision=resource_revision(request),
                        access='WRITE', scope_id=request.scope_id)],
        expected_predicate_refs=['predicate:owned-worker-current', 'predicate:exact-cpu-policy'],
        candidate_artifact_refs=[], dependencies=[], required_review_classes=[],
        requires_human_approval=True, budget=request.operation_budget.as_dict(),
        failure_plan_ref='plan:owned-cpu-reconcile', compensation_plan_ref='plan:separate-approved-restore',
        context_ref=request.request_id, model_configuration_id=None, status='VALIDATED')
    return codec.decode(canonical_bytes(record))


def _registry(enrollment):
    operations = [dict(adapter_id=ADAPTER_ID, adapter_version=ADAPTER_VERSION,
                       adapter_commitment=enrollment.adapter_commitment, operation=operation)
                  for operation in (CAP_OPERATION, RESTORE_OPERATION)]
    return canonical_bytes(dict(profile=KERNEL_PROFILE, scope_id=enrollment.installation_id,
        commitment=digest('owner-operation-registry', operations), operations=operations))


def _row(wire):
    return object_value(wire, _ROW_FIELDS, OWNER_PROFILE)


def _wire(value):
    return canonical_bytes(dict(value, profile=OWNER_PROFILE))


def _new_id(prefix):
    return prefix+uuid.uuid4().hex


@dataclass(frozen=True, slots=True)
class OwnerAuthorityState:
    """Historical metadata, never a native authority or replay instruction."""
    wire: bytes

    def __post_init__(self):
        require(type(self.wire) is bytes, 'OWNER_STATE_BYTES_REQUIRED')
        _row(self.wire)

    def as_dict(self):
        return _row(self.wire)


class KernelOwnerAuthority:
    """Private delegation on the same kernel, codec, store and captured owners."""

    def __init__(self, kernel):
        self.k = kernel
        try:
            info = time.get_clock_info('perf_counter')
        except (OSError, ValueError) as error:
            raise ContractError('OWNER_ELAPSED_CLOCK_UNAVAILABLE') from error
        require(info.monotonic is True and info.adjustable is False
                and type(info.resolution) is float and math.isfinite(info.resolution)
                and info.resolution > 0, 'OWNER_ELAPSED_CLOCK_UNAVAILABLE')
        self._resolution_ns = math.ceil(info.resolution*1_000_000_000)
        require(1 <= self._resolution_ns <= MAXIMUM_OWNER_CHECK_NS//2, 'OWNER_ELAPSED_CLOCK_UNAVAILABLE')

    def _expected(self, context):
        method = getattr(self.k._owners, 'owner_enrollment_expected', None)
        require(callable(method), 'OWNER_ENROLLMENT_PROVIDER_UNAVAILABLE')
        result = method(context)
        require(type(result) is EnrollmentRequest, 'OWNER_EXPECTED_ENROLLMENT_REQUIRED')
        return decode_enrollment_request(result.canonical_wire)

    def _guard(self, phase, enrollment, request, transcript, native_proof, peer, context):
        require(phase in _PHASES, 'OWNER_PHASE_INVALID')
        started = time.perf_counter_ns()
        require(type(started) is int and 0 <= started <= MAX_INTEGER, 'OWNER_ELAPSED_COUNTER_INVALID')
        require(self.k._peer(context) == peer, 'OWNER_PEER_CHANGED')
        require((peer.principal_id, peer.session_id) == (enrollment.principal_id, enrollment.actor_session),
                'OWNER_PEER_BINDING_MISMATCH')
        expected = self._expected(context)
        require(expected.canonical_wire == enrollment.canonical_wire, 'OWNER_EXPECTED_ENROLLMENT_CHANGED')
        samples = self.k._clock(progress=False)
        previous, sample = (ClockSample(**{name: getattr(value, name) for name in ClockSample.__dataclass_fields__})
                            for value in samples)
        require_clock_progress(previous, sample)
        highwater = getattr(self, '_highwater', None)
        if highwater is not None: require_clock_progress(highwater, sample)
        if phase not in ('STOP', 'REVOKE', 'RECOVER'):
            require_enrollment_current(enrollment, expected, previous, sample)
            if phase == 'ENROLL':
                require_enrollment_transcript_binding(enrollment, expected, transcript, previous, sample)
            if request is not None:
                self._effect_binding(enrollment, request)
                require_approval_binding(request, transcript, previous, sample)
                require(0 <= sample.monotonic_ns-request.expected_limit.observed_monotonic_ns
                        <= request.maximum_observation_age_ns, 'OWNER_EFFECT_OBSERVATION_STALE')
        method = getattr(self.k._owners, 'require_owner_authority_current', None)
        require(callable(method), 'OWNER_AUTHORITY_PROVIDER_UNAVAILABLE')
        # FINAL external owner/clock callback: one coordinated current native view.
        # No subsequent independent authentication/clock call reopens that seam.
        require(method(phase, enrollment, request, transcript, native_proof, peer, context) is None,
                'OWNER_NATIVE_DECISION_INVALID')
        finished = time.perf_counter_ns()
        require(type(finished) is int and started <= finished <= MAX_INTEGER, 'OWNER_ELAPSED_COUNTER_INVALID')
        # Charge two endpoint resolution units conservatively. Python3.12's
        # GetTickCount64 monotonic clock can report0 across a real3ms callback;
        # the selected Windows perf_counter stopwatch uses measured QPC.
        elapsed = finished-started+2*self._resolution_ns
        require(0 <= elapsed <= MAXIMUM_OWNER_CHECK_NS, 'OWNER_NATIVE_CHECK_TOO_SLOW')
        if phase not in ('STOP', 'REVOKE', 'RECOVER'):
            for deadline in (enrollment.deadline,) if request is None else (enrollment.deadline, request.deadline):
                require(sample.monotonic_ns+elapsed < deadline.expires_monotonic_ns
                        and sample.latest_wall_ns+elapsed < deadline.expires_wall_ns,
                        'OWNER_DEADLINE_ELAPSED')
            if transcript is not None:
                require(sample.monotonic_ns+elapsed-transcript.observed_clock.monotonic_ns
                        <= enrollment.maximum_observation_age_ns, 'OWNER_TRANSCRIPT_ELAPSED')
            if request is not None:
                require(sample.monotonic_ns+elapsed-request.expected_limit.observed_monotonic_ns
                        <= request.maximum_observation_age_ns, 'OWNER_EFFECT_OBSERVATION_STALE')
        self._highwater = sample
        return sample

    @staticmethod
    def _effect_binding(enrollment, request):
        require(all(getattr(request, name) == getattr(enrollment, name) for name in
            ('scope_id', 'principal_id', 'actor_session', 'owner_session_nonce', 'policy_commitment',
             'adapter_commitment', 'environment_commitment', 'source_commitment')), 'OWNER_EFFECT_ENROLLMENT_MISMATCH')
        require(request.process_identity.image_digest == enrollment.worker_image_commitment,
                'OWNER_WORKER_IMAGE_MISMATCH')
        require(request.maximum_duration_ns <= enrollment.maximum_effect_duration_ns
                and request.maximum_observation_age_ns <= enrollment.maximum_observation_age_ns
                and request.required_outcome_bytes <= enrollment.evidence_reserve_bytes,
                'OWNER_EFFECT_LIMIT_EXCEEDED')
        a, b = enrollment.deadline, request.deadline
        require((a.boot_id, a.durable_epoch, a.resume_generation) == (b.boot_id, b.durable_epoch, b.resume_generation)
                and a.issued_monotonic_ns <= b.issued_monotonic_ns < b.expires_monotonic_ns <= a.expires_monotonic_ns
                and a.issued_earliest_wall_ns <= b.issued_earliest_wall_ns < b.expires_wall_ns <= a.expires_wall_ns,
                'OWNER_EFFECT_DEADLINE_OUTSIDE_ENROLLMENT')
        available = enrollment.recovery_budget if request.operation == RESTORE_OPERATION else enrollment.authority_budget.subtract(enrollment.recovery_budget)
        require(available.contains(request.operation_budget), 'OWNER_EFFECT_BUDGET_EXCEEDED')

    def _decision(self, enrollment, phase, outcome, cells, request=None, transcript=None):
        return self.k._codec.decode(canonical_bytes(dict(record_type='PolicyDecision', schema_version='1',
            record_id=_new_id('decision:'), scope_id=enrollment.installation_id, causation_ref=enrollment.request_id,
            request_ref=enrollment.request_id if request is None else request.request_id,
            policy_commitment=enrollment.policy_commitment, rule_refs=['rule:owned-cpu-session-v1'],
            evaluated_inputs_commitment=digest('owner-authority-'+phase.lower(), dict(
                enrollment=enrollment.input_commitment, effect=None if request is None else request.input_commitment,
                transcript=None if transcript is None else (enrollment_transcript_commitment(transcript)
                    if phase == 'ENROLL' else transcript.transcript_commitment))),
            relevant_revision_refs=[cell.revision for cell in cells.values()], outcome=outcome,
            reason_codes=['CAPTURED_OWNER_PREDICATE_PASSED'],
            obligation_refs=['obligation:retained-native-admission', 'obligation:independent-durable-outcome'],
            revalidation_triggers=['trigger:stop', 'trigger:revocation', 'trigger:boot', 'trigger:source', 'trigger:policy'],
            authority_owner_id='kernel:cmp02')))

    def _commit(self, enrollment, phase, peer, context, cells, values, *, request=None,
                transcript=None, native_proof=None, grant=None, proposal=None, event_id=None):
        event_id = event_id or _new_id('event:')
        outcome = 'SEEK_AUTHORITY' if phase == 'CHALLENGE' else ('DENY' if phase in ('STOP', 'REVOKE') else 'ALLOW')
        decision = self._decision(enrollment, phase, outcome, cells, request, transcript)
        sample = self._guard(phase, enrollment, request, transcript, native_proof, peer, context)
        records = [(decision, event_id, 'kernel.owner.'+phase.lower())]
        if grant is not None: records.append((grant, _new_id('event:'), 'kernel.owner.grant.'+phase.lower()))
        if proposal is not None: records.append((proposal, _new_id('event:'), 'kernel.owner.preparation.'+phase.lower()))
        points = {record.as_dict()['scope_id']: self.k._store.position(record.as_dict()['scope_id']) for record, _, _ in records}
        next_points = dict(points); entries = []; event_by_scope = {}; grant_event = None
        for record, identity, kind in records:
            scope = record.as_dict()['scope_id']; point = next_points[scope]
            entry = self.k._entry(point, record, identity, kind, peer, sample)
            entries.append(entry)
            head = self.k._events.preimages(entry.event_wire).head
            next_points[scope] = StreamPosition(scope, point.next_sequence+1, head)
            event_by_scope.setdefault(scope, identity)
            if record.record_type == 'StandingGrant': grant_event = identity
        def guard(): self._guard(phase, enrollment, request, transcript, native_proof, peer, context)
        changes = tuple(StoreChange(self.k._expect(cells[key]), wire,
            grant_event if key.collection == 'grant' else event_by_scope[key.scope_id]) for key, wire in values.items())
        committed = self.k._store.commit(tuple(points.values()), tuple(entries),
            checks=tuple(self.k._expect(cell) for cell in cells.values()), changes=changes, guard=guard)
        # A denied return never rewrites committed enrollment/grant/tombstone rows.
        # This is a publication snapshot, not an effect lease retained after return.
        after = self.k._snapshot(tuple(cells))
        require(all(after[key].value_wire == values.get(key, cell.value_wire)
                    and after[key].generation == cell.generation+(1 if key in values else 0)
                    for key, cell in cells.items()), 'OWNER_POST_COMMIT_STATE_CHANGED')
        guard()
        return KernelResult(decision.canonical_wire, entries[0].event_wire, points[enrollment.installation_id], committed)

    def _read(self, enrollment_id, context):
        identifier(enrollment_id)
        peer = self.k._peer(context)
        key = enrollment_key(self.k._installation, enrollment_id)
        initial = self.k._snapshot((key,))
        value = _row(self.k._present(initial, key))
        enrollment = decode_enrollment_request(value['request_wire'].encode('utf-8'))
        require(value['scope_id'] == enrollment.installation_id == self.k._installation
                and value['enrollment_id'] == enrollment.request_id == enrollment_id, 'OWNER_ENROLLMENT_KEY_MISMATCH')
        return peer, key, initial[key], value, enrollment

    def _current(self, cells, row, enrollment):
        require(row['state'] == 'ENROLLED', 'OWNER_ENROLLMENT_NOT_ACTIVE')
        control = object_value(self.k._present(cells, self.k._control),
            ('scope_id', 'authority_generation', 'fence_generation', 'policy_commitment', 'environment_commitment'))
        require(control_wire(control['scope_id'], control['authority_generation'], control['fence_generation'],
                    control['policy_commitment'], control['environment_commitment']) == self.k._present(cells, self.k._control)
                and control['scope_id'] == enrollment.installation_id
                and control['authority_generation'] == row['authority_generation']
                and control['fence_generation'] == row['fence_generation']
                and control['policy_commitment'] == enrollment.policy_commitment
                and control['environment_commitment'] == enrollment.environment_commitment
                and self.k._present(cells, self.k._registry) == _registry(enrollment), 'OWNER_CURRENT_CONTROL_CHANGED')
        return control

    def begin(self, request_wire, context):
        enrollment = decode_enrollment_request(request_wire)
        peer = self.k._peer(context)
        require(enrollment.installation_id == self.k._installation and enrollment.scope_id != self.k._installation,
                'OWNER_INSTALLATION_SCOPE_MISMATCH')
        require(enrollment.authority_generation == enrollment.policy_generation == 0,
                'OWNER_FRESH_BOOTSTRAP_GENERATIONS_REQUIRED')
        self.k._store.position(enrollment.scope_id)
        key = enrollment_key(self.k._installation, enrollment.request_id)
        profile = owner_profile_key(self.k._installation)
        challenge = ceremony_key(self.k._installation, 'challenge', enrollment.challenge_id)
        nonce = ceremony_key(self.k._installation, 'nonce', enrollment.ceremony_nonce)
        cells = self.k._snapshot((key, profile, challenge, nonce, self.k._control, self.k._registry))
        require(all(cell.generation == 0 for cell in cells.values()), 'OWNER_BOOTSTRAP_ALREADY_DESIGNATED')
        event = _new_id('event:')
        row = dict(scope_id=self.k._installation, enrollment_id=enrollment.request_id,
            request_wire=enrollment.canonical_wire.decode('utf-8'), state='CHALLENGE', authority_generation=0, fence_generation=0,
            policy_generation=0, challenge_event_ref=event, enrollment_event_ref=None, enrollment_transcript_wire=None,
            grant_key=None, cap_approval=None, restore_approval=None, stop_reason_ref=None)
        values = {key: _wire(row), profile: _wire(dict(scope_id=self.k._installation,
            enrollment_id=enrollment.request_id, request_commitment=enrollment.input_commitment)),
            self.k._control: control_wire(self.k._installation, 0, 0, enrollment.policy_commitment, enrollment.environment_commitment),
            self.k._registry: _registry(enrollment)}
        for target, kind, value in ((challenge, 'challenge', enrollment.challenge_id), (nonce, 'nonce', enrollment.ceremony_nonce)):
            values[target] = _wire(dict(scope_id=self.k._installation, kind=kind, value=value,
                enrollment_id=enrollment.request_id, request_commitment=enrollment.input_commitment,
                state='RESERVED', event_ref=event))
        return self._commit(enrollment, 'CHALLENGE', peer, context, cells, values, event_id=event)

    def enroll(self, request_wire, transcript_wire, native_proof, context):
        enrollment = decode_enrollment_request(request_wire)
        transcript = decode_enrollment_transcript(transcript_wire)
        peer, key, before, row, stored = self._read(enrollment.request_id, context)
        require(stored.canonical_wire == enrollment.canonical_wire and row['state'] == 'CHALLENGE', 'OWNER_CHALLENGE_NOT_PENDING')
        challenge = ceremony_key(self.k._installation, 'challenge', enrollment.challenge_id)
        nonce = ceremony_key(self.k._installation, 'nonce', enrollment.ceremony_nonce)
        cells = self.k._snapshot((key, challenge, nonce, self.k._control, self.k._registry))
        require(cells[key] == before, 'OWNER_CHALLENGE_CHANGED')
        require(self.k._present(cells, self.k._control) == control_wire(self.k._installation, 0, 0,
                enrollment.policy_commitment, enrollment.environment_commitment)
                and self.k._present(cells, self.k._registry) == _registry(enrollment), 'OWNER_BOOTSTRAP_STATE_CHANGED')
        event = _new_id('event:'); values = {}
        for target, kind, value in ((challenge, 'challenge', enrollment.challenge_id), (nonce, 'nonce', enrollment.ceremony_nonce)):
            old = _wire(dict(scope_id=self.k._installation, kind=kind, value=value,
                enrollment_id=enrollment.request_id, request_commitment=enrollment.input_commitment,
                state='RESERVED', event_ref=row['challenge_event_ref']))
            require(self.k._present(cells, target) == old, 'OWNER_CEREMONY_ALREADY_CONSUMED')
            values[target] = _wire(dict(strict_loads(old), state='CONSUMED', event_ref=event))
        row.update(state='ENROLLED', authority_generation=1, fence_generation=1, enrollment_event_ref=event,
            enrollment_transcript_wire=enrollment_transcript_bytes(transcript).decode('utf-8'))
        values[key] = _wire(row)
        values[self.k._control] = control_wire(self.k._installation, 1, 1,
            enrollment.policy_commitment, enrollment.environment_commitment)
        return self._commit(enrollment, 'ENROLL', peer, context, cells, values,
                            transcript=transcript, native_proof=native_proof, event_id=event)

    def approve(self, enrollment_id, request_wire, transcript_wire, native_proof, context):
        request = decode_owned_cpu_request(request_wire)
        transcript = decode_native_approval_transcript(transcript_wire)
        peer, key, before, row, enrollment = self._read(enrollment_id, context)
        self._effect_binding(enrollment, request)
        require(transcript.helper_commitment == enrollment.helper_commitment
                and transcript.ui_commitment == enrollment.ui_commitment, 'OWNER_APPROVAL_CODE_MISMATCH')
        require(transcript.challenge_id != enrollment.challenge_id and transcript.ceremony_nonce != enrollment.ceremony_nonce,
                'OWNER_ENROLLMENT_CEREMONY_REUSED')
        cap = request.operation == CAP_OPERATION; field = 'cap_approval' if cap else 'restore_approval'
        require(row[field] is None, 'OWNER_EFFECT_ALREADY_APPROVED')
        grant_key = grant_key_for(enrollment); liability = budget_key(grant_key)
        proposal = owned_cpu_proposal(self.k._codec, request)
        prepared = basis_key(request.scope_id, request.proposal_id)
        task = task_key(request.scope_id, request.task_id); resource = resource_key(request.scope_id, worker_resource(request))
        challenge = ceremony_key(self.k._installation, 'challenge', transcript.challenge_id)
        nonce = ceremony_key(self.k._installation, 'nonce', transcript.ceremony_nonce)
        request_key = logical_key('projection', self.k._installation, 'owner-effect', request.request_id)
        selected = (key, self.k._control, self.k._registry, grant_key, liability, prepared, task, resource, challenge, nonce, request_key)
        original = None; issuance = None
        if not cap:
            require(type(row['cap_approval']) is dict, 'OWNER_CAP_APPROVAL_REQUIRED')
            original = decode_owned_cpu_request(row['cap_approval']['request_wire'].encode('utf-8'))
            require_restoration_link(original, request)
            issuance = logical_key('projection', original.scope_id, 'issuance', original.proposal_id)
            selected += (issuance,)
        cells = self.k._snapshot(selected)
        require(cells[key] == before, 'OWNER_ENROLLMENT_CHANGED')
        control = self._current(cells, row, enrollment)
        require(all(cells[target].generation == 0 for target in (prepared, challenge, nonce, request_key)),
                'OWNER_APPROVAL_IDENTITY_REPLAY')
        event = _new_id('event:'); grant = None
        if cap:
            require(all(cells[target].generation == 0 for target in (grant_key, liability, task, resource)),
                    'OWNER_RESOURCE_ALREADY_DESIGNATED')
            grant = self.k._codec.decode(canonical_bytes(dict(record_type='StandingGrant', schema_version='1',
                record_id=grant_key.record_id, scope_id=grant_key.scope_id, causation_ref=event,
                issuer_id='kernel:cmp02', grantee_id=peer.principal_id, purpose_ref=request.task_id,
                resource_scope=[dict(resource_id=worker_resource(request), scope_id=request.scope_id, revision=None, access='WRITE')],
                operation_classes=[CAP_OPERATION, RESTORE_OPERATION], budget=enrollment.authority_budget.as_dict(),
                valid_from=deadline_text(enrollment.deadline.issued_earliest_wall_ns),
                expires_at=deadline_text(enrollment.deadline.expires_wall_ns), revocation_generation=0,
                delegation='PROHIBITED', trigger_refs=[], policy_commitment=enrollment.policy_commitment,
                approval_evidence_ref=event, issuance_evidence_ref=event, status='ACTIVE')))
            budget = budget_wire(grant_key.scope_id, grant_key.record_id, enrollment.authority_budget, enrollment.recovery_budget)
        else:
            current_grant = self.k._decode(self.k._present(cells, grant_key), 'StandingGrant').as_dict()
            require(row['grant_key'] == grant_key.as_dict() and current_grant['status'] == 'ACTIVE', 'OWNER_GRANT_NOT_ACTIVE')
            require(self.k._present(cells, task) == task_wire(request.scope_id, request.task_id, original.task_revision)
                    and original.task_revision == request.task_revision, 'OWNER_RESTORATION_TASK_CHANGED')
            issued = object_value(self.k._present(cells, issuance),
                ('scope_id', 'proposal_id', 'permit_id', 'issuance_event_ref', 'sequence', 'previous_head'))
            permit_key = StoreKey('permit', original.scope_id, issued['permit_id'])
            intention_key = intent_key(original.scope_id, issued['permit_id'])
            expanded = self.k._snapshot(tuple(cells)+(permit_key, intention_key))
            require(all(expanded[target] == cell for target, cell in cells.items()), 'OWNER_RESTORATION_STATE_CHANGED')
            cells = expanded
            permit = self.k._decode(self.k._present(cells, permit_key), 'OperationPermit').as_dict()
            intention = read_intent(self.k._present(cells, intention_key))
            require(issued['scope_id'] == original.scope_id and issued['proposal_id'] == original.proposal_id
                    and permit['status'] == 'CONSUMED' and permit['proposal_ref'] == original.proposal_id
                    and intention['state'] == 'ADMISSION_REDEEMED'
                    and intention['basis_wire'] == row['cap_approval']['basis_wire']
                    and intention['grant_key'] == grant_key.as_dict(), 'OWNER_CAP_NOT_CANONICALLY_CONSUMED')
            # Resolve the existing exact durable event/index/payload/peer binding;
            # a consumed label in an otherwise coherent store is insufficient.
            self.k._resolve_consumption(self.k._decode(self.k._present(cells, permit_key), 'OperationPermit'), peer=peer)
            limit, recovery, held, charged = read_budget(self.k._present(cells, liability), liability)
            require(limit == enrollment.authority_budget and recovery == enrollment.recovery_budget
                    and held == ZERO_BUDGET and charged == original.operation_budget, 'OWNER_RESTORATION_LIABILITY_MISMATCH')
            require(limit.subtract(charged).contains(request.operation_budget), 'OWNER_RESTORATION_BUDGET_EXHAUSTED')
            budget = budget_wire(grant_key.scope_id, grant_key.record_id, limit, ZERO_BUDGET, held, charged)
        read_set = ReadSet(request.scope_id, control['authority_generation'], control['fence_generation'],
            enrollment.policy_commitment, enrollment.environment_commitment,
            (ResourceRevision(worker_resource(request), resource_revision(request)),))
        basis = encode_basis(proposal, grant_key, read_set, principal_id=peer.principal_id,
            actor_session=peer.session_id, adapter_commitment=enrollment.adapter_commitment,
            registry_commitment=strict_loads(_registry(enrollment))['commitment'], owner_input_commitment=request.input_commitment,
            candidate_commitment=None, task_revision=request.task_revision, review_refs=(), approval_evidence_ref=event)
        approval = dict(request_wire=request.canonical_wire.decode('utf-8'), transcript_wire=transcript.canonical_wire.decode('utf-8'),
            proposal_wire=proposal.canonical_wire.decode('utf-8'), basis_wire=basis.decode('utf-8'), decision_event_ref=event)
        row[field] = approval; row['grant_key'] = grant_key.as_dict()
        values = {key: _wire(row), liability: budget, prepared: basis,
            task: task_wire(request.scope_id, request.task_id, request.task_revision),
            resource: resource_wire(request.scope_id, worker_resource(request), resource_revision(request)),
            request_key: _wire(dict(scope_id=self.k._installation, enrollment_id=enrollment_id,
                request_commitment=request.input_commitment, decision_event_ref=event))}
        if cap: values[grant_key] = grant.canonical_wire
        for target, kind, value in ((challenge, 'challenge', transcript.challenge_id), (nonce, 'nonce', transcript.ceremony_nonce)):
            values[target] = _wire(dict(scope_id=self.k._installation, kind=kind, value=value,
                enrollment_id=enrollment_id, request_commitment=request.input_commitment, state='CONSUMED', event_ref=event))
        return self._commit(enrollment, 'APPROVE_CAP' if cap else 'APPROVE_RESTORE', peer, context, cells, values,
            request=request, transcript=transcript, native_proof=native_proof, grant=grant, proposal=proposal, event_id=event)

    def stop(self, enrollment_id, context, reason_ref, *, revoke=False):
        identifier(reason_ref)
        peer, key, before, row, enrollment = self._read(enrollment_id, context)
        require(row['state'] in ('CHALLENGE', 'ENROLLED'), 'OWNER_ENROLLMENT_ALREADY_STOPPED')
        grant_key = grant_key_for(enrollment)
        cells = self.k._snapshot((key, self.k._control, self.k._registry, grant_key))
        require(cells[key] == before, 'OWNER_ENROLLMENT_CHANGED')
        control = object_value(self.k._present(cells, self.k._control),
            ('scope_id', 'authority_generation', 'fence_generation', 'policy_commitment', 'environment_commitment'))
        require(control_wire(control['scope_id'], control['authority_generation'], control['fence_generation'],
                    control['policy_commitment'], control['environment_commitment']) == self.k._present(cells, self.k._control)
                and control['scope_id'] == enrollment.installation_id
                and control['authority_generation'] == row['authority_generation']
                and control['fence_generation'] == row['fence_generation']
                and control['policy_commitment'] == enrollment.policy_commitment
                and control['environment_commitment'] == enrollment.environment_commitment, 'OWNER_CURRENT_CONTROL_CHANGED')
        generation = bound_generation(control['authority_generation']+1)
        fence = bound_generation(control['fence_generation']+1)
        row.update(state='REVOKED' if revoke else 'STOPPED', authority_generation=generation, fence_generation=fence, stop_reason_ref=reason_ref)
        values = {key: _wire(row), self.k._control: control_wire(self.k._installation, generation, fence,
            enrollment.policy_commitment, enrollment.environment_commitment)}
        grant = None
        if cells[grant_key].value_wire is not None:
            value = self.k._decode(self.k._present(cells, grant_key), 'StandingGrant').as_dict()
            require(value['status'] in ('ACTIVE', 'EXHAUSTED', 'REVOKED'), 'OWNER_GRANT_STATE_INVALID')
            value.update(status='REVOKED', revocation_generation=bound_generation(value['revocation_generation']+1), causation_ref=reason_ref)
            grant = self.k._codec.decode(canonical_bytes(value)); values[grant_key] = grant.canonical_wire
        return self._commit(enrollment, 'REVOKE' if revoke else 'STOP', peer, context, cells, values, grant=grant)

    def recover(self, enrollment_id, context):
        peer, key, before, row, enrollment = self._read(enrollment_id, context)
        cells = self.k._snapshot((key,))
        require(cells[key] == before, 'OWNER_RECOVERY_STATE_CHANGED')
        self._guard('RECOVER', enrollment, None, None, None, peer, context)
        return OwnerAuthorityState(before.value_wire)
