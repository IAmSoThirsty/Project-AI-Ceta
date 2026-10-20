"""Run literal parent hostile methods on the unchanged fresh candidate."""
from et_support import *
import ast, contextlib, unittest
sys.path[:0] = [str(Q/'src'),str(Q/'tests/contract')]
from ceta.store.sqlite_runtime import load_sqlite
load_sqlite()
import test_owned_cpu_outcome_transactions as tests
from ceta.contracts.kernel_transactions import budget_key,logical_key
from ceta.contracts.resource_management import ObservationState
from ceta.contracts.store_transactions import StoreKey
from ceta.contracts.wire import strict_loads
label = sys.argv[1]; assert label.replace('-','').isalnum()
fixtures = R / (label+'-fixtures'); fixtures.mkdir()
class RuntimeRoot:
    def __fspath__(self): return str(Q)
    def __truediv__(self, part):
        part=str(part).replace('\\','/')
        return fixtures/part[len('.agents/fixtures/'):] if part.startswith('.agents/fixtures/') else Q/part
tests.parent.ROOT=tests.ROOT=RuntimeRoot()
origin=F/'.agents/runtime/et1-20261014/independent-review/probe_cumulative_budget.py'
raw=fs.read_bytes(origin); assert digest(raw)=='8d28ba91b34795876ea8010951791cec53434d485fd119d69fbbb149f2b79c7a'
tree=ast.parse(raw); node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='CumulativeBudgetProbe')
literal=ast.get_source_segment(raw.decode(),node); facts=[]
exec(compile(ast.Module(body=[node],type_ignores=[]),str(origin),'exec'),globals())
methods=('test_advancing_uncertainty_cannot_exceed_one_finite_request_write_budget',
    'test_exact_uncertain_retry_is_still_read_only_and_does_not_replay_effect')
before={name:ordinary(Q/name) for name in json.loads((R/'STAGED-INPUTS.json').read_text())['payloads']}
executed=[]
class Result(unittest.TextTestResult):
    def startTest(self,test): executed.append(test.id()); super().startTest(test)
with (R/(label+'.txt')).open('x',encoding='utf-8',buffering=1) as output:
    with contextlib.redirect_stdout(output),contextlib.redirect_stderr(output):
        result=unittest.TextTestRunner(stream=output,verbosity=2,resultclass=Result).run(
            unittest.TestSuite(CumulativeBudgetProbe(name) for name in methods))
assert before=={name:ordinary(Q/name) for name in before}
record={'at':utc(),'tests_run':result.testsRun,'executed_ids':executed,'failures':len(result.failures),
    'errors':len(result.errors),'skips':len(result.skipped),'facts':facts,
    'failure_details':[{'id':t.id(),'traceback':tb} for t,tb in result.failures+result.errors],
    'raw':reference(R/(label+'.txt')),'literal_parent_probe':reference(origin),
    'literal_class_ast_sha256':digest(ast.dump(node,include_attributes=False).encode()),
    'literal_class_text_sha256':digest(literal.encode()),'candidate_before_after_exact':True,
    'candidate_before':before,'Source_application':False,'actual_native_effects':False,
    'exit_status':0 if result.wasSuccessful() else 1}
write_new(R/(label+'.json'),record)
print(json.dumps({k:record[k] for k in ('tests_run','failures','errors','skips','exit_status')}))
sys.exit(record['exit_status'])
