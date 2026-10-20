"""Self-review and release only the measured bounded AC3 environment candidate."""
from ac3_support import *
import ast,difflib,re
read=lambda path:json.loads(path.read_text(encoding='utf-8-sig'))
inputs=read(R/'SOURCE-INPUTS.json');binding=read(R/'TASK-BINDING.json')
main=read(R/'native-r2/RESULT.json');adverse=read(R/'adverse-r1/hostile-cleanup-r1.json')
assert main['tests_run']==64 and main['original_AC2_methods_run']==49 and main['new_AC3_methods']==15
assert main['expected_ids']==main['executed_ids']==main['stopped_ids'] and len(set(main['executed_ids']))==64
assert adverse['tests_run']==3 and adverse['expected_ids']==adverse['executed_ids'] and len(set(adverse['executed_ids']))==3
assert set(main['executed_ids']).isdisjoint(adverse['executed_ids'])
for value in (main,adverse):
    assert value['exit_status']==0 and value['failures']==value['errors']==value['skipped']==[]
    assert value['candidate_before']==value['candidate_after'] and value['source_before']==value['source_after']==inputs['Source_payloads']
assert main['all_recorded_lifetimes_closed'] and not main['remaining_new_threads'] and main['forbidden_calls']==[]
assert read(R/'adverse-r1/NO-PROFILE-GUARD.json')['forbidden_calls']==[]
assert sha(R/'adverse-r1/hostile_cleanup.py')==sha(F/'.agents/runtime/ac2-20261014/closure-r4/hostile_cleanup.py')
for value,raw in ((main,R/'native-r2/tests.txt'),(adverse,R/'adverse-r1/hostile-cleanup-r1.txt')):
    assert reference(raw)==value['raw']
    assert re.findall(r'^test_\S+ \(([^)]+)\)',raw.read_text(encoding='utf8'),re.MULTILINE)==value['executed_ids']
assert all(row['all_controlled_allocations_released'] is True for row in main['environment_receipts'])
environment=read(R/'environment-conservation.json')
assert environment['exit_status']==0 and environment['ordinary_files']==3601 and environment['ordinary_bytes']==231026067
assert environment['ordinary_file_bytes_identities_and_membership_exact'] is True and environment['all_membership_exact'] is True
source={name:ordinary(F/name) for name in inputs['Source_payloads']};assert source==inputs['Source_payloads']
assert all(ordinary(Path(row['path']))==row for row in inputs['AC2_payloads'].values())
candidate={name:ordinary(Q/name) for name in inputs['selected_dependencies']};assert len(candidate)==294
assert candidate==main['candidate_after']==adverse['candidate_after']
changed=sorted(name for name,row in candidate.items() if row['sha256']!=inputs['selected_dependencies'][name]['facts']['sha256'])
assert changed==sorted(binding['scope'])
product='src/ceta/supervisor/isolated_worker.py';test='tests/contract/test_isolated_worker.py'
old=(R/'before-images'/product).read_text(encoding='utf8');new=(Q/product).read_text(encoding='utf8')
def methods(text):
    tree=ast.parse(text);result={}
    for node in tree.body:
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):result[('',node.name)]=node
        if isinstance(node,ast.ClassDef):
            for member in node.body:
                if isinstance(member,(ast.FunctionDef,ast.AsyncFunctionDef)):result[(node.name,member.name)]=member
    return result
a,b=methods(old),methods(new);changed_methods=[]
allowed={('_IsolationAPI','__init__'),('_IsolationAPI','retry_cleanup'),('_IsolationAPI','pending_native_resources'),('_IsolationAPI','environment'),('','_finish_cleanup')}
for key,node in a.items():
    assert key in b
    if ast.dump(node,include_attributes=False)!=ast.dump(b[key],include_attributes=False):
        assert key in allowed,key;changed_methods.append(key)
    if key not in {('_IsolationAPI','retry_cleanup'),('','_finish_cleanup')}:
        assert ast.dump(node.args,include_attributes=False)==ast.dump(b[key].args,include_attributes=False),key
assert set(changed_methods)==allowed
assert ast.dump(a[('IsolatedWindowsWorker','launch')],include_attributes=False)==ast.dump(b[('IsolatedWindowsWorker','launch')],include_attributes=False)
ta,tb=methods((R/'before-images'/test).read_text(encoding='utf8')),methods((Q/test).read_text(encoding='utf8'))
for key,node in ta.items():
    if key!=('NativeIsolatedWorkerTests','test_environment_has_only_native_allowlist'):
        assert ast.dump(node,include_attributes=False)==ast.dump(tb[key],include_attributes=False),key
assert main['deferred_original_case']['id'] not in main['executed_ids']
before_lifetime=main['native_process_lifetimes']
for row in before_lifetime:assert row['lifetime_closed'] and row['process_closed'] and row['job_closed'] and row['thread_closed']
powershell="""$ErrorActionPreference='Stop'
$proof=Get-Content -LiteralPath 'T:\\00-Active\\Project-AI-CETA\\.agents\\runtime\\ac3-20261014\\native-r2\\RESULT.json' -Raw | ConvertFrom-Json
$known=@{};foreach($row in $proof.native_process_lifetimes){if($row.creation_time -gt 0){$known[([string]$row.pid+':'+[string]$row.creation_time)]=$true}}
$rows=@(Get-CimInstance Win32_Process | Where-Object { $known.ContainsKey(([string]$_.ProcessId+':'+[string]$_.CreationDate.ToUniversalTime().ToFileTimeUtc())) } | Select-Object ProcessId,ParentProcessId,CreationDate)
$scope=@(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -and $_.Name -like 'python*.exe' -and $_.CommandLine.Contains('T:\\00-Active\\Project-AI-CETA\\.agents\\runtime\\ac3-20261014\\') -and $_.CommandLine.Contains('job-fixtures') } | Select-Object ProcessId,ParentProcessId,CreationDate)
[pscustomobject]@{clear=($rows.Count -eq 0 -and $scope.Count -eq 0);known_lifetimes_remaining=$rows;owned_fixture_processes_remaining=$scope;observed_at=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json -Depth 8 -Compress
"""
script=R/'native-census.ps1'
with script.open('x',encoding='utf8') as output:output.write(powershell)
done=subprocess.run(['powershell.exe','-NoProfile','-File',str(script)],cwd=F,capture_output=True)
for suffix,raw in (('stdout.txt',done.stdout),('stderr.txt',done.stderr)):
    with (R/('native-census.'+suffix)).open('xb') as output:output.write(raw)
result=json.loads(done.stdout.decode('utf-8-sig'))
write_new(R/'native-census.json',{'recorded_at':utc(),'exit_status':done.returncode,'result':result,
    'recorded_lifetimes':before_lifetime,'raw':reference(R/'native-census.stdout.txt'),
    'qualification':'Exact persisted PID/creation endpoints and private job-fixture command scope only; no whole-host or profile mutation claim.'})
assert done.returncode==0 and result['clear'] is True,result
def executable(text):
    excluded=set()
    if text:
        for node in ast.walk(ast.parse(text)):
            body=getattr(node,'body',None)
            if isinstance(body,list) and body and isinstance(body[0],ast.Expr) and isinstance(body[0].value,ast.Constant) and isinstance(body[0].value.value,str):excluded.update(range(body[0].lineno-1,body[0].end_lineno))
            if isinstance(node,ast.ClassDef) and any(isinstance(base,ast.Name) and base.id=='Protocol' for base in node.bases):excluded.update(range(node.lineno-1,node.end_lineno))
    return {i for i,line in enumerate(text.splitlines()) if line.strip() and not line.lstrip().startswith('#') and i not in excluded}
def delta(old,new):
    a,b=executable(old),executable(new);added=removed=0
    for tag,a1,a2,b1,b2 in difflib.SequenceMatcher(a=old.splitlines(),b=new.splitlines(),autojunk=False).get_opcodes():
        if tag!='equal':added+=len(b&set(range(b1,b2)));removed+=len(a&set(range(a1,a2)))
    return {'added':added,'removed':removed}
loc={'recorded_at':utc(),'basis':'Actual AC3 new changes versus byte-exact accepted AC2 selected files; all existing source/native helper reuse receives zero new credit.',
    'method':'Raw-line SequenceMatcher(autojunk=False) spans intersect nonblank/noncomment Python line masks; complete AST docstrings and Protocol classes excluded.',
    'source':delta(old,new),'tests':delta((R/'before-images'/test).read_text(encoding='utf8'),(Q/test).read_text(encoding='utf8')),
    'reused_source_LOC_credit':0,'integrated_source_LOC':0}
compile(new,str(Q/product),'exec');compile((Q/test).read_bytes(),str(Q/test),'exec')
write_new(R/'LOC.json',loc)
limits=['Internal cause203 remains UNESTABLISHED; six-key environment is a measured/documented candidate, not a verified launch repair.',
    'The historical restricted-launch method remains byte/AST exact in source and is explicitly deferred because no new profile or restricted retry is authorized.',
    'Controlled response-loss tests retain product UNCERTAIN state even when the fixture independently retires its own known native allocation.',
    'Positive token/isolation/bypass/asset/network outcomes require the separately reviewed exact qualification tool and fresh genuine operator approval.',
    'No Source publication, public real-effect acceptance, or whole-unit completion is established.']
self_review={'recorded_at':utc(),'author':ACTOR,'decision':'AUTHOR_SELF_REVIEW_PENDING_DISTINCT_ROOT_REVIEW','actual_changed_paths':changed,
    'changed_existing_methods':[list(key) for key in changed_methods],'all_public_launch_parameters_unchanged':True,
    'native_CreateProcess_launch_AST_unchanged':True,'original_method_ASTs_preserved_except_intentional_environment_expectation':True,
    'native_observation':reference(R/'READ-ONLY-NATIVE-OBSERVATION.json'),'main':reference(R/'native-r2/RESULT.json'),
    'adverse':reference(R/'ADVERSE-QUALIFICATION.json'),'unique_methods':67,'native_lifetimes':len(before_lifetime),
    'environment':reference(R/'environment-conservation.json'),'census':reference(R/'native-census.json'),'LOC':reference(R/'LOC.json'),
    'reader_failure':reference(R/'original-count-reader-failure.json'),'cause_status':'UNESTABLISHED',
    'Source_native_and_hash_conserved':True,'AC2_full_native_and_hash_conserved':True,'Source_application':False,
    'actual_profile_Create_Delete':0,'actual_restricted_CreateProcess':0,'qualification_limits':limits}
write_new(R/'self-review.json',self_review)
manifest={'schema_version':'ceta.isolated-worker.ac3.v1','cut':RUN,'author':ACTOR,'frozen_at':utc(),'candidate_root':str(Q),'source_root':str(F),
    'payload_count':294,'payloads':candidate,'eligible_paths':read(F/'.agents/ac2-20261014/TRANSFER-MANIFEST.json')['eligible_paths'],
    'author_delta_changed_paths':changed,'application_paths':read(F/'.agents/ac2-20261014/TRANSFER-MANIFEST.json')['eligible_paths'],
    'source_inputs':reference(R/'SOURCE-INPUTS.json'),'parent_manifest':inputs['AC2_manifest'],'before_images':{name:reference(R/'before-images'/name) for name in changed},
    'current_source_REUSE_count':290,'source_application':False,'isolation_qualified':False,'activation_ready':False,'whole_unit_completion':False,
    'functional_status':'NATIVE_SIX_KEY_CONSTRUCTION_AND_CUSTODY_QUALIFIED; RESTRICTED_LAUNCH_UNVERIFIED',
    'tests':{'main':reference(R/'native-r2/RESULT.json'),'adverse':reference(R/'ADVERSE-QUALIFICATION.json'),'unique_methods':67,
        'original_methods_executed':52,'new_methods':15,'deferred':main['deferred_original_case']},
    'native_observation':reference(R/'READ-ONLY-NATIVE-OBSERVATION.json'),'environment_conservation':reference(R/'environment-conservation.json'),
    'native_census':reference(R/'native-census.json'),'self_review':reference(R/'self-review.json'),'LOC':loc,
    'native_rust_byte_exact_reuse':True,'native_binary_byte_exact_reuse':'527518104fb84c430e3e9e0be61982c533b0c6fbb13e1a85e959ba1a3866ad0f',
    'qualification_limits':limits,'review_acceptance':'PENDING_DISTINCT_ROOT_REVIEW',
    'publication_rule':'Only the four selected AC2/AC3 worker paths after distinct Root review. All other Source/foundation forward paths, especially canonical windows_jobs and RB/PERF owners, remain untouched. Do not overlay the complete old staged candidate.'}
write_new(Q/'TRANSFER-MANIFEST.json',manifest)
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_runtime import _snapshot_workspace
from taar.orchestration_receipts import sha256_json
snapshot=_snapshot_workspace(Q,Path('T:/'));assert len(snapshot)==295
write_new(R/'source-freeze.json',{'recorded_at':utc(),'manifest':reference(Q/'TRANSFER-MANIFEST.json'),'snapshot':snapshot,'members':295,'native_payloads':candidate})
complete('implement',{'manifest':reference(Q/'TRANSFER-MANIFEST.json'),'self_review':reference(R/'self-review.json'),'freeze':reference(R/'source-freeze.json'),
    'tests':manifest['tests'],'LOC':loc,'Source_application':False,'qualification_limits':limits},
    [{'command':str(PY)+' -B -X utf8 '+str(R/'observe_environment.py'),'exit_status':0},
     {'command':str(PY)+' -B -X utf8 '+str(R/'run_tests.py')+' native-r2','exit_status':0},
     {'command':str(PY)+' -B -X utf8 '+str(R/'run_adverse.py'),'exit_status':0},
     {'command':str(PY)+' -B -X utf8 '+str(R/'verify_environment.py'),'exit_status':0}],
    [('67_unique_native_negative_inherited_methods_zero_failures_errors_skips',True),('one_unapproved_actual_restricted_launch_explicitly_deferred',True),
     ('no_profile_or_restricted_Create_calls',True),('source290_AC2294_E33601_conserved',True),('all_recorded_owned_lifetimes_closed',True),
     ('modern_native_known_folder_cleanup_and_uncertainty_explicit',True),('distinct_Root_review_required',True)])
state=read(R/RUN/'state.json');claims=read(R/RUN/'claims.json');submitted=read(R/'implement.json');stored=read(R/RUN/'receipts/implement.json')
assert state['sequence']==7 and state['nodes']['implement']['state']=='SUCCEEDED' and state['nodes']['review']['state']=='READY' and claims=={}
assert len(submitted)==12 and set(stored)==set(submitted)|{'git_baseline','observed_git','receipt_hash'}
typed=lambda value:json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
assert typed(submitted)==typed({key:stored[key] for key in submitted})
normalized=dict(stored);normalized.pop('receipt_hash');fingerprint=sha256_json(normalized)
assert fingerprint==stored['receipt_hash']==state['nodes']['implement']['receipt_hash']
assert _snapshot_workspace(Q,Path('T:/'))==snapshot
write_new(R/'ACTUAL-IMPLEMENT-READBACK.json',{'recorded_at':utc(),'sequence':7,'implement':'SUCCEEDED','review':'READY','claims':{},
    'manifest_sha256':sha(Q/'TRANSFER-MANIFEST.json'),'implement_sha256':sha(R/'implement.json'),'strict_submitted_fields':12,'persisted_fields':15,
    'strict_typed_projection_equal':True,'normalized_fingerprint':fingerprint,'tests':67,'cause_status':'UNESTABLISHED','Source_application':False})
print(json.dumps({'manifest_sha256':sha(Q/'TRANSFER-MANIFEST.json'),'implement_sha256':sha(R/'implement.json'),'readback_sha256':sha(R/'ACTUAL-IMPLEMENT-READBACK.json'),
    'state':'implementSUCCEEDED/reviewREADY/sequence7/claims{}','tests':67,'LOC':loc}),flush=True)
