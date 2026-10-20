"""Actual retained Windows job limits, measurements and recovery.

Every native effect targets a newly owned disposable child. Injected failures
exercise the actual handle path, while execution-owner fixtures stay labelled.
"""
import ctypes as C
from dataclasses import replace
import os
from pathlib import Path
import struct
import sys
import threading
import time
import unittest
from unittest.mock import patch

import test_windows_jobs as jobs
import ceta.supervisor.windows_jobs as native
from ceta.contracts.resource_management import ObservationState, ResourceVector
from ceta.contracts.workload_throttling import CpuRateLimit, WorkloadThrottleIntent
from ceta.contracts.wire import ContractError, strict_loads
from ceta.resource.pressure import WorkloadThrottlingController
from test_resource_reservations import ResourceFixture
from test_workload_throttling import ControlledExecutionOwner, capacity, HASH

ROOT = Path(__file__).resolve().parents[2]
NATIVE_RECEIPTS = []
BUSY_CHILD = jobs.HELPERS + r'''
ready,release=sys.argv[1:]
h=k.OpenEventW(0x100000,False,release);assert h
signal(ready)
x=1
while k.WaitForSingleObject(h,0)==258:
    for i in range(1000): x=(x*1664525+1013904223)&0xffffffff
assert k.CloseHandle(h)
'''


@unittest.skipUnless(os.name == 'nt' and struct.calcsize('P') == 8, 'actual Windows x64 required')
class WindowsThrottleTests(unittest.TestCase):
    def setUp(self):
        # Reuse fixture functions, not inherited/discovered TestCase methods.
        self.fixture = jobs.WindowsJobTests()
        self.fixture.setUp()
        info = self.fixture.directory.stat()
        self.receipt = {'test_id': self.id(), 'fixture': str(self.fixture.directory), 'lifetimes': [],
                        'fixture_before_child': {'device': info.st_dev, 'inode': info.st_ino, 'mtime_ns': info.st_mtime_ns}}
        self.addCleanup(self.settle)

    def settle(self):
        self.fixture.tearDown()
        self.receipt['closed_lifetimes'] = [{'pid': owned.pid, 'creation': owned.creation_time,
                                           'lifetime_closed': owned.lifetime_closed}
                                          for owned in self.fixture.owned]
        self.receipt['all_owned_lifetimes_closed'] = all(owned.lifetime_closed for owned in self.fixture.owned)
        NATIVE_RECEIPTS.append(self.receipt)

    def simple(self):
        owned, release, metadata = self.fixture.simple()
        self.receipt['lifetimes'].append({'pid': owned.pid, 'creation': owned.creation_time, 'image_sha256': owned.image_sha256})
        return owned, release

    def observe(self, owned):
        result = owned.cpu_rate_observation(owned.resource_identity, maximum_duration_ns=500_000_000)
        self.assertEqual(result.state, ObservationState.MEASURED, result)
        return result

    def apply(self, owned, expected=None, operation='throttle:native', rate=100):
        return owned.apply_cpu_rate_limit(operation, owned.resource_identity, expected or self.observe(owned),
            CpuRateLimit.hard_cap(rate), deadline_monotonic_ns=time.monotonic_ns() + 5_000_000_000,
            maximum_duration_ns=500_000_000)

    def restore(self, owned, change, operation='restore:native'):
        return owned.restore_cpu_rate_limit(operation, change.operation_id, owned.resource_identity, self.observe(owned),
            change.before,
            deadline_monotonic_ns=time.monotonic_ns() + 5_000_000_000, maximum_duration_ns=500_000_000)

    def test_actual_query_apply_and_exact_original_policy_recovery(self):
        owned, release = self.simple(); before = self.observe(owned)
        basic_before, basic_after = native.EXTENDED_LIMIT(), native.EXTENDED_LIMIT()
        self.assertTrue(owned._api.QueryInformationJobObject(owned._job, 9, C.byref(basic_before), C.sizeof(basic_before), None))
        change = self.apply(owned, before)
        self.assertEqual(change.state, 'APPLIED'); self.assertEqual(change.before, before.limit)
        self.assertEqual(self.observe(owned).limit, CpuRateLimit.hard_cap(100))
        restored = self.restore(owned, change)
        self.assertEqual((restored.state, restored.observed.limit), ('RESTORED', before.limit))
        self.assertTrue(owned._api.QueryInformationJobObject(owned._job, 9, C.byref(basic_after), C.sizeof(basic_after), None))
        self.assertEqual(bytes(basic_before.basic), bytes(basic_after.basic))
        self.assertTrue(basic_after.basic.flags & native.KILL_ON_JOB_CLOSE)
        release.signal(); self.assertTrue(owned.wait(5))
        self.fixture.until(lambda: owned.active_process_count() == 0)
        self.assertEqual(owned.active_process_count(), 0)
        self.receipt.update(before_flags=before.limit.control_flags, before_value=before.limit.value,
            applied_flags=change.observed.limit.control_flags, applied_value=change.observed.limit.value,
            recovered_flags=restored.observed.limit.control_flags, recovered_value=restored.observed.limit.value,
            original_basic_limit_bytes_exact=True, empty_job=True)

    def test_native_concurrent_expected_version_allows_only_one_effect(self):
        owned, release = self.simple(); expected = self.observe(owned)
        original = owned._api.SetInformationJobObject; calls = []; outputs = []; barrier = threading.Barrier(3)
        def counted(*arguments):
            calls.append(arguments[1]); return original(*arguments)
        def run(operation):
            barrier.wait()
            try: outputs.append(self.apply(owned, expected, operation))
            except ContractError as failure: outputs.append(failure.code)
        with patch.object(owned._api, 'SetInformationJobObject', counted):
            threads = [threading.Thread(target=run, args=('throttle:' + str(i),)) for i in range(2)]
            for thread in threads: thread.start()
            barrier.wait()
            for thread in threads: thread.join(5); self.assertFalse(thread.is_alive())
        successes = [value for value in outputs if not isinstance(value, str)]
        self.assertEqual((len(successes), calls), (1, [15]))
        self.assertIn('WINDOWS_CPU_LIMIT_CONFLICT', outputs)
        self.assertEqual(self.restore(owned, successes[0]).state, 'RESTORED')
        self.receipt.update(native_effect_calls=len(calls), competition_states=[getattr(x, 'state', x) for x in outputs])

    def test_duplicate_apply_and_restore_do_not_repeat_native_effect(self):
        owned, release = self.simple(); change = self.apply(owned)
        original = owned._api.SetInformationJobObject; calls = []
        def counted(*args): calls.append(args[1]); return original(*args)
        with patch.object(owned._api, 'SetInformationJobObject', counted):
            duplicate = self.apply(owned, operation=change.operation_id)
            self.assertEqual(duplicate.state, 'APPLIED'); self.assertEqual(calls, [])
            restored = self.restore(owned, change)
            duplicate_restore = self.restore(owned, change)
            self.assertEqual(duplicate_restore.state, 'RESTORED'); self.assertEqual(calls, [15])
        self.assertEqual(restored.observed.limit, change.before)

    def test_wrong_lifetime_job_and_stale_limit_reject_before_set(self):
        owned, release = self.simple(); expected = self.observe(owned)
        inputs = (replace(expected, job_digest='sha256:' + 'b' * 64),
                  replace(expected, identity=replace(expected.identity, creation_time=expected.identity.creation_time + 1)),
                  replace(expected, version=expected.version + 1))
        with patch.object(owned._api, 'SetInformationJobObject') as setter:
            for value in inputs:
                with self.subTest(value=value), self.assertRaises(ContractError): self.apply(owned, value)
            setter.assert_not_called()
        self.assertEqual(self.observe(owned).limit, expected.limit)

    def test_future_expired_and_invalid_bounds_never_apply(self):
        owned, release = self.simple(); expected = self.observe(owned)
        with patch.object(owned._api, 'SetInformationJobObject') as setter:
            with self.assertRaises(ContractError): self.apply(owned, replace(expected, observed_monotonic_ns=time.monotonic_ns() + 1_000_000_000))
            with self.assertRaises(ContractError):
                owned.apply_cpu_rate_limit('throttle:expired', owned.resource_identity, expected, CpuRateLimit.hard_cap(100),
                                          deadline_monotonic_ns=time.monotonic_ns())
            for bound in (0, True, -1, 1_000_000_001):
                with self.subTest(bound=bound), self.assertRaises(ContractError):
                    owned.cpu_rate_observation(owned.resource_identity, maximum_duration_ns=bound)
            setter.assert_not_called()

    def test_actual_slow_query_rejects_subtick_elapsed_window(self):
        owned, release = self.simple(); original = owned._api.QueryInformationJobObject
        def delayed(*args):
            result = original(*args)
            if args[1] == 15: time.sleep(.02)
            return result
        with patch.object(owned._api, 'QueryInformationJobObject', delayed):
            observed = owned.cpu_rate_observation(owned.resource_identity, maximum_duration_ns=5_000_000)
        self.assertEqual((observed.state, observed.limit, observed.reason),
                         (ObservationState.UNAVAILABLE, None, 'WINDOWS_CPU_OBSERVATION_TOO_SLOW'))
        self.receipt.update(injected_query_delay_ns=20_000_000, rejected_window_ns=5_000_000,
                            public_clock_resolution_ns=int(time.get_clock_info('monotonic').resolution * 1e9))

    def test_expectation_age_rechecked_after_real_delayed_currentness(self):
        owned, release = self.simple(); expected = self.observe(owned)
        original = owned._api.QueryInformationJobObject
        def delayed(*args):
            result = original(*args)
            if args[1] == 15: time.sleep(.12)
            return result
        with patch.object(owned._api, 'QueryInformationJobObject', delayed), patch.object(owned._api, 'SetInformationJobObject') as setter:
            with self.assertRaisesRegex(ContractError, 'WINDOWS_CPU_EXPECTATION_STALE'):
                owned.apply_cpu_rate_limit('throttle:aged', owned.resource_identity, expected, CpuRateLimit.hard_cap(100),
                    deadline_monotonic_ns=time.monotonic_ns() + 5_000_000_000,
                    maximum_age_ns=100_000_000, maximum_duration_ns=500_000_000)
            setter.assert_not_called()

    def test_query_oserror_and_wrong_payload_size_are_unavailable(self):
        owned, release = self.simple(); original = owned._api.QueryInformationJobObject
        def broken(*args):
            if args[1] == 15: raise OSError('private native detail')
            return original(*args)
        with patch.object(owned._api, 'QueryInformationJobObject', broken):
            observed = owned.cpu_rate_observation(owned.resource_identity)
        self.assertEqual((observed.state, observed.limit, observed.reason),
                         (ObservationState.UNAVAILABLE, None, 'WINDOWS_CPU_NATIVE_UNAVAILABLE'))
        def wrong_size(*args):
            result = original(*args)
            if args[1] == 15: C.cast(args[4], C.POINTER(native.DWORD)).contents.value = 4
            return result
        with patch.object(owned._api, 'QueryInformationJobObject', wrong_size):
            observed = owned.cpu_rate_observation(owned.resource_identity)
        self.assertEqual(observed.reason, 'WINDOWS_CPU_QUERY_SIZE_INVALID')

    def test_native_failed_set_spends_version_and_observes_original(self):
        owned, release = self.simple(); expected = self.observe(owned)
        with patch.object(owned._api, 'SetInformationJobObject', return_value=0):
            result = self.apply(owned, expected)
        self.assertEqual((result.state, result.observed.limit), ('NOT_APPLIED', expected.limit))
        self.assertGreater(result.observed.version, expected.version)
        with self.assertRaises(ContractError): self.apply(owned, expected, operation='throttle:later')

    def test_interrupted_real_apply_retains_owner_and_reconciles_without_retry(self):
        owned, release = self.simple(); original = owned._api.SetInformationJobObject; calls = []
        failure = KeyboardInterrupt('primary apply interruption')
        def interrupted(*args):
            calls.append(args[1]); self.assertTrue(original(*args)); raise failure
        with patch.object(owned._api, 'SetInformationJobObject', interrupted):
            with self.assertRaises(KeyboardInterrupt) as caught: self.apply(owned)
        self.assertIs(caught.exception, failure); self.assertIs(failure.owned_process, owned)
        self.assertEqual(failure.cpu_rate_change.state, 'UNCERTAIN')
        with patch.object(owned._api, 'SetInformationJobObject') as setter:
            reconciled = owned.reconcile_cpu_rate_limit(owned.resource_identity)
            self.assertEqual(reconciled.state, 'APPLIED'); setter.assert_not_called()
        self.assertEqual(self.restore(owned, reconciled).state, 'RESTORED')
        self.receipt.update(primary_exception_preserved=True, apply_native_calls=len(calls), read_only_reconciliation=True)

    def test_interrupted_real_restoration_observes_original_before_duplicate(self):
        owned, release = self.simple(); change = self.apply(owned)
        original = owned._api.SetInformationJobObject; failure = SystemExit(19)
        def interrupted(*args): self.assertTrue(original(*args)); raise failure
        with patch.object(owned._api, 'SetInformationJobObject', interrupted):
            with self.assertRaises(SystemExit) as caught: self.restore(owned, change)
        self.assertIs(caught.exception, failure)
        self.assertEqual(failure.cpu_rate_change.restoration_id, 'restore:native')
        reconciled = owned.reconcile_cpu_rate_limit(owned.resource_identity)
        self.assertEqual((reconciled.state, reconciled.observed.limit), ('RESTORED', change.before))
        with patch.object(owned._api, 'SetInformationJobObject') as setter:
            self.assertEqual(self.restore(owned, change).state, 'RESTORED'); setter.assert_not_called()

    def test_uncertain_post_apply_query_requires_reconciliation_before_restore(self):
        owned, release = self.simple(); original = owned._api.QueryInformationJobObject; calls = 0
        def lost_after(*args):
            nonlocal calls
            if args[1] == 15:
                calls += 1
                if calls >= 2: return 0
            return original(*args)
        expected = self.observe(owned)
        with patch.object(owned._api, 'QueryInformationJobObject', lost_after): result = self.apply(owned, expected)
        self.assertEqual(result.state, 'UNCERTAIN')
        with self.assertRaisesRegex(ContractError, 'WINDOWS_CPU_UNCERTAIN_RECONCILIATION_REQUIRED'): self.restore(owned, result)
        reconciled = owned.reconcile_cpu_rate_limit(owned.resource_identity)
        self.assertEqual(reconciled.state, 'APPLIED')
        self.assertEqual(self.restore(owned, reconciled).state, 'RESTORED')

    def test_unexpected_external_owned_job_change_is_not_blindly_overwritten(self):
        owned, release = self.simple(); change = self.apply(owned); old = self.observe(owned)
        foreign = native.CPU_RATE_CONTROL(5, 200)
        self.assertTrue(owned._api.SetInformationJobObject(owned._job, 15, C.byref(foreign), C.sizeof(foreign)))
        with patch.object(owned._api, 'SetInformationJobObject') as setter:
            with self.assertRaises(ContractError):
                owned.restore_cpu_rate_limit('restore:native', change.operation_id, owned.resource_identity, old,
                    change.before,
                    deadline_monotonic_ns=time.monotonic_ns() + 5_000_000_000)
            self.assertEqual(owned.reconcile_cpu_rate_limit(owned.resource_identity).state, 'CONFLICT')
            setter.assert_not_called()
        self.assertEqual(self.observe(owned).limit.value, 200)

    def test_distinct_restoration_target_mismatch_rejects_before_native_set(self):
        owned, release = self.simple(); change = self.apply(owned)
        with patch.object(owned._api, 'SetInformationJobObject') as setter:
            with self.assertRaisesRegex(ContractError, 'WINDOWS_CPU_RESTORATION_TARGET_MISMATCH'):
                owned.restore_cpu_rate_limit('restore:wrong', change.operation_id, owned.resource_identity,
                    self.observe(owned), CpuRateLimit.hard_cap(300),
                    deadline_monotonic_ns=time.monotonic_ns() + 5_000_000_000)
            setter.assert_not_called()
        self.assertEqual(self.observe(owned).limit, change.intended)
        self.assertEqual(self.restore(owned, change).state, 'RESTORED')

    def test_incoming_limit_mutation_during_query_does_not_change_captured_effect(self):
        owned, release = self.simple(); expected = self.observe(owned); intended = CpuRateLimit.hard_cap(100)
        original = owned._api.QueryInformationJobObject
        def changed_input(*args):
            result = original(*args)
            if args[1] == 15: object.__setattr__(intended, 'value', 200)
            return result
        with patch.object(owned._api, 'QueryInformationJobObject', changed_input):
            change = owned.apply_cpu_rate_limit('throttle:captured', owned.resource_identity, expected, intended,
                deadline_monotonic_ns=time.monotonic_ns() + 5_000_000_000)
        self.assertEqual((intended.value, change.intended.value, change.observed.limit.value), (200, 100, 100))
        self.assertEqual(self.restore(owned, change).state, 'RESTORED')

    def test_actual_weight_policy_is_observed_and_unsupported_conversion_is_denied(self):
        owned, release = self.simple(); weight = native.CPU_RATE_CONTROL(3, 5)
        self.assertTrue(owned._api.SetInformationJobObject(owned._job, 15, C.byref(weight), C.sizeof(weight)))
        expected = self.observe(owned)
        self.assertEqual(expected.limit, CpuRateLimit(3, 5))
        with patch.object(owned._api, 'SetInformationJobObject') as setter:
            with self.assertRaisesRegex(ContractError, 'WINDOWS_CPU_REDUCTION_REQUIRED'): self.apply(owned, expected)
            setter.assert_not_called()
        self.assertEqual(self.observe(owned).limit, CpuRateLimit(3, 5))

    def test_native_notification_policy_is_not_silently_removed(self):
        owned, release = self.simple(); notified = native.CPU_RATE_CONTROL(13, 1000)
        self.assertTrue(owned._api.SetInformationJobObject(owned._job, 15, C.byref(notified), C.sizeof(notified)))
        expected = self.observe(owned); self.assertEqual(expected.limit, CpuRateLimit(13, 1000))
        with patch.object(owned._api, 'SetInformationJobObject') as setter:
            with self.assertRaisesRegex(ContractError, 'WINDOWS_CPU_NOTIFICATION_PRESERVATION_REQUIRED'):
                self.apply(owned, expected)
            setter.assert_not_called()
        preserved = owned.apply_cpu_rate_limit('throttle:notified', owned.resource_identity, expected, CpuRateLimit(13, 100),
            deadline_monotonic_ns=time.monotonic_ns() + 5_000_000_000)
        self.assertEqual((preserved.state, preserved.observed.limit), ('APPLIED', CpuRateLimit(13, 100)))
        self.assertEqual(self.restore(owned, preserved).observed.limit, expected.limit)

    def test_owned_stop_remains_observable_under_native_cpu_cap(self):
        owned, release = self.simple(); change = self.apply(owned, rate=1)
        started = time.perf_counter_ns(); owned.terminate(126)
        self.assertTrue(owned.wait(5)); self.fixture.until(lambda: owned.active_process_count() == 0)
        elapsed = time.perf_counter_ns() - started
        self.assertEqual(owned.active_process_count(), 0)
        self.assertEqual(owned.cpu_rate_observation(owned.resource_identity).state, ObservationState.UNAVAILABLE)
        self.receipt.update(owned_stop_elapsed_ns=elapsed, cap_cycles_per_10000=1,
                            primary_exit_observed=True, empty_job=True)
        self.assertLess(elapsed, 5_000_000_000)

    def test_native_clock_rollback_remains_closed_after_clock_recovers(self):
        owned, release = self.simple(); self.observe(owned)
        current = time.monotonic_ns()
        with patch.object(native.time, 'monotonic_ns', return_value=current - 1_000_000_000):
            with self.assertRaisesRegex(ContractError, 'WINDOWS_CPU_CLOCK_ROLLBACK'): self.observe(owned)
        with self.assertRaisesRegex(ContractError, 'WINDOWS_CPU_CLOCK_ROLLBACK'): self.observe(owned)

    def test_job_nonce_failure_occurs_before_native_handle_or_process_creation(self):
        from unittest.mock import Mock
        api = native._API(); failure = OSError('nonce unavailable')
        create_process = Mock(wraps=api.dll.CreateProcessW)
        create_job = Mock(wraps=api.dll.CreateJobObjectW)
        with patch.object(native.C, 'WinDLL', return_value=api.dll), \
             patch.object(api.dll, 'CreateProcessW', create_process), \
             patch.object(api.dll, 'CreateJobObjectW', create_job), \
             patch.object(native.os, 'urandom', side_effect=failure):
            with self.assertRaises(OSError) as caught:
                native.WindowsOwnedProcess.launch(str(jobs.BASE), ('-B', '-I', '-c', 'pass'),
                    cwd=str(self.fixture.directory), environment=self.fixture.environment)
        self.assertIs(caught.exception, failure)
        create_process.assert_not_called(); create_job.assert_not_called()
        self.receipt.update(nonce_failure_before_native_job_or_process=True, native_creation_calls=0)

    def test_stopped_lifetime_rejects_new_cpu_mutation(self):
        owned, release = self.simple(); expected = self.observe(owned)
        owned.terminate(126); self.assertTrue(owned.wait(5))
        with patch.object(owned._api, 'SetInformationJobObject') as setter:
            with self.assertRaises(ContractError): self.apply(owned, expected)
            setter.assert_not_called()
        self.assertEqual(owned.cpu_rate_observation(owned.resource_identity).state, ObservationState.UNAVAILABLE)

    def test_actual_busy_workload_cpu_pressure_decreases_and_recovers(self):
        ready, release = self.fixture.event(), self.fixture.event()
        owned = self.fixture.launch(('-B', '-I', '-c', BUSY_CHILD, ready.name, release.name))
        self.receipt['lifetimes'].append({'pid': owned.pid, 'creation': owned.creation_time, 'image_sha256': owned.image_sha256})
        ready.wait(); before = self.observe(owned)
        def measure(seconds):
            initial = owned.resource_counters(); start = time.perf_counter_ns()
            time.sleep(seconds)
            final = owned.resource_counters(); end = time.perf_counter_ns()
            a, b = initial.usage.cpu_time_100ns, final.usage.cpu_time_100ns
            self.assertTrue(a.measured and b.measured)
            self.assertGreaterEqual(b.value, a.value)
            return {'cpu_100ns': b.value - a.value, 'elapsed_ns': end - start,
                    'cpu_milli': (b.value - a.value) * 100 * 1000 // (end - start)}
        baseline = measure(.6)
        change = self.apply(owned, rate=1)
        capped = measure(1.0)
        restored = self.restore(owned, change)
        recovered = measure(.6)
        self.receipt.update(baseline=baseline, capped=capped, recovered=recovered,
            cap_cycles_per_10000=1, before_policy=[before.limit.control_flags, before.limit.value],
            restored_policy=[restored.observed.limit.control_flags, restored.observed.limit.value],
            claim='One owned fixture on this host; no whole-machine quota or production timing guarantee')
        self.assertEqual(restored.observed.limit, before.limit)
        self.assertGreater(baseline['cpu_milli'], 50)
        self.assertLess(capped['cpu_milli'], baseline['cpu_milli'] * .6)
        self.assertGreater(recovered['cpu_milli'], capped['cpu_milli'] * 2 + 10)
        release.signal(); self.assertTrue(owned.wait(5))
        self.fixture.until(lambda: owned.active_process_count() == 0)
        self.assertEqual(owned.active_process_count(), 0)

    def test_actual_sqlite_lease_controller_and_native_owner_conformance(self):
        owned, release = self.simple(); expected = self.observe(owned)
        fixture = ResourceFixture(strict_loads((ROOT / 'contracts/schemas/records.schema.json').read_bytes()))
        self.addCleanup(fixture.close_with_receipt, self.id())
        request = fixture.request(); fixture.port.reserve(request); lease = fixture.port.recover(request.request_id)
        context = object(); owner = ControlledExecutionOwner(context)
        intent = WorkloadThrottleIntent('throttle:joined', HASH, HASH, lease, fixture.read_budget(), owned.resource_identity,
            expected, CpuRateLimit.hard_cap(100), capacity(time.monotonic_ns()), ResourceVector(10, 10, 10, 10),
            time.monotonic_ns() + 5_000_000_000)
        controller = WorkloadThrottlingController(owner, maximum_decision_duration_ns=500_000_000)
        result = controller.execute(intent, owned, context)
        self.assertEqual((result.state, result.change.state), ('APPLIED', 'APPLIED'))
        original_pressure_time = intent.pressure.total.observed_monotonic_ns
        self.fixture.until(lambda: time.monotonic_ns() > original_pressure_time)
        restored_intent = replace(intent, operation_id='restore:joined', restoration_of=intent.operation_id,
            expected_limit=self.observe(owned), proposed_limit=expected.limit,
            pressure=capacity(time.monotonic_ns(), sequence=2), deadline_monotonic_ns=time.monotonic_ns() + 5_000_000_000)
        restored = controller.execute(restored_intent, owned, context)
        self.assertEqual(restored.state, 'RESTORED', restored)
        self.assertEqual(restored.change.observed.limit, expected.limit)
        self.assertEqual(fixture.read_budget(), intent.budget)
        self.receipt.update(real_SQLite_resource_lease=True, real_native_effect_observation=True,
            execution_provider='Controlled fixture only; durable authenticated production admission remains pending',
            pressure_producer='Controlled pressure snapshot; no physical observation authenticity claim')


class WindowsDispatchFenceTests(unittest.TestCase):
    """Actual retained owned jobs and controlled canonical admission schedules."""
    def setUp(self):
        self.h = WindowsThrottleTests(); self.h.setUp(); self.h.receipt['test_id'] = self.id()
        self.addCleanup(self.h.doCleanups)

    def bound_controller(self, owned, *, change=None):
        f = ResourceFixture(strict_loads((ROOT / 'contracts/schemas/records.schema.json').read_bytes()))
        self.addCleanup(f.close_with_receipt, self.id())
        request = f.request(); f.port.reserve(request)
        context = object(); owner = ControlledExecutionOwner(context)
        intent = WorkloadThrottleIntent('throttle:dispatch', HASH, HASH, f.port.recover(request.request_id), f.read_budget(),
            owned.resource_identity, self.h.observe(owned), CpuRateLimit.hard_cap(100), capacity(time.monotonic_ns()),
            ResourceVector(10, 10, 10, 10), time.monotonic_ns() + 5_000_000_000)
        if change is not None:
            intent = replace(intent, operation_id='restore:dispatch', restoration_of=change.operation_id, proposed_limit=change.before)
        controller = WorkloadThrottlingController(owner, maximum_decision_duration_ns=1_000_000_000)
        return context, owner, intent, controller

    def test_stop_in_native_preparation_clock_preserves_policy_and_version(self):
        owned, release = self.h.simple(); context, owner, intent, controller = self.bound_controller(owned)
        old_clock = owned._cpu_now; stopped = False; setters = []
        def clock():
            nonlocal stopped
            if not stopped: stopped = True; controller.stop()
            return old_clock()
        original = owned._api.SetInformationJobObject
        def counted(*args): setters.append(args[1]); return original(*args)
        with patch.object(owned, '_cpu_now', clock), patch.object(owned._api, 'SetInformationJobObject', counted):
            result = controller.execute(intent, owned, context)
        observed = self.h.observe(owned)
        self.assertEqual((result.state, setters, observed.limit), ('BLOCKED', [], intent.expected_limit.limit))
        self.assertEqual(observed.version, intent.expected_limit.version); self.assertIsNone(owned._cpu_change)
        self.h.receipt.update(dispatch_stop=True, native_set_calls=0, version_unspent=True)

    def test_restoration_stop_in_last_controller_clock_preserves_applied_limit(self):
        owned, release = self.h.simple(); change = self.h.apply(owned)
        context, owner, intent, controller = self.bound_controller(owned, change=change)
        armed = False; plans = 0; original_plan = controller.plan; original_set = owned._api.SetInformationJobObject
        setters = []
        def plan(*args, **kwargs):
            nonlocal plans, armed
            result = original_plan(*args, **kwargs); plans += 1
            if plans == 2: armed = True
            return result
        def clock():
            nonlocal armed
            if armed: armed = False; controller.stop()
            return time.monotonic_ns()
        def counted(*args): setters.append(args[1]); return original_set(*args)
        controller._clock = clock
        with patch.object(controller, 'plan', plan), patch.object(owned._api, 'SetInformationJobObject', counted):
            result = controller.execute(intent, owned, context)
        observed = self.h.observe(owned)
        self.assertEqual((result.state, setters, observed.limit), ('BLOCKED', [], change.intended))
        self.assertEqual(observed.version, intent.expected_limit.version)
        self.assertEqual(self.h.restore(owned, change, 'restore:distinct-recovery').state, 'RESTORED')
        self.h.receipt.update(restoration_dispatch_denied=True, original_policy_restored=True)

    def test_stop_thread_does_not_wait_for_held_native_and_authority_locks(self):
        owned, release = self.h.simple(); context, owner, intent, controller = self.bound_controller(owned)
        entered = threading.Event(); proceed = threading.Event(); checks = 0; outputs = []; faults = []; setters = []
        def hook():
            nonlocal checks
            checks += 1
            if checks == 2: entered.set(); self.assertTrue(proceed.wait(3))
        owner.hook = hook; original = owned._api.SetInformationJobObject
        def counted(*args): setters.append(args[1]); return original(*args)
        def run():
            try: outputs.append(controller.execute(intent, owned, context))
            except BaseException as failure: faults.append(failure)
        with patch.object(owned._api, 'SetInformationJobObject', counted):
            worker = threading.Thread(target=run); worker.start()
            try:
                self.assertTrue(entered.wait(3)); started = time.perf_counter_ns(); controller.stop()
                latency = time.perf_counter_ns() - started
                self.assertLess(latency, 250_000_000); self.assertTrue(worker.is_alive())
            finally: proceed.set(); worker.join(3)
        self.assertFalse(worker.is_alive()); self.assertEqual(faults, [])
        self.assertEqual((outputs[0].state, setters), ('BLOCKED', []))
        self.assertEqual(self.h.observe(owned).limit, intent.expected_limit.limit)
        self.h.receipt.update(joined_threads=1, stop_elapsed_ns=latency, native_set_calls=0)

    def test_stop_after_logical_admission_retains_native_effect_and_separate_recovery(self):
        owned, release = self.h.simple(); context, owner, intent, controller = self.bound_controller(owned)
        entered = threading.Event(); proceed = threading.Event(); outputs = []; faults = []; setters = []
        original = owned._api.SetInformationJobObject
        def paused_set(*args):
            entered.set(); self.assertTrue(proceed.wait(3)); setters.append(args[1]); return original(*args)
        def run():
            try: outputs.append(controller.execute(intent, owned, context))
            except BaseException as failure: faults.append(failure)
        with patch.object(owned._api, 'SetInformationJobObject', paused_set):
            worker = threading.Thread(target=run); worker.start()
            try: self.assertTrue(entered.wait(3)); controller.stop()
            finally: proceed.set(); worker.join(3)
        self.assertFalse(worker.is_alive()); self.assertEqual(faults, [])
        self.assertEqual(setters, [15]); self.assertIn(outputs[0].state, ('APPLIED', 'UNCERTAIN'))
        self.assertEqual(self.h.observe(owned).limit, intent.proposed_limit); self.assertTrue(owner.outcomes)
        reconciled = owned.reconcile_cpu_rate_limit(owned.resource_identity)
        self.assertEqual(self.h.restore(owned, reconciled, 'restore:after-admission').state, 'RESTORED')
        self.h.receipt.update(joined_threads=1, stop_after_logical_admission=True, native_set_calls=1, original_policy_restored=True)

    def test_stop_after_irreversible_set_retains_the_observed_effect(self):
        owned, release = self.h.simple(); context, owner, intent, controller = self.bound_controller(owned)
        original = owned._api.SetInformationJobObject
        def stopped_after_set(*args):
            succeeded = original(*args); controller.stop(); return succeeded
        with patch.object(owned._api, 'SetInformationJobObject', stopped_after_set):
            result = controller.execute(intent, owned, context)
        self.assertIn(result.state, ('APPLIED', 'UNCERTAIN'))
        self.assertIsNotNone(result.change); self.assertEqual(self.h.observe(owned).limit, intent.proposed_limit)
        self.assertTrue(owner.outcomes)
        reconciled = owned.reconcile_cpu_rate_limit(owned.resource_identity)
        self.assertEqual(self.h.restore(owned, reconciled, 'restore:after-set').state, 'RESTORED')
        self.h.receipt.update(stop_after_irreversible_set=True, original_policy_restored=True)

    def test_non_none_dispatch_decision_preserves_native_state_without_set(self):
        owned, release = self.h.simple(); expected = self.h.observe(owned)
        with patch.object(owned._api, 'SetInformationJobObject') as setter:
            with self.assertRaisesRegex(ContractError, 'WINDOWS_CPU_DISPATCH_DECISION_MALFORMED'):
                owned.apply_cpu_rate_limit('throttle:bad-fence', owned.resource_identity, expected, CpuRateLimit.hard_cap(100),
                    deadline_monotonic_ns=time.monotonic_ns() + 5_000_000_000,
                    maximum_duration_ns=500_000_000, dispatch_fence=lambda: True)
            setter.assert_not_called()
        observed = self.h.observe(owned)
        self.assertEqual((observed.limit, observed.version), (expected.limit, expected.version)); self.assertIsNone(owned._cpu_change)

    def test_reentrant_native_policy_change_in_fence_is_not_overwritten(self):
        owned, release = self.h.simple(); expected = self.h.observe(owned); first = []
        def fence(): first.append(self.h.apply(owned, expected, 'throttle:reentrant', rate=200))
        with self.assertRaisesRegex(ContractError, 'WINDOWS_CPU_DISPATCH_STATE_CHANGED'):
            owned.apply_cpu_rate_limit('throttle:prepared', owned.resource_identity, expected, CpuRateLimit.hard_cap(100),
                deadline_monotonic_ns=time.monotonic_ns() + 5_000_000_000,
                maximum_duration_ns=500_000_000, dispatch_fence=fence)
        self.assertEqual(self.h.observe(owned).limit, CpuRateLimit.hard_cap(200))
        self.assertEqual(owned._cpu_change.operation_id, 'throttle:reentrant')
        self.assertEqual(self.h.restore(owned, first[0], 'restore:reentrant').state, 'RESTORED')
        self.h.receipt.update(reentrant_preparation_denied=True, original_policy_restored=True)
