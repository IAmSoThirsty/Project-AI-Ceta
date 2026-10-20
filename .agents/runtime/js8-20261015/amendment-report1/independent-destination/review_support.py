"""Exact Source180 release, fixture routing and reused native7 observation."""
from pathlib import Path
import ast
import functools
import importlib
import json
import os
import sys

F=Path('T:/00-Active/Project-AI-CETA');R=F/'.agents/runtime/js8-20261015/amendment-report1';Q=F/'.agents/js8-amendment-report1-20261017'
V=Path(__file__).resolve().parent;ACTOR='/root/publication_recovery_review'
PIN='2a3abde78bd4ab25af268ad1b16cef9eeaf9e2c30586c06fac4600876ba3c7c6'
AMENDMENT_PIN='ad3091e4ac129d0efcecae70b45ff15d45d6dedcc0c52dc30efead3714929776'
sys.path.insert(0,str(R))
import amendment_support as j
from amendment_support import s,PY
HELPERS=('review_support.py','resource_observer.py','bounded_custody.py','resource_witness.py',
    'run_delivered.py','launch_delivered.py','record_actual_delivered_review.py')

def helper_pins():return {name:s.ordinary(V/name)['sha256'] for name in HELPERS}

def preparation():
    p=j.current_json(V/'PREPARATION.json')
    assert p['manifest_sha256']==PIN and s.sha(Q/'TRANSFER-MANIFEST.json')==PIN
    assert p['amendment']==j.exact_ref(R/'AMENDMENT.json') and p['amendment']['sha256']==AMENDMENT_PIN
    assert p['required_ids']==j.manifest()['required_independent_ids'] and len(p['required_ids'])==180
    assert p['expected_payload_hashes']==j.manifest()['expected_payload_hashes']
    assert p['helpers']==helper_pins()
    return p

def require_delivery_release(path,pin):
    path=s.fs.safe_components(Path(path));assert path.parent==R/'releases'
    value=j.pinned_json(path,pin);m=j.manifest();p=preparation()
    assert type(value['schema_version']) is int and value['schema_version']==1
    assert value['phase']=='DELIVERY-REVIEW' and value['executor']=='/root' and value['reviewer']==ACTOR
    assert value['manifest_sha256']==PIN and value['reviewer_helpers']==helper_pins()
    assert value['amendment']==p['amendment'] and value['preparation']==j.exact_ref(V/'PREPARATION.json')
    assert value['fixture_root']==p['fixture_root'] and value['one_attempt'] is True
    assert value['automatic_retry'] is False and type(value['timeout_seconds']) is int and value['timeout_seconds']==600
    assert value['Source_publication'] is False and value['all_conflicting_Source_runs_released'] is True
    assert value['profile_operations'] is False and value['restricted_launch'] is False
    assert value['native_cpu_case_ids']==p['native_cpu_ids']
    assert value['completion_script_sha256']==m['scripts']['complete_source.py']==s.sha(R/'complete_source.py')
    _,helper=j.proof(value['completion_helper_review'])
    assert helper['reviewer']==ACTOR and helper['decision']=='approved'
    assert type(helper['exit_status']) is int and helper['exit_status']==0
    assert helper['manifest_sha256']==PIN and helper['completion_script_sha256']==value['completion_script_sha256']
    claim=j.require_current_claim()
    assert value['claim_input_hash']==claim['input_hash'] and value['claim_started_at']==claim['claimed_at']
    j.require_candidate_readiness(value['candidate_readiness'],source='after')
    j.require_validation(value['candidate_readiness'],source='after')
    for phase in ('destination-full',):
        proof_path,full=j.proof(value[phase.replace('-','_')])
        launch_path,launch=j.proof(value[phase.replace('-','_')+'_launch'])
        assert proof_path==R/phase/'RESULT.json' and launch_path==R/(phase+'-LAUNCH-RESULT.json')
        j.require_full(full,launch,phase,value[phase.replace('-','_')])
    application_path,application=j.proof(value['application'])
    assert application_path==R/'active-application/APPLIED.json'
    assert application['paths']==m['application_paths'] and application['Source_accepted'] is False
    assert application['candidate_readiness']==value['candidate_readiness']
    assert set(application['source352'])==set(m['expected_payload_hashes'])
    for name,row in application['source352'].items():
        assert row['sha256']==m['expected_payload_hashes'][name] and s.ordinary(F/name)==row
    originals=j.inputs()['Source295'];required={name for name in m['application_paths'] if name in originals}
    assert set(application['native_backups'])==required and len(required)==4
    for name in required:
        backup=s.ordinary(R/'active-application/native-backups'/name)
        assert backup==application['native_backups'][name]
        assert backup['sha256']==originals[name]['sha256'] and backup['native_identity']==originals[name]['native_identity']
    j.verify(source='after')
    return value

class FixtureRoot:
    """Only test fixture globals change; Source and native guards stay exact."""
    def __init__(self,source,fixture):
        self.source=Path(source);self.fixture=Path(fixture);self.routes=[]
        assert self.fixture.is_relative_to(self.source/'.agents/fixtures')
    def __truediv__(self,value):
        part=Path(value)
        assert not part.is_absolute() and not part.drive and '..' not in part.parts
        if part.parts[:2]==('.agents','fixtures'):
            target=self.fixture.joinpath(*part.parts[2:]);assert target.is_relative_to(self.fixture)
            list.append(self.routes,str(target));return target
        return self.source/part
    def __fspath__(self):return str(self.source)
    def __str__(self):return str(self.source)

def route_fixture_globals(fixture):
    routed=[];mappers=[]
    for name,module in list(sys.modules.items()):
        path=getattr(module,'__file__',None)
        if not name.startswith('test_') or path is None or not Path(path).is_relative_to(F/'tests/contract'):continue
        for key,value in list(vars(module).items()):
            if type(value) is type(F) and value==F and key in ('ROOT','Q'):
                mapper=FixtureRoot(F,fixture);setattr(module,key,mapper);mappers.append(mapper);routed.append(name+'.'+key)
            elif isinstance(value,Path) and value.is_relative_to(F/'.agents/fixtures'):
                replacement=Path(fixture)/value.relative_to(F/'.agents/fixtures')
                setattr(module,key,replacement);routed.append(name+'.'+key)
    return routed,mappers

def verify_method_asts(required,expected):
    actual={}
    for identifier in required:
        module,cls,name=identifier.split('.');path=F/'tests/contract'/(module+'.py')
        target=next(node for node in ast.parse(path.read_bytes()).body if isinstance(node,ast.ClassDef) and node.name==cls)
        method=next(node for node in target.body if isinstance(node,ast.FunctionDef) and node.name==name)
        actual[identifier]=s.digest(ast.dump(method,include_attributes=False).encode())
    assert actual==expected
    return actual

def deny_profile_and_restricted_operations():
    """Native7 is ordinary-worker only; no restricted case is selected."""
    forbidden=[]
    def audit(event,args):
        if event=='ctypes.dlsym' and len(args)>1 and args[1] in (
            'CreateAppContainerProfile','DeleteAppContainerProfile','CreateProcessAsUserW',
            'CreateProcessWithTokenW','LogonUserW'):
            forbidden.append(args[1]);raise RuntimeError('DELIVERY_PROFILE_TOKEN_OPERATION_FORBIDDEN')
    sys.addaudithook(audit)
    from ceta.supervisor import isolated_worker
    original=isolated_worker._IsolationAPI.__init__
    @functools.wraps(original)
    def guarded(api,*args,**kwargs):
        original(api,*args,**kwargs)
        def restricted(*args,**kwargs):
            forbidden.append('restricted_CreateProcessW');raise RuntimeError('DELIVERY_RESTRICTED_LAUNCH_FORBIDDEN')
        api.CreateProcessW=restricted
        for name in ('CreateAppContainerProfile','DeleteAppContainerProfile'):
            def denied(*args,_name=name,**kwargs):
                forbidden.append(_name);raise RuntimeError('DELIVERY_PROFILE_OPERATION_FORBIDDEN')
            setattr(api.userenv,name,denied)
    isolated_worker._IsolationAPI.__init__=guarded
    return forbidden,(isolated_worker._IsolationAPI,original)

class NativeSevenWitness:
    """Byte-exact accepted witness, scoped only to the last seven methods."""
    def __init__(self,fixture,active,stream):
        from resource_witness import Witness
        self.fixture=Path(fixture);self.active=active;self.stream=stream
        self.witness=Witness(lambda:active[0]);self.restores=[];self.installed=False
    def install(self):
        assert not self.installed
        from ceta.supervisor import windows_jobs as windows
        from ceta.identity import native_clock as clock
        from ceta.store import journal
        import test_windows_jobs as jobs
        import sqlite3,threading
        import bounded_custody as custody
        for cls,name in ((windows._API,'__init__'),(windows.WindowsOwnedProcess,'launch'),
            (jobs.WindowsJobTests,'setUp'),(journal.SqliteJournal,'__init__'),
            (clock.NativeSessionClock,'__init__'),(clock._NativeClockAPI,'__init__'),
            (threading.Thread,'start'),(threading.Thread,'join')):
            self.restores.append((cls,name,vars(cls)[name]))
        base=j.inputs()['base_python'];SystemRoot=os.environ['SystemRoot']
        assert str(jobs.BASE)==base['path']
        child_pin=preparation()['native_worker_program_sha256']
        assert s.digest(jobs.CHILD.encode('utf8'))==child_pin
        def worker_gate(executable,arguments,kwargs):
            assert executable==base['path'] and type(arguments) is tuple and len(arguments)==8
            assert arguments[:3]==('-B','-I','-c') and arguments[3]==jobs.CHILD and arguments[-1]=='7'
            assert all(type(v) is str for v in arguments)
            assert all(arguments[i].startswith('Local\\CETA-Owned-Job-Test-') and len(arguments[i].split('-')[-1])==32 for i in (4,5))
            cwd=Path(kwargs['cwd']);assert cwd.is_relative_to(self.fixture) and cwd.is_dir()
            assert Path(arguments[6])==cwd/'primary.json'
            assert kwargs['environment']=={'SystemRoot':SystemRoot,'TEMP':str(cwd),'TMP':str(cwd),'CETA_JOB_ENV':'explicit'}
            assert s.ordinary(Path(base['path']))==base
        def emit(owner):
            row=dict(test_id=self.active[0],object_id=id(owner),pid=owner.pid,
                creation_time=owner.creation_time,image_sha256=owner.image_sha256,
                retained_process_handle=int(owner._process),retained_job_handle=int(owner._job))
            text=json.dumps(row,allow_nan=False)+'\n';count=self.stream.write(text)
            assert count==len(text);self.stream.flush()
        self.installed=True
        self.witness.install(windows,jobs,clock,journal,sqlite3,custody,emit,
            lambda path:s.fs.file_identity(s.fs.lstat(path)),worker_gate)
    def uninstall(self):
        if self.installed:
            for cls,name,original in reversed(self.restores):setattr(cls,name,original)
            self.installed=False
    def finish(self):
        assert not self.installed
        result=self.witness.result()
        assert len(result['owners'])==len(result['journals'])==len(result['clocks'])==len(result['registrations'])==8
        return result
