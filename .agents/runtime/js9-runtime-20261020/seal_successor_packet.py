"""Read-only source/environment capture and static adapter packet sealing."""
from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,importlib.util,json,os,stat,sys

F=Path('T:/00-Active/Project-AI-CETA');R=Path(__file__).resolve().parent;D=R/'successor-r1'
Q=F/'.agents/js9-runtime-20261020';PY=F/'.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now(timezone.utc).isoformat()
def save(path,value):
    with path.open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2);stream.write('\n')
def reference(path):return dict(repository_relative_path=path.relative_to(F).as_posix(),sha256=sha(path))

foundation=F/'.agents/runtime/js8-20261015/foundation_support.py'
assert sha(foundation)=='3d429a51f846289438acdead20d4ec4ef875d8d199d571656423dd78b255b023'
spec=importlib.util.spec_from_file_location('js9_packet_read_only_preservation',foundation)
s=importlib.util.module_from_spec(spec);sys.modules[spec.name]=s;spec.loader.exec_module(s)
manifest=R/'MANIFEST-R4.json';assert sha(manifest)=='212f1913af6ef24c24041628d2dcca23c7b754849ba79de9db8d75a210b3f532'
m=json.loads(manifest.read_bytes());expected=m['payload_hashes']
assert len(expected)==530 and all(sha(Q/name)==pin for name,pin in expected.items())
targets={}
for name in sorted(expected):
    target=F/name
    try:s.fs.lstat(target)
    except FileNotFoundError:
        s.fs.safe_components(target,allow_missing=True);targets[name]=None
    else:targets[name]=s.ordinary(target)
changed=[name for name,row in targets.items() if (None if row is None else row['sha256'])!=expected[name]]
save(D/'SOURCE-BEFORE.json',dict(at=now(),targets=targets,
    source352=reference(F/'.agents/runtime/js8-20261015/amendment-report1/ACCEPTED-SOURCE-BASELINE.json'),
    reasoning_R3=reference(F/'.agents/runtime/reasoning-core-repair-20261020/R3-MANIFEST.json'),
    selected26=reference(F/'.agents/runtime/joined-runtime-readiness-20261020/MERGE-MAP-R2.json'),
    changed_or_new_paths=changed,Source_mutated=False))
files={};pending=[PY.parents[1]]
while pending:
    parent=pending.pop()
    with os.scandir(parent) as entries:
        for entry in entries:
            path=parent/entry.name;info=s.fs.lstat(path);assert not s.fs.reparse(info)
            if stat.S_ISDIR(info.st_mode):pending.append(path)
            else:assert stat.S_ISREG(info.st_mode);files[path.relative_to(PY.parents[1]).as_posix()]=s.ordinary(path)
save(D/'ENVIRONMENT.json',dict(at=now(),python=s.ordinary(PY),base_python=s.ordinary(Path(sys._base_executable)),environment_files=files))

scripts={}
for path in sorted(D.glob('*.py')):
    ast.parse(path.read_bytes());scripts[path.name]=sha(path)
dependencies={key:s.ordinary(F/name) for key,name in {
    'foundation':'.agents/runtime/js8-20261015/foundation_support.py',
    'preservation_reader':'.agents/pr4-20261014/preserve_ceta_complete.py',
    'raw_release_reader':'.agents/runtime/js7-20261015/publish_source.py',
    'publication_primitive':'.agents/runtime/rs2-20261014/apply_joined_source.py',
    'isolation_helper':'.agents/runtime/ac1-20261014/native_fixture_support.py',
    'worker':'.agents/runtime/ac1-20261014/build-r2/isolated_worker.exe',
    'observer':'.agents/runtime/ob2-20261014/build-reuse/effect_observer.exe',
    'capacity':'.agents/runtime/outcome-capacity-20261015/build-r2/outcome_capacity.dll',
    'approval_build':'.agents/runtime/na2-20261014/build-r1/build.json',
    'observer_build':'.agents/runtime/ob2-20261014/build-reuse/BUILD-REUSE.json',
}.items()}
assert dependencies['worker']['sha256']=='527518104fb84c430e3e9e0be61982c533b0c6fbb13e1a85e959ba1a3866ad0f'
assert dependencies['observer']['sha256']=='2cb69daab94b1225be228db19ce17393f1972a24ee5aa37d7b035bd30d1917f0'
assert dependencies['capacity']['sha256']=='5fe04c516ca120acf9cfb2c7cb65dfeca3786c24a0745049f26e9e06a9e8a665'
cases=json.loads((D/'CASESET.json').read_bytes());assert len(cases['expected_ids'])==2622
modules=sorted(name for name in expected if name.startswith('src/ceta/') and name.endswith('.py') and '/vendor/' not in name)
packet=dict(schema_version=1,at=now(),run_id='js9-runtime-20261020',author='/root/recovery_regression20',
    candidate_manifest=reference(manifest),case_set=reference(D/'CASESET.json'),
    Source_before=reference(D/'SOURCE-BEFORE.json'),environment=reference(D/'ENVIRONMENT.json'),
    git_dependency=reference(F/'.agents/runtime/js8-20261015/GIT-SEARCH-DEPENDENCY.json'),
    Git=dict(HEAD=s.fs.text_git(F,'rev-parse','HEAD'),branch=s.fs.text_git(F,'branch','--show-current')),
    scripts=scripts,fixture_dependencies=dependencies,application_paths=changed,product_modules=modules,
    original_case_id='test_isolated_worker.NativeIsolatedWorkerTests.test_actual_nonpersistent_launch_denial_and_medium_control_retirement',
    native_observer_ids=sorted(name for name in cases['expected_ids'] if name.startswith('test_native_observer_origin.NativeObserverOriginTests.')),
    native_store_ids=sorted(name for name in cases['expected_ids'] if name.startswith('test_native_owner_view.NativeStoreBindingTests.')),
    inactive_retained_vendor_payloads=150,source_baseline_status='Accepted JS8 Source352 plus separately pinned existing reasoning inputs; JS9 not published',
    execution='DORMANT_PENDING_DISTINCT_REVIEW_AND_ROOT_RELEASE',Source_publication=False,
    product_acceptance=False,host_profiles=False,adapter_deltas=reference(D/'ADAPTER-DELTAS.json'))
assert len(packet['native_store_ids'])==18 and len(packet['native_observer_ids'])==6
assert packet['Git']==dict(HEAD='83fc9432b4a37ee7f91d6c5b0d358a015548aed4',branch='candidate/societal-reasoning-v1')
save(D/'PACKET.json',packet)
result=R/'original_callers_r2/RESULT.json';caller=json.loads(result.read_bytes())
save(R/'TERMINAL-ORIGINAL-CALLERS-R2.json',dict(tool_start_chunk='267ee3',tool_terminal_chunk='e186c8',
    former_session_id=95460,terminal_exit_status=0,result=reference(result),
    tests_run=caller['tests_run'],actual_journals=caller['journals_created'],
    all_journals_closed=caller['all_journals_closed'],interpreter=caller['interpreter']))
save(D/'STATIC-PREPARATION.json',dict(at=now(),packet=reference(D/'PACKET.json'),
    parsed_scripts=len(scripts),exact_case_ids=2622,original_cases_preserved=2334,
    reasoning_original21=21,reasoning_repairs29=29,product_module_paths=len(modules),
    environment_files=len(files),current_targets=len(targets),changed_or_new_paths=len(changed),
    unmodified_native_process_custody_wrapper=True,
    controlled_unknown_open='Explicitly pending in the single exact pure test; native cleanup never claimed for that state',
    tests_run=False,native_operations=False,Source_publication=False,
    required_releases=['native-store18','native-observer6','candidate-full2622','publish','destination-full2622']))
print(json.dumps(dict(packet_sha256=sha(D/'PACKET.json'),scripts=len(scripts),cases=2622,
    product_modules=len(modules),environment_files=len(files),changed_or_new_paths=len(changed),
    caller_result_sha256=sha(result)),indent=2),flush=True)
