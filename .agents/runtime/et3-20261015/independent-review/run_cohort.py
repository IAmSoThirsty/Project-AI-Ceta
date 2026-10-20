"""Exact ET3 cases on reviewer-owned byte copies; live native custody, no effects."""
from review_support import *
import contextlib, ctypes, functools, importlib, threading, unittest
from unittest.mock import patch
M=D/'replica'; label=sys.argv[1]
assert label in ('connected','native')
E=D/(label+'-r1'); E.mkdir()
os.environ['TEMP']=os.environ['TMP']=str(E)
sys.path[:0]=[str(M/'src'),str(M/'tests/contract')]
from ceta.store.sqlite_runtime import load_sqlite,runtime_identity
load_sqlite()
from ceta.store.journal import SqliteJournal
from ceta.supervisor.windows_jobs import WindowsOwnedProcess
names=['test_fresh_observer_reconciliation','test_owned_cpu_outcome_transactions','test_owner_authority_transactions',
    'test_kernel_transactions','test_kernel_authority','test_kernel_recovery','test_store_transactions',
    'test_read_sets','test_temporal','test_wire','test_all_records','test_real_effect_contract',
    'test_owner_enrollment','test_resource_reservations']
modules=[importlib.import_module(name) for name in names]
if label=='native': suite=unittest.defaultTestLoader.loadTestsFromTestCase(sys.modules['test_kernel_authority'].NativeAuthorityResolutionTests)
else: suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m) for m in modules)
def ids(group):
    if isinstance(group,unittest.TestSuite):
        for item in group: yield from ids(item)
    else: yield group.id()
expected=list(ids(suite))
author=json.loads((R/('connected-r1.json' if label=='connected' else 'native-custody-r1/RESULT.json')).read_text())
assert expected==author['expected_ids'] and len(expected)==len(set(expected))==(406 if label=='connected' else 3)
setup=json.loads((D/'PREPARATION.json').read_text())
def conserved():
    assert all(ordinary(Q/name)==row for name,row in setup['original_candidate'].items())
    assert all(ordinary(M/name)==row for name,row in setup['replica'].items())
    assert all(ordinary(F/name)==row for name,row in setup['Source290'].items())
conserved()
owners,launched,stores,executed,stopped=[],[],[],[],[]
live_events=[];forbidden=[];class9=[]
real_dll=ctypes.WinDLL
class Forbidden:
    def __init__(self,name):self.name=name
    def __call__(self,*args,**kwargs):forbidden.append(self.name);raise AssertionError('FORBIDDEN_NATIVE_PROFILE_RESTRICTED_LAUNCH_OR_CPU_EFFECT')
class JobSet:
    def __init__(self,original):object.__setattr__(self,'original',original)
    def __getattr__(self,name):return getattr(self.original,name)
    def __setattr__(self,name,value):setattr(self.original,name,value)
    def __call__(self,job,kind,*args):
        value=kind if type(kind) is int else kind.value
        if value==15:forbidden.append('SetInformationJobObject:15');raise AssertionError('CPU_POLICY_SET_FORBIDDEN')
        assert value==9,('Unexpected job mutation',value)
        class9.append({'at':utc(),'job':int(job) if type(job) is int else job.value,'class':value})
        return self.original(job,kind,*args)
class DLL:
    def __init__(self,original):self.original=original
    def __getattr__(self,name):
        if name in ('CreateAppContainerProfile','DeleteAppContainerProfile','CreateProcessAsUserW','CreateProcessWithTokenW','CreateProcessWithLogonW'):
            return Forbidden(name)
        function=getattr(self.original,name)
        return JobSet(function) if name=='SetInformationJobObject' else function
def guarded_dll(name,*args,**kwargs):return DLL(real_dll(name,*args,**kwargs))
def stream(value):
    with (E/'lifetimes.jsonl').open('a',encoding='utf8') as out:
        out.write(json.dumps(value)+'\n');out.flush();os.fsync(out.fileno())
def owner_row(owner):
    return {'pid':owner.pid,'creation_time':owner.creation_time,'image_sha256':owner.image_sha256,
        'lifetime_closed':owner.lifetime_closed,'process_closed':owner._process is None,
        'job_closed':owner._job is None,'thread_closed':owner._thread is None}
original_owner,original_launch,original_close=WindowsOwnedProcess.__init__,WindowsOwnedProcess.launch.__func__,WindowsOwnedProcess.close
original_store=SqliteJournal.__init__
def owner_init(owner,*args,**kwargs):
    try:original_owner(owner,*args,**kwargs)
    finally:
        if hasattr(owner,'_process'):owners.append(owner)
def observed_launch(cls,*args,**kwargs):
    owner=original_launch(cls,*args,**kwargs)
    assert type(owner.pid) is int and owner.pid>0 and type(owner.creation_time) is int and owner.creation_time>0
    launched.append(owner)
    event={'at':utc(),'phase':'AFTER_CANONICAL_LAUNCH_NATIVE_LIFETIME_ASSIGNED',**owner_row(owner),
        'poll':owner.poll(),'active_job_processes':owner.active_process_count()}
    live_events.append(event);stream(event)
    return owner
def observed_close(owner,*args,**kwargs):
    if not owner.lifetime_closed and owner._process is not None:
        stream({'at':utc(),'phase':'BEFORE_CANONICAL_CLOSE','pid':owner.pid,'creation_time':owner.creation_time,
            'poll':owner.poll(),'active_job_processes':owner.active_process_count()})
    try:return original_close(owner,*args,**kwargs)
    finally:stream({'at':utc(),'phase':'AFTER_CANONICAL_CLOSE',**owner_row(owner)})
def store_init(store,*args,**kwargs):
    try:original_store(store,*args,**kwargs)
    finally:
        if hasattr(store,'_closed'):stores.append(store)
class Result(unittest.TextTestResult):
    def startTest(self,test):executed.append(test.id());super().startTest(test)
    def stopTest(self,test):
        stopped.append(test.id())
        for owner in owners:stream({'at':utc(),'phase':'CASE_STOP_AFTER_TEARDOWN','test':test.id(),**owner_row(owner)})
        super().stopTest(test)
old_threads=set(threading.enumerate());started=utc()
write(E/'PREFLIGHT.json',{'at':started,'expected_ids':expected,'original_Q_preserved':True,
    'replica_byte_exact':True,'sqlite':runtime_identity(),'native_guard':'No profile/restricted launch/class15Set; canonical owned class9 setup allowed',
    'native_custody':'Record live PID/creation/job membership after canonical launch, and closed handle observations after cleanup; no constructor snapshot substituted'})
with patch.object(ctypes,'WinDLL',guarded_dll),patch.object(WindowsOwnedProcess,'__init__',owner_init),\
    patch.object(WindowsOwnedProcess,'launch',classmethod(observed_launch)),patch.object(WindowsOwnedProcess,'close',observed_close),\
    patch.object(SqliteJournal,'__init__',store_init),(E/'tests.txt').open('x',encoding='utf8',buffering=1) as out:
    with contextlib.redirect_stdout(out),contextlib.redirect_stderr(out):
        result=unittest.TextTestRunner(stream=out,verbosity=2,resultclass=Result).run(suite)
remaining=[{'name':t.name,'native_id':t.native_id} for t in set(threading.enumerate())-old_threads if t.is_alive()]
store_rows=[{'path':str(s.path),'closed':s._closed} for s in stores]
owner_rows=[owner_row(owner) for owner in owners]
all_closed=all(row['closed'] for row in store_rows) and all(all(row[key] for key in ('lifetime_closed','process_closed','job_closed','thread_closed')) for row in owner_rows)
imports={name:str(Path(m.__file__).resolve()) for name,m in sys.modules.items() if (name=='ceta' or name.startswith('ceta.')) and getattr(m,'__file__',None)}
assert all(Path(path).is_relative_to(M/'src') for path in imports.values())
if label=='native':assert len(launched)==len(owner_rows)==6
conserved()
passed=result.wasSuccessful() and not result.skipped and expected==executed==stopped and all_closed and not remaining and not forbidden
write(E/'RESULT.json',{'started_at':started,'finished_at':utc(),'tests_run':result.testsRun,
    'expected_ids':expected,'executed_ids':executed,'stopped_ids':stopped,
    'failures':[{'id':t.id(),'traceback':tb} for t,tb in result.failures],
    'errors':[{'id':t.id(),'traceback':tb} for t,tb in result.errors],'skips':result.skipped,
    'stores':store_rows,'native_owners':owner_rows,'live_launch_events':live_events,
    'all_observed_resources_closed':all_closed,'remaining_threads':remaining,'forbidden_calls':forbidden,
    'canonical_fresh_owned_class9_setup':class9,'source_imports':imports,'sqlite_identity':runtime_identity(),
    'crash_observations':sys.modules['test_owned_cpu_outcome_transactions'].CRASH_OBSERVATIONS,
    'raw_sha256':sha(E/'tests.txt'),'streamed_native_custody_sha256':sha(E/'lifetimes.jsonl'),
    'original_Q_Source290_replica_input_bytes_exact':True,'genuine_native_proof_provider':'NOT_QUALIFIED_CONTROLLED_DOMAIN_FIXTURES',
    'profile_operations':[],'CPU_policy_effects':[],'exit_status':0 if passed else 1})
print(json.dumps({'mode':label,'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
    'skips':len(result.skipped),'stores':len(store_rows),'launched_lifetimes':len(launched),
    'all_closed':all_closed,'new_threads':remaining,'exit_status':0 if passed else 1}),flush=True)
sys.exit(0 if passed else 1)
