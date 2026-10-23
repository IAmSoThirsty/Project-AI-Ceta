"""Fresh independent application readback; no test, snapshot, claim or application replay."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,importlib.util,json,os,sys
F=Path('T:/00-Active/Project-AI-CETA');S=F/'.agents/runtime/oq23/st2';W=S/'work';C=S/'control';D=S/'delivery'
PREP='5729a01e71127efd8d9970e8b5d1405f9b297eb12e421e94946983f125c6ff32'
os.environ.update(PYTHONDONTWRITEBYTECODE='1',GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false');sys.path.insert(0,str(W))
import status_core as s
assert sys.flags.optimize==0 and s.sha(W/'status_core.py')=='19668309370195f7d6c765d0da708e9159844814c40cd6a56bd8f8f7dcd40691'
assert not (C/'INDEPENDENT-POSTRUN-CHECK.json').exists()
assert s.sha(W/'MANIFEST.json')==PREP
process_path=C/'EXECUTION-PROCESS.json';result_path=D/'RESULT.json';process=json.loads(process_path.read_bytes());result=json.loads(result_path.read_bytes())
assert s.sha(process_path)=='e5dac542b3fe60d46d79f54d6e9022723951d9b885b25b041414158b2c5e0dd5'
assert s.sha(result_path)=='3f0a62d57543f1eb8c31d5f4d374b65f22e8b6ab25dbf70b9ba301d72e3b0e51'
assert type(process['exit_status']) is int and process['exit_status']==0 and process['manifest_sha256']==PREP
assert process['observation_amendment_sha256']==s.sha(C/'HANDLE-QUALIFIED-EXECUTION-AMENDMENT.json')=='3d2edaa37528d2d38d6cb7ecace953eebfbef6c8dde4f221c0c5c1866eda640f'
for name,key in [('EXECUTION.stdout','stdout_sha256'),('EXECUTION.stderr','stderr_sha256')]:assert s.sha(C/name)==process[key]
assert s.sha(C/'run_handle_qualified.py')=='0923c3b1ec7081489d8c9f4dcee17083b3df6d65801215d6c4b27a288640bbf8' and s.sha(C/'execute_handle_qualified_once.py')=='727a150fc63889a1a1cb9b158f90a99adbf76388edeef4c6b3224d232bfb498d'
assert s.sha(C/'INDEPENDENT-HANDLE-EXECUTION-APPROVAL.json')=='590689f9e333e0989a46cb2684e914483a22a240ec6249c15e33aac778ee89b8'
assert Path(process['argv'][process['argv'].index('--action')+1])==Path('apply')
for stem in ('ROOT-HANDLE-INTEGRATE-CLAIM','ROOT-HANDLE-EVIDENCE-CLAIM','ROOT-HANDLE-APPLICATION'):
 p=json.loads((C/(stem+'-PROCESS.json')).read_bytes());assert type(p['actual_process_exit_status']) is int and p['actual_process_exit_status']==0
 for suffix,key in [('.stdout','stdout_sha256'),('.stderr','stderr_sha256')]:assert s.sha(C/(stem+suffix))==p[key]
assert s.sha(C/'capture_process_r2.py')=='68dec29c0c75a079d08df95b817eb7e11ce3bb83561d480b9713cf45500b5ed5'
# Read the already accepted file/Git observer; never invoke its execution or runtime entry points.
observer=F/'.agents/runtime/oq23/jr2/work/run_canonical_journal.py';assert s.sha(observer)=='37ca7bbfa361475ea42398c5d3bda42f8c1f95a0f3329154176f286a262d17ed'
spec=importlib.util.spec_from_file_location('_independent_postrun_readers',observer);q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
b=json.loads((W/'BINDING.json').read_bytes());packet=json.loads((S/'packet/INPUTS.json').read_bytes());tests=json.loads((D/'record-checks/RESULT.json').read_bytes());seal=json.loads((D/'record-checks/REPORT-SEAL.json').read_bytes())
assert s.sha(D/'record-checks/RESULT.json')=='6c962f0799734f7c150c75fee61f72d2b90f87116dfee54e211a22ea605b7df6'
assert result['test_cohort_passed'] and result['execution_complete'] and result['tests_run']==tests['tests_run']==29 and result['actual_test_return_code']==0
assert tests['selected_test_ids']==tests['started_test_ids']==tests['stopped_test_ids'] and len(set(tests['selected_test_ids']))==29
assert tests['failures']==tests['errors']==result['failures']==result['errors']==0
for key in ('skips','expected_failures','unexpected_successes','test_error_details'):assert tests[key]==[]
assert tests['primary'] is None and tests['cleanup']==[] and tests['early_stop'] is False and tests['full_product_acceptance'] is False
assert q.execution_complete(D/'record-checks',0)
for name,key in [('RESULT.json','result_sha256'),('START.json','start_sha256'),('events.jsonl','events_sha256'),('TESTS.log','log_sha256')]:assert s.sha(D/'record-checks'/name)==seal[key]
targets=packet['targets'];assert targets==result['applied_targets'] and len(targets)==4 and set(targets)==set(b['targets'])
after_native={};unchanged=0
for name,before in b['source_native'].items():
 path=Path(name);rel=path.relative_to(F).as_posix();q.ancestors(F,path.parent);native,raw=q.stable(path)
 if rel in b['targets']:assert native['sha256']==b['targets'][rel]['candidate_sha256']
 else:assert native==before,('untouched source changed',rel);unchanged+=1
 after_native[name]=native
assert len(after_native)==562 and unchanged==558
Git=q.git_observation(b['Git']);after=dict(source_native=after_native,Git=Git)
assert after==json.loads((D/'SOURCE-AFTER-BINDING.json').read_bytes())==tests['source_after']
source_manifest=json.loads((W/'SOURCE-MANIFEST.json').read_bytes());assert len(source_manifest['payload_hashes'])==560
for rel,pin in source_manifest['payload_hashes'].items():assert after_native[str(F/rel)]['sha256']==pin
fixtures=[rel for rel in source_manifest['payload_hashes'] if rel.startswith('.local-build-cache/restoration-proof/')];assert len(fixtures)==5
history=[]
for rel,item in b['targets'].items():
 assert s.sha(W/'before'/rel)==item['before_sha256'] and s.sha(W/'candidate'/rel)==item['candidate_sha256'] and s.sha(F/rel)==item['candidate_sha256']
 assert (F/rel).read_bytes()==(W/'candidate'/rel).read_bytes()
 if rel.endswith('.json'):
  old=json.loads((W/'before'/rel).read_bytes());current=json.loads((F/rel).read_bytes());s.preserve_json(old,current,item['changed_old_fields'])
  status=current['current_repository_execution_20261023'];assert status['completion_percentage'] is None and status['full_product_acceptance'] is False and status['full_product_complete'] is False
  failed=status['failed_broader_predecessor'];assert failed['actual_exit_status']==1 and failed['test_cohort_passed'] is False and failed['success_seal_present'] is False and failed['tests_selected']==failed['tests_started']==failed['tests_stopped']==510
  rejected=status['rejected_broader_preparation'];assert rejected['canonical_test_bodies_executed']==0 and rejected['execution_intent_present'] is False and rejected['review_decision']=='rejected' and rejected['actual_review_state']=='FAILED'
  if rel=='handoff/continuity.json':
   copied=current['historical_current_fields_before_oq23_st2'];assert set(copied)==set(item['changed_old_fields']) and all(s.same_json(old[key],copied[key]) for key in copied) and s.same_json(old['next_action'],current['historical_next_action_before_oq23_st2'])
  if rel=='build/gates.json':assert s.same_json(old['gates'],current['gates']) and len(current['gates'])==8 and all(row['state']=='NOT_EVALUATED' for row in current['gates'])
  history.append(rel)
 else:assert s.constructor_successor((W/'before'/rel).read_bytes(),packet['target_before_sha256']['build/gates.json'],b['targets']['build/gates.json']['candidate_sha256'])==(F/rel).read_bytes()
for rel in packet['temporary_paths']:assert not (F/rel).exists() and not (F/rel).is_symlink()
state=json.loads((C/'ceta-st23-r2/state.json').read_bytes());claims=json.loads((C/'ceta-st23-r2/claims.json').read_bytes());assert set(claims)=={'integrate','evidence'}
for node,workspace in [('integrate',F),('evidence',D)]:assert state['nodes'][node]['state']=='RUNNING' and claims[node]['executor_id']=='/root' and Path(claims[node]['workspace'])==workspace
for name in ('ROOT-INTEGRATE-CLAIM-PROCESS.json','ROOT-INTEGRATE-CLAIM-R2-PROCESS.json'):assert json.loads((C/name).read_bytes())['actual_process_exit_status']==1
interruption=C/'READ-ONLY-PRECHECK-INTERRUPTION-20261023T1714.json';assert interruption.is_file()
report=dict(recorded_at=datetime.now(timezone.utc).isoformat(),reviewer='/root/status_packet_review',decision='PASS_EXACT_RECORD_APPLICATION',process_sha256=s.sha(process_path),result_sha256=s.sha(result_path),test_result_sha256=s.sha(D/'record-checks/RESULT.json'),report_seal_sha256=s.sha(D/'record-checks/REPORT-SEAL.json'),prepared_manifest_sha256=PREP,source_after_binding_sha256=s.sha(D/'SOURCE-AFTER-BINDING.json'),source_manifest_sha256=s.sha(W/'SOURCE-MANIFEST.json'),actual_process_exit_status=0,canonical_consistency_tests=29,selected_started_stopped_exact=True,failures=0,errors=0,skips=0,primary=None,cleanup=[],exact_target_hashes={rel:s.sha(F/rel) for rel in targets},source_native_checked=562,untouched_source_native_preserved=558,Git=Git,all_original_values_preserved_or_exact_typed_history=True,continuity_three_original_current_fields_preserved=True,all_eight_gate_rows_unchanged_NOT_EVALUATED=True,strict_constructor_gate_hash_literal_only=True,exact_five_immutable_restoration_inputs_preserved=True,temporary_paths_absent=True,old_failed_claims_preserved=True,read_only_precheck_interruption_preserved=dict(path=str(interruption),sha256=s.sha(interruption),actual_exit_status='NOT_CAPTURED',cause='UNKNOWN'),outer_capture_review=dict(path=str(C/'capture_process_r2.py'),sha256=s.sha(C/'capture_process_r2.py'),assessment='Ordinary no-shell argv, create-only streams, actual child wait status and flushed/fsynced process receipt. Missing receipt after interruption is not completion proof.'),postcheck_tool_sha256=s.sha(Path(__file__)),test_or_application_replayed=False,stock_F_snapshot_or_runtime_API_called=False,canonical_mutation_by_reviewer=False,native_worker_or_AC7_activity=False,full_product_acceptance=False,completion_percentage=None)
s.save(C/'INDEPENDENT-POSTRUN-CHECK.json',report)
print(json.dumps(dict(decision=report['decision'],reviewer=report['reviewer'],postcheck_sha256=s.sha(C/'INDEPENDENT-POSTRUN-CHECK.json'),source_native_checked=562,untouched=558,canonical_consistency_tests=29,Git_index_preserved=True,process_sha256=report['process_sha256'],result_sha256=report['result_sha256'],full_product_acceptance=False)))
