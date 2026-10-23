from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,sys
F=Path('T:/00-Active/Project-AI-CETA');S=F/'.agents/runtime/oq23/st2';W=S/'work';R=S/'review';C=S/'control'
os.environ.update(GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false',PYTHONDONTWRITEBYTECODE='1');sys.path[:0]=[str(W),'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce']
import status_core as s,run_status as r
from taar.orchestration_runtime import OrchestrationRuntime
pin='5729a01e71127efd8d9970e8b5d1405f9b297eb12e421e94946983f125c6ff32';rp='469df543417b7d35d7673c388eb898f5b87bd09ac63cb27de509f543591c839f';ap='cc7de6e2547f9b566d4dc6c3880c6a0ce3b4cbf13f5a82ebee7f7d42921efbff';cp='9543dcaca98f74ec2836401cbbfc263a6521771f981b664b921caa4b261e2484'
assert s.sha(R/'MANIFEST.json')==rp
m=json.loads((R/'MANIFEST.json').read_bytes());rev=json.loads((R/'REVIEW.json').read_bytes())
for item in (m,rev):
 assert item['decision']=='approved' and item['manifest_sha256']==pin and item['execution_amendment_sha256']==ap and item['closure_successor_sha256']==cp
assert s.sha(C/'EXECUTION-AMENDMENT.json')==ap and s.sha(C/'ROOT-CLOSE-R2.py')==cp
full=s.snapshot(R,F,ignored=frozenset());current={Path(n).relative_to(R.relative_to(F)).as_posix():v for n,v in full['files'].items()}
assert full['excluded_symlinks']=={} and set(current)==set(m['files'])|{'MANIFEST.json'}
for n,h in m['files'].items():assert current[n]['sha256']==h and current[n]==m['file_native'][n],('review physical leaf drift',n)
assert set(full['directories'])==set(m['directory_identity'])
for n,v in m['directory_identity'].items():assert all(full['directories'][n][k]==x for k,x in v.items()),('review directory identity drift',n)
for n,h in m['external_pins'].items():assert s.sha(Path(n))==h,('external support drift',n)
assert s.sha(R/'REVIEW.json')=='40d58c5e21d4206a99d71467d7b7c7fb6f5e7a07ab33d7d5f9e03380bc2e5d84'
rt=OrchestrationRuntime(C);v=rt.verify(s.RUN);assert v['allowed'] and v['receipts_valid'] and v['states']['review']=='SUCCEEDED' and v['states']['validate']=='READY'
state=json.loads((C/s.RUN/'state.json').read_bytes());receipt_path=C/s.RUN/state['nodes']['review']['receipt_ref'];receipt=json.loads(receipt_path.read_bytes());assert receipt['decision']=='approved'
for k,h in [('manifest_sha256',pin),('execution_amendment_sha256',ap),('closure_successor_sha256',cp)]:assert receipt['result'][k]==h
b,q=r.load_prepared(pin);assert q.source_observation(b)==b['source_before']
result=dict(recorded_at=datetime.now(timezone.utc).isoformat(),recorded_by='/root',decision='PASS_EXACT_COMBINED_REVIEW',manifest_sha256=pin,review_manifest_sha256=rp,execution_amendment_sha256=ap,closure_successor_sha256=cp,physical_review_leaves_pinned=len(m['files']),physical_review_files_including_manifest=len(current),external_pins_reread=len(m['external_pins']),all_native_file_and_directory_identities_match=True,actual_review_state=v['states']['review'],actual_review_receipt_sha256=s.sha(receipt_path),stock_snapshot_complete_coverage_claim=False,full_physical_review_coverage_verified=True,canonical_source562_and_Git_index_unchanged=True,canonical_writes=False,full_product_acceptance=False)
s.save(C/'ROOT-COMBINED-REVIEW-PREFLIGHT.json',result);print(json.dumps(result))
