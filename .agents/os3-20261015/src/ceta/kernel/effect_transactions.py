"""Owned CPU outcomes delegated by the existing kernel to its captured journal.

No function dispatches native work, authenticates a supplied DTO or refunds a
consumed liability. The private captured owner predicate authenticates the
actual retained attempt/producer/observer proof; defaults remain closed.
"""
from dataclasses import dataclass
import math
import time
import uuid

from ceta.contracts.events import StreamPosition
from ceta.contracts.kernel_transactions import (BUDGET_FIELDS, BudgetVector, budget_key,
    deadline_text, digest, intent_key, logical_key, object_value, read_basis,
    read_budget, read_intent, require)
from ceta.contracts.real_effect import (CAP_OPERATION, RESTORE_OPERATION,
    decode_cpu_effect_observation, decode_owned_cpu_request)
from ceta.contracts.resource_management import ObservationState
from ceta.contracts.store_transactions import StoreChange, StoreKey
from ceta.contracts.temporal import ClockSample, require_clock_progress, require_deadline_current, utc_nanoseconds
from ceta.contracts.wire import MAX_INTEGER, canonical_bytes, strict_loads
from .owner_authority import owned_cpu_proposal, worker_resource

OUTCOME_PROFILE = 'ceta-owned-cpu-outcome-v1'
MAXIMUM_OWNER_CHECK_NS = 50_000_000
_FIELDS = ('scope_id', 'permit_id', 'request_commitment', 'consumption', 'attempt_index',
    'state', 'reserved_bytes', 'stored_bytes', 'prior_stored_bytes', 'attempt_stored_bytes', 'receipt_index', 'observation_index',
    'settlement_index', 'native_observation_commitment', 'settlement_clock', 'settlement_elapsed_ns', 'revision')
_STATES = ('ATTEMPT_COMMITTED', 'UNCERTAIN', 'DISCREPANCY', 'SETTLED_OBSERVED')


def outcome_key(scope, permit):
    return logical_key('projection', scope, 'owned-cpu-outcome', permit)


def task_outcome_key(scope, task):
    return logical_key('projection', scope, 'owned-cpu-task-outcome', task)


@dataclass(frozen=True)
class OwnedCpuOutcome:
    """Historical readback data; never an execution lease or replay capability."""
    projection_wire: bytes
    receipt_wire: bytes | None
    observation_wire: bytes | None
    settlement_wire: bytes | None

    def as_dict(self):
        return strict_loads(self.projection_wire)


class KernelEffectTransactions:
    def __init__(self, kernel):
        self.k = kernel
        info = time.get_clock_info('perf_counter')
        require(info.monotonic is True and info.adjustable is False and
            type(info.resolution) is float and math.isfinite(info.resolution) and
            info.resolution > 0, 'OUTCOME_ELAPSED_CLOCK_UNAVAILABLE')
        self.resolution = math.ceil(info.resolution * 1_000_000_000)
        require(1 <= self.resolution <= MAXIMUM_OWNER_CHECK_NS // 2, 'OUTCOME_ELAPSED_CLOCK_UNAVAILABLE')
        self.highwater = None

    def _load(self, request_wire, permit_wire, context):
        request = decode_owned_cpu_request(request_wire)
        peer = self.k._peer(context)
        require((peer.principal_id, peer.session_id) == (request.principal_id, request.actor_session),
                'OUTCOME_PEER_BINDING_MISMATCH')
        supplied = self.k._decode(permit_wire, 'OperationPermit')
        permit = self.k._recover_permit(supplied, peer)
        p = permit.as_dict()
        require(p['status'] == 'CONSUMED', 'OUTCOME_CONSUMPTION_REQUIRED')
        evidence = self.k._resolve_consumption(permit, peer=peer)
        require(evidence.consumed_permit_wire == permit.canonical_wire, 'OUTCOME_CONSUMPTION_CHANGED')
        key = StoreKey('permit', request.scope_id, p['record_id'])
        intention = intent_key(request.scope_id, p['record_id'])
        first = self.k._snapshot((key, intention))
        metadata = read_intent(self.k._present(first, intention))
        basis, grant, _ = read_basis(metadata['basis_wire'].encode('utf-8'), self.k._codec)
        proposal = owned_cpu_proposal(self.k._codec, request)
        require(basis['proposal_wire'].encode('utf-8') == proposal.canonical_wire
            and p['scope_id'] == request.scope_id and p['proposal_ref'] == request.proposal_id
            and p['task_id'] == request.task_id and p['operation'] == request.operation
            and p['arguments_commitment'] == request.input_commitment
            and p['adapter_commitment'] == request.adapter_commitment,
            'OUTCOME_REQUEST_BINDING_MISMATCH')
        reservation = StoreKey('reservation', request.scope_id, p['reservation_ref'])
        state_key = outcome_key(request.scope_id, p['record_id'])
        task_key = task_outcome_key(request.scope_id, request.task_id)
        cells = self.k._snapshot(tuple(first) + (budget_key(grant), reservation, state_key, task_key))
        require(all(cells[key] == row for key, row in first.items()) and
            self.k._present(cells, key) == permit.canonical_wire, 'OUTCOME_STATE_CHANGED')
        liability = object_value(self.k._present(cells, reservation),
            ('scope_id', 'reservation_id', 'permit_id', 'grant_key', 'cost', 'state'))
        require(liability['state'] == 'CHARGED' and liability['permit_id'] == p['record_id']
            and liability['scope_id'] == request.scope_id and liability['reservation_id'] == p['reservation_ref']
            and liability['grant_key'] == grant.as_dict()
            and BudgetVector.from_dict(liability['cost']) == request.operation_budget
            and BudgetVector.from_dict(metadata['cost']) == request.operation_budget,
            'OUTCOME_CHARGED_LIABILITY_REQUIRED')
        _, _, _, charged = read_budget(self.k._present(cells, budget_key(grant)), budget_key(grant))
        require(charged.contains(request.operation_budget), 'OUTCOME_LIABILITY_CHANGED')
        return request, permit, peer, cells, metadata, state_key, task_key

    def _guard(self, phase, request, permit, receipt, observation, proof, peer, context):
        started = time.perf_counter_ns()
        require(type(started) is int and 0 <= started <= MAX_INTEGER, 'OUTCOME_ELAPSED_COUNTER_INVALID')
        require(self.k._peer(context) == peer, 'OUTCOME_PEER_CHANGED')
        previous, current = self.k._clock()
        previous = ClockSample(**{n: getattr(previous, n) for n in ClockSample.__dataclass_fields__})
        current = ClockSample(**{n: getattr(current, n) for n in ClockSample.__dataclass_fields__})
        if self.highwater is not None: require_clock_progress(self.highwater, current)
        if phase == 'ATTEMPT': require_deadline_current(request.deadline, previous, current)
        frozen = (request.canonical_wire, permit.canonical_wire,
                  None if receipt is None else receipt.canonical_wire,
                  None if observation is None else observation.canonical_wire)
        method = self.k._owned_cpu_outcome_current
        require(callable(method), 'OUTCOME_NATIVE_OWNER_UNAVAILABLE')
        # Final external callback. It coordinates original context, proof,
        # current producer/observer/native binding and evidence capacity.
        require(method(phase, request, permit, receipt, observation, proof, peer, context) is None,
                'OUTCOME_NATIVE_DECISION_INVALID')
        finished = time.perf_counter_ns()
        require(type(finished) is int and started <= finished <= MAX_INTEGER, 'OUTCOME_ELAPSED_COUNTER_INVALID')
        require(finished - started + 2 * self.resolution <= MAXIMUM_OWNER_CHECK_NS, 'OUTCOME_OWNER_CHECK_TOO_SLOW')
        self.last_elapsed = finished - started + 2 * self.resolution
        if phase == 'ATTEMPT':
            require(current.monotonic_ns + self.last_elapsed < request.deadline.expires_monotonic_ns
                and current.latest_wall_ns + self.last_elapsed < request.deadline.expires_wall_ns,
                'OUTCOME_ATTEMPT_DEADLINE_ELAPSED')
        require(frozen == (request.canonical_wire, permit.canonical_wire,
            None if receipt is None else receipt.canonical_wire,
            None if observation is None else observation.canonical_wire), 'OUTCOME_OWNER_INPUT_MUTATED')
        self.highwater = current
        return current

    def _decision(self, request, permit, reason, cause, inputs):
        return self.k._codec.decode(canonical_bytes(dict(record_type='PolicyDecision', schema_version='1',
            record_id='decision:' + uuid.uuid4().hex, scope_id=request.scope_id, causation_ref=cause,
            request_ref=request.request_id, policy_commitment=request.policy_commitment, rule_refs=[],
            evaluated_inputs_commitment=digest('owned-cpu-outcome', inputs), relevant_revision_refs=[],
            outcome='ALLOW', reason_codes=[reason], obligation_refs=[], revalidation_triggers=[],
            authority_owner_id='kernel:cmp02')))

    @staticmethod
    def _index(point, record, event):
        return dict(sequence=point.next_sequence, previous_head=point.head,
            event_id=event, payload_commitment=record.commitment)

    def _resolve(self, index, scope, kind, peer):
        require(type(index) is dict and set(index) == {'sequence', 'previous_head', 'event_id', 'payload_commitment'},
                'OUTCOME_INDEX_INVALID')
        prior = StreamPosition(scope, index['sequence'], index['previous_head'])
        rows = self.k._store.replay(scope, prior.next_sequence, 1)
        require(len(rows) == 1, 'OUTCOME_EVENT_UNAVAILABLE')
        event = self.k._events.require_successor(rows[0].event_wire, prior)
        payload = self.k._events.require_payload(rows[0].event_wire, rows[0].payload_wire)
        fields = event.record.as_dict()
        require(fields['record_id'] == index['event_id'] and fields['event_type'] == kind
            and (fields['actor_id'], fields['actor_session']) == (peer.principal_id, peer.session_id)
            and payload.commitment == index['payload_commitment'], 'OUTCOME_INDEX_BINDING_MISMATCH')
        return payload

    def _row(self, request, permit, cells, metadata, key):
        if cells[key].value_wire is None: return None
        row = object_value(cells[key].value_wire, _FIELDS, OUTCOME_PROFILE)
        require(row['scope_id'] == request.scope_id and row['permit_id'] == permit.record_id
            and row['request_commitment'] == request.input_commitment
            and row['consumption'] == metadata['consumption'] and row['state'] in _STATES
            and type(row['revision']) is int and 1 <= row['revision'] <= MAX_INTEGER
            and type(row['stored_bytes']) is int and 0 < row['stored_bytes'] <= row['reserved_bytes']
            and type(row['prior_stored_bytes']) is int and 0 <= row['prior_stored_bytes'] < row['stored_bytes']
            and (row['prior_stored_bytes'] == 0) == (row['revision'] == 1)
            and type(row['attempt_stored_bytes']) is int and 0 < row['attempt_stored_bytes'] <= row['stored_bytes']
            and (row['revision'] != 1 or row['stored_bytes'] == row['attempt_stored_bytes'])
            and type(row['reserved_bytes']) is int and row['reserved_bytes'] == request.required_outcome_bytes,
            'OUTCOME_PROJECTION_BINDING_MISMATCH')
        return row

    @staticmethod
    def _projection_inputs(row):
        return {name: row[name] for name in ('state', 'reserved_bytes', 'stored_bytes', 'prior_stored_bytes', 'attempt_stored_bytes',
            'settlement_clock', 'settlement_elapsed_ns', 'revision', 'attempt_index')}

    @staticmethod
    def _attempt_accounting(row):
        # Exclude the attempt's own index: its payload commitment is an output
        # of this decision. The exact count is bound without a hash cycle.
        return dict(reserved_bytes=row['reserved_bytes'], stored_bytes=row['attempt_stored_bytes'],
            prior_stored_bytes=0, revision=1)

    @staticmethod
    def _task_wire(row, key, task_id):
        cause = row['attempt_index']['event_id'] if row['revision'] == 1 else row['settlement_index']['event_id']
        return canonical_bytes(dict(profile=OUTCOME_PROFILE, scope_id=row['scope_id'], task_id=task_id,
            outcome_ref=key.record_id, state=row['state'], request_commitment=row['request_commitment'], event_id=cause))

    def _require_accounting(self, row, key, task_id, indexes, evidence=None):
        # These are the exact current batch's canonical bytes, recovered from
        # their already verified immutable journal indices. Prior cumulative
        # bytes are authenticated by the preceding writer and the current
        # decision commitment; projections never reset the consumed charge.
        size = len(canonical_bytes(row)) + len(self._task_wire(row, key, task_id))
        for index in indexes:
            entries = self.k._store.replay(row['scope_id'], index['sequence'], 1)
            require(len(entries) == 1, 'OUTCOME_EVENT_UNAVAILABLE')
            size += len(entries[0].event_wire) + len(entries[0].payload_wire)
        if evidence is not None: size += len(evidence)
        require(row['stored_bytes'] == row['prior_stored_bytes'] + size,
                'OUTCOME_CUMULATIVE_ACCOUNTING_MISMATCH')

    def _commit(self, records, kinds, peer, sample, cells, row, key, task_key, task_id, guard, evidence=None, settlement_inputs=None, attempt_inputs=None):
        point = self.k._store.position(row['scope_id']); initial = point
        fields = ('attempt_index',) if len(records) == 1 else (
                                       (('receipt_index', 'observation_index', 'settlement_index') if len(records) == 3 else
                                        ('receipt_index', 'settlement_index') if records[0].record_type == 'ExecutionReceipt' else
                                        ('observation_index', 'settlement_index')))
        event_ids = tuple('event:' + uuid.uuid4().hex for _ in records)
        # Charge this same consumed request across its entire durable history.
        # The caller recovered/authenticated the prior projection before this
        # mutation; the original cell and CAS preserve that exact starting total.
        prior = 0 if cells[key].value_wire is None else strict_loads(cells[key].value_wire)['stored_bytes']
        row['prior_stored_bytes'], row['stored_bytes'] = prior, prior + 1
        for _ in range(8):
            if row['revision'] == 1: row['attempt_stored_bytes'] = row['stored_bytes']
            if settlement_inputs is not None:
                data = records[-1].as_dict()
                data['evaluated_inputs_commitment'] = digest('owned-cpu-outcome',
                    dict(settlement_inputs, projection=self._projection_inputs(row)))
                records = records[:-1] + (self.k._codec.decode(canonical_bytes(data)),)
            else:
                data = records[0].as_dict()
                data['evaluated_inputs_commitment'] = digest('owned-cpu-outcome',
                    dict(attempt_inputs, accounting=self._attempt_accounting(row)))
                records = (self.k._codec.decode(canonical_bytes(data)),)
            point, entries = initial, []
            for record, kind, field, event in zip(records, kinds, fields, event_ids):
                entry = self.k._entry(point, record, event, kind, peer, sample)
                row[field] = self._index(point, record, event); entries.append(entry)
                point = StreamPosition(point.scope_id, point.next_sequence + 1,
                    self.k._events.require_successor(entry.event_wire, point).head)
            cause = row['attempt_index']['event_id'] if len(records) == 1 else row['settlement_index']['event_id']
            encoded = canonical_bytes(row); task_wire = self._task_wire(row, key, task_id)
            size = prior + sum(len(e.event_wire) + len(e.payload_wire) for e in entries) + len(encoded) + len(task_wire)
            if evidence is not None: size += len(evidence[1])
            if row['stored_bytes'] == size: break
            row['stored_bytes'] = size
        require(row['stored_bytes'] == size and size <= row['reserved_bytes'], 'OUTCOME_RESERVED_CAPACITY_EXCEEDED')
        changes = (StoreChange(self.k._expect(cells[key]), canonical_bytes(row), cause),
                   StoreChange(self.k._expect(cells[task_key]), task_wire, cause))
        if evidence is not None:
            changes += (StoreChange(self.k._expect(cells[evidence[0]]), evidence[1], cause),)
        self.k._store.commit((initial,), tuple(entries), checks=tuple(self.k._expect(c) for c in cells.values()),
            changes=changes, guard=guard)

    def begin(self, request_wire, permit_wire, proof, context):
        request, permit, peer, cells, metadata, key, task_key = self._load(request_wire, permit_wire, context)
        sample = self._guard('ATTEMPT', request, permit, None, None, proof, peer, context)
        row = self._row(request, permit, cells, metadata, key)
        if row is not None:
            result = self._recover(request, permit, peer, cells, metadata, key)
            require(self.k._snapshot(tuple(cells)) == cells, 'OUTCOME_STATE_CHANGED')
            self._guard('ATTEMPT', request, permit, None, None, proof, peer, context)
            return result
        row = dict(profile=OUTCOME_PROFILE, scope_id=request.scope_id, permit_id=permit.record_id,
            request_commitment=request.input_commitment, consumption=metadata['consumption'],
            state='ATTEMPT_COMMITTED', reserved_bytes=request.required_outcome_bytes,
            stored_bytes=1, prior_stored_bytes=0, attempt_stored_bytes=1,
            attempt_index=None, receipt_index=None, observation_index=None, settlement_index=None,
            native_observation_commitment=None, settlement_clock=None, settlement_elapsed_ns=None, revision=1)
        attempt_inputs = {'request': request.input_commitment, 'permit': permit.commitment,
            'consumption': metadata['consumption'], 'reserved_bytes': row['reserved_bytes']}
        record = self._decision(request, permit, 'OWNED_CPU_ATTEMPT_RESERVED',
            permit.as_dict()['consume_event_ref'], attempt_inputs)
        guard = lambda: self._guard('ATTEMPT', request, permit, None, None, proof, peer, context)
        self._commit((record,), ('kernel.owned-cpu.attempt',), peer, sample, cells, row, key, task_key, request.task_id, guard,
            attempt_inputs=attempt_inputs)
        guard()
        return self.recover(request_wire, permit_wire, context)

    def _receipt(self, request, permit, wire, attempt):
        record = self.k._decode(wire, 'ExecutionReceipt'); value = record.as_dict(); p = permit.as_dict()
        require(value['scope_id'] == request.scope_id and value['task_id'] == request.task_id
            and value['operation_id'] == request.request_id and value['permit_ref'] == permit.record_id
            and value['input_commitment'] == p['input_commitment']
            and value['dispatch_event_ref'] == attempt['event_id'] and value['causation_ref'] == attempt['event_id']
            and value['executor_session'] == request.actor_session, 'OUTCOME_RECEIPT_BINDING_MISMATCH')
        require(value['attestation_ref'] is None and value['plan_node_ref'] is None
            and len(value['error_refs']) <= 8 and len(set(value['error_refs'])) == len(value['error_refs'])
            and value['changed_resource_claims'] in ([], owned_cpu_proposal(self.k._codec, request).as_dict()['resources']),
            'OUTCOME_RECEIPT_CLAIMS_UNSUPPORTED')
        require((value['started_at'] is None and value['finished_at'] is None) or
            (value['started_at'] is not None and value['finished_at'] is not None and
             utc_nanoseconds(value['started_at']) <= utc_nanoseconds(value['finished_at'])), 'OUTCOME_RECEIPT_TIME_INVALID')
        require((value['output_ref'] is None) == (value['output_commitment'] is None), 'OUTCOME_OUTPUT_BINDING_REQUIRED')
        require(value['effect_status'] != 'NOT_STARTED' or value['exit_code'] is None,
                'OUTCOME_NOT_STARTED_EXIT_CLAIM')
        return record

    @staticmethod
    def _classify(request, observation, current, elapsed=0):
        if observation is None: return 'UNCERTAIN'
        if observation.state is ObservationState.UNAVAILABLE or observation.target_state != 'LIVE_IN_OWNED_JOB':
            return 'UNCERTAIN'
        a, b = observation.clock, current
        if ((a.boot_id, a.durable_epoch, a.resume_generation) != (b.boot_id, b.durable_epoch, b.resume_generation)
            or not a.wall_trusted or not b.wall_trusted or a.monotonic_ns < request.deadline.issued_monotonic_ns
            or not 0 <= b.monotonic_ns - a.monotonic_ns
            or b.monotonic_ns + elapsed - a.monotonic_ns > request.maximum_observation_age_ns
            or a.earliest_wall_ns > b.latest_wall_ns): return 'UNCERTAIN'
        return 'SETTLED_OBSERVED' if observation.limit == request.target_limit else 'DISCREPANCY'

    def _observation(self, request, receipt, observation, state, record_id=None):
        return self.k._codec.decode(canonical_bytes(dict(record_type='EffectObservation', schema_version='1',
            record_id=record_id or 'observation:' + uuid.uuid4().hex, scope_id=request.scope_id,
            causation_ref=receipt.record_id, operation_id=request.request_id, receipt_ref=receipt.record_id,
            observer_session='observer:' + str(observation.observer_identity.pid) + ':' + str(observation.observer_identity.creation_time),
            observer_implementation=observation.observer_commitment,
            resource=dict(resource_id=worker_resource(request), revision=None, access='READ', scope_id=request.scope_id),
            observed_at=deadline_text(observation.clock.wall_time_ns), method=observation.method,
            expected_predicate_ref='predicate:exact-cpu-policy',
            observed_payload_ref=logical_key('projection', request.scope_id, 'owned-cpu-evidence', observation.observation_commitment).record_id,
            observed_commitment=observation.observation_commitment,
            verdict='SATISFIED' if state == 'SETTLED_OBSERVED' else 'VIOLATED' if state == 'DISCREPANCY' else 'INDETERMINATE',
            causal_attribution='UNESTABLISHED', independence_class='SEPARATE_PROCESS',
            limitations=['Same-host separate process; native proof must authenticate origins.'])))

    def record(self, request_wire, permit_wire, receipt_wire, observation_wire, proof, context):
        request, permit, peer, cells, metadata, key, task_key = self._load(request_wire, permit_wire, context)
        row = self._row(request, permit, cells, metadata, key)
        require(row is not None, 'OUTCOME_ATTEMPT_REQUIRED')
        self._recover(request, permit, peer, cells, metadata, key)
        receipt = self._receipt(request, permit, receipt_wire, row['attempt_index'])
        observation = None if observation_wire is None else decode_cpu_effect_observation(observation_wire)
        if observation is not None:
            require(observation.request_commitment == request.input_commitment and observation.operation_id == request.request_id
                and observation.identity == request.process_identity and observation.job_digest == request.job_digest
                and observation.observer_commitment == request.observer_commitment, 'OUTCOME_OBSERVATION_BINDING_MISMATCH')
        sample = self._guard('OUTCOME', request, permit, receipt, observation, proof, peer, context)
        prior_receipt = None if row['receipt_index'] is None else self._resolve(row['receipt_index'], request.scope_id, 'kernel.owned-cpu.receipt', peer)
        if prior_receipt is not None:
            require(prior_receipt.canonical_wire == receipt.canonical_wire, 'OUTCOME_RECEIPT_CONFLICT')
            if row['native_observation_commitment'] == (None if observation is None else observation.observation_commitment):
                require(self.k._snapshot(tuple(cells)) == cells, 'OUTCOME_STATE_CHANGED')
                self._guard('OUTCOME', request, permit, receipt, observation, proof, peer, context)
                return self._recover(request, permit, peer, cells, metadata, key)
            require(row['state'] != 'SETTLED_OBSERVED', 'OUTCOME_ALREADY_SETTLED')
            require(observation is not None, 'OUTCOME_RECONCILIATION_OBSERVATION_REQUIRED')
            if row['native_observation_commitment'] is not None:
                previous = self._native_observation(row)
                require(observation.observer_identity == previous.observer_identity and observation.sequence > previous.sequence
                    and observation.clock.monotonic_ns > previous.clock.monotonic_ns, 'OUTCOME_OBSERVATION_REPLAY')
        state = self._classify(request, observation, sample, self.last_elapsed)
        require(receipt.as_dict()['effect_status'] != 'OBSERVED_EFFECT' or state == 'SETTLED_OBSERVED',
                'OUTCOME_UNSUPPORTED_OBSERVED_EFFECT_CLAIM')
        evidence = None
        if observation is not None:
            evidence_key = logical_key('projection', request.scope_id, 'owned-cpu-evidence', observation.observation_commitment)
            expanded = self.k._snapshot(tuple(cells) + (evidence_key,))
            require(all(expanded[k] == cell for k, cell in cells.items()), 'OUTCOME_STATE_CHANGED')
            require(expanded[evidence_key].generation == 0, 'OUTCOME_OBSERVATION_ALREADY_INDEXED')
            cells = expanded; evidence = (evidence_key, observation.canonical_wire)
        row.update(state=state, native_observation_commitment=None if observation is None else observation.observation_commitment,
            settlement_clock={n: getattr(sample, n) for n in ClockSample.__dataclass_fields__},
            settlement_elapsed_ns=self.last_elapsed, revision=row['revision'] + 1)
        records, kinds = [], []
        if prior_receipt is None: records.append(receipt); kinds.append('kernel.owned-cpu.receipt')
        if observation is not None:
            records.append(self._observation(request, receipt, observation, state)); kinds.append('kernel.owned-cpu.observation')
        settlement_inputs = {'request': request.input_commitment, 'permit': permit.commitment, 'receipt': receipt.commitment,
             'observation': None if observation is None else observation.observation_commitment, 'state': state,
             'attempt_event': row['attempt_index']['event_id']}
        decision = self._decision(request, permit, 'OWNED_CPU_' + state, receipt.record_id, settlement_inputs)
        records.append(decision); kinds.append('kernel.owned-cpu.settlement')
        def guard():
            fresh = self._guard('OUTCOME', request, permit, receipt, observation, proof, peer, context)
            require(self._classify(request, observation, fresh, self.last_elapsed) == state, 'OUTCOME_CLASSIFICATION_CHANGED')
        self._commit(tuple(records), tuple(kinds), peer, sample, cells, row, key, task_key, request.task_id, guard, evidence, settlement_inputs)
        guard()
        return self.recover(request_wire, permit_wire, context)

    def _recover(self, request, permit, peer, cells, metadata, key):
        row = self._row(request, permit, cells, metadata, key)
        if row is None:
            return OwnedCpuOutcome(canonical_bytes(dict(profile=OUTCOME_PROFILE, scope_id=request.scope_id,
                permit_id=permit.record_id, request_commitment=request.input_commitment, state='CONSUMED_UNRESOLVED')),
                None, None, None)
        attempt = self._resolve(row['attempt_index'], request.scope_id, 'kernel.owned-cpu.attempt', peer)
        expect = {'request': request.input_commitment, 'permit': permit.commitment,
                  'consumption': metadata['consumption'], 'reserved_bytes': row['reserved_bytes'],
                  'accounting': self._attempt_accounting(row)}
        require(attempt.record_type == 'PolicyDecision' and attempt.as_dict()['evaluated_inputs_commitment'] == digest('owned-cpu-outcome', expect)
            and attempt.as_dict()['reason_codes'] == ['OWNED_CPU_ATTEMPT_RESERVED']
            and attempt.as_dict()['causation_ref'] == permit.as_dict()['consume_event_ref'], 'OUTCOME_ATTEMPT_BINDING_MISMATCH')
        if row['state'] == 'ATTEMPT_COMMITTED':
            require(all(row[name] is None for name in ('receipt_index', 'observation_index', 'settlement_index',
                'native_observation_commitment', 'settlement_clock', 'settlement_elapsed_ns')), 'OUTCOME_UNEXPECTED_EVIDENCE')
            self._require_accounting(row, key, request.task_id, (row['attempt_index'],))
            return OwnedCpuOutcome(canonical_bytes(row), None, None, None)
        receipt = self._resolve(row['receipt_index'], request.scope_id, 'kernel.owned-cpu.receipt', peer)
        self._receipt(request, permit, receipt.canonical_wire, row['attempt_index'])
        observation = self._native_observation(row)
        canonical_observation = None
        require(type(row['settlement_clock']) is dict and set(row['settlement_clock']) == set(ClockSample.__dataclass_fields__), 'OUTCOME_CLOCK_INVALID')
        sample = ClockSample(**row['settlement_clock'])
        require(type(row['settlement_elapsed_ns']) is int and 0 <= row['settlement_elapsed_ns'] <= MAXIMUM_OWNER_CHECK_NS,
                'OUTCOME_ELAPSED_COUNTER_INVALID')
        require(row['state'] == self._classify(request, observation, sample, row['settlement_elapsed_ns']), 'OUTCOME_SETTLEMENT_STATE_MISMATCH')
        if observation is not None:
            canonical_observation = self._resolve(row['observation_index'], request.scope_id, 'kernel.owned-cpu.observation', peer)
            require(canonical_observation.canonical_wire == self._observation(request, receipt, observation, row['state'], canonical_observation.record_id).canonical_wire,
                    'OUTCOME_OBSERVATION_INDEX_MISMATCH')
            evidence_key = logical_key('projection', request.scope_id, 'owned-cpu-evidence', observation.observation_commitment)
            require(self.k._snapshot((evidence_key,))[evidence_key].value_wire == observation.canonical_wire,
                    'OUTCOME_NATIVE_EVIDENCE_CHANGED')
        else: require(row['observation_index'] is None, 'OUTCOME_UNEXPECTED_EVIDENCE')
        settlement = self._resolve(row['settlement_index'], request.scope_id, 'kernel.owned-cpu.settlement', peer)
        expected = {'request': request.input_commitment, 'permit': permit.commitment, 'receipt': receipt.commitment,
            'observation': None if observation is None else observation.observation_commitment,
            'state': row['state'], 'attempt_event': row['attempt_index']['event_id'],
            'projection': self._projection_inputs(row)}
        require(settlement.record_type == 'PolicyDecision' and settlement.as_dict()['evaluated_inputs_commitment'] == digest('owned-cpu-outcome', expected)
            and settlement.as_dict()['reason_codes'] == ['OWNED_CPU_' + row['state']]
            and settlement.as_dict()['causation_ref'] == receipt.record_id, 'OUTCOME_SETTLEMENT_INDEX_MISMATCH')
        indexes = ((row['receipt_index'],) if row['revision'] == 2 else ())
        if observation is not None: indexes += (row['observation_index'],)
        indexes += (row['settlement_index'],)
        self._require_accounting(row, key, request.task_id, indexes,
            None if observation is None else observation.canonical_wire)
        return OwnedCpuOutcome(canonical_bytes(row), receipt.canonical_wire,
            None if canonical_observation is None else canonical_observation.canonical_wire, settlement.canonical_wire)

    def _native_observation(self, row):
        value = row['native_observation_commitment']
        if value is None: return None
        key = logical_key('projection', row['scope_id'], 'owned-cpu-evidence', value)
        observation = decode_cpu_effect_observation(self.k._present(self.k._snapshot((key,)), key))
        require(observation.observation_commitment == value, 'OUTCOME_NATIVE_EVIDENCE_CHANGED')
        return observation

    def recover(self, request_wire, permit_wire, context):
        request, permit, peer, cells, metadata, key, _ = self._load(request_wire, permit_wire, context)
        result = self._recover(request, permit, peer, cells, metadata, key)
        require(self.k._peer(context) == peer, 'OUTCOME_PEER_CHANGED')
        require(self.k._snapshot(tuple(cells)) == cells, 'OUTCOME_STATE_CHANGED')
        require(self.k._peer(context) == peer, 'OUTCOME_PEER_CHANGED')
        return result
