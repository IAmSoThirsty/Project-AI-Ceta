"""Claim one private, exact-version foundation integration; never publish Source."""
from foundation_support import *

PACKAGES = {
    'ka5': ('ka5-20261015', 'd96cae1fbddd213a2ab3d49309a5021c018db8bca57404c41712a502bcd9c3fd',
        'independent-review', 'ca6a2d83f5ea8ced6a10f92eaeb0c1146673d6be793b25eb5f3f24eaacbd7dfe'),
    'os5': ('os5-20261015', 'e61b267de1efe099163881b09648cd7777692a03ed869ff2c2c9cb8895559235',
        'independent-root-review', '501b9bd2f8cc7639650dfae7b9b9b7f5d1c89addc56005ec3480da683258bdd6'),
    'js5': ('js5-20261015', '4c222e6f1b57cf023713b8af229c3bfa963523e46ac9b5c14023731c642f07a3',
        'independent-review', 'a41a1b9e3d182ba68c07d78b57e02877fff5bde8fd8f929508b51d5470c3f1b3'),
}

def authenticate_review(run, directory, pin, manifest_pin):
    runtime=F/'.agents/runtime'/run
    path=runtime/directory/'review.json'
    facts=ordinary(path);raw=path.read_bytes()
    assert digest(raw)==pin==facts['sha256'] and ordinary(path)==facts
    local=json.loads(raw);stored=read(runtime/run/'receipts/review.json')
    state=read(runtime/run/'state.json');node=state['nodes']['review']
    result=read(runtime/run/'results/review.json')
    assert set(local)==STRICT and set(stored)==STRICT|{'git_baseline','observed_git','receipt_hash'}
    assert all(canonical(local[k])==canonical(stored[k]) for k in STRICT)
    assert local['run_id']==run and local['node_id']=='review'
    assert type(local['exit_status']) is int and local['exit_status']==0 and local['decision']=='approved'
    assert type(local['executor_id']) is str and local['executor_id'] and local['executor_id']!=AUTHOR
    assert local['result']['manifest_sha256']==manifest_pin
    assert node['state']=='SUCCEEDED' and node['claim'] is None
    assert set(result)=={'node_id','receipt_hash','result'} and result['node_id']=='review'
    assert canonical(result['result'])==canonical(local['result'])
    assert node['receipt_hash']==stored['receipt_hash']==result['receipt_hash']
    sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
    from taar.orchestration_receipts import validate_receipt
    from taar.orchestration_persistence import sha256_json
    normalized=validate_receipt(local,run_id=run,node_id='review',executor_id=local['executor_id'],
        input_hash=local['input_hash'],claimed_at=local['started_at'],
        node=read(runtime/run/'graph.json')['graph']['nodes']['review'])
    normalized.pop('receipt_hash');normalized.update(git_baseline=stored['git_baseline'],observed_git=stored['observed_git'])
    assert sha256_json(normalized)==stored['receipt_hash']
    assert node['artifact_hash']==sha256_json({'input_hash':local['input_hash'],'result':local['result']})
    return dict(review=reference(path),state=reference(runtime/run/'state.json'),
        persisted=reference(runtime/run/'receipts/review.json'),receipt_hash=stored['receipt_hash'],
        reviewer=local['executor_id'],scope=local['result'].get('review_scope',local['result'].get('scope')))

assert not Q.exists()
manifests={};qualified={};inputs={}
for label,(run,pin,directory,review_pin) in PACKAGES.items():
    path=F/'.agents'/run/'TRANSFER-MANIFEST.json'
    facts=ordinary(path);raw=path.read_bytes()
    assert digest(raw)==pin==facts['sha256'] and ordinary(path)==facts
    manifests[label]=json.loads(raw)
    qualified[label]=authenticate_review(run,directory,review_pin,pin)
    inputs[label]=dict(manifest=reference(path),review=qualified[label],payload_count=len(manifests[label]['payloads']))

# Authenticate the accepted library foundation, retaining its explicit limits.
f4run='re-foundation4-20261015';f4path=F/'.agents'/f4run/'TRANSFER-MANIFEST.json'
assert sha(f4path)=='98b49f825ab4f5d8b23ed980b93dd3c90a82be1869a93e034047f0fafcffb8bb'
f4review=authenticate_review(f4run,'independent-review',
    '6590906b90dda87767e5224420f308119b19c917265b46fd01ff07d7404ddd7e',sha(f4path))
lineage=[]
for run in ('ka5-20261015','ka4-20261015','ka3-20261015','ka2-20261015'):
    path=F/'.agents'/run/'TRANSFER-MANIFEST.json';body=read(path)
    parent=body['parent_manifest'];safe_proof(parent)
    lineage.append(dict(run_id=run,manifest=reference(path),parent=parent))
assert lineage[-1]['parent']==reference(f4path)
f4=read(f4path);safe_proof(f4['parent_qualification'])
f4body=read(F/'.agents/runtime'/f4run/'independent-review/review.json')['result']

environment_old=read(F/'.agents/runtime/ka5-20261015/INPUTS.json')['E33601']
environment={n:ordinary(PY.parent.parent/n) for n in environment_old}
assert environment==environment_old and len(environment)==3601
Q.mkdir()
invoke(['run','init','--root','T:/','--scope',str(Q),'--run-id',RUN],'run-init')
claim('discover')
selected={label:manifests[label].get('eligible_application_paths',manifests[label].get('application_paths'))
    for label in ('os5','js5')}
write_new(R/'TASK-BINDING.json',dict(at=utc(),author=AUTHOR,candidate=str(Q),runtime=str(R),
    objective='Reconcile reviewed KA5, OS5 and JS5 executable libraries in one private candidate.',
    exact_inputs=inputs,selected=selected,base='ka5',Root_directive='FN5 exact private real-effect foundation assembly',
    merge='Only transactions.py requires combined owner logic. Keep KA5 coordinator, consume, Stop, registration and outcomes; add OS5 private invocation and same-CAS preparation fences.',
    Source_publication=False,Source_status='Root owns authorized Source290 to295 transition; no continuous live Source equality gate.',
    forbidden='No native product worker/effect, profile, Hello, CPU Set or full suite.',
    copied_product_and_tests_credit=0,default_runtime_admission='CLOSED'))
complete('discover',dict(binding=reference(R/'TASK-BINDING.json')),[],[('exact_approved_parent_inputs_and_scopes',True)])
claim('plan')
write_new(R/'CODE-SCOPE.json',dict(at=utc(),base_payloads=342,selected_overlay_paths=selected,
    surgical_merge='src/ceta/kernel/transactions.py',new_focused_test='tests/contract/test_foundation_preparation_coordination.py',
    all_other_inputs='Exact selected reviewed bytes; no whole-tree overlay.',
    controlled_gates='KA5 controlled admission/cross-kernel/interruption/timing and OS5 canonical preparation/currentness plus dependency-ready journal/codec/retention consumers.',
    full_native_gates='PENDING independent releases; original native7 and restricted no-profile case NOT_RUN here.'))
complete('plan',dict(scope=reference(R/'CODE-SCOPE.json')),[],[('finite_existing_architecture_integration',True)])
claim('implement')
copied={}
for name,row in manifests['ka5']['payloads'].items():
    source=F/'.agents/ka5-20261015'/name
    copied[name]=bytes_copy(source,Q/name,row['candidate'])
assert len(copied)==342
overlap={}
for label in ('os5','js5'):
    package=F/'.agents'/PACKAGES[label][0]
    for name in selected[label]:
        source=package/name;facts=ordinary(source)
        assert facts==manifests[label]['payloads'][name]['candidate']
        prior=ordinary(Q/name) if (Q/name).exists() else None
        if prior is not None:bytes_copy(Q/name,R/'before-images'/label/name,prior)
        bytes_copy(source,R/'approved-inputs'/label/name,facts)
        overlap.setdefault(name,[]).append(dict(package=label,before=prior,approved_input=facts,
            decision='SURGICAL_MERGE' if name=='src/ceta/kernel/transactions.py' else
                ('EXACT_REUSE' if prior and prior['sha256']==facts['sha256'] else 'SELECTED_REPLACEMENT' if prior else 'SELECTED_CREATE')))
write_new(R/'INPUTS.json',dict(at=utc(),packages=inputs,base_payloads=copied,selected=selected,overlap=overlap,
    F4_manifest=reference(f4path),F4_approved_review=f4review,KA_lineage=lineage,
    F4_parent_qualification=f4['parent_qualification'],
    F4_limits=f4['limits'],F4_unresolved_metadata=f4body.get('unresolved_fixture_metadata'),
    F4_whole_fixture_preservation_accepted=f4body.get('whole_fixture_preservation_accepted'),
    E33601=environment,python=ordinary(PY),
    prior_failures=[dict(tool_chunk='f6ebf3',exit_status=1,type='SyntaxError',effect='Read-only Python diff failed compilation before execution; unmatched closing parenthesis.'),
        dict(tool_chunk='daa6ba',exit_status=1,type='Missing guessed lifecycle.py helper',effect='Read-only lookup; actual foundation_support.py then located.')],
    Source_publication=False,no_live_Source_conservation_claim=True,
    future_source_handoff='Bind Root accepted then-current Source baseline before any publication; never overlay stale reused paths.'))
print(json.dumps(dict(actual_implement='RUNNING',sequence=6,copied=len(copied),selected={k:len(v) for k,v in selected.items()},Source_writes=False)))
