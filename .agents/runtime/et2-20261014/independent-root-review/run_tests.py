"""Actual isolated SQLite cohort with exact IDs and unchanged Source bytes."""
from review_support import *
import contextlib, importlib, threading, unittest
label = sys.argv[1]; assert label.replace('-', '').isalnum()
sys.path[:0] = [str(Q / 'src'), str(Q / 'tests/contract')]
from ceta.store.sqlite_runtime import load_sqlite, runtime_identity
load_sqlite(); sqlite_identity = runtime_identity()
import test_owned_cpu_outcome_transactions as tests
import test_owner_authority_transactions as owners
import test_kernel_transactions as kernel_tests
import test_real_effect_contract as effect_contract
import test_owner_enrollment as enrollment
fixtures = R / (label + '-fixtures'); fixtures.mkdir()
class RuntimeRoot:
    def __fspath__(self): return str(Q)
    def __truediv__(self, part):
        part = str(part).replace('\\', '/')
        if part == '.agents/fixtures': return fixtures
        if part.startswith('.agents/fixtures/'): return fixtures / part[len('.agents/fixtures/'):]
        return Q / part
tests.ROOT = RuntimeRoot()
if len(sys.argv) == 2:
    owners.ROOT = RuntimeRoot()
    modules = (tests,)
else:
    module_names = ('test_owned_cpu_outcome_transactions', 'test_owner_authority_transactions',
        'test_kernel_transactions', 'test_kernel_authority', 'test_kernel_recovery',
        'test_store_transactions', 'test_read_sets', 'test_temporal', 'test_wire', 'test_all_records',
        'test_real_effect_contract', 'test_owner_enrollment', 'test_resource_reservations')
    modules = tuple(importlib.import_module(name) for name in module_names)
    # Unchanged native-root/child-recovery assertions use their actual candidate
    # ROOT and only fresh Q/.agents/fixtures children. New ET2 fixtures use R.
journals = []; real_init = owners.SqliteJournal.__init__
def observed_init(self, *args, **kwargs):
    real_init(self, *args, **kwargs); journals.append(self)
owners.SqliteJournal.__init__ = observed_init
suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(module) for module in modules)
def ids(item):
    if isinstance(item, unittest.TestSuite):
        for child in item: yield from ids(child)
    else: yield item.id()
expected = list(ids(suite)); assert len(expected) == len(set(expected)) and not any('_FailedTest' in n for n in expected)
names = set(json.loads((R / 'STAGED-INPUTS.json').read_text())['payloads'])
names.update(('src/ceta/kernel/effect_transactions.py', 'tests/contract/test_owned_cpu_outcome_transactions.py',
              'contracts/OWNED_CPU_OUTCOME_V1.md'))
before = {name: ordinary(Q / name) for name in sorted(names)}
write_new(R / (label + '-preflight.json'), {'recorded_at': utc(), 'expected_ids': expected,
    'candidate_before': before, 'sqlite_identity': sqlite_identity, 'genuine_native_effect_invocation': False})
executed, stopped = [], []; started = utc(); old_threads = set(threading.enumerate())
class Result(unittest.TextTestResult):
    def startTest(self, test): executed.append(test.id()); super().startTest(test)
    def stopTest(self, test): stopped.append(test.id()); super().stopTest(test)
with (R / (label + '.txt')).open('x', encoding='utf-8', buffering=1) as output:
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        result = unittest.TextTestRunner(stream=output, verbosity=2, resultclass=Result).run(suite)
after = {name: ordinary(Q / name) for name in before}; assert before == after
remaining = [{'name': t.name, 'native_id': t.native_id} for t in set(threading.enumerate()) - old_threads if t.is_alive()]
closed = all(store._closed for store in journals)
record = {'started_at': started, 'finished_at': utc(), 'tests_run': result.testsRun,
    'expected_ids': expected, 'executed_ids': executed, 'stopped_ids': stopped, 'unique_methods': len(set(executed)),
    'failures': len(result.failures), 'errors': len(result.errors), 'skips': len(result.skipped),
    'failure_details': [{'id': case.id(), 'traceback': body} for case, body in result.failures + result.errors],
    'candidate_before': before, 'candidate_after': after, 'sqlite_identity': sqlite_identity,
    'fixture_stores': [{'path': str(store.path), 'closed': store._closed} for store in journals],
    'all_fixture_stores_closed': closed, 'new_threads_remaining': remaining,
    'crash_observations': tests.CRASH_OBSERVATIONS, 'cumulative_observations': tests.CUMULATIVE_OBSERVATIONS, 'source_imports': {
        name: str(Path(module.__file__)) for name, module in sys.modules.items()
        if name.startswith('ceta') and getattr(module, '__file__', None)},
    'raw': reference(R / (label + '.txt')), 'genuine_native_effect_invocation': False,
    'controlled_native_providers': True,
    'exit_status': 0 if result.wasSuccessful() and not result.skipped and expected == executed == stopped and closed and not remaining else 1}
write_new(R / (label + '.json'), record)
print(json.dumps({key: record[key] for key in ('tests_run', 'unique_methods', 'failures', 'errors', 'skips', 'all_fixture_stores_closed', 'exit_status')}))
for failure in record['failure_details']: print(failure['id'] + '\n' + failure['traceback'])
sys.exit(record['exit_status'])
