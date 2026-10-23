"""Exact composition input and closed-qualification readback; no snapshot/application."""
from pathlib import Path
import hashlib,json,os,sys
from unittest.mock import patch
F=Path('T:/00-Active/Project-AI-CETA');S=F/'.agents/runtime/oq23/st2';C=S/'control';W=S/'work';Q=F/'.agents/runtime/oq23/ds2';R=C/'independent-handle-composition-r1';A=C/'HANDLE-QUALIFIED-EXECUTION-AMENDMENT.json';PREP='5729a01e71127efd8d9970e8b5d1405f9b297eb12e421e94946983f125c6ff32';APIN='3d2edaa37528d2d38d6cb7ecace953eebfbef6c8dde4f221c0c5c1866eda640f';GRAPH='997829e1616609bafc88eea12f601eba7d715ad0e03b27e55a3f1af59a0d51ed';QRUN='ceta-ds23-r2-gate-r2'
os.environ.update(PYTHONDONTWRITEBYTECODE='1',GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false');sys.path[:0]=[str(W),'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce',str(Q/'work')]
import status_core as s,conservation
from taar.orchestration_persistence import sha256_json
from taar.orchestration_runtime import OrchestrationRuntime
assert s.sha(A)==APIN;amend=json.loads(A.read_bytes());assert len(amend['support_pins'])==27
for path,pin in amend['support_pins'].items():assert s.sha(Path(path))==pin
assert s.sha(C/'run_handle_qualified.py')==amend['runner_sha256']=='0923c3b1ec7081489d8c9f4dcee17083b3df6d65801215d6c4b27a288640bbf8'
assert s.sha(C/'execute_handle_qualified_once.py')==amend['launcher_sha256']=='727a150fc63889a1a1cb9b158f90a99adbf76388edeef4c6b3224d232bfb498d'
assert amend['prepared_manifest_sha256']==s.sha(W/'MANIFEST.json')==PREP
sm=json.loads((W/'MANIFEST.json').read_bytes());sr=json.loads((S/'review/MANIFEST.json').read_bytes());qm=json.loads((Q/'work/MANIFEST.json').read_bytes());qr=json.loads((Q/'review-r2/MANIFEST.json').read_bytes())
assert s.sha(S/'review/MANIFEST.json')=='469df543417b7d35d7673c388eb898f5b87bd09ac63cb27de509f543591c839f'
assert s.sha(Q/'work/MANIFEST.json')==amend['qualification_manifest_sha256']=='736a2a3ef8639bf99acced85d0ce3950b74b01bf9f23d856148ca7a7061df2f6'
assert s.sha(Q/'review-r2/MANIFEST.json')==amend['qualification_review_manifest_sha256']=='faa4f16f6778962a7c4d1de8681a519395c0118d9d6783e0d5f1b236db215b57'
counts={};external={}
for label,base,members,native in [('Swork',W,sm['work_hashes'],sm['work_file_native']),('Sreview',S/'review',sr['files'],sr['file_native']),('Qwork',Q/'work',{name:item['sha256'] for name,item in qm['files'].items()},qm['files']),('Qreview',Q/'review-r2',qr['files'],qr['file_native'])]:
 for name,pin in members.items():
  value=s.stable(base/name);assert value['sha256']==pin and value==native[name],(label,name)
 counts[label]=len(members)
for manifest in (sm,sr,qm,qr):external.update(manifest['external_pins'])
for path,pin in external.items():assert s.sha(Path(path))==pin,('external drift',path)
def checked_receipt(base,run,node):
 state=json.loads((base/run/'state.json').read_bytes());item=state['nodes'][node];assert item['state']=='SUCCEEDED' and item['claim'] is None
 recpath=base/run/item['receipt_ref'];assert recpath.resolve().is_relative_to((base/run/'receipts').resolve())
 rec=json.loads(recpath.read_bytes());body=dict(rec);stored=body.pop('receipt_hash');assert sha256_json(body)==stored==item['receipt_hash']
 assert rec['run_id']==run and rec['node_id']==node and rec['executor_id']==item['executor_id'] and type(rec['exit_status']) is int and rec['exit_status']==0
 assert all(item['passed'] is True for item in rec['validations'])
 return state,item,rec,dict(path=str(recpath),raw_file_sha256=s.sha(recpath),normalized_receipt_hash=stored)
qc=json.loads(Path(amend['qualification_closure']).read_bytes());qv=json.loads(Path(amend['qualification_verification']).read_bytes())['response'];accepted_path=Q/'delivery/ACCEPTED-QUALIFICATION.json';accepted=json.loads(accepted_path.read_bytes());qreceipts={}
assert qc['run_id']==qv['run_id']==amend['qualification_run_id']==QRUN and qc['graph_fingerprint']==qv['graph_fingerprint']==amend['qualification_graph_fingerprint']==GRAPH
assert qc['terminal_success'] is True and qv['terminal_success'] is True and qv['receipts_valid'] is True and len(qv['states'])==6 and all(value=='SUCCEEDED' for value in qv['states'].values())
assert qc['verification_sha256']==s.sha(Path(amend['qualification_verification'])) and qc['accepted_qualification_sha256']==s.sha(accepted_path)
assert accepted['work_manifest_sha256']==qc['manifest_sha256']==amend['qualification_manifest_sha256'] and accepted['review_manifest_sha256']==qc['review_manifest_sha256']==amend['qualification_review_manifest_sha256']
assert accepted['review_sha256']==s.sha(Q/'review-r2/REVIEW.json') and accepted['root_candidate_closure_sha256']==qr['root_candidate_closure_sha256']==s.sha(Q/'control-r2/ROOT-CLOSE-QUALIFICATION-R2.py')
assert accepted['provider']['sha256']==s.sha(Path(amend['source_provider']))==qm['provider_sha256'] and Path(accepted['provider']['path'])==Path(amend['source_provider'])
for field,name in [('controls_sha256','CONTROLS-R2.json'),('full_F_qualification_sha256','FULL-F-QUALIFICATION.json'),('full_F_snapshot_sha256','FULL-F-SNAPSHOT.json'),('access_time_policy_sha256','ACCESS-TIME-OBSERVATION-POLICY.json')]:assert accepted[field]==s.sha(Q/'work'/name)==qm['files'][name]['sha256']
for node in qv['states']:
 state,item,rec,ref=checked_receipt(Q/'control-r2',QRUN,node);qreceipts[node]=ref
 if node=='review':assert rec['decision']=='approved' and rec['result']['manifest_sha256']==amend['qualification_manifest_sha256'] and rec['result']['root_candidate_closure_sha256']==accepted['root_candidate_closure_sha256']
 if node=='validate':assert item['validation_passed'] is True and rec['commands']==[dict(command=json.loads((Q/'packet-r2/INPUTS.json').read_bytes())['exact_gate_command'],exit_status=0)]
assert {name:item['state'] for name,item in state['nodes'].items()}==qv['states'] and not json.loads((Q/'control-r2'/QRUN/'claims.json').read_bytes())
assert json.loads((Q/'control/ceta-ds23-r2/state.json').read_bytes())['nodes']['review']['state']=='FAILED' and json.loads((Q/'review/REVIEW.json').read_bytes())['decision']=='rejected'
assert json.loads((F/'.agents/runtime/oq23/ds1/control/ceta-ds23-r1/state.json').read_bytes())['nodes']['review']['state']=='FAILED'
sreceipts={}
for node in ('review','validate'):
 state,item,rec,ref=checked_receipt(C,'ceta-st23-r2',node);sreceipts[node]=ref
 if node=='review':assert rec['decision']=='approved' and rec['result']['manifest_sha256']==PREP and rec['result']['execution_amendment_sha256']=='cc7de6e2547f9b566d4dc6c3880c6a0ce3b4cbf13f5a82ebee7f7d42921efbff' and rec['result']['closure_successor_sha256']=='9543dcaca98f74ec2836401cbbfc263a6521771f981b664b921caa4b261e2484'
 if node=='validate':assert item['validation_passed'] is True and rec['commands']==[dict(command=x,exit_status=0) for x in json.loads((C/'ceta-st23-r2/graph.json').read_bytes())['graph']['nodes']['validate']['commands']]
assert state['nodes']['integrate']['state']==state['nodes']['evidence']['state']=='READY' and not json.loads((C/'ceta-st23-r2/claims.json').read_bytes())
assert not any((S/'delivery').iterdir()) and not (C/'EXECUTION-INTENT.json').exists() and not (C/'INDEPENDENT-HANDLE-EXECUTION-APPROVAL.json').exists()
assert amend['scope']['canonical_targets']==json.loads((S/'packet/INPUTS.json').read_bytes())['targets'] and len(amend['scope']['canonical_targets'])==4
for name in ('ROOT-INTEGRATE-CLAIM-PROCESS.json','ROOT-INTEGRATE-CLAIM-R2-PROCESS.json'):assert json.loads((C/name).read_bytes())['actual_process_exit_status']==1
peer=C/'independent-amendment-generator-r2';pm=json.loads((peer/'MANIFEST.json').read_bytes());pr=json.loads((peer/'REVIEW.json').read_bytes());pc=json.loads((peer/'CONTROLS.json').read_bytes());witness=json.loads((peer/'PHYSICAL-READER-WITNESS.json').read_bytes())
for name,pin in pm['files'].items():assert s.sha(peer/name)==pin['sha256'] and s.physical(peer/name).stat().st_size==pin['bytes']
assert pr['decision']=='APPROVED_METADATA_GENERATOR_PREFLIGHT_ONLY' and pr['source_sha256']==pm['source_sha256']==s.sha(C/'BUILD-HANDLE-EXECUTION-AMENDMENT.py')=='12ecd4e5b56d0c10081bbdc23248922e26106ef72a04d1383cae1413bea280ff'
assert pc['controls']==pc['passed']==30 and not pc['failed'] and pr['physical_reader']['final_exact_reader_passes']==pr['physical_reader']['ordinary_path_failures']==7
creation=json.loads((C/'ROOT-BUILD-HANDLE-BINDING-PROCESS.json').read_bytes());close=json.loads((Q/'control-r2/ROOT-QUALIFICATION-CLOSE-PROCESS.json').read_bytes())
assert creation['actual_process_exit_status']==close['actual_process_exit_status']==0
assert json.loads((C/'ROOT-BUILD-HANDLE-BINDING.stdout').read_bytes())['amendment_sha256']==APIN
assert 'BUILD-HANDLE-EXECUTION-AMENDMENT.py' in str(creation['argv']) and 'ROOT-CLOSE-QUALIFICATION-R2.py' in str(close['argv'])
# Pure file verification of both event chains; no runtime API or lock acquisition.
ledger_refs={}
for label,base,run in [('qualification',Q/'control-r2',QRUN),('status',C,'ceta-st23-r2')]:
 current=json.loads((base/run/'state.json').read_bytes());previous=None;count=0
 for line in (base/run/'events.jsonl').read_text(encoding='utf8').splitlines():
  if not line.strip():continue
  event=json.loads(line);count+=1;assert event['sequence']==count and event['run_id']==run and event['previous_hash']==previous
  body=dict(event);claimed=body.pop('event_hash');assert sha256_json(body)==claimed;previous=claimed
 assert current['sequence']==count and current['ledger_head']==previous
 assert not (base/run/'.state.lock').exists() and not (base/run/'.transaction.json').exists()
 if label=='qualification':assert qv['event_count']==count and qv['ledger_head']==previous and count==13
 else:assert count==11 and current['nodes']['integrate']['state']==current['nodes']['evidence']['state']=='READY'
 ledger_refs[label]=dict(event_count=count,ledger_head=previous,state_sha256=s.sha(base/run/'state.json'),events_sha256=s.sha(base/run/'events.jsonl'),claims_sha256=s.sha(base/run/'claims.json'),transient_lock_present=False)
conservation.observe()
report=dict(classification='EXACT_REAL_COMPOSITION_BINDING_READBACK_NOT_EXECUTION',amendment_sha256=APIN,support_pins=27,member_counts=counts,unique_external_pins_reread=len(external),qualification_actual_closed=True,event_chain_readback=ledger_refs,qualification_receipts=qreceipts,original_status_receipts=sreceipts,generator_sha256=pr['source_sha256'],generator_actual_process_exit_status=0,peer_review_sha256=s.sha(peer/'REVIEW.json'),peer_manifest_sha256=s.sha(peer/'MANIFEST.json'),peer_synthetic_controls=30,peer_real_long_reader_witnesses=7,source562_Git_index_ST2_preapplication_preserved=True,old_failed_claims_DS1_and_old_DS2_gate_rejection_preserved=True,original_failure_causes='UNKNOWN; original path/scalars NOT_CAPTURED',no_snapshot_native_claim_or_canonical_execution=True,full_product_acceptance=False)
s.save(R/'ACTUAL-COMPOSITION-READBACK.json',report);print(json.dumps(report,indent=2))
