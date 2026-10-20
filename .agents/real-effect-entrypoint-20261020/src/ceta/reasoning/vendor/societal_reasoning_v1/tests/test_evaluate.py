import copy
import json
import tempfile
import unittest
from pathlib import Path

from societal_reasoning.evaluate import evaluate_cases, evaluate_file
from societal_reasoning.engine import SocietalReasoner

ROOT=Path(__file__).resolve().parents[1]


class EvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reasoner=SocietalReasoner.starter()
        cls.path=ROOT/'evaluations'/'behavior-contract.v1.json'

    def test_fixed_regression_suite(self):
        report=evaluate_file(self.reasoner,self.path)
        self.assertEqual(report['cases'],18)
        self.assertEqual(report['failed'],0)
        self.assertEqual(report['passed'],18)
        self.assertEqual(report['suite_type'],'developer_authored_regression_not_empirical_accuracy')

    def test_modifying_expected_result_fails(self):
        rows=json.loads(self.path.read_text())
        rows[0]['expected_status']='incorrect_magic'
        report=evaluate_cases(self.reasoner, rows)
        self.assertEqual(report['failed'],1)
        self.assertFalse(report['results'][0]['pass'])

    def test_empty_suite_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_cases(self.reasoner,[])

    def test_duplicate_case_id_rejected(self):
        rows=json.loads(self.path.read_text())
        with self.assertRaisesRegex(ValueError,'distinct'):
            evaluate_cases(self.reasoner,[rows[0],rows[0]])

    def test_unknown_extra_case_fields_rejected(self):
        row=json.loads(self.path.read_text())[0]
        row['bypass']='yes'
        with self.assertRaisesRegex(ValueError,'exactly'):
            evaluate_cases(self.reasoner,[row])

    def test_case_expected_primary_type_checked(self):
        row=json.loads(self.path.read_text())[0]
        row['expected_primary']={'trick':'json'}
        with self.assertRaisesRegex(ValueError,'string or null'):
            evaluate_cases(self.reasoner,[row])

    def test_case_data_mutation_does_not_change_fixture(self):
        rows=json.loads(self.path.read_text())
        report=evaluate_cases(self.reasoner, copy.deepcopy(rows))
        self.assertTrue(all(item['pass'] for item in report['results']))
        self.assertEqual(len(rows),18)

    def test_non_json_fails(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'bad.json'
            f.write_text('{}',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'JSON array'):
                evaluate_file(self.reasoner,f)


if __name__=='__main__': unittest.main()
