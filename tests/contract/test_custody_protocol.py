"""Independent public transcript comparisons; all owner inputs are synthetic.

No cryptographic proof, consent, key release, quorum, physical effect or current
authority is established by these fixtures. The assertions independently bind
the existing schema fields, exact bytes and temporal boundaries.
"""
from copy import deepcopy
from dataclasses import fields, replace
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts.custody_protocol import (
    CUSTODY_BINDING_PROFILE, MATERIAL_FIELDS, REQUIRED_OWNER_VERIFICATIONS,
    CanonicalProtectedTranscript, CustodyMaterialExpectation, ProtectedContributionBinding,
    ProtectedExecutionBinding, ProtectedObjectBinding, ProtectedOperationContext,
    ProtectedRequestBinding, ResolvedCustodyMaterial,
)
from ceta.contracts.temporal import ClockSample, Deadline, utc_nanoseconds
from ceta.contracts.wire import ContractError, PROFILE, RecordCodec
from test_all_records import example

SOURCE_SHA = "2e4a40449f655d38612c326e55b713cb11c04f64d950488a2a036ed4b543d4f9"
SCHEMA_SHA = "f83f8a1116492266aa9ffbbf85c4e4677218e99d8771f0de61a3affef8313f79"
ISSUED = "2026-10-11T18:00:00.000000001Z"
NOW = "2026-10-11T18:00:01Z"
EXPIRES = "2026-10-11T18:01:00Z"


def wire(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def h(value):
    return "sha256:" + hashlib.sha256(value.encode()).hexdigest()


class ProtectedTranscriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (ROOT / "src/ceta/contracts/custody_protocol.py").read_bytes()
        schema = (ROOT / "contracts/schemas/records.schema.json").read_bytes()
        if hashlib.sha256(source).hexdigest() != SOURCE_SHA or hashlib.sha256(schema).hexdigest() != SCHEMA_SHA:
            raise AssertionError("Frozen protected-transcript source/schema cut changed")
        cls.schema = json.loads(schema)

    def setUp(self):
        self.codec = RecordCodec(deepcopy(self.schema))
        value = example(self.schema["$defs"]["ProtectedOperationRequest"])
        value.update(record_id="request:synthetic", scope_id="scope:synthetic", object_id="object:synthetic",
            object_key_lineage_ref="lineage:synthetic", consumer_id="consumer:synthetic", nonce="nonce:synthetic",
            issued_at=ISSUED, expires_at=EXPIRES, epoch=7)
        self.document = value
        self.transcript = CanonicalProtectedTranscript(self.codec, wire(value))
        self.binding = self.transcript.binding
        self.materials = tuple(ResolvedCustodyMaterial(name, value["scope_id"], value[name],
            ("SYNTHETIC_PUBLIC_MATERIAL:" + name).encode()) for name in MATERIAL_FIELDS)
        ns = utc_nanoseconds(NOW)
        self.previous = ClockSample("boot:synthetic", 3, 4, 100, ns - 100, 0, True)
        self.current = ClockSample("boot:synthetic", 3, 4, 200, ns, 0, True)
        self.deadline = Deadline("boot:synthetic", 3, 4, 100, 10000,
            utc_nanoseconds(ISSUED), utc_nanoseconds(EXPIRES))
        self.context = ProtectedOperationContext(self.binding, tuple(item.expectation() for item in self.materials),
            self.previous, self.current, self.deadline, (), ())

    def reject(self, function, *args, code=None, **kwargs):
        with self.assertRaises(ContractError) as caught:
            function(*args, **kwargs)
        if code is not None:
            self.assertEqual(caught.exception.code, code)
        return caught.exception

    def changed(self, **updates):
        return CanonicalProtectedTranscript(self.codec, wire({**self.document, **updates}))

    def test_exact_existing_twenty_record_schema_and_all_twenty_nine_request_fields_round_trip(self):
        self.assertEqual(len(self.schema["$defs"]), 20)
        self.assertEqual(len(self.document), 29)
        self.assertEqual(set(self.binding.as_record()), set(self.schema["$defs"]["ProtectedOperationRequest"]["required"]))
        self.assertEqual(self.binding.as_record(), self.document)
        self.assertEqual(self.transcript.to_wire(), wire(self.document))
        self.assertEqual(CanonicalProtectedTranscript.from_binding(self.codec, self.binding), self.transcript)
        self.assertEqual(ProtectedRequestBinding.from_record(self.document), self.binding)

    def test_original_wire_is_preserved_while_canonical_transcript_domain_is_exact(self):
        original = json.dumps(self.document, ensure_ascii=True, indent=2).encode()
        selected = CanonicalProtectedTranscript.from_wire(self.codec, original)
        self.assertEqual(selected.to_wire(), original)
        self.assertEqual(selected.to_wire(preserve_original=False), wire(self.document))
        domain = ("CETA:protected-operation-transcript:" + PROFILE + ":v1\0").encode()
        self.assertEqual(selected.preimage(), domain + wire(self.document))
        self.assertEqual(selected.commitment(), "sha256:" + hashlib.sha256(domain + wire(self.document)).hexdigest())
        self.assertEqual(selected.commitment(), self.transcript.commitment())
        self.assertNotEqual(selected.original_sha256, self.transcript.original_sha256)
        self.assertNotEqual(selected.record_commitment, selected.commitment())
        self.reject(selected.to_wire, preserve_original=1)

    def test_fresh_request_changes_request_commitment_without_rekeying_stable_object(self):
        newer = self.changed(record_id="request:new", nonce="nonce:new", capability_ref="capability:new",
            issued_at=NOW, expires_at="2026-10-11T18:02:00Z")
        self.assertEqual(newer.require_same_object(self.transcript), self.binding.object_binding)
        self.assertIsNone(newer.require_distinct_request(self.transcript))
        self.assertEqual(newer.binding.object_binding.commitment(), self.binding.object_binding.commitment())
        self.assertNotEqual(newer.commitment(), self.transcript.commitment())
        for update in ({"record_id": "request:new"}, {"nonce": "nonce:new"}, {}):
            with self.subTest(update=update):
                self.reject(self.changed(**update).require_distinct_request, self.transcript)

    def test_every_stable_object_field_changes_the_object_commitment(self):
        original = self.binding.object_binding
        for field in fields(ProtectedObjectBinding):
            name = field.name
            replacement = h("changed:" + name) if name in {"object_version", "ciphertext_commitment"} else "changed:" + name
            with self.subTest(field=name):
                candidate = self.changed(**{name: replacement})
                self.assertNotEqual(candidate.binding.object_binding.commitment(), original.commitment())
                self.reject(candidate.require_same_object, self.transcript, code="CUSTODY_STABLE_OBJECT_CHANGED")

    def test_every_request_field_is_required_and_unknown_or_duplicate_keys_are_rejected(self):
        for name in self.document:
            candidate = dict(self.document)
            del candidate[name]
            with self.subTest(missing=name):
                self.reject(CanonicalProtectedTranscript, self.codec, wire(candidate))
        self.reject(CanonicalProtectedTranscript, self.codec, wire({**self.document, "allow": True}))
        duplicate = wire(self.document)[:-1] + b',"epoch":7}'
        self.reject(CanonicalProtectedTranscript, self.codec, duplicate)
        self.reject(CanonicalProtectedTranscript, self.codec, bytearray(wire(self.document)))

    def test_caller_expectation_binds_every_variable_request_field(self):
        for name, value in self.document.items():
            if name in {"record_type", "schema_version"}:
                continue
            if name == "issued_at":
                replacement = "2026-10-11T18:00:00.000000002Z"
            elif name == "expires_at":
                replacement = "2026-10-11T18:01:01Z"
            elif name == "epoch":
                replacement = value + 1
            elif type(value) is str and value.startswith("sha256:"):
                replacement = h("different:" + name)
            else:
                replacement = "different:" + name
            with self.subTest(field=name):
                self.reject(self.changed(**{name: replacement}).verify_bindings, self.context, self.materials,
                    code="CUSTODY_CALLER_CONTEXT_REQUEST_MISMATCH")

    def test_exact_complete_material_set_is_order_independent_but_duplicates_are_not(self):
        result = self.transcript.verify_bindings(self.context, tuple(reversed(self.materials)))
        self.assertEqual(result.transcript_commitment, self.transcript.commitment())
        self.assertEqual(len(self.materials), 16)
        self.reject(self.transcript.verify_bindings, self.context, self.materials[:-1])
        self.reject(self.transcript.verify_bindings, self.context, self.materials[:-1] + (self.materials[0],))
        self.reject(ProtectedOperationContext, self.binding, self.context.material_expectations[:-1],
            self.previous, self.current, self.deadline, (), ())

    def test_each_resolved_material_raw_byte_sequence_and_scope_is_bound(self):
        for index, material in enumerate(self.materials):
            for update in ({"raw_bytes": material.raw_bytes + b"changed"}, {"scope_id": "scope:other"}):
                changed = list(self.materials)
                changed[index] = replace(material, **update)
                with self.subTest(field=material.field_name, update=tuple(update)):
                    self.reject(self.transcript.verify_bindings, self.context, tuple(changed))
        self.reject(ResolvedCustodyMaterial, "allow", self.document["scope_id"], "fixture", b"x")
        self.reject(ResolvedCustodyMaterial, MATERIAL_FIELDS[0], self.document["scope_id"],
            self.document[MATERIAL_FIELDS[0]], bytearray(b"mutable"))

    def test_expectations_require_exact_hash_length_binding_and_scope_types(self):
        original = self.context.material_expectations[0]
        for update in ({"byte_length": True}, {"byte_length": 1.0}, {"byte_length": 0},
                       {"byte_length": 16 * 1024 * 1024 + 1}, {"raw_sha256": "not-a-hash"}):
            with self.subTest(update=update):
                self.reject(replace, original, **update)
        for update in ({"scope_id": "scope:other"}, {"binding": h("wrong") if original.binding.startswith("sha256:") else "ref:wrong"},
                       {"raw_sha256": h("wrong")}, {"byte_length": original.byte_length + 1}):
            with self.subTest(update=update):
                expectations = (replace(original, **update),) + self.context.material_expectations[1:]
                try:
                    context = replace(self.context, material_expectations=expectations)
                except ContractError:
                    continue
                self.reject(self.transcript.verify_bindings, context, self.materials)

    def test_context_captures_immutable_nested_inputs_and_rechecks_forged_fields(self):
        original = self.materials[0].expectation()
        supplied = (original,) + self.context.material_expectations[1:]
        captured = replace(self.context, material_expectations=supplied)
        expected = captured.material_expectations[0]
        self.assertIsNot(expected, original)
        object.__setattr__(original, "byte_length", True)
        self.transcript.verify_bindings(captured, self.materials)
        forged = replace(self.context)
        object.__setattr__(forged, "used_nonces", [self.document["nonce"]])
        self.reject(self.transcript.verify_bindings, forged, self.materials)
        forged_material = replace(self.materials[0])
        object.__setattr__(forged_material, "raw_bytes", bytearray(b"mutable"))
        self.reject(self.transcript.verify_bindings, self.context, (forged_material,) + self.materials[1:])

    def test_request_issuance_and_expiry_use_exact_nanoseconds_and_uncertainty(self):
        issued = utc_nanoseconds(ISSUED)
        expiry = utc_nanoseconds(EXPIRES)
        for stamp, uncertainty, accepted in ((issued - 1, 0, False), (issued, 0, True),
                (issued, 1, False), (expiry - 1, 0, True), (expiry - 1, 1, False), (expiry, 0, False)):
            with self.subTest(stamp=stamp, uncertainty=uncertainty):
                previous = replace(self.previous, wall_time_ns=issued - 10)
                current = replace(self.current, wall_time_ns=stamp, uncertainty_ns=uncertainty)
                context = replace(self.context, previous_clock=previous, current_clock=current)
                if accepted:
                    self.transcript.verify_bindings(context, self.materials)
                else:
                    self.reject(self.transcript.verify_bindings, context, self.materials)

    def test_deadline_cannot_outlive_request_or_reuse_expired_monotonic_lifetime(self):
        context = replace(self.context, deadline=replace(self.deadline, expires_wall_ns=utc_nanoseconds(EXPIRES) + 1))
        self.reject(self.transcript.verify_bindings, context, self.materials, code="CUSTODY_DEADLINE_EXCEEDS_REQUEST_EXPIRY")
        context = replace(self.context, current_clock=replace(self.current, monotonic_ns=self.deadline.expires_monotonic_ns))
        self.reject(self.transcript.verify_bindings, context, self.materials)
        self.reject(self.changed, issued_at=EXPIRES)

    def test_boot_epoch_resume_trust_and_clock_rollback_are_rejected(self):
        for update in ({"boot_id": "boot:changed"}, {"durable_epoch": 4}, {"resume_generation": 5},
                       {"wall_trusted": False}, {"monotonic_ns": 99}, {"wall_time_ns": self.previous.wall_time_ns - 1}):
            with self.subTest(update=update):
                self.reject(self.transcript.verify_bindings,
                    replace(self.context, current_clock=replace(self.current, **update)), self.materials)

    def test_observed_nonce_and_request_id_replay_cannot_pass(self):
        for update in ({"used_nonces": (self.document["nonce"],)}, {"used_request_ids": (self.document["record_id"],)}):
            with self.subTest(update=update):
                self.reject(self.transcript.verify_bindings, replace(self.context, **update), self.materials,
                    code="CUSTODY_REPLAY_OBSERVED")
        self.reject(replace, self.context, used_nonces=("same", "same"))
        self.reject(replace, self.context, used_request_ids=(True,))
        self.reject(replace, self.context, used_nonces=tuple("nonce:" + str(i) for i in range(4097)))

    def test_forged_transcript_cached_values_are_revalidated_at_every_consumer(self):
        for field, value in (("canonical_wire", b"{}"), ("original_sha256", h("bad")),
                             ("record_commitment", h("bad")), ("original_wire", b"{}")):
            selected = CanonicalProtectedTranscript(self.codec, wire(self.document))
            object.__setattr__(selected, field, value)
            with self.subTest(field=field):
                self.reject(selected.commitment)
                self.reject(selected.to_wire)
                self.reject(selected.verify_bindings, self.context, self.materials)
        selected = CanonicalProtectedTranscript(self.codec, wire(self.document))
        object.__setattr__(selected.binding, "epoch", True)
        self.reject(selected.commitment)

    def test_schema_mutation_after_transcript_construction_cannot_change_captured_request(self):
        before = self.transcript.commitment()
        self.codec._schema.clear()
        self.assertEqual(self.transcript.commitment(), before)
        self.assertEqual(self.transcript.to_wire(), wire(self.document))
        self.reject(CanonicalProtectedTranscript, self.codec, wire(self.document))

    def test_contribution_uses_stable_material_binding_when_valid_clock_advances(self):
        first = self.transcript.contribution_binding(self.context, self.materials)
        advanced = replace(self.context, previous_clock=self.current,
            current_clock=replace(self.current, wall_time_ns=self.current.wall_time_ns + 1, monotonic_ns=201))
        second = self.transcript.contribution_binding(advanced, self.materials)
        self.assertEqual(first, second)
        self.assertNotEqual(self.context.commitment(), advanced.commitment())
        self.assertEqual(self.transcript.require_contribution_binding(first, advanced, self.materials), first)
        self.assertNotEqual(first.commitment(), self.transcript.commitment())
        for field in fields(ProtectedContributionBinding):
            value = getattr(first, field.name)
            changed = value + 1 if type(value) is int else h("changed") if value.startswith("sha256:") else "changed:binding"
            with self.subTest(field=field.name):
                self.reject(self.transcript.require_contribution_binding, replace(first, **{field.name: changed}),
                    self.context, self.materials)

    def receipt(self):
        expected = ProtectedExecutionBinding(self.transcript.commitment(), self.document["scope_id"],
            "task:synthetic", "operation:synthetic", "permit:synthetic", "executor:synthetic", h("input"),
            "dispatch:synthetic", "receipt:synthetic")
        value = example(self.schema["$defs"]["ExecutionReceipt"])
        value.update(scope_id=expected.scope_id, record_id=expected.receipt_id, task_id=expected.task_id,
            operation_id=expected.operation_id, permit_ref=expected.permit_id, executor_session=expected.executor_session,
            input_commitment=expected.input_commitment, dispatch_event_ref=expected.dispatch_event_ref)
        return expected, value

    def test_execution_receipt_matches_each_dispatch_binding_without_deriving_a_permit(self):
        expected, value = self.receipt()
        self.assertNotEqual(expected.permit_id, self.document["capability_ref"])
        result = self.transcript.require_execution_receipt(self.codec, wire(value), expected)
        self.assertEqual(result.as_dict(), value)
        for name in ("scope_id", "record_id", "task_id", "operation_id", "permit_ref", "executor_session",
                     "input_commitment", "dispatch_event_ref"):
            changed = h("other-input") if name == "input_commitment" else "other:reference"
            with self.subTest(field=name):
                self.reject(self.transcript.require_execution_receipt, self.codec, wire({**value, name: changed}), expected)
        self.reject(self.transcript.require_execution_receipt, self.codec, wire(value),
            replace(expected, transcript_commitment=h("other-request")))

    def test_successful_comparisons_preserve_all_outstanding_owner_obligations(self):
        result = self.transcript.verify_bindings(self.context, self.materials)
        self.assertEqual(result.required_verifications, REQUIRED_OWNER_VERIFICATIONS)
        self.assertEqual(len(result.required_verifications), 11)
        self.assertFalse(hasattr(result, "authorized"))
        self.assertFalse(hasattr(result, "allow"))
        self.reject(replace, result, required_verifications=())
        self.reject(replace, self.binding, epoch=True)
        self.reject(replace, self.binding, epoch=7.0)


if __name__ == "__main__":
    unittest.main()
