"""Finite unchanged native IPC subset with streamed exact process custody."""
from review_support import *
import threading, unittest
from unittest.mock import patch
sys.path[:0] = [str(Q / 'src'), str(Q / 'tests/contract')]
from ceta.store.sqlite_runtime import load_sqlite
load_sqlite()
import test_kernel_authority as tests
from ceta.supervisor.windows_jobs import WindowsOwnedProcess
from ceta.store.journal import SqliteJournal
D = R / 'native-custody-r1'; D.mkdir()
before = {name: ordinary(Q / name) for name in json.loads((R / 'STAGED-INPUTS.json').read_text())['payloads']}
owners, stores, executed, stopped = [], [], [], []
original_owner, original_store = WindowsOwnedProcess.__init__, SqliteJournal.__init__
def owner_init(owner, *args, **kwargs):
    try: original_owner(owner, *args, **kwargs)
    finally:
        if hasattr(owner, '_process'): owners.append(owner)
def store_init(store, *args, **kwargs):
    try: original_store(store, *args, **kwargs)
    finally:
        if hasattr(store, '_closed'): stores.append(store)
class Result(unittest.TextTestResult):
    def startTest(self, case): executed.append(case.id()); super().startTest(case)
    def stopTest(self, case):
        stopped.append(case.id())
        with (D / 'lifetimes.jsonl').open('a', encoding='utf8') as stream:
            for owner in owners:
                stream.write(json.dumps({'at': utc(), 'test': case.id(), 'pid': owner.pid,
                    'creation_time': owner.creation_time, 'lifetime_closed': owner.lifetime_closed,
                    'process_closed': owner._process is None, 'job_closed': owner._job is None,
                    'thread_closed': owner._thread is None}) + '\n')
            stream.flush(); os.fsync(stream.fileno())
        super().stopTest(case)
threads = set(threading.enumerate()); started = utc()
suite = unittest.defaultTestLoader.loadTestsFromTestCase(tests.NativeAuthorityResolutionTests)
expected = [case.id() for case in suite]; assert len(expected) == 3
with patch.object(WindowsOwnedProcess, '__init__', owner_init), patch.object(SqliteJournal, '__init__', store_init), (D / 'tests.txt').open('x', encoding='utf8') as stream:
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Result).run(suite)
lifetimes = [{'pid': owner.pid, 'creation_time': owner.creation_time, 'lifetime_closed': owner.lifetime_closed,
    'process_closed': owner._process is None, 'job_closed': owner._job is None, 'thread_closed': owner._thread is None} for owner in owners]
remaining = [{'name': item.name, 'native_id': item.native_id} for item in set(threading.enumerate()) - threads if item.is_alive()]
assert before == {name: ordinary(Q / name) for name in before}
closed = len(lifetimes) == 6 and all(all(row[key] for key in ('lifetime_closed', 'process_closed', 'job_closed', 'thread_closed')) for row in lifetimes) and all(store._closed for store in stores)
passed = result.wasSuccessful() and not result.skipped and expected == executed == stopped and closed and not remaining
write_new(D / 'RESULT.json', {'started_at': started, 'finished_at': utc(), 'expected_ids': expected,
    'executed_ids': executed, 'stopped_ids': stopped, 'tests_run': result.testsRun,
    'failures': [(case.id(), trace) for case, trace in result.failures],
    'errors': [(case.id(), trace) for case, trace in result.errors], 'skips': result.skipped,
    'native_lifetimes': lifetimes, 'stores': [{'path': str(store.path), 'closed': store._closed} for store in stores],
    'all_recorded_custody_closed': closed, 'new_threads': remaining,
    'full394_prior_PID_capture': 'Not instrumented; this separate finite subset retains exact identities without backfilling that historical run.',
    'raw': reference(D / 'tests.txt'), 'streamed_lifetimes': reference(D / 'lifetimes.jsonl'),
    'profile_operations': [], 'CPU_policy_effects': [], 'exit_status': 0 if passed else 1})
print(json.dumps({'tests': result.testsRun, 'lifetimes': len(lifetimes), 'closed': closed,
    'failures': len(result.failures), 'errors': len(result.errors), 'exit_status': 0 if passed else 1}), flush=True)
sys.exit(0 if passed else 1)
