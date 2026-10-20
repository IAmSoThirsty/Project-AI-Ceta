"""Verify actual persisted completion, all fields and normalized fingerprint."""
from en_support import *

local_path,persisted_path=R/'implement.json',R/RUN/'receipts/implement.json'
local,persisted=json.loads(local_path.read_text()),json.loads(persisted_path.read_text())
fields={'schema_version','run_id','node_id','executor_id','started_at','finished_at',
    'input_hash','changed_files','result','commands','validations','exit_status'}
assert set(local)==fields and set(persisted)==fields|{'git_baseline','observed_git','receipt_hash'}
typed=lambda value:json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
for name in fields:assert typed(local[name])==typed(persisted[name])
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_persistence import sha256_json
assert sha256_json({k:v for k,v in persisted.items() if k!='receipt_hash'}) == persisted['receipt_hash']
state=json.loads((R/RUN/'state.json').read_text())
claims=json.loads((R/RUN/'claims.json').read_text())
assert state['nodes']['implement']['state']=='SUCCEEDED' and state['nodes']['review']['state']=='READY'
assert state['sequence']==7 and claims=={}
actual_result=json.loads((R/RUN/'results/implement.json').read_text())
assert set(actual_result)=={'node_id','receipt_hash','result'}
assert actual_result['node_id']=='implement' and actual_result['receipt_hash']==persisted['receipt_hash']
assert typed(actual_result['result'])==typed(local['result'])
manifest=json.loads((Q/'TRANSFER-MANIFEST.json').read_text())
assert local['result']['manifest']==reference(Q/'TRANSFER-MANIFEST.json')
assert all(ordinary(Q/name)==row for name,row in manifest['payloads'].items())
source=json.loads((R/'SOURCE-INPUTS.json').read_text())['Source290']
assert {name:ordinary(F/name) for name in source}==source
write_new(R/'AUTHOR-READBACK.json',{'at':utc(),'manifest':reference(Q/'TRANSFER-MANIFEST.json'),
    'local_implement':reference(local_path),'persisted_implement':reference(persisted_path),
    'local12_and_persisted15_fields_typed_exact':True,'normalized_fingerprint_verified':persisted['receipt_hash'],
    'state':state,'claims':claims,'actual_node_result':reference(R/RUN/'results/implement.json'),
    'frozen_payload_count':296,'Source290_conserved':True,'Source_application':False})
members=('HANDOFF.json','implement.json','AUTHOR-READBACK.json','SELF-REVIEW.json',
    'targeted-r2.json','targeted-r2.txt','targeted-r1.json','targeted-r1.txt',
    'before-r1.json','before-r1.txt','implementation-measures.json','SOURCE-INPUTS.json')
write_new(R/'AUTHOR-SEAL.json',{'at':utc(),'author':ACTOR,
    'manifest':reference(Q/'TRANSFER-MANIFEST.json'),'members':{name:reference(R/name) for name in members},
    'candidate_immutable':True,'actual_author_claim_released':True,'distinct_review_required':True,'Source_application':False})
print(json.dumps({'implement':'SUCCEEDED','review':'READY','sequence':7,'claims':claims,
    'manifest':reference(Q/'TRANSFER-MANIFEST.json'),'readback':reference(R/'AUTHOR-READBACK.json'),
    'seal':reference(R/'AUTHOR-SEAL.json')}))
