"""Exact three selected original pure-leaf guard methods."""
from foundation_support import *
import unittest
sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
import test_source_coverage as c
names=('test_contract_core_has_no_infrastructure_or_other_domain_imports',
    'test_only_the_observed_enum_type_import_is_qualified',
    'test_contract_leaf_rejects_infrastructure_and_relative_domain_escape')
D=R/'leaf-r1';D.mkdir();executed=[];stopped=[]
class Result(unittest.TextTestResult):
    def startTest(self,t):executed.append(t.id());super().startTest(t)
    def stopTest(self,t):stopped.append(t.id());super().stopTest(t)
suite=unittest.TestSuite(c.SourceCoverageTests(name) for name in names)
with (D/'tests.txt').open('x',encoding='utf8') as out:
    result=unittest.TextTestRunner(stream=out,verbosity=2,resultclass=Result).run(suite)
expected=['test_source_coverage.SourceCoverageTests.'+name for name in names]
passed=result.wasSuccessful() and not result.skipped and expected==executed==stopped
write_new(D/'RESULT.json',dict(at=utc(),tests_run=result.testsRun,expected_ids=expected,executed_ids=executed,stopped_ids=stopped,
    failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),raw=reference(D/'tests.txt'),
    Source_publication=False,exit_status=0 if passed else 1))
sys.exit(0 if passed else 1)
