"""Local provenance controls and separately selected real Windows observation.

Controlled tests execute the production driver with explicit transport/clock/
custody substitutes. Only NativeObserverOriginTests provide native evidence.
Neither cohort supplies canonical permission, capacity or effect success.
"""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import copy
import ctypes as C
import os
import struct
import threading
import unittest

import ceta.effects.native_observer as module
import ceta.supervisor.windows_jobs as native
from ceta.contracts.real_effect import (decode_cpu_effect_observation,
    decode_owned_cpu_request, compare_cpu_observation)
from ceta.contracts.resource_management import ObservationState
from ceta.contracts.wire import ContractError
from ceta.identity.native_clock import NativeSessionClock
import test_owner_authority_transactions as data
import test_native_effect_observer as native_fixture


class ControlledObserverOriginTests(unittest.TestCase):
    def setUp(self):
        self.driver = 'c'*64
        self.image = 'b'*64
        self.code = module.observer_code_commitment(self.image, self.driver)
        self.request = data.effect_request(data.enrollment_request(), observer_commitment=self.code)
        self.target = object.__new__(native.WindowsOwnedProcess)
        self.target._pid, self.target._creation_time, self.target._image_sha256 = 104, 100, 'a'*64
        self.target.cpu_rate_observation = lambda *args, **kwargs: self.request.expected_limit
        self.target.export_cpu_query_handles = lambda *args: SimpleNamespace(inherited_handles=(101, 102))
        self.clock = object.__new__(NativeSessionClock)
        self.sample = 0
        self.clock.clock = self.sample_clock
        self.custodies = []
        self.response_state, self.response_reason = 1, 0
        self.close_failure = self.evidence_failure = None
        self.on_evidence = None
        self.fail_close_number = None
        self.leave_custody_pending = False
        for control in (patch.object(module, '_source_hash', return_value=self.driver),
                patch.object(module, '_Custody', self.custody),
                patch.object(module.C, 'WinDLL', self.controlled_frequency)):
            control.start(); self.addCleanup(control.stop)
        self.observer = module.NativeCpuEffectObserver(module.__file__, self.image, self.code, clock=self.clock)
        self.observer._exchange = self.exchange

    def sample_clock(self):
        self.sample += 1
        before = data.clock(1_000_000_000 + (self.sample-1)*100_000_000)
        return before, data.clock(before.monotonic_ns+100_000_000)

    @staticmethod
    def controlled_frequency(*args, **kwargs):
        def frequency(pointer):
            C.cast(pointer, C.POINTER(C.c_int64)).contents.value = 1_000_000_000
            return 1
        return SimpleNamespace(QueryPerformanceFrequency=frequency)

    def custody(self):
        owner = SimpleNamespace(closed=False, lease=None, close_calls=0,
            process=SimpleNamespace(resource_identity=data.ProcessResourceIdentity(105, 100, 'sha256:'+self.image)))
        def close():
            owner.close_calls += 1
            if self.close_failure is not None and owner.close_calls == self.fail_close_number:
                raise self.close_failure
            owner.closed = not self.leave_custody_pending
        def evidence():
            if self.evidence_failure is not None: raise self.evidence_failure
            if self.on_evidence is not None: self.on_evidence()
            return {'controlled': True, 'closed': owner.closed, 'close_calls': owner.close_calls}
        owner.close, owner.evidence = close, evidence
        self.custodies.append(owner)
        return owner

    def exchange(self, custody, frame, cancelled, deadline):
        fields = module.REQUEST.unpack(frame)
        start = 1_000_000_000+self.sample*100_000_000+10_000_000
        raw = module.RESPONSE.pack(b'CETAOR1\0', 1, fields[2], fields[5], fields[6], fields[7], fields[8],
            105, 100, bytes.fromhex(self.image), fields[9], fields[10], fields[11],
            self.response_state, self.response_reason, 1, 1, 259, start, start+10_000_000,
            1_000_000_000, 0, 0)
        return raw, b'', 0

    def observe(self):
        return self.observer.observe(self.request, self.target)

    def require_origin(self, value, *, request=None, target=None, observer=None):
        return (observer or self.observer).require_observation_origin(
            self.request if request is None else request, self.target if target is None else target, value)

    def denied(self, value, **changes):
        with self.assertRaises(ContractError): self.require_origin(value, **changes)

    def test_no_origin_before_first_success(self):
        self.denied(object())

    def test_success_retains_exact_object_and_allows_canonical_request_decode(self):
        value = self.observe()
        self.assertIsNone(self.require_origin(value))
        self.assertIsNone(self.require_origin(value, request=decode_owned_cpu_request(self.request.canonical_wire)))
        self.assertTrue(all(owner.closed for owner in self.custodies))
        self.assertIsNone(self.observer._custody)

    def test_equal_reconstructed_replaced_and_copied_observation_are_denied(self):
        value = self.observe()
        for other in (decode_cpu_effect_observation(value.canonical_wire), replace(value), copy.copy(value)):
            with self.subTest(kind=type(other).__name__):
                self.assertEqual(value.canonical_wire, other.canonical_wire)
                self.assertIsNot(value, other); self.denied(other)
        self.assertIsNone(self.require_origin(value))

    def test_another_observer_and_shallow_copied_observer_are_denied(self):
        value = self.observe()
        other = module.NativeCpuEffectObserver(module.__file__, self.image, self.code, clock=self.clock)
        self.denied(value, observer=other)
        self.denied(value, observer=copy.copy(self.observer))

    def test_equal_target_identity_does_not_replace_retained_target(self):
        value = self.observe(); target = copy.copy(self.target)
        self.assertEqual(target.resource_identity, self.target.resource_identity)
        self.denied(value, target=target)

    def test_changed_request_bytes_are_denied(self):
        value = self.observe()
        self.denied(value, request=replace(self.request, task_id='task:changed'))

    def test_changed_original_observation_bytes_are_denied(self):
        value = self.observe()
        object.__setattr__(value, 'operation_id', 'request:changed')
        self.denied(value)

    def test_changed_original_request_bytes_are_denied(self):
        value = self.observe()
        object.__setattr__(self.request, 'task_id', 'task:changed')
        self.denied(value)

    def test_observer_sequence_mismatch_is_denied(self):
        value = self.observe(); self.observer._sequence += 1
        self.denied(value)

    def test_next_success_invalidates_prior_observation(self):
        first = self.observe(); second = self.observe()
        self.denied(first); self.assertIsNone(self.require_origin(second))
        self.assertEqual(second.sequence, first.sequence+1)

    def test_accepted_attempt_invalidates_prior_before_driver_check(self):
        value = self.observe()
        with patch.object(module, '_source_hash', return_value='d'*64):
            with self.assertRaisesRegex(ContractError, 'OBSERVER_DRIVER_CHANGED'): self.observe()
        self.denied(value)
        self.assertEqual(self.observer._sequence, value.sequence)

    def test_busy_attempt_does_not_supersede_origin_and_predicate_never_waits(self):
        value = self.observe(); self.assertTrue(self.observer._lock.acquire(blocking=False))
        try:
            self.denied(value)
            with self.assertRaisesRegex(ContractError, 'OBSERVER_BUSY'): self.observe()
        finally: self.observer._lock.release()
        self.assertIsNone(self.require_origin(value))

    def test_origin_cannot_be_used_while_new_attempt_is_in_flight(self):
        first = self.observe(); original = self.observer._exchange
        def exchange(*args):
            self.denied(first)
            return original(*args)
        with patch.object(self.observer, '_exchange', exchange): second = self.observe()
        self.denied(first); self.assertIsNone(self.require_origin(second))

    def test_failed_protocol_invalidates_prior_and_does_not_publish(self):
        value = self.observe()
        with patch.object(self.observer, '_exchange', return_value=(b'bad', b'', 0)):
            with self.assertRaisesRegex(ContractError, 'OBSERVER_OUTPUT_SIZE_INVALID'): self.observe()
        self.denied(value); self.assertFalse(self.observer.last_evidence['accepted'])

    def test_cancelled_accepted_attempt_invalidates_prior(self):
        value = self.observe(); cancelled = threading.Event(); cancelled.set()
        with self.assertRaisesRegex(ContractError, 'OBSERVER_CANCELLED'):
            self.observer.observe(self.request, self.target, cancelled=cancelled)
        self.denied(value)

    def test_invalid_input_does_not_admit_new_attempt(self):
        value = self.observe()
        with self.assertRaises(ContractError): self.observer.observe(object(), self.target)
        with self.assertRaises(ContractError): self.observer.observe(self.request, self.target, cancelled=object())
        self.assertIsNone(self.require_origin(value))

    def test_request_change_during_transport_is_rejected_before_return(self):
        previous = self.observe(); original = self.observer._exchange
        def changed(*args):
            result = original(*args)
            object.__setattr__(self.request, 'task_id', 'task:changed-during-observe')
            return result
        with patch.object(self.observer, '_exchange', changed):
            with self.assertRaises(ContractError): self.observe()
        self.denied(previous)

    def test_computed_result_and_diagnostic_failure_never_publish_origin(self):
        previous = self.observe(); diagnostic = OSError('CONTROLLED_DIAGNOSTIC_FAILURE')
        self.evidence_failure = diagnostic
        with self.assertRaises(OSError) as caught: self.observe()
        self.assertIs(caught.exception, diagnostic); self.assertTrue(diagnostic.observer_custody.closed)
        self.denied(previous); self.assertFalse(self.observer.last_evidence['accepted'])

    def test_computed_unreturned_object_is_denied_even_after_explicit_cleanup(self):
        values = []; constructor = module.CpuEffectObservation
        def captured(*args):
            value = constructor(*args); values.append(value); return value
        self.evidence_failure = OSError('CONTROLLED_DIAGNOSTIC_FAILURE')
        with patch.object(module, 'CpuEffectObservation', captured):
            with self.assertRaises(OSError): self.observe()
        self.assertEqual(len(values), 1); self.denied(values[0])
        self.evidence_failure = None
        self.observer.close_cleanup(); self.denied(values[0])

    def test_observation_byte_change_during_diagnostic_finalization_cannot_publish(self):
        values = []; constructor = module.CpuEffectObservation
        def captured(*args):
            value = constructor(*args); values.append(value); return value
        self.on_evidence = lambda: object.__setattr__(values[0], 'operation_id', 'request:changed-finalization')
        with patch.object(module, 'CpuEffectObservation', captured):
            with self.assertRaisesRegex(ContractError, 'OBSERVER_ORIGIN_CHANGED'): self.observe()
        self.assertEqual(len(values), 1); self.denied(values[0])
        self.assertFalse(self.observer.last_evidence['accepted'])

    def test_interruption_after_origin_assignment_and_actual_lock_release_retires_origin(self):
        values = []; constructor = module.CpuEffectObservation
        def captured(*args):
            value = constructor(*args); values.append(value); return value
        actual = self.observer._lock; failure = KeyboardInterrupt('CONTROLLED_RELEASE_RESPONSE_LOSS')
        class ReleaseResponseLoss:
            def acquire(self, *args, **kwargs): return actual.acquire(*args, **kwargs)
            def release(self): actual.release(); raise failure
        self.observer._lock = ReleaseResponseLoss()
        try:
            with patch.object(module, 'CpuEffectObservation', captured):
                with self.assertRaises(KeyboardInterrupt) as caught: self.observe()
            self.assertIs(caught.exception, failure)
        finally: self.observer._lock = actual
        self.assertEqual(len(values), 1); self.denied(values[0])
        self.assertFalse(self.observer.last_evidence['accepted'])

    def test_final_close_uncertainty_does_not_publish_computed_result(self):
        previous = self.observe(); self.close_failure = OSError('CONTROLLED_FINAL_CLOSE_RESPONSE_LOSS')
        self.fail_close_number = 2
        with self.assertRaises(module.NativeObserverError): self.observe()
        self.denied(previous); self.assertFalse(self.observer.last_evidence['accepted'])

    def test_unretired_custody_cannot_publish_even_when_close_returns(self):
        previous = self.observe(); self.leave_custody_pending = True
        with self.assertRaises(ContractError): self.observe()
        self.denied(previous); self.assertIsNotNone(self.observer._custody)

    def test_primary_is_preserved_with_diagnostic_secondary_and_origin_denied(self):
        previous = self.observe(); primary = KeyboardInterrupt('CONTROLLED_PRIMARY')
        diagnostic = OSError('CONTROLLED_SECONDARY'); self.evidence_failure = diagnostic
        with patch.object(self.observer, '_exchange', side_effect=primary):
            with self.assertRaises(KeyboardInterrupt) as caught: self.observe()
        self.assertIs(caught.exception, primary)
        self.assertIs(primary.observer_diagnostic_error, diagnostic)
        self.denied(previous)

    def test_diagnostic_assignment_failure_cannot_publish_or_leave_request_lock_held(self):
        previous = self.observe(); original = module.NativeCpuEffectObserver.__setattr__
        failure = KeyboardInterrupt('CONTROLLED_DIAGNOSTIC_ASSIGNMENT')
        def assigned(owner, name, value):
            if owner is self.observer and name == '_last_evidence': raise failure
            original(owner, name, value)
        with patch.object(module.NativeCpuEffectObserver, '__setattr__', assigned):
            with self.assertRaises(KeyboardInterrupt) as caught: self.observe()
        self.assertIs(caught.exception, failure); self.denied(previous)
        self.assertTrue(self.observer._lock.acquire(blocking=False)); self.observer._lock.release()

    def test_evidence_dictionary_is_not_positive_proof(self):
        value = self.observe(); detached = self.observer.last_evidence
        detached.clear(); self.observer._last_evidence = {'accepted': False}
        self.assertIsNone(self.require_origin(value))
        with patch.object(module, '_source_hash', return_value='d'*64):
            with self.assertRaises(ContractError): self.observe()
        self.observer._last_evidence = {'accepted': True, 'sequence': value.sequence}
        self.denied(value)

    def test_predicate_is_local_and_does_not_query_clock_native_target_or_transport(self):
        value = self.observe()
        with patch.object(module.C, 'WinDLL', side_effect=AssertionError('NATIVE_QUERY')), \
                patch.object(module, '_source_hash', side_effect=AssertionError('SOURCE_QUERY')), \
                patch.object(self.clock, 'clock', side_effect=AssertionError('CLOCK_QUERY')), \
                patch.object(self.target, 'cpu_rate_observation', side_effect=AssertionError('TARGET_QUERY')), \
                patch.object(self.observer, '_exchange', side_effect=AssertionError('TRANSPORT')), \
                patch.object(module.time, 'monotonic_ns', side_effect=AssertionError('TIME_QUERY')), \
                patch.object(module.time, 'sleep', side_effect=AssertionError('WAIT')):
            self.assertIsNone(self.require_origin(value))
            self.denied(replace(value))

    def test_unavailable_origin_still_has_unavailable_outcome(self):
        self.response_state, self.response_reason = 0, 4
        value = self.observe(); self.assertIsNone(self.require_origin(value))
        self.assertIs(value.state, ObservationState.UNAVAILABLE); self.assertIsNone(value.limit)
        now = data.clock(1_300_000_000)
        self.assertEqual(compare_cpu_observation(self.request, value, value.clock, now, minimum_sequence=0), 'UNAVAILABLE')


@unittest.skipUnless(os.name == 'nt' and struct.calcsize('P') == 8, 'actual Windows x64 required')
class NativeObserverOriginTests(unittest.TestCase):
    """Reuse existing disposable fixture methods, not its whole test inventory."""
    setUp = native_fixture.NativeEffectObserverTests.setUp
    new_target = native_fixture.NativeEffectObserverTests.new_target
    observer = native_fixture.NativeEffectObserverTests.observer
    request = native_fixture.NativeEffectObserverTests.request
    call = native_fixture.NativeEffectObserverTests.call
    settle = native_fixture.NativeEffectObserverTests.settle
    mutate_response = native_fixture.NativeEffectObserverTests.mutate_response

    def test_actual_native_return_has_origin_and_equal_decoded_dto_does_not(self):
        observer, code = self.observer(); request = self.request(code)
        value = self.call(observer, request)
        self.assertIsNone(observer.require_observation_origin(request, self.target, value))
        self.assertIs(value.state, ObservationState.MEASURED)
        self.assertNotEqual(value.identity.pid, value.observer_identity.pid)
        self.assertIsNone(observer._custody); self.assertEqual(len(self.target._cpu_query_exports), 0)
        self.assertTrue(observer.last_evidence['cleanup']['closed'])
        with self.assertRaises(ContractError):
            observer.require_observation_origin(request, self.target, decode_cpu_effect_observation(value.canonical_wire))

    def test_actual_second_observation_retires_first_origin(self):
        observer, code = self.observer(); request = self.request(code)
        first = self.call(observer, request); second = self.call(observer, request)
        with self.assertRaises(ContractError): observer.require_observation_origin(request, self.target, first)
        self.assertIsNone(observer.require_observation_origin(request, self.target, second))

    def test_actual_protocol_rejection_invalidates_previous_origin(self):
        observer, code = self.observer(); request = self.request(code)
        previous = self.call(observer, request)
        with self.mutate_response(observer, 2, lambda value: value+1):
            with self.assertRaisesRegex(ContractError, 'OBSERVER_RESPONSE_BINDING_MISMATCH'):
                self.call(observer, request)
        with self.assertRaises(ContractError): observer.require_observation_origin(request, self.target, previous)
        self.assertFalse(observer.last_evidence['accepted']); self.assertIsNone(observer._custody)

    def test_actual_cleanup_complete_but_diagnostic_failure_does_not_publish(self):
        observer, code = self.observer(); request = self.request(code)
        previous = self.call(observer, request); primary = OSError('CONTROLLED_DIAGNOSTIC_FAILURE')
        with patch.object(module._Custody, 'evidence', side_effect=primary):
            with self.assertRaises(OSError) as caught: self.call(observer, request)
        self.assertIs(caught.exception, primary); self.assertTrue(primary.observer_custody.closed)
        with self.assertRaises(ContractError): observer.require_observation_origin(request, self.target, previous)
        self.assertFalse(observer.last_evidence['accepted']); self.assertIsNone(observer._custody)

    def test_actual_other_retained_target_and_observer_are_denied(self):
        observer, code = self.observer(); request = self.request(code)
        value = self.call(observer, request); other_target = self.new_target(); other_observer, _ = self.observer()
        with self.assertRaises(ContractError): observer.require_observation_origin(request, other_target, value)
        with self.assertRaises(ContractError): other_observer.require_observation_origin(request, self.target, value)
        self.assertIsNone(observer.require_observation_origin(request, self.target, value))

    def test_actual_unavailable_membership_has_origin_but_no_measured_outcome(self):
        observer, code = self.observer(); request = self.request(code); other = self.new_target()
        lease = other.export_cpu_query_handles(other.resource_identity); self.leases.append(lease)
        other_job = lease.inherited_handles[1]
        original = native.WindowsCpuQueryHandles.inherited_handles.fget
        def wrong_job(item):
            process, job = original(item)
            return (process, other_job) if item.identity == request.process_identity else (process, job)
        with patch.object(native.WindowsCpuQueryHandles, 'inherited_handles', property(wrong_job)):
            value = self.call(observer, request)
        self.assertIsNone(observer.require_observation_origin(request, self.target, value))
        self.assertIs(value.state, ObservationState.UNAVAILABLE); self.assertIsNone(value.limit)
        self.assertEqual(value.target_state, 'NOT_IN_OWNED_JOB')
        _, current = self.clock.clock()
        self.assertEqual(compare_cpu_observation(request, value, value.clock, current, minimum_sequence=0), 'UNAVAILABLE')


if __name__ == '__main__': unittest.main()
