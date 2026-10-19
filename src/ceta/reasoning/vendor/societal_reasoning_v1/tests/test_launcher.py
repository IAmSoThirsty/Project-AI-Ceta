import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class NoInstallLaunchTests(unittest.TestCase):
    def run_script(self,*args):
        return subprocess.run([sys.executable,str(ROOT/'run.py'),*args],
                              cwd=ROOT, capture_output=True,encoding='utf-8',check=False)

    def test_no_install_audit(self):
        result=self.run_script('audit')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['concept_count'],2000)

    def test_no_install_dictionary(self):
        result=self.run_script('define','context')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['dictionary'],'Merriam-Webster')

    def test_no_install_regression_runner(self):
        result=self.run_script('evaluate',str(ROOT/'evaluations'/'behavior-contract.v1.json'))
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['passed'],18)

    def test_no_install_structured_interpretation(self):
        result=self.run_script('reason',str(ROOT/'examples'/'semantic_ambiguity.json'))
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'],'clarification_required')

if __name__=='__main__': unittest.main()
