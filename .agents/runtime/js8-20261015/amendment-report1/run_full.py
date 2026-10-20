"""Joined unchanged-method full runner; exact Root phase/native releases required."""
from pathlib import Path
import argparse,importlib,importlib.metadata,json,os,sys,threading,time,traceback,unittest
import amendment_support as j
from amendment_support import s,F,Q,R,PY

def execute(args,release,v,gate):
    after=args.phase=='destination-full'
    interpreter=j.interpreter_observation(v)
    root=F if after else Q;m=j.manifest();before={name:s.ordinary(root/name)['sha256'] for name in m['expected_payload_hashes']}
    output=R/args.phase;output.mkdir(exist_ok=False);temporary=output/'temporary';temporary.mkdir(exist_ok=False)
    os.environ.update(QT_QPA_PLATFORM='offscreen',TEMP=str(temporary),TMP=str(temporary))
    sys.path[:0]=[str(root/'src'),str(root/'tools'),str(root/'tests/contract')]
    # The one canonical DLL must be loaded before any test imports sqlite3.
    from ceta.store.sqlite_runtime import load_sqlite,runtime_identity
    load_sqlite();sqlite_identity=runtime_identity()
    dependencies=[]
    for distribution,name in [('PySide6','PySide6'),('PySide6_Essentials','PySide6'),('shiboken6','shiboken6'),
        ('jsonschema','jsonschema'),('attrs','attrs'),('referencing','referencing'),('rpds-py','rpds')]:
        module=importlib.import_module(name);path=Path(module.__file__).resolve()
        assert path.is_relative_to(PY.parents[1]/'Lib/site-packages')
        try:version=importlib.metadata.version(distribution);metadata='AVAILABLE'
        except importlib.metadata.PackageNotFoundError:version=None;metadata='UNAVAILABLE_DISTRIBUTION_METADATA'
        dependencies.append({'distribution':distribution,'module':name,'version':version,'metadata':metadata,'file':s.ordinary(path)})
    modules=[]
    for path in sorted((root/'src/ceta').rglob('*.py')):
        parts=list(path.relative_to(root/'src').with_suffix('').parts)
        if parts[-1]=='__init__':parts.pop()
        module=importlib.import_module('.'.join(parts));assert Path(module.__file__).resolve()==path
        modules.append(s.ordinary(path))
    assert len(modules)==88
    from fixture_runtime import prepare,configure_suite,NativeObservations
    from resource_observer import Observer as ResourceObserver
    import sqlite3
    physical=ResourceObserver(sqlite3);physical.install()
    native=NativeObservations();native.install()
    fixture_wiring=prepare(root,output,gate)
    loader=unittest.TestLoader();suite=loader.discover(str(root/'tests/contract'),pattern='test_*.py')
    expected=list(j.ids(suite));j.require_case_ids(expected);assert not loader.errors
    controlled_arithmetic=configure_suite(suite)
    from gc_observer import Observer,native_handle_count
    observer=Observer(native_handle_count());observer.install() # No API class supplied: no native wrapping.
    threads=set(threading.enumerate());started=s.utc();tick=time.perf_counter();executed=[];stopped=[];primary=result=None
    def save(path,value):j.write_bytes(path,(json.dumps(value,indent=2,allow_nan=False)+'\n').encode())
    save(output/'PREFLIGHT.json',{'at':started,'phase':args.phase,'root':str(root),'expected_ids':expected,
        'argv':list(sys.orig_argv),'interpreter':interpreter,
        'before_hashes':before,'manifest_sha256':s.sha(Q/'TRANSFER-MANIFEST.json'),'release':j.exact_ref(args.release_path),
        'product_modules':modules,'dependencies':dependencies,'sqlite_runtime':sqlite_identity,
        'native_api_wrappers':'Only the separately reviewed original-case no-profile gate; enclosing owner constructors are observed.',
        'native_case_release':release['native_case_release'],'fixture_wiring':fixture_wiring,
        'product_deadline_changes':False,'test_order_amendment':j.exact_ref(R/'AMENDMENT.json')})
    event_stream=(output/'CASE-EVENTS.jsonl').open('x',encoding='utf-8',buffering=1)
    def case_event(kind,test,**details):
        row=dict(event=kind,test_id=test.id(),at=s.utc(),elapsed_seconds=time.perf_counter()-tick,**details)
        raw=json.dumps(row,allow_nan=False)+'\n'
        assert event_stream.write(raw)==len(raw),'CASE_EVENT_SHORT_WRITE'
        event_stream.flush()
    class Result(unittest.TextTestResult):
        def startTest(self,test):
            case_event('PREPARE',test)
            gate.enter(test.id());native.active_case=test.id()
            observer.before_test(test.id());executed.append(test.id());super().startTest(test)
            case_event('START',test)
        def stopTest(self,test):
            primary=None
            try:
                gate.finish_case(test.id())
                if test.id()==m['native_gate']['original_case_id']:
                    # The bounded native permission ends at its original case.
                    # Guards stay installed for subsequent ordinary cases.
                    proof=gate.finish()
                    gate.close(preserve_guards=True)
                    proof['release_reader_closed']=gate.reader.closed
                    gate.completed_case_proof=proof
                    save(output/'NATIVE-CASE-EARLY-PROOF.json',proof)
            except BaseException as error:
                primary=error
                raise
            finally:
                try:
                    native.active_case=None;stopped.append(test.id());super().stopTest(test)
                    case_event('STOP',test)
                except BaseException as secondary:
                    if primary is None:raise
                    j.retain(primary,secondary,'case-stop-diagnostics')
        def addFailure(self,test,error):
            super().addFailure(test,error)
            case_event('FAILURE',test,traceback=self.failures[-1][1])
        def addError(self,test,error):
            super().addError(test,error)
            case_event('ERROR',test,traceback=self.errors[-1][1])
        def addSubTest(self,test,subtest,error):
            super().addSubTest(test,subtest,error)
            if error is not None:
                case_event('SUBTEST_FAILURE',subtest,traceback=self._exc_info_to_string(error,test))
    stream=None
    try:
        stream=(output/'RAW.txt').open('x',encoding='utf-8',buffering=1)
        result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
    except BaseException as error:primary=error
    finally:
        if stream is not None:
            try:j.close(stream,primary,'test-log-close')
            except BaseException as error:primary=error
        try:j.close(event_stream,primary,'case-events-close')
        except BaseException as error:
            if primary is None:primary=error
            else:j.retain(primary,error,'case-events-close')
        try:observer.uninstall()
        except BaseException as error:
            if primary is None:primary=error
            else:j.retain(primary,error,'observer-uninstall')
        for operation,label in ((physical.uninstall,'physical-observer-uninstall'),(native.uninstall,'native-observer-uninstall')):
            try:operation()
            except BaseException as error:
                if primary is None:primary=error
                else:j.retain(primary,error,label)
    try:
        remaining=[{'name':t.name,'native_id':t.native_id} for t in set(threading.enumerate())-threads if t.is_alive()]
        receipts={name:getattr(sys.modules[name],field) for name,field in [
            ('test_journal_constructor_cleanup','NATIVE_CONNECTION_RECEIPTS'),('test_journal_postconstruction_cleanup','NATIVE_RECEIPTS')]}
        closed=all(row['all_fixture_native_connections_closed'] for row in receipts['test_journal_constructor_cleanup'])
        closed=closed and all(row['all_exact_native_connections_closed'] for row in receipts['test_journal_postconstruction_cleanup'])
        save(output/'SQLITE-RECEIPTS.json',receipts)
        physical_proof=physical.finish();native_proof=native.finish()
        save(output/'PHYSICAL-CUSTODY.json',physical_proof)
        save(output/'NATIVE-OWNERS.json',native_proof)
        after_hashes={name:s.ordinary(root/name)['sha256'] for name in m['expected_payload_hashes']}
        j.verify(source='after' if after else 'before')
        assert j.interpreter_observation(v)==interpreter
        counts={'tests_run':result.testsRun if result is not None else len(executed),
            'failures':len(result.failures) if result is not None else 0,'errors':len(result.errors) if result is not None else 0,
            'skips':len(result.skipped) if result is not None else 0}
        success=(primary is None and result is not None and result.wasSuccessful() and not counts['skips'] and
            executed==stopped==expected and not observer.failed and not remaining and closed and
            physical_proof['owned_resources_closed'] and native_proof['owned_resources_closed'] and
            before==after_hashes==m['expected_payload_hashes'])
        report={'phase':args.phase,'started_at':started,'finished_at':s.utc(),'elapsed_seconds':time.perf_counter()-tick,
            'argv':list(sys.orig_argv),'interpreter':interpreter,
            'manifest_sha256':s.sha(Q/'TRANSFER-MANIFEST.json'),'expected_ids':expected,'executed_ids':executed,'stopped_ids':stopped,**counts,
            'failure_details':[(test.id(),detail) for test,detail in result.failures] if result is not None else [],
            'error_details':[(test.id(),detail) for test,detail in result.errors] if result is not None else [],
            'skip_details':[(test.id(),reason) for test,reason in result.skipped] if result is not None else [],
            'uniform_pre_test_collection':observer.test_rows,'gc_events':observer.gc_rows,'gc_observation_failed':observer.failed,
            'suite_aborted':primary is not None,'primary_error':{'type':type(primary).__name__} if primary is not None else None,
            'remaining_threads':remaining,'captured_journal_fixtures_closed':closed,'sqlite_receipts':j.exact_ref(output/'SQLITE-RECEIPTS.json'),
            'sqlite_runtime':sqlite_identity,'product_modules':modules,'dependencies':dependencies,
            'physical_custody':j.exact_ref(output/'PHYSICAL-CUSTODY.json'),
            'native_owners_proof':j.exact_ref(output/'NATIVE-OWNERS.json'),
            'controlled_arithmetic':controlled_arithmetic,'fixture_wiring':fixture_wiring,
            'deferred_ids':[],'mandatory_full_gate_complete':True,
            'expected_payload_hashes':m['expected_payload_hashes'],'before_hashes':before,'after_hashes':after_hashes,
            'source_unchanged':before==after_hashes,'Source_publication':False,'Source_accepted':False,
            'case_events':j.exact_ref(output/'CASE-EVENTS.jsonl'),'raw':j.exact_ref(output/'RAW.txt'),'release':j.exact_ref(args.release_path),'exit_status':0 if success else 1}
    except BaseException as secondary:
        if primary is None:raise
        j.retain(primary,secondary,'post-test-diagnostics')
        raise primary
    if primary is not None:raise primary
    return report

def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=('candidate-full','destination-full'))
    parser.add_argument('--release-path',type=Path,required=True);parser.add_argument('--release-sha256',required=True)
    args=parser.parse_args();release=j.require_release(args.release_path,args.release_sha256,args.phase)
    v=j.verify(source='after' if args.phase=='destination-full' else 'before')
    gate=j.capture_native_case_gate(release,args.phase)
    primary=report=native_proof=None
    try:
        gate.start()  # Create-only attempt/nonce, before the first CETA import.
        report=execute(args,release,v,gate)
    except BaseException as error:primary=error
    finally:
        try:
            native_proof=getattr(gate,'completed_case_proof',None)
            if native_proof is None:native_proof=gate.finish()
        except BaseException as error:
            if primary is None:primary=error
            else:j.retain(primary,error,'native-case-finish',gate)
        try:gate.close(primary)
        except BaseException as error:
            if primary is None:primary=error
            else:j.retain(primary,error,'native-case-release-close',gate)
    output=R/args.phase
    if output.is_dir():
        if native_proof is None:native_proof={'passed':False,'original_case_id':j.manifest()['native_gate']['original_case_id']}
        native_proof['release_reader_closed']=gate.reader.closed
        try:
            j.write_bytes(output/'NATIVE-CASE-PROOF.json',(json.dumps(native_proof,indent=2,allow_nan=False)+'\n').encode())
            if report is None:
                report=dict(phase=args.phase,tests_run=0,exit_status=1,suite_aborted=True,
                    primary_error=None if primary is None else {'type':type(primary).__name__},
                    Source_publication=False,Source_accepted=False)
            report['native_case_proof']=j.exact_ref(output/'NATIVE-CASE-PROOF.json')
            report['exit_status']=0 if primary is None and report['exit_status']==0 and native_proof['passed'] is True and gate.reader.closed else 1
            j.write_bytes(output/'RESULT.json',(json.dumps(report,indent=2,allow_nan=False)+'\n').encode())
        except BaseException as error:
            if primary is None:raise
            j.retain(primary,error,'result-writer')
    if primary is not None:raise primary
    assert report is not None
    print(json.dumps({'tests_run':report['tests_run'],'exit_status':report['exit_status'],'result':j.exact_ref(output/'RESULT.json')}),flush=True)
    return report['exit_status']
if __name__=='__main__':sys.exit(main())
