"""Frozen JS9 engineering adapters; every effect requires a fresh Root release.

This module supplies no product authority and creates no release. Existing
native-file preservation and cleanup observers remain pinned dependencies.
"""
from pathlib import Path
import hashlib, importlib.util, json, os, shutil, stat, sys, time

R=Path(__file__).resolve().parent
F=Path('T:/00-Active/Project-AI-CETA')
Q=F/'.agents/js9-runtime-r5-20261020'
PY=F/'.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
RUN='js9-runtime-20261020'
AUTHOR='/root/recovery_regression20'
FOUNDATION=F/'.agents/runtime/js8-20261015/foundation_support.py'
assert hashlib.sha256(FOUNDATION.read_bytes()).hexdigest()=='3d429a51f846289438acdead20d4ec4ef875d8d199d571656423dd78b255b023'
spec=importlib.util.spec_from_file_location('js9_preservation_dependency',FOUNDATION)
s=importlib.util.module_from_spec(spec);sys.modules[spec.name]=s;spec.loader.exec_module(s)
# Only these in-process designations change. No old graph/receipt helper runs.
s.R=R;s.Q=Q;s.AUTHOR=AUTHOR

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
def retain(primary,secondary,stage,stream=None):
    try:
        data=BaseException.__dict__['__dict__'].__get__(primary)
        prior=dict.get(data,'publication_evidence_failures',())
        if type(prior) is not tuple:prior=()
        trace=BaseException.__dict__['__traceback__'].__get__(secondary)
        dict.__setitem__(data,'publication_evidence_failures',prior+((stage,secondary,trace),))
        if stream is not None:
            owners=dict.get(data,'publication_io_owners',())
            if type(owners) is not tuple:owners=()
            dict.__setitem__(data,'publication_io_owners',owners+((stage,stream),))
    except BaseException:pass

def close(stream,primary,stage):
    try:stream.close()
    except BaseException as secondary:
        if primary is None:retain(secondary,secondary,stage,stream);raise
        retain(primary,secondary,stage,stream)

def write_bytes(path,raw):
    path=Path(path);assert path.is_relative_to(R)
    stream=path.open('xb');primary=None
    try:
        count=stream.write(raw);assert type(count) is int and count==len(raw),'SHORT_WRITE'
        stream.flush();os.fsync(stream.fileno())
    except BaseException as error:primary=error;raise
    finally:close(stream,primary,'write-close')

def pinned_bytes(path,pin):
    before=s.ordinary(path);assert before['sha256']==pin,'PROOF_PIN_MISMATCH'
    stream=Path(path).open('rb');primary=None
    try:raw=stream.read()
    except BaseException as error:primary=error;raise
    finally:close(stream,primary,'read-close')
    assert s.digest(raw)==pin and s.ordinary(path)==before,'PROOF_CHANGED_DURING_READ'
    return raw

def pinned_json(path,pin):return json.loads(pinned_bytes(path,pin).decode('utf-8-sig'))
def current_json(path):return pinned_json(path,s.ordinary(path)['sha256'])
def exact_ref(path):return dict(repository_relative_path=Path(path).relative_to(F).as_posix(),sha256=s.ordinary(path)['sha256'])

def proof_bytes(reference):
    assert type(reference) is dict and set(reference)=={'repository_relative_path','sha256'}
    name=reference['repository_relative_path']
    assert type(name) is str and name and name==name.replace('\\','/')
    assert not Path(name).is_absolute() and not Path(name).drive
    assert all(part not in ('','.','..') for part in name.split('/'))
    path=F/s.fs.relative_name(name);s.fs.safe_components(path)
    return path,pinned_bytes(path,reference['sha256'])

def proof(reference):
    path,raw=proof_bytes(reference);return path,json.loads(raw.decode('utf-8-sig'))

def packet():
    value=current_json(R/'PACKET.json')
    assert value['run_id']==RUN and value['author']==AUTHOR
    for name,pin in value['scripts'].items():assert s.ordinary(R/name)['sha256']==pin
    return value

def manifest():
    p=packet();_,m=proof(p['candidate_manifest'])
    assert len(m['payload_hashes'])==p['candidate_payload_count']==541
    return dict(expected_payload_hashes=m['payload_hashes'],case_set=p['case_set'],
        application_paths=p['application_paths'],native_gate=dict(script=exact_ref(R/'native_case_gate.py'),
        original_case_id=p['original_case_id']),fixture_dependencies=p['fixture_dependencies'],
        product_modules=p['product_modules'],scripts=p['scripts'])

def manifest_reference():return packet()['candidate_manifest']
def inputs():return proof(packet()['environment'])[1]

def inventory(root):
    out={};pending=[Path(root)]
    while pending:
        parent=pending.pop()
        with os.scandir(parent) as entries:
            for entry in entries:
                path=parent/entry.name;info=s.fs.lstat(path);assert not s.fs.reparse(info)
                if stat.S_ISDIR(info.st_mode):pending.append(path)
                else:assert stat.S_ISREG(info.st_mode);out[path.relative_to(root).as_posix()]=s.ordinary(path)
    return out

def verify(*,source='before',environment=True,verify_git=True):
    assert Path(sys.executable)==PY and not sys.flags.optimize and os.name=='nt'
    p=packet();m=manifest();v=inputs();_,before=proof(p['Source_before'])
    for name,pin in m['expected_payload_hashes'].items():assert s.ordinary(Q/name)['sha256']==pin
    for name,row in before['targets'].items():
        target=F/name
        if source=='after' and name in p['application_paths']:
            assert s.ordinary(target)['sha256']==m['expected_payload_hashes'][name]
        elif row is None:
            try:s.fs.lstat(target)
            except FileNotFoundError:pass
            else:raise AssertionError('ABSENT_SOURCE_TARGET_NOW_EXISTS:'+name)
        else:assert s.ordinary(target)==row,('SOURCE_NATIVE_CAS_CHANGED',name)
    assert source in ('before','after')
    assert s.ordinary(PY)==v['python'] and s.ordinary(Path(sys._base_executable))==v['base_python']
    if environment:assert inventory(PY.parents[1])==v['environment_files']
    assert type(verify_git) is bool
    git=None
    if verify_git:
        git=dict(HEAD=s.fs.text_git(F,'rev-parse','HEAD'),branch=s.fs.text_git(F,'branch','--show-current'))
        assert git==p['Git']
    for row in p['fixture_dependencies'].values():assert s.ordinary(Path(row['path']))==row
    return dict(v,Git_observed=git)

def interpreter_observation(v):
    value=dict(sys_executable=sys.executable,sys_base_executable=sys._base_executable,
        python=s.ordinary(Path(sys.executable)),base_python=s.ordinary(Path(sys._base_executable)))
    assert value['sys_executable']==v['python']['path'] and value['sys_base_executable']==v['base_python']['path']
    assert value['python']==v['python'] and value['base_python']==v['base_python']
    return value

def require_case_ids(actual):
    _,cases=proof(packet()['case_set']);required=cases['expected_ids']
    assert type(actual) is list and len(actual)==len(set(actual))==cases['expected_count']
    assert actual==required and not any('_FailedTest' in name for name in actual)
    parent=cases['parent2334_ids'];assert len(parent)==2334
    assert [name for name in actual if name in set(parent)]==parent
    assert sum(name.startswith('reasoning.test_reasoning_integration.') for name in actual)==21
    assert sum(name.startswith('reasoning.test_reasoning_repairs.') for name in actual)==29
    return required

def ids(group):
    import unittest
    if isinstance(group,unittest.TestSuite):
        for item in group:yield from ids(item)
    else:yield group.id()

def ordered_suite(discovered,root,loader):
    """Retain every original case and explicitly load both namespace modules."""
    import importlib,unittest
    _,cases=proof(packet()['case_set'])
    def leaves(group):
        if isinstance(group,unittest.TestSuite):
            for item in group:yield from leaves(item)
        else:yield group
    tests=list(leaves(discovered))
    for name in cases['explicit_namespace_modules']:
        module=importlib.import_module(name)
        expected=Path(root)/'tests/contract'/Path(name.replace('.','/')+'.py')
        assert Path(module.__file__).resolve()==expected.resolve()
        tests.extend(leaves(loader.loadTestsFromModule(module)))
    mapping={test.id():test for test in tests}
    assert len(mapping)==len(tests),'DUPLICATE_DISCOVERED_CASE'
    assert set(mapping)==set(cases['expected_ids']),'DISCOVERED_CASESET_MISMATCH'
    return unittest.TestSuite(mapping[name] for name in cases['expected_ids'])

def require_full_result(reference,launch_reference,phase):
    path,value=proof(reference);_,launch=proof(launch_reference)
    assert path==R/phase/'RESULT.json'
    require_case_ids(value['expected_ids'])
    assert value['phase']==phase and value['manifest_sha256']==manifest_reference()['sha256']
    assert value['executed_ids']==value['stopped_ids']==value['expected_ids']
    assert value['tests_run']==len(value['expected_ids'])
    assert value['failures']==value['errors']==value['skips']==0
    assert value['suite_aborted'] is False and value['primary_error'] is None
    assert value['remaining_threads']==[] and value['captured_journal_fixtures_closed'] is True
    assert value['gc_observation_failed'] is False and value['source_unchanged'] is True
    assert value['before_hashes']==value['after_hashes']==manifest()['expected_payload_hashes']
    _,physical=proof(value['physical_custody']);_,native=proof(value['native_owners_proof'])
    _,gate=proof(value['native_case_proof'])
    assert physical['owned_resources_closed'] is True and native['owned_resources_closed'] is True
    assert gate['passed'] is True and gate['release_reader_closed'] is True
    assert value['exit_status']==launch['exit_status']==0
    assert launch['phase']==phase and launch['primary_error'] is None
    assert launch['record']['child_exit']==0 and launch['record']['child_result']==reference
    assert launch['record']['retirement_error'] is None and launch['record']['primary_error'] is None
    assert all(launch['record']['native_owner_after'].values())
    v=inputs();expected=interpreter_observation(v)
    assert value['interpreter']==launch['interpreter']==expected
    assert value['argv'][0]==v['base_python']['path'] and launch['child_argv'][0]==v['python']['path']
    assert value['argv'][1:]==launch['child_argv'][1:]
    return value

def require_native_terminal(reference,phase):
    """A child passing its component cases still requires parent Git evidence."""
    assert phase in ('native-store','native-observer')
    path,value=proof(reference);p=packet()
    assert path.is_relative_to(R) and path.parent!=R
    assert value['phase']==phase and value['packet']==exact_ref(R/'PACKET.json')
    assert value['candidate_manifest']==p['candidate_manifest']
    script='run_native_store.py' if phase=='native-store' else 'run_native_observer.py'
    assert value['runner_sha256']==p['scripts'][script]
    assert value['passed'] is True and value['post_CAS_verified'] is True
    assert value['acceptance_complete'] is False
    assert value['Git_corroboration']==dict(status='PENDING_ROOT_CORROBORATION',before=p['Git'],after=None)
    measured=value['interpreter'] if phase=='native-store' else value['interpreter_observation']
    assert measured==interpreter_observation(inputs())
    expected=p['native_store_ids'] if phase=='native-store' else p['native_observer_ids']
    assert value['expected_ids']==expected and value['tests_run']==len(expected)
    if phase=='native-store':
        assert [row['id'] for row in value['events'] if row['event']=='START']==expected
        assert [row['id'] for row in value['events'] if row['event']=='STOP']==expected
        assert not value['failures'] and not value['errors'] and not value['skips']
        assert value['primary_error'] is None and value['remaining_threads']==[]
        assert value['boundary_violations']==[] and value['physical_custody']['owned_resources_closed'] is True
        assert value['binding_custody'] and all(row['closed'] and not row['pending'] for row in value['binding_custody'])
    else:
        assert value['expected_ids']==value['executed_ids']==value['stopped_ids']
        assert not value['failures'] and not value['errors'] and not value['skips'] and value['run_error'] is None
        assert value['checks'] and all(item is True for item in value['checks'].values())
        assert value['custody'] and all(row['all_closed'] for row in value['custody'])
    return value

def require_native_corroboration(reference,phase):
    _,value=proof(reference);p=packet()
    assert value['phase']==phase and value['accepted'] is True
    assert value['status']=='ACCEPTED_NATIVE_ENGINEERING_SCOPE'
    assert value['packet']==exact_ref(R/'PACKET.json') and value['candidate_manifest']==p['candidate_manifest']
    terminal=require_native_terminal(value['native_terminal'],phase)
    assert value['native_release']==terminal['release']
    assert value['exit_status']==0 and value['primary_error'] is None
    assert value['parent_runner_sha256']==p['scripts']['launch_native.py']
    child=value['native_child_process']
    assert child['child_exit']==0 and child['child_result']==value['native_terminal']
    assert child['primary_error'] is None and child['retirement_error'] is None
    assert child['native_owner_after'] and all(item is True for item in child['native_owner_after'].values())
    v=inputs();script='run_native_store.py' if phase=='native-store' else 'run_native_observer.py'
    assert child['native_owner']['image_sha256']==v['python']['sha256']
    assert type(child['native_owner']['pid']) is int and child['native_owner']['pid']>0
    assert type(child['native_owner']['creation_time']) is int and child['native_owner']['creation_time']>0
    argv=value['native_child_argv']
    assert type(argv) is list and len(argv)==10 and argv[0]==v['python']['path']
    assert argv[1:5]==['-B','-X','utf8',str(R/script)]
    assert terminal['observed_argv']==[v['base_python']['path'],*argv[1:]]
    assert terminal['cwd']==value['native_child_cwd']==str(R)
    release_path,_=proof_bytes(value['native_release'])
    assert argv[6:]==['--release-path',str(release_path),'--release-sha256',value['native_release']['sha256']]
    expected_leaf='RESULT.json' if phase=='native-store' else 'native.json'
    assert value['native_terminal']['repository_relative_path']==(R/argv[5]/expected_leaf).relative_to(F).as_posix()
    assert value['Git_observed']==p['Git'] and value['environment']==p['environment']
    assert value['Source_before']==p['Source_before']
    _,before=proof(p['Source_before'])
    assert value['Source_observed']==before['targets']
    assert value['fixture_dependencies_observed']==p['fixture_dependencies']
    assert value['interpreter']==interpreter_observation(v)
    assert type(value['started_at_ns']) is type(value['finished_at_ns']) is int
    assert value['started_at_ns']<=value['finished_at_ns']
    _,release=proof(value['native_release'])
    assert release['issued_at_ns']<=value['started_at_ns']<release['expires_at_ns']
    assert value['source_publication'] is False and value['product_acceptance'] is False
    return value

def child_environment(temporary):
    _,value=proof(packet()['git_dependency'])
    assert s.ordinary(Path(value['git']['path']))==value['git']
    assert value['PATH']==str(Path(value['git']['path']).parent)+';'+value['system32']
    assert Path(shutil.which('git.exe',path=value['PATH']))==Path(value['git']['path'])
    return dict(SystemRoot=value['SystemRoot'],PATH=value['PATH'],TEMP=str(temporary),TMP=str(temporary),PYTHONDONTWRITEBYTECODE='1')

def require_release(path,pin,phase):
    assert phase in ('candidate-full','destination-full','native-observer','native-store','publish')
    path=s.fs.safe_components(Path(path));assert path.parent==R/'releases'
    value=pinned_json(path,pin);p=packet()
    assert type(value['schema_version']) is int and value['schema_version']==1
    assert value['executor']=='/root' and value['run_id']==RUN and value['phase']==phase
    assert value['packet']==exact_ref(R/'PACKET.json') and value['candidate_manifest']==p['candidate_manifest']
    assert value['reviewed_scripts']==p['scripts'] and value['case_set']==p['case_set']
    assert value['Source_before']==p['Source_before']
    assert value['automatic_retry'] is False and value['create_profiles'] is False
    assert value['Source_publication'] is (phase=='publish')
    assert value['all_conflicting_Source_pinned_runs_released'] is True
    assert type(value['issued_at_ns']) is type(value['expires_at_ns']) is int
    assert 0<value['expires_at_ns']-value['issued_at_ns']<=1_800_000_000_000
    assert value['issued_at_ns']<=time.time_ns()<value['expires_at_ns']
    _,review=proof(value['independent_review'])
    assert review['reviewer'] not in (AUTHOR,'/root') and review['author']==AUTHOR
    assert review['decision']=='approved' and type(review['exit_status']) is int and review['exit_status']==0
    assert review['packet']==value['packet'] and review['reviewed_scripts']==p['scripts']
    assert review['candidate_manifest']==p['candidate_manifest']
    if phase in ('candidate-full','destination-full'):
        native_path,_=proof_bytes(value['native_case_release']);assert native_path.parent==R/'releases'
    if phase in ('candidate-full','destination-full','publish'):
        require_native_corroboration(value['native_store_corroboration'],'native-store')
        require_native_corroboration(value['native_observer_corroboration'],'native-observer')
    return value

def native_case_subject(phase,nonce):
    assert phase in ('candidate-full','destination-full')
    assert type(nonce) is str and len(nonce)==32 and all(c in '0123456789abcdef' for c in nonce)
    m=manifest();v=inputs();root=F if phase=='destination-full' else Q
    payloads={name:s.ordinary(root/name) for name in m['expected_payload_hashes']}
    assert {name:row['sha256'] for name,row in payloads.items()}==m['expected_payload_hashes']
    environment=inventory(PY.parents[1]);assert environment==v['environment_files']
    environment['base_python']=s.ordinary(Path(v['base_python']['path']))
    tools={name:s.ordinary(R/name) for name in packet()['scripts']}
    for name,row in m['fixture_dependencies'].items():tools['fixture/'+name]=s.ordinary(Path(row['path']))
    return dict(run_id=RUN,run_nonce=nonce,mode=phase,original_case_id=packet()['original_case_id'],
        source_root=str(root),fixture_runtime=str(R/phase/'isolation-harness/.agents/runtime/ac1-20261014'),
        payload_map_sha256=s.digest(canonical(payloads).encode()),environment_sha256=s.digest(canonical(environment).encode()),
        tools_sha256=s.digest(canonical(tools).encode()),expected_ids_sha256=packet()['case_set']['sha256'],
        fixture_helper_sha256=m['fixture_dependencies']['isolation_helper']['sha256'],
        native_image_sha256=m['fixture_dependencies']['worker']['sha256'])

def capture_native_case_gate(release,phase):
    reference=release['native_case_release'];path,raw=proof_bytes(reference)
    value=json.loads(raw.decode('utf8'));nonce=value['run_nonce']
    gate_path=R/'native_case_gate.py'
    spec=importlib.util.spec_from_file_location('js9_frozen_native_case_gate',gate_path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module.NativeCaseGate.capture(path,reference['sha256'],expected_subject=native_case_subject(phase,nonce),
        snapshot=lambda:native_case_subject(phase,nonce),support=s,ports=sys.modules[__name__])
