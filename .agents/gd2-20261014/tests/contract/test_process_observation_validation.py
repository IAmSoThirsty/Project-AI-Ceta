"""Exact seven independent oracles retained; no native observation claim."""
import unittest
from unittest.mock import patch
from ceta.resource.diagnostics import ResourceTelemetryRecorder
from ceta.contracts.wire import ContractError
from test_process_observation_timing import ProcessObservationTimingTests
from test_process_diagnostics import counters
import test_process_observation_timing as timing
from ceta.contracts.resource_management import ObservationState
from ceta.resource.diagnostics import PerformanceDiagnostics, PerformanceEnvelope
from test_process_diagnostics import digest
observations = []

class IndependentTimingBoundaryTests(unittest.TestCase):
    fixture = ProcessObservationTimingTests.fixture

    def test_after_public_precise_rollback_keeps_both_high_waters(self):
        now, elapsed, port, sampler = self.fixture()
        sampler.sample()
        now[0] = 110
        sequence = iter((1020, 1019))
        sampler._elapsed_clock = lambda: next(sequence)
        denied = sampler.sample()
        self.assertEqual(denied.cpu_milli.reason, 'PROCESS_CLOCK_ROLLBACK')
        self.assertEqual((sampler._last_clock, sampler._last_elapsed, port.calls), (110, 1020, 1))
        sampler._elapsed_clock = lambda: elapsed[0]
        for stamp in (1018, 1019):
            now[0], elapsed[0] = now[0] + 1, stamp
            self.assertFalse(sampler.sample().memory_bytes.measured)
            self.assertEqual(sampler._last_elapsed, 1020)
        now[0], elapsed[0] = 120, 1030
        self.assertEqual(sampler.sample().cpu_milli.reason, 'PROCESS_CPU_BASELINE_REQUIRED')
        observations.append({'case': 'asymmetric_precise_rollback', 'retained_public_high_water': sampler._last_clock,
            'retained_precise_high_water': sampler._last_elapsed, 'counter_calls': port.calls})

    def test_precise_read_exception_does_not_reset_public_high_water(self):
        now, elapsed, port, sampler = self.fixture()
        sampler.sample()
        now[0] = 110
        interruption = SystemExit(19)
        calls = [0]
        def elapsed_read():
            calls[0] += 1
            if calls[0] == 2: raise interruption
            return 1020
        sampler._elapsed_clock = elapsed_read
        with self.assertRaises(SystemExit) as caught: sampler.sample()
        self.assertIs(caught.exception, interruption)
        self.assertEqual((sampler._last_clock, sampler._last_elapsed), (110, 1020))
        self.assertIsNone(sampler._cached)
        sampler._elapsed_clock = lambda: elapsed[0]
        now[0], elapsed[0] = 109, 1030
        self.assertEqual(sampler.sample().cpu_milli.reason, 'PROCESS_CLOCK_ROLLBACK')
        now[0], elapsed[0] = 120, 1040
        self.assertEqual(sampler.sample().cpu_milli.reason, 'PROCESS_CPU_BASELINE_REQUIRED')

    def test_final_public_clock_lookup_time_invalidates_counter_frame(self):
        now, elapsed, port, sampler = self.fixture()
        sampler.sample()
        original_bounds = (sampler._accepted_time, tuple(sampler._counter_high_water))
        now[0], elapsed[0] = 110, 1010
        calls = [0]
        def public():
            calls[0] += 1
            if calls[0] == 3: elapsed[0] += 31
            return now[0]
        sampler._clock = public
        denied = sampler.sample()
        self.assertEqual(denied.cpu_milli.reason, 'PROCESS_PROBE_TOO_SLOW')
        self.assertEqual((sampler._accepted_time, tuple(sampler._counter_high_water)), original_bounds)
        self.assertIsNone(denied.process_usage)
        self.assertEqual(port.calls, 2)

    def test_unaccepted_large_counter_does_not_poison_accepted_counter_high_water(self):
        now, elapsed, port, sampler = self.fixture()
        sampler.sample()
        now[0], elapsed[0] = 110, 1010
        def slow_large_frame():
            elapsed[0] += 31
            return counters(110, cpu=9999, read=9999, write=9999)
        with patch.object(port, 'resource_counters', side_effect=slow_large_frame):
            denied = sampler.sample()
        self.assertEqual(denied.cpu_milli.reason, 'PROCESS_PROBE_TOO_SLOW')
        self.assertEqual(tuple(sampler._counter_high_water), (100, 100, 50))
        now[0], elapsed[0] = 120, 1050
        recovered = sampler.sample()
        self.assertTrue(recovered.memory_bytes.measured)
        self.assertEqual(recovered.cpu_milli.reason, 'PROCESS_CPU_BASELINE_REQUIRED')

    def test_recorder_delay_never_extends_cached_frame_lifetime(self):
        now, elapsed, port, sampler = self.fixture(interval=50, age=200, window=100)
        recorder = ResourceTelemetryRecorder(maximum_samples=2)
        original = recorder.record
        def late_retention(frame):
            elapsed[0] += 75
            return original(frame)
        with patch.object(recorder, 'record', side_effect=late_retention): first = sampler.collect(recorder)
        now[0] = 101
        second = sampler.collect(recorder)
        self.assertIsNot(second, first)
        self.assertEqual((first.source.sequence, second.source.sequence, port.calls), (1, 2, 2))

    def test_quantization_cache_age_boundary_is_inclusive_then_reprobed(self):
        now, elapsed, port, sampler = self.fixture(interval=90, age=100, window=100, resolution=5)
        first = sampler.sample()
        now[0], elapsed[0] = 195, 1040
        self.assertIs(sampler.sample(), first)
        now[0], elapsed[0] = 196, 1041
        refreshed = sampler.sample()
        self.assertIsNot(refreshed, first)
        self.assertEqual((port.calls, refreshed.cpu_milli.reason, refreshed.memory_bytes.measured),
                         (2, 'PROCESS_CPU_BASELINE_REQUIRED', True))

    def test_malformed_frame_interrupts_cache_without_erasing_accepted_bounds(self):
        now, elapsed, port, sampler = self.fixture()
        sampler.sample()
        original_bounds = sampler._accepted_time, tuple(sampler._counter_high_water)
        bad = counters(110)
        object.__setattr__(bad.usage.cpu_time_100ns, 'value', True)
        now[0], elapsed[0], port.next = 110, 1010, bad
        with self.assertRaises(ContractError): sampler.sample()
        self.assertIsNone(sampler._cached)
        self.assertEqual((sampler._accepted_time, tuple(sampler._counter_high_water)), original_bounds)
        now[0], elapsed[0], port.next = 120, 1020, counters(120)
        self.assertEqual(sampler.sample().cpu_milli.reason, 'PROCESS_CPU_BASELINE_REQUIRED')

# Retain the fixture function without duplicate imported TestCase discovery.
del ProcessObservationTimingTests

class NestedMeasurementValidationTests(unittest.TestCase):
    fixture = timing.ProcessObservationTimingTests.fixture

    @staticmethod
    def quantities(frame):
        return (frame.working_set_bytes, frame.usage.cpu_time_100ns,
                frame.usage.private_bytes, frame.usage.read_io_bytes,
                frame.usage.write_io_bytes)

    def test_all_five_invalid_values_are_rejected_before_first_state_adoption(self):
        for index in range(5):
            for invalid in (True, False, -1, 2**63, 1.0, "100", None):
                with self.subTest(index=index, invalid=invalid):
                    now, elapsed, port, sampler = self.fixture()
                    frame = counters(now[0])
                    object.__setattr__(self.quantities(frame)[index], "value", invalid)
                    port.next = frame
                    with self.assertRaises(ContractError) as caught:
                        sampler.sample()
                    self.assertEqual(caught.exception.code, "RESOURCE_MEASUREMENT_INVALID")
                    self.assertEqual((sampler._accepted_time, sampler._sequence), (-1, 0))
                    self.assertEqual(sampler._counter_high_water, [None, None, None])
                    self.assertIsNone(sampler._cached)
                    self.assertIsNone(sampler._cpu_baseline)
                    self.assertIsNone(sampler._cpu_elapsed_baseline)

    def test_nested_state_time_method_and_reason_reject_before_retention(self):
        changes = (("state", "MEASURED"), ("observed_monotonic_ns", True),
                   ("method", ""), ("method", 1), ("reason", "not-a-measurement"),
                   ("state", ObservationState.UNAVAILABLE))
        for index in range(5):
            for field, invalid in changes:
                with self.subTest(index=index, field=field, invalid=invalid):
                    now, elapsed, port, sampler = self.fixture()
                    recorder = ResourceTelemetryRecorder(maximum_samples=2)
                    frame = counters(now[0])
                    object.__setattr__(self.quantities(frame)[index], field, invalid)
                    port.next = frame
                    with self.assertRaises(ContractError):
                        sampler.collect(recorder)
                    self.assertEqual(sampler._sequence, 0)
                    self.assertEqual(sampler._accepted_time, -1)
                    self.assertEqual(recorder.recent(now_monotonic_ns=100,
                        maximum_age_ns=100, scope_digest=digest("scope")), ())
                    self.assertEqual(recorder._retained_payloads, {})

    def test_malformed_later_quantities_preserve_bounds_then_restart_cpu_baseline(self):
        for index in range(5):
            with self.subTest(index=index):
                now, elapsed, port, sampler = self.fixture()
                sampler.sample()
                accepted = sampler._accepted_time, tuple(sampler._counter_high_water)
                now[0], elapsed[0] = 110, 1010
                frame = counters(110, cpu=100_000, read=100_000, write=100_000)
                object.__setattr__(self.quantities(frame)[index], "value", True)
                port.next = frame
                with self.assertRaises(ContractError):
                    sampler.sample()
                self.assertEqual((sampler._accepted_time, tuple(sampler._counter_high_water)), accepted)
                self.assertEqual(sampler._sequence, 1)
                self.assertIsNone(sampler._cached)
                self.assertIsNone(sampler._cpu_baseline)
                now[0], elapsed[0], port.next = 120, 1020, counters(120, cpu=110)
                baseline = sampler.sample()
                self.assertEqual((baseline.source.sequence, baseline.cpu_milli.reason),
                                 (2, "PROCESS_CPU_BASELINE_REQUIRED"))
                now[0], elapsed[0], port.next = 130, 1030, counters(130, cpu=120)
                self.assertEqual(sampler.sample().cpu_milli.value, 100_000)

    def test_unavailable_observations_and_measured_zero_remain_distinct(self):
        now, elapsed, port, sampler = self.fixture()
        unavailable = counters(100)
        for observation in self.quantities(unavailable):
            object.__setattr__(observation, "state", ObservationState.UNAVAILABLE)
            object.__setattr__(observation, "value", None)
            object.__setattr__(observation, "reason", "NOT_OBSERVED")
        port.next = unavailable
        first = sampler.sample()
        self.assertFalse(first.memory_bytes.measured)
        self.assertIsNone(first.memory_bytes.value)
        self.assertEqual(sampler._counter_high_water, [None, None, None])
        now[0], elapsed[0], port.next = 110, 1010, counters(110, cpu=0, memory=0, private=0, read=0, write=0)
        baseline = sampler.sample()
        self.assertTrue(baseline.memory_bytes.measured)
        self.assertEqual(baseline.memory_bytes.value, 0)
        self.assertEqual(baseline.cpu_milli.reason, "PROCESS_CPU_BASELINE_REQUIRED")
        now[0], elapsed[0], port.next = 120, 1020, counters(120, cpu=0, memory=0, private=0, read=0, write=0)
        zero = sampler.sample()
        self.assertTrue(zero.cpu_milli.measured)
        self.assertEqual(zero.cpu_milli.value, 0)
        self.assertEqual(sampler._counter_high_water, [0, 0, 0])

    def test_invalid_first_frame_cannot_create_false_later_measured_analysis(self):
        now, elapsed, port, sampler = self.fixture()
        recorder = ResourceTelemetryRecorder(maximum_samples=2)
        frame = counters(100)
        object.__setattr__(frame.usage.cpu_time_100ns, "value", True)
        port.next = frame
        with self.assertRaises(ContractError):
            sampler.collect(recorder)
        now[0], elapsed[0], port.next = 110, 1010, counters(110, cpu=100)
        baseline = sampler.collect(recorder)
        self.assertEqual((baseline.source.sequence, baseline.cpu_milli.reason),
                         (1, "PROCESS_CPU_BASELINE_REQUIRED"))
        now[0], elapsed[0], port.next = 120, 1020, counters(120, cpu=100)
        self.assertEqual(sampler.collect(recorder).cpu_milli.value, 0)
        retained = recorder.recent(now_monotonic_ns=120, maximum_age_ns=100,
                                   scope_digest=digest("scope"))
        analysis = PerformanceDiagnostics().analyze_process_current(retained,
            PerformanceEnvelope(100, 1000, 10_000), now_monotonic_ns=120,
            maximum_age_ns=100, scope_digest=digest("scope"),
            environment_digest=digest("environment"))
        self.assertEqual([sample.source.sequence for sample in retained], [1, 2])
        self.assertEqual(analysis.measurement_state, "MEASURED_PROCESS_USAGE")
        self.assertEqual(analysis.telemetry.peak_cpu_milli, 0)

    def test_unavailable_value_and_reason_mutations_are_rejected_without_order_adoption(self):
        for field, invalid in (("value", 0), ("value", False), ("reason", None),
                               ("reason", ""), ("reason", 42)):
            with self.subTest(field=field, invalid=invalid):
                now, elapsed, port, sampler = self.fixture()
                frame = counters(100)
                observation = frame.usage.read_io_bytes
                object.__setattr__(observation, "state", ObservationState.UNAVAILABLE)
                object.__setattr__(observation, "value", None)
                object.__setattr__(observation, "reason", "NOT_OBSERVED")
                object.__setattr__(observation, field, invalid)
                port.next = frame
                with self.assertRaises(ContractError) as caught:
                    sampler.sample()
                self.assertEqual(caught.exception.code, "RESOURCE_UNAVAILABLE_INVALID")
                self.assertEqual((sampler._accepted_time, sampler._sequence), (-1, 0))
                self.assertEqual(sampler._counter_high_water, [None, None, None])
        observations.append({'case': 'asymmetric_precise_rollback', 'retained_public_high_water': sampler._last_clock,
            'retained_precise_high_water': sampler._last_elapsed, 'counter_calls': port.calls})
