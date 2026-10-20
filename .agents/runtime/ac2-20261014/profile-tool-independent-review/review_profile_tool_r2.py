"""Independent negative review only. Never authorize or mutate a host profile."""
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch
import ast, ctypes, hashlib, importlib.util, json, os, stat, sys, traceback, types, unittest, uuid

F = Path('T:/00-Active/Project-AI-CETA')
R = F / '.agents/runtime/ac2-20261014'
D = R / 'profile-tool-independent-review/attempt-r2'
PY = F / '.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
TOOL = R / 'profile_qualification.py'
TEST = R / 'test_profile_preparation.py'
PIN = '45c09e4cb0fe05d3993e8bb6f68b6414b6c0bd69e493736a0a36836aa681a3c9'
assert Path(sys.executable) == PY and not sys.flags.optimize and os.name == 'nt'
sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
digest = lambda raw: hashlib.sha256(raw).hexdigest()
sha = lambda path: digest(path.read_bytes())
read = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
utc = lambda: datetime.now(timezone.utc).isoformat()
assert sha(TOOL) == PIN
D.mkdir(exist_ok=False)

def save(path, value):
    assert path.is_relative_to(D)
    with path.open('x', encoding='utf-8', newline='\n') as output:
        json.dump(value, output, indent=2, allow_nan=False)
        output.write('\n'); output.flush(); os.fsync(output.fileno())

blocked_native = []
native_windll = ctypes.WinDLL
class ForbiddenProfileFunction:
    def __init__(self, name): self.name = name
    def __call__(self, *args):
        blocked_native.append(self.name)
        raise AssertionError('FORBIDDEN_ACTUAL_PROFILE_MUTATION:' + self.name)
class GuardedDLL:
    def __init__(self, original): self.original = original
    def __getattr__(self, name):
        if name in ('CreateAppContainerProfile', 'DeleteAppContainerProfile'):
            return ForbiddenProfileFunction(name)
        return getattr(self.original, name)
def guarded_windll(name, *args, **kwargs):
    return GuardedDLL(native_windll(name, *args, **kwargs))

with patch.object(ctypes, 'WinDLL', guarded_windll):
    spec = importlib.util.spec_from_file_location('independent_exact_profile_tool', TOOL)
    tool = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = tool
    spec.loader.exec_module(tool)
    # Retain exact reviewed bytes. The copy is not imported or executed.
    with (D / 'profile_qualification.py').open('xb') as output: output.write(TOOL.read_bytes())
    with (D / 'test_profile_preparation.original.py').open('xb') as output: output.write(TEST.read_bytes())

    input_paths = [TOOL, TEST, R / 'ac2_support.py',
        F / '.agents/runtime/ac1-20261014/native_fixture_support.py',
        F / '.agents/runtime/ac1-20261014/build-r2/isolated_worker.exe', tool.PROPOSAL,
        tool.Q / 'TRANSFER-MANIFEST.json',
        R / 'profile-preparation-tests-r1.json', R / 'profile-preparation-tests-r1.txt']
    input_before = {str(path.relative_to(F)): tool.observed(path) for path in input_paths}
    source_before = tool.source_cut()
    candidate_before = {relative: tool.observed(tool.Q / relative)
        for relative in read(tool.Q / 'TRANSFER-MANIFEST.json')['payloads']}
    save(D / 'INPUTS-BEFORE.json', {'at': utc(), 'inputs': input_before,
        'Source290': source_before, 'candidate294': candidate_before})

    # Exactly the original four TestCase method ASTs; only their harness R moves.
    test_tree = ast.parse(TEST.read_text(encoding='utf-8'))
    original_class = next(node for node in test_tree.body if isinstance(node, ast.ClassDef)
        and node.name == 'ProfilePreparationTests')
    namespace = {'__name__': '__main__', 'module': tool, 'R': D, 'Path': Path,
                 'patch': patch, 'hashlib': hashlib, 'json': json, 'sys': sys,
                 'unittest': unittest, 'uuid': uuid}
    exec(compile(ast.Module(body=[original_class], type_ignores=[]), str(TEST), 'exec'), namespace)
    original_suite = unittest.defaultTestLoader.loadTestsFromTestCase(namespace['ProfilePreparationTests'])
    original_ids = [case.id() for case in original_suite]
    with (D / 'original4-r1.txt').open('x', encoding='utf-8') as output:
        original_result = unittest.TextTestRunner(stream=output, verbosity=2).run(original_suite)
    save(D / 'original4-r1.json', {'at': utc(), 'expected_ids': original_ids,
        'tests_run': original_result.testsRun,
        'failures': [{'id': case.id(), 'traceback': trace} for case, trace in original_result.failures],
        'errors': [{'id': case.id(), 'traceback': trace} for case, trace in original_result.errors],
        'skips': original_result.skipped, 'exact_original_TestCase_AST': True,
        'harness_only_relocation': str(D), 'native_Create_Delete_executed': False,
        'raw_sha256': sha(D / 'original4-r1.txt')})
    assert original_result.wasSuccessful() and original_result.testsRun == 4

    # Execute the exact preparation function with controlled source read drift.
    # This function copies files/imports helpers; it does not launch the probe.
    binary = F / '.agents/runtime/ac1-20261014/build-r2/isolated_worker.exe'
    original_read_bytes = Path.read_bytes
    binary_reads = []
    controlled_body = b'CONTROLLED_BINARY_DRIFT_NEGATIVE_ORACLE_NOT_EXECUTABLE\n'
    def drifted_read(path):
        if path == binary:
            binary_reads.append(str(path))
            if len(binary_reads) == 2: return controlled_body
        return original_read_bytes(path)
    copied = D / ('binary-drift-' + uuid.uuid4().hex)
    with patch.object(Path, 'read_bytes', drifted_read):
        helper = tool.prepare_probe(copied)
    copied_pin = sha(copied / 'build-r2/isolated_worker.exe')
    binary_finding = {'at': utc(), 'exact_prepare_probe_executed': True,
        'controlled_source_read_drift_only': True, 'native_probe_executed': False,
        'source_binary_reads': len(binary_reads), 'expected_IMAGE': tool.IMAGE,
        'copied_binary_sha256': copied_pin, 'copied_binary_matches_IMAGE': copied_pin == tool.IMAGE,
        'binding': read(copied / 'PROBE-BINDING.json'),
        'actual_original_binary_unchanged': tool.observed(binary) == input_before[str(binary.relative_to(F))]}
    assert len(binary_reads) == 2 and copied_pin != tool.IMAGE
    assert binary_finding['binding']['binary_sha256'] == tool.IMAGE
    assert binary_finding['actual_original_binary_unchanged']
    save(D / 'binary-drift-r1.json', binary_finding)

    # No operator record is constructed. This exact post-gate AST suffix tests
    # only exceptional control flow with entirely simulated profile APIs.
    full_tree = ast.parse(TOOL.read_text(encoding='utf-8'))
    qualify_node = next(node for node in full_tree.body if isinstance(node, ast.FunctionDef)
        and node.name == 'qualify')
    suffix = ast.FunctionDef(name='controlled_post_gate_suffix', args=qualify_node.args,
        body=[node for node in qualify_node.body if node.lineno >= 163],
        decorator_list=[], returns=None, type_comment=None, type_params=[])
    suffix.lineno, suffix.col_offset = qualify_node.lineno, qualify_node.col_offset
    suffix.end_lineno, suffix.end_col_offset = qualify_node.end_lineno, qualify_node.end_col_offset
    ast.fix_missing_locations(suffix)
    save(D / 'exception-oracle-binding.json', {
        'exact_tool_sha256': PIN, 'original_function': 'qualify',
        'original_post_gate_start_line': 163, 'original_gate_lines_not_executed': [155, 162],
        'suffix_ast_sha256': digest(ast.dump(suffix, include_attributes=False).encode()),
        'mode': 'CONTROLLED_NEGATIVE_EXCEPTION_ORACLE_ONLY',
        'genuine_operator_record_created': False, 'actual_Create_Delete_calls_permitted': False,
        'limitation': 'Simulated API outcome/control flow; no native profile effect or cleanup qualification.'})

    outcomes = []
    for label in ('create_return_write_fails', 'sid_text_fails', 'created_write_fails',
                  'retirement_write_fails'):
        case_root = D / ('controlled-' + label + '-' + uuid.uuid4().hex)
        case_root.mkdir()
        calls, saves, apis = [], [], []
        class ControlledFunction:
            def __init__(self, name): self.name = name
            def __call__(self, *args):
                calls.append(self.name)
                if self.name == 'simulated_Create':
                    ctypes.cast(args[-1], ctypes.POINTER(ctypes.c_void_p))[0] = ctypes.c_void_p(12345)
                    return 0
                return 0
        class ControlledAPI:
            def __init__(self):
                self.pending_sids = []; apis.append(self)
                self.userenv = types.SimpleNamespace(
                    CreateAppContainerProfile=ControlledFunction('simulated_Create'),
                    DeleteAppContainerProfile=ControlledFunction('simulated_Delete'))
            def sid_text(self, pointer):
                if label == 'sid_text_fails': raise RuntimeError('CONTROLLED_SID_CONVERSION_FAILURE')
                return tool.SID
            def release_sids(self): calls.append('simulated_FreeSid'); self.pending_sids.clear()
            def pending_native_resources(self): return tuple(self.pending_sids)
        class ControlledOwner:
            def __init__(self): pass
        def negative_probe(*args, **kwargs):
            raise RuntimeError('CONTROLLED_PROBE_DENIAL_NO_WORKER')
        def prepare_only(directory):
            directory.mkdir()
            return types.SimpleNamespace(run_native_probe=negative_probe)
        def save_case(path, value):
            saves.append(path.name)
            fault = {'create_return_write_fails': 'CREATE-RETURN.json',
                'created_write_fails': 'CREATED.json',
                'retirement_write_fails': 'RETIREMENT.json'}.get(label)
            if path.name == fault: raise OSError('CONTROLLED_EVIDENCE_WRITE_FAILURE:' + fault)
            save(path, value)
        local = dict(tool.__dict__)
        local.update(R=case_root, module=types.SimpleNamespace(_IsolationAPI=ControlledAPI,
            appcontainer_sid=lambda name: tool.SID), WindowsOwnedProcess=ControlledOwner,
            prepare_probe=prepare_only,
            inspect=lambda: {'prior_folder': {'HRESULT': -2147024894, 'path': None}},
            source_cut=lambda: {'CONTROLLED_READ_ONLY_SOURCE_CUT': True}, save=save_case)
        exec(compile(ast.Module(body=[suffix], type_ignores=[]), str(TOOL), 'exec'), local)
        caught = None
        try:
            local['controlled_post_gate_suffix'](None, 'CONTROLLED_NOT_AN_OPERATOR_APPROVAL')
        except BaseException as error:
            caught = {'type': type(error).__name__, 'text': str(error), 'traceback': traceback.format_exc()}
        all_files = [str(path.relative_to(case_root)) for path in case_root.rglob('*') if path.is_file()]
        result = {'label': label, 'controlled_non_native_calls': calls,
            'attempted_saves': saves, 'files': all_files, 'exception': caught,
            'simulated_pending_sid_addresses': [list(api.pending_sids) for api in apis],
            'final_RESULT_recorded': any(path.endswith('/RESULT.json') for path in all_files),
            'retained_profile_recorded': any(path.endswith('/PROFILE-RETAINED.json') for path in all_files),
            'actual_profile_mutation': False}
        assert caught and 'simulated_Create' in calls and 'simulated_Delete' not in calls
        assert not result['final_RESULT_recorded'] and not result['retained_profile_recorded']
        outcomes.append(result)
    save(D / 'exception-windows-r1.json', {'at': utc(), 'cases': outcomes,
        'native_Create_Delete_executed': False, 'operator_record_created': False})

    input_after = {str(path.relative_to(F)): tool.observed(path) for path in input_paths}
    source_after = tool.source_cut()
    candidate_after = {relative: tool.observed(tool.Q / relative)
        for relative in read(tool.Q / 'TRANSFER-MANIFEST.json')['payloads']}
    assert input_before == input_after and source_before == source_after and candidate_before == candidate_after
    assert not blocked_native
    save(D / 'CONSERVATION.json', {'at': utc(), 'inputs_after': input_after,
        'Source290_after': source_after, 'candidate294_after': candidate_after,
        'inputs_exact': True, 'Source290_native_and_hash_exact': True,
        'candidate294_native_and_hash_exact': True, 'profile_mutation_calls_attempted': blocked_native,
        'native_Create_Delete_executed': False, 'native_worker_or_job_created': False,
        'genuine_operator_approval_record_created': False})
print(json.dumps({'original_negative_methods': 4, 'original_pass': True,
    'confirmed_binary_copy_binding_defect': True,
    'controlled_exception_windows': len(outcomes), 'actual_profile_mutation': False,
    'Source290_candidate294_inputs_conserved': True}))
