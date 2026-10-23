"""Fresh journal engineering cohort; exact source, actual claims, no ROOT overlay.

Successful execution requires the actual process exit0 and the report seal, not
the test outcome field alone. Preparation collects identities but runs no cases.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib,json,os,stat,subprocess,sys,time,traceback,unittest

F=Path('T:/00-Active/Project-AI-CETA')
W=Path(__file__).resolve().parent
J=W.parent
RUN='ceta-jr23-r2'
PACKET_SHA='b19574893637649e56879f87a552b81d744694405e5c08313a1a5f0888d0ddd4'
PLAN_SHA='a453efc079f4096b992b28a9c9a27778f8f79c8c84aee1481baf17c84ca82c2f'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def plain(path):
    info=path.lstat()
    assert not path.is_symlink() and not getattr(info,'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT,('linked path',str(path))
    return info

def ancestors(root,path):
    assert path.is_relative_to(root)
    while True:
        plain(path)
        if path==root:return
        path=path.parent

def stable(path):
    first=plain(path);assert stat.S_ISREG(first.st_mode)
    raw=path.read_bytes();last=plain(path)
    key=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)
    assert key(first)==key(last) and len(raw)==last.st_size,('unstable file',str(path))
    return dict(device=last.st_dev,inode=last.st_ino,bytes=last.st_size,mtime_ns=last.st_mtime_ns,
                sha256=hashlib.sha256(raw).hexdigest()),raw

def snapshot(base):
    """Complete one claimed base, including ignored names and empty directories.

    Directory identity/type is preserved; parent mtime/size may change when a
    newly created fixture child is added. File bytes and native metadata stay exact.
    """
    def directory(path):
        s=plain(path);assert stat.S_ISDIR(s.st_mode)
        return dict(kind='directory',device=s.st_dev,inode=s.st_ino,mtime_ns=s.st_mtime_ns)
    out={'.':directory(base)}
    def onerror(error):raise error
    for name,dirs,files in os.walk(base,topdown=True,onerror=onerror,followlinks=False):
        root=Path(name)
        for part in sorted(dirs):
            p=root/part;out[p.relative_to(base).as_posix()+'/']=directory(p)
        for part in sorted(files):
            p=root/part;native,_=stable(p)
            out[p.relative_to(base).as_posix()]=dict(kind='file',**native)
    return out

def preservation(before,after):
    for name,prior in before.items():
        assert name in after,('preexisting entry disappeared',name)
        current=after[name]
        if prior['kind']=='file':assert current==prior,('preexisting file changed',name)
        else:
            assert all(current[k]==prior[k] for k in ('kind','device','inode')),('directory replaced',name)
    return True

def save(path,value):
    raw=(json.dumps(value,indent=2,allow_nan=False)+'\n').encode('utf-8')
    with path.open('xb') as stream:
        assert stream.write(raw)==len(raw);stream.flush();os.fsync(stream.fileno())

def identities(suite):
    if isinstance(suite,unittest.TestCase):return [suite.id()]
    return [identity for child in suite for identity in identities(child)]

def module_origin(module):
    values=vars(module);origin=values.get('__file__')
    if not isinstance(origin,str):origin=getattr(values.get('__spec__'),'origin',None)
    if not isinstance(origin,str) or origin in ('built-in','frozen'):return dict(origin=origin,file=False)
    path=Path(origin).resolve(strict=True);pin,_=stable(path)
    return dict(origin=str(path),file=True,native=pin)

def dependency_identities():
    out={}
    for name,module in sorted(tuple(sys.modules.items())):
        if module is not None and (name.startswith(('ceta','jsonschema','referencing','rpds','attrs','attr'))
                or name in ('sqlite3','sqlite3.dbapi2','_sqlite3','_ctypes','ctypes','unittest','json')):
            out[name]=module_origin(module)
    return out

def canonical_suite(packet):
    assert packet['project']==str(F) and packet['selected']==['test_journal_read_budget','test_operator_resource_diagnostics']
    sys.path[:0]=[str(F/'src'),str(F/'tests/contract')]
    modules={}
    for name in packet['selected']:
        module=importlib.import_module(name)
        assert Path(module.__file__).resolve()==F/'tests/contract'/(name+'.py'),('noncanonical module',name)
        assert module.ROOT==F,('noncanonical ROOT',name)
        assert sha(Path(module.__file__))==packet['selected_sha256'][name]
        modules[name]=module_origin(module)
    for name,module in tuple(sys.modules.items()):
        if module is None:continue
        if name=='ceta' or name.startswith('ceta.'):
            origin=module_origin(module);assert origin['file'] and Path(origin['origin']).is_relative_to(F/'src')
            if 'ROOT' in vars(module):assert module.ROOT==F,('noncanonical product ROOT',name)
        elif name.startswith('test_'):
            assert Path(module.__file__).resolve().is_relative_to(F/'tests/contract'),('noncanonical test dependency',name)
            if 'ROOT' in vars(module):assert module.ROOT==F,('noncanonical helper ROOT',name)
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in packet['selected'])
    ids=identities(suite)
    assert ids and len(ids)==len(set(ids)) and not any('_FailedTest' in i for i in ids)
    return suite,ids,modules

def source_observation(binding):
    out={}
    for name,pin in binding['source_native'].items():
        path=Path(name);ancestors(F,path.parent)
        native,_=stable(path);assert native==pin,('source/native identity drift',name)
        out[name]=native
    return dict(source_native=out,Git=git_observation(binding['Git']))

def git_observation(expected):
    assert not any(k in os.environ for k in ('GIT_INDEX_FILE','GIT_DIR','GIT_WORK_TREE','GIT_COMMON_DIR',
        'GIT_OBJECT_DIRECTORY','GIT_ALTERNATE_OBJECT_DIRECTORIES')),'nonstandard Git environment'
    def git(*args):return subprocess.check_output(['git','--no-optional-locks','-c','core.fsmonitor=false',*args],cwd=F)
    assert Path(git('rev-parse','--show-toplevel').decode().strip()).resolve()==F
    index=Path(git('rev-parse','--git-path','index').decode().strip())
    if not index.is_absolute():index=F/index
    assert index.resolve()==F/'.git/index';ancestors(F,index.parent)
    assert not (F/'.git/index.lock').exists()
    current=dict(root=str(F),branch=git('symbolic-ref','HEAD').decode().strip(),head=git('rev-parse','HEAD').decode().strip(),
        origin=git('remote','get-url','origin').decode().strip(),
        status_sha256=hashlib.sha256(git('status','--porcelain=v1','-z','--untracked-files=all')).hexdigest(),index_native=stable(index)[0])
    assert current==expected,'Git identity/status/normal-index drift'
    return current

def require_live(binding):
    """Real runtime/readiness/input/scope checks; READY is never authority."""
    sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
    from taar.orchestration_runtime import OrchestrationRuntime
    from taar.orchestration_graph import compile_graph
    control=Path(binding['control']);root=Path(binding['graph_root']);run=binding['run_id']
    runtime=OrchestrationRuntime(control);verified=runtime.verify(run)
    assert verified['allowed'] is True and verified['receipts_valid'] is True and verified['run_id']==run
    assert verified['graph_fingerprint']==binding['graph_fingerprint']
    graph=compile_graph(root,control)
    assert graph.fingerprint==binding['graph_fingerprint']
    state=json.loads((control/run/'state.json').read_bytes())
    assert state['run_id']==run and state['graph_fingerprint']==graph.fingerprint
    assert Path(state['graph_root']).resolve()==root.resolve() and Path(state['scope']).resolve()==control.resolve()
    assert state['nodes']['review']['state']=='SUCCEEDED' and state['nodes']['review']['decision']=='approved'
    assert state['nodes']['review']['executor_id']!=state['nodes']['implement']['executor_id']
    assert state['nodes']['validate']['state']=='SUCCEEDED' and state['nodes']['validate']['validation_passed'] is True
    reviewed=json.loads((control/run/state['nodes']['review']['receipt_ref']).read_bytes())
    assert reviewed['result']['manifest_sha256']==binding['prepared_manifest_sha256']
    gate=json.loads((control/run/state['nodes']['validate']['receipt_ref']).read_bytes())
    assert gate['commands']==[dict(command=c,exit_status=0) for c in graph.nodes['validate']['commands']]
    assert [dict(command=c['command'],exit_status=c['exit_status']) for c in gate['result']['commands']]==gate['commands']
    claims={}
    for node,workspace in binding['workspaces'].items():
        record=state['nodes'][node];claim=record.get('claim')
        assert record['state']=='RUNNING' and claim,('claim not running',node)
        assert claim['executor_id']=='/root' and claim['node_id']==node,('wrong executor/node',node)
        path=Path(workspace)
        assert Path(claim['workspace']).resolve()==path.resolve()
        assert claim['effective_write_scope']==[path.relative_to(root).as_posix()+'/**']
        assert claim['input_hash']==runtime._input_hash(graph,state,node)
        ancestors(root,path)
        claims[node]=claim
    return claims

def diagnostic(error):
    """Bounded raw exception facts: never call an exception/provider formatter.

    Exact scalar types only; arbitrary values are typed, never str/repr'd. Raw
    BaseException descriptors bypass subclass properties and hostile dictionaries.
    The single node budget also bounds shared/cyclic storage, args and chains.
    Tracebacks contain code names/positions only, without reading source lines.
    """
    seen=set();remaining=[64]
    def typename(value):return str.__getitem__(type.__dict__['__name__'].__get__(type(value)),slice(0,128))
    def scalar(value):
        kind=type(value)
        if kind is str:return value[:512]
        if kind is bool or kind is type(None):return value
        if kind is int and int.bit_length(value)<=64:return value
        return dict(type=typename(value),unsupported=True)
    def raw(name,value):return BaseException.__dict__[name].__get__(value)
    def visit(value,depth=0):
        if remaining[0]<=0 or depth>=6:return dict(truncated=True)
        remaining[0]-=1
        if type(value) is str or type(value) is int or type(value) is bool or type(value) is type(None):return scalar(value)
        if id(value) in seen:return dict(type=typename(value),cycle=True)
        seen.add(id(value))
        if issubclass(type(value),BaseException):
            args=raw('args',value);attrs=raw('__dict__',value)
            storage=[]
            for key,item in dict.items(attrs):
                if len(storage)>=16 or remaining[0]<=0:break
                storage.append(dict(key=scalar(key),value=visit(item,depth+1)))
            frames=[];tb=raw('__traceback__',value)
            while tb is not None and len(frames)<16:
                code=tb.tb_frame.f_code
                frames.append(dict(file=str.__getitem__(code.co_filename,slice(0,512)),
                    name=str.__getitem__(code.co_name,slice(0,128)),line=tb.tb_lineno))
                tb=tb.tb_next
            return dict(type=typename(value),message=args[0][:512] if args and type(args[0]) is str else '<raw args only>',
                args=visit(args,depth+1),storage=storage,storage_truncated=dict.__len__(attrs)>len(storage),
                traceback=frames,traceback_truncated=tb is not None,
                cause=visit(raw('__cause__',value),depth+1),context=visit(raw('__context__',value),depth+1),
                suppress_context=raw('__suppress_context__',value))
        if type(value) is tuple or type(value) is list:
            return dict(type=typename(value),items=[visit(item,depth+1) for item in value[:16]],truncated=len(value)>16)
        return scalar(value)
    return visit(error)

def result_fields(result):
    """Called inside the report guard; its failures cannot replace a body error."""
    return dict(started_test_ids=[] if result is None else result.started,
        stopped_test_ids=[] if result is None else result.stopped,
        tests_run=None if result is None else result.testsRun,
        failures=None if result is None else len(result.failures),errors=None if result is None else len(result.errors),
        skips=None if result is None else [dict(test_id=t.id(),reason=reason) for t,reason in result.skipped],
        expected_failures=None if result is None else [dict(test_id=t.id(),traceback=trace) for t,trace in result.expectedFailures],
        unexpected_successes=None if result is None else [t.id() for t in result.unexpectedSuccesses],
        early_stop=None if result is None else result.shouldStop,
        test_error_details=[] if result is None else result.details)

def run_observed(suite,selected,output,fixtures,observe_source,authorize,*,metadata=None):
    """Reusable observation engine; controls use only disposable synthetic cases."""
    assert output.is_dir() and not any(output.iterdir())
    claims=authorize();before_source=observe_source()
    before={name:snapshot(path) for name,path in fixtures.items()}
    assert authorize()==claims,'authority changed before first test/report write'
    save(output/'START.json',dict(test_ids=selected,claims=claims,source_before=before_source,
        fixtures_before=before,metadata=metadata,full_product_acceptance=False))
    result=None;created_result=[];primary=None;primary_info=None;secondary=[];after={};after_source=None;events=None;log=None
    started=time.monotonic_ns()
    def describe(error,exc_info=None):
        nonlocal primary,primary_info
        try:return diagnostic(error)
        except BaseException as fault:
            # When formatting a unittest body error, preserve that exact triple.
            if primary is None and exc_info is not None:primary=exc_info[1];primary_info=exc_info
            secondary.append(fault)
            return dict(diagnostic_unavailable=True)
    def event(kind,test=None,error=None):
        raw=(json.dumps(dict(kind=kind,test_id=None if test is None else test.id(),
            at=datetime.now(timezone.utc).isoformat(),error=describe(error)),allow_nan=False)+'\n').encode()
        assert events.write(raw)==len(raw);events.flush();os.fsync(events.fileno())
    class Result(unittest.TextTestResult):
        def __init__(self,*a,**kw):super().__init__(*a,**kw);self.started=[];self.stopped=[];self.details=[];created_result.append(self)
        def startTest(self,test):self.started.append(test.id());event('started',test);super().startTest(test)
        def stopTest(self,test):self.stopped.append(test.id());event('stopped',test);super().stopTest(test)
        def _exc_info_to_string(self,error,test):return json.dumps(describe(error[1],error),allow_nan=False)
        def addError(self,test,error):self.details.append(dict(test_id=test.id(),kind='error',error=describe(error[1],error)));super().addError(test,error)
        def addFailure(self,test,error):self.details.append(dict(test_id=test.id(),kind='failure',error=describe(error[1],error)));super().addFailure(test,error)
        def addSubTest(self,test,subtest,error):
            if error is not None:self.details.append(dict(test_id=test.id(),subtest_id=subtest.id(),kind='subtest',error=describe(error[1],error)))
            super().addSubTest(test,subtest,error)
    try:
        events=(output/'events.jsonl').open('xb')
        log=(output/'TESTS.log').open('x',encoding='utf-8')
        # The exact same three live claims are checked immediately before cases.
        assert authorize()==claims,'authority changed before test bodies'
        result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=Result).run(suite)
    except BaseException as error:
        if primary is None:primary=error;primary_info=sys.exc_info()
        else:secondary.append(error)
    finally:
        if result is None and created_result:result=created_result[0]
        for handle in (log,events):
            if handle is not None:
                try:handle.flush();os.fsync(handle.fileno())
                except BaseException as error:secondary.append(error)
                try:handle.close()
                except BaseException as error:secondary.append(error)
        try:after_source=observe_source()
        except BaseException as error:secondary.append(error)
        for name,path in fixtures.items():
            try:after[name]=snapshot(path);preservation(before[name],after[name])
            except BaseException as error:secondary.append(error)
    if primary is None and secondary:primary=secondary[0]
    complete=False
    try:
        complete=(result is not None and result.testsRun==len(selected) and result.started==result.stopped==selected
            and result.wasSuccessful() and not result.skipped and not result.expectedFailures
            and not result.unexpectedSuccesses and not result.shouldStop and primary is None
            and before_source==after_source and len(after)==len(before))
        report=dict(test_cohort_passed=complete,execution_success_requires_process_exit_zero_and_seal=True,
            selected_test_ids=selected,**result_fields(result),primary=describe(primary),
            cleanup=[describe(e) for e in tuple(secondary)],source_after=after_source,fixtures_after=after,
            elapsed_ns=time.monotonic_ns()-started,full_product_acceptance=False,native_process_execution=False)
    except BaseException as error:
        secondary.append(error)
        if primary is None:primary=error;primary_info=sys.exc_info()
        report=dict(test_cohort_passed=False,report_assembly_failed=True,primary=describe(primary),
            cleanup=[describe(e) for e in tuple(secondary)],source_after=after_source,fixtures_after=after,
            full_product_acceptance=False,native_process_execution=False)
    if primary is None and secondary:primary=secondary[0]
    complete=complete and primary is None and not secondary
    report['test_cohort_passed']=complete
    try:save(output/'RESULT.json',report)
    except BaseException as error:
        secondary.append(error)
        if primary is None:primary=error;primary_info=sys.exc_info()
        try:save(output/'REPORT-ERROR.json',dict(phase='RESULT',error=describe(error),full_product_acceptance=False))
        except BaseException as extra:secondary.append(extra)
    if primary is not None:
        if primary_info is None:primary_info=(type(primary),primary,BaseException.__dict__['__traceback__'].__get__(primary))
        attrs=BaseException.__dict__['__dict__'].__get__(primary)
        dict.__setitem__(attrs,'runner_secondary_errors',tuple(secondary))
        dict.__setitem__(attrs,'runner_primary_exc_info',primary_info)
        raise BaseException.with_traceback(primary,primary_info[2])
    try:
        save(output/'REPORT-SEAL.json',dict(result_sha256=sha(output/'RESULT.json'),
            start_sha256=sha(output/'START.json'),events_sha256=sha(output/'events.jsonl'),log_sha256=sha(output/'TESTS.log'),
            test_cohort_passed=complete,requires_actual_process_exit_zero=True,full_product_acceptance=False))
    except BaseException as error:
        info=sys.exc_info()
        try:save(output/'REPORT-ERROR.json',dict(phase='REPORT-SEAL',error=describe(error),full_product_acceptance=False))
        except BaseException as extra:secondary.append(extra)
        attrs=BaseException.__dict__['__dict__'].__get__(error)
        dict.__setitem__(attrs,'runner_secondary_errors',tuple(secondary))
        dict.__setitem__(attrs,'runner_primary_exc_info',info)
        raise BaseException.with_traceback(error,info[2])
    return 0 if complete else 1

def execution_complete(output,actual_exit_status):
    """The caller supplies its observed process code; a report alone cannot pass."""
    if type(actual_exit_status) is not int or actual_exit_status!=0:return False
    if (output/'REPORT-ERROR.json').exists():return False
    try:
        seal=json.loads((output/'REPORT-SEAL.json').read_bytes())
        for key,name in [('result_sha256','RESULT.json'),('start_sha256','START.json'),
                         ('events_sha256','events.jsonl'),('log_sha256','TESTS.log')]:
            if sha(output/name)!=seal[key]:return False
        start=json.loads((output/'START.json').read_bytes());result=json.loads((output/'RESULT.json').read_bytes())
        ids=start['test_ids']
        if not (ids and len(ids)==len(set(ids)) and result['test_cohort_passed'] is True
            and result['selected_test_ids']==result['started_test_ids']==result['stopped_test_ids']==ids
            and type(result['tests_run']) is int and result['tests_run']==len(ids)
            and result['failures']==result['errors']==0 and result['skips']==[]
            and result['early_stop'] is False and result['primary'] is None and not result['cleanup']
            and result['source_after']==start['source_before']):return False
        for name,before in start['fixtures_before'].items():preservation(before,result['fixtures_after'][name])
        return seal['test_cohort_passed'] is True
    except (OSError,ValueError,KeyError,AssertionError):return False

def load_prepared(pin):
    assert J==F/'.agents/runtime/oq23/jr2'
    assert sha(W/'MANIFEST.json')==pin
    manifest=json.loads((W/'MANIFEST.json').read_bytes())
    for name,value in manifest['work_hashes'].items():assert sha(W/name)==value
    for name,value in manifest['external_pins'].items():assert sha(Path(name))==value
    packet=json.loads((J/'packet/INPUTS.json').read_bytes())
    assert sha(J/'packet/INPUTS.json')==PACKET_SHA and sha(J/'packet/PLAN.md')==PLAN_SHA
    assert Path(sys.executable).resolve()==Path(packet['python']).resolve() and sha(Path(sys.executable))==packet['python_sha256']
    binding=json.loads((W/'BINDING.json').read_bytes())
    binding['prepared_manifest_sha256']=pin
    assert binding['control']==str(J/'control') and binding['run_id']==RUN and binding['graph_root']==str(Path('T:/').resolve())
    expected=dict(integrate=str(J/'delivery'),**packet['fixture_workspaces'])
    assert binding['workspaces']==expected
    return packet,binding

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest-sha256',required=True)
    args=parser.parse_args();packet,binding=load_prepared(args.manifest_sha256)
    source_observation(binding);claims=require_live(binding)
    suite,selected,modules=canonical_suite(packet)
    assert selected==json.loads((W/'COLLECTION.json').read_bytes())['test_ids']
    from ceta.store.sqlite_runtime import runtime_identity
    sqlite=runtime_identity()
    assert Path(sqlite['dll_path'])==F/'native/sqlite_runtime/win-x64/sqlite3.dll'
    metadata=dict(source_root=str(F),ordinary_imports=True,ROOT_override=False,module_overlay=False,
        test_modules=modules,dependencies=dependency_identities(),sqlite=sqlite,
        interpreter=dict(path=sys.executable,native=stable(Path(sys.executable))[0]))
    assert require_live(binding)==claims
    return run_observed(suite,selected,J/'delivery',
        {n:Path(p) for n,p in packet['fixture_workspaces'].items()},lambda:source_observation(binding),
        lambda:require_live(binding),metadata=metadata)

if __name__=='__main__':raise SystemExit(main())
