import copy
import unittest

from societal_reasoning.models import MaterialTerm, Scenario
from societal_reasoning.semantics import LexicalRegistry, Term, Sense
from societal_reasoning.engine import SocietalReasoner


class LexicalRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LexicalRegistry.starter()
        cls.reasoner = SocietalReasoner.starter()

    def test_ten_source_linked_terms(self):
        self.assertEqual(len(self.registry.terms), 10)

    def test_dictionary_source_for_all_terms(self):
        for term in self.registry.terms.values():
            self.assertTrue(term.url.startswith('https://www.merriam-webster.com/dictionary/'))
            self.assertGreaterEqual(len(term.senses), 2)

    def test_glosses_are_not_claimed_verbatim(self):
        self.assertEqual(self.registry.lookup('context')['gloss_status'], 'original_project_paraphrase_not_dictionary_quote')

    def test_nonexistent_term_returns_none(self):
        self.assertIsNone(self.registry.lookup('globally-unlisted-xyz'))

    def test_canonical_casefold_lookup(self):
        self.assertEqual(self.registry.lookup(' CONTEXT ')['term'], 'context')

    def test_reject_noncanonical_dictionary_domain(self):
        with self.assertRaises(ValueError):
            Term.from_dict({'term':'context','url':'https://evil.example/dictionary/context',
                            'senses':[{'id':'a','gloss':'x','mw_reference':'1'}]})

    def test_reject_http_dictionary_domain(self):
        with self.assertRaises(ValueError):
            Term.from_dict({'term':'context','url':'http://www.merriam-webster.com/dictionary/context',
                            'senses':[{'id':'a','gloss':'x','mw_reference':'1'}]})

    def test_reject_duplicate_sense(self):
        with self.assertRaisesRegex(ValueError,'Duplicate dictionary sense'):
            Term.from_dict({'term':'context','url':'https://www.merriam-webster.com/dictionary/context',
                            'senses':[{'id':'a','gloss':'x','mw_reference':'1'},
                                      {'id':'a','gloss':'y','mw_reference':'2'}]})

    def test_ambiguous_term_requires_clarification(self):
        report=self.registry.assess((MaterialTerm('context'),))
        self.assertEqual(report['status'],'requires_clarification')
        self.assertEqual(report['unresolved'][0]['issue'],'material_dictionary_ambiguity')

    def test_caller_explicit_sense_is_used(self):
        report=self.registry.assess((MaterialTerm('context','discourse'),))
        self.assertEqual(report['status'],'resolved')
        self.assertEqual(report['resolved'][0]['resolution_basis'],'caller_explicit_sense')

    def test_unknown_sense_not_guessed(self):
        report=self.registry.assess((MaterialTerm('context','unknown'),))
        self.assertEqual(report['status'],'requires_clarification')
        self.assertEqual(report['unresolved'][0]['issue'],'unknown_sense_id')

    def test_absent_dictionary_entry_does_not_fabricate(self):
        report=self.registry.assess((MaterialTerm('unlistedconcept'),))
        self.assertEqual(report['unresolved'][0]['issue'],'term_not_in_reviewed_registry')

    def test_no_material_terms_does_not_invent_word_sense(self):
        report=self.registry.assess(())
        self.assertEqual(report['status'],'resolved')
        self.assertEqual(report['resolved'],[])

    def test_reasoning_halts_on_material_ambiguity(self):
        case=Scenario.from_dict({'id':'ctx','question':'Evaluate','material_terms':[{'term':'context'}],
                                  'evidence':[{'id':'a','origin':'user_report','statement':'Meme mocks people',
                                               'cues':['derisive_form','people_or_group_targeted']}]})
        result=self.reasoner.analyze(case)
        self.assertEqual(result['status'],'clarification_required')
        self.assertIsNone(result['primary'])
        self.assertEqual(result['clarification_question'], "Which Merriam-Webster sense of 'context' applies here?")
        self.assertIn('material_terms', result)
        self.assertEqual(result['operational_boundary'],'ADVISORY_ONLY_NO_EXTERNAL_ACTION_OR_AUTHORIZATION')

    def test_explicit_sense_allows_bounded_interpretation(self):
        data={'id':'ctx','question':'Evaluate','material_terms':[{'term':'context','sense_id':'setting'}],
              'evidence':[{'id':'a','origin':'user_report','statement':'Meme mocks people',
                           'cues':['derisive_form','people_or_group_targeted']}]}
        result=self.reasoner.analyze(Scenario.from_dict(data))
        self.assertEqual(result['status'],'provisional_interpretation')
        self.assertEqual(result['primary']['rule_id'],'public_group_ridicule')
        self.assertEqual(result['material_terms']['resolved'][0]['dictionary_sense_reference'],'noun 2')

    def test_duplicate_material_term_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate material term'):
            Scenario.from_dict({'id':'one','question':'Q','evidence':[],
                                'material_terms':[{'term':'context'},{'term':'CONTEXT'}]})

    def test_unrecognized_material_term_key_rejected(self):
        with self.assertRaisesRegex(ValueError,'Unexpected material term fields'):
            MaterialTerm.from_dict({'term':'context','override_authority':True})

    def test_source_label_not_authority_grant(self):
        data={'id':'authority','question':'Q','material_terms':[{'term':'authority','sense_id':'power'}],
              'evidence':[]}
        response=self.reasoner.analyze(Scenario.from_dict(data))
        self.assertEqual(response['status'],'insufficient_evidence')
        self.assertEqual(response['operational_boundary'],'ADVISORY_ONLY_NO_EXTERNAL_ACTION_OR_AUTHORIZATION')


if __name__=='__main__': unittest.main()
