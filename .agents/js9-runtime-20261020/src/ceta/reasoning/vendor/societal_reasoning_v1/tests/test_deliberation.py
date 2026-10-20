"""Adversarial contracts for caller-proposed, evidence-linked alternatives.

These tests do not prove human-level interpretation; they protect provenance,
conditional relevance, source separation and refusal to assign people labels.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import unittest

from societal_reasoning import DeliberationCase, SocietalReasoner

ROOT = Path(__file__).resolve().parents[1]


def example(name="public"):
    return json.loads((ROOT / "examples" / f"deliberation_{name}.json").read_text(encoding="utf-8"))


class DeliberationContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = SocietalReasoner.starter()

    def evaluate(self, data=None):
        return self.engine.deliberate(DeliberationCase.from_dict(data or example()))

    def test_public_case_is_source_bounded(self):
        out = self.evaluate()
        self.assertEqual(out["schema"], "deliberation.v1")
        self.assertEqual(out["version"], "1")
        self.assertEqual(out["response_guidance"]["mode"], "present_alternatives_with_sources")
        self.assertEqual([p["status"] for p in out["candidates"]],
                         ["active_pro_warrants_not_semantic_proof", "active_pro_warrants_not_semantic_proof",
                          "no_active_supporting_warrants", "no_active_supporting_warrants"])
        self.assertEqual(len(out["candidates"][0]["supporting_warrants"]), 2)
        self.assertEqual(out["candidates"][3]["excluded_warrants"][0]["evidence_origin"], "interpretation")
        self.assertFalse(out["candidates"][3]["supporting_warrants"])
        self.assertEqual(out["candidates"][0]["related_concepts_not_premises"][0]["label"], "Humor")

    def test_context_switch_changes_only_applicable_readings(self):
        public = DeliberationCase.from_dict(example())
        private = DeliberationCase.from_dict(example("private"))
        diff = self.engine.compare_deliberations(public, private)
        self.assertEqual(diff["schema"], "deliberation_comparison.v1")
        self.assertEqual({p["id"] for p in diff["candidate_changes"]},
                         {"group-directed-reading", "private-joking-reading"})
        self.assertFalse(diff["evidence_changes"])
        self.assertEqual(diff["context_change"]["changed_factors"][0]["category"], "channel")
        self.assertEqual(diff["before"]["candidates"][1]["status"],
                         diff["after"]["candidates"][1]["status"])

    def test_unrelated_context_change_does_not_change_reading(self):
        before = example()
        after = deepcopy(before)
        after["context_facts"][1]["value"] = "Different day of the week"
        result = self.engine.compare_deliberations(DeliberationCase.from_dict(before), DeliberationCase.from_dict(after))
        self.assertEqual(result["candidate_changes"], [])
        self.assertFalse(result["context_change"]["requires_reconsideration"])

    def test_changed_candidate_authorship_is_visible(self):
        p, q = example(), example()
        q["hypotheses"][0]["proposed_by"] = "model_proposal"
        changes = self.engine.compare_deliberations(DeliberationCase.from_dict(p), DeliberationCase.from_dict(q))
        self.assertEqual(changes["candidate_changes"][0]["id"], "group-directed-reading")
        self.assertIn("proposed_by", changes["candidate_changes"][0]["changed_fields"])
        self.assertFalse(changes["before"]["candidates"][0]["proposer_identity_authenticated"])

    def test_changed_candidate_unknowns_are_visible(self):
        p, q = example(), example()
        q["hypotheses"][0]["unknowns"].append("Whether a private reply followed")
        changes = self.engine.compare_deliberations(DeliberationCase.from_dict(p), DeliberationCase.from_dict(q))
        self.assertIn("not_established", changes["candidate_changes"][0]["changed_fields"])

    def test_direct_constructor_rejects_duplicate_warrant(self):
        from societal_reasoning.deliberation import Hypothesis
        h = DeliberationCase.from_dict(example()).hypotheses[0]
        with self.assertRaises(ValueError):
            Hypothesis(h.id, h.reading, h.proposed_by, h.warrants + (h.warrants[0],))

    def test_proposed_rationale_is_not_entailment_proof(self):
        p = example()
        p["hypotheses"][0]["reading"] = "An arbitrary and unsupported claim about a person."
        p["hypotheses"][0]["warrants"][0]["rationale"] = "The evidence supposedly proves everything."
        result = self.evaluate(p)
        self.assertFalse(result["candidates"][0]["semantic_entailment_checked"])
        self.assertFalse(result["candidates"][0]["supporting_warrants"][0]["rationale_semantically_verified"])
        self.assertIn("not_semantic_proof", result["candidates"][0]["status"])

    def test_case_order_stable_for_same_input(self):
        p = example()
        self.assertEqual(self.evaluate(p), self.evaluate(deepcopy(p)))

    def test_model_context_only_cannot_activate_warrant(self):
        p = example()
        p["context_facts"][0]["origin"] = "model_hypothesis"
        result = self.evaluate(p)
        first = result["candidates"][0]
        self.assertFalse(first["supporting_warrants"])
        self.assertEqual(len(first["deferred_warrants"]), 2)
        self.assertEqual(first["deferred_warrants"][0]["condition_state"], "context_not_established")

    def test_conflicted_channel_does_not_select_favorite(self):
        p = example()
        p["context_facts"].append({"id": "conflict", "category": "channel", "value": "private_chat",
                                   "origin": "external_record", "source_ref": "other"})
        result = self.evaluate(p)
        self.assertEqual(len(result["context"]["source_conflicts"]), 1)
        for candidate in (result["candidates"][0], result["candidates"][2]):
            self.assertEqual(candidate["status"], "no_active_supporting_warrants")
            self.assertEqual(candidate["deferred_warrants"][0]["condition_state"], "unresolved_conflict")

    def test_absent_channel_stays_unknown(self):
        p = example()
        p["context_facts"] = []
        result = self.evaluate(p)
        self.assertEqual(result["candidates"][0]["deferred_warrants"][0]["condition_state"], "context_not_established")

    def test_context_not_normalized_to_a_person_attribute(self):
        p = example()
        p["context_facts"][0]["value"] = "public_forum"
        r = self.evaluate(p)
        self.assertEqual(r["candidates"][0]["conclusion_status"], "proposed_interpretation_not_factual_finding")
        self.assertNotIn("You are", json.dumps(r))

    def test_casefold_context_match(self):
        p = example()
        p["context_facts"][0]["value"] = " PUBLIC_FORUM "
        r = self.evaluate(p)
        self.assertEqual(r["candidates"][0]["status"], "active_pro_warrants_not_semantic_proof")

    def test_inactive_warrant_does_not_become_a_challenge(self):
        r = self.evaluate(example("private"))
        self.assertEqual(r["candidates"][0]["status"], "no_active_supporting_warrants")
        self.assertFalse(r["candidates"][0]["challenging_warrants"])
        self.assertTrue(r["candidates"][0]["inactive_warrants"])

    def test_speaker_report_not_a_proven_event(self):
        r = self.evaluate()
        self.assertTrue(r["candidates"][0]["supporting_warrants"][0]["evidence_is_report_not_certified_fact"])
        self.assertIn("not_independent_factual_findings", r["claim_boundary"])

    def test_quoted_content_cannot_be_assumed_true(self):
        r = self.evaluate()
        quote = r["candidates"][0]["supporting_warrants"][1]
        self.assertEqual(quote["evidence_origin"], "quoted_material")
        self.assertTrue(quote["evidence_is_report_not_certified_fact"])

    def test_evidence_sha_follows_source_text(self):
        r = self.evaluate()
        first = r["candidates"][0]["supporting_warrants"][0]
        self.assertEqual(first["source_sha256"], sha256(first["evidence_text"].encode()).hexdigest())

    def test_changed_source_changes_digest_and_is_reported_in_comparison(self):
        old, new = example(), example()
        new["scenario"]["evidence"][0]["statement"] += " (correction supplied)"
        changed = self.engine.compare_deliberations(DeliberationCase.from_dict(old), DeliberationCase.from_dict(new))
        self.assertEqual([x["evidence_id"] for x in changed["evidence_changes"]], ["e1"])
        self.assertIn("group-directed-reading", {x["id"] for x in changed["candidate_changes"]})

    def test_infer_nothing_without_positive_evidence(self):
        p = example()
        for h in p["hypotheses"]:
            h["warrants"] = [w for w in h["warrants"] if w["role"] == "challenge"] or [
                {"evidence_id": "e4", "role": "support", "rationale": "Unsupported guess"}
            ]
        result = self.evaluate(p)
        self.assertTrue(all(x["status"] == "no_active_supporting_warrants" for x in result["candidates"]))
        self.assertEqual(result["response_guidance"]["mode"], "withhold_unsupported_conclusion")

    def test_challenge_without_support(self):
        p = example()
        p["hypotheses"][1]["warrants"][0]["role"] = "challenge"
        r = self.evaluate(p)
        self.assertEqual(r["candidates"][1]["status"], "active_con_warrants_only")

    def test_challenge_with_support_remains_contested(self):
        p = example()
        p["hypotheses"][0]["warrants"].append({"evidence_id": "e3", "role": "challenge",
                                                   "rationale": "A specific reported defect may complicate a solely ridicule-based reading"})
        r = self.evaluate(p)
        self.assertEqual(r["candidates"][0]["status"], "active_pro_and_con_warrants_not_semantic_proof")
        self.assertTrue(r["candidates"][0]["challenging_warrants"])
        self.assertEqual(r["response_guidance"]["mode"], "present_alternatives_with_sources")

    def test_repeated_sources_not_independent_confirmation(self):
        p = example()
        p["scenario"]["evidence"][1]["source_ref"] = "report-1"
        r = self.evaluate(p)
        self.assertEqual(r["candidates"][0]["supporting_source_refs_not_independence_proof"], ["report-1"])

    def test_unattributed_sources_not_counted_independent(self):
        p = example()
        p["scenario"]["evidence"][0]["source_ref"] = None
        p["scenario"]["evidence"][1]["source_ref"] = None
        r = self.evaluate(p)
        self.assertEqual(r["candidates"][0]["supporting_source_refs_not_independence_proof"], ["unknown-origin"])

    def test_unverified_topic_cannot_change_candidate_status(self):
        p = example()
        original = self.evaluate(p)
        p["hypotheses"][0]["concept_ids"] = [75]
        changed = self.evaluate(p)
        self.assertEqual(original["candidates"][0]["status"], changed["candidates"][0]["status"])

    def test_model_authored_hypothesis_is_not_an_observation(self):
        p = example()
        p["hypotheses"][0]["proposed_by"] = "model_proposal"
        r = self.evaluate(p)
        self.assertEqual(r["candidates"][0]["proposed_by"], "model_proposal")
        self.assertEqual(r["candidates"][0]["conclusion_status"], "proposed_interpretation_not_factual_finding")

    def test_contradiction_is_not_mandatory_clarification(self):
        p = example()
        p["context_facts"].append({"id": "conflict", "category": "channel", "value": "private_chat",
                                   "origin": "external_record", "source_ref": "other"})
        result = self.evaluate(p)
        self.assertTrue(result["response_guidance"]["clarification_is_not_automatically_required"])

    def test_opaque_context_cannot_leak_model_hypothesis_into_retrieval(self):
        p = example()
        p["context_facts"].append({"id": "fantasy", "category": "other", "value": "anger jealousy coercion",
                                   "origin": "model_hypothesis"})
        old = self.evaluate(example())
        new = self.evaluate(p)
        self.assertEqual(old["knowledge_considerations"], new["knowledge_considerations"])

    def test_no_external_api_or_network_called(self):
        self.assertEqual(self.evaluate()["version"], "1")
        self.assertNotIn("http", repr(self.evaluate()["response_guidance"]))

    def test_compare_same_question_required(self):
        p, q = example(), example("private")
        q["scenario"]["question"] = "Different question"
        with self.assertRaises(ValueError):
            self.engine.compare_deliberations(DeliberationCase.from_dict(p), DeliberationCase.from_dict(q))

    def test_compare_same_id_required(self):
        p, q = example(), example("private")
        q["scenario"]["id"] = "different"
        with self.assertRaises(ValueError):
            self.engine.compare_deliberations(DeliberationCase.from_dict(p), DeliberationCase.from_dict(q))

    def test_compare_candidate_set_must_be_identical(self):
        p, q = example(), example("private")
        q["hypotheses"].pop()
        with self.assertRaises(ValueError):
            self.engine.compare_deliberations(DeliberationCase.from_dict(p), DeliberationCase.from_dict(q))

    def test_context_multiple_conditions_must_all_match(self):
        p = example()
        p["hypotheses"][0]["warrants"][0]["conditions"].append({"category": "relationship", "value": "coworkers"})
        r = self.evaluate(p)
        self.assertEqual(r["candidates"][0]["deferred_warrants"][0]["condition_state"], "context_not_established")
        p["context_facts"].append({"id": "friendship", "category": "relationship", "value": "coworkers", "origin": "user_report"})
        r = self.evaluate(p)
        self.assertEqual(r["candidates"][0]["supporting_warrants"][0]["condition_state"], "applicable")

    def test_two_conditions_one_mismatched_is_inactive(self):
        p = example()
        p["hypotheses"][0]["warrants"][0]["conditions"].append({"category": "setting", "value": "private-home"})
        p["context_facts"].append({"id": "place", "category": "setting", "value": "public-square", "origin": "user_report"})
        r = self.evaluate(p)
        self.assertEqual(r["candidates"][0]["inactive_warrants"][0]["condition_state"], "not_applicable_to_this_context")

    def test_context_conflict_takes_precedence_over_other_conditions(self):
        p = example()
        p["hypotheses"][0]["warrants"][0]["conditions"].append({"category": "relationship", "value": "coworkers"})
        p["context_facts"].append({"id": "conflict", "category": "channel", "value": "private_chat", "origin": "user_report"})
        r = self.evaluate(p)
        self.assertEqual(r["candidates"][0]["deferred_warrants"][0]["condition_state"], "unresolved_conflict")

    def test_conflicting_support_and_challenge_same_evidence_stays_visible(self):
        p = example()
        p["hypotheses"][0]["warrants"].append({"evidence_id": "e1", "role": "challenge", "rationale": "Alternative reading of the same evidence"})
        r = self.evaluate(p)
        self.assertEqual(r["candidates"][0]["status"], "active_pro_and_con_warrants_not_semantic_proof")
        self.assertEqual(r["candidates"][0]["supporting_warrants"][0]["evidence_id"],
                         r["candidates"][0]["challenging_warrants"][0]["evidence_id"])

    def test_model_proposals_in_context_are_excluded_even_if_exactly_matched(self):
        p = example()
        p["context_facts"][0]["origin"] = "model_hypothesis"
        p["context_facts"].append({"id": "new", "category": "channel", "value": "private_chat", "origin": "model_hypothesis"})
        r = self.evaluate(p)
        self.assertEqual(r["candidates"][2]["status"], "no_active_supporting_warrants")

    def test_no_silent_role_promotion_for_prior_interpretations(self):
        p = example()
        p["hypotheses"][3]["warrants"].append({"evidence_id": "e2", "role": "challenge", "rationale": "Quoted text is not actual private intent"})
        r = self.evaluate(p)
        self.assertEqual(r["candidates"][3]["status"], "active_con_warrants_only")
        self.assertEqual(len(r["candidates"][3]["excluded_warrants"]), 1)

    def test_validate_duplicate_hypothesis_id(self):
        p = example();p["hypotheses"][1]["id"] = p["hypotheses"][0]["id"]
        with self.assertRaises(ValueError):DeliberationCase.from_dict(p)

    def test_validate_duplicate_warrant(self):
        p = example();p["hypotheses"][0]["warrants"].append(deepcopy(p["hypotheses"][0]["warrants"][0]))
        with self.assertRaises(ValueError):DeliberationCase.from_dict(p)

    def test_validate_invalid_role(self):
        p = example();p["hypotheses"][0]["warrants"][0]["role"] = "verified"
        with self.assertRaises(ValueError):DeliberationCase.from_dict(p)

    def test_validate_missing_evidence_reference(self):
        p = example();p["hypotheses"][0]["warrants"][0]["evidence_id"] = "unknown"
        with self.assertRaises(ValueError):DeliberationCase.from_dict(p)

    def test_validate_unknown_context_category(self):
        p = example();p["hypotheses"][0]["warrants"][0]["conditions"][0]["category"] = "mind_reader"
        with self.assertRaises(ValueError):DeliberationCase.from_dict(p)

    def test_validate_malformed_proposer(self):
        p = example();p["hypotheses"][0]["proposed_by"] = "authoritative_model"
        with self.assertRaises(ValueError):DeliberationCase.from_dict(p)

    def test_validate_unexpected_injected_key(self):
        p = example();p["hypotheses"][0]["warrants"][0]["ignore_rules"] = True
        with self.assertRaises(ValueError):DeliberationCase.from_dict(p)

    def test_validate_invalid_concept(self):
        p = example();p["hypotheses"][0]["concept_ids"] = [800000]
        with self.assertRaises(ValueError):self.evaluate(p)

    def test_validate_incorrect_json_type_for_conditions(self):
        p = example();p["hypotheses"][0]["warrants"][0]["conditions"] = "channel:public_forum"
        with self.assertRaises(ValueError):DeliberationCase.from_dict(p)

    def test_validate_duplicate_condition_dimension(self):
        p = example();p["hypotheses"][0]["warrants"][0]["conditions"].append({"category": "channel", "value": "private_chat"})
        with self.assertRaises(ValueError):DeliberationCase.from_dict(p)

    def test_validate_interpretation_only_case(self):
        p = example();p["hypotheses"] = [p["hypotheses"][3]]
        r = self.evaluate(p)
        self.assertEqual(r["response_guidance"]["mode"], "withhold_unsupported_conclusion")

    def test_validate_more_than_sixteen_hypotheses(self):
        p = example();p["hypotheses"] = [deepcopy(p["hypotheses"][0]) for _ in range(17)]
        with self.assertRaises(ValueError):DeliberationCase.from_dict(p)

    def test_validate_more_than_sixty_four_evidence_items(self):
        p = example();p["scenario"]["evidence"] = [dict(id=f"e{x}", statement="X", origin="user_report") for x in range(65)]
        with self.assertRaises(ValueError):DeliberationCase.from_dict(p)

    def test_validate_more_than_maximum_evidence_text(self):
        p = example();p["scenario"]["evidence"][0]["statement"] = "A" * 4097
        with self.assertRaises(ValueError):DeliberationCase.from_dict(p)

    def test_validate_more_than_maximum_warrants(self):
        p = example();p["hypotheses"][0]["warrants"] = [dict(evidence_id="e1", role="support", rationale=f"Reason {x}") for x in range(33)]
        with self.assertRaises(ValueError):DeliberationCase.from_dict(p)

    def test_validate_duplicate_context_id(self):
        p = example();p["context_facts"].append(deepcopy(p["context_facts"][0]))
        with self.assertRaises(ValueError):DeliberationCase.from_dict(p)

    def test_default_corpus_integrity_persists(self):
        self.assertEqual(self.engine.graph.audit()["concept_count"], 2000)
        self.assertEqual(self.engine.graph.audit()["original_inventory_ids_not_present"], 0)

    def test_cli_deliberate_smoke(self):
        cmd = [sys.executable, "run.py", "deliberate", "examples/deliberation_public.json"]
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["schema"], "deliberation.v1")

    def test_cli_compare_smoke(self):
        cmd = [sys.executable, "run.py", "compare-deliberations",
               "examples/deliberation_public.json", "examples/deliberation_private.json"]
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(result.stdout)["candidate_changes"]), 2)


if __name__ == "__main__":
    unittest.main()
