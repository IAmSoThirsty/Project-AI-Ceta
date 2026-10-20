"""Pure synthetic result binding tests; no native/store/effect qualification.

KernelResult and ConsumptionEvidence are real internal value types instantiated
with synthetic records/commit positions. These tests execute no kernel/store,
transport, profile, model, native helper or authority-owner implementation.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts.events import EventContract, StreamPosition
from ceta.contracts.evidence_admission import ConsumptionEvidence
from ceta.contracts.history import JournalCommit
from ceta.contracts.kernel_transactions import KernelResult
from ceta.contracts.local_ipc import decode_message, encode_message
from ceta.contracts.local_results import RESULT_PROFILE, decode_response, encode_response
from ceta.contracts.store_transactions import StoreCell, StoreCommit, StoreKey, StorePosition
from ceta.contracts.wire import ContractError, MAX_WIRE_BYTES, PROFILE, RecordCodec, canonical_bytes, strict_loads
from test_all_records import example

HASH = "sha256:" + "a" * 64


class LocalResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes())
        cls.codec = RecordCodec(cls.schema)

    def setUp(self):
        self.proposal = self.record("ActionProposal", record_id="proposal:result",
                                    scope_id="project:result", task_id="task:result")
        self.permit = self.record("OperationPermit", record_id="permit:result",
            scope_id="project:result", causation_ref="proposal:result", proposal_ref="proposal:result",
            task_id="task:result", adapter_id=self.proposal["adapter_id"], operation=self.proposal["operation"],
            arguments_commitment=self.proposal["arguments_commitment"], resources=self.proposal["resources"],
            issuance_evidence_ref="event:prepare", consume_event_ref=None, status="PREPARED")
        self.grant = self.record("StandingGrant", record_id="grant:result",
                                 scope_id="project:result", status="ACTIVE", revocation_generation=0)
        self.request = self.message(self.proposal, "kernel.prepare")
        self.prepared = self.kernel_result(self.permit, "kernel.intent.committed", "event:prepare")
        self.wire = encode_response(self.request, self.prepared, self.codec)

    def record(self, kind, **updates):
        value = example(self.schema["$defs"][kind])
        value.update(updates)
        self.codec.decode(canonical_bytes(value))
        return value

    def message(self, record, operation, *, original=None, **updates):
        values = dict(message_id="message:result", sender_session="session:result",
            receiver_generation="service:result", operation=operation, issued_at_ms=1000,
            expires_at_ms=2000, correlation_ref="correlation:result", causation_ref="cause:result",
            reason_ref="reason:result" if operation == "kernel.revoke" else None)
        values.update(updates)
        wire = encode_message(canonical_bytes(record) if original is None else original,
                              self.codec, **values)
        return decode_message(wire, self.codec)

    def event(self, payload, event_type, event_id, prior=None, **updates):
        parsed = self.codec.decode(canonical_bytes(payload))
        prior = prior or StreamPosition(payload["scope_id"], 0, None)
        value = self.record("EventRecord", record_id=event_id, scope_id=payload["scope_id"],
            causation_ref=payload["causation_ref"], sequence=prior.next_sequence,
            previous_head=prior.head, event_type=event_type, payload_ref=payload["record_id"],
            payload_commitment=parsed.commitment, canonicalization_profile=PROFILE,
            actor_session="session:result", signer_key_ref=None, signature_ref=None)
        value.update(updates)
        return canonical_bytes(value), prior

    def kernel_result(self, payload, event_type, event_id, *, prior=None, event_updates=None,
                      extra_scope=False):
        wire = canonical_bytes(payload)
        event, before = self.event(payload, event_type, event_id, prior, **(event_updates or {}))
        head = EventContract(self.codec).preimages(event).head
        after = StreamPosition(before.scope_id, before.next_sequence + 1, head)
        history = (JournalCommit(before, after, (event_id,)),)
        collection = "grant" if payload["record_type"] == "StandingGrant" else "permit"
        cells = (StoreCell(StoreKey(collection, payload["scope_id"], payload["record_id"]), 1, wire),)
        if extra_scope:
            other = StreamPosition("installation:private", 0, None)
            history += (JournalCommit(other, StreamPosition(other.scope_id, 1, HASH), ("event:private",)),)
            cells += (StoreCell(StoreKey("budget", other.scope_id, "grant:private"), 1,
                                canonical_bytes({"private_budget": "NEVER_SERIALIZE_THIS"})),)
        commit = StoreCommit(history, StorePosition(1, HASH), cells)
        return KernelResult(wire, event, before, commit)

    def consumed(self):
        return dict(self.permit, status="CONSUMED", consume_event_ref="event:consume",
                    causation_ref="event:consume")

    def reject(self, call, code=None):
        with self.assertRaises(ContractError) as caught:
            call()
        if code is not None:
            self.assertEqual(caught.exception.code, code)

    def reject_wire(self, value, code=None, request=None):
        self.reject(lambda: decode_response(canonical_bytes(value), request or self.request, self.codec), code)

    def rewrite_payload(self, wire, updates, event_updates=None):
        value = strict_loads(wire)
        payload = strict_loads(value["record_wire"].encode("utf8"))
        payload.update(updates)
        parsed = self.codec.decode(canonical_bytes(payload))
        value["record_wire"] = parsed.canonical_wire.decode("utf8")
        if value["event_wire"] is not None:
            event = strict_loads(value["event_wire"].encode("utf8"))
            event.update(payload_ref=parsed.record_id, payload_commitment=parsed.commitment,
                         causation_ref=payload["causation_ref"], scope_id=payload["scope_id"])
            event.update(event_updates or {})
            value["event_wire"] = canonical_bytes(event).decode("utf8")
        return value

    def test_prepared_kernel_result_round_trips_only_its_scoped_payload_and_event(self):
        result = self.kernel_result(self.permit, "kernel.intent.committed", "event:prepare", extra_scope=True)
        wire = encode_response(self.request, result, self.codec)
        decoded = decode_response(wire, self.request, self.codec)
        self.assertEqual(decoded.kind, "COMMITTED")
        self.assertEqual((decoded.record_wire, decoded.event_wire, decoded.prior_position),
                         (result.record_wire, result.event_wire, result.prior_position))
        self.assertEqual(decoded.original_response, wire)
        self.assertIsNone(decoded.error_code)
        self.assertNotIn(b"NEVER_SERIALIZE_THIS", wire)
        self.assertNotIn(b"installation:private", wire)
        self.assertNotIn("commit", strict_loads(wire))

    def test_consumed_kernel_result_round_trips_without_claiming_an_effect(self):
        request = self.message(self.permit, "kernel.consume")
        result = self.kernel_result(self.consumed(), "kernel.permit.consumed", "event:consume")
        decoded = decode_response(encode_response(request, result, self.codec), request, self.codec)
        self.assertEqual(decoded.kind, "COMMITTED")
        self.assertEqual(strict_loads(decoded.record_wire)["status"], "CONSUMED")
        self.assertNotIn("effect_completed", strict_loads(decoded.original_response))

    def test_revoked_kernel_result_requires_exact_original_grant_and_reason(self):
        request = self.message(self.grant, "kernel.revoke")
        revoked = dict(self.grant, status="REVOKED", revocation_generation=1, causation_ref="reason:result")
        result = self.kernel_result(revoked, "kernel.grant.revoked", "event:revoke")
        wire = encode_response(request, result, self.codec)
        self.assertEqual(decode_response(wire, request, self.codec).kind, "COMMITTED")
        for changes in ({"revocation_generation": 2}, {"causation_ref": "reason:other"},
                        {"record_id": "grant:other"}, {"grantee_id": "principal:other"}):
            with self.subTest(changes=changes):
                self.reject_wire(self.rewrite_payload(wire, changes), request=request)

    def test_evidence_preserves_historical_actor_and_actual_predecessor(self):
        consumed = self.consumed()
        request = self.message(consumed, "kernel.resolve_consumption")
        prior = StreamPosition("project:result", 4, HASH)
        event, prior = self.event(consumed, "kernel.permit.consumed", "event:consume", prior,
                                  actor_session="session:historical")
        evidence = ConsumptionEvidence(canonical_bytes(consumed), event, prior)
        decoded = decode_response(encode_response(request, evidence, self.codec), request, self.codec)
        self.assertEqual(decoded.kind, "EVIDENCE")
        self.assertEqual(decoded.prior_position, prior)
        self.assertEqual(decoded.event_wire, event)

    def test_current_prepared_permit_is_read_only_without_event_or_commit(self):
        request = self.message(self.permit, "kernel.recover_permit")
        parsed = self.codec.decode(canonical_bytes(self.permit))
        decoded = decode_response(encode_response(request, parsed, self.codec), request, self.codec)
        self.assertEqual(decoded.kind, "CURRENT_RECORD")
        self.assertEqual(decoded.record_wire, parsed.original_wire)
        self.assertIsNone(decoded.event_wire)
        self.assertIsNone(decoded.prior_position)

    def test_recovery_can_observe_consumed_permit_after_lost_consumption_result(self):
        request = self.message(self.permit, "kernel.recover_permit")
        parsed = self.codec.decode(canonical_bytes(self.consumed()))
        decoded = decode_response(encode_response(request, parsed, self.codec), request, self.codec)
        self.assertEqual(strict_loads(decoded.record_wire)["consume_event_ref"], "event:consume")
        self.assertEqual(decoded.kind, "CURRENT_RECORD")
        self.assertIsNone(decoded.event_wire)  # Authentication/evidence lookup are kernel duties.

    def test_postcommit_denial_preserves_uncertainty_and_has_no_payload(self):
        # The independently constructed committed result and subsequent denial
        # model the kernel's already documented post-COMMIT clock-guard failure.
        committed = self.kernel_result(self.consumed(), "kernel.permit.consumed", "event:consume")
        request = self.message(self.permit, "kernel.consume")
        decode_response(encode_response(request, committed, self.codec), request, self.codec)
        denied = encode_response(request, ContractError("CLOCK_EPOCH_CHANGED", "$/private/path"), self.codec)
        result = decode_response(denied, request, self.codec)
        self.assertEqual((result.kind, result.error_code), ("DENIED_RECONCILE", "CLOCK_EPOCH_CHANGED"))
        self.assertIsNone(result.record_wire)
        self.assertIsNone(result.event_wire)
        self.assertIsNone(result.prior_position)
        self.assertNotIn(b"private/path", denied)
        self.assertNotIn(b"NOT_STARTED", denied)
        self.assertEqual(strict_loads(committed.record_wire)["status"], "CONSUMED")

    def test_error_codes_are_bounded_uppercase_codes_without_raw_messages_or_paths(self):
        for code in ("raw secret at C:\\private", "lower_case", "A" * 81, "", None, 17,
                     "CODE\nPRIVATE", "CODE/path"):
            with self.subTest(code=code):
                wire = encode_response(self.request, ContractError(code, "$/private"), self.codec)
                result = decode_response(wire, self.request, self.codec)
                self.assertEqual(result.error_code, "INTERNAL_ERROR_RECONCILE")
                self.assertNotIn(b"$/private", wire)
        wire = encode_response(self.request, ContractError("VALID_CODE_24"), self.codec)
        self.assertEqual(decode_response(wire, self.request, self.codec).error_code, "VALID_CODE_24")

    def test_each_request_identity_field_is_bound(self):
        value = strict_loads(self.wire)
        for name in ("request_sha256", "message_id", "correlation_ref", "causation_ref", "sender_session",
                     "receiver_generation", "operation", "scope_id", "request_record_id"):
            with self.subTest(field=name):
                self.reject_wire(dict(value, **{name: "substitute:other"}), "RESULT_REQUEST_BINDING")

    def test_same_message_id_different_task_or_attempt_bytes_cannot_reuse_response(self):
        for changes in ({"task_id": "task:other"}, {"request_ref": "attempt:other"},
                        {"proposal_revision": "sha256:" + "b" * 64}):
            with self.subTest(changes=changes):
                other = self.message(dict(self.proposal, **changes), "kernel.prepare")
                self.reject(lambda: decode_response(self.wire, other, self.codec), "RESULT_REQUEST_BINDING")

    def test_exact_original_request_bytes_are_bound_even_when_record_semantics_match(self):
        other = self.message(self.proposal, "kernel.prepare", original=json.dumps(self.proposal, indent=2).encode())
        self.assertEqual(other.record.canonical_wire, self.request.record.canonical_wire)
        self.assertNotEqual(other.original_message, self.request.original_message)
        self.reject(lambda: decode_response(self.wire, other, self.codec), "RESULT_REQUEST_BINDING")
        self.assertEqual(strict_loads(self.wire)["request_sha256"], hashlib.sha256(self.request.original_message).hexdigest())

    def test_manually_forged_request_or_parsed_record_cannot_replace_original_wire(self):
        self.reject(lambda: decode_response(self.wire, replace(self.request, sender_session="session:other"), self.codec),
                    "RESULT_REQUEST_BINDING")
        request = self.message(self.permit, "kernel.recover_permit")
        parsed = self.codec.decode(canonical_bytes(self.permit))
        self.reject(lambda: encode_response(request, replace(parsed, record_id="permit:other"), self.codec),
                    "RESULT_PARSED_RECORD_BINDING")

    def test_extra_missing_duplicate_and_nonobject_frames_are_rejected(self):
        value = strict_loads(self.wire)
        for name in value:
            changed = dict(value)
            del changed[name]
            with self.subTest(missing=name):
                self.reject_wire(changed, "RESULT_FIELDS")
        self.reject_wire(dict(value, authenticated=True), "RESULT_FIELDS")
        self.reject(lambda: decode_response(self.wire[:-1] + b',"version":1}', self.request, self.codec), "DUPLICATE_KEY")
        for value in ([], True, None, "text"):
            self.reject_wire(value, "RESULT_FIELDS")

    def test_profile_version_kind_and_noncanonical_framing_are_rejected(self):
        value = strict_loads(self.wire)
        self.reject_wire(dict(value, profile="other"), "RESULT_VERSION")
        self.assertEqual(value["profile"], RESULT_PROFILE)
        for version in (True, "1", 0, 2, None):
            self.reject_wire(dict(value, version=version), "RESULT_VERSION")
        for kind in ("ALLOW", "EFFECT_COMPLETED", [], None):
            self.reject_wire(dict(value, kind=kind), "RESULT_KIND")
        self.reject(lambda: decode_response(json.dumps(value, indent=2).encode(), self.request, self.codec), "RESULT_CANONICAL")

    def test_wire_size_type_unicode_and_codec_are_checked(self):
        for wire in (b"", b"x" * (MAX_WIRE_BYTES + 1), bytearray(self.wire), self.wire.decode(), None):
            self.reject(lambda: decode_response(wire, self.request, self.codec), "RESULT_SIZE")
        self.reject(lambda: decode_response(b"\xff", self.request, self.codec), "MALFORMED_JSON")
        self.reject(lambda: decode_response(self.wire, self.request, object()), "RESULT_REQUEST_OR_CODEC_REQUIRED")
        self.reject(lambda: encode_response(self.request, object(), self.codec), "RESULT_VALUE_REQUIRED")

    def test_schema_valid_result_substitutions_do_not_pass_with_recomputed_payload_hash(self):
        for updates in ({"proposal_ref": "proposal:other"}, {"task_id": "task:other"},
                        {"adapter_id": "adapter:other"}, {"operation": "operation:other"},
                        {"arguments_commitment": "sha256:" + "b" * 64}, {"scope_id": "project:other"}):
            with self.subTest(updates=updates):
                self.reject_wire(self.rewrite_payload(self.wire, updates))

    def test_events_bind_payload_reference_hash_scope_and_predecessor(self):
        value = strict_loads(self.wire)
        for updates in ({"payload_ref": "permit:other"}, {"payload_commitment": "sha256:" + "b" * 64},
                        {"scope_id": "project:other"}, {"sequence": 1}, {"previous_head": HASH},
                        {"event_type": "kernel.permit.consumed"}, {"actor_session": "session:other"}):
            event = strict_loads(value["event_wire"].encode())
            event.update(updates)
            with self.subTest(updates=updates):
                self.reject_wire(dict(value, event_wire=canonical_bytes(event).decode()))
        for prior in ({"scope_id": "project:other", "next_sequence": 0, "head": None},
                      {"scope_id": "project:result", "next_sequence": 1, "head": HASH},
                      {"scope_id": "project:result", "next_sequence": True, "head": None},
                      {"scope_id": "project:result", "next_sequence": 0, "head": None, "allow": True}):
            self.reject_wire(dict(value, prior_position=prior))

    def test_noncanonical_inner_result_or_event_bytes_are_rejected(self):
        value = strict_loads(self.wire)
        for field in ("record_wire", "event_wire"):
            changed = dict(value, **{field: json.dumps(strict_loads(value[field].encode()), indent=2)})
            self.reject_wire(changed)

    def test_commit_encoding_requires_exact_history_and_record_membership(self):
        event_id = self.codec.decode(self.prepared.event_wire).record_id
        before = self.prepared.prior_position
        wrong_after = StreamPosition(before.scope_id, 1, HASH)
        bad_history = (JournalCommit(before, wrong_after, (event_id,)),)
        bad = StoreCommit(bad_history, self.prepared.commit.position, self.prepared.commit.cells)
        self.reject(lambda: encode_response(self.request, replace(self.prepared, commit=bad), self.codec), "RESULT_COMMIT_HISTORY")
        empty = StoreCommit(self.prepared.commit.history, self.prepared.commit.position, ())
        self.reject(lambda: encode_response(self.request, replace(self.prepared, commit=empty), self.codec), "RESULT_COMMIT_RECORD")

    def test_consumption_and_evidence_reject_wrong_event_or_changed_permit_identity(self):
        request = self.message(self.permit, "kernel.consume")
        result = self.kernel_result(self.consumed(), "kernel.permit.consumed", "event:consume")
        wire = encode_response(request, result, self.codec)
        for updates in ({"consume_event_ref": "event:other"}, {"nonce": "nonce:other"},
                        {"reservation_ref": "reservation:other"}, {"input_commitment": "sha256:" + "b" * 64}):
            self.reject_wire(self.rewrite_payload(wire, updates), request=request)
        consumed_request = self.message(self.consumed(), "kernel.resolve_consumption")
        evidence = ConsumptionEvidence(result.record_wire, result.event_wire, result.prior_position)
        evidence_wire = encode_response(consumed_request, evidence, self.codec)
        self.reject_wire(self.rewrite_payload(evidence_wire, {"consume_event_ref": "event:other"}), request=consumed_request)

    def test_current_record_cannot_regress_or_substitute_known_consumption(self):
        request = self.message(self.consumed(), "kernel.recover_permit")
        prepared = self.codec.decode(canonical_bytes(self.permit))
        self.reject(lambda: encode_response(request, prepared, self.codec))
        other = self.codec.decode(canonical_bytes(dict(self.consumed(), consume_event_ref="event:other", causation_ref="event:other")))
        self.reject(lambda: encode_response(request, other, self.codec), "RESULT_CONSUMPTION_BINDING")

    def assert_recovery_selector_rejected(self, selector, code):
        # Each selector is schema-valid and the forged response is rebound to
        # its exact request digest, so rejection must reach recovery semantics.
        request = self.message(selector, "kernel.recover_permit")
        parsed = self.codec.decode(canonical_bytes(self.consumed()))
        legitimate = self.message(self.permit, "kernel.recover_permit")
        value = strict_loads(encode_response(legitimate, parsed, self.codec))
        value["request_sha256"] = hashlib.sha256(request.original_message).hexdigest()
        self.reject(lambda: encode_response(request, parsed, self.codec), code)
        self.reject_wire(value, code, request)

    def test_current_record_rejects_schema_valid_settled_and_admitted_selectors(self):
        for selector in (dict(self.consumed(), status="SETTLED", causation_ref="event:settlement"),
                         dict(self.permit, status="ADMITTED")):
            with self.subTest(status=selector["status"]):
                self.assert_recovery_selector_rejected(selector, "RESULT_RECOVERY_SELECTOR_STATE")

    def test_current_record_rejects_incorrect_original_causal_and_consumption_references(self):
        selectors = (dict(self.permit, causation_ref="event:prepare"),
                     dict(self.permit, causation_ref=None),
                     dict(self.permit, consume_event_ref="event:consume"),
                     dict(self.consumed(), causation_ref="proposal:result"),
                     dict(self.consumed(), causation_ref=None),
                     dict(self.consumed(), consume_event_ref=None))
        for selector in selectors:
            with self.subTest(status=selector["status"], cause=selector["causation_ref"],
                              consumption=selector["consume_event_ref"]):
                self.assert_recovery_selector_rejected(selector, "RESULT_RECOVERY_SELECTOR_BINDING")

    def test_issued_is_a_structural_codec_denial_not_a_schema_valid_selector(self):
        self.assertNotIn("ISSUED", self.schema["$defs"]["OperationPermit"]["properties"]["status"]["enum"])
        bad_wire = canonical_bytes(dict(self.permit, status="ISSUED"))
        self.reject(lambda: self.codec.decode(bad_wire), "SCHEMA_VALUE")
        self.reject(lambda: self.message(dict(self.permit, status="ISSUED"), "kernel.recover_permit"), "SCHEMA_VALUE")
        request = self.message(self.permit, "kernel.recover_permit")
        parsed = self.codec.decode(canonical_bytes(self.permit))
        value = strict_loads(encode_response(request, parsed, self.codec))
        value["record_wire"] = bad_wire.decode("utf8")
        self.reject_wire(value, "SCHEMA_VALUE", request)
        self.reject(lambda: encode_response(request, replace(parsed, original_wire=bad_wire), self.codec), "SCHEMA_VALUE")

    def test_historic_settled_evidence_selector_retains_consumption_evidence_binding(self):
        consumed = self.consumed()
        settled = dict(consumed, status="SETTLED", causation_ref="event:settlement")
        request = self.message(settled, "kernel.resolve_consumption")
        prior = StreamPosition("project:result", 3, HASH)
        event, prior = self.event(consumed, "kernel.permit.consumed", "event:consume", prior,
                                  actor_session="session:historical")
        evidence = ConsumptionEvidence(canonical_bytes(consumed), event, prior)
        response = decode_response(encode_response(request, evidence, self.codec), request, self.codec)
        self.assertEqual(response.kind, "EVIDENCE")
        self.assertEqual(response.record_wire, evidence.consumed_permit_wire)
        self.assertEqual(response.event_wire, evidence.event_wire)
        self.assertEqual(response.prior_position, prior)

    def test_result_kinds_cannot_be_switched_between_read_only_and_mutating_routes(self):
        value = strict_loads(self.wire)
        self.reject_wire(dict(value, kind="EVIDENCE"), "RESULT_OPERATION_KIND")
        self.reject_wire(dict(value, kind="CURRENT_RECORD", event_wire=None, prior_position=None), "RESULT_OPERATION_KIND")
        request = self.message(self.permit, "kernel.recover_permit")
        parsed = self.codec.decode(canonical_bytes(self.permit))
        current = strict_loads(encode_response(request, parsed, self.codec))
        self.reject_wire(dict(current, event_wire=self.prepared.event_wire.decode()), "RESULT_CURRENT_RECORD_SHAPE", request)

    def test_denial_never_carries_payload_or_unsanitized_wire_error(self):
        value = strict_loads(encode_response(self.request, ContractError("DENIED"), self.codec))
        for changes in ({"record_wire": self.prepared.record_wire.decode()},
                        {"event_wire": self.prepared.event_wire.decode()},
                        {"prior_position": {"scope_id": "project:result", "next_sequence": 0, "head": None}},
                        {"error_code": "private/path"}, {"error_code": "A" * 81}, {"error_code": None}):
            self.reject_wire(dict(value, **changes), "RESULT_DENIAL_SHAPE")
        self.reject_wire(dict(strict_loads(self.wire), error_code="DENIED"), "RESULT_UNEXPECTED_ERROR")


if __name__ == "__main__":
    unittest.main()
