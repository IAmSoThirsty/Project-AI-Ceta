"""Integrity gate only; no canonical imports, tests, writes or native effects."""
from pathlib import Path
import importlib.util,json,sys
import status_core as s
W=s.W;F=s.F;S=s.S
m=json.loads((W/'MANIFEST.json').read_bytes());b=json.loads((W/'BINDING.json').read_bytes());p=json.loads((S/'packet/INPUTS.json').read_bytes())
for name,pin in m['work_hashes'].items():assert s.sha(W/name)==pin,('work drift',name)
observed=s.snapshot(W,F,ignored=frozenset());allowed={'MANIFEST.json','PREPARED.stdout','PREPARED.stderr','PREPARED.json'}
current={Path(name).relative_to(W.relative_to(F)).as_posix():item for name,item in observed['files'].items()}
assert set(current)-allowed==set(m['work_hashes']), 'work entry set changed'
for name,item in m['work_file_native'].items():assert current[name]==item,('work native identity changed',name)
for name,identity in m['work_directory_identity'].items():assert all(observed['directories'][name][k]==v for k,v in identity.items()),('work directory replaced',name)
for name,pin in m['external_pins'].items():assert s.sha(Path(name))==pin,('support drift',name)
assert s.sha(S/'packet/INPUTS.json')==b['input_sha256'] and s.sha(S/'packet/PLAN.md')==b['plan_sha256']
for rel,item in b['targets'].items():
 assert s.sha(F/rel)==item['before_sha256'] and s.sha(W/'before'/rel)==item['before_sha256'] and s.sha(W/'candidate'/rel)==item['candidate_sha256']
 if rel.endswith('.json'):
  original=json.loads((W/'before'/rel).read_bytes());current=json.loads((W/'candidate'/rel).read_bytes());s.preserve_json(original,current,item['changed_old_fields'])
  status=current['current_repository_execution_20261023'];assert status['completion_percentage'] is None and not status['full_product_acceptance'] and not status['full_product_complete']
  failed=status['failed_broader_predecessor'];broader=status['broader_regression']
  assert failed['run_id']=='ceta-br23-r1' and failed['actual_exit_status']==1 and failed['test_cohort_passed'] is False and failed['success_seal_present'] is False
  assert failed['tests_selected']==failed['tests_started']==failed['tests_stopped']==510 and failed['test_body_failures']==failed['test_body_errors']==failed['test_body_skips']==0
  assert failed['elapsed_ns']==214500000000 and failed['elapsed_scope']=='WHOLE_BROADER_EXECUTION_NOT_ADMISSION_GUARD_BENCHMARK' and failed['original_failed_file_path']=='UNKNOWN' and failed['current_reproduced_witness_is_original_path_proof'] is False and failed['js9_after_observation_present'] is False
  assert broader['run_id']=='ceta-br23-r3' and broader['tests_run']==510
  rejected=status['rejected_broader_preparation'];assert rejected['run_id']=='ceta-br23-r2' and rejected['canonical_test_bodies_executed']==0 and rejected['execution_intent_present'] is False and rejected['review_decision']=='rejected' and rejected['actual_review_state']=='FAILED' and rejected['unclaimed_execution_nodes_remain_PENDING'] is True
  history=status['broader_admission_history'];assert history['original_release_actual_exit_status']==1 and history['original_release_state']=='FAILED_BEFORE_CANONICAL_TESTS' and history['original_failure_scalars']=='NOT_CAPTURED' and history['continuation_actual_exit_status']==0 and history['continuations']==1 and history['canonical_bodies_before_continuation']==0 and history['original_failures_not_relabelled'] is True
  expected_state='VALID_BROADER_SELECTED_COHORT_PASSED' if broader['test_cohort_passed'] and broader['actual_exit_status']==0 else 'VALID_BROADER_SELECTED_COHORT_HAS_RECORDED_FAILURES'
  assert status['broader_state']==expected_state and status['controlled_execution_effects']['bounded_disposable_Python_custody_helpers'] is True and not status['controlled_execution_effects']['native_worker_or_live_profile_qualification']
  assert status['broader_successor_authority']['sha256']==b['broader_successor_input_sha256']==s.sha(S/'control/AUTHORIZED-BROADER-CUSTODY-SUCCESSOR-INPUT.json')
  authority=json.loads((S/'control/AUTHORIZED-BROADER-CUSTODY-SUCCESSOR-INPUT.json').read_bytes());assert broader['graph_fingerprint']==authority['current_successor']['graph_fingerprint']==b['prerequisites']['broader']['graph_fingerprint']
  closure=json.loads((F/'.agents/runtime/oq23/br3/control/ROOT-EXECUTION-COMPLETION.json').read_bytes());assert closure['prepared_manifest_sha256']==broader['prepared_manifest']['sha256']==s.sha(F/'.agents/runtime/oq23/br3/work/MANIFEST.json')
  if rel=='handoff/continuity.json':
   assert item['changed_old_fields']==['current_deliverable','first_next_action','next_action'];history=current['historical_current_fields_before_oq23_st2'];assert set(history)==set(item['changed_old_fields']) and all(s.same_json(original[key],history[key]) for key in history) and s.same_json(original['next_action'],current['historical_next_action_before_oq23_st2'])
  if rel=='build/gates.json':assert original['gates']==current['gates'] and len(current['gates'])==8
 else:assert s.constructor_successor((W/'before'/rel).read_bytes(),p['target_before_sha256']['build/gates.json'],b['targets']['build/gates.json']['candidate_sha256'])==(W/'candidate'/rel).read_bytes()
for rel in p['temporary_paths']:assert not (F/rel).exists() and not (F/rel).is_symlink()
import record_candidates as builder
old_start=json.loads((F/'.agents/runtime/oq23/br/delivery/START.json').read_bytes());new_start=json.loads((F/'.agents/runtime/oq23/br3/delivery/START.json').read_bytes());new_result=json.loads((F/'.agents/runtime/oq23/br3/delivery/RESULT.json').read_bytes());old_collection=json.loads((F/'.agents/runtime/oq23/br/work/COLLECTION.json').read_bytes())
assert new_start['test_ids']==new_result['selected_test_ids']==new_result['started_test_ids']==new_result['stopped_test_ids']==old_collection['test_ids']
assert len(new_start['source_before']['source_native'])==562 and set(old_start['source_before']['source_native'])==set(new_start['source_before']['source_native']) and builder.exact_subset(old_start['source_before'],new_start['source_before'])
assert not (F/'.agents/runtime/oq23/br/delivery/REPORT-SEAL.json').exists()
old=json.loads(Path(p['source_manifest']).read_bytes())['payload_hashes'];new=json.loads((W/'SOURCE-MANIFEST.json').read_bytes())['payload_hashes'];assert len(old)==len(new)==560 and set(old)==set(new)
assert {rel for rel in old if old[rel]!=new[rel]}=={'build/gates.json','src/ceta/contracts/construction.py'}
fixtures={rel for rel in new if rel.startswith('.local-build-cache/restoration-proof/')};assert len(fixtures)==5 and all(old[rel]==new[rel] for rel in fixtures)
controls=json.loads((W/'controls-r6/RESULT.json').read_bytes());assert controls['successful'] and controls['tests_run']==36 and controls['failures']==controls['errors']==controls['skips']==0
assert controls['tested_core_sha256']==s.sha(W/'status_core.py')
probe=json.loads((W/'source-snapshot-qualification-r2/RESULT.json').read_bytes());process=json.loads((W/'SOURCE-PROBE-PROCESS.json').read_bytes());assert process['result_sha256']==s.sha(W/'source-snapshot-qualification-r2/RESULT.json')
assert probe['successful'] and process['actual_process_exit_status']==0 and s.sha(W/'source-snapshot-qualification-r2/OBSERVATION.json')==probe['observation_sha256']
accepted=F/'.agents/runtime/oq23/jr2/work/run_canonical_journal.py';spec=importlib.util.spec_from_file_location('_accepted_status_observer',accepted);q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q);q.source_observation(b)
for rel in m['python_sources']:compile((W/rel).read_bytes(),str(W/rel),'exec')
assert sys.flags.optimize==0
print('PREPARED PASS:4 exact metadata/pin targets, all original values/history/gates preserved, closed actual outcomes pinned, source560+2/Git/index/native unchanged; no canonical writes/test bodies; full acceptance false')
