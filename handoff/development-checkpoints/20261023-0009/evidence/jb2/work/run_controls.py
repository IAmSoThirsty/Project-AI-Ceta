"""Pure candidate controls: exact module routing and forbidden native effects."""
from pathlib import Path
import argparse,ctypes,hashlib,importlib,importlib.abc,importlib.util,json,os,socket,subprocess,sys,time,unittest
from unittest.mock import patch

F=Path('T:/00-Active/Project-AI-CETA');W=Path(__file__).resolve().parent
C=W/'candidate';sys.dont_write_bytecode=True
MODULES={name:C/'src'/Path(*name.split('.')).with_suffix('.py') for name in (
    'ceta.identity.windows_pipe','ceta.composition.real_effect_service',
    'ceta.identity.native_approval','ceta.effects.native_observer','ceta.identity.owner_session')}
class CandidateFinder(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname in MODULES:return importlib.util.spec_from_file_location(fullname,MODULES[fullname])
sys.meta_path.insert(0,CandidateFinder())
sys.path[:0]=[str(C/'tests/contract'),str(F/'tests/contract'),str(F/'src'),str(W)]
parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
    with path.open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2);stream.write('\n')
barrier_calls=[]
def forbid(*a,**kw):
    barrier_calls.append(dict(args=repr(a),kwargs=repr(kw)))
    raise AssertionError('JB2 pure controls forbid actual native/process/socket execution')
def audit(event,args):
    if event in ('subprocess.Popen','os.system','os.startfile','socket.__new__','ctypes.dlopen'):
        raise AssertionError('Forbidden actual audit event: '+event)
    if event=='open':
        path,mode,flags=args
        writes=(isinstance(mode,str) and any(ch in mode for ch in 'wax+')) or (
            isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        if writes and not isinstance(path,int):
            actual=Path(path).resolve()
            if not actual.is_relative_to(W):raise AssertionError('Out-of-scope write: '+str(actual))
sys.addaudithook(audit)
barriers=[patch(name,side_effect=forbid) for name in (
    'ctypes.WinDLL','ctypes.CDLL','subprocess.Popen','subprocess.run','socket.socket')]
for barrier in barriers:barrier.start()
class Result(unittest.TextTestResult):
    def __init__(self,*a,**kw):super().__init__(*a,**kw);self.started=[];self.stopped=[]
    def startTest(self,test):self.started.append(test.id());super().startTest(test)
    def stopTest(self,test):self.stopped.append(test.id());super().stopTest(test)
def flatten(suite):
    for item in suite:
        if isinstance(item,unittest.TestSuite):yield from flatten(item)
        else:yield item
suite=unittest.TestSuite()
for module,kind in (
    ('test_real_effect_entrypoint','ManualEntrypointPureTests'),
    ('test_native_owner_approval','NativeApprovalDataTests'),
    ('test_native_owner_approval','NativeEnrollmentDataTests'),
    ('test_native_observer_origin','ControlledObserverOriginTests')):
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(getattr(importlib.import_module(module),kind)))
for name in ('test_adapter_keeps_primary_dispatch_error_when_observation_and_writer_fail',
    'test_adapter_records_uncertainty_and_reraises_exact_observer_error',
    'test_reconciliation_never_redispatches','test_hostile_primary_hooks_do_not_replace_primary_or_custody'):
    suite.addTest(getattr(importlib.import_module('test_native_cpu_outcome_provenance'),'CpuOutcomeProvenanceTests')(name))
if (W/'test_joint_budget_controls.py').exists():
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module('test_joint_budget_controls')))
selected=[item.id() for item in flatten(suite)]
assert len(selected)==len(set(selected))
origins={name:dict(path=str(Path(importlib.import_module(name).__file__).resolve()),sha256=sha(MODULES[name])) for name in MODULES}
assert all(value['path']==str(MODULES[name].resolve()) for name,value in origins.items())
started=time.perf_counter_ns()
with (W/(args.label+'.unittest.log')).open('x',encoding='utf8') as stream:
    result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
elapsed=time.perf_counter_ns()-started
dependencies={}
for name,module in tuple(sys.modules.items()):
    file=getattr(module,'__file__',None)
    if file:
        file=Path(file).resolve()
        if file.is_relative_to(F) and not file.is_relative_to(W):
            dependencies[file.relative_to(F).as_posix()]=sha(file)
report=dict(schema_version=1,run_id='ceta-jb23-r2',label=args.label,
    selected=selected,started=result.started,stopped=result.stopped,tests_run=result.testsRun,
    failures=[dict(test=t.id(),trace=trace) for t,trace in result.failures],
    errors=[dict(test=t.id(),trace=trace) for t,trace in result.errors],
    skips=[dict(test=t.id(),reason=reason) for t,reason in result.skipped],
    expected_failures=[t.id() for t,_ in result.expectedFailures],unexpected_successes=[t.id() for t in result.unexpectedSuccesses],
    elapsed_ns=elapsed,candidate_origins=origins,unchanged_dependencies=dependencies,
    forbidden_call_attempts=barrier_calls,pure_controlled_only=True,native_effects=False,
    full_product_acceptance=False,successful=result.wasSuccessful())
save(W/(args.label+'.json'),report)
print(json.dumps({key:report[key] for key in ('label','tests_run','elapsed_ns','successful','candidate_origins')}))
sys.exit(0 if result.wasSuccessful() and not result.skipped and selected==result.started==result.stopped else 1)
