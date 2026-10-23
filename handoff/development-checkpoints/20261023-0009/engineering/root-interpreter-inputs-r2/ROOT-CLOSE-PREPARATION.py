"""Root completion of accepted private preparation; canonical Git remains unchanged."""
import os,sys
if sys.flags.optimize != 0:
 raise RuntimeError('CP9 requires unoptimized Python before imports or effects')
os.environ.pop('PYTHONOPTIMIZE',None)
from pathlib import Path
from datetime import datetime,timezone
import json,os,sys,subprocess
F=Path('T:/00-Active/Project-AI-CETA');P=F/'.agents/runtime/oq23/cp9';C=P/'control';W=P/'work';D=P/'delivery'
os.environ.update(PYTHONDONTWRITEBYTECODE='1',GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false');sys.path[:0]=[str(W),'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce']
import checkpoint_core as c
from verify_prepared import audit
from taar.orchestration_runtime import OrchestrationRuntime
assert len(sys.argv)==3;freeze_pin,review_pin=sys.argv[1:]
assert c.sha((W/'WORK-FREEZE.json').read_bytes())==freeze_pin and c.sha((P/'review/MANIFEST.json').read_bytes())==review_pin
review=json.loads((P/'review/REVIEW.json').read_bytes());assert review['decision']=='approved' and review['work_freeze_sha256']==freeze_pin
outcome=audit();assert outcome['status']=='PASS' and not any(D.iterdir()) and not (C/'ROOT-PREPARATION-COMPLETION.json').exists()
rt=OrchestrationRuntime(C);state=json.loads((C/c.RUN/'state.json').read_bytes());assert state['nodes']['review']['state']=='SUCCEEDED' and state['nodes']['review']['decision']=='approved' and state['nodes']['validate']['state']=='READY'
a=rt.claim(c.RUN,'validate','/root',workspace=P/'packet');assert a['allowed'];c.save(C/'ROOT-validate-claim-api.json',dict(api='OrchestrationRuntime.claim',response=a))
a=rt.run_gate(c.RUN,'validate');c.save(C/'ROOT-validate-gate-api.json',dict(api='OrchestrationRuntime.run_gate',response=a));assert a['allowed'] and a['states']['validate']=='SUCCEEDED'
a=rt.claim(c.RUN,'integrate','/root',workspace=D);assert a['allowed'];c.save(C/'ROOT-integrate-claim-api.json',dict(api='OrchestrationRuntime.claim',response=a));claim=json.loads((C/c.RUN/'claims.json').read_bytes())['integrate']
assert audit()==outcome
c.save(D/'COMPLETION.json',dict(recorded_at=datetime.now(timezone.utc).isoformat(),run_id=c.RUN,parent=c.PARENT,commit=outcome['commit'],work_freeze_sha256=freeze_pin,review_manifest_sha256=review_pin,prepared_sha256=c.sha((W/'prepared-0001/PREPARED.json').read_bytes()),final_input_sha256=c.sha((C/'FINAL-CANONICAL-INPUTS-R2.json').read_bytes()),actual_declared_gate_succeeded=True,private_index_and_object_store=True,parent_paths_modes_five_fixtures_six_pdf_exports_preserved=True,canonical_Git_HEAD_index_source_unchanged=True,publication=False,full_product_acceptance=False))
receipt=dict(schema_version=1,run_id=c.RUN,node_id='integrate',executor_id='/root',started_at=claim['claimed_at'],finished_at=datetime.now(timezone.utc).isoformat(),input_hash=claim['input_hash'],changed_files=[(D/'COMPLETION.json').relative_to(Path('T:/')).as_posix()],result=dict(work_freeze_sha256=freeze_pin,commit=outcome['commit'],private_preparation_only=True,canonical_Git_mutation=False,full_product_acceptance=False),commands=[],validations=[dict(name='Exact accepted frozen private preparation, ordinary declared gate, no canonical Git/source changes',passed=True)],exit_status=0)
c.save(C/'integrate-receipt.json',receipt);a=rt.complete(c.RUN,'integrate',C/'integrate-receipt.json');assert a['allowed'];c.save(C/'ROOT-integrate-complete-api.json',dict(api='OrchestrationRuntime.complete',response=a))
v=rt.verify(c.RUN);assert v['receipts_valid'] and v['terminal_success'] and all(x=='SUCCEEDED' for x in v['states'].values());c.save(C/'verify-final-api.json',dict(api='OrchestrationRuntime.verify',response=v))
c.save(C/'ROOT-PREPARATION-COMPLETION.json',dict(run_id=c.RUN,terminal_success=True,all_actual_nodes_succeeded=True,work_freeze_sha256=freeze_pin,review_manifest_sha256=review_pin,commit=outcome['commit'],verification_sha256=c.sha((C/'verify-final-api.json').read_bytes()),private_preparation_only=True,canonical_Git_mutation=False,publication=False,full_product_acceptance=False))
print(json.dumps(dict(terminal_success=True,states=v['states'],commit=outcome['commit'],closure_sha256=c.sha((C/'ROOT-PREPARATION-COMPLETION.json').read_bytes()),publication=False)))
