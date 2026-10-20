"""Independent AC5 operator-tool checks. No native profile/process creation."""
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch
import ast, contextlib, ctypes, hashlib, importlib.util, io, json, os, stat, subprocess, sys, types, unittest, uuid

F = Path('T:/00-Active/Project-AI-CETA')
R = F / '.agents/runtime/ac6-profile-preparation-20261018'
D = Path(__file__).resolve().parent / 'controlled-r2'
D.mkdir(exist_ok=False)
assert D == R / 'controlled-r2'
assert Path(sys.executable) == F / '.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
sys.dont_write_bytecode = True
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
utc = lambda: datetime.now(timezone.utc).isoformat()
def write(path, value):
    assert Path(path).is_relative_to(D)
    with Path(path).open('x', encoding='utf8', newline='\n') as out:
        json.dump(value, out, indent=2, allow_nan=False); out.write('\n'); out.flush(); os.fsync(out.fileno())

TOOL = 'a7a86f8164df9d1c2a4de37503bd5476cab28c35333630ba0b8e56a6bf3dc061'
WRAPPER = 'b79b00b0cc2053efae21a3f7bec4a246eefec490ac4edc7ef65a37fd965a0206'
assert sha(R / 'profile_qualification.py') == TOOL
assert sha(R / 'run_one_approved_attempt_v2.py') == WRAPPER
assert sha(R / 'PROFILE-CREATION-PROPOSAL-AC6.json') == 'aa849834a68cd670928ea8f17dc446a50354442b2dbd658ed8889c0cdc982f49'
frozen_input_names = ['profile_qualification.py','run_one_approved_attempt_v2.py','PROFILE-CREATION-PROPOSAL-AC6.json','test_ac6_controlled_r2.py','profile_qualification.before-r2.py','run_one_approved_attempt_v2.before-r2.py','test_ac6_controlled.py','CONTROLLED-R1-FAILURE.json','controlled-r1/independent-r1.txt','PATH-PROJECTION.json','repair-r2.diff']
before_tool_hashes = {name:sha(R/name) for name in frozen_input_names}
blocked = []
real_dll = ctypes.WinDLL
class Forbidden:
    def __init__(self, name): self.name = name
    def __call__(self, *args, **kwargs):
        blocked.append(self.name); raise AssertionError('NATIVE_PROFILE_AND_PROCESS_CREATION_FORBIDDEN')
class DLL:
    def __init__(self, original): self.original = original
    def __getattr__(self, name):
        if name in ('CreateAppContainerProfile', 'DeleteAppContainerProfile', 'CreateProcessW',
                    'CreateProcessAsUserW', 'CreateProcessWithTokenW', 'CreateProcessWithLogonW', 'SetNamedSecurityInfoW', 'SetTokenInformation', 'AdjustTokenPrivileges'):
            return Forbidden(name)
        return getattr(self.original, name)
def guarded_dll(name, *args, **kwargs): return DLL(real_dll(name, *args, **kwargs))

with patch.object(ctypes, 'WinDLL', guarded_dll):
    spec = importlib.util.spec_from_file_location('independent_frozen_ac5_tool', R / 'profile_qualification.py')
    module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)

fs = module.fs
def ordinary(path):
    path = fs.safe_components(Path(path)); before = fs.file_identity(fs.lstat(path))
    size, digest, _ = fs.hash_file(path)
    assert fs.file_identity(fs.lstat(path)) == before and size == before['bytes']
    return {'sha256': digest, 'native_identity': before}
def inventory(root):
    if root == R: return {name:ordinary(R/name) for name in frozen_input_names}
    result = {}
    for base, directories, files in os.walk(root, followlinks=False):
        directories[:] = [name for name in directories if Path(base)/name != D]
        for name in list(directories):
            path = Path(base) / name
            assert not fs.reparse(fs.lstat(path)), path
        for name in files:
            path = Path(base) / name; assert stat.S_ISREG(fs.lstat(path).st_mode)
            result[path.relative_to(root).as_posix()] = ordinary(path)
    return result

before_source, before_candidate = module.source_cut(), module.candidate_cut()
before_tool = inventory(R)
before_manifest = ordinary(module.SOURCE_BASELINE)
before_dependencies = {name: ordinary(F / name) for name in module.DEPENDENCIES}
before_original = {name: ordinary(F / name) for name in (
    '.agents/runtime/ac3-20261014/profile-tool/profile_qualification.py',
    '.agents/runtime/ac3-20261014/profile-tool/test_profile_qualification.py',
    '.agents/runtime/ac3-20261014/profile-tool/ROOT-FINDINGS.json',
    '.agents/runtime/ac3-20261014/profile-tool/collaborative-review-20261015/REPORT.json',
    '.agents/runtime/ac5-20261015/independent-root-review/review.json',
    '.agents/runtime/real-effect-20261014/ac5_tool_diagnostic_tests.py')}
git_args = (('rev-parse', '--show-toplevel', '--git-common-dir', 'HEAD'),
            ('status', '--porcelain=v1', '--untracked-files=no'))
before_git = [fs.text_git(F, *args) for args in git_args]
write(D / 'BEFORE.json', {'at': utc(), 'source': before_source, 'candidate': before_candidate,
    'manifest': before_manifest, 'tool_tree': before_tool, 'dependencies': before_dependencies,
    'originals': before_original, 'git': before_git, 'script': ordinary(__file__)})

parent_tree = ast.parse((F / '.agents/runtime/ac5-profile-tool-20261015/profile_qualification.py').read_text())
tool_tree = ast.parse((R / 'profile_qualification.py').read_text())
dump = lambda node: ast.dump(node, include_attributes=False)
parent_funcs = {n.name: n for n in parent_tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
tool_funcs = {n.name: n for n in tool_tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
for name in ('validate_operator_record', 'assert_isolation', 'describe', 'inspect', 'folder', 'user_sid'):
    assert dump(parent_funcs[name]) == dump(tool_funcs[name]), name
old_methods = {n.name: n for n in parent_funcs['_QualificationRun'].body if isinstance(n, ast.FunctionDef)}
new_methods = {n.name: n for n in tool_funcs['_QualificationRun'].body if isinstance(n, ast.FunctionDef)}
changed_methods = [name for name in old_methods if dump(old_methods[name]) != dump(new_methods[name])]
assert changed_methods == ['snapshot']
assert dump(old_methods['snapshot']).replace('Source290_native_and_hash_conserved','Source352_native_and_hash_conserved').replace('candidate295_native_and_hash_conserved','execution_source352_native_and_hash_conserved') == dump(new_methods['snapshot'])
original_native_path = module._native_path
native_controls = []
def controlled_native_path(path, *, directory):
    native_controls.append({'path':str(path),'directory':directory,'classification':'CONTROLLED_PATH_NOT_NATIVE_OBSERVATION'})
    return r'\\?\Volume{00000000-0000-0000-0000-000000000000}\ac6' + ('' if directory else r'\assets\isolated_worker.exe')
def controlled_inspect():
    return {'name':module.NAME,'SID':module.SID,'user_sid':module.USER,'native_Create_or_Delete_executed':False,'activation_ready':False,
            'prior_folder':{'HRESULT':-2147024894,'path':None},'classification':'CONTROLLED_INSPECTION_NOT_HOST_OBSERVATION'}
# Test controls only: frozen tool was imported at its exact path first; redirect
# its evidence root into our exclusive output scope. Q/PROPOSAL/dependency pins stay exact.
module.R = D
N = D / 'negative-fixtures'; N.mkdir()
(N / 'profile_qualification.py').write_bytes((R / 'profile_qualification.py').read_bytes())
old_tests = F / '.agents/runtime/ac2-20261014/test_profile_preparation.py'
old_class = next(n for n in ast.parse(old_tests.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'ProfilePreparationTests')
scope = {'__name__': '__main__', 'module': module, 'R': N, 'D': N, 'F': F,
    'Path': Path, 'patch': patch, 'hashlib': hashlib, 'json': json, 'sys': sys,
    'unittest': unittest, 'uuid': uuid, 'types': types, 'io': io, 'ctypes': ctypes, 'contextlib': contextlib}
exec(compile(ast.Module(body=[old_class], type_ignores=[]), str(old_tests), 'exec'), scope)
negative_path = F / '.agents/runtime/ac5-profile-tool-20261015/test_profile_qualification.py'
with_body = next(n.body for n in ast.parse(negative_path.read_text()).body if isinstance(n, ast.With))
start = next(i for i,n in enumerate(with_body) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'binary' for t in n.targets))
stop = next(i for i,n in enumerate(with_body) if isinstance(n, ast.ClassDef) and n.name == 'RepairNegativeTests')
scope['original_read'] = module.fs.read_bytes
exec(compile(ast.Module(body=with_body[start:stop+1], type_ignores=[]), str(negative_path), 'exec'), scope)
diagnostic_path = F / '.agents/runtime/real-effect-20261014/ac5_tool_diagnostic_tests.py'
diagnostic_with = next(n for n in ast.parse(diagnostic_path.read_text()).body if isinstance(n, ast.With))
diagnostic_class = next(n for n in diagnostic_with.body if isinstance(n, ast.ClassDef))
exec(compile(ast.Module(body=[diagnostic_class], type_ignores=[]), str(diagnostic_path), 'exec'), scope)

class AdditionalSerializationTests(unittest.TestCase):
    def test_primary_snapshot_and_failure_list_retain_measured_values(self):
        error = KeyboardInterrupt('CONTROLLED_REJECTED_TOKEN')
        sample = scope['DiagnosticSerializationTests']().sample()
        BaseException.__dict__['__dict__'].__get__(error)['native_isolation_token_observation'] = sample
        run = module._QualificationRun(D / 'NOT_EXECUTED', 'CONTROLLED_NOT_AUTHORITY')
        run.fail(error, 'CONTROLLED_NATIVE_TOKEN_REJECTION')
        snapshot = json.loads(json.dumps(run.snapshot(), allow_nan=False))
        self.assertIs(run.primary_error, error)
        self.assertEqual(snapshot['primary_failure']['native_isolation_token_observation'], sample)
        self.assertEqual(snapshot['failures'][0]['native_isolation_token_observation'], sample)
        self.assertFalse(snapshot['positive_isolation_qualified'])
        self.assertFalse(snapshot['canonical_real_effect_accepted'])
    def test_malformed_data_never_changes_primary_or_qualifies(self):
        for bad in (None, [], {'schema': 1}, {'schema': 'ceta-rejected-isolation-token-v1',
                'classification': 'QUALIFIED'}, {'schema': 'ceta-rejected-isolation-token-v1',
                'classification': 'REJECTED_NATIVE_OBSERVATION', 'stage': object()}):
            with self.subTest(kind=type(bad).__name__):
                error = SystemExit(76)
                BaseException.__dict__['__dict__'].__get__(error)['native_isolation_token_observation'] = bad
                run = module._QualificationRun(D / 'NOT_EXECUTED', 'CONTROLLED_NOT_AUTHORITY')
                run.fail(error, 'CONTROLLED_REJECTION')
                result = json.loads(json.dumps(run.snapshot(), allow_nan=False))
                self.assertIs(run.primary_error, error)
                self.assertFalse(result['positive_isolation_qualified'])
                self.assertFalse(result['canonical_real_effect_accepted'])
                self.assertNotIn('native_isolation_token_observation', result['primary_failure'])
    def test_captured_support_functions_resolve_exact_Q_and_own_evidence_root(self):
        directory = D / ('support-binding-' + uuid.uuid4().hex)
        helper = module.prepare_probe(directory)
        defining = sys.modules['profile_r2_captured_ac_support']
        shim = sys.modules['ac_support']
        self.assertEqual((defining.Q, defining.R, defining.D), (module.Q, directory, directory))
        self.assertEqual((shim.Q, shim.R, shim.D), (module.Q, directory, directory))
        self.assertIs(helper.ordinary.__globals__, defining.__dict__)
        self.assertEqual(helper.ordinary.__globals__['Q'], module.Q)
        self.assertEqual(helper.ordinary.__globals__['R'], directory)
        with self.assertRaises(AssertionError): helper.write_new(D / 'FORBIDDEN-OUTSIDE-CAPTURE.json', {})

wrapper_path = R / 'run_one_approved_attempt_v2.py'
wrapper_tree = ast.parse(wrapper_path.read_text())
wrapper_statements = wrapper_tree.body
marker_index = next(i for i,n in enumerate(wrapper_statements) if isinstance(n, ast.Assert) and 'ONE-ATTEMPT-STARTED.json' in ast.unparse(n))
import_index = next(i for i,n in enumerate(wrapper_statements) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'spec' for t in n.targets))
wrapper_facts = []
def wrapper_fixture(label, *, review_decision='approved', wrong_review_hash=False,
        marker=False, prior=False, approval_error=True, profile_present=False,
        source_count=352, child_error=None, child_return=17, change_review_between_reads=False):
    directory = D / ('wrapper-' + label + '-' + uuid.uuid4().hex); directory.mkdir()
    review_file = directory / 'SYNTHETIC-REVIEW-NOT-AN-APPROVAL.json'
    initial_review = {'decision': review_decision, 'tool_sha256': TOOL,
        'classification': 'SYNTHETIC_CONTROL_ONLY_NOT_A_REAL_REVIEW_OR_APPROVAL'}
    write(review_file, initial_review)
    original_hash = sha(review_file)
    if marker: write(directory / 'ONE-ATTEMPT-STARTED.json', {'classification': 'SYNTHETIC_PREEXISTING_MARKER'})
    if prior: (directory / 'q-SYNTHETIC').mkdir()
    approval_file = directory / 'ABSENT-NONAPPROVAL.json'
    calls = []
    fake_module = types.ModuleType('CONTROLLED_WRAPPER_MODULE_NO_NATIVE_CODE')
    fake_module.validate_operator_record = lambda *args: (_ for _ in ()).throw(AssertionError('CONTROLLED_NO_APPROVAL')) if approval_error else calls.append('SIMULATED_VALIDATION_NO_AUTHORITY')
    fake_module.inspect = lambda: calls.append('SIMULATED_INSPECT') or {'prior_folder': {'HRESULT': 0 if profile_present else -2147024894, 'path': 'SYNTHETIC_PROFILE' if profile_present else None}}
    fake_module.source_cut = lambda: {str(n): 'SYNTHETIC' for n in range(source_count)}
    fake_module.candidate_cut = lambda: {str(n): 'SYNTHETIC' for n in range(352)}
    fake_module.now = utc
    fake_module.save = write
    class Loader:
        def exec_module(self, instance): instance.__dict__.update(fake_module.__dict__)
    fake_spec = types.SimpleNamespace(name='CONTROLLED_WRAPPER_IMPORT', loader=Loader())
    def child(*args, **kwargs):
        calls.append('SIMULATED_CHILD_NOT_EXECUTED')
        if child_error is not None: raise child_error
        return types.SimpleNamespace(returncode=child_return, stdout=b'CONTROLLED NO CHILD EXECUTED\n', stderr=b'CONTROLLED DENIAL\n')
    original_read_text = Path.read_text
    changed_hash = None
    captured_review_facts = []
    def captured_review(path, expected_sha):
        nonlocal changed_hash
        payload, identity = module.capture(path, expected_sha)
        captured_review_facts.append({'captured_sha256': hashlib.sha256(payload).hexdigest(), 'identity': identity})
        if change_review_between_reads and path == review_file:
            path.write_text(json.dumps(dict(initial_review, decision='approved')), encoding='utf8')
            changed_hash = sha(path)
        return payload, identity
    fake_module.capture = captured_review
    def drift(path, *args, **kwargs):
        nonlocal changed_hash
        if change_review_between_reads and path == review_file:
            replacement = dict(initial_review, decision='approved')
            path.write_text(json.dumps(replacement), encoding='utf8')
            changed_hash = sha(path)
        return original_read_text(path, *args, **kwargs)
    env = {'__name__': 'CONTROLLED_FROZEN_WRAPPER_AST', '__file__': str(wrapper_path)}
    argv = [str(wrapper_path), str(approval_file), '0'*64, str(review_file), 'f'*64 if wrong_review_hash else original_hash]
    caught = None
    with patch.object(sys, 'argv', argv), \
         patch.object(importlib.util, 'spec_from_file_location', lambda *args, **kwargs: fake_spec), \
         patch.object(importlib.util, 'module_from_spec', lambda spec: types.ModuleType(spec.name)), \
         patch.object(subprocess, 'run', child), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        try:
            # Exact prefix includes real frozen tool/proposal hashes; v2 captures review later.
            exec(compile(ast.Module(body=wrapper_statements[:marker_index], type_ignores=[]), str(wrapper_path), 'exec'), env)
            # Sole runtime test override redirects marker/raw/result writes to our own child.
            env['R'] = directory
            exec(compile(ast.Module(body=wrapper_statements[marker_index:], type_ignores=[]), str(wrapper_path), 'exec'), env)
        except BaseException as error: caught = error
    fact = {'label': label, 'directory': str(directory), 'calls': calls,
        'exception_type': type(caught).__name__ if caught is not None else None,
        'exception_text': str(caught) if caught is not None else None,
        'initial_review_sha256': original_hash, 'review_after_sha256': sha(review_file),
        'changed_review_sha256': changed_hash, 'captured_review_facts': captured_review_facts,
        'approval_file_exists': approval_file.exists(),
        'marker_exists': (directory / 'ONE-ATTEMPT-STARTED.json').exists(),
        'native_operation_executed': False, 'actual_child_executed': False}
    wrapper_facts.append(fact)
    return directory, calls, caught, fact

class WrapperNegativeTests(unittest.TestCase):
    def test_wrong_review_hash_refuses_before_approval(self):
        _, calls, error, _ = wrapper_fixture('wrong-hash', wrong_review_hash=True)
        self.assertIsInstance(error, AssertionError); self.assertEqual(calls, [])
    def test_rejected_review_refuses_before_approval(self):
        _, calls, error, _ = wrapper_fixture('rejected-review', review_decision='rejected')
        self.assertIsInstance(error, AssertionError); self.assertEqual(calls, [])
    def test_existing_marker_refuses_before_approval(self):
        _, calls, error, _ = wrapper_fixture('existing-marker', marker=True)
        self.assertIsInstance(error, AssertionError); self.assertEqual(calls, [])
        self.assertIn('PRIOR_ATTEMPT_MARKER_REFUSED', str(error))
    def test_existing_qualification_directory_refuses_before_approval(self):
        _, calls, error, _ = wrapper_fixture('existing-directory', prior=True)
        self.assertIsInstance(error, AssertionError); self.assertEqual(calls, [])
        self.assertIn('PRIOR_QUALIFICATION_DIRECTORY_REFUSED', str(error))
    def test_invalid_approval_cannot_inspect_or_write_marker_or_invoke(self):
        _, calls, error, fact = wrapper_fixture('no-approval')
        self.assertIsInstance(error, AssertionError); self.assertEqual(calls, [])
        self.assertFalse(fact['marker_exists']); self.assertFalse(fact['approval_file_exists'])
    def test_present_profile_refuses_before_marker(self):
        _, calls, error, fact = wrapper_fixture('present-profile', approval_error=False, profile_present=True)
        self.assertIsInstance(error, AssertionError); self.assertNotIn('SIMULATED_CHILD_NOT_EXECUTED', calls)
        self.assertFalse(fact['marker_exists'])
    def test_wrong_source_count_refuses_before_marker(self):
        _, calls, error, fact = wrapper_fixture('source-count', approval_error=False, source_count=289)
        self.assertIsInstance(error, AssertionError); self.assertNotIn('SIMULATED_CHILD_NOT_EXECUTED', calls)
        self.assertFalse(fact['marker_exists'])
    def test_spawn_failure_keeps_nooverwrite_marker_and_no_automatic_retry(self):
        directory, calls, error, fact = wrapper_fixture('spawn-failure', approval_error=False, child_error=OSError('CONTROLLED_SPAWN_REFUSAL'))
        self.assertIsInstance(error, OSError); self.assertTrue(fact['marker_exists'])
        self.assertEqual(calls.count('SIMULATED_CHILD_NOT_EXECUTED'), 1)
        self.assertFalse((directory / 'APPROVED-QUALIFICATION.json').exists())
    def test_nonzero_child_exit_is_preserved_with_raw_output(self):
        directory, calls, error, fact = wrapper_fixture('nonzero-child', approval_error=False)
        self.assertIsInstance(error, SystemExit); self.assertEqual(error.code, 17)
        self.assertEqual(calls.count('SIMULATED_CHILD_NOT_EXECUTED'), 1)
        value = json.loads((directory / 'APPROVED-QUALIFICATION.json').read_text())
        self.assertEqual(value['exit_status'], 17); self.assertFalse(value['automatic_retry'])
        self.assertEqual(value['stdout_sha256'], sha(directory / 'APPROVED-QUALIFICATION.stdout'))
        self.assertEqual(value['stderr_sha256'], sha(directory / 'APPROVED-QUALIFICATION.stderr'))
    def test_review_hash_checked_bytes_must_be_the_decoded_review(self):
        _, calls, error, fact = wrapper_fixture('review-between-reads', review_decision='rejected',
            approval_error=False, change_review_between_reads=True)
        self.assertNotEqual(fact['initial_review_sha256'], fact['review_after_sha256'])
        self.assertNotIn('SIMULATED_CHILD_NOT_EXECUTED', calls,
            'Checked rejected review bytes were replaced before decode; changed approved bytes reached invocation')


class CurrentSourceAndPathTests(unittest.TestCase):
    def test_execution_view_is_canonical_source352(self):
        self.assertEqual(module.Q, F)
        self.assertEqual(len(module.FROZEN),352)
        self.assertEqual(module.source_cut(),module.candidate_cut())
        self.assertEqual(Path(module.module.__file__).resolve(),(F/'src/ceta/supervisor/isolated_worker.py').resolve())
    def test_source_identity_drift_is_rejected(self):
        original=module.capture
        def changed(path,*args):
            if Path(path)==F/'src/ceta/supervisor/isolated_worker.py':raise AssertionError('CONTROLLED_SOURCE_IDENTITY_DRIFT')
            return original(path,*args)
        with patch.object(module,'capture',changed):
            with self.assertRaisesRegex(AssertionError,'CONTROLLED_SOURCE_IDENTITY_DRIFT'):module.source_cut()
    def test_projected_overlength_denies_before_copy(self):
        path=D/('long-layout-'+uuid.uuid4().hex)
        with patch.object(module,'_native_path',lambda *a,**k:'X'*230),patch.object(module,'write_payload') as write:
            with self.assertRaisesRegex(AssertionError,'PROBE_NATIVE_PATH_TOO_LONG'):module.prepare_probe(path)
            write.assert_not_called()
    def test_actual_image_overlength_denies_receipt(self):
        path=D/('long-image-'+uuid.uuid4().hex);path.mkdir()
        with patch.object(module,'_native_path',side_effect=['X'*180,'X'*258]):
            with self.assertRaisesRegex(AssertionError,'PROBE_NATIVE_PATH_TOO_LONG'):module.check_launch_paths(path,path/'image.exe')
        self.assertFalse((path/'LAUNCH-PATHS.json').exists())
    def test_projected_and_actual_receipts_are_distinct(self):
        path=D/('path-rows-'+uuid.uuid4().hex);path.mkdir()
        projected=module.check_launch_paths(path)
        actual=module.check_launch_paths(path,path/'image.exe')
        self.assertTrue(projected['predicted_fixture_suffix']);self.assertFalse(actual['predicted_fixture_suffix'])
        self.assertLess(projected['native_image_length'],258)
        self.assertFalse(actual['qualification_claim']);self.assertFalse(actual['missing_profile_causality_claim'])
    def test_native_reader_primary_reaches_canonical_cleanup(self):
        path=D/('path-primary-'+uuid.uuid4().hex);path.mkdir()
        primary=RuntimeError('CONTROLLED_PATH_PRIMARY');queued=[];finished=[]
        api=types.SimpleNamespace(CreateFileW=lambda *a:4321,queue_handle=queued.append,native_volume_path=lambda h:(_ for _ in ()).throw(primary))
        with patch.object(module.module,'_IsolationAPI',lambda:api),patch.object(module.module,'_finish_cleanup',lambda a,p:finished.append((a,p))):
            with self.assertRaises(RuntimeError) as caught:original_native_path(path,directory=True)
        self.assertIs(caught.exception,primary);self.assertEqual(queued,[4321]);self.assertEqual(finished,[(api,primary)])
    def test_captured_driver_checks_paths_before_api_and_launch(self):
        directory=D/('driver-guard-'+uuid.uuid4().hex)
        helper=module.prepare_probe(directory)
        self.assertIs(helper.check_launch_paths,module.check_launch_paths)
        body=ast.parse((directory/'native_fixture_support.py').read_text())
        run=next(n for n in body.body if isinstance(n,ast.FunctionDef) and n.name=='run_native_probe')
        statements=[ast.unparse(n) for n in run.body]
        self.assertTrue(statements[1].startswith('check_launch_paths(fixture, image)'))
        self.assertTrue(statements[2].startswith('control, api ='))
    def test_full_uuid_short_attempt_directory_and_unchanged_validator(self):
        function=tool_funcs['qualify']
        self.assertIn("'q-' + uuid.uuid4().hex",ast.unparse(function))
        self.assertEqual(dump(parent_funcs['validate_operator_record']),dump(tool_funcs['validate_operator_record']))

families = [scope['ProfilePreparationTests'], scope['RepairNegativeTests'],
    scope['DiagnosticSerializationTests'], AdditionalSerializationTests, WrapperNegativeTests, CurrentSourceAndPathTests]
suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in families)
def flat(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite): yield from flat(item)
        else: yield item
expected = [test.id() for test in flat(suite)]
assert len(expected) == len(set(expected)) == 57
executed, stopped = [], []
class Recorder(unittest.TextTestResult):
    def startTest(self, test): executed.append(test.id()); super().startTest(test)
    def stopTest(self, test): stopped.append(test.id()); super().stopTest(test)
def process_audit(event, args):
    if event in ('subprocess.Popen', 'os.system', 'os.startfile', 'socket.connect', 'socket.bind'):
        blocked.append(event); raise AssertionError('ALL_ACTUAL_PROCESS_CREATION_FORBIDDEN')
sys.addaudithook(process_audit)
with patch.object(ctypes, 'WinDLL', guarded_dll), patch.object(module,'_native_path',controlled_native_path), patch.object(module,'inspect',controlled_inspect), (D / 'independent-r1.txt').open('x', encoding='utf8') as output:
    result = unittest.TextTestRunner(stream=output, verbosity=2, resultclass=Recorder).run(suite)
assert executed == expected and stopped == expected
assert not blocked
after_source, after_candidate = module.source_cut(), module.candidate_cut()
after_tool = inventory(R)
after_dependencies = {name: ordinary(F / name) for name in before_dependencies}
after_original = {name: ordinary(F / name) for name in before_original}
assert before_source == after_source and before_candidate == after_candidate
assert before_tool == after_tool and before_dependencies == after_dependencies and before_original == after_original
assert before_manifest == ordinary(module.SOURCE_BASELINE)
assert not (R / 'ONE-ATTEMPT-STARTED.json').exists() and not list(R.glob('q-*'))
write(D / 'RESULT-r1.json', {'at': utc(), 'actor':'/root/native_denial_diagnosis', 'review_type':'AUTHOR_CONTROLLED_CHECKS_NOT_INDEPENDENT', 'new_source_path_methods':8, 'native_path_controls':native_controls, 'host_inspection':'CONTROLLED', 'tool_sha256': TOOL, 'wrapper_sha256': WRAPPER,
    'tests_run': result.testsRun, 'expected_ids': expected, 'executed_ids': executed, 'stopped_ids': stopped,
    'failures': [{'id': test.id(), 'traceback': trace} for test,trace in result.failures],
    'errors': [{'id': test.id(), 'traceback': trace} for test,trace in result.errors],
    'skips': result.skipped, 'exit_status': 0 if result.wasSuccessful() and not result.skipped else 1,
    'original_negative_methods': 30, 'controlled_variants': len(scope['outcomes']),
    'serialization_methods': 6, 'additional_serialization_and_binding_methods': 3,
    'wrapper_methods': 10, 'wrapper_facts': wrapper_facts, 'controlled_outcomes': scope['outcomes'],
    'raw_sha256': sha(D / 'independent-r1.txt'), 'forbidden_calls': blocked,
    'actual_profile_operations': [], 'actual_process_launches': [], 'actual_operator_approvals_created': [],
    'actual_tool_marker_created': False, 'source352_native_and_hash_exact': True,
    'execution_source352_native_and_hash_exact': True, 'all_frozen_ac6_inputs_exact': True,
    'changed_method_ASTs': changed_methods, 'operator_validator_AST_exact': True,
    'before_evidence_sha256': sha(D / 'BEFORE.json'),
    'harness_rebinding': ['tool.R -> reviewer scope after exact frozen import',
        'original negative tests R/D -> reviewer negative-fixtures',
        'wrapper AST split immediately before marker guard; R redirected only to reviewer child',
        'wrapper loader/approval/inspection/child controls are simulated; no genuine approval supplied',
        'v2 fixture calls actual frozen tool.capture, then changes ONLY own fixture bytes after capture returns; old hostile test method unchanged',
        'R1 rejected wrapper and all failing evidence remain historical and immutable'],
    'limitations': ['No profile or worker operation', 'No native isolation qualification',
        'Snapshot rejection data does not authenticate or authorize',
        'Author controlled checks, no independent approval; prior methods retained with explicit synthetic profile/path fixtures',
        'Synthetic wrapper flow tests do not execute real approval or child paths']})
print(json.dumps({'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
    'controlled_variants': len(scope['outcomes']), 'forbidden_calls': blocked}), flush=True)
sys.exit(0 if result.wasSuccessful() and not result.skipped else 1)
