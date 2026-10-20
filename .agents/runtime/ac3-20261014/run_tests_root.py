"""Original AC2 cohort with one unapproved launch case deferred, plus AC3 native tests."""
from ac3_support import *
ACTOR="/root"
import ctypes as C,types,threading,unittest
from unittest.mock import patch
label=sys.argv[1] if len(sys.argv)==2 else 'native-r1'
assert label.replace('-','').isalnum()
D=R/label;D.mkdir()
harness=D/'harness';native_runtime=harness/'.agents/runtime/ac1-20261014'
native_runtime.mkdir(parents=True);(native_runtime/'build-r2').mkdir()
prior=F/'.agents/runtime/ac1-20261014'
driver=prior/'native_fixture_support.py';binary=prior/'build-r2/isolated_worker.exe'
assert sha(driver)=='a7247426deee70890107b9d826c7cda9209015edd5f1192f93ee3bd1e5a4314f'
assert sha(binary)=='527518104fb84c430e3e9e0be61982c533b0c6fbb13e1a85e959ba1a3866ad0f'
for source,target in [(driver,native_runtime/'native_fixture_support.py'),(binary,native_runtime/'build-r2/isolated_worker.exe')]:fs.write_new(target,fs.read_bytes(source))
os.environ.update(CETA_AC1_RUNTIME_ROOT=str(native_runtime),CETA_AC3_TEST_ROOT=str(D),CETA_AC3_IMAGE=str(binary))
sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
shim=types.ModuleType('ac_support');shim.__dict__.update({key:value for key,value in globals().copy().items() if not key.startswith('_')})
shim.Q=Q;shim.R=shim.D=native_runtime;sys.modules['ac_support']=shim
sys.path.insert(0,str(native_runtime))
import test_isolated_worker as tests
import test_windows_jobs as jobs
from ceta.supervisor import isolated_worker as module
from ceta.supervisor import windows_jobs as native
tests.ROOT=harness
fixture_root=D/'job-fixtures';fixture_root.mkdir()
class FixtureRoot:
    def __fspath__(self):return str(Q)
    def __str__(self):return str(Q)
    def __truediv__(self,value):
        text=str(value).replace('\\','/')
        if text=='.agents/fixtures':return fixture_root
        if text.startswith('.agents/fixtures/'):return fixture_root/text[len('.agents/fixtures/'):]
        return Q/value
jobs.ROOT=FixtureRoot()
def flatten(suite):
    for case in suite:
        if isinstance(case,unittest.TestSuite):yield from flatten(case)
        else:yield case
all_cases=list(flatten(unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(item) for item in (tests,jobs))))
deferred='test_isolated_worker.NativeIsolatedWorkerTests.test_actual_nonpersistent_launch_denial_and_medium_control_retirement'
assert sum(case.id()==deferred for case in all_cases)==1
suite=unittest.TestSuite(case for case in all_cases if case.id()!=deferred)
expected=[case.id() for case in suite];assert len(expected)==len(set(expected))
old=json.loads((F/'.agents/runtime/ac2-20261014/original-r4.json').read_text())['expected_ids']
assert len(old)==50 and set(old)-{deferred}<=set(expected)
executed,stopped,owners,apis,forbidden=[],[],[],[],[]
real_init,real_owner_init=module._IsolationAPI.__init__,native.WindowsOwnedProcess.__init__
def guarded_init(api,*args,**kwargs):
    real_init(api,*args,**kwargs);apis.append(api)
    def denied(*args):
        forbidden.append('restricted_CreateProcessW');raise AssertionError('AC3_NO_RESTRICTED_CREATE_AUTHORITY')
    api.CreateProcessW=denied
    for name in ('CreateAppContainerProfile','DeleteAppContainerProfile'):
        def prohibited(*args,_name=name):
            forbidden.append(_name);raise AssertionError('AC3_NO_PROFILE_MUTATION_AUTHORITY')
        setattr(api.userenv,name,prohibited)
def owned_init(owner,*args,**kwargs):
    real_owner_init(owner,*args,**kwargs);owners.append(owner)
class Recorder(unittest.TextTestResult):
    def startTest(self,case):executed.append(case.id());super().startTest(case)
    def stopTest(self,case):stopped.append(case.id());super().stopTest(case)
inputs=json.loads((R/'SOURCE-INPUTS.json').read_text())
names=set(inputs['selected_dependencies'])
before={name:ordinary(Q/name) for name in names};source_before={name:ordinary(F/name) for name in inputs['Source_payloads']}
thread_before=set(threading.enumerate());started=utc()
with patch.object(module._IsolationAPI,'__init__',guarded_init),patch.object(native.WindowsOwnedProcess,'__init__',owned_init),(D/'tests.txt').open('x',encoding='utf8') as out:
    result=unittest.TextTestRunner(stream=out,verbosity=2,resultclass=Recorder).run(suite)
lifetimes=[{'pid':owner.pid,'creation_time':owner.creation_time,'lifetime_closed':owner.lifetime_closed,
    'process_closed':owner._process is None,'job_closed':owner._job is None,'thread_closed':owner._thread is None} for owner in owners]
remaining=[{'name':thread.name,'native_id':thread.native_id} for thread in set(threading.enumerate())-thread_before if thread.is_alive()]
closed=all(row['lifetime_closed'] and row['process_closed'] and row['job_closed'] and row['thread_closed'] for row in lifetimes)
after={name:ordinary(Q/name) for name in names};source_after={name:ordinary(F/name) for name in inputs['Source_payloads']}
imports={name:ordinary(Path(item.__file__)) for name,item in sys.modules.items() if (name=='ceta' or name.startswith('ceta.')) and getattr(item,'__file__',None)}
assert all(Path(row['path']).is_relative_to(Q/'src') for row in imports.values())
passed=result.wasSuccessful() and not result.skipped and expected==executed==stopped and before==after and source_before==source_after and closed and not remaining and not forbidden
write_new(D/'RESULT.json',{'started_at':started,'finished_at':utc(),'expected_ids':expected,'executed_ids':executed,'stopped_ids':stopped,
    'tests_run':result.testsRun,'failures':[{'id':case.id(),'traceback':trace} for case,trace in result.failures],
    'errors':[{'id':case.id(),'traceback':trace} for case,trace in result.errors],'skipped':result.skipped,
    'deferred_original_case':{'id':deferred,'reason':'No additional profile creation or restricted launch retry is authorized; retained source body not executed.'},
    'original_AC2_methods_run':49,'original_AC2_original50':reference(F/'.agents/runtime/ac2-20261014/original-r4.json'),
    'new_AC3_methods':len(expected)-49,'candidate_before':before,'candidate_after':after,'source_before':source_before,'source_after':source_after,
    'native_process_lifetimes':lifetimes,'all_recorded_lifetimes_closed':closed,'remaining_new_threads':remaining,
    'environment_receipts':tests.NATIVE_ENVIRONMENT_RECEIPTS,'guarded_API_constructions':len(apis),'forbidden_calls':forbidden,
    'actual_profile_mutations':[],'actual_restricted_launch_retries':[],'imports':imports,'raw':reference(D/'tests.txt'),
    'qualification':'Read-only native folder environment, bounded real allocation/handle cleanup and 49 inherited original-cohort cases. One prior native restricted-launch test is explicitly deferred. The separate original three adverse methods require their own run; no full53, positive isolation or error203 repair claim.',
    'Source_application':False,'exit_status':0 if passed else 1})
print(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
    'skips':len(result.skipped),'closed':closed,'lifetimes':len(lifetimes),'new_cases':len(expected)-49,'forbidden_calls':forbidden,
    'exit_status':0 if passed else 1}),flush=True)
sys.exit(0 if passed else 1)
