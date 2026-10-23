"""Close only a reviewed frozen timing candidate delivery; never canonical integration."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,sys
F=Path('T:/00-Active/Project-AI-CETA');B=F/'.agents/runtime/oq23/jb2';C=B/'control';W=B/'work';D=B/'delivery';RUN='ceta-jb23-r2'
os.environ.update(PYTHONDONTWRITEBYTECODE='1',GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false');sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_runtime import OrchestrationRuntime
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
 with p.open('x',encoding='utf8') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
assert len(sys.argv)==3;pin,rpin=sys.argv[1:];assert sha(W/'MANIFEST.json')==pin=='e9b0ac804a3bcebad266e400e6ce41a8fbb113749026230baf6e4ed59f93db72' and sha(B/'review/MANIFEST.json')==rpin
review=json.loads((B/'review/REVIEW.json').read_bytes());assert review['decision']=='approved' and review['manifest_sha256']==pin
assert review['root_candidate_closure_sha256']==sha(Path(__file__))
m=json.loads((W/'MANIFEST.json').read_bytes())
for name,v in m['files'].items():assert sha(W/name)==v['sha256'] and (W/name).stat().st_size==v['bytes']
for name,h in m['external_pins'].items():assert sha(Path(name))==h
assert not any(D.iterdir()) and not (C/'ROOT-CANDIDATE-COMPLETION.json').exists()
rt=OrchestrationRuntime(C);v=rt.verify(RUN);assert v['allowed'] and v['receipts_valid'] and v['states']['review']=='SUCCEEDED' and v['states']['validate']=='READY'
a=rt.claim(RUN,'validate','/root',workspace=B/'packet');assert a['allowed'];save(C/'ROOT-validate-claim-api.json',dict(api='OrchestrationRuntime.claim',response=a))
a=rt.run_gate(RUN,'validate');save(C/'ROOT-validate-gate-api.json',dict(api='OrchestrationRuntime.run_gate',response=a));assert a['allowed'] and a['states']['validate']=='SUCCEEDED'
a=rt.claim(RUN,'integrate','/root',workspace=D);assert a['allowed'];save(C/'ROOT-integrate-claim-api.json',dict(api='OrchestrationRuntime.claim',response=a));claim=json.loads((C/RUN/'claims.json').read_bytes())['integrate']
paths=sorted(p for p in (W/'candidate').rglob('*') if p.is_file());assert len(paths)==8
pins={}
for p in paths:
 rel=p.relative_to(W/'candidate');dest=D/'candidate'/rel;dest.parent.mkdir(parents=True,exist_ok=True);raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==m['files']['candidate/'+rel.as_posix()]['sha256']
 with dest.open('xb') as f:assert f.write(raw)==len(raw)
 pins[rel.as_posix()]=sha(dest)
save(D/'ACCEPTED-CANDIDATE.json',dict(recorded_at=datetime.now(timezone.utc).isoformat(),run_id=RUN,status='INDEPENDENTLY_REVIEWED_CONTROLLED_CANDIDATE_ONLY',manifest_sha256=pin,review_manifest_sha256=rpin,review_sha256=sha(B/'review/REVIEW.json'),candidate_files=pins,controlled_tests=136,retained_prior_test_ids=112,four_case_witness=4,canonical_integration_performed=False,native_execution_performed=False,admission_bound_ns=50000000,reliable_admission_timing='NOT_ESTABLISHED',reserves='UNMEASURED_ENGINEERING_POLICY',AC7_replay=False,full_product_acceptance=False,completion_percentage=None))
changed=sorted(p.relative_to(Path('T:/')).as_posix() for p in D.rglob('*') if p.is_file());receipt=dict(schema_version=1,run_id=RUN,node_id='integrate',executor_id='/root',started_at=claim['claimed_at'],finished_at=datetime.now(timezone.utc).isoformat(),input_hash=claim['input_hash'],changed_files=changed,result=dict(manifest_sha256=pin,review_manifest_sha256=rpin,candidate_files=pins,canonical_integration_performed=False,native_execution_performed=False,full_product_acceptance=False),commands=[],validations=[dict(name='Eight candidate bytes equal independently approved frozen inputs; ordinary exact preparation gate succeeded',passed=True)],exit_status=0)
save(C/'integrate-receipt.json',receipt);a=rt.complete(RUN,'integrate',C/'integrate-receipt.json');assert a['allowed'];save(C/'ROOT-integrate-complete-api.json',dict(api='OrchestrationRuntime.complete',response=a));v=rt.verify(RUN);assert v['allowed'] and v['receipts_valid'] and v['terminal_success'] and all(x=='SUCCEEDED' for x in v['states'].values());save(C/'verify-final-api.json',dict(api='OrchestrationRuntime.verify',response=v));save(C/'ROOT-CANDIDATE-COMPLETION.json',dict(run_id=RUN,terminal_success=True,all_actual_nodes_succeeded=True,manifest_sha256=pin,review_manifest_sha256=rpin,accepted_candidate_sha256=sha(D/'ACCEPTED-CANDIDATE.json'),verification_sha256=sha(C/'verify-final-api.json'),canonical_integration_performed=False,native_execution_performed=False,full_product_acceptance=False))
print(json.dumps(dict(terminal_success=True,states=v['states'],candidate_files=8,canonical_integration_performed=False,native_execution_performed=False)))
