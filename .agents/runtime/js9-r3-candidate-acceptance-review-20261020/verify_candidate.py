"""Dormant file-only terminal candidate review. Never run product/test/native code."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import ast,hashlib,json,os,stat,sys,types
F=Path('T:/00-Active/Project-AI-CETA')
D=F/'.agents/runtime/js9-runtime-20261020/successor-r3'
ROOT=F/'.agents/runtime/js9-root-r3-execution-20261020'
OUT=Path(__file__).resolve().parent;C=D/'candidate-full';PHASE='candidate-full'
controls=[];denied=[];refs={}
def audit(event,args):
    if event=='ctypes.dlopen' or event.startswith(('subprocess.','socket.')) or event in ('sqlite3.connect','os.system','os.startfile','os.posix_spawn','os.fork'):
        denied.append(event);raise RuntimeError('FILE_ONLY_REVIEW_DENIES:'+event)
    if event=='open':
        path,mode,flags=args
        writing=isinstance(mode,str) and any(c in mode for c in 'wax+') or isinstance(flags,int) and bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        if writing and (not isinstance(path,(str,bytes,os.PathLike)) or not Path(os.fsdecode(path)).resolve().is_relative_to(OUT)):
            denied.append(event);raise RuntimeError('WRITE_OUTSIDE_REVIEW_SCOPE')
sys.addaudithook(audit)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def sha(path):return digest(path.read_bytes())
def load(path):return json.loads(path.read_bytes())
def ref(path):
    value=dict(repository_relative_path=path.relative_to(F).as_posix(),sha256=sha(path));refs[value['repository_relative_path']]=value['sha256'];return value
def check(name,value,**evidence):
    assert value,(name,evidence)
    controls.append(dict(name=name,passed=True,**evidence))
def ordinary(path):
    before=path.lstat();assert stat.S_ISREG(before.st_mode) and not before.st_file_attributes&1024
    raw=path.read_bytes();after=path.lstat()
    fields=('st_size','st_mtime_ns','st_mode','st_dev','st_ino','st_file_attributes')
    assert all(getattr(before,k)==getattr(after,k) for k in fields)
    return dict(path=str(path),bytes=len(raw),sha256=digest(raw),native_identity=dict(bytes=before.st_size,mtime_ns=before.st_mtime_ns,mode=stat.S_IMODE(before.st_mode),device=before.st_dev,inode=before.st_ino,attributes=before.st_file_attributes))
def proof_bytes(reference):
    assert type(reference) is dict and set(reference)=={'repository_relative_path','sha256'}
    name=reference['repository_relative_path'];assert type(name) is str and name and '\\' not in name and not Path(name).drive
    assert all(part not in ('','.','..') for part in name.split('/'))
    path=F/name;raw=path.read_bytes();assert digest(raw)==reference['sha256'];refs[name]=reference['sha256'];return path,raw
def proof(reference):
    path,raw=proof_bytes(reference);return path,json.loads(raw)

def run():
    required=[C/'RESULT.json',D/'candidate-full-LAUNCH-RESULT.json',ROOT/'candidate-full-TERMINAL.json']
    check('terminal_receipts_present',all(p.is_file() for p in required))
    packet=load(D/'PACKET.json');manifest=load(D/'MANIFEST-Q5.json');q=Path(manifest['candidate'])
    check('exact_packet',ref(D/'PACKET.json')['sha256']=='32575147e478c63ead51c6269af9e22eebe06ccdc74619cdb04e46231fe9ac82')
    check('exact_Q5_manifest',ref(D/'MANIFEST-Q5.json')['sha256']=='cce2c8e2c3a31fbedf5c2d83b2d15d499a93030c38ebe0c1e4545b868ef99acf')
    check('all_frozen_script_pins',all(sha(D/n)==h for n,h in packet['scripts'].items()))
    cases=proof(packet['case_set'])[1];expected=cases['expected_ids'];v=proof(packet['environment'])[1]
    source_before=proof(packet['Source_before'])[1]
    current_source={n:None if r is None and not (F/n).exists() else ordinary(F/n) for n,r in source_before['targets'].items()}
    check('Source_before_current_native_CAS_and_absences',current_source==source_before['targets'],files=len(current_source))
    check('candidate_all541_current',len(manifest['payload_hashes'])==541 and all(sha(q/n)==h for n,h in manifest['payload_hashes'].items()))
    baseline_path=F/'.agents/runtime/js8-20261015/amendment-report1/ACCEPTED-SOURCE-BASELINE.json';baseline=load(baseline_path)
    check('accepted_Source352_bytes_unchanged',len(baseline['effective_payload_hashes'])==352 and all(sha(F/n)==h for n,h in baseline['effective_payload_hashes'].items()))
    actual_environment={};environment_root=Path(v['python']['path']).parents[1]
    for directory,dirs,files in os.walk(environment_root,followlinks=False):
        for name in dirs:assert not (Path(directory)/name).lstat().st_file_attributes&1024
        for name in files:
            path=Path(directory)/name;actual_environment[path.relative_to(environment_root).as_posix()]=ordinary(path)
    check('E3_environment_current_native_facts',actual_environment==v['environment_files'],files=len(actual_environment))
    check('native_fixture_inputs_current',all(ordinary(Path(row['path']))==row for row in packet['fixture_dependencies'].values()))
    githead=(F/'.git/HEAD').read_text().strip();assert githead.startswith('ref: refs/heads/')
    check('current_Git_HEAD_ref',githead.removeprefix('ref: refs/heads/')==packet['Git']['branch'] and (F/'.git'/githead.removeprefix('ref: ')).read_text().strip()==packet['Git']['HEAD'])
    tree=ast.parse((D/'js9_support.py').read_text(encoding='utf8'))
    names={'interpreter_observation','require_case_ids','require_full_result','require_native_terminal','require_native_corroboration'}
    body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names];assert {n.name for n in body}==names
    scope=dict(Path=Path,F=F,R=D,sys=sys,s=types.SimpleNamespace(ordinary=ordinary),proof=proof,proof_bytes=proof_bytes,
        packet=lambda:packet,inputs=lambda:v,exact_ref=ref,manifest_reference=lambda:packet['candidate_manifest'],manifest=lambda:dict(expected_payload_hashes=manifest['payload_hashes']))
    exec(compile(ast.Module(body=body,type_ignores=[]),str(D/'js9_support.py'),'exec'),scope)
    full=load(C/'RESULT.json');launch=load(D/'candidate-full-LAUNCH-RESULT.json');root_terminal=load(ROOT/'candidate-full-TERMINAL.json')
    admission_error=None
    try:admitted=scope['require_full_result'](ref(C/'RESULT.json'),ref(D/'candidate-full-LAUNCH-RESULT.json'),PHASE)==full
    except (AssertionError,KeyError,TypeError) as error:
        admitted=False;admission_error=dict(type=type(error).__name__,message=str(error))
    expected_exit=0 if full['failures']==full['errors']==full['skips']==0 and full['primary_error'] is None else 1
    check('actual_admission_agrees_with_recorded_failures',admitted is (expected_exit==0))
    check('Root_terminal_matches_actual_full_status',type(root_terminal['exit_status']) is int and root_terminal['exit_status']==launch['exit_status']==full['exit_status']==expected_exit and root_terminal['command_returned'] is True and root_terminal['execution_error'] is None)
    command=load(ROOT/'candidate-full-COMMAND.json');check('Root_exact_command_and_no_retry',command['argv']==root_terminal['argv'] and command['cwd']==root_terminal['cwd']==str(D) and command['automatic_retry'] is False)
    check('Root_raw_terminal_hashes',sha(ROOT/'candidate-full.stdout')==root_terminal['stdout_sha256'] and sha(ROOT/'candidate-full.stderr')==root_terminal['stderr_sha256'])
    release_path,release=proof(full['release'])
    check('Root_command_exact_release',command['argv']==[v['python']['path'],'-B','-X','utf8',str(D/'launch_full.py'),PHASE,'--release-path',str(release_path),'--release-sha256',full['release']['sha256']])
    check('parent_launch_retains_actual_child_status',launch['child_terminal']==ref(C/'RESULT.json') and launch['child_status']['exit_status']==expected_exit and launch['child_status']['primary_error']==full['primary_error'] and launch['child_status']['preflight_complete'] is True and launch['record']['child_exit']==expected_exit)
    check('same_launch_owner',load(D/'candidate-full-LAUNCH-OWNER.json')==launch['record']['native_owner'])
    check('actual_owner_retired_all_five',set(launch['record']['native_owner_after'])=={'closed','process_closed','thread_closed','job_closed','startup_handles_closed'} and all(v is True for v in launch['record']['native_owner_after'].values()))
    check('readiness_and_complete_failure_details',full['preflight_complete'] is True and full['mandatory_full_gate_complete'] is True and full['deferred_ids']==[] and len(full['failure_details'])==full['failures'] and len(full['error_details'])==full['errors'] and len(full['skip_details'])==full['skips'])
    check('exact2622_original2334_reasoning50',full['expected_ids']==full['executed_ids']==full['stopped_ids']==expected and len(expected)==2622 and len(cases['parent2334_ids'])==2334 and sum(n.startswith('reasoning.test_reasoning_integration.') for n in expected)==21 and sum(n.startswith('reasoning.test_reasoning_repairs.') for n in expected)==29)
    event_path,event_bytes=proof_bytes(full['case_events']);events=[json.loads(line) for line in event_bytes.splitlines()]
    execution_events=[r for r in events if r['event'] in ('PREPARE','START','STOP')]
    diagnostic_events=[r for r in events if r['event'] not in ('PREPARE','START','STOP')]
    check('all_events_exact_PREPARE_START_STOP',[(r['event'],r['test_id']) for r in execution_events]==[(kind,n) for n in expected for kind in ('PREPARE','START','STOP')])
    check('all_other_events_are_explicit_failure_diagnostics',all(r['event'] in ('FAILURE','ERROR','SUBTEST_FAILURE') and type(r['traceback']) is str for r in diagnostic_events))
    check('event_times_nondecreasing',all(type(r['elapsed_seconds']) in (int,float) and r['elapsed_seconds']>=0 for r in events) and all(a['elapsed_seconds']<=b['elapsed_seconds'] for a,b in zip(events,events[1:])))
    raw_path,raw_bytes=proof_bytes(full['raw']);raw=raw_bytes.decode('utf8')
    check('all_raw_case_results_present',all('('+n+') ...' in raw for n in expected) and 'Ran 2622 tests' in raw)
    check('raw_summary_matches_actual_result',(raw.rstrip().endswith('OK') if expected_exit==0 else 'FAILED (' in raw))
    collection=full['uniform_pre_test_collection']
    check('all2622_pretest_GC_collections',[r['test_id'] for r in collection]==expected and all(r['gc_enabled'] is True and type(r['before_collect_handles']) is type(r['after_collect_handles']) is int for r in collection))
    check('GC_observer_no_reported_failure',full['gc_observation_failed'] is False and all(r['phase'] in ('start','stop') for r in full['gc_events']))
    physical=proof(full['physical_custody'])[1];native=proof(full['native_owners_proof'])[1];sqlite=proof(full['sqlite_receipts'])[1]
    check('physical_resources_all_closed',physical['owned_resources_closed'] is True and physical['remaining_resources']==[])
    check('all_captured_SQLite_objects_closed',all(r['physical_closed_probe'] is True and r['probe_observation']=='Cannot operate on a closed database.' for r in physical['sqlite']))
    check('all_captured_streams_closed',all(r['closed'] is True and r['fileno_denied'] is True for r in physical['streams']))
    check('captured_descriptors_retired',all(r['closed'] is True for r in physical['os_descriptors']))
    check('captured_native_service_owners_retired',all(r['retired'] is True and all(r['closed_native_designations'].values()) for r in physical['native_owners']))
    check('constructor_postconstructor_SQLite_probes',all(r['all_fixture_native_connections_closed'] is True for r in sqlite['test_journal_constructor_cleanup']) and all(r['all_exact_native_connections_closed'] is True for r in sqlite['test_journal_postconstruction_cleanup']))
    check('all_native_obligations_true',native['owned_resources_closed'] is True and native['obligations'] and all(value is True for value in native['obligations'].values()))
    check('actual_native_processes_retired',all(all(r[k] is True for k in ('lifetime_closed','process_closed','thread_closed','job_closed')) and r['remaining_query_exports']==0 for r in native['native_owners']))
    check('clocks_retired',all(r['state']=='CLOSED' and r['registered'] is False and r['sampler_alive'] is False for r in native['clock_owners']))
    allowed=set(native['controlled_uncertainty_cases']);pending_api=[r for r in native['native_APIs'] if r['pending']]
    check('controlled_API_uncertainty_exact',all(r['test_id'] in allowed and all(p['retry']=='UNCERTAIN' and p['kind'] in ('attributes','sid','sid_text','known_folder_path') for p in r['pending']) for r in pending_api))
    pending_bindings=[r for r in native['bindings'] if r['pending']]
    check('controlled_binding_uncertainty_exact',all(r['test_id']=='test_native_runtime_composition.NativeRuntimeCompositionTests.test_interrupted_native_open_preserves_unknown_output_without_false_closure' and r['kind']=='store' and r['controlled_API'] is True and r['closed'] is False and len(r['pending'])==1 and r['pending'][0]['kind']=='file_open' and r['pending'][0]['retry']=='UNCERTAIN' and r['pending'][0]['handle'] is None for r in pending_bindings))
    check('composition45_native_journals_closed',len(native['composition_receipts'])==45 and all(r['sqlite_closed'] is True and r['connection_close_state']=='CLOSED' for r in native['composition_receipts']))
    failed_ids={row[0] for row in full['failure_details']+full['error_details']}
    failed_observer_receipts=[row for row in native['observer_receipts'] if row['test_id'] in failed_ids]
    gate=proof(full['native_case_proof'])[1];early=load(C/'NATIVE-CASE-EARLY-PROOF.json')
    check('native_case_early_and_final_same',gate==early)
    native_release_path,native_release=proof(release['native_case_release'])
    check('native_gate_release_exact_nonce',gate['release']==release['native_case_release'] and gate['run_nonce']==native_release['run_nonce']==gate['subject']['run_nonce'] and gate['subject']==native_release['subject'])
    check('native_gate_one_exact_denial',gate['entered'] is True and gate['attempted'] is True and gate['exact_native_calls']==[dict(step='restricted_CreateProcessW',returned=True,succeeded=False,winerror=2)] and type(gate['exact_native_calls'][0]['winerror']) is int)
    check('native_gate_all_terminal_predicates',gate['passed'] is True and gate['precise_denial_matched'] is True and gate['owned_fixture_resources_closed'] is True and gate['release_reader_closed'] is True and gate['no_profile_create_delete'] is True and gate['issues']==[] and gate['diagnostic'] is None)
    check('seven_exact_handle_retirements',len(gate['handles'])==7 and all(r['close_attempted'] is True and r['closed'] is True and r['post_close_error']==6 for r in gate['handles']))
    check('three_exact_socket_retirements',len(gate['sockets'])==3 and all(r['close_attempted'] is True and r['closed'] is True and r['fileno']==-1 for r in gate['sockets']))
    queries=gate['profile_folder_observations'];setup=gate['original_probe_receipt']['value']['setup']
    check('two_exact_absent_folder_observations',[r['stage'] for r in queries]==['before','after'] and all(r['HRESULT']==-2147024894 and r['path'] is None and r['absent'] is True and r['allocation_closed'] is True and r['primary'] is None and r['cleanup'] is None for r in queries))
    check('fresh_single_no_profile_name',queries[0]['name']==queries[1]['name']==setup['container_name'] and queries[0]['sid']==queries[1]['sid']==setup['appcontainer_sid'] and setup['persistent_profile_install'] is False and Path(setup['fixture']).is_relative_to(C))
    probe_path,probe=proof(gate['original_probe_receipt']['reference']);check('original_probe_bytes_match',probe==gate['original_probe_receipt']['value'])
    check('ordinary_control_exact_retirement',len(probe['cleanup'])==1 and probe['cleanup'][0]['kind']=='trusted_medium_fixture' and probe['cleanup'][0]['pid']==probe['trusted_target']['pid'] and probe['cleanup'][0]['creation_time']==probe['trusted_target']['creation_time'] and probe['cleanup'][0]['exit_code']==125 and probe['cleanup'][0]['active_processes']==0 and probe['cleanup'][0]['lifetime_closed'] is True)
    check('original_restricted_failure_is_expected',probe['failure_type']=='ContractError' and probe['failure']=='ISOLATION_RESTRICTED_CREATE_FAILED:2 at $' and probe['raw_stdout']=='')
    check('single_native_case_event',sum(r['event']=='START' and r['test_id']==packet['original_case_id'] for r in events)==1)
    continuity=proof(release['operation_equivalence'])[1];auth=proof(release['operator_authorization'])[1]
    check('actual_human_authorization_reference',release['operator_authorization']['sha256']=='2de12485ef5fa2b204a1c5648667b2446105aebf16378238379455f6799ec2b0' and auth['executions_per_phase']==1 and continuity['prior_no_profile_attempts']==0 and continuity['original_operation_unchanged'] is True)
    check('Root_release_all_three_candidate_claims',release['phase']==PHASE and release['packet']==ref(D/'PACKET.json') and release['automatic_retry'] is False and release['create_profiles'] is False)
    state=proof(release['historical_lease_observation']['state'])[1];claims=proof(release['historical_lease_observation']['claims'])[1]
    check('historical_three_claims_RUNNING',all(state['nodes'][n]['state']=='RUNNING' and claims[n]['executor_id']=='/root' for n in ('implement','candidate_fixtures','candidate_cache')))
    for field,phase in [('native_store_corroboration','native-store'),('native_observer_corroboration','native-observer')]:
        check('fresh_packet_native_corroboration:'+phase,scope['require_native_corroboration'](release[field],phase)['accepted'] is True)
    native_review_path=F/'.agents/runtime/js9-r3-native-results-review-20261020/review.json';native_review=load(native_review_path)
    check('distinct_actual_native_review_approved',native_review['decision']=='approved' and native_review['packet']==ref(D/'PACKET.json'))
    preflight=load(C/'PREFLIGHT.json');check('preflight_exact_inputs',preflight['expected_ids']==expected and preflight['root']==str(q) and preflight['before_hashes']==manifest['payload_hashes'] and preflight['native_case_release']==release['native_case_release'] and preflight['product_deadline_changes'] is False)
    check('all_product_imports_from_Q5',len(preflight['product_modules'])==len(packet['product_modules']) and {r['path'] for r in preflight['product_modules']}=={str(q/n) for n in packet['product_modules']})
    check('frozen_evidence_stable_after_verification',all(sha(F/name)==pin for name,pin in refs.items()))
    check('no_prohibited_reviewer_operations',denied==[])
    return dict(candidate_accepted=admitted,admission_error=admission_error,failures=full['failures'],errors=full['errors'],skips=full['skips'],failure_details=full['failure_details'],error_details=full['error_details'],diagnostic_events=diagnostic_events,
        packet=ref(D/'PACKET.json'),candidate_manifest=packet['candidate_manifest'],full_result=ref(C/'RESULT.json'),
        launch=ref(D/'candidate-full-LAUNCH-RESULT.json'),Root_terminal=ref(ROOT/'candidate-full-TERMINAL.json'),
        actual_child=launch['record']['native_owner'],exact_cases=len(expected),events=len(events),
        pretest_collection_count=len(collection),gc_event_count=len(full['gc_events']),
        physical=dict(sqlite=len(physical['sqlite']),streams=len(physical['streams']),descriptors=len(physical['os_descriptors']),native_service_owners=len(physical['native_owners'])),
        native=dict(process_owners=len(native['native_owners']),clocks=len(native['clock_owners']),bindings=len(native['bindings']),pending_controlled_API_records=len(pending_api),pending_controlled_bindings=len(pending_bindings)),
        failed_observer_receipts=failed_observer_receipts,
        original_case=dict(nonce=gate['run_nonce'],folder_name=setup['container_name'],control=probe['cleanup'][0],restricted_winerror=2,handles=7,sockets=3),
        run_started_at=full['started_at'],run_finished_at=full['finished_at'],Root_started_at=root_terminal['started_at'],Root_finished_at=root_terminal['finished_at'],
        Source_baseline=ref(baseline_path),accepted_Source352_conserved=True,Source_publication=False,whole_product_acceptance=False,
        receipt_admission_ASTs=[dict(name=n.name,line=n.lineno,ast_sha256=digest(ast.dump(n,include_attributes=False).encode())) for n in body])

try:
    result=run()
except BaseException as error:
    record=dict(at=datetime.now(timezone.utc).isoformat(),status='VERIFICATION_REJECTED_OR_BLOCKED',error_type=type(error).__name__,error_message=str(error),controls=controls,evidence=refs,denied_reviewer_events=denied)
    with (OUT/'VERIFICATION-FAILURE.json').open('x',encoding='utf8') as stream:json.dump(record,stream,indent=2);stream.write('\n')
    raise
else:
    record=dict(at=datetime.now(timezone.utc).isoformat(),status='VERIFIED_CANDIDATE_ACCEPTED' if result['candidate_accepted'] else 'VERIFIED_CANDIDATE_REJECTED',reviewer='/root/recovery_join_review20',mode='FILE_ONLY_RETAINED_ACTUAL_FULL_RESULT',
        passed=len(controls),failed=0,controls=controls,evidence=refs,result=result,
        no_test_native_process_profile_database_rerun=True,no_CLI_claim_yet=True,
        controlled_uncertainty_limit='Accounted pure negative records remain explicitly uncertain; actual native owners and physical SQLite resources must close.',
        actual_receipt_function_ASTs=result['receipt_admission_ASTs'],
        limits=['File-only Source/Git/retirement review; no live system-wide process or profile scan.',
            'One expected denied restricted launch is not positive isolation or a governed application effect.',
            'This is candidate-full acceptance only; Source31 publication/destination/new baseline/product acceptance remain separate.'])
    with (OUT/'VERIFICATION.json').open('x',encoding='utf8') as stream:json.dump(record,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(passed=len(controls),result=result,verification=ref(OUT/'VERIFICATION.json')),indent=2))
