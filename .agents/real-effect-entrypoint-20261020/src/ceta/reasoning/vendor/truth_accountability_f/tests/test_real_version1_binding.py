"""Optional EXACT SOURCE acceptance suite. Requires real owner-supplied V1 ZIP.

Example:
  SOCIETAL_V1_SOURCE=/secure/Societal-Reasoning-Core-v1.zip \\
  SOCIETAL_V1_ROOT=/secure/Societal-Reasoning-Core \\
  PYTHONPATH=/secure/Societal-Reasoning-Core/src:. \\
  python -m unittest tests.test_real_version1_binding -v

No original Version 1 source is embedded in this reference package.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import unittest
from pathlib import Path
from truth_accountability import (
    CorpusMapping, GovernedModelBridge, GovernedTruthCore,
    SocietalGatedPipeline, Version1ReadOnlyAdapter, Version1RuntimeAdvisor,
    arithmetic_only_policy,
)

EXPECTED_V1_SHA256='b76b9482f95b93b0a25b8d88881ac3b68558b077118f32e3360f383ded4247b5'
SOURCE=os.environ.get('SOCIETAL_V1_SOURCE')
ROOT=os.environ.get('SOCIETAL_V1_ROOT')


class SourceProposer:
    def generate_proposal(self,source_id,source_text,*,contextual_references=None):
        return json.dumps({'kind':'paraphrase', 'text':'You demanded obedience',
            'source_id':source_id,'span':[0,len(source_text)]})


@unittest.skipUnless(SOURCE and ROOT, 'Owner-supplied Version 1 ZIP and extracted runtime root required')
class GenuineSourceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=Path(SOURCE)
        cls.root=Path(ROOT)
        cls.mapping=CorpusMapping('src/societal_reasoning/resources/concepts.full.jsonl',
                                  'id','original_text',2000)
        cls.adapter=Version1ReadOnlyAdapter(cls.source,mapping=cls.mapping,
                                            expected_zip_sha256=EXPECTED_V1_SHA256)
        cls.record=cls.adapter.inspect()
        src=(cls.root/'src').resolve()
        if str(src) not in sys.path:
            sys.path.insert(0,str(src))
        import societal_reasoning as v1
        if not Path(v1.__file__).resolve().is_relative_to(src):
            raise RuntimeError('Loaded Societal Reasoning package is not the provided Version 1 source')
        if v1.__version__ != '1':
            raise RuntimeError('Changed Version 1 version identity')
        cls.reasoner=v1.SocietalReasoner.starter()

    def test_actual_pinned_archive_and_canonical_mapping(self):
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(),EXPECTED_V1_SHA256)
        self.assertEqual(self.record.records,2000)
        self.assertEqual(self.record.members,109)
        self.assertEqual(self.record.corpus_sha256,
           '96a39faf6e3f13f3d6377896ee495edcfd44065cd14d4e4643d247f734d4af2c')

    def test_original_graph_full_inventory(self):
        audit=self.reasoner.graph.audit()
        self.assertEqual(len(self.reasoner.graph.concepts),2000)
        self.assertEqual(self.reasoner.graph.get(1080).label,'Context collapse in conversation')

    def test_real_sources_remain_context_not_evidence(self):
        matches=self.adapter.candidates('context collapse conversation',limit=6)
        self.assertTrue(any(x.entry_id=='1080' for x in matches))
        self.assertTrue(all(x.source_kind=='CONTEXTUAL_REFERENCE_NOT_PERSON_EVIDENCE' for x in matches))

    def test_full_source_api_captures_actual_utterance(self):
        utterance='I might attend, but I have not promised.'
        review=Version1RuntimeAdvisor(self.reasoner).review(
            speaker_id='speaker-1',source_id='turn-1', exact_text=utterance,
            gated_draft='Recorded statement from speaker-1: '+json.dumps(utterance)+' (quotation only, not fact verification)')
        self.assertEqual(review.api_schema,'text_assessment.v1')
        self.assertEqual(review.source_sha256,hashlib.sha256(utterance.encode()).hexdigest())
        self.assertEqual(review.status,'REVIEW_HOLD')
        self.assertIn('POSSIBLE_MODALITY_STRENGTHENING',review.issue_codes)

    def test_unambiguous_original_source_returns_advisory_pass(self):
        utterance='I understand.'
        review=Version1RuntimeAdvisor(self.reasoner).review(
            speaker_id='speaker-1',source_id='turn-2', exact_text=utterance,
            gated_draft='Recorded statement from speaker-1: '+json.dumps(utterance)+' (quotation only, not fact verification)')
        self.assertEqual(review.status,'ADVISORY_PASS')
        self.assertEqual(review.issue_codes,())

    def test_real_source_through_single_canonical_gate(self):
        core=GovernedTruthCore()
        try:
            pipe=SocietalGatedPipeline(core,GovernedModelBridge(core,arithmetic_only_policy),
               self.adapter,Version1RuntimeAdvisor(self.reasoner))
            utterance='I asked you to understand social context, not obey.'
            result=pipe.execute(speaker_id='speaker-1',exact_text=utterance,
                               proposer=SourceProposer())
            self.assertEqual(core.original(result.source_id),utterance)
            self.assertNotIn('You demanded obedience',result.response)
            self.assertNotEqual(result.decision,'MEANING_REVIEWED')
            self.assertIn(result.version1_runtime_review,{'ADVISORY_PASS','REVIEW_HOLD'})
            self.assertTrue(core.integrity_report()['ok'])
        finally:core.close()

    def test_broken_runtime_assessment_fails_closed(self):
        class MaliciousRuntime:
            def assess_text(self,*args,**kwargs):
                return {'schema':'text_assessment.v1','utterance':{'text':'fabricated','sha256':'0'*64}}
            def review_draft(self,*args,**kwargs):return {'status':'pass','issues':[]}
        core=GovernedTruthCore()
        try:
            pipeline=SocietalGatedPipeline(core,GovernedModelBridge(core,arithmetic_only_policy),
                  self.adapter,Version1RuntimeAdvisor(MaliciousRuntime()))
            answer=pipeline.execute(speaker_id='speaker-1',exact_text='Exact source',
                proposer=SourceProposer())
            self.assertEqual(answer.decision,'VERSION1_REVIEW_FAILURE')
            self.assertNotIn('demanded obedience',answer.response)
        finally:core.close()

    def test_advisory_review_withheld_on_explicit_issue(self):
        class HoldingRuntime:
            def __init__(self,delegate):self.delegate=delegate
            def assess_text(self,*args,**kw):return self.delegate.assess_text(*args,**kw)
            def review_draft(self,*args,**kw):
                return {'status':'hold','issues':[{'code':'REGRESSION','severity':'hold'}]}
        core=GovernedTruthCore()
        try:
            pipe=SocietalGatedPipeline(core,GovernedModelBridge(core,arithmetic_only_policy),
                 self.adapter,Version1RuntimeAdvisor(HoldingRuntime(self.reasoner)))
            result=pipe.execute(speaker_id='speaker-1',exact_text='Hello.',proposer=SourceProposer())
            self.assertEqual(result.decision,'VERSION1_REVIEW_HOLD')
            self.assertNotIn('demanded obedience',result.response)
        finally:core.close()

    def test_no_implicit_direct_runtime_execution_from_archive(self):
        # Read-only archive inspector does NOT import the Version 1 source.
        fresh=Version1ReadOnlyAdapter(self.source,mapping=self.mapping,
            expected_zip_sha256=EXPECTED_V1_SHA256)
        self.assertEqual(fresh.inspect().records,2000)
        self.assertEqual(fresh.candidates('institutional labels')[0].source_kind,
                         'CONTEXTUAL_REFERENCE_NOT_PERSON_EVIDENCE')


if __name__=='__main__':unittest.main()
