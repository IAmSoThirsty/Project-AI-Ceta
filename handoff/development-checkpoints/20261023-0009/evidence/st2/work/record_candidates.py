"""Create exact status candidates only after actual prerequisite attempts are closed."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,copy,hashlib,importlib.util,json,os,re,sys
import status_core as s
F=s.F;S=s.S;W=s.W;C=S/'control'
def load(path):return json.loads(path.read_bytes())
def ref(path):return dict(repository_relative_path=path.relative_to(F).as_posix(),sha256=s.sha(path))
def external(path,pins):pins[str(path)]=s.sha(path);return load(path)
def closed_cohort(name,closure_pin,pins):
 root=F/('.agents/runtime/oq23/'+name);control=root/'control';delivery=root/'delivery'
 assert s.sha(control/'ROOT-EXECUTION-COMPLETION.json')==closure_pin
 closure=external(control/'ROOT-EXECUTION-COMPLETION.json',pins)
 verification=external(control/'verify-final-api.json',pins)['response'];assert verification['receipts_valid'] is True
 assert closure['actual_run']==verification['run_id']=={'jr2':'ceta-jr23-r2','tm2':'ceta-tm23-r2','br3':'ceta-br23-r3'}[name], 'closed run identity mismatch'
 assert all(value in ('SUCCEEDED','FAILED','CANCELLED') for value in verification['states'].values()),'prerequisite claims/stages not closed'
 process=external(control/'EXECUTION-PROCESS.json',pins);result=external(delivery/'RESULT.json',pins);start=external(delivery/'START.json',pins);seal=external(delivery/'REPORT-SEAL.json',pins)
 for filename,key in [('START.json','start_sha256'),('RESULT.json','result_sha256'),('events.jsonl','events_sha256'),('TESTS.log','log_sha256')]:
  path=delivery/filename;assert s.sha(path)==seal[key];pins[str(path)]=s.sha(path)
 assert not (delivery/'REPORT-ERROR.json').exists()
 for filename,key in [('EXECUTION.stdout','stdout_sha256'),('EXECUTION.stderr','stderr_sha256')]:
  path=control/filename;assert s.sha(path)==process[key];pins[str(path)]=s.sha(path)
 ids=start['test_ids'];assert len(ids)==len(set(ids)) and ids==result['selected_test_ids']==result['started_test_ids']==result['stopped_test_ids'] and len(ids)==result['tests_run']
 assert result['source_after']==start['source_before']
 freeze=external(delivery/'EVIDENCE-FREEZE.json',pins);external(root/'work/MANIFEST.json',pins);external(root/'review/MANIFEST.json',pins)
 assert closure['prepared_manifest_sha256']==s.sha(root/'work/MANIFEST.json'),'closed preparation manifest identity mismatch'
 for key,path in [('process_receipt_sha256',control/'EXECUTION-PROCESS.json'),('result_sha256',delivery/'RESULT.json'),('seal_sha256',delivery/'REPORT-SEAL.json'),('delivery_freeze_sha256',delivery/'EVIDENCE-FREEZE.json'),('verification_sha256',control/'verify-final-api.json')]:assert closure[key]==s.sha(path),('closed execution reference mismatch',key)
 for rel,digest in freeze['files'].items():
  path=Path(rel);assert not path.is_absolute() and '..' not in path.parts
  assert s.stable(delivery/path)['sha256']==digest,('delivery freeze mismatch',rel)
  pins[str(delivery/path)]=digest
 expected_runner={'jr2':'run_canonical_journal.py','tm2':'run_challenge.py','br3':'run_broader.py'}[name];packet=external(root/'packet/INPUTS.json',pins)
 assert process['argv']==[packet['python'],'-B','-X','utf8',str(root/'work'/expected_runner),'--manifest-sha256',s.sha(root/'work/MANIFEST.json')]
 assert process['cwd']==str(F) and process['manifest_sha256']==s.sha(root/'work/MANIFEST.json')
 collection=external(root/'work/COLLECTION.json',pins);assert collection['test_ids']==ids

 return dict(run_id=verification['run_id'],graph_fingerprint=verification['graph_fingerprint'],verification=ref(control/'verify-final-api.json'),prepared_manifest=ref(root/'work/MANIFEST.json'),actual_process=ref(control/'EXECUTION-PROCESS.json'),result=ref(delivery/'RESULT.json'),seal=ref(delivery/'REPORT-SEAL.json'),log=ref(delivery/'TESTS.log'),closure=ref(control/'ROOT-EXECUTION-COMPLETION.json'),actual_exit_status=process['exit_status'],tests_run=result['tests_run'],failures=result['failures'],errors=result['errors'],skips=result['skips'],test_cohort_passed=result['test_cohort_passed'],full_product_acceptance=False),result

def exact_subset(original,current):
 if type(original) is not type(current):return False
 if type(original) is dict:return all(key in current and exact_subset(value,current[key]) for key,value in original.items())
 if type(original) is list:return len(original)==len(current) and all(exact_subset(a,b) for a,b in zip(original,current))
 return original==current

def failed_predecessor(pins):
 root=F/'.agents/runtime/oq23/br';control=root/'control';delivery=root/'delivery'
 closure_path=control/'ROOT-FAILED-EXECUTION-COMPLETION.json';assert s.sha(closure_path)=='59abce80bd41b9c1570abee6fafeb9b4316e2e0f020d495803e1a2847e621304'
 closure=external(closure_path,pins);verification=external(control/'ROOT-verify-failed-api.json',pins)['response']
 assert closure['run_id']==verification['run_id']=='ceta-br23-r1' and closure['execution_success'] is False and closure['terminal_success'] is False and verification['terminal_success'] is False and verification['receipts_valid'] is True
 assert all(verification['states'][name]=='FAILED' for name in ('integrate','fixture_0','fixture_1','fixture_2','fixture_3','fixture_4','fixture_5','js9'))
 assert all(state in ('SUCCEEDED','FAILED','CANCELLED') for state in verification['states'].values())
 process=external(control/'EXECUTION-PROCESS.json',pins);result=external(delivery/'RESULT.json',pins);start=external(delivery/'START.json',pins);assessment=external(delivery/'FAILED-EXECUTION-ASSESSMENT.json',pins);freeze=external(delivery/'FAILED-DATA-FREEZE.json',pins)
 for key,path in [('actual_process',control/'EXECUTION-PROCESS.json'),('actual_result',delivery/'RESULT.json'),('assessment',delivery/'FAILED-EXECUTION-ASSESSMENT.json'),('failed_data_freeze',delivery/'FAILED-DATA-FREEZE.json'),('verification',control/'ROOT-verify-failed-api.json')]:assert closure[key]['sha256']==s.sha(path)
 for rel,record in freeze['files'].items():
  path=Path(rel);assert not path.is_absolute() and '..' not in path.parts;assert s.sha(delivery/path)==record['sha256'];pins[str(delivery/path)]=record['sha256']
 assert freeze['kind']=='IMMUTABLE_FAILED_ATTEMPT_DATA_FREEZE_NOT_SUCCESS_SEAL' and freeze['execution_success'] is False
 assert not (delivery/'REPORT-SEAL.json').exists() and not (delivery/'REPORT-ERROR.json').exists()
 assert process['exit_status']==1 and result['test_cohort_passed'] is False
 assert result['tests_run']==510 and len(result['selected_test_ids'])==510 and result['selected_test_ids']==result['started_test_ids']==result['stopped_test_ids']==start['test_ids']
 for key in ('failures','errors','skips','expected_failures','unexpected_successes','test_error_details'):assert not result[key]
 assert result['early_stop'] is False and result['elapsed_ns']==214500000000
 assert set(result['fixtures_after'])=={'fixture_'+str(n) for n in range(6)}
 assert assessment['original_failed_file_path']=='UNKNOWN_NOT_RECORDED_BY_GENERIC_ASSERTION' and assessment['current_read_only_diagnosis']['original_failed_path_proven'] is False
 collection=external(root/'work/COLLECTION.json',pins);assert collection['test_ids']==result['selected_test_ids']
 for path in (root/'work/MANIFEST.json',root/'review/MANIFEST.json',control/'EXECUTION.stdout',control/'EXECUTION.stderr',delivery/'events.jsonl',delivery/'TESTS.log'):pins[str(path)]=s.sha(path)
 assert s.sha(control/'EXECUTION.stdout')==process['stdout_sha256'] and s.sha(control/'EXECUTION.stderr')==process['stderr_sha256']
 return dict(run_id='ceta-br23-r1',status='FAILED_REQUIRED_POST_EXECUTION_OBSERVATION',actual_process=ref(control/'EXECUTION-PROCESS.json'),result=ref(delivery/'RESULT.json'),closure=ref(closure_path),failed_data_freeze=ref(delivery/'FAILED-DATA-FREEZE.json'),diagnosis=ref(delivery/'FAILED-EXECUTION-ASSESSMENT.json'),actual_exit_status=1,test_cohort_passed=False,success_seal_present=False,tests_selected=510,tests_started=510,tests_stopped=510,test_body_failures=0,test_body_errors=0,test_body_skips=0,primary=result['primary'],cleanup=result['cleanup'],elapsed_ns=214500000000,elapsed_scope='WHOLE_BROADER_EXECUTION_NOT_ADMISSION_GUARD_BENCHMARK',fixture_after_observations=6,js9_after_observation_present=False,original_failed_file_path='UNKNOWN',current_reproduced_witness_is_original_path_proof=False,all_eight_execution_claims_closed_as_FAILED=True,full_product_acceptance=False),result

def rejected_preparation(pins):
 root=F/'.agents/runtime/oq23/br2';control=root/'control-r2';review_root=root/'review'
 closure_path=control/'ROOT-REJECTED-PREPARATION-COMPLETION.json';assert s.sha(closure_path)=='3422752d9491ba972a564157fefa8e0ae568fdcac1491b45776b088b544e2b6c'
 closure=external(closure_path,pins);verification_path=control/'ROOT-rejected-preparation-verify-api.json';verification=external(verification_path,pins)['response']
 assert closure['classification']=='REJECTED_PREPARATION_BEFORE_CANONICAL_EXECUTION' and closure['run_id']==verification['run_id']=='ceta-br23-r2'
 assert closure['canonical_test_bodies_executed']==0 and closure['execution_intent_present'] is False and closure['delivery_empty'] is True and closure['fresh_js9_absent'] is True and closure['all_actual_claims_closed'] is True
 assert closure['terminal_success'] is verification['terminal_success'] is False and verification['receipts_valid'] is True
 assert closure['states']==verification['states'] and verification['states']['review']=='FAILED' and verification['states']['validate']=='BLOCKED'
 assert not any(value=='RUNNING' for value in verification['states'].values()) and all(verification['states'][name]=='PENDING' for name in ('integrate','fixture_0','fixture_1','fixture_2','fixture_3','fixture_4','fixture_5','js9'))
 assert not (control/'EXECUTION-INTENT.json').exists() and not any((root/'delivery').iterdir()) and not (F/'.agents/fixtures/js9-b23-r2').exists()
 for key in ('prepared_manifest','review','review_manifest','rejected_receipt','verification'):
  item=closure[key];path=Path(item['path']);assert path.is_relative_to(root) and s.sha(path)==item['sha256'];pins[str(path)]=item['sha256']
 review=external(review_root/'REVIEW.json',pins);manifest=external(review_root/'MANIFEST-SUCCESSOR-R2.json',pins)
 assert review['decision']==manifest['decision']=='rejected' and review['canonical_execution_authorized'] is False and review['canonical_test_bodies_executed']==0 and review['canonical_fixture_writes'] is False
 assert manifest['candidate_manifest_sha256']==review['manifest_sha256']==s.sha(root/'work/MANIFEST.json') and manifest['review_sha256']==s.sha(review_root/'REVIEW.json')
 assert len(review['findings'])==1 and review['findings'][0]['id']=='BR2-CUSTODY-01'
 for rel,digest in manifest['files'].items():
  path=Path(rel);assert not path.is_absolute() and '..' not in path.parts;assert s.sha(review_root/path)==digest;pins[str(review_root/path)]=digest
 for path,digest in manifest['external_pins'].items():assert s.sha(Path(path))==digest;pins[path]=digest
 return dict(run_id='ceta-br23-r2',classification=closure['classification'],canonical_test_bodies_executed=0,execution_intent_present=False,delivery_empty=True,fresh_js9_absent=True,all_actual_claims_closed=True,review_decision='rejected',actual_review_state='FAILED',actual_validate_state='BLOCKED',unclaimed_execution_nodes_remain_PENDING=True,closure=ref(closure_path),verification=ref(verification_path),review=ref(review_root/'REVIEW.json'),review_manifest=ref(review_root/'MANIFEST-SUCCESSOR-R2.json'),finding=closure['finding'],failed_preparation_is_not_a_canonical_test_result=True,full_product_acceptance=False)

def broader_admission_history(pins):
 root=F/'.agents/runtime/oq23/br3';control=root/'control';diag=control/'independent-admission-diagnostic-r2-20261023T052412Z'
 original=external(control/'ROOT-RELEASE-PROCESS.json',pins);assert original['actual_process_exit_status']==1
 decision=external(control/'INDEPENDENT-ADMISSION-CONTINUATION.json',pins);assert decision['reviewer']=='/root/independent_broader_review' and decision['decision']=='APPROVED_ONE_MISSING_CLAIM_CONTINUATION' and decision['canonical_test_bodies_executed']==0 and decision['original_failure_scalars']=='NOT_CAPTURED' and decision['maximum_continuations']==1
 assert decision['failed_release_process_sha256']==s.sha(control/'ROOT-RELEASE-PROCESS.json') and decision['manifest_sha256']==s.sha(root/'work/MANIFEST.json')
 continuation=external(control/'ADMISSION-CONTINUATION-PROCESS.json',pins);assert continuation['actual_process_exit_status']==0
 intent=external(control/'ADMISSION-CONTINUATION-INTENT.json',pins);assert intent['maximum_continuations']==1 and intent['canonical_test_bodies_executed']==0 and intent['replay_gate_release_bootstrap_or_tests'] is False
 ready=external(control/'ROOT-RELEASE-READY.json',pins);assert ready['actual_logical_execution_leases']==8 and ready['canonical_test_bodies_executed']==0 and ready['independently_reviewed_single_missing_claim_continuation'] is True
 report=external(diag/'REPORT.json',pins);process=external(diag/'PROCESS.json',pins);lost=external(diag/'ATTEMPT-1-LOST-CAPTURE.json',pins)
 assert process['actual_process_exit_status']==0 and process['report_sha256']==s.sha(diag/'REPORT.json') and process['canonical_test_bodies_executed']==0 and process['claims_or_gate_or_release_or_bootstrap_actions']==0 and lost['actual_process_exit_status']==1 and lost['canonical_test_bodies_executed']==0
 assert report['stage']=='PASS' and report['all_six_exact'] and report['partial_claims_exact_current_and_unchanged'] and report['original_release_scalar_differences']=='NOT_CAPTURED'
 assert decision['diagnostic_report']['sha256']==s.sha(diag/'REPORT.json') and decision['diagnostic_process']['sha256']==s.sha(diag/'PROCESS.json')
 for name in ('ROOT-RELEASE.stdout','ROOT-RELEASE.stderr','ADMISSION-CONTINUATION.stdout','ADMISSION-CONTINUATION.stderr'):pins[str(control/name)]=s.sha(control/name)
 return dict(original_release=ref(control/'ROOT-RELEASE-PROCESS.json'),original_release_actual_exit_status=1,original_release_state='FAILED_BEFORE_CANONICAL_TESTS',original_failed_directory='.agents/fixtures/outer-process-custody-00',original_failure_scalars='NOT_CAPTURED',original_failure_cause='UNKNOWN; current stable conservation does not identify the original cause',lost_diagnostic=ref(diag/'ATTEMPT-1-LOST-CAPTURE.json'),independent_conservation=ref(diag/'REPORT.json'),independent_process=ref(diag/'PROCESS.json'),continuation_decision=ref(control/'INDEPENDENT-ADMISSION-CONTINUATION.json'),continuation_process=ref(control/'ADMISSION-CONTINUATION-PROCESS.json'),continuation_actual_exit_status=0,continuations=1,canonical_bodies_before_continuation=0,retained_claims=['integrate','fixture_0','fixture_1'],newly_claimed_nodes=['fixture_2','fixture_3','fixture_4','fixture_5','js9'],original_failures_not_relabelled=True,full_product_acceptance=False)

def main():
 p=argparse.ArgumentParser();p.add_argument('--br3-closure-sha256',required=True);args=p.parse_args();assert sys.flags.optimize==0
 packet=load(S/'packet/INPUTS.json');assert packet['project']==str(F) and packet['targets']==['build/progress.json','handoff/continuity.json','build/gates.json','src/ceta/contracts/construction.py']
 pins={str(C/name):s.sha(C/name) for name in ('execute_once.py','ROOT-SELF-REVIEW.py','ROOT-RELEASE.py','ROOT-CLOSE.py')};jr,jresult=closed_cohort('jr2','9a9456d443f6d9883186ee2ecaddf8609d570aaf01d0a36b545e4005cc80fc76',pins);tm,tresult=closed_cohort('tm2','222077a15a86be95dc1aaef6e81f3f6434168d34fc52a5e6f9b43d3a4d99992e',pins);br,bresult=closed_cohort('br3',args.br3_closure_sha256,pins);failed,fresult=failed_predecessor(pins);rejected=rejected_preparation(pins);admission_history=broader_admission_history(pins)
 assert jr['actual_exit_status']==0 and jr['tests_run']==33 and jr['test_cohort_passed']
 assert tm['tests_run']==1 and br['tests_run']==510
 authority=external(C/'AUTHORIZED-BROADER-CUSTODY-SUCCESSOR-INPUT.json',pins);assert authority['current_successor']['run_id']==br['run_id']=='ceta-br23-r3'
 assert authority['current_successor']['graph_fingerprint']==br['graph_fingerprint'],'authorized closed graph mismatch'
 assert Path(authority['current_successor']['root'])==F/'.agents/runtime/oq23/br3' and Path(authority['current_successor']['control'])==F/'.agents/runtime/oq23/br3/control','authorized closed scope mismatch'
 assert authority['original_packet_sha256']==s.sha(S/'packet/INPUTS.json') and authority['original_plan_sha256']==s.sha(S/'packet/PLAN.md')
 b2=F/'.agents/runtime/oq23/br3';assert s.sha(b2/'packet/INPUTS.json')==authority['current_successor']['packet_sha256'] and s.sha(b2/'packet/PLAN.md')==authority['current_successor']['plan_sha256']
 predecessor_collection=external(F/'.agents/runtime/oq23/br/work/COLLECTION.json',pins);assert bresult['selected_test_ids']==bresult['started_test_ids']==bresult['stopped_test_ids']==predecessor_collection['test_ids']==fresult['selected_test_ids']
 old_start=external(F/'.agents/runtime/oq23/br/delivery/START.json',pins);new_start=external(b2/'delivery/START.json',pins)
 assert set(old_start['source_before']['source_native'])==set(new_start['source_before']['source_native']) and len(new_start['source_before']['source_native'])==562
 assert exact_subset(old_start['source_before'],new_start['source_before']),'successor did not exercise the same source/native/Git bytes'
 assert authority['constraints']['source_manifest_sha256']==packet['source_manifest_sha256']
 timing=external(F/'.agents/runtime/oq23/tm2/delivery/TIMING-DIAGNOSIS.json',pins)
 assert timing['unchanged_bound_ns']==50000000 and timing['historical_failure_remains_open'] is True
 external(C/'CURRENT-FIELD-REFRESH-BASIS.json',pins)
 native=external(W/'NATIVE-PATH-ASSESSMENT.json',pins)
 for path,pin in native['source_pins'].items():assert s.sha(F/path)==pin;pins[str(F/path)]=pin
 accepted=F/'.agents/runtime/oq23/jr2/work/run_canonical_journal.py';assert s.sha(accepted)=='37ca7bbfa361475ea42398c5d3bda42f8c1f95a0f3329154176f286a262d17ed';pins[str(accepted)]=s.sha(accepted)
 spec=importlib.util.spec_from_file_location('_accepted_record_observer',accepted);q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
 tm_binding=external(F/'.agents/runtime/oq23/tm2/work/BINDING.json',pins);source_before=q.source_observation(tm_binding)
 for rel,pin in packet['target_before_sha256'].items():assert s.sha(F/rel)==pin
 prior=external(Path(packet['source_manifest']),pins);assert len(prior['payload_hashes'])==560
 application=F/'.agents/runtime/operational-resume-20261022/record-application-successor-r1/delivery/canonical-budget-application-r1/COMPLETION.json';external(application,pins)
 status='VALID_BROADER_SELECTED_COHORT_PASSED' if br['test_cohort_passed'] and br['actual_exit_status']==0 else 'VALID_BROADER_SELECTED_COHORT_HAS_RECORDED_FAILURES'
 now=datetime.now(timezone.utc).isoformat()
 common=dict(recorded_at=now,state='IN_PROGRESS_FULL_SCOPE',authoritative_repository=str(F),Git_HEAD=packet['Git']['head'],branch=packet['Git']['branch'],canonical_application=ref(application),validated_source_manifest=ref(Path(packet['source_manifest'])),canonical_payloads=560,journal_runtime=jr,CHALLENGE=tm,timing_diagnosis=ref(F/'.agents/runtime/oq23/tm2/delivery/TIMING-DIAGNOSIS.json'),timing_findings=timing,failed_broader_predecessor=failed,rejected_broader_preparation=rejected,broader_admission_history=admission_history,broader_regression=br,broader_successor_authority=ref(C/'AUTHORIZED-BROADER-CUSTODY-SUCCESSOR-INPUT.json'),broader_scope='EXACT_28_SELECTORS_26_MODULES_510_TESTS; CONTROLLED_CONTRACTS_ONLY',broader_state=status,fixture_and_coordinator_coverage='Reviewed BR3 complete exact-workspace adapter with explicit original-exception context custody with narrow directional Win32 synthesized execute-bit comparison; same-API drift checks, complete traversal and explicit stock policies retained; BR1 failed postcheck preserved separately',current_native_path_assessment=ref(W/'NATIVE-PATH-ASSESSMENT.json'),current_native_blockers=[row['finding'] for row in native['current_findings']],historical_halt_and_failed_receipts_preserved=True,completion_assessment='Concrete progress in canonical integration and evidence consistency; no defensible overall completion percentage. These results establish a stronger development baseline and do not establish a fully operational product.',completion_percentage=None,full_product_complete=False,full_product_acceptance=False,genuine_native_effect_qualification=False,installed_qualification='NOT_ESTABLISHED_BY_THIS_REFRESH',source_delta_this_refresh='Three requested registers plus only the strict construction _GATE_SHA literal; no runtime behavior/test change.',canonical_source_after_manifest='.agents/runtime/oq23/st2/work/SOURCE-MANIFEST.json',remaining_milestones=[dict(id=1,requirement='Fresh canonical journal validation',state='33_CANONICAL_TESTS_PASSED'),dict(id=2,requirement='CHALLENGE timing diagnosis',state='SINGLE_ATTEMPT_NOT_REPRODUCED; HISTORICAL_ELAPSED_AND_DEADLINE_NOT_CAPTURED; CAUSE_AND_RELIABLE_50MS_NOT_ESTABLISHED'),dict(id=3,requirement='Fixture traversal/snapshot coverage and broader regression',state=status),dict(id=4,requirement='Genuine authorization-to-native-effect and remaining full product obligations',state='MANDATORY_OPEN_FULL_R6_SCOPE')])
 common['controlled_execution_effects']=dict(single_sequential_test_driver=True,bounded_disposable_Python_custody_helpers=True,native_worker_or_live_profile_qualification=False)
 common['remaining_requirements']=['Establish reliable admission timing within the unchanged50ms contract and resolve the preserved historical failures.','Complete genuine child-owned native provisioning with a durable epoch, reviewed deployment/native facts, strict manual readiness, original-wire uncertainty custody and one nonrenewing joint timing budget; qualify the restricted worker through separately admitted diagnosis/execution.','Complete application/model/request compiler/UI/workflow requirements and installed, offline, migration, endurance, human/hardware acceptance for the full r6 inventory.']
 targets={};beforeimages={};history_key='historical_next_action_before_oq23_st2'
 for rel in packet['targets']:
  path=W/'before'/rel;path.parent.mkdir(parents=True,exist_ok=True);raw=(F/rel).read_bytes()
  with path.open('xb') as f:assert f.write(raw)==len(raw);f.flush();os.fsync(f.fileno())
  beforeimages[rel]=ref(path)
 for rel in packet['targets'][:3]:
  original=load(F/rel);candidate=copy.deepcopy(original);assert 'current_repository_execution_20261023' not in candidate;candidate['current_repository_execution_20261023']=common
  candidate['current_status_pointer']='current_repository_execution_20261023'
  changed=[]
  if rel=='handoff/continuity.json':
   assert history_key not in candidate;candidate[history_key]=original['next_action'];legacy=['current_deliverable','first_next_action','next_action'];candidate['historical_current_fields_before_oq23_st2']={key:copy.deepcopy(original[key]) for key in legacy};candidate['next_action']='Establish reproducible admission timing; controlled-test the existing owned-client transport with strict selected-manual readiness, original-wire uncertainty custody, genuine child provisioning and a nonrenewing joint timing budget, then complete genuine authorization-to-native-effect and all remaining full r6 application/model, installed/offline/migration/endurance/human/hardware obligations. Preserve historical failures and the consumed AC7 attempt.';candidate['first_next_action']=candidate['next_action'];candidate['current_deliverable']='Canonical560 source includes the applied reviewed journal read-budget and resource-diagnostics repairs. Fresh33 journal cases passed; the exact510-case broader outcome is '+status+'. CHALLENGE was not reproduced in its single case; cause and reliable admission timing remain open. This is a stronger development baseline, with no defensible completion percentage or fully operational product acceptance.';changed=legacy
   if not (br['test_cohort_passed'] and br['actual_exit_status']==0):candidate['next_action']='Diagnose and repair the exact failures in the preserved trustworthy broader regression, then rerun its accepted scope before continuing reliable admission timing and the genuine authorization-to-native-effect path; retain all full r6 obligations.';candidate['first_next_action']=candidate['next_action']
  if rel=='build/gates.json':
   assert len(candidate['gates'])==8 and all(row['state']=='NOT_EVALUATED' for row in candidate['gates'])
   candidate['current_gate_evidence_20261023']=[dict(gate_id=row['id'],qualification='NOT_ESTABLISHED',observation='Fresh journal and broader selected contract evidence supports its exact controlled scope; genuine native/installed/full-product gate acceptance remains open.',evidence_refs=[jr['result'],tm['result'],br['result']]) for row in candidate['gates']]
  if rel=='handoff/continuity.json':assert all(s.same_json(original[key],candidate['historical_current_fields_before_oq23_st2'][key]) for key in changed)
  s.preserve_json(original,candidate,changed);output=W/'candidate'/rel;output.parent.mkdir(parents=True,exist_ok=True);s.save(output,candidate);targets[rel]=dict(before_sha256=packet['target_before_sha256'][rel],candidate_sha256=s.sha(output),changed_old_fields=changed)
 rel=packet['targets'][3];raw=s.constructor_successor((F/rel).read_bytes(),packet['target_before_sha256']['build/gates.json'],targets['build/gates.json']['candidate_sha256']);output=W/'candidate'/rel;output.parent.mkdir(parents=True,exist_ok=True)
 with output.open('xb') as f:assert f.write(raw)==len(raw);f.flush();os.fsync(f.fileno())
 targets[rel]=dict(before_sha256=packet['target_before_sha256'][rel],candidate_sha256=s.sha(output),source_delta='STRICT_GATE_HASH_LITERAL_ONLY')
 successor=copy.deepcopy(prior)
 for rel in ('build/gates.json','src/ceta/contracts/construction.py'):successor['payload_hashes'][rel]=targets[rel]['candidate_sha256']
 successor['input_source_manifest_sha256']=s.sha(Path(packet['source_manifest']));successor['full_product_acceptance']=False;successor['canonical_source_engineering']='STATUS_METADATA_AND_STRICT_GATE_PIN_ONLY; APPLY_REQUIRES_ACTUAL_REVIEW_GATE_AND_ROOT_CLAIMS'
 assert set(successor['payload_hashes'])==set(prior['payload_hashes']) and len(successor['payload_hashes'])==560
 s.save(W/'SOURCE-MANIFEST.json',successor)
 sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce');import taar.orchestration_runtime as runtime
 from taar.orchestration_graph import compile_graph
 binding=dict(run_id=s.RUN,graph_fingerprint=compile_graph(F,C).fingerprint,runtime_sha256=s.sha(Path(runtime.__file__)),targets=targets,source_native=tm_binding['source_native'],Git=packet['Git'],source_before=source_before,external_pins=pins,input_sha256=s.sha(S/'packet/INPUTS.json'),plan_sha256=s.sha(S/'packet/PLAN.md'),new_source_manifest_sha256=s.sha(W/'SOURCE-MANIFEST.json'),new_status_sha256={rel:targets[rel]['candidate_sha256'] for rel in packet['targets'][:2]},scope='FOUR_EXACT_CANONICAL_TARGETS_PLUS_FOUR_TEMPORARY_PATHS',prerequisites=dict(journal=jr,timing=tm,failed_broader_predecessor=failed,rejected_broader_preparation=rejected,broader=br),broader_successor_input_sha256=s.sha(C/'AUTHORIZED-BROADER-CUSTODY-SUCCESSOR-INPUT.json'),full_product_acceptance=False)
 s.save(W/'BINDING.json',binding);s.save(W/'PREPARATION.json',dict(targets=targets,beforeimages=beforeimages,source_before=source_before,canonical_writes=False,test_bodies_executed=False,full_product_acceptance=False));print(json.dumps(dict(prepared=True,targets=targets,full_product_acceptance=False)))
if __name__=='__main__':main()
