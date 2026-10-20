"""Real SQLite accounting plus controlled throttle-owner conformance.

The retained execution fixture below is not production authentication, durable
throttle admission or canonical evidence integration. Native enforcement is
qualified separately on actual disposable Windows resources.
"""
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
import threading
import time
import unittest

from ceta.contracts.resource_management import (CapacitySnapshot, ObservationState, ProcessResourceIdentity,
    QuantityObservation, ResourceKind, ResourceVector)
from ceta.contracts.workload_throttling import (CpuRateChange, CpuRateLimit, CpuRateObservation,
    WorkloadThrottleIntent)
from ceta.contracts.wire import ContractError, strict_loads
from ceta.resource.pressure import WorkloadThrottlingController
from test_resource_reservations import ResourceFixture

ROOT = Path(__file__).resolve().parents[2]
HASH = 'sha256:' + 'a' * 64


def capacity(at, sequence=1, utilization=950):
    def q(value): return QuantityObservation(ObservationState.MEASURED, value, at, 'fixture:CPU-pressure')
    return CapacitySnapshot(ResourceKind.CPU, q(1000), q(1000 - utilization), q(0), q(utilization), sequence)


class ControlledNativeOwner:
    """Deterministic effect-count oracle only; never called a native sensor."""
    def __init__(self):
        self.calls = 0
        self.fail = self.after = None

    def apply_cpu_rate_limit(self, operation_id, identity, expected, limit, **bounds):
        fence = bounds.get('dispatch_fence')
        if fence is not None:
            if not callable(fence) or fence() is not None:
                raise ContractError('CONTROLLED_DISPATCH_FENCE_MALFORMED')
        self.calls += 1
        if self.fail: raise self.fail
        observed = replace(expected, limit=limit, version=expected.version + 1)
        result = CpuRateChange(operation_id, identity, expected.job_digest, expected.limit, limit,
                               observed, 'APPLIED', 'CONTROLLED_EFFECT_OBSERVED')
        if self.after: self.after(result)
        return result


class ControlledExecutionOwner:
    """Explicit controlled retained lifetime and competition/evidence oracle."""
    def __init__(self, context):
        self.context, self.lock = context, threading.RLock()
        self.evidence_available = self.current = True
        self.operations, self.outcomes, self.observations = set(), [], []
        self.hook = None
        self.current_result = self.record_result = None
        self.exit_failure = None

    @contextmanager
    def admit_throttle(self, original_context, intent, owned_process):
        with self.lock:
            if original_context is not self.context: raise ContractError('CONTROLLED_CONTEXT_DENIED')
            if not self.evidence_available: raise ContractError('CONTROLLED_EVIDENCE_UNAVAILABLE')
            if not self.current: raise ContractError('CONTROLLED_AUTHORITY_REVOKED')
            if intent.operation_id in self.operations: raise ContractError('CONTROLLED_OPERATION_SPENT')
            self.operations.add(intent.operation_id)
            self.operation_id, self.input_commitment = intent.operation_id, intent.input_commitment
            self.intent_ref, self.evidence_ref = 'fixture:intent', 'fixture:evidence-capacity'
            self.observations.append(('intent', intent.operation_id))
            try: yield self
            finally:
                self.observations.append(('exit', intent.operation_id))
                if self.exit_failure: raise self.exit_failure

    def require_current(self, intent, owned_process):
        self.observations.append(('current', intent.operation_id))
        if self.hook: self.hook()
        if not self.current: raise ContractError('CONTROLLED_AUTHORITY_REVOKED')
        return self.current_result

    def record_outcome(self, intent, change):
        self.observations.append(('outcome', intent.operation_id))
        self.outcomes.append(change)
        return self.record_result


class WorkloadThrottleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = strict_loads((ROOT / 'contracts/schemas/records.schema.json').read_bytes())

    def setUp(self):
        self.f = ResourceFixture(self.schema)
        self.addCleanup(self.f.close_with_receipt, self.id())
        request = self.f.request(); self.f.port.reserve(request)
        self.lease = self.f.port.recover(request.request_id)
        self.budget = self.f.read_budget()
        self.now = 100_000_000
        self.context = object()
        self.owner = ControlledExecutionOwner(self.context)
        self.native = ControlledNativeOwner()
        self.controller = WorkloadThrottlingController(self.owner, clock=lambda: self.now)

    def intent(self, **changes):
        identity = ProcessResourceIdentity(123, 456, HASH)
        limit = CpuRateObservation(identity, HASH, ObservationState.MEASURED, CpuRateLimit(0, 0), 0, self.now)
        result = WorkloadThrottleIntent('throttle:one', HASH, HASH, self.lease, self.budget, identity,
            limit, CpuRateLimit.hard_cap(500), capacity(self.now), ResourceVector(10, 10, 10, 10),
            self.now + 10_000_000_000)
        return replace(result, **changes)

    def execute(self, intent=None, **kwargs):
        return self.controller.execute(intent or self.intent(), self.native, self.context, **kwargs)

    def test_exact_plan_preserves_canonical_accounting_and_does_not_apply(self):
        before = self.f.cut_resources(self.lease.request)
        intent = self.intent(); result = self.controller.plan(intent)
        self.assertEqual(result.state, 'PLANNED')
        self.assertEqual(result.input_commitment, intent.input_commitment)
        self.assertEqual(self.native.calls, 0)
        self.assertEqual(self.f.cut_resources(self.lease.request), before)

    def test_default_execution_owner_denies_without_effect(self):
        self.controller = WorkloadThrottlingController(clock=lambda: self.now)
        self.assertEqual(self.execute().reason_codes, ('THROTTLE_EXECUTION_OWNER_UNAVAILABLE',))
        self.assertEqual(self.native.calls, 0)

    def test_current_kernel_denial_cannot_become_execution_owner(self):
        self.controller = WorkloadThrottlingController(self.f.kernel, clock=lambda: self.now)
        with self.assertRaisesRegex(ContractError, 'RUNTIME_AUTHORITY_OWNERS_UNAVAILABLE'):
            self.f.kernel.require_runtime_admission()
        self.assertEqual(self.execute().state, 'BLOCKED')
        self.assertEqual(self.native.calls, 0)

    def test_unavailable_evidence_prevents_controlled_admission_and_effect(self):
        self.owner.evidence_available = False
        self.assertEqual(self.execute().reason_codes, ('CONTROLLED_EVIDENCE_UNAVAILABLE',))
        self.assertEqual((self.native.calls, self.owner.outcomes), (0, []))

    def test_original_opaque_context_required(self):
        result = self.controller.execute(self.intent(), self.native, object())
        self.assertEqual(result.reason_codes, ('CONTROLLED_CONTEXT_DENIED',))
        self.assertEqual(self.native.calls, 0)

    def test_each_mandatory_safeguard_denies_reduction(self):
        for name in ('preserves_verification', 'preserves_evidence', 'preserves_stop', 'preserves_recovery'):
            with self.subTest(name=name):
                self.assertEqual(self.execute(self.intent(**{name: False})).state, 'BLOCKED')
        self.assertEqual(self.native.calls, 0)

    def test_stop_and_request_cancellation_close_admission(self):
        self.assertEqual(self.execute(cancelled=True).state, 'CANCELLED')
        self.controller.stop()
        self.assertEqual(self.execute().state, 'CANCELLED')
        self.assertEqual(self.native.calls, 0)

    def test_control_reserve_is_not_spent_to_throttle(self):
        result = self.execute(self.intent(required_control_reserve=ResourceVector(101, 10, 10, 10)))
        self.assertEqual(result.reason_codes, ('THROTTLE_CONTROL_RESERVE_UNAVAILABLE',))
        self.assertEqual(self.native.calls, 0)

    def test_stale_budget_and_missing_reservation_deny(self):
        for budget in (replace(self.budget, generation=1), replace(self.budget, reserved_use=ResourceVector(0, 0, 0, 0))):
            with self.subTest(budget=budget):
                self.assertEqual(self.execute(self.intent(budget=budget)).state, 'STALE')
        self.assertEqual(self.native.calls, 0)

    def test_stale_future_and_incoherent_pressure_deny(self):
        original = capacity(self.now)
        samples = (capacity(self.now + 1), capacity(self.now - 10, utilization=950),
                   replace(original, free=replace(original.free, observed_monotonic_ns=self.now - 1)))
        for snapshot in samples:
            with self.subTest(snapshot=snapshot):
                intent = self.intent(pressure=snapshot, maximum_age_ns=5)
                self.assertEqual(self.execute(intent).state, 'STALE')
        self.assertEqual(self.native.calls, 0)

    def test_unavailable_pressure_is_not_measured_zero(self):
        snapshot = capacity(self.now)
        unknown = QuantityObservation(ObservationState.UNAVAILABLE, None, self.now, 'fixture:CPU', 'unavailable')
        result = self.execute(self.intent(pressure=replace(snapshot, total=unknown)))
        self.assertEqual(result.state, 'STALE'); self.assertEqual(self.native.calls, 0)

    def test_replayed_changed_pressure_stream_closes_plan(self):
        self.assertEqual(self.controller.plan(self.intent()).state, 'PLANNED')
        changed = self.intent(pressure=capacity(self.now, utilization=960))
        self.assertEqual(self.execute(changed).state, 'STALE')
        self.assertEqual(self.native.calls, 0)

    def test_deadline_and_persistent_clock_rollback_deny(self):
        self.assertEqual(self.execute(self.intent(deadline_monotonic_ns=self.now)).state, 'STALE')
        self.assertEqual(self.controller.plan(self.intent()).state, 'PLANNED')
        self.now -= 1
        self.assertEqual(self.execute().reason_codes, ('THROTTLE_CLOCK_ROLLBACK',))
        self.now += 100
        self.assertEqual(self.execute().reason_codes, ('THROTTLE_CLOCK_ROLLBACK',))
        self.assertEqual(self.native.calls, 0)

    def test_clock_oserror_explicit_and_control_interruption_preserved(self):
        self.controller = WorkloadThrottlingController(clock=lambda: (_ for _ in ()).throw(OSError('private-clock-detail')))
        result = self.execute(); self.assertEqual(result.reason_codes, ('THROTTLE_CLOCK_UNAVAILABLE',))
        self.assertNotIn('private-clock-detail', repr(result))
        failure = KeyboardInterrupt('primary')
        self.controller = WorkloadThrottlingController(clock=lambda: (_ for _ in ()).throw(failure))
        with self.assertRaises(KeyboardInterrupt) as caught: self.execute()
        self.assertIs(caught.exception, failure); self.assertEqual(self.native.calls, 0)

    def test_bool_owner_decision_and_missing_recorder_deny(self):
        self.owner.current_result = True
        self.assertEqual(self.execute().reason_codes, ('THROTTLE_OWNER_DECISION_MALFORMED',))
        self.assertEqual(self.native.calls, 0)
        self.owner = ControlledExecutionOwner(self.context); self.owner.record_outcome = None
        self.controller = WorkloadThrottlingController(self.owner, clock=lambda: self.now)
        self.assertEqual(self.execute().reason_codes, ('THROTTLE_EVIDENCE_WRITER_UNAVAILABLE',))
        self.assertEqual(self.native.calls, 0)

    def test_revocation_and_deadline_during_current_check_prevent_effect(self):
        self.owner.hook = lambda: setattr(self.owner, 'current', False)
        self.assertEqual(self.execute().state, 'BLOCKED')
        self.assertEqual(self.native.calls, 0)
        self.owner = ControlledExecutionOwner(self.context)
        intent = self.intent()
        self.owner.hook = lambda: setattr(self, 'now', intent.deadline_monotonic_ns)
        self.controller = WorkloadThrottlingController(self.owner, clock=lambda: self.now)
        self.assertEqual(self.execute(intent).reason_codes, ('THROTTLE_PRE_EFFECT_INPUT_STALE',))
        self.assertEqual(self.native.calls, 0)

    def test_callback_elapsed_time_is_fenced_without_claiming_preemption(self):
        self.controller = WorkloadThrottlingController(self.owner, clock=lambda: self.now, maximum_decision_duration_ns=5_000_000)
        self.owner.hook = lambda: time.sleep(.015)
        self.assertEqual(self.execute().reason_codes, ('THROTTLE_OWNER_CHECK_TOO_SLOW',))
        self.assertEqual(self.native.calls, 0)

    def test_nested_mutation_after_admission_prevents_effect(self):
        intent = self.intent()
        self.owner.hook = lambda: object.__setattr__(intent.proposed_limit, 'value', 400)
        self.assertEqual(self.execute(intent).reason_codes, ('THROTTLE_INPUT_CHANGED',))
        self.assertEqual(self.native.calls, 0)

    def test_malformed_nested_values_reject_before_admission(self):
        intent = self.intent()
        object.__setattr__(intent.budget.control_reserve, 'cpu_milli', True)
        with self.assertRaises(ContractError): self.execute(intent)
        self.assertEqual((self.native.calls, self.owner.operations), (0, set()))

    def test_controlled_effect_retains_same_semantics_and_records_outcome(self):
        intent = self.intent(); result = self.execute(intent)
        self.assertEqual(result.state, 'APPLIED')
        self.assertEqual((result.operation_id, result.input_commitment), (intent.operation_id, intent.input_commitment))
        self.assertEqual(result.change.identity, intent.process_identity)
        self.assertEqual(self.owner.outcomes, [result.change])
        self.assertEqual(self.owner.observations[0], ('intent', intent.operation_id))
        self.assertEqual(self.owner.observations[-1], ('exit', intent.operation_id))

    def test_two_controllers_compete_for_one_controlled_single_use_intent(self):
        intent = self.intent(); barrier = threading.Barrier(3); outputs = []
        controllers = [WorkloadThrottlingController(self.owner, clock=lambda: self.now) for _ in range(2)]
        def run(controller):
            barrier.wait(); outputs.append(controller.execute(intent, self.native, self.context))
        threads = [threading.Thread(target=run, args=(controller,)) for controller in controllers]
        for thread in threads: thread.start()
        barrier.wait()
        for thread in threads: thread.join(2); self.assertFalse(thread.is_alive())
        self.assertEqual(sorted(value.state for value in outputs), ['APPLIED', 'BLOCKED'])
        self.assertEqual(self.native.calls, 1)

    def test_post_effect_revocation_is_uncertain_and_not_automatically_restored(self):
        self.native.after = lambda change: setattr(self.owner, 'current', False)
        result = self.execute()
        self.assertEqual((result.state, result.change.state, self.native.calls), ('UNCERTAIN', 'APPLIED', 1))
        self.assertEqual(self.owner.outcomes, [])

    def test_post_effect_recording_failure_remains_uncertain(self):
        self.owner.record_result = False
        result = self.execute()
        self.assertEqual(result.state, 'UNCERTAIN')
        self.assertEqual(result.reason_codes, ('THROTTLE_OWNER_DECISION_MALFORMED',))
        self.assertEqual(self.native.calls, 1)

    def test_missing_native_response_after_dispatch_is_uncertain(self):
        def lost_response(*args, **kwargs):
            self.native.calls += 1
            return None
        self.native.apply_cpu_rate_limit = lost_response
        result = self.execute()
        self.assertEqual((result.state, result.change, self.native.calls), ('UNCERTAIN', None, 1))
        self.assertEqual(result.reason_codes, ('THROTTLE_NATIVE_RESULT_MALFORMED',))

    def test_native_oserror_after_dispatch_is_uncertain(self):
        self.native.fail = OSError('private native detail')
        result = self.execute()
        self.assertEqual((result.state, self.native.calls), ('UNCERTAIN', 1))
        self.assertNotIn('private native detail', repr(result))

    def test_exit_failure_after_observed_effect_is_uncertain(self):
        self.owner.exit_failure = OSError('exit failure')
        result = self.execute()
        self.assertEqual((result.state, result.change.state, self.native.calls), ('UNCERTAIN', 'APPLIED', 1))

    def test_coarse_clock_cannot_hide_deadline_time_spent_in_owner_callback(self):
        intent = self.intent(deadline_monotonic_ns=self.now + 5_000_000)
        self.owner.hook = lambda: time.sleep(.015)
        result = self.execute(intent)
        self.assertEqual(result.reason_codes, ('THROTTLE_EXECUTION_DEADLINE_EXPIRED',))
        self.assertEqual(self.native.calls, 0)

    def test_stop_does_not_wait_behind_execution_lock_and_prevents_dispatch(self):
        entered, release, stop_finished = threading.Event(), threading.Event(), threading.Event()
        outputs = []
        def current_hook():
            entered.set(); self.assertTrue(release.wait(2))
        self.owner.hook = current_hook
        worker = threading.Thread(target=lambda: outputs.append(self.execute()))
        worker.start(); self.assertTrue(entered.wait(2))
        stopper = threading.Thread(target=lambda: (self.controller.stop(), stop_finished.set()))
        stopper.start()
        try: self.assertTrue(stop_finished.wait(.5), 'stop waited behind the held execution lock')
        finally: release.set(); worker.join(2); stopper.join(2)
        self.assertFalse(worker.is_alive()); self.assertFalse(stopper.is_alive())
        self.assertEqual(outputs[0].reason_codes, ('THROTTLE_PRE_EFFECT_INPUT_STALE',))
        self.assertEqual(self.native.calls, 0)

    def test_released_canonical_lease_cannot_authorize_throttling(self):
        released = self.f.port.release(self.lease.request.request_id, 'fixture:cleanup')
        intent = self.intent(lease=released, budget=self.f.read_budget())
        self.assertEqual(self.execute(intent).reason_codes, ('THROTTLE_RESOURCE_LEASE_STALE',))
        self.assertEqual(self.native.calls, 0)

    def test_primary_control_exception_survives_retained_owner_exit_failure(self):
        failure = KeyboardInterrupt('primary')
        self.native.fail = failure; self.owner.exit_failure = OSError('secondary')
        with self.assertRaises(KeyboardInterrupt) as caught: self.execute()
        self.assertIs(caught.exception, failure)
        self.assertEqual(self.native.calls, 1)
        self.assertEqual(self.execute().state, 'CANCELLED')

    def test_limit_scalar_flags_and_ranges_are_exact(self):
        for flags, value in ((True, 1), (5, False), (5, 0), (5, 10001), (7, 5), (21, 1), (3, 10), (32, 1)):
            with self.subTest(flags=flags, value=value), self.assertRaises(ContractError): CpuRateLimit(flags, value)
        self.assertEqual(CpuRateLimit(17, (2000 << 16) | 1000).control_flags, 17)

    def test_existing_cpu_notification_policy_is_preserved(self):
        intent = self.intent()
        notified = replace(intent.expected_limit, limit=CpuRateLimit(13, 1000))
        changed = replace(intent, expected_limit=notified)
        self.assertEqual(self.execute(changed).reason_codes, ('THROTTLE_NOTIFICATION_PRESERVATION_REQUIRED',))
        self.assertEqual(self.native.calls, 0)
        preserved = replace(changed, proposed_limit=CpuRateLimit(13, 500))
        self.assertEqual(self.execute(preserved).state, 'APPLIED')

    def test_distinct_restoration_operation_and_complete_commitment(self):
        intent = self.intent()
        with self.assertRaises(ContractError): replace(intent, restoration_of=intent.operation_id)
        restored = replace(intent, operation_id='restore:one', restoration_of=intent.operation_id, proposed_limit=CpuRateLimit(0, 0))
        self.assertEqual(self.controller.plan(restored).state, 'PLANNED')
        self.assertNotEqual(restored.input_commitment, intent.input_commitment)
        self.assertNotEqual(replace(intent, deadline_monotonic_ns=intent.deadline_monotonic_ns - 1).input_commitment,
                            intent.input_commitment)


class DispatchOrderingTests(unittest.TestCase):
    """Controlled retained-owner schedules; no production admission claim."""
    def setUp(self):
        self.h = WorkloadThrottleTests()
        self.h.schema = strict_loads((ROOT / 'contracts/schemas/records.schema.json').read_bytes())
        self.h.setUp()
        self.addCleanup(self.h.doCleanups)
        self.h.controller._decision_limit = 1_000_000_000

    def run_worker(self, callback):
        outputs, faults = [], []
        def run():
            try: outputs.append(callback())
            except BaseException as failure: faults.append(failure)
        worker = threading.Thread(target=run); worker.start()
        return worker, outputs, faults

    def test_stop_from_native_method_resolution_denies_before_dispatch(self):
        h = self.h
        class NativeView:
            @property
            def apply_cpu_rate_limit(self):
                h.controller.stop()
                return h.native.apply_cpu_rate_limit
        result = h.controller.execute(h.intent(), NativeView(), h.context)
        self.assertEqual(result.state, 'BLOCKED'); self.assertEqual(h.native.calls, 0)

    def test_stop_in_restoration_final_clock_denies_the_distinct_effect(self):
        h = self.h; now = h.now; calls = []; armed = False; plans = 0
        original_plan = h.controller.plan
        def plan(*args, **kwargs):
            nonlocal armed, plans
            result = original_plan(*args, **kwargs); plans += 1
            if plans == 2: armed = True
            return result
        def clock():
            nonlocal armed
            if armed: armed = False; h.controller.stop()
            return now
        def restore(*args, **kwargs):
            kwargs['dispatch_fence'](); calls.append(args)
            raise AssertionError('Cancelled restoration must not dispatch')
        h.native.restore_cpu_rate_limit = restore; h.controller._clock = clock
        from unittest.mock import patch
        intent = h.intent(operation_id='restore:clock', restoration_of='throttle:prior',
            expected_limit=replace(h.intent().expected_limit, limit=CpuRateLimit.hard_cap(500)), proposed_limit=CpuRateLimit(0, 0))
        with patch.object(h.controller, 'plan', plan): result = h.execute(intent)
        self.assertEqual((result.state, calls, h.native.calls), ('BLOCKED', [], 0))

    def test_real_thread_stop_wins_during_last_owner_callback_without_waiting_for_it(self):
        h = self.h; entered = threading.Event(); release = threading.Event(); checks = 0
        def hook():
            nonlocal checks
            checks += 1
            if checks == 2: entered.set(); self.assertTrue(release.wait(3))
        h.owner.hook = hook
        worker, outputs, faults = self.run_worker(h.execute)
        try:
            self.assertTrue(entered.wait(3)); started = time.perf_counter_ns(); h.controller.stop()
            self.assertLess(time.perf_counter_ns() - started, 250_000_000); self.assertTrue(worker.is_alive())
        finally: release.set(); worker.join(3)
        self.assertFalse(worker.is_alive()); self.assertEqual(faults, [])
        self.assertEqual((outputs[0].state, h.native.calls, h.owner.outcomes), ('BLOCKED', 0, []))

    def test_stop_after_logical_admission_retains_the_inflight_effect(self):
        h = self.h; admitted = threading.Event(); release = threading.Event(); original = h.native.apply_cpu_rate_limit
        def admitted_call(*args, **kwargs):
            kwargs.pop('dispatch_fence')(); admitted.set(); self.assertTrue(release.wait(3))
            return original(*args, **kwargs)
        h.native.apply_cpu_rate_limit = admitted_call
        worker, outputs, faults = self.run_worker(h.execute)
        try: self.assertTrue(admitted.wait(3)); h.controller.stop()
        finally: release.set(); worker.join(3)
        self.assertFalse(worker.is_alive()); self.assertEqual(faults, [])
        self.assertEqual((outputs[0].state, h.native.calls, len(h.owner.outcomes)), ('APPLIED', 1, 1))
        self.assertEqual(h.controller.plan(h.intent(operation_id='throttle:later')).state, 'CANCELLED')

    def test_stop_after_observed_effect_keeps_the_recorded_change(self):
        h = self.h; h.native.after = lambda change: h.controller.stop()
        result = h.execute()
        self.assertEqual((result.state, result.change.state, h.native.calls), ('APPLIED', 'APPLIED', 1))
        self.assertEqual(h.owner.outcomes, [result.change])

    def test_native_adapter_ignoring_the_dispatch_fence_cannot_report_success(self):
        h = self.h; original = h.native.apply_cpu_rate_limit
        def unfenced(*args, **kwargs):
            kwargs.pop('dispatch_fence'); return original(*args, **kwargs)
        h.native.apply_cpu_rate_limit = unfenced; result = h.execute()
        self.assertEqual((result.state, result.change.state, h.native.calls), ('UNCERTAIN', 'APPLIED', 1))
        self.assertEqual(result.reason_codes, ('THROTTLE_DISPATCH_FENCE_NOT_OBSERVED',))

    def test_current_owner_revocation_in_final_fence_denies_before_effect(self):
        h = self.h; checks = 0
        def revoke():
            nonlocal checks
            checks += 1
            if checks == 2: h.owner.current = False
        h.owner.hook = revoke; result = h.execute()
        self.assertEqual((result.state, h.native.calls), ('BLOCKED', 0))
        self.assertEqual(result.reason_codes, ('CONTROLLED_AUTHORITY_REVOKED',))

    def test_primary_interruption_in_final_fence_keeps_unspent_native_effect(self):
        h = self.h; primary = KeyboardInterrupt('final controlled owner fence'); checks = 0
        def interrupt():
            nonlocal checks
            checks += 1
            if checks == 2: raise primary
        h.owner.hook = interrupt
        with self.assertRaises(KeyboardInterrupt) as caught: h.execute()
        self.assertIs(caught.exception, primary); self.assertEqual(h.native.calls, 0)
        self.assertIn(h.intent().operation_id, h.owner.operations)
