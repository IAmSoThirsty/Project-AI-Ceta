"""Acceptance and hostile tests for the bounded, source-grounded relevance path."""
from __future__ import annotations

from hashlib import sha256
import json
import unittest

from societal_reasoning.context import compare_context
from societal_reasoning.engine import SocietalReasoner
from societal_reasoning.graph import KnowledgeGraph
from societal_reasoning.models import Scenario
from societal_reasoning.relevance import EvidenceText, KnowledgeRelevance


class RetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.retriever = KnowledgeRelevance(KnowledgeGraph.canonical())

    def suggest(self, text, origin="user_utterance", **options):
        return self.retriever.suggest([EvidenceText("turn-1", text, origin)], **options)

    def test_exact_label_matches(self):
        result = self.suggest("We discussed humor and reputation.")
        self.assertEqual([x["concept_id"] for x in result["topics"][:2]], [151, 74])

    def test_no_canned_label_for_job_loss(self):
        self.assertEqual(self.suggest("I lost my job.")["topics"], [])

    def test_absent_topic_is_not_forced(self):
        result = self.suggest("Axyz Bxyz Cxyz.")
        self.assertEqual(result["status"], "no_defensible_lexical_matches")

    def test_common_single_word_does_not_retrieve_spurious_multiword_label(self):
        self.assertEqual(self.suggest("Context changes everything.")["topics"], [])

    def test_preserves_source_digest(self):
        row = self.suggest("I appreciate humor.")["topics"][0]
        self.assertEqual(row["source"]["source_sha256"], sha256(b"I appreciate humor.").hexdigest())
        self.assertEqual(row["source"]["source_id"], "turn-1")
        self.assertEqual(row["source"]["origin"], "user_utterance")

    def test_quoted_text_never_becomes_observation(self):
        row = self.suggest("The quote mentioned humor.", origin="quoted_material")["topics"][0]
        self.assertEqual(row["source"]["origin"], "quoted_material")
        self.assertIn("not_independently_verified", row["source"]["evidence_status"])

    def test_relationship_hypotheses_not_inferred_facts(self):
        result = self.suggest("Humor shaped the conversation.")
        self.assertTrue(result["related_relationship_hypotheses"])
        self.assertTrue(all(row["assertion_status"] == "unverified_relationship_hypothesis_not_an_inference"
                            for row in result["related_relationship_hypotheses"]))
        self.assertTrue(all("hypothesis" in row["provenance"]
                            for row in result["related_relationship_hypotheses"]))

    def test_max_relationships_zero(self):
        result = self.suggest("Humor matters.", max_related_edges=0)
        self.assertEqual(result["related_relationship_hypotheses"], [])

    def test_limit_restricts_results(self):
        self.assertEqual(len(self.suggest("humor and reputation", limit=1)["topics"]), 1)

    def test_rejects_zero_limit(self):
        with self.assertRaisesRegex(ValueError, "limit"):
            self.suggest("Humor", limit=0)

    def test_rejects_noninteger_limit(self):
        with self.assertRaisesRegex(ValueError, "limit"):
            self.suggest("Humor", limit=True)

    def test_rejects_large_limit(self):
        with self.assertRaises(ValueError):
            self.suggest("Humor", limit=999)

    def test_rejects_invalid_edge_limit(self):
        with self.assertRaisesRegex(ValueError, "max_related_edges"):
            self.suggest("Humor", max_related_edges=-1)

    def test_rejects_bogus_source_identifier(self):
        with self.assertRaisesRegex(ValueError, "identifier"):
            EvidenceText("../../bad", "Humor", "user_utterance")

    def test_rejects_empty_source_text(self):
        with self.assertRaisesRegex(ValueError, "text"):
            EvidenceText("t1", "   ", "user_utterance")

    def test_rejects_oversize_source_text(self):
        with self.assertRaisesRegex(ValueError, "text"):
            EvidenceText("t1", "x" * 65537, "user_utterance")

    def test_rejects_unknown_origin(self):
        with self.assertRaisesRegex(ValueError, "origins"):
            EvidenceText("t1", "Humor", "model_hypothesis")

    def test_rejects_invalid_source_reference(self):
        with self.assertRaisesRegex(ValueError, "reference"):
            EvidenceText("t1", "Humor", "quoted_material", source_ref="")

    def test_rejects_too_long_source_reference(self):
        with self.assertRaisesRegex(ValueError, "reference"):
            EvidenceText("t1", "Humor", "external_record", source_ref="x" * 513)

    def test_rejects_aggregate_source_limit(self):
        with self.assertRaisesRegex(ValueError, "Aggregate"):
            self.retriever.suggest([EvidenceText(f"t{i}", "a" * 65536, "user_report") for i in range(3)])

    def test_rejects_duplicate_source_ids(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.retriever.suggest([EvidenceText("t1", "Humor", "user_report"),
                                   EvidenceText("t1", "Trust", "user_report")])

    def test_no_sources_abstains(self):
        result = self.retriever.suggest([])
        self.assertEqual(result["source_count"], 0)
        self.assertEqual(result["status"], "no_defensible_lexical_matches")

    def test_rejects_too_many_sources(self):
        with self.assertRaisesRegex(ValueError, "64"):
            self.retriever.suggest([EvidenceText(f"t{i}", "Humor", "user_utterance") for i in range(65)])

    def test_sorted_result_is_stable_across_input_order(self):
        a = EvidenceText("a", "Humor", "user_utterance")
        b = EvidenceText("b", "Reputation", "quoted_material")
        x = self.retriever.suggest([a,b])
        y = self.retriever.suggest([b,a])
        self.assertEqual(x,y)

    def test_status_not_person_classification(self):
        row = self.suggest("Humor")["topics"][0]
        self.assertEqual(row["interpretation_status"], "topic_to_consider_not_a_claim_about_a_person")
        self.assertNotIn("person_label", row)

    def test_no_topic_is_claimed_independently_verified(self):
        result = self.suggest("Humor and reputation")
        self.assertTrue(all(t["record_status"] == "source_transcribed" for t in result["topics"]))
        self.assertIn("No human feeling", " ".join(result["limitations"]))

    def test_user_context_can_have_source_ref(self):
        x = EvidenceText("ctx:abc", "Trust", "external_record", source_ref="publication-12")
        record = self.retriever.suggest([x])["topics"][0]
        self.assertEqual(record["source"]["source_ref"], "publication-12")


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reasoner = SocietalReasoner.starter()

    def test_assess_now_consults_all_2000(self):
        result = self.reasoner.assess_text("What role does humor play?")
        self.assertEqual(result["knowledge_considerations"]["topics"][0]["concept_id"], 74)
        self.assertEqual(self.reasoner.graph.audit()["concept_count"],2000)

    def test_assess_does_not_infer_user_emotions(self):
        result = self.reasoner.assess_text("I lost my job.")
        self.assertEqual(result["response_mode"], "no_requested_action_identified")
        self.assertEqual(result["knowledge_considerations"]["topics"], [])
        self.assertNotIn("depressed", str(result["knowledge_considerations"]))

    def test_explicit_reported_context_is_attributed(self):
        fact = {"id":"c1", "category":"audience", "value":"public reputation",
                "origin":"user_report", "source_ref":"user-message-2"}
        a = self.reasoner.assess_text("What happened?", context_facts=(fact,))
        self.assertTrue(a["knowledge_considerations"]["topics"])
        source = a["knowledge_considerations"]["topics"][0]["source"]
        self.assertEqual(source["source_id"], "context:c1")
        self.assertEqual(source["source_ref"], "user-message-2")

    def test_model_context_does_not_create_knowledge_evidence(self):
        fact = {"id":"c1", "category":"audience", "value":"public reputation",
                "origin":"model_hypothesis"}
        a = self.reasoner.assess_text("What happened?", context_facts=(fact,))
        self.assertEqual(a["knowledge_considerations"]["topics"], [])
        self.assertEqual(a["knowledge_considerations"]["excluded_context_ids"],["c1"])

    def test_conflicting_reports_do_not_select_side(self):
        facts = (
            {"id":"c1", "category":"audience", "value":"public reputation", "origin":"user_report"},
            {"id":"c2", "category":"audience", "value":"privacy", "origin":"user_report"},
        )
        result = self.reasoner.assess_text("What happened?", context_facts=facts)
        self.assertEqual(result["knowledge_considerations"]["topics"], [])
        self.assertEqual(result["knowledge_considerations"]["excluded_context_ids"], ["c1", "c2"])
        self.assertEqual(result["context"]["source_conflicts"][0]["category"], "audience")

    def test_relevant_context_changes_knowledge_context_not_objective(self):
        reported = ({"id":"c1", "category":"audience", "value":"public reputation", "origin":"user_report"},)
        before = self.reasoner.assess_text("What happened?")
        after = self.reasoner.assess_text("What happened?", context_facts=reported)
        self.assertEqual(before["objective"],after["objective"])
        self.assertNotEqual(before["knowledge_considerations"]["topics"],
                            after["knowledge_considerations"]["topics"])

    def test_context_change_is_not_proof_of_effects(self):
        a = ({"id":"c1", "category":"audience", "value":"Humor", "origin":"user_report"},)
        b = ({"id":"c1", "category":"audience", "value":"Reputation", "origin":"user_report"},)
        delta = compare_context(a,b)
        self.assertTrue(delta["requires_reconsideration"])
        self.assertIn("actual effect",delta["cannot_infer"])

    def test_ambiguity_gate_stays_authoritative_with_topics(self):
        a = self.reasoner.assess_text("What is the context of humor?", material_words=("context",))
        self.assertEqual(a["response_mode"], "necessary_clarification")
        self.assertTrue(a["knowledge_considerations"]["topics"])

    def test_no_person_label_based_on_knowledge_leads(self):
        result = self.reasoner.assess_text("Tell me about greed.")
        self.assertIn(57, [x["concept_id"] for x in result["knowledge_considerations"]["topics"]])
        self.assertNotIn("the user", str(result["knowledge_considerations"]))

    def test_structured_interpretation_only_evidence_excluded_from_retrieval(self):
        case = Scenario.from_dict({
            "id":"test-case", "question":"What happened?", "evidence": [
                {"id":"i", "origin":"interpretation", "statement":"Humor is the only explanation", "cues":["public_audience"]},
            ]})
        a = self.reasoner.analyze(case)
        self.assertEqual(a["knowledge_considerations"]["source_count"],0)
        self.assertEqual(a["knowledge_considerations"]["topics"],[])
        self.assertEqual(a["status"],"insufficient_evidence")

    def test_structured_evidence_is_report_not_independent_proof(self):
        case = Scenario.from_dict({
            "id":"test-case", "question":"What happened?", "evidence": [
                {"id":"e1", "origin":"user_report", "statement":"We discussed humor.", "cues":[]},
            ]})
        a = self.reasoner.analyze(case)
        self.assertEqual(a["knowledge_considerations"]["topics"][0]["source"]["source_id"],"evidence:e1")
        self.assertEqual(a["status"],"insufficient_evidence")

    def test_untrusted_graph_edges_cannot_activate_rule(self):
        case = Scenario.from_dict({
            "id":"test-case", "question":"Is this hostile?", "evidence": [
                {"id":"e1", "origin":"user_report", "statement":"We discussed humor.", "cues":[]},
            ]})
        a = self.reasoner.analyze(case)
        self.assertTrue(a["knowledge_considerations"]["related_relationship_hypotheses"])
        self.assertEqual(a["status"],"insufficient_evidence")
        self.assertIsNone(a["primary"])

    def test_structured_case_can_still_apply_prior_rules(self):
        from pathlib import Path
        case = Scenario.from_dict(json.loads(Path("examples/friendly_banter.json").read_text()))
        a = self.reasoner.analyze(case)
        self.assertEqual(a["primary"]["rule_id"],"mutual_playful_banter")
        self.assertIn("knowledge_considerations",a)

    def test_compact_json_serializable(self):
        a = self.reasoner.assess_text("Can you explain trust?")
        self.assertIn("topic_to_consider", json.dumps(a))


if __name__ == "__main__":
    unittest.main()
