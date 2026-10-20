"""Read-only source review and DATA_ONLY buffer probes; never binds a native DLL."""
from pathlib import Path
import ast
import ctypes as C
import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone

F = Path('T:/00-Active/Project-AI-CETA').resolve(strict=True)
D = Path(__file__).resolve(strict=True).parent
assert D == F / '.agents/runtime/ac7-token-contract-review-20261020'
R = F / '.agents/runtime/ac6-profile-preparation-20261018'
Q = R / 'q-a0f34385bc1a415e91da84232a428b13'
assert not (D / 'PURE-RESULT.json').exists()
blocked = []

def audit(event, args):
    if event in {'subprocess.Popen', 'os.system', 'os.startfile', 'sqlite3.connect',
                 'socket.__new__', 'ctypes.dlopen', 'ctypes.dlsym'}:
        blocked.append(event)
        raise AssertionError('READ_ONLY_PURE_REVIEW_FORBIDS_' + event)
    if event == 'open':
        name, mode, flags = args
        writing = bool((flags or 0) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if writing:
            target = Path(name).resolve()
            if not target.is_relative_to(D):
                blocked.append('write_outside_review')
                raise AssertionError('REVIEW_WRITE_SCOPE')

sys.addaudithook(audit)
def no_native(*args, **kwargs):
    raise AssertionError('NATIVE_LIBRARY_BINDING_FORBIDDEN')
C.WinDLL = no_native
sys.dont_write_bytecode = True
sys.path.insert(0, str(F / 'src'))
spec = importlib.util.spec_from_file_location('ac7_review_controlled_buffers',
    F / 'tests/contract/test_isolation_token_diagnostics.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
module = fixture.module

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

names = [
 'src/ceta/supervisor/isolated_worker.py',
 'native/windows_broker/isolated_worker.rs',
 'tests/contract/test_isolation_token_diagnostics.py',
 'tests/contract/test_isolated_worker.py',
 'contracts/ISOLATED_WORKER_V1.md',
 'docs/specification/21_windows_process_and_resource_enforcement.md',
 'policies/POL-13_windows_containment.md',
 '.agents/runtime/ac6-profile-preparation-20261018/profile_qualification.py',
 '.agents/runtime/ac1-20261014/build-r2/build.json',
 '.agents/runtime/ac1-20261014/build-r2/isolated_worker.exe',
 '.agents/runtime/ac6-profile-preparation-20261018/APPROVED-QUALIFICATION.json',
 '.agents/runtime/ac6-profile-preparation-20261018/OPERATOR-APPROVAL-20261020.json',
 '.agents/runtime/ac6-profile-preparation-20261018/PROFILE-CREATION-PROPOSAL-AC6.json',
]
names.extend(str(p.relative_to(F)).replace('\\', '/') for p in Q.iterdir() if p.is_file())
before = {name: sha(F / name) for name in names}
assert before[names[0]] == '1c3c880e6f089e9629b56f84d85da48f6aee12e3e78cf84a1a448970bee8d0f3'
assert before[names[1]] == '56c68f251ca45b8d88d1f7efbce41822a785effb510e43ec3933ea1544709a03'
assert before[names[7]] == 'a7a86f8164df9d1c2a4de37503bd5476cab28c35333630ba0b8e56a6bf3dc061'

class Controlled(fixture._ControlledBuffers):
    def __init__(self, *, raw, last_error, **kwargs):
        super().__init__(**kwargs)
        self.raw, self.last_error = raw, last_error
    def IsTokenRestricted(self, token):
        self.calls.append(('restricted',))
        C.set_last_error(self.last_error)  # ctypes private thread-local copy; no Windows call
        return self.raw

def observe(name, raw, last_error, **kwargs):
    api = Controlled(raw=raw, last_error=last_error, **kwargs)
    old_clock = module.time.monotonic_ns
    module.time.monotonic_ns = lambda: 11
    try:
        try:
            facts = module._IsolationAPI.token_facts(api, 55, 303)
        except fixture.ContractError as error:
            row = {'id': name, 'disposition': 'REJECTED', 'code': error.code,
                'observation': error.native_isolation_token_observation.copy()}
        else:
            row = {'id': name, 'disposition': 'ACCEPTED_DATA_SHAPE_ONLY',
                'restricted': facts.restricted}
    finally:
        module.time.monotonic_ns = old_clock
    row.update({'controlled_raw_result': raw, 'controlled_last_error': last_error,
        'calls': api.calls, 'closed_controlled_tokens': api.closed,
        'pending_handles': len(api._pending_handles),
        'pending_outputs': len(api._pending_token_outputs)})
    assert api.closed == [7701] and not api._pending_handles and not api._pending_token_outputs
    return row

cases = [observe('same_false_empty_or_unavailable_a', 0, 0),
         observe('same_false_empty_or_unavailable_b', 0, 5),
         observe('nonzero_bool_control', 1, 0),
         observe('unchanged_non_appcontainer_rejection', 1, 0, app=0),
         observe('unchanged_capability_rejection', 1, 0, capabilities=1),
         observe('unchanged_integrity_rejection', 1, 0, integrity='S-1-16-8192')]
assert cases[0]['observation'] == cases[1]['observation']
assert cases[0]['code'] == cases[1]['code'] == 'ISOLATION_TOKEN_NOT_QUALIFIED'
assert cases[2]['disposition'] == 'ACCEPTED_DATA_SHAPE_ONLY'
assert all(row['disposition'] == 'REJECTED' for row in cases[3:])
assert not any('last_error' in k or 'restricted_sid' in k for k in cases[0]['observation'])

tree = ast.parse((F / names[0]).read_text(encoding='utf-8'))
token_method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'token_facts')
queries = [n.args[1].value for n in ast.walk(token_method) if isinstance(n, ast.Call)
    and isinstance(n.func, ast.Attribute) and n.func.attr == 'token_data'
    and len(n.args) == 2 and isinstance(n.args[1], ast.Constant)]
assert queries == [29, 31, 30, 25] and 11 not in queries
launch = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'launch')
call_lines = {}
for n in ast.walk(launch):
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in {'CreateProcessW','token_facts','ResumeThread'}:
        call_lines.setdefault(n.func.attr, []).append(n.lineno)
assert len(call_lines['ResumeThread']) == 1 and len(call_lines['token_facts']) == 1
assert call_lines['CreateProcessW'][0] < call_lines['token_facts'][0] < call_lines['ResumeThread'][0]

source_before = json.loads((Q / 'SOURCE-BEFORE.json').read_bytes())
source_after = json.loads((Q / 'SOURCE-AFTER.json').read_bytes())
candidate_before = json.loads((Q / 'CANDIDATE-BEFORE.json').read_bytes())
candidate_after = json.loads((Q / 'CANDIDATE-AFTER.json').read_bytes())
assert source_before == source_after and candidate_before == candidate_after
assert len(source_before) == len(candidate_before) == 352
assert source_before[names[0]]['sha256'] == before[names[0]]
assert source_before[names[1]]['sha256'] == before[names[1]]
after = {name: sha(F / name) for name in names}
assert before == after and not blocked
record = {'schema':'ceta-ac7-token-contract-readonly-review-v1',
 'at':datetime.now(timezone.utc).isoformat(), 'actor':'/root/recovery_join_review20',
 'scope':'DATA_ONLY current-method controls and AST; no native isolation qualification',
 'command_argv':[sys.executable, '-B', '-X', 'utf8', str(Path(__file__).resolve())],
 'receipt_and_source_before':before, 'receipt_and_source_after':after, 'all_pins_unchanged':True,
 'controlled_cases':cases, 'same_false_different_error_indistinguishable':True,
 'ast':{'token_classes_queried':queries,'launch_call_lines':call_lines},
 'historical_ac6_snapshots_equal':True, 'historical_ac6_source_entries':352,
 'historical_ac6_candidate_entries':352, 'blocked_events':blocked,
 'native_profile_calls':[], 'native_worker_calls':[], 'listener_calls':[],
 'production_tests_run':0, 'production_source_changes':[], 'limitations':[
 'Zero and error5 were injected controls, not recovered AC6 API status.',
 'A successful data shape does not authenticate a token, execute a worker, or prove isolation.',
 'AC6 historical source identity is checked for the token/worker inputs; review does not compare all352 current source paths.']}
with (D / 'PURE-RESULT.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
print(json.dumps({'controlled_cases':len(cases),'result_sha256':sha(D/'PURE-RESULT.json'),
    'same_false_different_error_indistinguishable':True,'pins_unchanged':True,
    'native_operations':0,'blocked_events':blocked}))
