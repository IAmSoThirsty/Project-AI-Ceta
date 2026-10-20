"""Attribution and intent protection: synthetic cases, no private transcripts."""

from __future__ import annotations

from dataclasses import replace
import json
import unittest

from societal_reasoning import SocietalReasoner
from societal_reasoning.claims import derive_objective, record_statements
from societal_reasoning.input_boundary import SourceSpan, Utterance
from societal_reasoning.response_review import review_draft


class ExactInputBoundary(unittest.TestCase):
    def test_unicode_source_is_not_normalized(self):
        utterance = Utterance.capture("Hey—I'm here. 🌊", turn_id="u:1")
        self.assertEqual(utterance.text, "Hey—I'm here. 🌊")
        self.assertEqual(len(utterance.sha256), 64)
        span = SourceSpan.capture(utterance, 4, 13)
        self.assertEqual(span.text, utterance.text[4:13])
        span.verify(utterance)

    def test_whitespace_is_exact(self):
        row = Utterance.capture("  A\tB\n")
        self.assertEqual(row.text, "  A\tB\n")

    def test_source_tampering_is_detected(self):
        a = Utterance.capture("my original text")
        span = SourceSpan.capture(a, 3, 11)
        with self.assertRaises(ValueError):
            span.verify(Utterance.capture("my changed text"))

    def test_hash_tamper_fails(self):
        a = Utterance.capture("my original text")
        span = SourceSpan.capture(a, 3, 11)
        with self.assertRaisesRegex(ValueError, "digest"):
            replace(span, sha256="0" * 64).verify(a)

    def test_invalid_source_spans(self):
        a = Utterance.capture("short")
        for args in ((0, 0), (-1, 3), (2, 6), (True, 4)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                SourceSpan.capture(a, *args)

    def test_blank_input_denied(self):
        for value in ("", " \n ", 123, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                Utterance.capture(value)

    def test_long_input_denied(self):
        with self.assertRaises(ValueError):
            Utterance.capture("a" * 65537)

    def test_direct_constructor_cannot_forge_digest(self):
        with self.assertRaises(ValueError):
            Utterance("turn-1", "user", "different text", "0" * 64)

    def test_direct_span_constructor_cannot_forge_digest(self):
        with self.assertRaises(ValueError):
            SourceSpan("turn-1", 0, 4, "word", "0" * 64)

    def test_invalid_identity_denied(self):
        for turn_id in ("two words", "", "../../session", "<script>"):
            with self.subTest(turn_id=turn_id), self.assertRaises(ValueError):
                Utterance.capture("text", turn_id=turn_id)


class ClaimSurfaceTests(unittest.TestCase):
    def statements(self, text):
        return record_statements(Utterance.capture(text))

    def test_question_is_not_attributed_as_opinion(self):
        row = self.statements("Why would someone do that?")[0]
        self.assertEqual(row.speech_act_proposal, "question")
        self.assertEqual(row.proposition_status, "unclassified_not_asserted")

    def test_command_preserves_requested_scope(self):
        rows = self.statements("Begin the implementation.")
        result = derive_objective(rows)
        self.assertEqual(result["text"], "Begin the implementation.")
        self.assertNotEqual(result["status"], "verified_intent")

    def test_casual_remark_is_not_a_task(self):
        rows = self.statements("I lost my job yesterday.")
        self.assertEqual(derive_objective(rows)["status"], "no_explicit_request_identified")

    def test_quoted_material_not_own_assertion(self):
        row = self.statements('"I hate you"')[0]
        self.assertEqual(row.speech_act_proposal, "quoted_material")

    def test_uncertainty_preserved(self):
        row = self.statements("I might attend.")[0]
        self.assertIn("might", row.modality_markers)
        self.assertEqual(row.source.text, "I might attend.")

    def test_negation_preserved(self):
        row = self.statements("I did not agree.")[0]
        self.assertIn("not", row.negation_markers)

    def test_quantity_preserved(self):
        row = self.statements("I coordinated for 70 hours.")[0]
        self.assertEqual(row.numeric_literals, ("70",))

    def test_conditionality_preserved(self):
        row = self.statements("If I have time, I may attend.")[0]
        self.assertIn("if", row.conditional_markers)
        self.assertIn("may", row.modality_markers)

    def test_correction_detected_as_proposal(self):
        row = self.statements("I meant tomorrow, not yesterday.")[0]
        self.assertEqual(row.speech_act_proposal, "possible_correction")

    def test_two_independent_turns_do_not_share_attribution(self):
        a = record_statements(Utterance.capture("I worked.", turn_id="u1", speaker="a"))[0]
        b = record_statements(Utterance.capture("I rested.", turn_id="u2", speaker="b"))[0]
        self.assertNotEqual(a.speaker, b.speaker)
        self.assertNotEqual(a.source.turn_id, b.source.turn_id)

    def test_no_private_emotion_added(self):
        row = self.statements("I lost my job.")[0]
        self.assertEqual(row.source.text, "I lost my job.")
        self.assertNotIn("angry", str(row.to_dict()))


class FreeTextAssessmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = SocietalReasoner.starter()

    def test_bare_statement_does_not_request_analysis(self):
        answer = self.engine.assess_text("I saw a funny meme.")
        self.assertEqual(answer["response_mode"], "no_requested_action_identified")
        self.assertEqual(answer["version"], "1")

    def test_question_has_unchanged_objective(self):
        answer = self.engine.assess_text("Why was this funny?")
        self.assertEqual(answer["objective"]["text"], "Why was this funny?")
        self.assertEqual(answer["response_mode"], "respond_to_extracted_request")

    def test_dictionary_word_discovery_non_material_does_not_interrogate(self):
        answer = self.engine.assess_text("What is the context of this paragraph?")
        self.assertEqual(answer["response_mode"], "respond_to_extracted_request")
        self.assertTrue(any(c["term"] == "context" for c in answer["semantics"]["candidates"]))
        self.assertEqual(answer["semantics"]["dictionary_consultation"], "offline_registry_links_no_live_dictionary_access")

    def test_material_ambiguity_held(self):
        answer = self.engine.assess_text("What is the context?", material_words=("context",))
        self.assertEqual(answer["response_mode"], "necessary_clarification")
        self.assertIn("context", answer["clarification_question"])

    def test_material_context_of_paragraph_resolves_without_asking(self):
        a = self.engine.assess_text("Explain the context of this paragraph.", material_words=("context",))
        self.assertEqual(a["response_mode"], "respond_to_extracted_request")
        self.assertEqual(a["semantics"]["declared_material_assessment"]["resolved"][0]["sense_id"], "discourse")
        self.assertEqual(a["semantics"]["declared_material_assessment"]["resolved"][0]["resolution_basis"], "transparent_narrow_phrase_pattern_not_general_understanding")

    def test_material_context_of_incident_resolves_without_asking(self):
        a = self.engine.assess_text("Explain the context of this incident.", material_words=("context",))
        self.assertEqual(a["response_mode"], "respond_to_extracted_request")
        self.assertEqual(a["semantics"]["declared_material_assessment"]["resolved"][0]["sense_id"], "setting")

    def test_unrelated_sense_selection_is_not_silently_applied(self):
        with self.assertRaises(ValueError):
            self.engine.assess_text("Explain the context.", selected_senses={"context": "setting"})

    def test_selected_word_sense_proceeds(self):
        answer = self.engine.assess_text("What is the context?", material_words=("context",), selected_senses={"context": "setting"})
        self.assertEqual(answer["response_mode"], "respond_to_extracted_request")
        self.assertEqual(answer["semantics"]["declared_material_assessment"]["resolved"][0]["sense_id"], "setting")

    def test_bad_sense_does_not_silently_choose(self):
        answer = self.engine.assess_text("What is the context?", material_words=("context",), selected_senses={"context": "invalid"})
        self.assertEqual(answer["response_mode"], "necessary_clarification")

    def test_absent_material_word_invalid(self):
        with self.assertRaises(ValueError):
            self.engine.assess_text("What happened?", material_words=("context",))

    def test_freeform_knowledge_is_advisory_not_a_person_label(self):
        result = self.engine.assess_text("I saw something strange.")
        self.assertIn("knowledge_considerations", result)
        self.assertEqual(result["knowledge_considerations"]["method"],
                         "bounded_lexical_retrieval_not_person_classification")
        self.assertTrue(any("retrieval does not establish" in x for x in result["known_limits"]))

    def test_tampered_assessment_rejected(self):
        a = self.engine.assess_text("I might attend.")
        a["utterance"]["text"] = "I will attend."
        with self.assertRaisesRegex(ValueError, "integrity"):
            self.engine.review_draft(a, "Maybe.")


class DraftReviewTests(unittest.TestCase):
    def review(self, user, draft, **kw):
        return review_draft(Utterance.capture(user), draft, **kw)

    def test_exact_quote_passes(self):
        result = self.review("I might attend.", 'You said "I might attend."')
        self.assertEqual(result["status"], "pass")

    def test_misquoted_user_held(self):
        result = self.review("I might attend.", 'You said "I will attend."')
        self.assertEqual(result["status"], "hold")
        self.assertEqual(result["issues"][0]["code"], "MISQUOTED_USER")

    def test_unreported_user_emotion_held(self):
        result = self.review("I lost my job.", "You are upset.")
        self.assertEqual(result["status"], "hold")
        self.assertEqual(result["issues"][0]["code"], "UNSUPPORTED_PERSON_STATE")

    def test_unreported_contracted_person_state_held(self):
        result = self.review("The meeting ended.", "You're angry.")
        self.assertEqual(result["status"], "hold")

    def test_unreported_person_sound_state_held(self):
        result = self.review("The meeting ended.", "You sound upset.")
        self.assertEqual(result["status"], "hold")

    def test_source_self_reported_contraction_can_be_repeated(self):
        result = self.review("I'm angry.", "You're angry.")
        self.assertEqual(result["status"], "pass")

    def test_self_reported_emotion_can_be_reported(self):
        result = self.review("I am upset.", "You are upset.")
        self.assertEqual(result["status"], "pass")

    def test_unreported_third_party_motive_held(self):
        result = self.review("We had a debate.", "He intends to humiliate you.")
        self.assertEqual(result["status"], "hold")

    def test_unverified_first_person_ghostwriting_review(self):
        result = self.review("I like documentaries.", "I am an expert developer.", writing_as_user=True)
        self.assertEqual(result["status"], "review_needed")

    def test_verbatim_first_person_allowed(self):
        result = self.review("I am learning.", "I am learning.", writing_as_user=True)
        self.assertEqual(result["status"], "pass")

    def test_unsupported_user_quantity_held(self):
        result = self.review("I worked 70 hours.", "You worked 80 hours.")
        self.assertEqual(result["status"], "hold")
        self.assertTrue(any(i["code"] == "UNSUPPORTED_USER_QUANTITY" for i in result["issues"]))

    def test_uncertainty_strengthening_review(self):
        result = self.review("I might attend.", "You will attend.")
        self.assertEqual(result["status"], "review_needed")

    def test_stated_negative_vs_positive_review(self):
        result = self.review("I do not agree.", "You do agree.")
        self.assertEqual(result["status"], "review_needed")

    def test_no_unsupported_warning_on_simple_answer(self):
        result = self.review("What time is it?", "I cannot see a local clock.")
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["review_scope"], "bounded_surface_attribution_checks_not_complete_semantic_verification")

    def test_empty_draft_rejected(self):
        with self.assertRaises(ValueError):
            self.review("Hello.", " ")

    def test_first_person_input_never_implies_permission_to_ghostwrite(self):
        result = self.review("I like documentaries.", "I am learning about films.")
        self.assertFalse(result["writing_as_user"])

    def test_output_is_json_serializable(self):
        a = self.review("I might attend.", "You will attend.")
        self.assertIn('"review_scope"', json.dumps(a))


if __name__ == "__main__":
    unittest.main()
