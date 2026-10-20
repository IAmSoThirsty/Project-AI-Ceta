"""File-only verification of retained R3 native results. No native/test rerun."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import ast,copy,hashlib,json,os,stat,sys,types

F=Path('T:/00-Active/Project-AI-CETA')
D=F/'.agents/runtime/js9-runtime-20261020/successor-r3'
ROOT=F/'.agents/runtime/js9-root-r3-execution-20261020'
OUT=Path(__file__).resolve().parent
controls=[];denied=[]
def audit(event,args):
    if event=='ctypes.dlopen' or event.startswith(('subprocess.','socket.')) or event in ('sqlite3.connect','os.system','os.startfile','os.posix_spawn','os.fork'):
        denied.append(event);raise RuntimeError('FILE_ONLY_REVIEW_DENIES:'+event)
    if event=='open':
        p,mode,flags=args
        writing=isinstance(mode,str) and any(c in mode for c in 'wax+') or isinstance(flags,int) and bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        if writing and (not isinstance(p,(str,bytes,os.PathLike)) or not Path(os.fsdecode(p)).resolve().is_relative_to(OUT)):
            denied.append(event);raise RuntimeError('WRITE_OUTSIDE_REVIEW_SCOPE')
sys.addaudithook(audit)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def sha(p):return digest(p.read_bytes())
def load(p):return json.loads(p.read_bytes())
def check(name,value,**evidence):
    assert value,(name,evidence)
    controls.append(dict(name=name,passed=True,**evidence))
def ref(path):return dict(repository_relative_path=path.relative_to(F).as_posix(),sha256=sha(path))
def ordinary(path):
    before=path.lstat();check_no_reparse=not before.st_file_attributes&1024
    assert check_no_reparse and stat.S_ISREG(before.st_mode)
    raw=path.read_bytes();after=path.lstat();assert before==after
    return dict(path=str(path),bytes=len(raw),sha256=digest(raw),native_identity=dict(bytes=before.st_size,mtime_ns=before.st_mtime_ns,mode=stat.S_IMODE(before.st_mode),device=before.st_dev,inode=before.st_ino,attributes=before.st_file_attributes))
def proof_bytes(reference):
    assert type(reference) is dict and set(reference)=={'repository_relative_path','sha256'}
    name=reference['repository_relative_path'];assert type(name) is str and '\\' not in name
    assert name and not Path(name).drive and all(p not in ('','.','..') for p in name.split('/'))
    path=F/name;raw=path.read_bytes();assert digest(raw)==reference['sha256']
    return path,raw
def proof(reference):
    path,raw=proof_bytes(reference);return path,json.loads(raw)
packet=load(D/'PACKET.json');manifest=load(D/'MANIFEST-Q5.json');q=Path(manifest['candidate'])
v=proof(packet['environment'])[1];source_before=proof(packet['Source_before'])[1]
check('final_packet',sha(D/'PACKET.json')=='32575147e478c63ead51c6269af9e22eebe06ccdc74619cdb04e46231fe9ac82')
check('final_manifest',sha(D/'MANIFEST-Q5.json')=='cce2c8e2c3a31fbedf5c2d83b2d15d499a93030c38ebe0c1e4545b868ef99acf')
check('all12_scripts_current',len(packet['scripts'])==12 and all(sha(D/name)==pin for name,pin in packet['scripts'].items()))
check('all541_candidate_hashes_current',len(manifest['payload_hashes'])==541 and all(sha(q/name)==pin for name,pin in manifest['payload_hashes'].items()))
observed_source={}
for name,row in source_before['targets'].items():
    observed_source[name]=None if row is None and not (F/name).exists() else ordinary(F/name)
check('current_Source_before_native_facts_and_absences_match',observed_source==source_before['targets'],targets=len(observed_source))
baseline_path=F/'.agents/runtime/js8-20261015/amendment-report1/ACCEPTED-SOURCE-BASELINE.json';baseline=load(baseline_path)
check('accepted_Source352_bytes_conserved',len(baseline['effective_payload_hashes'])==352 and all(sha(F/name)==pin for name,pin in baseline['effective_payload_hashes'].items()))
environment_root=Path(v['python']['path']).parents[1]
env_actual={}
for directory,dirs,files in os.walk(environment_root,followlinks=False):
    for name in dirs:assert not (Path(directory)/name).lstat().st_file_attributes&1024
    for name in files:
        path=Path(directory)/name;env_actual[path.relative_to(environment_root).as_posix()]=ordinary(path)
check('current_E3_inventory_and_native_facts_exact',env_actual==v['environment_files'],files=len(env_actual))
check('current_python_and_base_python_facts',ordinary(Path(v['python']['path']))==v['python'] and ordinary(Path(v['base_python']['path']))==v['base_python'])
check('current_fixture_dependency_facts',all(ordinary(Path(row['path']))==row for row in packet['fixture_dependencies'].values()))
git_head=(F/'.git/HEAD').read_text().strip();assert git_head.startswith('ref: refs/heads/')
branch=git_head.removeprefix('ref: refs/heads/');gitref=F/'.git'/git_head.removeprefix('ref: ')
check('file_only_current_Git_HEAD_and_branch',branch==packet['Git']['branch'] and gitref.read_text().strip()==packet['Git']['HEAD'])

# Replay the exact receipt-admission function ASTs against pinned actual JSON and file-only readers.
tree=ast.parse((D/'js9_support.py').read_text(encoding='utf8'))
names={'require_native_terminal','require_native_corroboration','interpreter_observation'}
body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
assert {n.name for n in body}==names
scope=dict(Path=Path,R=D,F=F,sys=sys,s=types.SimpleNamespace(ordinary=ordinary),proof=proof,proof_bytes=proof_bytes,
    packet=lambda:packet,exact_ref=ref,inputs=lambda:v)
exec(compile(ast.Module(body=body,type_ignores=[]),str(D/'js9_support.py'),'exec'),scope)
cohorts={};facts=[]
for phase,label,leaf in [('native-store','native_store_r3','RESULT.json'),('native-observer','native_observer_r3','native.json')]:
    path=D/label/leaf;terminal=load(path);corrob_path=D/(label+'-CORROBORATION.json');corrob=load(corrob_path)
    root_terminal=load(ROOT/(phase+'-TERMINAL.json'));root_command=load(ROOT/(phase+'-COMMAND.json'))
    release_path,release=proof(terminal['release'])
    expected=packet['native_store_ids' if phase=='native-store' else 'native_observer_ids']
    check('actual_terminal_admitted:'+phase,scope['require_native_terminal'](ref(path),phase)==terminal)
    check('actual_parent_corroboration_admitted:'+phase,scope['require_native_corroboration'](ref(corrob_path),phase)==corrob)
    check('root_terminal_exact0:'+phase,type(root_terminal['exit_status']) is int and root_terminal['exit_status']==0 and root_terminal['command_returned'] is True and root_terminal['execution_error'] is None)
    check('Root_command_matches_terminal:'+phase,root_command['argv']==root_terminal['argv'] and root_command['cwd']==root_terminal['cwd']==str(D))
    check('Root_command_exact_R3:'+phase,root_terminal['argv']==[v['python']['path'],'-B','-X','utf8',str(D/'launch_native.py'),phase,label,'--release-path',str(release_path),'--release-sha256',terminal['release']['sha256']])
    check('Root_raw_output_hashes:'+phase,sha(ROOT/(phase+'.stdout'))==root_terminal['stdout_sha256'] and sha(ROOT/(phase+'.stderr'))==root_terminal['stderr_sha256'])
    output=Path(ROOT/(phase+'.stdout')).read_text(encoding='utf8').strip().splitlines()
    last=json.loads(output[-1])
    check('Root_stdout_exact_parent_receipt:'+phase,last==dict(receipt=ref(corrob_path),accepted=True,child_exit=0))
    check('retained_launch_owner_matches:'+phase,load(D/(label+'-LAUNCH-OWNER.json'))==corrob['native_child_process']['native_owner'])
    attempt=load(D/(label+'-LAUNCH-ATTEMPT.json'))
    check('one_shot_attempt_binding:'+phase,attempt['phase']==phase and attempt['child_argv']==corrob['native_child_argv'] and attempt['packet']==ref(D/'PACKET.json') and attempt['release']==terminal['release'] and attempt['automatic_retry'] is False)
    check('release_exact_phase_and_review:'+phase,release['phase']==phase and release['packet']==ref(D/'PACKET.json') and release['candidate_manifest']==packet['candidate_manifest'] and release['reviewed_scripts']==packet['scripts'] and proof(release['independent_review'])[1]['decision']=='approved')
    historic=release['historical_lease_observation'];claims=proof(historic['claims'])[1];state=proof(historic['state'])[1]
    claim=claims['implement']
    check('historical_actual_implement_lease:'+phase,claim['executor_id']=='/root' and Path(claim['workspace'])==D and state['nodes']['implement']['state']=='RUNNING' and claim['input_hash']==release['execution_lease']['input_hash']==state['nodes']['implement']['claim']['input_hash'])
    check('lease_frozen_copy_exact_release_ref:'+phase,historic['claims']['sha256']==release['execution_lease']['claims']['sha256'] and historic['state']['sha256']==release['execution_lease']['state']['sha256'])
    check('recorded_Git_parent_and_child_preflight:'+phase,corrob['Git_observed']==packet['Git'] and terminal['Git_corroboration']==dict(status='PENDING_ROOT_CORROBORATION',before=packet['Git'],after=None) and terminal['acceptance_complete'] is False)
    rawpath=D/label/('RAW.txt' if phase=='native-store' else 'native.txt');raw=rawpath.read_text(encoding='utf8')
    check('raw_all_exact_case_results:'+phase,all('('+name+') ... ok' in raw for name in expected) and 'Ran '+str(len(expected))+' tests' in raw and raw.rstrip().endswith('OK'))
    check('no_errors_failures_skips:'+phase,terminal['failures']==terminal['errors']==terminal['skips']==[])
    owner=corrob['native_child_process'];assert all(value is True for value in owner['native_owner_after'].values())
    if phase=='native-store':
        check('store_exact_START_STOP_alternation',[(row['event'],row['id']) for row in terminal['events']]==[(kind,name) for name in expected for kind in ('START','STOP')])
        physical=terminal['physical_custody']
        check('store_all_SQLite_objects_physically_closed',bool(physical['sqlite']) and all(row['physical_closed_probe'] is True and row['probe_observation']=='Cannot operate on a closed database.' for row in physical['sqlite']))
        check('store_all_captured_streams_physically_closed',all(row['closed'] is True and row['fileno_denied'] is True for row in physical['streams']))
        check('store_no_remaining_captured_resources',physical['owned_resources_closed'] is True and physical['remaining_resources']==[] and terminal['remaining_threads']==[])
        check('store_all_retained_binding_custody_closed',len(terminal['binding_custody'])==20 and all(row['closed'] is True and row['pending']==[] for row in terminal['binding_custody']))
        sqlite=terminal['sqlite_runtime']
        check('store_exact_loaded_SQLite_files',sha(Path(sqlite['dll_path']))==sqlite['dll_sha256'] and sha(Path(sqlite['wrapper_path']))==sqlite['wrapper_sha256'])
        details=dict(binding_custody=len(terminal['binding_custody']),physical_SQLite_objects=len(physical['sqlite']),streams=len(physical['streams']),SQLite_database_paths_missing=sum(row['database'] is None for row in physical['sqlite']))
    else:
        check('observer_exact_ids_and_no_threads',terminal['expected_ids']==terminal['executed_ids']==terminal['stopped_ids']==expected and terminal['new_threads_remaining']==[])
        check('observer_all_nominal_launches_exact',len(terminal['launches'])==17 and all(row['returned'] is True and type(row['pid']) is int and type(row['creation_time']) is int for row in terminal['launches']))
        count_images=Counter(row['expected_image_sha256'] for row in terminal['launches'])
        check('observer_eight_targets_nine_helpers',count_images=={packet['fixture_dependencies']['worker']['sha256']:8,packet['fixture_dependencies']['observer']['sha256']:9})
        for group in terminal['custody']:
            check('observer_closed_custody:'+group['kind'],group['count']==len(group['rows']) and group['all_closed'] is True and all(row['closed'] is True for row in group['rows']))
        process=next(g for g in terminal['custody'] if g['kind']=='owned_process')
        check('observer_exact_owned_process_handle_retirement',len(process['rows'])==17 and all(row['process_handle'] is None and row['job_handle'] is None and row['thread_handle'] is None and row['cleanup_handles']==[] and row['query_exports']==0 for row in process['rows']))
        check('observer_recorded_images_match_retained_processes',{(r['pid'],r['creation_time'],r['image_sha256']) for r in process['rows']}=={(r['pid'],r['creation_time'],r['expected_image_sha256']) for r in terminal['launches']})
        check('observer_no_forbidden_or_source_changes',terminal['forbidden_events']==[] and terminal['before']==terminal['after']==manifest['payload_hashes'] and terminal['run_error'] is None)
        check('observer_successor_import_origins',all(Path(path).is_relative_to(q/'src') for path in terminal['imports'].values()))
        check('observer_raw_log_hash',sha(rawpath)==terminal['raw_sha256'])
        observations=[item for row in terminal['native_receipts'] for item in row['observations']]
        raw_frames=[item for item in observations if 'raw_bytes' in item]
        check('observer_all_retained_raw_bytes_hashes',all(digest(bytes.fromhex(item['raw_bytes']['hex']))==item['raw_bytes']['sha256']==item['raw_sha256'] for item in raw_frames))
        check('observer_all_original_fixture_cleanup_receipts',all(row['cleanup_failures']==[] and row['clock_closed'] is True and all(t['lifetime_closed'] is True and t['remaining_query_exports']==0 for t in row['closed_targets']) for row in terminal['native_receipts']))
        details=dict(nominal_processes=17,targets=8,observer_helpers=9,custody_groups={g['kind']:g['count'] for g in terminal['custody']},native_fixture_receipts=len(terminal['native_receipts']),retained_observations=len(observations),raw_frames=len(raw_frames),controlled_observation_failures=Counter(str(item.get('failure')) for item in observations if item.get('failure') is not None),exit_codes=Counter(str(row['exit_code']) for row in process['rows']))
    cohorts[phase]=dict(terminal=ref(path),parent_corroboration=ref(corrob_path),root_command=ref(ROOT/(phase+'-COMMAND.json')),root_terminal=ref(ROOT/(phase+'-TERMINAL.json')),raw=ref(rawpath),tests=len(expected),root_started_at=root_terminal['started_at'],root_finished_at=root_terminal['finished_at'],native_child_owner=owner['native_owner'],native_child_exit=owner['child_exit'],retirement=owner['native_owner_after'],details=details)
    facts.extend([ref(path),ref(corrob_path),ref(ROOT/(phase+'-TERMINAL.json')),ref(D/(label+'-LAUNCH-OWNER.json')),ref(D/(label+'-LAUNCH-ATTEMPT.json')),ref(release_path),ref(rawpath),ref(ROOT/(phase+'.stdout')),ref(ROOT/(phase+'.stderr'))])

check('cohort_case_sets_disjoint',not set(packet['native_store_ids'])&set(packet['native_observer_ids']))
check('two_distinct_retained_child_lifetimes',len({(row['native_child_owner']['pid'],row['native_child_owner']['creation_time']) for row in cohorts.values()})==2)
check('no_prohibited_reviewer_operations',denied==[])
report=dict(at=datetime.now(timezone.utc).isoformat(),reviewer='/root/recovery_join_review20',mode='FILE_ONLY_RETAINED_ACTUAL_RESULT_VERIFICATION',
    packet=ref(D/'PACKET.json'),candidate_manifest=ref(D/'MANIFEST-Q5.json'),Source_baseline=ref(baseline_path),
    controls=controls,passed=len(controls),failed=0,cohorts=cohorts,evidence=facts,
    exact_admission_functions=[dict(name=n.name,line=n.lineno,ast_sha256=digest(ast.dump(n,include_attributes=False).encode())) for n in body],
    actual_native_test_rerun=False,actual_Git_subprocess_rerun=False,current_Git_check='File-only HEAD/ref observation plus retained actual parent default-verification witness',
    Source_publication=False,product_acceptance=False,profile_authorization_issued=False,
    limits=['Retirement is verified from exact retained owner/resource records and their source-bound probes. No current process, handle, profile or system-wide scan was performed.',
        'All19 recorded SQLite objects have positive physical closed probes; their database path fields are null, so this receipt is not an exact SQLite-path inventory.',
        'Observer negative-case receipts intentionally contain rejected/control observations, including diagnostic failures; actual unittest failures/errors/skips are empty.',
        'The native observer child receipt has no exit_status field; its actual parent child_exit0 and Root terminal0 establish process termination status.',
        'This acceptance covers only the two engineering cohorts. Candidate-full, publication, destination-full, governed real effect and whole-product acceptance remain separate.'])
with (OUT/'VERIFICATION.json').open('x',encoding='utf8') as stream:json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
print(json.dumps(dict(passed=len(controls),failed=0,verification=ref(OUT/'VERIFICATION.json'),cohorts=cohorts),indent=2))
