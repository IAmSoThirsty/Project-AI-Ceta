"""Read back the terminal rejection without re-completing the node."""
from pathlib import Path
import json,sys
F=Path('T:/00-Active/Project-AI-CETA');R=F/'.agents/runtime/f4-full-gate-successor-20261015';D=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.path.insert(0,str(F/'.agents/runtime/ka1-20261014'))
import ka1_support as s
s.Q=R/'candidate';s.R=R
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_persistence import sha256_json
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
local=read(D/'review-rejected.json');stored=read(R/R.name/'receipts/review.json')
state=read(R/R.name/'state.json');claims=read(R/R.name/'claims.json');node=state['nodes']['review']
assert len(local)==13 and len(stored)==16 and local=={k:stored[k] for k in local}
assert stored['receipt_hash']==sha256_json({k:v for k,v in stored.items() if k!='receipt_hash'})
assert read(R/R.name/'results/review.json')=={'node_id':'review','receipt_hash':stored['receipt_hash'],'result':stored['result']}
assert node['state']=='FAILED' and node['reason']=='Independent reviewer rejected the artifact'
assert node['artifact_hash'] is None and node['validation_passed'] is False
assert state['sequence']==9 and claims=={}
s.write_new(D/'REJECTED-ACTUAL-READBACK.json',{'at':s.utc(),'local':s.reference(D/'review-rejected.json'),
 'persisted':s.reference(R/R.name/'receipts/review.json'),'official_fingerprint_and_envelope_verified':True,
 'state':'FAILED','sequence':9,'claims':{},'artifact_hash':None,'expected_complete_exit_status':1,
 'expected_code':'REVIEW_REJECTED','Source_publication':False,
 'readback_assertion_correction':'Initial readback incorrectly expected a success artifact hash for a rejected node; actual null is preserved. No node operation was repeated.'})
s.write_new(D/'REJECTED-REVIEW-SEAL.json',{'at':s.utc(),'reviewer':'/root','decision':'rejected',
 'members':{p.relative_to(D).as_posix():s.ordinary(p) for p in D.rglob('*') if p.is_file()},'claim_released':True})
print(json.dumps({'state':'FAILED','sequence':9,'claims':{},'report':s.reference(D/'REJECTED-REPORT.json'),
 'readback':s.reference(D/'REJECTED-ACTUAL-READBACK.json'),'seal':s.reference(D/'REJECTED-REVIEW-SEAL.json')}))
