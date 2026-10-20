"""One truthful installed review receipt after the exact finite FN6 cohort."""
from review_support import *
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_persistence import sha256_json
from taar.orchestration_receipts import validate_receipt
from taar.orchestration_runtime import _snapshot_workspace,_changed_files

frozen=preflight();m=read(Q/'TRANSFER-MANIFEST.json')
state=read(A/RUN/'state.json');claims=read(A/RUN/'claims.json')
assert state['sequence']==8 and state['nodes']['review']['state']=='RUNNING'
assert set(claims)=={'review'} and claims['review']['executor_id']==ACTOR and Path(claims['review']['workspace'])==Q
claim=claims['review']
cohorts={};ordered=[];physical={};all_pass=True
for label in ('initializer-r1','controlled-r1','preparation-r1','consumers-r1','joined-r1','outcomes-r1'):
    row=m['selected_cohorts'][label]
    value=read(V/label/'RESULT.json')
    assert value['expected_ids']==value['executed_ids']==value['stopped_ids']==row['executed_ids']
    assert value['tests_run']==row['tests_run'] and type(value['tests_run']) is int
    for name in ('failures','errors','skips','exit_status'):assert type(value[name]) is int
    all_pass=all_pass and all(value[k]==0 for k in ('failures','errors','skips','exit_status'))
    ordered.extend(value['executed_ids'])
    cohorts[label]=dict(result=reference(V/label/'RESULT.json'),raw=reference(V/label/'tests.txt'),tests_run=value['tests_run'],
        expected_ids=value['expected_ids'],executed_ids=value['executed_ids'],stopped_ids=value['stopped_ids'],
        failures=value['failures'],errors=value['errors'],skips=value['skips'],exit_status=value['exit_status'])
leaf=read(V/'leaf-r1/RESULT.json');expected_leaf=m['contract_leaf']['executed_ids']
assert leaf['expected_ids']==leaf['executed_ids']==leaf['stopped_ids']==expected_leaf and leaf['tests_run']==3
all_pass=all_pass and all(type(leaf[k]) is int and leaf[k]==0 for k in ('failures','errors','skips','exit_status'))
ordered.extend(leaf['executed_ids']);assert len(ordered)==len(set(ordered))==461
assert set(ordered)==set(m['executed_ids'])
cohorts['leaf-r1']=dict(result=reference(V/'leaf-r1/RESULT.json'),raw=reference(V/'leaf-r1/tests.txt'),tests_run=3,
    expected_ids=expected_leaf,executed_ids=leaf['executed_ids'],stopped_ids=leaf['stopped_ids'],failures=leaf['failures'],
    errors=leaf['errors'],skips=leaf['skips'],exit_status=leaf['exit_status'])
for kind in ('controlled','preparation','consumers','joined','outcomes','initializer','leaf'):
    proof=read(V/('PHYSICAL-'+kind+'.json'))
    assert proof['runner_exit_status']==0 and proof['exit_status']==0
    assert proof['all_physical_captured_resources_closed'] is True and proof['remaining_threads']==[]
    resources=proof['physical_resources']
    assert resources['remaining_resources']==[] and resources['owned_resources_closed'] is True
    assert all(row['physical_closed_probe'] is True for row in resources['sqlite'])
    assert all(row['closed'] is True and row['fileno_denied'] is True for row in resources['streams'])
    assert all(row['closed'] is True for row in resources['os_descriptors'])
    physical[kind]=dict(proof=reference(V/('PHYSICAL-'+kind+'.json')),sqlite=len(resources['sqlite']),
        streams=len(resources['streams']),descriptors=len(resources['os_descriptors']),all_captured_physically_closed=True)
control=read(V/'controlled-r1/RESULT.json');retained=control['retained_fixture_custody']
initializer=read(V/'initializer-r1/RESULT.json')
oracle_facts=initializer['exact_reviewer_oracle_facts']
assert len(oracle_facts)==3
assert {r['control'] for r in oracle_facts}=={'KeyboardInterrupt','SystemExit','MemoryError'}
assert all(r['exact_primary'] is True and r['manual_binding_calls']==1 and r['exact_owner'] is True
    and r['owner_unbound'] is True and r['next_constructor_error'] is None and r['borrowed_store_stays_open'] is True
    and r['borrowed_connection_executes_select'] is True and r['transaction_open'] is False and r['actual_native_calls']==0
    for r in oracle_facts)
assert len(retained)==11 and control['retained_pending_pairs_exact'] is True
assert all(row['pending_cleanup'] is True and row['closed'] is False and row['controlled_retainer_locked'] is False for row in retained)
assert control['mutation_registry_empty'] is True and control['metadata_lock_nonblocking_acquired'] is True
assert control['forbidden_native_constructor_calls']==[] and control['native_admission_receipts']==[]
assert len(control['controlled_elapsed_evidence'])==1
supervision=read(V/'supervision-controlled-r1/SUPERVISION-RESULT.json')
assert supervision['exit_status']==0 and supervision['primary'] is None and supervision['source_six_preserved'] is True
native=supervision['record'];assert native['child_exit']==0 and all(native['native_owner_after'].values())
assert native['retirement_error'] is None and native['automatic_cleanup_retry'] is False
consumers=read(V/'consumers-r1/RESULT.json')
assert consumers['constructor_native_connections_closed'] is True and consumers['postconstruction_native_connections_closed'] is True
for label in ('preparation-r1','consumers-r1','joined-r1','outcomes-r1','initializer-r1'):
    value=read(V/label/'RESULT.json')
    assert value.get('remaining_threads',[])==[]
    assert value.get('forbidden_calls',value.get('forbidden_native_calls',[]))==[]

def members(text):
    tree=ast.parse(text);c=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='KernelTransactions')
    return tree,{n.name:n for n in c.body if isinstance(n,ast.FunctionDef)}
_,joined=members((Q/'src/ceta/kernel/transactions.py').read_bytes())
_,ka5=members((F/'.agents/ka5-20261015/src/ceta/kernel/transactions.py').read_bytes())
_,os5=members((F/'.agents/os5-20261015/src/ceta/kernel/transactions.py').read_bytes())
ka5_methods={name:ast.dump(node,include_attributes=False)==ast.dump(ka5[name],include_attributes=False)
    for name,node in joined.items() if name not in ('__init__','prepare','_prepare')}
assert len(ka5_methods)==31 and all(ka5_methods.values())
for name in ('prepare','_prepare'):
    assert [ast.dump(n,include_attributes=False) for n in joined[name].body]==[ast.dump(n,include_attributes=False) for n in os5[name].body]
assert [ast.dump(n,include_attributes=False) for n in joined['prepare'].decorator_list]==[ast.dump(n,include_attributes=False) for n in ka5['prepare'].decorator_list]
mapping=read(F/'.agents/runtime/fn5-20261015/APPROVED-TEST-CONFLICT-RESOLUTION.json')
for name in ('approved_selected_input','preserved_prior'):s.safe_proof(mapping[name])
projection=Q/mapping['path'];assert sha(projection)==mapping['approved_selected_input']['sha256']
def methods(path):
    return {c.name+'.'+n.name:ast.dump(n,include_attributes=False) for c in ast.parse(Path(path).read_bytes()).body
        if isinstance(c,ast.ClassDef) for n in c.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
old=methods(s.safe_proof(mapping['preserved_prior']));new=methods(projection)
assert set(old)==set(new)
changed=[name for name in old if old[name]!=new[name]]
assert changed==[mapping['method'].split('.',1)[1]]
lineage={}
for name,parent in m['parent_library_lineage'].items():
    manifest=s.safe_proof(parent['manifest']);review=s.safe_proof(parent['review']['review'])
    local=read(review);stored_path=s.safe_proof(parent['review']['persisted']);stored=read(stored_path)
    runtime=stored_path.parents[1];run=local['run_id'];current=read(runtime/'state.json')
    assert set(local)==s.STRICT and set(stored)==s.STRICT|{'git_baseline','observed_git','receipt_hash'}
    assert all(canonical(local[k])==canonical(stored[k]) for k in s.STRICT)
    assert local['decision']=='approved' and type(local['exit_status']) is int and local['exit_status']==0
    assert current['nodes']['review']['state']=='SUCCEEDED'
    assert current['nodes']['review']['receipt_hash']==stored['receipt_hash']==parent['review']['receipt_hash']
    normalized=validate_receipt(local,run_id=run,node_id='review',executor_id=local['executor_id'],input_hash=local['input_hash'],
        claimed_at=local['started_at'],node=read(runtime/'graph.json')['graph']['nodes']['review'])
    normalized.pop('receipt_hash');normalized.update(git_baseline=stored['git_baseline'],observed_git=stored['observed_git'])
    assert sha256_json(normalized)==stored['receipt_hash']
    lineage[name]=dict(manifest=reference(manifest),review=reference(review),persisted=reference(stored_path),
        actual_review_state='SUCCEEDED',official_fingerprint=stored['receipt_hash'],current_run_sequence=current['sequence'],
        review_only_not_parent_integrate_acceptance=True)

preflight()
changed_files=_changed_files(claim['baseline_snapshot'],_snapshot_workspace(Q,Path('T:/')))
assert changed_files==[]
commands=[dict(command=str(s.PY)+' -B -X utf8 '+str(V/'prepare_review.py'),exit_status=0),
    dict(command=str(s.PY)+' -B -X utf8 '+str(V/'execute_review.py')+' initializer',exit_status=0),
    dict(command=str(s.PY)+' -B -X utf8 '+str(V/'supervise_review.py'),exit_status=supervision['exit_status'])]
commands.extend(dict(command=str(s.PY)+' -B -X utf8 '+str(V/'execute_review.py')+' '+kind,exit_status=0)
    for kind in ('preparation','consumers','joined','outcomes','leaf'))
limits=[
    'This approves only the private FN6 integrated library and its constructor repair; Source publication and product completion are not established.',
    'Exactly461 selected methods executed:82 controlled admission+218 preparation+94 consumers+8 coordination+53 outcomes+3 original leaf+3 initializer. Original458 selections and all method bodies retained.',
    'Original seven native CPU methods, OS5 native cases, restricted no-profile case and one crash-child outcome case are NOT_RUN. No native product worker, profile, Hello or CPU Set was executed.',
    'Authority, native observations, target and physical-capacity positives are CONTROLLED. Actual disposable SQLite/canonical preparation does not qualify genuine identity, isolation, native effects or physical storage reservation.',
    'Eleven expected pending controlled owner/store/lease pairs are retained with locks unlocked, leases not closed and mutation registrations empty. They are not successful product cleanup or empty liveness.',
    'Physical closure probes cover the exact captured actual SQLite connections, streams/descriptors and the benign bounded interpreter owner. No general historical handle-retirement claim is made.',
    'One original nonnative arithmetic method retains its disclosed deterministic1000ns elapsed fixture; no natural-time/native timing qualification is inferred.',
    'FN5 actual FAILED9 and original literal three failing subcases remain preserved. This is a fresh successor review, not a retry of FN5.',
    'Source CT4 is the historical accepted290 baseline; no fresh whole Source conservation or acceptance claim is made. Only the six current read-only canonical files used by the benign supervisor are separately pinned.',
    'Q352,parent351,E33601 ordinary membership/bytes/native facts are conserved. Whole directory metadata equality and earlier F4/interrupted-run/NC3 historical concerns remain unwaived.',
    'Reviewer previously authored WT4/AC3 dependencies and reviewed KA5; this review independently qualifies the FN6 assembly/constructor delta while relying on the recorded distinct component reviews.',
    'Meaningful FN6 physical delta3added/3removed includes one moved publication line;2 new assignments,68new test lines,42 reused literal-oracle lines credit0. All350 reused payloads and copied runtime tests receive zero new product credit.',
    'The exploratory nonexistent finish_review.py read failed before review claim; it is disclosed preparation history and not listed as a successful qualifying command.'
]
decision='approved' if all_pass else 'rejected'
report=dict(at=utc(),decision=decision,author=s.AUTHOR,reviewer=ACTOR,manifest=reference(Q/'TRANSFER-MANIFEST.json'),
    manifest_sha256=sha(Q/'TRANSFER-MANIFEST.json'),selected_source_paths=m['eligible_application_paths'],
    code_findings=[],constructor_final_publication=True,public_signature_preserved=True,borrowed_store_preserved=True,
    actual_original_oracle_facts=oracle_facts,review_helper=reference(Path(__file__)),
    literal_counterexample=reference(F/'.agents/runtime/fn5-20261015/independent-review/probe_initializer_binding.py'),
    original_counterexample_method_AST_exact=True,other33_transaction_methods_exact=True,KA5_exact31_methods=ka5_methods,
    exact_OS5_prepare_bodies=True,prepare_KA5_coordinated_decorator_exact=True,
    unchanged350_payloads=True,parent2327_test_methods_exact=True,approved_projection_method_mapping=reference(F/'.agents/runtime/fn5-20261015/APPROVED-TEST-CONFLICT-RESOLUTION.json'),
    parent_library_reviews=lineage,cohorts=cohorts,tests_run=461,failures=sum(c['failures'] for c in cohorts.values()),
    errors=sum(c['errors'] for c in cohorts.values()),skips=sum(c['skips'] for c in cohorts.values()),
    executed_ids=ordered,physical_resources=physical,benign_native_outer=reference(V/'supervision-controlled-r1/SUPERVISION-RESULT.json'),
    actual_benign_native_identity=native['native_owner'],actual_benign_native_closed=native['native_owner_after'],
    eleven_expected_pending_controlled_pairs=retained,pending_pair_qualification='Controlled failure custody retained, lockedFalse, not closed.',
    candidate_parent_environment_conserved=True,changed_files=[],reviewed_scripts=m['scripts'],meaningful_LOC=m['meaningful_LOC'],
    commands=commands,preparation_disclosure=reference(V/'PREPARATION-DISCLOSURE.json'),limits=limits,
    Source_publication=False,Source_acceptance=False,native7_qualified=False,product_complete=False)
write_new(V/'REPORT.json',report)
result=dict(manifest_sha256=sha(Q/'TRANSFER-MANIFEST.json'),report=reference(V/'REPORT.json'),reviewed_scripts=m['scripts'],
    decision=decision,tests_run=461,failures=report['failures'],errors=report['errors'],skips=report['skips'],
    cohorts=cohorts,physical_resources=physical,Source_publication=False,native_admission_qualified=False,
    full_gate_complete=False,limits=limits,review_input_manifest=reference(V/'REVIEW-INPUTS.json'))
receipt=dict(schema_version=1,run_id=RUN,node_id='review',executor_id=ACTOR,started_at=claim['claimed_at'],
    finished_at=utc(),input_hash=claim['input_hash'],changed_files=[],result=result,commands=commands,
    validations=[dict(name=name,passed=True) for name in (
        'complete_inputs_pinned_before_every_cohort','all461_selected_exact_ids_PASS_zero_skip',
        'original_literal_failure_repaired_without_publishing_incomplete_kernel',
        'canonical_positive_retry_borrowed_SQLite_and_closed_defaults',
        'all350_reuse33methods2327parent_ASTs_and_projection_mapping_exact',
        'captured_physical_SQL_stream_descriptor_and_benign_native_owners_retired',
        'eleven_expected_controlled_pending_pairs_explicit_unlocked',
        'Q_parent_E3_ordinary_native_conserved_Source_native7_not_claimed')],
    exit_status=0 if all_pass else 1,decision=decision)
validate_receipt(receipt,run_id=RUN,node_id='review',executor_id=ACTOR,input_hash=claim['input_hash'],
    claimed_at=claim['claimed_at'],node=read(A/RUN/'graph.json')['graph']['nodes']['review'])
write_new(V/'review.json',receipt)
invoke(['node','complete',RUN,'review',str(V/'review.json')],'review-complete')
local,stored,state,envelope=current_receipt('review',V/'review.json',ACTOR)
claims=read(A/RUN/'claims.json')
assert state['sequence']==9 and state['nodes']['review']['state']==('SUCCEEDED' if all_pass else 'FAILED') and claims=={}
expected_artifact=sha256_json({'input_hash':claim['input_hash'],'result':receipt['result']}) if all_pass else None
assert state['nodes']['review']['artifact_hash']==expected_artifact
write_new(V/'REVIEW-READBACK.json',dict(at=utc(),actual_state=state['nodes']['review']['state'],sequence=state['sequence'],claims=claims,
    review=reference(V/'review.json'),report=reference(V/'REPORT.json'),persisted=reference(A/RUN/'receipts/review.json'),
    result_envelope=reference(A/RUN/'results/review.json'),strict_local13_persisted16=True,result3_exact=True,
    official_augmented_fingerprint=stored['receipt_hash'],artifact_hash=expected_artifact,actual_readonly_artifact_verified=True,
    tests_run=461,Source_publication=False,native7_NOT_RUN=True))
files=[p for p in V.rglob('*') if p.is_file()]
assert not (V/'REVIEW-SEAL.json').exists()
write_new(V/'REVIEW-SEAL.json',dict(at=utc(),members=[ordinary(p) for p in sorted(files)],
    actual_state=state['nodes']['review']['state'],sequence=9,claims={},Source_publication=False))
for row in read(V/'REVIEW-SEAL.json')['members']:assert ordinary(Path(row['path']))==row
print(json.dumps(dict(actual_state=state['nodes']['review']['state'],sequence=9,claims={},tests_run=461,
    report=reference(V/'REPORT.json'),review=reference(V/'review.json'),readback=reference(V/'REVIEW-READBACK.json'),
    seal=reference(V/'REVIEW-SEAL.json'),physical_resources=physical,official_fingerprint=stored['receipt_hash'])))
