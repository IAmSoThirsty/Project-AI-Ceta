"""Complete/release only this engineering candidate, preserving every prior attempt."""
from pathlib import Path
import json,os,stat,sys
F=Path('T:/00-Active/Project-AI-CETA');R=Path(__file__).resolve().parent;Q=R/'candidate'
sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
sys.path.insert(0,str(F/'.agents/runtime/ka1-20261014'));import ka1_support as s
s.Q=Q;s.R=R;s.RUN='f4-full-gate-successor-20261015';s.ACTOR='/root/history_preservation'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
norm=lambda value:json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
manifest_path=Q/'TRANSFER-MANIFEST.json';manifest=read(manifest_path)
assert s.sha(manifest_path)=='043a722debd79ae1abd7d95414873f8893a326409ad6b2337e866eeaa9f438fe'
proof=read(R/'QUALIFICATION.json');tests=read(R/'tests-r4/RESULT.json')
assert proof['exit_status']==tests['exit_status']==0 and tests['tests_run']==42
assert tests['expected_ids']==tests['executed_ids']==tests['stopped_ids']
assert not any(tests[key] for key in ('failures','errors','skips','forbidden_native_and_process_calls','remaining_threads'))
for name,row in manifest['payloads'].items():assert s.ordinary(Q/name)==row
self_review={'at':s.utc(),'author':s.ACTOR,'decision':'author_ready_for_distinct_Root_review',
 'manifest':s.reference(manifest_path),'qualified':s.reference(R/'QUALIFICATION.json'),
 'personally_inspected':['All new engineering source/tests and exact original F4 runner/completion/callers',
 'Original runner function ASTs retained except two declared instrumentation/entry fences; original test bodies unchanged',
 'All old completion assertions retained except exact self-script reference; actual new argv/output and extra independent gates',
 'Genuine operator trust boundary versus synthetic records; two durable create-only consumption identities; no refund/retry',
 'Conservative deadline, source/environment/nonce/currentness and exact original native denial observation',
 'No automatic metadata waiver/publication; Root engineering scope disposition separate from human-specific native authorization',
 'Final42 ID equality/no skips/no forbidden native/process effects, Source290/F4candidate336/5717 sealed review files/E33601 conservation'],
 'prior_failures':manifest['prior_failures'],'Root_scope_clarification':s.reference(R/'ROOT-SCOPE-CLARIFICATION.json'),
 'LOC':manifest['LOC'],'limitations':manifest['limitations'],'independent_review':False,'Source_published':False}
s.write_new(R/'SELF-REVIEW.json',self_review)
result={'manifest_sha256':s.sha(manifest_path),'manifest':s.reference(manifest_path),'successor_scripts':manifest['successor_scripts'],
 'qualification':s.reference(R/'QUALIFICATION.json'),'self_review':s.reference(R/'SELF-REVIEW.json'),
 'tests':s.reference(R/'tests-r4/RESULT.json'),'controlled_tests_run':42,'Source_tests_run':0,'Source_application_paths':[],
 'LOC':manifest['LOC'],'prior_failures':manifest['prior_failures'],'Root_scope_clarification':s.reference(R/'ROOT-SCOPE-CLARIFICATION.json'),
 'parent_manifest':manifest['parent_manifest'],'limitations':manifest['limitations'],'metadata109_waived':False,
 'actual_original_restricted_case_run':False,'Source_published':False}
commands=[{'command':str(s.PY)+' -B -X utf8 '+str(R/'run_tests.py')+' tests-r4','exit_status':0},
 {'command':str(s.PY)+' -B -X utf8 '+str(R/'qualify.py'),'exit_status':0}]
s.complete('implement',result,commands,[('final42_controlled_unique_tests_no_fail_error_skip',True),
 ('all2053_original_ID_selection_possible_only_with_exact_fresh_operator_record',True),
 ('partial2052_explicitly_NOT_ACCEPTED_and_complete_gate_stays_strict',True),
 ('replay_drift_expiry_double_use_and_wrong_native_denial_rejected',True),
 ('Source290_F4candidate336_old5717proofs_E33601_Git_conserved',True),
 ('no_original_restricted_case_profile_process_CETA_native_or_Source_execution',True),
 ('metadata109_preserved_unwaived_and_prior_nonzero_attempts_retained',True)])
status=s.invoke(['run','status',s.RUN],'author-final-status')
assert status['sequence']==7 and status['states']['implement']=='SUCCEEDED' and status['states']['review']=='READY'
claims=read(R/s.RUN/'claims.json');assert claims=={}
local=read(R/'implement.json');stored_path=R/s.RUN/'receipts/implement.json';stored=read(stored_path)
assert len(local)==12 and len(stored)==15 and norm(local)==norm({key:stored[key] for key in local})
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_persistence import sha256_json
from taar.orchestration_runtime import _snapshot_workspace,_artifact_hash
assert stored['receipt_hash']==sha256_json({key:value for key,value in stored.items() if key!='receipt_hash'})
node=status['nodes']['implement'];assert node['receipt_hash']==stored['receipt_hash']
envelope_path=R/s.RUN/'results/implement.json';envelope=read(envelope_path)
assert set(envelope)=={'node_id','receipt_hash','result'} and envelope['node_id']=='implement' and envelope['receipt_hash']==stored['receipt_hash'] and norm(envelope['result'])==norm(local['result'])
snapshot=_snapshot_workspace(Q,Path('T:/'));assert len(snapshot)==6
assert node['artifact_hash']==_artifact_hash(snapshot,stored['changed_files'])
prefix=Q.relative_to(Path('T:/')).as_posix()+'/'
assert set(stored['changed_files'])=={prefix+name for name in manifest['payloads']}|{prefix+'TRANSFER-MANIFEST.json'}
readback={'at':s.utc(),'run_id':s.RUN,'sequence':7,'states':status['states'],'claims':claims,
 'submitted':s.reference(R/'implement.json'),'persisted':s.reference(stored_path),'result_envelope':s.reference(envelope_path),
 'local12_persisted15_normalized_equality':True,'official_receipt_fingerprint_verified':True,
 'three_key_result_envelope_verified':True,'actual_snapshot_count':6,'actual_changed_files':len(stored['changed_files']),
 'actual_artifact_hash':node['artifact_hash'],'manifest':s.reference(manifest_path),'actual_status':s.reference(R/'author-final-status.json'),
 'author_released':True,'Source_published':False,'independent_review':False}
s.write_new(R/'AUTHOR-READBACK.json',readback)
ready={'at':s.utc(),'candidate':str(Q),'runtime':str(R),'manifest':s.reference(manifest_path),
 'implement':s.reference(R/'implement.json'),'readback':s.reference(R/'AUTHOR-READBACK.json'),
 'review_entrypoint':s.reference(R/'run_tests.py'),'final_tests':s.reference(R/'tests-r4/RESULT.json'),
 'qualification':s.reference(R/'QUALIFICATION.json'),'derived_diffs':manifest['derived'],
 'required_review_result_fields':{'manifest_sha256':s.sha(manifest_path),'reviewed_successor_scripts':manifest['successor_scripts']},
 'reviewer_scope':'Fresh independent-review outputs only; bind test module R constant to own runtime and keep runner R exact. Test functions use synthetic records, native effect/process APIs forbidden; no original restricted case/full CETA cohort.',
 'limitations':manifest['limitations'],'author_released':True,'Source_published':False}
s.write_new(R/'READY-FOR-REVIEW.json',ready)
def inventory(root):
 members={};links={};pending=[root]
 while pending:
  directory=pending.pop()
  with os.scandir(directory) as entries:
   for entry in entries:
    path=directory/entry.name;name=path.relative_to(root).as_posix();parts=Path(name).parts
    if root==R and (parts[0]==s.RUN or parts[0] in ('independent-review','independent-root-review','root-integration','runs','consumed-authorizations','consumed-nonces','attempt-failures') or name=='AUTHOR-SEAL.json'):continue
    info=s.fs.lstat(path)
    if s.fs.reparse(info):links[name]=s.fs.file_identity(info)
    elif stat.S_ISDIR(info.st_mode):pending.append(path)
    elif stat.S_ISREG(info.st_mode):members[name]=s.ordinary(path)
    else:raise AssertionError('Unknown engineering author output')
 return members,links
candidate,candidate_links=inventory(Q);evidence,evidence_links=inventory(R)
assert not candidate_links and not evidence_links and len(candidate)==6
seal={'at':s.utc(),'author':s.ACTOR,'manifest':s.reference(manifest_path),'readback':s.reference(R/'AUTHOR-READBACK.json'),
 'candidate_members':candidate,'author_evidence_members':evidence,
 'excluded':['Mutable actual installed lifecycle directory','Later distinct review/root integration scopes','Future authorized executions/consumption/failure outputs','Self-referential seal'],
 'author_released':True,'Source_published':False,'independent_review':False}
s.write_new(R/'AUTHOR-SEAL.json',seal)
print(json.dumps({'manifest':s.reference(manifest_path),'implement':s.reference(R/'implement.json'),'persisted':s.reference(stored_path),
 'readback':s.reference(R/'AUTHOR-READBACK.json'),'seal':s.reference(R/'AUTHOR-SEAL.json'),'ready':s.reference(R/'READY-FOR-REVIEW.json'),
 'sequence':7,'states':status['states'],'claims':claims,'candidate_members':len(candidate),'author_evidence_members':len(evidence),
 'successor_script_pins':manifest['successor_scripts']},indent=2))
