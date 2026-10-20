"""Actual SQLite cumulative-byte accounting; native proof provider is controlled."""
from pathlib import Path
import json,os,sys,unittest
P=Path('T:/00-Active/Project-AI-CETA');Q=P/'.agents/et1-20261014';BASE=P/'.agents/runtime/et1-20261014';D=BASE/'independent-review';M=D/'replica'
sys.path.insert(0,str(P/'.agents/runtime/ka1-20261014'));import ka1_support as s
s.Q=Q;s.R=D;s.RUN='et1-20261014'
sys.path[:0]=[str(M/'src'),str(M/'tests/contract')]
from ceta.store.sqlite_runtime import load_sqlite
load_sqlite()
import test_owned_cpu_outcome_transactions as tests
from ceta.contracts.kernel_transactions import budget_key,logical_key
from ceta.contracts.resource_management import ObservationState
from ceta.contracts.store_transactions import StoreKey
from ceta.contracts.wire import strict_loads
facts=[]
class CumulativeBudgetProbe(tests.OutcomeTransactionsTests):
    def test_advancing_uncertainty_cannot_exceed_one_finite_request_write_budget(self):
        f=self.fixture(attempt=False);scope=f.effect.scope_id
        first=f.store.position(scope).next_sequence
        consumed=f.codec.decode(f.permit).as_dict()
        keys=(budget_key(tests.parent.grant_key_for(f.request)),StoreKey('reservation',scope,consumed['reservation_ref']))
        budget_before=f.store.snapshot(keys)
        attempt=self.begin(f);receipt=self.receipt(f);evidence=[];steps=[]
        observation=self.observation(f,state=ObservationState.UNAVAILABLE,limit=None,reason='native:unavailable')
        for index in range(4):
            obs=self.observation(f,state=ObservationState.UNAVAILABLE,limit=None,reason='native:unavailable',
                sequence=index+1,clock=tests.parent.clock(1_080_000_000+index*10_000_000))
            result=self.record(f,receipt,obs);row=result.as_dict()
            evidence_key=logical_key('projection',scope,'owned-cpu-evidence',obs.observation_commitment)
            stored=f.cell(evidence_key).value_wire;self.assertEqual(stored,obs.canonical_wire);evidence.append(stored)
            entries=f.store.replay(scope,first,128)
            journal_bytes=sum(len(item.event_wire)+len(item.payload_wire) for item in entries)
            evidence_bytes=sum(len(item) for item in evidence)
            point=f.store.position(scope)
            steps.append(dict(iteration=index+1,scope_sequence=point.next_sequence,events=len(entries),
                outcome_state=row['state'],projection_revision=row['revision'],transaction_stored_bytes=row['stored_bytes'],
                transaction_reserved_bytes=row['reserved_bytes'],cumulative_immutable_event_payload_bytes=journal_bytes,
                cumulative_immutable_native_evidence_bytes=evidence_bytes,cumulative_immutable_lower_bound=journal_bytes+evidence_bytes,
                charged_budget_and_reservation_unchanged=f.store.snapshot(keys)==budget_before,
                native_observation_commitment=obs.observation_commitment))
            self.assertEqual(row['state'],'UNCERTAIN')
            self.assertLessEqual(row['stored_bytes'],row['reserved_bytes'])
        observation=dict(test_id=self.id(),root=str(f.root),request_commitment=f.effect.input_commitment,
            permit_id=consumed['record_id'],operation_budget=f.effect.operation_budget.as_dict(),
            required_outcome_bytes=f.effect.required_outcome_bytes,attempt_stored_bytes=attempt.as_dict()['stored_bytes'],
            first_outcome_sequence=first,steps=steps,
            final_budget_reservation_unchanged=f.store.snapshot(keys)==budget_before,
            lower_bound_excludes='All mutable projection writes, SQL/WAL/pages, row indexes and pre-attempt prepare/consume/enrollment work.',
            actual_native_effects=0,positive_provider='Controlled domain fixture only')
        facts.append(observation)
        self.assertLessEqual(steps[-1]['cumulative_immutable_lower_bound'],f.effect.operation_budget.as_dict()['max_bytes_written'],
            'Advancing reconciliation appended more canonical bytes than the finite consumed request write budget without a further charge/denial')

    def test_exact_uncertain_retry_is_still_read_only_and_does_not_replay_effect(self):
        f=self.fixture();receipt=self.receipt(f)
        obs=self.observation(f,state=ObservationState.UNAVAILABLE,limit=None,reason='native:unavailable')
        first=self.record(f,receipt,obs);before=self.snapshot(f)
        self.assertEqual(self.record(f,receipt,obs),first);self.assertEqual(self.snapshot(f),before)
        facts.append(dict(test_id=self.id(),exact_retry_no_commit=True,state=first.as_dict()['state'],actual_native_effects=0))

methods=('test_advancing_uncertainty_cannot_exceed_one_finite_request_write_budget',
 'test_exact_uncertain_retry_is_still_read_only_and_does_not_replay_effect')
expected=['__main__.CumulativeBudgetProbe.'+name for name in methods];executed=[]
class Result(unittest.TextTestResult):
    def startTest(self,test):executed.append(test.id());super().startTest(test)
with (D/'cumulative-budget-r1.txt').open('x',encoding='utf-8',buffering=1) as stream:
    result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(unittest.TestSuite(CumulativeBudgetProbe(name) for name in methods))
setup=json.loads((D/'PREPARATION.json').read_text())
assert all(s.ordinary(Q/name)==row for name,row in setup['original_candidate'].items())
assert all(s.ordinary(M/name)==row for name,row in setup['replica'].items())
assert all(s.ordinary(P/name)==row for name,row in setup['Source290'].items())
s.write_new(D/'CUMULATIVE-BUDGET-PROBE.json',dict(recorded_at=s.utc(),tests_run=result.testsRun,expected_ids=expected,executed_ids=executed,
    failures=[(t.id(),tb) for t,tb in result.failures],errors=[(t.id(),tb) for t,tb in result.errors],skips=result.skipped,
    facts=facts,raw=s.reference(D/'cumulative-budget-r1.txt'),probe=s.reference(Path(__file__)),
    original_Q_Source290_and_replica_payload_native_bytes_exact=True,native_effect_invocation=False,
    exit_status=0 if result.wasSuccessful() else 1))
print(json.dumps(dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),facts=facts)),flush=True)
sys.exit(0 if result.wasSuccessful() else 1)
