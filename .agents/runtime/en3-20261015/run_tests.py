"""Pure enrollment/schema/temporal and unchanged import-boundary qualification."""
from en_support import *
import contextlib,importlib,threading,unittest
label=sys.argv[1]
assert label.replace('-','').isalnum()
sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
modules=[importlib.import_module(name) for name in ('test_owner_enrollment',
    'test_temporal','test_wire','test_all_records','test_source_coverage','test_owner_enrollment_guid')]
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(module) for module in modules)
def ids(item):
    if isinstance(item,unittest.TestSuite):
        for child in item:yield from ids(child)
    else:yield item.id()
expected=list(ids(suite))
assert len(expected)==len(set(expected)) and not any('_FailedTest' in name for name in expected)
names=set(json.loads((R/'STAGED-INPUTS.json').read_text())['payloads'])
names.add('tests/contract/test_owner_enrollment_guid.py')
before={name:ordinary(Q/name) for name in sorted(names)}
source=json.loads((R/'SOURCE-INPUTS.json').read_text())['Source290']
assert {name:ordinary(F/name) for name in source}==source
started,threads=utc(),set(threading.enumerate())
executed,stopped=[],[]
class Result(unittest.TextTestResult):
    def startTest(self,test):executed.append(test.id());super().startTest(test)
    def stopTest(self,test):stopped.append(test.id());super().stopTest(test)
write_new(R/(label+'-preflight.json'),{'at':started,'expected_ids':expected,'candidate_before':before,'Source290':source})
with (R/(label+'.txt')).open('x',encoding='utf-8') as stream:
    with contextlib.redirect_stdout(stream),contextlib.redirect_stderr(stream):
        result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
after={name:ordinary(Q/name) for name in before}
assert before==after and {name:ordinary(F/name) for name in source}==source
remaining=[{'name':t.name,'native_id':t.native_id} for t in set(threading.enumerate())-threads if t.is_alive()]
record={'started_at':started,'finished_at':utc(),'tests_run':result.testsRun,
    'expected_ids':expected,'executed_ids':executed,'stopped_ids':stopped,
    'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),
    'details':[{'id':case.id(),'traceback':body} for case,body in result.failures+result.errors],
    'candidate_before':before,'candidate_after':after,'Source290_native_bytes_exact':True,
    'threads_remaining':remaining,'raw':reference(R/(label+'.txt')),
    'native_process_profile_or_authority_operations':False,
    'exit_status':0 if result.wasSuccessful() and not result.skipped and expected==executed==stopped and not remaining else 1}
write_new(R/(label+'.json'),record)
print(json.dumps({k:record[k] for k in ('tests_run','failures','errors','skips','exit_status')}))
for detail in record['details']:print(detail['id']+'\n'+detail['traceback'])
sys.exit(record['exit_status'])
