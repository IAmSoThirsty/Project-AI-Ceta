"""Adversarial tests for the bounded source-claim premise checker."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import unittest

from societal_reasoning import DeliberationCase, SocietalReasoner
from societal_reasoning.deliberation import Warrant
from societal_reasoning.models import Evidence
from societal_reasoning.semantic_support import WarrantPremise, check_premise


def digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def evidence(statement="Alex will not attend the meeting.", origin="user_report"):
    return Evidence.from_dict({"id": "e1", "statement": statement, "origin": origin, "source_ref": "reported-1"})


def literal(text="Alex will not attend the meeting.", *, statement="Alex will not attend the meeting."):
    return WarrantPremise.from_dict({"kind": "literal_assertion", "text": text,
                                    "evidence_sha256": digest(statement)})


def excerpt(text="will not attend", *, statement="Alex will not attend the meeting."):
    at = statement.index(text)
    return WarrantPremise.from_dict({"kind": "verbatim_span", "text": text,
                                    "evidence_sha256": digest(statement),
                                    "start": at, "end": at + len(text)})


def case(statement="Alex will not attend the meeting.", kind="literal_assertion",
         claim="Alex will not attend the meeting.", role="support", origin="user_report"):
    if kind == "literal_assertion":
        premise = literal(claim, statement=statement).to_dict()
    else:
        premise = excerpt(claim, statement=statement).to_dict()
    return {"scenario": {"id": "semantic-premise-demo", "question": "What does the text establish?",
                         "evidence": [{"id": "e1", "statement": statement, "origin": origin,
                                       "source_ref": "reported-1"}]},
            "hypotheses": [{"id": "reading-a", "reading": "A person's intention is proposed, not established.",
                            "proposed_by": "caller", "warrants": [
                                {"evidence_id": "e1", "role": role,
                                 "rationale": "The caller says this evidence justifies the reading; unverified.",
                                 "premise": premise}]}]}


class LiteralParserTests(unittest.TestCase):
    def test_same_literal_proposition_is_source_asserted_not_factual_proof(self):
        check = check_premise(evidence(), literal())
        self.assertEqual(check["status"], "source_asserts_literal_proposition")
        self.assertEqual(check["source_atom"]["subject"], "alex")
        self.assertEqual(check["source_atom"]["polarity"], "negative")
        self.assertFalse(check["factual_truth_checked"])
        self.assertFalse(check["social_inference_validated"])
        self.assertFalse(check["external_authenticity_checked"])

    def test_exact_source_digest_exposed(self):
        check = check_premise(evidence(), literal())
        self.assertEqual(check["actual_source_sha256"], digest(evidence().statement))
        self.assertEqual(check["expected_source_sha256"], digest(evidence().statement))

    def test_explicit_will_not_versus_will_is_opposed(self):
        self.assertEqual(check_premise(evidence(), literal("Alex will attend the meeting."))["status"],
                         "source_explicitly_opposes_claim")

    def test_explicit_did_not_versus_did_is_opposed(self):
        s = "Alex did not attend the meeting."
        self.assertEqual(check_premise(evidence(s), literal("Alex did attend the meeting.", statement=s))["status"],
                         "source_explicitly_opposes_claim")

    def test_lexically_similar_actor_cannot_be_reassigned(self):
        self.assertEqual(check_premise(evidence(), literal("Jordan will not attend the meeting."))["status"],
                         "actor_scope_mismatch")

    def test_predicate_not_paraphrased(self):
        self.assertEqual(check_premise(evidence(), literal("Alex will not visit the meeting."))["status"],
                         "predicate_or_scope_mismatch")

    def test_object_not_paraphrased(self):
        self.assertEqual(check_premise(evidence(), literal("Alex will not attend the ceremony."))["status"],
                         "predicate_or_scope_mismatch")

    def test_time_not_assumed_equal(self):
        s = "Alex will attend on Tuesday."
        p = literal("Alex will attend on Wednesday.", statement=s)
        self.assertEqual(check_premise(evidence(s), p)["status"], "predicate_or_scope_mismatch")

    def test_different_modals_not_equal(self):
        s = "Alex might attend the meeting."
        p = literal("Alex will attend the meeting.", statement=s)
        self.assertEqual(check_premise(evidence(s), p)["status"], "modality_mismatch")

    def test_possibility_and_negated_possibility_not_contradictions(self):
        for modal in ("may", "might", "could", "can"):
            s = f"Alex {modal} not attend the meeting."
            p = literal(f"Alex {modal} attend the meeting.", statement=s)
            with self.subTest(modal=modal):
                self.assertEqual(check_premise(evidence(s), p)["status"], "modal_polarity_undetermined")

    def test_modal_variants_are_literally_preserved(self):
        for modal in ("may", "might", "could", "can", "did", "does", "do", "will"):
            s = f"Alex {modal} attend the meeting."
            with self.subTest(modal=modal):
                self.assertEqual(check_premise(evidence(s), literal(s, statement=s))["status"],
                                 "source_asserts_literal_proposition")

    def test_inline_conditional_is_not_a_simple_assertion(self):
        s = "Alex will attend if invited."
        self.assertEqual(check_premise(evidence(s), literal("Alex will attend.", statement=s))["status"],
                         "unreviewable_source_syntax")

    def test_reported_speech_is_not_direct_assertion(self):
        s = "They said they will attend."
        self.assertEqual(check_premise(evidence(s), literal("They will attend.", statement=s))["status"],
                         "unreviewable_source_syntax")

    def test_thinking_is_not_assertion_of_embedded_claim(self):
        s = "I think I will attend."
        self.assertEqual(check_premise(evidence(s), literal("I will attend.", statement=s))["status"],
                         "unreviewable_source_syntax")

    def test_quotes_are_not_assigned_to_the_quoting_speaker(self):
        s = '"Alex will attend."'
        self.assertEqual(check_premise(evidence(s), literal("Alex will attend.", statement=s))["status"],
                         "unreviewable_source_syntax")

    def test_quoted_material_origin_requires_attribution_review(self):
        s = "Alex will attend."
        self.assertEqual(check_premise(evidence(s, origin="quoted_material"), literal(s, statement=s))["status"],
                         "unreviewable_attribution")

    def test_question_cannot_establish_answer(self):
        s = "Alex will attend?"
        self.assertEqual(check_premise(evidence(s), literal("Alex will attend.", statement=s))["status"],
                         "unreviewable_source_syntax")

    def test_hedge_cannot_be_hidden(self):
        for s in ("Maybe Alex will attend.", "Alex will probably attend.", "Alex will reportedly attend."):
            with self.subTest(s=s):
                self.assertEqual(check_premise(evidence(s), literal("Alex will attend.", statement=s))["status"],
                                 "unreviewable_source_syntax")

    def test_trailing_second_clause_does_not_pass(self):
        s = "Alex will attend. Jordan will not attend."
        self.assertEqual(check_premise(evidence(s), literal("Alex will attend.", statement=s))["status"],
                         "unreviewable_source_syntax")

    def test_stale_binding_detected(self):
        old = literal("Alex will attend.", statement="Alex will attend.")
        self.assertEqual(check_premise(evidence("Alex will not attend."), old)["status"],
                         "stale_source_binding")

    def test_prior_interpretation_not_promoted(self):
        self.assertEqual(check_premise(evidence(origin="interpretation"), literal())["status"],
                         "excluded_prior_interpretation")


class ExactSpanTests(unittest.TestCase):
    def test_exact_offsets_are_proven(self):
        check = check_premise(evidence(), excerpt())
        self.assertEqual(check["status"], "source_text_matched")
        self.assertEqual(check["matched_span"]["text"], "will not attend")
        self.assertFalse(check["social_inference_validated"])

    def test_exact_case_required(self):
        source = "Alex will not attend the meeting."
        p = WarrantPremise("verbatim_span", "Will not attend", digest(source), 5, 20)
        self.assertEqual(check_premise(evidence(), p)["status"], "not_established")

    def test_repeated_substring_wrong_span_does_not_count(self):
        s = "go, go, go"
        p = WarrantPremise("verbatim_span", "go", digest(s), 3, 5)
        self.assertEqual(check_premise(evidence(s), p)["status"], "not_established")

    def test_matching_span_in_quote_is_not_truth(self):
        s = 'They quoted "Alex secretly hates the group" as a claim.'
        p = excerpt("Alex secretly hates the group", statement=s)
        check = check_premise(evidence(s, origin="quoted_material"), p)
        self.assertEqual(check["status"], "source_text_matched")
        self.assertFalse(check["factual_truth_checked"])

    def test_unicode_offsets_use_character_positions(self):
        s = "\u03c0 and laughter \u2014 what is said?"
        p = excerpt("laughter", statement=s)
        self.assertEqual(check_premise(evidence(s), p)["status"], "source_text_matched")

    def test_premise_sha_mutation_blocks_matching_span(self):
        s = "Alex will attend."
        p = excerpt("will attend", statement=s)
        self.assertEqual(check_premise(evidence("Alex will not attend."), p)["status"], "stale_source_binding")

    def test_direct_invalid_span_rejected(self):
        s = "abc"
        with self.assertRaises(ValueError):
            WarrantPremise("verbatim_span", "a", digest(s), True, 1)

    def test_span_length_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            WarrantPremise("verbatim_span", "word", "a" * 64, 0, 7)

    def test_unexpected_field_rejected(self):
        row = excerpt().to_dict()
        row["identity_verified"] = True
        with self.assertRaises(ValueError):
            WarrantPremise.from_dict(row)

    def test_bool_offsets_not_allowed(self):
        with self.assertRaises(ValueError):
            WarrantPremise("verbatim_span", "x", "a" * 64, False, 1)

    def test_wrong_digest_type_and_case_rejected(self):
        for h in ("A" * 64, "x" * 64, 1234):
            with self.subTest(h=h), self.assertRaises(ValueError):
                WarrantPremise.from_dict({"kind": "literal_assertion", "text": "Alex will attend.",
                                          "evidence_sha256": h})

    def test_invalid_literal_premise_is_rejected(self):
        for text in ("Alex attended.", "He might be angry if mocked.",
                     '"Alex will attend."', "I think I will attend.", "I will attend?"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                WarrantPremise("literal_assertion", text, "a" * 64)


class DeliberationWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = SocietalReasoner.starter()

    def evaluate(self, document):
        return self.engine.deliberate(DeliberationCase.from_dict(document))

    def test_matching_literal_active_but_not_social_proof(self):
        result = self.evaluate(case())
        candidate = result["candidates"][0]
        self.assertEqual(candidate["status"], "active_pro_warrants_not_semantic_proof")
        self.assertEqual(candidate["bounded_premises_verified"], 1)
        check = candidate["supporting_warrants"][0]["premise_check"]
        self.assertEqual(check["status"], "source_asserts_literal_proposition")
        self.assertFalse(candidate["semantic_entailment_checked"])
        self.assertFalse(candidate["supporting_warrants"][0]["rationale_semantically_verified"])

    def test_opposed_polarity_is_excluded_not_support(self):
        result = self.evaluate(case(claim="Alex will attend the meeting."))
        candidate = result["candidates"][0]
        self.assertEqual(candidate["status"], "no_active_supporting_warrants")
        self.assertEqual(candidate["excluded_warrants"][0]["premise_check"]["status"],
                         "source_explicitly_opposes_claim")
        self.assertEqual(result["response_guidance"]["mode"], "withhold_unsupported_conclusion")

    def test_wrong_actor_deferred(self):
        result = self.evaluate(case(claim="Jordan will not attend the meeting."))
        candidate = result["candidates"][0]
        self.assertEqual(candidate["status"], "no_active_supporting_warrants")
        self.assertEqual(candidate["deferred_warrants"][0]["premise_check"]["status"], "actor_scope_mismatch")

    def test_literal_excerpt_activates_only_source_presence(self):
        result = self.evaluate(case(kind="verbatim_span", claim="will not attend"))
        check = result["candidates"][0]["supporting_warrants"][0]["premise_check"]
        self.assertEqual(check["status"], "source_text_matched")
        self.assertFalse(check["social_inference_validated"])

    def test_different_source_text_invalidates_bound_warrant(self):
        document = case()
        document["scenario"]["evidence"][0]["statement"] = "Alex will attend the meeting."
        result = self.evaluate(document)
        self.assertEqual(result["candidates"][0]["excluded_warrants"][0]["premise_check"]["status"],
                         "stale_source_binding")

    def test_unquoted_assertion_source_with_quoted_material_origin_is_deferred(self):
        document = case(origin="quoted_material")
        result = self.evaluate(document)
        self.assertEqual(result["candidates"][0]["deferred_warrants"][0]["premise_check"]["status"],
                         "unreviewable_attribution")

    def test_prior_interpretation_always_excluded(self):
        document = case(origin="interpretation")
        result = self.evaluate(document)
        self.assertEqual(result["candidates"][0]["status"], "no_active_supporting_warrants")
        self.assertEqual(result["candidates"][0]["excluded_warrants"][0]["premise_check"]["status"],
                         "excluded_prior_interpretation")

    def test_source_quote_remains_quote_even_if_cited_as_challenge(self):
        document = case(kind="verbatim_span", claim="will not attend", role="challenge")
        result = self.evaluate(document)
        self.assertEqual(result["candidates"][0]["status"], "active_con_warrants_only")
        self.assertEqual(result["candidates"][0]["bounded_premises_verified"], 1)
        self.assertEqual(result["response_guidance"]["mode"], "withhold_unsupported_conclusion")

    def test_no_premise_legacy_is_retained_unverified(self):
        document = case()
        document["hypotheses"][0]["warrants"][0].pop("premise")
        result = self.evaluate(document)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["status"], "active_pro_warrants_not_semantic_proof")
        self.assertEqual(candidate["supporting_warrants"][0]["premise_check"]["status"], "not_requested")
        self.assertEqual(candidate["bounded_premises_verified"], 0)

    def test_context_only_comparison_preserves_semantic_check(self):
        document = case()
        other = deepcopy(document)
        other["scenario"]["evidence"][0]["statement"] = "Alex will attend the meeting."
        delta = self.engine.compare_deliberations(DeliberationCase.from_dict(document),
                                                   DeliberationCase.from_dict(other))
        self.assertEqual(len(delta["evidence_changes"]), 1)
        self.assertEqual(delta["candidate_changes"][0]["before_status"], "active_pro_warrants_not_semantic_proof")
        self.assertEqual(delta["candidate_changes"][0]["after_status"], "no_active_supporting_warrants")

    def test_direct_constructor_rejects_bogus_premise(self):
        row = case()
        w = DeliberationCase.from_dict(row).hypotheses[0].warrants[0]
        with self.assertRaises(ValueError):
            Warrant(w.evidence_id, w.role, w.rationale, w.conditions, {"kind": "literal_assertion"})

    def test_schema_invalid_premise_is_rejected(self):
        document = case()
        document["hypotheses"][0]["warrants"][0]["premise"]["kind"] = "semantic_entailment_proven"
        with self.assertRaises(ValueError):
            DeliberationCase.from_dict(document)

    def test_proposal_only_warrant_never_grants_factual_verdict(self):
        document = case()
        document["hypotheses"][0]["reading"] = "Alex definitely despises the attendees."
        result = self.evaluate(document)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["conclusion_status"], "proposed_interpretation_not_factual_finding")
        self.assertFalse(candidate["semantic_entailment_checked"])
        self.assertEqual(result["claim_boundary"], "warrants_and_readings_are_proposals_not_independent_factual_findings")


if __name__ == "__main__":
    unittest.main()


class CrossEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = SocietalReasoner.starter()

    def with_second_report(self, *, text="Alex will attend the meeting.", origin="external_record", ref="reported-2"):
        document = case()
        document["scenario"]["evidence"].append({"id": "e2", "statement": text, "origin": origin,
                                                    "source_ref": ref})
        return self.engine.deliberate(DeliberationCase.from_dict(document))

    def test_opposed_reports_visible_without_assigning_blame(self):
        result = self.with_second_report()
        conflicts = result["literal_source_oppositions"]
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["evidence_ids"], ["e2", "e1"])
        self.assertEqual(conflicts[0]["status"], "opposed_literal_source_reports_not_a_factual_verdict")
        self.assertFalse(conflicts[0]["same_event_or_time_independently_established"])
        self.assertFalse(conflicts[0]["subject_coreference_independently_established"])
        self.assertEqual(result["response_guidance"]["mode"], "present_alternatives_with_sources")
        self.assertTrue(result["response_guidance"]["opposed_report_review_needed"])

    def test_does_not_pick_a_winner_from_two_reports(self):
        result = self.with_second_report()
        self.assertEqual(result["candidates"][0]["conclusion_status"],
                         "proposed_interpretation_not_factual_finding")
        self.assertFalse(result["candidates"][0]["semantic_entailment_checked"])

    def test_quoted_alternative_is_not_assumed_authoritative(self):
        result = self.with_second_report(origin="quoted_material")
        self.assertEqual(result["literal_source_oppositions"], [])

    def test_prior_interpretation_cannot_conflict_as_source(self):
        result = self.with_second_report(origin="interpretation")
        self.assertEqual(result["literal_source_oppositions"], [])

    def test_same_source_citation_does_not_claim_independent_confirmation(self):
        result = self.with_second_report(ref="reported-1")
        self.assertEqual(result["literal_source_oppositions"][0]["source_refs"],
                         ["reported-1", "reported-1"])
        self.assertFalse(result["literal_source_oppositions"][0]["external_source_authenticity_checked"])

    def test_differing_modal_is_not_an_explicit_conflict(self):
        result = self.with_second_report(text="Alex might attend the meeting.")
        self.assertEqual(result["literal_source_oppositions"], [])

    def test_possibility_polarities_do_not_conflict(self):
        d = case(statement="Alex might not attend the meeting.",
                 claim="Alex might not attend the meeting.")
        d["scenario"]["evidence"].append({"id": "e2", "statement": "Alex might attend the meeting.",
                                            "origin": "external_record", "source_ref": "reported-2"})
        r = self.engine.deliberate(DeliberationCase.from_dict(d))
        self.assertEqual(r["literal_source_oppositions"], [])

    def test_different_names_do_not_conflict(self):
        result = self.with_second_report(text="Jordan will attend the meeting.")
        self.assertEqual(result["literal_source_oppositions"], [])

    def test_different_dates_do_not_conflict(self):
        d = case(statement="Alex will not attend on Tuesday.", claim="Alex will not attend on Tuesday.")
        d["scenario"]["evidence"].append({"id": "e2", "statement": "Alex will attend on Wednesday.",
                                            "origin": "user_report"})
        r = self.engine.deliberate(DeliberationCase.from_dict(d))
        self.assertEqual(r["literal_source_oppositions"], [])

    def test_report_comparison_records_new_opposition(self):
        doc = case()
        updated = deepcopy(doc)
        updated["scenario"]["evidence"].append({"id": "e2", "statement": "Alex will attend the meeting.",
                                                  "origin": "external_record"})
        delta = self.engine.compare_deliberations(DeliberationCase.from_dict(doc),
                                                   DeliberationCase.from_dict(updated))
        self.assertEqual(delta["literal_oppositions_before"], [])
        self.assertEqual(len(delta["literal_oppositions_after"]), 1)
        self.assertEqual(delta["response_mode_after"], "present_alternatives_with_sources")

    def test_rejects_too_many_records_for_direct_helper(self):
        from societal_reasoning.semantic_support import find_opposed_source_assertions
        with self.assertRaises(ValueError):
            find_opposed_source_assertions(tuple(evidence() for _ in range(65)))


class DirectConstructionTests(unittest.TestCase):
    def test_direct_evidence_cannot_spoof_origin(self):
        with self.assertRaises(ValueError):
            Evidence(id="x", statement="Alex will attend.", origin="verified_truth")

    def test_direct_evidence_cannot_hide_source_in_invalid_type(self):
        with self.assertRaises(ValueError):
            Evidence(id="x", statement="Alex will attend.", origin="user_report", source_ref=123)

    def test_direct_evidence_rejects_unvalidated_cue_list(self):
        with self.assertRaises(ValueError):
            Evidence(id="x", statement="Alex will attend.", origin="user_report", cues=["foo"])

    def test_rejects_null_offsets_on_literal_contract(self):
        row = literal("Alex will attend.", statement="Alex will attend.").to_dict()
        row["start"] = None
        row["end"] = None
        with self.assertRaises(ValueError):
            WarrantPremise.from_dict(row)

    def test_imported_public_premise_is_available(self):
        from societal_reasoning import WarrantPremise as PublicPremise
        self.assertIs(PublicPremise, WarrantPremise)
