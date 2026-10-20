"""Synthetic event bindings; no live store, key or actor authentication."""
from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts import ContractError, RecordCodec, canonical_bytes, strict_loads
from ceta.contracts.events import EventContract, StreamPosition
from ceta.contracts.wire import PROFILE


class EventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.codec = RecordCodec(strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes()))
        cls.contract = EventContract(cls.codec)

    def setUp(self):
        fixture = strict_loads((ROOT / "contracts/examples/observation_shape_valid.json").read_bytes())
        self.payload_wire = canonical_bytes(fixture["instance"])
        self.payload = self.codec.decode(self.payload_wire)
        self.event = {
            "record_type": "EventRecord", "schema_version": "1", "record_id": "event:0",
            "scope_id": self.payload.as_dict()["scope_id"], "causation_ref": None,
            "sequence": 0, "event_type": "observation.accepted", "actor_id": "observer:fixture",
            "actor_session": "session:1", "recorded_at": "2026-10-06T21:00:00.123456789Z",
            "previous_head": None, "payload_ref": self.payload.record_id,
            "payload_commitment": self.payload.commitment, "canonicalization_profile": PROFILE,
            "signer_key_ref": "key:fixture:1", "signature_ref": None,
        }

    def reject(self, code, fn, *args):
        with self.assertRaises(ContractError) as raised:
            fn(*args)
        self.assertEqual(raised.exception.code, code)

    def test_preimages_have_exact_domains_and_exclude_only_future_signature(self):
        wire = json.dumps(self.event, indent=2).encode()
        result = self.contract.preimages(wire)
        body = dict(self.event)
        del body["signature_ref"]
        expected_body = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
        self.assertEqual(result.body, expected_body)
        self.assertEqual(result.head_preimage, b"CETA:event-head:ceta-json-integer-nfc-v1\0" + expected_body)
        self.assertEqual(result.signature_preimage, b"CETA:event-signature:ceta-json-integer-nfc-v1\0" + expected_body)
        self.assertEqual(result.head, "sha256:" + hashlib.sha256(result.head_preimage).hexdigest())
        self.assertNotEqual(result.head, result.record.commitment)
        self.assertNotEqual(result.head_preimage, result.signature_preimage)
        self.assertEqual(result.record.original_wire, wire)

    def test_fixed_manual_body_and_separate_sha256_oracle_vector(self):
        vector = strict_loads((ROOT / "contracts/vectors/event-preimage-v1.json").read_bytes())
        result = self.contract.preimages(canonical_bytes(vector["instance"]))
        body = vector["expected_body"].encode("utf-8")
        self.assertEqual(result.body, body)
        self.assertEqual(result.head_preimage, vector["expected_head_domain"].encode("ascii") + body)
        self.assertEqual(result.signature_preimage, vector["expected_signature_domain"].encode("ascii") + body)
        self.assertEqual(result.head, vector["expected_head"])

    def test_attaching_signature_changes_record_commitment_but_not_head_or_signing_bytes(self):
        before = self.contract.preimages(canonical_bytes(self.event))
        self.event["signature_ref"] = "signature:fixture:1"
        after = self.contract.preimages(canonical_bytes(self.event))
        self.assertEqual(before.head, after.head)
        self.assertEqual(before.signature_preimage, after.signature_preimage)
        self.assertNotEqual(before.record.commitment, after.record.commitment)

    def test_every_other_event_field_is_bound(self):
        original = self.contract.preimages(canonical_bytes(self.event))
        changes = {
            "record_id": "event:other", "scope_id": "project:other", "causation_ref": "cause:other",
            "sequence": 1, "event_type": "observation.rejected", "actor_id": "observer:other",
            "actor_session": "session:other", "recorded_at": "2026-10-06T21:00:00.123456788Z",
            "previous_head": "sha256:" + "b" * 64, "payload_ref": "observation:other",
            "payload_commitment": "sha256:" + "b" * 64, "signer_key_ref": "key:other",
        }
        for field, value in changes.items():
            changed = dict(self.event, **{field: value})
            with self.subTest(field=field):
                prepared = self.contract.preimages(canonical_bytes(changed))
                self.assertNotEqual(original.head, prepared.head)
                self.assertNotEqual(original.signature_preimage, prepared.signature_preimage)
        for field in ("schema_version", "record_type", "canonicalization_profile"):
            with self.subTest(field=field), self.assertRaises(ContractError):
                self.contract.preimages(canonical_bytes(dict(self.event, **{field: "unsupported"})))

    def test_successor_requires_exact_scope_sequence_and_accepted_prior_head(self):
        genesis = StreamPosition(self.event["scope_id"], 0, None)
        first = self.contract.require_successor(canonical_bytes(self.event), genesis)
        self.event.update(sequence=1, previous_head=first.head, record_id="event:1")
        next_position = StreamPosition(self.event["scope_id"], 1, first.head)
        self.contract.require_successor(canonical_bytes(self.event), next_position)
        for field, value, code in (
            ("scope_id", "project:other", "EVENT_SCOPE_MISMATCH"),
            ("sequence", 2, "EVENT_SEQUENCE_MISMATCH"),
            ("previous_head", "sha256:" + "b" * 64, "EVENT_PRIOR_HEAD_MISMATCH"),
        ):
            self.reject(code, self.contract.require_successor,
                        canonical_bytes(dict(self.event, **{field: value})), next_position)
        self.reject("STREAM_POSITION_REQUIRED", self.contract.require_successor,
                    canonical_bytes(self.event), {"scope_id": self.event["scope_id"]})

    def test_payload_requires_exact_record_scope_reference_and_commitment(self):
        event_wire = canonical_bytes(self.event)
        self.assertEqual(self.contract.require_payload(event_wire, self.payload_wire), self.payload)
        for field, value, code in (
            ("scope_id", "project:other", "EVENT_PAYLOAD_SCOPE_MISMATCH"),
            ("payload_ref", "observation:other", "EVENT_PAYLOAD_REFERENCE_MISMATCH"),
            ("payload_commitment", "sha256:" + "b" * 64, "EVENT_PAYLOAD_COMMITMENT_MISMATCH"),
        ):
            self.reject(code, self.contract.require_payload,
                        canonical_bytes(dict(self.event, **{field: value})), self.payload_wire)
        changed_payload = self.payload.as_dict()
        changed_payload["scope_id"] = "project:other"
        self.reject("EVENT_PAYLOAD_SCOPE_MISMATCH", self.contract.require_payload,
                    event_wire, canonical_bytes(changed_payload))

    def test_signature_requires_key_and_unsigned_event_has_no_signing_preimage(self):
        self.event.update(signer_key_ref=None, signature_ref="signature:fixture")
        self.reject("SIGNATURE_KEY_REQUIRED", self.contract.preimages, canonical_bytes(self.event))
        self.event["signature_ref"] = None
        self.assertIsNone(self.contract.preimages(canonical_bytes(self.event)).signature_preimage)

    def test_reject_wrong_record_future_hash_unknown_profile_and_duplicate_fields(self):
        self.reject("EVENT_RECORD_REQUIRED", self.contract.preimages, self.payload_wire)
        self.reject("UNSUPPORTED_EVENT_PROFILE", self.contract.preimages,
                    canonical_bytes(dict(self.event, canonicalization_profile="future-profile")))
        self.reject("UNKNOWN_FIELD", self.contract.preimages,
                    canonical_bytes(dict(self.event, final_hash="sha256:" + "a" * 64)))
        wire = canonical_bytes(self.event)
        self.reject("DUPLICATE_KEY", self.contract.preimages, b'{"sequence":1,' + wire[1:])

    def test_position_rejects_invalid_or_ambiguous_genesis_and_exact_integer_types(self):
        for args in (("scope", True, None), ("scope", -1, None), ("scope", 2**53, None),
                     ("scope", 0, "sha256:" + "a" * 64), ("scope", 1, None),
                     ([], 0, None), ("scope", 1, [])):
            with self.subTest(args=args), self.assertRaises(ContractError):
                StreamPosition(*args)

    def test_preimages_are_immutable_and_payload_reordering_preserves_commitment(self):
        result = self.contract.preimages(canonical_bytes(self.event))
        with self.assertRaises(FrozenInstanceError):
            result.head = "forged"
        payload_wire = json.dumps(self.payload.as_dict(), indent=4).encode()
        checked = self.contract.require_payload(canonical_bytes(self.event), payload_wire)
        self.assertEqual(checked.commitment, self.payload.commitment)
        self.assertNotEqual(checked.original_sha256, self.payload.original_sha256)


if __name__ == "__main__":
    unittest.main()
