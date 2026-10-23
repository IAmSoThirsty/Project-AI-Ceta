from pathlib import Path
from datetime import datetime,timezone
import os,sys,json
F=Path('T:/00-Active/Project-AI-CETA');B=F/'.agents/runtime/oq23/br3';C=B/'control'
os.environ.update(GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false',PYTHONDONTWRITEBYTECODE='1');sys.path.insert(0,str(B/'work'))
import run_broader as b
assert len(sys.argv)==2;pin=sys.argv[1];value,binding=b.load_prepared(pin);source=b.source_observation(binding)
assert b.sha(C/'execute_once.py')=='e9384efbf8bed7f8acdcec779de3f5a4361c542b951e3b82547907b27f0af85c'
collection=json.loads((B/'work/COLLECTION.json').read_bytes());prior=json.loads((F/'.agents/runtime/oq23/br/work/COLLECTION.json').read_bytes());assert collection['test_ids']==prior['test_ids'] and len(collection['test_ids'])==len(set(collection['test_ids']))==510
controls=json.loads((B/'work/CONTROLS-FINAL.json').read_bytes());assert controls['successful'] and controls['tests']>=44 and controls['process_exit_status']==0 and controls['selected']==controls['started']==controls['stopped']
old_controls=json.loads((F/'.agents/runtime/oq23/br2/work/CONTROLS-FINAL.json').read_bytes());assert set(old_controls['selected']).issubset(set(controls['selected']))
assert not any((B/'delivery').iterdir()) and not (C/'EXECUTION-INTENT.json').exists()
assert binding['control']==str(C) and binding['run_id']=='ceta-br23-r3' and binding['graph_fingerprint']=='38a70f9069edec1aeb7daff0dbd491a474891ac5997d9a69a7ceda296aa4740e'
b.r.save(C/'ROOT-SELF-REVIEW.json',dict(recorded_at=datetime.now(timezone.utc).isoformat(),reviewer='/root',independent_review=False,manifest_sha256=pin,launcher_sha256=b.sha(C/'execute_once.py'),frozen_work_and_external_pins_verified=True,source562_Git_index_native_and_failed_JS9_read_only_preserved=True,stock_transition_scopes_receipts_locks_input_hash_and_event_checks_retained=True,exact_execution_workspaces=8,sequential_suite_driver=True,bounded_disposable_Python_custody_helpers=True,helper_effect_scope='Existing selected launcher custody cases; exact outer-process-custody fixture; own holder retirement; no service construction or native worker/profile qualification',collected_tests=510,ordered_predecessor_ids_exact=True,disposable_controls_passed=controls['tests'],failed_predecessor_remains_failed=True,rejected_BR2_preparation_preserved=True,all_three_explicit_exception_custody_boundaries_required=True,canonical_test_bodies_executed=False,independent_exact_review_and_actual_gate_required=True,full_product_acceptance=False))
print(json.dumps(dict(self_review=True,tests_collected=510,canonical_tests_executed=0,manifest_sha256=pin)))
