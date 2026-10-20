"""Authority freshness regressions; IMPLEMENTED_NOT_QUALIFIED.

KernelCommitAuthorityTests uses the real v2 SQLite KernelFixture and its existing
before/after-COMMIT hooks with explicitly synthetic identity/decision owners.
NativeAuthorityResolutionTests uses real owned Windows service/client/IPC after
synthetic preparation and consumption; the parent journal is closed first. The
child's positive authority remains CLOSED. No effect, real approval, trusted
clock, protected resource, original B acceptance or independence is qualified.
"""
from dataclasses import replace
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ceta.contracts.events import EventContract, StreamPosition
from ceta.contracts.kernel_transactions import PeerIdentity, ZERO_BUDGET, encode_basis, read_basis
from ceta.contracts.store_transactions import StoreKey
from ceta.contracts.temporal import utc_nanoseconds
from ceta.contracts.wire import ContractError, canonical_bytes, strict_loads
from test_kernel_transactions import COST, PROJECT, KernelFixture
from test_owned_service import _ServiceTestCase


class KernelCommitAuthorityTests(unittest.TestCase):
    """Actual SQLite boundaries, controlled owner changes, no native authority."""

    @classmethod
    def setUpClass(cls):
        cls.schema = strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes())

    def setUp(self):
        self.fixtures = []

    def fixture(self):
        fixture = KernelFixture(self.schema)
        self.fixtures.append(fixture)
        return fixture

    def tearDown(self):
        for fixture in self.fixtures:
            fixture.before_commit_action = None
            fixture.store.after_commit = None
            fixture.store.close()

    def operation(self, fixture, operation):
        if operation == "prepare":
            context = fixture.owners.worker_context
            return lambda: fixture.service.prepare(fixture.proposal_wire, context), (), None
        if operation == "consume":
            prepared = fixture.prepare()
            context = fixture.owners.worker_context
            return (lambda: fixture.service.consume(prepared.record_wire, context),
                    fixture.permit_keys(prepared.record_wire), prepared)
        if operation == "revoke":
            context = fixture.owners.owner_context
            return (lambda: fixture.service.revoke(fixture.grant_wire, context, "reason:owner-revoke"),
                    (), None)
        raise AssertionError("unknown fixture operation")

    def invalidation(self, fixture, operation, kind):
        if kind == "context":
            name = "owner_context" if operation == "revoke" else "worker_context"
            return lambda: setattr(fixture.owners, name, object()), "FIXTURE_AUTHENTICATION_DENIED"
        if kind in {"principal", "session"}:
            original = fixture.owners.worker
            changed = PeerIdentity(
                "worker:replacement" if kind == "principal" else original.principal_id,
                "session:replacement" if kind == "session" else original.session_id)
            return lambda: setattr(fixture.owners, "worker", changed), "KERNEL_PEER_BINDING_MISMATCH"
        if kind != "owner":
            raise AssertionError("unknown fixture invalidation")
        if operation == "prepare":
            return fixture.owners.prepared.clear, "FIXTURE_PREPARATION_DENIED"
        if operation == "consume":
            return lambda: setattr(fixture.owners, "admission_available", False), "FIXTURE_ADMISSION_DENIED"
        # The existing revocation predicate receives the original ACTIVE grant.
        # Withdraw only that fixture decision, keeping identity/time/store stable.
        original = fixture.owners.require_revocation
        available = [True]

        def require_revocation(grant, peer, reason_ref):
            if not available[0]:
                raise ContractError("FIXTURE_REVOCATION_DENIED")
            return original(grant, peer, reason_ref)

        fixture.owners.require_revocation = require_revocation
        return lambda: available.__setitem__(0, False), "FIXTURE_REVOCATION_DENIED"

    def denial_before_commit(self, operation, kind):
        fixture = self.fixture()
        action, keys, _ = self.operation(fixture, operation)
        invalidate, code = self.invalidation(fixture, operation, kind)
        before = fixture.cut(keys), fixture.budget()
        reached = []

        def change_owner():
            reached.append(True)
            invalidate()

        fixture.before_commit_action = change_owner
        try:
            with self.assertRaises(ContractError) as caught:
                action()
            self.assertEqual(caught.exception.code, code)
        finally:
            fixture.before_commit_action = None
        self.assertEqual(reached, [True], "invalidation did not reach the real writer boundary")
        self.assertEqual((fixture.cut(keys), fixture.budget()), before)
        fixture.reopen()
        self.assertEqual((fixture.cut(keys), fixture.budget()), before)

    def assert_prepared_commit(self, fixture):
        association = strict_loads(fixture.cell(fixture.issuance_key()).value_wire)
        record = fixture.codec.decode(fixture.cell(
            StoreKey("permit", PROJECT, association["permit_id"])).value_wire)
        permit = record.as_dict()
        self.assertEqual(permit["status"], "PREPARED")
        self.assertIsNone(permit["consume_event_ref"])
        self.assertEqual(permit["proposal_ref"], fixture.proposal["record_id"])
        keys = fixture.permit_keys(record.canonical_wire)
        self.assertEqual(strict_loads(fixture.cell(keys[1]).value_wire)["state"], "HELD")
        self.assertEqual(strict_loads(fixture.cell(keys[2]).value_wire)["state"], "INTENT_COMMITTED")
        self.assertEqual(fixture.budget()[2:], (COST, ZERO_BUDGET))
        prior = StreamPosition(PROJECT, association["sequence"], association["previous_head"])
        rows = fixture.store.replay(PROJECT, prior.next_sequence, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].payload_wire, record.canonical_wire)
        events = EventContract(fixture.codec)
        event = events.require_successor(rows[0].event_wire, prior)
        events.require_payload(rows[0].event_wire, rows[0].payload_wire)
        self.assertEqual(event.record.record_id, permit["issuance_evidence_ref"])
        self.assertEqual(event.record.record_id, association["issuance_event_ref"])
        self.assertEqual(event.record.as_dict()["event_type"], "kernel.intent.committed")
        return record, keys

    def assert_consumed_commit(self, fixture, prepared):
        keys = fixture.permit_keys(prepared.record_wire)
        record = fixture.codec.decode(fixture.cell(keys[0]).value_wire)
        self.assertEqual(record.as_dict()["status"], "CONSUMED")
        self.assertIsNotNone(record.as_dict()["consume_event_ref"])
        self.assertEqual(strict_loads(fixture.cell(keys[1]).value_wire)["state"], "CHARGED")
        self.assertEqual(strict_loads(fixture.cell(keys[2]).value_wire)["state"], "ADMISSION_REDEEMED")
        self.assertEqual(fixture.budget()[2:], (ZERO_BUDGET, COST))
        # Deliberately keep the existing INTERNAL one-argument compatibility API.
        evidence = fixture.service.resolve_consumption(record)
        self.assertEqual(evidence.consumed_permit_wire, record.canonical_wire)
        rows = fixture.store.replay(PROJECT, evidence.prior_position.next_sequence, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].event_wire, evidence.event_wire)
        self.assertEqual(rows[0].payload_wire, evidence.consumed_permit_wire)
        return record, keys

    def denial_after_commit(self, operation, kind):
        fixture = self.fixture()
        action, keys, prepared = self.operation(fixture, operation)
        invalidate, code = self.invalidation(fixture, operation, kind)
        before = fixture.store.store_position()
        budget_before = fixture.budget()
        reached = []

        def change_owner():
            reached.append(True)
            invalidate()

        fixture.store.after_commit = change_owner
        try:
            with self.assertRaises(ContractError) as caught:
                action()
            self.assertEqual(caught.exception.code, code)
        finally:
            fixture.store.after_commit = None
        self.assertEqual(reached, [True], "invalidation did not follow real SQLite COMMIT")
        self.assertEqual(fixture.store.store_position().next_commit, before.next_commit + 1)
        if operation == "prepare":
            _, keys = self.assert_prepared_commit(fixture)
        elif operation == "consume":
            self.assert_consumed_commit(fixture, prepared)
        else:
            revoked = fixture.codec.decode(fixture.cell(fixture.grant_key).value_wire).as_dict()
            self.assertEqual(revoked["status"], "REVOKED")
            self.assertEqual(revoked["revocation_generation"], 1)
            self.assertEqual(revoked["causation_ref"], "reason:owner-revoke")
            self.assertEqual(fixture.budget(), budget_before)
        committed = fixture.cut(keys), fixture.budget()
        fixture.reopen()
        self.assertEqual((fixture.cut(keys), fixture.budget()), committed)
        if operation == "consume":
            self.assert_consumed_commit(fixture, prepared)
            with self.assertRaises(ContractError) as duplicate:
                fixture.service.consume(prepared.record_wire, fixture.owners.worker_context)
            self.assertEqual(duplicate.exception.code, "KERNEL_PERMIT_NOT_PREPARED")
            self.assertEqual((fixture.cut(keys), fixture.budget()), committed)

    def test_valid_original_owner_predicates_prepare_consume_revoke_and_internal_resolution(self):
        fixture = self.fixture()
        prepared = fixture.prepare()
        self.assert_prepared_commit(fixture)
        consumed = fixture.service.consume(prepared.record_wire, fixture.owners.worker_context)
        record, keys = self.assert_consumed_commit(fixture, prepared)
        self.assertEqual(record.canonical_wire, consumed.record_wire)
        revoked = fixture.service.revoke(fixture.grant_wire, fixture.owners.owner_context,
                                         "reason:owner-revoke")
        self.assertEqual(fixture.codec.decode(revoked.record_wire).as_dict()["status"], "REVOKED")
        before = fixture.cut(keys), fixture.budget()
        self.assertEqual(fixture.service.resolve_consumption(record).event_wire, consumed.event_wire)
        self.assertEqual((fixture.cut(keys), fixture.budget()), before)
        with self.assertRaises(ContractError) as unavailable:
            fixture.service.require_runtime_admission()
        self.assertEqual(unavailable.exception.code, "RUNTIME_AUTHORITY_OWNERS_UNAVAILABLE")

    def test_prepare_precommit_captured_context_invalidation_rolls_back(self):
        self.denial_before_commit("prepare", "context")

    def test_prepare_precommit_preparation_decision_withdrawal_rolls_back(self):
        self.denial_before_commit("prepare", "owner")

    def test_consume_precommit_captured_context_invalidation_rolls_back(self):
        self.denial_before_commit("consume", "context")

    def test_consume_precommit_admission_decision_withdrawal_rolls_back(self):
        self.denial_before_commit("consume", "owner")

    def test_revoke_precommit_captured_context_invalidation_rolls_back(self):
        self.denial_before_commit("revoke", "context")

    def test_revoke_precommit_revocation_decision_withdrawal_rolls_back(self):
        self.denial_before_commit("revoke", "owner")

    def test_consume_precommit_authenticated_principal_substitution_rolls_back(self):
        self.denial_before_commit("consume", "principal")

    def test_consume_precommit_authenticated_session_substitution_rolls_back(self):
        self.denial_before_commit("consume", "session")

    def test_prepare_postcommit_context_invalidation_denies_but_retains_held_state(self):
        self.denial_after_commit("prepare", "context")

    def test_prepare_postcommit_decision_withdrawal_denies_but_retains_held_state(self):
        self.denial_after_commit("prepare", "owner")

    def test_consume_postcommit_context_invalidation_denies_but_retains_charge(self):
        self.denial_after_commit("consume", "context")

    def test_consume_postcommit_decision_withdrawal_denies_but_retains_charge(self):
        self.denial_after_commit("consume", "owner")

    def test_revoke_postcommit_context_invalidation_denies_but_retains_revocation(self):
        self.denial_after_commit("revoke", "context")

    def test_revoke_postcommit_decision_withdrawal_denies_but_retains_revocation(self):
        self.denial_after_commit("revoke", "owner")

    def test_owner_spies_receive_identical_original_records_and_basis_at_all_commit_phases(self):
        fixture = self.fixture()
        proposal = fixture.codec.decode(fixture.proposal_wire)
        grant = fixture.codec.decode(fixture.grant_wire)
        phase, observed = ["initial"], {name: [] for name in ("prepare", "consume", "revoke")}
        original_prepare = fixture.owners.require_prepared_basis
        original_admission = fixture.owners.require_admission
        original_revocation = fixture.owners.require_revocation
        expected_permit = [None]

        def prepared_spy(actual, basis_wire, peer):
            self.assertEqual(actual, proposal)
            self.assertEqual(actual.original_wire, fixture.proposal_wire)
            self.assertEqual(basis_wire, fixture.basis)
            observed["prepare"].append(phase[0])
            return original_prepare(actual, basis_wire, peer)

        def admission_spy(actual, basis_wire, peer):
            self.assertEqual(actual, expected_permit[0])
            self.assertEqual(actual.original_wire, expected_permit[0].original_wire)
            self.assertEqual(actual.as_dict()["status"], "PREPARED")
            self.assertEqual(basis_wire, fixture.basis)
            observed["consume"].append(phase[0])
            return original_admission(actual, basis_wire, peer)

        def revocation_spy(actual, peer, reason_ref):
            self.assertEqual(actual, grant)
            self.assertEqual(actual.original_wire, fixture.grant_wire)
            self.assertEqual(actual.as_dict()["status"], "ACTIVE")
            observed["revoke"].append(phase[0])
            return original_revocation(actual, peer, reason_ref)

        fixture.before_commit_action = lambda: phase.__setitem__(0, "preCOMMIT")
        fixture.store.after_commit = lambda: phase.__setitem__(0, "postCOMMIT")
        try:
            with patch.object(fixture.owners, "require_prepared_basis", prepared_spy), \
                    patch.object(fixture.owners, "require_admission", admission_spy), \
                    patch.object(fixture.owners, "require_revocation", revocation_spy):
                prepared = fixture.prepare()
                expected_permit[0] = fixture.codec.decode(prepared.record_wire)
                self.assert_prepared_commit(fixture)
                phase[0] = "initial"
                consumed = fixture.service.consume(prepared.record_wire, fixture.owners.worker_context)
                record, keys = self.assert_consumed_commit(fixture, prepared)
                self.assertEqual(record.canonical_wire, consumed.record_wire)
                phase[0] = "initial"
                revoked = fixture.service.revoke(fixture.grant_wire, fixture.owners.owner_context,
                                                 "reason:owner-revoke")
                self.assertEqual(fixture.codec.decode(revoked.record_wire).as_dict()["status"], "REVOKED")
                for operation in ("prepare", "consume", "revoke"):
                    self.assertTrue({"initial", "preCOMMIT", "postCOMMIT"}.issubset(observed[operation]),
                                    (operation, observed[operation]))
                before = fixture.cut(keys), fixture.budget()
                self.assertEqual(fixture.service.resolve_consumption(record).event_wire, consumed.event_wire)
                self.assertEqual((fixture.cut(keys), fixture.budget()), before)
        finally:
            fixture.before_commit_action = None
            fixture.store.after_commit = None

    def test_context_invalidated_inside_precommit_owner_predicate_rolls_back(self):
        fixture = self.fixture()
        prepared = fixture.prepare()
        keys, context = fixture.permit_keys(prepared.record_wire), fixture.owners.worker_context
        before = fixture.cut(keys), fixture.budget()
        armed, reached = [False], []
        original = fixture.owners.require_admission

        def admission_then_invalidate(permit, basis_wire, peer):
            result = original(permit, basis_wire, peer)
            if armed[0]:
                reached.append(True)
                fixture.owners.worker_context = object()
            return result

        fixture.before_commit_action = lambda: armed.__setitem__(0, True)
        try:
            with patch.object(fixture.owners, "require_admission", admission_then_invalidate):
                with self.assertRaises(ContractError) as caught:
                    fixture.service.consume(prepared.record_wire, context)
                self.assertEqual(caught.exception.code, "FIXTURE_AUTHENTICATION_DENIED")
        finally:
            fixture.before_commit_action = None
        self.assertEqual(reached, [True])
        self.assertEqual((fixture.cut(keys), fixture.budget()), before)
        fixture.reopen()
        self.assertEqual((fixture.cut(keys), fixture.budget()), before)

    def test_peer_bound_historical_queries_after_expiry_revocation_and_unrelated_progress_are_readonly(self):
        fixture = self.fixture()
        prepared = fixture.prepare()
        consumed = fixture.service.consume(prepared.record_wire, fixture.owners.worker_context)
        keys = fixture.permit_keys(prepared.record_wire)
        last = fixture.owners.samples[-1]
        fixture.owners.samples = (last, replace(last, monotonic_ns=last.monotonic_ns + 7_200_000_000_000,
                                               wall_time_ns=utc_nanoseconds("2026-10-08T14:00:00Z")))
        fixture.service.revoke(fixture.grant_wire, fixture.owners.owner_context, "reason:owner-revoke")
        telemetry = StoreKey("projection", PROJECT, "telemetry:unrelated")
        fixture.put(telemetry, canonical_bytes({"observation": "unrelated history progress"}))
        keys += (telemetry,)
        before = fixture.cut(keys), fixture.budget()
        no_admission = AssertionError("historical query attempted positive authority or clock sampling")
        with patch.object(fixture.owners, "clock", side_effect=no_admission), \
                patch.object(fixture.owners, "require_prepared_basis", side_effect=no_admission), \
                patch.object(fixture.owners, "require_admission", side_effect=no_admission), \
                patch.object(fixture.owners, "require_revocation", side_effect=no_admission), \
                patch.object(fixture.store, "commit", side_effect=AssertionError("historical query wrote")):
            evidence = fixture.service.resolve_consumption_for_peer(consumed.record_wire, fixture.owners.worker_context)
            recovered = fixture.service.recover_permit(prepared.record_wire, fixture.owners.worker_context)
            internal = fixture.service.resolve_consumption(fixture.codec.decode(consumed.record_wire))
        self.assertEqual(evidence.consumed_permit_wire, consumed.record_wire)
        self.assertEqual(evidence.event_wire, consumed.event_wire)
        self.assertEqual(evidence.prior_position, consumed.prior_position)
        self.assertEqual(recovered.canonical_wire, consumed.record_wire)
        self.assertEqual(internal, evidence)
        self.assertEqual((fixture.cut(keys), fixture.budget()), before)

    def replace_intent_with_foreign_basis(self, fixture, permit_wire, variant):
        """Controlled canonical metadata mutation through the real fixture writer.

        This models inconsistent durable metadata, not a demonstrated ability to
        compromise a protected journal. The permit and logical subject stay exact.
        """
        intent = fixture.permit_keys(permit_wire)[2]
        value = strict_loads(fixture.cell(intent).value_wire)
        basis, grant_key, read_set = read_basis(value["basis_wire"].encode("utf8"), fixture.codec)
        proposal = fixture.codec.decode(basis["proposal_wire"].encode("utf8"))
        foreign = "project:foreign-fixture"
        if variant == "proposal":
            changed = proposal.as_dict()
            changed["scope_id"] = foreign
            changed["resources"] = [dict(resource, scope_id=foreign) for resource in changed["resources"]]
            proposal = fixture.codec.decode(canonical_bytes(changed))
            read_set = replace(read_set, scope_id=foreign)
        elif variant == "grant":
            grant_key = StoreKey("grant", foreign, grant_key.record_id)
        else:
            raise AssertionError("unknown foreign-basis fixture variant")
        wire = encode_basis(proposal, grant_key, read_set,
            principal_id=basis["principal_id"], actor_session=basis["actor_session"],
            adapter_commitment=basis["adapter_commitment"], registry_commitment=basis["registry_commitment"],
            owner_input_commitment=basis["owner_input_commitment"], candidate_commitment=basis["candidate_commitment"],
            task_revision=basis["task_revision"], review_refs=tuple(basis["review_refs"]),
            approval_evidence_ref=basis["approval_evidence_ref"])
        read_basis(wire, fixture.codec)  # Shape and embedded original commitment remain valid.
        value.update(basis_wire=wire.decode("utf8"), grant_key=grant_key.as_dict())
        fixture.put(intent, canonical_bytes(value))

    def test_consumed_query_rejects_canonical_foreign_proposal_or_grant_scope_without_writes(self):
        for variant in ("proposal", "grant"):
            fixture = self.fixture()
            prepared = fixture.prepare()
            consumed = fixture.service.consume(prepared.record_wire, fixture.owners.worker_context)
            keys = fixture.permit_keys(prepared.record_wire)
            self.replace_intent_with_foreign_basis(fixture, prepared.record_wire, variant)
            before = fixture.cut(keys), fixture.budget()
            with patch.object(fixture.store, "commit", side_effect=AssertionError("query wrote")):
                with self.assertRaises(ContractError) as caught:
                    fixture.service.resolve_consumption_for_peer(consumed.record_wire, fixture.owners.worker_context)
            self.assertEqual(caught.exception.code, "KERNEL_INTENT_BINDING_MISMATCH", variant)
            self.assertEqual((fixture.cut(keys), fixture.budget()), before, variant)

    def mutation_during_consumption_replay(self, kind):
        fixture = self.fixture()
        prepared = fixture.prepare()
        consumed = fixture.service.consume(prepared.record_wire, fixture.owners.worker_context)
        keys = fixture.permit_keys(prepared.record_wire)
        target = keys[0] if kind == "permit" else keys[2]
        original_cell = fixture.cell(target)
        original_wire = original_cell.value_wire
        original_replay = fixture.store.replay
        original_position, original_budget = fixture.store.store_position(), fixture.budget()
        reached, after_mutation = [], []

        def replay_then_mutate(*args, **kwargs):
            rows = original_replay(*args, **kwargs)
            if not reached:
                reached.append(True)
                changed = strict_loads(original_wire)
                if kind == "permit":
                    changed["nonce"] = "nonce:replay-change"
                else:
                    changed["state"] = "INTENT_COMMITTED"
                fixture.put(target, canonical_bytes(changed))
                if kind == "aba":
                    fixture.put(target, original_wire)
                after_mutation.append((fixture.cut(keys), fixture.budget()))
            return rows

        with patch.object(fixture.store, "replay", replay_then_mutate):
            with self.assertRaises(ContractError) as caught:
                fixture.service.resolve_consumption_for_peer(consumed.record_wire, fixture.owners.worker_context)
        self.assertEqual(caught.exception.code, "KERNEL_RECOVERY_STATE_CHANGED")
        self.assertEqual(reached, [True])
        self.assertEqual((fixture.cut(keys), fixture.budget()), after_mutation[0],
                         "query must not add writes beyond the deliberately injected writer commits")
        count = 2 if kind == "aba" else 1
        self.assertEqual(fixture.store.store_position().next_commit, original_position.next_commit + count)
        self.assertEqual(fixture.cell(target).generation, original_cell.generation + count)
        self.assertEqual(fixture.budget(), original_budget)
        if kind == "aba":
            self.assertEqual(fixture.cell(target).value_wire, original_wire)
            self.assertNotEqual(fixture.cell(target).revision, original_cell.revision)

    def test_public_query_denies_actual_permit_mutation_during_real_replay(self):
        self.mutation_during_consumption_replay("permit")

    def test_public_query_denies_actual_intent_mutation_during_real_replay(self):
        self.mutation_during_consumption_replay("intent")

    def test_public_query_denies_aba_intent_generation_change_during_real_replay(self):
        self.mutation_during_consumption_replay("aba")

    def test_public_query_final_authentication_denies_context_invalidated_during_replay(self):
        fixture = self.fixture()
        prepared = fixture.prepare()
        consumed = fixture.service.consume(prepared.record_wire, fixture.owners.worker_context)
        keys, context = fixture.permit_keys(prepared.record_wire), fixture.owners.worker_context
        before = fixture.cut(keys), fixture.budget()
        original_replay, reached = fixture.store.replay, []

        def replay_then_invalidate(*args, **kwargs):
            rows = original_replay(*args, **kwargs)
            if not reached:
                reached.append(True)
                fixture.owners.worker_context = object()
            return rows

        with patch.object(fixture.store, "replay", replay_then_invalidate), \
                patch.object(fixture.store, "commit", side_effect=AssertionError("query wrote")):
            with self.assertRaises(ContractError) as caught:
                fixture.service.resolve_consumption_for_peer(consumed.record_wire, context)
        self.assertEqual(caught.exception.code, "FIXTURE_AUTHENTICATION_DENIED")
        self.assertEqual(reached, [True])
        self.assertEqual((fixture.cut(keys), fixture.budget()), before)

    def test_final_postcommit_authentication_crossing_deadline_denies_and_retains_spent_state(self):
        fixture = self.fixture()
        prepared = fixture.prepare()
        keys, context = fixture.permit_keys(prepared.record_wire), fixture.owners.worker_context
        deadline = strict_loads(fixture.cell(keys[2]).value_wire)["deadline"]
        before = fixture.store.store_position()
        committed, post_authentications, crossed = [False], [], []
        original_authenticate = fixture.owners.authenticate

        def authenticate_then_cross_deadline(actual_context):
            peer = original_authenticate(actual_context)
            if committed[0]:
                post_authentications.append(True)
                if len(post_authentications) == 2:
                    previous = fixture.owners.samples[-1]
                    fixture.owners.samples = (previous, replace(previous,
                        monotonic_ns=deadline["expires_monotonic_ns"], wall_time_ns=deadline["expires_wall_ns"]))
                    crossed.append(True)
            return peer

        fixture.store.after_commit = lambda: committed.__setitem__(0, True)
        try:
            with patch.object(fixture.owners, "authenticate", authenticate_then_cross_deadline):
                with self.assertRaises(ContractError) as caught:
                    fixture.service.consume(prepared.record_wire, context)
                self.assertEqual(caught.exception.code, "DEADLINE_EXPIRED_OR_UNCERTAIN")
        finally:
            fixture.store.after_commit = None
        self.assertTrue(committed[0], "the counterexample must cross the durable boundary")
        self.assertEqual(crossed, [True], "the last authentication must return a valid peer at exact expiry")
        self.assertEqual(fixture.store.store_position().next_commit, before.next_commit + 1)
        self.assert_consumed_commit(fixture, prepared)
        retained = fixture.cut(keys), fixture.budget()
        fixture.reopen()
        self.assertEqual((fixture.cut(keys), fixture.budget()), retained)
        with self.assertRaises(ContractError) as duplicate:
            fixture.service.consume(prepared.record_wire, fixture.owners.worker_context)
        self.assertEqual(duplicate.exception.code, "KERNEL_PERMIT_NOT_PREPARED")
        self.assertEqual((fixture.cut(keys), fixture.budget()), retained)

    def test_prepared_recovery_rejects_canonical_foreign_proposal_or_grant_scope_without_writes(self):
        for variant in ("proposal", "grant"):
            fixture = self.fixture()
            prepared = fixture.prepare()
            keys = fixture.permit_keys(prepared.record_wire)
            self.replace_intent_with_foreign_basis(fixture, prepared.record_wire, variant)
            before = fixture.cut(keys), fixture.budget()
            with patch.object(fixture.store, "commit", side_effect=AssertionError("recovery query wrote")):
                with self.assertRaises(ContractError) as caught:
                    fixture.service.recover_permit(prepared.record_wire, fixture.owners.worker_context)
            self.assertEqual(caught.exception.code, "KERNEL_INTENT_BINDING_MISMATCH", variant)
            self.assertEqual((fixture.cut(keys), fixture.budget()), before, variant)


class NativeAuthorityResolutionTests(_ServiceTestCase):
    """Real owned IPC read authorization; no inherited test methods or admission."""

    def seeded_consumption(self):
        fixture = self.fixture()
        prepared = fixture.prepare()
        consumed = fixture.service.consume(prepared.record_wire, fixture.owners.worker_context)
        keys = fixture.permit_keys(prepared.record_wire)
        before = fixture.cut(keys), fixture.budget()
        return fixture, consumed, keys, before

    def test_actual_public_resolution_same_selected_subject_returns_exact_evidence_without_writes(self):
        fixture, consumed, keys, before = self.seeded_consumption()
        service = self.fixture_service(fixture)
        self.ready(service)
        _, response = self.call(service, consumed.record_wire, "kernel.resolve_consumption")
        self.assertEqual(response.kind, "EVIDENCE")
        self.assertEqual(response.record_wire, consumed.record_wire)
        self.assertEqual(response.event_wire, consumed.event_wire)
        self.assertEqual(response.prior_position, consumed.prior_position)
        self.assertEqual(service.snapshot()["authority"], "CLOSED")
        self.stop(service)
        self.reopen_unchanged(fixture, before, keys)

    def test_actual_public_resolution_wrong_selected_principal_denies_without_disclosure_or_writes(self):
        fixture, consumed, keys, before = self.seeded_consumption()
        service = self.fixture_service(fixture, principal="worker:another-selected-principal")
        self.ready(service)
        _, recovery = self.call(service, consumed.record_wire, "kernel.recover_permit")
        self.assertEqual(recovery.kind, "DENIED_RECONCILE")
        self.assertEqual(recovery.error_code, "KERNEL_PEER_BINDING_MISMATCH")
        _, response = self.call(service, consumed.record_wire, "kernel.resolve_consumption")
        self.assertEqual(response.kind, "DENIED_RECONCILE")
        self.assertEqual(response.error_code, "KERNEL_PEER_BINDING_MISMATCH")
        self.assertIsNone(response.record_wire)
        self.assertIsNone(response.event_wire)
        self.assertIsNone(response.prior_position)
        self.assertEqual(service.snapshot()["authority"], "CLOSED")
        self.stop(service)
        self.reopen_unchanged(fixture, before, keys)

    def test_actual_public_resolution_wrong_selected_session_denies_without_disclosure_or_writes(self):
        fixture, consumed, keys, before = self.seeded_consumption()
        service = self.fixture_service(fixture, session="session:another-selected-session")
        self.ready(service)
        _, recovery = self.call(service, consumed.record_wire, "kernel.recover_permit")
        self.assertEqual(recovery.kind, "DENIED_RECONCILE")
        self.assertEqual(recovery.error_code, "KERNEL_PEER_BINDING_MISMATCH")
        _, response = self.call(service, consumed.record_wire, "kernel.resolve_consumption")
        self.assertEqual(response.kind, "DENIED_RECONCILE")
        self.assertEqual(response.error_code, "KERNEL_PEER_BINDING_MISMATCH")
        self.assertIsNone(response.record_wire)
        self.assertIsNone(response.event_wire)
        self.assertIsNone(response.prior_position)
        self.assertEqual(service.snapshot()["authority"], "CLOSED")
        self.stop(service)
        self.reopen_unchanged(fixture, before, keys)


if __name__ == "__main__":
    unittest.main()
