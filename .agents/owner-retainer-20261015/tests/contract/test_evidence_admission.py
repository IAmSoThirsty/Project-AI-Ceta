"""Finding 5 pure bindings; no authentication, effects or qualification fixture."""
from dataclasses import FrozenInstanceError, replace
import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts.evidence_admission import (
    ConsumptionEvidence, EvidenceAdmissionChecks, PreparationEvidence,
    QualificationEvidence,
)
from ceta.contracts.events import StreamPosition
from ceta.contracts.read_sets import ReadSet, ResourceRevision, require_current_preparation
from ceta.contracts.wire import ContractError, PROFILE, RecordCodec, canonical_bytes, strict_loads
from test_all_records import example

H1, H2, H3 = ("sha256:" + c * 64 for c in "abc")


class EvidenceAdmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes())
        cls.codec = RecordCodec(cls.schema)

    def record(self, name, **changes):
        value = example(self.schema["$defs"][name])
        value.update(changes)
        return value

    def wire(self, value):
        return canonical_bytes(value)

    def reject(self, code, fn, *args):
        with self.assertRaises(ContractError) as caught:
            fn(*args)
        self.assertEqual(caught.exception.code, code)

    def setUp(self):
        self.permit = self.record("OperationPermit", record_id="permit:1", scope_id="project:1",
                                  status="CONSUMED", consume_event_ref="event:consume:1")
        consumed_wire = self.wire(self.permit)
        self.event = self.record(
            "EventRecord", record_id="event:consume:1", scope_id="project:1", sequence=5,
            previous_head=H1, payload_ref="permit:1",
            payload_commitment=self.codec.decode(consumed_wire).commitment,
            canonicalization_profile=PROFILE, signer_key_ref=None, signature_ref=None,
        )
        # event_type remains the existing synthetic schema example; no normative
        # consumption event-type vocabulary or authenticated actor is fabricated.
        self.consumption = ConsumptionEvidence(
            consumed_wire, self.wire(self.event), StreamPosition("project:1", 5, H1))
        self.qualification = self.record(
            "CapabilityQualification", status="QUALIFIED_WITHIN_SCOPE", sample_count=3,
            failure_count=1, skip_count=1, executable_commitment=H1,
            evidence_bundle_refs=["bundle:results", "bundle:method"],
            independence_class="SAME_ACTOR",
        )
        self.qualification_evidence = QualificationEvidence(
            self.codec.decode(self.wire(self.qualification)).commitment, 3, 1, 1,
            (("bundle:results", "sha256:" + hashlib.sha256(b"synthetic results").hexdigest()),
             ("bundle:method", "sha256:" + hashlib.sha256(b"synthetic SAME_ACTOR method").hexdigest())),
            ("bundle:method",),
        )
        self.read_set = ReadSet("project:1", 4, 7, H1, H2, (
            ResourceRevision("file:target", H1), ResourceRevision("artifact:input", H2)))
        self.proposal = self.record("ActionProposal", record_id="proposal:1", scope_id="project:1",
                                   resources=[{"resource_id": "file:target", "revision": H1,
                                               "access": "WRITE", "scope_id": "project:1"}])
        self.preparation = PreparationEvidence(
            self.codec.decode(self.wire(self.proposal)).commitment,
            ("file:target", "artifact:input"), self.read_set)
        self.checks = EvidenceAdmissionChecks(
            self.codec, resolve_consumption=lambda _: self.consumption,
            resolve_qualification=lambda _: self.qualification_evidence,
            resolve_preparation=lambda _: self.preparation)

    def test_consumed_and_settled_null_reference_decode_but_semantic_check_rejects(self):
        for status in ("CONSUMED", "SETTLED"):
            with self.subTest(status=status):
                value = dict(self.permit, status=status, consume_event_ref=None)
                self.assertEqual(self.codec.decode(self.wire(value)).as_dict(), value)
                self.reject("CONSUMPTION_REFERENCE_REQUIRED", self.checks.check_permit_evidence,
                            self.wire(value))

    def test_preconsumption_shape_remains_legal_without_becoming_authority(self):
        for status in ("PREPARED", "ADMITTED"):
            with self.subTest(status=status):
                value = dict(self.permit, status=status, consume_event_ref=None)
                self.assertIsNone(EvidenceAdmissionChecks(self.codec).check_permit_evidence(self.wire(value)))
        self.reject("RUNTIME_EVIDENCE_OWNERS_UNAVAILABLE", self.checks.require_runtime_admission)

    def test_exact_consumed_and_settled_bindings_are_only_positive_predicates(self):
        self.assertIsNone(self.checks.check_permit_evidence(self.wire(self.permit)))
        settled = dict(self.permit, status="SETTLED", causation_ref="event:settlement:1")
        self.assertIsNone(self.checks.check_permit_evidence(self.wire(settled)))
        self.reject("RUNTIME_EVIDENCE_OWNERS_UNAVAILABLE", self.checks.require_runtime_admission)

    def test_consumption_without_resolved_evidence_rejects(self):
        self.reject("CONSUMPTION_EVIDENCE_UNAVAILABLE",
                    EvidenceAdmissionChecks(self.codec).check_permit_evidence, self.wire(self.permit))
        self.consumption = None
        self.reject("CONSUMPTION_EVIDENCE_REQUIRED", self.checks.check_permit_evidence,
                    self.wire(self.permit))

    def test_changed_consumed_id_nonce_task_or_arguments_cannot_reuse_event(self):
        for field, value in (("record_id", "permit:other"), ("nonce", "nonce:other"),
                             ("task_id", "task:other"), ("arguments_commitment", H3),
                             ("grant_ref", "grant:other"), ("reservation_ref", "reservation:other")):
            with self.subTest(field=field):
                self.reject("CONSUMED_PERMIT_BINDING_MISMATCH", self.checks.check_permit_evidence,
                            self.wire(dict(self.permit, **{field: value})))

    def test_consumption_event_payload_scope_hash_reference_and_sequence_reject(self):
        original = self.consumption
        for field, value, code in (
            ("record_id", "event:wrong", "CONSUMPTION_EVENT_REFERENCE_MISMATCH"),
            ("payload_ref", "permit:wrong", "EVENT_PAYLOAD_REFERENCE_MISMATCH"),
            ("payload_commitment", H3, "EVENT_PAYLOAD_COMMITMENT_MISMATCH"),
            ("scope_id", "project:other", "EVENT_SCOPE_MISMATCH"),
            ("sequence", 6, "EVENT_SEQUENCE_MISMATCH"),
            ("previous_head", H3, "EVENT_PRIOR_HEAD_MISMATCH"),
        ):
            with self.subTest(field=field):
                self.consumption = replace(original, event_wire=self.wire(dict(self.event, **{field: value})))
                self.reject(code, self.checks.check_permit_evidence, self.wire(self.permit))
        self.consumption = original

    def test_nonconsumed_payload_cannot_supply_consumption_evidence(self):
        payload = self.wire(dict(self.permit, status="SETTLED"))
        event = dict(self.event, payload_commitment=self.codec.decode(payload).commitment)
        self.consumption = replace(self.consumption, consumed_permit_wire=payload, event_wire=self.wire(event))
        self.reject("CONSUMED_PERMIT_STATUS_REQUIRED", self.checks.check_permit_evidence,
                    self.wire(self.permit))

    def test_zero_sample_self_asserted_qualified_record_still_decodes_and_rejects(self):
        value = dict(self.qualification, sample_count=0, executable_commitment=None,
                     evidence_bundle_refs=[], independence_class="INDEPENDENT_ADMIN_DOMAIN")
        self.assertEqual(self.codec.decode(self.wire(value)).as_dict(), value)
        self.reject("QUALIFICATION_SAMPLES_REQUIRED", self.checks.check_qualification_evidence,
                    self.wire(value))

    def test_qualification_missing_executable_or_bundle_rejects_separately(self):
        for field, value, code in (
            ("executable_commitment", None, "QUALIFICATION_EXECUTABLE_REQUIRED"),
            ("evidence_bundle_refs", [], "QUALIFICATION_BUNDLES_REQUIRED"),
            ("evidence_bundle_refs", ["bundle:results", "bundle:results"], "QUALIFICATION_BUNDLES_REQUIRED"),
        ):
            with self.subTest(field=field):
                self.reject(code, self.checks.check_qualification_evidence,
                            self.wire(dict(self.qualification, **{field: value})))

    def test_qualification_label_cannot_replace_resolved_independence_evidence(self):
        self.reject("QUALIFICATION_EVIDENCE_UNAVAILABLE",
                    EvidenceAdmissionChecks(self.codec).check_qualification_evidence,
                    self.wire(self.qualification))
        self.qualification_evidence = replace(self.qualification_evidence, independence_evidence_refs=())
        self.reject("QUALIFICATION_INDEPENDENCE_EVIDENCE_REQUIRED",
                    self.checks.check_qualification_evidence, self.wire(self.qualification))

    def test_exact_qualification_evidence_preserves_failures_skips_and_no_authority(self):
        self.assertIsNone(self.checks.check_qualification_evidence(self.wire(self.qualification)))
        self.assertEqual((self.qualification["failure_count"], self.qualification["skip_count"]), (1, 1))
        self.reject("RUNTIME_EVIDENCE_OWNERS_UNAVAILABLE", self.checks.require_runtime_admission)

    def test_rebound_scope_source_executable_config_fixture_or_policy_rejects(self):
        for field, value in (("scope_id", "project:other"), ("application_source", H3),
                             ("executable_commitment", H3), ("configuration_commitment", H3),
                             ("fixture_set", H3), ("threshold_policy_ref", "policy:other"),
                             ("independence_class", "INDEPENDENT_ADMIN_DOMAIN")):
            with self.subTest(field=field):
                self.reject("QUALIFICATION_BINDING_MISMATCH", self.checks.check_qualification_evidence,
                            self.wire(dict(self.qualification, **{field: value})))

    def test_actual_count_mismatch_and_boolean_count_are_rejected(self):
        original = self.qualification_evidence
        for field in ("sample_count", "failure_count", "skip_count"):
            for value in (0, True):
                with self.subTest(field=field, value=value):
                    self.qualification_evidence = replace(original, **{field: value})
                    self.reject("QUALIFICATION_COUNT_MISMATCH", self.checks.check_qualification_evidence,
                                self.wire(self.qualification))

    def test_missing_duplicate_unbound_or_null_bundle_commitments_reject(self):
        original = self.qualification_evidence
        for bundles, code in (
            ((), "QUALIFICATION_BUNDLE_BINDING_REQUIRED"),
            ((("bundle:results", None), ("bundle:method", H1)), "QUALIFICATION_BUNDLE_BINDING_REQUIRED"),
            ((("bundle:results", H1), ("bundle:results", H2)), "QUALIFICATION_BUNDLE_REFERENCE_MISMATCH"),
            ((("bundle:results", H1), ("bundle:unknown", H2)), "QUALIFICATION_BUNDLE_REFERENCE_MISMATCH"),
        ):
            with self.subTest(code=code):
                self.qualification_evidence = replace(original, bundle_commitments=bundles)
                self.reject(code, self.checks.check_qualification_evidence, self.wire(self.qualification))
        self.qualification_evidence = replace(original, independence_evidence_refs=("bundle:unknown",))
        self.reject("QUALIFICATION_INDEPENDENCE_EVIDENCE_REQUIRED",
                    self.checks.check_qualification_evidence, self.wire(self.qualification))

    def test_caller_omission_can_match_old_comparison_but_not_owner_resolved_set(self):
        omitted = replace(self.read_set, resources=(self.read_set.resources[0],))
        self.assertIsNone(require_current_preparation(omitted, omitted, ("file:target",)))
        self.reject("READ_SET_DEPENDENCY_MISMATCH", self.checks.check_preparation_evidence,
                    self.wire(self.proposal), omitted)
        self.reject("PREPARATION_EVIDENCE_UNAVAILABLE",
                    EvidenceAdmissionChecks(self.codec).check_preparation_evidence,
                    self.wire(self.proposal), omitted)

    def test_public_preparation_call_cannot_supply_required_resource_ids(self):
        with self.assertRaises(TypeError):
            self.checks.check_preparation_evidence(self.wire(self.proposal), self.read_set,
                                                  required_resource_ids=("file:target",))

    def test_complete_current_owner_resolution_passes_only_binding_predicate(self):
        self.assertIsNone(self.checks.check_preparation_evidence(self.wire(self.proposal), self.read_set))
        unrelated = replace(self.read_set, resources=self.read_set.resources + (ResourceRevision("file:other", H3),))
        self.preparation = replace(self.preparation, current=unrelated)
        self.assertIsNone(self.checks.check_preparation_evidence(self.wire(self.proposal), self.read_set))
        self.reject("RUNTIME_EVIDENCE_OWNERS_UNAVAILABLE", self.checks.require_runtime_admission)

    def test_preparation_detects_stale_generation_resource_and_proposal(self):
        original = self.preparation
        for current, code in (
            (replace(self.read_set, authority_generation=5), "AUTHORITY_GENERATION_CHANGED"),
            (replace(self.read_set, fence_generation=8), "FENCE_GENERATION_CHANGED"),
            (replace(self.read_set, resources=(ResourceRevision("file:target", H3), self.read_set.resources[1])),
             "RESOURCE_REVISION_CHANGED"),
        ):
            with self.subTest(code=code):
                self.preparation = replace(original, current=current)
                self.reject(code, self.checks.check_preparation_evidence, self.wire(self.proposal), self.read_set)
        self.preparation = original
        self.reject("PREPARATION_PROPOSAL_BINDING_MISMATCH", self.checks.check_preparation_evidence,
                    self.wire(dict(self.proposal, arguments_commitment=H3)), self.read_set)

    def test_proposal_resource_scope_revision_and_duplicate_claims_reject(self):
        resource = self.proposal["resources"][0]
        for resources, code in (
            ([dict(resource, revision=None)], "PREPARATION_RESOURCE_BINDING_MISMATCH"),
            ([dict(resource, scope_id="project:other")], "PREPARATION_RESOURCE_SCOPE_MISMATCH"),
            ([resource, resource], "DUPLICATE_PROPOSAL_RESOURCE"),
        ):
            with self.subTest(code=code):
                proposal = dict(self.proposal, resources=resources)
                self.preparation = replace(self.preparation, proposal_commitment=self.codec.decode(self.wire(proposal)).commitment)
                self.reject(code, self.checks.check_preparation_evidence, self.wire(proposal), self.read_set)

    def test_all_twenty_shapes_round_trip_and_internal_read_set_remains_unadmitted(self):
        self.assertEqual(len(self.schema["$defs"]), 20)
        for name, shape in self.schema["$defs"].items():
            with self.subTest(record=name):
                value = example(shape)
                parsed = self.codec.decode(self.wire(value))
                self.assertEqual(parsed.as_dict(), value)
                self.assertEqual(self.codec.decode(parsed.canonical_wire).commitment, parsed.commitment)
        self.assertEqual(strict_loads(self.read_set.canonical_wire())["contract_type"], "RelevantReadSet")
        self.reject("UNKNOWN_RECORD_TYPE", self.codec.decode, self.read_set.canonical_wire())

    def test_wrong_record_types_and_injected_truth_flag_never_authorize(self):
        for method, code in ((self.checks.check_permit_evidence, "OPERATION_PERMIT_REQUIRED"),
                             (self.checks.check_qualification_evidence, "CAPABILITY_QUALIFICATION_REQUIRED")):
            self.reject(code, method, self.wire(self.proposal))
        forged = dict(self.qualification, authenticated=True)
        self.reject("UNKNOWN_FIELD", self.checks.check_qualification_evidence, self.wire(forged))
        with self.assertRaises(TypeError):
            self.checks.require_runtime_admission(authenticated=True)

    def test_internal_resolver_inputs_are_immutable_not_authority_tokens(self):
        for obj, field, value in ((self.consumption, "event_wire", b"changed"),
                                  (self.qualification_evidence, "sample_count", 99),
                                  (self.preparation, "required_resource_ids", ("worker:chosen",))):
            with self.subTest(field=field), self.assertRaises(FrozenInstanceError):
                setattr(obj, field, value)
        self.reject("RUNTIME_EVIDENCE_OWNERS_UNAVAILABLE", self.checks.require_runtime_admission)


if __name__ == "__main__":
    unittest.main()
