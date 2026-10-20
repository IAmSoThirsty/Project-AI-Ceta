"""Complete and release this author claim; distinct review and Source stay pending."""
from foundation_support import *
m=read(Q/'TRANSFER-MANIFEST.json');assert m['executed_unique_methods']==461
for name,row in m['payloads'].items():assert ordinary(Q/name)==row['candidate']
for name,pin in m['scripts'].items():assert sha(R/name)==pin
commands=[dict(command=str(PY)+' -B -X utf8 '+str(R/name)+tail,exit_status=0) for name,tail in (
    ('bootstrap.py',''),('repair.py',''),('prepare_runners.py',''),('run_initializer.py',' initializer-r1'),
    ('supervise_controlled.py',' controlled-r1 all'),('run_preparation.py',' preparation-r1 connected'),
    ('run_consumers.py',' consumers-r1'),('run_joined_controls.py',' joined-r1 joined'),('run_outcomes.py',' outcomes-r1'),
    ('qualify.py',''),('freeze.py',''))]
complete('implement',dict(manifest=reference(Q/'TRANSFER-MANIFEST.json'),manifest_sha256=sha(Q/'TRANSFER-MANIFEST.json'),
    payloads=352,REUSE=350,EXTEND=1,CREATE=1,selected_paths=m['eligible_application_paths'],
    tests=m['selected_cohorts'],contract_leaf=m['contract_leaf'],executed_unique_methods=461,
    failed_parent=m['parent_failed_review'],qualification=m['qualification'],meaningful_LOC=m['meaningful_LOC'],
    prior_failures=m['prior_failures'],scripts=m['scripts'],Source_publication=False,native_admission_qualified=False,full_gate_complete=False),
    commands,[('exact_frozen_FN5_and_actual_rejected_review_fingerprint_bound',True),
        ('descriptor_and_all_constructor_fallibility_precede_final_owner_publication',True),
        ('exact_literal_WT_3_control_failures_reproduced_then_closed',True),
        ('positive_retry_and_canonical_prepare_reuse_borrowed_SQLite_defaults_stay_closed',True),
        ('all350_other_payloads33_transaction_methods2327_parent_test_bodies_exact',True),
        ('original458_plus3_constructor_methods461_unique_PASS_zero_skip',True),
        ('physical_constructor_fixture_closure_and_benign_runner_native_retirement',True),
        ('parent351_E33601_ordinary_membership_bytes_native_conserved',True),
        ('native7_OS5native_restricted_no_profile_full_and_Source_gates_pending',True)])
local=read(R/'implement.json');stored=read(R/RUN/'receipts/implement.json');state=read(R/RUN/'state.json')
claims=read(R/RUN/'claims.json');envelope=read(R/RUN/'results/implement.json')
assert len(local)==12 and set(stored)==set(local)|{'git_baseline','observed_git','receipt_hash'}
assert all(canonical(local[k])==canonical(stored[k]) for k in local)
assert state['sequence']==7 and state['nodes']['implement']['state']=='SUCCEEDED' and state['nodes']['review']['state']=='READY' and claims=={}
assert set(envelope)=={'node_id','receipt_hash','result'} and envelope['node_id']=='implement'
assert canonical(envelope['result'])==canonical(local['result'])
assert envelope['receipt_hash']==stored['receipt_hash']==state['nodes']['implement']['receipt_hash']
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_receipts import validate_receipt
from taar.orchestration_persistence import sha256_json
from taar.orchestration_runtime import _snapshot_workspace,_artifact_hash
normalized=validate_receipt(local,run_id=RUN,node_id='implement',executor_id=AUTHOR,input_hash=local['input_hash'],
    claimed_at=local['started_at'],node=read(R/RUN/'graph.json')['graph']['nodes']['implement'])
normalized.pop('receipt_hash');normalized.update(git_baseline=stored['git_baseline'],observed_git=stored['observed_git'])
assert sha256_json(normalized)==stored['receipt_hash']
assert _artifact_hash(_snapshot_workspace(Q,Path('T:/')),local['changed_files'])==state['nodes']['implement']['artifact_hash']
write_new(R/'AUTHOR-READBACK.json',dict(at=utc(),state=state,claims=claims,manifest=reference(Q/'TRANSFER-MANIFEST.json'),
    implement=reference(R/'implement.json'),persisted=reference(R/RUN/'receipts/implement.json'),result=reference(R/RUN/'results/implement.json'),
    strict12_persisted15_typed_equal=True,official_computed_fingerprint=stored['receipt_hash'],actual_changed_file_artifact_exact=True))
write_new(R/'READY-FOR-REVIEW.json',dict(at=utc(),run_id=RUN,author=AUTHOR,reviewer_expected='/root/wt1_reviewer',
    candidate_root=str(Q),runtime_root=str(R),manifest=reference(Q/'TRANSFER-MANIFEST.json'),implement=reference(R/'implement.json'),
    readback=reference(R/'AUTHOR-READBACK.json'),actual_implement='SUCCEEDED',review='READY',sequence=7,claims={},
    payloads=352,tests=461,selected_paths=m['eligible_application_paths'],scripts=m['scripts'],
    recipe='Reviewer-owned runtime outputs and exact Q imports. Run original458 recipes plus run_initializer.py(3 methods), retain all original ASTs and the same single arithmetic elapsed fixture; no native product/original7/OS5native/restricted no-profile/full/Source/profile/Hello/CPU Set.',
    failed_parent=m['parent_failed_review'],meaningful_LOC=m['meaningful_LOC'],limits=m['limits'],Source_publication=False))
critical=[Q/'TRANSFER-MANIFEST.json',R/'implement.json',R/'AUTHOR-READBACK.json',R/'READY-FOR-REVIEW.json',
    R/'TASK-BINDING.json',R/'CODE-SCOPE.json',R/'INPUTS.json',R/'INPUT-ROW-CLARIFICATION.json',R/'ASSEMBLY.json',
    R/'REPAIR.json',R/'RUNNER-PROVENANCE.json',R/'FAILED-PARENT-READBACK.json',R/'QUALIFICATION.json',
    R/'PRIOR-ATTEMPTS.json',R/'SELF-REVIEW.json',R/'transactions-initializer.diff',R/'contract-leaf-tests.txt',
    R/'initializer-binding-r1/RESULT.json',R/'initializer-binding-r1/RAW.txt',
    R/RUN/'receipts/implement.json',R/RUN/'results/implement.json',R/RUN/'state.json',R/RUN/'claims.json']
for label in m['selected_cohorts']:critical.extend((R/label/'RESULT.json',R/label/'tests.txt'))
for leaf in ('PREPARED-INPUTS.json','ATTEMPT.json','OWNED-RUNNER.json','SUPERVISION-RESULT.json'):
    critical.append(R/'supervision-controlled-r1'/leaf)
critical.extend(R/name for name in m['scripts'])
write_new(R/'AUTHOR-SEAL.json',dict(at=utc(),critical_members=[ordinary(path) for path in critical],payloads=352,
    actual_author_complete=True,claims={},distinct_review_pending=True,Source_publication=False))
print(json.dumps(dict(actual_implement='SUCCEEDED',sequence=7,review='READY',claims={},
    manifest=reference(Q/'TRANSFER-MANIFEST.json'),implement=reference(R/'implement.json'),
    readback=reference(R/'AUTHOR-READBACK.json'),seal=reference(R/'AUTHOR-SEAL.json'),tests=461,meaningful_LOC=m['meaningful_LOC'])))
