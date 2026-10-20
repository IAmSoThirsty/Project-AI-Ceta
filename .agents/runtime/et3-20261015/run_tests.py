"""Exact IDs and native file conservation around disposable SQLite tests."""
from et_support import *
import contextlib, importlib, threading, unittest

label = sys.argv[1]
assert label.replace('-', '').isalnum()
sys.path[:0] = [str(Q / 'src'), str(Q / 'tests/contract')]
from ceta.store.sqlite_runtime import load_sqlite, runtime_identity
load_sqlite()
import test_owned_cpu_outcome_transactions as prior
import test_owner_authority_transactions as owners
fixtures = R / (label + '-fixtures')
fixtures.mkdir()
class RuntimeRoot:
    def __fspath__(self): return str(Q)
    def __truediv__(self, part):
        part = str(part).replace('\\', '/')
        if part == '.agents/fixtures': return fixtures
        if part.startswith('.agents/fixtures/'): return fixtures / part[len('.agents/fixtures/'):]
        return Q / part
prior.ROOT = RuntimeRoot()
names = ['test_fresh_observer_reconciliation']
if len(sys.argv) > 2:
    names += ['test_owned_cpu_outcome_transactions', 'test_owner_authority_transactions',
        'test_kernel_transactions', 'test_kernel_authority', 'test_kernel_recovery',
        'test_store_transactions', 'test_read_sets', 'test_temporal', 'test_wire', 'test_all_records',
        'test_real_effect_contract', 'test_owner_enrollment', 'test_resource_reservations']
else:
    owners.ROOT = RuntimeRoot()
modules = [importlib.import_module(name) for name in names]
suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m) for m in modules)
def ids(item):
    if isinstance(item, unittest.TestSuite):
        for child in item: yield from ids(child)
    else: yield item.id()
expected = list(ids(suite))
assert len(expected) == len(set(expected)) and not any('_FailedTest' in n for n in expected)
payload_names = set(json.loads((R / 'STAGED-INPUTS.json').read_text())['payloads'])
payload_names.add('tests/contract/test_fresh_observer_reconciliation.py')
before = {name: ordinary(Q / name) for name in sorted(payload_names)}
source = json.loads((R / 'SOURCE-INPUTS.json').read_text())['Source290']
assert {name: ordinary(F / name) for name in source} == source
journals = []
real_init = owners.SqliteJournal.__init__
def observed_init(self, *args, **kwargs):
    real_init(self, *args, **kwargs)
    journals.append(self)
owners.SqliteJournal.__init__ = observed_init
executed, stopped = [], []
class Result(unittest.TextTestResult):
    def startTest(self, test): executed.append(test.id()); super().startTest(test)
    def stopTest(self, test): stopped.append(test.id()); super().stopTest(test)
started, old_threads = utc(), set(threading.enumerate())
write_new(R / (label + '-preflight.json'), {'at': started, 'expected_ids': expected,
    'candidate_before': before, 'Source290': source, 'sqlite_identity': runtime_identity()})
with (R / (label + '.txt')).open('x', encoding='utf-8', buffering=1) as stream:
    with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Result).run(suite)
after = {name: ordinary(Q / name) for name in before}
assert before == after and {name: ordinary(F / name) for name in source} == source
remaining = [{'name': t.name, 'native_id': t.native_id} for t in set(threading.enumerate()) - old_threads if t.is_alive()]
stores = [{'path': str(store.path), 'closed': store._closed} for store in journals]
assert all(store['closed'] for store in stores)
record = {'started_at': started, 'finished_at': utc(), 'tests_run': result.testsRun,
    'expected_ids': expected, 'executed_ids': executed, 'stopped_ids': stopped,
    'unique_methods': len(set(executed)), 'failures': len(result.failures),
    'errors': len(result.errors), 'skips': len(result.skipped),
    'failure_details': [{'id': c.id(), 'traceback': b} for c,b in result.failures+result.errors],
    'candidate_before': before, 'candidate_after': after, 'Source290_preserved': True,
    'sqlite_identity': runtime_identity(), 'fixture_stores': stores, 'new_threads_remaining': remaining,
    'source_imports': {name: str(Path(m.__file__)) for name,m in sys.modules.items()
        if name.startswith('ceta') and getattr(m,'__file__',None)},
    'native_effect': False, 'native_proof_providers': 'CONTROLLED',
    'crash_observations': prior.CRASH_OBSERVATIONS,
    'raw': reference(R / (label + '.txt')),
    'exit_status': 0 if result.wasSuccessful() and not result.skipped and expected == executed == stopped and not remaining else 1}
write_new(R / (label + '.json'), record)
print(json.dumps({key: record[key] for key in ('tests_run','unique_methods','failures','errors','skips','exit_status')}))
for failure in record['failure_details']: print(failure['id']+'\n'+failure['traceback'])
sys.exit(record['exit_status'])
