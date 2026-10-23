"""Pin closed actual preceding attempts as data; execute no predecessor runner."""
from pathlib import Path
import json
import run_broader as b

W=b.W;J=b.J2;T=b.F/'.agents/runtime/oq23/tm2';old=b.F/'.agents/runtime/oq23/tm'
external={}
def pin(path,expected=None):
    actual=b.o.stable(path)['sha256']
    if expected is not None:assert actual==expected,('preceding evidence drift',str(path))
    external[str(path)]=actual;return actual
def read(path,expected=None):pin(path,expected);return json.loads(path.read_bytes())

previous_broad=Path(b.packet()['failed_broader_predecessor']['root'])
auth=read(previous_broad/'control/AUTHORIZED-TIMING-SUCCESSOR-INPUT.json',b.TIMING_INPUT_SHA)
assert auth['prior_canonical_case_executions']==0 and auth['failed_predecessor_remains_failed'] is True
assert auth['successor_run']=='ceta-tm23-r2' and auth['successor_root']==str(T)
pin(T/'packet/INPUTS.json',auth['successor_INPUTS_sha256']);pin(T/'packet/PLAN.md',auth['successor_PLAN_sha256'])
old_review=read(old/'review/REVIEW.json');assert old_review['decision']=='rejected' and old_review['canonical_test_bodies_executed'] is False
pin(old/'work/MANIFEST.json',auth['prior_manifest_sha256'])
pin(old/'review/MANIFEST.json','437b40cf73ddeda825a8d805b2c286e57bc7a5a4d5556e15be81719a0eced31a')
old_state=read(old/'control/ceta-tm23-r1/state.json')
assert old_state['nodes']['review']['state']=='FAILED' and old_state['nodes']['validate']['state']=='BLOCKED'

def closed(root,run,count,closure_pin,process_pin,result_pin,seal_pin,verify_pin):
    closure=read(root/'control/ROOT-EXECUTION-COMPLETION.json',closure_pin)
    assert closure['actual_run']==run and closure['tests']==count and closure['all_actual_nodes_succeeded'] is True
    process=read(root/'control/EXECUTION-PROCESS.json',process_pin)
    assert type(process['exit_status']) is int and process['exit_status']==0
    pin(root/'work/MANIFEST.json',closure['prepared_manifest_sha256'])
    review=read(root/'review/REVIEW.json');assert review['decision']=='approved' and review['manifest_sha256']==closure['prepared_manifest_sha256']
    pin(root/'review/MANIFEST.json')
    result=read(root/'delivery/RESULT.json',result_pin);seal=read(root/'delivery/REPORT-SEAL.json',seal_pin)
    start=read(root/'delivery/START.json')
    ids=result['selected_test_ids']
    assert len(ids)==len(set(ids))==count and result['started_test_ids']==result['stopped_test_ids']==ids
    assert result['tests_run']==count and result['failures']==result['errors']==0 and result['test_cohort_passed'] is True
    if root==J:assert result['skips']==[]
    else:assert type(result['skips']) is int and result['skips']==0
    assert result['early_stop'] is False and result['primary'] is None
    for field,name in [('result_sha256','RESULT.json'),('start_sha256','START.json'),('events_sha256','events.jsonl'),('log_sha256','TESTS.log')]:pin(root/'delivery'/name,seal[field])
    assert not (root/'delivery/REPORT-ERROR.json').exists()
    pin(root/'control/EXECUTION.stdout',process['stdout_sha256']);pin(root/'control/EXECUTION.stderr',process['stderr_sha256'])
    pin(root/'delivery/EVIDENCE-FREEZE.json',closure['delivery_freeze_sha256'])
    verification=read(root/'control/verify-final-api.json',verify_pin)['response']
    assert verification['allowed'] and verification['receipts_valid'] and verification['terminal_success']
    assert verification['run_id']==run and all(v=='SUCCEEDED' for v in verification['states'].values())
    state=read(root/'control'/run/'state.json')
    assert all(v['state']=='SUCCEEDED' and v['claim'] is None for v in state['nodes'].values())
    for node,v in state['nodes'].items():pin(root/'control'/run/v['receipt_ref'])
    pin(root/'control'/run/'events.jsonl')
    return closure,process,result,ids

jc,jp,jr,ji=closed(J,'ceta-jr23-r2',33,
    '9a9456d443f6d9883186ee2ecaddf8609d570aaf01d0a36b545e4005cc80fc76',
    '5e5173eacd1abc2f0366b3d15e662cb62dcf4090366bae4d07575bbe011ae5a7',
    '9030fef9127ed3531f0687194e2a73f2be4ceab85c2fa8762f6b31e14a8d0d11',
    '364a3cbdf2e73bed025326aaef4eeda1ae27bea7b716427bbb35dd7c8700c61a',
    '792959145941101373ac104c4df61dcabcfe29844bd80dacf7944cf69dbf4139')
tc,tp,tr,ti=closed(T,'ceta-tm23-r2',1,
    '222077a15a86be95dc1aaef6e81f3f6434168d34fc52a5e6f9b43d3a4d99992e',
    '4cf1e7993bc530478a5f4d05d216aa07f95683b756c1aed4758075a0d012fa14',
    '82b070c5e6f87a732e2357966e5e1e4149793e74139efca1067b227313536899',
    '176439698fe6c49fe3a5b09ff58376ea22eb59de671dd1835ff84b223a9b82ba',
    '0f7afc74a1f01f41054cc425cfb955f084d76936c8893ac6a0837ba3c2b91f8c')
assert ti==['test_cpu_execution_admission.CpuExecutionAdmissionTests.test_stop_in_final_elapsed_callback_wins_after_all_owner_callbacks']
assert tr['one_attempt'] is True and tr['observation']['reproduction']=='NOT_REPRODUCED'
assert tr['successful_guard_timings']==tr['provider_spans']=='NOT_MEASURED'
diagnosis=read(T/'delivery/TIMING-DIAGNOSIS.json')
assert diagnosis['root_cause']==diagnosis['reliable_50ms_admission']==diagnosis['speedup']=='NOT_ESTABLISHED'
assert diagnosis['unchanged_bound_ns']==50000000 and diagnosis['historical_failure_remains_open'] is True
assessment=read(T/'delivery/INDEPENDENT-POSTRUN-ASSESSMENT.json')

failed_packet=b.packet()['failed_broader_predecessor']
fc=read(Path(failed_packet['closure']),failed_packet['closure_sha256'])
assert fc['run_id']=='ceta-br23-r1' and fc['actual_exit_status']==1
assert fc['execution_success'] is False and fc['terminal_success'] is False
assert fc['all_execution_claims_closed_as_FAILED'] is True and fc['success_receipts_not_fabricated'] is True
for field in ('prepared_manifest','review_manifest','actual_process','actual_result','assessment','failed_data_freeze','verification'):
    item=fc[field];pin(Path(item['path']),item['sha256'])
fa=read(Path(failed_packet['assessment']),failed_packet['assessment_sha256'])
fp=read(previous_broad/'control/EXECUTION-PROCESS.json',fc['actual_process']['sha256'])
fr=read(previous_broad/'delivery/RESULT.json',fc['actual_result']['sha256'])
assert fp['exit_status']==1 and fr['test_cohort_passed'] is False
fi=fr['selected_test_ids'];assert len(fi)==len(set(fi))==510 and fr['started_test_ids']==fr['stopped_test_ids']==fi
assert fr['tests_run']==510 and fr['failures']==fr['errors']==0 and not fr['skips'] and not fr['early_stop']
assert not (previous_broad/'delivery/REPORT-SEAL.json').exists()
assert fa['original_failed_file_path']=='UNKNOWN_NOT_RECORDED_BY_GENERIC_ASSERTION'
freeze=read(previous_broad/'delivery/FAILED-DATA-FREEZE.json',fc['failed_data_freeze']['sha256'])
assert freeze['kind']=='IMMUTABLE_FAILED_ATTEMPT_DATA_FREEZE_NOT_SUCCESS_SEAL' and freeze['execution_success'] is False
for name,record in freeze['files'].items():
    path=previous_broad/'delivery'/name;current=b.o.stable(path)
    assert all(current[k]==value for k,value in record.items()),('failed predecessor freeze drift',name)
    pin(path,record['sha256'])
pin(previous_broad/'control/EXECUTION.stdout',fp['stdout_sha256']);pin(previous_broad/'control/EXECUTION.stderr',fp['stderr_sha256'])
fv=read(Path(fc['verification']['path']),fc['verification']['sha256'])['response']
assert fv['allowed'] and fv['receipts_valid'] and fv['terminal_success'] is False
fs=read(previous_broad/'control/ceta-br23-r1/state.json')
execution_nodes={'integrate','fixture_0','fixture_1','fixture_2','fixture_3','fixture_4','fixture_5','js9'}
for name,entry in fs['nodes'].items():
    assert entry['claim'] is None
    assert entry['state']==('FAILED' if name in execution_nodes else 'SUCCEEDED')
    if entry['receipt_ref']:pin(previous_broad/'control/ceta-br23-r1'/entry['receipt_ref'])
pin(previous_broad/'control/ceta-br23-r1/events.jsonl')
failed=dict(run='ceta-br23-r1',actual_exit_status=1,selected_started_stopped=510,test_body_failures=0,test_body_errors=0,
    whole_validation_passed=False,success_seal_absent=True,mandatory_post_snapshot_failed=True,
    original_failed_file_path='UNKNOWN_NOT_RECORDED',assessment_original_failed_file_path=fa['original_failed_file_path'],closed_as_failed=True,closure=fc,
    failure_assessment_path=failed_packet['assessment'],failure_assessment_sha256=failed_packet['assessment_sha256'],
    old_main_replayed=False,failed_JS9_preserved_read_only=True)

rejected_packet=b.packet()['rejected_broader_preparation'];R2=Path(rejected_packet['root']);R2W=R2/'work';R2C=Path(rejected_packet['control'])
rejected_closure=read(Path(rejected_packet['closure']),rejected_packet['closure_sha256'])
assert rejected_closure['run_id']=='ceta-br23-r2' and rejected_closure['terminal_success'] is False
assert rejected_closure['canonical_test_bodies_executed']==0 and rejected_closure['execution_intent_present'] is False
assert rejected_closure['all_actual_claims_closed'] and rejected_closure['delivery_empty'] and rejected_closure['fresh_js9_absent']
for field in ('prepared_manifest','review','review_manifest','rejected_receipt','verification'):
    record=rejected_closure[field];pin(Path(record['path']),record['sha256'])
rejected_manifest=read(R2W/'MANIFEST.json',rejected_packet['work_manifest_sha256'])
rejected_review=read(R2/'review/REVIEW.json',rejected_packet['review_sha256'])
assert rejected_review['decision']=='rejected'
rejected_state=read(R2C/'ceta-br23-r2/state.json')
assert rejected_state['nodes']['review']['state']=='FAILED' and rejected_state['nodes']['validate']['state']=='BLOCKED'
assert all(node['claim'] is None for node in rejected_state['nodes'].values())
rejected_raw=b.o.snapshot(R2W)
assert set(rejected_raw)-set(rejected_manifest['post_freeze_outputs'])==set(rejected_manifest['work_observation'])
b.o.preservation(rejected_manifest['work_observation'],rejected_raw)
for name,record in rejected_raw.items():
    # Every nested entry remains in the complete native/byte observation below.
    # Only top-level immutable sources/data are executable runtime support pins.
    if record['kind']=='file' and '/' not in name:pin(R2W/name,record['sha256'])
for name in ('reproduce_primary_custody_r2.py','DIRECT-CUSTODY-REPRODUCTION-R2.json','DIRECT-CUSTODY-R2-PROCESS.json'):
    pin(R2/'review'/name)
direct=read(R2/'review/DIRECT-CUSTODY-REPRODUCTION-R2.json')
assert direct['candidate_primary_custody_requirement_passed'] is False
assert len(direct['results'])==3 and all(case['original_identity_retained'] is False for case in direct['results'])
assert direct['canonical_test_bodies_executed'] is False and direct['canonical_fixture_writes'] is False
contextlib_pin=b.packet()['explicit_context_custody_repair']['exact_runtime_contextlib_source']
pin(Path(contextlib_pin['path']),contextlib_pin['sha256'])
assert not (b.F/'.agents/fixtures/js9-b23-r2').exists()
assert not (R2/'delivery/START.json').exists() and not (R2C/'EXECUTION-INTENT.json').exists()
rejected=dict(run='ceta-br23-r2',classification='REJECTED_PREPARATION_BEFORE_CANONICAL_EXECUTION',
    closure=rejected_closure,review=rejected_review,work_manifest_sha256=rejected_packet['work_manifest_sha256'],
    work_observation=rejected_raw,direct_three_port_failure=direct,all_actual_claims_closed=True,
    whole_observation_rechecks_required_at_freeze_and_prepared_verification=True,
    nested_disposable_entries_are_data_not_runtime_support=True,
    canonical_test_bodies_executed=0,canonical_fixture_writes=False,terminal_success=False,old_executable_replayed=False,
    failure='BR2-CUSTODY-01: hostile traceback setter replaces original through contextlib generator exit')

b.r.save(W/'PRIOR-EVIDENCE.json',dict(journal=dict(run='ceta-jr23-r2',actual_exit_status=jp['exit_status'],tests=33,
    all_actual_nodes_succeeded=True,closure=jc,test_ids=ji),
    timing=dict(run='ceta-tm23-r2',actual_case_executions=1,actual_exit_status=tp['exit_status'],test_ids=ti,
        failed_predecessor_preserved=True,predecessor_canonical_executions=0,predecessor_review=old_review,
        closure=tc,observation=tr['observation'],successful_guard_timings='NOT_MEASURED',provider_spans='NOT_MEASURED',
        diagnosis=diagnosis,independent_postrun_assessment=assessment),
    failed_broader=failed,rejected_broader_preparation=rejected,timing_successor_authorization_sha256=b.TIMING_INPUT_SHA,external_pins=external,
    predecessor_executables_imported=False,canonical_bodies_executed_by_preparation=False,full_product_acceptance=False))
print(json.dumps(dict(journal_tests=33,timing_tests=1,timing_actual_exit_status=tp['exit_status'],timing_reproduction='NOT_REPRODUCED',support_pins=len(external)),indent=2))
