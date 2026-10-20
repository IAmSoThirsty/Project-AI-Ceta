"""Real disposable SQLite transactions; positive proof providers are controlled.

No native policy effect, actual independent observer, authentication ceremony or
production owner integration is established by these opaque proof fixtures.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import threading
import unittest
import uuid
from unittest.mock import patch

import test_owner_authority_transactions as parent
from ceta.contracts.kernel_transactions import budget_key, intent_key, read_budget
from ceta.contracts.real_effect import CpuEffectObservation
from ceta.contracts.resource_management import ObservationState, ProcessResourceIdentity
from ceta.contracts.store_transactions import STORE_PROFILE, StoreKey
from ceta.contracts.wire import ContractError, canonical_bytes, strict_loads
from ceta.kernel.effect_transactions import outcome_key, task_outcome_key
from ceta.kernel.transactions import KernelTransactions

ROOT = Path(__file__).resolve().parents[2]
CRASH_OBSERVATIONS = []
CUMULATIVE_OBSERVATIONS = []
CONTROLLED_SUCCESS_RESERVE = 32768


class ControlledOutcomeOwners(parent.ControlledOwners):
    def __init__(self, request):
        super().__init__(request)
        self.outcome_proofs = {}; self.outcome_return = None
        self.outcome_on_check = None; self.outcome_calls = []

    def native_proof(self, phase, request, permit, receipt=None, observation=None):
        proof = object()
        self.outcome_proofs[proof] = (phase, request.canonical_wire, permit,
            receipt, None if observation is None else observation.canonical_wire)
        return proof

    def require_owned_cpu_outcome_current(self, phase, request, permit, receipt, observation, proof, peer, context):
        with self.lock:
            self.outcome_calls.append(phase)
            if self.outcome_on_check is not None: self.outcome_on_check(phase)
            if self.authenticate(context) != peer: raise ContractError('CONTROLLED_OUTCOME_PEER_DENIED')
            supplied = (phase, request.canonical_wire, permit.canonical_wire,
                None if receipt is None else receipt.canonical_wire,
                None if observation is None else observation.canonical_wire)
            if self.outcome_proofs.get(proof) != supplied: raise ContractError('CONTROLLED_NATIVE_PROOF_DENIED')
            return self.outcome_return


class OutcomeTransactionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((ROOT / 'contracts/schemas/records.schema.json').read_text())

    def fixture(self, *, reserve=CONTROLLED_SUCCESS_RESERVE, attempt=True):
        # The old8KiB positive fixture cannot cover attempt+first outcome
        # cumulatively (measured10,786 bytes before this fixture amendment).
        # This is an explicit finite controlled enrollment/operation change;
        # the shared contract and production constants remain byte-exact.
        enrollment = replace(parent.enrollment_request(),
            authority_budget=parent.budget(max_bytes_written=65536),
            recovery_budget=parent.budget(1, wall_time_ms=5000, max_bytes_read=8192, max_bytes_written=32768),
            evidence_reserve_bytes=CONTROLLED_SUCCESS_RESERVE)
        with patch.object(parent, 'ControlledOwners', ControlledOutcomeOwners), \
                patch.object(parent, 'enrollment_request', return_value=enrollment):
            f = parent.Fixture(self.schema)
        self.addCleanup(f.close); f.begin(); f.enroll()
        f.effect = parent.effect_request(f.request, required_outcome_bytes=reserve,
            operation_budget=parent.budget(1, wall_time_ms=1000, max_bytes_read=8192, max_bytes_written=reserve))
        f.approve(f.effect); proposal = f.allow_basis()
        f.prepared = f.kernel.prepare(proposal, f.owners.context).record_wire
        f.permit = f.kernel.consume(f.prepared, f.owners.context).record_wire
        f.attempt_proof = f.owners.native_proof('ATTEMPT', f.effect, f.permit)
        f.capacity_start = f.store.store_position().next_commit
        if attempt: self.begin(f)
        return f

    def begin(self, f, kernel=None):
        return (kernel or f.kernel).begin_owned_cpu_attempt(f.effect.canonical_wire, f.permit,
            f.attempt_proof, f.owners.context)

    def receipt(self, f, **changes):
        state = f.kernel.recover_owned_cpu_outcome(f.effect.canonical_wire, f.permit, f.owners.context).as_dict()
        permit = f.codec.decode(f.permit).as_dict()
        record = dict(record_type='ExecutionReceipt', schema_version='1', record_id='receipt:' + uuid.uuid4().hex,
            scope_id=f.effect.scope_id, causation_ref=state['attempt_index']['event_id'], task_id=f.effect.task_id,
            operation_id=f.effect.request_id, permit_ref=permit['record_id'], plan_node_ref=None,
            executor_session=f.effect.actor_session, input_commitment=permit['input_commitment'],
            dispatch_event_ref=state['attempt_index']['event_id'], started_at=None, finished_at=None,
            exit_code=None, output_ref=None, output_commitment=None, changed_resource_claims=[],
            error_refs=[], cancellation_state='NONE', effect_status='MAY_HAVE_EXECUTED', attestation_ref=None)
        record.update(changes); return canonical_bytes(record)

    def observation(self, f, **changes):
        values = dict(request_commitment=f.effect.input_commitment, operation_id=f.effect.request_id,
            identity=f.effect.process_identity, job_digest=f.effect.job_digest,
            observer_identity=ProcessResourceIdentity(201, 200, parent.H), observer_commitment=f.effect.observer_commitment,
            sequence=1, clock=parent.clock(1_080_000_000), state=ObservationState.MEASURED,
            limit=f.effect.target_limit, target_state='LIVE_IN_OWNED_JOB')
        values.update(changes); return CpuEffectObservation(**values)

    def record(self, f, receipt, observation, *, kernel=None, proof=None):
        if proof is None: proof = f.owners.native_proof('OUTCOME', f.effect, f.permit, receipt, observation)
        return (kernel or f.kernel).record_owned_cpu_outcome(f.effect.canonical_wire, f.permit, receipt,
            None if observation is None else observation.canonical_wire, proof, f.owners.context)

    def recovered(self, f, kernel=None):
        return (kernel or f.kernel).recover_owned_cpu_outcome(f.effect.canonical_wire, f.permit, f.owners.context)

    def snapshot(self, f):
        return f.store.store_position(), f.store.position(parent.PROJECT), f.store.position(parent.INSTALLATION)

    def actual_writes(self, f, journal=None):
        """Independent read of retained canonical commit/change history."""
        journal = journal or f.store
        key = outcome_key(f.effect.scope_id, f.codec.decode(f.permit).record_id).as_dict()
        totals = dict(event_bytes=0, payload_bytes=0, projection_bytes=0, transactions=0)
        for sequence, wire in journal._connection.execute(
                'SELECT sequence,commit_wire FROM store_commits WHERE sequence>=? ORDER BY sequence', (f.capacity_start,)):
            commit = strict_loads(wire)
            if not any(all(change[n] == key[n] for n in key) for change in commit['changes']): continue
            totals['transactions'] += 1
            for event in commit['events']:
                event_wire, payload_wire = journal._connection.execute(
                    'SELECT event_wire,payload_wire FROM history_events WHERE scope_id=? AND sequence=?',
                    (event['scope_id'], event['sequence'])).fetchone()
                totals['event_bytes'] += len(event_wire); totals['payload_bytes'] += len(payload_wire)
            totals['projection_bytes'] += sum(len(value) for (value,) in journal._connection.execute(
                'SELECT value_wire FROM store_changes WHERE commit_sequence=?', (sequence,)) if value is not None)
        totals['total'] = sum(totals[n] for n in ('event_bytes','payload_bytes','projection_bytes'))
        return totals

    def fault_row(self, f, change):
        key = outcome_key(f.effect.scope_id, f.codec.decode(f.permit).record_id)
        cell = f.cell(key); value = strict_loads(cell.value_wire); change(value)
        seed = f.codec.decode(f.store.replay(parent.INSTALLATION, 0, 1)[0].payload_wire).as_dict()
        seed.update(record_id='decision:' + uuid.uuid4().hex, scope_id=f.effect.scope_id,
            reason_codes=['CONTROLLED_OUTCOME_PROJECTION_FAULT'])
        f.kernel._commit(f.codec.decode(canonical_bytes(seed)), 'event:' + uuid.uuid4().hex,
            'kernel.fixture.outcome.fault', f.owners.peer, parent.clock(), {key: cell},
            {key: canonical_bytes(value)}, f.effect.policy_commitment)

    def test_consumption_without_attempt_is_read_only_unresolved(self):
        f = self.fixture(attempt=False); before = self.snapshot(f)
        self.assertEqual(self.recovered(f).as_dict()['state'], 'CONSUMED_UNRESOLVED')
        self.assertEqual(self.snapshot(f), before)

    def test_attempt_is_durable_one_per_permit_and_not_execution_evidence(self):
        f = self.fixture(); before = self.snapshot(f)
        row = self.begin(f).as_dict(); self.assertEqual(row['state'], 'ATTEMPT_COMMITTED')
        self.assertIsNone(row['receipt_index']); self.assertEqual(self.snapshot(f), before)
        self.assertEqual(f.kernel.resolve_consumption_for_peer(f.permit, f.owners.context).consumed_permit_wire, f.permit)

    def test_actual_atomic_receipt_observation_settlement_and_task_projection(self):
        f = self.fixture(); before = self.snapshot(f); receipt = self.receipt(f); obs = self.observation(f)
        result = self.record(f, receipt, obs); row = result.as_dict()
        self.assertEqual(row['state'], 'SETTLED_OBSERVED')
        self.assertEqual(row['receipt_index']['sequence'] + 1, row['observation_index']['sequence'])
        self.assertEqual(row['observation_index']['sequence'] + 1, row['settlement_index']['sequence'])
        self.assertEqual(self.snapshot(f)[0].next_commit, before[0].next_commit + 1)
        self.assertEqual(strict_loads(result.observation_wire)['independence_class'], 'SEPARATE_PROCESS')
        self.assertEqual(strict_loads(result.observation_wire)['causal_attribution'], 'UNESTABLISHED')
        task = strict_loads(f.cell(task_outcome_key(f.effect.scope_id, f.effect.task_id)).value_wire)
        self.assertEqual(task['task_id'], f.effect.task_id); self.assertEqual(task['state'], row['state'])
        self.assertLessEqual(row['stored_bytes'], row['reserved_bytes'])

    def test_exact_outcome_retry_has_no_new_event_or_refund(self):
        f = self.fixture(); receipt = self.receipt(f); obs = self.observation(f)
        first = self.record(f, receipt, obs); before = self.snapshot(f)
        self.assertEqual(self.record(f, receipt, obs), first); self.assertEqual(self.snapshot(f), before)

    def test_missing_or_unavailable_observation_preserves_uncertainty(self):
        for unavailable in (False, True):
            with self.subTest(unavailable=unavailable):
                f = self.fixture(); receipt = self.receipt(f)
                obs = self.observation(f, state=ObservationState.UNAVAILABLE, limit=None, reason='native:unavailable') if unavailable else None
                result = self.record(f, receipt, obs)
                self.assertEqual(result.as_dict()['state'], 'UNCERTAIN')
                self.assertEqual(strict_loads(result.receipt_wire)['effect_status'], 'MAY_HAVE_EXECUTED')

    def test_mismatch_is_discrepancy_and_process_exit_does_not_prove_effect(self):
        f = self.fixture(); obs = self.observation(f, limit=f.effect.original_limit)
        self.assertEqual(self.record(f, self.receipt(f, effect_status='PROCESS_EXITED', exit_code=0), obs).as_dict()['state'], 'DISCREPANCY')

    def test_settled_state_preserves_original_consumption_intent_and_charged_budget(self):
        f = self.fixture(); permit = f.codec.decode(f.permit).as_dict()
        keys = (StoreKey('permit', f.effect.scope_id, permit['record_id']), intent_key(f.effect.scope_id, permit['record_id']),
            StoreKey('reservation', f.effect.scope_id, permit['reservation_ref']), budget_key(parent.grant_key_for(f.request)))
        before = f.store.snapshot(keys); self.record(f, self.receipt(f), self.observation(f))
        self.assertEqual(f.store.snapshot(keys), before)
        self.assertEqual(f.kernel.resolve_consumption_for_peer(f.permit, f.owners.context).consumed_permit_wire, f.permit)
        self.assertEqual(f.kernel.recover_permit(f.prepared, f.owners.context).canonical_wire, f.permit)

    def test_fresh_reconciliation_preserves_original_receipt_and_old_evidence(self):
        f = self.fixture(); receipt = self.receipt(f)
        obs = self.observation(f, state=ObservationState.UNAVAILABLE, limit=None, reason='native:unavailable')
        first = self.record(f, receipt, obs); first_row = first.as_dict()
        fresh = self.observation(f, sequence=2, clock=parent.clock(1_090_000_000))
        result = self.record(f, receipt, fresh)
        self.assertEqual(result.as_dict()['state'], 'SETTLED_OBSERVED')
        self.assertEqual(result.as_dict()['receipt_index'], first_row['receipt_index'])
        self.assertEqual(f.store.replay(f.effect.scope_id, first_row['observation_index']['sequence'], 1)[0].payload_wire, first.observation_wire)
        key = strict_loads(first.observation_wire)['observed_payload_ref']
        self.assertEqual(f.cell(StoreKey('projection', f.effect.scope_id, key)).value_wire, obs.canonical_wire)

    def test_default_missing_boolean_or_fabricated_proof_is_closed(self):
        f = self.fixture(); receipt = self.receipt(f); obs = self.observation(f); before = self.snapshot(f)
        for proof in (True, False, {}, 'sha256:' + 'a' * 64, object()):
            with self.subTest(type=type(proof).__name__), self.assertRaises((ContractError, TypeError)):
                self.record(f, receipt, obs, proof=proof)
        self.assertEqual(self.snapshot(f), before)
        f.kernel._owned_cpu_outcome_current = None
        with self.assertRaisesRegex(ContractError, 'NATIVE_OWNER_UNAVAILABLE'): self.record(f, receipt, obs)

    def test_owner_port_is_captured_and_boolean_result_cannot_commit(self):
        f = self.fixture(); f.owners.require_owned_cpu_outcome_current = lambda *args: (_ for _ in ()).throw(AssertionError('replacement called'))
        f.owners.outcome_return = True; before = self.snapshot(f)
        with self.assertRaisesRegex(ContractError, 'NATIVE_DECISION_INVALID'): self.record(f, self.receipt(f), self.observation(f))
        self.assertEqual(self.snapshot(f), before)

    def test_wrong_peer_and_changed_original_context_are_denied(self):
        f = self.fixture(); before = self.snapshot(f)
        with self.assertRaises(ContractError): f.kernel.recover_owned_cpu_outcome(f.effect.canonical_wire, f.permit, object())
        self.assertEqual(self.snapshot(f), before)

    def test_wrong_receipt_index_input_permit_or_dispatch_is_denied(self):
        f = self.fixture(); before = self.snapshot(f)
        for changes in ({'input_commitment': parent.H2}, {'permit_ref': 'permit:foreign'},
                {'dispatch_event_ref': 'event:foreign'}, {'operation_id': 'operation:foreign'}, {'executor_session': 'session:foreign'}):
            with self.subTest(fields=list(changes)), self.assertRaises(ContractError): self.record(f, self.receipt(f, **changes), self.observation(f))
        self.assertEqual(self.snapshot(f), before)

    def test_wrong_process_job_observer_or_request_binding_is_denied(self):
        f = self.fixture(); before = self.snapshot(f)
        for changes in ({'job_digest': parent.H2}, {'observer_commitment': parent.H2},
                {'identity': replace(f.effect.process_identity, creation_time=101)}, {'request_commitment': parent.H2}):
            with self.subTest(fields=list(changes)), self.assertRaises(ContractError): self.record(f, self.receipt(f), self.observation(f, **changes))
        self.assertEqual(self.snapshot(f), before)

    def test_stale_future_changed_epoch_or_lost_target_stays_uncertain(self):
        for changes in ({'clock': parent.clock(1_200_000_000)}, {'clock': parent.clock(1_080_000_000, durable_epoch=8)},
                {'target_state': 'EXITED'}, {'clock': parent.clock(1_080_000_000, wall_trusted=False)}):
            with self.subTest(fields=list(changes)):
                f = self.fixture(); self.assertEqual(self.record(f, self.receipt(f), self.observation(f, **changes)).as_dict()['state'], 'UNCERTAIN')

    def test_observed_effect_without_matching_independent_observation_is_denied(self):
        f = self.fixture(); before = self.snapshot(f)
        with self.assertRaisesRegex(ContractError, 'UNSUPPORTED_OBSERVED_EFFECT'):
            self.record(f, self.receipt(f, effect_status='OBSERVED_EFFECT'), None)
        self.assertEqual(self.snapshot(f), before)

    def test_reconciliation_sequence_or_timestamp_replay_is_denied(self):
        f = self.fixture(); receipt = self.receipt(f)
        old = self.observation(f, limit=f.effect.original_limit)
        self.record(f, receipt, old); before = self.snapshot(f)
        for changes in ({'sequence': 1, 'clock': parent.clock(1_090_000_000)},
                {'sequence': 2, 'clock': old.clock}):
            with self.subTest(changes=changes), self.assertRaisesRegex(ContractError, 'OBSERVATION_REPLAY'):
                self.record(f, receipt, self.observation(f, **changes))
        self.assertEqual(self.snapshot(f), before)

    def test_terminal_settlement_cannot_be_overwritten_or_replayed_as_an_attempt(self):
        f = self.fixture(); receipt = self.receipt(f); self.record(f, receipt, self.observation(f)); before = self.snapshot(f)
        with self.assertRaisesRegex(ContractError, 'ALREADY_SETTLED'):
            self.record(f, receipt, self.observation(f, sequence=2, clock=parent.clock(1_090_000_000)))
        self.begin(f); self.assertEqual(self.snapshot(f), before)
        with self.assertRaises(ContractError): f.kernel.consume(f.prepared, f.owners.context)

    def test_conflicting_receipt_cannot_replace_original_process_evidence(self):
        f = self.fixture(); self.record(f, self.receipt(f), None); before = self.snapshot(f)
        with self.assertRaisesRegex(ContractError, 'RECEIPT_CONFLICT'): self.record(f, self.receipt(f), self.observation(f))
        self.assertEqual(self.snapshot(f), before)

    def test_real_sqlite_fault_rolls_back_all_receipt_observation_settlement_writes(self):
        f = self.fixture(); before = self.snapshot(f)
        def fail(): raise RuntimeError('after actual SQLite inserts')
        f.fault = fail
        with self.assertRaisesRegex(RuntimeError, 'SQLite'): self.record(f, self.receipt(f), self.observation(f))
        f.fault = None; self.assertEqual(self.snapshot(f), before)
        self.assertEqual(self.recovered(f).as_dict()['state'], 'ATTEMPT_COMMITTED')

    def test_primary_control_exception_survives_real_writer_rollback(self):
        f = self.fixture(); before = self.snapshot(f); primary = KeyboardInterrupt('exact outcome primary')
        def fail(): raise primary
        f.fault = fail
        with self.assertRaises(KeyboardInterrupt) as caught: self.record(f, self.receipt(f), self.observation(f))
        self.assertIs(caught.exception, primary); f.fault = None; self.assertEqual(self.snapshot(f), before)
        self.record(f, self.receipt(f), self.observation(f))

    def test_precommit_native_binding_failure_rolls_back_without_refund(self):
        f = self.fixture(); before = self.snapshot(f); count = []
        def changed(phase):
            count.append(phase)
            if len(count) == 2: raise ContractError('CONTROLLED_NATIVE_BINDING_CHANGED')
        f.owners.outcome_on_check = changed
        with self.assertRaisesRegex(ContractError, 'BINDING_CHANGED'): self.record(f, self.receipt(f), self.observation(f))
        f.owners.outcome_on_check = None; self.assertEqual(self.snapshot(f), before)

    def test_lost_acknowledgment_recovers_committed_outcome_without_new_effect(self):
        f = self.fixture()
        def lost(): raise OSError('lost actual commit acknowledgment')
        f.store.after_commit = lost
        with self.assertRaisesRegex(OSError, 'acknowledgment'): self.record(f, self.receipt(f), self.observation(f))
        f.store.after_commit = None; before = self.snapshot(f)
        self.assertEqual(self.recovered(f).as_dict()['state'], 'SETTLED_OBSERVED'); self.assertEqual(self.snapshot(f), before)

    def test_capacity_failure_keeps_durable_attempt_unresolved(self):
        f = self.fixture(reserve=4096); before = self.snapshot(f)
        with self.assertRaisesRegex(ContractError, 'RESERVED_CAPACITY'): self.record(f, self.receipt(f), self.observation(f))
        self.assertEqual(self.snapshot(f), before); self.assertEqual(self.recovered(f).as_dict()['state'], 'ATTEMPT_COMMITTED')

    def test_readonly_reopen_replays_exact_outcomes_without_authority_or_write(self):
        f = self.fixture(); result = self.record(f, self.receipt(f), self.observation(f)); before = self.snapshot(f)
        f.close(); store = parent.SqliteJournal(f.root, f.codec, (parent.INSTALLATION, parent.PROJECT), profile=STORE_PROFILE, read_only=True)
        self.addCleanup(store.close); kernel = KernelTransactions(store, f.codec, parent.INSTALLATION, f.owners)
        self.assertEqual(self.recovered(f, kernel), result); self.assertEqual(store.store_position(), before[0])
        self.assertEqual(self.begin(f, kernel), result)
        self.assertEqual(store.store_position(), before[0])

    def test_concurrent_attempts_have_one_actual_sqlite_transaction_winner(self):
        f = self.fixture(attempt=False); other = parent.BarrierJournal(f.root, f.codec, (parent.INSTALLATION, parent.PROJECT), profile=STORE_PROFILE)
        self.addCleanup(other.close); kernel = KernelTransactions(other, f.codec, parent.INSTALLATION, f.owners)
        barrier = threading.Barrier(2); f.store.barrier = barrier; other.barrier = barrier
        def run(k):
            try: self.begin(f, k); return 'COMMITTED'
            except ContractError: return 'CONFLICT'
        with ThreadPoolExecutor(max_workers=2) as pool: results = list(pool.map(run, (f.kernel, kernel)))
        f.store.barrier = other.barrier = None
        self.assertEqual(sorted(results), ['COMMITTED', 'CONFLICT'])
        self.assertEqual(self.recovered(f).as_dict()['revision'], 1)

    def test_concurrent_outcomes_have_one_settlement_and_no_duplicate_receipt(self):
        f = self.fixture(); other = parent.BarrierJournal(f.root, f.codec, (parent.INSTALLATION, parent.PROJECT), profile=STORE_PROFILE)
        self.addCleanup(other.close); kernel = KernelTransactions(other, f.codec, parent.INSTALLATION, f.owners)
        barrier = threading.Barrier(2); f.store.barrier = barrier; other.barrier = barrier
        receipt, obs = self.receipt(f), self.observation(f); before = self.snapshot(f)
        def run(k):
            try: self.record(f, receipt, obs, kernel=k); return 'COMMITTED'
            except ContractError: return 'CONFLICT'
        with ThreadPoolExecutor(max_workers=2) as pool: results = list(pool.map(run, (f.kernel, kernel)))
        f.store.barrier = other.barrier = None
        self.assertEqual(sorted(results), ['COMMITTED', 'CONFLICT'])
        self.assertEqual(self.snapshot(f)[0].next_commit, before[0].next_commit + 1)

    def test_altered_attempt_or_settlement_index_is_rejected_on_recovery(self):
        for field in ('attempt_index', 'receipt_index', 'observation_index', 'settlement_index'):
            with self.subTest(field=field):
                f = self.fixture(); self.record(f, self.receipt(f), self.observation(f))
                self.fault_row(f, lambda row: row[field].update(event_id='event:wrong-index'))
                with self.assertRaisesRegex(ContractError, 'INDEX_BINDING'): self.recovered(f)

    def test_restoration_requires_distinct_approval_consumption_attempt_and_proof(self):
        f = self.fixture(); original = f.effect
        self.record(f, self.receipt(f), self.observation(f))
        restore = parent.effect_request(f.request, restore=original, required_outcome_bytes=CONTROLLED_SUCCESS_RESERVE,
            operation_budget=parent.budget(1, wall_time_ms=1000, max_bytes_read=8192, max_bytes_written=CONTROLLED_SUCCESS_RESERVE))
        f.approve(restore); proposal = f.allow_basis('restore_approval')
        prepared = f.kernel.prepare(proposal, f.owners.context).record_wire
        consumed = f.kernel.consume(prepared, f.owners.context).record_wire
        with self.assertRaisesRegex(ContractError, 'PROOF_DENIED'):
            f.kernel.begin_owned_cpu_attempt(restore.canonical_wire, consumed, f.attempt_proof, f.owners.context)
        f.effect, f.permit = restore, consumed
        f.attempt_proof = f.owners.native_proof('ATTEMPT', restore, consumed)
        self.begin(f); result = self.record(f, self.receipt(f), self.observation(f))
        self.assertEqual(result.as_dict()['state'], 'SETTLED_OBSERVED')
        self.assertEqual(restore.target_limit, original.original_limit)

    def test_settlement_count_revision_clock_and_elapsed_are_bound_to_journal(self):
        for field in ('stored_bytes', 'revision', 'settlement_elapsed_ns', 'settlement_clock'):
            with self.subTest(field=field):
                f = self.fixture(); self.record(f, self.receipt(f), self.observation(f))
                def alter(row):
                    if field == 'settlement_clock': row[field]['wall_time_ns'] += 1
                    else: row[field] += 1
                self.fault_row(f, alter)
                with self.assertRaisesRegex(ContractError, 'SETTLEMENT_INDEX_MISMATCH'): self.recovered(f)

    def test_native_predicate_control_exception_keeps_exact_primary_and_no_commit(self):
        f = self.fixture(); before = self.snapshot(f); primary = SystemExit('exact native proof interruption')
        def interrupted(phase): raise primary
        f.owners.outcome_on_check = interrupted
        with self.assertRaises(SystemExit) as caught: self.record(f, self.receipt(f), self.observation(f))
        self.assertIs(caught.exception, primary); self.assertEqual(self.snapshot(f), before)

    def test_owner_elapsed_rollback_and_timeout_deny_without_new_writes(self):
        for ticks in ((100, 99), (0, 50_000_000)):
            with self.subTest(ticks=ticks):
                f = self.fixture(); before = self.snapshot(f); receipt, obs = self.receipt(f), self.observation(f)
                with patch('ceta.kernel.effect_transactions.time.perf_counter_ns', side_effect=ticks):
                    with self.assertRaises(ContractError): self.record(f, receipt, obs)
                self.assertEqual(self.snapshot(f), before)

    def test_late_outcome_records_uncertainty_without_reviving_expired_attempt_authority(self):
        f = self.fixture(); receipt, obs = self.receipt(f), self.observation(f)
        f.owners.samples = (parent.clock(62_000_000_000), parent.clock(62_100_000_000))
        with self.assertRaises(ContractError): self.begin(f)
        result = self.record(f, receipt, obs)
        self.assertEqual(result.as_dict()['state'], 'UNCERTAIN')
        self.assertEqual(strict_loads(result.receipt_wire)['effect_status'], 'MAY_HAVE_EXECUTED')

    def test_before_and_after_commit_process_crashes_reopen_without_dispatch(self):
        schema_path = ROOT / 'contracts/schemas/records.schema.json'
        for stage, expected in (('before', 'ATTEMPT_COMMITTED'), ('after', 'SETTLED_OBSERVED')):
            with self.subTest(stage=stage):
                directory = ROOT / '.agents/fixtures/outcome-crashes' / uuid.uuid4().hex
                directory.mkdir(parents=True)
                metadata = directory / 'case.json'
                code = r'''
import json,os,pathlib,sys
sys.dont_write_bytecode=True
sys.path[:0]=[sys.argv[1],sys.argv[2]]
from ceta.store.sqlite_runtime import load_sqlite
load_sqlite()
import test_owned_cpu_outcome_transactions as m
m.parent.ROOT=pathlib.Path(sys.argv[3])
t=m.OutcomeTransactionsTests();t.schema=json.loads(pathlib.Path(sys.argv[4]).read_text())
f=t.fixture();receipt=t.receipt(f);obs=t.observation(f)
pathlib.Path(sys.argv[5]).write_text(json.dumps({'root':str(f.root),'enrollment':f.request.canonical_wire.decode(),'request':f.effect.canonical_wire.decode(),'permit':f.permit.decode()}))
if sys.argv[6]=='before':f.fault=lambda:os._exit(71)
else:f.store.after_commit=lambda:os._exit(72)
t.record(f,receipt,obs)
raise AssertionError('crash seam not reached')
'''
                done = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', code,
                    str(Path(__file__).resolve().parents[2] / 'src'), str(Path(__file__).resolve().parent),
                    str(directory), str(schema_path), str(metadata), stage], capture_output=True, timeout=45)
                self.assertEqual(done.returncode, 71 if stage == 'before' else 72, done.stderr.decode(errors='replace'))
                value = json.loads(metadata.read_text())
                from ceta.contracts.owner_enrollment import decode_enrollment_request
                owners = ControlledOutcomeOwners(decode_enrollment_request(value['enrollment'].encode()))
                codec = parent.RecordCodec(self.schema)
                store = parent.SqliteJournal(Path(value['root']), codec, (parent.INSTALLATION, parent.PROJECT), profile=STORE_PROFILE, read_only=True)
                try:
                    kernel = KernelTransactions(store, codec, parent.INSTALLATION, owners); before = store.store_position()
                    outcome = kernel.recover_owned_cpu_outcome(value['request'].encode(), value['permit'].encode(), owners.context)
                    self.assertEqual(outcome.as_dict()['state'], expected); self.assertEqual(store.store_position(), before)
                    CRASH_OBSERVATIONS.append({'stage': stage, 'exit_code': done.returncode, 'root': value['root'], 'state': expected, 'no_dispatch': True})
                finally: store.close()

    def test_cumulative_attempt_and_outcome_equal_actual_retained_write_values(self):
        f = self.fixture(); attempt = self.recovered(f).as_dict(); first = self.actual_writes(f)
        self.assertEqual(first['total'], attempt['stored_bytes'])
        self.assertEqual(attempt['attempt_stored_bytes'], attempt['stored_bytes'])
        result = self.record(f, self.receipt(f), self.observation(f)); row = result.as_dict()
        actual = self.actual_writes(f)
        self.assertEqual(row['stored_bytes'], actual['total'])
        self.assertEqual(row['prior_stored_bytes'], first['total'])
        self.assertEqual(row['attempt_stored_bytes'], first['total'])
        self.assertLess(row['stored_bytes'], row['reserved_bytes'])
        CUMULATIVE_OBSERVATIONS.append(dict(test_id=self.id(),reserve=row['reserved_bytes'],attempt=first,outcome=actual))

    def test_eight_kib_initial_outcome_overflow_is_atomic_and_keeps_charges(self):
        f = self.fixture(reserve=8192); before = self.snapshot(f); prior = self.recovered(f)
        permit = f.codec.decode(f.permit).as_dict()
        keys = (budget_key(parent.grant_key_for(f.request)), StoreKey('reservation',f.effect.scope_id,permit['reservation_ref']))
        charged = f.store.snapshot(keys); written = self.actual_writes(f)
        observation = self.observation(f)
        with self.assertRaisesRegex(ContractError,'RESERVED_CAPACITY'):
            self.record(f,self.receipt(f),observation)
        self.assertEqual(self.snapshot(f),before); self.assertEqual(self.recovered(f),prior)
        self.assertEqual(f.store.snapshot(keys),charged); self.assertEqual(self.actual_writes(f),written)
        evidence = strict_loads(self.recovered(f).projection_wire)['native_observation_commitment']
        self.assertIsNone(evidence)
        self.assertEqual(self.recovered(f).as_dict()['state'],'ATTEMPT_COMMITTED')

    def test_advancing_unavailable_observations_exhaust_one_cumulative_reserve(self):
        f = self.fixture(); receipt = self.receipt(f); steps = []
        for sequence in range(1,10):
            observation = self.observation(f,state=ObservationState.UNAVAILABLE,limit=None,reason='native:unavailable',
                sequence=sequence,clock=parent.clock(1_010_000_000+sequence*5_000_000))
            before = self.snapshot(f); previous = self.recovered(f); written = self.actual_writes(f)
            try: result = self.record(f,receipt,observation)
            except ContractError as error:
                self.assertEqual(error.code,'OUTCOME_RESERVED_CAPACITY_EXCEEDED')
                self.assertEqual(self.snapshot(f),before); self.assertEqual(self.recovered(f),previous)
                self.assertEqual(self.actual_writes(f),written)
                self.assertGreater(len(steps),1); break
            row = result.as_dict(); actual = self.actual_writes(f)
            self.assertEqual(row['state'],'UNCERTAIN'); self.assertEqual(row['stored_bytes'],actual['total'])
            self.assertEqual(row['prior_stored_bytes'],written['total'])
            self.assertLessEqual(actual['total'],f.effect.required_outcome_bytes)
            steps.append(dict(sequence=sequence,stored_bytes=row['stored_bytes'],actual=actual))
        else:self.fail('Finite cumulative reserve never exhausted')
        CUMULATIVE_OBSERVATIONS.append(dict(test_id=self.id(),reserve=f.effect.required_outcome_bytes,steps=steps,
            overflow_sequence=sequence,atomic_denial=True))

    def test_reopened_writer_keeps_cumulative_count_and_denies_next_overflow(self):
        f = self.fixture(reserve=20000); receipt = self.receipt(f)
        for sequence in (1,2):
            result = self.record(f,receipt,self.observation(f,state=ObservationState.UNAVAILABLE,limit=None,reason='native:unavailable',
                sequence=sequence,clock=parent.clock(1_010_000_000+sequence*10_000_000)))
        expected = result; f.close()
        reopened = parent.SqliteJournal(f.root,f.codec,(parent.INSTALLATION,parent.PROJECT),profile=STORE_PROFILE)
        self.addCleanup(reopened.close); kernel = KernelTransactions(reopened,f.codec,parent.INSTALLATION,f.owners)
        self.assertEqual(self.recovered(f,kernel),expected)
        self.assertEqual(expected.as_dict()['stored_bytes'],self.actual_writes(f,reopened)['total'])
        before = reopened.store_position(); actual = self.actual_writes(f,reopened)
        with self.assertRaisesRegex(ContractError,'RESERVED_CAPACITY'):
            self.record(f,receipt,self.observation(f,sequence=3,clock=parent.clock(1_050_000_000)),kernel=kernel)
        self.assertEqual(reopened.store_position(),before); self.assertEqual(self.actual_writes(f,reopened),actual)

    def test_competing_reconciliations_cannot_double_spend_remaining_capacity(self):
        f = self.fixture(reserve=20000); receipt = self.receipt(f)
        self.record(f,receipt,self.observation(f,state=ObservationState.UNAVAILABLE,limit=None,reason='native:unavailable'))
        other = parent.BarrierJournal(f.root,f.codec,(parent.INSTALLATION,parent.PROJECT),profile=STORE_PROFILE)
        self.addCleanup(other.close); kernel = KernelTransactions(other,f.codec,parent.INSTALLATION,f.owners)
        barrier = threading.Barrier(2); f.store.barrier = other.barrier = barrier
        observations = [self.observation(f,state=ObservationState.UNAVAILABLE,limit=None,reason='native:unavailable',
            sequence=n,clock=parent.clock(1_080_000_000+n*1_000_000)) for n in (2,3)]
        def run(pair):
            owner, observation = pair
            try:self.record(f,receipt,observation,kernel=owner); return 'COMMITTED'
            except ContractError:return 'CONFLICT'
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(run,((f.kernel,observations[0]),(kernel,observations[1]))))
        finally:f.store.barrier = other.barrier = None
        self.assertEqual(sorted(results),['COMMITTED','CONFLICT'])
        row = self.recovered(f).as_dict(); self.assertEqual(row['stored_bytes'],self.actual_writes(f)['total'])
        before = self.snapshot(f)
        with self.assertRaisesRegex(ContractError,'RESERVED_CAPACITY'):
            self.record(f,receipt,self.observation(f,sequence=4,clock=parent.clock(1_090_000_000)))
        self.assertEqual(self.snapshot(f),before)

    def test_attempt_count_cannot_be_reduced_to_supply_new_capacity(self):
        for field in ('stored_bytes','attempt_stored_bytes','prior_stored_bytes'):
            with self.subTest(field=field):
                f = self.fixture()
                self.fault_row(f,lambda row:row.update({field:row[field]-1 if row[field] else 1}))
                before = self.snapshot(f)
                with self.assertRaises(ContractError):self.recovered(f)
                self.assertEqual(self.snapshot(f),before)

    def test_prior_and_total_cannot_be_lowered_together_after_settlement(self):
        f = self.fixture(); receipt = self.receipt(f)
        self.record(f,receipt,self.observation(f,state=ObservationState.UNAVAILABLE,limit=None,reason='native:unavailable'))
        def lower(row):row.update(stored_bytes=row['stored_bytes']-1,prior_stored_bytes=row['prior_stored_bytes']-1)
        self.fault_row(f,lower); before = self.snapshot(f)
        with self.assertRaisesRegex(ContractError,'SETTLEMENT_INDEX_MISMATCH'):self.recovered(f)
        with self.assertRaisesRegex(ContractError,'SETTLEMENT_INDEX_MISMATCH'):
            self.record(f,receipt,self.observation(f,sequence=2,clock=parent.clock(1_090_000_000)))
        self.assertEqual(self.snapshot(f),before)

    def test_repeated_exact_uncertain_retries_consume_no_cumulative_bytes(self):
        f = self.fixture(); receipt = self.receipt(f)
        observation = self.observation(f,state=ObservationState.UNAVAILABLE,limit=None,reason='native:unavailable')
        first = self.record(f,receipt,observation); before = self.snapshot(f); written = self.actual_writes(f)
        for _ in range(3):
            self.assertEqual(self.record(f,receipt,observation),first)
            self.assertEqual(self.snapshot(f),before); self.assertEqual(self.actual_writes(f),written)

    def test_failed_reconciliation_neither_consumes_nor_refunds_count(self):
        f = self.fixture(); receipt = self.receipt(f)
        self.record(f,receipt,self.observation(f,state=ObservationState.UNAVAILABLE,limit=None,reason='native:unavailable'))
        before = self.snapshot(f); written = self.actual_writes(f)
        observation = self.observation(f,sequence=2,clock=parent.clock(1_090_000_000))
        def interrupted():raise RuntimeError('cumulative write rollback')
        f.fault = interrupted
        with self.assertRaisesRegex(RuntimeError,'cumulative write'):self.record(f,receipt,observation)
        f.fault = None; self.assertEqual(self.snapshot(f),before); self.assertEqual(self.actual_writes(f),written)
        row = self.record(f,receipt,observation).as_dict()
        self.assertEqual(row['prior_stored_bytes'],written['total'])
        self.assertEqual(row['stored_bytes'],self.actual_writes(f)['total'])
