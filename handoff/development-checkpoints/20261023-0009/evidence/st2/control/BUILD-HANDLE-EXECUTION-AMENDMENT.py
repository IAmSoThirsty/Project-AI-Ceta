"""Root creates an additive execution binding only after accepted DS2 ordinary closure."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,sys
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_persistence import sha256_json
F=Path('T:/00-Active/Project-AI-CETA');S=F/'.agents/runtime/oq23/st2';C=S/'control';W=S/'work';D=S/'delivery';Q=F/'.agents/runtime/oq23/ds2'
PREP='5729a01e71127efd8d9970e8b5d1405f9b297eb12e421e94946983f125c6ff32';GRAPH='997829e1616609bafc88eea12f601eba7d715ad0e03b27e55a3f1af59a0d51ed'
RUNNER='0923c3b1ec7081489d8c9f4dcee17083b3df6d65801215d6c4b27a288640bbf8';LAUNCHER='727a150fc63889a1a1cb9b158f90a99adbf76388edeef4c6b3224d232bfb498d'
def read_bytes(p):
 p=Path(p);assert p.is_absolute()
 text=str(p);prefix=chr(92)*2+'?'+chr(92)
 if os.name=='nt' and not text.startswith(prefix):
  assert not text.startswith(chr(92)*2),'UNC source outside exact drive-based scope'
  p=Path(prefix+text)
 return p.read_bytes()
def sha(p):return hashlib.sha256(read_bytes(p)).hexdigest()
def load(p):return json.loads(read_bytes(p))
def ref(p):return dict(path=str(p),sha256=sha(p))
def receipt_at(base,run,node):
 state=load(base/run/'state.json');n=state['nodes'][node]
 assert n['state']=='SUCCEEDED' and n['claim'] is None
 path=base/run/n['receipt_ref'];assert path.resolve().is_relative_to((base/run/'receipts').resolve())
 rec=load(path);assert rec['run_id']==run and rec['node_id']==node and rec['executor_id']==n['executor_id']
 assert type(rec['exit_status']) is int and rec['exit_status']==0
 assert type(rec['validations']) is list and all(type(x) is dict and x.get('passed') is True for x in rec['validations'])
 body=dict(rec);stored=body.pop('receipt_hash');assert sha256_json(body)==stored==n['receipt_hash']
 return state,n,rec

p=argparse.ArgumentParser();p.add_argument('--qualification-manifest-sha256',required=True);p.add_argument('--qualification-review-manifest-sha256',required=True);a=p.parse_args()
assert sha(W/'MANIFEST.json')==PREP and sha(C/'run_handle_qualified.py')==RUNNER and sha(C/'execute_handle_qualified_once.py')==LAUNCHER
assert sha(Q/'work/MANIFEST.json')==a.qualification_manifest_sha256 and sha(Q/'review-r2/MANIFEST.json')==a.qualification_review_manifest_sha256
v=load(Q/'control-r2/verify-final-api.json')['response'];qc=load(Q/'control-r2/ROOT-QUALIFICATION-COMPLETION.json');review=load(Q/'review-r2/REVIEW.json')
assert v['run_id']==qc['run_id']=='ceta-ds23-r2-gate-r2' and v['graph_fingerprint']==qc['graph_fingerprint']==GRAPH
assert v['receipts_valid'] and v['terminal_success'] and all(x=='SUCCEEDED' for x in v['states'].values())
assert qc['terminal_success'] and qc['canonical_or_installed_mutation'] is False and review['decision']=='approved'
assert qc['manifest_sha256']==a.qualification_manifest_sha256 and qc['review_manifest_sha256']==a.qualification_review_manifest_sha256
state=load(C/'ceta-st23-r2/state.json');assert not load(C/'ceta-st23-r2/claims.json')
assert state['nodes']['review']['state']=='SUCCEEDED' and state['nodes']['review']['decision']=='approved' and state['nodes']['validate']['state']=='SUCCEEDED'
assert state['nodes']['integrate']['state']==state['nodes']['evidence']['state']=='READY'
assert not any(D.iterdir()) and not (C/'EXECUTION-INTENT.json').exists() and not (C/'HANDLE-QUALIFIED-EXECUTION-AMENDMENT.json').exists() and not (C/'INDEPENDENT-HANDLE-EXECUTION-APPROVAL.json').exists()
for name in ('ROOT-INTEGRATE-CLAIM-PROCESS.json','ROOT-INTEGRATE-CLAIM-R2-PROCESS.json'):assert load(C/name)['actual_process_exit_status']==1
accepted=load(Q/'delivery/ACCEPTED-QUALIFICATION.json');assert accepted['source_qualification_run_id']=='ceta-ds23-r2' and accepted['provider_bytes_unchanged_by_gate_metadata_successor'] is True and accepted['original_gate_setup_rejected'] is True
old_state=load(Q/'control/ceta-ds23-r2/state.json');assert old_state['nodes']['review']['state']=='FAILED' and old_state['nodes']['review']['claim'] is None and load(Q/'review/REVIEW.json')['decision']=='rejected'
wm=load(Q/'work/MANIFEST.json');rm=load(Q/'review-r2/MANIFEST.json')
assert wm['run_id']=='ceta-ds23-r2' and rm['decision']=='approved'
assert review['manifest_sha256']==rm['candidate_manifest_sha256']==a.qualification_manifest_sha256
assert rm['review_sha256']==sha(Q/'review-r2/REVIEW.json')
for name,item in wm['files'].items():
 path=Q/'work'/name;assert path.resolve().is_relative_to((Q/'work').resolve());assert sha(path)==item['sha256'],('frozen work member drift',name)
for name,item in rm['files'].items():
 path=Q/'review-r2'/name;assert path.resolve().is_relative_to((Q/'review-r2').resolve());assert sha(path)==(item['sha256'] if type(item) is dict else item),('frozen review member drift',name)
helper=Q/'control-r2/ROOT-CLOSE-QUALIFICATION-R2.py'
assert review['root_candidate_closure_sha256']==rm['root_candidate_closure_sha256']==sha(helper)
assert qc['verification_sha256']==sha(Q/'control-r2/verify-final-api.json')
assert qc['accepted_qualification_sha256']==sha(Q/'delivery/ACCEPTED-QUALIFICATION.json')
assert accepted['work_manifest_sha256']==a.qualification_manifest_sha256 and accepted['review_manifest_sha256']==a.qualification_review_manifest_sha256
assert accepted['review_sha256']==sha(Q/'review-r2/REVIEW.json') and accepted['root_candidate_closure_sha256']==sha(helper)
assert accepted['provider']['path']==str(Q/'work/directory_snapshot.py') and accepted['provider']['sha256']==wm['provider_sha256']==wm['files']['directory_snapshot.py']['sha256']
assert accepted['controls_sha256']==wm['files']['CONTROLS-R2.json']['sha256'] and accepted['controlled_tests']==50
assert accepted['full_F_qualification_sha256']==wm['files']['FULL-F-QUALIFICATION.json']['sha256']
assert accepted['full_F_snapshot_sha256']==wm['files']['FULL-F-SNAPSHOT.json']['sha256']
assert accepted['access_time_policy_sha256']==wm['files']['ACCESS-TIME-OBSERVATION-POLICY.json']['sha256']
assert sha(Q/'packet-r2/INPUTS.json')=='3d249901dc59431ffe30d25a44996a01400b7bcf3ab91415922a74b1813dccc7'
relocation=load(Q/'packet-r2/ROOT-CLOSURE-RELOCATION-AMENDMENT.json');assert relocation['successor_helper']['sha256']==sha(helper)
qstate,qnode,qreceipt=receipt_at(Q/'control-r2','ceta-ds23-r2-gate-r2','review')
assert qnode['executor_id']=='/root/status_packet_review' and qreceipt['decision']=='approved'
assert qreceipt['result']['manifest_sha256']==a.qualification_manifest_sha256 and qreceipt['result']['review_sha256']==sha(Q/'review-r2/REVIEW.json') and qreceipt['result']['root_candidate_closure_sha256']==sha(helper)
qstate,qnode,qreceipt=receipt_at(Q/'control-r2','ceta-ds23-r2-gate-r2','validate')
assert qnode['validation_passed'] is True and qreceipt['validations']
assert qreceipt['commands']==[dict(command=load(Q/'packet-r2/INPUTS.json')['exact_gate_command'],exit_status=0)]
assert qstate['graph_fingerprint']==GRAPH and {n:item['state'] for n,item in qstate['nodes'].items()}==v['states']
assert not load(Q/'control-r2'/'ceta-ds23-r2-gate-r2/claims.json')
for qn in v['states']:receipt_at(Q/'control-r2','ceta-ds23-r2-gate-r2',qn)
srm=load(S/'review/MANIFEST.json');sreview=load(S/'review/REVIEW.json')
assert srm['decision']==sreview['decision']=='approved' and srm['manifest_sha256']==sreview['manifest_sha256']==PREP
for name,h in srm['files'].items():assert sha(S/'review'/name)==h,('original review member drift',name)
sstate,snode,sreceipt=receipt_at(C,'ceta-st23-r2','review');assert sreceipt['decision']=='approved'
assert sreceipt['result']['manifest_sha256']==PREP and sreceipt['result']['execution_amendment_sha256']=='cc7de6e2547f9b566d4dc6c3880c6a0ce3b4cbf13f5a82ebee7f7d42921efbff' and sreceipt['result']['closure_successor_sha256']=='9543dcaca98f74ec2836401cbbfc263a6521771f981b664b921caa4b261e2484'

sm=load(W/'MANIFEST.json')
for name,h in sm['work_hashes'].items():assert sha(W/name)==h,('original preparation member drift',name)
sstate,snode,sreceipt=receipt_at(C,'ceta-st23-r2','validate')
assert snode['validation_passed'] is True and sreceipt['validations']
sg=load(C/'ceta-st23-r2/graph.json');expected_s_command='"'+str(F/'.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe')+'" -B -X utf8 "'+str(W/'verify_prepared.py')+'"'
assert sg['fingerprint']==sstate['graph_fingerprint']=='d910dc965aeb7397df6e2bf9d23ef3a31f34ade6d171ffd972185d41aa94b62b'
assert sg['graph']['nodes']['validate']['commands']==[expected_s_command] and sreceipt['commands']==[dict(command=expected_s_command,exit_status=0)]


critical=[C/'AGENTS.md',C/'ceta-st23-r2/graph.json',Q/'packet-r2/ROOT-CLOSURE-RELOCATION-AMENDMENT.json',Q/'review/REVIEW.json',Q/'review/MANIFEST.json',Q/'control/ceta-ds23-r2/receipts/review.json',Q/'control-r2/AGENTS.md',Q/'packet-r2/INPUTS.json',Q/'work/MANIFEST.json',Q/'work/directory_snapshot.py',Q/'work/ACCESS-TIME-OBSERVATION-POLICY.json',Q/'control-r2/ROOT-CLOSE-QUALIFICATION-R2.py',Q/'work/FULL-F-QUALIFICATION.json',Q/'work/FULL-F-SNAPSHOT.json',Q/'review-r2/MANIFEST.json',Q/'review-r2/REVIEW.json',Q/'control-r2/ROOT-QUALIFICATION-COMPLETION.json',Q/'control-r2/verify-final-api.json',Q/'delivery/ACCEPTED-QUALIFICATION.json',S/'review/MANIFEST.json',S/'review/REVIEW.json',C/'EXECUTION-AMENDMENT.json',C/'ROOT-CLOSE-R2.py',C/'ROOT-INTEGRATE-CLAIM-PROCESS.json',C/'ROOT-INTEGRATE-CLAIM-R2-PROCESS.json',C/'independent-source-admission-r1/MANIFEST.json',C/'independent-source-admission-r1/SOURCE-ADMISSION-ASSESSMENT.json']
assert sha(C/'EXECUTION-AMENDMENT.json')=='cc7de6e2547f9b566d4dc6c3880c6a0ce3b4cbf13f5a82ebee7f7d42921efbff' and sha(C/'ROOT-CLOSE-R2.py')=='9543dcaca98f74ec2836401cbbfc263a6521771f981b664b921caa4b261e2484'
assert sha(S/'review/MANIFEST.json')=='469df543417b7d35d7673c388eb898f5b87bd09ac63cb27de509f543591c839f'
value=dict(schema_version=1,recorded_at=datetime.now(timezone.utc).isoformat(),run_id='ceta-st23-r2',prepared_manifest_sha256=PREP,runner_sha256=RUNNER,launcher_sha256=LAUNCHER,original_status_core_sha256=sha(W/'status_core.py'),qualification_run_id='ceta-ds23-r2-gate-r2',qualification_graph_fingerprint=GRAPH,qualification_manifest_sha256=a.qualification_manifest_sha256,qualification_review_manifest_sha256=a.qualification_review_manifest_sha256,qualification_closure=str(Q/'control-r2/ROOT-QUALIFICATION-COMPLETION.json'),qualification_verification=str(Q/'control-r2/verify-final-api.json'),source_provider=str(Q/'work/directory_snapshot.py'),support_pins={str(q):sha(q) for q in critical},change='Process-local exact F,F snapshot provider only; unchanged original ordinary-file observation and stock exclusion policy. Other workspace observations delegate to the original. The reviewed original four-target application, 29 record/construction cases, ordinary transitions and existing Root closure successor remain bound.',history=dict(original_failed_admissions_preserved=True,original_failure_paths_and_scalars='NOT_CAPTURED',original_causes='UNKNOWN',prior_unchanged_observer_continuation_consumed=True,DS1_rejection_preserved=True,DS2_accepted_only_after_actual_review_gate_and_delivery_closure=True),execution=dict(fresh_qualified_integrate_claims=1,fresh_qualified_evidence_claims=1,canonical_application_attempts=1,automatic_generic_retries=False,create_only_existing_execution_intent=True,normal_ordinary_gate_already_succeeded=True),scope=dict(canonical_targets=['build/progress.json','handoff/continuity.json','build/gates.json','src/ceta/contracts/construction.py'],canonical_runtime_or_test_behavior_change=False,installed_dependency_mutation=False,snapshot_override_installed=False,publications=False,native_worker_or_AC7_replay=False,full_product_acceptance=False),independent_composition_approval_required=True)
raw=(json.dumps(value,indent=2,allow_nan=False)+'\n').encode()
with (C/'HANDLE-QUALIFIED-EXECUTION-AMENDMENT.json').open('xb') as s:assert s.write(raw)==len(raw);s.flush();os.fsync(s.fileno())
print(json.dumps(dict(amendment_sha256=sha(C/'HANDLE-QUALIFIED-EXECUTION-AMENDMENT.json'),support_pins=len(critical),independent_composition_approval_required=True,canonical_or_installed_mutation=False)))
