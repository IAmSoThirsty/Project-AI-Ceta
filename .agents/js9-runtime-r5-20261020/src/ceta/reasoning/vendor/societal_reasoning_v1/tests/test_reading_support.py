"""Hostile tests for candidate-reading validation without person labeling."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest

from societal_reasoning import SocietalReasoner
from societal_reasoning.deliberation import DeliberationCase, Hypothesis
from societal_reasoning.models import Evidence, Scenario
from societal_reasoning.reading_support import assess_reading_sources, source_language_signals

ROOT = Path(__file__).resolve().parents[1]


def ev(text="All AI coders are incompetent.", origin="quoted_material", ref="caption", id="e1"):
    return Evidence(id, text, origin, source_ref=ref)


def alignment(reading: str, *items: Evidence) -> dict:
    return assess_reading_sources(reading, tuple(items))


class UniversalLanguagePatternTests(unittest.TestCase):
    def test_group_quantifier_is_observation_about_words_not_people(self):
        signals = source_language_signals((ev(),))
        self.assertEqual(len(signals), 1)
        s = signals[0]
        self.assertEqual(s["surface_form"]["subject_phrase"], "AI coders")
        self.assertEqual(s["surface_form"]["predicate_phrase"], "incompetent")
        self.assertEqual(s["source_origin"], "quoted_material")
        self.assertEqual(s["evidence_sha256"], sha256(ev().statement.encode()).hexdigest())
        for claim in ("independently_verified_truth", "speaker_endorsement_proven",
                      "actual_social_function_proven", "personal_attribute_proven"):
            self.assertFalse(s[claim])

    def test_textual_reading_is_bounded_to_same_group(self):
        report = alignment("The supplied text makes a universal claim about AI coders.", ev())
        self.assertEqual(report["status"], "bounded_textual_generalization_matched")
        self.assertEqual(len(report["matches"]), 1)
        self.assertFalse(report["social_entailment_verified"])
        self.assertFalse(report["private_motive_or_attribute_verified"])

    def test_different_named_group_is_not_licensed(self):
        report = alignment("The supplied text makes a universal claim about all developers.", ev())
        self.assertEqual(report["status"], "textual_generalization_not_established")
        self.assertFalse(report["matches"])

    def test_supported_quantifiers(self):
        for text in ("All developers are beginners.", "Every developer is important.",
                     "No developers can attend.", "All members have rights."):
            with self.subTest(text=text):
                self.assertEqual(len(source_language_signals((ev(text),))), 1)

    def test_hedges_and_nonuniversals_do_not_pass(self):
        for text in (
            "Some AI coders are incompetent.", "Not all AI coders are incompetent.",
            "Maybe all AI coders are incompetent.", "All AI coders are probably incompetent.",
            "All AI coders are not incompetent.", "All AI coders are incompetent if careless.",
            "All AI coders are incompetent because they rely on tools.",
            '"All AI coders are incompetent."', "All coders are incompetent?",
            "All coders are incompetent; no exceptions.",
            "They said all AI coders are incompetent.",
        ):
            with self.subTest(text=text):
                self.assertEqual(source_language_signals((ev(text),)), [])

    def test_interpretation_is_never_observation(self):
        self.assertEqual(source_language_signals((ev(origin="interpretation"),)), [])
        report = alignment("The supplied text makes a universal claim about AI coders.",
                           ev(origin="interpretation"))
        self.assertEqual(report["status"], "textual_generalization_not_established")

    def test_user_report_is_still_only_source_wording(self):
        report = alignment("The supplied text makes a universal claim about AI coders.",
                           ev(origin="user_report"))
        self.assertEqual(report["status"], "bounded_textual_generalization_matched")
        self.assertTrue(report["source_text_only_not_factual_truth"])
        self.assertFalse(report["independent_authenticity_checked"])

    def test_unicode_and_long_hypothetical_are_not_guessed(self):
        for text in ("All developers are ‘brilliant’.", "All users are likely to be confused.",
                     "All users are competent, really."):
            with self.subTest(text=text):
                self.assertEqual(source_language_signals((ev(text),)), [])

    def test_source_order_is_canonical_by_identifier(self):
        one = ev(id="z", ref="source-z")
        two = ev("Every writer is a person.", id="a", ref="source-a")
        self.assertEqual([x["evidence_id"] for x in source_language_signals((one, two))], ["a", "z"])

    def test_duplicate_direct_evidence_rejected(self):
        with self.assertRaises(ValueError):
            source_language_signals((ev(id="same"), ev(id="same")))

    def test_resource_cap_is_applied(self):
        with self.assertRaises(ValueError):
            source_language_signals((ev("a" * 4097),))
        with self.assertRaises(ValueError):
            source_language_signals(tuple(ev(id=f"id-{i}") for i in range(65)))


class LiteralReadingAssessmentTests(unittest.TestCase):
    def test_plain_report_matches_reading_without_certifying_fact(self):
        report = alignment("Alex will attend the meeting.", ev("Alex will attend the meeting.", "user_report"))
        self.assertEqual(report["status"], "literal_reading_asserted_in_source_reports")
        self.assertEqual(report["check_method"], "restricted_literal_claim_alignment")
        self.assertEqual(report["matches"][0]["source_origin"], "user_report")
        self.assertFalse(report["social_entailment_verified"])
        self.assertTrue(report["source_text_only_not_factual_truth"])

    def test_direct_literal_opposition_is_detected(self):
        report = alignment("Alex will attend the meeting.", ev("Alex will not attend the meeting.", "user_report"))
        self.assertEqual(report["status"], "literal_reading_opposed_by_source_reports")
        self.assertEqual(len(report["oppositions"]), 1)

    def test_source_conflict_is_not_adjudicated(self):
        report = alignment("Alex will attend the meeting.",
                           ev("Alex will not attend the meeting.", "user_report", "person-1", "e1"),
                           ev("Alex will attend the meeting.", "external_record", "person-2", "e2"))
        self.assertEqual(report["status"], "opposed_source_reports_for_literal_reading")
        self.assertEqual([p["evidence_id"] for p in report["matches"]], ["e2"])
        self.assertEqual([p["evidence_id"] for p in report["oppositions"]], ["e1"])
        self.assertFalse(report["independent_authenticity_checked"])

    def test_modal_possibilities_are_not_opposed(self):
        report = alignment("Alex might attend the meeting.",
                           ev("Alex might not attend the meeting.", "user_report"))
        self.assertEqual(report["status"], "literal_reading_not_established_by_supplied_sources")
        self.assertEqual(report["oppositions"], [])
        self.assertEqual(report["unresolved_modality"][0]["reason"],
                         "positive_and_negative_possibilities_can_coexist")

    def test_hedge_is_not_a_definite_assertion(self):
        report = alignment("Alex will attend the meeting.",
                           ev("Alex will probably attend the meeting.", "external_record"))
        self.assertEqual(report["status"], "literal_reading_not_established_by_supplied_sources")

    def test_different_tense_does_not_count_as_support(self):
        report = alignment("Alex did attend the meeting.",
                           ev("Alex will attend the meeting.", "user_report"))
        self.assertEqual(report["status"], "literal_reading_not_established_by_supplied_sources")
        self.assertEqual(report["unresolved_modality"][0]["reason"], "modality_or_tense_differs")

    def test_different_time_and_event_remain_unmatched(self):
        report = alignment("Alex did attend on Tuesday.",
                           ev("Alex did attend on Wednesday.", "user_report"))
        self.assertEqual(report["status"], "literal_reading_not_established_by_supplied_sources")
        self.assertFalse(report["oppositions"])

    def test_quotes_are_text_not_an_assertion_by_recorder(self):
        report = alignment("Alex will attend the meeting.", ev("Alex will attend the meeting."))
        self.assertEqual(report["status"], "literal_reading_not_established_by_supplied_sources")
        self.assertFalse(report["matches"])

    def test_hypotheses_cannot_be_self_evidence(self):
        report = alignment("Alex will attend the meeting.",
                           ev("Alex will attend the meeting.", "interpretation"))
        self.assertEqual(report["status"], "literal_reading_not_established_by_supplied_sources")

    def test_named_person_private_state_is_not_promoted_from_source_text(self):
        r = alignment("Alex wants the team to lose.",
                      ev("Alex wants the team to lose.", "external_record"))
        self.assertEqual(r["status"], "third_party_private_state_not_independently_established")
        self.assertFalse(r["private_motive_or_attribute_verified"])

    def test_not_every_feeling_verb_is_a_human_private_state(self):
        r = alignment("The patch feels slow.",
                      ev("The patch feels slow.", "user_report"))
        self.assertEqual(r["status"], "unreviewable_social_or_open_language_reading")

    def test_direct_user_statement_is_not_renarrated_as_personal_diagnosis(self):
        r = alignment("I feel happy.", ev("I feel happy.", "user_report"))
        self.assertEqual(r["status"], "unreviewable_social_or_open_language_reading")

    def test_no_motive_claim_is_proven(self):
        report = alignment("Alex did intend to embarrass the team.",
                           ev("Alex did criticize the code.", "user_report"))
        self.assertEqual(report["status"], "unreviewable_social_or_open_language_reading")
        self.assertFalse(report["private_motive_or_attribute_verified"])

    def test_open_social_interpretation_is_not_disproved(self):
        report = alignment("The illustration may function as public ridicule.",
                           ev("All AI coders are incompetent."))
        self.assertEqual(report["status"], "unreviewable_social_or_open_language_reading")

    def test_open_language_complex_sentence_not_rewritten(self):
        report = alignment("The people may have felt mocked, depending on the context.", ev())
        self.assertEqual(report["status"], "unreviewable_social_or_open_language_reading")
        self.assertFalse(report["private_motive_or_attribute_verified"])

    def test_stable_under_evidence_reordering(self):
        pair = (ev("Alex will attend the meeting.", "user_report", "a", "b"),
                ev("Alex will not attend the meeting.", "external_record", "b", "a"))
        self.assertEqual(alignment("Alex will attend the meeting.", *pair),
                         alignment("Alex will attend the meeting.", *reversed(pair)))

    def test_empty_evidence_does_not_fabricate_source(self):
        report = alignment("Alex will attend the meeting.")
        self.assertEqual(report["status"], "literal_reading_not_established_by_supplied_sources")

    def test_bad_input_fails_closed(self):
        with self.assertRaises(ValueError):
            assess_reading_sources("", (ev(),))
        with self.assertRaises(ValueError):
            assess_reading_sources("x" * 4097, (ev(),))
        with self.assertRaises(ValueError):
            assess_reading_sources("Alex will attend.", [ev()])




class WorkProductWordingTests(unittest.TestCase):
    def test_specific_patch_evaluation_is_textual_not_verified(self):
        signal = source_language_signals((ev("The patch fails three unit tests.", "external_record"),))[0]
        self.assertEqual(signal["kind"], "explicit_work_product_evaluation_in_source_text")
        self.assertEqual(signal["surface_form"]["artifact_phrase"], "patch")
        self.assertEqual(signal["surface_form"]["detail"], "three unit tests")
        self.assertFalse(signal["independently_verified_truth"])

    def test_bounded_work_product_reading_matches_same_artifact(self):
        report = alignment("The supplied text evaluates the patch.",
                           ev("The patch passes three unit tests.", "user_report"))
        self.assertEqual(report["status"], "bounded_work_product_evaluation_matched")
        self.assertEqual(report["matches"][0]["surface_form"]["predicate"], "passes")
        self.assertTrue(report["reported_evaluation_is_not_verified_defect"])

    def test_other_artifact_is_not_promoted(self):
        report = alignment("The supplied text evaluates the code.",
                           ev("The patch fails three unit tests.", "user_report"))
        self.assertEqual(report["status"], "work_product_evaluation_not_established")

    def test_artifact_vocabulary_does_not_label_people(self):
        self.assertEqual(source_language_signals((ev("The developer fails three unit tests."),)), [])

    def test_unsupported_hedges_and_conditionals_defer(self):
        for text in ("The patch fails if not reviewed.", "Maybe the patch fails three tests.",
                     "The patch does not fail three tests.",
                     "The patch fails because of missing imports.",
                     "The patch failed a test; it still shipped.",
                     "The patch fails three tests?",
                     "The patch fails three tests, reportedly."):
            with self.subTest(text=text):
                self.assertEqual(source_language_signals((ev(text),)), [])

    def test_success_as_well_as_failure_is_evaluation_not_defect_proof(self):
        for verb in ("passed", "passes", "failed", "fails", "contains", "lacks"):
            with self.subTest(verb=verb):
                s = source_language_signals((ev(f"The code {verb} three checks."),))
                self.assertEqual(len(s), 1)
                self.assertFalse(s[0]["independently_verified_truth"])

    def test_group_and_artifact_wording_can_coexist_without_one_label(self):
        evidence = (ev("All AI coders are incompetent.", id="e1"),
                    ev("The patch fails three unit tests.", "user_report", "record-2", "e2"))
        signals = source_language_signals(evidence)
        self.assertEqual([s["kind"] for s in signals], [
            "explicit_universal_quantifier_in_source_text",
            "explicit_work_product_evaluation_in_source_text",
        ])
        for s in signals:
            self.assertFalse(s["actual_social_function_proven"])
            self.assertFalse(s["personal_attribute_proven"])

    def test_quoted_work_evaluation_not_certified_as_result(self):
        r = alignment("The supplied text evaluates the patch.",
                      ev("The patch passes three unit tests.", "quoted_material"))
        self.assertEqual(r["status"], "bounded_work_product_evaluation_matched")
        self.assertFalse(r["independent_authenticity_checked"])
        self.assertFalse(r["social_entailment_verified"])

    def test_interpretation_cannot_supply_technical_results(self):
        r = alignment("The supplied text evaluates the patch.",
                      ev("The patch fails three unit tests.", "interpretation"))
        self.assertEqual(r["status"], "work_product_evaluation_not_established")

    def test_artifact_signal_stale_when_wording_edited(self):
        before = alignment("The supplied text evaluates the patch.",
                           ev("The patch fails three unit tests."))
        after = alignment("The supplied text evaluates the patch.",
                          ev("The code fails three unit tests."))
        self.assertEqual(before["status"], "bounded_work_product_evaluation_matched")
        self.assertEqual(after["status"], "work_product_evaluation_not_established")


class DeliberationIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reasoner = SocietalReasoner.starter()

    def case(self, reading, statements):
        evidence = [{"id": f"e{i}", "statement": statement,
                     "origin": origin, "source_ref": f"record-{i}"}
                    for i, (statement, origin) in enumerate(statements)]
        return {"scenario": {"id": "proof-boundary", "question": "What does the supplied wording show?",
                             "evidence": evidence},
                "hypotheses": [{"id": "candidate", "reading": reading,
                                "proposed_by": "caller", "warrants": [
                                    {"evidence_id": "e0", "role": "support",
                                     "rationale": "Submitted warrant; not automatically proof"}]}]}

    def evaluate(self, row):
        return self.reasoner.deliberate(DeliberationCase.from_dict(row))

    def test_directly_opposed_reading_blocks_one_reading_guidance(self):
        out = self.evaluate(self.case("Alex will attend the meeting.",
                        [("Alex will not attend the meeting.", "user_report")]))
        candidate = out["candidates"][0]
        self.assertEqual(candidate["status"], "active_pro_warrants_not_semantic_proof")
        self.assertEqual(candidate["reading_source_alignment"]["status"],
                         "literal_reading_opposed_by_source_reports")
        self.assertEqual(out["response_guidance"]["mode"], "withhold_unsupported_conclusion")
        self.assertEqual(out["response_guidance"]["bounded_literal_readings_not_supported"], ["candidate"])

    def test_matched_literal_reading_can_be_considered_not_certified(self):
        out = self.evaluate(self.case("Alex will attend the meeting.",
                        [("Alex will attend the meeting.", "user_report")]))
        self.assertEqual(out["response_guidance"]["mode"], "consider_one_reading_without_ascribing_motives")
        self.assertEqual(out["candidates"][0]["reading_source_alignment"]["status"],
                         "literal_reading_asserted_in_source_reports")
        self.assertFalse(out["candidates"][0]["semantic_entailment_checked"])

    def test_textual_generalization_can_be_checked_not_personal_quality(self):
        out = self.evaluate(self.case("The supplied text makes a universal claim about AI coders.",
                              [("All AI coders are incompetent.", "quoted_material")]))
        c = out["candidates"][0]
        self.assertEqual(c["reading_source_alignment"]["status"], "bounded_textual_generalization_matched")
        self.assertFalse(c["reading_source_alignment"]["private_motive_or_attribute_verified"])
        self.assertEqual(out["source_language_signals"][0]["surface_form"]["subject_phrase"], "AI coders")
        self.assertFalse(c["semantic_entailment_checked"])

    def test_language_signal_not_person_label(self):
        result = self.evaluate(self.case("The author definitely hates these people.",
                               [("All AI coders are incompetent.", "quoted_material")]))
        self.assertEqual(result["candidates"][0]["reading_source_alignment"]["status"],
                         "third_party_private_state_not_independently_established")
        self.assertEqual(result["response_guidance"]["mode"], "withhold_unsupported_conclusion")
        self.assertEqual(result["response_guidance"]["private_state_readings_not_established"],
                         ["candidate"])
        self.assertFalse(result["source_language_signals"][0]["personal_attribute_proven"])

    def test_direct_constructor_duplicate_scenario_ids_rejected(self):
        scenario = Scenario(id="direct", question="Why?", evidence=(ev(id="same"), ev(id="same")))
        hypothesis = Hypothesis.from_dict({"id": "h", "reading": "Some reading", "proposed_by": "caller",
                                           "warrants": [{"evidence_id": "same", "role": "support", "rationale": "reported"}]})
        with self.assertRaises(ValueError):
            DeliberationCase(scenario=scenario, hypotheses=(hypothesis,))

    def test_old_cases_retained_without_changed_guidance(self):
        case = json.loads((ROOT / "examples" / "deliberation_public.json").read_text())
        out = self.evaluate(case)
        self.assertEqual(out["response_guidance"]["mode"], "present_alternatives_with_sources")
        self.assertTrue(all(not c["reading_source_alignment"]["social_entailment_verified"]
                            for c in out["candidates"]))

    def test_unknown_social_reading_does_not_trigger_auto_clarification(self):
        result = self.evaluate(self.case("This probably feels hostile to someone.",
                                       [("All AI coders are incompetent.", "quoted_material")]))
        self.assertEqual(result["response_guidance"]["mode"],
                         "consider_one_reading_without_ascribing_motives")
        self.assertTrue(result["response_guidance"]["clarification_is_not_automatically_required"])

    def test_two_distinct_evidence_types_do_not_force_exclusive_reading(self):
        row = self.case("The supplied text makes a universal claim about AI coders.",
                        [("All AI coders are incompetent.", "quoted_material"),
                         ("The patch fails three unit tests.", "external_record")])
        row["hypotheses"].append({"id": "specific-evaluation",
                                  "reading": "The supplied text evaluates the patch.",
                                  "proposed_by": "caller", "warrants": [
                                      {"evidence_id": "e1", "role": "support",
                                       "rationale": "This supplied text evaluates a specific work product"}]})
        out = self.evaluate(row)
        self.assertEqual(out["response_guidance"]["mode"], "present_alternatives_with_sources")
        self.assertEqual(len(out["source_language_signals"]), 2)
        self.assertEqual({c["reading_source_alignment"]["status"] for c in out["candidates"]}, {
            "bounded_textual_generalization_matched", "bounded_work_product_evaluation_matched"})

    def test_digest_changes_after_evidence_edit(self):
        old = self.case("The supplied text makes a universal claim about AI coders.",
                        [("All AI coders are incompetent.", "quoted_material")])
        new = deepcopy(old)
        new["scenario"]["evidence"][0]["statement"] = "Some AI coders are incompetent."
        result = self.reasoner.compare_deliberations(DeliberationCase.from_dict(old),
                                                      DeliberationCase.from_dict(new))
        self.assertIn("reading_source_alignment", result["candidate_changes"][0]["changed_fields"])
        self.assertTrue(result["evidence_changes"])


if __name__ == "__main__":
    unittest.main()
