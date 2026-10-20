"""Timing fences: declared test clocks and actual owned Windows observations."""
from dataclasses import replace
import threading
import time
import unittest
from unittest.mock import patch

from ceta.contracts.wire import ContractError
from ceta.resource.diagnostics import OwnedProcessTelemetrySampler, PerformanceDiagnostics, PerformanceEnvelope, ResourceTelemetryRecorder
from test_process_diagnostics import CounterPort, IDENTITY, WORKLOAD, counters, digest
import test_windows_jobs as jobs

NATIVE_OBSERVATIONS = []


class ProcessObservationTimingTests(unittest.TestCase):
    def fixture(self, *, interval=10, age=100, window=30, resolution=0):
        now, elapsed = [100], [1000]
        port = CounterPort(now)
        sampler = OwnedProcessTelemetrySampler(port, IDENTITY,
            scope_digest=digest("scope"), environment_digest=digest("environment"),
            workload_digest=digest("workload"), source_generation=4,
            clock=lambda: now[0], minimum_interval_ns=interval,
            maximum_age_ns=age, maximum_probe_window_ns=window)
        # Explicit deterministic timing-domain injection. Actual native default
        # clocks and retained handles are exercised separately below.
        sampler._elapsed_clock = lambda: elapsed[0]
        sampler._clock_resolution = resolution
        return now, elapsed, port, sampler

    def test_currentness_occupancy_exceeding_bound_with_zero_public_delta_is_rejected(self):
        now, elapsed, port, sampler = self.fixture()
        def delayed(identity):
            elapsed[0] += 31
            return True
        with patch.object(port, "resource_observation_current", side_effect=delayed):
            result = sampler.sample()
        self.assertEqual((result.cpu_milli.reason, result.memory_bytes.measured, port.calls),
                         ("PROCESS_PROBE_TOO_SLOW", False, 0))

    def test_counter_occupancy_exceeding_bound_with_zero_public_delta_is_rejected(self):
        now, elapsed, port, sampler = self.fixture()
        def delayed():
            elapsed[0] += 31
            return counters(now[0])
        with patch.object(port, "resource_counters", side_effect=delayed):
            result = sampler.sample()
        self.assertEqual(result.cpu_milli.reason, "PROCESS_PROBE_TOO_SLOW")
        self.assertIsNone(result.process_usage)

    def test_combined_lifetime_and_counter_time_is_bounded(self):
        now, elapsed, port, sampler = self.fixture()
        def current(identity):
            elapsed[0] += 20
            return True
        def queried():
            elapsed[0] += 20
            return counters(now[0])
        with patch.object(port, "resource_observation_current", side_effect=current), patch.object(port, "resource_counters", side_effect=queried):
            self.assertEqual(sampler.sample().cpu_milli.reason, "PROCESS_PROBE_TOO_SLOW")

    def test_public_clock_bound_also_remains_enforced(self):
        now, elapsed, port, sampler = self.fixture()
        def delayed():
            now[0] += 31
            return counters(now[0])
        with patch.object(port, "resource_counters", side_effect=delayed):
            self.assertEqual(sampler.sample().cpu_milli.reason, "PROCESS_PROBE_TOO_SLOW")

    def test_slow_public_clock_lookup_is_included_in_elapsed_window(self):
        now, elapsed, port, sampler = self.fixture()
        def clock():
            elapsed[0] += 31
            return now[0]
        sampler._clock = clock
        result = sampler.sample()
        self.assertEqual((result.cpu_milli.reason, port.calls), ("PROCESS_PROBE_TOO_SLOW", 0))

    def test_elapsed_clock_rollback_preserves_its_high_water_across_public_progress(self):
        now, elapsed, port, sampler = self.fixture()
        sampler.sample()
        for at, tick in ((110, 999), (120, 999), (130, 998)):
            now[0], elapsed[0] = at, tick
            self.assertEqual(sampler.sample().cpu_milli.reason, "PROCESS_CLOCK_ROLLBACK")
        self.assertEqual((port.calls, sampler._last_elapsed), (1, 1000))
        now[0], elapsed[0] = 140, 1020
        result = sampler.sample()
        self.assertEqual(result.cpu_milli.reason, "PROCESS_CPU_BASELINE_REQUIRED")

    def test_public_clock_rollback_preserves_high_water_and_cache_never_reopens(self):
        now, elapsed, port, sampler = self.fixture()
        sampler.sample()
        now[0], elapsed[0] = 120, 1020
        sampler.sample()
        for at in (119, 110, 118):
            now[0], elapsed[0] = at, elapsed[0] + 10
            result = sampler.sample()
            self.assertEqual(result.cpu_milli.reason, "PROCESS_CLOCK_ROLLBACK")
            self.assertEqual(result.observed_monotonic_ns, at)
            self.assertEqual(sampler._last_clock, 120)
        self.assertEqual(port.calls, 2)
        now[0], elapsed[0] = 130, 1070
        self.assertEqual(sampler.sample().cpu_milli.reason, "PROCESS_CPU_BASELINE_REQUIRED")

    def test_elapsed_clock_wrong_types_and_bounds_fail_before_native_probe(self):
        for invalid in (True, -1, 2**63, None, 1.0):
            now, elapsed, port, sampler = self.fixture()
            sampler._elapsed_clock = lambda: invalid
            with self.subTest(invalid=invalid), self.assertRaises(ContractError) as caught:
                sampler.sample()
            self.assertEqual(caught.exception.code, "RESOURCE_PROCESS_ELAPSED_CLOCK_INVALID")
            self.assertEqual(port.calls, 0)

    def test_invalid_clock_after_currentness_clears_old_baseline_and_cached_frame(self):
        now, elapsed, port, sampler = self.fixture()
        sampler.sample()
        def current(identity):
            now[0] = True
            return True
        with patch.object(port, "resource_observation_current", side_effect=current), self.assertRaises(ContractError):
            sampler.sample()
        self.assertIsNone(sampler._cpu_baseline)
        self.assertIsNone(sampler._cached)
        now[0], elapsed[0] = 110, 1010
        self.assertEqual(sampler.sample().cpu_milli.reason, "PROCESS_CPU_BASELINE_REQUIRED")

    def test_cached_eligibility_is_rechecked_after_currentness_using_elapsed_time(self):
        now, elapsed, port, sampler = self.fixture(interval=50, window=100)
        first = sampler.sample()
        elapsed[0] = 1040
        def current(identity):
            now[0], elapsed[0] = 101, 1060
            return True
        with patch.object(port, "resource_observation_current", side_effect=current):
            fresh = sampler.sample()
        self.assertIsNot(fresh, first)
        self.assertEqual((port.calls, fresh.source.sequence, fresh.observed_monotonic_ns), (2, 2, 101))

    def test_cache_minimum_interval_is_not_extended_by_coarse_clock(self):
        now, elapsed, port, sampler = self.fixture(interval=50, window=100)
        first = sampler.sample()
        now[0], elapsed[0] = 101, 1049
        self.assertIs(sampler.sample(), first)
        now[0], elapsed[0] = 102, 1050
        self.assertEqual(sampler.sample().source.sequence, 2)
        self.assertEqual(port.calls, 2)

    def test_quantization_margin_can_disqualify_a_cache_before_public_age_expiry(self):
        now, elapsed, port, sampler = self.fixture(interval=90, window=100, resolution=5)
        first = sampler.sample()
        now[0], elapsed[0] = 196, 1040
        fresh = sampler.sample()
        self.assertIsNot(fresh, first)
        self.assertEqual((port.calls, fresh.memory_bytes.measured), (2, True))
        self.assertEqual(fresh.cpu_milli.reason, "PROCESS_CPU_BASELINE_REQUIRED")

    def test_old_frame_inside_quantization_margin_remains_unavailable(self):
        now, elapsed, port, sampler = self.fixture(age=100, resolution=5)
        port.next = counters(4)
        self.assertEqual(sampler.sample().cpu_milli.reason, "PROCESS_OBSERVATION_STALE_OR_FUTURE")

    def test_age_bound_smaller_than_clock_resolution_does_not_claim_a_measurement(self):
        now, elapsed, port, sampler = self.fixture(age=20, window=20, resolution=21)
        result = sampler.sample()
        self.assertEqual(result.cpu_milli.reason, "PROCESS_OBSERVATION_STALE_OR_FUTURE")
        self.assertFalse(result.memory_bytes.measured)

    def test_future_frame_stays_rejected_with_elapsed_clock_enabled(self):
        now, elapsed, port, sampler = self.fixture(resolution=5)
        port.next = counters(101)
        self.assertEqual(sampler.sample().cpu_milli.reason, "PROCESS_OBSERVATION_STALE_OR_FUTURE")

    def test_cpu_rate_uses_precise_elapsed_window_without_changing_public_timestamp(self):
        now, elapsed, port, sampler = self.fixture(age=1_000_000_000, window=100, interval=1)
        sampler.sample()
        now[0], elapsed[0] = 100_000_100, 200_001_000
        port.next = counters(now[0], cpu=2_000_100)
        result = sampler.sample()
        self.assertEqual((result.cpu_milli.value, result.cpu_milli.observed_monotonic_ns), (1000, now[0]))

    def test_elapsed_cpu_window_expiry_requires_a_new_baseline_even_with_fresh_public_frame(self):
        now, elapsed, port, sampler = self.fixture(interval=1)
        sampler.sample()
        now[0], elapsed[0] = 110, 1101
        port.next = counters(110, cpu=200)
        fresh = sampler.sample()
        self.assertEqual(fresh.cpu_milli.reason, "PROCESS_CPU_BASELINE_REQUIRED")
        self.assertTrue(fresh.memory_bytes.measured)
        now[0], elapsed[0] = 120, 1111
        port.next = counters(120, cpu=200)
        self.assertEqual(sampler.sample().cpu_milli.value, 0)

    def test_coarse_cpu_window_quantization_margin_requires_new_baseline(self):
        now, elapsed, port, sampler = self.fixture(interval=1, resolution=5)
        sampler.sample()
        now[0], elapsed[0] = 196, 1090
        self.assertEqual(sampler.sample().cpu_milli.reason, "PROCESS_CPU_BASELINE_REQUIRED")

    def test_currentness_and_counter_control_exceptions_propagate_and_invalidate_cache(self):
        for operation in ("resource_observation_current", "resource_counters"):
            for exception in (KeyboardInterrupt("timing-interruption"), SystemExit(7)):
                now, elapsed, port, sampler = self.fixture()
                sampler.sample()
                now[0], elapsed[0] = 110, 1010
                with self.subTest(operation=operation, exception=type(exception).__name__), patch.object(port, operation, side_effect=exception), self.assertRaises(type(exception)) as caught:
                    sampler.sample()
                self.assertIs(caught.exception, exception)
                self.assertIsNone(sampler._cached)
                now[0], elapsed[0] = 120, 1020
                self.assertEqual(sampler.sample().cpu_milli.reason, "PROCESS_CPU_BASELINE_REQUIRED")

    def test_elapsed_clock_control_exception_is_not_swallowed(self):
        now, elapsed, port, sampler = self.fixture()
        sampler.sample()
        interruption = KeyboardInterrupt("precise-clock-interruption")
        sampler._elapsed_clock = lambda: (_ for _ in ()).throw(interruption)
        with self.assertRaises(KeyboardInterrupt) as caught:
            sampler.sample()
        self.assertIs(caught.exception, interruption)
        self.assertIsNone(sampler._cached)

    def test_currentness_oserror_clears_rate_and_recovery_preserves_sequence(self):
        now, elapsed, port, sampler = self.fixture()
        first = sampler.sample()
        now[0], elapsed[0] = 110, 1010
        with patch.object(port, "resource_observation_current", side_effect=OSError("owned-query-fault")):
            denied = sampler.sample()
        self.assertEqual(denied.cpu_milli.reason, "PROCESS_QUERY_FAILED")
        now[0], elapsed[0] = 120, 1020
        recovered = sampler.sample()
        self.assertEqual(recovered.cpu_milli.reason, "PROCESS_CPU_BASELINE_REQUIRED")
        self.assertEqual([first.source.sequence, denied.source.sequence, recovered.source.sequence], [1, 2, 3])

    def test_cancellation_does_not_query_owner_and_recovery_restarts_rate(self):
        now, elapsed, port, sampler = self.fixture()
        sampler.sample()
        now[0], elapsed[0] = 110, 1010
        with patch.object(port, "resource_observation_current", side_effect=AssertionError("must not query")):
            result = sampler.sample(cancelled=True)
        self.assertEqual(result.cpu_milli.reason, "PROCESS_OBSERVATION_CANCELLED")
        now[0], elapsed[0] = 120, 1020
        self.assertEqual(sampler.sample().cpu_milli.reason, "PROCESS_CPU_BASELINE_REQUIRED")

    def test_counter_high_water_survives_elapsed_failures(self):
        now, elapsed, port, sampler = self.fixture()
        sampler.sample()
        now[0], elapsed[0] = 110, 999
        sampler.sample()
        now[0], elapsed[0] = 120, 1020
        port.next = counters(120, read=99)
        self.assertEqual(sampler.sample().cpu_milli.reason, "PROCESS_COUNTER_ROLLBACK")

    def test_coherent_duplicate_cache_preserves_observation_identity(self):
        now, elapsed, port, sampler = self.fixture()
        first = sampler.sample()
        for stamp in (1001, 1005, 1009):
            elapsed[0] = stamp
            self.assertIs(sampler.sample(), first)
        self.assertEqual((port.calls, first.source.sequence), (1, 1))

    def test_concurrent_elapsed_reads_and_retention_are_serialized(self):
        now, elapsed, port, sampler = self.fixture(interval=500, age=1000, window=500)
        access = threading.Lock()
        def precise():
            if not access.acquire(blocking=False):
                raise AssertionError("clock read outside owner lock")
            try:
                time.sleep(0.0001)
                elapsed[0] += 1
                return elapsed[0]
            finally:
                access.release()
        sampler._elapsed_clock = precise
        recorder, failures, samples = ResourceTelemetryRecorder(maximum_samples=2), [], []
        def collect():
            try:
                samples.append(sampler.collect(recorder))
            except BaseException as error:
                failures.append(error)
        threads = [threading.Thread(target=collect) for _ in range(16)]
        for thread in threads: thread.start()
        for thread in threads: thread.join(5)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(failures, [])
        self.assertEqual((port.calls, len(samples), len(recorder.recent(now_monotonic_ns=100, maximum_age_ns=1000, scope_digest=digest("scope")))), (1, 16, 1))
        self.assertTrue(all(sample is samples[0] for sample in samples))

    def test_custom_declared_clock_keeps_existing_domain_and_rate_semantics(self):
        now = [100]
        port = CounterPort(now)
        sampler = OwnedProcessTelemetrySampler(port, IDENTITY, scope_digest=digest("scope"),
            environment_digest=digest("environment"), workload_digest=digest("workload"), source_generation=4,
            clock=lambda: now[0], minimum_interval_ns=1, maximum_age_ns=100, maximum_probe_window_ns=30)
        sampler.sample()
        now[0], port.next = 110, counters(110, cpu=101)
        self.assertEqual(sampler.sample().cpu_milli.value, 10_000)
        self.assertIsNone(sampler._elapsed_clock)


def spin_ns(duration):
    begin = time.perf_counter_ns()
    while time.perf_counter_ns() - begin < duration:
        pass


class NativeProcessObservationTimingTests(unittest.TestCase):
    setUp, tearDown = jobs.WindowsJobTests.setUp, jobs.WindowsJobTests.tearDown
    until, event, launch, simple = jobs.WindowsJobTests.until, jobs.WindowsJobTests.event, jobs.WindowsJobTests.launch, jobs.WindowsJobTests.simple

    def sampler(self, process, *, interval=1_000_000, age=1_000_000_000, window=100_000_000):
        return OwnedProcessTelemetrySampler(process, process.resource_identity,
            scope_digest=digest("native-scope"), environment_digest=digest("native-environment"),
            workload_digest=digest(WORKLOAD), source_generation=1,
            minimum_interval_ns=interval, maximum_age_ns=age, maximum_probe_window_ns=window)

    def settle(self, process, release):
        release.signal()
        self.assertTrue(process.wait(5))
        self.until(lambda: process.active_process_count() == 0)
        NATIVE_OBSERVATIONS.append({"pid": process.pid, "creation_time": process.creation_time,
            "exit_code": process.poll(), "active_job_members": process.active_process_count()})

    def test_actual_currentness_delay_rejects_each_fresh_sub_tick_trial(self):
        process, release, _ = self.simple()
        real = process.resource_observation_current
        def delayed(identity):
            result = real(identity)
            spin_ns(6_000_000)
            return result
        try:
            with patch.object(process, "resource_observation_current", side_effect=delayed):
                for attempt in range(8):
                    sampler = self.sampler(process, window=5_000_000)
                    tick, begin = time.monotonic_ns(), time.perf_counter_ns()
                    sample = sampler.sample()
                    elapsed = time.perf_counter_ns() - begin
                    NATIVE_OBSERVATIONS.append({"case": "currentness", "attempt": attempt,
                        "pid": process.pid, "creation_time": process.creation_time, "elapsed_ns": elapsed,
                        "public_delta_ns": time.monotonic_ns() - tick, "bound_ns": 5_000_000,
                        "reason": sample.cpu_milli.reason, "memory_measured": sample.memory_bytes.measured})
                    self.assertGreater(elapsed, 5_000_000)
                    self.assertEqual(sample.cpu_milli.reason, "PROCESS_PROBE_TOO_SLOW")
                    self.assertFalse(sample.memory_bytes.measured)
        finally:
            self.settle(process, release)

    def test_actual_counter_delay_rejects_real_frame_after_slow_return(self):
        process, release, _ = self.simple()
        sampler = self.sampler(process, window=30_000_000)
        real = process.resource_counters
        calls = []
        def delayed():
            result = real()
            calls.append(result.observed_monotonic_ns)
            spin_ns(40_000_000)
            return result
        try:
            begin = time.perf_counter_ns()
            with patch.object(process, "resource_counters", side_effect=delayed):
                sample = sampler.sample()
            elapsed = time.perf_counter_ns() - begin
            self.assertGreater(elapsed, 30_000_000)
            self.assertEqual(len(calls), 1)
            self.assertEqual(sample.cpu_milli.reason, "PROCESS_PROBE_TOO_SLOW")
            NATIVE_OBSERVATIONS.append({"case": "counter-return", "pid": process.pid,
                "creation_time": process.creation_time, "elapsed_ns": elapsed, "bound_ns": 30_000_000,
                "actual_counter_calls": len(calls), "reason": sample.cpu_milli.reason})
        finally:
            self.settle(process, release)

    def test_actual_delayed_currentness_invalidates_cache_and_restarts_cpu_baseline(self):
        process, release, _ = self.simple()
        sampler = self.sampler(process, interval=20_000_000, window=20_000_000)
        first = sampler.sample()
        self.assertTrue(first.memory_bytes.measured)
        real = process.resource_observation_current
        def delayed(identity):
            result = real(identity)
            spin_ns(60_000_000)
            return result
        try:
            with patch.object(process, "resource_observation_current", side_effect=delayed):
                rejected = sampler.sample()
            self.assertEqual(rejected.cpu_milli.reason, "PROCESS_PROBE_TOO_SLOW")
            self.assertFalse(rejected.memory_bytes.measured)
            fresh = sampler.sample()
            self.assertEqual(fresh.cpu_milli.reason, "PROCESS_CPU_BASELINE_REQUIRED")
            self.assertTrue(fresh.memory_bytes.measured)
            NATIVE_OBSERVATIONS.append({"case": "cache-recovery", "pid": process.pid,
                "creation_time": process.creation_time, "sequences": [first.source.sequence, rejected.source.sequence, fresh.source.sequence]})
        finally:
            self.settle(process, release)

    def test_actual_quantization_limit_stays_unavailable_for_sub_resolution_age(self):
        process, release, _ = self.simple()
        sampler = self.sampler(process, interval=1, age=1_000_000, window=1_000_000)
        try:
            sample = sampler.sample()
            self.assertGreater(sampler._clock_resolution, 1_000_000)
            self.assertFalse(sample.memory_bytes.measured)
            self.assertIn(sample.cpu_milli.reason, {"PROCESS_OBSERVATION_STALE_OR_FUTURE", "PROCESS_PROBE_TOO_SLOW"})
            NATIVE_OBSERVATIONS.append({"case": "resolution", "pid": process.pid, "creation_time": process.creation_time,
                "clock_resolution_ns": sampler._clock_resolution, "maximum_age_ns": 1_000_000, "reason": sample.cpu_milli.reason})
        finally:
            self.settle(process, release)

    def test_actual_interruption_keeps_child_and_fresh_measurement_recovery(self):
        process, release, _ = self.simple()
        sampler = self.sampler(process)
        sampler.sample()
        interruption = KeyboardInterrupt("owned-native-timing-interruption")
        try:
            with patch.object(process, "resource_observation_current", side_effect=interruption), self.assertRaises(KeyboardInterrupt) as caught:
                sampler.sample()
            self.assertIs(caught.exception, interruption)
            self.assertTrue(process.resource_observation_current(process.resource_identity))
            time.sleep(0.025)
            fresh = sampler.sample()
            self.assertEqual(fresh.cpu_milli.reason, "PROCESS_CPU_BASELINE_REQUIRED")
            self.assertTrue(fresh.memory_bytes.measured)
            NATIVE_OBSERVATIONS.append({"case": "interruption-recovery", "pid": process.pid,
                "creation_time": process.creation_time, "source_sequence": fresh.source.sequence,
                "child_current_after_interruption": True})
        finally:
            self.settle(process, release)

    def test_actual_owned_workload_retention_and_measurable_analysis(self):
        ready, work, done, release = (self.event() for _ in range(4))
        process = self.launch(("-B", "-I", "-c", WORKLOAD, ready.name, work.name, done.name,
                              release.name, str(self.directory / "gd1-owned-io.bin")))
        ready.wait()
        sampler, recorder = self.sampler(process), ResourceTelemetryRecorder(maximum_samples=2)
        try:
            first = sampler.collect(recorder)
            work.signal()
            done.wait()
            second = sampler.collect(recorder)
            self.assertTrue(second.cpu_milli.measured)
            self.assertGreater(second.cpu_milli.value, 0)
            self.assertTrue(second.memory_bytes.measured)
            retained = recorder.recent(now_monotonic_ns=time.monotonic_ns(), maximum_age_ns=1_000_000_000, scope_digest=digest("native-scope"))
            self.assertEqual([sample.source.sequence for sample in retained], [1, 2])
            analysis = PerformanceDiagnostics().analyze_process_current(retained, PerformanceEnvelope(1000, 100000, 2**40),
                now_monotonic_ns=time.monotonic_ns(), maximum_age_ns=1_000_000_000,
                scope_digest=digest("native-scope"), environment_digest=digest("native-environment"))
            self.assertEqual(analysis.measurement_state, "MEASURED_PROCESS_USAGE")
            self.assertGreater(analysis.write_io_bytes, 0)
            NATIVE_OBSERVATIONS.append({"case": "workload", "pid": process.pid, "creation_time": process.creation_time,
                "workload_digest": digest(WORKLOAD), "before_cpu_time_100ns": first.process_usage.cpu_time_100ns.value,
                "after_cpu_time_100ns": second.process_usage.cpu_time_100ns.value, "sampled_cpu_milli": second.cpu_milli.value,
                "before_memory_bytes": first.memory_bytes.value, "after_memory_bytes": second.memory_bytes.value,
                "write_io_delta": analysis.write_io_bytes, "analysis_state": analysis.measurement_state,
                "findings": list(analysis.findings)})
        finally:
            self.settle(process, release)
