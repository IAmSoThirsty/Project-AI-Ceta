"""Read-only lost-result recovery over real v2 SQLite with synthetic owners.

These are development regressions, IMPLEMENTED_NOT_QUALIFIED. KernelFixture
creates a fresh UUID directory and real journal; its opaque identities, clock
and owner allowlists are explicit fixtures, not OS authentication. Recovery
observes durable state, never retries admission, charges, refunds or executes
an effect. Original acceptance scenarios and installed qualification stay open.
"""
from dataclasses import replace
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ceta.composition.kernel_service import compose_kernel
from ceta.contracts.kernel_transactions import PeerIdentity
from ceta.contracts.wire import ContractError, ParsedRecord, canonical_bytes, strict_loads
from test_kernel_transactions import (CHANGED, COST, INSTALLATION, PROJECT,
                                      ZERO_BUDGET, KernelFixture)


class KernelRecoveryTests(unittest.TestCase):
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
            fixture.store.close()

    def observation(self, fixture, keys):
        # Includes global and both scope heads, complete replay, selected cells
        # and all seven budget dimensions. Equality alone grants no authority.
        return fixture.cut(keys), fixture.budget()

    def query_unchanged(self, fixture, wire, keys, *, service=None, context=None):
        before = self.observation(fixture, keys)
        service = fixture.service if service is None else service
        context = fixture.owners.worker_context if context is None else context
        with patch.object(fixture.store, "commit", side_effect=AssertionError(
                "recovery called the mutating store commit API")):
            result = service.recover_permit(wire, context)
        self.assertIs(type(result), ParsedRecord)
        self.assertEqual(self.observation(fixture, keys), before)
        return result

    def denied_unchanged(self, fixture, wire, keys, *, service=None, context=None, code=None):
        before = self.observation(fixture, keys)
        service = fixture.service if service is None else service
        context = fixture.owners.worker_context if context is None else context
        with patch.object(fixture.store, "commit", side_effect=AssertionError(
                "denied recovery called the mutating store commit API")):
            with self.assertRaises(ContractError) as caught:
                service.recover_permit(wire, context)
        if code is not None:
            self.assertEqual(caught.exception.code, code)
        self.assertEqual(self.observation(fixture, keys), before)

    def forbid_decision_callbacks(self, fixture):
        def unexpected(*args, **kwargs):
            raise AssertionError("read-only recovery requested clock or positive owner decision")
        for name in ("clock", "require_prepared_basis", "require_admission", "require_revocation"):
            setattr(fixture.owners, name, unexpected)
        fixture.owners.prepared.clear()
        fixture.owners.admission_available = False

    def test_prepared_recovery_returns_exact_stored_record_without_clock_or_decision(self):
        f = self.fixture()
        prepared = f.prepare()
        keys = f.permit_keys(prepared.record_wire)
        self.forbid_decision_callbacks(f)
        recovered = self.query_unchanged(f, prepared.record_wire, keys)
        self.assertEqual(recovered, f.codec.decode(prepared.record_wire))
        self.assertEqual(recovered.original_wire, f.cell(keys[0]).value_wire)
        self.assertEqual(recovered.as_dict()["status"], "PREPARED")
        self.assertIsNone(recovered.as_dict()["consume_event_ref"])
        self.assertEqual(f.budget()[2:], (COST, ZERO_BUDGET))

    def test_fresh_composition_recovers_with_same_selected_logical_session(self):
        f = self.fixture()
        prepared = f.prepare()
        keys = f.permit_keys(prepared.record_wire)
        old_context = f.owners.worker_context
        f.reopen()
        # This is a new synthetic opaque context, not an OS process-lifetime
        # claim. The fixture owner retains its originally selected identity.
        f.owners.worker_context = object()
        self.forbid_decision_callbacks(f)
        self.assertEqual(self.query_unchanged(f, prepared.record_wire, keys).canonical_wire,
                         prepared.record_wire)
        self.denied_unchanged(f, prepared.record_wire, keys, context=old_context,
                              code="FIXTURE_AUTHENTICATION_DENIED")

    def test_original_prepared_recovers_exact_consumed_record_and_actual_evidence(self):
        f = self.fixture()
        prepared = f.prepare()
        consumed = f.service.consume(prepared.record_wire, f.owners.worker_context)
        keys = f.permit_keys(prepared.record_wire)
        f.reopen()
        self.forbid_decision_callbacks(f)
        recovered = self.query_unchanged(f, prepared.record_wire, keys)
        self.assertEqual(recovered, f.codec.decode(consumed.record_wire))
        self.assertEqual(recovered.as_dict()["consume_event_ref"],
                         strict_loads(consumed.event_wire)["record_id"])
        before = self.observation(f, keys)
        evidence = f.service.resolve_consumption(recovered)
        self.assertEqual((evidence.consumed_permit_wire, evidence.event_wire, evidence.prior_position),
                         (consumed.record_wire, consumed.event_wire, consumed.prior_position))
        self.assertEqual(self.observation(f, keys), before)
        self.assertEqual(f.budget()[2:], (ZERO_BUDGET, COST))

    def test_current_consumed_input_recovers_without_reconsumption_or_refund(self):
        f = self.fixture()
        prepared = f.prepare()
        consumed = f.service.consume(prepared.record_wire, f.owners.worker_context)
        keys = f.permit_keys(prepared.record_wire)
        self.forbid_decision_callbacks(f)
        self.assertEqual(self.query_unchanged(f, consumed.record_wire, keys).canonical_wire,
                         consumed.record_wire)
        before = self.observation(f, keys)
        for wire in (prepared.record_wire, consumed.record_wire):
            with self.assertRaises(ContractError) as caught:
                f.service.consume(wire, f.owners.worker_context)
            self.assertEqual(caught.exception.code, "KERNEL_PERMIT_NOT_PREPARED")
        self.assertEqual(self.observation(f, keys), before)
        with self.assertRaises(ContractError) as caught:
            f.service.require_runtime_admission()
        self.assertEqual(caught.exception.code, "RUNTIME_AUTHORITY_OWNERS_UNAVAILABLE")

    def test_postcommit_expired_return_recovers_durable_spent_and_charged_state(self):
        f = self.fixture()
        prepared = f.prepare()
        keys = f.permit_keys(prepared.record_wire)
        deadline = strict_loads(f.cell(keys[2]).value_wire)["deadline"]
        point = f.store.store_position()

        def expire_after_real_commit():
            sample = f.owners.samples[1]
            later = replace(sample, monotonic_ns=deadline["expires_monotonic_ns"],
                            wall_time_ns=deadline["expires_wall_ns"])
            f.owners.samples = (sample, later)

        f.store.after_commit = expire_after_real_commit
        try:
            with self.assertRaises(ContractError) as caught:
                f.service.consume(prepared.record_wire, f.owners.worker_context)
            self.assertEqual(caught.exception.code, "DEADLINE_EXPIRED_OR_UNCERTAIN")
        finally:
            f.store.after_commit = None
        self.assertEqual(f.store.store_position().next_commit, point.next_commit + 1)
        stored = f.codec.decode(f.cell(keys[0]).value_wire)
        self.assertEqual(stored.as_dict()["status"], "CONSUMED")
        self.assertEqual(strict_loads(f.cell(keys[1]).value_wire)["state"], "CHARGED")
        self.assertEqual(f.budget()[2:], (ZERO_BUDGET, COST))
        f.reopen()
        self.forbid_decision_callbacks(f)
        self.assertEqual(self.query_unchanged(f, prepared.record_wire, keys), stored)
        self.assertEqual(f.service.resolve_consumption(stored).consumed_permit_wire,
                         stored.canonical_wire)
        before = self.observation(f, keys)
        with self.assertRaises(ContractError) as caught:
            f.service.consume(prepared.record_wire, f.owners.worker_context)
        self.assertEqual(caught.exception.code, "KERNEL_PERMIT_NOT_PREPARED")
        self.assertEqual(self.observation(f, keys), before)

    def test_revoked_grant_recovery_is_observation_and_never_fresh_admission(self):
        f = self.fixture()
        prepared = f.prepare()
        keys = f.permit_keys(prepared.record_wire)
        f.service.revoke(f.grant_wire, f.owners.owner_context, "reason:owner-revoke")
        self.forbid_decision_callbacks(f)
        self.assertEqual(self.query_unchanged(f, prepared.record_wire, keys).as_dict()["status"],
                         "PREPARED")
        before = self.observation(f, keys)
        with self.assertRaises(ContractError):
            f.service.consume(prepared.record_wire, f.owners.worker_context)
        self.assertEqual(self.observation(f, keys), before)
        self.assertEqual(f.budget()[2:], (COST, ZERO_BUDGET))

    def test_missing_owners_and_forged_context_do_not_fall_back_to_caller_identity(self):
        f = self.fixture()
        prepared = f.prepare()
        keys = f.permit_keys(prepared.record_wire)
        closed = compose_kernel(f.store, f.codec, INSTALLATION)
        self.denied_unchanged(f, prepared.record_wire, keys, service=closed,
                              code="KERNEL_OWNERS_UNAVAILABLE")
        for context in (object(), {"authenticated": True,
                                   "principal_id": f.owners.worker.principal_id,
                                   "session_id": f.owners.worker.session_id}):
            with self.subTest(context_type=type(context).__name__):
                self.denied_unchanged(f, prepared.record_wire, keys, context=context,
                                      code="FIXTURE_AUTHENTICATION_DENIED")

    def test_other_authenticated_principal_or_session_cannot_recover_original_permit(self):
        for consumed in (False, True):
            for changed in ("principal", "session"):
                with self.subTest(consumed=consumed, changed=changed):
                    f = self.fixture()
                    prepared = f.prepare()
                    if consumed:
                        f.service.consume(prepared.record_wire, f.owners.worker_context)
                    keys = f.permit_keys(prepared.record_wire)
                    peer = f.owners.worker
                    f.owners.worker = PeerIdentity(
                        "worker:other" if changed == "principal" else peer.principal_id,
                        "session:other" if changed == "session" else peer.session_id)
                    self.denied_unchanged(f, prepared.record_wire, keys,
                                          code="KERNEL_PEER_BINDING_MISMATCH")

    def test_owner_context_does_not_select_a_different_principals_permit(self):
        f = self.fixture()
        prepared = f.prepare()
        self.denied_unchanged(f, prepared.record_wire, f.permit_keys(prepared.record_wire),
                              context=f.owners.owner_context, code="KERNEL_PEER_BINDING_MISMATCH")

    def test_nonpermit_record_and_schema_valid_immutable_substitutions_are_denied(self):
        mutations = {
            "record_id": "permit:other", "scope_id": "project:other",
            "grant_ref": "grant:other", "task_id": "task:other",
            "proposal_ref": "proposal:other", "adapter_id": "adapter:other",
            "adapter_commitment": CHANGED, "operation": "file.write",
            "arguments_commitment": CHANGED, "input_commitment": CHANGED,
            "candidate_commitment": CHANGED, "policy_commitment": CHANGED,
            "review_refs": ["review:other"], "approval_evidence_ref": "evidence:other",
            "environment_commitment": CHANGED, "authority_generation": 2,
            "fence_generation": 2, "nonce": "nonce:other",
            "expires_at": "2026-10-08T12:00:02Z", "reservation_ref": "reservation:other",
            "issuance_evidence_ref": "event:other",
            "resources": [{"resource_id": "resource:other", "revision": CHANGED,
                           "access": "READ", "scope_id": PROJECT}],
        }
        for consumed in (False, True):
            f = self.fixture()
            prepared = f.prepare()
            if consumed:
                f.service.consume(prepared.record_wire, f.owners.worker_context)
            keys = f.permit_keys(prepared.record_wire)
            self.denied_unchanged(f, f.proposal_wire, keys, code="KERNEL_OPERATIONPERMIT_REQUIRED")
            for field, value in mutations.items():
                with self.subTest(consumed=consumed, field=field):
                    changed = strict_loads(prepared.record_wire)
                    changed[field] = value
                    wire = canonical_bytes(changed)
                    # Prove this reaches semantic recovery; schema rejection
                    # would not substantiate immutable binding enforcement.
                    self.assertEqual(f.codec.decode(wire).record_type, "OperationPermit")
                    self.denied_unchanged(f, wire, keys)

    def test_prepared_causal_or_fake_lifecycle_substitutions_cannot_hide_consumption(self):
        f = self.fixture()
        prepared = f.prepare()
        f.service.consume(prepared.record_wire, f.owners.worker_context)
        keys = f.permit_keys(prepared.record_wire)
        original = strict_loads(prepared.record_wire)
        self.assertEqual(original["causation_ref"], original["proposal_ref"])
        for edits in ({"causation_ref": original["issuance_evidence_ref"]},
                      {"consume_event_ref": "event:invented"},
                      {"status": "CONSUMED", "consume_event_ref": "event:invented",
                       "causation_ref": "event:invented"}, {"status": "SETTLED"}):
            with self.subTest(edits=edits):
                wire = canonical_bytes(dict(original, **edits))
                self.assertEqual(f.codec.decode(wire).record_type, "OperationPermit")
                self.denied_unchanged(f, wire, keys)

    def test_consumed_input_requires_actual_consume_reference_and_causal_binding(self):
        f = self.fixture()
        prepared = f.prepare()
        consumed = f.service.consume(prepared.record_wire, f.owners.worker_context)
        keys = f.permit_keys(prepared.record_wire)
        for edits in ({"consume_event_ref": "event:other", "causation_ref": "event:other"},
                      {"consume_event_ref": None}, {"causation_ref": "event:other"}):
            with self.subTest(edits=edits):
                wire = canonical_bytes(dict(strict_loads(consumed.record_wire), **edits))
                self.assertEqual(f.codec.decode(wire).record_type, "OperationPermit")
                self.denied_unchanged(f, wire, keys)

    def test_stored_consumed_label_without_committed_consumption_is_not_recovered(self):
        f = self.fixture()
        prepared = f.prepare()
        keys = f.permit_keys(prepared.record_wire)
        forged = dict(strict_loads(prepared.record_wire), status="CONSUMED",
                      consume_event_ref="event:fiction", causation_ref="event:fiction")
        # A real fixture writer stores a structurally admitted permit payload.
        # Its fixture seed event is not consumption evidence or an exploit claim.
        f.put(keys[0], canonical_bytes(forged))
        self.denied_unchanged(f, prepared.record_wire, keys)
        self.assertEqual(f.budget()[2:], (COST, ZERO_BUDGET))

    def test_current_consumption_index_substitutions_are_denied_without_state_changes(self):
        for field, value in (("event_id", "event:other"), ("sequence", 0),
                             ("previous_head", None)):
            with self.subTest(field=field):
                f = self.fixture()
                prepared = f.prepare()
                f.service.consume(prepared.record_wire, f.owners.worker_context)
                keys = f.permit_keys(prepared.record_wire)
                intention = strict_loads(f.cell(keys[2]).value_wire)
                self.assertNotEqual(intention["consumption"][field], value)
                intention["consumption"][field] = value
                f.put(keys[2], canonical_bytes(intention))
                self.denied_unchanged(f, prepared.record_wire, keys)
                self.assertEqual(f.budget()[2:], (ZERO_BUDGET, COST))

    def test_stored_intent_scope_permit_and_basis_substitutions_do_not_select_foreign_state(self):
        for field, value in (("scope_id", "project:other"), ("permit_id", "permit:other"),
                             ("basis_wire", "{}")):
            with self.subTest(field=field):
                f = self.fixture()
                prepared = f.prepare()
                keys = f.permit_keys(prepared.record_wire)
                intention = strict_loads(f.cell(keys[2]).value_wire)
                intention[field] = value
                f.put(keys[2], canonical_bytes(intention))
                self.denied_unchanged(f, prepared.record_wire, keys)

    def test_stored_unsupported_lifecycle_status_never_becomes_recovery_authority(self):
        for status in ("ADMITTED", "REVOKED", "EXPIRED", "INDETERMINATE", "SETTLED"):
            with self.subTest(status=status):
                f = self.fixture()
                prepared = f.prepare()
                keys = f.permit_keys(prepared.record_wire)
                value = dict(strict_loads(prepared.record_wire), status=status)
                f.put(keys[0], canonical_bytes(value))
                self.denied_unchanged(f, prepared.record_wire, keys,
                                      code="KERNEL_RECOVERY_STATE_UNAVAILABLE")

    def test_actual_owned_history_payload_corruption_denies_and_preserves_raw_rows(self):
        f = self.fixture()
        prepared = f.prepare()
        consumed = f.service.consume(prepared.record_wire, f.owners.worker_context)
        altered = dict(strict_loads(consumed.record_wire), nonce="nonce:corrupted-history")
        # Explicit fault injection only into this freshly owned fixture DB. This
        # private connection is not an application SQL or authorization API.
        f.store._connection.execute(
            "UPDATE history_events SET payload_wire=? WHERE scope_id=? AND sequence=?",
            (canonical_bytes(altered), PROJECT, consumed.prior_position.next_sequence))
        tables = ("history_meta", "history_scopes", "history_events",
                  "store_commits", "store_changes", "store_cells")

        def raw_rows():
            return tuple((name, tuple(sorted(f.store._connection.execute(
                'SELECT * FROM "' + name + '"').fetchall(), key=repr))) for name in tables)

        before = raw_rows()
        with patch.object(f.store, "commit", side_effect=AssertionError("corrupt history query wrote")):
            with self.assertRaises(ContractError):
                f.service.recover_permit(prepared.record_wire, f.owners.worker_context)
        self.assertFalse(f.store._connection.in_transaction)
        self.assertEqual(raw_rows(), before)

    def test_authentication_change_at_final_read_denies_without_mutating_store(self):
        f = self.fixture()
        prepared = f.prepare()
        keys = f.permit_keys(prepared.record_wire)
        original = f.owners.authenticate
        calls = []

        def changed_peer(context):
            peer = original(context)
            calls.append(peer)
            return peer if len(calls) == 1 else PeerIdentity(peer.principal_id, "session:changed")

        with patch.object(f.owners, "authenticate", side_effect=changed_peer):
            self.denied_unchanged(f, prepared.record_wire, keys,
                                  code="KERNEL_PEER_BINDING_MISMATCH")
        self.assertEqual(len(calls), 2)
