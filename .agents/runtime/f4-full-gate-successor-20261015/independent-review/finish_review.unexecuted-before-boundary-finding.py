"""Approve the exact engineering gate; keep execution and publication pending."""
from pathlib import Path
import json,sys
F=Path('T:/00-Active/Project-AI-CETA');R=F/'.agents/runtime/f4-full-gate-successor-20261015'
Q=R/'candidate';D=Path(__file__).resolve().parent;RUN=R.name
sys.dont_write_bytecode=True
sys.path.insert(0,str(F/'.agents/runtime/ka1-20261014'));import ka1_support as s
s.Q=Q;s.R=R;s.RUN=RUN;s.ACTOR='/root'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
norm=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
assert s.sha(Q/'TRANSFER-MANIFEST.json')=='043a722debd79ae1abd7d95414873f8893a326409ad6b2337e866eeaa9f438fe'
assert s.sha(R/'AUTHOR-SEAL.json')=='45e990dbfb74f7264277f70c7f7bc62aaea9c86efa315e0a77139bbfc2bcfbba'
ready=read(R/'READY-FOR-REVIEW.json');manifest=read(Q/'TRANSFER-MANIFEST.json');seal=read(R/'AUTHOR-SEAL.json')
proof=read(D/'root42-r1/RESULT.json');qualification=read(R/'QUALIFICATION.json');inputs=read(R/'INPUTS.json')
assert proof['exit_status']==0 and proof['tests_run']==42
assert proof['expected_ids']==proof['executed_ids']==proof['stopped_ids']
assert len(set(proof['expected_ids']))==42
assert not any(proof[k] for k in ('failures','errors','skips','forbidden_native_and_process_calls','remaining_threads','CETA_product_imports'))
assert proof['original_restricted_no_profile_case']=='NOT_RUN' and not proof['full_Source2053_executed']
for name,row in seal['candidate_members'].items():assert s.ordinary(Q/name)==row
for name,row in seal['author_evidence_members'].items():assert s.ordinary(R/name)==row
for name,row in qualification['Source290'].items():assert s.ordinary(F/name)==row
for name,row in qualification['F4_candidate336'].items():assert s.ordinary(Path(row['path']))==row
for name,row in qualification['E33601'].items():assert s.ordinary(s.PY.parent.parent/name)==row
assert s.fs.text_git(F,'rev-parse','HEAD')==inputs['HEAD']
assert s.fs.text_git(F,'branch','--show-current')==inputs['branch']
assert s.fs.text_git(F,'status','--porcelain=v1','-uno')==inputs['dirty']
scripts=ready['required_review_result_fields']['reviewed_successor_scripts']
assert scripts=={name:s.sha(Q/name) for name in scripts}
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_persistence import sha256_json
from taar.orchestration_runtime import _snapshot_workspace,_changed_files,_artifact_hash
from taar.orchestration_receipts import validate_receipt
author=read(R/'implement.json');stored_author=read(R/RUN/'receipts/implement.json')
assert len(author)==12 and len(stored_author)==15
assert norm(author)==norm({k:stored_author[k] for k in author})
assert stored_author['receipt_hash']==sha256_json({k:v for k,v in stored_author.items() if k!='receipt_hash'})
assert read(R/RUN/'results/implement.json')=={'node_id':'implement','receipt_hash':stored_author['receipt_hash'],'result':stored_author['result']}
snapshot=_snapshot_workspace(Q,Path('T:/'));assert len(snapshot)==6
assert read(R/RUN/'state.json')['nodes']['implement']['artifact_hash']==_artifact_hash(snapshot,stored_author['changed_files'])
report={'at':s.utc(),'reviewer':'/root','author':'/root/history_preservation','decision':'approved',
 'manifest':s.reference(Q/'TRANSFER-MANIFEST.json'),'scope':'Dormant exact F4 regression authorization/selection/completion engineering successor.',
 'independent_tests_passed':42,'independent_result':s.reference(D/'root42-r1/RESULT.json'),
 'reviewed_successor_scripts':scripts,'actual_full_Source2053_test_execution':False,
 'verified_findings':['Exact single original case is included only with a fresh bounded per-run operator authorization; partial2052 selection is explicitly unaccepted.',
   'Original runner is hash-bound and amended only at the named selection/output/original-case fences; original full2053 completion checks remain strict.',
   'Approval bytes are captured once under a retained share-read-only native file handle, with digest/nonce create-only consumption and current source/environment/tool checks.',
   'The exact observed native error is separately retained and checked; the preserved unanchored :2 legacy regex is not promoted to exact WinError2 evidence.',
   'Distinct actual successor/delivered reviews and an exact Root ordinary-library scope disposition remain prerequisites for completion.',
   'Current Source290, F4candidate336, E33601, all six candidate files,154 sealed author-evidence files and dirty Git state retain exact recorded values.'],
 'code_personally_inspected':['full_gate.py','run_authorized.py','complete_authorized.py','test_full_gate.py','derived/run_joined.py.diff','derived/complete_source.py.diff'],
 'limitations':ready['limitations'],'preserved_failures':qualification['preserved_failures'],
 'fixture_attribute_reproduction':s.reference(F/'.agents/runtime/fixture-attribute-probe-20261015/FRESH-DIRECTORY-OBSERVATIONS-R1.json'),
 'fixture_attribute_status':'Eight fresh owned directories/24 observations returned16; original109 current records conserved. Original cause/time and whole-fixture preservation remain unestablished; no metadata waiver or mutation.',
 'actual_human_authorization_created':False,'profile_or_CETA_effect_executed':False,
 'Source_publication':False,'CETA_product_LOC_integrated':0,'product_operational_completion':False}
s.write_new(D/'REPORT.json',report)
claim=read(R/RUN/'claims.json')['review'];assert claim['executor_id']=='/root'
assert _changed_files(claim['baseline_snapshot'],snapshot)==[]
receipt={'schema_version':1,'run_id':RUN,'node_id':'review','executor_id':'/root',
 'started_at':claim['claimed_at'],'finished_at':s.utc(),'input_hash':claim['input_hash'],'changed_files':[],
 'result':{'manifest_sha256':s.sha(Q/'TRANSFER-MANIFEST.json'),'report':s.reference(D/'REPORT.json'),
   'reviewed_successor_scripts':scripts,'independent_tests_passed':42,'full_Source_execution':False,'Source_publication':False},
 'commands':[{'command':str(s.PY)+' -B -X utf8 '+str(D/'prepare_review.py'),'exit_status':0},
             {'command':str(s.PY)+' -B -X utf8 '+str(D/'run_tests.py')+' root42-r1','exit_status':0}],
 'validations':[{'name':name,'passed':True} for name in ('42 exact distinct controlled cases pass with zero forbidden effects',
    'Original full2053 strict assertions and exact named case retained','Fresh per-run single-use exact subject and capture tested',
    'Current Source environment candidate and author-seal conservation','All unexecuted native and unresolved metadata boundaries remain explicit')],
 'exit_status':0,'decision':'approved'}
validate_receipt(receipt,run_id=RUN,node_id='review',executor_id='/root',input_hash=claim['input_hash'],
 claimed_at=claim['claimed_at'],node=read(R/RUN/'graph.json')['graph']['nodes']['review'])
s.write_new(D/'review.json',receipt)
s.invoke(['node','complete',RUN,'review',str(D/'review.json')],'review-complete')
stored=read(R/RUN/'receipts/review.json');state=read(R/RUN/'state.json');claims=read(R/RUN/'claims.json')
assert len(receipt)==13 and len(stored)==16 and norm(receipt)==norm({k:stored[k] for k in receipt})
assert stored['receipt_hash']==sha256_json({k:v for k,v in stored.items() if k!='receipt_hash'})
assert state['sequence']==9 and state['nodes']['review']['state']=='SUCCEEDED' and claims=={}
assert read(R/RUN/'results/review.json')=={'node_id':'review','receipt_hash':stored['receipt_hash'],'result':stored['result']}
assert state['nodes']['review']['artifact_hash']==sha256_json({'input_hash':stored['input_hash'],'result':stored['result']})
s.write_new(D/'ACTUAL-READBACK.json',{'at':s.utc(),'local':s.reference(D/'review.json'),
 'persisted':s.reference(R/RUN/'receipts/review.json'),'strict_local13_persisted16_typed_equality':True,
 'official_fingerprint_result_envelope_artifact_verified':True,'sequence':9,'state':'SUCCEEDED','claims':{},'Source_publication':False})
members={p.relative_to(D).as_posix():s.ordinary(p) for p in D.rglob('*') if p.is_file()}
s.write_new(D/'REVIEW-SEAL.json',{'at':s.utc(),'reviewer':'/root','decision':'approved','members':members,
 'manifest':s.reference(Q/'TRANSFER-MANIFEST.json'),'actual_claim_released':True,'Source_publication':False})
print(json.dumps({'review':s.reference(D/'review.json'),'report':s.reference(D/'REPORT.json'),
 'readback':s.reference(D/'ACTUAL-READBACK.json'),'seal':s.reference(D/'REVIEW-SEAL.json'),'tests':42,'sequence':9,'claims':{}}))
