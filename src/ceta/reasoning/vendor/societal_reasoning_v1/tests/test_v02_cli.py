import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from societal_reasoning.cli import main

ROOT=Path(__file__).resolve().parents[1]


class V02CLITests(unittest.TestCase):
    def call(self,args):
        out=io.StringIO(); err=io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            rc=main(args)
        return rc,out.getvalue(),err.getvalue()

    def test_define_context(self):
        code,out,err=self.call(['define','context'])
        self.assertEqual(code,0,err)
        data=json.loads(out)
        self.assertEqual(len(data['senses']),2)
        self.assertEqual(data['dictionary'],'Merriam-Webster')

    def test_define_missing_term_fails_without_making_up_definition(self):
        code,out,err=self.call(['define','unlistedterm'])
        self.assertEqual(code,2)
        self.assertIn('No sense asserted',err)

    def test_evaluate_regressions(self):
        code,out,err=self.call(['evaluate',str(ROOT/'evaluations'/'behavior-contract.v1.json')])
        self.assertEqual(code,0,err)
        self.assertEqual(json.loads(out)['passed'],18)

    def test_evaluate_detects_failure_with_nonzero_exit(self):
        cases=json.loads((ROOT/'evaluations'/'behavior-contract.v1.json').read_text())
        cases[0]['expected_primary']='defect_that_does_not_exist'
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'changed.json'
            path.write_text(json.dumps(cases))
            code,out,_=self.call(['evaluate',str(path)])
            self.assertEqual(code,1)
            self.assertEqual(json.loads(out)['failed'],1)

    def test_explicit_ambiguity_cli(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'scenario.json'
            path.write_text(json.dumps({'id':'lex','question':'meaning','material_terms':[{'term':'context'}],'evidence':[]}))
            code,out,_=self.call(['reason',str(path)])
            self.assertEqual(code,0)
            self.assertEqual(json.loads(out)['status'],'clarification_required')

    def test_invalid_material_terms_is_bounded_error(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'scenario.json'
            path.write_text(json.dumps({'id':'lex','question':'meaning','material_terms':42,'evidence':[]}))
            code,out,err=self.call(['reason',str(path)])
            self.assertEqual(code,2)
            self.assertIn('must be an array',err)

    def test_neighbors_honors_custom_graph(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'concepts.jsonl'
            obj={'id':150001,'label':'Private example','summary':'x','source':{'kind':'fixture'},'status':'seed_summary_pending_transcription'}
            path.write_text(json.dumps(obj)+'\n')
            code,out,err=self.call(['neighbors','150001','--concepts',str(path)])
            self.assertEqual(code,0,err)
            self.assertEqual(json.loads(out),[])


if __name__=='__main__': unittest.main()
