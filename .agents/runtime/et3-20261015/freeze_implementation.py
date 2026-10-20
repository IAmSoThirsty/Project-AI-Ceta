"""Freeze exact author evidence and complete one actual implement claim."""
from et_support import *

inputs=json.loads((R/'SOURCE-INPUTS.json').read_text())
stage=json.loads((R/'STAGED-INPUTS.json').read_text())
parent=F/'.agents/et2-20261014'
scope=inputs['eligible_paths']
proof=json.loads((R/'connected-r1.json').read_text())
assert proof['tests_run'] == proof['unique_methods'] == 406 and proof['exit_status'] == 0
assert proof['expected_ids'] == proof['executed_ids'] == proof['stopped_ids']
assert not proof['skips'] and not proof['new_threads_remaining']
assert all(row['closed'] for row in proof['fixture_stores'])
targeted=json.loads((R/'targeted-r1.json').read_text())
assert targeted['tests_run'] == 12 and targeted['exit_status'] == 0
native=json.loads((R/'native-custody-r1/RESULT.json').read_text())
assert native['exit_status'] == 0 and native['all_recorded_custody_closed'] and len(native['native_lifetimes']) == 6
assert all(type(row['creation_time']) is int and row['creation_time'] > 0 for row in native['native_lifetimes'])
self_review=json.loads((R/'SELF-REVIEW.json').read_text())
assert self_review['only_changed_code_definition'] == ['KernelEffectTransactions.record']
assert self_review['original_test_file_bytes_exact'] and len(self_review['new_test_methods']) == 12
rows={name:ordinary(Q/name) for name in sorted(proof['candidate_after'])}
assert rows == proof['candidate_before'] == proof['candidate_after'] and len(rows) == 317
source={name:ordinary(F/name) for name in inputs['Source290']}
assert source == inputs['Source290'] and len(source) == 290
for name, facts in stage['payloads'].items():
    assert ordinary(parent/name)['sha256'] == facts['sha256']
    if name not in scope: assert ordinary(Q/name) == facts

environment=json.loads((R/'environment-final.json').read_text())
root=PY.parent.parent
actual={name:ordinary(root/name) for name in environment['ordinary_files']}
assert actual == environment['ordinary_files'] and len(actual) == 3601
write_new(R/'environment-after-qualification.json', {'at':utc(),'ordinary_files':actual,
    'previous':reference(R/'environment-final.json'),'file_bytes_native_identities_exact':True,
    'membership':'Full membership was checked in environment-final; this final pass rechecks every member, not full directory membership.'})
actions={}
for name in scope:
    if name in source:
        saved=R/'Source-before-images'/name
        saved.parent.mkdir(parents=True,exist_ok=True)
        fs.write_new(saved,fs.read_bytes(F/name))
        actions[name]={'action':'EXTEND','before':source[name],'before_image':ordinary(saved),'candidate':rows[name]}
    else:
        try:fs.lstat(F/name)
        except FileNotFoundError:pass
        else:raise AssertionError('Occupied Source CREATE: '+name)
        actions[name]={'action':'CREATE','before':None,'absence_observed_by_lstat':True,'candidate':rows[name]}
write_new(R/'publication-before-images.json', {'at':utc(),'actions':actions,
    'rule':'Join these three approved successor paths with the accepted ET2 dependencies; no whole-tree application or competing transaction owner.',
    'Source_application':False})
measures=json.loads((R/'implementation-measures.json').read_text())
manifest={'schema_version':1,'cut':RUN,'frozen_at':utc(),'author':ACTOR,
    'source_root':str(F),'candidate_root':str(Q),'runtime_root':str(R),
    'eligible_application_paths':scope,'application_actions':actions,
    'payload_count':317,'payloads':rows,'parent_manifest':inputs['parent_manifest'],
    'parent_review':inputs['parent_review'],'readiness_audit':inputs['readiness_audit'],
    'changed_parent_payloads':self_review['changed_parent_paths'],
    'parent_payloads_exact':314,'new_test_path':scope[1],
    'new_source_LOC':measures['new_source_LOC'],'source_removed':measures['source_removed'],
    'new_test_LOC':measures['new_test_LOC'],'new_methods':12,
    'inherited_source_dependencies_evidence_documents_support_LOC_credit':0,
    'qualification':reference(R/'connected-r1.json'),'qualification_raw':reference(R/'connected-r1.txt'),
    'focused':reference(R/'targeted-r1.json'),'native_custody':reference(R/'native-custody-r1/RESULT.json'),
    'self_review':reference(R/'SELF-REVIEW.json'),'implementation_measures':reference(R/'implementation-measures.json'),
    'Source290':reference(R/'SOURCE-INPUTS.json'),'conservation':reference(R/'input-conservation-final.json'),
    'E3_after':reference(R/'environment-after-qualification.json'),'before_images':reference(R/'publication-before-images.json'),
    'prior_failure':reference(R/'before-r1.json'),'prior_failure_raw':reference(R/'before-r1.txt'),
    'before_test_adjustment':reference(R/'before-test-adjustment/BINDING.json'),
    'tests':{'unique_connected_methods':406,'unchanged_original_ids':394,'new_methods':12,
        'focused_methods':12,'failures':0,'errors':0,'skips':0,
        'observed_journals_closed':len(proof['fixture_stores']),
        'separate_native_methods':3,'separate_native_lifetimes_retired':6,
        'main406_native_PID_capture':'Not instrumented; separate3 subset has streamed exact identities. No historical backfill.',
        'real_crash_observations':proof['crash_observations']},
    'APIs':json.loads((parent/'TRANSFER-MANIFEST.json').read_text())['APIs'],
    'positive_native_provenance':'CONTROLLED_FIXTURES_ONLY',
    'runtime_activation':False,'genuine_native_effect_invocation':False,'Source_published':False,
    'status':'EXECUTABLE_RECONCILIATION_REPAIR_AWAITING_DISTINCT_REVIEW',
    'remaining':['Distinct review and joined acceptance are pending.',
        'Actual native producer/observer owner integration remains unqualified; typed data and matching image never authorize an observation.',
        'New observer-controller instance after restart must establish sequence continuity through canonical retained evidence; this cut provides no controller restart owner.',
        'Physical storage capacity, genuine owner authentication and retained native dispatch remain separate required implementation/qualification.'],
    'review_support':{name:ordinary(R/name) for name in ('et_support.py','run_tests.py','self_review.py','conserve_inputs.py','run_native_custody.py')},
    'reviewer_guidance':'Obtain actual own READY review claim. Preserve317 normative payloads and fixtures. Run12new+394original connectedIDs in own runtime fixture paths and unchanged3 native custody cases. Check exact owner predicate/transaction accounting and old test bytes. No Source/profile/Hello/native CPU mutation.'}
write_new(Q/'TRANSFER-MANIFEST.json',manifest)
write_new(R/'HANDOFF.json',{'at':utc(),'manifest':reference(Q/'TRANSFER-MANIFEST.json'),
    'eligible_paths':scope,'new_source_LOC':measures['new_source_LOC'],
    'source_removed':measures['source_removed'],'new_test_LOC':measures['new_test_LOC'],
    'tests':manifest['tests'],'remaining':manifest['remaining'],'distinct_review_required':True,'Source_application':False})
def command(script,*args):
    return {'command':subprocess.list2cmdline([str(PY),'-B','-X','utf8',str(R/script),*args]),'exit_status':0}
complete('implement',{'manifest':reference(Q/'TRANSFER-MANIFEST.json'),
    'handoff':reference(R/'HANDOFF.json'),'qualification':manifest['qualification'],
    'native_custody':manifest['native_custody'],'Source_application':False,
    'new_source_LOC':measures['new_source_LOC'],'new_test_LOC':measures['new_test_LOC']},
    [command('run_tests.py','connected-r1','connected'),command('run_native_custody.py'),
     command('self_review.py'),command('conserve_inputs.py')],
    [('406exact IDs including394 unchanged+12new pass with0 failures/errors/skips and all observed journals closed',True),
     ('Fresh-child reconciliation preserves actual canonical evidence/accounting, anti-replay and captured native-owner guard',True),
     ('Separate3 native cases capture6 actual retired process lifetimes without CPU effects or profile operations',True),
     ('Source290,314 reused dependencies and3601 installed E3 ordinary files retain exact bytes/native identities',True),
     ('Prior failed cut/test-fixture mismatch preserved; no native production integration or Source acceptance claimed',True)])
print(json.dumps({'manifest':reference(Q/'TRANSFER-MANIFEST.json'),
    'implement':reference(R/'implement.json'),'tests':406,'new_source_LOC':measures['new_source_LOC'],
    'new_test_LOC':measures['new_test_LOC']}))
