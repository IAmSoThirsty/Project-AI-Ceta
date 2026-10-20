"""Run the exact original bounded denial case only after proved own cleanup."""
from pathlib import Path
import ast,contextlib,functools,hashlib,importlib.util,json,os,sys,threading,types,unittest,uuid
from unittest.mock import patch
F=Path('T:/00-Active/Project-AI-CETA');R=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
tool=R/'profile_qualification.py'
assert sha(tool)=='8d3ce66b6ac17d2774f4c11a8852b23b45e41218df887f6b18c99ac0add05414'
spec=importlib.util.spec_from_file_location('no_profile_approved_tool',tool)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
approval=R/'ACTUAL-OPERATOR-APPROVAL.json'
assert sha(approval)=='3401d05d82ee4bcfe6bf62c21f2fb84324261bd78cbaf2761848d322e22ed4b5'
actual=m.read(approval)
assert actual['human_reply']=='Approve this exact AC3 attempt, own-profile cleanup, and bounded post-cleanup denial regression'
attempt=R/'profile-qualification-a82d795283474f5daa218f8c158d5047'
result=m.read(attempt/'RESULT.json');post=m.read(attempt/'POST-DELETE-OBSERVATION.json')
assert result['all_captured_resources_retired'] and result['created_this_run'] and result['exact_returned_SID_verified']
assert result['profile_cleanup_status']=='DELETE_SUCCEEDED_AND_FOLDER_ABSENCE_OBSERVED'
assert post['native_delete_HRESULT']==0 and post['folder_observation']['path'] is None
assert not list(R.glob('approved-no-profile-*')), 'EXACT_APPROVED_REGRESSION_NOT_RETRIED'
before_profile=m.inspect();assert before_profile['prior_folder']['HRESULT'] in (-2147024894,-2147024893)
assert before_profile['prior_folder']['path'] is None
source=m.source_cut();candidate=m.candidate_cut()
D=R/('approved-no-profile-'+uuid.uuid4().hex);D.mkdir()
isolated_harness=D/'isolation-harness';native=isolated_harness/'.agents/runtime/ac1-20261014'
native.mkdir(parents=True);(native/'build-r2').mkdir()
source_helper=F/'.agents/runtime/ac1-20261014/native_fixture_support.py'
assert sha(source_helper)=='a7247426deee70890107b9d826c7cda9209015edd5f1192f93ee3bd1e5a4314f'
image=F/'.agents/runtime/ac1-20261014/build-r2/isolated_worker.exe'
assert sha(image)==m.IMAGE
for origin,target in ((source_helper,native/'native_fixture_support.py'),(image,native/'build-r2/isolated_worker.exe')):
    m.write_payload(target,origin.read_bytes(),sha(origin))
sys.path.insert(0,str(F/'.agents/runtime/ac3-20261014'));import ac3_support as s
shim=types.ModuleType('ac_support');shim.__dict__.update({k:v for k,v in vars(s).items() if not k.startswith('_')})
shim.Q=m.Q;shim.R=shim.D=native;sys.modules['ac_support']=shim
os.environ.update(CETA_AC1_RUNTIME_ROOT=str(native),CETA_AC3_TEST_ROOT=str(D),CETA_AC3_IMAGE=str(image))
sys.path[:0]=[str(m.Q/'src'),str(m.Q/'tests/contract')]
import test_isolated_worker as tests
tests.ROOT=isolated_harness
case_name='test_actual_nonpersistent_launch_denial_and_medium_control_retirement'
expected=['test_isolated_worker.NativeIsolatedWorkerTests.'+case_name]
tree=ast.parse((m.Q/'tests/contract/test_isolated_worker.py').read_text())
method=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==case_name)
executed=[];stopped=[];apis=[];owners=[];profile_mutations=[]
old_api=m.module._IsolationAPI.__init__;old_owner=m.WindowsOwnedProcess.__init__
class GuardProfileWrites:
    def __init__(self,library):self.library=library
    def __getattr__(self,name):
        if name in ('CreateAppContainerProfile','DeleteAppContainerProfile'):
            def refuse(*args):profile_mutations.append(name);raise AssertionError('PROFILE_MUTATION_FORBIDDEN_IN_DENIAL_REGRESSION')
            return refuse
        return getattr(self.library,name)
@functools.wraps(old_api)
def api_init(api,*args,**kwargs):
    apis.append(api);old_api(api,*args,**kwargs);api.userenv=GuardProfileWrites(api.userenv)
@functools.wraps(old_owner)
def owner_init(owner,*args,**kwargs):owners.append(owner);old_owner(owner,*args,**kwargs)
class Recorded(unittest.TextTestResult):
    def startTest(self,test):executed.append(test.id());super().startTest(test)
    def stopTest(self,test):stopped.append(test.id());super().stopTest(test)
threads_before=set(threading.enumerate());started=m.now()
m.save(D/'PREFLIGHT.json',{'at':started,'human_approval_sha256':sha(approval),'completed_attempt':str(attempt),
    'fresh_reserved_profile_absence':before_profile,'expected_ids':expected,
    'original_test_method_AST_sha256':hashlib.sha256(ast.dump(method,include_attributes=False).encode()).hexdigest(),
    'actual_profile_Create_Delete_permitted':False,'Source_application':False})
with patch.object(m.module._IsolationAPI,'__init__',api_init),patch.object(m.WindowsOwnedProcess,'__init__',owner_init):
    with (D/'raw.txt').open('x',encoding='utf-8',buffering=1) as raw:
        with contextlib.redirect_stdout(raw),contextlib.redirect_stderr(raw):
            outcome=unittest.TextTestRunner(stream=raw,verbosity=2,resultclass=Recorded).run(
                unittest.TestSuite([tests.NativeIsolatedWorkerTests(case_name)]))
source_after=m.source_cut();candidate_after=m.candidate_cut();after_profile=m.inspect()
lifetimes=[{'pid':o.pid,'creation_time':o.creation_time,'lifetime_closed':o.lifetime_closed,
    'process_closed':o._process is None,'job_closed':o._job is None,'thread_closed':o._thread is None} for o in owners]
pending=[list(api.pending_native_resources()) for api in apis]
remaining=[{'name':t.name,'native_id':t.native_id} for t in set(threading.enumerate())-threads_before if t.is_alive()]
closed=all(row['lifetime_closed'] and row['process_closed'] and row['job_closed'] and row['thread_closed'] for row in lifetimes)
passed=outcome.wasSuccessful() and not outcome.skipped and expected==executed==stopped and closed and not any(pending) and not remaining and not profile_mutations
passed=passed and source==source_after and candidate==candidate_after and after_profile['prior_folder']['path'] is None and after_profile['prior_folder']['HRESULT'] in (-2147024894,-2147024893)
report={'started_at':started,'finished_at':m.now(),'tests_run':outcome.testsRun,'expected_ids':expected,
    'executed_ids':executed,'stopped_ids':stopped,'failures':len(outcome.failures),'errors':len(outcome.errors),'skips':len(outcome.skipped),
    'failure_details':[{'test':t.id(),'traceback':body} for t,body in outcome.failures+outcome.errors],
    'native_lifetimes':lifetimes,'all_recorded_lifetimes_closed':closed,'pending_native_resources':pending,
    'remaining_new_threads':remaining,'profile_Create_Delete_calls':profile_mutations,
    'profile_absence_before':before_profile,'profile_absence_after':after_profile,
    'Source_before':source,'Source_after':source_after,'candidate_before':candidate,'candidate_after':candidate_after,
    'source_imports':{name:str(Path(mod.__file__)) for name,mod in sys.modules.items() if name.startswith('ceta.') and getattr(mod,'__file__',None)},
    'raw_sha256':sha(D/'raw.txt'),'Source_application':False,'positive_isolation_qualified':False,
    'exit_status':0 if passed else 1}
assert all(Path(p).is_relative_to(m.Q/'src') for p in report['source_imports'].values())
m.save(D/'RESULT.json',report)
print(json.dumps({'receipt':str(D/'RESULT.json'),'tests':outcome.testsRun,'failures':len(outcome.failures),
    'errors':len(outcome.errors),'lifetimes':lifetimes,'profile_mutations':profile_mutations,'exit_status':report['exit_status']}),flush=True)
for failure in report['failure_details']:print(failure['traceback'])
sys.exit(report['exit_status'])
