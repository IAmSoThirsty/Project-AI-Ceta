"""Executable internal-record checks with explicitly synthetic fixture identities.

The oracles cover byte shape, exact binding, bounded types, and captured value
ownership. They do not authenticate a principal, consume a permit, dispatch an
adapter, measure actual usage, or qualify an observed physical effect. Original
ExecutionReceipt/EffectObservation source roles keep process exit and independent
observation separate; the six internal records do not extend the public codec.
"""
from dataclasses import FrozenInstanceError, fields, replace
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts.kernel_transactions import BudgetVector
from ceta.contracts.read_sets import ReadSet, ResourceRevision
from ceta.contracts.runtime_records import (
    AcceptanceIntent, AdapterManifest, ApprovalEvidence, ObservedOutcome,
    RuntimeAdmission, RuntimeBasis,
)
from ceta.contracts.temporal import ClockSample, Deadline
from ceta.contracts.wire import ContractError, RecordCodec, canonical_bytes, strict_loads

PROFILE = "ceta-production-internal-records-v1"
LIMIT = 2**53 - 1
SCHEMA_SHA256 = "f83f8a1116492266aa9ffbbf85c4e4677218e99d8771f0de61a3affef8313f79"
RECORD_FIELDS = {
    RuntimeBasis: {"scope_id", "task_id", "principal_id", "actor_session_id",
                   "task_revision", "objective_commitment", "candidate_commitment",
                   "expected_store_revision", "read_set", "deadline"},
    AcceptanceIntent: {"intent_id", "basis", "raw_input_commitment", "meaning_commitment",
                       "proposal_commitment", "expected_draft_revision"},
    ApprovalEvidence: {"evidence_id", "intent_commitment", "scope_id", "task_id", "principal_id",
                       "actor_session_id", "display_commitment", "decision_reference",
                       "decision_commitment", "decision", "observed_clock", "deadline"},
    RuntimeAdmission: {"admission_id", "basis", "permit_id", "consumed_permit_commitment",
                       "prepared_request_commitment", "runtime_lease_id", "runtime_commitment",
                       "worker_session_id", "reserved_budget"},
    AdapterManifest: {"adapter_id", "adapter_version", "operation_ids", "operation_catalog_commitment",
                      "schema_commitment", "executable_commitment", "configuration_commitment",
                      "maximum_request_bytes", "maximum_response_bytes"},
    ObservedOutcome: {"outcome_id", "admission_commitment", "execution_receipt_commitment", "observer_id",
                      "observer_session_id", "execution_state", "effect_state",
                      "observed_resource_commitments", "evidence_commitments", "actual_usage"},
}


def h(label):
    """A deterministic test-data commitment, never a real authority reference."""
    return "sha256:" + hashlib.sha256(("SYNTHETIC_RUNTIME_TEST_ONLY:" + label).encode()).hexdigest()


def encoded(value, *, ascii=False):
    """Independent exact JSON encoder; malformed-value tests bypass canonical_bytes."""
    return json.dumps(value, ensure_ascii=ascii, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


class RuntimeRecordTests(unittest.TestCase):
    def setUp(self):
        self.clock = ClockSample("boot:test-only", 2, 3, 110, 1100, 1, True)
        self.deadline = Deadline("boot:test-only", 2, 3, 100, 200, 1000, 2000)
        self.read_set = ReadSet("project:test-only", 4, 5, h("policy"), h("environment"), (
            ResourceRevision("artifact:a", h("input")), ResourceRevision("file:z", h("target"))))
        self.basis = RuntimeBasis("project:test-only", "task:test-only", "principal:test-only",
                                  "session:test-only", h("task"), h("objective"), h("candidate"),
                                  None, self.read_set, self.deadline)
        self.intent = AcceptanceIntent("intent:test-only", self.basis, h("raw"), h("meaning"),
                                       h("proposal"), 7)
        self.approval = ApprovalEvidence("approval:test-only", self.intent.commitment(), self.basis.scope_id,
                                        self.basis.task_id, self.basis.principal_id, self.basis.actor_session_id,
                                        h("display"), "decision:test-only", h("decision"), "APPROVED",
                                        self.clock, self.deadline)
        self.budget = BudgetVector((1000, 2, 1, 10, 20, 30, 40))
        self.admission = RuntimeAdmission("admission:test-only", self.basis, "permit:test-only",
                                          h("consumed"), h("prepared"), "lease:test-only", h("runtime"),
                                          "worker:test-only", self.budget)
        self.adapter = AdapterManifest("adapter:test-only", "v1", ("operation:read", "operation:write"),
                                       h("catalog"), h("schema"), h("executable"), h("configuration"),
                                       1024, 2048)
        self.outcome = ObservedOutcome("outcome:test-only", self.admission.commitment(), h("execution"),
                                      "observer:test-only", "observer-session:test-only", "SUCCEEDED",
                                      "NOT_OBSERVED", (), (), None)
        self.records = (self.basis, self.intent, self.approval, self.admission, self.adapter, self.outcome)

    def rejected(self, fn, *args, code=None, **kwargs):
        with self.assertRaises(ContractError) as raised:
            fn(*args, **kwargs)
        if code is not None:
            self.assertEqual(raised.exception.code, code)
        return raised.exception

    def doc(self, record):
        return json.loads(record.canonical_wire())

    def test_all_six_records_round_trip_with_independent_canonical_preimage(self):
        for record in self.records:
            with self.subTest(record=type(record).__name__):
                wire = record.canonical_wire()
                document = self.doc(record)
                self.assertEqual(set(document), {"profile", "record_type", "record_version", "value"})
                self.assertEqual(document["profile"], PROFILE)
                self.assertEqual(document["record_type"], type(record).__name__)
                self.assertEqual(document["record_version"], "1")
                self.assertEqual(set(document["value"]), RECORD_FIELDS[type(record)])
                self.assertEqual(wire, encoded(document))
                restored = type(record).from_wire(wire)
                self.assertIs(type(restored), type(record))
                self.assertEqual(restored, record)
                self.assertEqual(restored.canonical_wire(), wire)

    def test_commitments_bind_exact_wire_and_record_specific_domain(self):
        commitments = set()
        for record in self.records:
            with self.subTest(record=type(record).__name__):
                domain = ("CETA:ceta-production-internal-records-v1:" + type(record).__name__ + "\0").encode("ascii")
                expected = "sha256:" + hashlib.sha256(domain + record.canonical_wire()).hexdigest()
                self.assertEqual(record.commitment(), expected)
                self.assertNotEqual(expected, "sha256:" + hashlib.sha256(record.canonical_wire()).hexdigest())
                commitments.add(expected)
        self.assertEqual(len(commitments), 6)

    def test_internal_records_do_not_extend_original_twenty_record_ipc_schema(self):
        wire = (ROOT / "contracts/schemas/records.schema.json").read_bytes()
        self.assertEqual(hashlib.sha256(wire).hexdigest(), SCHEMA_SHA256)
        schema = strict_loads(wire)
        self.assertEqual(len(schema["$defs"]), 20)
        self.assertTrue({kind.__name__ for kind in RECORD_FIELDS}.isdisjoint(schema["$defs"]))
        codec = RecordCodec(schema)
        for record in self.records:
            with self.subTest(record=type(record).__name__):
                self.rejected(codec.decode, record.canonical_wire(), code="UNKNOWN_RECORD_TYPE")

    def test_each_root_and_record_field_is_required_and_unknown_fields_reject(self):
        for record in self.records:
            for key in ("profile", "record_type", "record_version", "value"):
                document = self.doc(record)
                del document[key]
                with self.subTest(record=type(record).__name__, missing=key):
                    self.rejected(type(record).from_wire, encoded(document))
            for key in RECORD_FIELDS[type(record)]:
                document = self.doc(record)
                del document["value"][key]
                with self.subTest(record=type(record).__name__, missing_value=key):
                    self.rejected(type(record).from_wire, encoded(document))
            for place in ("root", "value"):
                document = self.doc(record)
                (document if place == "root" else document["value"])["caller_approved"] = True
                with self.subTest(record=type(record).__name__, extra=place):
                    self.rejected(type(record).from_wire, encoded(document))

    def test_versions_profile_and_cross_record_dispatch_cannot_be_substituted(self):
        for record in self.records:
            for key, values in (("profile", ("other", None, True, 1)),
                                ("record_version", ("2", 1, True, None)),
                                ("record_type", ("OtherRecord", 1, True, None))):
                for value in values:
                    document = self.doc(record)
                    document[key] = value
                    with self.subTest(record=type(record).__name__, key=key, value=value):
                        self.rejected(type(record).from_wire, encoded(document))
            for other in self.records:
                if type(other) is not type(record):
                    self.rejected(type(record).from_wire, other.canonical_wire())

    def test_noncanonical_valid_json_has_no_internal_record_identity(self):
        for record in self.records:
            document = self.doc(record)
            for wire in (json.dumps(document, indent=2).encode(), record.canonical_wire() + b"\n",
                         b" " + record.canonical_wire(),
                         json.dumps(dict(reversed(tuple(document.items()))), separators=(",", ":")).encode()):
                with self.subTest(record=type(record).__name__, wire=wire[:40]):
                    self.rejected(type(record).from_wire, wire, code="RUNTIME_RECORD_NONCANONICAL")

    def test_duplicate_keys_root_and_nested_are_rejected_before_dispatch(self):
        root = self.basis.canonical_wire().replace(b'{"profile":', b'{"profile":"forged","profile":', 1)
        nested = self.basis.canonical_wire().replace(b'"task_id":', b'"task_id":"forged","task_id":', 1)
        for wire in (root, nested):
            self.rejected(RuntimeBasis.from_wire, wire, code="DUPLICATE_KEY")

    def test_nonfinite_float_and_exponent_numbers_are_rejected_as_numbers(self):
        wire = self.intent.canonical_wire()
        for token in (b"NaN", b"Infinity", b"-Infinity", b"7.0", b"7e0"):
            self.rejected(AcceptanceIntent.from_wire,
                          wire.replace(b'"expected_draft_revision":7', b'"expected_draft_revision":' + token),
                          code="NON_INTEGER_NUMBER")

    def test_wire_exact_bytes_utf8_size_depth_and_top_level_shape_are_bounded(self):
        wire = self.basis.canonical_wire()
        for value in (wire.decode(), bytearray(wire), memoryview(wire), None, True):
            self.rejected(RuntimeBasis.from_wire, value, code="WIRE_MUST_BE_BYTES")
        for malformed in (b"\xff", b"\xef\xbb\xbf" + wire, wire[:-1], b"{}{}"):
            self.rejected(RuntimeBasis.from_wire, malformed)
        self.rejected(RuntimeBasis.from_wire, b" " * (1024 * 1024 + 1), code="WIRE_SIZE_LIMIT")
        self.rejected(RuntimeBasis.from_wire, b"[" * 33 + b"0" + b"]" * 33, code="DEPTH_LIMIT")
        for value in (None, [], True, "record", 1):
            self.rejected(RuntimeBasis.from_wire, encoded(value), code="RUNTIME_RECORD_SHAPE_INVALID")

    def test_unicode_non_nfc_surrogates_and_identifier_aliases_reject(self):
        for text in ("e\u0301", "\ud800", "\udfff"):
            document = self.doc(self.basis)
            document["value"]["task_id"] = text
            self.rejected(RuntimeBasis.from_wire, encoded(document, ascii=True))
        for value in ("task:é", "task:Ａ", "task:one two", " task:one", "task:one\n", "task:\x00"):
            self.rejected(replace, self.basis, task_id=value, code="STORE_IDENTIFIER_INVALID")
        # Upper/lower ASCII identifiers are distinct values, not normalized aliases.
        self.assertNotEqual(replace(self.basis, task_id="Task:One").commitment(),
                            replace(self.basis, task_id="task:one").commitment())

    def test_identifier_exact_types_and_length_bound_on_every_identity_field(self):
        names = {
            RuntimeBasis: ("scope_id", "task_id", "principal_id", "actor_session_id"),
            AcceptanceIntent: ("intent_id",),
            ApprovalEvidence: ("evidence_id", "scope_id", "task_id", "principal_id", "actor_session_id", "decision_reference"),
            RuntimeAdmission: ("admission_id", "permit_id", "runtime_lease_id", "worker_session_id"),
            AdapterManifest: ("adapter_id", "adapter_version"),
            ObservedOutcome: ("outcome_id", "observer_id", "observer_session_id"),
        }
        for record in self.records:
            for key in names[type(record)]:
                for value in (None, True, 1, [], b"id", "", "a" * 161, "../escaped?", ":bad"):
                    with self.subTest(record=type(record).__name__, key=key, value=value):
                        self.rejected(replace, record, **{key: value}, code="STORE_IDENTIFIER_INVALID")
        for length in (1, 160):
            accepted = replace(self.intent, intent_id="a" * length)
            self.assertEqual(AcceptanceIntent.from_wire(accepted.canonical_wire()), accepted)

    def test_commitment_exact_types_prefix_length_hex_and_optional_none(self):
        names = {
            RuntimeBasis: ("task_revision", "objective_commitment", "candidate_commitment", "expected_store_revision"),
            AcceptanceIntent: ("raw_input_commitment", "meaning_commitment", "proposal_commitment"),
            ApprovalEvidence: ("intent_commitment", "display_commitment", "decision_commitment"),
            RuntimeAdmission: ("consumed_permit_commitment", "prepared_request_commitment", "runtime_commitment"),
            AdapterManifest: ("operation_catalog_commitment", "schema_commitment", "executable_commitment", "configuration_commitment"),
            ObservedOutcome: ("admission_commitment", "execution_receipt_commitment"),
        }
        invalid = (True, 1, b"hash", [], "sha256:" + "a" * 63, "sha256:" + "a" * 65,
                   "sha256:" + "A" * 64, "sha256:" + "g" * 64, "SHA256:" + "a" * 64)
        for record in self.records:
            for key in names[type(record)]:
                for value in invalid:
                    with self.subTest(record=type(record).__name__, key=key, value=value):
                        self.rejected(replace, record, **{key: value}, code="STORE_COMMITMENT_INVALID")
                if key not in ("expected_store_revision", "execution_receipt_commitment"):
                    self.rejected(replace, record, **{key: None}, code="STORE_COMMITMENT_INVALID")
        self.assertIsNone(RuntimeBasis.from_wire(self.basis.canonical_wire()).expected_store_revision)
        absent = replace(self.outcome, execution_receipt_commitment=None)
        self.assertIsNone(ObservedOutcome.from_wire(absent.canonical_wire()).execution_receipt_commitment)

    def test_expected_draft_revision_safe_integer_bound_for_constructor_and_wire(self):
        for value in (0, LIMIT):
            record = replace(self.intent, expected_draft_revision=value)
            self.assertEqual(AcceptanceIntent.from_wire(record.canonical_wire()).expected_draft_revision, value)
        for value in (-1, LIMIT + 1, True, False, 7.0, "7", None):
            self.rejected(replace, self.intent, expected_draft_revision=value, code="RUNTIME_COUNTER_INVALID")
            document = self.doc(self.intent)
            document["value"]["expected_draft_revision"] = value
            self.rejected(AcceptanceIntent.from_wire, encoded(document))

    def test_read_set_scope_generation_resources_and_wire_profile_are_preserved(self):
        value = self.doc(self.basis)["value"]["read_set"]
        self.assertEqual(value["scope_id"], self.basis.scope_id)
        self.assertEqual(value["authority_generation"], 4)
        self.assertEqual(value["fence_generation"], 5)
        self.assertEqual([row["resource_id"] for row in value["resources"]], ["artifact:a", "file:z"])
        self.rejected(replace, self.basis, read_set=replace(self.read_set, scope_id="project:other"),
                      code="RUNTIME_SCOPE_MISMATCH")
        for key in ("contract_type", "contract_version", "read_set_profile", "canonicalization_profile"):
            document = self.doc(self.basis)
            document["value"]["read_set"][key] = "forged"
            self.rejected(RuntimeBasis.from_wire, encoded(document), code="RUNTIME_READ_SET_PROFILE_MISMATCH")
        for key in ("authority_generation", "fence_generation"):
            for invalid in (True, -1, LIMIT + 1):
                document = self.doc(self.basis)
                document["value"]["read_set"][key] = invalid
                self.rejected(RuntimeBasis.from_wire, encoded(document))
        document = self.doc(self.basis)
        document["value"]["read_set"]["resources"].reverse()
        self.rejected(RuntimeBasis.from_wire, encoded(document), code="RUNTIME_READ_SET_PROFILE_MISMATCH")

    def test_nested_shapes_missing_unknown_null_and_duplicate_resources_reject(self):
        for record, path in ((self.basis, ("read_set",)), (self.basis, ("deadline",)),
                             (self.intent, ("basis",)), (self.approval, ("observed_clock",)),
                             (self.admission, ("reserved_budget",))):
            document = self.doc(record)
            nested = document["value"][path[0]]
            for key in tuple(nested):
                changed = self.doc(record)
                del changed["value"][path[0]][key]
                self.rejected(type(record).from_wire, encoded(changed))
            document["value"][path[0]]["authority_override"] = True
            self.rejected(type(record).from_wire, encoded(document))
            document = self.doc(record)
            document["value"][path[0]] = None
            self.rejected(type(record).from_wire, encoded(document))
        document = self.doc(self.basis)
        row = document["value"]["read_set"]["resources"][0]
        for malformed in ({"resource_id": row["resource_id"]}, {**row, "allow": True}, None, True):
            document = self.doc(self.basis)
            document["value"]["read_set"]["resources"][0] = malformed
            self.rejected(RuntimeBasis.from_wire, encoded(document))
        for rows in ([], [row, row], None, {}):
            document = self.doc(self.basis)
            document["value"]["read_set"]["resources"] = rows
            self.rejected(RuntimeBasis.from_wire, encoded(document))

    def test_read_set_resource_count_and_safe_generation_bound_are_enforced_after_capture(self):
        for count in (1, 4096):
            resources = tuple(ResourceRevision(f"resource:{n:04d}", h(f"resource:{n}")) for n in range(count))
            captured = replace(self.basis, read_set=replace(self.read_set, resources=resources))
            restored = RuntimeBasis.from_wire(captured.canonical_wire())
            self.assertEqual(len(restored.read_set.resources), count)
            self.assertEqual(restored.canonical_wire(), captured.canonical_wire())
        for generation in (0, LIMIT):
            captured = replace(self.basis, read_set=replace(self.read_set,
                               authority_generation=generation, fence_generation=generation))
            restored = RuntimeBasis.from_wire(captured.canonical_wire())
            self.assertEqual((restored.read_set.authority_generation, restored.read_set.fence_generation),
                             (generation, generation))
        for resources in ((), (self.read_set.resources[0],) * 4097):
            forged = object.__new__(ReadSet)
            for field in fields(ReadSet):
                object.__setattr__(forged, field.name, getattr(self.read_set, field.name))
            object.__setattr__(forged, "resources", resources)
            self.rejected(replace, self.basis, read_set=forged, code="RUNTIME_RESOURCE_SET_INVALID")

    def test_deadline_and_clock_integer_trust_and_interval_bounds_reject(self):
        for key in ("durable_epoch", "resume_generation", "issued_monotonic_ns", "expires_monotonic_ns"):
            for value in (True, -1, 2**63):
                document = self.doc(self.basis)
                document["value"]["deadline"][key] = value
                self.rejected(RuntimeBasis.from_wire, encoded(document))
        for key in ("expires_monotonic_ns", "expires_wall_ns"):
            document = self.doc(self.basis)
            document["value"]["deadline"][key] = 0
            self.rejected(RuntimeBasis.from_wire, encoded(document), code="INVALID_DEADLINE_INTERVAL")
        for value in (0, 1, "true", None):
            document = self.doc(self.approval)
            document["value"]["observed_clock"]["wall_trusted"] = value
            self.rejected(ApprovalEvidence.from_wire, encoded(document), code="INVALID_TIME_TRUST_FLAG")
        for key in ("monotonic_ns", "uncertainty_ns", "durable_epoch", "resume_generation"):
            document = self.doc(self.approval)
            document["value"]["observed_clock"][key] = True
            self.rejected(ApprovalEvidence.from_wire, encoded(document), code="INVALID_TEMPORAL_INTEGER")

    def test_budget_exact_seven_fields_safe_integer_bounds_and_optional_actual_usage(self):
        names = ("wall_time_ms", "max_model_calls", "max_effects", "max_input_tokens",
                 "max_output_tokens", "max_bytes_read", "max_bytes_written")
        self.assertEqual(set(self.doc(self.admission)["value"]["reserved_budget"]), set(names))
        for value in (0, LIMIT):
            vector = BudgetVector((value,) * 7)
            record = replace(self.admission, reserved_budget=vector)
            self.assertEqual(RuntimeAdmission.from_wire(record.canonical_wire()).reserved_budget, vector)
        for key in names:
            for invalid in (True, -1, LIMIT + 1, 1.0, "1", None):
                document = self.doc(self.admission)
                document["value"]["reserved_budget"][key] = invalid
                self.rejected(RuntimeAdmission.from_wire, encoded(document))
        for value in (None, [], {}, self.budget.as_dict()):
            self.rejected(replace, self.admission, reserved_budget=value)
        measured_fixture = replace(self.outcome, actual_usage=self.budget)
        self.assertEqual(ObservedOutcome.from_wire(measured_fixture.canonical_wire()).actual_usage, self.budget)
        self.assertIsNone(ObservedOutcome.from_wire(self.outcome.canonical_wire()).actual_usage)

    def test_frozen_public_fields_and_nested_records_are_owned_copies(self):
        for record in self.records:
            with self.subTest(record=type(record).__name__):
                with self.assertRaises(FrozenInstanceError):
                    setattr(record, fields(record)[0].name, "changed")
        self.assertIsNot(self.basis.read_set, self.read_set)
        self.assertIsNot(self.basis.read_set.resources[0], self.read_set.resources[0])
        self.assertIsNot(self.basis.deadline, self.deadline)
        self.assertIsNot(self.intent.basis, self.basis)
        self.assertIsNot(self.intent.basis.read_set, self.basis.read_set)
        self.assertIsNot(self.approval.observed_clock, self.clock)
        self.assertIsNot(self.approval.deadline, self.deadline)
        self.assertIsNot(self.admission.reserved_budget, self.budget)
        copy = replace(self.outcome, actual_usage=self.budget)
        self.assertIsNot(copy.actual_usage, self.budget)

    def test_mutating_supplied_nested_instances_cannot_change_captured_wire(self):
        before = {type(record): record.canonical_wire() for record in self.records}
        object.__setattr__(self.read_set.resources[0], "revision", h("mutated-input"))
        object.__setattr__(self.deadline, "expires_monotonic_ns", 999)
        object.__setattr__(self.clock, "monotonic_ns", 999)
        object.__setattr__(self.budget, "values", (0,) * 7)
        for record in self.records:
            self.assertEqual(record.canonical_wire(), before[type(record)])
        # Basis supplied to other records has already been captured independently.
        object.__setattr__(self.basis, "task_id", "task:mutated")
        self.assertEqual(self.intent.canonical_wire(), before[AcceptanceIntent])
        self.assertEqual(self.admission.canonical_wire(), before[RuntimeAdmission])

    def test_corrupt_owned_nested_instances_fail_when_encoded_or_consumed(self):
        for name, record, mutate in (
            ("read-set", self.basis, lambda: object.__setattr__(self.basis.read_set, "authority_generation", True)),
            ("deadline", self.intent, lambda: object.__setattr__(self.intent.basis.deadline, "expires_monotonic_ns", True)),
            ("clock", self.approval, lambda: object.__setattr__(self.approval.observed_clock, "wall_trusted", 1)),
            ("budget", self.admission, lambda: object.__setattr__(self.admission.reserved_budget, "values", (True,) * 7)),
        ):
            with self.subTest(nested=name):
                mutate()
                self.rejected(record.canonical_wire)
                self.rejected(record.commitment)

    def test_incomplete_top_level_and_nested_dataclasses_reject_with_contract_error(self):
        for kind in RECORD_FIELDS:
            forged = object.__new__(kind)
            with self.subTest(record=kind.__name__):
                self.rejected(forged.canonical_wire)
                self.rejected(forged.commitment)
        for kind, fn, key in ((ReadSet, replace, "read_set"), (Deadline, replace, "deadline")):
            self.rejected(fn, self.basis, **{key: object.__new__(kind)})
        for kind, record, key in ((RuntimeBasis, self.intent, "basis"),
                                  (ClockSample, self.approval, "observed_clock"),
                                  (BudgetVector, self.admission, "reserved_budget")):
            self.rejected(replace, record, **{key: object.__new__(kind)})
        forged_set = object.__new__(ReadSet)
        for field in fields(ReadSet):
            object.__setattr__(forged_set, field.name, getattr(self.read_set, field.name))
        object.__setattr__(forged_set, "resources", (object.__new__(ResourceRevision),))
        self.rejected(replace, self.basis, read_set=forged_set)
        self.rejected(object.__new__(ApprovalEvidence).require_intent, self.intent, displayed_commitment=h("display"))
        self.rejected(object.__new__(AdapterManifest).require_operation, "operation:read", catalog_commitment=h("catalog"))
        self.rejected(object.__new__(ObservedOutcome).require_admission, self.admission)

    def test_exact_record_types_subclasses_and_dict_substitutes_reject(self):
        class BasisSubclass(RuntimeBasis):
            pass
        derived = BasisSubclass(**{field.name: getattr(self.basis, field.name) for field in fields(RuntimeBasis)})
        for value in (derived, self.doc(self.basis)["value"], None, True):
            self.rejected(replace, self.intent, basis=value, code="RUNTIME_RECORD_TYPE_REQUIRED")
            self.rejected(replace, self.admission, basis=value, code="RUNTIME_RECORD_TYPE_REQUIRED")
        self.rejected(derived.canonical_wire, code="RUNTIME_RECORD_TYPE_REQUIRED")
        self.rejected(BasisSubclass.from_wire, self.basis.canonical_wire(), code="RUNTIME_RECORD_TYPE_REQUIRED")
        for value in (self.budget.as_dict(), (), True):
            self.rejected(replace, self.outcome, actual_usage=value, code="RUNTIME_RECORD_TYPE_REQUIRED")

    def test_approval_exact_intent_and_display_bindings_reject_substitution(self):
        self.assertIsNone(self.approval.require_intent(self.intent, displayed_commitment=h("display")))
        self.rejected(self.approval.require_intent, self.intent, displayed_commitment=h("other-display"),
                      code="RUNTIME_APPROVAL_BINDING_MISMATCH")
        for key, value in (("intent_id", "intent:other"), ("raw_input_commitment", h("other-raw")),
                           ("meaning_commitment", h("other-meaning")), ("proposal_commitment", h("other-proposal")),
                           ("expected_draft_revision", 8),
                           ("basis", replace(self.basis, candidate_commitment=h("other-candidate"))),
                           ("basis", replace(self.basis, task_revision=h("other-task-revision"))),
                           ("basis", replace(self.basis, read_set=replace(self.read_set, fence_generation=6)))):
            with self.subTest(changed=key, value=value):
                altered = replace(self.intent, **{key: value})
                self.assertNotEqual(altered.commitment(), self.intent.commitment())
                self.rejected(self.approval.require_intent, altered, displayed_commitment=h("display"),
                              code="RUNTIME_APPROVAL_BINDING_MISMATCH")

    def test_approval_scope_task_principal_session_and_deadline_are_exact(self):
        for key in ("scope_id", "task_id", "principal_id", "actor_session_id"):
            self.rejected(replace(self.approval, **{key: "id:other"}).require_intent,
                          self.intent, displayed_commitment=h("display"), code="RUNTIME_APPROVAL_IDENTITY_MISMATCH")
        changed = replace(self.approval, deadline=replace(self.deadline, expires_monotonic_ns=201))
        self.rejected(changed.require_intent, self.intent, displayed_commitment=h("display"),
                      code="RUNTIME_APPROVAL_DEADLINE_MISMATCH")
        for key, value in (("boot_id", "boot:other"), ("durable_epoch", 3), ("resume_generation", 4)):
            self.rejected(replace, self.approval, observed_clock=replace(self.clock, **{key: value}),
                          code="RUNTIME_APPROVAL_EPOCH_MISMATCH")

    def test_recorded_denial_cancellation_or_untrusted_time_do_not_turn_into_approval(self):
        for decision in ("APPROVED", "DENIED", "CANCELLED"):
            record = replace(self.approval, decision=decision)
            restored = ApprovalEvidence.from_wire(record.canonical_wire())
            self.assertEqual(restored.decision, decision)
            # This method is a binding check; it deliberately issues no permission.
            self.assertIsNone(restored.require_intent(self.intent, displayed_commitment=h("display")))
        untrusted = replace(self.approval, observed_clock=replace(self.clock, wall_trusted=False))
        self.assertFalse(ApprovalEvidence.from_wire(untrusted.canonical_wire()).observed_clock.wall_trusted)
        for invalid in ("ALLOW", "approved", "VERIFIED", True, None):
            self.rejected(replace, self.approval, decision=invalid, code="RUNTIME_APPROVAL_STATE_INVALID")

    def test_binding_consumers_revalidate_caller_mutation_and_incomplete_arguments(self):
        original_intent = self.intent.commitment()
        object.__setattr__(self.intent.basis, "candidate_commitment", h("later-candidate"))
        self.assertNotEqual(self.intent.commitment(), original_intent)
        self.rejected(self.approval.require_intent, self.intent, displayed_commitment=h("display"),
                      code="RUNTIME_APPROVAL_BINDING_MISMATCH")
        object.__setattr__(self.adapter, "maximum_request_bytes", True)
        self.rejected(self.adapter.require_operation, "operation:read", catalog_commitment=h("catalog"))
        object.__setattr__(self.admission.reserved_budget, "values", (True,) * 7)
        self.rejected(self.outcome.require_admission, self.admission)
        self.rejected(self.approval.require_intent, object.__new__(AcceptanceIntent), displayed_commitment=h("display"))
        self.rejected(self.outcome.require_admission, object.__new__(RuntimeAdmission))

    def test_adapter_operation_names_uniqueness_count_and_wire_byte_limits(self):
        for operations in ((), [], ("operation:a",) * 2, (True,), ("bad operation",),
                           tuple(f"operation:{n}" for n in range(257))):
            self.rejected(replace, self.adapter, operation_ids=operations)
        for count in (1, 256):
            record = replace(self.adapter, operation_ids=tuple(f"operation:{n}" for n in range(count)))
            self.assertEqual(AdapterManifest.from_wire(record.canonical_wire()).operation_ids, record.operation_ids)
        for key in ("maximum_request_bytes", "maximum_response_bytes"):
            for value in (1, 1024 * 1024):
                record = replace(self.adapter, **{key: value})
                self.assertEqual(getattr(AdapterManifest.from_wire(record.canonical_wire()), key), value)
            for invalid in (0, -1, 1024 * 1024 + 1, True, 1.0, "1", None):
                self.rejected(replace, self.adapter, **{key: invalid}, code="RUNTIME_ADAPTER_WIRE_BOUND_INVALID")

    def test_adapter_requires_exact_catalog_and_declared_operation(self):
        for operation in self.adapter.operation_ids:
            self.assertIsNone(self.adapter.require_operation(operation, catalog_commitment=h("catalog")))
        self.rejected(self.adapter.require_operation, "operation:read", catalog_commitment=h("changed-catalog"),
                      code="RUNTIME_OPERATION_CATALOG_CHANGED")
        self.rejected(self.adapter.require_operation, "operation:undeclared", catalog_commitment=h("catalog"),
                      code="RUNTIME_ADAPTER_OPERATION_UNDECLARED")
        self.rejected(self.adapter.require_operation, True, catalog_commitment=h("catalog"))
        self.rejected(self.adapter.require_operation, "operation:read", catalog_commitment=True)
        for key in ("operation_catalog_commitment", "schema_commitment", "executable_commitment", "configuration_commitment"):
            self.assertNotEqual(replace(self.adapter, **{key: h("changed:" + key)}).commitment(), self.adapter.commitment())

    def test_all_declared_execution_and_effect_states_stay_independent(self):
        execution_states = ("NOT_STARTED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED",
                            "TIMED_OUT", "INTERRUPTED", "INDETERMINATE")
        effect_states = ("NOT_OBSERVED", "NO_EFFECT", "EXPECTED_EFFECT", "UNEXPECTED_EFFECT",
                         "PARTIAL_EFFECT", "INDETERMINATE")
        for execution in execution_states:
            for effect in effect_states:
                observed = effect not in ("NOT_OBSERVED", "INDETERMINATE")
                record = replace(self.outcome, execution_state=execution, effect_state=effect,
                                 observed_resource_commitments=(h("observed"),) if observed else (),
                                 evidence_commitments=(h("observation-evidence"),) if observed else ())
                restored = ObservedOutcome.from_wire(record.canonical_wire())
                self.assertEqual((restored.execution_state, restored.effect_state), (execution, effect))
                self.assertIsNone(restored.require_admission(self.admission))
        for key, code in (("execution_state", "RUNTIME_EXECUTION_STATE_INVALID"),
                          ("effect_state", "RUNTIME_EFFECT_STATE_INVALID")):
            for invalid in ("PASS", "SUCCESS", "VERIFIED", "succeeded", True, 1, None):
                self.rejected(replace, self.outcome, **{key: invalid}, code=code)

    def test_process_success_and_receipt_reference_never_imply_observed_effect(self):
        restored = ObservedOutcome.from_wire(self.outcome.canonical_wire())
        self.assertEqual(restored.execution_state, "SUCCEEDED")
        self.assertEqual(restored.execution_receipt_commitment, h("execution"))
        self.assertEqual(restored.effect_state, "NOT_OBSERVED")
        self.assertEqual(restored.observed_resource_commitments, ())
        self.assertEqual(restored.evidence_commitments, ())
        self.assertIsNone(restored.actual_usage)
        # Even a NO_EFFECT assertion requires independently supplied observation bindings.
        for effect in ("NO_EFFECT", "EXPECTED_EFFECT", "UNEXPECTED_EFFECT", "PARTIAL_EFFECT"):
            self.rejected(replace, restored, effect_state=effect, code="RUNTIME_REFERENCES_INVALID")
            self.rejected(replace, restored, effect_state=effect, observed_resource_commitments=(h("observed"),),
                          code="RUNTIME_REFERENCES_INVALID")
            self.rejected(replace, restored, effect_state=effect, evidence_commitments=(h("evidence"),),
                          code="RUNTIME_REFERENCES_INVALID")

    def test_observation_reference_exact_tuple_uniqueness_and_bound(self):
        for key in ("observed_resource_commitments", "evidence_commitments"):
            for invalid in ([], None, True, (True,), (h("same"), h("same"))):
                self.rejected(replace, self.outcome, **{key: invalid})
            boundary = tuple(h(f"reference:{n}") for n in range(4096))
            record = replace(self.outcome, **{key: boundary})
            self.assertEqual(getattr(ObservedOutcome.from_wire(record.canonical_wire()), key), boundary)
            self.rejected(replace, self.outcome, **{key: boundary + (h("overflow"),)},
                          code="RUNTIME_REFERENCES_INVALID")
        for key in ("operation_ids", "observed_resource_commitments", "evidence_commitments"):
            record = self.adapter if key == "operation_ids" else self.outcome
            for invalid in ({}, None, "reference", True):
                document = self.doc(record)
                document["value"][key] = invalid
                self.rejected(type(record).from_wire, encoded(document), code="RUNTIME_SEQUENCE_INVALID")

    def test_outcome_exact_admission_includes_basis_permit_runtime_worker_and_budget(self):
        self.assertIsNone(self.outcome.require_admission(self.admission))
        changes = {
            "admission_id": "admission:other", "permit_id": "permit:other",
            "consumed_permit_commitment": h("other-consumption"),
            "prepared_request_commitment": h("other-prepared"), "runtime_lease_id": "lease:other",
            "runtime_commitment": h("other-runtime"), "worker_session_id": "worker:other",
            "reserved_budget": BudgetVector((1001, 2, 1, 10, 20, 30, 40)),
            "basis": replace(self.basis, objective_commitment=h("other-objective")),
        }
        for key, value in changes.items():
            with self.subTest(changed=key):
                changed = replace(self.admission, **{key: value})
                self.assertNotEqual(changed.commitment(), self.admission.commitment())
                self.rejected(self.outcome.require_admission, changed, code="RUNTIME_OUTCOME_ADMISSION_MISMATCH")
        self.rejected(self.outcome.require_admission, self.doc(self.admission), code="RUNTIME_RECORD_TYPE_REQUIRED")


if __name__ == "__main__":
    unittest.main()
