"""Seal exact cumulative-capacity repair for a separate reviewer."""
from et_support import *
inputs=json.loads((R/'SOURCE-INPUTS.json').read_text());scope=inputs['eligible_paths']
parent=F/'.agents/et1-20261014';parent_manifest=json.loads((parent/'TRANSFER-MANIFEST.json').read_text())
proof=json.loads((R/'connected-r1.json').read_text());assert proof['tests_run']==394 and proof['exit_status']==0
assert proof['expected_ids']==proof['executed_ids']==proof['stopped_ids'] and not proof['skips']
assert proof['all_fixture_stores_closed'] and not proof['new_threads_remaining']
rows={name:ordinary(Q/name) for name in sorted(proof['candidate_after'])}
assert rows==proof['candidate_before']==proof['candidate_after'] and len(rows)==316
source={name:ordinary(F/name) for name in inputs['Source290']};assert source==inputs['Source290']
conserved=json.loads((R/'input-conservation-final.json').read_text())
assert conserved['Source290_bytes_native_identities_exact'] and conserved['E3_ordinary_files_exact']==3601
measures=json.loads((R/'implementation-measures.json').read_text())
assert measures['new_source_LOC']==50 and measures['source_removed']==13 and measures['new_test_LOC']==149
assert json.loads((R/'all-source-imports.json').read_text())['count']==82
closure=json.loads((R/'parent-closure-r2.json').read_text());assert closure['exit_status']==0 and closure['all_fixture_stores_closed']
review=F/'.agents/runtime/et1-20261014/independent-review/review.json'
assert sha(review)=='51d31973e50a5092aa6e204d4ceeaf547b6f3ea1acd970a26674ba085f8ac01a'
assert json.loads(review.read_text())['decision']=='rejected'
for name,row in parent_manifest['payloads'].items():assert ordinary(parent/name)==row
actions={}
for name in scope:
    if name in source:
        image=R/'Source-before-images'/name;image.parent.mkdir(parents=True,exist_ok=True)
        fs.write_new(image,fs.read_bytes(F/name));assert sha(image)==source[name]['sha256']
        actions[name]={'action':'EXTEND','before':source[name],'logical_before_image':ordinary(image),'candidate':rows[name]}
    else:
        try:fs.lstat(F/name)
        except FileNotFoundError:pass
        else:raise AssertionError('Occupied Source CREATE '+name)
        actions[name]={'action':'CREATE','before':None,'absence_observed_by_lstat':True,'candidate':rows[name]}
assert sum(row['action']=='EXTEND' for row in actions.values())==1
write_new(R/'publication-before-images.json',{'at':utc(),'actions':actions,'Source290':source,
    'parent_before_images':{name:ordinary(R/'before-images'/name) for name in scope},
    'rule':'Only four original ET1 application paths. transactions.py is byte-exact ET1/KA1 reuse, not newly credited ET2 source. Root must join exact approved canonical owner dependencies separately; no whole-tree overlay.',
    'Source_application':False})
failed={label:reference(R/(label+'.json')) for label in ('baseline-r1','capacity-r1','targeted-r1')}
write_new(R/'PRIOR-FAILURES.json',{'at':utc(),'attempts':failed,
    'raw':{label:reference(R/(label+'.txt')) for label in failed},
    'rejected_parent_manifest':reference(parent/'TRANSFER-MANIFEST.json'),'rejected_parent_review':reference(review),
    'parent_cumulative_probe':inputs['rejected_parent_probe'],'parent_probe_result':inputs['parent_probe_result'],
    'classifications':{
        'baseline-r1':'Literal unchanged parent2methods: one cumulative-capacity failure and one exact-retry pass. All316fresh staged payloads conserved.',
        'capacity-r1':'First cumulative repair with unchanged8KiB fixture:33methods/4failures/28errors because the new cumulative limit prevents initial full outcomes and later fault/crash seams. This is retained rejected qualification, not a green run.',
        'targeted-r1':'33methods/1failure/28errors: the first larger-fixture repair compared historical attempt decision against mutable latest accounting. Preserved before-images; fixed by retaining separately decision-bound initial attempt count.',
        'current':'42focused and394connected methods pass. Literal original classAST is unchanged in separately named closure wrappers; explicit8KiB now denies before the original unsafe reconciliation. Exact retry uses declared32KiB fixture.',
        'reader':'An initial read referenced nonexistent ET1 freeze.py; inspected the actual freeze_implementation.py instead. No missing file creation or metadata-corruption claim.'},
    'failed_cut_before_images':{name:ordinary(R/'attempt-accounting-r1-before-images'/name)
        for name in ('effect_transactions.py','test_owned_cpu_outcome_transactions.py')},
    'first_capacity_measurement':reference(R/'measured-capacity-r1.json'),
    'unmodified_original_probe_class_AST_sha256':closure['literal_class_ast_sha256'],
    'original_attempts_and_sources_retained':True})
fixtures={}
root=Q/'.agents/fixtures'
if root.exists():
    for path in sorted(root.rglob('*')):
        if path.is_file():fixtures[path.relative_to(Q).as_posix()]=ordinary(path)
write_new(R/'owned-fixture-inventory.json',{'at':utc(),'candidate_fixture_members':fixtures,
    'qualification':'Only disposable candidate/runtime engineering fixtures. Closed journal evidence and real child exits are in connected proof. Generated data is excluded from normative payloads, application and LOC.'})
support=('et_support.py','bootstrap.py','run_tests.py','run_parent_probe.py','run_parent_closure.py',
    'conserve_inputs.py','conserve_final.py','self_review.py','freeze_implementation.py')
changed=[name for name,row in rows.items() if row['sha256']!=parent_manifest['payloads'][name]['sha256']]
assert set(changed)=={scope[0],scope[2],scope[3]}
manifest={'schema_version':1,'cut':RUN,'frozen_at':utc(),'author':ACTOR,'source_root':str(F),
    'candidate_root':str(Q),'runtime_root':str(R),'eligible_application_paths':scope,
    'application_actions':actions,'payload_count':316,'payloads':rows,
    'parent_manifest':reference(parent/'TRANSFER-MANIFEST.json'),'parent_rejected_review':reference(review),
    'changed_parent_payloads':changed,'parent_payloads_exact':313,
    'new_source_LOC':50,'source_removed':13,'new_test_LOC':149,'test_removed':measures['test_removed'],
    'inherited_ET1_KA1_dependencies_runtime_generated_document_oracle_LOC_credit':0,
    'measures':reference(R/'implementation-measures.json'),'self_review':reference(R/'SELF-REVIEW.json'),
    'method_conservation':reference(R/'original-method-conservation.json'),
    'qualification':reference(R/'connected-r1.json'),'qualification_raw':reference(R/'connected-r1.txt'),
    'focused':reference(R/'targeted-r2.json'),'literal_parent_closure':reference(R/'parent-closure-r2.json'),
    'tests':{'connected_unique_methods':394,'prior_unique_ids_retained':385,'new_methods':9,
        'focused_unique_methods':42,'literal_class_closure_methods':2,'failures':0,'errors':0,'skips':0,
        'actual_journals_closed':len(proof['fixture_stores']),'real_crash_exits':[71,72],'new_threads_remaining':[]},
    'actual_cumulative_measurements':proof['cumulative_observations'],
    'fixture_change':{'operation_reserve_bytes':32768,'enrollment_written_budget_bytes':65536,
        'enrollment_recovery_written_budget_bytes':32768,'enrollment_evidence_reserve_bytes':32768,
        'production_constants_or_shared_contracts_changed':False,'8KiB_atomic_overflow_retained':True},
    'accounting_units':'Cumulative committed logical canonical event/payload wires and every StoreChange value written for outcome/task/native evidence, counted once per logical write. Replacements remain charged. Internal store metadata, duplicate physical copies/index/page/WAL overhead are separate, unqualified physical obligations.',
    'Source290_before':reference(R/'SOURCE-INPUTS.json'),'before_images':reference(R/'publication-before-images.json'),
    'input_conservation':reference(R/'input-conservation-final.json'),'prior_failures':reference(R/'PRIOR-FAILURES.json'),
    'owned_fixture_inventory':reference(R/'owned-fixture-inventory.json'),'imports':reference(R/'all-source-imports.json'),
    'source_modules':82,'review_support':{name:ordinary(R/name) for name in support},
    'status':'EXECUTABLE_CUMULATIVE_REPAIR_AWAITING_DISTINCT_REVIEW',
    'Source_published':False,'runtime_activation':False,'genuine_native_effect_invocation':False,
    'positive_native_provider':'CONTROLLED_FIXTURES_ONLY',
    'APIs':parent_manifest['APIs'],
    'remaining':['Distinct review and Root guarded integration have not occurred.',
        'Canonical native outcome/currentness producer, independent observer and real effect/authenticated runtime composition remain unqualified and default closed.',
        'An8KiB request can hold a durable attempt but cannot fit the tested complete outcome; this attempt is never permission to dispatch. Real effect composition must establish sufficient bounded outcome capacity before actual admission.',
        'Physical SQLite/WAL/free-space/power-loss behavior is not guaranteed by logical serialized evidence accounting.'],
    'reviewer_guidance':'Use actual separate READY review claim; preserve every frozen payload and preexisting fixture. Initialize canonical SQLite loader before test discovery. Copy/relocate only reviewer support roots into own scope, keep ceta imports underQ. Run original385IDs+9new, literal2closure ASTs, exact8KiB overflow and cumulative retained SQL-write equality. No Source/E3/native effects/Hello/profile changes.'}
write_new(Q/'TRANSFER-MANIFEST.json',manifest)
write_new(R/'HANDOFF.json',{'at':utc(),'manifest':reference(Q/'TRANSFER-MANIFEST.json'),
    'tests':manifest['tests'],'eligible_paths':scope,'new_source_LOC':50,'source_removed':13,'new_test_LOC':149,
    'Source_application':False,'distinct_review_required':True,'remaining':manifest['remaining']})
def command(name,*args):return {'command':subprocess.list2cmdline([str(PY),'-B','-X','utf8',str(R/name),*args]),'exit_status':0}
complete('implement',{'manifest':reference(Q/'TRANSFER-MANIFEST.json'),'handoff':reference(R/'HANDOFF.json'),
    'qualification':manifest['qualification'],'literal_parent_closure':manifest['literal_parent_closure'],
    'prior_failures':manifest['prior_failures'],'new_source_LOC':50,'source_removed':13,'new_test_LOC':149,
    'Source_application':False,'genuine_native_effect_invocation':False},
    [command('run_tests.py','connected-r1','connected'),command('run_parent_closure.py','parent-closure-r2'),
     command('conserve_final.py'),command('self_review.py')],
    [('394unique original385plus9 methods pass with no failures/errors/skips; all observed journals closed and crash71/72 retained',True),
     ('Exact canonical cumulative byte equality, finite overflow, restart, CAS concurrency, tamper rejection and exact-retry no-write verified',True),
     ('32original test methodASTs exact; restoration budget fixture amendment explicit and shared contracts/delegates unchanged',True),
     ('Source290 and3601E3 ordinary bytes/native identities/membership retained; no native effects or activation',True),
     ('Frozen exact author cut awaits independent review; prior failed original and repaired attempts preserved',True)])
print(json.dumps({'manifest':reference(Q/'TRANSFER-MANIFEST.json'),'implement':reference(R/'implement.json'),
    'payloads':316,'tests':394,'source_added':50,'source_removed':13,'test_added':149}))
