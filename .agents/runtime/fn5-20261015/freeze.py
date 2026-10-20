"""Freeze the private joined library, preserving every open acceptance gate."""
from foundation_support import *
import ast,collections,difflib

v=read(R/'INPUTS.json');assembly=read(R/'ASSEMBLY.json');qualification=read(R/'QUALIFICATION.json')
inventory=read(R/'TEST-METHOD-INVENTORY-r2.json');ownership=read(R/'FILE-OWNERSHIP.json')
assert len(assembly['payloads'])==351 and not (Q/'TRANSFER-MANIFEST.json').exists()
assert qualification['E33601_ordinary_file_membership_bytes_native_identity_exact']
assert all(row['ordinary_native_identity_exact'] for row in qualification['parent_after'].values())
cohorts={};all_ids=[]
for label,count in (('controlled-r1',82),('preparation-r1',218),('consumers-r2',94),('joined-r2',8),('outcomes-r1',53)):
    body=read(R/label/'RESULT.json')
    assert body['tests_run']==count and body['failures']==body['errors']==body['skips']==body['exit_status']==0
    assert body['expected_ids']==body['executed_ids']==body['stopped_ids']
    assert body['candidate_before']==body['candidate_after']==assembly['payloads']
    assert body['remaining_threads']==[]
    all_ids.extend(body['executed_ids'])
    cohorts[label]=dict(result=reference(R/label/'RESULT.json'),raw=reference(R/label/'tests.txt'),
        count=count,executed_ids=body['executed_ids'])
leaf=qualification['contract_leaf'];assert leaf['tests_run']==3 and leaf['exit_status']==0
all_ids.extend(leaf['executed_ids']);assert len(all_ids)==len(set(all_ids))==458
supervision=read(R/'supervision-controlled-r1/SUPERVISION-RESULT.json')
assert supervision['exit_status']==0 and supervision['primary'] is None
assert supervision['candidate_and_six_source_files_preserved'] and supervision['record']['child_exit']==0
assert all(value is True for value in supervision['record']['native_owner_after'].values())
controlled=read(R/'controlled-r1/RESULT.json')
assert controlled['mutation_registry_empty'] and controlled['retained_pending_pairs_exact']
assert len(controlled['retained_fixture_custody'])==11 and controlled['all_journals_closed']
assert controlled['forbidden_native_constructor_calls']==[] and controlled['native_admission_receipts']==[]
for label in ('preparation-r1','joined-r2','outcomes-r1'):
    body=read(R/label/'RESULT.json');assert body.get('forbidden_calls',[])==[]
consumer=read(R/'consumers-r2/RESULT.json')
assert consumer['forbidden_native_calls']==[] and consumer['constructor_native_connections_closed']
assert consumer['postconstruction_native_connections_closed']

base=v['base_payloads'];final={n:ordinary(Q/n) for n in assembly['payloads']}
assert final==assembly['payloads']
changed=[n for n in final if n not in base or final[n]['sha256']!=base[n]['sha256']]
created=[n for n in final if n not in base];extended=[n for n in changed if n in base]
physical_deltas={}
for name in extended:
    old=F/'.agents/ka5-20261015'/name
    diff=list(difflib.unified_diff(old.read_text(encoding='utf8').splitlines(True),
        (Q/name).read_text(encoding='utf8').splitlines(True),fromfile='KA5/'+name,tofile='FN5/'+name))
    path=R/'diffs'/(name+'.diff');path.parent.mkdir(parents=True,exist_ok=True)
    fs.write_new(path,''.join(diff).encode('utf8'))
    physical_deltas[name]=dict(diff=reference(path),uncredited_text_lines_added=sum(line.startswith('+') and not line.startswith('+++') for line in diff),
        uncredited_text_lines_removed=sum(line.startswith('-') and not line.startswith('---') for line in diff),new_product_authorship=0)

# Match method ranges to their exact approved owner, rather than calling all
# of the assembled transactions file newly written implementation.
def class_methods(path):
    tree=ast.parse(Path(path).read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='KernelTransactions')
    return {n.name:n for n in cls.body if isinstance(n,ast.FunctionDef)}
merged=class_methods(Q/'src/ceta/kernel/transactions.py')
a=class_methods(F/'.agents/ka5-20261015/src/ceta/kernel/transactions.py')
b=class_methods(F/'.agents/os5-20261015/src/ceta/kernel/transactions.py')
method_rows={}
for name,node in merged.items():
    if name=='__init__':
        origin='Ordered composition: KA5 initialization including CPU coordinator, then exact OS5 preparation binding fields.'
    elif name in ('prepare','_prepare'):
        origin='Exact OS5 body; public prepare retains the exact KA5 _coordinated decorator.'
        assert ast.dump(ast.Module(body=node.body,type_ignores=[]),include_attributes=False)==ast.dump(ast.Module(body=b[name].body,type_ignores=[]),include_attributes=False)
    else:
        origin='Exact KA5 AST, including all decorators, signature and body.'
        assert ast.dump(node,include_attributes=False)==ast.dump(a[name],include_attributes=False)
    method_rows[name]=dict(first_line=min([node.lineno]+[x.lineno for x in node.decorator_list]),
        last_line=node.end_lineno,origin=origin,new_implementation_credit=0)
write_new(R/'TRANSACTION-LINE-OWNERSHIP.json',dict(at=utc(),path='src/ceta/kernel/transactions.py',
    merged=reference(Q/'src/ceta/kernel/transactions.py'),methods=method_rows,
    constructor_order=assembly['constructor_order'],
    exact_OS5_helpers=['_PreparationInvocation','_preparation_failure'],
    public_signatures_preserved=True,no_new_authority_store_or_effect_boundary=True,new_implementation_credit=0))

prior=qualification['prior_failures']
write_new(R/'PRIOR-ATTEMPTS.json',dict(at=utc(),failures=prior,
    inherited_parent_failures='Exact parent manifests, KA5 failed native attempt, F4 interrupted r4 and failed JS3/JS4/JS5 publication wrappers remain immutable. Component source adoption is not acceptance of those tools or later Source publication.',
    original_consumer94_pass_raw=reference(R/'consumers-r1/tests.txt'),
    original_joined8_one_wrong_state_oracle=reference(R/'joined-r1/RESULT.json'),
    original_inventory_failure=reference(R/'prior-attempts/TEST-METHOD-INVENTORY-r1.json'),
    original_assembly_reader=reference(R/'prior-attempts/assemble-r1.py'),
    original_consumer_reader=reference(R/'prior-attempts/run_consumers-r1.py'),
    original_joined_oracle=reference(R/'prior-attempts/test_preparation_coordination-r1.py')))
limits=[
    'Private integrated executable libraries only. No active Source publication, Source baseline acceptance or whole-product completion is claimed.',
    'Root retains the Source transition. CT4 Source290 remains the last accepted baseline at handoff; any future publication must authenticate then-current accepted Source and preserve its forward changes.',
    'The JS5 selected product code is reviewed; its original publication wrapper failed before Source replacement. No JS5/JS6 publication or new full result is relabelled as FN5 acceptance.',
    '458 actual unique selected methods passed with zero failures/errors/skips:82 admission,218 preparation,94 journal/codec/retention,8 new runtime coordination controls,53 outcomes and3 leaf checks. This is not the full joined suite.',
    'The AST inventory maps2327 local test methods; it is neither full discovery nor execution. All parent bodies are conserved except one exact approved stronger JS5 projection/poisoned-journal successor mapping with the same ID.',
    'Original seven native CPU methods, native owner-session qualification, actual genuine approval, profile/Hello/CPU Set, native product worker and the original restricted no-profile case were NOT_RUN here.',
    'One original SQLite crash-child method is retained but excluded from the selected no-child outcome cohort; its ID and reason are explicit. It remains a future bounded/full gate.',
    'Controlled native observation, approval, target and physical-capacity providers are not live production authentication, native enforcement, isolated execution or physical outcome-storage guarantees.',
    'Public runtime admission and the selected native owner admission/revocation defaults remain CLOSED. Successful preparation alone creates no execution permission.',
    'Canonical cumulative logical evidence-byte accounting is tested; physical SQLite/WAL storage reservation is not thereby qualified.',
    'The82 controlled admission methods deliberately retain11 pending controlled owner/store/lease custody pairs with fixture locks unlocked. This is not empty liveness or successful product cleanup. Mutation registrations retire.',
    'The benign bounded admission test interpreter exited0 with all five captured native custody flags closed. No native product cohort ran in it.',
    'General journal closed flags and independently probed constructor/postconstruction native connection retirement are distinct evidence. Positive fixture native facts remain controlled.',
    'All351 candidate payloads, three frozen parent ordinary-file maps and E33601 ordinary membership/bytes/native identities were conserved. Whole directory metadata equality is not claimed.',
    'F4 preexisting109 directory-attribute differences, interrupted-r4 historical custody uncertainty and NC3 historical command-provenance correction remain unwaived and bound through lineage.',
    'The one previously reviewed nonnative admission arithmetic method retains its explicit deterministic elapsed source; it is not native or natural-time qualification.',
    'Copied/reconciled/integrated source and tests receive zero new product LOC. The120 meaningful new runtime-only test lines implement eight integration controls; there is no new normative product/test source authorship.',
    'This writer authored the component dependencies. FN5 assembly and conflict resolution require a named distinct reviewer before substantial acceptance.'
]
write_new(R/'SELF-REVIEW.json',dict(at=utc(),author=AUTHOR,independent_review=False,
    inspected=['All selected approved source paths and actual callers','Exact transactions line/method/decorator merge and constructor publication order',
        'Same-CAS enrollment/approval/request-index/challenge/nonce preparation guards without SQL or native work inside writer',
        'Canonical coordinated consume, Stop/revoke, registration, cumulative outcome/reconciliation and no repeated native effect',
        'Exact original test ASTs and single stronger approved projection transition','All458 executed IDs/raw logs, retained pending custody and actual benign process retirement',
        'Parent and candidate ordinary-file/native hashes, actual E3 membership, Python compilation and unchanged contract leaf denials'],
    line_ownership=reference(R/'TRANSACTION-LINE-OWNERSHIP.json'),approved_test_mapping=reference(R/'APPROVED-TEST-CONFLICT-RESOLUTION.json'),
    limits=limits,Source_publication=False))
scripts={name:sha(R/name) for name in ('foundation_support.py','bootstrap.py','assemble.py','finalize_assembly.py','prepare_runners.py',
    'run_controlled.py','supervise_controlled.py','bounded_custody.py','run_preparation.py','run_consumers.py',
    'run_joined_controls.py','test_preparation_coordination.py','run_outcomes.py','inventory-r2.py','qualify.py','freeze.py','release_author.py')}
payloads={n:dict(candidate=row,base_KA5=base.get(n),classification='CREATE' if n in created else 'EXTEND' if n in extended else 'REUSE',
    source_provenance=ownership['paths'][n]['origin'],integration_and_copy_credit=0,
    active_Source_action='FUTURE_ACCEPTED_BASELINE_AND_BEFORE_IMAGE_BINDING_REQUIRED',Source_publication_authorized=False)
    for n,row in final.items()}
write_new(Q/'TRANSFER-MANIFEST.json',dict(schema_version=1,run_id=RUN,author=AUTHOR,recorded_at=utc(),
    source_root=str(F),candidate_root=str(Q),runtime_root=str(R),scope='Private joined real-effect executable library integration',
    inputs=reference(R/'INPUTS.json'),packages=v['packages'],F4_manifest=v['F4_manifest'],F4_approved_review=v['F4_approved_review'],KA_lineage=v['KA_lineage'],
    payloads=payloads,payload_count=351,base_payload_count=342,REUSE=len(final)-len(changed),EXTEND=len(extended),CREATE=len(created),
    selected_vs_KA5=changed,approved_overlay_paths=v['selected'],OS5_test_scope_addition=reference(R/'SCOPE-ADDITION-OS5-TESTS.json'),
    auxiliaries=assembly['auxiliaries'],assembly=reference(R/'ASSEMBLY.json'),ownership=reference(R/'FILE-OWNERSHIP.json'),
    line_ownership=reference(R/'TRANSACTION-LINE-OWNERSHIP.json'),physical_diff_excluding_credit=physical_deltas,
    test_inventory=reference(R/'TEST-METHOD-INVENTORY-r2.json'),approved_test_successor_mapping=reference(R/'APPROVED-TEST-CONFLICT-RESOLUTION.json'),
    selected_cohorts=cohorts,contract_leaf=leaf,executed_unique_methods=458,executed_ids=all_ids,
    retained_pending_controlled_custody=controlled['retained_fixture_custody'],benign_supervision=reference(R/'supervision-controlled-r1/SUPERVISION-RESULT.json'),
    outcome_deferred_ids=read(R/'outcomes-r1/RESULT.json')['explicit_targeted_exclusions'],
    qualification=reference(R/'QUALIFICATION.json'),prior_failures=reference(R/'PRIOR-ATTEMPTS.json'),self_review=reference(R/'SELF-REVIEW.json'),
    meaningful_LOC=qualification['meaningful_LOC'],new_product_LOC=0,new_normative_test_LOC=0,new_runtime_test_LOC=120,
    scripts=scripts,limits=limits,Source_publication=False,full_joined_gate_complete=False,native_admission_qualified=False,
    genuine_owner_isolation_outcome_gates_complete=False,activation_ready=False))
print(json.dumps(dict(manifest=reference(Q/'TRANSFER-MANIFEST.json'),payloads=351,REUSE=len(final)-len(changed),EXTEND=len(extended),CREATE=len(created),
    executed_unique=458,new_product_LOC=0,new_runtime_test_LOC=120)))
