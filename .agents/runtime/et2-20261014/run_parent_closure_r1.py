"""Literal old hostile bodies with an explicit finite-overflow closure oracle."""
from et_support import *
import ast,contextlib,unittest
sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
from ceta.store.sqlite_runtime import load_sqlite
load_sqlite()
import test_owned_cpu_outcome_transactions as tests
from ceta.contracts.kernel_transactions import budget_key,logical_key
from ceta.contracts.resource_management import ObservationState
from ceta.contracts.store_transactions import StoreKey
from ceta.contracts.wire import ContractError,strict_loads
label=sys.argv[1];assert label.replace('-','').isalnum()
fixtures=R/(label+'-fixtures');fixtures.mkdir()
class RuntimeRoot:
    def __fspath__(self):return str(Q)
    def __truediv__(self,part):
        part=str(part).replace('\\','/')
        return fixtures/part[len('.agents/fixtures/'):] if part.startswith('.agents/fixtures/') else Q/part
tests.parent.ROOT=tests.ROOT=RuntimeRoot()
origin=F/'.agents/runtime/et1-20261014/independent-review/probe_cumulative_budget.py'
raw=fs.read_bytes(origin);assert digest(raw)=='8d28ba91b34795876ea8010951791cec53434d485fd119d69fbbb149f2b79c7a'
node=next(n for n in ast.parse(raw).body if isinstance(n,ast.ClassDef) and n.name=='CumulativeBudgetProbe')
facts=[];exec(compile(ast.Module(body=[node],type_ignores=[]),str(origin),'exec'),globals())
class BoundedClosure(CumulativeBudgetProbe):
    def fixture(self,*,reserve=None,attempt=True):
        f=tests.OutcomeTransactionsTests.fixture(self,reserve=self.explicit_reserve,attempt=attempt)
        self.captured=f
        self.original_snapshot=self.snapshot(f)
        self.original_writes=self.actual_writes(f)
        permit=f.codec.decode(f.permit).as_dict()
        self.charge_keys=(budget_key(tests.parent.grant_key_for(f.request)),
            StoreKey('reservation',f.effect.scope_id,permit['reservation_ref']))
        self.original_charges=f.store.snapshot(self.charge_keys)
        return f
    def test_literal_advancing_8k_probe_is_stopped_by_atomic_capacity_denial(self):
        self.explicit_reserve=8192
        with self.assertRaisesRegex(ContractError,'OUTCOME_RESERVED_CAPACITY_EXCEEDED'):
            CumulativeBudgetProbe.test_advancing_uncertainty_cannot_exceed_one_finite_request_write_budget(self)
        f=self.captured
        # The literal body explicitly asks for attempt=False, then begins the
        # attempt before its first record. Only that authorized attempt may be
        # added; no original unsafe reconciliation is accepted.
        row=self.recovered(f).as_dict();actual=self.actual_writes(f)
        self.assertEqual(row['state'],'ATTEMPT_COMMITTED')
        self.assertEqual(actual['transactions'],1)
        self.assertEqual(actual['total'],row['stored_bytes'])
        self.assertLessEqual(actual['total'],8192)
        self.assertIsNone(row['receipt_index'])
        self.assertEqual(f.store.snapshot(self.charge_keys),self.original_charges)
        facts.append({'test_id':self.id(),'reserve':8192,'early_capacity_denial':True,'actual':actual,
            'original_unsafe_append_accepted':False,'native_effects':0})
    def test_literal_exact_retry_control_uses_declared_32k_success_fixture(self):
        self.explicit_reserve=32768
        CumulativeBudgetProbe.test_exact_uncertain_retry_is_still_read_only_and_does_not_replay_effect(self)
        self.assertEqual(self.recovered(self.captured).as_dict()['stored_bytes'],self.actual_writes(self.captured)['total'])
methods=('test_literal_advancing_8k_probe_is_stopped_by_atomic_capacity_denial',
    'test_literal_exact_retry_control_uses_declared_32k_success_fixture')
before={name:ordinary(Q/name) for name in json.loads((R/'STAGED-INPUTS.json').read_text())['payloads']}
executed=[]
class Result(unittest.TextTestResult):
    def startTest(self,test):executed.append(test.id());super().startTest(test)
with (R/(label+'.txt')).open('x',encoding='utf-8',buffering=1) as output:
    with contextlib.redirect_stdout(output),contextlib.redirect_stderr(output):
        result=unittest.TextTestRunner(stream=output,verbosity=2,resultclass=Result).run(
            unittest.TestSuite(BoundedClosure(name) for name in methods))
assert before=={name:ordinary(Q/name) for name in before}
record={'at':utc(),'tests_run':result.testsRun,'executed_ids':executed,'failures':len(result.failures),
    'errors':len(result.errors),'skips':len(result.skipped),'facts':facts,
    'failure_details':[{'id':t.id(),'traceback':tb} for t,tb in result.failures+result.errors],
    'raw':reference(R/(label+'.txt')),'literal_parent_probe':reference(origin),
    'literal_class_ast_sha256':digest(ast.dump(node,include_attributes=False).encode()),
    'baseline':reference(R/'baseline-r1.json'),
    'adaptation':'Literal parent class/method ASTs unchanged. An explicit8KiB fixture now raises capacity before first outcome; wrapper requires one attempt, zero outcome writes and unchanged charge. Exact retry body uses explicitly declared32KiB success fixture.',
    'candidate_before_after_exact':True,'candidate_before':before,'native_effects':0,'controlled_providers':True,
    'exit_status':0 if result.wasSuccessful() and not result.skipped else 1}
write_new(R/(label+'.json'),record)
print(json.dumps({k:record[k] for k in ('tests_run','failures','errors','skips','exit_status')}))
sys.exit(record['exit_status'])
