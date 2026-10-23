from pathlib import Path
from datetime import datetime,timezone
import os,sys,json
F=Path('T:/00-Active/Project-AI-CETA');B=F/'.agents/runtime/oq23/br3';C=B/'control';RUN='ceta-br23-r3'
os.environ.update(GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false',PYTHONDONTWRITEBYTECODE='1');sys.path.insert(0,str(B/'work'))
import run_broader as b
from taar.orchestration_runtime import OrchestrationRuntime
assert len(sys.argv)==3;pin=sys.argv[1];review_pin=sys.argv[2];value,binding=b.load_prepared(pin)
assert b.sha(B/'review/MANIFEST.json')==review_pin
review=json.loads((B/'review/REVIEW.json').read_bytes());assert review['decision']=='approved' and review['manifest_sha256']==pin
assert b.sha(C/'execute_once.py')=='e9384efbf8bed7f8acdcec779de3f5a4361c542b951e3b82547907b27f0af85c'
rt=OrchestrationRuntime(C);verified=rt.verify(RUN);assert verified['receipts_valid'] and verified['states']['validate']=='READY'
response=rt.claim(RUN,'validate','/root',workspace=B/'packet');assert response['allowed'];b.r.save(C/'ROOT-validate-claim-api.json',dict(api='OrchestrationRuntime.claim',response=response))
response=rt.run_gate(RUN,'validate');b.r.save(C/'ROOT-validate-gate-api.json',dict(api='OrchestrationRuntime.run_gate',response=response));assert response['allowed'] and response['states']['validate']=='SUCCEEDED'
js9=Path(value['fixture_workspaces']['js9']);assert not js9.exists() and not js9.is_symlink();b.o.ancestors(F,js9.parent)
b.r.save(C/'BOOTSTRAP-INTENT.json',dict(recorded_at=datetime.now(timezone.utc).isoformat(),path=str(js9),action='CREATE_ONE_EMPTY_DECLARED_DIRECTORY_AFTER_REVIEW_AND_GATE',files_permitted=False,canonical_test_bodies_executed=False,full_product_acceptance=False));js9.mkdir(exist_ok=False)
assert set(b.o.snapshot(js9))=={'.'};b.r.save(C/'BOOTSTRAP-RESULT.json',dict(path=str(js9),empty=True,full_product_acceptance=False))
runtime=b.BoundRuntime(binding)
for node,workspace in binding['workspaces'].items():
 response=runtime.claim(RUN,node,'/root',workspace=Path(workspace));assert response['allowed'];b.r.save(C/('ROOT-'+node+'-claim-api.json'),dict(api='BoundRuntime.claim(stock transition with exact complete snapshot port)',response=response))
claims=b.require_live(binding);b.source_observation(binding)
b.r.save(C/'ROOT-RELEASE-READY.json',dict(recorded_at=datetime.now(timezone.utc).isoformat(),prepared_manifest_sha256=pin,review_manifest_sha256=b.sha(B/'review/MANIFEST.json'),exact_claims=list(claims),actual_gate_succeeded=True,source562_Git_index_native_unchanged=True,actual_logical_execution_leases=8,sequential_suite_driver=True,bounded_disposable_Python_custody_helpers=True,native_worker_or_live_profile_qualification=False,full_product_acceptance=False))
print(json.dumps(dict(ready=True,claims=list(claims),actual_gate='SUCCEEDED',prepared_manifest_sha256=pin)))
