import unittest

from societal_reasoning.context import ContextFactor, assemble_context, compare_context
from societal_reasoning.effects import effects_from_review
from societal_reasoning.engine import SocietalReasoner


class ContextContractTests(unittest.TestCase):
    def fact(self, category, value, *, key="c1", origin="user_report"):
        return {"id": key, "category": category, "value": value, "origin": origin, "source_ref": "u1"}

    def test_user_report_not_recast_as_independently_observed(self):
        a = assemble_context((self.fact("relationship", "friends"),))
        self.assertEqual(a["reported_or_proposed_factors"][0]["epistemic_status"], "reported_or_recorded_not_independently_verified")

    def test_model_hypothesis_cannot_be_reported_as_fact(self):
        a = assemble_context((self.fact("power", "unequal", origin="model_hypothesis"),))
        self.assertEqual(a["reported_or_proposed_factors"][0]["epistemic_status"], "model_proposal_not_observed")

    def test_conflicting_reports_preserved(self):
        a = assemble_context((self.fact("setting", "public"), self.fact("setting", "private", key="c2")))
        self.assertEqual(a["source_conflicts"][0]["status"], "unresolved_not_automatically_reconciled")

    def test_context_dimension_change_requires_reconsideration_not_a_label(self):
        before = (self.fact("relationship", "close friends"),)
        after = (self.fact("relationship", "unfamiliar people"),)
        a = compare_context(before, after)
        self.assertTrue(a["requires_reconsideration"])
        self.assertIn("participant motive", a["cannot_infer"])

    def test_irrelevant_descriptive_detail_does_not_force_reconsideration(self):
        before = (self.fact("other", "blue poster"),)
        after = (self.fact("other", "red poster"),)
        a = compare_context(before, after)
        self.assertFalse(a["requires_reconsideration"])

    def test_new_model_hypothesis_does_not_count_as_observed_change(self):
        before = (self.fact("audience", "private"),)
        after = before + (self.fact("power", "coercive", key="c2", origin="model_hypothesis"),)
        self.assertFalse(compare_context(before, after)["requires_reconsideration"])

    def test_conflicting_context_ids_rejected(self):
        with self.assertRaises(ValueError):
            assemble_context((self.fact("audience", "public"), self.fact("setting", "private")))

    def test_unsupported_origin_rejected(self):
        with self.assertRaises(ValueError):
            ContextFactor.from_dict(self.fact("relationship", "friends", origin="verified_user_motive"))

    def test_new_context_preserved_by_public_api(self):
        engine = SocietalReasoner.starter()
        result = engine.assess_text("What happened?", context_facts=(self.fact("audience", "public"),))
        self.assertEqual(result["context"]["reported_or_proposed_factors"][0]["value"], "public")
        self.assertNotIn("malicious", str(result))

    def test_no_factors_no_invention(self):
        a = assemble_context(())
        self.assertEqual(a["reported_or_proposed_factors"], [])


class PotentialEffectTests(unittest.TestCase):
    def test_no_problem_no_impact_conjecture(self):
        self.assertEqual(effects_from_review({"issues": []}), [])

    def test_potential_not_claimed_real(self):
        engine = SocietalReasoner.starter()
        a = engine.assess_text("I might attend.")
        b = engine.review_draft(a, 'You said "I will attend."')
        self.assertEqual(b["status"], "hold")
        self.assertEqual(b["possible_effects"][0]["status"], "hypothetical_not_observed")

    def test_bad_review_rejected(self):
        with self.assertRaises(ValueError):
            effects_from_review({"issues": "fake"})


if __name__ == "__main__":
    unittest.main()
