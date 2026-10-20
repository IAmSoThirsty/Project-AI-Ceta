"""Demonstrate explicit in-memory supersession and stale-quote review.

Run: PYTHONPATH=src python examples/session_correction.py
"""
from societal_reasoning import CorrectionLedger, SocietalReasoner
from societal_reasoning.input_boundary import Utterance

reasoner = SocietalReasoner.starter()
ledger = CorrectionLedger("demo-local-session")
original = Utterance.capture("I might attend.", turn_id="u1")
correction = Utterance.capture("Correction: I will not attend.", turn_id="u2")
ledger.add_turn(original)
ledger.add_turn(correction)
ledger.correct("u1", "u2", start=12, end=len(correction.text))
assessment = reasoner.assess_text(original.text, turn_id="u1", session_id=ledger.session_id)
result = reasoner.review_draft(assessment, 'Your current position is "I might attend."', correction_ledger=ledger)
assert result["status"] == "hold"
assert result["issues"][-1]["code"] == "SUPERSEDED_USER_QUOTE_AS_CURRENT"
print("Historical statement preserved; stale current attribution held.")
ledger.purge()
