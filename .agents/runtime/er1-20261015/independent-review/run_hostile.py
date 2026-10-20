"""Independent pure-leaf hostile checks; no native/journal/Qt/full execution."""
from pathlib import Path
import importlib
import json
import sys
import threading
import unittest
from review_support import Q, V, s, read, conservation, ACTOR


def ids(group):
    if isinstance(group, unittest.TestSuite):
        for child in group:
            yield from ids(child)
    else:
        yield group.id()


def main():
    before = conservation()
    baseline = read(V / 'CONSERVATION-BEFORE.json')
    assert before == baseline
    blocked = []
    class PureBoundary:
        def find_spec(self, fullname, path=None, target=None):
            if fullname.startswith('ceta.') and not (fullname == 'ceta.contracts' or fullname.startswith('ceta.contracts.')):
                blocked.append(fullname)
                raise AssertionError('Reviewer permits only canonical candidate pure leaf')
    guard = PureBoundary()
    sys.meta_path.insert(0, guard)
    threads = set(threading.enumerate())
    executed = []
    stopped = []
    try:
        module = importlib.import_module('test_hostile_scans')
        suite = unittest.defaultTestLoader.loadTestsFromModule(module)
        expected = list(ids(suite))
        assert len(expected) == len(set(expected)) == 7
        class Result(unittest.TextTestResult):
            def startTest(self, test):
                executed.append(test.id()); super().startTest(test)
            def stopTest(self, test):
                stopped.append(test.id()); super().stopTest(test)
        with (V / 'HOSTILE-R1.txt').open('x', encoding='utf8') as stream:
            result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Result).run(suite)
    finally:
        sys.meta_path.remove(guard)
    remaining = [thread.name for thread in set(threading.enumerate()) - threads if thread.is_alive()]
    imported = {name: s.reference(Path(value.__file__)) for name, value in sys.modules.items()
        if name.startswith('ceta.') and getattr(value, '__file__', None)}
    assert all((s.P / row['repository_relative_path']).is_relative_to(Q / 'src/ceta/contracts') for row in imported.values())
    after = conservation()
    assert after == before
    accepted = result.wasSuccessful() and not result.skipped and not blocked and not remaining and executed == stopped == expected
    proof = {'at': s.utc(), 'executor_id': ACTOR, 'scope': 'Seven independent finite pure-contract methods',
        'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors), 'skips': len(result.skipped),
        'expected_ids': expected, 'executed_ids': executed, 'stopped_ids': stopped,
        'failure_details': [(test.id(), detail) for test, detail in result.failures + result.errors],
        'vector_counts_by_method': module.COUNTS, 'retained_request_decode': module.REQUEST_PROOF,
        'imported_pure_modules': imported, 'blocked_noncontract_import_attempts': blocked,
        'remaining_threads': remaining, 'conservation_before': s.reference(V / 'CONSERVATION-BEFORE.json'),
        'before_equals_after': before == after, 'raw': s.reference(V / 'HOSTILE-R1.txt'),
        'copied_original_AST_oracle_credit': 0, 'Source_publication': False, 'full_gate_complete': False,
        'exit_status': 0 if accepted else 1}
    s.write_new(V / 'HOSTILE-R1.json', proof)
    print(json.dumps({'proof': s.reference(V / 'HOSTILE-R1.json'), 'tests_run': result.testsRun,
        'failures': len(result.failures), 'errors': len(result.errors), 'exit_status': proof['exit_status']}), flush=True)
    return proof['exit_status']


if __name__ == '__main__':
    sys.exit(main())
