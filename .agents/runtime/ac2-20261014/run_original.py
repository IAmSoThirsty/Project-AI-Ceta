"""Exact AC1 method bodies on AC2 imports with fresh runtime-only fixtures."""
from ac2_support import *
import unittest

label = sys.argv[1] if len(sys.argv) == 2 else 'original-r1'
assert label in ('original-r1', 'original-r2', 'original-r3', 'original-r4')
harness = R / (label + '-harness')
native_runtime = harness / '.agents/runtime/ac1-20261014'
native_runtime.mkdir(parents=True); (native_runtime / 'build-r2').mkdir()
for name in ('native_fixture_support.py',):
    fs.write_new(native_runtime / name, fs.read_bytes(PRIOR_R / name))
fs.write_new(native_runtime / 'ac_support.py', fs.read_bytes(R / 'ac_support.py'))
fs.write_new(native_runtime / 'build-r2/isolated_worker.exe', fs.read_bytes(PRIOR_R / 'build-r2/isolated_worker.exe'))
inputs = json.loads((R / 'source-inputs.json').read_text())
for name in set(inputs['source_payloads']) | set(inputs['scope']):
    if name.startswith('src/') or name == 'tests/contract/test_windows_jobs.py':
        target = harness / name; target.parent.mkdir(parents=True, exist_ok=True)
        fs.write_new(target, fs.read_bytes(Q / name))
os.environ['CETA_AC1_RUNTIME_ROOT'] = str(native_runtime)
os.environ['CETA_AC2_PROBE_ROOT'] = str(native_runtime)
sys.path.insert(0, str(Q / 'src'))
modules = []
for name, path in (('test_isolated_worker', Q / 'tests/contract/test_isolated_worker.py'),
                   ('test_windows_jobs', harness / 'tests/contract/test_windows_jobs.py')):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module)
    modules.append(module)
modules[0].ROOT = harness  # Retained guard derives its exact AC1-named runtime below this own harness.
suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(module) for module in modules)
def ids(suite):
    for case in suite:
        if isinstance(case, unittest.TestSuite): yield from ids(case)
        else: yield case.id()
expected = list(ids(suite)); assert len(expected) == len(set(expected))
old = json.loads((PRIOR_R / 'independent-review/original-r1.json').read_text())['executed_ids']
assert set(old) <= set(expected)
before = {name: ordinary(Q / name) for name in set(inputs['source_payloads']) | set(inputs['scope'])}
executed, census = [], []
old_teardown = modules[1].WindowsJobTests.tearDown
def observed_teardown(case):
    owners = list(case.owned); old_teardown(case)
    for owner in owners:
        row = {'test_id': case.id(), 'pid': owner.pid, 'creation_time': owner.creation_time,
               'lifetime_closed': owner.lifetime_closed, 'job_closed': owner._job is None,
               'process_closed': owner._process is None}
        assert row['lifetime_closed'] and row['job_closed'] and row['process_closed']; census.append(row)
modules[1].WindowsJobTests.tearDown = observed_teardown
class Recorder(unittest.TextTestResult):
    def startTest(self, case): executed.append(case.id()); super().startTest(case)
started = utc()
with (R / (label + '.txt')).open('x', encoding='utf-8') as stream:
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Recorder).run(suite)
after = {name: ordinary(Q / name) for name in before}; assert before == after
bindings = {}
for name, module in sorted(sys.modules.items()):
    if name == 'ceta' or name.startswith('ceta.'):
        path = Path(module.__file__).resolve(strict=True)
        assert path.is_relative_to(Q / 'src')
        bindings[name] = ordinary(path)
record = {'started_at': started, 'finished_at': utc(), 'expected_ids': expected, 'executed_ids': executed,
    'tests_run': result.testsRun, 'expected_executed_equal': expected == executed,
    'original_39_ids_retained': old, 'failures': [{'id':case.id(),'traceback':text} for case,text in result.failures],
    'errors': [{'id':case.id(),'traceback':text} for case,text in result.errors], 'skipped': result.skipped,
    'exit_status': 0 if result.wasSuccessful() else 1, 'candidate_before': before, 'candidate_after': after,
    'canonical_job_census': census, 'ceta_import_bindings': bindings, 'raw': reference(R / (label + '.txt')),
    'fixture_support_reuse': reference(PRIOR_R / 'native_fixture_support.py'),
    'fixture_scope': str(harness), 'test_harness_binding': 'Only module ROOT constant is rebound; all original39 method bodies remain unchanged and ceta imports resolve in actual Q2',
    'limits': 'Actual restrictive error2 and safe cleanup only; positive restricted-worker isolation is unexecuted.'}
write_new(R / (label + '.json'), record)
print(json.dumps({'tests_run': result.testsRun, 'original_39_retained': True, 'failures': len(result.failures),
                  'errors': len(result.errors), 'skipped': len(result.skipped), 'exit_status': record['exit_status']}), flush=True)
sys.exit(record['exit_status'])
