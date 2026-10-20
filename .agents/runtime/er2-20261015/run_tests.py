"""Finite ER2 controlled-clock and unchanged original Qt/session regression."""
from pathlib import Path
import argparse
import json
import os
import sys
import threading
import unittest

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
Q = F / '.agents/er2-20261015'
sys.dont_write_bytecode = True
sys.path.insert(0, str(F / '.agents/runtime/ka1-20261014'))
import ka1_support as s
s.Q, s.R, s.RUN, s.ACTOR = Q, R, Q.name, '/root'


def test_ids(suite):
    if isinstance(suite, unittest.TestSuite):
        for item in suite:
            yield from test_ids(item)
    else:
        yield suite.id()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('label')
    parser.add_argument('--cohort', action='store_true')
    args = parser.parse_args()
    assert args.label.replace('-', '').isalnum()
    output = R / args.label
    output.mkdir(exist_ok=False)
    temporary = output / 'temporary'
    temporary.mkdir()
    os.environ.update(QT_QPA_PLATFORM='offscreen', TEMP=str(temporary), TMP=str(temporary))
    inputs = json.loads((R / 'SOURCE-INPUTS.json').read_bytes())
    names = [*inputs['parent294'], 'tests/contract/test_editor_retention_queue.py']
    before = {name: s.ordinary(Q / name) for name in names}
    sys.path[:0] = [str(Q / 'src'), str(Q / 'tools'), str(Q / 'tests/contract')]
    from ceta.store.sqlite_runtime import load_sqlite, runtime_identity
    sqlite = load_sqlite()
    loader = unittest.TestLoader()
    modules = ['test_editor_retention_queue']
    if args.cohort:
        modules += ['test_task_meaning_view', 'test_task_view', 'test_editor_recovery']
    suite = loader.loadTestsFromNames(modules)
    expected = list(test_ids(suite))
    assert not loader.errors and len(expected) == len(set(expected))
    assert not any('_FailedTest' in identifier for identifier in expected)
    started = s.utc()
    threads = set(threading.enumerate())
    executed, stopped, physical = [], [], []

    class Result(unittest.TextTestResult):
        def startTest(self, test):
            executed.append(test.id())
            super().startTest(test)

        def stopTest(self, test):
            for fixture in getattr(test, 'fixtures', ()):
                store = getattr(fixture, 'store', None)
                connection = getattr(store, '_connection', None)
                if type(connection) is sqlite.Connection:
                    closed, observation = False, None
                    try:
                        connection.execute('SELECT 1')
                    except sqlite.ProgrammingError as error:
                        observation = str(error)
                        closed = observation == 'Cannot operate on a closed database.'
                    physical.append({'test_id': test.id(), 'object_id': id(connection),
                                     'closed': closed, 'observation': observation})
            stopped.append(test.id())
            super().stopTest(test)

    with (output / 'RAW.txt').open('x', encoding='utf-8', buffering=1) as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Result).run(suite)
    remaining = [{'name': value.name, 'native_id': value.native_id}
                 for value in set(threading.enumerate()) - threads if value.is_alive()]
    after = {name: s.ordinary(Q / name) for name in names}
    parent_exact = all(s.ordinary(F / '.agents/js3-20261015' / name) == row
                       for name, row in inputs['parent294'].items())
    source_exact = all(s.ordinary(F / name) == row for name, row in inputs['Source290'].items())
    imports = {name: str(Path(module.__file__).resolve()) for name, module in sys.modules.items()
               if (name == 'ceta' or name.startswith('ceta.')) and getattr(module, '__file__', None)}
    candidate_imports = all(Path(path).is_relative_to(Q / 'src') for path in imports.values())
    success = (result.wasSuccessful() and not result.skipped and expected == executed == stopped
               and not remaining and physical and all(row['closed'] for row in physical)
               and before == after and source_exact and parent_exact and candidate_imports)
    proof = {'started_at': started, 'finished_at': s.utc(), 'expected_ids': expected,
             'executed_ids': executed, 'stopped_ids': stopped, 'tests_run': result.testsRun,
             'failures': len(result.failures), 'errors': len(result.errors), 'skips': len(result.skipped),
             'failure_details': [(test.id(), detail) for test, detail in result.failures],
             'error_details': [(test.id(), detail) for test, detail in result.errors],
             'remaining_threads': remaining, 'physical_sqlite_probes': physical,
             'all_observed_fixture_connections_closed': bool(physical) and all(row['closed'] for row in physical),
             'candidate_before': before, 'candidate_after': after, 'Source290_exact': source_exact,
             'parent294_exact': parent_exact, 'ceta_imports': imports,
             'all_ceta_imports_from_candidate': candidate_imports, 'sqlite_runtime': runtime_identity(),
             'original_test_methods_unchanged': True,
             'new_controlled_clock_scope': 'Only task_operator.time.monotonic in five explicit new tests; original deadlines unchanged.',
             'transport_and_identity': 'Controlled fixture; native owner approval not established.',
             'Source_publication': False, 'Source_accepted': False,
             'raw': s.reference(output / 'RAW.txt'), 'exit_status': 0 if success else 1}
    s.write_new(output / 'RESULT.json', proof)
    print(json.dumps({'tests_run': result.testsRun, 'failures': len(result.failures),
                      'errors': len(result.errors), 'exit_status': proof['exit_status'],
                      'proof': s.reference(output / 'RESULT.json')}), flush=True)
    return proof['exit_status']


if __name__ == '__main__':
    sys.exit(main())
