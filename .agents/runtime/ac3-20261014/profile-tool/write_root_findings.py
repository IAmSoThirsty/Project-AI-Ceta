"""Preserve exact approved host-operation findings without altering source."""
from pathlib import Path
import hashlib,json,os,re,sys
F=Path('T:/00-Active/Project-AI-CETA');R=Path(__file__).resolve().parent
sys.path.insert(0,str(F/'.agents/runtime/en1-20261014'));import en1_support as s
s.R=R;s.Q=F/'.agents/ac3-20261014'
read=lambda p:json.loads(p.read_text())
attempt=R/'profile-qualification-a82d795283474f5daa218f8c158d5047'
regression=R/'approved-no-profile-13b4cd2a9c00471f91340cb3a9f017e8'
result=read(attempt/'RESULT.json');post=read(attempt/'POST-DELETE-OBSERVATION.json');negative=read(regression/'RESULT.json')
assert result['positive_isolation_qualified'] is False and result['all_captured_resources_retired'] is True
assert result['primary_failure']['text']=='ISOLATION_TOKEN_NOT_QUALIFIED at $'
assert result['profile_cleanup_status']=='DELETE_SUCCEEDED_AND_FOLDER_ABSENCE_OBSERVED'
assert post['native_delete_HRESULT']==0 and post['folder_observation']['HRESULT']==-2147024894 and post['folder_observation']['path'] is None
assert negative['tests_run']==1 and negative['exit_status']==0 and negative['profile_Create_Delete_calls']==[]
assert negative['all_recorded_lifetimes_closed'] and not negative['remaining_new_threads']
assert negative['Source_before']==negative['Source_after'] and negative['candidate_before']==negative['candidate_after']
assert all(s.ordinary(F/name)['sha256']==row['sha256'] and s.ordinary(F/name)['native_identity']==row['native_identity'] for name,row in negative['Source_after'].items())
raw=(regression/'raw.txt').read_text();assert 'ISOLATION_RESTRICTED_CREATE_FAILED:267' in raw
assert re.search('ISOLATION_RESTRICTED_CREATE_FAILED:2','ISOLATION_RESTRICTED_CREATE_FAILED:267 at $')
facts={'at':s.utc(),'reviewer':'/root','operator_scope_completed':True,
    'qualification':'FAILED','primary_failure':result['primary_failure'],
    'exact_failed_token_predicate':'UNESTABLISHED; actual rejected token fields were not serialized by this tool',
    'native_worker_mainthread_resume':'Inspected launch code rejects token_facts before its ResumeThread call; no completed worker probe facts exist.',
    'created_new_profile_once':True,'additional_profile_creation':False,'automatic_retry':False,
    'own_cleanup':{'native_Delete_HRESULT':0,'folder_HRESULT':-2147024894,'observed_path':None,
        'captured_lifetimes':result['retirement']['custody'],'all_known_native_resources_retired':True},
    'original_no_profile_test':{'methods':1,'failed':0,'errors':0,'skips':0,
        'observed_native_error':267,'legacy_regex':'ISOLATION_RESTRICTED_CREATE_FAILED:2',
        'qualification':'Original assertions pass and known process retires. The prefix regex accepts267, so exacterror2 and missing-profile causality are not established.'},
    'Source290_and_candidate294_conserved':True,'Source_application':False,'genuine_owner_approval':'NOT_RUN',
    'canonical_real_effect_accepted':False,
    'existing_issues':[
      {'id':'AC3-LIVE-TOKEN-QUALIFICATION','classification':'blocking real-effect isolation acceptance',
       'next_executable_path':'Retain exact measured/rejected token values in a reviewed successor; diagnose each unchanged token predicate before proposing another actual profile attempt.'},
      {'id':'AC3-NO-PROFILE-REGEX','classification':'requires separate follow-up work',
       'next_executable_path':'Use an exact structured native error check or explicitly declared permitted denial set; preserve actual267 and never claim exact2 from this original regex.'}],
    'evidence':{name:s.reference(path) for name,path in {
       'actual_human_approval':R/'ACTUAL-OPERATOR-APPROVAL.json',
       'exact_reviewed_tool':R/'profile_qualification.py','execution':R/'APPROVED-QUALIFICATION.json',
       'qualification_result':attempt/'RESULT.json','created_profile':attempt/'CREATED.json',
       'retirement':attempt/'RETIREMENT.json','post_delete':attempt/'POST-DELETE-OBSERVATION.json',
       'original_regression':regression/'RESULT.json','original_regression_raw':regression/'raw.txt'}.items()}}
s.write_new(R/'ROOT-FINDINGS.json',facts)
print(json.dumps({'result':'FAILED_QUALIFICATION_WITH_VERIFIED_OWN_CLEANUP','findings_sha256':s.sha(R/'ROOT-FINDINGS.json'),
    'original_regression':'ONE_CASE_PASSED_ORIGINAL_ASSERTIONS','Source_changes':[]}),flush=True)
