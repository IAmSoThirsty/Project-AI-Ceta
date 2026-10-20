"""NC1 native observation and explicitly controlled failure/scheduling fixtures."""
from pathlib import Path
import ctypes as C
from dataclasses import asdict, replace
from datetime import datetime, timezone
import inspect
import sys
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from ceta.identity import native_clock as module
from ceta.contracts.temporal import issue_deadline, require_clock_progress, require_deadline_current
from ceta.contracts.wire import ContractError, MAX_INTEGER

NATIVE_OBSERVATIONS = []
GUID = '12345678-1234-4234-8234-123456789abc'


def frame(index=0, **changes):
    offset = index * 10_000_000
    value = module._NativeFrame(GUID, GUID, 32, 2, 1_000_000_000,
        10_000_000_000 + offset, 10_000_001_000 + offset,
        1_792_000_000_000_000_000 + offset, 1_792_000_000_000_000_100 + offset,
        5_000_000_000 + offset, 5_000_001_000 + offset,
        2_000_000_000 + offset, 2_000_001_000 + offset, 1000)
    return replace(value, **changes)


class ControlledAPI:
    """Deterministic domain fixture; fake registration never proves native custody."""
    def __init__(self):
        self.platform = module.NativeClockPlatform((10, 0, 0), (), 'CONTROLLED_FIXTURE', 32, 16,
                                                   'CONTROLLED_FIXTURE_NO_LIVE_CLOCK_TRUST')
        self.calls, self.unregister_calls, self.index = 0, 0, 0
        self.next = None
        self.on_unregister = None

    def acquire(self):
        self.calls += 1
        if self.next is not None:
            action, self.next = self.next, None
            return action()
        value = frame(self.index)
        self.index += 1
        return value

    def register(self, subscription):
        self.subscription = subscription
        return 111

    def unregister(self, handle):
        assert handle == 111
        self.unregister_calls += 1
        if self.on_unregister is not None:
            return self.on_unregister()


class ControlledClockTests(unittest.TestCase):
    def make(self, api=None, bounds=None):
        api = api or ControlledAPI()
        bounds = bounds or module.ClockBounds(sampling_interval_ns=1_000_000_000)
        with patch.object(module, '_NativeClockAPI', return_value=api):
            clock = module.NativeSessionClock(9, bounds=bounds)
        self.addCleanup(clock.close)
        return clock, api

    def reject_next(self, changes, code):
        clock, api = self.make()
        api.next = lambda: frame(1, **changes)
        with self.assertRaisesRegex(module.NativeClockUnavailable, code):
            clock.clock()
        self.assertEqual(clock.status().state, 'LATCHED')
        count = api.calls
        with self.assertRaises(module.NativeClockUnavailable):
            clock.clock()
        self.assertEqual(api.calls, count)

    def test_public_constructor_has_no_wall_trust_or_epoch_reset(self):
        names = set(inspect.signature(module.NativeSessionClock).parameters)
        self.assertEqual(names, {'durable_epoch', 'bounds'})
        self.assertFalse(hasattr(module.NativeSessionClock, 'reset'))
        self.assertFalse(hasattr(module.NativeSessionClock, 'set_epoch'))

    def test_typed_epoch_and_bounded_configuration(self):
        for value in (True, -1, MAX_INTEGER + 1, None):
            with self.subTest(value=value), self.assertRaises(ContractError):
                module.NativeSessionClock(value)
        for changes in ({'maximum_gap_ns': True}, {'sampling_interval_ns': 0},
                        {'maximum_acquisition_ns': 11_000_000_000},
                        {'sampling_interval_ns': 2_000_000_000}):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                module.ClockBounds(**changes)

    def test_retained_previous_pair_and_integer_uncertainty(self):
        clock, api = self.make()
        retained = clock._last
        previous, current = clock.clock()
        self.assertIs(previous, retained)
        self.assertEqual(current.durable_epoch, 9)
        self.assertEqual(current.monotonic_ns - previous.monotonic_ns, 10_000_000)
        self.assertGreaterEqual(current.uncertainty_ns, 2051)
        require_clock_progress(previous, current)
        self.assertEqual(clock.status().accepted_sequence, 2)

    def test_measured_zero_counter_is_distinct_from_unavailable(self):
        api = ControlledAPI()
        api.next = lambda: frame(0, qpc_start=0, qpc_end=0, interrupt_start_ns=0,
            interrupt_end_ns=0, unbiased_start_ns=0, unbiased_end_ns=0)
        clock, _ = self.make(api)
        self.assertEqual(clock._last.monotonic_ns, 0)
        self.assertGreater(clock._last.uncertainty_ns, 0)

    def test_counter_fraction_rounds_uncertainty_up(self):
        api = ControlledAPI()
        api.next = lambda: frame(0, qpc_frequency=3, qpc_start=1, qpc_end=1)
        clock, _ = self.make(api)
        self.assertGreaterEqual(clock._last.uncertainty_ns, 333_334_335)
        self.assertEqual(clock._last.monotonic_ns, 333_333_333)

    def test_qpc_rollback_latches(self):
        self.reject_next({'qpc_start': 1, 'qpc_end': 2}, 'CLOCK_MONOTONIC_ROLLBACK')

    def test_nonadvancing_counter_end_is_stale_even_with_new_wall(self):
        self.reject_next({'qpc_start': 10_000_001_000, 'qpc_end': 10_000_001_000}, 'CLOCK_STALE_SAMPLE')

    def test_native_active_counter_rollback_latches(self):
        self.reject_next({'unbiased_start_ns': 1, 'unbiased_end_ns': 2}, 'CLOCK_MONOTONIC_ROLLBACK')

    def test_native_interrupt_counter_rollback_latches(self):
        self.reject_next({'interrupt_start_ns': 1, 'interrupt_end_ns': 2}, 'CLOCK_MONOTONIC_ROLLBACK')

    def test_wall_rollback_inside_observation_latches(self):
        self.reject_next({'wall_end_ns': 0}, 'CLOCK_WALL_ROLLBACK')

    def test_wall_rollback_across_observations_latches(self):
        self.reject_next({'wall_start_ns': 1, 'wall_end_ns': 2}, 'CLOCK_WALL_ROLLBACK')

    def test_boot_change_latches(self):
        other = 'aaaaaaaa-1234-4234-8234-123456789abc'
        self.reject_next({'boot_guid': other, 'boot_guid_after': other}, 'CLOCK_BOOT_CHANGED')

    def test_mid_acquisition_boot_change_denied(self):
        self.reject_next({'boot_guid_after': 'aaaaaaaa-1234-4234-8234-123456789abc'}, 'CLOCK_BOOT_WITNESS_UNAVAILABLE')

    def test_missing_nonzero_boot_witness_denied(self):
        zero = '00000000-0000-0000-0000-000000000000'
        self.reject_next({'boot_guid': zero, 'boot_guid_after': zero}, 'CLOCK_BOOT_WITNESS_UNAVAILABLE')

    def test_missing_native_return_length_denied(self):
        self.reject_next({'boot_return_length': 0}, 'CLOCK_BOOT_WITNESS_UNAVAILABLE')

    def test_frequency_change_latches(self):
        self.reject_next({'qpc_frequency': 999_999_999}, 'CLOCK_CALIBRATION_CHANGED')

    def test_resolution_change_latches(self):
        self.reject_next({'resolution_ns': 2000}, 'CLOCK_CALIBRATION_CHANGED')

    def test_boolean_measurement_denied(self):
        self.reject_next({'qpc_start': True}, 'CLOCK_INTEGER_INVALID')

    def test_zero_frequency_is_unavailable(self):
        self.reject_next({'qpc_frequency': 0}, 'CLOCK_NATIVE_FRAME_INVALID')

    def test_overlong_native_acquisition_denied(self):
        self.reject_next({'qpc_end': 10_200_000_000}, 'CLOCK_ACQUISITION_TOO_SLOW')

    def test_native_query_error_latches_without_zero_sample(self):
        clock, api = self.make()
        def fail():
            raise module.NativeClockUnavailable('CLOCK_BOOT_WITNESS_UNAVAILABLE', native_status=-1)
        api.next = fail
        with self.assertRaises(module.NativeClockUnavailable) as raised:
            clock.clock()
        self.assertEqual(raised.exception.native_status, -1)
        self.assertEqual(clock.status().accepted_sequence, 1)

    def test_native_oserror_is_typed_and_latched(self):
        clock, api = self.make()
        def fail():
            raise OSError('CONTROLLED_PUBLIC_ERROR')
        api.next = fail
        with self.assertRaisesRegex(module.NativeClockUnavailable, 'CLOCK_NATIVE_READ_UNAVAILABLE'):
            clock.clock()
        self.assertEqual(clock.status().state, 'LATCHED')

    def test_wrong_native_record_type_denied(self):
        clock, api = self.make()
        api.next = lambda: {'wall_trusted': True}
        with self.assertRaisesRegex(module.NativeClockUnavailable, 'CLOCK_NATIVE_FRAME_INVALID'):
            clock.clock()

    def test_long_sampling_gap_latches(self):
        clock, api = self.make()
        api.next = lambda: frame(500)
        with self.assertRaisesRegex(module.NativeClockUnavailable, 'CLOCK_SAMPLING_GAP'):
            clock.clock()

    def test_sleep_sensitive_and_active_time_discontinuity_denied(self):
        self.reject_next({'interrupt_start_ns': 6_010_000_000, 'interrupt_end_ns': 6_010_001_000},
                         'CLOCK_SLEEP_DISCONTINUITY')

    def test_qpc_and_interrupt_witness_divergence_denied(self):
        self.reject_next({'interrupt_start_ns': 6_010_000_000, 'interrupt_end_ns': 6_010_001_000,
                          'unbiased_start_ns': 3_010_000_000, 'unbiased_end_ns': 3_010_001_000},
                         'CLOCK_WITNESS_DISCONTINUITY')

    def test_forward_wall_jump_denied(self):
        self.reject_next({'wall_start_ns': 1_792_000_001_010_000_000,
                          'wall_end_ns': 1_792_000_001_010_000_100}, 'CLOCK_WALL_DISCONTINUITY')

    def test_controlled_power_events_latch_without_reset(self):
        for event in (4, 7, 18, 999):
            with self.subTest(event=event):
                clock, api = self.make()
                self.assertEqual(clock._callback(None, event, None), 0)
                self.assertEqual(clock.status().resume_generation, 1)
                self.assertEqual(clock.status().state, 'LATCHED')
                with self.assertRaises(module.NativeClockUnavailable): clock.clock()
                clock.close()

    def test_power_callback_during_acquisition_denies_return(self):
        clock, api = self.make()
        def transition():
            clock._callback(None, 18, None)
            return frame(1)
        api.next = transition
        with self.assertRaisesRegex(module.NativeClockUnavailable, 'CLOCK_POWER_TRANSITION'):
            clock.clock()
        self.assertEqual(clock.status().accepted_sequence, 1)

    def test_primary_control_exceptions_propagate_and_latch(self):
        for kind in (KeyboardInterrupt, SystemExit):
            with self.subTest(kind=kind.__name__):
                clock, api = self.make()
                def fail(): raise kind('CONTROLLED_CLOCK_CONTROL')
                api.next = fail
                with self.assertRaises(kind): clock.clock()
                self.assertEqual(clock.status().reason, 'CLOCK_CONTROL_INTERRUPTION')
                clock.close()

    def test_unregister_failure_preserves_owner_and_retry(self):
        clock, api = self.make()
        def fail(): raise module.NativeClockUnavailable('CONTROLLED_UNREGISTER_FAILURE')
        api.on_unregister = fail
        with self.assertRaisesRegex(module.NativeClockUnavailable, 'CONTROLLED_UNREGISTER_FAILURE'):
            clock.close()
        self.assertTrue(clock.status().registration_owned)
        self.assertIsNotNone(clock._callback)
        api.on_unregister = None
        clock.close()
        self.assertFalse(clock.status().registration_owned)
        self.assertFalse(clock.status().sampler_alive)

    def test_constructor_failure_retires_registration(self):
        api = ControlledAPI()
        api.next = lambda: None
        with patch.object(module, '_NativeClockAPI', return_value=api):
            with self.assertRaises(module.NativeClockUnavailable): module.NativeSessionClock(9)
        self.assertEqual(api.unregister_calls, 1)

    def test_constructor_primary_survives_failed_cleanup_and_retains_owner(self):
        api = ControlledAPI()
        def control(): raise KeyboardInterrupt('CONTROLLED_CONSTRUCTOR')
        def close_fail(): raise module.NativeClockUnavailable('CONTROLLED_UNREGISTER_FAILURE')
        api.next, api.on_unregister = control, close_fail
        with patch.object(module, '_NativeClockAPI', return_value=api):
            with self.assertRaisesRegex(KeyboardInterrupt, 'CONTROLLED_CONSTRUCTOR') as raised:
                module.NativeSessionClock(9)
        clock = raised.exception.clock_custody
        self.assertTrue(clock.status().registration_owned)
        api.on_unregister = None
        clock.close()

    def test_concurrent_reads_remain_serial_and_analyzable(self):
        clock, api = self.make()
        pairs, errors = [], []
        start = threading.Barrier(5)
        def read():
            try:
                start.wait(1)
                pairs.append(clock.clock())
            except BaseException as error: errors.append(type(error).__name__)
        threads = [threading.Thread(target=read) for _ in range(4)]
        for thread in threads: thread.start()
        start.wait(1)
        for thread in threads: thread.join(1)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(errors, [])
        self.assertEqual(len(pairs), 4)
        self.assertEqual(len({pair[1].monotonic_ns for pair in pairs}), 4)
        for pair in pairs: require_clock_progress(*pair)
        self.assertEqual(clock.status().accepted_sequence, 5)

    def test_delayed_return_after_native_frame_is_rejected(self):
        clock, api = self.make()
        def delayed():
            value = frame(1)
            time.sleep(.08)  # Controlled scheduling, no host clock mutation.
            return value
        api.next = delayed
        with self.assertRaisesRegex(module.NativeClockUnavailable, 'CLOCK_ACQUISITION_TOO_SLOW'):
            clock.clock()

    def test_reentrant_power_transition_during_final_bound_read_denies_pair(self):
        clock, api = self.make()
        real = time.monotonic_ns
        calls = []
        def bound_read():
            calls.append(1)
            if len(calls) == 2:
                clock._callback(None, 18, None)  # Controlled same-thread native callback invocation.
            return real()
        with patch.object(module.time, 'monotonic_ns', bound_read):
            with self.assertRaisesRegex(module.NativeClockUnavailable, 'CLOCK_POWER_TRANSITION'):
                clock.clock()
        self.assertEqual(clock.status().accepted_sequence, 1)

    def test_unavailable_native_platform_load_is_typed(self):
        with patch.object(module, '_NativeClockAPI', side_effect=OSError('CONTROLLED_DLL_LOAD')):
            with self.assertRaisesRegex(module.NativeClockUnavailable, 'CLOCK_NATIVE_PLATFORM_UNAVAILABLE'):
                module.NativeSessionClock(9)

    def test_close_stops_later_reads_and_is_idempotent(self):
        clock, api = self.make()
        clock.close(); count = api.calls
        clock.close()
        with self.assertRaises(module.NativeClockUnavailable): clock.clock()
        self.assertEqual(api.calls, count)
        self.assertEqual(api.unregister_calls, 1)

    def test_restart_nonce_prevents_old_deadline_revival(self):
        first, _ = self.make()
        previous, current = first.clock()
        expiry = datetime.fromtimestamp(current.wall_time_ns // module.NS + 2, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        deadline = issue_deadline(expiry, module.NS, previous, current)
        first.close()
        second, _ = self.make()
        self.assertEqual(first.status().boot_guid, second.status().boot_guid)
        self.assertNotEqual(first.status().session_nonce, second.status().session_nonce)
        with self.assertRaisesRegex(ContractError, 'BOOT_CHANGED'):
            require_deadline_current(deadline, *second.clock())

    def test_blocked_sampler_close_is_bounded_and_retryable(self):
        bounds = module.ClockBounds(sampling_interval_ns=1_000_000,
            maximum_gap_ns=2_000_000_000, close_timeout_ns=30_000_000)
        clock, api = self.make(bounds=bounds)
        entered, release = threading.Event(), threading.Event()
        def blocked():
            entered.set()
            if not release.wait(1): raise AssertionError('controlled probe release timeout')
            return frame(1)
        api.next = blocked
        try:
            self.assertTrue(entered.wait(1))
            with self.assertRaisesRegex(module.NativeClockUnavailable, 'CLOCK_SAMPLER_RETIREMENT_UNRESOLVED'):
                clock.close()
            self.assertTrue(clock.status().sampler_alive)
            self.assertFalse(clock.status().registration_owned)
        finally:
            release.set()
            clock._thread.join(1)
            clock.close()
        self.assertFalse(clock.status().sampler_alive)


class ActualNativeClockTests(unittest.TestCase):
    def make(self):
        clock = module.NativeSessionClock(17)
        self.addCleanup(clock.close)
        return clock

    def capture(self, clock, label):
        clock.close()
        status = asdict(clock.status())
        self.assertEqual(status['state'], 'CLOSED')
        self.assertFalse(status['registration_owned'])
        self.assertFalse(status['sampler_alive'])
        self.assertEqual(status['callbacks_active'], 0)
        NATIVE_OBSERVATIONS.append({'test_id': self.id(), 'label': label, 'final_status': status,
            'qualification': 'Actual native reads/registration/custody only; no real host suspend or external UTC attestation'})

    def test_actual_native_pair_and_resolution(self):
        clock = self.make()
        previous, current = clock.clock()
        require_clock_progress(previous, current)
        self.assertGreater(current.wall_time_ns, 0)
        self.assertGreater(current.uncertainty_ns, 0)
        self.assertEqual(clock.status().platform.boot_profile, module.BOOT_PROFILE)
        self.assertEqual(len(clock.status().platform.dll_sha256), 4)
        self.capture(clock, 'native-pair')

    def test_actual_power_registration_and_idempotent_unregister(self):
        clock = self.make()
        self.assertTrue(clock.status().registration_owned)
        self.assertGreater(clock.status().sampler_native_id, 0)
        self.capture(clock, 'native-unregister')
        clock.close()

    def test_actual_periodic_sampler_progress_and_close(self):
        clock = self.make()
        initial = clock.status().accepted_sequence
        end = time.monotonic() + 1
        while clock.status().accepted_sequence <= initial and time.monotonic() < end:
            threading.Event().wait(.01)
        self.assertGreater(clock.status().accepted_sequence, initial)
        self.capture(clock, 'native-periodic')

    def test_actual_boot_witness_and_session_nonce_distinct(self):
        first, second = self.make(), self.make()
        self.assertEqual(first.status().boot_guid, second.status().boot_guid)
        self.assertNotEqual(first.status().session_nonce, second.status().session_nonce)
        self.assertNotEqual(first.clock()[1].boot_id, second.clock()[1].boot_id)
        self.capture(first, 'native-session-one')
        self.capture(second, 'native-session-two')

    def test_actual_boot_abi_query_has_exact_status_and_length(self):
        api = module._NativeClockAPI()
        observations = []
        for _ in range(3):
            value, length = module._BootEnvironment(), module.W.ULONG()
            status = api.NtQuerySystemInformation(90, C.byref(value), C.sizeof(value), C.byref(length))
            self.assertEqual(status, 0)
            self.assertEqual(length.value, 32)
            self.assertTrue(any(value.guid))
            observations.append({'status': status, 'length': length.value,
                'guid': str(module.uuid.UUID(bytes_le=bytes(value.guid))), 'firmware_type': value.firmware_type,
                'flags': value.boot_flags})
        self.assertEqual(len({item['guid'] for item in observations}), 1)
        NATIVE_OBSERVATIONS.append({'test_id': self.id(), 'observations': observations,
            'platform': asdict(api.platform), 'limit': 'Empirical current-OS ABI, absent public SDK class90/struct guarantee'})

    def test_actual_platform_pin_mismatch_denies_before_registration(self):
        with patch.object(module, '_NC1_WINDOWS_VERSION', (10, 0, 0)):
            with self.assertRaisesRegex(ContractError, 'CLOCK_NATIVE_PLATFORM_PIN_MISMATCH'):
                module.NativeSessionClock(17)
        NATIVE_OBSERVATIONS.append({'test_id': self.id(),
            'qualification': 'Actual observed DLL/OS metadata versus explicitly controlled wrong expected pin; no native callback/thread acquired'})


if __name__ == '__main__': unittest.main()
