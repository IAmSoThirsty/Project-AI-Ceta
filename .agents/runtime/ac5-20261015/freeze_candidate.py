"""Freeze custody-only successor and release actual author implement claim."""
from ac_support import *
inputs=json.loads((R/'SOURCE-INPUTS.json').read_text());staged=json.loads((R/'STAGED-INPUTS.json').read_text())
proof=json.loads((R/'focused-r1/RESULT.json').read_text());closure=json.loads((R/'literal-closure-r2.json').read_text())
assert proof['tests_run']==26 and proof['exit_status']==0 and closure['tests_run']==2 and closure['exit_status']==0
assert proof['expected_ids']==proof['executed_ids']==proof['stopped_ids']
assert not proof['forbidden_calls'] and not proof['new_threads'] and not any(proof['pending_native_resources'])
rows={name:ordinary(Q/name) for name in staged['payloads']}
assert rows==proof['candidate_before']==proof['candidate_after']==closure['candidate_after'] and len(rows)==295
conservation=json.loads((R/'input-conservation.json').read_text())
assert conservation['Source290_bytes_native_identities_exact'] and conservation['E3_ordinary_files_exact']==3601
source={name:ordinary(F/name) for name in inputs['Source290']};assert source==inputs['Source290']
parent=F/'.agents/ac4-20261015';parent_manifest=json.loads((parent/'TRANSFER-MANIFEST.json').read_text())
for name,row in parent_manifest['payloads'].items():assert ordinary(parent/name)==row
changed=[name for name,row in rows.items() if row['sha256']!=parent_manifest['payloads'][name]['sha256']]
assert set(changed)==set(inputs['eligible_author_paths'])
measures=json.loads((R/'implementation-measures.json').read_text())
assert measures['new_source_LOC']==9 and measures['source_removed']==5 and measures['new_test_LOC']==92
actions={}
for name in inputs['eligible_application_paths']:
    if name in source:
        image=R/'Source-before-images'/name;image.parent.mkdir(parents=True,exist_ok=True)
        fs.write_new(image,fs.read_bytes(F/name))
        actions[name]={'action':'EXTEND','before':source[name],'logical_before_image':ordinary(image),'candidate':rows[name]}
    else:
        try:fs.lstat(F/name)
        except FileNotFoundError:pass
        else:raise AssertionError('Occupied Source create '+name)
        actions[name]={'action':'CREATE','before':None,'absence_observed_by_lstat':True,'candidate':rows[name]}
write_new(R/'publication-before-images.json',{'at':utc(),'actions':actions,
    'author_parent_before_images':{name:ordinary(R/'before-images'/name) for name in inputs['eligible_author_paths']},
    'rule':'Only five inherited worker application paths may later join; only three are changed by AC5. No whole-tree overlay or reused LOC credit.',
    'Source_application':False})
write_new(R/'PRIOR-FAILURES.json',{'at':utc(),'rejected_parent_manifest':inputs['parent_manifest'],
    'rejected_parent_review':inputs['parent_rejected_review'],'literal_parent_probe':inputs['exact_hostile_probe'],
    'baseline':reference(R/'baseline-r1.json'),'baseline_raw':reference(R/'baseline-r1.txt'),
    'classification':'Exact frozen native classAST reproduced2missing-custody failures,0errors, with exact primary identity and all owned native resources retired. Fresh successor fixes canonical custody; original parent/evidence unchanged.',
    'first_closure':reference(R/'literal-closure-r1.json'),'final_same_cut_closure':reference(R/'literal-closure-r2.json'),
    'baseline_and_final_class_AST_exact':True,'additional_failed_author_attempts':[]})
support=('ac_support.py','bootstrap.py','run_literal_probe.py','run_diagnostics.py','conserve_inputs.py','self_review.py','freeze_candidate.py')
manifest={'schema_version':1,'cut':RUN,'author':ACTOR,'frozen_at':utc(),'source_root':str(F),
    'candidate_root':str(Q),'runtime_root':str(R),'parent_manifest':inputs['parent_manifest'],
    'parent_rejected_review':inputs['parent_rejected_review'],'payload_count':295,'payloads':rows,
    'eligible_author_paths':inputs['eligible_author_paths'],'eligible_application_paths':inputs['eligible_application_paths'],
    'application_actions':actions,'changed_parent_payloads':changed,'unchanged_parent_payloads':292,
    'qualification':reference(R/'focused-r1/RESULT.json'),'literal_closure':reference(R/'literal-closure-r2.json'),
    'self_review':reference(R/'SELF-REVIEW.json'),'measures':reference(R/'implementation-measures.json'),
    'new_source_LOC':9,'source_removed':5,'new_test_LOC':92,'test_removed':0,
    'inherited_runtime_generated_document_oracle_LOC_credit':0,
    'tests':{'original22_unique_IDs_retained':True,'cohort_unique_methods':26,'new_methods':4,
        'original15_method_ASTs_exact':True,'literal_native_probe_methods':2,'literal_class_AST_unchanged':True,
        'cohort_native_current_token_cases':4,'final_literal_native_cases':2,'failures':0,'errors':0,'skips':0,
        'retirement_through_exposed_cleanup':True,'profile_operations':[],'worker_launches':[],
        'parent_full_launch_cohort_executed':False},
    'scope_guards':['All module AST outside _attach_cleanup exact, including native predicates/query/launch order.',
        'All original diagnostic15test methods, original isolated-worker tests and Rust bytes exact.',
        'Actual token/SID resources retired; no pending native resource/new thread/forbidden API call.'],
    'before_images':reference(R/'publication-before-images.json'),'source_inputs':reference(R/'SOURCE-INPUTS.json'),
    'input_conservation':reference(R/'input-conservation.json'),'prior_failures':reference(R/'PRIOR-FAILURES.json'),
    'review_support':{name:ordinary(R/name) for name in support},
    'status':'CUSTODY_REPAIR_AWAITING_DISTINCT_REVIEW','Source_published':False,'positive_isolation_qualified':False,
    'activation_ready':False,'profile_operations':[],'worker_launches':[],'native_CPU_effects':[],
    'remaining':['Root distinct review and guarded integration remain pending.',
        'Historical AC3 rejected token values remain unknown; no positive isolation/profile/worker launch qualified here.',
        'Existing unanchored:2native-regression specificity issue remains separately recorded; no launch was executed here.'],
    'reviewer_guidance':'Claim actual READY review. Rebind runtime outputs only, keep all ceta imports inQ. Run original22+4new, literal frozen nativeclass2; verify Source/E3 and all295frozen payloads. No profile/worker/Source/E3 operations. New native tests must recover through the exposed exact cleanup, not a private external owner.'}
write_new(Q/'TRANSFER-MANIFEST.json',manifest)
write_new(R/'HANDOFF.json',{'at':utc(),'manifest':reference(Q/'TRANSFER-MANIFEST.json'),'tests':manifest['tests'],
    'eligible_author_paths':manifest['eligible_author_paths'],'new_source_LOC':9,'source_removed':5,'new_test_LOC':92,
    'Source_application':False,'distinct_review_required':True,'remaining':manifest['remaining']})
def command(name,*args):return {'command':subprocess.list2cmdline([str(PY),'-B','-X','utf8',str(R/name),*args]),'exit_status':0}
complete('implement',{'manifest':reference(Q/'TRANSFER-MANIFEST.json'),'handoff':reference(R/'HANDOFF.json'),
    'qualification':manifest['qualification'],'literal_closure':manifest['literal_closure'],
    'prior_failures':manifest['prior_failures'],'new_source_LOC':9,'source_removed':5,'new_test_LOC':92,
    'Source_application':False,'positive_isolation_qualified':False},
    [command('run_diagnostics.py','focused-r1'),command('run_literal_probe.py','literal-closure-r2'),
        command('conserve_inputs.py'),command('self_review.py')],
    [('Original22plus4 methods and unchanged literalnative2 pass with no failures/errors/skips',True),
     ('Canonical exact cleanup custody survives hooks; actual native resources retire through exposed owner, including nested retry failure',True),
     ('Original15methodASTs, all other production AST, native predicates/launch/Rust bytes unchanged',True),
     ('Source290 and3601E3 ordinary bytes/native identities retained; no profile/worker/CPU effect or activation',True),
     ('Frozen precise successor awaits separate Root review; parent2failure evidence retained',True)])
print(json.dumps({'manifest':reference(Q/'TRANSFER-MANIFEST.json'),'implement':reference(R/'implement.json'),
    'tests':26,'literal':2,'source_added':9,'source_removed':5,'test_added':92}))
