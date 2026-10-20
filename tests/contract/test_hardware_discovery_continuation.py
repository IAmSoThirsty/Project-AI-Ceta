"""CETA-20.01.02 affinity visibility, invalidation and recovery obligations."""
import ctypes
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from ceta.contracts.resource_management import ResourceVector
from ceta.resource.hardware import SamplingPolicy, WindowsComputeAvailabilityMonitor, available_capacity
from ceta.resource.pressure import ResourcePressureDetector


class NativeFunction:
    def __init__(self, operation):
        self.operation = operation

    def __call__(self, *args):
        return self.operation(*args)


class AffinityDiscoveryTests(unittest.TestCase):
    def kernel(self, process=15, system=15, processors=4, groups=1, success=1):
        calls = []
        def affinity(handle, process_out, system_out):
            calls.append(handle)
            process_out._obj.value = process
            system_out._obj.value = system
            return success
        kernel = SimpleNamespace(
            GetActiveProcessorGroupCount=NativeFunction(lambda: groups),
            GetActiveProcessorCount=NativeFunction(lambda group: processors),
            GetCurrentProcess=NativeFunction(lambda: -1),
            GetProcessAffinityMask=NativeFunction(affinity))
        return kernel, calls

    def monitor(self, now, read):
        policy = SamplingPolicy(maximum_age_ns=100, minimum_interval_ns=10, control_cpu_milli=50)
        with patch.object(WindowsComputeAvailabilityMonitor, '_system_times', side_effect=read):
            return WindowsComputeAvailabilityMonitor(clock=lambda: now[0], policy=policy,
                                                     processor_count=lambda: 4)

    def test_matching_noncontiguous_masks_qualify_and_use_pointer_sized_outputs(self):
        kernel, calls = self.kernel(process=0b10101010, system=0b10101010)
        with patch('ceta.resource.hardware.ctypes.WinDLL', return_value=kernel):
            self.assertEqual(WindowsComputeAvailabilityMonitor._native_processor_scope(), (1, 4))
        self.assertEqual(calls, [-1])
        self.assertEqual(kernel.GetProcessAffinityMask.argtypes,
                         (ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t)))
        self.assertEqual(kernel.GetCurrentProcess.restype, ctypes.c_void_p)

    def test_restricted_zero_inconsistent_and_failed_masks_are_unavailable(self):
        for values in ({'process': 1}, {'process': 0}, {'process': 0, 'system': 0},
                       {'system': 7, 'process': 7}, {'process': 31}, {'success': 0}):
            kernel, _ = self.kernel(**values)
            with self.subTest(values=values), patch('ceta.resource.hardware.ctypes.WinDLL', return_value=kernel):
                self.assertIsNone(WindowsComputeAvailabilityMonitor._native_processor_scope())

    def test_unsupported_groups_and_counts_do_not_probe_affinity(self):
        for values in ({'groups': 2}, {'processors': 0}, {'processors': 65}):
            kernel, calls = self.kernel(**values)
            with self.subTest(values=values), patch('ceta.resource.hardware.ctypes.WinDLL', return_value=kernel):
                self.assertIsNone(WindowsComputeAvailabilityMonitor._native_processor_scope())
            self.assertEqual(calls, [])

    def test_missing_and_failed_native_affinity_are_unknown_without_diagnostic_leak(self):
        for failure in (AttributeError('private diagnostic'), OSError('private diagnostic')):
            kernel, _ = self.kernel()
            kernel.GetProcessAffinityMask = NativeFunction(lambda *args: (_ for _ in ()).throw(failure))
            with self.subTest(failure=type(failure)), patch('ceta.resource.hardware.ctypes.WinDLL', return_value=kernel):
                self.assertIsNone(WindowsComputeAvailabilityMonitor._native_processor_scope())

    def test_restricted_affinity_blocks_counter_probe_and_real_capacity_consumers(self):
        kernel, _ = self.kernel(process=1)
        monitor = self.monitor([100], lambda: self.fail('counter probe outside qualified scope'))
        with patch('ceta.resource.hardware.ctypes.WinDLL', return_value=kernel):
            result = monitor.sample()
        self.assertEqual(result.free.reason, 'CPU_PROCESSOR_GROUP_SCOPE_UNAVAILABLE')
        self.assertIsNone(available_capacity(result, ResourceVector(0, 0, 0, 0), 100, 100))
        self.assertFalse(ResourcePressureDetector().observe(result, current=True).admission_open)

    def test_affinity_change_invalidates_positive_cache_and_requires_new_baseline(self):
        now, frames = [100], iter(((1000, 100), (2000, 1100), (3000, 1200), (4000, 1700)))
        monitor = self.monitor(now, lambda: next(frames))
        unrestricted, _ = self.kernel()
        restricted, _ = self.kernel(process=1)
        with patch('ceta.resource.hardware.ctypes.WinDLL', return_value=unrestricted):
            self.assertEqual(monitor.sample().free.reason, 'CPU_BASELINE_REQUIRED')
            now[0] = 110
            measured = monitor.sample()
            self.assertEqual((measured.free.value, measured.reservable.value), (4000, 3950))
            self.assertEqual(available_capacity(measured, ResourceVector(900, 0, 0, 0), 110, 100), 3050)
            self.assertIs(monitor.sample(), measured)
        now[0] = 111  # Inside the minimum interval: cached positive capacity must be fenced.
        with patch('ceta.resource.hardware.ctypes.WinDLL', return_value=restricted):
            denied = monitor.sample()
            self.assertEqual(denied.free.reason, 'CPU_PROCESSOR_GROUP_SCOPE_UNAVAILABLE')
        self.assertEqual(denied.sequence, measured.sequence + 1)
        self.assertFalse(ResourcePressureDetector().observe(denied, current=True).admission_open)
        now[0] = 121
        with patch('ceta.resource.hardware.ctypes.WinDLL', return_value=unrestricted):
            self.assertEqual(monitor.sample().free.reason, 'CPU_BASELINE_REQUIRED')
            now[0] = 131
            self.assertEqual(monitor.sample().free.value, 2000)

    def test_affinity_changes_during_counter_read_are_rejected(self):
        kernel, _ = self.kernel()
        now = [100]
        def read():
            kernel.GetProcessAffinityMask = self.kernel(process=1)[0].GetProcessAffinityMask
            return 1000, 100
        monitor = self.monitor(now, read)
        with patch('ceta.resource.hardware.ctypes.WinDLL', return_value=kernel):
            self.assertEqual(monitor.sample().free.reason, 'CPU_PROCESSOR_SCOPE_CHANGED')

    def test_transient_cache_scope_conflict_cannot_bridge_old_counter_baseline(self):
        now, frames, reads = [100], iter(((1000, 100), (2000, 1100), (3000, 1200), (4000, 1700))), []
        def read():
            reads.append(now[0])
            return next(frames)
        monitor = self.monitor(now, read)
        with patch.object(monitor, '_native_processor_scope', return_value=(1, 4)):
            monitor.sample()
            now[0] = 110
            self.assertEqual(monitor.sample().reservable.value, 3950)
        now[0] = 111
        with patch.object(monitor, '_native_processor_scope', side_effect=(None, (1, 4), (1, 4))) as scope:
            conflict = monitor.sample()
        self.assertEqual(conflict.free.reason, 'CPU_PROCESSOR_GROUP_SCOPE_UNAVAILABLE')
        self.assertEqual((scope.call_count, reads), (1, [100, 110]))
        self.assertIsNone(monitor._previous)
        self.assertIsNone(available_capacity(conflict, ResourceVector(0, 0, 0, 0), 111, 100))
        with patch.object(monitor, '_native_processor_scope', return_value=(1, 4)):
            now[0] = 121
            self.assertEqual(monitor.sample().free.reason, 'CPU_BASELINE_REQUIRED')
            now[0] = 131
            self.assertEqual(monitor.sample().free.value, 2000)
        self.assertEqual(reads, [100, 110, 121, 131])

    def test_delayed_affinity_cache_check_cannot_return_precheck_capacity(self):
        for elapsed_only in (False, True):
            now, elapsed, frames = [100], [1000], iter(((1000, 100), (2000, 1100)))
            monitor = self.monitor(now, lambda: next(frames))
            if elapsed_only:
                monitor._timeline._elapsed_clock = lambda: elapsed[0]
            kernel, _ = self.kernel()
            with self.subTest(elapsed_only=elapsed_only), patch('ceta.resource.hardware.ctypes.WinDLL', return_value=kernel):
                monitor.sample()
                now[0], elapsed[0] = 110, 1010
                measured = monitor.sample()
                original = kernel.GetProcessAffinityMask
                def delayed(*args):
                    if elapsed_only:
                        elapsed[0] += 101
                    else:
                        now[0] += 101
                    return original(*args)
                kernel.GetProcessAffinityMask = NativeFunction(delayed)
                rejected = monitor.sample()
                self.assertIsNot(rejected, measured)
                self.assertEqual(rejected.free.reason, 'RESOURCE_PROBE_WINDOW_EXCEEDED')
                self.assertIsNone(available_capacity(rejected, ResourceVector(0, 0, 0, 0), now[0], 100))

    def test_affinity_interruption_propagates_and_recovery_has_no_old_baseline(self):
        now = [100]
        for interruption in (KeyboardInterrupt(), SystemExit(7)):
            frames = iter(((1000, 100), (2000, 1100), (3000, 1200)))
            monitor = self.monitor(now, lambda: next(frames))
            kernel, _ = self.kernel()
            with patch('ceta.resource.hardware.ctypes.WinDLL', return_value=kernel):
                now[0] = 100
                monitor.sample()
                now[0] = 110
                monitor.sample()
                original = kernel.GetProcessAffinityMask
                kernel.GetProcessAffinityMask = NativeFunction(lambda *args: (_ for _ in ()).throw(interruption))
                now[0] = 111
                with self.assertRaises(type(interruption)):
                    monitor.sample()
                kernel.GetProcessAffinityMask = original
                self.assertEqual(monitor.sample().free.reason, 'CPU_BASELINE_REQUIRED')

    def test_cache_age_is_rechecked_at_exact_probe_bound(self):
        now, elapsed, frames = [100], [1000], iter(((1000, 100), (2000, 1100), (3000, 1200)))
        monitor = self.monitor(now, lambda: next(frames))
        monitor._timeline._elapsed_clock = lambda: elapsed[0]
        kernel, _ = self.kernel()
        with patch('ceta.resource.hardware.ctypes.WinDLL', return_value=kernel):
            monitor.sample()
            now[0], elapsed[0] = 110, 1010
            measured = monitor.sample()
            now[0], elapsed[0] = 111, 1011
            original = kernel.GetProcessAffinityMask
            delayed = [False]
            def read(*args):
                if not delayed[0]:
                    elapsed[0] += 100
                    delayed[0] = True
                return original(*args)
            kernel.GetProcessAffinityMask = NativeFunction(read)
            result = monitor.sample()
        self.assertIsNot(result, measured)
        self.assertEqual(result.free.reason, 'CPU_BASELINE_REQUIRED')

    def test_concurrent_cached_requests_serialize_affinity_reads(self):
        now, frames = [100], iter(((1000, 100), (2000, 1100)))
        monitor = self.monitor(now, lambda: next(frames))
        kernel, _ = self.kernel()
        with patch('ceta.resource.hardware.ctypes.WinDLL', return_value=kernel):
            monitor.sample()
            now[0] = 110
            expected = monitor.sample()
            results = []
            workers = [threading.Thread(target=lambda: results.append(monitor.sample())) for _ in range(4)]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join(2)
            self.assertFalse(any(worker.is_alive() for worker in workers))
            self.assertEqual(len(results), 4)
            self.assertTrue(all(result is expected for result in results))


if __name__ == '__main__':
    unittest.main()
