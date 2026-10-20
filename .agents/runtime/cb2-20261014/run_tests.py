"""Actual Windows code pin and retained-lease cases; evidence stays on T:."""
from pathlib import Path
import json,os,sys,threading,unittest
R=Path(__file__).resolve().parent;F=R.parents[2];Q=F/'.agents/cb2-20261014'
sys.path.insert(0,str(F/'.agents/runtime/en1-20261014'));import en1_support as s
s.Q=Q;s.R=R;s.RUN='cb2-20261014';s.ACTOR='/root'
label=sys.argv[1];assert label.replace('-','').isalnum();D=R/label;D.mkdir(exist_ok=False)
inputs=json.loads((R/'SOURCE-INPUTS.json').read_text());source={name:s.ordinary(F/name) for name in inputs['Source290']}
assert source==inputs['Source290']
names=sorted([str(path.relative_to(Q)) for top in ('src','tests','contracts') for path in (Q/top).rglob('*') if path.is_file()])
before={name:s.ordinary(Q/name) for name in names}
sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
import test_native_code_binding as tests
tests.ROOT=D
suite=unittest.defaultTestLoader.loadTestsFromModule(tests)
def ids(item):
    if isinstance(item,unittest.TestSuite):
        for child in item:yield from ids(child)
    else:yield item.id()
expected=list(ids(suite));assert len(expected)==len(set(expected))==18
executed,stopped=[],[]
class Recorder(unittest.TextTestResult):
    def startTest(self,test):executed.append(test.id());super().startTest(test)
    def stopTest(self,test):stopped.append(test.id());super().stopTest(test)
threads_before=set(threading.enumerate())
with (D/'tests.txt').open('x',encoding='utf-8',buffering=1) as out:
    result=unittest.TextTestRunner(stream=out,verbosity=2,resultclass=Recorder).run(suite)
remaining=[thread.name for thread in set(threading.enumerate())-threads_before if thread.is_alive()]
after={name:s.ordinary(Q/name) for name in names};source_after={name:s.ordinary(F/name) for name in source}
assert before==after and source==source_after
imports={name:str(Path(module.__file__)) for name,module in sys.modules.items() if name.startswith('ceta') and getattr(module,'__file__',None)}
assert all(Path(path).is_relative_to(Q/'src') for path in imports.values())
passed=result.wasSuccessful() and not result.skipped and expected==executed==stopped and not remaining
proof={'at':s.utc(),'expected_ids':expected,'executed_ids':executed,'stopped_ids':stopped,'tests_run':result.testsRun,
 'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),
 'details':[{'id':test.id(),'traceback':raw} for test,raw in result.failures+result.errors],
 'candidate_before':before,'candidate_after':after,'Source_before':source,'Source_after':source_after,
 'native_receipts':tests.NATIVE_RECEIPTS,'imports':imports,'remaining_threads':remaining,
 'exit_status':0 if passed else 1,'Source_application':False,'authority_accepted':False}
s.write_new(D/'RESULT.json',proof)
print(json.dumps({name:proof[name] for name in ('tests_run','failures','errors','skips','exit_status','remaining_threads')}),flush=True)
for row in proof['details']:print(row['id']+'\n'+row['traceback'])
sys.exit(proof['exit_status'])
