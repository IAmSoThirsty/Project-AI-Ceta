import json
import tempfile
import unittest
from pathlib import Path

from evaluate_model import MockProposer, _load_cases, run_evaluation
from truth_accountability import GovernedTruthCore, GovernedModelBridge, SocietalGatedPipeline, arithmetic_only_policy

ROOT=Path(__file__).resolve().parents[1]
CASES=ROOT/'evaluations/public_adversarial.jsonl'


class EvaluationRunnerTests(unittest.TestCase):
    def test_mock_protocol_24_24_is_not_model_score(self):
        report=run_evaluation(cases_path=CASES,backend='mock')
        self.assertEqual(report['case_count'],24)
        self.assertEqual(report['mock_protocol_passed'],24)
        self.assertEqual(report['inference_class'],'DETERMINISTIC_SIMULATION_NO_MODEL')
        self.assertEqual(sum(report['statuses'].values()),24)

    def test_person_hypothesis_not_published_as_fact_even_when_qualified(self):
        core=GovernedTruthCore()
        try:
            bridge=GovernedModelBridge(core,arithmetic_only_policy)
            pipeline=SocietalGatedPipeline(core,bridge)
            result=pipeline.execute(speaker_id='synthetic',exact_text='Someone disagreed with the proposal.',
                proposer=MockProposer({'kind':'hypothesis','text':'Maybe they secretly hate you.'}))
            self.assertEqual(result.decision,'NEEDS_PERSON_EVIDENCE')
            self.assertNotIn('secretly hate',result.response)
        finally: core.close()

    def test_objective_source_cannot_be_replaced_by_model(self):
        core=GovernedTruthCore()
        try:
            runner=SocietalGatedPipeline(core,GovernedModelBridge(core,arithmetic_only_policy))
            result=runner.execute(speaker_id='synthetic',exact_text='I might attend.',
                proposer=MockProposer({'kind':'quote','text':'I will attend.','source_id':'$SOURCE_ID','span':'$FULL_SPAN'}))
            self.assertEqual(result.decision,'MODEL_PROPOSAL_REJECTED')
            self.assertEqual(core.original(result.source_id),'I might attend.')
        finally:core.close()

    def test_hypothesis_about_untested_physical_mechanism_remains_qualified(self):
        core=GovernedTruthCore()
        try:
            runner=SocietalGatedPipeline(core,GovernedModelBridge(core,arithmetic_only_policy))
            result=runner.execute(speaker_id='synthetic',exact_text='A radio signal had an unexpected pattern.',
                proposer=MockProposer({'kind':'hypothesis','text':'Perhaps the instrumentation has a new failure mode.'}))
            self.assertEqual(result.decision,'HYPOTHESIS_HELD_FOR_REVIEW')
            self.assertFalse(result.established_fact)
        finally:core.close()

    def test_mock_case_input_duplicate_ids_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            x=Path(td)/'dup.jsonl'
            example=json.loads(CASES.read_text().splitlines()[0])
            x.write_text(json.dumps(example)+'\n'+json.dumps(example)+'\n')
            with self.assertRaises(ValueError): _load_cases(x)

    def test_missing_real_model_cannot_be_called_live_success(self):
        with self.assertRaises(ValueError): run_evaluation(cases_path=CASES,backend='ollama',model='')

    def test_source_and_mapping_must_be_supplied_together(self):
        with self.assertRaises(ValueError): run_evaluation(cases_path=CASES,backend='mock',version1_source=Path('missing.zip'))

    def test_missing_replay_provenance_rejected(self):
        with self.assertRaises(ValueError): run_evaluation(cases_path=CASES,backend='replay')

    def test_real_replay_labeled_not_live(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'subset.jsonl'; rp=Path(td)/'replay.json'
            record=json.loads(CASES.read_text().splitlines()[0])
            p.write_text(json.dumps(record)+'\n')
            rp.write_text(json.dumps({record['id']:json.dumps({'kind':'hypothesis','text':'A possible explanation exists'})}))
            report=run_evaluation(cases_path=p,backend='replay',replay_path=rp)
            self.assertEqual(report['inference_class'],'RECORDED_PROPOSALS_NOT_LIVE')
            self.assertIsNone(report['mock_protocol_passed'])

    def test_malformed_oversized_model_output_is_never_parsed_as_authority(self):
        class HugeProposer:
            def generate_proposal(self,*args,**kwargs):
                return '{"kind":"fact","text":"'+'x'*100000+'"}'
        core=GovernedTruthCore()
        try:
            pipe=SocietalGatedPipeline(core,GovernedModelBridge(core,arithmetic_only_policy))
            with self.assertRaisesRegex(ValueError,'exceeds the 32 KiB contract'):
                pipe.execute(speaker_id='synthetic',exact_text='Hello',proposer=HugeProposer())
        finally:core.close()

    def test_lexical_nonmental_hypothesis_does_not_create_factual_authority(self):
        core=GovernedTruthCore()
        try:
            pipe=SocietalGatedPipeline(core,GovernedModelBridge(core,arithmetic_only_policy))
            res=pipe.execute(speaker_id='synthetic',exact_text='The observation remains unresolved',
                proposer=MockProposer({'kind':'hypothesis','text':'A sensor miscalibration may explain it.'}))
            self.assertEqual(res.decision,'HYPOTHESIS_HELD_FOR_REVIEW')
            self.assertFalse(res.established_fact)
        finally:core.close()

    def test_case_manifest_is_hash_bound(self):
        report=run_evaluation(cases_path=CASES,backend='mock')
        import hashlib
        self.assertEqual(report['case_manifest_sha256'],hashlib.sha256(CASES.read_bytes()).hexdigest())

if __name__=='__main__':unittest.main()
