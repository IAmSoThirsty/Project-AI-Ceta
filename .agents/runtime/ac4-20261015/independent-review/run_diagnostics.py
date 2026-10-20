"""Finite AC4 diagnostic cohort; no profile operation or worker launch."""
from pathlib import Path
import ast, importlib, json, os, sys, threading, unittest
from unittest.mock import patch
F = Path('T:/00-Active/Project-AI-CETA')
sys.path.insert(0, str(F / '.agents/runtime/en1-20261014'))
import en1_support as s
Q = s.Q = F / '.agents/ac4-20261015'
OR = F / '.agents/runtime/ac4-20261015'
R = s.R = Path(__file__).resolve().parent
s.RUN, s.ACTOR = 'ac4-20261015', '/root/pressure_writer'
label = sys.argv[1]
assert label.replace('-', '').isalnum()
D = R / label; D.mkdir()
inputs = json.loads((OR / 'SOURCE-INPUTS.json').read_text())
source_before = {name: s.ordinary(F / name) for name in inputs['Source290']}
assert source_before == inputs['Source290']
names = sorted(set(inputs['candidate_before']) | {'tests/contract/test_isolation_token_diagnostics.py'})
candidate_before = {name: s.ordinary(Q / name) for name in names}
for name, row in inputs['candidate_before'].items():
    if name not in ('src/ceta/supervisor/isolated_worker.py', 'contracts/ISOLATED_WORKER_V1.md'):
        assert candidate_before[name] == row
parent = F / '.agents/ac3-20261014'
original = ast.parse((parent / 'src/ceta/supervisor/isolated_worker.py').read_text())
current = ast.parse((Q / 'src/ceta/supervisor/isolated_worker.py').read_text())
for name in ('IsolationTokenFacts', 'SECURITY_CAPABILITIES', 'SID_AND_ATTRIBUTES'):
    select = lambda tree: ast.dump(next(item for item in tree.body if isinstance(item, ast.ClassDef) and item.name == name), include_attributes=False)
    assert select(original) == select(current)
for name in ('tests/contract/test_isolated_worker.py', 'native/windows_broker/isolated_worker.rs'):
    assert (Q / name).read_bytes() == (parent / name).read_bytes()
sys.path[:0] = [str(Q / 'src'), str(Q / 'tests/contract')]
import test_isolation_token_diagnostics as tests
import test_isolated_worker as old
from ceta.supervisor import isolated_worker as module

def flatten(items):
    for item in items:
        if isinstance(item, unittest.TestSuite): yield from flatten(item)
        else: yield item
cases = list(flatten(unittest.TestSuite((unittest.defaultTestLoader.loadTestsFromModule(tests),
    unittest.defaultTestLoader.loadTestsFromTestCase(old.IsolationFactsContractTests)))))
expected = [case.id() for case in cases]
assert len(expected) == len(set(expected))
executed, stopped, forbidden, apis = [], [], [], []
original_init = module._IsolationAPI.__init__
def guarded_init(api, *args, **kwargs):
    original_init(api, *args, **kwargs); apis.append(api)
    def deny(*args):
        forbidden.append('CreateProcessW'); raise AssertionError('AC4_NO_WORKER_LAUNCH')
    api.CreateProcessW = deny
    for name in ('CreateAppContainerProfile', 'DeleteAppContainerProfile'):
        def refuse(*args, _name=name):
            forbidden.append(_name); raise AssertionError('AC4_NO_PROFILE_OPERATION')
        setattr(api.userenv, name, refuse)
class Recorder(unittest.TextTestResult):
    def startTest(self, case): executed.append(case.id()); super().startTest(case)
    def stopTest(self, case): stopped.append(case.id()); super().stopTest(case)
threads_before = set(threading.enumerate()); started = s.utc()
with patch.object(module._IsolationAPI, '__init__', guarded_init), (D / 'tests.txt').open('x', encoding='utf8') as out:
    result = unittest.TextTestRunner(stream=out, verbosity=2, resultclass=Recorder).run(unittest.TestSuite(cases))
remaining = [{'name': item.name, 'native_id': item.native_id}
    for item in set(threading.enumerate()) - threads_before if item.is_alive()]
source_after = {name: s.ordinary(F / name) for name in source_before}
candidate_after = {name: s.ordinary(Q / name) for name in names}
pending = [list(api.pending_native_resources()) for api in apis]
passed = (result.wasSuccessful() and not result.skipped and expected == executed == stopped
    and not remaining and not forbidden and not any(pending)
    and source_before == source_after and candidate_before == candidate_after)
s.write_new(D / 'RESULT.json', {'started_at': started, 'finished_at': s.utc(),
    'expected_ids': expected, 'executed_ids': executed, 'stopped_ids': stopped,
    'tests_run': result.testsRun, 'failures': [{'id': case.id(), 'traceback': trace} for case, trace in result.failures],
    'errors': [{'id': case.id(), 'traceback': trace} for case, trace in result.errors], 'skipped': result.skipped,
    'native_observations': tests.NATIVE_TOKEN_DIAGNOSTIC_RECEIPTS,
    'guarded_API_constructions': len(apis), 'pending_native_resources': pending, 'forbidden_calls': forbidden,
    'new_threads': remaining, 'source_before': source_before, 'source_after': source_after,
    'candidate_before': candidate_before, 'candidate_after': candidate_after,
    'original_qualification_predicates_AST_exact': True, 'original_tests_and_worker_bytes_exact': True,
    'profile_operations': [], 'worker_launches': [], 'positive_isolation_qualified': False,
    'raw': s.reference(D / 'tests.txt'), 'exit_status': 0 if passed else 1})
print(json.dumps({'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
    'skips': len(result.skipped), 'Source_conserved': source_before == source_after,
    'candidate_conserved': candidate_before == candidate_after, 'pending': pending, 'exit_status': 0 if passed else 1}), flush=True)
sys.exit(0 if passed else 1)
