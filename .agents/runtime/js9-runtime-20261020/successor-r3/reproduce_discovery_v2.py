"""Actual import/discovery only; no test, fixture, process, profile or socket work."""
from pathlib import Path
import ast, hashlib, importlib, json, os, sys, traceback, unittest
from datetime import datetime, timezone

F=Path('T:/00-Active/Project-AI-CETA');D2=F/'.agents/runtime/js9-runtime-20261020/successor-r2'
R=Path(__file__).resolve().parent;Q=F/'.agents/js9-runtime-20261020'
denied=[];libraries=[];symbols=[];stages=[]
def audit(event,args):
    if event=='ctypes.dlopen': libraries.append(str(args[0]))
    if event=='ctypes.dlsym': symbols.append(str(args[1]))
    reason=None
    if event.startswith(('subprocess.','socket.')) or event in ('os.system','os.startfile','os.posix_spawn','os.fork','sqlite3.connect'):
        reason='PROCESS_SOCKET_OR_SQLITE_FIXTURE_DENIED'
    if event=='open':
        path,mode,flags=args
        writing=(isinstance(mode,str) and any(token in mode for token in 'wax+')) or (isinstance(flags,int) and bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)))
        if writing and (not isinstance(path,(str,bytes,os.PathLike)) or not Path(os.fsdecode(path)).resolve().is_relative_to(R)):
            reason='WRITE_OUTSIDE_DIAGNOSTIC_SCOPE'
    if event in ('os.mkdir','os.rmdir','os.remove','os.rename','os.link','os.symlink','os.chmod','os.utime'):
        reason='FIXTURE_MUTATION_DENIED'
    if reason:
        denied.append(dict(event=event,reason=reason,arguments=[str(value) for value in args]))
        raise RuntimeError(reason+':'+event)
sys.addaudithook(audit)

def profile(frame,event,arg):
    if event!='call': return
    name=frame.f_code.co_name;filename=frame.f_code.co_filename.replace('\\','/')
    if filename.startswith(str(Q).replace('\\','/')) and (
        name.startswith(('test_','setUp','tearDown')) or name in ('setUpModule','tearDownModule','run_native_probe')):
        denied.append(dict(event='python.call',reason='TEST_OR_FIXTURE_BODY_DENIED',file=filename,function=name))
        raise RuntimeError('TEST_OR_FIXTURE_BODY_DENIED:'+name)
    if name=='__init__' and any(token in frame.f_code.co_qualname for token in ('_IsolationAPI.','WindowsOwnedProcess.','NativeStoreBinding.','SqliteJournal.','_CapacityRuntime.')):
        denied.append(dict(event='python.call',reason='NATIVE_OR_SQLITE_OWNER_ACQUISITION_DENIED',file=filename,function=frame.f_code.co_qualname))
        raise RuntimeError('NATIVE_OR_SQLITE_OWNER_ACQUISITION_DENIED:'+frame.f_code.co_qualname)
sys.setprofile(profile)

report=dict(started_at=datetime.now(timezone.utc).isoformat(),mode='ACTUAL_IMPORT_AND_DISCOVERY_ONLY',
    no_test_bodies=True,no_fixture_preparation=True,standard_library_imports_permitted=True,
    denied_calls=denied,libraries=libraries,native_symbol_lookups=symbols,stages=stages)
primary=None;loader=None
try:
    sys.path[:0]=[str(D2),str(Q/'src'),str(Q/'tools'),str(Q/'tests/contract')]
    import js9_support as j
    assert hashlib.sha256((D2/'PACKET.json').read_bytes()).hexdigest()=='eb5f4c993a74f7b378db9b2dd10e039fadc64ebff3c31887c78393ce58157055'
    manifest=j.manifest()
    stages.append('load_pinned_sqlite_library_no_connection')
    from ceta.store.sqlite_runtime import load_sqlite,runtime_identity
    load_sqlite();report['sqlite_library_identity']=runtime_identity()
    stages.append('actual_dependency_imports')
    for name in ('PySide6','shiboken6','jsonschema','attrs','referencing','rpds'):importlib.import_module(name)
    stages.append('actual_product_imports')
    for name in manifest['product_modules']:
        path=Q/name;parts=list(path.relative_to(Q/'src').with_suffix('').parts)
        if parts[-1]=='__init__':parts.pop()
        module=importlib.import_module('.'.join(parts))
        assert Path(module.__file__).resolve()==path,('PRODUCT_ORIGIN',name)
    stages.append('actual_unittest_discover')
    loader=unittest.TestLoader();suite=loader.discover(str(Q/'tests/contract'),pattern='test_*.py')
    actual=list(j.ids(suite));report['discovered_ids']=actual
    report['loader_errors']=list(loader.errors)
    cases=json.loads((D2/'CASESET.json').read_bytes());report['expected_ids']=cases['expected_ids']
    stages.append('actual_explicit_namespace_imports')
    explicit=[]
    for name in cases['explicit_namespace_modules']:
        module=importlib.import_module(name);explicit.extend(j.ids(loader.loadTestsFromModule(module)))
    report['explicit_ids']=explicit;combined=actual+explicit
    report['combined_ids']=combined
    report['duplicates']=sorted(name for name in set(combined) if combined.count(name)>1)
    report['missing']=sorted(set(cases['expected_ids'])-set(combined))
    report['unexpected']=sorted(set(combined)-set(cases['expected_ids']))
    stages.append('exact_ordered_suite')
    ordered=j.ordered_suite(suite,Q,loader)
    report['ordered_ids']=list(j.ids(ordered))
    stages.append('exact_require_case_ids')
    j.require_case_ids(report['ordered_ids']);assert not loader.errors
    stages.append('exact_configure_suite_no_test_call')
    import fixture_runtime
    report['controlled_arithmetic_before_tests']=fixture_runtime.configure_suite(ordered)
    stages.append('preflight_discovery_complete')
except BaseException as error:
    primary=error
    report['primary_error']=dict(type=type(error).__name__,message=str(error),traceback=''.join(traceback.format_exception(error)))
finally:
    sys.setprofile(None)
    if loader is not None:report['loader_errors']=list(loader.errors)
    report['finished_at']=datetime.now(timezone.utc).isoformat()
    report['exit_status']=0 if primary is None else 1
    output=R/'ACTUAL-DISCOVERY-R2.json'
    with output.open('x',encoding='utf8') as stream:json.dump(report,stream,indent=2);stream.write('\n')
print(json.dumps(dict(exit_status=report['exit_status'],stages=stages,
    discovered=len(report.get('discovered_ids',[])),combined=len(report.get('combined_ids',[])),
    missing=report.get('missing'),unexpected=report.get('unexpected'),duplicates=report.get('duplicates'),
    loader_errors=report.get('loader_errors'),primary_error=report.get('primary_error'),denied=denied,
    output=str(output),sha256=hashlib.sha256(output.read_bytes()).hexdigest())),flush=True)
sys.exit(report['exit_status'])
