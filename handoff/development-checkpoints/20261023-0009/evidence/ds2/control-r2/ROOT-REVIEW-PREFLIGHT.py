"""Root exact physical readback of the approved DS2 review and canonical conservation."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,os,sys
F=Path('T:/00-Active/Project-AI-CETA');B=F/'.agents/runtime/oq23/ds2';C=B/'control-r2';R=B/'review-r2';W=B/'work';S=F/'.agents/runtime/oq23/st2'
os.environ.update(GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false',PYTHONDONTWRITEBYTECODE='1');sys.path[:0]=[str(W),str(S/'work'),'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce']
import status_core as s
from taar.orchestration_runtime import OrchestrationRuntime
p=argparse.ArgumentParser();p.add_argument('--manifest-sha256',required=True);p.add_argument('--review-manifest-sha256',required=True);a=p.parse_args()
assert s.sha(W/'MANIFEST.json')==a.manifest_sha256 and s.sha(R/'MANIFEST.json')==a.review_manifest_sha256
m=json.loads((R/'MANIFEST.json').read_bytes());rev=json.loads((R/'REVIEW.json').read_bytes())
assert m['decision']==rev['decision']=='approved' and m['candidate_manifest_sha256']==rev['manifest_sha256']==a.manifest_sha256
assert m['root_candidate_closure_sha256']==rev['root_candidate_closure_sha256']==s.sha(C/'ROOT-CLOSE-QUALIFICATION-R2.py')
assert m['review_sha256']==s.sha(R/'REVIEW.json')
full=s.snapshot(R,F,ignored=frozenset());current={Path(n).relative_to(R.relative_to(F)).as_posix():v for n,v in full['files'].items()}
assert full['excluded_symlinks']=={} and set(current)==set(m['files'])|{'MANIFEST.json'}
for n,h in m['files'].items():assert current[n]['sha256']==h and current[n]==m['file_native'][n],('review physical file drift',n)
assert set(full['directories'])==set(m['directory_identity'])
for n,want in m['directory_identity'].items():assert all(full['directories'][n][k]==v for k,v in want.items()),('review directory drift',n)
for n,h in m['external_pins'].items():assert s.sha(Path(n))==h,('external pin drift',n)
rt=OrchestrationRuntime(C);v=rt.verify('ceta-ds23-r2-gate-r2');assert v['allowed'] and v['receipts_valid'] and v['states']['review']=='SUCCEEDED' and v['states']['validate']=='READY'
state=json.loads((C/'ceta-ds23-r2-gate-r2/state.json').read_bytes());node=state['nodes']['review'];assert node['decision']=='approved' and node['executor_id']=='/root/status_packet_review' and node['claim'] is None
receipt_path=C/'ceta-ds23-r2-gate-r2'/node['receipt_ref'];receipt=json.loads(receipt_path.read_bytes());assert receipt['decision']=='approved'
assert receipt['result']['manifest_sha256']==a.manifest_sha256 and receipt['result']['review_sha256']==s.sha(R/'REVIEW.json') and receipt['result']['root_candidate_closure_sha256']==s.sha(C/'ROOT-CLOSE-QUALIFICATION-R2.py')
import conservation
conservation.observe()
result=dict(recorded_at=datetime.now(timezone.utc).isoformat(),recorded_by='/root',decision='PASS_EXACT_DS2_QUALIFICATION_REVIEW',manifest_sha256=a.manifest_sha256,review_manifest_sha256=a.review_manifest_sha256,review_sha256=s.sha(R/'REVIEW.json'),root_candidate_closure_sha256=s.sha(C/'ROOT-CLOSE-QUALIFICATION-R2.py'),physical_review_leaves_pinned=len(m['files']),physical_review_files_including_manifest=len(current),external_pins_reread=len(m['external_pins']),actual_review_receipt_sha256=s.sha(receipt_path),full_physical_review_coverage_verified=True,canonical_source562_and_Git_index_ST2_unchanged=True,canonical_writes=False,full_product_acceptance=False)
s.save(C/'ROOT-REVIEW-PREFLIGHT.json',result);print(json.dumps(result))
