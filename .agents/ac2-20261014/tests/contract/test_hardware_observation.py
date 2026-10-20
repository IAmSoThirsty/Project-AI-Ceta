"""Hardware timing, counter integrity and actual disposable Windows probes."""
from dataclasses import replace
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ceta.contracts.resource_management import AdmissionState, BudgetEnvelope, ObservationState, ResourceVector
from ceta.resource.admission import AdmissionRequest, WorkloadAdmissionController, WorkloadEstimate, assess_budget
from ceta.resource.hardware import (
    SamplingPolicy, StorageCapacityMonitor, WindowsComputeAvailabilityMonitor,
    WindowsHardwareProfiler, available_capacity,
)
from ceta.resource.pressure import ResourcePressureDetector
from fixture_paths import ROOT

NATIVE_OBSERVATIONS = []


class HardwareObservationTests(unittest.TestCase):
    def policy(self, **changes):
        return replace(SamplingPolicy(maximum_age_ns=100, minimum_interval_ns=10,
            control_cpu_milli=0, control_memory_bytes=0, control_storage_bytes=0), **changes)

    def storage(self, now, reader=None, **changes):
        return StorageCapacityMonitor(path=ROOT, clock=lambda: now[0], policy=self.policy(**changes),
            disk_usage=reader if reader is not None else lambda path: SimpleNamespace(total=1000, free=600))

    def cpu(self, now, frames, **kwargs):
        values = iter(frames)
        return WindowsComputeAvailabilityMonitor(clock=lambda: now[0], policy=self.policy(),
            system_times=lambda: next(values), processor_count=kwargs.get("count", lambda: 4))

    def assert_unknown(self, result, reason):
        for item in (result.total, result.free, result.reservable, result.utilization_milli):
            self.assertEqual((item.state, item.value, item.reason), (ObservationState.UNAVAILABLE, None, reason))

    def test_sampling_policy_rejects_unbounded_reserves_and_interval_inputs(self):
        for changes in ({"control_cpu_milli": True}, {"control_memory_bytes": 1 << 63},
                        {"control_storage_bytes": -1}, {"maximum_probe_window_ns": 0},
                        {"maximum_probe_window_ns": 101}, {"maximum_probe_window_ns": True},
                        {"maximum_sampling_interval_ns": 9}, {"maximum_sampling_interval_ns": 101},
                        {"maximum_sampling_interval_ns": "100"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.policy(**changes)
        self.assertEqual((self.policy().probe_window_ns, self.policy().sampling_interval_ns), (100, 100))

    def test_constructor_rejections_precede_all_probes(self):
        calls = []
        for factory, kwargs in ((StorageCapacityMonitor, {"path": "T:/"}),
                (StorageCapacityMonitor, {"clock": None}), (StorageCapacityMonitor, {"disk_usage": False}),
                (StorageCapacityMonitor, {"policy": None}), (WindowsComputeAvailabilityMonitor, {"clock": 0}),
                (WindowsComputeAvailabilityMonitor, {"system_times": False}),
                (WindowsComputeAvailabilityMonitor, {"processor_count": None}),
                (WindowsComputeAvailabilityMonitor, {"policy": None}),
                (WindowsHardwareProfiler, {"storage_path": "T:/"}),
                (WindowsHardwareProfiler, {"accelerator_memory_reader": False})):
            with self.subTest(factory=factory.__name__, kwargs=kwargs), self.assertRaises(ValueError):
                factory(**kwargs)
        self.assertEqual(calls, [])

    def test_relative_storage_path_is_anchored_at_construction(self):
        paths = []
        monitor = StorageCapacityMonitor(path=Path("relative"), clock=lambda: 100, policy=self.policy(),
            disk_usage=lambda path: paths.append(path) or SimpleNamespace(total=0, free=0))
        expected = Path("relative").absolute()
        with patch("ceta.resource.hardware.Path.cwd", return_value=ROOT / "other"):
            monitor.sample()
        self.assertEqual(paths, [expected])

    def test_invalid_clock_precedes_native_probe_and_recovery_discards_cpu_baseline(self):
        for bad in (-1, True, 1 << 63, None, "100"):
            calls, now = [], [bad]
            monitor = self.storage(now, lambda path: calls.append(path) or SimpleNamespace(total=1000, free=600))
            with self.subTest(bad=bad), self.assertRaises(ValueError): monitor.sample()
            self.assertEqual(calls, [])
        now = [100]
        monitor = self.cpu(now, ((1000, 100), (2000, 200), (3000, 300)))
        monitor.sample()
        now[0] = True
        with self.assertRaises(ValueError): monitor.sample()
        now[0] = 110
        self.assert_unknown(monitor.sample(), "CPU_BASELINE_REQUIRED")
        now[0] = 120
        self.assertTrue(monitor.sample().free.measured)

    def test_storage_rollback_invalidates_cached_capacity_without_probe(self):
        now, calls = [100], []
        monitor = self.storage(now, lambda path: calls.append(path) or SimpleNamespace(total=1000, free=600))
        first = monitor.sample()
        now[0] = 99
        rollback = monitor.sample()
        self.assert_unknown(rollback, "RESOURCE_CLOCK_ROLLBACK")
        self.assertEqual((rollback.sequence, rollback.total.observed_monotonic_ns, len(calls)), (2, 100, 1))
        self.assertIsNot(rollback, first)
        self.assertIsNone(available_capacity(rollback, ResourceVector(0, 0, 0, 0), 99, 100))
        now[0] = 98
        self.assert_unknown(monitor.sample(), "RESOURCE_CLOCK_ROLLBACK")
        self.assertEqual(len(calls), 1)
        now[0] = 110
        self.assertTrue(monitor.sample().free.measured)

    def test_cpu_rollback_invalidates_cached_measurement_and_requires_fresh_baseline(self):
        now = [100]
        monitor = self.cpu(now, ((1000, 100), (2000, 500), (3000, 900), (4000, 1300)))
        monitor.sample()
        now[0] = 110
        self.assertTrue(monitor.sample().free.measured)
        now[0] = 109
        self.assert_unknown(monitor.sample(), "RESOURCE_CLOCK_ROLLBACK")
        now[0] = 120
        self.assert_unknown(monitor.sample(), "CPU_BASELINE_REQUIRED")
        now[0] = 130
        self.assertTrue(monitor.sample().free.measured)

    def test_counter_tuple_shape_and_absolute_bounds_are_enforced(self):
        malformed = [[], [1000, 100], (1000,), (1000, 100, 0), (True, 0), (1000, True),
                     (-1, 0), (1000, -1), (1000, 1001), (1 << 65, 0), (1 << 64, 1 << 64), ("1000", 100)]
        for frame in malformed:
            with self.subTest(frame=frame):
                self.assert_unknown(self.cpu([100], (frame,)).sample(), "CPU_QUERY_INVALID")

    def test_invalid_counter_deltas_remain_unavailable_and_do_not_seed_recovery(self):
        for frame in ((1000, 500), (999, 500), (1100, 400), (1100, 700)):
            now = [100]
            monitor = self.cpu(now, ((1000, 500), frame, (2000, 900), (2100, 950)))
            monitor.sample()
            now[0] = 110
            self.assert_unknown(monitor.sample(), "CPU_COUNTER_DELTA_INVALID")
            now[0] = 120
            self.assert_unknown(monitor.sample(), "CPU_BASELINE_REQUIRED")
            now[0] = 130
            self.assertEqual(monitor.sample().free.value, 2000)

    def test_measured_zero_and_full_idle_are_preserved_without_clamping(self):
        now = [100]
        monitor = self.cpu(now, ((1000, 500), (1100, 500), (1200, 600)))
        monitor.sample()
        now[0] = 110
        busy = monitor.sample()
        self.assertEqual((busy.free.measured, busy.free.value, busy.utilization_milli.value), (True, 0, 1000))
        now[0] = 120
        idle = monitor.sample()
        self.assertEqual((idle.free.value, idle.reservable.value, idle.utilization_milli.value), (4000, 4000, 0))

    def test_cpu_control_reserve_is_held_from_actual_idle_capacity(self):
        now, values = [100], iter(((1000, 100), (2000, 600)))
        monitor = WindowsComputeAvailabilityMonitor(clock=lambda: now[0], policy=self.policy(control_cpu_milli=60),
            system_times=lambda: next(values), processor_count=lambda: 4)
        monitor.sample()
        now[0] = 110
        observed = monitor.sample()
        self.assertEqual((observed.total.value, observed.free.value, observed.reservable.value), (4000, 2000, 1940))

    def test_cpu_long_baseline_interval_requires_new_baseline(self):
        now, values = [100], iter(((1000, 100), (2000, 600), (3000, 1100)))
        monitor = WindowsComputeAvailabilityMonitor(clock=lambda: now[0], policy=self.policy(maximum_sampling_interval_ns=20),
            system_times=lambda: next(values), processor_count=lambda: 4)
        monitor.sample()
        now[0] = 121
        self.assert_unknown(monitor.sample(), "CPU_BASELINE_REQUIRED")
        now[0] = 131
        self.assertTrue(monitor.sample().free.measured)

    def test_cpu_capacity_change_requires_new_baseline(self):
        now, count = [100], [4]
        monitor = self.cpu(now, ((1000, 100), (2000, 600), (3000, 1100)), count=lambda: count[0])
        monitor.sample()
        now[0], count[0] = 110, 8
        self.assert_unknown(monitor.sample(), "CPU_BASELINE_REQUIRED")
        now[0] = 120
        self.assertEqual(monitor.sample().total.value, 8000)

    def test_processor_scope_change_during_probe_is_unavailable(self):
        now, values = [100], iter((4, 8))
        monitor = self.cpu(now, ((1000, 100),), count=lambda: next(values))
        self.assert_unknown(monitor.sample(), "CPU_PROCESSOR_SCOPE_CHANGED")

    def test_boolean_post_probe_count_cannot_match_integer_capacity(self):
        counts = iter((1, True))
        monitor = self.cpu([100], ((1000, 100),), count=lambda: next(counts))
        self.assert_unknown(monitor.sample(), "CPU_PROCESSOR_SCOPE_CHANGED")

    def test_invalid_processor_count_values_never_reach_counter_probe(self):
        for count in (None, 0, -1, True, "4", 1 << 63):
            calls = []
            monitor = WindowsComputeAvailabilityMonitor(clock=lambda: 100, policy=self.policy(),
                processor_count=lambda: count, system_times=lambda: calls.append(1) or (1000, 100))
            self.assert_unknown(monitor.sample(), "CPU_QUERY_UNAVAILABLE")
            self.assertEqual(calls, [])

    def test_native_scope_must_be_one_matching_group_before_counter_read(self):
        for scope in (None, (2, 64), (1, 8)):
            with self.subTest(scope=scope), patch.object(WindowsComputeAvailabilityMonitor, "_native_processor_scope", return_value=scope), \
                    patch.object(WindowsComputeAvailabilityMonitor, "_system_times") as read:
                monitor = WindowsComputeAvailabilityMonitor(clock=lambda: 100, policy=self.policy(), processor_count=lambda: 4)
                self.assert_unknown(monitor.sample(), "CPU_PROCESSOR_GROUP_SCOPE_UNAVAILABLE")
                read.assert_not_called()

    def test_native_scope_is_checked_again_after_counter_probe(self):
        with patch.object(WindowsComputeAvailabilityMonitor, "_native_processor_scope", side_effect=((1, 4), None)), \
                patch.object(WindowsComputeAvailabilityMonitor, "_system_times", return_value=(1000, 100)):
            monitor = WindowsComputeAvailabilityMonitor(clock=lambda: 100, policy=self.policy(), processor_count=lambda: 4)
            self.assert_unknown(monitor.sample(), "CPU_PROCESSOR_SCOPE_CHANGED")

    def test_reader_failures_discard_cpu_baseline_and_recover(self):
        for failure in (None, OSError("probe"), RuntimeError("probe")):
            now, frames = [100], iter(((1000, 100), failure, (3000, 500), (4000, 900)))
            def read():
                frame = next(frames)
                if isinstance(frame, Exception): raise frame
                return frame
            monitor = WindowsComputeAvailabilityMonitor(clock=lambda: now[0], policy=self.policy(),
                system_times=read, processor_count=lambda: 4)
            monitor.sample()
            now[0] = 110
            self.assert_unknown(monitor.sample(), "CPU_QUERY_FAILED")
            now[0] = 120
            self.assert_unknown(monitor.sample(), "CPU_BASELINE_REQUIRED")
            now[0] = 130
            self.assertTrue(monitor.sample().free.measured)

    def test_cpu_interruptions_propagate_and_require_new_baseline(self):
        for interruption in (KeyboardInterrupt(), SystemExit(7)):
            now, frames = [100], iter(((1000, 100), interruption, (3000, 500), (4000, 900)))
            def read():
                value = next(frames)
                if isinstance(value, BaseException): raise value
                return value
            monitor = WindowsComputeAvailabilityMonitor(clock=lambda: now[0], policy=self.policy(),
                system_times=read, processor_count=lambda: 4)
            monitor.sample()
            now[0] = 110
            with self.assertRaises(type(interruption)): monitor.sample()
            now[0] = 120
            self.assert_unknown(monitor.sample(), "CPU_BASELINE_REQUIRED")
            now[0] = 130
            self.assertTrue(monitor.sample().free.measured)

    def test_storage_interruptions_propagate_and_do_not_reuse_old_cache(self):
        for interruption in (KeyboardInterrupt(), SystemExit(7)):
            now, count = [100], [0]
            def read(path):
                count[0] += 1
                if count[0] == 2: raise interruption
                return SimpleNamespace(total=1000, free=600)
            monitor = self.storage(now, read)
            monitor.sample()
            now[0] = 110
            with self.assertRaises(type(interruption)): monitor.sample()
            recovered = monitor.sample()
            self.assertEqual((recovered.sequence, count[0], recovered.free.measured), (3, 3, True))

    def test_delayed_storage_probe_rejects_late_measurement_then_recovers(self):
        now, delayed = [100], [True]
        def read(path):
            if delayed[0]: now[0] += 21
            return SimpleNamespace(total=1000, free=600)
        monitor = self.storage(now, read, maximum_probe_window_ns=20)
        self.assert_unknown(monitor.sample(), "RESOURCE_PROBE_WINDOW_EXCEEDED")
        now[0], delayed[0] = 131, False
        self.assertTrue(monitor.sample().free.measured)

    def test_delayed_cpu_probe_discards_baseline(self):
        now, calls = [100], [0]
        def read():
            calls[0] += 1
            if calls[0] == 2: now[0] += 21
            return 1000 * calls[0], 100 * calls[0]
        monitor = WindowsComputeAvailabilityMonitor(clock=lambda: now[0], policy=self.policy(maximum_probe_window_ns=20),
            system_times=read, processor_count=lambda: 4)
        monitor.sample()
        now[0] = 110
        self.assert_unknown(monitor.sample(), "RESOURCE_PROBE_WINDOW_EXCEEDED")
        now[0] = 141
        self.assert_unknown(monitor.sample(), "CPU_BASELINE_REQUIRED")
        now[0] = 151
        self.assertTrue(monitor.sample().free.measured)

    def test_probe_finish_rollback_preserves_high_water_and_denies_capacity(self):
        now = [100]
        def read(path):
            now[0] = 99
            return SimpleNamespace(total=1000, free=600)
        monitor = self.storage(now, read)
        result = monitor.sample()
        self.assert_unknown(result, "RESOURCE_CLOCK_ROLLBACK")
        self.assertEqual(result.total.observed_monotonic_ns, 100)
        self.assertIsNone(available_capacity(result, ResourceVector(0, 0, 0, 0), 99, 100))

    def test_cpu_probe_finish_rollback_requires_clean_baseline(self):
        now, fail = [100], [True]
        def read():
            if fail[0]: now[0] = 99
            return 1000, 100
        monitor = WindowsComputeAvailabilityMonitor(clock=lambda: now[0], policy=self.policy(),
            system_times=read, processor_count=lambda: 4)
        self.assert_unknown(monitor.sample(), "RESOURCE_CLOCK_ROLLBACK")
        now[0], fail[0] = 110, False
        self.assert_unknown(monitor.sample(), "CPU_BASELINE_REQUIRED")

    def test_storage_fields_and_optional_used_are_validated(self):
        for usage in (None, {}, SimpleNamespace(total=True, free=0), SimpleNamespace(total=-1, free=0),
                SimpleNamespace(total=1000, free=1001), SimpleNamespace(total=1 << 63, free=0),
                SimpleNamespace(total=1000, free=0.0), SimpleNamespace(total=1000, free=600, used=401),
                SimpleNamespace(total=1000, free=600, used=True)):
            with self.subTest(usage=usage):
                self.assert_unknown(self.storage([100], lambda path: usage).sample(), "STORAGE_QUERY_INVALID")

    def test_storage_zero_is_measured_and_evidence_reserve_stays_distinct(self):
        zero = self.storage([100], lambda path: SimpleNamespace(total=0, free=0, used=0)).sample()
        self.assertEqual((zero.total.measured, zero.total.value, zero.free.value, zero.reservable.value), (True, 0, 0, 0))
        # Pressure classifies utilization. A zero-byte measurement still has
        # zero allocatable bytes; a nonzero requirement must fail the budget.
        self.assertEqual(available_capacity(zero, ResourceVector(0, 0, 0, 0), 100, 100), 0)
        budget = BudgetEnvelope("budget.zero", ResourceVector(0, 0, 0, 0), ResourceVector(0, 0, 0, 0),
                                ResourceVector(0, 0, 0, 0), ResourceVector(0, 0, 0, 0), 1)
        self.assertFalse(assess_budget(budget, ResourceVector(0, 0, 1, 0))[0])
        result = self.storage([100], control_storage_bytes=500).sample()
        self.assertEqual((result.total.value, result.free.value, result.reservable.value), (1000, 600, 100))
        self.assertEqual(available_capacity(result, ResourceVector(0, 0, 90, 0), 100, 100), 10)
        self.assertEqual(available_capacity(result, ResourceVector(0, 0, 110, 0), 100, 100), 0)

    def test_storage_query_errors_have_explicit_unavailable_and_can_recover(self):
        for failure in (OSError("private path"), RuntimeError("private path")):
            now, fail = [100], [True]
            def read(path):
                if fail[0]: raise failure
                return SimpleNamespace(total=1000, free=600)
            monitor = self.storage(now, read)
            self.assert_unknown(monitor.sample(), "STORAGE_QUERY_FAILED")
            now[0], fail[0] = 110, False
            self.assertTrue(monitor.sample().free.measured)

    def assert_serialized_sampling(self, kind):
        entered, release, second_attempted = threading.Event(), threading.Event(), threading.Event()
        reads, errors, results = [], [], []
        def clock():
            reads.append(threading.current_thread().name)
            return 100
        def probe(*args):
            entered.set()
            if not release.wait(2): raise AssertionError("owned probe barrier timed out")
            return (1000, 100) if kind == "cpu" else SimpleNamespace(total=1000, free=600)
        monitor = (WindowsComputeAvailabilityMonitor(clock=clock, policy=self.policy(), system_times=probe, processor_count=lambda: 4)
                   if kind == "cpu" else StorageCapacityMonitor(path=ROOT, clock=clock, policy=self.policy(), disk_usage=probe))
        def collect(second=False):
            if second: second_attempted.set()
            try: results.append(monitor.sample())
            except BaseException as exc: errors.append(exc)
        first = threading.Thread(target=collect, name="first")
        second = threading.Thread(target=lambda: collect(True), name="second")
        first.start()
        try:
            self.assertTrue(entered.wait(2))
            second.start()
            self.assertTrue(second_attempted.wait(2))
            time.sleep(0.03)
            self.assertEqual(reads, ["first"])
        finally:
            release.set()
            first.join(2)
            if second.ident is not None: second.join(2)
        self.assertFalse(first.is_alive() or second.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 2)
        self.assertIs(results[0], results[1])

    def test_storage_clock_and_probe_are_serialized(self): self.assert_serialized_sampling("storage")
    def test_cpu_clock_and_probe_are_serialized(self): self.assert_serialized_sampling("cpu")

    def test_profiler_rejects_window_exceedance_as_one_coherent_unknown_profile(self):
        now = [100]
        def accelerator():
            now[0] = 121
            return (1000,)
        profiler = WindowsHardwareProfiler(clock=lambda: now[0], storage_path=ROOT,
            policy=self.policy(maximum_probe_window_ns=20), accelerator_memory_reader=accelerator)
        result = profiler.profile("profile.bound")
        for snapshot in (result.cpu, result.memory, result.storage, *result.accelerators):
            self.assert_unknown(snapshot, "RESOURCE_PROBE_WINDOW_EXCEEDED")
            self.assertEqual((snapshot.sequence, snapshot.total.observed_monotonic_ns), (1, 121))
        self.assertEqual(result.measured_monotonic_ns, 121)
        self.assertEqual(result.isolation_available.reason, "RESOURCE_PROBE_WINDOW_EXCEEDED")

    def test_profiler_rollback_skips_probes_and_does_not_lower_high_water(self):
        now, calls = [100], []
        profiler = WindowsHardwareProfiler(clock=lambda: now[0], storage_path=ROOT, policy=self.policy(),
            accelerator_memory_reader=lambda: calls.append(1) or (1000,))
        profiler.profile("profile.first")
        now[0] = 99
        result = profiler.profile("profile.rollback")
        self.assert_unknown(result.cpu, "RESOURCE_CLOCK_ROLLBACK")
        self.assertEqual((len(calls), result.measured_monotonic_ns, result.cpu.sequence), (1, 100, 2))

    def test_profiler_keeps_earliest_time_and_static_accelerator_semantics(self):
        now = [100]
        def accelerator():
            now[0] = 110
            return (0, 1000)
        result = WindowsHardwareProfiler(clock=lambda: now[0], storage_path=ROOT, policy=self.policy(),
            accelerator_memory_reader=accelerator).profile("profile.coherent")
        self.assertEqual((result.measured_monotonic_ns, result.cpu.total.observed_monotonic_ns), (110, 100))
        for item in result.accelerators:
            self.assertTrue(item.total.measured)
            self.assertEqual(item.free.reason, "ACCELERATOR_RUNTIME_AVAILABILITY_NOT_OBSERVED")
            self.assertIsNone(available_capacity(item, ResourceVector(0, 0, 0, 0), 110, 100))

    def test_profiler_rejects_oversized_accelerator_capacity(self):
        profiler = WindowsHardwareProfiler(clock=lambda: 100, storage_path=ROOT, policy=self.policy(),
            accelerator_memory_reader=lambda: (1 << 63,))
        self.assert_unknown(profiler.profile("profile.invalid").accelerators[0], "ACCELERATOR_QUERY_INVALID")

    def test_profiler_malformed_native_memory_fields_are_unavailable(self):
        class NativeFunction:
            def __init__(self, total, free, load): self.values = total, free, load
            def __call__(self, pointer):
                status = pointer._obj
                status.ullTotalPhys, status.ullAvailPhys, status.dwMemoryLoad = self.values
                return 1
        profiler = WindowsHardwareProfiler(clock=lambda: 100, storage_path=ROOT, policy=self.policy(),
            accelerator_memory_reader=lambda: ())
        for values in ((1000, 1001, 20), (1 << 63, 0, 0), (1000, 500, 101)):
            kernel = SimpleNamespace(GlobalMemoryStatusEx=NativeFunction(*values))
            with self.subTest(values=values), patch("ceta.resource.hardware.ctypes.WinDLL", return_value=kernel):
                self.assert_unknown(profiler._memory(100, 1), "MEMORY_QUERY_INVALID")

    def test_native_kernel_idle_invariant_rejects_corrupt_filetime_fields(self):
        class NativeFunction:
            def __call__(self, idle, kernel, user):
                idle._obj.dwLowDateTime = 100
                kernel._obj.dwLowDateTime = 99
                user._obj.dwLowDateTime = 1000
                return 1
        with patch("ceta.resource.hardware.ctypes.WinDLL", return_value=SimpleNamespace(GetSystemTimes=NativeFunction())):
            self.assertIsNone(WindowsComputeAvailabilityMonitor._system_times())

    def test_profiler_storage_invalid_fields_remain_unavailable(self):
        profiler = WindowsHardwareProfiler(clock=lambda: 100, storage_path=ROOT, policy=self.policy(),
            accelerator_memory_reader=lambda: ())
        with patch("ceta.resource.hardware.shutil.disk_usage", return_value=SimpleNamespace(total=1000, free=2000)):
            self.assert_unknown(profiler.profile("profile.storage.invalid").storage, "STORAGE_QUERY_INVALID")

    def test_profiler_sequences_and_entire_probe_windows_are_serialized(self):
        active, maximum, guard = [0], [0], threading.Lock()
        def accelerator():
            with guard:
                active[0] += 1
                maximum[0] = max(maximum[0], active[0])
            time.sleep(0.01)
            with guard: active[0] -= 1
            return (0,)
        profiler = WindowsHardwareProfiler(clock=lambda: 100, storage_path=ROOT, policy=self.policy(),
            accelerator_memory_reader=accelerator)
        results, errors = [], []
        def run(index):
            try: results.append(profiler.profile("profile.concurrent." + str(index)))
            except BaseException as exc: errors.append(exc)
        workers = [threading.Thread(target=run, args=(i,)) for i in range(4)]
        for worker in workers: worker.start()
        for worker in workers: worker.join(3)
        self.assertFalse(any(worker.is_alive() for worker in workers))
        self.assertEqual(errors, [])
        self.assertEqual(maximum[0], 1)
        self.assertEqual(sorted(item.cpu.sequence for item in results), [1, 2, 3, 4])

    def test_default_elapsed_fence_rejects_zero_coarse_delta_overlong_probes(self):
        for kind in ("storage", "cpu", "profile"):
            values = iter((1000, 1000, 1101))
            if kind == "storage":
                owner = StorageCapacityMonitor(path=ROOT, policy=self.policy(),
                    disk_usage=lambda path: SimpleNamespace(total=1000, free=600))
                operation = owner.sample
            elif kind == "cpu":
                owner = WindowsComputeAvailabilityMonitor(policy=self.policy(),
                    system_times=lambda: (1000, 100), processor_count=lambda: 4)
                operation = owner.sample
            else:
                owner = WindowsHardwareProfiler(storage_path=ROOT, policy=self.policy(),
                    accelerator_memory_reader=lambda: (1000,))
                operation = lambda: owner.profile("profile.elapsed")
            self.assertIsNotNone(owner._timeline._elapsed_clock)
            owner._timeline._clock = lambda: 100  # emulate one unchanged coarse tick
            owner._timeline._elapsed_clock = lambda: next(values)
            result = operation()
            if kind == "profile": result = result.storage
            self.assert_unknown(result, "RESOURCE_PROBE_WINDOW_EXCEEDED")

    def test_default_elapsed_age_prevents_stale_cache_even_when_coarse_tick_is_unchanged(self):
        calls, elapsed = [], iter((1000, 1000, 1001, 1101, 1101, 1102))
        owner = StorageCapacityMonitor(path=ROOT, policy=self.policy(),
            disk_usage=lambda path: calls.append(path) or SimpleNamespace(total=1000, free=600))
        owner._timeline._clock = lambda: 100
        owner._timeline._elapsed_clock = lambda: next(elapsed)
        first, second = owner.sample(), owner.sample()
        self.assertEqual((first.sequence, second.sequence, len(calls)), (1, 2, 2))
        self.assertIsNot(first, second)
        self.assertEqual((first.total.observed_monotonic_ns, second.total.observed_monotonic_ns), (100, 100))

    def test_default_elapsed_minimum_interval_survives_coarse_clock_boundary_jump(self):
        calls, elapsed, coarse = [], iter((1000, 1000, 1001, 1002, 1002)), iter((100, 100, 120))
        owner = StorageCapacityMonitor(path=ROOT, policy=self.policy(),
            disk_usage=lambda path: calls.append(path) or SimpleNamespace(total=1000, free=600))
        owner._timeline._clock = lambda: next(coarse)
        owner._timeline._elapsed_clock = lambda: next(elapsed)
        first, cached = owner.sample(), owner.sample()
        self.assertIs(first, cached)
        self.assertEqual(len(calls), 1)

    def test_default_elapsed_maximum_interval_expires_cache_before_maximum_age(self):
        elapsed, calls = iter((1000, 1000, 1001, 1021, 1021, 1022)), []
        owner = StorageCapacityMonitor(path=ROOT, policy=self.policy(maximum_sampling_interval_ns=20),
            disk_usage=lambda path: calls.append(path) or SimpleNamespace(total=1000, free=600))
        owner._timeline._clock = lambda: 100
        owner._timeline._elapsed_clock = lambda: next(elapsed)
        first, fresh = owner.sample(), owner.sample()
        self.assertIsNot(first, fresh)
        self.assertEqual((fresh.sequence, len(calls)), (2, 2))

    def test_default_elapsed_cpu_interval_reestablishes_baseline_with_unchanged_coarse_tick(self):
        elapsed, frames = iter((1000, 1000, 1001, 1101, 1101, 1102, 1111, 1111, 1112)), iter(((1000, 100), (2000, 200), (3000, 300)))
        owner = WindowsComputeAvailabilityMonitor(policy=self.policy(), system_times=lambda: next(frames), processor_count=lambda: 4)
        owner._timeline._clock = lambda: 100
        owner._timeline._elapsed_clock = lambda: next(elapsed)
        self.assert_unknown(owner.sample(), "CPU_BASELINE_REQUIRED")
        self.assert_unknown(owner.sample(), "CPU_BASELINE_REQUIRED")
        # Explicitly expire the coarse cache after the reset to exercise the
        # next valid counter interval while retaining its real elapsed bound.
        owner._timeline._clock = lambda: 110
        self.assertTrue(owner.sample().free.measured)

    def test_default_elapsed_rollback_is_explicit_and_preserves_high_water(self):
        elapsed, calls = iter((1000, 1000, 999, 998, 998)), []
        owner = StorageCapacityMonitor(path=ROOT, policy=self.policy(),
            disk_usage=lambda path: calls.append(path) or SimpleNamespace(total=1000, free=600))
        owner._timeline._clock = lambda: 100
        owner._timeline._elapsed_clock = lambda: next(elapsed)
        self.assert_unknown(owner.sample(), "RESOURCE_ELAPSED_CLOCK_ROLLBACK")
        self.assert_unknown(owner.sample(), "RESOURCE_ELAPSED_CLOCK_ROLLBACK")
        self.assertEqual((owner._timeline._elapsed_high_water, len(calls)), (1000, 1))

    def test_invalid_default_elapsed_clock_rejects_before_native_read(self):
        calls = []
        owner = StorageCapacityMonitor(path=ROOT, policy=self.policy(),
            disk_usage=lambda path: calls.append(path) or SimpleNamespace(total=1000, free=600))
        owner._timeline._elapsed_clock = lambda: True
        with self.assertRaises(ValueError): owner.sample()
        self.assertEqual(calls, [])

    def test_default_elapsed_cache_age_is_rechecked_after_delayed_public_clock_lookup(self):
        elapsed, delayed, calls = [1000], [False], []
        def coarse():
            if delayed[0]: elapsed[0] = 1101
            return 100
        owner = StorageCapacityMonitor(path=ROOT, policy=self.policy(),
            disk_usage=lambda path: calls.append(path) or SimpleNamespace(total=1000, free=600))
        owner._timeline._clock = coarse
        owner._timeline._elapsed_clock = lambda: elapsed[0]
        first = owner.sample()
        self.assertTrue(first.free.measured)
        delayed[0] = True
        rejected = owner.sample()
        self.assert_unknown(rejected, "RESOURCE_PROBE_WINDOW_EXCEEDED")
        self.assertEqual((rejected.sequence, len(calls)), (2, 2))
        self.assertIsNot(rejected, first)


class NativeHardwareObservationTests(unittest.TestCase):
    def fixture(self):
        directory = ROOT / ".agents/fixtures"
        directory.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(prefix="hd2-native-", dir=directory)

    def wait_interval(self, snapshot, policy):
        # Python 3.12's Windows monotonic default is GetTickCount64. Wait for
        # observed clock advancement, rather than assuming a 3 ms sleep moves it.
        deadline = time.perf_counter() + 1
        while time.monotonic_ns() - snapshot.total.observed_monotonic_ns < policy.minimum_interval_ns:
            self.assertLess(time.perf_counter(), deadline, "native monotonic clock did not advance")
            time.sleep(0.002)

    def test_native_disposable_storage_capacity_pressure_and_reservation_subtraction(self):
        self.assertEqual(os.name, "nt")
        with self.fixture() as folder:
            path = Path(folder)
            payload = path / "owned-sampling-fixture.bin"
            payload.write_bytes(b"ceta-hd2-native\0" * 65536)
            digest = hashlib.sha256(payload.read_bytes()).hexdigest()
            policy = SamplingPolicy(minimum_interval_ns=1_000_000, control_storage_bytes=4096)
            monitor = StorageCapacityMonitor(path=path, policy=policy)
            first = monitor.sample()
            self.assertTrue(first.total.measured)
            self.assertEqual(first.reservable.value, max(0, first.free.value - 4096))
            detector = ResourcePressureDetector()
            first_decision = detector.observe(first, current=True)
            self.assertEqual(first_decision.admission_open, first.utilization_milli.value < 800)
            self.wait_interval(first, policy)
            fresh = monitor.sample()
            self.assertGreater(fresh.sequence, first.sequence)
            self.assertGreater(fresh.total.observed_monotonic_ns, first.total.observed_monotonic_ns)
            now = time.monotonic_ns()
            self.assertEqual(available_capacity(fresh, ResourceVector(0, 0, 1, 0), now, policy.maximum_age_ns),
                             max(0, fresh.reservable.value - 1))
            self.assertIsNone(available_capacity(fresh, ResourceVector(0, 0, 0, 0), now + policy.maximum_age_ns + 1, policy.maximum_age_ns))
            self.assertEqual(hashlib.sha256(payload.read_bytes()).hexdigest(), digest)
            NATIVE_OBSERVATIONS.append({"test": self.id(), "fixture_sha256": digest,
                "total_bytes": fresh.total.value, "free_bytes": fresh.free.value, "reservable_bytes": fresh.reservable.value,
                "sequence": fresh.sequence, "method": fresh.total.method, "pressure": first_decision.level.value})
        self.assertFalse(path.exists())

    def test_native_storage_delayed_read_is_unavailable_and_recovery_is_measured(self):
        with self.fixture() as folder:
            path, delayed = Path(folder), [True]
            def read(target):
                value = shutil.disk_usage(target)
                if delayed[0]: time.sleep(0.05)
                return value
            policy = SamplingPolicy(maximum_age_ns=200_000_000, minimum_interval_ns=1_000_000,
                                    maximum_probe_window_ns=20_000_000)
            monitor = StorageCapacityMonitor(path=path, policy=policy, disk_usage=read)
            started = time.monotonic_ns()
            late = monitor.sample()
            elapsed = time.monotonic_ns() - started
            self.assertFalse(late.free.measured)
            self.assertEqual(late.free.reason, "RESOURCE_PROBE_WINDOW_EXCEEDED")
            delayed[0] = False
            self.wait_interval(late, policy)
            self.assertTrue(monitor.sample().free.measured)
            NATIVE_OBSERVATIONS.append({"test": self.id(), "actual_native_read": "shutil.disk_usage",
                "injected_delay_ns": 50_000_000, "elapsed_ns": elapsed, "reason": late.free.reason})
        self.assertFalse(path.exists())

    def test_native_cpu_qualified_scope_actual_counters_cache_and_pressure_consumer(self):
        self.assertEqual(os.name, "nt")
        scope = WindowsComputeAvailabilityMonitor._native_processor_scope()
        policy = SamplingPolicy(minimum_interval_ns=10_000_000, maximum_probe_window_ns=500_000_000)
        monitor = WindowsComputeAvailabilityMonitor(policy=policy)
        first = monitor.sample()
        self.assertFalse(first.free.measured)
        if scope is None or scope[1] != os.cpu_count():
            self.assertEqual(first.free.reason, "CPU_PROCESSOR_GROUP_SCOPE_UNAVAILABLE")
            NATIVE_OBSERVATIONS.append({"test": self.id(), "scope": scope, "state": "UNAVAILABLE", "reason": first.free.reason})
            return
        self.assertEqual(first.free.reason, "CPU_BASELINE_REQUIRED")
        self.assertIs(monitor.sample(), first)
        detector, measured = ResourcePressureDetector(), []
        self.assertFalse(detector.observe(first, current=True).admission_open)
        for _ in range(4):
            time.sleep(0.015)
            result = monitor.sample()
            if result.free.measured:
                measured.append(result)
                self.assertEqual(result.total.value, scope[1] * 1000)
                self.assertLessEqual(result.free.value, result.total.value)
                decision = detector.observe(result, current=True)
                if decision.admission_open: self.assertLess(result.utilization_milli.value, 800)
        self.assertTrue(measured)
        NATIVE_OBSERVATIONS.append({"test": self.id(), "scope": scope, "measured_frames": len(measured),
            "latest_total_milli": measured[-1].total.value, "latest_free_milli": measured[-1].free.value,
            "latest_sequence": measured[-1].sequence, "method": measured[-1].total.method})

    def test_native_cpu_injected_scheduling_delay_rejects_actual_counter_frame(self):
        scope = WindowsComputeAvailabilityMonitor._native_processor_scope()
        if scope is None:
            self.assertEqual(WindowsComputeAvailabilityMonitor().sample().free.reason,
                             "CPU_PROCESSOR_GROUP_SCOPE_UNAVAILABLE")
            NATIVE_OBSERVATIONS.append({"test": self.id(), "scope": scope, "delay_case": "SCOPE_UNAVAILABLE"})
            return
        delayed = [True]
        def read():
            value = WindowsComputeAvailabilityMonitor._system_times()
            if delayed[0]: time.sleep(0.05)
            return value
        policy = SamplingPolicy(maximum_age_ns=200_000_000, minimum_interval_ns=1_000_000,
                                maximum_probe_window_ns=20_000_000)
        monitor = WindowsComputeAvailabilityMonitor(policy=policy, system_times=read, processor_count=lambda: scope[1])
        started = time.monotonic_ns()
        late = monitor.sample()
        elapsed = time.monotonic_ns() - started
        self.assertEqual(late.free.reason, "RESOURCE_PROBE_WINDOW_EXCEEDED")
        delayed[0] = False
        self.wait_interval(late, policy)
        baseline = monitor.sample()
        self.assertEqual(baseline.free.reason, "CPU_BASELINE_REQUIRED")
        time.sleep(0.025)
        self.wait_interval(baseline, policy)
        self.assertTrue(monitor.sample().free.measured)
        NATIVE_OBSERVATIONS.append({"test": self.id(), "scope": scope, "actual_native_read": "GetSystemTimes",
            "injected_delay_ns": 50_000_000, "elapsed_ns": elapsed, "reason": late.free.reason})

    def test_native_profiler_is_coherent_and_keeps_static_memory_separate(self):
        with self.fixture() as folder:
            profile = WindowsHardwareProfiler(storage_path=Path(folder)).profile("profile.native.hd2")
            observations = [profile.cpu, profile.memory, profile.storage, *profile.accelerators]
            self.assertTrue(profile.cpu.total.measured)
            self.assertTrue(profile.memory.total.measured)
            self.assertTrue(profile.storage.total.measured)
            self.assertEqual(profile.cpu.free.reason, "AVAILABILITY_REQUIRES_RUNTIME_SAMPLE")
            self.assertTrue(all(item.sequence == profile.cpu.sequence for item in observations))
            self.assertEqual(len({item.total.observed_monotonic_ns for item in observations}), 1)
            self.assertLessEqual(profile.cpu.total.observed_monotonic_ns, profile.measured_monotonic_ns)
            for item in profile.accelerators: self.assertFalse(item.free.measured)
            NATIVE_OBSERVATIONS.append({"test": self.id(), "cpu_total_milli": profile.cpu.total.value,
                "memory_total_bytes": profile.memory.total.value, "storage_total_bytes": profile.storage.total.value,
                "accelerator_totals": [item.total.value for item in profile.accelerators],
                "generation": profile.cpu.sequence, "probe_window_ns": profile.measured_monotonic_ns - profile.cpu.total.observed_monotonic_ns})

    def test_native_unknown_capacity_and_missing_profile_deny_reservation_dispatch(self):
        class DeniedOwnerPort:
            def __init__(self): self.calls = 0
            def reserve(self, request):
                self.calls += 1
                raise AssertionError("this read-only native qualification must not dispatch reservations")
        with self.fixture() as folder:
            def delayed_read(target):
                usage = shutil.disk_usage(target)
                time.sleep(0.05)
                return usage
            policy = SamplingPolicy(maximum_age_ns=200_000_000, minimum_interval_ns=1_000_000,
                                    maximum_probe_window_ns=20_000_000)
            snapshot = StorageCapacityMonitor(path=Path(folder), policy=policy, disk_usage=delayed_read).sample()
            self.assertFalse(snapshot.free.measured)
            pressure = ResourcePressureDetector().observe(snapshot, current=True)
            self.assertFalse(pressure.admission_open)
            owner = DeniedOwnerPort()
            controller = WorkloadAdmissionController(owner)
            zero = ResourceVector(0, 0, 0, 0)
            budget = BudgetEnvelope("budget.native.denied", zero, zero, zero, zero, 0)
            estimate = WorkloadEstimate("workload.native.denied", None, 0, snapshot.total.method,
                state="UNRESOLVED", confidence_milli=0, reason_code="CANONICAL_WORKLOAD_PROFILE_NOT_AVAILABLE")
            result = controller.admit(AdmissionRequest("request.native.denied", budget, estimate,
                snapshot.sequence, snapshot.total.observed_monotonic_ns, False, pressure.level))
            self.assertEqual((result.state, result.reason_codes, owner.calls),
                             (AdmissionState.STALE, ("CAPACITY_OBSERVATION_STALE",), 0))
            NATIVE_OBSERVATIONS.append({"test": self.id(), "native_reason": snapshot.free.reason,
                "pressure": pressure.level.value, "admission_state": result.state.value, "owner_dispatches": owner.calls,
                "qualification": "actual native producer through real negative consumer path; no positive owner integration"})

    def test_native_high_resolution_probe_fence_rejects_six_ms_read_with_five_ms_bound(self):
        with self.fixture() as folder:
            def read(target):
                value = shutil.disk_usage(target)
                time.sleep(0.006)
                return value
            policy = SamplingPolicy(maximum_age_ns=200_000_000, minimum_interval_ns=1_000_000,
                                    maximum_probe_window_ns=5_000_000)
            owner = StorageCapacityMonitor(path=Path(folder), policy=policy, disk_usage=read)
            started, coarse_started = time.perf_counter_ns(), time.monotonic_ns()
            result = owner.sample()
            elapsed, coarse_delta = time.perf_counter_ns() - started, time.monotonic_ns() - coarse_started
            self.assertEqual(result.free.reason, "RESOURCE_PROBE_WINDOW_EXCEEDED")
            self.assertGreater(elapsed, policy.probe_window_ns)
            NATIVE_OBSERVATIONS.append({"test": self.id(), "native_read": "shutil.disk_usage", "injected_delay_ns": 6_000_000,
                "high_resolution_elapsed_ns": elapsed, "coarse_delta_ns": coarse_delta, "bound_ns": policy.probe_window_ns,
                "reason": result.free.reason})


if __name__ == "__main__": unittest.main()

