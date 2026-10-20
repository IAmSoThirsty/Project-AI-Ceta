"""Replay the entire frozen native hostile class AST, unchanged."""
from ac_support import *
import ast,contextlib,ctypes as C,threading,unittest
label=sys.argv[1];assert label.replace('-','').isalnum()
sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
from ceta.supervisor import isolated_worker as module
assert Path(module.__file__).is_relative_to(Q/'src')
origin=F/'.agents/runtime/ac4-20261015/independent-review/probe_combined_custody.py'
raw=fs.read_bytes(origin);assert digest(raw)=='c1bf61753112cbcc381d0a4c57aed13f226de2a4997931388c065edf3c63eb09'
node=next(n for n in ast.parse(raw).body if isinstance(n,ast.ClassDef) and n.name=='CombinedCustody')
observations=[];forbidden=[]
exec(compile(ast.Module(body=[node],type_ignores=[]),str(origin),'exec'),globals())
staged=json.loads((R/'STAGED-INPUTS.json').read_text());inputs=json.loads((R/'SOURCE-INPUTS.json').read_text())
before={name:ordinary(Q/name) for name in staged['payloads']}
executed=[];started=utc();old_threads=set(threading.enumerate())
class Result(unittest.TextTestResult):
    def startTest(self,test):executed.append(test.id());super().startTest(test)
with (R/(label+'.txt')).open('x',encoding='utf-8',buffering=1) as output:
    with contextlib.redirect_stdout(output),contextlib.redirect_stderr(output):
        result=unittest.TextTestRunner(stream=output,verbosity=2,resultclass=Result).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(CombinedCustody))
after={name:ordinary(Q/name) for name in before};assert before==after
assert {name:ordinary(F/name) for name in inputs['Source290']}==inputs['Source290']
remaining=[dict(name=t.name,native_id=t.native_id) for t in set(threading.enumerate())-old_threads if t.is_alive()]
closed=all(row['all_owned_native_resources_retired'] for row in observations)
record={'started_at':started,'finished_at':utc(),'tests_run':result.testsRun,'executed_ids':executed,
    'failures':[{'id':t.id(),'traceback':tb} for t,tb in result.failures],
    'errors':[{'id':t.id(),'traceback':tb} for t,tb in result.errors],'skips':result.skipped,
    'observations':observations,'all_owned_native_resources_retired':closed,'new_threads':remaining,
    'literal_origin':reference(origin),'literal_class_AST_sha256':digest(ast.dump(node,include_attributes=False).encode()),
    'literal_method_ASTs_unchanged':True,'candidate_before':before,'candidate_after':after,
    'Source290_exact':True,'forbidden_calls':forbidden,'raw':reference(R/(label+'.txt')),
    'exit_status':0 if result.wasSuccessful() and closed and not remaining and not forbidden else 1}
write_new(R/(label+'.json'),record)
print(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
    'owned_native_retired':closed,'exit_status':record['exit_status']}))
sys.exit(record['exit_status'])
