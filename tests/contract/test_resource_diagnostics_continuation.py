"""CETA-20.05.02 process-window regressions; controlled port, no native claims."""
from dataclasses import asdict, replace
import threading
import unittest
from unittest.mock import patch

from ceta.contracts.wire import ContractError
from ceta.resource.diagnostics import PerformanceDiagnostics, PerformanceEnvelope, ResourceTelemetryRecorder
import test_process_diagnostics as fixture


class ProcessWindowContinuationTests(unittest.TestCase):
    def setUp(self):
        self.now, self.port, self.sampler = fixture.ProcessDiagnosticsTests().fixture()
        self.first = self.sampler.sample()
        self.now[0] = 110
        self.port.next = fixture.counters(110, cpu=200, read=600, write=250, private=1200)
        self.last = self.sampler.sample()
        self.engine = PerformanceDiagnostics()
        self.envelope = PerformanceEnvelope(20, 2000, 10000)

    def analyze(self, samples=None, age=100):
        return self.engine.analyze_process_current((self.first, self.last) if samples is None else samples,
            self.envelope, now_monotonic_ns=120, maximum_age_ns=age,
            scope_digest=fixture.digest("scope"), environment_digest=fixture.digest("environment"))

    def rejected(self, samples, code, age=100):
        result = self.analyze(samples, age)
        self.assertEqual(result.measurement_state, "CURRENT_PROCESS_INPUT_REJECTED")
        self.assertIn(code, result.findings)
        self.assertEqual((result.read_io_bytes, result.write_io_bytes, result.peak_private_bytes), (None, None, None))

    def test_01_09_real_sampler_recorder_analysis_retains_numeric_facts(self):
        """AT-CETA-20.05.02-01/-02/-09 bounded domain integration, not product qualification."""
        recorder = ResourceTelemetryRecorder(maximum_samples=2)
        recorder.record(self.first)
        self.sampler.collect(recorder)
        retained = recorder.recent(now_monotonic_ns=120, maximum_age_ns=100, scope_digest=fixture.digest("scope"))
        self.assertNotEqual(retained[0].sample_id, self.first.sample_id)
        result = self.analyze(retained)
        self.assertEqual(result.measurement_state, "MEASURED_PROCESS_USAGE")
        self.assertEqual((result.read_io_bytes, result.write_io_bytes, result.peak_private_bytes), (500, 200, 1200))
        self.assertIn("MEASURED_PROCESS_USAGE_NO_CAUSAL_BOTTLENECK_CLAIM", result.findings)
        self.assertFalse(result.telemetry.within_envelope)  # Workload latency remains unobserved.

    def test_07_conflicting_duplicate_identity_never_yields_measured_delta(self):
        self.rejected((self.first, replace(self.last, sample_id=self.first.sample_id)),
                      "PROCESS_SAMPLE_REUSED_OR_DUPLICATED")

    def test_04_counter_timestamps_cannot_precede_or_follow_wrapper(self):
        """Fresh constituent observations still must describe the same probe."""
        for at in (109, 111):
            for name in ("cpu_time_100ns", "private_bytes", "read_io_bytes", "write_io_bytes"):
                with self.subTest(at=at, field=name):
                    usage = self.last.process_usage
                    observation = replace(getattr(usage, name), observed_monotonic_ns=at)
                    usage = replace(usage, window_started_monotonic_ns=109, **{name: observation})
                    self.rejected((self.first, replace(self.last, process_usage=usage)),
                                  "PROCESS_COUNTER_WINDOW_INCOHERENT")
        self.rejected((self.first, replace(self.last, memory_bytes=replace(self.last.memory_bytes, observed_monotonic_ns=111))),
                      "PROCESS_COUNTER_WINDOW_INCOHERENT")

    def test_04_old_probe_start_cannot_hide_behind_fresh_counters(self):
        old = replace(self.last, process_usage=replace(self.last.process_usage, window_started_monotonic_ns=0))
        self.rejected((self.first, old), "PROCESS_COUNTER_WINDOW_STALE_OR_FUTURE", age=30)
        boundary = replace(self.last, process_usage=replace(self.last.process_usage, window_started_monotonic_ns=90))
        self.assertEqual(self.analyze((self.first, boundary), age=30).measurement_state, "MEASURED_PROCESS_USAGE")

    def test_03_reconstructed_nested_boolean_rejected_before_arithmetic(self):
        forged = replace(self.last.process_usage.read_io_bytes)
        object.__setattr__(forged, "value", True)
        changed = replace(self.last, process_usage=replace(self.last.process_usage, read_io_bytes=forged))
        with self.assertRaisesRegex(ContractError, "RESOURCE_MEASUREMENT_INVALID"):
            self.analyze((self.first, changed))

    def test_03_reconstructed_source_generation_is_validated(self):
        source = replace(self.last.source)
        object.__setattr__(source, "source_generation", True)
        with self.assertRaisesRegex(ContractError, "RESOURCE_TELEMETRY_GENERATION_INVALID"):
            self.analyze((self.first, replace(self.last, source=source)))

    def test_06_input_bounds_rejected_before_snapshot_work(self):
        with patch.object(PerformanceDiagnostics, "_copy_process_sample", side_effect=AssertionError("unbounded copy")):
            for samples in ([self.first], (self.first,) * 8193):
                with self.subTest(size=len(samples)), self.assertRaisesRegex(ContractError, "RESOURCE_CURRENT_DIAGNOSTIC_INPUT_INVALID"):
                    self.analyze(samples)

    def test_06_08_interruption_preserves_inputs_and_retry(self):
        before = asdict(self.first), asdict(self.last)
        for primary in (KeyboardInterrupt("copy interrupted"), SystemExit(23)):
            with patch.object(PerformanceDiagnostics, "_copy_process_sample", side_effect=primary):
                with self.assertRaises(type(primary)) as caught:
                    self.analyze()
                self.assertIs(caught.exception, primary)
            self.assertEqual((asdict(self.first), asdict(self.last)), before)
            self.assertEqual(self.analyze().read_io_bytes, 500)

    def test_07_caller_mutation_after_copy_cannot_change_measurements(self):
        original = PerformanceDiagnostics.analyze_current
        target = self.last.process_usage.read_io_bytes
        def mutate_then_analyze(engine, samples, envelope, **context):
            object.__setattr__(target, "value", 2**63 - 1)
            return original(engine, samples, envelope, **context)
        with patch.object(PerformanceDiagnostics, "analyze_current", new=mutate_then_analyze):
            result = self.analyze()
        self.assertEqual(result.read_io_bytes, 500)
        self.assertEqual(target.value, 2**63 - 1)  # The caller owns its original.

    def test_07_caller_envelope_mutation_does_not_change_snapshot(self):
        original = PerformanceDiagnostics.analyze_current
        target = self.envelope
        def mutate_then_analyze(engine, samples, envelope, **context):
            object.__setattr__(target, "maximum_memory_bytes", 0)
            return original(engine, samples, envelope, **context)
        with patch.object(PerformanceDiagnostics, "analyze_current", new=mutate_then_analyze):
            result = self.analyze()
        self.assertNotIn("MEMORY_PEAK_EXCEEDED", result.telemetry.findings)
        self.assertEqual(target.maximum_memory_bytes, 0)

    def test_07_concurrent_computation_keeps_source_and_results_identical(self):
        before = asdict(self.first), asdict(self.last)
        barrier = threading.Barrier(8)
        outputs, failures = [], []
        def run():
            try:
                barrier.wait(timeout=5)
                outputs.append(self.analyze())
            except BaseException as error:
                failures.append(error)
        threads = [threading.Thread(target=run) for _ in range(8)]
        for thread in threads: thread.start()
        for thread in threads:
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
        self.assertEqual(failures, [])
        self.assertEqual(len(outputs), 8)
        self.assertTrue(all(item == outputs[0] for item in outputs))
        self.assertEqual((asdict(self.first), asdict(self.last)), before)

    def test_04_08_rejection_does_not_poison_fresh_reconstruction(self):
        self.rejected((self.first, replace(self.last, source=replace(self.last.source, source_generation=5))),
                      "PROCESS_SOURCE_MIXED")
        rebuilt = tuple(self.engine._copy_process_sample(x) for x in (self.first, self.last))
        self.assertEqual(self.analyze(rebuilt), self.analyze())
        self.assertEqual(self.analyze(rebuilt).read_io_bytes, 500)


if __name__ == "__main__":
    unittest.main()
