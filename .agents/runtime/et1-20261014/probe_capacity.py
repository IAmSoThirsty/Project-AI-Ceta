from et_support import *
import traceback, uuid
sys.path[:0] = [str(Q / 'src'), str(Q / 'tests/contract')]
from ceta.store.sqlite_runtime import load_sqlite
load_sqlite()
import test_owned_cpu_outcome_transactions as tests
fixture = R / ('capacity-probe-' + uuid.uuid4().hex[:8]); fixture.mkdir()
tests.parent.ROOT = fixture
case = tests.OutcomeTransactionsTests(); case.schema = json.loads((Q / 'contracts/schemas/records.schema.json').read_text())
try:
    f = case.fixture(); case.record(f, case.receipt(f), case.observation(f))
except BaseException as error:
    item = error.__traceback__; facts = []
    while item:
        if item.tb_frame.f_code.co_name == '_commit':
            local = item.tb_frame.f_locals
            facts.append({'actual_serialized_bytes': local.get('size'), 'reserved_bytes': local.get('row', {}).get('reserved_bytes'),
                'entry_bytes': [len(e.event_wire) + len(e.payload_wire) for e in local.get('entries', ())],
                'projection_bytes': len(local.get('encoded', b'')), 'task_bytes': len(local.get('task_wire', b'')),
                'native_evidence_bytes': len(local['evidence'][1]) if local.get('evidence') else 0})
        item = item.tb_next
    write_new(fixture / 'failure.json', {'recorded_at': utc(), 'exception': str(error), 'facts': facts,
        'source': ordinary(Q / 'src/ceta/kernel/effect_transactions.py')})
    print(json.dumps(facts))
finally: case.doCleanups()
