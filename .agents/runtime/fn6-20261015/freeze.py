"""Freeze the two-path constructor-only successor after its required checks."""
from foundation_support import *
v=read(R/'INPUTS.json');qualification=read(R/'QUALIFICATION.json')
P=F/'.agents/fn5-20261015';PR=F/'.agents/runtime/fn5-20261015'
parent=read(P/'TRANSFER-MANIFEST.json');failed=read(R/'FAILED-PARENT-READBACK.json')
assert failed['actual_state']=='FAILED' and failed['sequence']==9 and failed['claims']=={}
assert not (Q/'TRANSFER-MANIFEST.json').exists()
rows=qualification['payloads'];assert len(rows)==352
for name,row in rows.items():assert ordinary(Q/name)==row
cohorts={};ids=[]
for label,count in (('controlled-r1',82),('preparation-r1',218),('consumers-r1',94),('joined-r1',8),('outcomes-r1',53),('initializer-r1',3)):
    result=read(R/label/'RESULT.json')
    assert result['tests_run']==count and result['failures']==result['errors']==result['skips']==result['exit_status']==0
    assert result['expected_ids']==result['executed_ids']==result['stopped_ids']
    assert result['candidate_before']==result['candidate_after']==rows
    assert result['remaining_threads']==[]
    ids.extend(result['executed_ids'])
    cohorts[label]=dict(result=reference(R/label/'RESULT.json'),raw=reference(R/label/'tests.txt'),
        tests_run=count,executed_ids=result['executed_ids'])
leaf=qualification['contract_leaf'];assert leaf['tests_run']==3 and leaf['exit_status']==0
ids.extend(leaf['executed_ids']);assert len(ids)==len(set(ids))==461
baseline=read(R/'initializer-binding-r1/RESULT.json')
assert baseline['tests_run']==1 and baseline['failures']==3 and baseline['errors']==baseline['skips']==0 and baseline['exit_status']==1
assert baseline['physical_resources']['owned_resources_closed'] and len(baseline['facts'])==3
assert all(row['borrowed_store_stays_open'] and row['borrowed_connection_executes_select']
    and not row['transaction_open'] and not row['owner_unbound'] for row in baseline['facts'])
focused=read(R/'initializer-r1/RESULT.json');assert focused['all_physical_fixture_resources_closed']
assert all(row['owner_unbound'] and row['next_constructor_error'] is None
    and row['borrowed_store_stays_open'] and row['borrowed_connection_executes_select']
    and not row['transaction_open'] for row in focused['exact_reviewer_oracle_facts'])
controlled=read(R/'controlled-r1/RESULT.json')
assert controlled['mutation_registry_empty'] and controlled['retained_pending_pairs_exact'] and controlled['all_journals_closed']
assert len(controlled['retained_fixture_custody'])==11 and controlled['native_admission_receipts']==[]
supervision=read(R/'supervision-controlled-r1/SUPERVISION-RESULT.json')
assert supervision['exit_status']==0 and supervision['primary'] is None and supervision['record']['child_exit']==0
assert all(value is True for value in supervision['record']['native_owner_after'].values())
assert qualification['parent351_ordinary_native_exact'] and qualification['unchanged350_payloads']
assert qualification['E33601_ordinary_membership_bytes_native_exact']
limits=[
    'Private controlled initializer repair only. No active Source publication, Source/status/Git/E3 mutation, full suite, original native7, OS5 native, restricted no-profile, profile, Hello or CPU Set execution.',
    'The exact WT counterexample reproduced one method/three failed control subcases before repair. Original failed FN5 receipt, raw evidence and seal remain immutable.',
    '461 unique methods pass with zero failures/errors/skips: the exact original458 selections plus three normative constructor methods. One original SQLite crash-child method remains explicitly outside the selected no-child outcome cohort.',
    'All350 reused payloads,2327 parent local test-method bodies, the other33 transaction methods and all noninitializer production ASTs remain exact. One new normative method is the exact reused WT oracle; it receives zero authorship credit.',
    'The initializer now stores the exact bound check and local owner before final publication. No fallible constructor operation follows that publication; existing type/store/owner validation and borrowed-store ownership remain unchanged.',
    'Positive approval/native observations and capacity are CONTROLLED. Actual disposable SQLite and positive canonical retry/prepare do not qualify genuine owner authentication, isolated runtime, physical evidence capacity or native effects.',
    'Public runtime/native admission remains CLOSED. No second issuer/store/scheduler/policy engine is introduced.',
    'Eleven expected controlled pending CPU owner/store/lease pairs remain explicit; their fixture locks are unlocked and mutation registrations retire. This is not successful product cleanup or empty liveness.',
    'The benign bounded test interpreter exited0 with all five captured native custody flags closed. Constructor fixture SQLite/stream/descriptor closure has separate actual physical probes.',
    'F4 directory-attribute differences, interrupted-r4 custody uncertainty and historical NC3 command-provenance correction remain unwaived through the frozen FN5 lineage.',
    'Frozen parent351 and E33601 ordinary membership/bytes/native identities are conserved. Whole directory metadata equality and uninterrupted live Source conservation are not claimed.',
    'CT4 Source290 remains the accepted historical authority; JS5 publisher FAILED13. Any future publication must authenticate Root then-current accepted Source and preserve every forward change.',
    'The copied FN5 packages and eight runtime integration tests receive zero new credit. Physical source diff is3 added/3 removed meaningful lines including one moved publication line; two assignment lines are newly authored. New authored normative test lines68; reused literal oracle42lines credit0.',
    'The single inherited nonnative admission arithmetic test retains its disclosed deterministic elapsed fixture; this supplies no native or natural-time qualification.',
    'This writer authored FN5 and FN6. Distinct WT review remains required before acceptance; no review or integration node is completed by this author.'
]
write_new(R/'PRIOR-ATTEMPTS.json',dict(at=utc(),parent_failed_review=reference(R/'FAILED-PARENT-READBACK.json'),
    WT_original_probe=v['failure_probe'],WT_original_failed_result=v['failure_result'],
    author_exact_baseline=reference(R/'initializer-binding-r1/RESULT.json'),author_baseline_raw=reference(R/'initializer-binding-r1/RAW.txt'),
    author_baseline_exit_status=1,author_baseline_failed_control_subcases=3,
    parent_prior_attempts=parent['prior_failures'],new_unexpected_failed_attempts=[],
    initial_input_row_label_clarification=reference(R/'INPUT-ROW-CLARIFICATION.json')))
write_new(R/'SELF-REVIEW.json',dict(at=utc(),author=AUTHOR,independent_review=False,
    inspected=['Actual initializer descriptor/publication order and every caller',
        'Exact original WT method AST, primary object identity and three baseline/refusal facts',
        'Actual positive retry, canonical preparation, borrowed SQLite SELECT1/no transaction/no implicit close and closed runtime defaults',
        'Other33 transaction ASTs, public signatures, all350 payloads and2327 old method bodies',
        'Original458 selections plus3 constructors, rawIDs, no skips, eleven pending controlled custody pairs and benign runner retirement',
        'Actual physical constructor fixture closure and parent/E3 ordinary-file preservation',
        'Actual rejected FN5 strict13/persisted16/result3/computed fingerprint and artifactnull readback'],
    qualification=reference(R/'QUALIFICATION.json'),failed_parent=reference(R/'FAILED-PARENT-READBACK.json'),
    prior=reference(R/'PRIOR-ATTEMPTS.json'),limits=limits,Source_publication=False))
scripts={name:sha(R/name) for name in ('foundation_support.py','bootstrap.py','probe_initializer_binding.py','repair.py',
    'prepare_runners.py','run_initializer.py','resource_observer.py','run_controlled.py','supervise_controlled.py','bounded_custody.py',
    'run_preparation.py','run_consumers.py','run_joined_controls.py','test_preparation_coordination.py','run_outcomes.py',
    'qualify.py','freeze.py','release_author.py')}
selected=['src/ceta/kernel/transactions.py','tests/contract/test_kernel_initializer_publication.py']
payloads={name:dict(candidate=row,parent=parent['payloads'].get(name),classification='REUSE' if name not in selected else 'EXTEND' if name in parent['payloads'] else 'CREATE',
    active_Source_action='FUTURE_EXACT_ACCEPTED_BASELINE_BINDING_REQUIRED',Source_publication_authorized=False,
    copied_implementation_credit=0 if name not in selected else 'Measured separately in meaningful_LOC') for name,row in rows.items()}
write_new(Q/'TRANSFER-MANIFEST.json',dict(schema_version=1,run_id=RUN,author=AUTHOR,recorded_at=utc(),
    source_root=str(F),candidate_root=str(Q),runtime_root=str(R),scope='FN6 minimal initializer-publication successor',
    parent_manifest=v['parent_manifest'],parent_failed_review=reference(R/'FAILED-PARENT-READBACK.json'),
    parent_author_seal=v['parent_author_seal'],parent_library_lineage=parent['packages'],
    inputs=reference(R/'INPUTS.json'),input_row_clarification=reference(R/'INPUT-ROW-CLARIFICATION.json'),
    payloads=payloads,payload_count=352,REUSE=350,EXTEND=1,CREATE=1,eligible_application_paths=selected,
    auxiliaries={name:ordinary(Q/name) for name in parent['auxiliaries']},
    initializer_repair=reference(R/'REPAIR.json'),constructor_diff=qualification['constructor_diff'],
    selected_cohorts=cohorts,contract_leaf=leaf,executed_unique_methods=461,executed_ids=ids,
    retained458_ids=parent['executed_ids'],original7native='NOT_RUN',original_restricted_no_profile='NOT_RUN',
    exact_original_WT_oracle=True,new_normative_test_methods=3,reused_WT_oracle_methods=1,
    qualification=reference(R/'QUALIFICATION.json'),meaningful_LOC=qualification['meaningful_LOC'],
    prior_failures=reference(R/'PRIOR-ATTEMPTS.json'),self_review=reference(R/'SELF-REVIEW.json'),scripts=scripts,
    retained_pending_controlled_custody=controlled['retained_fixture_custody'],limits=limits,
    Source_publication=False,full_gate_complete=False,native_admission_qualified=False,activation_ready=False))
assert set(parent['executed_ids']).issubset(ids)
print(json.dumps(dict(manifest=reference(Q/'TRANSFER-MANIFEST.json'),payloads=352,tests=461,meaningful_LOC=qualification['meaningful_LOC'])))
