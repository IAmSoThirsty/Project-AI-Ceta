"""Record the demonstrated runner defect and terminally reject this exact cut."""
from pathlib import Path
import json, os, subprocess, sys

F=Path('T:/00-Active/Project-AI-CETA')
R=F/'.agents/runtime/f4-full-gate-successor-20261015'
Q=R/'candidate'; D=Path(__file__).resolve().parent; RUN=R.name
sys.dont_write_bytecode=True
sys.path.insert(0,str(F/'.agents/runtime/ka1-20261014'))
import ka1_support as s
s.Q=Q; s.R=R; s.RUN=RUN; s.ACTOR='/root'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
assert s.sha(D/'ORIGINAL-CASE-BOUNDARY-DEFECT-R1.json')=='95fa453a0ced8b0e858df50ded56a2a065f0be1cf53ec4d1f726e4926392ef71'
assert s.sha(Q/'TRANSFER-MANIFEST.json')=='043a722debd79ae1abd7d95414873f8893a326409ad6b2337e866eeaa9f438fe'
assert s.sha(R/'AUTHOR-SEAL.json')=='45e990dbfb74f7264277f70c7f7bc62aaea9c86efa315e0a77139bbfc2bcfbba'
seal=read(R/'AUTHOR-SEAL.json')
for name,row in seal['candidate_members'].items(): assert s.ordinary(Q/name)==row
for name,row in seal['author_evidence_members'].items(): assert s.ordinary(R/name)==row
proof=read(D/'ORIGINAL-CASE-BOUNDARY-DEFECT-R1.json')
assert proof['exact_exception_text']=="name '_Result__execution_gate' is not defined"
assert proof['gate_enter_calls']==proof['executed_method_ids']==[]
controls=read(D/'root42-r1/RESULT.json')
assert controls['tests_run']==42 and controls['exit_status']==0
assert not any(controls[k] for k in ('failures','errors','skips'))
claim=read(R/RUN/'claims.json')['review']
assert claim['executor_id']=='/root'
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_persistence import sha256_json
from taar.orchestration_runtime import _snapshot_workspace, _changed_files
from taar.orchestration_receipts import validate_receipt
assert _changed_files(claim['baseline_snapshot'],_snapshot_workspace(Q,Path('T:/')))==[]
report={'at':s.utc(),'reviewer':'/root','author':'/root/history_preservation','decision':'rejected',
 'manifest':s.reference(Q/'TRANSFER-MANIFEST.json'),
 'finding':proof['finding'],'severity':'blocking required original-case admission',
 'exact_original_class_boundary':s.reference(D/'ORIGINAL-CASE-BOUNDARY-DEFECT-R1.json'),
 'controlled_tests_passed':42,'controlled_result':s.reference(D/'root42-r1/RESULT.json'),
 'coverage_gap':'The earlier 42 controls did not execute Result.startTest at the original-case boundary.',
 'next_repair':proof['next_repair'],'candidate_and_author_evidence_preserved':True,
 'profile_or_native_case_executed':False,'Source_publication':False}
s.write_new(D/'REJECTED-REPORT.json',report)
receipt={'schema_version':1,'run_id':RUN,'node_id':'review','executor_id':'/root',
 'started_at':claim['claimed_at'],'finished_at':s.utc(),'input_hash':claim['input_hash'],'changed_files':[],
 'result':{'decision':'rejected','report':s.reference(D/'REJECTED-REPORT.json'),
   'controlled_tests_passed':42,'required_original_case_boundary_passed':False,'Source_publication':False},
 'commands':[{'command':str(s.PY)+' -B -X utf8 '+str(D/'prepare_review.py'),'exit_status':0},
   {'command':str(s.PY)+' -B -X utf8 '+str(D/'run_tests.py')+' root42-r1','exit_status':0},
   {'command':str(s.PY)+' -B -X utf8 '+str(D/'probe_original_case_boundary.py'),'exit_status':0}],
 'validations':[{'name':'42 controlled cases passed','passed':True},
   {'name':'exact original-case boundary admits its gate','passed':False},
   {'name':'candidate and author evidence preserved','passed':True}],
 'exit_status':0,'decision':'rejected'}
validate_receipt(receipt,run_id=RUN,node_id='review',executor_id='/root',input_hash=claim['input_hash'],
 claimed_at=claim['claimed_at'],node=read(R/RUN/'graph.json')['graph']['nodes']['review'])
s.write_new(D/'review-rejected.json',receipt)
command=['powershell','-NoProfile','-File','T:/02-Config/agents/taar-orchestrate.ps1',
 'node','complete',RUN,'review',str(D/'review-rejected.json'),'--runtime-root',str(R)]
started=s.utc()
done=subprocess.run(command,cwd=str(F),capture_output=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
for suffix,raw in (('stdout.txt',done.stdout),('stderr.txt',done.stderr)):
 with (D/('reject-complete.'+suffix)).open('xb') as stream:stream.write(raw)
response=json.loads(done.stdout.decode('utf-8-sig'))
s.write_new(D/'reject-complete.json',{'command_argv':command,'started_at':started,'finished_at':s.utc(),
 'exit_status':done.returncode,'response':response})
assert done.returncode==1 and response['allowed'] is False and response['code']=='REVIEW_REJECTED',response
stored=read(R/RUN/'receipts/review.json');state=read(R/RUN/'state.json');claims=read(R/RUN/'claims.json')
assert len(receipt)==13 and len(stored)==16
assert receipt=={key:stored[key] for key in receipt}
assert stored['receipt_hash']==sha256_json({key:value for key,value in stored.items() if key!='receipt_hash'})
assert read(R/RUN/'results/review.json')=={'node_id':'review','receipt_hash':stored['receipt_hash'],'result':stored['result']}
assert state['sequence']==9 and state['nodes']['review']['state']=='FAILED' and claims=={}
assert state['nodes']['review']['artifact_hash']==sha256_json({'input_hash':stored['input_hash'],'result':stored['result']})
s.write_new(D/'REJECTED-ACTUAL-READBACK.json',{'at':s.utc(),'local':s.reference(D/'review-rejected.json'),
 'persisted':s.reference(R/RUN/'receipts/review.json'),'official_fingerprint_and_envelope_verified':True,
 'state':'FAILED','sequence':9,'claims':{},'expected_complete_exit_status':1,'expected_code':'REVIEW_REJECTED',
 'Source_publication':False})
s.write_new(D/'REJECTED-REVIEW-SEAL.json',{'at':s.utc(),'reviewer':'/root','decision':'rejected',
 'members':{p.relative_to(D).as_posix():s.ordinary(p) for p in D.rglob('*') if p.is_file()},'claim_released':True})
print(json.dumps({'state':'FAILED','reason':'REVIEW_REJECTED','claims':{},
 'readback':s.reference(D/'REJECTED-ACTUAL-READBACK.json'),'seal':s.reference(D/'REJECTED-REVIEW-SEAL.json')}))
