"""Submit one rejected review, verify persisted fields/state, then seal scope."""
from pathlib import Path
import json,os,subprocess,sys
F=Path('T:/00-Active/Project-AI-CETA');Q=F/'.agents/ac4-20261015';R=F/'.agents/runtime/ac4-20261015';D=Path(__file__).resolve().parent
sys.path.insert(0,str(F/'.agents/runtime/en1-20261014'));import en1_support as s
s.Q=Q;s.R=D
read=lambda path:json.loads(Path(path).read_text())
local=read(D/'review.json');assert local['decision']=='rejected' and local['exit_status']==1
assert local['result']['manifest']==s.reference(Q/'TRANSFER-MANIFEST.json')
assert local['result']['report']==s.reference(D/'REPORT.json')
claims=read(R/'ac4-20261015/claims.json');assert claims['review']['executor_id']=='/root/pressure_writer'
command=['powershell.exe','-NoProfile','-File','T:/02-Config/agents/taar-orchestrate.ps1',
    'node','complete','ac4-20261015','review',str(D/'review.json'),'--runtime-root',str(R)]
started=s.utc();done=subprocess.run(command,cwd='T:/00-Active',capture_output=True,
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',GIT_OPTIONAL_LOCKS='0',GIT_NO_LAZY_FETCH='1'))
(D/'complete.stdout.txt').open('xb').write(done.stdout);(D/'complete.stderr.txt').open('xb').write(done.stderr)
response=json.loads(done.stdout.decode('utf-8-sig'))
s.write_new(D/'complete.json',{'command_argv':command,'started_at':started,'finished_at':s.utc(),
    'exit_status':done.returncode,'response':response})
assert response.get('allowed') is False and response.get('code')=='EXECUTION_FAILED',response
state=read(R/'ac4-20261015/state.json');claims=read(R/'ac4-20261015/claims.json')
stored=read(R/'ac4-20261015/receipts/review.json')
strict={'schema_version','run_id','node_id','executor_id','started_at','finished_at','input_hash',
    'changed_files','decision','exit_status','result','commands','validations'}
assert set(local)==strict and set(stored)==strict|{'git_baseline','observed_git','receipt_hash'}
typed=lambda value:json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
assert all(typed(local[name])==typed(stored[name]) for name in strict)
assert state['sequence']==9 and state['nodes']['review']['state']=='FAILED' and claims=={}
assert state['nodes']['review']['decision']=='rejected' and state['nodes']['review']['claim'] is None
assert state['nodes']['review']['receipt_hash']==stored['receipt_hash']
graph=read(R/'ac4-20261015/graph.json')
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_graph import compile_graph
from taar.orchestration_runtime import _snapshot_workspace,_changed_files
assert compile_graph(Path('T:/'),Q).fingerprint==graph['fingerprint']==state['graph_fingerprint']
preparation=read(D/'REVIEW-PREPARATION.json')
assert _snapshot_workspace(Q,Path('T:/'))==preparation['candidate_snapshot']
for name,row in preparation['source_before_after'].items():assert s.ordinary(F/name)==row
s.write_new(D/'ACTUAL-REVIEW-READBACK.json',{'at':s.utc(),'actual_review_state':'FAILED','sequence':9,'claims':{},
    'persisted_decision':'rejected','persisted_exit_status':1,'strict_local_fields':13,'persisted_fields':16,
    'all13_fields_typed_JSON_equal':True,'graph_fingerprint':state['graph_fingerprint'],
    'local_review':s.reference(D/'review.json'),'persisted_review':s.reference(R/'ac4-20261015/receipts/review.json'),
    'actual_completion':s.reference(D/'complete.json'),'manifest':s.reference(Q/'TRANSFER-MANIFEST.json'),
    'report':s.reference(D/'REPORT.json'),'candidate_Source290_exact':True,
    'all_reviewer_owned_token_SID_resources_retired':True,'profile_operations':[],'worker_launches':[]})
members={}
for path in sorted(D.rglob('*')):
    info=s.fs.lstat(path);assert not s.fs.reparse(info)
    if path.is_file():members[path.relative_to(D).as_posix()]=s.ordinary(path)
s.write_new(D/'SCOPE-SEAL.json',{'sealed_at':s.utc(),'reviewer':'/root/pressure_writer',
    'manifest':s.reference(Q/'TRANSFER-MANIFEST.json'),'review':s.reference(D/'review.json'),
    'report':s.reference(D/'REPORT.json'),'readback':s.reference(D/'ACTUAL-REVIEW-READBACK.json'),
    'members':members,'self_excluded':True,'actual_review_state':'FAILED','claims':{},'further_reviewer_writes':'CLOSED',
    'Source_application':False})
print(json.dumps({'actual_review_state':'FAILED','decision':'rejected','sequence':9,'claims':{},
    'review':s.reference(D/'review.json'),'report':s.reference(D/'REPORT.json'),
    'readback':s.reference(D/'ACTUAL-REVIEW-READBACK.json'),'seal':s.reference(D/'SCOPE-SEAL.json')}))
