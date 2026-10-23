from pathlib import Path
from datetime import datetime,timezone
import json,os,sys,subprocess
F=Path('T:/00-Active/Project-AI-CETA');B=F/'.agents/runtime/oq23/br3';D=B/'delivery';C=B/'control';RUN='ceta-br23-r3'
os.environ.update(GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false',PYTHONDONTWRITEBYTECODE='1');sys.path[:0]=[str(B/'work'),'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce']
import run_broader as b
failure=json.loads((C/'ROOT-CLOSE-PROCESS.json').read_bytes());assert failure['actual_process_exit_status']==1 and b.sha(C/'ROOT-CLOSE.py')=='9c2145d7e23cbcd5b2b5410e8c60375e1c7459a6f1e9ad7874805226f8f4716e'
assert 'TypeError: dict() got multiple values for keyword argument' in (C/'ROOT-CLOSE.stderr').read_text()
assert {x.name for x in D.iterdir()}=={'START.json','RESULT.json','REPORT-SEAL.json','events.jsonl','TESTS.log'},'partial completion effects already present; no replay'
assert not (C/'ROOT-EXECUTION-COMPLETION.json').exists()
assert len(sys.argv)==2;pin=sys.argv[1];packet,binding=b.load_prepared(pin);claims=b.require_live(binding)
p=json.loads((C/'EXECUTION-PROCESS.json').read_bytes());start=json.loads((D/'START.json').read_bytes());result=json.loads((D/'RESULT.json').read_bytes());seal=json.loads((D/'REPORT-SEAL.json').read_bytes());post=json.loads((C/'INDEPENDENT-POSTRUN-CHECK.json').read_bytes())
assert p['exit_status']==0 and b.execution_complete(D,0)
assert post['reviewer']=='/root/independent_broader_review' and post['decision']=='PASS_LIMITED_CANONICAL_COHORT' and post['process_sha256']==b.sha(C/'EXECUTION-PROCESS.json') and post['result_sha256']==b.sha(D/'RESULT.json') and post['seal_sha256']==b.sha(D/'REPORT-SEAL.json')
for name,key in [('RESULT.json','result_sha256'),('START.json','start_sha256'),('events.jsonl','events_sha256'),('TESTS.log','log_sha256')]:assert b.sha(D/name)==seal[key]
assert not (D/'REPORT-ERROR.json').exists() and result['test_cohort_passed'] and result['tests_run']==510
ids=json.loads((B/'work/COLLECTION.json').read_bytes())['test_ids'];oldids=json.loads((F/'.agents/runtime/oq23/br/work/COLLECTION.json').read_bytes())['test_ids'];assert ids==oldids==result['selected_test_ids']==result['started_test_ids']==result['stopped_test_ids'] and len(ids)==len(set(ids))==510
for name in ('failures','errors','skips','expected_failures','unexpected_successes','test_error_details'):assert not result[name]
assert result['primary'] is None and result['cleanup']==[] and result['early_stop'] is False
assert claims==start['claims'] and b.source_observation(binding)==start['source_before']==result['source_after']
for name,path in packet['fixture_workspaces'].items():
 now=b.o.snapshot(Path(path));assert now==result['fixtures_after'][name];b.o.preservation(start['fixtures_before'][name],now)
assert b.sha(F/'.agents/runtime/oq23/br/control/ROOT-FAILED-EXECUTION-COMPLETION.json')=='59abce80bd41b9c1570abee6fafeb9b4316e2e0f020d495803e1a2847e621304' and not (F/'.agents/runtime/oq23/br/delivery/REPORT-SEAL.json').exists()
assert b.sha(F/'.agents/runtime/oq23/br2/control-r2/ROOT-REJECTED-PREPARATION-COMPLETION.json')=='3422752d9491ba972a564157fefa8e0ae568fdcac1491b45776b088b544e2b6c' and not (F/'.agents/runtime/oq23/br2/control-r2/EXECUTION-INTENT.json').exists()
b.r.save(D/'INDEPENDENT-POSTRUN-ASSESSMENT.json',dict(post,recorded_by='/root',recorded_at=datetime.now(timezone.utc).isoformat(),basis='Root transcription of actual independent read-only postrun verification; exact external check pinned',check_path=str(C/'INDEPENDENT-POSTRUN-CHECK.json'),check_sha256=b.sha(C/'INDEPENDENT-POSTRUN-CHECK.json')))
b.r.save(D/'COMPLETION.json',dict(recorded_at=datetime.now(timezone.utc).isoformat(),scope='EXACT_28_SELECTORS_26_CANONICAL_MODULES_510_CONTROLLED_CONTRACT_TESTS',prepared_manifest_sha256=pin,tests=510,failures=0,errors=0,skips=0,elapsed_ns=result['elapsed_ns'],elapsed_scope='WHOLE_COHORT_NOT_ADMISSION_GUARD_BENCHMARK',actual_child_exit_status=0,independent_postrun='PASS_LIMITED_CANONICAL_COHORT',canonical_source560_plus2_status_Git_index_native_unchanged=True,all_preexisting_fixture_entries_and_failed_BR1_JS9_preserved=True,failed_predecessor_remains_failed=True,single_sequential_driver=True,bounded_disposable_Python_custody_helpers=True,native_worker_or_live_profile_qualification=False,installed_qualification=False,full_product_acceptance=False,completion_percentage=None,remaining=['Reliable admission timing within unchanged50ms contract; preserve historical elapsed/deadline NOT_CAPTURED','Genuine attributable authorization-to-native-effect path and restricted-worker qualification','All remaining full r6 application/model/installed/offline/migration/endurance/human/hardware acceptance']))
b.r.save(D/'EVIDENCE-FREEZE.json',dict(files={path.relative_to(D).as_posix():b.sha(path) for path in sorted(D.rglob('*')) if path.is_file()},self_excluded=True,full_product_acceptance=False))
runtime=b.BoundRuntime(binding)
for node in (*packet['fixture_workspaces'],'integrate'):
 claim=json.loads((C/RUN/'claims.json').read_bytes())[node];assert claim['executor_id']=='/root'
 changed=runtime.changed_files(RUN,node)
 receipt=dict(schema_version=1,run_id=RUN,node_id=node,executor_id='/root',started_at=claim['claimed_at'],finished_at=datetime.now(timezone.utc).isoformat(),input_hash=claim['input_hash'],changed_files=changed,result=dict(manifest_sha256=pin,shared_actual_canonical_execution=str(C/'EXECUTION-PROCESS.json'),actual_child_exit_status=0,tests_in_one_shared_cohort=510,all_selected_started_stopped_exact=True,source_and_preexisting_fixtures_preserved=True,failed_predecessor_preserved=True,full_product_acceptance=False),commands=[dict(command=subprocess.list2cmdline(p['argv']),exit_status=0)] if node=='integrate' else [],validations=[dict(name='actual510 canonical cohort complete current fixture and source preservation',passed=True)],exit_status=0)
 path=C/(node+'-receipt.json');b.r.save(path,receipt);response=runtime.complete(RUN,node,path);assert response['allowed'];b.r.save(C/('ROOT-'+node+'-complete-api.json'),dict(api='BoundRuntime.complete; all installed stock transitions with exact reviewed observation dispatch',response=response))
v=runtime.verify(RUN);assert v['receipts_valid'] and v['terminal_success'] and all(x=='SUCCEEDED' for x in v['states'].values());b.r.save(C/'verify-final-api.json',dict(api='BoundRuntime.verify; installed stock receipt/event/artifact checks',response=v))
b.r.save(C/'ROOT-EXECUTION-COMPLETION.json',dict(actual_run=RUN,all_actual_nodes_succeeded=True,terminal_success=True,prepared_manifest_sha256=pin,process_receipt_sha256=b.sha(C/'EXECUTION-PROCESS.json'),result_sha256=b.sha(D/'RESULT.json'),seal_sha256=b.sha(D/'REPORT-SEAL.json'),delivery_freeze_sha256=b.sha(D/'EVIDENCE-FREEZE.json'),verification_sha256=b.sha(C/'verify-final-api.json'),tests=510,failed_predecessor_remains_failed=True,full_product_acceptance=False))
print(json.dumps(dict(terminal_success=v['terminal_success'],states=v['states'],closure_sha256=b.sha(C/'ROOT-EXECUTION-COMPLETION.json'),verification_sha256=b.sha(C/'verify-final-api.json'))))
