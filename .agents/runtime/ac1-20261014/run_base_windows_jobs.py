from ac_support import *
import importlib.util, unittest
sys.path.insert(0, str(Q / 'src'))
path = Q / 'tests/contract/test_windows_jobs.py'
spec = importlib.util.spec_from_file_location('test_windows_jobs', path)
module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
original_teardown = module.WindowsJobTests.tearDown
census = []
def observed_teardown(case):
    owners = list(case.owned)
    original_teardown(case)
    for owner in owners:
        row = {'test_id': case.id(), 'pid': owner.pid, 'creation_time': owner.creation_time,
               'image_sha256': owner.image_sha256, 'lifetime_closed': owner.lifetime_closed,
               'job_handle_closed': owner._job is None, 'process_handle_closed': owner._process is None}
        census.append(row)
        assert row['lifetime_closed'] and row['job_handle_closed'] and row['process_handle_closed']
module.WindowsJobTests.tearDown = observed_teardown
suite = unittest.defaultTestLoader.loadTestsFromModule(module)
def ids(suite):
    for case in suite:
        if isinstance(case, unittest.TestSuite): yield from ids(case)
        else: yield case.id()
expected = list(ids(suite)); executed = []
class Recorder(unittest.TextTestResult):
    def startTest(self, case): executed.append(case.id()); super().startTest(case)
before = {name: ordinary(Q / name) for name in ('tests/contract/test_windows_jobs.py','src/ceta/supervisor/windows_jobs.py')}
started = utc()
with (R / 'base-windows-jobs-r1.txt').open('x', encoding='utf-8') as output:
    result = unittest.TextTestRunner(stream=output, verbosity=2, resultclass=Recorder).run(suite)
after = {name: ordinary(Q / name) for name in before}
assert {n:x['sha256'] for n,x in before.items()} == {n:x['sha256'] for n,x in after.items()}
record = {'started_at': started, 'finished_at': utc(), 'tests_run': result.testsRun,
          'expected_ids': expected, 'executed_ids': executed, 'expected_executed_equal': expected == executed,
          'failure_count': len(result.failures), 'error_count': len(result.errors), 'skipped': result.skipped,
          'failures': [{'id':c.id(),'traceback':t} for c,t in result.failures],
          'errors': [{'id':c.id(),'traceback':t} for c,t in result.errors],
          'exit_status': 0 if result.wasSuccessful() else 1, 'before': before, 'after': after,
          'census': census, 'raw': reference(R / 'base-windows-jobs-r1.txt'),
          'limit': 'Existing canonical trusted-job lifecycle regression; not AppContainer positive isolation.'}
write_new(R / 'base-windows-jobs-r1.json', record)
print(json.dumps({'tests_run': result.testsRun, 'exit_status': record['exit_status'],
                  'failures': record['failures'], 'errors': record['errors'], 'owned_census': len(census)}, indent=2))
sys.exit(record['exit_status'])
