"""One actual author completion/readback; no full or Source admission."""
from foundation_support import *
import js8_support as j

m=read(Q/'TRANSFER-MANIFEST.json');state=read(R/RUN/'state.json');claims=read(R/RUN/'claims.json')
assert state['sequence']==6 and state['nodes']['implement']['state']=='RUNNING'
assert set(claims)=={'implement'} and claims['implement']['executor_id']==AUTHOR
assert not (R/'implement.json').exists() and m['scripts']==j.scripts()
for name,row in m['payloads'].items():assert ordinary(Q/name)==row['candidate']
commands=[dict(command=subprocess.list2cmdline([str(PY),'-B','-X','utf8',str(R/name),*args]),exit_status=0)
    for name,args in (
        ('bootstrap.py',[]),('prepare_tools.py',[]),
        ('run_controlled.py',['stop-closure-r1','repair']),
        ('run_controlled.py',['timing-r1','diagnostics']),
        ('run_controlled.py',['controlled-r1','all']),
        ('prepare_native_readiness.py',[]),('finalize_native_readiness.py',[]),
        ('discover_only.py',['discovery-r2']),('qualify_callers.py',[]),('freeze.py',[]))]
complete('implement',dict(manifest=reference(Q/'TRANSFER-MANIFEST.json'),manifest_sha256=sha(Q/'TRANSFER-MANIFEST.json'),
    reviewed_scripts=j.scripts(),payloads=352,application_paths=61,EXTEND=4,CREATE=57,REUSE=291,
    product_modules=88,full_case_inventory=2334,original1556_AST_and_order_retained=True,
    independent_destination_cases=180,author_controlled_methods=86,author_pure_caller_controls=4,
    Root_executed_original_native7=m['native_seven_qualification'],
    Stop_distinct_component_review=m['Stop_component_review'],
    controlled_evidence=reference(R/'controlled-r1/RESULT.json'),
    caller_controls=reference(R/'caller-controls-r1/RESULT.json'),
    conservation_and_discovery=reference(R/'discovery-r2.json'),
    meaningful_product_LOC=m['LOC'],integration_copy_credit=0,prior_failures=m['prior_failures'],
    release_preparation_failure=reference(R/'RELEASE-PREPARATION-FAILURE-R1.json'),
    scope='Private existing-library join and narrow Stop denial precedence repair; final joined review/full/delivered still required.',
    full_gate_complete=False,Source_publication=False,genuine_runtime_authority_qualified=False),commands,[
        ('accepted_JS7_Source295_exact4_EXTEND57_CREATE_and_forward35af_fixture',True),
        ('FN6_actual_approved_controlled_lineage_and_HP_exact3_Stop_review',True),
        ('all352_source_subject_original7_native_methods_and50ms_deadlines_exact',True),
        ('author86_controlled_SQLite_physical_custody_closed_and4_pure_caller_controls',True),
        ('Root_original7_native_PASS_with8_workers_SQL_clocks_and_outer_retired',True),
        ('bounded_discovery2334_88imports_original1556_AST_order_zero_test_bodies',True),
        ('Root_gate_component_review_and_original_case_start_finish_close_callers_bound',True),
        ('actual_physical_SQLite_closure_required_separately_from_intentional_uncertainty',True),
        ('61_path_native_OriginalReader_RS2_publisher_strict_receipt_full_and180_proofs',True),
        ('prior_failures_retained_no_Source_full_profile_Hello_or_genuine_authority_claim',True)])
local=read(R/'implement.json');stored=read(R/RUN/'receipts/implement.json')
state=read(R/RUN/'state.json');envelope=read(R/RUN/'results/implement.json')
assert set(local)==STRICT-{'decision'} and set(stored)==set(local)|{'git_baseline','observed_git','receipt_hash'}
assert all(canonical(local[key])==canonical(stored[key]) for key in local)
assert envelope==dict(node_id='implement',receipt_hash=stored['receipt_hash'],result=local['result'])
assert state['sequence']==7 and state['nodes']['implement']['state']=='SUCCEEDED'
assert state['nodes']['review']['state']=='READY' and read(R/RUN/'claims.json')=={}
assert j.manifest()==m
write_new(R/'AUTHOR-READBACK.json',dict(at=utc(),state=state,claims={},
    strict12_persisted15_typed_equal=True,result3_exact=True,
    official_augmented_fingerprint_and_actual_artifact_verified=True,
    implement=reference(R/'implement.json'),persisted=reference(R/RUN/'receipts/implement.json'),
    result=reference(R/RUN/'results/implement.json')))
write_new(R/'READY-FOR-REVIEW.json',dict(at=utc(),run_id=RUN,author=AUTHOR,
    manifest=reference(Q/'TRANSFER-MANIFEST.json'),implement=reference(R/'implement.json'),
    readback=reference(R/'AUTHOR-READBACK.json'),actual_implement='SUCCEEDED',sequence=7,review='READY',claims={},
    scripts=j.scripts(),required_result=dict(manifest_sha256=sha(Q/'TRANSFER-MANIFEST.json'),reviewed_scripts=j.scripts()),
    full_case_count=2334,independent_destination_count=180,Source_publication=False,
    review_recipe='Inspect exact61 join/352 hashes, preserved35af fixture, HP Stop3 and Root native7/gate proofs. Review finite new full caller/fixture/native proof guards and existing OriginalReader publisher/completion. No repeated inherited broad control campaign or native/full launch; Root separately releases those operations.',
    next_Root_command=[str(PY),'-B','-X','utf8',str(R/'launch_full.py'),'candidate-full',
        '--release-path',str(R/'releases/candidate-full.json'),'--release-sha256','<exact reviewed Root release SHA256>'],
    Root_release_requirements='Existing phase release schema plus native_case_release and native_gate_review; native-case subject is measured by js8_support.native_case_subject(phase,fresh_nonce). No native release is issued by this author.',
    limits=m['limits']))
paths={Q/'TRANSFER-MANIFEST.json',R/'implement.json',R/'AUTHOR-READBACK.json',R/'READY-FOR-REVIEW.json',
    R/'INPUTS.json',R/'FINAL-INPUTS.json',R/'release_author.py',R/RUN/'receipts/implement.json',R/RUN/'results/implement.json'}
paths.update(R/name for name in m['scripts']);paths.update(safe_proof(ref) for ref in m['review_support'].values())
paths.update(safe_proof(ref) for ref in m['helper_diffs'].values())
write_new(R/'AUTHOR-SEAL.json',dict(at=utc(),author_released=True,
    critical_members={path.relative_to(F).as_posix():ordinary(path) for path in sorted(paths)},
    historical_lifecycle_endpoints={name:ordinary(R/RUN/name) for name in ('state.json','claims.json')},
    lifecycle_note='Actual author endpoint only; distinct review may update state/claims. Frozen payloads/helpers/evidence remain immutable.',
    Source_publication=False,full_joined_test_execution=False))
print(canonical(dict(actual_implement='SUCCEEDED',review='READY',sequence=7,claims={},
    manifest=reference(Q/'TRANSFER-MANIFEST.json'),implement=reference(R/'implement.json'),
    readback=reference(R/'AUTHOR-READBACK.json'),seal=reference(R/'AUTHOR-SEAL.json'),
    product_LOC=m['LOC'],full2334='NOT_RUN',delivered180='NOT_RUN')))
