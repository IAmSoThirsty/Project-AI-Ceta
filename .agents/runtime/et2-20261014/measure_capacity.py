"""Measure exact logical cumulative bytes on the finite historical fixture."""
from et_support import *
sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
from ceta.store.sqlite_runtime import load_sqlite
load_sqlite()
import test_owned_cpu_outcome_transactions as tests
from ceta.contracts.wire import ContractError
fixtures=R/'measured-capacity-fixtures'; fixtures.mkdir()
tests.parent.ROOT=fixtures
case=tests.OutcomeTransactionsTests();case.setUpClass()
rows=[]
try:
    for reserve in (8192,):
        f=case.fixture(reserve=reserve);before=case.snapshot(f)
        try:case.record(f,case.receipt(f),case.observation(f))
        except ContractError as error:
            trace=error.__traceback__;frame=None
            while trace is not None:
                if trace.tb_frame.f_code.co_name=='_commit':frame=trace.tb_frame
                trace=trace.tb_next
            assert frame is not None and error.code=='OUTCOME_RESERVED_CAPACITY_EXCEEDED'
            row=frame.f_locals['row'];entries=frame.f_locals['entries']
            rows.append({'reserve':reserve,'attempt_bytes':row['prior_stored_bytes'],
                'required_cumulative_bytes':frame.f_locals['size'],
                'attempt_plus_complete_outcome_cannot_fit':frame.f_locals['size']>reserve,
                'current_batch_event_payload_bytes':sum(len(e.event_wire)+len(e.payload_wire) for e in entries),
                'atomic_no_change':case.snapshot(f)==before,'error':error.code})
        else:raise AssertionError('Historical8KiB unexpectedly fits')
finally:case.doCleanups()
write_new(R/'measured-capacity-r1.json',{'at':utc(),'rows':rows,'production_constants_changed':False,
    'candidate_source':ordinary(Q/'src/ceta/kernel/effect_transactions.py'),
    'controlled_provider_only':True,'native_effect_invocations':0})
print(json.dumps(rows))
