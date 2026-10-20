"""Real SQLite reconciliation; observer/provenance providers are controlled.

Fresh process identities model OB2's observed one-child-per-call contract. These
tests establish canonical acceptance and rejection, never native authentication.
"""
from dataclasses import replace
import unittest

import test_owned_cpu_outcome_transactions as prior
from ceta.contracts.resource_management import ObservationState, ProcessResourceIdentity
from ceta.contracts.store_transactions import StoreKey
from ceta.contracts.wire import ContractError, strict_loads


class FreshObserverReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prior.OutcomeTransactionsTests.setUpClass()

    def setUp(self):
        self.case = prior.OutcomeTransactionsTests()
        self.addCleanup(self.case.doCleanups)

    def pending(self, *, discrepancy=False):
        f = self.case.fixture()
        receipt = self.case.receipt(f)
        changes = dict(limit=f.effect.original_limit) if discrepancy else dict(
            state=ObservationState.UNAVAILABLE, limit=None, reason='native:unavailable')
        observation = self.case.observation(f, **changes)
        first = self.case.record(f, receipt, observation)
        return f, receipt, observation, first

    def fresh(self, f, **changes):
        fields = dict(observer_identity=ProcessResourceIdentity(202, 300, prior.parent.H),
            sequence=2, clock=prior.parent.clock(1_090_000_000))
        fields.update(changes)
        return self.case.observation(f, **fields)

    def test_fresh_child_can_settle_uncertain_without_replacing_prior_evidence(self):
        f, receipt, observation, first = self.pending()
        result = self.case.record(f, receipt, self.fresh(f))
        row = result.as_dict()
        self.assertEqual(row['state'], 'SETTLED_OBSERVED')
        self.assertEqual(result.receipt_wire, first.receipt_wire)
        self.assertEqual(row['receipt_index'], first.as_dict()['receipt_index'])
        self.assertGreater(row['stored_bytes'], first.as_dict()['stored_bytes'])
        self.assertEqual(row['stored_bytes'], self.case.actual_writes(f)['total'])
        old = strict_loads(first.observation_wire)['observed_payload_ref']
        self.assertEqual(f.cell(StoreKey('projection', f.effect.scope_id, old)).value_wire,
            observation.canonical_wire)
        self.assertEqual(f.store.replay(f.effect.scope_id,
            first.as_dict()['observation_index']['sequence'], 1)[0].payload_wire,
            first.observation_wire)

    def test_fresh_child_can_reconcile_discrepancy(self):
        f, receipt, _, first = self.pending(discrepancy=True)
        self.assertEqual(first.as_dict()['state'], 'DISCREPANCY')
        result = self.case.record(f, receipt, self.fresh(f))
        self.assertEqual(result.as_dict()['state'], 'SETTLED_OBSERVED')

    def test_reused_pid_with_new_creation_time_is_distinct_authenticated_lifetime(self):
        f, receipt, old, _ = self.pending()
        fresh = self.fresh(f, observer_identity=replace(old.observer_identity,
            creation_time=old.observer_identity.creation_time + 1))
        self.assertEqual(self.case.record(f, receipt, fresh).as_dict()['state'], 'SETTLED_OBSERVED')

    def test_fresh_child_different_image_is_denied_atomically(self):
        f, receipt, _, _ = self.pending()
        before = self.case.snapshot(f)
        with self.assertRaisesRegex(ContractError, 'OUTCOME_OBSERVATION_REPLAY'):
            self.case.record(f, receipt, self.fresh(f,
                observer_identity=ProcessResourceIdentity(202, 300, prior.parent.H2)))
        self.assertEqual(self.case.snapshot(f), before)

    def test_new_child_identity_does_not_reset_controller_sequence(self):
        f, receipt, _, _ = self.pending()
        before = self.case.snapshot(f)
        for sequence in (0, 1):
            with self.subTest(sequence=sequence), self.assertRaises(ContractError):
                self.case.record(f, receipt, self.fresh(f, sequence=sequence))
        self.assertEqual(self.case.snapshot(f), before)

    def test_new_child_identity_does_not_allow_equal_or_older_observation_time(self):
        f, receipt, old, _ = self.pending()
        before = self.case.snapshot(f)
        for sample in (old.clock, prior.parent.clock(old.clock.monotonic_ns - 1)):
            with self.subTest(sample=sample), self.assertRaisesRegex(
                    ContractError, 'OUTCOME_OBSERVATION_REPLAY'):
                self.case.record(f, receipt, self.fresh(f, clock=sample))
        self.assertEqual(self.case.snapshot(f), before)

    def test_fresh_lifetime_still_requires_the_exact_captured_native_proof(self):
        f, receipt, _, _ = self.pending()
        before = self.case.snapshot(f)
        for supplied in (object(), True, False, {}):
            with self.subTest(kind=type(supplied).__name__), self.assertRaises(ContractError):
                self.case.record(f, receipt, self.fresh(f), proof=supplied)
        self.assertEqual(self.case.snapshot(f), before)

    def test_changed_observer_implementation_cannot_use_fresh_lifetime(self):
        f, receipt, _, _ = self.pending()
        before = self.case.snapshot(f)
        with self.assertRaisesRegex(ContractError, 'OUTCOME_OBSERVATION_BINDING_MISMATCH'):
            self.case.record(f, receipt, self.fresh(f, observer_commitment=prior.parent.H2))
        self.assertEqual(self.case.snapshot(f), before)

    def test_exact_fresh_child_retry_and_recovery_remain_read_only(self):
        f, receipt, _, _ = self.pending()
        observation = self.fresh(f)
        first = self.case.record(f, receipt, observation)
        before = self.case.snapshot(f)
        self.assertEqual(self.case.record(f, receipt, observation), first)
        self.assertEqual(self.case.recovered(f), first)
        self.assertEqual(self.case.snapshot(f), before)

    def test_new_child_after_terminal_settlement_is_denied_without_refund(self):
        f, receipt, _, _ = self.pending()
        self.case.record(f, receipt, self.fresh(f))
        before = self.case.snapshot(f)
        with self.assertRaisesRegex(ContractError, 'OUTCOME_ALREADY_SETTLED'):
            self.case.record(f, receipt, self.fresh(f, sequence=3,
                observer_identity=ProcessResourceIdentity(203, 400, prior.parent.H),
                clock=prior.parent.clock(1_095_000_000)))
        self.assertEqual(self.case.snapshot(f), before)

    def test_multiple_fresh_unavailable_children_use_one_cumulative_reserve(self):
        f, receipt, _, initial = self.pending()
        previous = initial.as_dict()['stored_bytes']
        for sequence in (2, 3):
            fresh = self.fresh(f, sequence=sequence,
                observer_identity=ProcessResourceIdentity(201 + sequence, 200 + sequence, prior.parent.H),
                clock=prior.parent.clock(1_080_000_000 + sequence * 1_000_000),
                state=ObservationState.UNAVAILABLE, limit=None, reason='native:unavailable')
            row = self.case.record(f, receipt, fresh).as_dict()
            self.assertEqual(row['state'], 'UNCERTAIN')
            self.assertEqual(row['prior_stored_bytes'], previous)
            self.assertEqual(row['stored_bytes'], self.case.actual_writes(f)['total'])
            previous = row['stored_bytes']
