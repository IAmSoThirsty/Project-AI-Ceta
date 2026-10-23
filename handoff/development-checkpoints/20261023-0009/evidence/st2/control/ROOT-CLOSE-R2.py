"""Close only actual successful status application and its two admitted scopes."""
from pathlib import Path
from datetime import datetime,timezone
import json,os,sys,subprocess
F=Path('T:/00-Active/Project-AI-CETA');S=F/'.agents/runtime/oq23/st2';W=S/'work';C=S/'control';D=S/'delivery';RUN='ceta-st23-r2'
os.environ.update(GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false',PYTHONDONTWRITEBYTECODE='1');sys.path[:0]=[str(W),'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce']
import run_status as r
assert len(sys.argv)==2;pin=sys.argv[1];b,q=r.load_prepared(pin);amendment=json.loads((C/'EXECUTION-AMENDMENT.json').read_bytes());assert amendment['prepared_manifest_sha256']==pin and amendment['successor_closer_sha256']==r.s.sha(Path(__file__)) and amendment['superseded_closer_sha256']==r.s.sha(C/'ROOT-CLOSE.py') and amendment['old_closer_must_not_be_executed'] is True
state=json.loads((C/RUN/'state.json').read_bytes());review_node=state['nodes']['review'];assert review_node['state']=='SUCCEEDED' and review_node['decision']=='approved';review=json.loads((C/RUN/review_node['receipt_ref']).read_bytes())
assert review['result']['manifest_sha256']==pin and review['result']['execution_amendment_sha256']==r.s.sha(C/'EXECUTION-AMENDMENT.json') and review['result']['closure_successor_sha256']==r.s.sha(Path(__file__))
assert not (C/'ROOT-EXECUTION-COMPLETION.json').exists() and not (D/'COMPLETION.json').exists(),'no closure replay or partial-completion retry'
process=json.loads((C/'EXECUTION-PROCESS.json').read_bytes());result=json.loads((D/'RESULT.json').read_bytes());tests=json.loads((D/'record-checks/RESULT.json').read_bytes());seal=json.loads((D/'record-checks/REPORT-SEAL.json').read_bytes());post=json.loads((C/'INDEPENDENT-POSTRUN-CHECK.json').read_bytes())
assert process['exit_status']==0 and process['manifest_sha256']==pin and result['test_cohort_passed'] and result['execution_complete'] and result['tests_run']==29 and result['failures']==result['errors']==0
assert q.execution_complete(D/'record-checks',0) and tests['tests_run']==29 and tests['selected_test_ids']==tests['started_test_ids']==tests['stopped_test_ids'] and len(set(tests['selected_test_ids']))==29
for key in ('failures','errors','skips','expected_failures','unexpected_successes','test_error_details'):assert not tests[key]
assert tests['primary'] is None and tests['cleanup']==[] and tests['early_stop'] is False
for name,key in [('RESULT.json','result_sha256'),('START.json','start_sha256'),('events.jsonl','events_sha256'),('TESTS.log','log_sha256')]:assert r.s.sha(D/'record-checks'/name)==seal[key]
assert post['reviewer']=='/root/status_packet_review' and post['decision']=='PASS_EXACT_RECORD_APPLICATION' and post['process_sha256']==r.s.sha(C/'EXECUTION-PROCESS.json') and post['result_sha256']==r.s.sha(D/'RESULT.json')
after=r.expected_after(b,q);assert after==json.loads((D/'SOURCE-AFTER-BINDING.json').read_bytes())==tests['source_after']
p=json.loads((S/'packet/INPUTS.json').read_bytes())
for rel in p['targets']:
 assert r.s.sha(F/rel)==b['targets'][rel]['candidate_sha256']
 if rel.endswith('.json'):r.s.preserve_json(json.loads((W/'before'/rel).read_bytes()),json.loads((F/rel).read_bytes()),b['targets'][rel]['changed_old_fields'])
assert not any((F/rel).exists() for rel in p['temporary_paths'])
r.s.save(D/'INDEPENDENT-POSTRUN-ASSESSMENT.json',dict(post,recorded_at=datetime.now(timezone.utc).isoformat(),recorded_by='/root',check_path=str(C/'INDEPENDENT-POSTRUN-CHECK.json'),check_sha256=r.s.sha(C/'INDEPENDENT-POSTRUN-CHECK.json')))
r.s.save(D/'COMPLETION.json',dict(recorded_at=datetime.now(timezone.utc).isoformat(),run_id=RUN,prepared_manifest_sha256=pin,applied_targets=p['targets'],temporary_paths_absent=True,canonical_consistency_tests=29,actual_process_exit_status=0,source_manifest=r.ref(W/'SOURCE-MANIFEST.json'),all_original_halt_failure_and_gate_values_preserved=True,strict_gate_hash_literal_only=True,independent_postrun='PASS_EXACT_RECORD_APPLICATION',canonical_source_Git_index_native_preserved_outside_four_targets=True,native_runtime_qualification=False,full_product_acceptance=False,completion_percentage=None))
r.s.save(D/'EVIDENCE-FREEZE.json',dict(files={path.relative_to(D).as_posix():r.s.sha(path) for path in sorted(D.rglob('*')) if path.is_file()},self_excluded=True,full_product_acceptance=False))
with r.s.qualified_runtime() as runtime:
 rt=runtime.OrchestrationRuntime(C);claims=r.live(rt,b)
 for node in ('evidence','integrate'):
  claim=claims[node]
  # Receipt declares the already verified four intended writes; stock complete independently snapshots all F and refuses any difference.
  changed=sorted(p['targets']) if node=='integrate' else runtime._changed_files(claim['baseline_snapshot'],runtime._snapshot_workspace(Path(claim['workspace']),F))
  receipt=dict(schema_version=1,run_id=RUN,node_id=node,executor_id='/root',started_at=claim['claimed_at'],finished_at=datetime.now(timezone.utc).isoformat(),input_hash=claim['input_hash'],changed_files=changed,result=dict(manifest_sha256=pin,actual_process=str(C/'EXECUTION-PROCESS.json'),actual_process_exit_status=0,canonical_consistency_tests=29,source_manifest_sha256=b['new_source_manifest_sha256'],all_original_halt_failure_and_gate_values_preserved=True,strict_gate_hash_literal_only=True,full_product_acceptance=False),commands=[dict(command=subprocess.list2cmdline(process['argv']),exit_status=0)] if node=='integrate' else [],validations=[dict(name='Exact four targets, preserved original values, strict gate pin, actual canonical29 consistency cases',passed=True)],exit_status=0)
  path=C/(node+'-receipt.json');r.s.save(path,receipt);a=rt.complete(RUN,node,path);assert a['allowed'];r.s.save(C/('ROOT-'+node+'-complete-api.json'),dict(api='OrchestrationRuntime.complete with exact qualified source snapshot policy',response=a))
 v=rt.verify(RUN);assert v['receipts_valid'] and v['terminal_success'] and all(value=='SUCCEEDED' for value in v['states'].values());r.s.save(C/'verify-final-api.json',dict(api='OrchestrationRuntime.verify with exact qualified source snapshot policy',response=v))
r.s.save(C/'ROOT-EXECUTION-COMPLETION.json',dict(actual_run=RUN,terminal_success=True,all_actual_nodes_succeeded=True,prepared_manifest_sha256=pin,process_receipt_sha256=r.s.sha(C/'EXECUTION-PROCESS.json'),result_sha256=r.s.sha(D/'RESULT.json'),delivery_freeze_sha256=r.s.sha(D/'EVIDENCE-FREEZE.json'),verification_sha256=r.s.sha(C/'verify-final-api.json'),applied_targets=p['targets'],canonical_consistency_tests=29,full_product_acceptance=False,completion_percentage=None))
print(json.dumps(dict(terminal_success=v['terminal_success'],states=v['states'],closure_sha256=r.s.sha(C/'ROOT-EXECUTION-COMPLETION.json'),verification_sha256=r.s.sha(C/'verify-final-api.json'))))
