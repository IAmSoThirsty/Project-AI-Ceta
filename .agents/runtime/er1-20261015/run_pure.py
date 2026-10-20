"""Finite real pure-contract regression, with unchanged dependency readback."""
from pathlib import Path
import importlib
import json
import sys
import threading
import unittest

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
Q = F / '.agents/er1-20261015'
P = F / '.agents/js2-20261015'
sys.dont_write_bytecode = True
sys.path.insert(0, str(F / '.agents/runtime/ka1-20261014'))
import ka1_support as s
s.Q, s.R, s.RUN, s.ACTOR = Q, R, Q.name, '/root'


def test_ids(suite):
    for value in suite:
        if isinstance(value, unittest.TestSuite):
            yield from test_ids(value)
        else:
            yield value.id()


def main():
    assert len(sys.argv) == 2
    label = sys.argv[1]
    assert label.isascii() and label.replace('-', '').isalnum()
    output = R / label
    output.mkdir(exist_ok=False)
    inputs = json.loads((R / 'SOURCE-INPUTS.json').read_bytes())
    names = [*inputs['parent292'], 'tests/contract/test_wire_scanning.py']
    before = {name: s.ordinary(Q / name) for name in names}
    started = s.utc()
    threads = set(threading.enumerate())
    sys.path[:0] = [str(Q / 'src'), str(Q / 'tests/contract')]
    blocked = []
    class PureBoundary:
        def find_spec(self, fullname, path=None, target=None):
            if fullname.startswith('ceta.') and not (
                    fullname == 'ceta.contracts' or fullname.startswith('ceta.contracts.')):
                blocked.append(fullname)
                raise AssertionError('Only the canonical pure leaf is admitted')
    guard = PureBoundary()
    sys.meta_path.insert(0, guard)
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for name in ('test_wire_scanning', 'test_wire', 'test_all_records', 'test_local_ipc', 'test_local_results'):
        suite.addTests(loader.loadTestsFromModule(importlib.import_module(name)))
    expected = list(test_ids(suite))
    assert len(expected) == len(set(expected)) == 85 and not loader.errors
    executed, stopped = [], []
    class Result(unittest.TextTestResult):
        def startTest(self, test):
            executed.append(test.id())
            super().startTest(test)
        def stopTest(self, test):
            stopped.append(test.id())
            super().stopTest(test)
    try:
        with (output / 'RAW.txt').open('x', encoding='utf-8') as stream:
            result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Result).run(suite)
    finally:
        sys.meta_path.remove(guard)
    after = {name: s.ordinary(Q / name) for name in names}
    source_after = {name: s.ordinary(F / name) for name in inputs['Source290']}
    parent_after = {name: s.ordinary(P / name) for name in inputs['parent292']}
    modules = {name: s.reference(Path(module.__file__)) for name, module in sys.modules.items()
               if name.startswith('ceta.') and getattr(module, '__file__', None)}
    correct_imports = all((F / row['repository_relative_path']).is_relative_to(Q / 'src/ceta/contracts')
                          for row in modules.values())
    remaining = [thread.name for thread in set(threading.enumerate()) - threads if thread.is_alive()]
    passed = (result.wasSuccessful() and not result.skipped and executed == stopped == expected
        and before == after and source_after == inputs['Source290'] and parent_after == inputs['parent292']
        and correct_imports and not blocked and not remaining)
    proof = {'started_at': started, 'finished_at': s.utc(), 'executor': '/root', 'scope': 'Pure contract component only',
        'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'skips': len(result.skipped), 'expected_ids': expected, 'executed_ids': executed, 'stopped_ids': stopped,
        'failure_details': [(test.id(), body) for test, body in result.failures + result.errors],
        'raw': s.reference(output / 'RAW.txt'), 'candidate_before': before, 'candidate_after': after,
        'Source290_after': source_after, 'parent292_after': parent_after,
        'all_imports_from_candidate_pure_leaf': correct_imports, 'product_modules': modules,
        'blocked_noncontract_import_attempts': blocked, 'remaining_threads': remaining,
        'native_or_journal_tests': 'NOT_RUN', 'prior_full_failure_repaired': False,
        'Source_publication': False, 'exit_status': 0 if passed else 1}
    s.write_new(output / 'RESULT.json', proof)
    print(json.dumps({'tests_run': result.testsRun, 'failures': len(result.failures),
        'errors': len(result.errors), 'skips': len(result.skipped),
        'proof': s.reference(output / 'RESULT.json'), 'exit_status': proof['exit_status']}))
    return proof['exit_status']


if __name__ == '__main__':
    sys.exit(main())
