"""Finite ET3 fresh-child adversarial cases on actual disposable SQLite."""
from review_support import *
from concurrent.futures import ThreadPoolExecutor
import threading, unittest
M=D/'replica'; E=D/'hostile-r1'; E.mkdir()
os.environ['TEMP']=os.environ['TMP']=str(E)
sys.path[:0]=[str(M/'src'),str(M/'tests/contract')]
from ceta.store.sqlite_runtime import load_sqlite
load_sqlite()
import test_owned_cpu_outcome_transactions as prior
from ceta.contracts.resource_management import ObservationState,ProcessResourceIdentity
from ceta.contracts.store_transactions import STORE_PROFILE,StoreKey
from ceta.contracts.wire import ContractError
from ceta.kernel.transactions import KernelTransactions
facts=[]
class AdversarialFreshChildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):prior.OutcomeTransactionsTests.setUpClass()
    def setUp(self):
        self.case=prior.OutcomeTransactionsTests();self.addCleanup(self.case.doCleanups)
    def pending(self):
        f=self.case.fixture();receipt=self.case.receipt(f)
        old=self.case.observation(f,state=ObservationState.UNAVAILABLE,limit=None,reason='native:unavailable')
        proof=f.owners.native_proof('OUTCOME',f.effect,f.permit,receipt,old)
        first=self.case.record(f,receipt,old,proof=proof)
        return f,receipt,old,proof,first
    def fresh(self,f,sequence=2,**changes):
        fields=dict(observer_identity=ProcessResourceIdentity(200+sequence,300+sequence,prior.parent.H),
            sequence=sequence,clock=prior.parent.clock(1_080_000_000+sequence*1_000_000))
        fields.update(changes);return self.case.observation(f,**fields)
    def test_same_image_new_lifetime_cannot_reuse_prior_child_proof(self):
        f,receipt,old,proof,first=self.pending();before=self.case.snapshot(f)
        with self.assertRaisesRegex(ContractError,'CONTROLLED_NATIVE_PROOF_DENIED'):
            self.case.record(f,receipt,self.fresh(f),proof=proof)
        self.assertEqual(self.case.snapshot(f),before);self.assertEqual(self.case.recovered(f),first)
        facts.append({'test':self.id(),'old_child_proof_reuse':'DENIED','no_writes':True})
    def test_replacing_public_owner_method_cannot_replace_captured_proof_gate(self):
        f,receipt,old,proof,first=self.pending();before=self.case.snapshot(f);called=[]
        f.owners.require_owned_cpu_outcome_current=lambda *args:called.append(True)
        with self.assertRaisesRegex(ContractError,'CONTROLLED_NATIVE_PROOF_DENIED'):
            self.case.record(f,receipt,self.fresh(f),proof=object())
        self.assertEqual(called,[]);self.assertEqual(self.case.snapshot(f),before)
        facts.append({'test':self.id(),'replacement_method_calls':called,'captured_provider_retained':True})
    def test_fresh_unavailable_children_exhaust_one_reserve_atomically(self):
        f,receipt,old,proof,first=self.pending();counts=[first.as_dict()['stored_bytes']]
        permit=f.codec.decode(f.permit).as_dict()
        liability_keys=(prior.budget_key(prior.parent.grant_key_for(f.request)),
            StoreKey('reservation',f.effect.scope_id,permit['reservation_ref']))
        initial_budget=f.store.snapshot(liability_keys)
        overflow=None
        for sequence in range(2,16):
            before=self.case.snapshot(f);retained=self.case.recovered(f)
            observation=self.fresh(f,sequence,state=ObservationState.UNAVAILABLE,limit=None,reason='native:unavailable')
            try:result=self.case.record(f,receipt,observation)
            except ContractError as error:
                self.assertEqual(error.code,'OUTCOME_RESERVED_CAPACITY_EXCEEDED')
                self.assertEqual(self.case.snapshot(f),before);self.assertEqual(self.case.recovered(f),retained)
                overflow={'sequence':sequence,'code':error.code,'retained_bytes':retained.as_dict()['stored_bytes']}
                break
            row=result.as_dict();actual=self.case.actual_writes(f)['total']
            self.assertEqual(row['stored_bytes'],actual);self.assertEqual(row['prior_stored_bytes'],counts[-1])
            self.assertGreater(actual,counts[-1]);self.assertLessEqual(actual,row['reserved_bytes']);counts.append(actual)
            retry_before=self.case.snapshot(f);self.assertEqual(self.case.record(f,receipt,observation),result)
            self.assertEqual(self.case.snapshot(f),retry_before)
        self.assertIsNotNone(overflow,'bounded15 observations must reach declared finite reserve')
        self.assertEqual(f.store.snapshot(liability_keys),initial_budget)
        facts.append({'test':self.id(),'cumulative_counts':counts,'overflow':overflow,'reserve':f.effect.required_outcome_bytes,
            'no_reset_no_retry_charge_no_refund':True})
    def test_competing_fresh_children_have_one_atomic_terminal_settlement(self):
        f,receipt,old,proof,first=self.pending()
        other=prior.parent.BarrierJournal(f.root,f.codec,(prior.parent.INSTALLATION,prior.parent.PROJECT),profile=STORE_PROFILE)
        self.addCleanup(other.close);kernel=KernelTransactions(other,f.codec,prior.parent.INSTALLATION,f.owners)
        barrier=threading.Barrier(2);f.store.barrier=other.barrier=barrier;before=self.case.snapshot(f)
        observations=(self.fresh(f,2),self.fresh(f,3));threads=[]
        def run(pair):
            k,observation=pair;threads.append(threading.get_native_id())
            try:return ('COMMITTED',self.case.record(f,receipt,observation,kernel=k))
            except ContractError as error:return ('DENIED',error.code)
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                results=list(pool.map(run,zip((f.kernel,kernel),observations)))
        finally:f.store.barrier=other.barrier=None
        self.assertEqual(sorted(row[0] for row in results),['COMMITTED','DENIED'])
        self.assertEqual(self.case.snapshot(f)[0].next_commit,before[0].next_commit+1)
        outcome=self.case.recovered(f);self.assertEqual(outcome.as_dict()['state'],'SETTLED_OBSERVED')
        self.assertEqual(outcome.receipt_wire,first.receipt_wire)
        self.assertEqual(outcome.as_dict()['stored_bytes'],self.case.actual_writes(f)['total'])
        facts.append({'test':self.id(),'native_thread_ids':threads,'results':[row[0] for row in results],
            'one_commit':True,'original_receipt_retained':True,'all_threads_joined':True})
suite=unittest.defaultTestLoader.loadTestsFromTestCase(AdversarialFreshChildTests)
expected=[case.id() for case in suite];executed=[]
class Result(unittest.TextTestResult):
    def startTest(self,test):executed.append(test.id());super().startTest(test)
threads=set(threading.enumerate());started=utc()
with (E/'tests.txt').open('x',encoding='utf8') as out:
    result=unittest.TextTestRunner(stream=out,verbosity=2,resultclass=Result).run(suite)
remaining=[{'name':t.name,'native_id':t.native_id} for t in set(threading.enumerate())-threads if t.is_alive()]
passed=result.wasSuccessful() and not result.skipped and expected==executed and not remaining
write(E/'RESULT.json',{'started_at':started,'finished_at':utc(),'expected_ids':expected,'executed_ids':executed,
    'tests_run':result.testsRun,'failures':[{'id':t.id(),'traceback':tb} for t,tb in result.failures],
    'errors':[{'id':t.id(),'traceback':tb} for t,tb in result.errors],'skips':result.skipped,'facts':facts,
    'threads_remaining':remaining,'raw_sha256':sha(E/'tests.txt'),'positive_native_provenance':'CONTROLLED_ONLY',
    'native_effects':False,'exit_status':0 if passed else 1})
print(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'exit_status':0 if passed else 1}),flush=True)
sys.exit(0 if passed else 1)
