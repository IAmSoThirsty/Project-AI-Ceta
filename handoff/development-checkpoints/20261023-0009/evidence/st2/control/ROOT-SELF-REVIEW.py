"""Root assessment of exact prepared records; not independent acceptance."""
from pathlib import Path
from datetime import datetime,timezone
import os,sys,json
F=Path('T:/00-Active/Project-AI-CETA');S=F/'.agents/runtime/oq23/st2';C=S/'control';W=S/'work'
os.environ.update(GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false',PYTHONDONTWRITEBYTECODE='1');sys.path.insert(0,str(W))
import run_status as r
assert len(sys.argv)==2;pin=sys.argv[1];b,q=r.load_prepared(pin);assert q.source_observation(b)==b['source_before']
p=json.loads((S/'packet/INPUTS.json').read_bytes());controls=json.loads((W/'controls-r6/RESULT.json').read_bytes());process=json.loads((W/'CONTROLS-R6-PROCESS.json').read_bytes())
assert controls['successful'] and controls['tests_run']==36 and controls['failures']==controls['errors']==controls['skips']==0 and process['actual_process_exit_status']==0 and controls['tested_core_sha256']==r.s.sha(W/'status_core.py')
for rel in p['targets']:
 assert r.s.sha(F/rel)==b['targets'][rel]['before_sha256'] and r.s.sha(W/'candidate'/rel)==b['targets'][rel]['candidate_sha256']
 if rel.endswith('.json'):r.s.preserve_json(json.loads((F/rel).read_bytes()),json.loads((W/'candidate'/rel).read_bytes()),b['targets'][rel]['changed_old_fields'])
 if rel=='handoff/continuity.json':
  original=json.loads((F/rel).read_bytes());current=json.loads((W/'candidate'/rel).read_bytes());assert set(current['historical_current_fields_before_oq23_st2'])=={'current_deliverable','first_next_action','next_action'} and all(r.s.same_json(original[key],value) for key,value in current['historical_current_fields_before_oq23_st2'].items()) and r.s.same_json(original['next_action'],current['historical_next_action_before_oq23_st2'])
assert not any((S/'delivery').iterdir()) and not (C/'EXECUTION-INTENT.json').exists()
r.s.save(C/'ROOT-SELF-REVIEW.json',dict(recorded_at=datetime.now(timezone.utc).isoformat(),reviewer='/root',independent_review=False,manifest_sha256=pin,frozen_work_and_external_pins_verified=True,exact_targets=p['targets'],temporary_paths=p['temporary_paths'],all_original_values_preserved_or_copied_exactly_to_current_field_history=True,all_eight_gate_rows_unchanged=True,strict_construction_gate_hash_literal_only=True,source560_plus2_Git_index_native_unchanged=True,controls_passed=36,failed_BR1_execution_preserved=True,rejected_BR2_preparation_preserved=True,current_BR3_closed=True,native_assessment_static_not_runtime_proof=True,canonical_writes=False,canonical_test_bodies_executed=0,actual_independent_review_and_gate_and_two_Root_claims_required=True,full_product_acceptance=False,completion_percentage=None))
print(json.dumps(dict(self_review=True,manifest_sha256=pin,canonical_writes=False)))
