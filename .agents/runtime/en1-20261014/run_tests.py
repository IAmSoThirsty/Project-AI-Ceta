from en1_support import *
from contextlib import redirect_stdout, redirect_stderr
import importlib, threading, unittest

label=sys.argv[1];assert label.replace('-','').isalnum()
assert json.loads((R/RUN/'claims.json').read_text())['implement']['executor_id']==ACTOR
inputs=json.loads((R/'SOURCE-INPUTS.json').read_text())
eligible=['src/ceta/contracts/owner_enrollment.py','tests/contract/test_owner_enrollment.py','contracts/OWNER_ENROLLMENT_V1.md']
names=sorted([*inputs['current290'],*inputs['dependencies'],*eligible]);assert len(set(names))==len(names)==295
before={name:ordinary(Q/name) for name in names}
source_before={name:ordinary(P/name) for name in inputs['current290']};assert source_before==inputs['current290']
sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
modules=[importlib.import_module(name) for name in ('test_owner_enrollment','test_temporal','test_wire','test_all_records')]
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(module) for module in modules)
def ids(group):
    for item in group:
        if isinstance(item,unittest.TestSuite):yield from ids(item)
        else:yield item.id()
expected=list(ids(suite));assert len(expected)==len(set(expected))
executed,stopped=[],[]
class Recorder(unittest.TextTestResult):
    def startTest(self,case):executed.append(case.id());super().startTest(case)
    def stopTest(self,case):stopped.append(case.id());super().stopTest(case)
started=utc()
with (R/(label+'.txt')).open('x',encoding='utf-8',buffering=1) as stream:
    with redirect_stdout(stream),redirect_stderr(stream):
        result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Recorder).run(suite)
after={name:ordinary(Q/name) for name in names};source_after={name:ordinary(P/name) for name in inputs['current290']}
passed=(result.wasSuccessful() and not result.skipped and before==after and source_before==source_after
        and expected==executed==stopped)
value={'started_at':started,'finished_at':utc(),'expected_ids':expected,'executed_ids':executed,'stopped_ids':stopped,
    'tests_run':result.testsRun,'new_cases':sum(name.startswith('test_owner_enrollment.') for name in expected),
    'retained_cases':sum(not name.startswith('test_owner_enrollment.') for name in expected),
    'failures':[{'id':case.id(),'traceback':trace} for case,trace in result.failures],
    'errors':[{'id':case.id(),'traceback':trace} for case,trace in result.errors],'skips':result.skipped,
    'candidate_before':before,'candidate_after':after,'source_before':source_before,'source_after':source_after,
    'raw':reference(R/(label+'.txt')),'driver':reference(Path(__file__)),
    'module_origins':{module.__name__:str(Path(module.__file__)) for module in modules},
    'contract_module':str(Path(sys.modules['ceta.contracts.owner_enrollment'].__file__)),
    'live_thread_names':[thread.name for thread in threading.enumerate()],'exit_status':0 if passed else 1,
    'qualification':'Controlled DATA_ONLY fixtures. No actual filesystem/Hello/profile/clock mutation, native enrollment, grant or authority acceptance.'}
write_new(R/(label+'.json'),value)
print(json.dumps({key:value[key] for key in ('tests_run','new_cases','retained_cases','failures','errors','skips','exit_status')},indent=2),flush=True)
sys.exit(value['exit_status'])
