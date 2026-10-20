"""Submit the independently qualified CT4 review using the installed lifecycle."""
from ct4_support import *
import ast, re
M='2e8cdfd1bcd8e1b2c250c33f156df450c03bbc34f60efbdce90c9de3edf08efe'
H='d667f4edcfcba670af85ee06620ac3ee84c713d4f599e36d6cd36d215ca34664'
I='447f7a9149781e1b71aabf7f8bbeb3c54859fafd7f201292909746d117bdb3ed'
B='89f93db80a8fca90e7d5ac49d74aed06484d137e9689ef404e00a471e7f09e98'
inspection=read(V/'candidate-inspection.json');narrow=read(V/'consumer-native-tests.json');wrapper=read(V/'wrapper-tests-r2.json');environment=read(V/'environment-conservation.json')
assert inspection['exit_status']==narrow['exit_status']==wrapper['exit_status']==environment['exit_status']==0
assert narrow['tests_run']==8 and wrapper['tests_run']==17
for value in [narrow,wrapper]:
    assert value['expected_ids']==value['executed_ids'] and len(set(value['executed_ids']))==value['tests_run']
    assert all(type(value[key]) is int and value[key]==0 for key in ('failures','errors','skips','exit_status'))
    raw=F/value['raw_output']['repository_relative_path'];assert sha(raw)==value['raw_output']['sha256']
    assert re.findall(r'^\S+ \(([^)]+)\)',raw.read_text(encoding='utf8'),re.MULTILINE)==value['executed_ids']
assert wrapper['source290_metadata2_candidate3_native_conserved'] is True
assert environment['ordinary_bytes_native_identities_and_membership_equal_to_accepted_ER1'] is True
assert sha(Q/'TRANSFER-MANIFEST.json')==M and sha(R/'apply_reviewed_status.py')==H and sha(R/'integrate_status.py')==I and sha(R/'ACCEPTED-SOURCE-BASELINE.json')==B
assert all(ordinary(F/rel)==row for rel,row in inspection['source_native'].items())
assert all(ordinary(F/rel)==row for rel,row in inspection['active_metadata_native'].items())
assert all(ordinary(Q/rel)==row for rel,row in inspection['candidate_native'].items())
assert all(ordinary(F/rel)==row for rel,row in inspection['globals_native'].items())
plan=F/read(Q/'build/progress.json')['current_repository_execution_20261014']['next_major_acceptance_milestone']['plan']['repository_relative_path']
gates=re.findall(r'^\| (RE-G\d+)\b',plan.read_text(encoding='utf8'),re.MULTILINE)
assert gates==['RE-G0','RE-G1','RE-G2','RE-G3','RE-G4','RE-G5']
helper_review={'executor':ACTOR,'decision':'approved','exit_status':0,'manifest_sha256':M,'publication_script_sha256':H,'integration_script_sha256':I,
    'native_primitive_sha256':'4592a2ccee83904c6fd698a2145d82279e07c0cc27cabb45fd1c13b844baec77',
    'exact_publication_main_and_integration_prefixes_executed':ref(V/'wrapper-tests-r2.json'),
    'unchanged_Source_consumer_and_native_primitive_cases':ref(V/'consumer-native-tests.json'),
    'actual_current_repository_collect':ref(V/'actual-register-measurements-before.json'),'candidate_inspection':ref(V/'candidate-inspection.json'),
    'controls':['Exact immutable two-path manifest, independent strict13/16 typed review records, Root source claim and validate stage',
        'Current accepted PERF seq13/all6/claims empty and exact full1479/Source290 retained',
        'Source originals measured before preservation, before ReplaceFileW, after backup and final original full metadata recheck',
        'Exact two targets with fsynced fresh stages/logical originals/native originals; output occupancy/stale byte guards',
        'Primary BaseException survives journal/add_note failure; explicit retained partial outcome and no automatic rollback',
        'Integration checks actual two targets, native originals, only one work-package leaf correction, historical observations and source baseline',
        'Actual updated collect(F), three consumer unit tests and installed exact two-path Source delta mandatory before Root completion'],
    'qualification':'Finite own native fixtures execute exact wrapper predicates. Fixture claims are unqualified as canonical authority. Root actual Source publication/completion and delivered observation remain pending. No group atomicity or arbitrary concurrent host mutation claim.',
    'prior_failed_attempts':[ref(V/'inspection-r1-command.json'),ref(V/'wrappers-r1-command.json'),ref(V/'fixture-repair.json')]}
save(V/'publication-helper-review.json',helper_review)
summary={'executor':ACTOR,'decision':'approved','exit_status':0,'reviewed_at':utc(),'source_root':str(F),'manifest_sha256':M,
    'publication_script_sha256':H,'integration_script_sha256':I,'baseline_sha256':B,'candidate_inspection':ref(V/'candidate-inspection.json'),
    'publication_helper_review':ref(V/'publication-helper-review.json'),'native_and_consumer_tests':ref(V/'consumer-native-tests.json'),
    'wrapper_tests':ref(V/'wrapper-tests-r2.json'),'tests_run':25,'fixture_consumer_cases':3,'native_primitive_cases':5,'exact_wrapper_cases':17,
    'actual_repository_collection':ref(V/'actual-register-measurements-before.json'),'accepted_environment_conservation':ref(V/'environment-conservation.json'),
    'root_full_Source_tests_inspected':1479,'Source_payloads_rehashed':290,'actual_module_paths_bound':74,'new_source_added':409,'new_source_removed':4,'new_test_added':556,'new_methods':63,
    'changed_json_leaf_counts':inspection['changed_json_leaf_counts'],'exact_work_package_repair':inspection['work_package_exact_leaf_repair'],
    'previous_observations_and_CT3_history_preserved':True,'global_product_axes_requirement_gate_and_other_work_package_states_preserved':True,
    'accepted_RB_and_PERF':'Actual sequence13, all six stages SUCCEEDED, claims empty, exact Source integration receipts and destination proofs',
    'historical_LOC_proof_reconciliation':'Historical preapplication Source_application=false retained under exact hashes; accepted integrated LOC facts independently bind actual accepted ledgers',
    'next_milestone':{'tasks':32,'acceptance_cases':38,'activation_gates':gates,'runtime_effect_acceptance':False,'whole_product_acceptance':False},
    'existing_issues':[{'issue':'WT1 final Stop native dispatch defect','classification':'requires separate follow-up work','proof':ref(F/'.agents/runtime/wt1-20261014/independent-review/review.json')},
        {'issue':'Real-effect native isolation, live owner/time, retained admission, independent outcome and crash acceptance','classification':'not blocking current task; required for next milestone','acceptance':'NOT_RUN'},
        {'issue':'Held history/capture and broader product/installed/endurance/human qualification','classification':'not blocking current task; remains open'}],
    'prior_failures':[ref(V/'inspection-r1-command.json'),ref(V/'wrappers-r1-command.json'),ref(V/'fixture-repair.json')],
    'review_limits':['Full1479 independently inspected exact raw/IDs/current bytes, not another full rerun',
        'Eight actual prepublication consumer inputs collected; Root completion must collect updated real documents',
        'Two-path publication can be partial; preserve native originals and exact journal for reconciliation',
        'Source installation, scoped runtime effect and whole-product acceptance are separate'],
    'Source_mutations':[],'candidate_mutations':[],'new_product_source_LOC':0,'new_product_test_LOC':0,
    'release_scope':'Only frozen two metadata paths through the exact approved helpers and actual Root lifecycle. Delivered readback remains required.'}
save(V/'REPORT.json',summary)
claim=read(R/RUN/'claims.json')['review'];assert claim['executor_id']==ACTOR and claim['workspace']==str(Q)
sys.path.insert(0,r'T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce')
from taar.orchestration_receipts import validate_receipt,load_receipt,sha256_json
from taar.orchestration_runtime import _snapshot_workspace,_changed_files
changed=_changed_files(claim['baseline_snapshot'],_snapshot_workspace(Q,Path('T:/')));assert changed==[]
receipt={'schema_version':1,'run_id':RUN,'node_id':'review','executor_id':ACTOR,'started_at':claim['claimed_at'],'finished_at':utc(),'input_hash':claim['input_hash'],
    'changed_files':changed,'result':summary|{'report':ref(V/'REPORT.json')},
    'commands':[{'command':str(PY)+' -B -X utf8 '+str(V/'inspect_candidate_r2.py'),'exit_status':0},
        {'command':str(PY)+' -B -X utf8 '+str(V/'run_narrow_tests.py')+' '+M,'exit_status':0},
        {'command':str(PY)+' -B -X utf8 '+str(V/'probe_wrappers_r2.py'),'exit_status':0},
        {'command':str(PY)+' -B -X utf8 '+str(V/'verify_environment.py'),'exit_status':0}],
    'validations':[{'name':name,'passed':True} for name in ('exact_707_JSON_leaf_changes_and_one_character_reference_deletion','actual_RB_PERF_accepted_ledgers_and_Source290_full1479_module74_binding',
        'all_prior_observations_CT3_history_and_global_product_axes_preserved','actual_three_consumer_five_native_and_seventeen_wrapper_cases',
        'historical_LOC_proofs_preserved_and_actual_integrated_counts_separate','real_effect_32_tasks38_cases6_gates_nonaccepted','accepted_E3_3601_ordinary_files_conserved','Source_candidate_and_global_native_conservation')],
    'exit_status':0,'decision':'approved'}
kwargs={'run_id':RUN,'node_id':'review','executor_id':ACTOR,'input_hash':claim['input_hash'],'claimed_at':claim['claimed_at'],'node':read(R/RUN/'graph.json')['graph']['nodes']['review']}
validate_receipt(receipt,**kwargs);save(V/'review.json',receipt);validate_receipt(load_receipt(V/'review.json'),**kwargs)
invoke('actual-review-complete',['node','complete',RUN,'review',str(V/'review.json')])
state=read(R/RUN/'state.json');claims=read(R/RUN/'claims.json');stored=read(R/RUN/'receipts/review.json')
assert state['sequence']==9 and state['nodes']['review']['state']=='SUCCEEDED' and claims=={} and stored['decision']=='approved'
assert len(receipt)==13 and set(stored)==set(receipt)|{'git_baseline','observed_git','receipt_hash'}
strict=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
assert strict({k:stored[k] for k in receipt})==strict(receipt)
normalized=dict(stored);normalized.pop('receipt_hash');fingerprint=sha256_json(normalized)
assert fingerprint==stored['receipt_hash']==state['nodes']['review']['receipt_hash']
save(V/'review-readback.json',{'observed_at':utc(),'actual_sequence':9,'actual_review_state':'SUCCEEDED','actual_claims':claims,'persisted_decision':stored['decision'],
    'submitted_fields':13,'persisted_fields':16,'normalized_receipt_fingerprint':fingerprint,'persisted_raw_sha256':sha(R/RUN/'receipts/review.json'),
    'strict_typed_projection_equal':True,'receipt':ref(V/'review.json'),'helper_review':ref(V/'publication-helper-review.json'),'report':ref(V/'REPORT.json'),
    'state_native':ordinary(R/RUN/'state.json'),'claims_native':ordinary(R/RUN/'claims.json')})
print(json.dumps({'decision':'approved','sequence':9,'review':'SUCCEEDED','claims':{},'review_sha256':sha(V/'review.json'),
    'helper_review_sha256':sha(V/'publication-helper-review.json'),'readback_sha256':sha(V/'review-readback.json'),'normalized_receipt_fingerprint':fingerprint}),flush=True)
