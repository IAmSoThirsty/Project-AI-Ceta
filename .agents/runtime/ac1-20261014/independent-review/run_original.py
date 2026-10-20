"""Independently execute exact original AC1 and owned-job method IDs."""
from ac_support import *
import unittest

os.environ['CETA_AC1_RUNTIME_ROOT'] = str(D)
sys.path.insert(0, str(Q / 'src'))
modules = []
for name, path in (
    ('test_isolated_worker', Q / 'tests/contract/test_isolated_worker.py'),
    ('test_windows_jobs', D / 'test-harness/tests/contract/test_windows_jobs.py')):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module)
    modules.append(module)

census = []
original_teardown = modules[1].WindowsJobTests.tearDown
def observed_teardown(case):
    owners = list(case.owned)
    original_teardown(case)
    for owner in owners:
        row = {'test_id': case.id(), 'pid': owner.pid, 'creation_time': owner.creation_time,
               'image_sha256': owner.image_sha256, 'lifetime_closed': owner.lifetime_closed,
               'job_handle_closed': owner._job is None, 'process_handle_closed': owner._process is None}
        census.append(row)
        assert row['lifetime_closed'] and row['job_handle_closed'] and row['process_handle_closed']
modules[1].WindowsJobTests.tearDown = observed_teardown
suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(module) for module in modules)
def ids(suite):
    for case in suite:
        if isinstance(case, unittest.TestSuite): yield from ids(case)
        else: yield case.id()
expected = list(ids(suite)); assert len(expected) == len(set(expected)) == 39
before = candidate_cut(); source_before = source_cut()
executed = []
class Recorder(unittest.TextTestResult):
    def startTest(self, case): executed.append(case.id()); super().startTest(case)
started = utc()
with (D / 'original-r1.txt').open('x', encoding='utf-8') as output:
    result = unittest.TextTestRunner(stream=output, verbosity=2, resultclass=Recorder).run(suite)
after = candidate_cut(); source_after = source_cut()
assert before == after
record = {'started_at': started, 'finished_at': utc(), 'tests_run': result.testsRun,
          'expected_ids': expected, 'executed_ids': executed, 'expected_executed_equal': expected == executed,
          'failures': [{'id': case.id(), 'traceback': text} for case,text in result.failures],
          'errors': [{'id': case.id(), 'traceback': text} for case,text in result.errors],
          'skipped': result.skipped, 'exit_status': 0 if result.wasSuccessful() else 1,
          'candidate_before': before, 'candidate_after': after,
          'source_before': source_before, 'source_after': source_after, 'owned_census': census,
          'raw': reference(D / 'original-r1.txt'),
          'qualification': 'Original AC1 21 safe-denial/custody plus canonical Windows jobs 18; no positive restricted isolation claim'}
write_new(D / 'original-r1.json', record)
print(json.dumps({'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
                  'skips': len(result.skipped), 'owned_lifetimes_closed': len(census), 'exit_status': record['exit_status']}), flush=True)
sys.exit(record['exit_status'])
