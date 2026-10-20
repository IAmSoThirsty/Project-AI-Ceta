from ac_support import *
import importlib.util, unittest

label = sys.argv[1] if len(sys.argv) == 2 else 'targeted-r1'
assert re.fullmatch(r'targeted-r[1-5]', label) if 're' in globals() else label in ['targeted-r1','targeted-r2','targeted-r3','targeted-r4','targeted-r5']
os.environ['CETA_AC1_RUNTIME_ROOT'] = str(R)
sys.path.insert(0, str(Q / 'src'))
test = Q / 'tests/contract/test_isolated_worker.py'
spec = importlib.util.spec_from_file_location('test_isolated_worker', test)
module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
suite = unittest.defaultTestLoader.loadTestsFromModule(module)
def ids(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite): yield from ids(item)
        else: yield item.id()
expected = list(ids(suite)); assert len(expected) == len(set(expected))
source_files = {name: ordinary(Q / name) for name in (
 'src/ceta/supervisor/isolated_worker.py','src/ceta/supervisor/windows_jobs.py',
 'native/windows_broker/isolated_worker.rs','tests/contract/test_isolated_worker.py','contracts/ISOLATED_WORKER_V1.md')}
executed = []
class Recorder(unittest.TextTestResult):
    def startTest(self, case): executed.append(case.id()); super().startTest(case)
started = utc()
with (R / (label + '.txt')).open('x', encoding='utf-8') as stream:
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Recorder).run(suite)
after = {name: ordinary(Q / name) for name in source_files}
assert {name: item['sha256'] for name, item in source_files.items()} == {name: item['sha256'] for name,item in after.items()}
record = {'started_at': started, 'finished_at': utc(), 'tests_run': result.testsRun,
          'expected_ids': expected, 'executed_ids': executed, 'expected_executed_equal': expected == executed,
          'failures': [{'id': case.id(), 'traceback': text} for case,text in result.failures],
          'errors': [{'id': case.id(), 'traceback': text} for case,text in result.errors],
          'skipped': result.skipped, 'exit_status': 0 if result.wasSuccessful() else 1,
          'source_before': source_files, 'source_after': after, 'raw': reference(R / (label + '.txt')),
          'qualification': 'Binding/pure shape/actual SID/native cleanup/safe unavailable denial only; positive AppContainer access/bypass/token/network remains blocked and NOT_EXECUTED'}
write_new(R / (label + '.json'), record)
print(json.dumps({'tests_run': result.testsRun, 'failure_count': len(result.failures), 'error_count': len(result.errors),
                  'skipped': len(result.skipped), 'exit_status': record['exit_status'],
                  'errors': record['errors'], 'failures': record['failures']}, indent=2), flush=True)
sys.exit(record['exit_status'])
