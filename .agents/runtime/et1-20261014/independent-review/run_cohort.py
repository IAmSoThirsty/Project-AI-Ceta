from pathlib import Path
import functools,importlib,json,os,subprocess,sys,threading,unittest
P=Path('T:/00-Active/Project-AI-CETA');Q=P/'.agents/et1-20261014';BASE=P/'.agents/runtime/et1-20261014';D=BASE/'independent-review';M=D/'replica'
sys.path.insert(0,str(P/'.agents/runtime/ka1-20261014'));import ka1_support as s
s.Q=Q;s.R=D;s.RUN='et1-20261014'
setup=json.loads((D/'PREPARATION.json').read_text());E=D/'cohort-r1';E.mkdir()
os.environ['TEMP']=os.environ['TMP']=str(E);sys.path[:0]=[str(M/'src'),str(M/'tests/contract')]
from ceta.store.sqlite_runtime import load_sqlite,runtime_identity
load_sqlite();sqlite=runtime_identity()
names=('test_owned_cpu_outcome_transactions','test_owner_authority_transactions','test_kernel_transactions',
 'test_kernel_authority','test_kernel_recovery','test_store_transactions','test_read_sets','test_temporal',
 'test_wire','test_all_records','test_real_effect_contract','test_owner_enrollment','test_resource_reservations')
modules=[importlib.import_module(name) for name in names]
from ceta.store.journal import SqliteJournal
from ceta.supervisor.windows_jobs import WindowsOwnedProcess
journals=[];processes=[]
def observer(cls,target,qualify):
    original=cls.__init__
    @functools.wraps(original)
    def observed(self,*args,**kwargs):
        try:original(self,*args,**kwargs)
        finally:
            if qualify(self):target.append(self)
    cls.__init__=observed
observer(SqliteJournal,journals,lambda value:hasattr(value,'_closed'))
observer(WindowsOwnedProcess,processes,lambda value:hasattr(value,'_process'))
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(module) for module in modules)
def ids(group):
    for item in group:
        if isinstance(item,unittest.TestSuite):yield from ids(item)
        else:yield item.id()
expected=list(ids(suite));author=json.loads((BASE/'connected-r1.json').read_text())
assert expected==author['expected_ids'] and len(expected)==len(set(expected))==385
executed=[];stopped=[];threads=set(threading.enumerate());started=s.utc()
class Result(unittest.TextTestResult):
    def startTest(self,test):executed.append(test.id());super().startTest(test)
    def stopTest(self,test):stopped.append(test.id());super().stopTest(test)
s.write_new(E/'PREFLIGHT.json',dict(recorded_at=started,expected_ids=expected,replica_root=str(M),sqlite_identity=sqlite,
    module_bytes_exact_to_Q=True,native_effect_invocation=False))
with (E/'tests.txt').open('x',encoding='utf-8',buffering=1) as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
remaining=[dict(name=t.name,native_id=t.native_id) for t in set(threading.enumerate())-threads if t.is_alive()]
stores=[dict(path=str(o.path),closed=o._closed) for o in journals]
owners=[dict(pid=getattr(o,'pid',None),creation_time=getattr(o,'creation_time',None),closed=o.lifetime_closed,
    process_closed=o._process is None,job_closed=o._job is None,thread_closed=o._thread is None) for o in processes]
imports={name:str(Path(value.__file__).resolve()) for name,value in sys.modules.items()
    if (name=='ceta' or name.startswith('ceta.')) and getattr(value,'__file__',None)}
assert all(Path(path).is_relative_to(M/'src') for path in imports.values())
assert all(s.ordinary(Q/name)==row for name,row in setup['original_candidate'].items())
assert all(s.ordinary(M/name)==row for name,row in setup['replica'].items())
assert all(s.ordinary(P/name)==row for name,row in setup['Source290'].items())
closed=all(o['closed'] for o in stores) and all(o['closed'] and o['process_closed'] and o['job_closed'] and o['thread_closed'] for o in owners)
passed=result.wasSuccessful() and not result.skipped and expected==executed==stopped and closed and not remaining
s.write_new(D/'COHORT.json',dict(started_at=started,finished_at=s.utc(),tests_run=result.testsRun,expected_ids=expected,executed_ids=executed,stopped_ids=stopped,
    failures=[(t.id(),tb) for t,tb in result.failures],errors=[(t.id(),tb) for t,tb in result.errors],skips=result.skipped,
    raw=s.reference(E/'tests.txt'),remaining_threads=remaining,journals=stores,native_process_owners=owners,all_observed_resources_closed=closed,
    crash_observations=modules[0].CRASH_OBSERVATIONS,imports=imports,sqlite_identity=sqlite,
    original_Q_and_Source_native_bytes_retained=True,replica_native_bytes_retained=True,
    positive_native_provider='CONTROLLED DOMAIN FIXTURES; no actual native effect/observer/approval authority.',exit_status=0 if passed else 1))
print(json.dumps(dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),journals=len(stores),native_owners=len(owners),remaining_threads=remaining,exit_status=0 if passed else 1)),flush=True)
sys.exit(0 if passed else 1)
