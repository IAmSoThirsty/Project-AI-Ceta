from pathlib import Path
import json, os, subprocess, sys
P=Path('T:/00-Active/Project-AI-CETA');Q=P/'.agents/en2-20261014';BASE=P/'.agents/runtime/en2-20261014';D=BASE/'independent-review';RUN='en2-20261014'
sys.path.insert(0,str(P/'.agents/runtime/ka1-20261014'));import ka1_support as s
s.Q=Q;s.R=D;s.RUN=RUN
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_receipts import validate_receipt,load_receipt
from taar.orchestration_runtime import _snapshot_workspace,_changed_files
claim=json.loads((BASE/RUN/'claims.json').read_text())['review'];graph=json.loads((BASE/RUN/'graph.json').read_text())['graph']
assert claim['executor_id']==s.ACTOR
changed=_changed_files(claim['baseline_snapshot'],_snapshot_workspace(Q,Path('T:/')));assert changed==[]
report=json.loads((D/'REPORT.json').read_text());assert report['decision']=='approved' and report['tests_run']==85
receipt=dict(schema_version=1,run_id=RUN,node_id='review',executor_id=s.ACTOR,started_at=claim['claimed_at'],finished_at=s.utc(),input_hash=claim['input_hash'],changed_files=[],
 result=dict(manifest_sha256=s.sha(Q/'TRANSFER-MANIFEST.json'),report=s.reference(D/'REPORT.json'),tests_run=85,original_cases=82,new_cases=3,Source290_retained=True,candidate295_retained=True,source_application=False),
 commands=[dict(command=str(s.PY)+' -B -X utf8 '+str(D/'run_review.py'),exit_status=0)],
 validations=[dict(name='exact_predicate_delta_original_AST_and_85_independent_cases',passed=True),dict(name='Source290_candidate295_native_bytes_and_ids_retained',passed=True)],exit_status=0,decision='approved')
kwargs=dict(run_id=RUN,node_id='review',executor_id=s.ACTOR,input_hash=claim['input_hash'],claimed_at=claim['claimed_at'],node=graph['nodes']['review'])
validate_receipt(receipt,**kwargs);s.write_new(D/'review.json',receipt);validate_receipt(load_receipt(D/'review.json'),**kwargs)
cmd=['powershell','-NoProfile','-File','T:/02-Config/agents/taar-orchestrate.ps1','node','complete',RUN,'review',str(D/'review.json'),'--runtime-root',str(BASE)]
r=subprocess.run(cmd,cwd='T:/00-Active',capture_output=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
(D/'review-complete.stdout.txt').write_bytes(r.stdout);(D/'review-complete.stderr.txt').write_bytes(r.stderr)
response=json.loads(r.stdout.decode('utf-8-sig'));s.write_new(D/'review-complete.json',dict(command_argv=cmd,exit_status=r.returncode,response=response));assert r.returncode==0 and response['allowed']
state=json.loads((BASE/RUN/'state.json').read_text());claims=json.loads((BASE/RUN/'claims.json').read_text());assert claims=={} and state['nodes']['review']['state']=='SUCCEEDED'
persisted=json.loads((BASE/RUN/'receipts/review.json').read_text());assert all(persisted[k]==v for k,v in receipt.items())
s.write_new(D/'ACTUAL-READBACK.json',dict(recorded_at=s.utc(),review_sha256=s.sha(D/'review.json'),manifest_sha256=s.sha(Q/'TRANSFER-MANIFEST.json'),state=state,claims=claims,authored_fields=len(receipt),persisted_fields=len(persisted),all_authored_fields_exact=True))
files={p.relative_to(D).as_posix():s.ordinary(p) for p in D.iterdir() if p.is_file()}
s.write_new(D/'REVIEW-SEAL.json',dict(recorded_at=s.utc(),files=files,review_sha256=s.sha(D/'review.json'),scope='EN2 independent review; reviewer released'))
print(json.dumps(dict(review_sha256=s.sha(D/'review.json'),readback_sha256=s.sha(D/'ACTUAL-READBACK.json'),seal_sha256=s.sha(D/'REVIEW-SEAL.json'),state=state['nodes']['review']['state'],sequence=state['sequence'],claims=claims,authored_fields=len(receipt),persisted_fields=len(persisted))),flush=True)
