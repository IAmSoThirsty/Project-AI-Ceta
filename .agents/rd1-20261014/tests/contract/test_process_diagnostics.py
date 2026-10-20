"""Owned-process telemetry boundaries and actual disposable Windows measurements."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts.resource_management import (
    ObservationState, ProcessResourceCounters, ProcessResourceIdentity, ProcessUsageMeasurements,
    QuantityObservation, TelemetrySample, TelemetrySourceBinding,
)
from ceta.contracts.wire import ContractError
from ceta.resource.diagnostics import OwnedProcessTelemetrySampler, PerformanceDiagnostics, PerformanceEnvelope, ResourceTelemetryRecorder
import test_windows_jobs as jobs

def digest(text): return "sha256:" + hashlib.sha256(text.encode()).hexdigest()
def measured(value, at, method="fixture"): return QuantityObservation(ObservationState.MEASURED, value, at, method)
def unknown(at, method="fixture", reason="NOT_OBSERVED"):
    return QuantityObservation(ObservationState.UNAVAILABLE, None, at, method, reason)
IDENTITY = ProcessResourceIdentity(42, 1001, digest("image"))

def counters(at, *, cpu=100, memory=1000, private=900, read=100, write=50, identity=IDENTITY, start=None):
    return ProcessResourceCounters(identity, at, measured(memory, at),
        ProcessUsageMeasurements(at if start is None else start, measured(cpu, at),
            measured(private, at), measured(read, at), measured(write, at)))

class CounterPort:
    """Explicit deterministic test source; native qualification is separate below."""
    resource_identity = IDENTITY
    def __init__(self, now): self.now, self.calls, self.current = now, 0, True; self.next = None
    def resource_observation_current(self, identity): return self.current and identity == self.resource_identity
    def resource_counters(self):
        self.calls += 1
        return self.next or counters(self.now[0])

class ProcessDiagnosticsTests(unittest.TestCase):
    def fixture(self, *, interval=10, age=100, window=30):
        now = [100]
        port = CounterPort(now)
        sampler = OwnedProcessTelemetrySampler(port, IDENTITY, scope_digest=digest("scope"),
            environment_digest=digest("environment"), workload_digest=digest("workload"), source_generation=4,
            clock=lambda: now[0], minimum_interval_ns=interval, maximum_age_ns=age, maximum_probe_window_ns=window)
        return now, port, sampler

    def analyze(self, samples, at=120, age=100):
        return PerformanceDiagnostics().analyze_process_current(tuple(samples), PerformanceEnvelope(20, 2000, 10000),
            now_monotonic_ns=at, maximum_age_ns=age, scope_digest=digest("scope"), environment_digest=digest("environment"))

    def test_identity_bounds_and_lifetime_digest(self):
        for pid, creation in ((0, 1), (True, 1), (42, 0), (42, -1), (2**32, 1)):
            with self.subTest(pid=pid, creation=creation), self.assertRaises(ContractError):
                ProcessResourceIdentity(pid, creation, digest("image"))
        self.assertNotEqual(IDENTITY.source_digest, replace(IDENTITY, creation_time=1002).source_digest)

    def test_baseline_cpu_unavailable_then_zero_is_a_measurement(self):
        now, port, sampler = self.fixture()
        first = sampler.sample()
        self.assertFalse(first.cpu_milli.measured)
        self.assertEqual(first.cpu_milli.reason, "PROCESS_CPU_BASELINE_REQUIRED")
        now[0] = 110
        second = sampler.sample()
        self.assertEqual((second.cpu_milli.measured, second.cpu_milli.value), (True, 0))
        self.assertEqual(second.memory_bytes.value, 1000)
        self.assertFalse(second.storage_bytes.measured)
        self.assertFalse(second.latency_ms.measured)

    def test_cpu_time_unit_conversion_does_not_clamp_multicore_usage(self):
        now, port, sampler = self.fixture(interval=1, age=2_000_000_000, window=100)
        sampler.sample()
        now[0] += 1_000_000_000
        port.next = counters(now[0], cpu=20_000_100)
        self.assertEqual(sampler.sample().cpu_milli.value, 2000)

    def test_sampling_cache_preserves_id_timestamp_and_probe_count(self):
        now, port, sampler = self.fixture()
        first = sampler.sample()
        for at in (101, 105, 109):
            now[0] = at
            self.assertIs(sampler.sample(), first)
        self.assertEqual(port.calls, 1)
        now[0] = 110
        fresh = sampler.sample()
        self.assertEqual((fresh.source.sequence, fresh.observed_monotonic_ns, port.calls), (2, 110, 2))

    def test_currentness_failure_invalidates_cached_measured_values(self):
        now, port, sampler = self.fixture()
        self.assertTrue(sampler.sample().memory_bytes.measured)
        port.current = False
        invalid = sampler.sample()
        self.assertFalse(invalid.memory_bytes.measured)
        self.assertEqual(invalid.cpu_milli.reason, "PROCESS_LIFETIME_UNAVAILABLE")
        self.assertEqual(port.calls, 1)

    def test_pid_reuse_creation_and_image_change_reject_before_probe(self):
        for identity in (replace(IDENTITY, pid=43), replace(IDENTITY, creation_time=1002), replace(IDENTITY, image_digest=digest("other"))):
            with self.subTest(identity=identity):
                now, port, sampler = self.fixture()
                port.resource_identity = identity
                denied = sampler.sample()
                self.assertEqual((denied.cpu_milli.measured, denied.cpu_milli.reason, port.calls),
                                 (False, "PROCESS_IDENTITY_MISMATCH", 0))

    def test_counter_frame_identity_mismatch_rejects_after_probe(self):
        now, port, sampler = self.fixture()
        port.next = counters(100, identity=replace(IDENTITY, creation_time=1002))
        self.assertEqual(sampler.sample().cpu_milli.reason, "PROCESS_IDENTITY_MISMATCH")

    def test_stale_and_future_frames_remain_unavailable(self):
        for at in (0, 101):
            with self.subTest(at=at):
                now, port, sampler = self.fixture(age=50)
                port.next = counters(at)
                self.assertEqual(sampler.sample().cpu_milli.reason, "PROCESS_OBSERVATION_STALE_OR_FUTURE")

    def test_order_rollback_keeps_counter_high_water(self):
        now, port, sampler = self.fixture()
        sampler.sample()
        now[0], port.next = 110, counters(99)
        self.assertEqual(sampler.sample().cpu_milli.reason, "PROCESS_OBSERVATION_ORDER_INVALID")
        now[0], port.next = 120, counters(100)
        self.assertEqual(sampler.sample().cpu_milli.reason, "PROCESS_OBSERVATION_ORDER_INVALID")
        now[0], port.next = 130, counters(130)
        self.assertEqual(sampler.sample().cpu_milli.reason, "PROCESS_CPU_BASELINE_REQUIRED")

    def test_cpu_and_io_counter_rollback_never_become_measured_zero(self):
        for field, value in (("cpu", 99), ("read", 99), ("write", 49)):
            with self.subTest(field=field):
                now, port, sampler = self.fixture()
                sampler.sample()
                now[0] = 110
                port.next = counters(110, **{field: value})
                self.assertEqual(sampler.sample().cpu_milli.reason, "PROCESS_COUNTER_ROLLBACK")
                now[0], port.next = 120, counters(120, **{field: value})
                self.assertEqual(sampler.sample().cpu_milli.reason, "PROCESS_COUNTER_ROLLBACK")

    def test_clock_rollback_is_explicit_and_retains_bound(self):
        now, port, sampler = self.fixture()
        sampler.sample()
        now[0] = 99
        self.assertEqual(sampler.sample().cpu_milli.reason, "PROCESS_CLOCK_ROLLBACK")
        now[0] = 100
        self.assertFalse(sampler.sample().cpu_milli.measured)

    def test_long_probe_window_does_not_enter_collector_as_measurement(self):
        now, port, sampler = self.fixture()
        port.next = counters(100, start=60)
        self.assertEqual(sampler.sample().cpu_milli.reason, "PROCESS_PROBE_TOO_SLOW")

    def test_gap_discards_cpu_baseline_instead_of_averaging_stale_history(self):
        now, port, sampler = self.fixture(age=100)
        sampler.sample()
        now[0], port.next = 250, counters(250, cpu=200)
        self.assertEqual(sampler.sample().cpu_milli.reason, "PROCESS_CPU_BASELINE_REQUIRED")
        now[0], port.next = 260, counters(260, cpu=200)
        self.assertEqual(sampler.sample().cpu_milli.value, 0)

    def test_elapsed_probe_occupancy_is_checked_alongside_producer_window(self):
        now, port, sampler = self.fixture(window=30)
        def delayed():
            now[0] = 150
            return counters(150)
        with patch.object(port, "resource_counters", side_effect=delayed):
            self.assertEqual(sampler.sample().cpu_milli.reason, "PROCESS_PROBE_TOO_SLOW")

    def test_native_probe_failure_recovery_reestablishes_cpu_baseline(self):
        now, port, sampler = self.fixture()
        sampler.sample()
        now[0] = 110
        with patch.object(port, "resource_counters", side_effect=OSError("test failure")):
            self.assertEqual(sampler.sample().cpu_milli.reason, "PROCESS_QUERY_FAILED")
        now[0] = 120
        self.assertEqual(sampler.sample().cpu_milli.reason, "PROCESS_CPU_BASELINE_REQUIRED")

    def test_process_control_exceptions_are_not_swallowed(self):
        now, port, sampler = self.fixture()
        with patch.object(port, "resource_counters", side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            sampler.sample()

    def test_cancel_before_probe_and_resume_with_fresh_baseline(self):
        now, port, sampler = self.fixture()
        self.assertEqual(sampler.sample(cancelled=True).cpu_milli.reason, "PROCESS_OBSERVATION_CANCELLED")
        self.assertEqual(port.calls, 0)
        now[0] = 110
        self.assertEqual(sampler.sample().cpu_milli.reason, "PROCESS_CPU_BASELINE_REQUIRED")

    def test_concurrent_sampling_caches_one_actual_probe(self):
        now, port, sampler = self.fixture()
        barrier = threading.Barrier(16)
        samples, failures = [], []
        def call():
            try:
                barrier.wait(timeout=5)
                samples.append(sampler.sample())
            except Exception as exc: failures.append(exc)
        threads = [threading.Thread(target=call) for _ in range(16)]
        for thread in threads: thread.start()
        for thread in threads: thread.join(timeout=10)
        self.assertFalse(failures)
        self.assertEqual((len(samples), port.calls), (16, 1))
        self.assertTrue(all(item is samples[0] for item in samples))

    def test_existing_recorder_bounds_process_measurements_and_deduplicates_cache(self):
        now, port, sampler = self.fixture()
        recorder = ResourceTelemetryRecorder(maximum_samples=3)
        for at in range(100, 250, 10):
            now[0] = at
            sampler.collect(recorder)
            sampler.collect(recorder)
        recent = recorder.recent(now_monotonic_ns=240, maximum_age_ns=100, scope_digest=digest("scope"))
        self.assertEqual(len(recent), 3)
        self.assertTrue(all(item.process_usage is not None for item in recent))
        self.assertTrue(all(item.source.source_digest == IDENTITY.source_digest for item in recent))
        self.assertEqual(len(recorder._retained_payloads), 3)

    def test_process_methods_reasons_and_raw_identifiers_are_projected_before_retention(self):
        now, port, sampler = self.fixture()
        sample = sampler.sample()
        marker = "REVIEW_SYNTHETIC_PRIVATE_SENTINEL"
        usage = replace(sample.process_usage, private_bytes=unknown(100, method=marker, reason=marker))
        raw = replace(sample, sample_id="private.raw.task-id", process_usage=usage)
        recorder = ResourceTelemetryRecorder(); recorder.record(raw)
        retained = recorder.recent(now_monotonic_ns=100, maximum_age_ns=100, scope_digest=digest("scope"))[0]
        self.assertEqual((retained.process_usage.private_bytes.method, retained.process_usage.private_bytes.reason),
                         ("METHOD_REDACTED", "REASON_REDACTED"))
        self.assertNotIn(marker, repr(recorder.__dict__))
        self.assertNotIn("private.raw.task-id", repr(retained))

    def test_same_telemetry_id_changed_io_payload_is_rejected(self):
        now, port, sampler = self.fixture()
        sample = sampler.sample()
        recorder = ResourceTelemetryRecorder(); recorder.record(sample)
        altered = replace(sample, process_usage=replace(sample.process_usage, read_io_bytes=measured(101, 100)))
        with self.assertRaisesRegex(ContractError, "RESOURCE_TELEMETRY_SAMPLE_ID_CONFLICT"):
            recorder.record(altered)

    def test_analyzer_reads_retained_process_values_and_labels_missing_latency(self):
        now, port, sampler = self.fixture()
        recorder = ResourceTelemetryRecorder()
        sampler.collect(recorder)
        now[0], port.next = 110, counters(110, cpu=100, private=1200, read=600, write=250)
        sampler.collect(recorder)
        result = self.analyze(recorder.recent(now_monotonic_ns=110, maximum_age_ns=100, scope_digest=digest("scope")), at=110)
        self.assertEqual((result.read_io_bytes, result.write_io_bytes, result.peak_private_bytes), (500, 200, 1200))
        self.assertEqual(result.measurement_state, "MEASURED_PROCESS_USAGE")
        self.assertFalse(result.telemetry.within_envelope)
        self.assertIn("LATENCY_UNAVAILABLE", result.telemetry.findings)

    def test_analysis_rejects_duplicate_gaps_mixed_epochs_and_workloads(self):
        now, port, sampler = self.fixture()
        first = sampler.sample()
        now[0] = 110
        second = sampler.sample()
        variants = [first, replace(second, source=replace(second.source, sequence=3)),
            replace(second, source=replace(second.source, source_generation=5)),
            replace(second, source=replace(second.source, workload_digest=digest("other")))]
        for variant in variants:
            with self.subTest(variant=variant.source):
                result = self.analyze((first, variant), at=110)
                self.assertEqual(result.measurement_state, "CURRENT_PROCESS_INPUT_REJECTED")
                self.assertIsNone(result.read_io_bytes)

    def test_stale_process_constituent_cannot_hide_inside_fresh_wrapper(self):
        now, port, sampler = self.fixture()
        sample = sampler.sample()
        changed = replace(sample, observed_monotonic_ns=200,
            cpu_milli=measured(0, 200), memory_bytes=measured(1000, 200),
            storage_bytes=unknown(200), latency_ms=unknown(200))
        result = self.analyze((changed,), at=200, age=50)
        self.assertIn("TELEMETRY_OBSERVATION_STALE_OR_FUTURE", result.findings)

    def test_typed_observation_shapes_and_sampling_bounds_fail_before_probe(self):
        with self.assertRaises(ContractError): ProcessUsageMeasurements(101, measured(1, 100), measured(1, 100), measured(1, 100), measured(1, 100))
        now, port, sampler = self.fixture()
        with self.assertRaises(ContractError):
            OwnedProcessTelemetrySampler(port, IDENTITY, scope_digest=digest("scope"), environment_digest=digest("environment"),
                workload_digest=digest("workload"), source_generation=4, minimum_interval_ns=101, maximum_age_ns=100)
        self.assertEqual(port.calls, 0)


WORKLOAD = jobs.HELPERS + r'''
import time
ready,work,done,release,path=sys.argv[1:]
memory=bytearray(8*1024*1024)
signal(ready)
wait(work)
data=b'owned-native-io-measurement'*65536
pathlib.Path(path).write_bytes(data)
assert pathlib.Path(path).read_bytes()==data
end=time.monotonic()+0.3
value=1
while time.monotonic()<end:
    value=(value*1664525+1013904223)&0xFFFFFFFF
signal(done)
wait(release)
'''

class NativeProcessDiagnosticsTests(unittest.TestCase):
    setUp, tearDown = jobs.WindowsJobTests.setUp, jobs.WindowsJobTests.tearDown
    until, event, launch, simple = jobs.WindowsJobTests.until, jobs.WindowsJobTests.event, jobs.WindowsJobTests.launch, jobs.WindowsJobTests.simple

    def sampler(self, process, *, interval=1_000_000):
        return OwnedProcessTelemetrySampler(process, process.resource_identity, scope_digest=digest("native-scope"),
            environment_digest=digest("native-environment"), workload_digest=digest(WORKLOAD), source_generation=1,
            minimum_interval_ns=interval, maximum_age_ns=10_000_000_000)

    def settled(self, process, release):
        release.signal()
        self.assertTrue(process.wait(5))
        self.until(lambda: process.active_process_count() == 0)

    def test_actual_owned_cpu_memory_io_collector_and_analyzer(self):
        ready, work, done, release = (self.event() for _ in range(4))
        process = self.launch(("-B", "-I", "-c", WORKLOAD, ready.name, work.name, done.name, release.name, str(self.directory / "native-io.bin")))
        ready.wait()
        try:
            sampler, recorder = self.sampler(process), ResourceTelemetryRecorder(maximum_samples=4)
            first = sampler.collect(recorder)
            self.assertTrue(first.memory_bytes.measured)
            self.assertFalse(first.cpu_milli.measured)
            work.signal(); done.wait()
            second = sampler.collect(recorder)
            self.assertGreater(second.cpu_milli.value, 0)
            self.assertGreater(second.memory_bytes.value, 0)
            retained = recorder.recent(now_monotonic_ns=time.monotonic_ns(), maximum_age_ns=10_000_000_000,
                                       scope_digest=digest("native-scope"))
            analysis = PerformanceDiagnostics().analyze_process_current(retained, PerformanceEnvelope(5000, 1_000_000, 2**40),
                now_monotonic_ns=time.monotonic_ns(), maximum_age_ns=10_000_000_000,
                scope_digest=digest("native-scope"), environment_digest=digest("native-environment"))
            self.assertEqual(analysis.measurement_state, "MEASURED_PROCESS_USAGE")
            self.assertGreaterEqual(analysis.read_io_bytes, len(b"owned-native-io-measurement") * 65536)
            self.assertGreaterEqual(analysis.write_io_bytes, len(b"owned-native-io-measurement") * 65536)
            self.assertGreater(analysis.peak_private_bytes, 0)
            (self.directory / "native-measurement.json").write_text(json.dumps({
                "identity_digest": process.resource_identity.source_digest, "pid": process.pid,
                "creation_time": process.creation_time, "first_observed_ns": first.observed_monotonic_ns,
                "second_observed_ns": second.observed_monotonic_ns, "cpu_milli": second.cpu_milli.value,
                "working_set_bytes": second.memory_bytes.value, "private_bytes": analysis.peak_private_bytes,
                "read_io_bytes": analysis.read_io_bytes, "write_io_bytes": analysis.write_io_bytes,
                "workload_digest": digest(WORKLOAD)}), encoding="utf-8")
        finally:
            work.signal()
            self.settled(process, release)

    def test_actual_cached_process_exit_and_creation_mismatch_reject(self):
        process, release, metadata = self.simple()
        sampler = self.sampler(process, interval=1_000_000_000)
        first = sampler.sample()
        self.assertIs(sampler.sample(), first)
        self.assertFalse(process.resource_observation_current(replace(process.resource_identity, creation_time=process.creation_time + 1)))
        self.settled(process, release)
        unavailable = sampler.sample()
        self.assertFalse(unavailable.memory_bytes.measured)
        self.assertEqual(unavailable.cpu_milli.reason, "PROCESS_LIFETIME_UNAVAILABLE")

    def test_actual_counter_queries_do_not_allocate_persistent_handles(self):
        process, release, metadata = self.simple()
        from ctypes import byref
        from ctypes.wintypes import DWORD
        try:
            before, after = DWORD(), DWORD()
            self.assertTrue(self.api.GetProcessHandleCount(self.api.GetCurrentProcess(), byref(before)))
            for _ in range(100):
                value = process.resource_counters()
                self.assertEqual(value.identity, process.resource_identity)
                self.assertTrue(value.usage.cpu_time_100ns.measured)
            self.assertTrue(self.api.GetProcessHandleCount(self.api.GetCurrentProcess(), byref(after)))
            self.assertEqual(before.value, after.value)
        finally: self.settled(process, release)

    def test_actual_api_failure_is_unavailable_and_recovery_uses_native_values(self):
        process, release, metadata = self.simple()
        try:
            with patch.object(process._api, "K32GetProcessMemoryInfo", return_value=False), patch.object(process._api, "GetProcessIoCounters", return_value=False):
                denied = process.resource_counters()
            self.assertFalse(denied.working_set_bytes.measured)
            self.assertEqual(denied.working_set_bytes.reason, "PROCESS_MEMORY_QUERY_FAILED")
            self.assertFalse(denied.usage.read_io_bytes.measured)
            self.assertEqual(denied.usage.read_io_bytes.reason, "PROCESS_IO_QUERY_FAILED")
            recovered = process.resource_counters()
            self.assertTrue(recovered.working_set_bytes.measured)
            self.assertTrue(recovered.usage.read_io_bytes.measured)
        finally: self.settled(process, release)

    def test_actual_concurrent_cache_and_lifetime_close_keep_owned_handle(self):
        process, release, metadata = self.simple()
        sampler = self.sampler(process, interval=1_000_000_000)
        barrier = threading.Barrier(12)
        samples, failures = [], []
        def read():
            try:
                barrier.wait(timeout=5)
                samples.append(sampler.sample())
            except Exception as exc: failures.append(exc)
        try:
            with patch.object(process, "resource_counters", wraps=process.resource_counters) as observed:
                threads = [threading.Thread(target=read) for _ in range(12)]
                for thread in threads: thread.start()
                for thread in threads: thread.join(timeout=10)
                self.assertFalse(failures)
                self.assertEqual((len(samples), observed.call_count), (12, 1))
                self.assertTrue(all(sample is samples[0] for sample in samples))
            self.settled(process, release)
            process.close()
            self.assertFalse(sampler.sample().memory_bytes.measured)
        finally:
            if not process.lifetime_closed: self.settled(process, release)
            if process.lifetime_closed: self.owned.remove(process)

if __name__ == "__main__": unittest.main()
