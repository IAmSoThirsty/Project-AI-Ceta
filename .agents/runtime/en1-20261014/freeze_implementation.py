from en1_support import *

eligible=['src/ceta/contracts/owner_enrollment.py','tests/contract/test_owner_enrollment.py','contracts/OWNER_ENROLLMENT_V1.md']
inputs=json.loads((R/'SOURCE-INPUTS.json').read_text());final=json.loads((R/'final-r5.json').read_text())
qualification=json.loads((R/'QUALIFICATION-FINAL.json').read_text())
measures=json.loads((R/'LOC-FINAL.json').read_text())
assert qualification['exit_status']==final['exit_status']==0
assert final['tests_run']==82 and final['new_cases']==35 and final['retained_cases']==47
assert all(ordinary(Q/name)==row for name,row in final['candidate_after'].items())
assert {name:ordinary(P/name) for name in inputs['current290']}==inputs['current290']
assert all(not (P/name).exists() for name in eligible)
assert ordinary(PY)==inputs['interpreter']
sys.path.insert(0,str(Q/'src'))
from ceta.contracts import owner_enrollment, real_effect, workload_throttling
imports={module.__name__:ordinary(Path(module.__file__)) for module in (owner_enrollment,real_effect,workload_throttling)}
assert imports['ceta.contracts.owner_enrollment']['path']==str(Q/eligible[0])
for name in inputs['dependencies']:
    assert sha(Q/name)==inputs['dependencies'][name]['source']['sha256']
write_new(R/'DEPENDENCY-IMPORTS.json',{'recorded_at':utc(),'actual_imports':imports,
    'dependency_state':'UNCREDITED_TYPED_BYTES_ONLY','native_acceptance_borrowed':False})
write_new(R/'SELF-REVIEW.json',{'recorded_at':utc(),'actor':ACTOR,'decision':'AUTHOR_SELF_REVIEW_COMPLETE',
    'independent_review':False,'files_personally_read':eligible,
    'requirements':['RE-T04 controlled bootstrap DATA binding','RE-T05 exact display/native transcript DATA binding',
                    'RE-T06 canonical enrollment transition input only; no transition implemented here'],
    'verified':['Fixed profile/one worker/one cap and one restore with separate approvals encoded',
        'Canonical volume-GUID path syntax plus full128-bit file ID/64-bit volume ID data',
        'Exact history.sqlite3 designated root/kind/volume/distinct ID binding',
        'Bounded native owner/process/token facts and exact expected request equality',
        'Complete display/input/transcript separate domains and exact nested canonical shapes',
        'Finite authority/recovery/resource/evidence limits and residual cap reserve',
        'Existing temporal rules with both ClockSample records revalidated at this boundary',
        'Original47 exact bytes/ASTs;35 new deterministic methods; four-thread32-request concurrency'],
    'prior_failures':reference(R/'PRIOR-ATTEMPTS-FINAL.json'),'qualification':reference(R/'QUALIFICATION-FINAL.json'),
    'conservation':reference(R/'CONSERVATION-FINAL.json'),'API':reference(R/'EXPORTED-API-FINAL.json'),
    'limits':['DATA_ONLY cannot authenticate origin, native root/token observations or genuine human ceremony',
        'No single-use consumption/grant/epoch transition; existing canonical owner must commit those',
        'Expected request and clocks must originate in captured canonical/native owners',
        'No actual Hello/profile/filesystem probe or native enrollment performed',
        'Two exact dependency sources uncredited; independent reconciliation required before Source publication'],
    'source_published':False})
payloads=[]
for name,row in sorted(inputs['current290'].items()):
    current=ordinary(Q/name);assert current['sha256']==row['sha256']
    payloads.append({'relative_path':name,'repository_relative_path':name,'classification':'REUSE',
        'candidate_sha256':current['sha256'],'candidate_native_identity':current['native_identity'],
        'source_sha256':row['sha256'],'source_native_identity':row['native_identity'],'new_LOC_credit':0})
for name,record in inputs['dependencies'].items():
    current=ordinary(Q/name)
    payloads.append({'relative_path':name,'repository_relative_path':name,'classification':'UNCREDITED_TYPED_DEPENDENCY',
        'candidate_sha256':current['sha256'],'candidate_native_identity':current['native_identity'],
        'source':record['source'],'new_LOC_credit':0,'acceptance_borrowed':False})
for name in eligible:
    current=ordinary(Q/name)
    payloads.append({'relative_path':name,'repository_relative_path':name,'classification':'CREATE',
        'candidate_sha256':current['sha256'],'candidate_native_identity':current['native_identity'],
        'active_source_path_absent':True,'LOC':measures['files'][name]})
assert len(payloads)==295
write_new(Q/'TRANSFER-MANIFEST.json',{'schema_version':1,'recorded_at':utc(),'job':RUN,'author':ACTOR,
    'source_root':str(P),'candidate_root':str(Q),'runtime_root':str(R),'payload_count':295,
    'eligible_application_paths':eligible,'source_current_cut':inputs['accepted_source'],
    'source_inputs':reference(R/'SOURCE-INPUTS.json'),'payloads':sorted(payloads,key=lambda row:row['relative_path']),
    'qualification':reference(R/'QUALIFICATION-FINAL.json'),'LOC':reference(R/'LOC-FINAL.json'),
    'self_review':reference(R/'SELF-REVIEW.json'),'conservation':reference(R/'CONSERVATION-FINAL.json'),
    'API':reference(R/'EXPORTED-API-FINAL.json'),'actual_dependency_imports':reference(R/'DEPENDENCY-IMPORTS.json'),
    'prior_attempts':reference(R/'PRIOR-ATTEMPTS-FINAL.json'),'source_published':False,
    'independent_review_required':True,'assurance':'DATA_ONLY',
    'limitations':'No native observation/authentication/enrollment grant/epoch/consumption/profile or effect. Source290 is the recorded input; known future foundation304 publication is a separate forward cut, not permission for stale overlay.'})
write_new(R/'HANDOFF.json',{'recorded_at':utc(),'author':ACTOR,'candidate':str(Q),'runtime':str(R),
    'manifest':reference(Q/'TRANSFER-MANIFEST.json'),'eligible_application_paths':eligible,
    'API':reference(R/'EXPORTED-API-FINAL.json'),'tests':reference(R/'final-r5.json'),
    'counts':{'final':82,'new':35,'retained':47,'failures':0,'errors':0,'skips':0},
    'LOC':reference(R/'LOC-FINAL.json'),'conservation':reference(R/'CONSERVATION-FINAL.json'),
    'self_review':reference(R/'SELF-REVIEW.json'),'prior_failures':reference(R/'PRIOR-ATTEMPTS-FINAL.json'),
    'dependencies':inputs['dependencies'],'next':'Root distinct review; then canonical existing-owner transition job if assigned',
    'source_published':False,'independent_review':False,'assurance':'DATA_ONLY'})
commands=[{'command':subprocess.list2cmdline([str(PY),'-B','-X','utf8',str(R/'run_tests.py'),'final-r5']),'exit_status':0},
          {'command':subprocess.list2cmdline([str(PY),'-B','-X','utf8',str(R/'qualify_final.py')]),'exit_status':0}]
result={'manifest_sha256':sha(Q/'TRANSFER-MANIFEST.json'),'manifest':reference(Q/'TRANSFER-MANIFEST.json'),
    'handoff':reference(R/'HANDOFF.json'),'tests_run':82,'new_cases':35,'retained_cases':47,
    'qualification':reference(R/'QUALIFICATION-FINAL.json'),'API':reference(R/'EXPORTED-API-FINAL.json'),
    'self_review':reference(R/'SELF-REVIEW.json'),'conservation':reference(R/'CONSERVATION-FINAL.json'),
    'LOC':reference(R/'LOC-FINAL.json'),'prior_failed_commands':reference(R/'PRIOR-ATTEMPTS-FINAL.json'),
    'raw_nonzero_relabelled':False,'assurance':'DATA_ONLY','source_published':False,'independent_review':False}
response=complete('implement',result,commands,[('Final82 exact IDs, zero failures/errors/skips',True),
    ('Original47 bytes/AST retained and295 candidate payloads pinned',True),
    ('Complete bounded request/display/domain bindings; native/authority acceptance explicitly absent',True),
    ('Recorded290 Source and E33601 endpoint conservation verified',True),
    ('Exact two uncredited dependencies and preserved failed attempts',True)])
print(json.dumps({'manifest':result['manifest'],'implement':reference(R/'implement.json'),
    'states':response['states'],'sequence':response['sequence']},indent=2))
