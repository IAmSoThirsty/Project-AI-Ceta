"""Complete and release only FN5 author implementation, never review or Source."""
from foundation_support import *
m=read(Q/'TRANSFER-MANIFEST.json');assert m['executed_unique_methods']==458 and m['Source_publication'] is False
for name,row in m['payloads'].items():assert ordinary(Q/name)==row['candidate']
for name,pin in m['scripts'].items():assert sha(R/name)==pin
commands=[dict(command=str(PY)+' -B -X utf8 '+str(R/name)+tail,exit_status=0) for name,tail in (
    ('bootstrap.py',''),('finalize_assembly.py',''),('prepare_runners.py',''),('inventory-r2.py',''),
    ('supervise_controlled.py',' controlled-r1 all'),('run_preparation.py',' preparation-r1 connected'),
    ('run_consumers.py',' consumers-r2'),('run_joined_controls.py',' joined-r2 joined'),
    ('run_outcomes.py',' outcomes-r1'),('qualify.py',''),('freeze.py',''))]
complete('implement',dict(manifest=reference(Q/'TRANSFER-MANIFEST.json'),manifest_sha256=sha(Q/'TRANSFER-MANIFEST.json'),
    scope=m['scope'],payloads=351,REUSE=m['REUSE'],EXTEND=m['EXTEND'],CREATE=m['CREATE'],
    executed_unique_methods=458,tests=m['selected_cohorts'],contract_leaf=m['contract_leaf'],
    test_inventory=m['test_inventory'],approved_test_mapping=m['approved_test_successor_mapping'],
    line_ownership=m['line_ownership'],qualification=m['qualification'],scripts=m['scripts'],
    meaningful_LOC=m['meaningful_LOC'],prior_failures=m['prior_failures'],
    Source_publication=False,full_joined_gate_complete=False,native_admission_qualified=False),commands,[
        ('exact_approved_KA5_OS5_JS5_source_inputs_and_underlying_F4_limited_review',True),
        ('351_private_payloads_no_wholesale_overlay_and_exact_constructor_publication_order',True),
        ('KA5_coordinator_Stop_consumption_outcomes_preserved_OS5_private_same_CAS_preparation_joined',True),
        ('all_parent_test_method_ASTs_retained_with_exact_approved_strengthened_projection_mapping',True),
        ('458_unique_selected_domain_and_contract_methods_PASS_zero_skip_with_raw_IDs',True),
        ('actual_disposable_SQLite_no_SQL_over_effect_no_native_product_authority_or_workers',True),
        ('frozen_parent_and_E33601_ordinary_membership_bytes_native_identity_exact',True),
        ('F4_metadata_interrupted_custody_native_full_and_Source_gates_explicitly_unwaived',True)])
local=read(R/'implement.json');stored=read(R/RUN/'receipts/implement.json')
state=read(R/RUN/'state.json');claims=read(R/RUN/'claims.json');envelope=read(R/RUN/'results/implement.json')
assert len(local)==12 and set(stored)==set(local)|{'git_baseline','observed_git','receipt_hash'}
assert all(canonical(local[k])==canonical(stored[k]) for k in local)
assert state['sequence']==7 and state['nodes']['implement']['state']=='SUCCEEDED'
assert state['nodes']['review']['state']=='READY' and claims=={}
assert set(envelope)=={'node_id','receipt_hash','result'} and envelope['node_id']=='implement'
assert stored['receipt_hash']==envelope['receipt_hash']==state['nodes']['implement']['receipt_hash']
assert canonical(local['result'])==canonical(envelope['result'])
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
    implement=reference(R/'implement.json'),persisted=reference(R/RUN/'receipts/implement.json'),
    result=reference(R/RUN/'results/implement.json'),strict12_persisted15_typed_equal=True,
    official_computed_fingerprint=stored['receipt_hash'],current_changed_file_artifact_verified=True))
write_new(R/'READY-FOR-REVIEW.json',dict(at=utc(),run_id=RUN,author=AUTHOR,candidate_root=str(Q),runtime_root=str(R),
    manifest=reference(Q/'TRANSFER-MANIFEST.json'),implement=reference(R/'implement.json'),readback=reference(R/'AUTHOR-READBACK.json'),
    actual_implement='SUCCEEDED',review='READY',sequence=7,claims={},payloads=351,executed_unique_methods=458,scripts=m['scripts'],
    review_scope='Joined library integration and exact selected controlled gates only; no Source publication or genuine/native/full acceptance.',
    authorship='This writer authored KA5, OS5, JS5 and the surgical FN5 assembly. Parent distinct component reviews are authenticated; FN5 requires a named distinct reviewer.',
    recipe='Use exact Q/src imports and new reviewer-owned runtime outputs. Transparently rebind fixture roots/receipt paths; preserve all original method ASTs and the disclosed single arithmetic elapsed fixture. Cohorts82+218+94+8+53+3; no native product, profile, Hello, CPU Set, restricted no-profile or original native7 rerun.',
    limits=m['limits'],Source_publication=False,full_gate_complete=False))
critical=[Q/'TRANSFER-MANIFEST.json',R/'implement.json',R/'AUTHOR-READBACK.json',R/'READY-FOR-REVIEW.json',
    R/'TASK-BINDING.json',R/'CODE-SCOPE.json',R/'SCOPE-ADDITION-OS5-TESTS.json',R/'INPUTS.json',R/'ASSEMBLY.json',
    R/'FILE-OWNERSHIP.json',R/'TRANSACTION-LINE-OWNERSHIP.json',R/'TEST-METHOD-INVENTORY-r2.json',
    R/'APPROVED-TEST-CONFLICT-RESOLUTION.json',R/'QUALIFICATION.json',R/'PRIOR-ATTEMPTS.json',R/'SELF-REVIEW.json',
    R/'RUNNER-PROVENANCE.json',R/'contract-leaf-tests.txt',R/RUN/'receipts/implement.json',R/RUN/'results/implement.json',
    R/RUN/'state.json',R/RUN/'claims.json']
for label in m['selected_cohorts']:
    critical.extend((R/label/'RESULT.json',R/label/'tests.txt'))
for name in ('PREPARED-INPUTS.json','ATTEMPT.json','OWNED-RUNNER.json','SUPERVISION-RESULT.json'):
    critical.append(R/'supervision-controlled-r1'/name)
critical.extend(R/name for name in m['scripts'])
critical.extend(safe_proof(row['diff']) for row in m['physical_diff_excluding_credit'].values())
critical.extend(R/name for name in ('prior-attempts/assemble-r1.py','prior-attempts/inventory-r1.py',
    'prior-attempts/TEST-METHOD-INVENTORY-r1.json','prior-attempts/run_consumers-r1.py',
    'prior-attempts/test_preparation_coordination-r1.py','consumers-r1/tests.txt','joined-r1/RESULT.json','joined-r1/tests.txt'))
write_new(R/'AUTHOR-SEAL.json',dict(at=utc(),critical_members=[ordinary(path) for path in critical],
    payloads=351,claims={},actual_author_complete=True,independent_review_pending=True,Source_publication=False))
print(json.dumps(dict(actual_implement='SUCCEEDED',sequence=7,review='READY',claims={},
    manifest=reference(Q/'TRANSFER-MANIFEST.json'),implement=reference(R/'implement.json'),
    readback=reference(R/'AUTHOR-READBACK.json'),seal=reference(R/'AUTHOR-SEAL.json'),
    tests=458,new_product_LOC=0,new_runtime_test_LOC=120)))
