"""Run the byte-exact three accepted AC2 adverse methods on actual AC3 imports."""
from ac3_support import *
D=R/'adverse-root-r1';D.mkdir();(D/'build-r2').mkdir()
original=F/'.agents/runtime/ac2-20261014/closure-r4/hostile_cleanup.py'
prior=json.loads((F/'.agents/runtime/ac2-20261014/closure-r4/hostile-cleanup-r1.json').read_text())
assert prior['tests_run']==3 and prior['exit_status']==0
binary=F/'.agents/runtime/ac1-20261014/build-r2/isolated_worker.exe'
assert sha(binary)=='527518104fb84c430e3e9e0be61982c533b0c6fbb13e1a85e959ba1a3866ad0f'
fs.write_new(D/'build-r2/isolated_worker.exe',fs.read_bytes(binary))
fs.write_new(D/'hostile_cleanup.py',fs.read_bytes(original))
shim='''from ac3_support import *
import atexit
R=D=Path(os.environ['CETA_AC3_ADVERSE_ROOT']).resolve(strict=True)
assert R.is_relative_to(F/'.agents/runtime/ac3-20261014')
sys.path.insert(0,str(Q/'src'))
from ceta.supervisor import isolated_worker as _module
_real_init=_module._IsolationAPI.__init__
_forbidden=[];_api_count=[]
def _guarded_init(api,*args,**kwargs):
    _real_init(api,*args,**kwargs);_api_count.append(1)
    def denied(*args):
        _forbidden.append('restricted_CreateProcessW');raise AssertionError('AC3_NO_RESTRICTED_CREATE_AUTHORITY')
    api.CreateProcessW=denied
    for name in ('CreateAppContainerProfile','DeleteAppContainerProfile'):
        def prohibited(*args,_name=name):
            _forbidden.append(_name);raise AssertionError('AC3_NO_PROFILE_MUTATION_AUTHORITY')
        setattr(api.userenv,name,prohibited)
_module._IsolationAPI.__init__=_guarded_init
def candidate_cut():
    inputs=json.loads((F/'.agents/runtime/ac3-20261014/SOURCE-INPUTS.json').read_text())
    return {name:ordinary(Q/name) for name in sorted(inputs['selected_dependencies'])}
def source_cut():
    inputs=json.loads((F/'.agents/runtime/ac3-20261014/SOURCE-INPUTS.json').read_text())
    return {name:ordinary(F/name) for name in inputs['Source_payloads']}
def _guard_record():
    write_new(D/'NO-PROFILE-GUARD.json',{'recorded_at':utc(),'guarded_API_constructions':len(_api_count),'forbidden_calls':_forbidden})
atexit.register(_guard_record)
'''
fs.write_new(D/'ac_support.py',shim.encode())
argv=[str(PY),'-B','-X','utf8',str(D/'hostile_cleanup.py')]
started=utc();done=subprocess.run(argv,cwd=F,capture_output=True,env=dict(os.environ,
    CETA_AC3_ADVERSE_ROOT=str(D),PYTHONPATH=str(R),PYTHONDONTWRITEBYTECODE='1'))
for suffix,raw in [('stdout.txt',done.stdout),('stderr.txt',done.stderr)]:
    with (D/('driver.'+suffix)).open('xb') as out:out.write(raw)
proof=json.loads((D/'hostile-cleanup-r1.json').read_text());guard=json.loads((D/'NO-PROFILE-GUARD.json').read_text())
write_new(R/'ADVERSE-QUALIFICATION-ROOT.json',{'started_at':started,'finished_at':utc(),'argv':argv,'exit_status':done.returncode,
    'original_oracle':ordinary(original),'copied_oracle':ordinary(D/'hostile_cleanup.py'),
    'actual_result':reference(D/'hostile-cleanup-r1.json'),'guard':reference(D/'NO-PROFILE-GUARD.json'),
    'all_original_method_bodies_and_raw_IDs_retained':proof['expected_ids']==proof['executed_ids']==prior['expected_ids'],
    'actual_native_facts':proof['native_facts'],'profile_or_restricted_creation_executed':False})
assert done.returncode==0 and proof['exit_status']==0 and proof['tests_run']==3
assert proof['failures']==proof['errors']==proof['skipped']==[] and proof['expected_ids']==proof['executed_ids']==prior['expected_ids']
assert proof['candidate_before']==proof['candidate_after'] and proof['source_before']==proof['source_after']
assert sha(original)==sha(D/'hostile_cleanup.py') and guard['forbidden_calls']==[]
print(json.dumps({'tests':3,'failures':0,'errors':0,'skips':0,'original_oracle_byte_exact':True,'forbidden_calls':[]}),flush=True)
