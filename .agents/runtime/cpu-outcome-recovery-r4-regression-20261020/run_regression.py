"""Run existing controlled owners/admission/outcome checks, no native execution."""
from pathlib import Path
from datetime import datetime, timezone
import gc
import hashlib
import json
import sys
import unittest

F = Path('T:/00-Active/Project-AI-CETA')
Q = F / '.agents/cpu-outcome-recovery-r4-20261020'
R = Path(__file__).resolve().parent
D = R / sys.argv[1]
assert D.parent == R and D.name.startswith('regression-')
D.mkdir(exist_ok=False)
sys.path[:0] = [str(Q/'src'), str(Q/'tests/contract')]
blocked = []
def audit(event, args):
    if event in ('subprocess.Popen', 'os.system', 'os.startfile') or (event == 'ctypes.dlsym' and
            args[1] in ('CreateProcessW', 'CreateProcessAsUserW', 'CreateAppContainerProfile',
                'DeleteAppContainerProfile', 'SetInformationJobObject')):
        blocked.append(dict(event=event))
        raise RuntimeError('CPU_CAPACITY_NATIVE_EFFECT_FORBIDDEN')
sys.addaudithook(audit)
from ceta.store.journal import SqliteJournal
stores = []
original = SqliteJournal.__init__
def construct(store, *args, **kwargs):
    original(store, *args, **kwargs)
    stores.append((store, store._connection))
SqliteJournal.__init__ = construct
import test_cpu_capacity_connection as connection
import test_native_owner_execution as execution
import test_native_owner_preparation as preparation
import test_owned_cpu_outcome_transactions as outcomes
import test_cpu_execution_admission as admission
import test_owner_authority_transactions as authority
import test_cpu_recovery_registration as registration
preparation.FIXTURES = D/'fixtures/preparation'
authority.ROOT = D/'fixtures/authority'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
def inputs():
    return {path.relative_to(Q).as_posix(): sha(path)
        for root in (Q/'src', Q/'tests', Q/'contracts') for path in root.rglob('*') if path.is_file()}
before = inputs()
manifest = json.loads((F/'.agents/runtime/cpu-outcome-recovery-repair-20261020/MANIFEST.json').read_bytes())
assert all(manifest['payload_hashes'][name] == pin for name,pin in before.items())
excluded = []
suite = unittest.TestSuite()
for cls in (execution.NativeOwnerExecutionTests, preparation.NativeOwnerPreparationTests,
            outcomes.OutcomeTransactionsTests, admission.CpuExecutionAdmissionTests, connection.CapacityConnectionTests):
    for test in unittest.defaultTestLoader.loadTestsFromTestCase(cls):
        if test._testMethodName == 'test_before_and_after_commit_process_crashes_reopen_without_dispatch':
            excluded.append(dict(id=test.id(), reason='Native/process cohort held by Root during destination full'))
        else: suite.addTest(test)
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(registration.RecoveryRegistrationTests))
expected = [test.id() for test in suite]
prior = json.loads((F/'.agents/runtime/cpu-outcome-recovery-20261017/regression-r1/RESULT.json').read_bytes())
cases = json.loads((R/'CASESET.json').read_bytes())
assert len(expected) == 177 and expected == cases['expected_ids']
assert expected[:169] == prior['expected_ids'] and expected[169:] == cases['registration8_ids']
assert excluded == prior['excluded_ids']
executed, stopped = [], []
class Result(unittest.TextTestResult):
    def startTest(self, test):
        gc.collect()
        executed.append(test.id()); super().startTest(test)
        with (R/'EVENTS.jsonl').open('a', encoding='utf8') as events:
            events.write(json.dumps(dict(at=datetime.now(timezone.utc).isoformat(), event='START', id=test.id()))+'\n')
    def stopTest(self, test):
        stopped.append(test.id()); super().stopTest(test)
        with (R/'EVENTS.jsonl').open('a', encoding='utf8') as events:
            events.write(json.dumps(dict(at=datetime.now(timezone.utc).isoformat(), event='STOP', id=test.id()))+'\n')
with (D/'RAW.txt').open('x', encoding='utf8') as stream:
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Result).run(suite)
after = inputs()
closure = []
for store, connection in stores:
    refusal = None
    try: connection.execute('SELECT 1')
    except store._sqlite.ProgrammingError: refusal = 'closed connection refusal'
    except BaseException as error: refusal = type(error).__name__
    closure.append(dict(path=str(store.path), closed=store._closed, refusal=refusal,
        retained_capacity=store._capacity_active is not None))
passed = (result.wasSuccessful() and not result.skipped and not blocked and before == after
    and expected == executed == stopped and len(expected) == len(set(expected))
    and all(row['closed'] and row['refusal'] == 'closed connection refusal' and not row['retained_capacity'] for row in closure))
record = dict(frozen_manifest=str(F/'.agents/runtime/cpu-outcome-recovery-repair-20261020/MANIFEST.json'), frozen_manifest_sha256=sha(F/'.agents/runtime/cpu-outcome-recovery-repair-20261020/MANIFEST.json'), at=datetime.now(timezone.utc).isoformat(), actor='/root/recovery_regression20',
    command=list(sys.orig_argv), source_root=str(Q), before=before, after=after,
    expected_ids=expected, executed_ids=executed, stopped_ids=stopped, excluded_ids=excluded,
    tests_run=result.testsRun, failures=[dict(id=test.id(), traceback=trace) for test,trace in result.failures],
    errors=[dict(id=test.id(), traceback=trace) for test,trace in result.errors], skips=len(result.skipped),
    sqlite_lifetimes=closure, prohibited_operations=blocked,
    raw_sha256=sha(D/'RAW.txt'), exit_status=0 if passed else 1,
    physical_capacity_evidence=False, actual_canonical_SQLite=True, native_CPU_Set_operations=0,
    provenance='CONTROLLED approved fixtures, not production provenance', source_publication=False)
with (D/'RESULT.json').open('x', encoding='utf8') as stream:
    json.dump(record, stream, indent=2); stream.write('\n')
print(json.dumps(dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
    skips=len(result.skipped), exit_status=record['exit_status'], result=str(D/'RESULT.json'), sha256=sha(D/'RESULT.json'))))
sys.exit(record['exit_status'])
