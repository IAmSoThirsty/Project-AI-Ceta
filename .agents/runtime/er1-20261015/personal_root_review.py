"""Personally check the distinct ER1 findings and their exact current bindings."""
from pathlib import Path
import json
import sys

F=Path('T:/00-Active/Project-AI-CETA')
R=Path(__file__).resolve().parent;V=R/'independent-review';Q=F/'.agents/er1-20261015'
sys.path.insert(0,str(F/'.agents/runtime/ka1-20261014'))
import ka1_support as s
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_persistence import sha256_json
read=lambda path:json.loads(path.read_bytes())
pins={'review.json':'78c5c16834bdfce0401e10ec97ce02ca198be473e9fb8ad55c08282918f12c8d',
 'REPORT.json':'4232e106918230e1d23ba888ff12d1462e530860213505519ef767da0d3cea10',
 'REVIEW-READBACK.json':'118e32436ebaadf7441b2779ffe09d32241fa37d2c76fb729cd45d73ccab2c05',
 'REVIEW-SEAL.json':'fb61903e3f591326fad03ff4f61e86719ad8adc31dcdb2d7cc47a77cd67ea752'}
for name,pin in pins.items():assert s.sha(V/name)==pin
assert s.sha(Q/'TRANSFER-MANIFEST.json')=='0d00ab72103eab15319ae2266e63a5834bea378e4422df5d475a0240a26c1f25'
seal=read(V/'REVIEW-SEAL.json')
for row in seal['members'].values():assert s.ordinary(Path(row['path']))==row
local=read(V/'review.json');stored=read(R/Q.name/'receipts/review.json')
assert len(local)==13 and len(stored)==16 and {k:stored[k] for k in local}==local
fingerprint=sha256_json({k:v for k,v in stored.items() if k!='receipt_hash'})
state=read(R/Q.name/'state.json');node=state['nodes']['review']
assert fingerprint==stored['receipt_hash']==node['receipt_hash']
assert read(R/Q.name/'results/review.json')==dict(node_id='review',receipt_hash=fingerprint,result=local['result'])
assert node['artifact_hash']==sha256_json(dict(input_hash=local['input_hash'],result=local['result']))
assert state['sequence']==9 and node['state']=='SUCCEEDED' and node['decision']=='approved'
assert read(R/Q.name/'claims.json')=={} and local['executor_id']=='/root/wt1_reviewer'
report=read(V/'REPORT.json');replay=read(V/'REPLAY-READBACK.json');extra=read(V/'HOSTILE-R1.json')
assert report['findings']==[] and report['independent_unique_methods_passed']==92
assert replay['tests_run']==85 and replay['exact_author85_ID_arrays_preserved']
assert extra['tests_run']==7 and extra['expected_ids']==extra['executed_ids']==extra['stopped_ids']
for proof in (replay,extra):assert all(proof[k]==0 for k in ('failures','errors','skips'))
assert extra['exit_status']==0 and extra['before_equals_after'] and not extra['blocked_noncontract_import_attempts'] and not extra['remaining_threads']
manifest=read(Q/'TRANSFER-MANIFEST.json')
for name,row in manifest['payloads'].items():
    assert s.ordinary(Q/name)==row['candidate']
    if row.get('parent') is not None:assert s.ordinary(Path(row['parent']['path']))==row['parent']
out=R/'PERSONAL-ROOT-REVIEW.json'
proof=dict(at=s.utc(),reviewer='/root',distinct_reviewer=local['executor_id'],
    manifest=s.reference(Q/'TRANSFER-MANIFEST.json'),review=s.reference(V/'review.json'),
    report=s.reference(V/'REPORT.json'),seal=s.reference(V/'REVIEW-SEAL.json'),
    sealed_members_rehashed=len(seal['members']),candidate_payloads_rehashed=len(manifest['payloads']),
    installed_review='SUCCEEDED',sequence=9,claims={},official_fingerprint=fingerprint,
    personally_inspected=['Exact structural scanner and remaining strict parser guards',
        'Reviewer declaration/AST comparison and original test conservation',
        '85-case replay receipt and seven-method independent vector/boundary results',
        'Same original retained request commitment; profile measurements include instrumentation overhead'],
    accepted_for='Five-path pure-contract component inclusion in a newly qualified source union',
    historical_JS2_failure_resolved=False,performance_generalization=False,
    Source_publication=False,full_gate_complete=False)
with out.open('x',encoding='utf8') as stream:json.dump(proof,stream,indent=2);stream.write('\n')
print(json.dumps(dict(personal_review=s.reference(out),members=len(seal['members']),methods=92,Source_publication=False)))
