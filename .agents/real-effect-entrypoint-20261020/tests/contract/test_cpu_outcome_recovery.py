"""Real canonical SQLite recovery with explicitly CONTROLLED native origins.

No native worker, CPU Set, Hello or host configuration operation is executed.
"""
import copy
from dataclasses import replace
from pathlib import Path
import pickle
import threading
import unittest
from unittest.mock import patch

from ceta.contracts.wire import ContractError, strict_loads
from ceta.identity import cpu_outcome_capacity as bindings
from ceta.kernel import cpu_execution
from ceta.store.journal import SqliteJournal
from ceta.store.outcome_capacity import OutcomeCapacityLease
from ceta.supervisor.windows_jobs import WindowsOwnedProcess
import test_cpu_capacity_connection as base

ROOT = Path(__file__).resolve().parents[2]
FACTS = base.FACTS


class CpuOutcomeRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = strict_loads((ROOT/'contracts/schemas/records.schema.json').read_bytes())

    def fixture(self):
        f = object.__new__(base.Fixture)
        self.addCleanup(f.close)
        base.Fixture.__init__(f, self.schema)
        return f

    def pending(self, f, *, lost_notification=False, observation=True):
        primary = RuntimeError('controlled outcome write failure')
        def fault(): raise primary
        original = SqliteJournal._capacity_commit
        def notification(store, entries, result, retained):
            if store is f.store and retained is not None and retained._lengths:
                raise primary
            return original(store, entries, result, retained)
        execution = f.lease()
        evidence = None
        try:
            with patch.object(SqliteJournal, '_capacity_commit', notification if lost_notification else original):
                with execution:
                    f.fence(execution)
                    evidence = f.evidence(observation=observation)
                    if not lost_notification: f.store._fault = fault
                    execution.record_outcome(*evidence)
        except RuntimeError as caught:
            self.assertIs(caught, primary)
        finally:
            f.store._fault = None
        self.assertTrue(execution._pending_cleanup)
        self.assertEqual(execution._retained.state, 'FAILED')
        self.assertIsNotNone(execution._pending_transaction)
        self.assertEqual(execution._outcome_capacity.lease.state, 'PENDING')
        return execution, evidence, primary

    def assert_closed(self, f, execution):
        self.assertTrue(execution._closed)
        self.assertFalse(execution._pending_cleanup)
        self.assertIsNone(execution._owner.active)
        self.assertIsNone(f.owner._execution)
        self.assertIsNone(f.store._capacity_active)
        self.assertIsNone(execution._pending_transaction)
        self.assertEqual(execution._outcome_capacity.lease.state, 'CLOSED')
        self.assertTrue(execution._outcome_capacity.lease.durable)
        self.assertEqual(f.status(), 'CONSUMED')

    def test_failed_commit_retries_exact_bytes_through_canonical_outcome(self):
        f = self.fixture(); execution, evidence, primary = self.pending(f)
        pending = execution._pending_transaction
        held = execution._outcome_capacity.lease
        previous = held.retained_payloads()
        with f.capture_commit(), execution.recover_outcome(f.context) as recovered:
            self.assertIs(recovered, execution)
            result = recovered.record_outcome(*evidence)
            self.assertEqual(result.as_dict()['state'], 'SETTLED_OBSERVED')
            self.assertEqual(held.retained_payloads(), previous)
            self.assertEqual(f.commit_calls[-1]['entries'], pending.entries)
        self.assert_closed(f, execution)
        self.assertIsNotNone(execution._cleanup_failure)
        self.assertTrue(execution._retained.cleanup_errors)

    def test_lost_commit_notification_uses_exact_verified_readback_no_new_write(self):
        f = self.fixture(); execution, evidence, _ = self.pending(f, lost_notification=True)
        position = f.store.store_position()
        pending = execution._pending_transaction
        self.assertEqual(position.next_commit, pending.position.next_commit + 1)
        with f.capture_commit(), execution.recover_outcome(f.context):
            result = execution.record_outcome(*evidence)
            self.assertEqual(result.as_dict()['state'], 'SETTLED_OBSERVED')
        self.assertEqual(f.commit_calls, [])
        self.assertEqual(f.store.store_position(), position)
        self.assert_closed(f, execution)

    def test_recovery_after_stop_preserves_consumption_and_blocks_dispatch(self):
        f = self.fixture(); execution, evidence, _ = self.pending(f)
        execution.cancel()
        self.assertTrue(execution._owner.stopped.is_set())
        with execution.recover_outcome(f.context):
            with self.assertRaisesRegex(ContractError, 'BOOKKEEPING_ONLY'):
                execution.driver_arguments()
            with self.assertRaisesRegex(ContractError, 'SINGLE_DISPATCH'):
                execution.dispatch()
            execution.record_outcome(*evidence)
        self.assert_closed(f, execution)
        self.assertTrue(execution._owner.stopped.is_set())

    def test_recovery_rejects_foreign_context_without_changing_custody(self):
        f = self.fixture(); execution, _, _ = self.pending(f)
        capacity = execution._outcome_capacity.lease
        with self.assertRaisesRegex(ContractError, 'ORIGINAL_CONTEXT'):
            with execution.recover_outcome(object()): pass
        self.assertIs(f.store._capacity_active, capacity)
        self.assertIsNone(execution._recovery)
        self.assertEqual(execution._retained.state, 'FAILED')

    def test_recovery_rejects_other_thread(self):
        f = self.fixture(); execution, _, _ = self.pending(f)
        errors = []
        def run():
            try:
                with execution.recover_outcome(f.context): pass
            except BaseException as error: errors.append(error)
        worker = threading.Thread(target=run); worker.start(); worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(len(errors), 1)
        self.assertIn('ORIGINAL_CONTEXT', str(errors[0]))

    def test_unknown_original_context_stays_denied(self):
        f = self.fixture(); execution, _, _ = self.pending(f)
        f.owner._dispatch = None
        with self.assertRaisesRegex(ContractError, 'ORIGINAL_BINDING_CHANGED'):
            with execution.recover_outcome(f.context): pass
        self.assertTrue(execution._pending_cleanup)
        self.assertIs(f.store._capacity_active, execution._outcome_capacity.lease)

    def test_recovery_is_noncopyable_and_single_use(self):
        f = self.fixture(); execution, evidence, _ = self.pending(f)
        recovery = execution.recover_outcome(f.context)
        for call in (lambda: copy.copy(recovery), lambda: copy.deepcopy(recovery), lambda: pickle.dumps(recovery)):
            with self.assertRaises(ContractError): call()
        with recovery: execution.record_outcome(*evidence)
        with self.assertRaisesRegex(ContractError, 'ORIGINAL_CONTEXT'):
            with recovery: pass

    def test_failed_retry_preserves_primary_bytes_and_allows_later_original_retry(self):
        f = self.fixture(); execution, evidence, _ = self.pending(f)
        pending = execution._pending_transaction
        primary = RuntimeError('second write failure')
        def fault(): raise primary
        f.store._fault = fault
        try:
            with self.assertRaises(RuntimeError) as caught:
                with execution.recover_outcome(f.context): execution.record_outcome(*evidence)
            self.assertIs(caught.exception, primary)
        finally: f.store._fault = None
        self.assertIs(execution._pending_transaction, pending)
        self.assertEqual(execution._outcome_capacity.state, 'PENDING')
        with execution.recover_outcome(f.context): execution.record_outcome(*evidence)
        self.assert_closed(f, execution)

    def test_changed_receipt_cannot_replace_pending_transaction(self):
        f = self.fixture(); execution, evidence, _ = self.pending(f)
        pending = execution._pending_transaction
        replacement = f.evidence()
        with self.assertRaisesRegex(ContractError, 'EXACT_PENDING_OUTCOME'):
            with execution.recover_outcome(f.context): execution.record_outcome(*replacement)
        self.assertIs(execution._pending_transaction, pending)
        with execution.recover_outcome(f.context): execution.record_outcome(*evidence)
        self.assert_closed(f, execution)

    def test_missing_outcome_does_not_release_or_clear_liveness(self):
        f = self.fixture(); execution, _, _ = self.pending(f)
        with self.assertRaises(ContractError):
            with execution.recover_outcome(f.context): pass
        self.assertFalse(execution._closed)
        self.assertTrue(execution._pending_cleanup)
        self.assertIs(execution._owner.active, execution)
        self.assertIs(f.store._capacity_active, execution._outcome_capacity.lease)

    def test_fresh_reservation_advances_uncertain_outcome_without_reconsumption(self):
        f = self.fixture()
        with f.lease() as execution:
            f.fence(execution)
            first = f.evidence(observation=False)
            uncertain = execution.record_outcome(*first)
        old = execution._outcome_capacity.lease
        self.assertEqual(uncertain.as_dict()['state'], 'UNCERTAIN')
        original_consume = execution._permit.canonical_wire
        observation = f.evidence()[1]
        proof = object()
        f.proofs[proof] = (f.request.canonical_wire, original_consume, first[0], observation)
        with execution.recover_outcome(f.context):
            self.assertIsNone(f.store._capacity_active)
            result = execution.record_outcome(first[0], observation, proof)
            fresh = execution._outcome_capacity.lease
            self.assertIsNot(fresh, old)
            self.assertIs(fresh.journal, old.journal)
            self.assertEqual(result.as_dict()['state'], 'SETTLED_OBSERVED')
            self.assertEqual(result.receipt_wire, first[0])
        self.assertEqual(execution._permit.canonical_wire, original_consume)
        self.assertIn(old, execution._outcome_capacity.previous_leases)
        self.assert_closed(f, execution)

    def test_exact_retry_of_closed_uncertain_outcome_never_allocates_or_writes(self):
        f = self.fixture()
        with f.lease() as execution:
            f.fence(execution)
            evidence = f.evidence(observation=False)
            first = execution.record_outcome(*evidence)
        position, held = f.store.store_position(), execution._outcome_capacity.lease
        with patch.object(SqliteJournal, 'reserve_outcome_capacity', side_effect=AssertionError('unexpected reserve')):
            with execution.recover_outcome(f.context):
                self.assertEqual(execution.record_outcome(*evidence), first)
        self.assertIs(execution._outcome_capacity.lease, held)
        self.assertEqual(f.store.store_position(), position)
        self.assert_closed(f, execution)

    def test_failed_direct_second_staging_does_not_publish_pending_transaction(self):
        f = self.fixture()
        with f.lease() as execution:
            f.fence(execution)
            first = f.evidence(observation=False)
            execution.record_outcome(*first)
            observation = f.evidence()[1]; proof = object()
            f.proofs[proof] = (f.request.canonical_wire, execution._permit.canonical_wire, first[0], observation)
            with self.assertRaisesRegex(ContractError, 'RECONCILIATION_RESERVATION_REQUIRED'):
                execution.record_outcome(first[0], observation, proof)
            self.assertIsNone(execution._pending_transaction)
        with execution.recover_outcome(f.context): execution.record_outcome(first[0], observation, proof)
        self.assert_closed(f, execution)

    def test_settled_outcome_cannot_allocate_another_reservation(self):
        f = self.fixture()
        with f.lease() as execution:
            f.fence(execution); execution.record_outcome(*f.evidence())
        with self.assertRaisesRegex(ContractError, 'RECONCILABLE_OUTCOME'):
            with execution.recover_outcome(f.context): pass
        self.assertIsNone(f.store._capacity_active)
        self.assertTrue(execution._closed)

    def test_post_mark_stop_captures_original_denial_and_records_without_observer(self):
        f = self.fixture()
        def controlled_wt4(target, *args, **kwargs):
            kwargs['dispatch_fence']()
            self.fail('Stop must deny the controlled final fence')
        original_mark = OutcomeCapacityLease.mark_may_have_executed
        def mark(held):
            original_mark(held)
            f.kernel._cpu_execution.stopped.set()
        with patch.object(WindowsOwnedProcess, 'apply_cpu_rate_limit', controlled_wt4), patch.object(cpu_execution, '_APPLY', controlled_wt4):
            execution = f.lease()
            with self.assertRaisesRegex(ContractError, 'STOPPED'):
                with execution, patch.object(OutcomeCapacityLease, 'mark_may_have_executed', mark):
                    execution.dispatch()
            self.assertFalse(execution._dispatch)
            self.assertIsNotNone(execution._denied_dispatch)
            self.assertTrue(execution._outcome_capacity.lease.may_have_executed)
            with execution.recover_outcome(f.context):
                outcome = execution.record_denied_outcome()
                self.assertEqual(outcome.as_dict()['state'], 'UNCERTAIN')
                self.assertEqual(strict_loads(outcome.receipt_wire)['effect_status'], 'NOT_STARTED')
        self.assert_closed(f, execution)

    def test_caller_flag_without_captured_denial_is_rejected(self):
        f = self.fixture()
        with f.lease() as execution:
            execution._called = True
            with self.assertRaisesRegex(ContractError, 'DENIAL_NOT_ESTABLISHED'):
                execution.record_denied_outcome()

    def test_uncertain_native_release_is_not_retried(self):
        f = self.fixture(); execution, _, _ = self.pending(f)
        execution._outcome_capacity.lease.release_attempted = True
        try:
            with self.assertRaisesRegex(ContractError, 'UNCERTAIN_RETIREMENT'):
                with execution.recover_outcome(f.context): pass
        finally:
            # Controlled fixture did not perform a native release; restore its
            # injected flag only for explicit no-effect fixture disposal.
            execution._outcome_capacity.lease.release_attempted = False

    def test_unconfigured_capacity_failed_entry_retires_without_consumption(self):
        f = self.fixture()
        f.store._capacity_vfs = None  # No native registration exists in this controlled fixture.
        execution = f.lease()
        with self.assertRaisesRegex(ContractError, 'NOT_CONFIGURED'): execution.__enter__()
        self.assertEqual(f.status(), 'PREPARED')
        self.assertTrue(execution._pending_cleanup)
        result = execution.retire_failed_entry(f.context)
        self.assertTrue(result['closed'])
        self.assertFalse(result['pending_cleanup'])
        self.assertIsNone(f.kernel._cpu_execution.active)
        self.assertIsNone(f.owner._execution)
        self.assertIsNone(execution._outcome_capacity.lease)
        self.assertEqual(f.status(), 'PREPARED')

    def test_failed_entry_retirement_rejects_consumed_attempt(self):
        f = self.fixture(); execution, _, _ = self.pending(f)
        with self.assertRaisesRegex(ContractError, 'EMPTY_ENTRY_REQUIRED'):
            execution.retire_failed_entry(f.context)
        self.assertEqual(f.status(), 'CONSUMED')

    def test_readback_rejects_changed_canonical_transaction_metadata(self):
        f = self.fixture(); execution, evidence, _ = self.pending(f, lost_notification=True)
        pending = execution._pending_transaction
        changed = replace(pending.changes[0], event_id=pending.entries[0] and 'event:foreign')
        with execution.recover_outcome(f.context):
            with self.assertRaisesRegex(ContractError, 'RECOVERY_HEAD_MISMATCH|RECOVERY_COMMIT_MISMATCH'):
                f.store._recover_capacity_commit(execution._outcome_capacity.lease,
                    pending.expected, pending.entries, pending.checks, (changed, *pending.changes[1:]),
                    pending.cells, pending.position, lambda: None)
            self.assertFalse(execution._outcome_capacity.lease.durable)
            execution.record_outcome(*evidence)
        self.assert_closed(f, execution)

    def test_readback_rejects_foreign_journal(self):
        f = self.fixture(); execution, evidence, _ = self.pending(f, lost_notification=True)
        other = self.fixture(); pending = execution._pending_transaction
        with execution.recover_outcome(f.context):
            with self.assertRaisesRegex(ContractError, 'RECOVERY_OWNER_CHANGED'):
                other.store._recover_capacity_commit(execution._outcome_capacity.lease,
                    pending.expected, pending.entries, pending.checks, pending.changes,
                    pending.cells, pending.position, lambda: None)
            execution.record_outcome(*evidence)
        self.assert_closed(f, execution)

    def test_pending_outcome_still_requires_original_provenance(self):
        f = self.fixture(); execution, evidence, _ = self.pending(f)
        with self.assertRaisesRegex(ContractError, 'CONTROLLED_ORIGIN_NOT_RETAINED'):
            with execution.recover_outcome(f.context): execution.record_outcome(evidence[0], evidence[1], object())
        self.assertIsNotNone(execution._pending_transaction)
        with execution.recover_outcome(f.context): execution.record_outcome(*evidence)
        self.assert_closed(f, execution)

    def test_original_native_context_retirement_prevents_empty_entry_release(self):
        f = self.fixture(); f.store._capacity_vfs = None
        execution = f.lease()
        with self.assertRaisesRegex(ContractError, 'NOT_CONFIGURED'): execution.__enter__()
        f.owner._registry._active.clear()
        with self.assertRaisesRegex(ContractError, 'CONTEXT_CHANGED'):
            execution.retire_failed_entry(f.context)
        self.assertTrue(execution._pending_cleanup)
        self.assertIs(f.kernel._cpu_execution.active, execution)

    def test_recovery_retains_liveness_if_registration_retirement_raises(self):
        f = self.fixture(); execution, evidence, _ = self.pending(f)
        primary = RuntimeError('controlled liveness retirement failure')
        with patch.object(type(execution._owner), 'release_liveness', side_effect=primary):
            with self.assertRaises(RuntimeError) as caught:
                with execution.recover_outcome(f.context): execution.record_outcome(*evidence)
        self.assertIs(caught.exception, primary)
        self.assertFalse(execution._closed)
        self.assertTrue(execution._pending_cleanup)
        self.assertIs(execution._owner.active, execution)
        self.assertTrue(execution._outcome_capacity.lease.durable)
        self.assertEqual(execution._outcome_capacity.lease.state, 'CLOSED')
