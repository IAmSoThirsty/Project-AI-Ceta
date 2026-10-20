"""Dictionary sense resolution and perspective preservation tests."""
import unittest
from truth_accountability import AuthenticatedActor, GovernedTruthCore


class ContextAndSenseTests(unittest.TestCase):
    def setUp(self):
        self.core=GovernedTruthCore()
        self.reviewer=AuthenticatedActor("reviewer",frozenset({"meaning_reviewer"}))
        self.speaker=AuthenticatedActor("a",frozenset({"authenticated_speaker"}))

    def tearDown(self):
        self.core.close()

    def test_ambiguity_requires_explicit_sense_binding(self):
        original="The right side is bright."
        source=self.core.preserve("a",original)
        claim=self.core.propose("paraphrase","The correct side is bright",source_id=source,span=(0,len(original)))
        self.core.review_meaning(claim,self.reviewer,"aligned","Initial reading")
        self.assertEqual(self.core.decision(claim).status,"MEANING_REVIEWED")
        issue=self.core.flag_material_ambiguity(source,span=(4,9),term="right",
                       reason="Could indicate direction or correctness",reviewer=self.reviewer)
        self.assertEqual(self.core.decision(claim).status,"NEEDS_SENSE_RESOLUTION")
        self.core.resolve_dictionary_sense(issue,selected_sense="direction, opposite of left",
                                           source_locator="https://www.merriam-webster.com/dictionary/right",
                                           reviewer=self.reviewer)
        self.assertEqual(self.core.decision(claim).status,"NEEDS_MEANING_REVIEW")
        self.core.review_meaning(claim,self.speaker,"rejected","I meant the right-hand side")
        self.assertEqual(self.core.decision(claim).status,"MEANING_DISPUTED")

    def test_sense_resolution_with_new_positive_review(self):
        src=self.core.preserve("a","This is right.")
        issue=self.core.flag_material_ambiguity(src,span=(8,13),term="right",
                           reason="Multiple dictionary senses",reviewer=self.reviewer)
        self.core.resolve_dictionary_sense(issue,selected_sense="correct",
             source_locator="https://www.merriam-webster.com/dictionary/right",reviewer=self.reviewer)
        claim=self.core.propose("paraphrase","This is correct",source_id=src,span=(0,14))
        self.assertEqual(self.core.decision(claim).status,"NEEDS_MEANING_REVIEW")
        self.core.review_meaning(claim,self.speaker,"aligned","I meant correct")
        self.assertEqual(self.core.decision(claim).status,"MEANING_REVIEWED")

    def test_dictionary_url_cannot_be_impostor(self):
        src=self.core.preserve("a","right")
        issue=self.core.flag_material_ambiguity(src,span=(0,5),term="right",reason="Polysemy",reviewer=self.reviewer)
        for url in ("http://www.merriam-webster.com/dictionary/right",
                    "https://www.merriam-webster.com.evil.org/dictionary/right",
                    "https://evil.org/dictionary/right",
                    "https://merriam-webster.com@evil.org/dictionary/right"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.core.resolve_dictionary_sense(issue,selected_sense="correct",source_locator=url,reviewer=self.reviewer)

    def test_material_ambiguity_flag_needs_source_match_and_authorization(self):
        src=self.core.preserve("a","The right side")
        with self.assertRaises(ValueError):
            self.core.flag_material_ambiguity(src,span=(4,9),term="left",reason="test",reviewer=self.reviewer)
        with self.assertRaises(PermissionError):
            self.core.flag_material_ambiguity(src,span=(4,9),term="right",reason="test",reviewer=self.speaker)

    def test_technical_glossary_scope_is_not_global(self):
        src=self.core.preserve("a","The gate is closed")
        issue=self.core.flag_material_ambiguity(src,span=(4,8),term="gate",reason="Project domain usage",reviewer=self.reviewer)
        with self.assertRaises(ValueError):
            self.core.resolve_dictionary_sense(issue,selected_sense="execution gate",source_locator="local:glossary",
                      reference_kind="TECHNICAL_GLOSSARY",reviewer=self.reviewer)
        self.core.resolve_dictionary_sense(issue,selected_sense="Project-specific executable authorization boundary",
                source_locator="local:project-glossary:v2",reference_kind="TECHNICAL_GLOSSARY",
                domain_scope="project-ai",reviewer=self.reviewer)

    def test_technical_glossary_definition_does_not_leak_to_other_domain(self):
        source=self.core.preserve("a","The gate is closed")
        issue=self.core.flag_material_ambiguity(source,span=(4,8),term="gate",
              reason="May be everyday or system-specific",reviewer=self.reviewer)
        self.core.resolve_dictionary_sense(issue,selected_sense="Permissioned execution boundary",
              source_locator="local:project-glossary:1",reference_kind="TECHNICAL_GLOSSARY",
              domain_scope="project-ai",reviewer=self.reviewer)
        general=self.core.propose("paraphrase","A generic door is shut",source_id=source,
                                  span=(0,18),scope={"domain":"general"})
        project=self.core.propose("paraphrase","The governed execution boundary is closed",
                                  source_id=source,span=(0,18),scope={"domain":"project-ai"})
        self.assertEqual(self.core.decision(general).status,"NEEDS_SENSE_RESOLUTION")
        self.assertEqual(self.core.decision(project).status,"NEEDS_MEANING_REVIEW")

    def test_perspective_records_do_not_create_truth_verdicts(self):
        src1=self.core.preserve("a","The street is safe in daylight.")
        src2=self.core.preserve("b","The street is dangerous at night.")
        self.core.record_perspective(src1,subject_key="street.x",span=(0,31),report_kind="observation",
                                     context={"time":"daylight"})
        self.core.record_perspective(src2,subject_key="street.x",span=(0,33),report_kind="experience",
                                     context={"time":"night"})
        comparison=self.core.compare_perspectives("street.x")
        self.assertEqual(comparison["context_variants"],2)
        self.assertEqual(comparison["comparison_status"],"DIFFERING_CONTEXTS")
        self.assertEqual(comparison["fact_resolution"],"REQUIRES_INDEPENDENT_EVIDENCE")
        self.assertEqual(len(comparison["reports"]),2)
        self.assertNotIn("is_true",str(comparison))

    def test_two_people_agree_still_not_independent_fact_verification(self):
        src1=self.core.preserve("a","I think this is true")
        src2=self.core.preserve("b","I think this is true")
        for src in (src1,src2):
            self.core.record_perspective(src,subject_key="shared.belief",span=(0,20),report_kind="belief")
        self.assertEqual(self.core.compare_perspectives("shared.belief")["fact_resolution"],"REQUIRES_INDEPENDENT_EVIDENCE")

    def test_perspective_source_must_be_exact_and_kind_allowed(self):
        src=self.core.preserve("a","I am cold")
        with self.assertRaises(ValueError):
            self.core.record_perspective(src,subject_key="me",span=(0,99),report_kind="experience")
        with self.assertRaises(ValueError):
            self.core.record_perspective(src,subject_key="me",span=(0,9),report_kind="infallible_fact")

    def test_no_perspectives_is_unknown_not_false(self):
        report=self.core.compare_perspectives("nobody")
        self.assertEqual(report["reports"],[])
        self.assertEqual(report["fact_resolution"],"REQUIRES_INDEPENDENT_EVIDENCE")


if __name__=="__main__":
    unittest.main()
