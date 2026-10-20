import tempfile
import unittest
from pathlib import Path

from truth_accountability import CheckResult, ClaimKind, TruthLedger, Verdict


class TruthLedgerTests(unittest.TestCase):
    def setUp(self):
        self.ledger = TruthLedger()

    def tearDown(self):
        self.ledger.db.close()

    def test_statement_is_preserved_verbatim(self):
        exact = "I asked you to understand, not to obey."
        ref = self.ledger.preserve_statement("speaker-a", exact)
        got = self.ledger.db.execute("SELECT exact_text FROM statements WHERE id=?", (ref,)).fetchone()
        self.assertEqual(got["exact_text"], exact)

    def test_direct_quote_is_not_world_fact(self):
        ref = self.ledger.preserve_statement("speaker-a", "The moon is cheese.")
        claim = self.ledger.propose_claim(ClaimKind.QUOTE, "The moon is cheese.", source_id=ref, source_quote="The moon is cheese.")
        self.assertEqual(self.ledger.status(claim), "VERIFIED_AS_VERBATIM_QUOTE")
        self.assertTrue(self.ledger.allowed_attributed_quotation(claim))
        self.assertFalse(self.ledger.allowed_factual_assertion(claim))

    def test_forged_quote_is_rejected(self):
        ref = self.ledger.preserve_statement("speaker-a", "I asked you to understand.")
        with self.assertRaises(ValueError):
            self.ledger.propose_claim(ClaimKind.QUOTE, "I demanded obedience.", source_id=ref, source_quote="I demanded obedience.")

    def test_inferred_motive_is_not_published_as_fact(self):
        ref = self.ledger.preserve_statement("speaker-a", "Please listen.")
        claim = self.ledger.propose_claim(ClaimKind.ATTRIBUTION, "You wanted power over me", source_id=ref)
        self.assertEqual(self.ledger.status(claim), "NEEDS_SPEAKER_OR_HUMAN_REVIEW")
        with self.assertRaises(PermissionError):
            self.ledger.publish(claim)

    def test_no_evidence_means_unverified(self):
        claim = self.ledger.propose_claim(ClaimKind.FACT, "An unknown moon exists")
        self.assertEqual(self.ledger.status(claim), "UNVERIFIED")
        with self.assertRaises(PermissionError):
            self.ledger.publish(claim)

    def test_verified_fact_requires_host_checker(self):
        claim = self.ledger.propose_claim(ClaimKind.FACT, "2 + 2 = 4")
        def checker(text, scope):
            return CheckResult(Verdict.SUPPORTS, "integer-arithmetic-test", "Python arithmetic establishes 2+2 == 4")
        self.ledger.run_fact_check(claim, "fixture-arithmetic", checker)
        self.assertEqual(self.ledger.status(claim), "SUPPORTED_BY_CHECK")
        self.ledger.publish(claim)

    def test_conflicting_checks_do_not_force_consensus(self):
        claim = self.ledger.propose_claim(ClaimKind.FACT, "Sample is positive", scope={"sample": "a"})
        self.ledger.run_fact_check(claim, "lab-a", lambda t,s: CheckResult(Verdict.SUPPORTS,"lab-a:1","Positive measurement"))
        self.ledger.run_fact_check(claim, "lab-b", lambda t,s: CheckResult(Verdict.REFUTES,"lab-b:1","Negative measurement"))
        self.assertEqual(self.ledger.status(claim), "DISPUTED")
        with self.assertRaises(PermissionError):
            self.ledger.publish(claim)

    def test_user_corrects_attribution_not_external_fact(self):
        ref = self.ledger.preserve_statement("speaker-a", "I am asking you to understand my reasoning.")
        claim = self.ledger.propose_claim(ClaimKind.ATTRIBUTION, "You demanded obedience", source_id=ref)
        self.ledger.record_prior_publication(claim)
        self.ledger.speaker_correction(claim,authenticated_speaker="speaker-a", clarification_exact="I asked for understanding, not obedience.")
        self.assertEqual(self.ledger.status(claim), "WITHDRAWN_AFTER_CORRECTION")
        self.assertIn("That attribution was wrong", self.ledger.acknowledgement(claim))

    def test_wrong_speaker_cannot_correct(self):
        ref = self.ledger.preserve_statement("speaker-a", "My report")
        claim = self.ledger.propose_claim(ClaimKind.ATTRIBUTION, "It was their motive", source_id=ref)
        with self.assertRaises(PermissionError):
            self.ledger.speaker_correction(claim,authenticated_speaker="speaker-b", clarification_exact="No")

    def test_user_clarification_cannot_verify_world_claim(self):
        claim = self.ledger.propose_claim(ClaimKind.FACT, "The bridge is safe")
        with self.assertRaises(TypeError):
            self.ledger.speaker_correction(claim,authenticated_speaker="speaker-a",clarification_exact="It is safe")

    def test_fact_error_correction_and_admission(self):
        claim = self.ledger.propose_claim(ClaimKind.FACT, "2 + 2 = 5")
        self.ledger.record_prior_publication(claim)
        self.ledger.run_fact_check(claim,"arithmetic",lambda t,s: CheckResult(Verdict.REFUTES,"calc:2plus2","2 + 2 equals 4, not 5","2 + 2 = 4"))
        self.assertEqual(self.ledger.status(claim), "REFUTED_BY_CHECK")
        self.ledger.correct_refuted_fact(claim)
        self.assertIn("I withdraw the earlier claim", self.ledger.acknowledgement(claim))

    def test_cannot_admit_without_recorded_correction(self):
        claim = self.ledger.propose_claim(ClaimKind.FACT, "A speculative idea")
        with self.assertRaises(ValueError):
            self.ledger.acknowledgement(claim)

    def test_hypothesis_does_not_become_fact(self):
        claim = self.ledger.propose_claim(ClaimKind.HYPOTHESIS, "Spacetime may emerge from deeper relations")
        self.assertEqual(self.ledger.status(claim), "HYPOTHESIS_ONLY")
        self.assertFalse(self.ledger.allowed_factual_assertion(claim))

    def test_unknown_is_retained_for_future_inquiry(self):
        claim = self.ledger.propose_claim(ClaimKind.FACT, "Unclassified observation has cause X")
        self.assertIn(claim, [cid for cid,_ in self.ledger.unresolved_claims()])

    def test_persistent_correction_survives_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "ledger.sqlite3"
            first = TruthLedger(db)
            ref = first.preserve_statement("speaker-a","Please understand")
            claim = first.propose_claim(ClaimKind.ATTRIBUTION,"Speaker demanded compliance",source_id=ref)
            first.speaker_correction(claim,authenticated_speaker="speaker-a",clarification_exact="I requested understanding")
            first.db.close()
            reopened = TruthLedger(db)
            self.assertEqual(reopened.status(claim),"WITHDRAWN_AFTER_CORRECTION")
            self.assertIn("I requested understanding",reopened.acknowledgement(claim))
            reopened.db.close()

    def test_correction_does_not_invent_prior_publication(self):
        ref = self.ledger.preserve_statement("speaker-a", "I requested understanding")
        claim = self.ledger.propose_claim(ClaimKind.ATTRIBUTION,"You demanded obedience", source_id=ref)
        self.ledger.speaker_correction(claim, authenticated_speaker="speaker-a", clarification_exact="I requested understanding")
        ack = self.ledger.acknowledgement(claim)
        self.assertIn("proposed but unpublished", ack)
        self.assertIn("No prior public assertion is claimed", ack)

    def test_untrusted_text_cannot_execute_as_sql(self):
        payload = "'); DROP TABLE statements; --"
        ref = self.ledger.preserve_statement("speaker-a", payload)
        self.assertEqual(self.ledger.db.execute("SELECT exact_text FROM statements WHERE id=?",(ref,)).fetchone()[0],payload)


if __name__ == "__main__":
    unittest.main()
