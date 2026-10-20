"""Verify installed review receipt/result envelope and released scope exactly."""
from review_support import *
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_persistence import sha256_json
local=json.loads((D/'review.json').read_text())
persisted=json.loads((R/RUN/'receipts/review.json').read_text())
fields={'schema_version','run_id','node_id','executor_id','started_at','finished_at','input_hash',
    'changed_files','result','commands','validations','exit_status','decision'}
assert set(local)==fields and set(persisted)==fields|{'git_baseline','observed_git','receipt_hash'}
typed=lambda value:json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
for name in fields:assert typed(local[name])==typed(persisted[name])
assert sha256_json({key:value for key,value in persisted.items() if key!='receipt_hash'})==persisted['receipt_hash']
assert local['decision']=='approved' and local['exit_status']==0 and local['executor_id']==ACTOR and local['changed_files']==[]
state=json.loads((R/RUN/'state.json').read_text());claims=json.loads((R/RUN/'claims.json').read_text())
assert state['nodes']['review']['state']=='SUCCEEDED' and state['nodes']['review']['decision']=='approved'
assert state['nodes']['review']['executor_id']==ACTOR and state['sequence']==9 and claims=={}
assert state['nodes']['review']['receipt_hash']==persisted['receipt_hash']
envelope=json.loads((R/RUN/'results/review.json').read_text())
assert set(envelope)=={'node_id','receipt_hash','result'}
assert envelope['node_id']=='review' and envelope['receipt_hash']==persisted['receipt_hash']
assert typed(envelope['result'])==typed(local['result'])
assert state['nodes']['review']['artifact_hash']==sha256_json({'input_hash':local['input_hash'],'result':local['result']})
assert local['result']['manifest_sha256']==sha(Q/'TRANSFER-MANIFEST.json')=='8772cd735ae0ff767108976fef15e004012718ffded50a1d888cc354fae329ec'
setup=json.loads((D/'PREPARATION.json').read_text())
assert all(ordinary(Q/name)==row for name,row in setup['whole_Q'].items())
assert all(ordinary(F/name)==row for name,row in setup['Source290'].items())
write(D/'ACTUAL-READBACK.json',{'at':utc(),'local_review':ordinary(D/'review.json'),
    'persisted_review':ordinary(R/RUN/'receipts/review.json'),'strict13_persisted16_typed_equality':True,
    'normalized_receipt_fingerprint':persisted['receipt_hash'],'actual_result_envelope':ordinary(R/RUN/'results/review.json'),
    'exact_three_key_result_envelope_verified':True,'result_artifact_sha256':state['nodes']['review']['artifact_hash'],
    'manifest':ordinary(Q/'TRANSFER-MANIFEST.json'),'node_state':'SUCCEEDED','decision':'approved',
    'sequence':9,'claims':claims,'actual_state':state,'Source290_Q297_retained_at_readback':True,
    'Source_published':False,'formal_product_completion':False,
    'prior_setup_failure':ordinary(D/'PREPARATION-FAILURE-r1.json'),'no_transition_repeat':True})
members={}
for base,dirs,files in os.walk(D,followlinks=False):
    for name in dirs:assert not fs.reparse(fs.lstat(Path(base)/name))
    for name in files:
        path=Path(base)/name;members[path.relative_to(D).as_posix()]=ordinary(path)
write(D/'REVIEW-SEAL.json',{'at':utc(),'reviewer':ACTOR,'scope':str(D),'decision':'approved',
    'manifest_sha256':sha(Q/'TRANSFER-MANIFEST.json'),'review_sha256':sha(D/'review.json'),
    'readback_sha256':sha(D/'ACTUAL-READBACK.json'),'members':members,
    'self_excluded':['REVIEW-SEAL.json'],'actual_claim_released':True,'Source_application':False})
print(json.dumps({'review':'SUCCEEDED','decision':'approved','sequence':9,'claims':{},
    'review_sha256':sha(D/'review.json'),'report_sha256':sha(D/'REPORT.json'),
    'readback_sha256':sha(D/'ACTUAL-READBACK.json'),'seal_sha256':sha(D/'REVIEW-SEAL.json'),
    'sealed_files':len(members)}),flush=True)
