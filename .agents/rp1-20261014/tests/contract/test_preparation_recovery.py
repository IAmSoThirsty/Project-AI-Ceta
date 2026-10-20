"""Unknown-selector preparation recovery, with explicit development limits.

Kernel cases use KernelFixture's real v2 SQLite journal, synthetic opaque peers,
positive owner allowlists and clock. Controlled replay/race faults affect only
fresh UUID fixtures, not a normal profile. They are not proof of journal
compromise or OS authentication. The IPC routing test uses a message-bound
identity fixture. Native cases start the real owned Windows service/client and
pipe, seeded by synthetic parent owners before its writer closes. Unchanged
child identity owners retain closed positive authority. No model, effect,
installed operation, independent acceptance or product qualification is claimed.

Candidate uses the Increment 26 input cut observed 2026-10-08T20:33:16.8979092Z.
Expected API: recover_preparation(original_proposal_wire, original_context).
Unknown-selector recovery requires versioned issuance input evidence; legacy
v1 intent stays supported by existing permit/consumption APIs.
"""
from dataclasses import replace
import json
from pathlib import Path
from fixture_paths import native_fixture_path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ceta.application.ipc_service import KernelIngress
from ceta.application.use_cases import KernelUseCases
from ceta.composition.kernel_service import compose_kernel
from ceta.contracts.history import JournalEntry
from ceta.contracts.kernel_transactions import (PeerIdentity, ZERO_BUDGET,
                                               basis_key, read_basis)
from ceta.contracts.local_ipc import decode_message, encode_message
from ceta.contracts.local_results import decode_response, encode_response
from ceta.contracts.store_transactions import StoreKey
from ceta.contracts.wire import ContractError, ParsedRecord, canonical_bytes, strict_loads
from test_kernel_transactions import CHANGED, COST, INSTALLATION, PROJECT, KernelFixture
from test_owned_service import _ServiceTestCase

ROUTE = "kernel.recover_preparation"
LEGACY_INTENT_PROFILE = "ceta-kernel-transactions-v1"
INPUT_INTENT_PROFILE = "ceta-kernel-intent-v2"


class PreparationRecoveryTests(unittest.TestCase):
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

    def observation(self, fixture, keys=()):
        # Scope/global heads, complete replay, selected cells and seven budget
        # dimensions are compared. Equality is not an authority decision.
        return fixture.cut(keys), fixture.budget()

    def known_issuance(self, fixture):
        # Only the test observer learns this selector to assert the outcome.
        # The recovery caller supplies just the original proposal bytes.
        index = strict_loads(fixture.cell(fixture.issuance_key()).value_wire)
        permit = fixture.codec.decode(fixture.cell(
            StoreKey("permit", PROJECT, index["permit_id"])).value_wire)
        return permit, fixture.permit_keys(permit.original_wire)

    def forbid_decision_callbacks(self, fixture):
        def unexpected(*args, **kwargs):
            raise AssertionError("read-only recovery invoked clock or positive authority")
        for name in ("clock", "require_prepared_basis", "require_admission", "require_revocation"):
            setattr(fixture.owners, name, unexpected)
        fixture.owners.prepared.clear()
        fixture.owners.admission_available = False

    def query_unchanged(self, fixture, wire, keys=(), *, service=None, context=None):
        before = self.observation(fixture, keys)
        service = fixture.service if service is None else service
        context = fixture.owners.worker_context if context is None else context
        with patch.object(fixture.store, "commit", side_effect=AssertionError("recovery wrote")):
            result = service.recover_preparation(wire, context)
        self.assertIs(type(result), ParsedRecord)
        self.assertEqual(self.observation(fixture, keys), before)
        return result

    def denied_unchanged(self, fixture, wire, keys=(), *, service=None, context=None, code=None):
        before = self.observation(fixture, keys)
        service = fixture.service if service is None else service
        context = fixture.owners.worker_context if context is None else context
        with patch.object(fixture.store, "commit", side_effect=AssertionError("denied recovery wrote")):
            with self.assertRaises(ContractError) as caught:
                service.recover_preparation(wire, context)
        if code is not None:
            self.assertEqual(caught.exception.code, code)
        self.assertEqual(self.observation(fixture, keys), before)

    def message(self, fixture, wire, operation=ROUTE):
        return decode_message(encode_message(wire, fixture.codec,
            message_id="message:preparation-recovery", sender_session=fixture.owners.worker.session_id,
            receiver_generation="service:preparation-recovery", operation=operation,
            issued_at_ms=1000, expires_at_ms=2000, correlation_ref="attempt:preparation-recovery"),
            fixture.codec)

    def test_postcommit_denial_recovers_preparation_when_generated_selector_was_not_returned(self):
        f = self.fixture()
        before = f.store.store_position()
        committed = []

        def expire_after_commit():
            permit, keys = self.known_issuance(f)
            deadline = strict_loads(f.cell(keys[2]).value_wire)["deadline"]
            sample = f.owners.samples[-1]
            f.owners.samples = (sample, replace(sample,
                monotonic_ns=deadline["expires_monotonic_ns"],
                wall_time_ns=deadline["expires_wall_ns"]))
            committed.append(permit)

        f.store.after_commit = expire_after_commit
        try:
            # No prepare result/permit selector reaches this caller.
            with self.assertRaises(ContractError) as caught:
                f.service.prepare(f.proposal_wire, f.owners.worker_context)
            self.assertEqual(caught.exception.code, "DEADLINE_EXPIRED_OR_UNCERTAIN")
        finally:
            f.store.after_commit = None
        self.assertEqual(len(committed), 1)
        self.assertEqual(f.store.store_position().next_commit, before.next_commit + 1)
        stored, keys = self.known_issuance(f)
        self.assertEqual(stored, committed[0])
        self.assertEqual(stored.as_dict()["status"], "PREPARED")
        self.assertEqual(strict_loads(f.cell(keys[1]).value_wire)["state"], "HELD")
        self.assertEqual(f.budget()[2:], (COST, ZERO_BUDGET))
        f.reopen()
        self.forbid_decision_callbacks(f)
        recovered = self.query_unchanged(f, f.proposal_wire, keys)
        self.assertEqual(recovered, stored)
        self.assertEqual(recovered.original_wire, f.cell(keys[0]).value_wire)

    def test_exact_noncanonical_proposal_bytes_survive_and_canonical_substitution_is_denied(self):
        f = self.fixture()
        original = json.dumps(f.proposal, ensure_ascii=False, indent=2).encode("utf8") + b"\n"
        self.assertNotEqual(original, f.proposal_wire)
        self.assertEqual(f.codec.decode(original).commitment, f.codec.decode(f.proposal_wire).commitment)
        f.proposal_wire = original
        f.basis = f.make_basis(original)
        f.allow(original, f.basis)
        f.put(basis_key(PROJECT, f.proposal["record_id"]), f.basis)
        prepared = f.prepare()
        keys = f.permit_keys(prepared.record_wire)
        self.forbid_decision_callbacks(f)
        self.assertEqual(self.query_unchanged(f, original, keys).original_wire, prepared.record_wire)
        self.denied_unchanged(f, canonical_bytes(f.proposal), keys)

    def test_consumed_recovery_after_restart_returns_actual_spent_record_and_evidence(self):
        f = self.fixture()
        prepared = f.prepare()
        consumed = f.service.consume(prepared.record_wire, f.owners.worker_context)
        keys = f.permit_keys(prepared.record_wire)
        retained = self.observation(f, keys)
        f.reopen()
        self.assertEqual(self.observation(f, keys), retained)
        self.forbid_decision_callbacks(f)
        recovered = self.query_unchanged(f, f.proposal_wire, keys)
        self.assertEqual(recovered.original_wire, consumed.record_wire)
        self.assertEqual(recovered.as_dict()["consume_event_ref"],
                         strict_loads(consumed.event_wire)["record_id"])
        before = self.observation(f, keys)
        with patch.object(f.store, "commit", side_effect=AssertionError("existing read route wrote")):
            old = f.service.recover_permit(prepared.record_wire, f.owners.worker_context)
            evidence = f.service.resolve_consumption_for_peer(
                consumed.record_wire, f.owners.worker_context)
        self.assertEqual(old, recovered)
        self.assertEqual((evidence.consumed_permit_wire, evidence.event_wire, evidence.prior_position),
                         (consumed.record_wire, consumed.event_wire, consumed.prior_position))
        self.assertEqual(self.observation(f, keys), before)
        self.assertEqual(f.budget()[2:], (ZERO_BUDGET, COST))

    def test_revoked_and_expired_historical_preparation_lookup_never_renews_authority(self):
        f = self.fixture()
        prepared = f.prepare()
        keys = f.permit_keys(prepared.record_wire)
        f.service.revoke(f.grant_wire, f.owners.owner_context, "reason:owner-revoke")
        sample = f.owners.samples[-1]
        f.owners.samples = (sample, replace(sample,
            wall_time_ns=sample.wall_time_ns + 3_600_000_000_000,
            monotonic_ns=sample.monotonic_ns + 3_600_000_000_000))
        self.forbid_decision_callbacks(f)
        self.assertEqual(self.query_unchanged(f, f.proposal_wire, keys).original_wire,
                         prepared.record_wire)
        before = self.observation(f, keys)
        with self.assertRaises(ContractError):
            f.service.consume(prepared.record_wire, f.owners.worker_context)
        self.assertEqual(self.observation(f, keys), before)
        self.assertEqual(f.budget()[2:], (COST, ZERO_BUDGET))
        with self.assertRaises(ContractError) as caught:
            f.service.require_runtime_admission()
        self.assertEqual(caught.exception.code, "RUNTIME_AUTHORITY_OWNERS_UNAVAILABLE")

    def test_missing_issuance_denies_without_preparing_or_calling_owner_decisions(self):
        f = self.fixture()
        self.assertIsNone(f.cell(f.issuance_key()).value_wire)
        self.forbid_decision_callbacks(f)
        self.denied_unchanged(f, f.proposal_wire)
        self.assertIsNone(f.cell(f.issuance_key()).value_wire)
        self.assertEqual(f.budget()[2:], (ZERO_BUDGET, ZERO_BUDGET))

    def test_missing_owners_and_forged_context_do_not_fall_back_to_request_subject(self):
        f = self.fixture()
        prepared = f.prepare()
        keys = f.permit_keys(prepared.record_wire)
        closed = compose_kernel(f.store, f.codec, INSTALLATION)
        self.denied_unchanged(f, f.proposal_wire, keys, service=closed,
                              code="KERNEL_OWNERS_UNAVAILABLE")
        for context in (object(), {"authenticated": True,
                                   "principal_id": f.owners.worker.principal_id,
                                   "session_id": f.owners.worker.session_id}):
            with self.subTest(context_type=type(context).__name__):
                self.denied_unchanged(f, f.proposal_wire, keys, context=context,
                                      code="FIXTURE_AUTHENTICATION_DENIED")

    def test_other_authenticated_principal_session_or_owner_cannot_select_preparation(self):
        for consumed in (False, True):
            for variant in ("principal", "session", "owner"):
                with self.subTest(consumed=consumed, variant=variant):
                    f = self.fixture()
                    prepared = f.prepare()
                    if consumed:
                        f.service.consume(prepared.record_wire, f.owners.worker_context)
                    keys = f.permit_keys(prepared.record_wire)
                    peer = f.owners.worker
                    if variant == "principal":
                        f.owners.worker = PeerIdentity("worker:foreign", peer.session_id)
                    elif variant == "session":
                        f.owners.worker = PeerIdentity(peer.principal_id, "session:foreign")
                    context = f.owners.owner_context if variant == "owner" else f.owners.worker_context
                    self.denied_unchanged(f, f.proposal_wire, keys, context=context,
                                          code="KERNEL_PEER_BINDING_MISMATCH")

    def test_schema_valid_proposal_field_substitutions_are_denied(self):
        f = self.fixture()
        prepared = f.prepare()
        keys = f.permit_keys(prepared.record_wire)
        changes = (
            {"record_id": "proposal:missing"}, {"scope_id": "project:foreign"},
            {"task_id": "task:foreign"}, {"adapter_id": "adapter:foreign"},
            {"adapter_version": "2.0.0"}, {"operation": "file.write"},
            {"arguments_commitment": CHANGED}, {"causation_ref": "cause:foreign"},
            {"requires_human_approval": False}, {"status": "VALIDATED"},
            {"budget": dict(f.proposal["budget"], max_input_tokens=11)},
            {"dependencies": ["dependency:foreign"]},
            {"resources": [dict(f.proposal["resources"][0], resource_id="resource:foreign")]})
        self.forbid_decision_callbacks(f)
        self.denied_unchanged(f, prepared.record_wire, keys)
        for change in changes:
            with self.subTest(change=change):
                wire = canonical_bytes(dict(f.proposal, **change))
                self.assertEqual(f.codec.decode(wire).record_type, "ActionProposal")
                self.denied_unchanged(f, wire, keys)

    def test_issuance_index_scope_selector_event_and_predecessor_substitutions_are_denied(self):
        for field, value in (("scope_id", "project:foreign"), ("proposal_id", "proposal:foreign"),
                             ("permit_id", "permit:missing"), ("issuance_event_ref", "event:foreign"),
                             ("sequence", 0), ("previous_head", None)):
            with self.subTest(field=field):
                f = self.fixture()
                prepared = f.prepare()
                keys = f.permit_keys(prepared.record_wire)
                index = strict_loads(f.cell(f.issuance_key()).value_wire)
                self.assertNotEqual(index[field], value)
                index[field] = value
                f.put(f.issuance_key(), canonical_bytes(index))
                self.forbid_decision_callbacks(f)
                self.denied_unchanged(f, f.proposal_wire, keys)

    def test_issuance_alias_to_other_real_same_scope_permit_cannot_cross_proposals(self):
        f = self.fixture()
        prepared = f.prepare()
        other_wire = f.add_proposal("proposal:other-fixture")
        other = f.service.prepare(other_wire, f.owners.worker_context)
        other_key = f.issuance_key("proposal:other-fixture")
        index = strict_loads(f.cell(f.issuance_key()).value_wire)
        other_index = strict_loads(f.cell(other_key).value_wire)
        for name in ("permit_id", "issuance_event_ref", "sequence", "previous_head"):
            index[name] = other_index[name]
        f.put(f.issuance_key(), canonical_bytes(index))
        keys = f.permit_keys(prepared.record_wire) + f.permit_keys(other.record_wire) + (other_key,)
        self.forbid_decision_callbacks(f)
        self.denied_unchanged(f, f.proposal_wire, keys)
        self.assertEqual(self.query_unchanged(f, other_wire, keys).original_wire, other.record_wire)
        self.assertEqual(f.budget()[2:], (COST.add(COST), ZERO_BUDGET))

    def test_consistent_intent_basis_rewrite_of_omitted_proposal_field_fails_issuance_input_binding(self):
        f = self.fixture()
        prepared = f.prepare()
        keys = f.permit_keys(prepared.record_wire)
        changed = dict(f.proposal, adapter_version="2.0.0")
        changed_wire = canonical_bytes(changed)
        intention = strict_loads(f.cell(keys[2]).value_wire)
        basis = strict_loads(intention["basis_wire"].encode("utf8"))
        basis.update(proposal_wire=changed_wire.decode("utf8"),
                     proposal_commitment=f.codec.decode(changed_wire).commitment)
        basis_wire = canonical_bytes(basis)
        read_basis(basis_wire, f.codec)
        intention["basis_wire"] = basis_wire.decode("utf8")
        f.put(keys[2], canonical_bytes(intention))
        direct = strict_loads(prepared.record_wire)
        for name in ("task_id", "adapter_id", "operation", "arguments_commitment", "resources"):
            self.assertEqual(direct[name], changed[name])
        self.assertNotIn("adapter_version", direct)
        self.forbid_decision_callbacks(f)
        self.denied_unchanged(f, changed_wire, keys, code="KERNEL_INPUT_BINDING_MISMATCH")

    def test_legacy_v1_consumption_and_peer_evidence_remain_exact_without_migration(self):
        f = self.fixture()
        prepared = f.prepare()
        keys = f.permit_keys(prepared.record_wire)
        intention = strict_loads(f.cell(keys[2]).value_wire)
        self.assertEqual(intention["profile"], INPUT_INTENT_PROFILE)
        self.assertIn("grant_commitment", intention)
        intention.pop("grant_commitment")
        intention["profile"] = LEGACY_INTENT_PROFILE
        f.put(keys[2], canonical_bytes(intention))
        before = self.observation(f, keys)
        with patch.object(f.store, "commit", side_effect=AssertionError("legacy observation wrote")):
            recovered = f.service.recover_permit(prepared.record_wire, f.owners.worker_context)
        self.assertEqual(recovered.original_wire, prepared.record_wire)
        self.assertEqual(self.observation(f, keys), before)
        self.denied_unchanged(f, f.proposal_wire, keys,
                              code="KERNEL_RECOVERY_INPUT_EVIDENCE_UNAVAILABLE")
        # A real legacy-compatible consumption transaction, not a read fixture.
        consumed = f.service.consume(prepared.record_wire, f.owners.worker_context)
        stored_intent = strict_loads(f.cell(keys[2]).value_wire)
        self.assertEqual(stored_intent["profile"], LEGACY_INTENT_PROFILE)
        self.assertNotIn("grant_commitment", stored_intent)
        self.assertEqual(stored_intent["state"], "ADMISSION_REDEEMED")
        self.forbid_decision_callbacks(f)
        before = self.observation(f, keys)
        with patch.object(f.store, "commit", side_effect=AssertionError("legacy resolution wrote")):
            recovered = f.service.recover_permit(prepared.record_wire, f.owners.worker_context)
            evidence = f.service.resolve_consumption_for_peer(
                consumed.record_wire, f.owners.worker_context)
        self.assertEqual(recovered.original_wire, consumed.record_wire)
        self.assertEqual((evidence.consumed_permit_wire, evidence.event_wire, evidence.prior_position),
                         (consumed.record_wire, consumed.event_wire, consumed.prior_position))
        self.assertEqual(self.observation(f, keys), before)
        self.denied_unchanged(f, f.proposal_wire, keys,
                              code="KERNEL_RECOVERY_INPUT_EVIDENCE_UNAVAILABLE")
        self.assertEqual(f.budget()[2:], (ZERO_BUDGET, COST))

    def test_intent_scope_basis_subject_input_and_mixed_profile_shape_substitutions_are_denied(self):
        variants = ("scope", "permit", "basis", "principal", "session", "grant_scope",
                    "grant_commitment", "v2_missing_field", "v1_extra_field", "unknown_profile")
        for variant in variants:
            with self.subTest(variant=variant):
                f = self.fixture()
                prepared = f.prepare()
                keys = f.permit_keys(prepared.record_wire)
                intention = strict_loads(f.cell(keys[2]).value_wire)
                if variant == "scope":
                    intention["scope_id"] = "project:foreign"
                elif variant == "permit":
                    intention["permit_id"] = "permit:foreign"
                elif variant == "basis":
                    intention["basis_wire"] = "{}"
                elif variant in {"principal", "session", "grant_scope"}:
                    basis = strict_loads(intention["basis_wire"].encode("utf8"))
                    if variant == "principal":
                        basis["principal_id"] = "worker:foreign"
                    elif variant == "session":
                        basis["actor_session"] = "session:foreign"
                    else:
                        basis["grant_key"]["scope_id"] = "project:foreign"
                        intention["grant_key"] = basis["grant_key"]
                    basis_wire = canonical_bytes(basis)
                    read_basis(basis_wire, f.codec)
                    intention["basis_wire"] = basis_wire.decode("utf8")
                elif variant == "grant_commitment":
                    intention["grant_commitment"] = CHANGED
                elif variant == "v2_missing_field":
                    self.assertEqual(intention["profile"], INPUT_INTENT_PROFILE)
                    intention.pop("grant_commitment")
                elif variant == "v1_extra_field":
                    self.assertIn("grant_commitment", intention)
                    intention["profile"] = LEGACY_INTENT_PROFILE
                else:
                    intention["profile"] = "ceta-kernel-intent-v3"
                f.put(keys[2], canonical_bytes(intention))
                self.forbid_decision_callbacks(f)
                self.denied_unchanged(f, f.proposal_wire, keys)
                if variant in {"v2_missing_field", "v1_extra_field", "unknown_profile"}:
                    before = self.observation(f, keys)
                    with patch.object(f.store, "commit", side_effect=AssertionError("invalid intent wrote")):
                        with self.assertRaises(ContractError):
                            f.service.recover_permit(prepared.record_wire, f.owners.worker_context)
                        with self.assertRaises(ContractError):
                            f.service.consume(prepared.record_wire, f.owners.worker_context)
                    self.assertEqual(self.observation(f, keys), before)
                    # Evidence must reach the malformed intent on a genuinely
                    # CONSUMED record, rather than deny at a PREPARED label.
                    g = self.fixture()
                    gp = g.prepare()
                    gc = g.service.consume(gp.record_wire, g.owners.worker_context)
                    gkeys = g.permit_keys(gp.record_wire)
                    malformed = strict_loads(g.cell(gkeys[2]).value_wire)
                    if variant == "v2_missing_field":
                        malformed.pop("grant_commitment")
                    elif variant == "v1_extra_field":
                        malformed["profile"] = LEGACY_INTENT_PROFILE
                    else:
                        malformed["profile"] = "ceta-kernel-intent-v3"
                    g.put(gkeys[2], canonical_bytes(malformed))
                    self.forbid_decision_callbacks(g)
                    before = self.observation(g, gkeys)
                    with patch.object(g.store, "commit", side_effect=AssertionError("invalid evidence wrote")):
                        with self.assertRaises(ContractError):
                            g.service.recover_permit(gp.record_wire, g.owners.worker_context)
                        with self.assertRaises(ContractError):
                            g.service.resolve_consumption_for_peer(gc.record_wire, g.owners.worker_context)
                    self.assertEqual(self.observation(g, gkeys), before)

    def test_current_permit_immutable_or_unsupported_lifecycle_substitutions_are_denied(self):
        variants = ({"nonce": "nonce:foreign"}, {"arguments_commitment": CHANGED},
                    {"input_commitment": CHANGED}, {"reservation_ref": "reservation:foreign"},
                    {"issuance_evidence_ref": "event:foreign"}, {"approval_evidence_ref": "evidence:foreign"},
                    {"status": "CONSUMED", "consume_event_ref": "event:fiction",
                     "causation_ref": "event:fiction"},
                    {"status": "ADMITTED"}, {"status": "SETTLED"}, {"status": "INDETERMINATE"})
        for change in variants:
            with self.subTest(change=change):
                f = self.fixture()
                prepared = f.prepare()
                keys = f.permit_keys(prepared.record_wire)
                wire = canonical_bytes(dict(strict_loads(prepared.record_wire), **change))
                self.assertEqual(f.codec.decode(wire).record_type, "OperationPermit")
                f.put(keys[0], wire)
                self.forbid_decision_callbacks(f)
                self.denied_unchanged(f, f.proposal_wire, keys)

    def test_issuance_event_actor_session_causation_type_and_payload_faults_are_denied(self):
        for change in ({"actor_id": "worker:foreign"}, {"actor_session": "session:foreign"},
                       {"causation_ref": "proposal:foreign"},
                       {"event_type": "fixture.not-issuance"}, {"record_id": "event:foreign"}):
            with self.subTest(event_change=change):
                f = self.fixture()
                prepared = f.prepare()
                keys = f.permit_keys(prepared.record_wire)
                index = strict_loads(f.cell(f.issuance_key()).value_wire)
                original_replay = f.store.replay
                reached = []

                def substituted_replay(scope_id, start=0, limit=128, *, checkpoints=()):
                    rows = original_replay(scope_id, start, limit, checkpoints=checkpoints)
                    if scope_id == PROJECT and start == index["sequence"] and limit == 1:
                        self.assertEqual(len(rows), 1)
                        event = strict_loads(rows[0].event_wire)
                        event.update(change)
                        reached.append(True)
                        return (JournalEntry(canonical_bytes(event), rows[0].payload_wire),)
                    return rows

                self.forbid_decision_callbacks(f)
                with patch.object(f.store, "replay", substituted_replay):
                    self.denied_unchanged(f, f.proposal_wire, keys)
                self.assertTrue(reached, "recovery must resolve the indexed issuance event")
        # Distinct real-database fault: no protected-store compromise claim.
        f = self.fixture()
        prepared = f.prepare()
        keys = f.permit_keys(prepared.record_wire)
        index = strict_loads(f.cell(f.issuance_key()).value_wire)
        payload = dict(strict_loads(prepared.record_wire), nonce="nonce:corrupt-owned-history")
        f.store._connection.execute(
            "UPDATE history_events SET payload_wire=? WHERE scope_id=? AND sequence=?",
            (canonical_bytes(payload), PROJECT, index["sequence"]))
        tables = ("history_meta", "history_scopes", "history_events",
                  "store_commits", "store_changes", "store_cells")

        def raw_rows():
            return tuple((name, tuple(sorted(f.store._connection.execute(
                'SELECT * FROM "' + name + '"').fetchall(), key=repr))) for name in tables)

        before = raw_rows()
        with patch.object(f.store, "commit", side_effect=AssertionError("corrupt recovery wrote")):
            with self.assertRaises(ContractError):
                f.service.recover_preparation(f.proposal_wire, f.owners.worker_context)
        self.assertFalse(f.store._connection.in_transaction)
        self.assertEqual(raw_rows(), before)

    def test_original_context_is_rechecked_after_replay_and_final_snapshot_before_disclosure(self):
        for variant in ("peer_changed", "context_invalidated", "final_snapshot_invalidated"):
            with self.subTest(variant=variant):
                f = self.fixture()
                prepared = f.prepare()
                keys = f.permit_keys(prepared.record_wire)
                index = strict_loads(f.cell(f.issuance_key()).value_wire)
                context = f.owners.worker_context
                original_replay = f.store.replay
                original_snapshot = f.store.snapshot
                original_authenticate = f.owners.authenticate
                reached, final_read, contexts = [], [], []
                authenticated_after_replay = []
                union = {f.issuance_key(), keys[0], keys[2]}

                def authenticate(actual_context):
                    contexts.append(actual_context)
                    self.assertIs(actual_context, context, "kernel retargeted the original context")
                    peer = original_authenticate(actual_context)
                    if reached:
                        authenticated_after_replay.append(True)
                    return peer

                def invalidate_after_replay(scope_id, start=0, limit=128, *, checkpoints=()):
                    rows = original_replay(scope_id, start, limit, checkpoints=checkpoints)
                    if scope_id == PROJECT and start == index["sequence"] and limit == 1 and not reached:
                        reached.append(True)
                        if variant == "peer_changed":
                            peer = f.owners.worker
                            f.owners.worker = PeerIdentity(peer.principal_id, "session:changed-after-read")
                        elif variant == "context_invalidated":
                            f.owners.worker_context = object()
                    return rows

                def invalidate_after_final_snapshot(selected, *, state_checkpoint=None):
                    cells = original_snapshot(selected, state_checkpoint=state_checkpoint)
                    if (variant == "final_snapshot_invalidated" and reached
                            and authenticated_after_replay and not final_read
                            and union.issubset(set(selected))):
                        # The private validator's earlier union read has
                        # finished. Invalidate only at the union read following
                        # a successful post-replay check of the original context.
                        final_read.append(True)
                        f.owners.worker_context = object()
                    return cells

                self.forbid_decision_callbacks(f)
                expected = ("KERNEL_PEER_BINDING_MISMATCH" if variant == "peer_changed"
                            else "FIXTURE_AUTHENTICATION_DENIED")
                with patch.object(f.owners, "authenticate", authenticate), \
                        patch.object(f.store, "replay", invalidate_after_replay), \
                        patch.object(f.store, "snapshot", invalidate_after_final_snapshot):
                    self.denied_unchanged(f, f.proposal_wire, keys, context=context, code=expected)
                self.assertEqual(reached, [True])
                if variant == "final_snapshot_invalidated":
                    self.assertEqual(final_read, [True], "must invalidate at the union read after successful post-replay authentication")
                self.assertGreaterEqual(len(contexts), 2)

    def test_generation_changes_in_each_selected_recovery_cell_deny_even_after_aba_restore(self):
        for collection in ("issuance", "permit", "intent"):
            with self.subTest(collection=collection):
                f = self.fixture()
                prepared = f.prepare()
                keys = f.permit_keys(prepared.record_wire)
                index = strict_loads(f.cell(f.issuance_key()).value_wire)
                target = (f.issuance_key() if collection == "issuance"
                          else keys[0] if collection == "permit" else keys[2])
                original_cell = f.cell(target)
                original_replay = f.store.replay
                position, budget = f.store.store_position(), f.budget()
                reached, injected_cut = [], []
                self.forbid_decision_callbacks(f)

                def replay_then_aba(scope_id, start=0, limit=128, *, checkpoints=()):
                    rows = original_replay(scope_id, start, limit, checkpoints=checkpoints)
                    if scope_id == PROJECT and start == index["sequence"] and limit == 1 and not reached:
                        reached.append(True)
                        value = strict_loads(original_cell.value_wire)
                        field = ("issuance_event_ref" if collection == "issuance"
                                 else "nonce" if collection == "permit" else "state")
                        value[field] = ("event:ABA-fixture" if collection == "issuance"
                                        else "nonce:ABA-fixture" if collection == "permit"
                                        else "INTENT_CHANGED_BY_FIXTURE")
                        # Deliberate real fixture writer commits restore bytes
                        # but advance generation, defeating value-only checks.
                        f.put(target, canonical_bytes(value))
                        f.put(target, original_cell.value_wire)
                        injected_cut.append(self.observation(f, keys))
                    return rows

                with patch.object(f.store, "replay", replay_then_aba):
                    with self.assertRaises(ContractError) as caught:
                        f.service.recover_preparation(f.proposal_wire, f.owners.worker_context)
                self.assertEqual(caught.exception.code, "KERNEL_RECOVERY_STATE_CHANGED")
                self.assertEqual(reached, [True])
                self.assertEqual(self.observation(f, keys), injected_cut[0],
                                 "query wrote beyond the explicit fixture ABA")
                self.assertEqual(f.store.store_position().next_commit, position.next_commit + 2)
                self.assertEqual(f.cell(target).generation, original_cell.generation + 2)
                self.assertEqual(f.cell(target).value_wire, original_cell.value_wire)
                self.assertNotEqual(f.cell(target).revision, original_cell.revision)
                self.assertEqual(f.budget(), budget)

    def test_consumption_index_substitution_cannot_turn_preparation_lookup_into_spent_evidence(self):
        for field, value in (("event_id", "event:foreign"), ("sequence", 0), ("previous_head", None)):
            with self.subTest(field=field):
                f = self.fixture()
                prepared = f.prepare()
                f.service.consume(prepared.record_wire, f.owners.worker_context)
                keys = f.permit_keys(prepared.record_wire)
                intention = strict_loads(f.cell(keys[2]).value_wire)
                self.assertNotEqual(intention["consumption"][field], value)
                intention["consumption"][field] = value
                f.put(keys[2], canonical_bytes(intention))
                self.forbid_decision_callbacks(f)
                self.denied_unchanged(f, f.proposal_wire, keys)
                self.assertEqual(f.budget()[2:], (ZERO_BUDGET, COST))

    def test_ingress_and_application_forward_exact_original_proposal_and_message_bound_context(self):
        f = self.fixture()
        prepared = f.prepare()
        original = json.dumps(f.proposal, ensure_ascii=False, indent=2).encode("utf8") + b"\n"
        message = self.message(f, original)
        context, calls = object(), []
        parsed = f.codec.decode(prepared.record_wire)

        def require_message(actual_context, actual_message):
            if actual_context is not context or actual_message is not message:
                raise ContractError("FIXTURE_MESSAGE_CONTEXT_BINDING")
            calls.append(("message", actual_context, actual_message))

        def authenticate(actual_context):
            self.assertIs(actual_context, context)
            calls.append(("authenticate", actual_context))
            return f.owners.worker

        def recover(wire, actual_context):
            self.assertEqual(wire, original)
            self.assertIs(actual_context, context)
            calls.append(("recover", wire, actual_context))
            return parsed

        identity = SimpleNamespace(require_message=require_message, authenticate=authenticate)
        kernel = KernelUseCases(SimpleNamespace(recover_preparation=recover))
        result = KernelIngress(kernel, identity)(message, context)
        self.assertIs(result, parsed)
        self.assertEqual([call[0] for call in calls], ["message", "authenticate", "recover"])
        self.assertEqual(message.record.original_wire, original)
        with self.assertRaises(ContractError) as caught:
            KernelIngress(kernel, identity)(message, object())
        self.assertEqual(caught.exception.code, "FIXTURE_MESSAGE_CONTEXT_BINDING")

    def test_current_record_results_bind_proposal_fields_scope_lifecycle_and_route(self):
        f = self.fixture()
        prepared = f.prepare()
        consumed = f.service.consume(prepared.record_wire, f.owners.worker_context)
        message = self.message(f, f.proposal_wire)
        for wire in (prepared.record_wire, consumed.record_wire):
            with self.subTest(status=strict_loads(wire)["status"]):
                response = encode_response(message, f.codec.decode(wire), f.codec)
                decoded = decode_response(response, message, f.codec)
                self.assertEqual(decoded.kind, "CURRENT_RECORD")
                self.assertEqual(decoded.record_wire, wire)
                self.assertIsNone(decoded.event_wire)
                self.assertIsNone(decoded.prior_position)
                for change in ({"proposal_ref": "proposal:foreign"}, {"scope_id": "project:foreign"},
                               {"task_id": "task:foreign"}, {"adapter_id": "adapter:foreign"},
                               {"operation": "file.write"}, {"arguments_commitment": CHANGED},
                               {"resources": [dict(f.proposal["resources"][0], resource_id="resource:foreign")]},
                               {"approval_evidence_ref": None}, {"status": "SETTLED"}):
                    with self.subTest(change=change):
                        changed = dict(strict_loads(wire), **change)
                        altered = strict_loads(response)
                        altered["record_wire"] = canonical_bytes(changed).decode("utf8")
                        self.assertEqual(f.codec.decode(canonical_bytes(changed)).record_type, "OperationPermit")
                        with self.assertRaises(ContractError):
                            decode_response(canonical_bytes(altered), message, f.codec)
                bad = strict_loads(response)
                bad.update(event_wire=prepared.event_wire.decode("utf8"),
                           prior_position={"scope_id": prepared.prior_position.scope_id,
                               "next_sequence": prepared.prior_position.next_sequence,
                               "head": prepared.prior_position.head})
                with self.assertRaises(ContractError):
                    decode_response(canonical_bytes(bad), message, f.codec)
        with self.assertRaises(ContractError):
            encode_response(message, prepared, f.codec)
        different_request = self.message(f, prepared.record_wire, "kernel.recover_permit")
        response = encode_response(message, f.codec.decode(prepared.record_wire), f.codec)
        with self.assertRaises(ContractError):
            decode_response(response, different_request, f.codec)


class NativePreparationRecoveryTests(_ServiceTestCase):
    """Real owned Windows IPC; positive fixture seed is not child authority."""

    def test_actual_prepared_lookup_from_original_proposal_preserves_store_and_budget(self):
        fixture = self.fixture()
        prepared = fixture.prepare()
        keys = fixture.permit_keys(prepared.record_wire)
        before = fixture.cut(keys), fixture.budget()
        service = self.fixture_service(fixture)
        self.ready(service)
        _, response = self.call(service, fixture.proposal_wire, ROUTE)
        self.assertEqual(response.kind, "CURRENT_RECORD")
        self.assertEqual(response.record_wire, prepared.record_wire)
        self.assertIsNone(response.event_wire)
        self.assertIsNone(response.prior_position)
        self.assertNotEqual(self.codec.decode(response.record_wire).record_id,
                            self.codec.decode(fixture.proposal_wire).record_id)
        self.stop(service)
        self.reopen_unchanged(fixture, before, keys)

    def test_actual_consumed_lookup_from_original_proposal_returns_spent_record_and_evidence(self):
        fixture = self.fixture()
        prepared = fixture.prepare()
        consumed = fixture.service.consume(prepared.record_wire, fixture.owners.worker_context)
        keys = fixture.permit_keys(prepared.record_wire)
        before = fixture.cut(keys), fixture.budget()
        service = self.fixture_service(fixture)
        self.ready(service)
        _, response = self.call(service, fixture.proposal_wire, ROUTE)
        self.assertEqual(response.kind, "CURRENT_RECORD")
        self.assertEqual(response.record_wire, consumed.record_wire)
        _, evidence = self.call(service, response.record_wire, "kernel.resolve_consumption")
        self.assertEqual(evidence.kind, "EVIDENCE")
        self.assertEqual((evidence.record_wire, evidence.event_wire, evidence.prior_position),
                         (consumed.record_wire, consumed.event_wire, consumed.prior_position))
        self.stop(service)
        self.reopen_unchanged(fixture, before, keys)

    def test_actual_different_launcher_bound_principal_or_session_cannot_select_preparation(self):
        for variant in ("principal", "session"):
            with self.subTest(variant=variant):
                fixture = self.fixture()
                prepared = fixture.prepare()
                keys = fixture.permit_keys(prepared.record_wire)
                before = fixture.cut(keys), fixture.budget()
                service = self.fixture_service(fixture,
                    principal="worker:other-selected-principal" if variant == "principal" else None,
                    session="session:other-selected-session" if variant == "session" else None)
                self.ready(service)
                _, response = self.call(service, fixture.proposal_wire, ROUTE)
                self.assertEqual(response.kind, "DENIED_RECONCILE")
                self.assertEqual(response.error_code, "KERNEL_PEER_BINDING_MISMATCH")
                self.assertIsNone(response.record_wire)
                self.stop(service)
                self.reopen_unchanged(fixture, before, keys)

    def test_actual_recovering_controller_allows_preparation_lookup_without_new_admission(self):
        fixture = self.fixture()
        prepared = fixture.prepare()
        keys = fixture.permit_keys(prepared.record_wire)
        before = fixture.cut(keys), fixture.budget()
        service = self.fixture_service(fixture)
        self.ready(service)
        attempt, denial = self.call(service, fixture.proposal_wire, "kernel.prepare")
        self.assertEqual(denial.kind, "DENIED_RECONCILE")
        self.assertEqual(denial.error_code, "TRUSTED_PREPARATION_OWNER_UNAVAILABLE")
        self.until(lambda: service.poll()["state"] == "RECOVERING" and service._send_task is None,
                   explanation="denied attempt did not retire into RECOVERING")
        request_path = service._spool / (attempt + ".request.json")
        original_request = native_fixture_path(request_path).read_bytes()
        self.assertEqual(decode_message(original_request, self.codec).record.original_wire,
                         fixture.proposal_wire)
        _, response = self.call(service, fixture.proposal_wire, ROUTE)
        self.assertEqual(response.kind, "CURRENT_RECORD")
        self.assertEqual(response.record_wire, prepared.record_wire)
        self.assertEqual(native_fixture_path(request_path).read_bytes(), original_request)
        self.assertEqual(service.poll()["state"], "READY")
        self.stop(service)
        self.reopen_unchanged(fixture, before, keys)


if __name__ == "__main__":
    unittest.main()
