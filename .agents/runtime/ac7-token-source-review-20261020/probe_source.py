"""Independent DATA_ONLY review probes; no native test or Windows API executes."""
from pathlib import Path
import ast
import ctypes as C
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch

F = Path('T:/00-Active/Project-AI-CETA').resolve(strict=True)
Q = F / '.agents/ac7-token-contract-20261020'
R = F / '.agents/runtime/ac7-token-contract-20261020'
D = Path(__file__).resolve(strict=True).parent
assert D == F / '.agents/runtime/ac7-token-source-review-20261020'
assert not (D / 'PURE-RESULT.json').exists()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
M = R / 'safe-halt-20261020/AC7-PARTIAL-MANIFEST.json'
assert sha(M) == '381b4db26695ca95b9eb2514e843219baed1bcb3311cff62bbc7bfe5760a9719'
manifest = json.loads(M.read_bytes())
expected = manifest['payload_hashes']
assert len(expected) == 352
def inventory(root):
    out = {}
    for n in expected:
        p = (root / n).resolve(strict=True)
        assert p.is_relative_to(root)
        out[n] = sha(p)
    return out
before = inventory(Q)
assert before == expected
source_before = inventory(F)
blocked = []
def audit(event, args):
    if event in {'subprocess.Popen','os.system','os.startfile','sqlite3.connect',
                 'socket.__new__','ctypes.dlopen','ctypes.dlsym'}:
        blocked.append(event); raise AssertionError('PURE_REVIEW_PROHIBITED_' + event)
    if event == 'open':
        path, mode, flags = args
        if (flags or 0) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            assert Path(path).resolve().is_relative_to(D), 'WRITE_OUTSIDE_REVIEW'
sys.addaudithook(audit)
def deny_dll(*args, **kwargs):
    blocked.append('WinDLL'); raise AssertionError('WINDOWS_API_BINDING_PROHIBITED')
C.WinDLL = deny_dll
sys.dont_write_bytecode = True
sys.path.insert(0, str(Q / 'src'))
test_path = Q / 'tests/contract/test_isolation_token_diagnostics.py'
spec = importlib.util.spec_from_file_location('independent_ac7_buffers', test_path)
fixture = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)
module = fixture.module
assert Path(module.__file__).resolve() == (Q / 'src/ceta/supervisor/isolated_worker.py').resolve()
API = module._IsolationAPI

class Controlled(fixture._ControlledBuffers):
    def pending_native_resources(self):
        return tuple({'kind':'CONTROLLED_TOKEN_ONLY','handle':row['handle']} for row in self._pending_handles)
    def GetCurrentProcess(self): return 55

rows = []
def measured(raw, error, count):
    api = Controlled(restricted=raw, restricted_count=count, restriction_error_code=error)
    with patch.object(module.time, 'monotonic_ns', return_value=11):
        try: facts = API.token_facts(api, 55, 303)
        except fixture.ContractError as failure:
            result = {'accepted':False,'code':failure.code,'observation':failure.native_isolation_token_observation}
        else:
            result = {'accepted':True,'restricted':facts.restricted,
                'count':facts.restricted_sid_count,'raw':facts.restriction_raw_result,
                'error':facts.restriction_last_error}
    assert api.closed == [7701] and not api._pending_handles and not api._pending_token_outputs
    correct = (bool(raw) == (count > 0)) and (raw != 0 or error == 0)
    assert result['accepted'] == correct
    if raw == 0 and error:
        assert 'restricted_sid_count' not in result['observation']
        assert ('query',11) not in api.calls
    rows.append({'raw':raw,'error':error,'count':count,'result':result})
for raw in (0,1,2,-1,-(1<<31),(1<<31)-1):
    for error in (0,5,0xffffffff):
        for count in (0,1): measured(raw,error,count)

def facts(**kw):
    fields = dict(appcontainer_sid=fixture.SID,is_appcontainer=True,capability_count=0,
        integrity_rid=4096,restricted=False,observed_monotonic_ns=11,
        restricted_sid_count=0,restriction_last_error=0,restriction_raw_result=0)
    fields.update(kw)
    return module.IsolationTokenFacts(**fields)
typed_negatives = [dict(restriction_raw_result=True),dict(restriction_raw_result=None),
    dict(restriction_raw_result=1<<31),dict(restriction_raw_result=-(1<<31)-1),
    dict(restriction_last_error=True),dict(restriction_last_error=-1),
    dict(restriction_last_error=1<<32),dict(restricted_sid_count=True),
    dict(restricted_sid_count=-1),dict(restricted_sid_count=None),
    dict(restricted_sid_count=4097),dict(is_appcontainer=1),dict(is_appcontainer=False),
    dict(capability_count=False),dict(capability_count=1),dict(integrity_rid=8192),
    dict(observed_monotonic_ns=-1)]
for row in typed_negatives:
    try: facts(**row)
    except fixture.ContractError: pass
    else: raise AssertionError(('TYPED_NEGATIVE_ACCEPTED',row))

buffers=[]
for count,size in ((0,4),(0,3),(1,24),(1,23),(2,40),(2,39),(4095,65528),(4096,65536),
                   (4096,65544),(0,65537)):
    storage=C.create_string_buffer(size)
    if size>=4: module.DWORD.from_buffer(storage).value=count
    try: observed=module._restricted_sid_count(storage)
    except fixture.ContractError: observed='REJECTED'
    buffers.append({'count':count,'actual_buffer_bytes':size,'result':observed})
assert buffers[7]['result']=='REJECTED'
assert buffers[8]['result']==4096 and buffers[9]['result']==0
impossible_shape=facts(restricted=True,restricted_sid_count=4096,restriction_raw_result=1)
assert impossible_shape.restricted_sid_count==4096

production_controls=[]
for base in (KeyboardInterrupt,SystemExit):
    primary=base('CONTROLLED_PRIMARY')
    api=Controlled(restricted=False,restricted_count=0)
    api.query_failure,api.query_error=11,primary
    api.cleanup_error=RuntimeError('CONTROLLED_CLEANUP_FAILED')
    try: API.token_facts(api,55,303)
    except BaseException as error: captured=error
    else: raise AssertionError('PRIMARY_WAS_LOST')
    raw=BaseException.__dict__['__dict__'].__get__(captured)
    cleanup=raw['isolation_cleanup']
    assert captured is primary and cleanup.isolation_api is api and api._pending_handles
    api.cleanup_error=None;cleanup.close_cleanup()
    assert not api._pending_handles
    production_controls.append({'primary':base.__name__,'preserved':True,'exact_cleanup_owner':True,'controlled_recovery':True})

# Extract only the newly added test body as source. All its native names below
# are substituted with DATA_ONLY controls; no unittest native suite is loaded.
test_ast=ast.parse(test_path.read_text(encoding='utf8'))
method=next(n for n in ast.walk(test_ast) if isinstance(n,ast.FunctionDef)
    and n.name=='test_actual_current_token_restricting_list_and_immediate_error_agree')
namespace={'module':module,'C':C,'NATIVE_TOKEN_DIAGNOSTIC_RECEIPTS':[]}
exec(compile(ast.Module(body=[method],type_ignores=[]),str(test_path),'exec'),namespace)
body=namespace[method.name]
native_body_controls=[]
for base in (None,KeyboardInterrupt,SystemExit):
    api=Controlled(restricted=False,restricted_count=0)
    primary=None if base is None else base('CONTROLLED_PRIMARY_IN_EXTRACTED_BODY')
    secondary=RuntimeError('CONTROLLED_SECONDARY_CLEANUP')
    if primary is not None: api.query_failure,api.query_error=11,primary
    api.cleanup_error=secondary if base is not None else None
    receipts=namespace['NATIVE_TOKEN_DIAGNOSTIC_RECEIPTS'];receipts.clear()
    captured=None
    with patch.object(module,'_IsolationAPI',return_value=api):
        try: body(unittest.TestCase())
        except BaseException as error: captured=error
    row={'primary':None if base is None else base.__name__,
        'raised':None if captured is None else type(captured).__name__,
        'exact_primary_preserved':primary is not None and captured is primary,
        'secondary_became_primary':captured is secondary,
        'receipt_entries':len(receipts),'pending_controlled_handles':len(api._pending_handles),
        'explicit_cleanup_owner_on_raised':False if captured is None else
            'isolation_cleanup' in BaseException.__dict__['__dict__'].__get__(captured)}
    if base is None: assert captured is None and len(receipts)==1 and not api._pending_handles
    else:
        assert captured is secondary and len(receipts)==0 and len(api._pending_handles)==1
        assert not row['explicit_cleanup_owner_on_raised']
        api.cleanup_error=None;api.retry_cleanup()
    row['controlled_fixture_retired_by_reviewer']=not api._pending_handles
    native_body_controls.append(row)

source_ast=ast.parse((Q/'src/ceta/supervisor/isolated_worker.py').read_text(encoding='utf8'))
launch=next(n for n in ast.walk(source_ast) if isinstance(n,ast.FunctionDef) and n.name=='launch')
order={name:[n.lineno for n in ast.walk(launch) if isinstance(n,ast.Call)
    and isinstance(n.func,ast.Attribute) and n.func.attr==name]
    for name in ('CreateProcessW','token_facts','ResumeThread')}
assert len(order['CreateProcessW'])==len(order['token_facts'])==len(order['ResumeThread'])==1
assert order['CreateProcessW'][0]<order['token_facts'][0]<order['ResumeThread'][0]

artifact_names=['CONTROLLED-PARENT-R1.json','CONTROLLED-PARENT-R1.txt','run_controlled.py',
    'build_worker.py','build-r1/BUILD.json','build-r1/pure-rust-tests.stdout',
    'build-r1/isolated_worker.exe','build-r1/isolated_worker_token_tests.exe']
artifacts={n:sha(R/n) for n in artifact_names}
build=json.loads((R/'build-r1/BUILD.json').read_bytes())
assert build['source']['sha256']==before['native/windows_broker/isolated_worker.rs']
assert build['native_image']['sha256']==artifacts['build-r1/isolated_worker.exe']
assert build['pure_test_image']['sha256']==artifacts['build-r1/isolated_worker_token_tests.exe']
assert all(row['exit_status']==0 for row in build['commands'])
assert sha(R/'build-r1/pure-rust-tests.stdout')==build['commands'][-1]['stdout_sha256']
assert inventory(Q)==before and inventory(F)==source_before and sha(M)=='381b4db26695ca95b9eb2514e843219baed1bcb3311cff62bbc7bfe5760a9719'
assert not blocked
result={'schema':'ceta-ac7-independent-source-probes-v1','at':datetime.now(timezone.utc).isoformat(),
 'actor':'/root/recovery_join_review20','manifest_sha256':sha(M),'candidate_pins':before,
 'candidate352_unchanged':True,'source352_unchanged_during_review':True,
 'command_argv':[sys.executable,'-B','-X','utf8',str(Path(__file__).resolve())],
 'measured_cases':rows,'typed_negative_cases':typed_negatives,'buffer_cases':buffers,
 'data_shape_accepts_count4096':True,'production_primary_cleanup_controls':production_controls,
 'extracted_native_body_data_only_controls':native_body_controls,
 'launch_source_order':order,'reviewed_existing_artifact_hashes':artifacts,
 'old_parent27':'Reported success and matching raw digest; receipt lacks persisted per-source candidate hashes',
 'old_rust5':'Receipt and source/image/output hash bindings verified; executable not rerun',
 'native_test_runs':0,'native_profile_worker_listener_calls':[],'blocked_events':blocked,
 'findings':{'native_case_cleanup_primary_and_receipt_loss':'REPRODUCED_WITH_PURE_SUBSTITUTIONS',
    'count_parser_over_64k_acceptance':'REPRODUCED_PRIVATE_HELPER_ONLY_NATIVE_QUERY_GUARDS_BOUND'},
 'limits':['Controlled buffers prove the evaluated method behavior only.',
    'Extracted native-case body used exclusively fake APIs and fake handle7701.',
    'No native-current-token suite, actual Windows API, profile, worker, listener, compiler or Rust test executable was run.',
    'Successor qualification tool/oracle files are outside this partial-source review.']}
with (D/'PURE-RESULT.json').open('x',encoding='utf8') as out:json.dump(result,out,indent=2)
print(json.dumps({'measurement_matrix':len(rows),'typed_negatives':len(typed_negatives),
 'buffer_cases':len(buffers),'production_cleanup_controls':len(production_controls),
 'extracted_body_controls':len(native_body_controls),'candidate352_unchanged':True,
 'native_operations':0,'result_sha256':sha(D/'PURE-RESULT.json')}))
