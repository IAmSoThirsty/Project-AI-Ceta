"""Seal the exact ER1 preparation cut after native tests and source conservation."""
from er1_support import *
import ast,base64,csv,io
start=utc();inventory=json.loads((R/'launcher-inventory-r2.json').read_text());generation=json.loads((R/'candidate-generation.json').read_text());tests=json.loads((R/'staged-tests-r2.json').read_text())
assert tests['tests_run']==7 and tests['failures']==tests['errors']==tests['skips']==tests['exit_status']==0
assert tests['executed_ids']==tests['expected_ids'] and len(set(tests['executed_ids']))==7
assert len(tests['actual_cli_invocations'])==7 and all(item['oracle_passed'] and item['observed_empty_job'] and item['owner_closed'] for item in tests['actual_cli_invocations'])
assert len(tests['entrypoint_imports'])==27 and sha(R/'staged-tests-r2.txt')==tests['raw_sha256']
assert tests['candidate_before']==tests['candidate_after']
assert {str(path.relative_to(Q)):sha(path) for path in Q.rglob('*') if path.is_file()}==tests['candidate_after']
after=snapshot_tree();write_new(R/'E3-after-tests.json',after)
before=json.loads((R/'E3-drift-r3.json').read_text());old=json.loads((R/'E3-before.json').read_text())
for earlier in (before,old):
    assert [row for row in earlier['members'] if row['kind']=='ordinary_file']==[row for row in after['members'] if row['kind']=='ordinary_file']
    assert earlier['root_native_identity']==after['root_native_identity']
left={row['relative_path']:row for row in before['members']};right={row['relative_path']:row for row in after['members']};assert set(left)==set(right)
directory_size_variations=[]
for name in left:
    a,b=left[name],right[name]
    if a!=b:
        assert a['kind']==b['kind']=='directory'
        assert [key for key in a['native_identity'] if a['native_identity'][key]!=b['native_identity'][key]]==['bytes']
        directory_size_variations.append({'path':name,'before':a['native_identity'],'after':b['native_identity']})
active_destinations=[];payloads=[]
for row in generation['launchers']:
    candidate=P/row['candidate']['repository_relative_path'];original=P/row['before_image']['repository_relative_path'];source=E3/row['source_relative_path']
    assert sha(candidate)==row['candidate']['sha256'] and sha(original)==sha(source)==row['source_sha256']
    assert ordinary(source)['native_identity']==row['source_native_identity']
    active_destinations.append(source.relative_to(E3).as_posix())
    payloads.append({'candidate_relative_path':candidate.relative_to(Q).as_posix(),'kind':'GENERATED_EXECUTABLE_CONSOLE_LAUNCHER','action':'EXTEND_STAGED_ONLY',
                     'candidate_bytes':candidate.stat().st_size,'candidate_sha256':sha(candidate),'source_path':str(source),'source_sha256':sha(source),'source_native_identity':row['source_native_identity'],
                     'before_image':reference(original),'distribution':row['distribution'],'version':row['distribution_version'],'entry_point':row['entry_point_value'],'current_shebang':row['candidate_shebang'],
                     'main_script_sha256':row['main_script_sha256'],'main_script_behavior':'EXACT_REUSE_ZERO_NEW_FUNCTIONAL_LOC','stub_sha256':row['stub_sha256'],'stub_behavior':'EXACT_REUSE','execution':row['execution_classification']})
for row in generation['metadata']:
    candidate=P/row['candidate']['repository_relative_path'];original=P/row['before_image']['repository_relative_path'];source=E3/row['source_relative_path']
    assert sha(candidate)==row['candidate']['sha256'] and sha(original)==sha(source)==row['source_observation']['sha256']
    assert ordinary(source)==row['source_observation']
    old_rows=list(csv.reader(io.StringIO(fs.read_bytes(original).decode())));new_rows=list(csv.reader(io.StringIO(fs.read_bytes(candidate).decode())))
    assert len(old_rows)==len(new_rows)==row['rows_before_after']
    expected={item['original_row'][0]:item for item in row['row_changes']};seen=set()
    for a,b in zip(old_rows,new_rows):
        if a and a[0] in expected:
            item=expected[a[0]];assert a==item['original_row'] and b==item['candidate_row'];seen.add(a[0])
        else:assert a==b
    assert set(expected)==seen
    active_destinations.append(source.relative_to(E3).as_posix())
    payloads.append({'candidate_relative_path':candidate.relative_to(Q).as_posix(),'kind':'EXACT_INSTALLED_RECORD_FIELD_CANDIDATE','action':'EXTEND_STAGED_ONLY','candidate_bytes':candidate.stat().st_size,'candidate_sha256':sha(candidate),
                     'source_path':str(source),'source_sha256':sha(source),'source_native_identity':row['source_observation']['native_identity'],'before_image':reference(original),'exact_changed_rows':row['row_changes'],
                     'row_count':row['rows_before_after'],'other_original_raw_lines_identical':True,'scope':'Only declared27 total launcher hash/size fields, original names/roworder/endings/quoting retained'})
assert len(payloads)==len(set(active_destinations))==30
source_proof={'observed_at':utc(),'whole_E3_ordinary_files':3601,'whole_E3_ordinary_bytes':231026958,'ordinary_before_after_exact':True,'ordinary_native_identities_exact':True,'full_namespace_paths_exact':True,
              'historical_before':reference(R/'E3-before.json'),'bounded_before':reference(R/'E3-drift-r3.json'),'after':reference(R/'E3-after-tests.json'),
              'future_active_destination_paths':sorted(active_destinations),'future_active_destination_count':30,'currently_modified_active_destinations':0,
              'all_other_ordinary_members_count':3571,'all_other_ordinary_members_preserved':True,'both_interpreters_preserved':True,'library_and_distribution_metadata_preserved':True,
              'directory_size_observations':{'initial_variations':reference(R/'source-drift-r3.json'),'native_query_identity_proof':reference(R/'directory-observation-proof.json'),'final_vs_bounded_variations':directory_size_variations,'OS_internal_cause':'UNRESOLVED','whole_raw_metadata_equality_claim':False},
              'limitations':['Native endpoint hashes/identities establish these observations; no assertion of continuous whole-source custody between every observation','Source is read-only for ER1 while Root/HD2 use own direct E3 Python concurrently','No external A/X/N source observations or modifications; source conservation is exact own E3 cut only']}
write_new(R/'source-conservation.json',source_proof)
def meaningful(path):
    text=path.read_text();docs=set()
    for node in ast.walk(ast.parse(text)):
        body=getattr(node,'body',None)
        if isinstance(body,list) and body and isinstance(body[0],ast.Expr) and isinstance(body[0].value,ast.Constant) and isinstance(body[0].value.value,str):docs.update(range(body[0].lineno,body[0].end_lineno+1))
    return len([line for number,line in enumerate(text.splitlines(),1) if line.strip() and not line.lstrip().startswith('#') and number not in docs])
prior=['discovery-r1-failure.json','discovery-r2-failure.json','discovery-r3-failure.json','discovery-failure-qualification.json','builder-r1-failure.json','staged-tests-r1-qualification.json']
self_review={'actor':ACTOR,'kind':'AUTHOR_SELF_REVIEW_PENDING_DISTINCT_REVIEW','scoped_outcome':'Real27 functional generated launchers plus3 exact metadata candidates; active environment not applied','candidate_controls':['Exact27 metadata/specifications; standard installed ScriptMaker generation only','Native original/stub/main bytes preserved; current T-root E3 interpreter','Memory file-operation emission avoids installed generator fallback rename; native exclusive candidate writes','All27 source originals and3 metadata originals retained','Seven real bounded CLI invocations observed exited; all jobs empty and owner handles closed','NoGUI/server/deploy/installer/network functions invoked','Whole3601 ordinary active E3 bytes/identities retained; directory-size queries explicitly qualified'],
             'first_failed_attempts':[reference(R/name) for name in prior],'tests':reference(R/'staged-tests-r2.json'),'test_raw':reference(R/'staged-tests-r2.txt'),
             'remaining':['Independent reviewer pressure_writer approval','Root separate native guarded publication of exact30 paths with fresh CAS/backups','Actual destination CLI/RECORD/source conservation qualification after publication','Aggregate PySide6 distribution metadata remains unavailable','All23 Qt tools require separate functional qualification where required; static imports only','Directory-stat-size OS-internal cause unresolved; proofs retain exact observed values'],
             'source_mutation':False,'whole_product_acceptance':False,'independence':'Same author produced candidate and these tests/selfchecks; no independent approval claimed'}
write_new(R/'self-review.json',self_review)
manifest={'schema_version':1,'job':'ER1 exact relocated E3 launcher and RECORD preparation','author':ACTOR,'frozen_at':utc(),'candidate_root':str(Q),'active_environment_root':str(E3),'state':'FROZEN_AUTHOR_CANDIDATE_FOR_SEPARATE_REVIEW',
          'current_inventory':reference(R/'launcher-inventory-r2.json'),'superseded_native_identity_bug_inventory':reference(R/'launcher-inventory.json'),'source_conservation':reference(R/'source-conservation.json'),'generation':reference(R/'candidate-generation.json'),
          'payloads':payloads,'payload_count':30,'launchers':27,'metadata':3,'exact_RECORD_rows_changed':27,'writer_source':{'path':'build_launchers.py','sha256':sha(Q/'build_launchers.py'),'meaningful_LOC':meaningful(Q/'build_launchers.py'),'physical_LOC':len((Q/'build_launchers.py').read_text().splitlines())},
          'generated_wrappers_and_stubs_new_LOC':0,'generated_wrapper_LOC_reason':'Exact reuse; exe bytes and metadata field replacements measured separately from hand-written source','author_tests':{'methods':7,'failures':0,'errors':0,'skips':0,'actual_CLI_invocations':7,'static_entrypoint_imports':27,'Qt_tools_executed':0,'test_automation_meaningful_LOC':meaningful(R/'run_staged_tests_r2.py'),'receipt':reference(R/'staged-tests-r2.json'),'raw':reference(R/'staged-tests-r2.txt')},
          'self_review':reference(R/'self-review.json'),'prior_failures':[reference(R/name) for name in prior],'additional_metadata_scope_authority':'Root explicitly authorized exactly3 staged RECORD paths and27 launcher checksum/size fields; no active E3 metadata or launcher publication authorized',
          'active_E3_or_source_application':False,'review_acceptance':'PENDING_DISTINCT_REVIEW'}
write_new(Q/'TRANSFER-MANIFEST.json',manifest)
from taar.orchestration_runtime import _snapshot_workspace,_changed_files
snapshot=_snapshot_workspace(Q,Path('T:/'));current=json.loads((R/RUN/'claims.json').read_text())['implement'];changed=_changed_files(current['baseline_snapshot'],snapshot)
assert len(snapshot)==33 and len(changed)==33
write_new(R/'source-freeze.json',{'manifest':reference(Q/'TRANSFER-MANIFEST.json'),'snapshot':snapshot,'changed_files':changed,'candidate_source_mutation_after_freeze':False})
commands=[{'command':subprocess.list2cmdline([sys.executable,'-B','-X','utf8',str(Q/'build_launchers.py')]),'exit_status':0},{'command':subprocess.list2cmdline(tests['command_argv']),'exit_status':0},{'command':subprocess.list2cmdline([sys.executable,'-B','-X','utf8',str(Path(__file__))]),'exit_status':0}]
response=complete('implement',{'manifest':reference(Q/'TRANSFER-MANIFEST.json'),'manifest_sha256':sha(Q/'TRANSFER-MANIFEST.json'),'source_freeze':reference(R/'source-freeze.json'),'source_conservation':reference(R/'source-conservation.json'),'self_review':reference(R/'self-review.json'),
                             'payload_count':30,'launcher_count':27,'metadata_count':3,'tests':manifest['author_tests'],'source_LOC':manifest['writer_source'],'prior_failure':manifest['prior_failures'],'active_application':False},commands,
                 [(name,True) for name in ['Exact27 functional PE launchers regenerated via current installed standard primitives','Exact3 RECORD files change27 hash/size fields while preserving raw other bytes/quoting/endings','Corrected native-ID supplement and all failures retained without rewriting old evidence','Seven actual bounded native CLI invocations and27 static imports pass; no skips','Whole3601 ordinary active E3 file bytes/native identities retained; directory-stat limitation explicit','Fresh no-overwrite candidate and all30 originals retained; active publication not authorized','Exact33-member candidate frozen for distinct independent review']])
state=json.loads((R/RUN/'state.json').read_text());claims=json.loads((R/RUN/'claims.json').read_text());assert state['nodes']['implement']['state']=='SUCCEEDED' and state['nodes']['review']['state']=='READY' and claims=={}
write_new(R/'actual-implement-readback.json',{'observed_at':utc(),'sequence':state['sequence'],'implement_state':'SUCCEEDED','review_state':'READY','claims':claims,'manifest_sha256':sha(Q/'TRANSFER-MANIFEST.json'),'implement_receipt_sha256':sha(R/'implement.json'),'payloads':30,'frozen_members':33,'source_conservation_sha256':sha(R/'source-conservation.json'),'active_application':False,'writer_released':True})
assert _snapshot_workspace(Q,Path('T:/'))==snapshot
print(json.dumps({'manifest_sha256':sha(Q/'TRANSFER-MANIFEST.json'),'implement_receipt_sha256':sha(R/'implement.json'),'sequence':state['sequence'],'implement':'SUCCEEDED','review':'READY','claims':claims,'payloads':30,'frozen_members':33,'ordinary_E3_files_preserved':3601,'builder_meaningful_LOC':manifest['writer_source']['meaningful_LOC'],'test_automation_meaningful_LOC':manifest['author_tests']['test_automation_meaningful_LOC']}))
