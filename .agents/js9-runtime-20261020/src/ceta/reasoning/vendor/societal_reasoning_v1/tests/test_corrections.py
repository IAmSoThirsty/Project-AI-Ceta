"""Local correction authority, cross-session boundaries, and stale quote guards."""
from __future__ import annotations

import unittest
from dataclasses import replace

from societal_reasoning.corrections import CorrectionLedger
from societal_reasoning.engine import SocietalReasoner
from societal_reasoning.input_boundary import Utterance


class CorrectionTests(unittest.TestCase):
    def setUp(self):
        self.ledger = CorrectionLedger("session-1")
        self.original = Utterance.capture("I might attend.", turn_id="t1", speaker="user")
        self.corrected = Utterance.capture("Correction: I will not attend.", turn_id="t2", speaker="user")
        self.ledger.add_turn(self.original)
        self.ledger.add_turn(self.corrected)

    def apply(self):
        return self.ledger.correct("t1", "t2", start=12, end=len(self.corrected.text))

    def test_correction_preserves_original(self):
        e = self.apply()
        a = self.ledger.active_state()
        self.assertEqual(e.corrected_source_span.text, "I will not attend.")
        self.assertEqual(a["superseded_turns"][0]["turn_id"], "t1")
        self.assertEqual(a["active_turn_ids"], ["t2"])
        self.assertEqual(self.original.text, "I might attend.")

    def test_chain_receipt(self):
        e = self.apply()
        self.assertEqual(len(e.chain_sha256), 64)
        self.assertEqual(e.sequence, 1)
        self.assertEqual(e.target_sha256, self.original.sha256)
        self.assertEqual(e.correction_sha256, self.corrected.sha256)

    def test_status_not_claim_of_fact(self):
        self.assertIn("not_independently_verified", self.apply().status)
        self.assertIn("not_independent_fact_verification", self.ledger.active_state()["epistemic_scope"])

    def test_no_implicit_persistent_memory(self):
        self.apply()
        self.assertEqual(self.ledger.active_state()["persistence"], "in_memory_only_no_implicit_person_profile")

    def test_current_quote_spoken_in_present_tense_is_held(self):
        self.apply()
        issues = self.ledger.review_current_attributions('You currently say "I might attend."')
        self.assertEqual(issues[0]["code"], "SUPERSEDED_USER_QUOTE_AS_CURRENT")

    def test_current_corrected_quote_is_not_held(self):
        self.apply()
        self.assertEqual(self.ledger.review_current_attributions('Your current position is "I will not attend."'), [])

    def test_stale_current_quote_is_held(self):
        self.apply()
        issues = self.ledger.review_current_attributions('Your current position is "I might attend."')
        self.assertEqual(issues[0]["code"], "SUPERSEDED_USER_QUOTE_AS_CURRENT")

    def test_historical_quote_is_permitted(self):
        self.apply()
        self.assertEqual(self.ledger.review_current_attributions('Earlier, you said "I might attend."'), [])
        self.assertEqual(self.ledger.review_current_attributions('You said "I might attend." before you corrected it.'), [])

    def test_truthful_unqualified_historical_quote_is_not_held(self):
        self.apply()
        self.assertEqual(self.ledger.review_current_attributions('You said "I might attend."'), [])

    def test_unattributed_restatement_not_falsely_reported(self):
        self.apply()
        self.assertEqual(self.ledger.review_current_attributions("I might attend."), [])

    def test_correction_cannot_retarget_old_statement(self):
        self.apply()
        self.ledger.add_turn(Utterance.capture("No, I meant Monday.", turn_id="t3", speaker="user"))
        with self.assertRaisesRegex(ValueError, "already been superseded"):
            self.ledger.correct("t1", "t3", start=11, end=17)

    def test_second_correction_supersedes_first_correction(self):
        self.apply()
        third = Utterance.capture("Correction: maybe next week.", turn_id="t3", speaker="user")
        self.ledger.add_turn(third)
        e2 = self.ledger.correct("t2", "t3", start=12, end=len(third.text))
        a = self.ledger.active_state()
        self.assertEqual(a["superseded_turns"][0]["effective_successor"],"t3")
        self.assertEqual(e2.sequence, 2)
        self.assertEqual(a["active_turn_ids"],["t3"])

    def test_cross_speaker_cannot_override(self):
        other = Utterance.capture("Correction: something else.", turn_id="t3", speaker="other")
        self.ledger.add_turn(other)
        with self.assertRaisesRegex(ValueError, "original speaker"):
            self.ledger.correct("t1", "t3", start=12, end=len(other.text))

    def test_unmarked_disagreement_cannot_be_assumed_correction(self):
        other = Utterance.capture("I disagree with that.", turn_id="t3", speaker="user")
        self.ledger.add_turn(other)
        with self.assertRaisesRegex(ValueError, "explicit correction marker"):
            self.ledger.correct("t1", "t3", start=0, end=len(other.text))

    def test_speaker_id_cannot_be_reused_differently(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.ledger.add_turn(Utterance.capture("Another statement.", turn_id="t1", speaker="someone"))

    def test_correction_after_target_not_before(self):
        with self.assertRaisesRegex(ValueError, "after"):
            self.ledger.correct("t2", "t1", start=0, end=8)

    def test_cannot_correct_self(self):
        with self.assertRaisesRegex(ValueError, "separate"):
            self.ledger.correct("t2", "t2", start=0, end=8)

    def test_must_reference_existing_turns(self):
        with self.assertRaisesRegex(ValueError, "exist"):
            self.ledger.correct("t1", "t100", start=0, end=10)

    def test_source_span_cannot_be_invented(self):
        with self.assertRaisesRegex(ValueError, "offsets"):
            self.ledger.correct("t1", "t2", start=0, end=1000)

    def test_source_construction_rejects_bad_digest(self):
        with self.assertRaises(ValueError):
            self.ledger.add_turn(replace(self.original, sha256="0" * 64))

    def test_reuse_correction_turn_rejected(self):
        self.apply()
        self.ledger.add_turn(Utterance.capture("A second original.", turn_id="t3", speaker="user"))
        with self.assertRaisesRegex(ValueError, "already used"):
            self.ledger.correct("t3", "t2", start=12, end=len(self.corrected.text))

    def test_purge_closes_and_drops_source_records(self):
        self.apply()
        res = self.ledger.purge()
        self.assertEqual(res, {"turns_purged": 2, "corrections_purged": 1})
        with self.assertRaisesRegex(ValueError, "closed"):
            self.ledger.active_state()
        with self.assertRaisesRegex(ValueError, "closed"):
            self.ledger.add_turn(Utterance.capture("New content.", turn_id="t3"))

    def test_cross_session_prevented_by_record_validation(self):
        self.apply()
        other = CorrectionLedger("other-session")
        other.add_turn(self.original)
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.ledger.verify_turn(Utterance.capture("Changed.", turn_id="t1"))
        self.assertNotEqual(self.ledger.session_id, other.session_id)

    def test_invalid_session_id_rejected(self):
        with self.assertRaisesRegex(ValueError, "session"):
            CorrectionLedger("../../outside")


class CorrectionFacadeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = SocietalReasoner.starter()

    def test_facade_allows_truthful_historical_quote_after_correction(self):
        ledger = CorrectionLedger("session-1")
        original = Utterance.capture("I might attend.", turn_id="t1")
        corrective = Utterance.capture("Correction: I will not attend.", turn_id="t2")
        ledger.add_turn(original)
        ledger.add_turn(corrective)
        ledger.correct("t1", "t2", start=12, end=len(corrective.text))
        a = self.engine.assess_text(original.text, turn_id="t1", session_id="session-1")
        reviewed = self.engine.review_draft(a, 'You said "I might attend."', correction_ledger=ledger)
        self.assertEqual(reviewed["status"], "pass")

    def test_ledger_blocks_stale_quote_in_draft(self):
        ledger = CorrectionLedger("session-1")
        old = Utterance.capture("I might attend.", turn_id="t1")
        new = Utterance.capture("Correction: I will not attend.", turn_id="t2")
        ledger.add_turn(old)
        ledger.add_turn(new)
        ledger.correct("t1", "t2", start=12, end=len(new.text))
        original_assessment = self.engine.assess_text(old.text, turn_id="t1", session_id="session-1")
        result = self.engine.review_draft(original_assessment, 'Your current position is "I might attend."',
                                          correction_ledger=ledger)
        self.assertEqual(result["status"],"hold")
        self.assertTrue(any(x["code"] == "SUPERSEDED_USER_QUOTE_AS_CURRENT"
                            for x in result["issues"]))

    def test_matching_source_required_to_apply_corrections(self):
        ledger = CorrectionLedger("session-2")
        ledger.add_turn(Utterance.capture("Other content.", turn_id="t1"))
        a = self.engine.assess_text("I might attend.", turn_id="t1", session_id="session-2")
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.engine.review_draft(a, "Sure.", correction_ledger=ledger)

    def test_no_ledger_behavior_still_passes(self):
        a = self.engine.assess_text("I might attend.")
        self.assertEqual(self.engine.review_draft(a, 'Your current position is "I might attend."')["status"], "pass")

    def test_session_identity_required_even_when_text_matches(self):
        ledger = CorrectionLedger("second-session")
        ledger.add_turn(Utterance.capture("I might attend.", turn_id="t1"))
        a = self.engine.assess_text("I might attend.", turn_id="t1", session_id="first-session")
        with self.assertRaisesRegex(ValueError, "session"):
            self.engine.review_draft(a, "Okay.", correction_ledger=ledger)

    def test_custom_speaker_correction_review(self):
        ledger = CorrectionLedger("session-1")
        old = Utterance.capture("I might attend.", turn_id="t1", speaker="human")
        new = Utterance.capture("Correction: I will not attend.", turn_id="t2", speaker="human")
        ledger.add_turn(old)
        ledger.add_turn(new)
        ledger.correct("t1", "t2", start=12, end=len(new.text))
        a = self.engine.assess_text(old.text, turn_id="t1", speaker="human", session_id="session-1")
        result = self.engine.review_draft(a, 'Your current position is "I might attend."', correction_ledger=ledger)
        self.assertEqual(result["status"], "hold")

    def test_nonledger_object_rejected(self):
        a = self.engine.assess_text("I might attend.")
        with self.assertRaisesRegex(ValueError, "CorrectionLedger"):
            self.engine.review_draft(a, "Okay.", correction_ledger={})


if __name__ == "__main__":
    unittest.main()
