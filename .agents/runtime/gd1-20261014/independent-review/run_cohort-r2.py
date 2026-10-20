"""Execute frozen GD1 cohort without changing source, tests or fixture guards."""
from datetime import datetime, timezone
from pathlib import Path
import ast
import hashlib
import importlib
import json
import os
import sys
import time
import traceback
import unittest

O = Path(__file__).resolve().parent
R = O.parent
F = R.parents[2]
Q = F / '.agents/gd1-20261014'
E3 = F / '.agents/source-assembly-20261014T021300Z/.agents/e3'
sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
assert Path(sys.executable) == E3 / 'Scripts/python.exe' and sys.flags.optimize == 0
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
read = lambda path: json.loads(Path(path).read_text(encoding='utf-8'))
utc = lambda: datetime.now(timezone.utc).isoformat()
started = utc()
def write_new(path, value):
    assert Path(path).is_relative_to(O)
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')

manifest_path = Q / 'TRANSFER-MANIFEST.json'
manifest_sha = sha(manifest_path)
assert manifest_sha == '3f64c0dca1637ef58d6eb5bd2c64809d9af48c2c1fb691f6d558b15047cbf9b3'
assert sha(R / 'implement.json') == 'bdade2cba4633cd602f390134ad0255f451c915edc5995fee97cd7493c1b4d85'
manifest = read(manifest_path)
payloads = {row['relative_path']: row for row in manifest['payloads']}
assert len(payloads) == len(manifest['payloads']) == 280
assert manifest['baseline_payloads'] == 279
source_expected = {name: row['active_before_sha256'] for name, row in payloads.items() if row['action'] != 'CREATE'}
assert len(source_expected) == 279
source_before = {name: sha(F / name) for name in source_expected}
assert source_before == source_expected
candidate_before = {name: sha(Q / name) for name in payloads}
assert all(candidate_before[name] == row['candidate_sha256'] for name, row in payloads.items())
assert sum(row['action'] == 'REUSE' for row in payloads.values()) == 277
assert {name for name, row in payloads.items() if row['action'] != 'REUSE'} == {
    'src/ceta/resource/diagnostics.py', 'contracts/PROCESS_DIAGNOSTICS_V1.md', 'tests/contract/test_process_observation_timing.py'}
for name in ('tests/contract/test_process_diagnostics.py', 'tests/contract/test_resource_management.py'):
    assert candidate_before[name] == source_expected[name]
specs = []
for row in manifest['input_specification_bindings']:
    assert sha(Path(row['path'])) == row['sha256']
    specs.append(row)
assert sha(F / manifest['tests']['repository_relative_path']) == manifest['tests']['sha256']
author = read(F / manifest['tests']['repository_relative_path'])
assert author['tests_run'] == 314 and author['failures'] == author['errors'] == author['skipped'] == 0
sys.path[:0] = [str(Q / 'src'), str(Q / 'tests/contract')]
modules = ['test_process_observation_timing', 'test_process_diagnostics', 'test_resource_management',
    'test_hardware_observation', 'test_workload_admission', 'test_temporal',
    'test_source_coverage.SourceCoverageTests.test_contract_core_has_no_infrastructure_or_other_domain_imports',
    'test_source_coverage.SourceCoverageTests.test_contract_leaf_guard_rejects_stdlib_prefix_module_escape',
    'test_source_coverage.SourceCoverageTests.test_contract_leaf_guard_rejects_nested_or_parent_contract_escape']
# Exact author method selection is joined to independently discovered IDs below;
# use its declared selectors if their guard names differ from this inventory.
modules = author['modules']
assert len(modules) == 9
suite = unittest.defaultTestLoader.loadTestsFromNames(modules)
def methods(suite):
    for entry in suite:
        if isinstance(entry, unittest.TestSuite): yield from methods(entry)
        else: yield entry
expected = [test.id() for test in methods(suite)]
assert len(expected) == len(set(expected)) == 314
assert expected == [row['id'] for row in author['cases']]
fixture_root = Q / '.agents/fixtures'
existing_children = {path.name for path in fixture_root.iterdir()}
def regular_hashes(root):
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_file(): result[path.relative_to(root).as_posix()] = sha(path)
    return result
existing_fixture_files = regular_hashes(fixture_root)
events = []
def audit(name, arguments):
    if name not in {'os.mkdir', 'os.rmdir', 'shutil.rmtree'}: return
    if not arguments or not isinstance(arguments[0], (str, bytes, os.PathLike)): return
    value = os.fsdecode(arguments[0])
    if value.startswith('\\\\?\\'): value = value[4:]
    path = Path(os.path.abspath(value))
    if path.is_relative_to(fixture_root):
        events.append({'operation': name, 'path': str(path), 'at': utc(), 'relative_path': path.relative_to(fixture_root).as_posix()})
sys.addaudithook(audit)
cases = []
class Result(unittest.TextTestResult):
    def startTest(self, test):
        self.start = time.perf_counter(); self.status = 'PASS'; super().startTest(test)
    def addFailure(self, test, error): self.status = 'FAIL'; super().addFailure(test, error)
    def addError(self, test, error): self.status = 'ERROR'; super().addError(test, error)
    def addSkip(self, test, reason): self.status = 'SKIP'; super().addSkip(test, reason)
    def addSubTest(self, test, subtest, error):
        if error is not None: self.status = 'FAIL' if issubclass(error[0], test.failureException) else 'ERROR'
        super().addSubTest(test, subtest, error)
    def stopTest(self, test):
        cases.append({'id': test.id(), 'status': self.status, 'seconds': time.perf_counter() - self.start}); super().stopTest(test)
print(json.dumps({'stage': 'independent_cohort_start', 'expected_methods': len(expected), 'candidate_payloads': 280,
    'retained_payloads': 277, 'Source_payloads_unchanged': 279, 'manifest_sha256': manifest_sha}), flush=True)
begin = time.perf_counter()
result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2, resultclass=Result).run(suite)
seconds = time.perf_counter() - begin
candidate_after = {name: sha(Q / name) for name in payloads}
source_after = {name: sha(F / name) for name in source_expected}
source_same = source_before == source_after
candidate_same = candidate_before == candidate_after and sha(manifest_path) == manifest_sha
assert all(sha(fixture_root / name) == value for name, value in existing_fixture_files.items())
new_children = [path for path in fixture_root.iterdir() if path.name not in existing_children]
new_fixture_files = {}
native_process_metadata = []
for child in new_children:
    for path in sorted(child.rglob('*')):
        if path.is_file():
            new_fixture_files[path.relative_to(Q).as_posix()] = {'bytes': path.stat().st_size, 'sha256': sha(path)}
            if path.name == 'primary.json':
                value = read(path)
                native_process_metadata.append({'path': str(path), 'sha256': sha(path), 'pid': value.get('pid'),
                    'creation_time_100ns': value.get('creation'), 'argv_count': len(value.get('argv', []))})
imports = {name: str(Path(module.__file__).resolve()) for name, module in sys.modules.items()
    if (name == 'ceta' or name.startswith('ceta.')) and getattr(module, '__file__', None)}
all_imports_own_cut = bool(imports) and all(Path(path).is_relative_to(Q / 'src') for path in imports.values())
native = sys.modules['test_process_observation_timing'].NATIVE_OBSERVATIONS
passed = result.wasSuccessful() and not result.skipped and expected == [row['id'] for row in cases] and source_same and candidate_same and all_imports_own_cut
out = {'schema_version': 1, 'executor': '/root/pressure_review', 'started_at': started, 'finished_at': utc(),
    'manifest_sha256': manifest_sha, 'implement_receipt_sha256': sha(R / 'implement.json'), 'candidate_root': str(Q), 'source_root': str(F),
    'command_argv': [sys.executable, '-B', '-X', 'utf8', str(Path(__file__)), *modules],
    'selected_modules': modules, 'expected_ids': expected, 'cases': cases, 'tests_run': result.testsRun,
    'failures': len(result.failures), 'errors': len(result.errors), 'skips': len(result.skipped), 'seconds': seconds,
    'failure_details': [{'test_id': test.id(), 'traceback': trace} for test, trace in result.failures + result.errors],
    'source_before': source_before, 'source_after': source_after, 'source_unchanged': source_same,
    'candidate_before': candidate_before, 'candidate_after': candidate_after, 'candidate_unchanged': candidate_same,
    'reused_payloads': 277, 'original_process_tests_unchanged': True, 'original_resource_tests_unchanged': True,
    'specification_bindings': specs, 'imports': imports, 'all_imports_own_cut': all_imports_own_cut,
    'native_observations': native, 'clock_info': {name: vars(time.get_clock_info(name)) for name in ('monotonic', 'perf_counter')},
    'fixture_events': events, 'native_process_metadata': native_process_metadata, 'new_retained_native_child_names': sorted(path.name for path in new_children),
    'new_fixture_files': new_fixture_files, 'preexisting_fixture_files_unchanged': True,
    'limits': ['All314 unchanged cases execute on frozen Q; Source application remains unperformed',
        'Only fresh Q native fixture children explicitly authorized by coordinator; original fixture ROOT guard unchanged',
        'Native observation/producer and recorder integration does not authenticate canonical clock/source authority or principals',
        'Direct E3 interpreter and native custodian remain shared administrator dependencies'],
    'exit_status': 0 if passed else 1}
write_new(O / 'connected-independent.json', out)
print(json.dumps({'stage': 'independent_cohort_complete', 'tests_run': result.testsRun, 'failures': len(result.failures),
    'errors': len(result.errors), 'skips': len(result.skipped), 'exit_status': out['exit_status'], 'receipt_sha256': sha(O / 'connected-independent.json')}), flush=True)
raise SystemExit(out['exit_status'])
