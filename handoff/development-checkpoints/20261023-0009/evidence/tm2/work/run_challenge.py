"""One reviewed canonical case once; postmortem observation only, no product edits."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, importlib, importlib.util, json, os, sys, unittest
import owner_timing_observer as observer

F=Path('T:/00-Active/Project-AI-CETA'); W=Path(__file__).resolve().parent; K=W.parent
RUN='ceta-tm23-r2'
PACKET_SHA='422dd2b9fa8d31396ed1e3ce6fae3a3f77a117d8cb43ada7cf776900a0c99504'
PLAN_SHA='7f77aee2cbe3686564e764bbf007bbc40edc10ea7fc9e640f9a26b6a7f774e93'
SELECTED=['test_cpu_execution_admission.CpuExecutionAdmissionTests.test_stop_in_final_elapsed_callback_wins_after_all_owner_callbacks']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def save(path,value):
    raw=(json.dumps(value,indent=2,allow_nan=False)+'\n').encode('utf-8')
    with path.open('xb') as stream:
        assert stream.write(raw)==len(raw); stream.flush(); os.fsync(stream.fileno())

def prerequisite(binding):
    """Actual accepted JR2 execution, not a prepared verdict, is mandatory."""
    pins=binding['journal_success_pins']
    for path,pin in pins.items(): assert sha(Path(path))==pin,('JR2 prerequisite drift',path)
    root=F/'.agents/runtime/oq23/jr2'; delivery=root/'delivery'
    process=json.loads((root/'control/EXECUTION-PROCESS.json').read_bytes())
    review=json.loads((root/'review/REVIEW.json').read_bytes())
    assert type(process['exit_status']) is int and process['exit_status']==0
    assert process['cwd']==str(F) and process['manifest_sha256']==sha(root/'work/MANIFEST.json')
    assert process['manifest_sha256']=='771fa4d915c6b9d6fb2f1f042d3c313448fb4f2cea8607420fcccca65bf4df53'
    packet=json.loads((root/'packet/INPUTS.json').read_bytes())
    assert process['argv']==[packet['python'],'-B','-X','utf8',str(root/'work/run_canonical_journal.py'),'--manifest-sha256',process['manifest_sha256']]
    assert review['decision']=='approved' and review['manifest_sha256']==process['manifest_sha256']
    for name,key in [('EXECUTION.stdout','stdout_sha256'),('EXECUTION.stderr','stderr_sha256')]:
        assert sha(root/'control'/name)==process[key]
    assert not (delivery/'REPORT-ERROR.json').exists()
    seal=json.loads((delivery/'REPORT-SEAL.json').read_bytes())
    for name,key in [('START.json','start_sha256'),('RESULT.json','result_sha256'),('events.jsonl','events_sha256'),('TESTS.log','log_sha256')]:
        assert sha(delivery/name)==seal[key]
    start=json.loads((delivery/'START.json').read_bytes()); result=json.loads((delivery/'RESULT.json').read_bytes())
    ids=start['test_ids']
    assert len(ids)==len(set(ids))==33
    assert result['selected_test_ids']==result['started_test_ids']==result['stopped_test_ids']==ids
    assert type(result['tests_run']) is int and result['tests_run']==33
    assert result['test_cohort_passed'] is True and seal['test_cohort_passed'] is True
    assert result['failures']==result['errors']==0 and result['skips']==[]
    assert result['expected_failures']==result['unexpected_successes']==[]
    assert result['early_stop'] is False and result['primary'] is None and result['cleanup']==[]
    assert result['source_after']==start['source_before']
    return dict(process_sha256=sha(root/'control/EXECUTION-PROCESS.json'),result_sha256=sha(delivery/'RESULT.json'),seal_sha256=sha(delivery/'REPORT-SEAL.json'),actual_exit_status=0,tests=33)

def support(binding):
    prerequisite(binding)
    path=Path(binding['support_path'])
    assert path==F/'.agents/runtime/oq23/jr2/work/run_canonical_journal.py'
    assert sha(path)==binding['support_sha256']
    spec=importlib.util.spec_from_file_location('_accepted_jr2_observation',path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    # Only these reviewed pure observations are used; never JR2 main/run/live guards.
    return module

def require_live(binding,r):
    sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
    from taar.orchestration_runtime import OrchestrationRuntime
    from taar.orchestration_graph import compile_graph
    control=K/'control'; root=Path('T:/').resolve()
    runtime=OrchestrationRuntime(control); verified=runtime.verify(RUN)
    assert verified['allowed'] is True and verified['receipts_valid'] is True and verified['run_id']==RUN
    graph=compile_graph(root,control)
    assert graph.fingerprint==binding['graph_fingerprint']==verified['graph_fingerprint']
    state=json.loads((control/RUN/'state.json').read_bytes())
    assert state['run_id']==RUN and state['graph_fingerprint']==graph.fingerprint
    assert Path(state['graph_root']).resolve()==root and Path(state['scope']).resolve()==control.resolve()
    nodes=state['nodes']; assert nodes['implement']['state']=='SUCCEEDED'
    assert nodes['review']['state']=='SUCCEEDED' and nodes['review']['decision']=='approved'
    assert nodes['review']['executor_id']!=nodes['implement']['executor_id']
    assert nodes['validate']['state']=='SUCCEEDED' and nodes['validate']['validation_passed'] is True
    review=json.loads((control/RUN/nodes['review']['receipt_ref']).read_bytes())
    assert review['result']['manifest_sha256']==binding['prepared_manifest_sha256']
    gate=json.loads((control/RUN/nodes['validate']['receipt_ref']).read_bytes())
    assert gate['commands']==[dict(command=c,exit_status=0) for c in graph.nodes['validate']['commands']]
    assert [dict(command=c['command'],exit_status=c['exit_status']) for c in gate['result']['commands']]==gate['commands']
    expected=dict(integrate=str(K/'delivery'),owner_authority=str(F/'.agents/fixtures/kernel-owner-authority'))
    assert binding['workspaces']==expected
    claims={}
    for node,workspace in expected.items():
        record=nodes[node]; claim=record.get('claim'); path=Path(workspace)
        assert record['state']=='RUNNING' and claim
        assert claim['executor_id']=='/root' and claim['node_id']==node
        assert Path(claim['workspace']).resolve()==path.resolve()
        assert claim['effective_write_scope']==[path.relative_to(root).as_posix()+'/**']
        assert claim['input_hash']==runtime._input_hash(graph,state,node)
        r.ancestors(root,path); claims[node]=claim
    assert set(claims)=={'integrate','owner_authority'}
    return claims

def canonical_suite(packet,r):
    assert packet['project']==str(F) and packet['selected']==SELECTED
    assert not any(k.startswith('CETA_') for k in os.environ),'CETA environment not sanitized'
    sys.path[:0]=[str(F/'src'),str(F/'tests/contract')]
    name='test_cpu_execution_admission'; module=importlib.import_module(name)
    assert Path(module.__file__).resolve()==F/'tests/contract'/(name+'.py')
    assert module.ROOT==F and sha(Path(module.__file__))==packet['selected_sha256'][name]
    suite=unittest.defaultTestLoader.loadTestsFromName(SELECTED[0]); ids=r.identities(suite)
    assert ids==SELECTED and suite.countTestCases()==1
    cases=list(suite); assert len(cases)==1 and type(cases[0]) is module.CpuExecutionAdmissionTests
    for name,loaded in tuple(sys.modules.items()):
        if loaded is None: continue
        if name=='ceta' or name.startswith('ceta.'):
            origin=r.module_origin(loaded)
            if name=='ceta.effects':
                assert origin['file'] is False and vars(loaded).get('__file__') is None
                assert list(vars(loaded)['__path__'])==[str(F/'src/ceta/effects')]
                assert not (F/'src/ceta/effects/__init__.py').exists()
                r.ancestors(F,F/'src/ceta/effects')
            else:
                assert origin['file'] and Path(origin['origin']).is_relative_to(F/'src')
            if 'ROOT' in vars(loaded): assert vars(loaded)['ROOT']==F
        elif name.startswith('test_'):
            assert Path(loaded.__file__).resolve().is_relative_to(F/'tests/contract')
            if 'ROOT' in vars(loaded): assert vars(loaded)['ROOT']==F
    from ceta.kernel.owner_authority import KernelOwnerAuthority
    from ceta.kernel.transactions import KernelTransactions
    from ceta.contracts.owner_enrollment import EnrollmentRequest
    from ceta.contracts.real_effect import OwnedCpuRequest
    from ceta.contracts.temporal import ClockSample,Deadline
    entries=tuple(vars(KernelTransactions)[n].__wrapped__.__code__ for n in
        ('begin_owner_enrollment','enroll_owner','approve_owned_cpu'))
    bound=observer.Binding(KernelOwnerAuthority._guard.__code__,KernelOwnerAuthority._commit.__code__,entries,
        KernelOwnerAuthority,KernelTransactions,EnrollmentRequest,ClockSample,Deadline,OwnedCpuRequest)
    identity=dict(guard=dict(file=bound.guard_code.co_filename,name=bound.guard_code.co_name,first_line=bound.guard_code.co_firstlineno),
        commit=dict(file=bound.commit_code.co_filename,name=bound.commit_code.co_name,first_line=bound.commit_code.co_firstlineno),
        entries=[dict(file=c.co_filename,name=c.co_name,first_line=c.co_firstlineno) for c in entries],
        binding='EXACT_FRESH_CANONICAL_CODE_OBJECTS_AND_RAW_CONTEXT_IDENTITY',transaction_state_inference=False)
    return suite,cases[0],bound,identity,{'test_cpu_execution_admission':r.module_origin(module)}

def dependencies(r):
    out=r.dependency_identities()
    if 'ceta.effects' in out:
        path=F/'src/ceta/effects'; info=r.plain(path)
        out['ceta.effects']['namespace']=dict(path=str(path),device=info.st_dev,inode=info.st_ino,mtime_ns=info.st_mtime_ns)
    return out

def formatted_outcomes(result,case,test_id):
    """Copy superclass text verbatim; never format a test or exception again."""
    out=dict(errors=[],failures=[])
    for name in ('errors','failures'):
        bucket=vars(result)[name]
        assert type(bucket) is list, 'unsupported unittest outcome bucket'
        for pair in bucket:
            assert type(pair) is tuple and len(pair)==2, 'unsupported unittest outcome entry'
            failed,text=pair
            assert type(text) is str, 'unsupported superclass formatted text'
            record=dict(test_id='NOT_CAPTURED',subtest_ordinal=None,identity_status='NOT_CAPTURED',formatted_text=text)
            if failed is case:
                record.update(test_id=test_id,identity_status='KNOWN_CASE')
            else:
                for index,(kind,parent,subtest,original) in enumerate(result.originals):
                    if kind=='subtest' and parent is case and subtest is failed:
                        ordinal=sum(k=='subtest' and p is case for k,p,_,_ in result.originals[:index+1])
                        record.update(test_id=test_id,subtest_ordinal=ordinal,identity_status='KNOWN_CASE_SUBTEST_EVENT')
                        break
            if record['identity_status']=='NOT_CAPTURED':result.coverage_complete=False
            out[name].append(record)
    return out

def run_observed(suite,case,bound,output,r,observe_source,authorize,fixtures,metadata):
    """Own one-case custody; all collector work occurs after an error unwinds."""
    assert output.is_dir() and not any(output.iterdir())
    claims=authorize(); before_source=observe_source(); before={n:r.snapshot(p) for n,p in fixtures.items()}
    assert authorize()==claims
    save(output/'START.json',dict(test_ids=SELECTED,claims=claims,source_before=before_source,fixtures_before=before,metadata=metadata,one_attempt=True,full_product_acceptance=False))
    result=None; primary=None; primary_info=None; secondary=[]; after={}; after_source=None; events=None; log=None
    formatted=dict(errors=[],failures=[])
    def event(kind,test=None,payload=None):
        identity=None if test is None else next(n for value,n in ((case,SELECTED[0]),) if test is value)
        raw=(json.dumps(dict(kind=kind,test_id=identity,payload=payload),allow_nan=False)+'\n').encode('utf-8')
        assert events.write(raw)==len(raw); events.flush(); os.fsync(events.fileno())
    class Result(observer.PostmortemResult):
        def __init__(self):
            super().__init__(bound,((case,SELECTED[0]),),sink=lambda item:event('postmortem',payload=item))
            self.started=[]; self.stopped=[]
        def startTest(self,test):
            self.started.append(SELECTED[0] if test is case else 'NOT_CAPTURED'); event('started',test); super().startTest(test)
        def stopTest(self,test):
            self.stopped.append(SELECTED[0] if test is case else 'NOT_CAPTURED'); event('stopped',test); super().stopTest(test)
    try:
        events=(output/'events.jsonl').open('xb'); log=(output/'TESTS.log').open('x',encoding='utf-8')
        result=Result(); assert authorize()==claims
        result.startTestRun()
        try: suite.run(result)
        finally: result.stopTestRun()
    except BaseException as error:
        if result is not None and result.originals:
            primary_info=result.originals[0][3]; primary=primary_info[1]; secondary.append(error)
        else:
            primary=error; primary_info=sys.exc_info()
    finally:
        if result is not None:
            try:
                formatted=formatted_outcomes(result,case,SELECTED[0])
                if log is not None:
                    json.dump(dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
                        formatted_outcomes=formatted),log,allow_nan=False)
                    log.write('\n')
            except BaseException as error:secondary.append(error)
        for handle in (events,log):
            if handle is not None:
                try: handle.flush(); os.fsync(handle.fileno())
                except BaseException as error: secondary.append(error)
                try: handle.close()
                except BaseException as error: secondary.append(error)
        try: after_source=observe_source()
        except BaseException as error: secondary.append(error)
        for name,path in fixtures.items():
            try: after[name]=r.snapshot(path); r.preservation(before[name],after[name])
            except BaseException as error: secondary.append(error)
    complete=False; report={}
    try:
        observation=None if result is None else result.report()
        faults=[] if result is None else result.faults
        secondary.extend(e for _,e,_ in faults)
        if primary is None and secondary:
            if result is not None and result.originals:
                primary_info=result.originals[0][3]; primary=primary_info[1]
            else: primary=secondary[0]
        complete=(result is not None and result.testsRun==1 and result.started==result.stopped==SELECTED
            and result.wasSuccessful() and result.coverage_complete and observation['coverage_complete'] is True
            and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses and not result.shouldStop
            and primary is None and not secondary and before_source==after_source and len(after)==len(before))
        report=dict(test_cohort_passed=complete,selected_test_ids=SELECTED,started_test_ids=[] if result is None else result.started,
            stopped_test_ids=[] if result is None else result.stopped,tests_run=None if result is None else result.testsRun,
            failures=None if result is None else len(result.failures),errors=None if result is None else len(result.errors),
            skips=None if result is None else len(result.skipped),expected_failures=None if result is None else len(result.expectedFailures),
            unexpected_successes=None if result is None else len(result.unexpectedSuccesses),early_stop=None if result is None else result.shouldStop,
            observation=observation,formatted_outcomes=formatted,primary=r.diagnostic(primary),secondary=[r.diagnostic(e) for e in secondary],source_after=after_source,
            fixtures_after=after,one_attempt=True,successful_guard_timings='NOT_MEASURED',provider_spans='NOT_MEASURED',full_product_acceptance=False)
    except BaseException as error:
        secondary.append(error)
        if primary is None:
            if result is not None and result.originals: primary_info=result.originals[0][3]; primary=primary_info[1]
            else: primary=error; primary_info=sys.exc_info()
        report=dict(test_cohort_passed=False,diagnostic_incomplete=True,formatted_outcomes=formatted,full_product_acceptance=False)
    try: save(output/'RESULT.json',report)
    except BaseException as error:
        secondary.append(error)
        if primary is None:
            if result is not None and result.originals: primary_info=result.originals[0][3]; primary=primary_info[1]
            else: primary=error; primary_info=sys.exc_info()
    if primary is not None or secondary:
        try: save(output/'REPORT-ERROR.json',dict(diagnostic_incomplete=True,full_product_acceptance=False))
        except BaseException as error: secondary.append(error)
        if primary is None: primary=secondary[0]
        if primary_info is None: primary_info=(type(primary),primary,BaseException.__dict__['__traceback__'].__get__(primary))
        attrs=BaseException.__dict__['__dict__'].__get__(primary)
        dict.__setitem__(attrs,'runner_primary_exc_info',primary_info); dict.__setitem__(attrs,'runner_secondary_errors',tuple(secondary))
        raise BaseException.with_traceback(primary,primary_info[2])
    try:
        save(output/'REPORT-SEAL.json',dict(result_sha256=sha(output/'RESULT.json'),start_sha256=sha(output/'START.json'),
            events_sha256=sha(output/'events.jsonl'),log_sha256=sha(output/'TESTS.log'),test_cohort_passed=complete,
            requires_actual_process_exit_zero=True,full_product_acceptance=False))
    except BaseException as error:
        secondary.append(error)
        if result is not None and result.originals: primary_info=result.originals[0][3]; primary=primary_info[1]
        else: primary=error; primary_info=sys.exc_info()
        try:save(output/'REPORT-ERROR.json',dict(phase='REPORT-SEAL',diagnostic_incomplete=True,full_product_acceptance=False))
        except BaseException as extra:secondary.append(extra)
        attrs=BaseException.__dict__['__dict__'].__get__(primary)
        dict.__setitem__(attrs,'runner_primary_exc_info',primary_info); dict.__setitem__(attrs,'runner_secondary_errors',tuple(secondary))
        raise BaseException.with_traceback(primary,primary_info[2])
    return 0 if complete else 1

def load_frozen(pin):
    assert K==F/'.agents/runtime/oq23/tm2' and sys.flags.optimize==0
    assert sha(W/'MANIFEST.json')==pin
    manifest=json.loads((W/'MANIFEST.json').read_bytes())
    for name,value in manifest['work_hashes'].items(): assert sha(W/name)==value
    for name,value in manifest['external_pins'].items(): assert sha(Path(name))==value
    assert sha(K/'packet/INPUTS.json')==PACKET_SHA and sha(K/'packet/PLAN.md')==PLAN_SHA
    packet=json.loads((K/'packet/INPUTS.json').read_bytes()); binding=json.loads((W/'BINDING.json').read_bytes())
    assert Path(sys.executable).resolve()==Path(packet['python']).resolve() and sha(Path(sys.executable))==packet['python_sha256']
    binding['prepared_manifest_sha256']=pin
    r=support(binding)
    actual=r.snapshot(W); allowed={'MANIFEST.json','PREPARED.stdout','PREPARED.stderr','PREPARED.json'}
    assert set(actual)-allowed==set(manifest['work_observation'])
    r.preservation(manifest['work_observation'],actual)
    return packet,binding,r

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--manifest-sha256',required=True)
    args=parser.parse_args(); packet,binding,r=load_frozen(args.manifest_sha256)
    r.source_observation(binding); claims=require_live(binding,r)
    suite,case,bound,identity,modules=canonical_suite(packet,r)
    assert identity==json.loads((W/'COLLECTION.json').read_bytes())['guard_binding']
    from ceta.store.sqlite_runtime import runtime_identity
    sqlite=runtime_identity(); assert Path(sqlite['dll_path'])==F/'native/sqlite_runtime/win-x64/sqlite3.dll'
    metadata=dict(source_root=str(F),ordinary_imports=True,ROOT_override=False,module_overlay=False,
        test_modules=modules,dependencies=dependencies(r),sqlite=sqlite,guard_binding=identity,
        interpreter=dict(path=sys.executable,native=r.stable(Path(sys.executable))[0]),journal_success=prerequisite(binding))
    assert require_live(binding,r)==claims
    return run_observed(suite,case,bound,K/'delivery',r,lambda:r.source_observation(binding),lambda:require_live(binding,r),
        {n:Path(p) for n,p in packet['fixture_workspaces'].items()},metadata)

if __name__=='__main__': raise SystemExit(main())
