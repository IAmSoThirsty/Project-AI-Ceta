"""Independent controlled join: real canonical SQL, no native worker or effect."""
from pathlib import Path
from datetime import datetime, timezone
import gc
import hashlib
import json
import os
import sys
import threading
import unittest
from unittest.mock import patch

R = Path(__file__).resolve().parent
Q = R / 'joined-candidate'
D = R / 'controlled-r2'
D.mkdir(exist_ok=False)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
inputs = json.loads((R / 'JOIN-INPUTS.json').read_bytes())
pins = {name: row['sha256'] for name, row in inputs['selected'].items()}
assert all(sha(Q / name) == digest for name, digest in pins.items())
blocked = []
def audit(event, args):
    if event in ('subprocess.Popen', 'os.system', 'os.startfile', 'socket.connect', 'socket.bind') or (
            event == 'ctypes.dlsym' and args[1] in ('CreateProcessW', 'CreateProcessAsUserW',
                'CreateAppContainerProfile', 'DeleteAppContainerProfile', 'SetInformationJobObject')):
        blocked.append(event)
        raise AssertionError('REVIEW_NATIVE_EFFECT_FORBIDDEN')
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)) and isinstance(args[2], int):
        if args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            assert Path(os.fsdecode(args[0])).resolve().is_relative_to(R), 'REVIEW_WRITE_BOUNDARY'
sys.addaudithook(audit)
sys.path[:0] = [str(Q / 'src'), str(Q / 'tests/contract')]
from ceta.store.journal import SqliteJournal
from ceta.contracts.wire import ContractError, strict_loads
from ceta.effects.native_observer import NativeCpuEffectObserver, _ObservationOrigin
from ceta.identity.native_cpu_outcome import NativeCpuOutcomeProvenance
import ceta.identity.native_cpu_outcome as producer_module
from ceta.composition.native_cpu_outcome import NativeCpuOutcomeAdapter
import ceta.composition.native_cpu_outcome as adapter_module
import test_native_cpu_outcome_provenance as author
import test_cpu_capacity_connection as connection

connection.preparation.FIXTURES = D / 'fixtures'
stores = []
constructor = SqliteJournal.__init__
def capture_store(store, *args, **kwargs):
    constructor(store, *args, **kwargs)
    stores.append((store, store._connection))
SqliteJournal.__init__ = capture_store


class JoinedOutcomeChecks(unittest.TestCase):
    def setUp(self):
        schema = strict_loads((Q / 'contracts/schemas/records.schema.json').read_bytes())
        self.f = object.__new__(connection.Fixture)
        self.addCleanup(self.f.close)
        connection.Fixture.__init__(self.f, schema)
        self.observer = object.__new__(NativeCpuEffectObserver)
        self.observer._clock, self.observer._lock = self.f.clock, threading.Lock()
        self.observer._executable, self.observer._image = 'CONTROLLED-NOT-LAUNCHED', 'a' * 64
        self.observer._driver_sha = 'b' * 64
        self.observer._commitment = self.f.request.observer_commitment
        self.observer._origin, self.observer._sequence = None, 0
        self.f.view._cpu_outcome = NativeCpuOutcomeProvenance(self.f.view, self.observer)
        # This is the exact proposed view-bound property, not a test provenance predicate.
        self.f.owner._execution_provenance = self.f.view.require_owned_cpu_outcome_provenance
        self.adapter = NativeCpuOutcomeAdapter(self.f.view)
        self.observe_error = None
        self.observe_calls = 0
        def observed(observer, request, target):
            self.assertIs(observer, self.observer)
            self.assertIs(request, self.f.kernel._cpu_execution.active._request)
            self.assertEqual(request.canonical_wire, self.f.request.canonical_wire)
            self.assertIs(target, self.f.binding._target)
            self.assertFalse(self.f.store._connection.in_transaction)
            self.observe_calls += 1
            observer._origin = None
            if self.observe_error is not None:
                raise self.observe_error
            value = connection.owner_fixture.outcomes.OutcomeTransactionsTests().observation(self.f)
            observer._sequence = value.sequence
            observer._origin = _ObservationOrigin(observer, target, request.canonical_wire,
                value, value.canonical_wire, value.sequence)
            return value
        control = patch.object(producer_module, '_OBSERVE', observed)
        control.start(); self.addCleanup(control.stop)

    def test_real_kernel_commit_joins_exact_producer_observer_and_capacity(self):
        f = self.f
        with f.lease() as lease, patch.object(adapter_module, '_DISPATCH', f.fence):
            with f.capture_commit():
                result = self.adapter.execute(lease)
            self.assertEqual(result.as_dict()['state'], 'SETTLED_OBSERVED')
            self.assertEqual(strict_loads(result.receipt_wire)['effect_status'], 'MAY_HAVE_EXECUTED')
            row = f.commit_calls[-1]
            self.assertEqual(row['staged'], tuple(e.payload_wire for e in row['entries']))
            self.assertTrue(lease._outcome_capacity.lease.durable)
            self.assertEqual(self.observe_calls, 1)
            self.assertFalse(f.store._connection.in_transaction)
        self.assertIsNone(f.store._capacity_active)

    def test_real_uncertainty_commit_precedes_exact_observer_primary(self):
        primary = KeyboardInterrupt('controlled observation unavailable')
        self.observe_error = primary
        f = self.f
        with f.lease() as lease, patch.object(adapter_module, '_DISPATCH', f.fence):
            try:
                self.adapter.execute(lease)
            except BaseException as caught:
                self.assertIs(caught, primary)
            else:
                self.fail('observer primary must remain visible')
            result = primary.cpu_recorded_outcome
            self.assertEqual(result.as_dict()['state'], 'UNCERTAIN')
            self.assertTrue(lease._outcome_capacity.lease.durable)
            self.assertIs(primary.owned_cpu_execution, lease)

    def test_stop_after_dispatch_keeps_canonical_bookkeeping_available(self):
        f = self.f
        def stop(lease):
            f.fence(lease)
            f.owner.request_stop()
        with f.lease() as lease, patch.object(adapter_module, '_DISPATCH', stop):
            result = self.adapter.execute(lease)
            self.assertEqual(result.as_dict()['state'], 'SETTLED_OBSERVED')
            self.assertTrue(lease._outcome_capacity.lease.durable)
            self.assertFalse(f.approval_proof.active)
            with self.assertRaises(ContractError):
                lease.driver_arguments()

    def test_real_commit_failure_retains_exact_capture_and_capacity(self):
        f = self.f
        primary = OSError('controlled canonical commit failure')
        def fail(): raise primary
        with self.assertRaises(OSError) as caught:
            with f.lease() as lease:
                f.fence(lease)
                bound = lease._outcome_capacity
                f.fault = fail
                self.adapter.reconcile(lease)
        f.fault = None
        self.assertIs(caught.exception, primary)
        self.assertIs(primary.owned_cpu_execution, lease)
        self.assertIsNotNone(primary.cpu_outcome_capture)
        self.assertIs(f.store._capacity_active, bound.lease)
        self.assertFalse(bound.lease.durable)
        self.assertEqual(bound.lease.state, 'PENDING')


suite = unittest.TestSuite((unittest.defaultTestLoader.loadTestsFromTestCase(author.CpuOutcomeProvenanceTests),
                           unittest.defaultTestLoader.loadTestsFromTestCase(JoinedOutcomeChecks)))
def flatten(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite): yield from flatten(test)
        else: yield test.id()
expected = list(flatten(suite)); executed = []; stopped = []
threads = set(threading.enumerate())
class Recorded(unittest.TextTestResult):
    def startTest(self, test):
        gc.collect(); executed.append(test.id()); super().startTest(test)
    def stopTest(self, test):
        stopped.append(test.id()); super().stopTest(test)
with (D / 'RAW.txt').open('x', encoding='utf-8') as stream:
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Recorded).run(suite)
closure = []
for store, connection_object in stores:
    closed = False
    try: connection_object.execute('SELECT 1')
    except store._sqlite.ProgrammingError: closed = True
    closure.append(dict(path=str(store.path), closed_connection_refusal=closed,
                        retained_capacity=store._capacity_active is not None))
after = {name: sha(Q / name) for name in pins}
remaining = [thread.name for thread in set(threading.enumerate()) - threads if thread.is_alive()]
passed = result.wasSuccessful() and not result.skipped and expected == executed == stopped and pins == after
passed = passed and not blocked and not remaining and all(row['closed_connection_refusal'] and not row['retained_capacity'] for row in closure)
proof = dict(at=datetime.now(timezone.utc).isoformat(), reviewer='/root', command=list(sys.orig_argv),
    inputs_sha256=sha(R / 'JOIN-INPUTS.json'), runner_sha256=sha(__file__), expected_ids=expected,
    executed_ids=executed, stopped_ids=stopped, tests_run=result.testsRun,
    failures=[(case.id(), trace) for case, trace in result.failures],
    errors=[(case.id(), trace) for case, trace in result.errors], skips=len(result.skipped),
    before=pins, after=after, sqlite=closure, fixture_retirement=connection.FACTS,
    prohibited_calls=blocked, remaining_threads=remaining, raw_sha256=sha(D / 'RAW.txt'),
    actual_canonical_SQLite=True, native_observer_and_effect='CONTROLLED', genuine_owner_authority=False,
    Source_publication=False, production_acceptance=False, exit_status=0 if passed else 1)
with (D / 'RESULT.json').open('x', encoding='utf-8') as stream:
    json.dump(proof, stream, indent=2, allow_nan=False)
print(json.dumps(dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
    skipped=len(result.skipped), passed=passed, result_sha256=sha(D / 'RESULT.json'))))
raise SystemExit(proof['exit_status'])
