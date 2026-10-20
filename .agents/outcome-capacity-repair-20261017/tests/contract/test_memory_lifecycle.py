"""Privacy/staleness cross-bindings and bounded deletion claims, using fixtures."""
import copy
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts import ContractError, RecordCodec, canonical_bytes, strict_loads
from ceta.contracts.memory_lifecycle import MEMORY_STATES, MemoryLifecycleContract
from test_all_records import example


class MemoryLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes())
        cls.codec = RecordCodec(cls.schema)

    def setUp(self):
        self.contract = MemoryLifecycleContract(self.codec)
        self.memory = example(self.schema["$defs"]["MemoryRecord"])
        self.memory.update(record_id="memory.1",scope_id="project.alpha",lifecycle="ACTIVE",
                           retention_policy_ref="retention-policy.1")
        self.event = example(self.schema["$defs"]["MemoryLifecycleEvent"])
        self.event.update(record_id="lifecycle.1",scope_id="project.alpha",memory_ref="memory.1",
                          policy_ref="retention-policy.1",before="ACTIVE",after="ARCHIVED",
                          payload_deletion_state="NOT_REQUESTED",evidence_refs=[])

    def assess(self, memory=None, event=None, **context):
        return self.contract.check_binding(canonical_bytes(self.memory if memory is None else memory),
            canonical_bytes(self.event if event is None else event),
            expected_scope=context.get("scope","project.alpha"),
            expected_policy_ref=context.get("policy","retention-policy.1"))

    def reject(self, call, code):
        with self.assertRaises(ContractError) as caught: call()
        self.assertEqual(caught.exception.code,code)

    def test_valid_binding_retains_current_candidate_and_outstanding_authority(self):
        result = self.assess()
        self.assertEqual(result.requested_state,"ARCHIVED")
        self.assertEqual(result.memory.commitment,self.codec.decode(canonical_bytes(self.memory)).commitment)
        self.assertEqual(result.lifecycle_event.commitment,self.codec.decode(canonical_bytes(self.event)).commitment)
        self.assertIn("CURRENT_AUTHORITY_AND_RETENTION_POLICY",result.required_verifications)
        self.assertIn("AUTHENTIC_INITIATOR_AND_APPROVAL",result.required_verifications)

    def test_same_identifier_in_another_scope_is_not_a_match(self):
        for target in ("memory","event","context"):
            memory,event = copy.deepcopy(self.memory),copy.deepcopy(self.event)
            context = {}
            if target == "context": context["scope"] = "project.beta"
            else: (memory if target == "memory" else event)["scope_id"] = "project.beta"
            with self.subTest(target=target):
                self.reject(lambda: self.assess(memory,event,**context),"MEMORY_SCOPE_MISMATCH")

    def test_current_memory_identity_must_match_event_reference(self):
        self.event["memory_ref"] = "memory.other"
        self.reject(self.assess,"MEMORY_REFERENCE_MISMATCH")

    def test_lifecycle_before_state_cannot_be_stale(self):
        self.event["before"] = "CANDIDATE"
        self.reject(self.assess,"MEMORY_STATE_STALE")

    def test_policy_rebinding_is_rejected_at_each_input(self):
        for target in ("memory","event","context"):
            memory,event = copy.deepcopy(self.memory),copy.deepcopy(self.event)
            context = {}
            if target == "context": context["policy"] = "retention-policy.other"
            elif target == "memory": memory["retention_policy_ref"] = "retention-policy.other"
            else: event["policy_ref"] = "retention-policy.other"
            with self.subTest(target=target):
                self.reject(lambda: self.assess(memory,event,**context),"MEMORY_POLICY_MISMATCH")

    def test_unknown_after_state_cannot_be_laundered_by_shape_valid_event(self):
        self.event["after"] = "GLOBALLY_FORGOTTEN"
        self.reject(self.assess,"UNKNOWN_MEMORY_LIFECYCLE")

    def test_requested_deletion_cannot_assert_deleted_payload(self):
        self.event["after"] = "DELETED_PAYLOAD"
        for state in ("NOT_REQUESTED","REQUESTED"):
            self.event["payload_deletion_state"] = state
            with self.subTest(state=state):
                self.reject(self.assess,"MEMORY_DELETION_CLAIM_UNSUPPORTED")

    def test_observed_partial_or_backup_deletion_needs_evidence_references(self):
        for state in ("LOCAL_DELETION_OBSERVED","BACKUP_RETENTION_PENDING","PARTIAL"):
            self.event.update(after="DELETED_PAYLOAD",payload_deletion_state=state,evidence_refs=[])
            with self.subTest(state=state):
                self.reject(self.assess,"MEMORY_DELETION_EVIDENCE_MISSING")

    def test_a_claimed_evidence_id_does_not_discharge_independent_verification(self):
        self.event.update(after="DELETED_PAYLOAD",payload_deletion_state="LOCAL_DELETION_OBSERVED",
                          evidence_refs=["claim.model-said-deleted"],derived_index_actions=["all copies done"])
        result = self.assess()
        self.assertIn("INDEPENDENT_PAYLOAD_DELETION_EVIDENCE",result.required_verifications)
        self.assertIn("DERIVED_COPY_AND_BACKUP_ACCOUNTING",result.required_verifications)
        self.assertEqual(result.claimed_payload_deletion_state,"LOCAL_DELETION_OBSERVED")

    def test_request_with_no_derivative_actions_keeps_copy_accounting_open(self):
        self.event.update(payload_deletion_state="REQUESTED",derived_index_actions=[])
        result = self.assess()
        self.assertIn("DERIVED_COPY_AND_BACKUP_ACCOUNTING",result.required_verifications)
        self.assertNotIn("INDEPENDENT_PAYLOAD_DELETION_EVIDENCE",result.required_verifications)

    def test_partial_and_backup_pending_claims_are_preserved_without_completion(self):
        for state in ("PARTIAL","BACKUP_RETENTION_PENDING"):
            self.event.update(after="DELETED_PAYLOAD",payload_deletion_state=state,evidence_refs=["evidence.1"])
            with self.subTest(state=state):
                result = self.assess()
                self.assertEqual(result.claimed_payload_deletion_state,state)
                self.assertIn("DERIVED_COPY_AND_BACKUP_ACCOUNTING",result.required_verifications)
                self.assertIn("INDEPENDENT_PAYLOAD_DELETION_EVIDENCE",result.required_verifications)

    def test_wrong_record_kind_is_not_accepted_as_memory_or_lifecycle(self):
        other = example(self.schema["$defs"]["ObservationEnvelope"])
        self.reject(lambda: self.assess(memory=other),"MEMORY_RECORD_TYPE_MISMATCH")
        self.reject(lambda: self.assess(event=other),"MEMORY_RECORD_TYPE_MISMATCH")

    def test_explicit_context_and_codec_are_required(self):
        for value in (None,"","../escape","x"*161,3,True,b"project.alpha"):
            with self.subTest(value=repr(value)):
                self.reject(lambda: self.assess(scope=value),"INVALID_MEMORY_CONTEXT")
                self.reject(lambda: self.assess(policy=value),"INVALID_MEMORY_CONTEXT")
        self.reject(lambda: MemoryLifecycleContract(object()),"INVALID_MEMORY_CODEC")

    def test_model_authority_field_remains_rejected(self):
        self.event["owner_says_allow"] = True
        self.reject(self.assess,"UNKNOWN_FIELD")

    def test_original_bytes_and_assessment_are_immutable(self):
        memory_wire = json.dumps(self.memory,indent=2).encode()+b"\r\n"
        event_wire = json.dumps(self.event,indent=2).encode()+b"\n"
        result = self.contract.check_binding(memory_wire,event_wire,expected_scope="project.alpha",
                                             expected_policy_ref="retention-policy.1")
        self.assertEqual(result.memory.original_wire,memory_wire)
        self.assertEqual(result.lifecycle_event.original_wire,event_wire)
        with self.assertRaises(FrozenInstanceError): result.requested_state = "ACTIVE"
        self.memory["content_ref"] = "content.rebound"
        self.assertNotEqual(self.assess().memory.commitment,result.memory.commitment)
        self.assertEqual(result.memory.original_wire,memory_wire)

    def test_profile_states_match_exact_existing_schema(self):
        self.assertEqual(MEMORY_STATES,frozenset(self.schema["$defs"]["MemoryRecord"]["properties"]["lifecycle"]["enum"]))


if __name__ == "__main__": unittest.main()
