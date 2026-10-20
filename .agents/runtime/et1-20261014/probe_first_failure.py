"""Bounded one-case reproduction of the first writer failure; no native effect."""
from et_support import *
import traceback
sys.path[:0] = [str(Q / 'src'), str(Q / 'tests/contract')]
from ceta.store.sqlite_runtime import load_sqlite
load_sqlite()
import test_owned_cpu_outcome_transactions as tests
fixture = R / 'probe-first-failure'; fixture.mkdir()
tests.parent.ROOT = fixture
case = tests.OutcomeTransactionsTests()
case.schema = json.loads((Q / 'contracts/schemas/records.schema.json').read_text())
try:
    f = case.fixture(); result = case.record(f, case.receipt(f), case.observation(f))
    print(result.as_dict()['state'])
except BaseException:
    raw = traceback.format_exc()
    with (R / 'probe-first-failure.txt').open('x', encoding='utf-8') as out: out.write(raw)
    print(raw)
finally: case.doCleanups()
