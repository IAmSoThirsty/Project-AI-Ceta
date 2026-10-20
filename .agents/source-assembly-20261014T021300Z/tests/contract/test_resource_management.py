"""Executable resource-domain, Windows-observation and recovery-boundary tests."""
from dataclasses import replace
from pathlib import Path
import hashlib
from types import SimpleNamespace
import sys
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ceta.contracts.resource_management import (
    AdmissionState, BudgetEnvelope, CapacitySnapshot, HardwareProfile, ObservationState, PressureLevel,
    QuantityObservation, ReservationResult, ResourceKind, ResourceVector, TelemetrySample, TelemetrySourceBinding,
)
from ceta.contracts.temporal import ClockSample, Deadline
from ceta.contracts.wire import ContractError
from ceta.resource.admission import (
    AdmissionRequest, MeasuredWorkloadProfile, ObservedWorkloadUsage, WorkloadAdmissionController, WorkloadEstimate,
    WorkloadRequirementEstimator, assess_budget, plan_concurrency, plan_concurrency_with_facts,
)
from ceta.resource.budget import (
    ChildBudgetRequest, ComputeBudgetController, ExecutionTimeBudgetController, MemoryBudgetController,
)
from ceta.resource.diagnostics import (
    CurrentComparisonContext, PerformanceDiagnostics, PerformanceEnvelope, ResourceTelemetryRecorder, WorkloadComparisonInput,
)
from ceta.resource.inference import assess_input_context, measure_input_tokens
from ceta.resource.hardware import (
    SamplingPolicy, StorageCapacityMonitor, WindowsComputeAvailabilityMonitor, WindowsHardwareProfiler,
    available_capacity,
)
from ceta.resource.pressure import (
    DegradationRequest, GracefulDegradationCoordinator, PressureThresholds, ReducedResourceMode,
    ResourcePressureDetector, TaskAuthorityBinding, ThrottleRequest, WorkloadThrottlingController,
)
from test_request_compiler import _CompilerFixture


def q(value, *, at=100, method="fixture"):
    return QuantityObservation(ObservationState.MEASURED, value, at, method)


def unavailable(*, at=100):
    return QuantityObservation(ObservationState.UNAVAILABLE, None, at, "fixture", "NOT_OBSERVED")


def snapshot(kind=ResourceKind.CPU, *, total=1000, free=600, reservable=550, utilization=400, at=100, sequence=1):
    return CapacitySnapshot(kind, q(total, at=at), q(free, at=at), q(reservable, at=at), q(utilization, at=at), sequence)


def digest(text):
    return "sha256:" + hashlib.sha256(text.encode("ascii")).hexdigest()


class FakeReservations:
    def __init__(self, result): self.result, self.requests = result, []
    def reserve(self, request): self.requests.append(request); return self.result


class ResourceContractTests(unittest.TestCase):
    def test_measured_zero_is_distinct_from_unavailable(self):
        zero = q(0)
        self.assertTrue(zero.measured)
        self.assertEqual(zero.value, 0)
        self.assertFalse(unavailable().measured)
        with self.assertRaises(ContractError) as raised:
            QuantityObservation(ObservationState.UNAVAILABLE, 0, 1, "fixture", "x")
        self.assertEqual(raised.exception.code, "RESOURCE_UNAVAILABLE_INVALID")

    def test_capacity_enforces_physical_free_and_reservable_order(self):
        with self.assertRaises(ContractError) as raised:
            snapshot(free=1001)
        self.assertEqual(raised.exception.code, "RESOURCE_FREE_EXCEEDS_TOTAL")
        with self.assertRaises(ContractError) as raised:
            snapshot(reservable=601)
        self.assertEqual(raised.exception.code, "RESOURCE_RESERVABLE_EXCEEDS_FREE")

    def test_stale_or_unavailable_observations_never_supply_capacity(self):
        reservations = ResourceVector(50, 0, 0, 0)
        self.assertIsNone(available_capacity(snapshot(at=100), reservations, 201, 100))
        unavailable_cpu = CapacitySnapshot(ResourceKind.CPU, unavailable(), unavailable(), unavailable(), unavailable(), 2)
        self.assertIsNone(available_capacity(unavailable_cpu, reservations, 100, 100))
        result = available_capacity(snapshot(reservable=50), reservations, 100, 100)
        self.assertEqual(result, 0)

    def test_mixed_age_snapshot_is_stale_and_never_claims_other_dimensions(self):
        mixed = replace(snapshot(at=100), free=q(600, at=1))
        self.assertFalse(mixed.is_recent(150, 100))
        self.assertIsNone(available_capacity(mixed, ResourceVector(0, 0, 0, 0), 150, 100))
        # A CPU snapshot produces a CPU quantity, not a partly fictional vector.
        self.assertEqual(available_capacity(snapshot(reservable=321), ResourceVector(1, 0, 0, 0), 100, 100), 320)

    def test_windows_hardware_profile_is_real_or_explicitly_unavailable(self):
        profile = WindowsHardwareProfiler().profile("r17.profile")
        self.assertIsInstance(profile, HardwareProfile)
        self.assertEqual(profile.cpu.kind, ResourceKind.CPU)
        self.assertFalse(profile.cpu.free.measured)
        self.assertEqual(profile.cpu.free.reason, "AVAILABILITY_REQUIRES_RUNTIME_SAMPLE")
        self.assertIn(profile.memory.total.state, (ObservationState.MEASURED, ObservationState.UNAVAILABLE))
        self.assertIn(profile.storage.total.state, (ObservationState.MEASURED, ObservationState.UNAVAILABLE))
        if profile.memory.total.measured:
            self.assertGreater(profile.memory.total.value, 0)
            self.assertLessEqual(profile.memory.free.value, profile.memory.total.value)

    def test_invalid_hardware_profile_id_is_rejected_before_any_probe(self):
        calls = []
        profiler = WindowsHardwareProfiler(clock=lambda: calls.append("clock") or 1,
                                           accelerator_memory_reader=lambda: calls.append("accelerator") or ())
        with patch("ceta.resource.hardware.os.cpu_count", side_effect=AssertionError("cpu probe invoked")), \
                self.assertRaises(ContractError) as raised:
            profiler.profile("invalid profile id")
        self.assertEqual(raised.exception.code, "RESOURCE_PROFILE_IDENTIFIER_INVALID")
        self.assertEqual(calls, [])

    def test_accelerator_capacity_keeps_runtime_availability_explicitly_unavailable(self):
        profiler = WindowsHardwareProfiler(accelerator_memory_reader=lambda: (0, 8 * 1024**3))
        with patch("ceta.resource.hardware.os.name", "nt"):
            profile = profiler.profile("r17.accelerator")
        self.assertEqual(tuple((item.kind, item.total.value, item.free.state, item.reservable.reason,
                                item.utilization_milli.reason, item.sequence)
                               for item in profile.accelerators),
                         ((ResourceKind.ACCELERATOR, 0, ObservationState.UNAVAILABLE,
                           "ACCELERATOR_RUNTIME_AVAILABILITY_NOT_OBSERVED",
                           "ACCELERATOR_RUNTIME_AVAILABILITY_NOT_OBSERVED", 1),
                          (ResourceKind.ACCELERATOR, 8 * 1024**3, ObservationState.UNAVAILABLE,
                           "ACCELERATOR_RUNTIME_AVAILABILITY_NOT_OBSERVED",
                           "ACCELERATOR_RUNTIME_AVAILABILITY_NOT_OBSERVED", 1)))

    def test_accelerator_discovery_fails_closed_for_probe_failure_or_invalid_result(self):
        for reader, reason in ((lambda: (), "ACCELERATOR_NOT_FOUND"),
                               (lambda: ("not-bytes",), "ACCELERATOR_QUERY_INVALID"),
                               (lambda: (_ for _ in ()).throw(OSError("native failure")), "ACCELERATOR_QUERY_FAILED"),
                               (lambda: (_ for _ in ()).throw(RuntimeError("reader failure")), "ACCELERATOR_QUERY_FAILED")):
            profiler = WindowsHardwareProfiler(accelerator_memory_reader=reader)
            with patch("ceta.resource.hardware.os.name", "nt"):
                accelerator = profiler.profile("r17.accelerator.fail").accelerators[0]
            self.assertEqual((accelerator.total.state, accelerator.total.reason),
                             (ObservationState.UNAVAILABLE, reason))

    def test_accelerator_discovery_does_not_swallow_process_control_exceptions(self):
        profiler = WindowsHardwareProfiler(
            accelerator_memory_reader=lambda: (_ for _ in ()).throw(KeyboardInterrupt()))
        with patch("ceta.resource.hardware.os.name", "nt"), self.assertRaises(KeyboardInterrupt):
            profiler.profile("r17.accelerator.interrupt")

    def test_profile_generation_is_shared_per_profile_and_monotonic_under_concurrency(self):
        profiler = WindowsHardwareProfiler(clock=lambda: 100, accelerator_memory_reader=lambda: (0, 1))
        results = []
        threads = [threading.Thread(target=lambda index=index: results.append(profiler.profile(f"r17.profile.{index}")))
                   for index in range(8)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(sorted(profile.cpu.sequence for profile in results), list(range(1, 9)))
        for profile in results:
            self.assertEqual({item.sequence for item in
                              (profile.cpu, profile.memory, profile.storage, *profile.accelerators)},
                             {profile.cpu.sequence})

    def test_hardware_profile_rejects_swapped_capacity_kinds(self):
        cpu, memory, storage = snapshot(), snapshot(ResourceKind.MEMORY), snapshot(ResourceKind.STORAGE)
        with self.assertRaises(ContractError) as raised:
            HardwareProfile("profile.swapped", memory, cpu, storage, (), q(1), 100, "fixture")
        self.assertEqual(raised.exception.code, "RESOURCE_PROFILE_CAPACITY_KIND_INVALID")
        with self.assertRaises(ContractError) as raised:
            HardwareProfile("profile.accelerator", cpu, memory, storage, (snapshot(),), q(1), 100, "fixture")
        self.assertEqual(raised.exception.code, "RESOURCE_ACCELERATOR_PROFILE_INVALID")

    def test_compute_sampler_baseline_is_not_misreported_as_capacity(self):
        monitor = WindowsComputeAvailabilityMonitor()
        first = monitor.sample()
        self.assertIn(first.reservable.state, (ObservationState.MEASURED, ObservationState.UNAVAILABLE))
        if first.reservable.state is ObservationState.UNAVAILABLE:
            self.assertEqual(first.reservable.reason, "CPU_BASELINE_REQUIRED")
            time.sleep(0.025)
            second = monitor.sample()
            if second.reservable.measured:
                self.assertGreaterEqual(second.reservable.value, 0)
                self.assertLessEqual(second.reservable.value, second.total.value)

    def test_compute_sampling_cache_bounds_native_probe_and_retains_original_timestamp(self):
        now, calls = [0], []
        readings = iter(((100, 50), (200, 120)))
        def read_times(): calls.append("native"); return next(readings)
        monitor = WindowsComputeAvailabilityMonitor(clock=lambda: now[0], processor_count=lambda: 4,
            system_times=read_times, policy=SamplingPolicy(maximum_age_ns=100, minimum_interval_ns=10))
        first = monitor.sample()
        now[0] = 5
        cached = monitor.sample()
        self.assertEqual((len(calls), cached.total.observed_monotonic_ns, cached.sequence), (1, 0, 1))
        now[0] = 10
        refreshed = monitor.sample()
        self.assertEqual((len(calls), refreshed.total.observed_monotonic_ns, refreshed.sequence), (2, 10, 2))
        self.assertTrue(refreshed.reservable.measured)

    def test_compute_failure_attempts_advance_generation_while_cached_failure_does_not(self):
        now, calls = [0], []
        def read_times(): calls.append("native"); return None
        monitor = WindowsComputeAvailabilityMonitor(clock=lambda: now[0], processor_count=lambda: 4,
            system_times=read_times, policy=SamplingPolicy(maximum_age_ns=100, minimum_interval_ns=10))
        first = monitor.sample()
        now[0] = 5
        cached = monitor.sample()
        now[0] = 10
        refreshed = monitor.sample()
        self.assertEqual((first.sequence, cached.sequence, refreshed.sequence, len(calls)), (1, 1, 2, 2))
        self.assertEqual((first.total.reason, refreshed.total.reason), ("CPU_QUERY_FAILED", "CPU_QUERY_FAILED"))

    def test_storage_monitor_distinguishes_real_zero_from_unavailable(self):
        result = StorageCapacityMonitor(path=ROOT).sample()
        self.assertEqual(result.kind, ResourceKind.STORAGE)
        if result.total.measured:
            self.assertGreater(result.total.value, 0)
            self.assertGreaterEqual(result.free.value, 0)

    def test_storage_sampling_cache_bounds_native_probe_and_retains_original_timestamp(self):
        now, calls = [0], []
        def disk_usage(path):
            calls.append(path)
            return SimpleNamespace(total=1000, free=500)
        monitor = StorageCapacityMonitor(path=ROOT, clock=lambda: now[0], disk_usage=disk_usage,
            policy=SamplingPolicy(maximum_age_ns=100, minimum_interval_ns=10))
        first = monitor.sample()
        now[0] = 9
        cached = monitor.sample()
        self.assertEqual((len(calls), cached.total.observed_monotonic_ns, cached.sequence), (1, 0, 1))
        now[0] = 10
        refreshed = monitor.sample()
        self.assertEqual((len(calls), refreshed.total.observed_monotonic_ns, refreshed.sequence), (2, 10, 2))

    def test_storage_failure_and_concurrent_cache_preserve_sequence_semantics(self):
        now, calls = [0], []
        def failed_disk_usage(path):
            calls.append(path)
            raise OSError("unavailable")
        failure = StorageCapacityMonitor(path=ROOT, clock=lambda: now[0], disk_usage=failed_disk_usage,
            policy=SamplingPolicy(maximum_age_ns=100, minimum_interval_ns=10))
        first = failure.sample()
        now[0] = 5
        cached = failure.sample()
        now[0] = 10
        refreshed = failure.sample()
        self.assertEqual((first.sequence, cached.sequence, refreshed.sequence, len(calls)), (1, 1, 2, 2))
        self.assertEqual(refreshed.total.reason, "STORAGE_QUERY_FAILED")
        now[0], calls[:] = 0, []
        monitor = StorageCapacityMonitor(path=ROOT, clock=lambda: now[0],
            disk_usage=lambda path: calls.append(path) or SimpleNamespace(total=1000, free=500),
            policy=SamplingPolicy(maximum_age_ns=100, minimum_interval_ns=10))
        results = []
        threads = [threading.Thread(target=lambda: results.append(monitor.sample())) for _ in range(8)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual((len(calls), {value.sequence for value in results}), (1, {1}))


class PressureTests(unittest.TestCase):
    def binding(self):
        return TaskAuthorityBinding("task.1", digest("task-revision"), 4, digest("authority"))

    def test_critical_closes_admission_then_requires_multiple_low_samples(self):
        detector = ResourcePressureDetector(PressureThresholds(800, 900, 500, 3), clock=lambda: 100)
        critical = detector.observe(snapshot(utilization=950), current=True)
        self.assertEqual((critical.level, critical.admission_open), (PressureLevel.CRITICAL, False))
        for expected in (2, 1):
            decision = detector.observe(snapshot(utilization=400), current=True)
            self.assertEqual(decision.level, PressureLevel.CRITICAL)
            self.assertEqual(decision.recovery_samples_remaining, expected)
        recovered = detector.observe(snapshot(utilization=400), current=True)
        self.assertEqual((recovered.level, recovered.admission_open, recovered.reason),
                         (PressureLevel.NORMAL, True, "RECOVERED_AFTER_HYSTERESIS"))

    def test_missing_or_stale_pressure_observation_is_fail_closed(self):
        detector = ResourcePressureDetector(clock=lambda: 100)
        decision = detector.observe(snapshot(), current=False)
        self.assertEqual((decision.level, decision.admission_open), (PressureLevel.UNKNOWN, False))
        unknown = CapacitySnapshot(ResourceKind.CPU, q(1000), q(500), q(400), unavailable(), 1)
        decision = detector.observe(unknown, current=True)
        self.assertEqual(decision.level, PressureLevel.UNKNOWN)

    def test_stale_pressure_timestamp_closes_even_when_caller_claims_current(self):
        detector = ResourcePressureDetector(clock=lambda: 201, maximum_observation_age_ns=100)
        decision = detector.observe(snapshot(at=100), current=True)
        self.assertEqual((decision.level, decision.admission_open, decision.reason),
                         (PressureLevel.UNKNOWN, False, "OBSERVATION_UNAVAILABLE_OR_STALE"))

    def test_concurrent_observation_preserves_valid_hysteresis_state(self):
        detector = ResourcePressureDetector(PressureThresholds(800, 900, 500, 4), clock=lambda: 100)
        detector.observe(snapshot(utilization=950), current=True)
        failures = []
        def call():
            try: detector.observe(snapshot(utilization=400), current=True)
            except Exception as exc: failures.append(exc)
        threads = [threading.Thread(target=call) for _ in range(4)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertFalse(failures)
        self.assertTrue(detector.observe(snapshot(utilization=400), current=True).admission_open)

    def test_throttling_recommends_only_optional_reduction_with_all_guardrails(self):
        request = ThrottleRequest(self.binding(), PressureLevel.CRITICAL, "CONCURRENCY_LIMIT", 4, 2,
                                  True, True, True, True, 4)
        recommendation = WorkloadThrottlingController().recommend(request)
        self.assertEqual((recommendation.state, recommendation.action, recommendation.proposed_limit),
                         ("RECOMMEND", "CONCURRENCY_LIMIT", 2))
        weakened = WorkloadThrottlingController().recommend(replace(request, preserves_evidence=False))
        self.assertEqual((weakened.state, weakened.reason_codes), ("BLOCKED", ("REQUIRED_GUARDRAIL_WEAKENED",)))
        stale = WorkloadThrottlingController().recommend(replace(request, current_authority_generation=5))
        self.assertEqual(stale.state, "STALE")

    def test_cancelled_throttle_and_degradation_are_idempotent_pure_recommendations(self):
        throttle = ThrottleRequest(self.binding(), PressureLevel.CRITICAL, "CONCURRENCY_LIMIT", 4, 2,
                                   True, True, True, True, 4, cancelled=True)
        controller = WorkloadThrottlingController()
        self.assertEqual(controller.recommend(throttle), controller.recommend(throttle))
        mode = ReducedResourceMode("mode.cancel", digest("cancel-mode"), True, True, True, True, True, False, False)
        request = DegradationRequest(self.binding(), mode, 4, cancelled=True)
        coordinator = GracefulDegradationCoordinator()
        self.assertEqual(coordinator.plan(request), coordinator.plan(request))

    def test_concurrent_pure_throttling_recommendations_do_not_share_state(self):
        request = ThrottleRequest(self.binding(), PressureLevel.ELEVATED, "BATCH_SIZE_LIMIT", 8, 4,
                                  True, True, True, True, 4)
        controller, results = WorkloadThrottlingController(), []
        threads = [threading.Thread(target=lambda: results.append(controller.recommend(request))) for _ in range(8)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(results, [results[0]] * 8)

    def test_degradation_requires_prequalification_and_new_decision_for_changed_scope(self):
        mode = ReducedResourceMode("mode.safe", digest("mode"), True, True, True, True, True, False, True)
        request = DegradationRequest(self.binding(), mode, 4)
        coordinator = GracefulDegradationCoordinator()
        self.assertEqual(coordinator.plan(request).state, "DECISION_REQUIRED")
        unverified = coordinator.plan(replace(request, new_decision_id="decision.1"))
        self.assertEqual((unverified.state, unverified.mode_id, unverified.decision_required),
                         ("DECISION_REQUIRED", None, True))
        self.assertIn("DECISION_CORRELATION_UNVERIFIED", unverified.reason_codes)
        unsafe = coordinator.plan(replace(request, mode=replace(mode, preserves_stop_capacity=False)))
        self.assertEqual(unsafe.state, "BLOCKED")


class DiagnosticTests(unittest.TestCase):
    def sample(self, sample_id, latency=10, cpu=20, memory=100, at=100):
        return TelemetrySample(sample_id, digest("scope"), digest("environment"), at,
                               q(cpu, at=at), q(memory, at=at), q(0, at=at), q(latency, at=at))

    def test_recorder_is_bounded_scoped_and_requires_digested_identity(self):
        recorder = ResourceTelemetryRecorder(maximum_samples=2)
        self.assertEqual(recorder.record(self.sample("sample.1", memory=201)), 0)
        self.assertEqual(recorder.record(self.sample("sample.2", memory=202)), 0)
        self.assertEqual(recorder.record(self.sample("sample.3", memory=203)), 1)
        retained = recorder.recent(now_monotonic_ns=110, maximum_age_ns=20, scope_digest=digest("scope"))
        self.assertEqual(tuple(sample.memory_bytes.value for sample in retained), (202, 203))
        self.assertEqual(len({sample.sample_id for sample in retained}), 2)
        self.assertTrue(all(sample.sample_id.startswith("telemetry:") for sample in retained))
        with self.assertRaises(ContractError) as raised:
            replace(self.sample("sample.4"), scope_digest="user@example.invalid")
        self.assertEqual(raised.exception.code, "RESOURCE_SCOPE_DIGEST_INVALID")
        with self.assertRaises(ContractError) as raised:
            recorder.recent(now_monotonic_ns=100, maximum_age_ns=1, scope_digest="untrusted scope")
        self.assertEqual(raised.exception.code, "RESOURCE_SCOPE_DIGEST_INVALID")

    def test_performance_reports_p95_and_unavailable_metrics(self):
        analyzer = PerformanceDiagnostics()
        samples = tuple(self.sample("sample." + str(index), latency=latency, cpu=40, memory=200)
                        for index, latency in enumerate((2, 3, 4, 5, 99), 1))
        result = analyzer.analyze(samples, PerformanceEnvelope(50, 50, 300))
        self.assertEqual(result.p95_latency_ms, 99)
        self.assertFalse(result.within_envelope)
        self.assertIn("P95_LATENCY_EXCEEDED", result.findings)
        unavailable_latency = replace(samples[0], latency_ms=unavailable())
        uncertain = analyzer.analyze((unavailable_latency,), PerformanceEnvelope(10, 50, 300))
        self.assertFalse(uncertain.within_envelope)
        self.assertIn("LATENCY_UNAVAILABLE", uncertain.findings)

    def test_current_analysis_rejects_stale_future_or_mixed_identity_without_partial_metrics(self):
        analyzer, envelope = PerformanceDiagnostics(), PerformanceEnvelope(50, 300, 400)
        stale = analyzer.analyze_current((self.sample("sample.stale", at=100),), envelope,
                                        now_monotonic_ns=201, maximum_age_ns=100,
                                        scope_digest=digest("scope"), environment_digest=digest("environment"))
        self.assertEqual((stale.sample_count, stale.mean_latency_ms, stale.findings),
                         (1, None, ("TELEMETRY_STALE_OR_FUTURE",
                                    "TELEMETRY_OBSERVATION_STALE_OR_FUTURE")))
        future = analyzer.analyze_current((self.sample("sample.future", at=202),), envelope,
                                         now_monotonic_ns=201, maximum_age_ns=100,
                                         scope_digest=digest("scope"), environment_digest=digest("environment"))
        self.assertEqual(future.findings, ("TELEMETRY_STALE_OR_FUTURE",
                                           "TELEMETRY_OBSERVATION_STALE_OR_FUTURE"))
        mixed = analyzer.analyze_current((replace(self.sample("sample.mixed"), scope_digest=digest("other-scope")),), envelope,
                                         now_monotonic_ns=100, maximum_age_ns=100,
                                         scope_digest=digest("scope"), environment_digest=digest("environment"))
        self.assertEqual((mixed.mean_latency_ms, mixed.findings),
                         (None, ("TELEMETRY_SCOPE_MISMATCH",)))

    def test_current_analysis_recovers_only_after_fresh_identity_bound_measurement(self):
        analyzer, envelope = PerformanceDiagnostics(), PerformanceEnvelope(50, 300, 400)
        rejected = analyzer.analyze_current((self.sample("sample.old", at=100),), envelope,
                                            now_monotonic_ns=201, maximum_age_ns=100,
                                            scope_digest=digest("scope"), environment_digest=digest("environment"))
        recovered = analyzer.analyze_current((self.sample("sample.fresh", latency=20, cpu=100, memory=200, at=201),), envelope,
                                             now_monotonic_ns=201, maximum_age_ns=100,
                                             scope_digest=digest("scope"), environment_digest=digest("environment"))
        self.assertFalse(rejected.within_envelope)
        self.assertEqual((recovered.mean_latency_ms, recovered.p95_latency_ms, recovered.findings),
                         (20.0, 20, ()))

    def test_current_analysis_rejects_stale_or_future_constituent_observations(self):
        analyzer, envelope = PerformanceDiagnostics(), PerformanceEnvelope(50, 300, 400)
        stale_cpu = replace(self.sample("sample.stale-cpu", at=200), cpu_milli=q(20, at=100))
        future_memory = replace(self.sample("sample.future-memory", at=200), memory_bytes=q(100, at=201))
        for sample in (stale_cpu, future_memory):
            with self.subTest(sample=sample.sample_id):
                result = analyzer.analyze_current((sample,), envelope, now_monotonic_ns=200,
                                                  maximum_age_ns=99, scope_digest=digest("scope"),
                                                  environment_digest=digest("environment"))
                self.assertEqual((result.mean_latency_ms, result.p95_latency_ms, result.peak_cpu_milli,
                                  result.peak_memory_bytes, result.within_envelope, result.findings),
                                 (None, None, None, None, False,
                                  ("TELEMETRY_OBSERVATION_STALE_OR_FUTURE",)))

    def test_telemetry_recorder_remains_bounded_under_concurrent_writers(self):
        recorder, failures = ResourceTelemetryRecorder(maximum_samples=8), []
        def record(index):
            try:
                recorder.record(self.sample("sample.concurrent." + str(index)))
            except Exception as exc:
                failures.append(exc)
        threads = [threading.Thread(target=record, args=(index,)) for index in range(32)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        retained = recorder.recent(now_monotonic_ns=100, maximum_age_ns=1, scope_digest=digest("scope"))
        self.assertFalse(failures)
        self.assertLessEqual(len(retained), 8)
        self.assertTrue(all(sample.scope_digest == digest("scope") for sample in retained))

    def test_digest_bound_workload_comparison_reports_only_measurement_difference(self):
        analyzer = PerformanceDiagnostics()
        baseline = (self.sample("baseline.1", latency=30, cpu=200, memory=300),)
        candidate = (self.sample("candidate.1", latency=10, cpu=100, memory=200),)
        result = analyzer.compare(WorkloadComparisonInput("workload.compare", digest("workload"), baseline, candidate),
                                  PerformanceEnvelope(50, 300, 400))
        self.assertEqual((result.state, result.reproducible, result.baseline_scope_digest, result.candidate_environment_digest),
                          ("HISTORICAL_UNQUALIFIED_COMPARISON", False, digest("scope"), digest("environment")))
        self.assertEqual([(item.metric, item.baseline, item.candidate, item.state) for item in result.deltas],
                         [("P95_LATENCY_MS", 30, 10, "MEASURED"), ("PEAK_CPU_MILLI", 200, 100, "MEASURED"),
                          ("PEAK_MEMORY_BYTES", 300, 200, "MEASURED")])
        self.assertEqual(result.findings, ("MEASURED_DIFFERENCE_ONLY_NO_CAUSAL_CLAIM", "COMPARISON_CONTEXT_REQUIRED"))

    def test_historical_analysis_preserves_values_without_current_qualification(self):
        sample = self.sample("sample.history", at=10000)
        result = PerformanceDiagnostics().analyze((sample,), PerformanceEnvelope(50, 300, 400))
        self.assertEqual((result.mean_latency_ms, result.within_envelope, result.measurement_state),
                         (10.0, True, "HISTORICAL_UNQUALIFIED"))
        comparison = WorkloadComparisonInput("workload.history", digest("history"), (sample,), (sample,))
        self.assertFalse(PerformanceDiagnostics().compare(comparison, PerformanceEnvelope(50, 300, 400)).reproducible)

    def test_recorder_projects_untrusted_method_and_reason_before_retention(self):
        marker = "REVIEW_NONSECRET_CONTENT_SENTINEL"
        original = replace(self.sample("sample.redacted"), cpu_milli=q(0, method=marker),
                           latency_ms=QuantityObservation(ObservationState.UNAVAILABLE, None, 100, marker, marker))
        recorder = ResourceTelemetryRecorder(); recorder.record(original)
        stored = recorder.recent(now_monotonic_ns=100, maximum_age_ns=1, scope_digest=digest("scope"))[0]
        self.assertNotIn(marker, repr(stored))
        self.assertNotIn(marker, repr(recorder.__dict__))
        self.assertEqual((stored.cpu_milli.value, stored.cpu_milli.method, stored.latency_ms.state,
                          stored.latency_ms.value, stored.latency_ms.reason),
                         (0, "METHOD_REDACTED", ObservationState.UNAVAILABLE, None, "REASON_REDACTED"))
        self.assertEqual(original.cpu_milli.method, marker)

    def test_recorder_projects_caller_identifier_before_retention_and_bookkeeping(self):
        marker = "REVIEW_RAW_IDENTIFIER_SENTINEL"
        original = self.sample(marker)
        recorder = ResourceTelemetryRecorder(maximum_samples=1)
        self.assertEqual(recorder.record(original), 0)
        stored = recorder.recent(now_monotonic_ns=100, maximum_age_ns=1, scope_digest=digest("scope"))[0]
        self.assertNotEqual(stored.sample_id, marker)
        self.assertRegex(stored.sample_id, r"^telemetry:[0-9a-f]{64}$")
        self.assertNotIn(marker, repr(stored))
        self.assertNotIn(marker, repr(recorder.__dict__))
        self.assertEqual(replace(stored, sample_id=marker), original)
        self.assertEqual(original.sample_id, marker)
        self.assertEqual(recorder.record(replace(original)), 0)
        self.assertEqual(recorder.recent(now_monotonic_ns=100, maximum_age_ns=1,
                                        scope_digest=digest("scope")), (stored,))

    def test_projected_identifier_conflict_keeps_original_and_eviction_drops_bookkeeping(self):
        marker = "REVIEW_PRIVATE_ID_WITH_CONFLICT"
        recorder = ResourceTelemetryRecorder(maximum_samples=1)
        recorder.record(self.sample(marker))
        with self.assertRaises(ContractError) as raised:
            recorder.record(self.sample(marker, memory=999))
        self.assertEqual(raised.exception.code, "RESOURCE_TELEMETRY_SAMPLE_ID_CONFLICT")
        stored = recorder.recent(now_monotonic_ns=100, maximum_age_ns=1, scope_digest=digest("scope"))[0]
        self.assertEqual(stored.memory_bytes.value, 100)
        self.assertNotIn(marker, repr(recorder.__dict__))
        self.assertEqual(recorder.record(self.sample("replacement.id")), 1)
        self.assertNotIn(stored.sample_id, recorder._retained_payloads)
        self.assertEqual(recorder.record(self.sample(marker, memory=999)), 1)
        self.assertEqual(len(recorder._retained_payloads), 1)
        self.assertNotIn(marker, repr(recorder.__dict__))

    def test_distinct_recorder_keys_yield_distinct_identifier_tokens(self):
        original = self.sample("REVIEW_PRIVATE_COMMON_IDENTIFIER")
        with patch("ceta.resource.diagnostics.secrets.token_bytes", side_effect=[b"A" * 32, b"B" * 32]):
            first, second = ResourceTelemetryRecorder(), ResourceTelemetryRecorder()
        first.record(original); second.record(original)
        first_id = first.recent(now_monotonic_ns=100, maximum_age_ns=1, scope_digest=digest("scope"))[0].sample_id
        second_id = second.recent(now_monotonic_ns=100, maximum_age_ns=1, scope_digest=digest("scope"))[0].sample_id
        self.assertNotEqual(first_id, second_id)
        for token in (first_id, second_id):
            self.assertRegex(token, r"^telemetry:[0-9a-f]{64}$")
            self.assertNotIn(original.sample_id, token)

    def test_recorder_preserves_known_native_method_and_unavailability_codes(self):
        methods = ("windows:os.cpu_count", "windows:DXGI.EnumAdapters:GetDesc", "windows:GlobalMemoryStatusEx",
                   "python:shutil.disk_usage", "windows:IsProcessInJob", "windows:GetSystemTimes")
        recorder = ResourceTelemetryRecorder()
        for index, method in enumerate(methods):
            sample = replace(self.sample("native." + str(index)), cpu_milli=q(0, method=method),
                             latency_ms=QuantityObservation(ObservationState.UNAVAILABLE, None, 100,
                                                            method, "CPU_BASELINE_REQUIRED"))
            recorder.record(sample)
        stored = recorder.recent(now_monotonic_ns=100, maximum_age_ns=1, scope_digest=digest("scope"))
        self.assertEqual(tuple(x.cpu_milli.method for x in stored), methods)
        self.assertTrue(all(x.latency_ms.value is None and x.latency_ms.reason == "CPU_BASELINE_REQUIRED" for x in stored))

    def test_identical_retained_delivery_never_counts_or_drops_twice(self):
        recorder = ResourceTelemetryRecorder(maximum_samples=1); sample = self.sample("sample.same")
        self.assertEqual(recorder.record(sample), 0)
        for _ in range(20): self.assertEqual(recorder.record(replace(sample)), 0)
        self.assertEqual(len(recorder.recent(now_monotonic_ns=100, maximum_age_ns=1, scope_digest=digest("scope"))), 1)

    def test_conflicting_sample_id_is_rejected_even_if_projection_is_identical(self):
        recorder = ResourceTelemetryRecorder()
        sample = replace(self.sample("sample.conflict"), cpu_milli=q(0, method="ARBITRARY_A"))
        recorder.record(sample)
        for altered in (replace(sample, memory_bytes=q(1)), replace(sample, cpu_milli=q(0, method="ARBITRARY_B"))):
            with self.assertRaises(ContractError) as raised: recorder.record(altered)
            self.assertEqual(raised.exception.code, "RESOURCE_TELEMETRY_SAMPLE_ID_CONFLICT")
        stored = recorder.recent(now_monotonic_ns=100, maximum_age_ns=1, scope_digest=digest("scope"))
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0].memory_bytes.value, 100)

    def test_duplicate_bookkeeping_is_bounded_and_eviction_limit_is_explicit(self):
        recorder = ResourceTelemetryRecorder(maximum_samples=2)
        for index in range(100): recorder.record(self.sample("sample." + str(index)))
        self.assertEqual(len(recorder._retained_payloads), 2)
        self.assertEqual(recorder.record(self.sample("sample.0")), 1)  # no durable cursor is claimed
        self.assertEqual(len(recorder._retained_payloads), 2)

    def test_concurrent_identical_delivery_has_one_record_and_zero_drops(self):
        recorder = ResourceTelemetryRecorder(maximum_samples=1); sample = self.sample("sample.concurrent.same")
        barrier = threading.Barrier(16); results, errors = [], []
        def record():
            try: barrier.wait(timeout=5); results.append(recorder.record(sample))
            except Exception as exc: errors.append(exc)
        threads = [threading.Thread(target=record) for _ in range(16)]
        for thread in threads: thread.start()
        for thread in threads: thread.join(timeout=5)
        self.assertFalse(any(thread.is_alive() for thread in threads)); self.assertFalse(errors)
        self.assertEqual(results, [0] * 16)
        self.assertEqual(len(recorder.recent(now_monotonic_ns=100, maximum_age_ns=1, scope_digest=digest("scope"))), 1)

    def test_concurrent_conflicting_deliveries_accept_exactly_one_payload(self):
        recorder = ResourceTelemetryRecorder(); barrier = threading.Barrier(2); results, errors = [], []
        def record(value):
            try: barrier.wait(timeout=5); results.append(recorder.record(self.sample("same.conflict", memory=value)))
            except ContractError as exc: errors.append(exc.code)
        threads = [threading.Thread(target=record, args=(value,)) for value in (100, 200)]
        for thread in threads: thread.start()
        for thread in threads: thread.join(timeout=5)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(results, [0]); self.assertEqual(errors, ["RESOURCE_TELEMETRY_SAMPLE_ID_CONFLICT"])

    def test_incomplete_comparison_is_unknown_not_a_measured_bottleneck(self):
        analyzer = PerformanceDiagnostics()
        baseline = (self.sample("baseline.2", latency=30),)
        candidate = (replace(self.sample("candidate.2", latency=10), latency_ms=unavailable()),)
        result = analyzer.compare(WorkloadComparisonInput("workload.unknown", digest("workload-unknown"), baseline, candidate),
                                  PerformanceEnvelope(50, 300, 400))
        self.assertEqual(result.state, "INCOMPLETE_MEASUREMENTS")
        self.assertIn("COMPARISON_UNKNOWN_P95_LATENCY_MS", result.findings)
        self.assertFalse(any("BOTTLENECK" in finding for finding in result.findings))

    def test_mixed_measurement_identity_is_preserved_and_not_reproducible(self):
        analyzer = PerformanceDiagnostics()
        baseline = (self.sample("baseline.3"), replace(self.sample("baseline.4"), scope_digest=digest("other-scope")))
        candidate = (self.sample("candidate.3"),)
        result = analyzer.compare(WorkloadComparisonInput("workload.mixed", digest("mixed"), baseline, candidate),
                                  PerformanceEnvelope(50, 300, 400))
        self.assertEqual((result.state, result.reproducible, result.baseline_scope_digest),
                         ("INCOMPLETE_MEASUREMENTS", False, None))
        self.assertIn("BASELINE_SCOPE_MIXED", result.findings)

    def test_environment_mismatch_is_not_reproducible(self):
        analyzer = PerformanceDiagnostics()
        baseline = (self.sample("baseline.environment"),)
        candidate = (replace(self.sample("candidate.environment"), environment_digest=digest("other-environment")),)
        result = analyzer.compare(WorkloadComparisonInput("workload.environment", digest("environment"), baseline, candidate),
                                  PerformanceEnvelope(50, 300, 400))
        self.assertEqual((result.state, result.reproducible), ("INCOMPLETE_MEASUREMENTS", False))
        self.assertIn("COMPARISON_ENVIRONMENT_MISMATCH", result.findings)


class CurrentComparisonTests(unittest.TestCase):
    def setUp(self):
        self.analyzer, self.envelope = PerformanceDiagnostics(), PerformanceEnvelope(50, 300, 400)
        self.workload = digest("workload.current")
        self.baseline = replace(DiagnosticTests.sample(self, "baseline.current", latency=30, cpu=200, memory=300, at=80),
                                source=TelemetrySourceBinding(digest("producer"), 4, 1, self.workload))
        self.candidate = replace(DiagnosticTests.sample(self, "candidate.current", latency=10, cpu=100, memory=200, at=90),
                                 source=TelemetrySourceBinding(digest("producer"), 4, 2, self.workload))
        self.context = CurrentComparisonContext(100, 30, digest("scope"), digest("environment"),
                                                digest("producer"), 4, 70, 85, 86, 100)

    def compare(self, baseline=None, candidate=None, context=None):
        request = WorkloadComparisonInput("workload.current", self.workload,
                    (self.baseline,) if baseline is None else baseline,
                    (self.candidate,) if candidate is None else candidate)
        return self.analyzer.compare_current(request, self.envelope, context=self.context if context is None else context)

    def assert_rejected(self, result, code):
        self.assertFalse(result.reproducible); self.assertEqual(result.state, "COMPARISON_CONTEXT_REJECTED")
        self.assertIn(code, result.findings)
        self.assertEqual((result.baseline.mean_latency_ms, result.candidate.mean_latency_ms), (None, None))

    def test_current_comparison_requires_distinct_fresh_source_bound_before_after_measurements(self):
        result = self.compare()
        self.assertTrue(result.reproducible); self.assertEqual(result.state, "MEASURED_REPRODUCIBLE_COMPARISON")
        self.assertEqual([(x.metric, x.baseline, x.candidate) for x in result.deltas],
                         [("P95_LATENCY_MS", 30, 10), ("PEAK_CPU_MILLI", 200, 100), ("PEAK_MEMORY_BYTES", 300, 200)])
        self.assertEqual(result.baseline.measurement_state, "CURRENT_IDENTITY_AND_TIME_BOUND")
        self.assertIn("CALLER_BOUND_CONTEXT_NOT_AUTHENTICATED_SOURCE_PROOF", result.findings)

    def test_measured_zero_is_valid_and_unavailable_is_incomplete(self):
        zero = replace(self.candidate, cpu_milli=q(0, at=90), memory_bytes=q(0, at=90), latency_ms=q(0, at=90))
        self.assertTrue(self.compare(candidate=(zero,)).reproducible)
        unknown = replace(zero, latency_ms=unavailable(at=90))
        result = self.compare(candidate=(unknown,))
        self.assertFalse(result.reproducible); self.assertEqual(result.state, "INCOMPLETE_MEASUREMENTS")
        self.assertEqual(result.deltas[0].candidate, None)

    def test_age_exact_boundary_accepts_and_clock_rollback_rejects(self):
        exact = replace(self.baseline, cpu_milli=q(200, at=70))
        self.assertTrue(self.compare(baseline=(exact,)).reproducible)
        self.assert_rejected(self.compare(context=replace(self.context, now_monotonic_ns=99, maximum_age_ns=29)),
                             "COMPARISON_WINDOW_STALE_OR_FUTURE")

    def test_future_wrapper_and_stale_or_future_constituents_reject_whole_comparison(self):
        cases = ((replace(self.candidate, observed_monotonic_ns=101), "TELEMETRY_STALE_OR_FUTURE"),
                 (replace(self.candidate, memory_bytes=q(200, at=101)), "TELEMETRY_OBSERVATION_STALE_OR_FUTURE"),
                 (replace(self.baseline, cpu_milli=q(200, at=69)), "TELEMETRY_OBSERVATION_STALE_OR_FUTURE"))
        for sample, code in cases:
            with self.subTest(sample=sample):
                result = self.compare(baseline=(sample,)) if sample.sample_id.startswith("baseline") else self.compare(candidate=(sample,))
                self.assert_rejected(result, code)

    def test_disjoint_windows_and_constituent_before_wrapper_are_required(self):
        for context in (replace(self.context, candidate_start_ns=85), replace(self.context, baseline_start_ns=86),
                        replace(self.context, candidate_end_ns=101)):
            with self.subTest(context=context): self.assertFalse(self.compare(context=context).reproducible)
        self.assert_rejected(self.compare(candidate=(replace(self.candidate, memory_bytes=q(200, at=91)),)),
                             "COMPARISON_OBSERVATION_OUTSIDE_WINDOW")

    def test_reused_ids_across_or_within_windows_are_rejected(self):
        self.assert_rejected(self.compare(candidate=(replace(self.candidate, sample_id=self.baseline.sample_id),)),
                             "COMPARISON_SAMPLE_REUSED_OR_DUPLICATED")
        self.assert_rejected(self.compare(baseline=(self.baseline, self.baseline)),
                             "COMPARISON_SAMPLE_REUSED_OR_DUPLICATED")

    def test_mixed_scope_environment_source_workload_or_generation_rejects(self):
        changes = ((replace(self.candidate, scope_digest=digest("other")), "TELEMETRY_SCOPE_MISMATCH"),
                   (replace(self.candidate, environment_digest=digest("other")), "TELEMETRY_ENVIRONMENT_MISMATCH"),
                   (replace(self.candidate, source=None), "COMPARISON_SOURCE_CONTEXT_MISSING"),
                   (replace(self.candidate, source=replace(self.candidate.source, source_digest=digest("other"))), "COMPARISON_SOURCE_MISMATCH"),
                   (replace(self.candidate, source=replace(self.candidate.source, workload_digest=digest("other"))), "COMPARISON_WORKLOAD_MISMATCH"),
                   (replace(self.candidate, source=replace(self.candidate.source, source_generation=5)), "COMPARISON_SOURCE_GENERATION_MISMATCH"))
        for sample, code in changes:
            with self.subTest(code=code): self.assert_rejected(self.compare(candidate=(sample,)), code)

    def test_sequence_reuse_reorder_and_gaps_remain_unqualified(self):
        for sequence, code in ((1, "COMPARISON_SEQUENCE_NOT_ORDERED"), (0, "COMPARISON_SEQUENCE_NOT_ORDERED"),
                               (3, "COMPARISON_SEQUENCE_GAP")):
            with self.subTest(sequence=sequence):
                sample = replace(self.candidate, source=replace(self.candidate.source, sequence=sequence))
                self.assert_rejected(self.compare(candidate=(sample,)), code)

    def test_sample_order_cannot_hide_reverse_monotonic_observations(self):
        second = replace(self.baseline, sample_id="baseline.second", observed_monotonic_ns=79,
                         cpu_milli=q(200, at=79), memory_bytes=q(300, at=79), storage_bytes=q(0, at=79), latency_ms=q(30, at=79),
                         source=replace(self.baseline.source, sequence=2))
        candidate = replace(self.candidate, source=replace(self.candidate.source, sequence=3))
        self.assert_rejected(self.compare(baseline=(self.baseline, second), candidate=(candidate,)),
                             "COMPARISON_SAMPLE_TIME_NOT_ORDERED")

    def test_missing_context_and_malformed_bounds_never_assume_current_success(self):
        comparison = WorkloadComparisonInput("workload.current", self.workload, (self.baseline,), (self.candidate,))
        with self.assertRaises(ContractError): self.analyzer.compare_current(comparison, self.envelope, context=None)
        for field, value in (("maximum_age_ns", 0), ("maximum_age_ns", 300_000_000_001),
                             ("now_monotonic_ns", -1), ("now_monotonic_ns", 2**63), ("source_generation", True)):
            with self.subTest(field=field, value=value):
                with self.assertRaises(ContractError): replace(self.context, **{field: value})
        with self.assertRaises(ContractError): WorkloadComparisonInput("workload.too-big", self.workload,
                                                                       (self.baseline,) * 8193, (self.candidate,))

    def test_concurrent_pure_comparisons_do_not_mutate_inputs_or_share_results(self):
        barrier = threading.Barrier(8); results, errors = [], []
        def compare():
            try: barrier.wait(timeout=5); results.append(self.compare())
            except Exception as exc: errors.append(exc)
        threads = [threading.Thread(target=compare) for _ in range(8)]
        for thread in threads: thread.start()
        for thread in threads: thread.join(timeout=5)
        self.assertFalse(any(thread.is_alive() for thread in threads)); self.assertFalse(errors)
        self.assertEqual(len(results), 8); self.assertTrue(all(x.reproducible for x in results))
        self.assertEqual(self.baseline.source.sequence, 1); self.assertEqual(self.candidate.source.sequence, 2)


class InferenceMeasurementTests(unittest.TestCase):
    def prepared(self, *, output_tokens=8):
        fixture = _CompilerFixture(context_tokens=8192)
        result, _ = fixture.compile(output_tokens=output_tokens)
        self.assertEqual(result.kind, "PREVIEW")
        self.assertIsNotNone(result.prepared)
        return result.prepared

    def test_exact_input_token_measurement_is_bound_to_prepared_state_without_charge(self):
        prepared = self.prepared(output_tokens=8)
        measurement = measure_input_tokens(prepared)
        result = assess_input_context(measurement, prepared)
        state = prepared.selection.state
        self.assertEqual((measurement.state, measurement.request_id, measurement.reserved_output_tokens, result.state),
                         ("MEASURED", state.request_id, state.reserved_output_tokens, "ADVISORY"))
        self.assertEqual((measurement.prepared_commitment, measurement.payload_commitment, measurement.runtime_digest),
                         (prepared.commitment, prepared.tokenization.payload_commitment, state.runtime.runtime_commitment))

    def test_inexact_or_substituted_prepared_bindings_fail_closed(self):
        prepared = self.prepared(output_tokens=8)
        inexact_prepared = replace(prepared, tokenization=replace(prepared.tokenization, exact=False))
        blocked = assess_input_context(measure_input_tokens(inexact_prepared), inexact_prepared)
        self.assertEqual((blocked.state, blocked.reason_codes),
                         ("BLOCKED", ("PREPARED_TOKENIZATION_NOT_EXACT",)))
        measurement = measure_input_tokens(prepared)
        prepared_became_inexact = assess_input_context(measurement, inexact_prepared)
        self.assertEqual((prepared_became_inexact.state, prepared_became_inexact.reason_codes),
                         ("BLOCKED", ("PREPARED_TOKENIZATION_NOT_EXACT",)))
        substituted_count = replace(measurement, input_tokens=measurement.input_tokens - 1)
        self.assertEqual(assess_input_context(substituted_count, prepared).reason_codes,
                         ("PREPARED_TOKEN_COUNT_MISMATCH",))
        other_prepared = replace(prepared, binding_wire=b"different-preview-binding")
        self.assertEqual(assess_input_context(measurement, other_prepared).reason_codes,
                         ("PREPARED_RECORD_STALE_OR_MISMATCHED",))
        substituted_request = replace(measurement, request_id="request.substituted")
        substituted_reserve = replace(measurement, reserved_output_tokens=1)
        self.assertEqual(assess_input_context(substituted_request, prepared).state, "BLOCKED")
        self.assertEqual(assess_input_context(substituted_reserve, prepared).state, "BLOCKED")


class AdmissionTests(unittest.TestCase):
    def budget(self):
        return BudgetEnvelope("budget.1", ResourceVector(1000, 1000, 1000, 1000),
                              ResourceVector(100, 100, 100, 100), ResourceVector(100, 100, 100, 100),
                              ResourceVector(100, 100, 100, 100), 7)

    def estimate(self, *, uncertainty=0, need=ResourceVector(100, 100, 100, 100), workload_id="workload.1"):
        profile = MeasuredWorkloadProfile(workload_id, f"{workload_id}.profile", digest(f"{workload_id}.revision"),
                                          digest(f"{workload_id}.source"), 90, (need,), 900)
        return WorkloadRequirementEstimator((profile,), clock=lambda: 100, headroom_milli=uncertainty).estimate(
            workload_id, expected_profile_revision=profile.profile_revision)

    def request(self, **changes):
        value = AdmissionRequest("request.1", self.budget(), self.estimate(), 4, 100, True, PressureLevel.NORMAL)
        return replace(value, **changes)

    def test_budget_retains_control_reserve_and_tracks_measured_distinct_from_reserved(self):
        budget = self.budget()
        self.assertEqual(budget.allocatable, ResourceVector(700, 700, 700, 700))
        self.assertEqual(assess_budget(budget, ResourceVector(700, 700, 700, 700)), (True, ()))
        self.assertEqual(assess_budget(budget, ResourceVector(701, 700, 700, 700)), (False, ("COMPUTE_BUDGET_EXHAUSTED",)))

    def test_individual_budget_controllers_are_pure_and_generation_pinned(self):
        budget = self.budget()
        controllers = ((ComputeBudgetController(), 701, "COMPUTE_BUDGET_EXHAUSTED"),
                       (MemoryBudgetController(), 701, "MEMORY_BUDGET_EXHAUSTED"),
                       (ExecutionTimeBudgetController(), 701, "EXECUTION_TIME_BUDGET_EXHAUSTED"))
        for controller, requested, code in controllers:
            with self.subTest(controller=type(controller).__name__):
                check = controller.assess(budget, requested)
                self.assertEqual((check.accepted, check.reason_codes, check.budget_generation), (False, (code,), 7))

    def test_child_budget_containment_rejects_extra_delegation_and_memory_headroom(self):
        parent = self.budget()
        safe = ChildBudgetRequest("budget.child", parent, 7, ResourceVector(500, 500, 500, 500),
                                  ResourceVector(100, 100, 100, 100), ResourceVector(100, 100, 100, 100),
                                  ResourceVector(100, 100, 100, 100))
        accepted = ComputeBudgetController().assess_child(safe)
        self.assertTrue(accepted.accepted)
        self.assertEqual((accepted.child_budget.generation, accepted.child_budget.allocatable),
                         (7, ResourceVector(200, 200, 200, 200)))
        extra = ChildBudgetRequest("budget.extra", parent, 7, ResourceVector(701, 1, 1, 1),
                                   ResourceVector(0, 0, 0, 0), ResourceVector(0, 0, 0, 0),
                                   ResourceVector(0, 0, 0, 0))
        memory = ChildBudgetRequest("budget.memory", parent, 7, ResourceVector(1, 701, 1, 1),
                                    ResourceVector(0, 0, 0, 0), ResourceVector(0, 0, 0, 0),
                                    ResourceVector(0, 0, 0, 0))
        self.assertEqual(ComputeBudgetController().assess_child(extra).reason_codes,
                         ("CHILD_BUDGET_EXCEEDS_PARENT_REMAINING",))
        self.assertEqual(MemoryBudgetController().assess_child(memory).reason_codes,
                         ("CHILD_BUDGET_EXCEEDS_PARENT_REMAINING",))

    def test_child_budget_generation_is_pinned_under_concurrent_evaluation(self):
        request = ChildBudgetRequest("budget.stale", self.budget(), 6, ResourceVector(1, 1, 1, 1),
                                     ResourceVector(0, 0, 0, 0), ResourceVector(0, 0, 0, 0),
                                     ResourceVector(0, 0, 0, 0))
        results = []
        threads = [threading.Thread(target=lambda: results.append(ComputeBudgetController().assess_child(request)))
                   for _ in range(8)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(results, [results[0]] * 8)
        self.assertEqual(results[0].reason_codes, ("PARENT_BUDGET_GENERATION_STALE",))

    def test_deadline_assessment_uses_canonical_monotonic_contract(self):
        budget = self.budget()
        deadline = Deadline("boot.budget", 1, 1, 1_000_000_000, 2_000_000_000, 1_000_000_000, 2_000_000_000)
        previous = ClockSample("boot.budget", 1, 1, 1_100_000_000, 1_100_000_000, 0, True)
        current = ClockSample("boot.budget", 1, 1, 1_600_000_000, 1_600_000_000, 0, True)
        controller = ExecutionTimeBudgetController()
        deadline_rejected = controller.assess_deadline(budget, 500, deadline=deadline,
                                                        previous_clock=previous, current_clock=current)
        self.assertEqual((deadline_rejected.accepted, deadline_rejected.reason_codes, deadline_rejected.remaining_deadline_ms),
                         (False, ("DEADLINE_BUDGET_EXCEEDED",), 400))
        budget_rejected = controller.assess_deadline(budget, 701, deadline=deadline,
                                                      previous_clock=previous, current_clock=current)
        self.assertEqual((budget_rejected.accepted, budget_rejected.reason_codes),
                         (False, ("EXECUTION_TIME_BUDGET_EXHAUSTED",)))
        ambiguous = controller.assess_deadline(budget, 1, deadline=deadline, previous_clock=previous,
                                               current_clock=replace(current, wall_trusted=False))
        self.assertEqual((ambiguous.accepted, ambiguous.reason_codes), (False, ("TRUSTED_TIME_UNAVAILABLE",)))
        expired = controller.assess_deadline(budget, 1, deadline=deadline, previous_clock=previous,
                                             current_clock=replace(current, monotonic_ns=2_000_000_000,
                                                                   wall_time_ns=2_000_000_000))
        self.assertEqual((expired.accepted, expired.reason_codes), (False, ("DEADLINE_EXPIRED_OR_UNCERTAIN",)))

    def test_admission_never_calls_reservation_port_for_stale_pressure_or_budget_denial(self):
        port = FakeReservations(ReservationResult(AdmissionState.ADMITTED, "reservation.1", 8, ()))
        controller = WorkloadAdmissionController(port, clock=lambda: 100)
        self.assertEqual(controller.admit(self.request(observation_current=False)).state, AdmissionState.STALE)
        self.assertEqual(controller.admit(self.request(pressure=PressureLevel.ELEVATED)).state, AdmissionState.BLOCKED)
        self.assertEqual(controller.admit(self.request(estimate=self.estimate(need=ResourceVector(999, 1, 1, 1)))).state,
                         AdmissionState.REJECTED)
        self.assertFalse(port.requests)

    def test_unknown_or_stale_measured_profile_is_not_admission_ready(self):
        profile = MeasuredWorkloadProfile("workload.profile", "profile.1", digest("revision.1"), digest("source.1"),
                                          100, (ResourceVector(100, 200, 300, 400), ResourceVector(200, 100, 250, 350)), 800)
        estimator = WorkloadRequirementEstimator((profile,), clock=lambda: 110, maximum_profile_age_ns=20,
                                                 headroom_milli=100)
        unknown = estimator.estimate("workload.unknown")
        measured = estimator.estimate("workload.profile", expected_profile_revision=profile.profile_revision)
        stale_revision = estimator.estimate("workload.profile", expected_profile_revision=digest("other-revision"))
        self.assertEqual((unknown.state, unknown.requirements, unknown.reason_code),
                         ("UNRESOLVED", None, "PROFILE_UNKNOWN"))
        self.assertEqual((measured.state, measured.requirements, measured.conservative_requirements,
                          measured.profile_id, measured.confidence_milli),
                         ("MEASURED", ResourceVector(200, 200, 300, 400), ResourceVector(220, 220, 330, 440),
                          "profile.1", 800))
        self.assertEqual((stale_revision.state, stale_revision.reason_code), ("UNRESOLVED", "PROFILE_REVISION_STALE"))
        stale = WorkloadRequirementEstimator((profile,), clock=lambda: 121, maximum_profile_age_ns=20).estimate(
            "workload.profile", expected_profile_revision=profile.profile_revision)
        self.assertEqual((stale.state, stale.reason_code), ("UNRESOLVED", "PROFILE_STALE"))
        port = FakeReservations(ReservationResult(AdmissionState.ADMITTED, "reservation.1", 8, ()))
        decision = WorkloadAdmissionController(port, clock=lambda: 100).admit(self.request(estimate=unknown))
        self.assertEqual((decision.state, decision.reason_codes),
                         (AdmissionState.UNCERTAIN, ("WORKLOAD_ESTIMATE_UNRESOLVED", "PROFILE_UNKNOWN")))
        stale_revision_decision = WorkloadAdmissionController(port, clock=lambda: 100).admit(
            self.request(estimate=stale_revision))
        self.assertEqual((stale_revision_decision.state, stale_revision_decision.reason_codes),
                         (AdmissionState.UNCERTAIN, ("WORKLOAD_ESTIMATE_UNRESOLVED", "PROFILE_REVISION_STALE")))
        self.assertFalse(port.requests)

    def test_estimator_is_deterministic_under_concurrent_evaluation(self):
        profile = MeasuredWorkloadProfile("workload.concurrent", "profile.concurrent", digest("revision.concurrent"),
                                          digest("source.concurrent"), 100, (ResourceVector(1, 2, 3, 4),), 900)
        estimator, results = WorkloadRequirementEstimator((profile,), clock=lambda: 100), []
        threads = [threading.Thread(target=lambda: results.append(estimator.estimate(
            "workload.concurrent", expected_profile_revision=profile.profile_revision)))
                   for _ in range(8)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(results, [results[0]] * 8)

    def test_profile_calibration_compares_peaks_and_returns_a_new_bounded_profile(self):
        profile = MeasuredWorkloadProfile("workload.calibrate", "profile.calibrate", digest("revision.calibrate"),
                                          digest("source.calibrate"), 100,
                                          (ResourceVector(100, 200, 300, 400), ResourceVector(200, 100, 250, 350)), 800)
        estimator = WorkloadRequirementEstimator((profile,), clock=lambda: 110, maximum_profile_age_ns=20,
                                                 headroom_milli=100)
        preceding = estimator.estimate("workload.calibrate", expected_profile_revision=profile.profile_revision)
        observation = ObservedWorkloadUsage("workload.calibrate", "profile.calibrate", profile.profile_revision,
                                            profile.source_digest, 105, ResourceVector(221, 150, 330, 430))
        calibration = estimator.calibrate(observation, preceding)
        self.assertEqual((calibration.state, calibration.comparison.state,
                          calibration.comparison.expected_conservative, calibration.comparison.exceeded_dimensions),
                         ("MEASURED", "MEASURED", ResourceVector(220, 220, 330, 440), ("CPU",)))
        self.assertEqual((len(calibration.profile.samples), calibration.profile.samples[-1], calibration.profile.calibration_count,
                          calibration.profile.profile_revision, calibration.profile.source_digest),
                         (3, observation.usage, 1, profile.profile_revision, profile.source_digest))
        future = WorkloadRequirementEstimator((calibration.profile,), clock=lambda: 110, maximum_profile_age_ns=20,
                                              headroom_milli=100).estimate(
                                                  "workload.calibrate", expected_profile_revision=profile.profile_revision)
        self.assertEqual(future.requirements, ResourceVector(221, 200, 330, 430))
        unpinned = estimator.estimate("workload.calibrate")
        self.assertEqual((unpinned.state, unpinned.reason_code), ("UNRESOLVED", "PROFILE_REVISION_REQUIRED"))

    def test_profile_calibration_rejects_identity_time_and_history_and_labels_missing_estimate(self):
        profile = MeasuredWorkloadProfile("workload.negative", "profile.negative", digest("revision.negative"),
                                          digest("source.negative"), 100, (ResourceVector(1, 2, 3, 4),), 600)
        estimator = WorkloadRequirementEstimator((profile,), clock=lambda: 110, maximum_profile_age_ns=20)
        preceding = estimator.estimate("workload.negative", expected_profile_revision=profile.profile_revision)
        observation = ObservedWorkloadUsage("workload.negative", "profile.negative", profile.profile_revision,
                                            profile.source_digest, 105, ResourceVector(2, 3, 4, 5))
        with self.assertRaises(ContractError) as raised:
            estimator.calibrate(replace(observation, source_digest=digest("wrong-source")), preceding)
        self.assertEqual(raised.exception.code, "RESOURCE_PROFILE_IDENTITY_MISMATCH")
        with self.assertRaises(ContractError) as raised:
            estimator.calibrate(replace(observation, profile_revision=digest("wrong-revision")), preceding)
        self.assertEqual(raised.exception.code, "RESOURCE_PROFILE_IDENTITY_MISMATCH")
        with self.assertRaises(ContractError) as raised:
            estimator.calibrate(replace(observation, observed_monotonic_ns=100), preceding)
        self.assertEqual(raised.exception.code, "RESOURCE_PROFILE_OBSERVATION_NON_MONOTONIC")
        with self.assertRaises(ContractError) as raised:
            WorkloadRequirementEstimator((profile,), clock=lambda: 130, maximum_profile_age_ns=20).calibrate(observation, preceding)
        self.assertEqual(raised.exception.code, "RESOURCE_PROFILE_OR_OBSERVATION_STALE")
        unavailable = estimator.calibrate(observation, replace(preceding, source_digest=digest("other-source")))
        self.assertEqual((unavailable.state, unavailable.comparison.state, unavailable.profile, unavailable.reason_code),
                         ("UNAVAILABLE", "UNAVAILABLE", None, "PRECEDING_ESTIMATE_UNAVAILABLE"))
        full = MeasuredWorkloadProfile("workload.full", "profile.full", digest("revision.full"), digest("source.full"),
                                       100, (ResourceVector(1, 1, 1, 1),) * 64, 500)
        full_estimator = WorkloadRequirementEstimator((full,), clock=lambda: 101)
        full_estimate = full_estimator.estimate("workload.full", expected_profile_revision=full.profile_revision)
        full_observation = ObservedWorkloadUsage("workload.full", "profile.full", full.profile_revision,
                                                 full.source_digest, 101, ResourceVector(1, 1, 1, 1))
        with self.assertRaises(ContractError) as raised:
            full_estimator.calibrate(full_observation, full_estimate)
        self.assertEqual(raised.exception.code, "RESOURCE_PROFILE_HISTORY_BOUND_EXCEEDED")
        with self.assertRaises(ContractError) as raised:
            WorkloadRequirementEstimator((), clock=lambda: 110).calibrate(observation, preceding)
        self.assertEqual(raised.exception.code, "RESOURCE_PROFILE_UNKNOWN")
        bootstrap = WorkloadRequirementEstimator((), clock=lambda: 110).calibrate(
            observation, preceding, bootstrap_profile=profile)
        self.assertEqual((bootstrap.state, bootstrap.profile.samples[-1], bootstrap.profile.calibration_count),
                         ("MEASURED", observation.usage, 1))

    def test_profile_calibration_rejects_preceding_estimate_from_another_same_identity_snapshot(self):
        profile = MeasuredWorkloadProfile("workload.snapshot", "profile.snapshot", digest("revision.snapshot"),
                                          digest("source.snapshot"), 100,
                                          (ResourceVector(10, 20, 30, 40),), 700)
        observation = ObservedWorkloadUsage("workload.snapshot", "profile.snapshot", profile.profile_revision,
                                            profile.source_digest, 105, ResourceVector(12, 22, 32, 42))
        older_estimate = WorkloadRequirementEstimator((profile,), clock=lambda: 110, maximum_profile_age_ns=20).estimate(
            "workload.snapshot", expected_profile_revision=profile.profile_revision)
        newer = replace(profile, observed_monotonic_ns=101,
                        samples=(ResourceVector(11, 21, 31, 41),), calibration_count=1)
        alternate = replace(profile, samples=(ResourceVector(99, 20, 30, 40),))
        current = WorkloadRequirementEstimator((newer,), clock=lambda: 110, maximum_profile_age_ns=20)
        alternate_estimate = WorkloadRequirementEstimator((alternate,), clock=lambda: 110, maximum_profile_age_ns=20).estimate(
            "workload.snapshot", expected_profile_revision=alternate.profile_revision)
        for preceding in (older_estimate, alternate_estimate):
            calibration = current.calibrate(observation, preceding)
            self.assertEqual((calibration.state, calibration.comparison.state,
                              calibration.profile, calibration.reason_code),
                             ("UNAVAILABLE", "UNAVAILABLE", None, "PRECEDING_ESTIMATE_UNAVAILABLE"))

    def test_profile_calibration_is_deterministic_under_concurrent_evaluation(self):
        profile = MeasuredWorkloadProfile("workload.calibration.concurrent", "profile.calibration.concurrent",
                                          digest("revision.calibration.concurrent"), digest("source.calibration.concurrent"),
                                          100, (ResourceVector(1, 2, 3, 4),), 700)
        estimator = WorkloadRequirementEstimator((profile,), clock=lambda: 110)
        preceding = estimator.estimate("workload.calibration.concurrent", expected_profile_revision=profile.profile_revision)
        observation = ObservedWorkloadUsage("workload.calibration.concurrent", "profile.calibration.concurrent",
                                            profile.profile_revision, profile.source_digest, 105, ResourceVector(2, 3, 4, 5))
        results = []
        threads = [threading.Thread(target=lambda: results.append(estimator.calibrate(observation, preceding)))
                   for _ in range(8)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(results, [results[0]] * 8)

    def test_admission_passes_conservative_estimate_and_pinned_generation_to_owner(self):
        port = FakeReservations(ReservationResult(AdmissionState.ADMITTED, "reservation.1", 8, ()))
        decision = WorkloadAdmissionController(port, clock=lambda: 100).admit(self.request(estimate=self.estimate(
            uncertainty=100, need=ResourceVector(100, 100, 100, 100))))
        self.assertEqual(decision.state, AdmissionState.ADMITTED)
        request = port.requests.pop()
        self.assertEqual(request.requirements, ResourceVector(110, 110, 110, 110))
        self.assertEqual((request.expected_generation, request.observation_sequence), (7, 4))

    def test_stale_timestamp_denies_even_if_the_caller_claims_current(self):
        port = FakeReservations(ReservationResult(AdmissionState.ADMITTED, "reservation.1", 8, ()))
        decision = WorkloadAdmissionController(port, clock=lambda: 201, maximum_observation_age_ns=100).admit(self.request())
        self.assertEqual(decision.state, AdmissionState.STALE)
        self.assertFalse(port.requests)

    def test_malformed_external_id_rejects_before_any_reservation_call(self):
        port = FakeReservations(ReservationResult(AdmissionState.ADMITTED, "reservation.1", 8, ()))
        with self.assertRaises(ContractError) as raised:
            self.request(request_id="invalid identity")
        self.assertEqual(raised.exception.code, "RESOURCE_ADMISSION_IDENTIFIER_INVALID")
        with self.assertRaises(ContractError) as raised:
            WorkloadEstimate("bad identity", ResourceVector(1, 1, 1, 1), 0, "fixture")
        self.assertEqual(raised.exception.code, "RESOURCE_WORKLOAD_IDENTIFIER_INVALID")
        self.assertFalse(port.requests)

    def test_missing_or_partial_estimate_provenance_never_calls_reservation_port(self):
        port = FakeReservations(ReservationResult(AdmissionState.ADMITTED, "reservation.1", 8, ()))
        with self.assertRaises(ContractError) as raised:
            WorkloadEstimate("workload.unbound", ResourceVector(1, 1, 1, 1), 0, "fixture")
        self.assertEqual(raised.exception.code, "RESOURCE_WORKLOAD_ESTIMATE_INVALID")
        with self.assertRaises(ContractError) as raised:
            WorkloadEstimate("workload.partial", ResourceVector(1, 1, 1, 1), 0, "fixture",
                             profile_id="profile.partial")
        self.assertEqual(raised.exception.code, "RESOURCE_WORKLOAD_ESTIMATE_INVALID")
        unresolved = WorkloadEstimate("workload.unresolved", None, 1000, "PROFILE_UNAVAILABLE", "UNRESOLVED",
                                      reason_code="PROFILE_PROVENANCE_REQUIRED")
        decision = WorkloadAdmissionController(port, clock=lambda: 100).admit(self.request(estimate=unresolved))
        self.assertEqual((decision.state, decision.reason_codes),
                         (AdmissionState.UNCERTAIN,
                          ("WORKLOAD_ESTIMATE_UNRESOLVED", "PROFILE_PROVENANCE_REQUIRED")))
        self.assertFalse(port.requests)

    def test_planner_does_not_admit_work_beyond_capacity_or_control_reserve(self):
        one = self.estimate(need=ResourceVector(100, 100, 100, 100))
        two = self.estimate(workload_id="workload.2", need=ResourceVector(150, 150, 150, 150))
        selected = plan_concurrency((one, two), ResourceVector(300, 300, 300, 300),
                                    control_reserve=ResourceVector(100, 100, 100, 100))
        self.assertEqual(selected, (one,))
        detailed = plan_concurrency_with_facts((one, two), ResourceVector(300, 300, 300, 300),
                                               control_reserve=ResourceVector(100, 100, 100, 100))
        self.assertEqual(detailed.admitted, (one,))
        self.assertEqual(detailed.awaiting_owner_inputs,
                         ("AWAITING_OWNER_FAIRNESS_INPUT", "AWAITING_OWNER_AUTHORITY_READINESS_INPUT",
                          "AWAITING_OWNER_SHARED_FILE_CONFLICT_INPUT"))
        unresolved = WorkloadEstimate("workload.unresolved", None, 1000, "PROFILE_UNAVAILABLE",
                                      "UNRESOLVED", confidence_milli=0, reason_code="PROFILE_UNKNOWN")
        self.assertEqual(plan_concurrency((unresolved, one), ResourceVector(300, 300, 300, 300),
                                          control_reserve=ResourceVector(100, 100, 100, 100)), ())


if __name__ == "__main__":
    unittest.main()
