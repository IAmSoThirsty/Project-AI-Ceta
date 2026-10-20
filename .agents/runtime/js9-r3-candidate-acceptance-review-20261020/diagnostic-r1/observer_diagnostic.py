"""One dormant original-case diagnostic. Root must review the exact manifest first."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ast,copy,functools,hashlib,importlib,json,os,secrets,sys,threading,time,traceback,types,unittest

F=Path('T:/00-Active/Project-AI-CETA')
D=F/'.agents/runtime/js9-runtime-20261020/successor-r3'
Q=F/'.agents/js9-runtime-r5-20261020'
HERE=Path(__file__).resolve().parent;RUN=HERE/'run-once'
CASE='test_native_effect_observer.NativeEffectObserverTests.test_actual_overlong_native_pipe_output_is_rejected_and_retired'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(repository_relative_path=p.relative_to(F).as_posix(),sha256=sha(p))
def load(p):return json.loads(p.read_bytes())
def save(path,value):
    with path.open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')
def error_record(error):
    if error is None:return None
    try:message=str(error)
    except BaseException:message='<exception text unavailable>'
    try:trace=''.join(traceback.format_exception(type(error),error,BaseException.__dict__['__traceback__'].__get__(error)))
    except BaseException:trace='<exception traceback unavailable>'
    return dict(type=type(error).__name__,message=message,traceback=trace)
def method_ast():
    tree=ast.parse((Q/'tests/contract/test_native_effect_observer.py').read_text(encoding='utf8'))
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='NativeEffectObserverTests')
    method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='test_actual_overlong_native_pipe_output_is_rejected_and_retired')
    return hashlib.sha256(ast.dump(method,include_attributes=False).encode()).hexdigest()
def bootstrap(pin):
    path=HERE/'MANIFEST.json';assert sha(path)==pin
    m=load(path);assert m['case']==CASE and m['max_attempts']==1 and m['profiles'] is False
    assert sha(Path(__file__))==m['tool_sha256']
    assert method_ast()==m['original_method_ast_sha256']
    assert ref(D/'PACKET.json')==m['packet'] and m['packet']['sha256']=='32575147e478c63ead51c6269af9e22eebe06ccdc74619cdb04e46231fe9ac82'
    p=load(D/'PACKET.json');assert p['candidate_manifest']==m['candidate_manifest']
    for name,pin in p['scripts'].items():assert sha(D/name)==pin
    sys.path.insert(0,str(D));import js9_support as j
    v=j.verify(source='before')
    extra_verify(m,j)
    return m,j,v
def extra_verify(m,j):
    for key in ('negative_reuse','negative_build'):
        row=m[key];assert ref(F/row['repository_relative_path'])==row
    assert j.s.ordinary(Path(m['negative_source']['path']))==m['negative_source']
    for name,row in m['negative_images'].items():
        assert Path(row['path']).name==name and j.s.ordinary(Path(row['path']))==row
    assert ref(D/'bounded_custody.py')==m['bounded_custody']

def parent(args):
    assert args.execute_once and args.nonce is None
    m,j,v=bootstrap(args.manifest_sha256)
    nonce=secrets.token_hex(16);started=datetime.now(timezone.utc).isoformat()
    child_args=['-B','-X','utf8',str(Path(__file__)),'child','--manifest-sha256',args.manifest_sha256,'--nonce',nonce]
    save(HERE/'ATTEMPT.json',dict(started_at=started,manifest=ref(HERE/'MANIFEST.json'),nonce=nonce,
        argv=list(sys.orig_argv),child_argv=[v['python']['path'],*child_args],cwd=str(HERE),timeout_seconds=120,automatic_retry=False))
    RUN.mkdir(exist_ok=False);temporary=RUN/'temporary';temporary.mkdir()
    environment=j.child_environment(temporary)
    sys.path.insert(0,str(Q/'src'))
    from ceta.supervisor.windows_jobs import WindowsOwnedProcess
    from bounded_custody import run_owned
    primary=record=child=None
    def launch():return WindowsOwnedProcess.launch(v['python']['path'],child_args,cwd=str(HERE),environment=environment,expected_image_sha256=v['python']['sha256'])
    def emit(owner):save(RUN/'OWNER.json',owner)
    def read_child():
        nonlocal child
        child=load(RUN/'child/RESULT.json')
        assert child['manifest']==ref(HERE/'MANIFEST.json') and child['nonce']==nonce
        assert child['expected_ids']==child['executed_ids']==child['stopped_ids']==[CASE]
        assert child['original_method_AST_unchanged'] is True
        return ref(RUN/'child/RESULT.json')
    try:
        record=run_owned(launch,emit,read_child,timeout=120)
        assert record['child_exit'] in (0,1)
        assert record['native_owner_after'] and all(record['native_owner_after'].values())
        assert record['primary_error'] is None and record['retirement_error'] is None
        assert child is not None and child['exit_status']==record['child_exit']
        j.verify(source='before');extra_verify(m,j)
    except BaseException as error:
        primary=error;data=BaseException.__dict__['__dict__'].__get__(error);record=dict.get(data,'full_runner_report',record)
    status=record['child_exit'] if primary is None else 1
    report=dict(started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),manifest=ref(HERE/'MANIFEST.json'),
        actual_parent_argv=list(sys.orig_argv),child_argv=[v['python']['path'],*child_args],nonce=nonce,record=record,
        child_result=None if child is None else ref(RUN/'child/RESULT.json'),primary_error=error_record(primary),
        diagnostic_completed=primary is None and child is not None and child['capture_complete'] is True,
        original_case_passed=None if child is None else child['original_case_passed'],exit_status=status,
        automatic_retry=False,Source_publication=False,product_acceptance=False,profile_operations=False)
    try:save(RUN/'PARENT-RESULT.json',report)
    except BaseException as secondary:
        if primary is None:raise
        j.retain(primary,secondary,'diagnostic-parent-result-writer',record)
    if primary is not None:raise primary
    print(json.dumps(dict(result=ref(RUN/'PARENT-RESULT.json'),diagnostic_completed=report['diagnostic_completed'],case_passed=report['original_case_passed'],exit_status=status)),flush=True)
    return status

def child(args):
    assert not args.execute_once and args.nonce is not None
    attempt=load(HERE/'ATTEMPT.json')
    assert attempt['nonce']==args.nonce and attempt['manifest']['sha256']==args.manifest_sha256
    assert Path.cwd()==HERE and RUN.is_dir()
    m,j,v=bootstrap(args.manifest_sha256)
    output=RUN/'child';output.mkdir(exist_ok=False)
    import ctypes as C
    notes=[];capture_errors=[];capture_failed=[False];forbidden=[];exchanges=[];launches=[];owners=[];original_errors=[]
    def capture(stage,read):
        saved=C.get_last_error()
        try:return read()
        except BaseException as error:
            capture_failed[0]=True
            try:capture_errors.append((stage,error))
            except BaseException:pass
            return None
        finally:C.set_last_error(saved)
    def event(kind,**value):
        return capture(kind,lambda:notes.append(dict(event=kind,monotonic_ns=time.monotonic_ns(),**value)))
    def audit(event,args):
        if event.startswith(('subprocess.','socket.')) or event in ('sqlite3.connect','os.system','os.startfile','os.posix_spawn','os.fork'):
            forbidden.append(event);raise RuntimeError('OUTSIDE_SINGLE_OBSERVER_DIAGNOSTIC:'+event)
        if event=='ctypes.dlsym' and str(args[1]) in ('CreateAppContainerProfile','DeleteAppContainerProfile','GetAppContainerFolderPath','DeriveAppContainerSidFromAppContainerName'):
            forbidden.append(event+':'+str(args[1]));raise RuntimeError('PROFILE_API_FORBIDDEN')
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            flags=args[2]
            if isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
                assert Path(os.fsdecode(args[0])).resolve().is_relative_to(RUN),'WRITE_OUTSIDE_DIAGNOSTIC'
        if event in ('os.mkdir','os.remove','os.rmdir','os.chmod','os.utime','os.truncate'):
            assert Path(os.fsdecode(args[0])).resolve().is_relative_to(RUN),'MUTATION_OUTSIDE_DIAGNOSTIC'
        if event in ('os.rename','os.link','os.symlink'):
            assert all(Path(os.fsdecode(p)).resolve().is_relative_to(RUN) for p in args[:2]),'MOVE_OUTSIDE_DIAGNOSTIC'
    sys.addaudithook(audit)
    sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
    from ceta.store.sqlite_runtime import load_sqlite
    load_sqlite()
    import ceta.effects.native_observer as obs
    import ceta.supervisor.windows_jobs as native
    import test_native_effect_observer as tests
    from fixture_runtime import native_report_data
    from unittest.mock import patch
    assert Path(tests.__file__)==Q/'tests/contract/test_native_effect_observer.py'
    assert Path(obs.__file__)==Q/'src/ceta/effects/native_observer.py'
    assert Path(native.__file__)==Q/'src/ceta/supervisor/windows_jobs.py'
    tests.ROOT=output/'fixtures'
    os.environ.update(CETA_EFFECT_OBSERVER_EXE=m['observer']['path'],CETA_OWNED_WORKER_EXE=m['worker']['path'],CETA_OBSERVER_NEGATIVE_ROOT=str(Path(m['negative_images']['overlong.exe']['path']).parent))
    original_method=tests.NativeEffectObserverTests.test_actual_overlong_native_pipe_output_is_rejected_and_retired
    original_exchange=obs.NativeCpuEffectObserver._exchange
    original_api_init=obs._ControlApi.__init__
    original_launch=native.WindowsOwnedProcess.launch.__func__
    def api_init(api,*a,**kw):
        original_api_init(api,*a,**kw)
        for name in ('PeekNamedPipe','ReadFile','WriteFile'):
            operation=getattr(api,name)
            def call(*args,_operation=operation,_name=name,**kwargs):
                event('pipe_api_enter',operation=_name,handle=int(args[0]) if type(args[0]) is int else None)
                try:result=_operation(*args,**kwargs)
                except BaseException as error:
                    saved=C.get_last_error()
                    try:
                        capture('pipe_error_retention',lambda:original_errors.append((error,'pipe_api:'+_name)))
                        event('pipe_api_raise',operation=_name,error_type=type(error).__name__,error_id=id(error),last_error=saved)
                    finally:C.set_last_error(saved)
                    raise
                saved=C.get_last_error()
                def record():
                    row=dict(event='pipe_api_return',operation=_name,monotonic_ns=time.monotonic_ns(),returned=int(result),last_error=saved)
                    if result:
                        pointer=args[4] if _name=='PeekNamedPipe' else args[3]
                        row['available' if _name=='PeekNamedPipe' else 'transferred']=C.cast(pointer,C.POINTER(native.DWORD)).contents.value
                    notes.append(row)
                try:capture('pipe_api_return',record)
                finally:C.set_last_error(saved)
                return result
            functools.update_wrapper(call,operation)
            for field in ('argtypes','restype'):
                if hasattr(operation,field):setattr(call,field,getattr(operation,field))
            setattr(api,name,call)
    def launch(cls,executable,arguments,**kwargs):
        path=Path(executable);expected=m['worker'] if path==Path(m['worker']['path']) else m['negative_images']['overlong.exe']
        assert path==Path(expected['path']) and kwargs['expected_image_sha256']==expected['sha256']
        assert tuple(arguments)==(('hold','30000') if path==Path(m['worker']['path']) else ('observe-v1',))
        assert not any(row['image']==str(path) for row in launches),'SECOND_DIAGNOSTIC_LAUNCH_FORBIDDEN'
        row=dict(image=str(path),arguments=list(arguments),launch_entry_ns=capture('launch_entry_time',time.monotonic_ns))
        slot=len(owners)
        try:
            launches.append(row)
            owners.append(None) # Reserve observation custody before launch; no allocation after return.
        except BaseException:
            capture_failed[0]=True
            raise
        try:owner=original_launch(cls,executable,arguments,**kwargs)
        except BaseException as error:
            saved=C.get_last_error()
            try:
                capture('launch_error_retention',lambda:original_errors.append((error,'launch')))
                capture('launch_raise',lambda:row.update(launch_return_ns=time.monotonic_ns(),returned=False,error_type=type(error).__name__,error_id=id(error),last_error=saved))
            finally:C.set_last_error(saved)
            raise
        saved=C.get_last_error()
        try:
            list.__setitem__(owners,slot,owner)
            capture('launch_return',lambda:row.update(launch_return_ns=time.monotonic_ns(),returned=True,pid=owner.pid,creation_time=owner.creation_time,last_error=saved))
        finally:C.set_last_error(saved)
        return owner
    def exchange(owner,custody,frame,cancelled,deadline_ns):
        row=dict(deadline_ns=deadline_ns,entry_ns=capture('exchange_entry_time',time.monotonic_ns),maximum_frame_bytes=len(frame))
        capture('exchange_row_registration',lambda:exchanges.append(row));event('exchange_enter',deadline_ns=deadline_ns)
        try:return original_exchange(owner,custody,frame,cancelled,deadline_ns)
        except BaseException as error:
            capture('exchange_error_retention',lambda:original_errors.append((error,'exchange')))
            capture('exchange_raise',lambda:row.update(original_error_type=type(error).__name__,original_error_id=id(error)))
            raise
        finally:
            capture('exchange_pre_cleanup',lambda:row.update(return_or_raise_ns=time.monotonic_ns(),pre_cleanup_transport_state=copy.deepcopy(custody.transport_state)))
            event('exchange_leave_before_source_cleanup')
    executed=[];stopped=[]
    class Result(unittest.TextTestResult):
        def startTest(self,test):executed.append(test.id());super().startTest(test)
        def stopTest(self,test):stopped.append(test.id());super().stopTest(test)
    suite=unittest.defaultTestLoader.loadTestsFromName('NativeEffectObserverTests.test_actual_overlong_native_pipe_output_is_rejected_and_retired',tests)
    assert [test.id() for test in suite]==[CASE]
    retained_test=list(suite)[0];threads_before=set(threading.enumerate())
    primary=result=None;started=datetime.now(timezone.utc).isoformat()
    with (output/'RAW.txt').open('x',encoding='utf8') as stream:
        try:
            with patch.object(obs._ControlApi,'__init__',api_init),patch.object(native.WindowsOwnedProcess,'launch',classmethod(launch)),patch.object(obs.NativeCpuEffectObserver,'_exchange',exchange):
                result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
        except BaseException as error:primary=error
    custody=[dict(pid=o.pid,creation_time=o.creation_time,lifetime_closed=o.lifetime_closed,
        process_closed=o._process is None,thread_closed=o._thread is None,job_closed=o._job is None,
        remaining_query_exports=len(o._cpu_query_exports)) for o in owners if o is not None]
    j.verify(source='before',verify_git=False);extra_verify(m,j)
    unchanged=tests.NativeEffectObserverTests.test_actual_overlong_native_pipe_output_is_rejected_and_retired is original_method and method_ast()==m['original_method_ast_sha256']
    new_threads=[dict(name=t.name,native_id=t.native_id) for t in set(threading.enumerate())-threads_before if t.is_alive()]
    clock=getattr(retained_test,'clock',None)
    clock_status=None if clock is None else clock.status()
    clock_receipt=None if clock_status is None else dict(state=clock_status.state,registered=clock_status.registration_owned,sampler_alive=clock_status.sampler_alive)
    closed=all(all(r[k] for k in ('lifetime_closed','process_closed','thread_closed','job_closed')) and not r['remaining_query_exports'] for r in custody)
    clock_closed=clock_receipt is None or clock_receipt['state']=='CLOSED' and not clock_receipt['registered'] and not clock_receipt['sampler_alive']
    completed=primary is None and result is not None and not capture_failed[0] and not forbidden and closed and clock_closed and not new_threads and len(custody)==len(owners) and executed==stopped==[CASE]
    case_passed=result is not None and result.wasSuccessful() and not result.skipped
    report=dict(started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),manifest=ref(HERE/'MANIFEST.json'),nonce=args.nonce,
        expected_ids=[CASE],executed_ids=executed,stopped_ids=stopped,tests_run=0 if result is None else result.testsRun,
        failures=[] if result is None else [(t.id(),text) for t,text in result.failures],errors=[] if result is None else [(t.id(),text) for t,text in result.errors],
        skips=[] if result is None else [(t.id(),text) for t,text in result.skipped],primary_error=error_record(primary),
        original_errors=[dict(stage=stage,error_id=id(error),error=error_record(error)) for error,stage in original_errors],
        original_method_AST_unchanged=unchanged,maximum_duration_unchanged=True,exchanges=exchanges,launches=launches,pipe_events=notes,
        custody=custody,clock=clock_receipt,new_threads_remaining=new_threads,original_fixture_receipts=native_report_data(tests.NATIVE_RECEIPTS),
        capture_errors=[dict(stage=stage,error=error_record(error)) for stage,error in capture_errors],forbidden_events=forbidden,
        capture_complete=completed and unchanged,original_case_passed=case_passed,exit_status=0 if completed and unchanged and case_passed else 1,
        raw=ref(output/'RAW.txt'),automatic_retry=False,profiles=False,Source_publication=False,product_acceptance=False,
        interpretation_limit='Read-only wrappers add measurement overhead. A repeat alone does not establish the cause of the earlier run.')
    try:save(output/'RESULT.json',report)
    except BaseException as secondary:
        if primary is None:raise
        j.retain(primary,secondary,'diagnostic-child-result-writer')
    if primary is not None:raise primary
    print(json.dumps(dict(result=ref(output/'RESULT.json'),capture_complete=report['capture_complete'],case_passed=case_passed)),flush=True)
    return report['exit_status']

def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('parent','child'))
    parser.add_argument('--manifest-sha256',required=True);parser.add_argument('--nonce');parser.add_argument('--execute-once',action='store_true')
    args=parser.parse_args();return parent(args) if args.mode=='parent' else child(args)
if __name__=='__main__':sys.exit(main())
