"""Bind the actual completed rejected predecessor, retaining earlier observations."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys
W=Path(__file__).resolve().parent;B=W.parent;OLD=B.parent/'ds1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pins={'review/REVIEW.json':'71d5f68a85fa1664570e6a10c1c71e78684e29eb7757510023bd5d01bc87b8f4',
    'review/MANIFEST.json':'a0675403728f8eecceb75ab1d5b0abf262679ae1dfc973f06e585baffc504728',
    'control/ceta-ds23-r1/receipts/review.json':'d13486fe5409baecfd0acb3b75ffa5363357b8aadd7b306edf7a60350477cd3c',
    'review/REVIEW-RECEIPT.json':'86150f1d073094e9148311c41e9bf2138d2efaecc192a951d5a47b93b2f40048'}
for rel,pin in pins.items():assert sha(OLD/rel)==pin,rel
prior=json.loads((W/'PRIOR-DS1-CONSERVATION.json').read_bytes())
for rel,pin in prior['files'].items():
    p=OLD/rel;assert sha(p)==pin['sha256'] and p.stat().st_size==pin['bytes'] and p.stat().st_mtime_ns==pin['mtime_ns'],rel
state=json.loads((OLD/'control/ceta-ds23-r1/state.json').read_bytes())
assert state['nodes']['review']['state']=='FAILED' and not json.loads((OLD/'control/ceta-ds23-r1/claims.json').read_bytes())
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_runtime import OrchestrationRuntime
v=OrchestrationRuntime(OLD/'control').verify('ceta-ds23-r1');assert v['receipts_valid']
value=dict(recorded_at=datetime.now(timezone.utc).isoformat(),run_id='ceta-ds23-r1',pins={str(OLD/k):v for k,v in pins.items()},
    actual_verification=v,actual_review_state='FAILED',claims_empty=True,
    original_successful_controls=41,original_full_F_pass_preserved=True,original_rejection_preserved=True,
    prior_work_and_review_files_exact=len(prior['files']))
with (W/'PRIOR-DS1-CLOSED.json').open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(prior_review='FAILED',prior_files_preserved=len(prior['files']),receipts_valid=True)))
