import json
import unittest
from truth_accountability import (
    GovernedModelBridge, GovernedTruthCore, VerificationRegistry,
    VerifierSpec, bounded_arithmetic, arithmetic_only_policy,
)


class BridgeTest(unittest.TestCase):
    def setUp(self):
        registry=VerificationRegistry()
        registry.register(VerifierSpec("arithmetic","arith",bounded_arithmetic))
        self.core=GovernedTruthCore(registry=registry)
        self.bridge=GovernedModelBridge(self.core,arithmetic_only_policy)

    def tearDown(self):
        self.core.close()

    def test_valid_arithmetic_generated_as_supported(self):
        answer=self.bridge.process(json.dumps({"kind":"fact","text":"7 * 8 = 56"}))
        self.assertTrue(answer.established_fact)
        self.assertEqual(answer.decision,"SUPPORTED_BY_CHECK")
        self.assertFalse(answer.verified_delivery)

    def test_false_arithmetic_not_published_as_fact(self):
        answer=self.bridge.process(json.dumps({"kind":"fact","text":"7 * 8 = 57"}))
        self.assertFalse(answer.established_fact)
        self.assertEqual(answer.decision,"REFUTED_BY_CHECK")
        self.assertIn("contradicted",answer.text)

    def test_model_cannot_downgrade_high_stakes_policy(self):
        answer=self.bridge.process(json.dumps({"kind":"fact","text":"The bridge is safe",
                                                "policy":"standard"}))
        persisted=self.core._proposal(answer.claim_id)
        self.assertEqual(persisted["evidence_policy"],"high_stakes")

    def test_model_cannot_select_its_own_fact_scope(self):
        answer=self.bridge.process(json.dumps({"kind":"fact","text":"The bridge is safe",
            "scope":{"domain":"medical","time":"tomorrow"}}),
            trusted_scope={"domain":"structural_engineering","time":"today"})
        persisted=self.core._proposal(answer.claim_id)
        self.assertEqual(json.loads(persisted["scope_json"]),
                         {"domain":"structural_engineering","time":"today"})

    def test_nonsupported_topic_is_not_proven_by_math_checker(self):
        answer=self.bridge.process(json.dumps({"kind":"fact","text":"This neighborhood is safe"}))
        self.assertEqual(answer.decision,"UNVERIFIED")
        self.assertNotIn("Evidence supports",answer.text)

    def test_inaccurate_attribution_never_automatically_published(self):
        original="I asked you to understand."
        src=self.core.preserve("user",original)
        answer=self.bridge.process(json.dumps({"kind":"paraphrase","text":"You demanded obedience",
                                       "source_id":src,"span":[0,len(original)]}),current_source_id=src)
        self.assertEqual(answer.decision,"NEEDS_MEANING_REVIEW")
        self.assertIn("original statement",answer.text)
        self.assertNotIn("demanded obedience",answer.text)

    def test_model_cannot_forge_domain_scope_for_paraphrase(self):
        src=self.core.preserve("a","The gate is closed")
        result=self.bridge.process(json.dumps({"kind":"paraphrase",
                       "text":"Authorization is denied","source_id":src,"span":[0,18],
                       "scope":{"domain":"project-ai"}}),current_source_id=src,
                       trusted_scope={"domain":"generic-conversation"})
        self.assertEqual(json.loads(self.core._proposal(result.claim_id)["scope_json"]),
                         {"domain":"generic-conversation"})

    def test_model_cannot_quote_another_source(self):
        other=self.core.preserve("person-b","Private statement")
        current=self.core.preserve("person-a","Visible statement")
        malicious=json.dumps({"kind":"quote","text":"Private statement","source_id":other,"span":[0,17]})
        with self.assertRaises(PermissionError):
            self.bridge.process(malicious,current_source_id=current)

    def test_raw_duplicate_key_cannot_bypass_bridge(self):
        with self.assertRaises(ValueError):
            self.bridge.process('{"kind":"fact","kind":"quote","text":"2 + 2 = 4"}')

    def test_unreviewed_hypothesis_does_not_reach_users(self):
        answer=self.bridge.process(json.dumps({"kind":"hypothesis","text":"Maybe the universe works differently"}))
        self.assertFalse(answer.established_fact)
        self.assertEqual(answer.decision,"HYPOTHESIS_HELD_FOR_REVIEW")
        self.assertNotIn("Maybe the universe",answer.text)

    def test_explicit_host_authorized_hypothesis_is_qualified(self):
        bridge=GovernedModelBridge(self.core, arithmetic_only_policy,
            host_hypothesis_release=lambda text,scope: scope.get('host_research_reviewed') is True)
        answer=bridge.process(json.dumps({"kind":"hypothesis","text":"A sensor may be miscalibrated",
             "scope":{"host_research_reviewed":True}}),trusted_scope={"host_research_reviewed":True})
        self.assertEqual(answer.decision,"HYPOTHESIS_ONLY")
        self.assertIn("Unverified hypothesis",answer.text)
        unauthorized=bridge.process(json.dumps({"kind":"hypothesis","text":"A colleague wants to mislead everyone",
            "scope":{"host_research_reviewed":True}}))
        self.assertEqual(unauthorized.decision,"HYPOTHESIS_HELD_FOR_REVIEW")
        self.assertNotIn("mislead everyone",unauthorized.text)


if __name__=="__main__":
    unittest.main()
