"""Deterministic diagnostics on actual SQLite admission, with controlled owners.

Elapsed values and targets here are controlled; no Windows target or effect is
created. The original seven native methods require a separate authorization.
"""
import unittest
from unittest.mock import patch

from ceta.contracts.wire import ContractError
from ceta.kernel import cpu_execution as execution
import test_cpu_execution_admission as original


class CpuTimingDiagnosticTests(unittest.TestCase):
    fixture = original.CpuExecutionAdmissionTests.fixture
    lease = original.CpuExecutionAdmissionTests.lease
    status = original.CpuExecutionAdmissionTests.status
    arm_domain_fence = original.CpuExecutionAdmissionTests.arm_domain_fence

    @classmethod
    def setUpClass(cls):
        original.CpuExecutionAdmissionTests.setUpClass.__func__(cls)

    def ticks(self, fixture):
        # This source controls only the current method's nonnative arithmetic.
        counter = [max(0, fixture.kernel._cpu_execution.elapsed_highwater)+1_000_000_000]
        return counter, patch.object(execution.time, 'perf_counter_ns', side_effect=lambda: counter[0])

    def diagnostic(self, error, phase, elapsed, resolution):
        data = BaseException.__dict__['__dict__'].__get__(error)
        self.assertEqual(dict.get(data, 'owned_cpu_timing'), dict(phase=phase,
            elapsed_ns=elapsed, bound_ns=50_000_000, resolution_ns=resolution))
        self.assertEqual(execution.MAXIMUM_CHECK_NS, 50_000_000)

    def entry(self, fixture, counter, elapsed):
        resolution = fixture.kernel._cpu_execution.resolution
        enter = original.ControlledRetainer.__enter__
        def delayed(manager):
            value = enter(manager)
            counter[0] += elapsed-2*resolution
            return value
        return patch.object(original.ControlledRetainer, '__enter__', delayed)

    def test_entry_overrun_retains_exact_terms_and_closed_prepared_custody(self):
        fixture = self.fixture(); counter, elapsed = self.ticks(fixture)
        lease = self.lease(fixture); resolution = fixture.kernel._cpu_execution.resolution
        with elapsed, self.entry(fixture, counter, 50_000_001):
            with self.assertRaisesRegex(ContractError, 'CPU_EXECUTION_ENTRY_TOO_SLOW') as raised:
                lease.__enter__()
        self.diagnostic(raised.exception, 'ENTRY', 50_000_001, resolution)
        self.assertIs(raised.exception.owned_cpu_execution, lease)
        self.assertTrue(lease.inspection()['closed']); self.assertFalse(lease.inspection()['dispatch_admitted'])
        self.assertFalse(fixture.owners.managers[-1].locked)
        self.assertEqual(self.status(fixture), 'PREPARED')

    def test_owner_overrun_retains_exact_phase_terms_before_consumption(self):
        fixture = self.fixture(); counter, elapsed = self.ticks(fixture)
        lease = self.lease(fixture); resolution = fixture.kernel._cpu_execution.resolution
        def delay(phase):
            if phase == 'CAPACITY': counter[0] += 50_000_001-2*resolution
        fixture.owners.on_execution = delay
        with elapsed:
            with self.assertRaisesRegex(ContractError, 'CPU_EXECUTION_OWNER_TOO_SLOW') as raised:
                lease.__enter__()
        self.diagnostic(raised.exception, 'CAPACITY', 50_000_001, resolution)
        self.assertIs(raised.exception.owned_cpu_execution, lease)
        self.assertTrue(lease.inspection()['closed']); self.assertEqual(self.status(fixture), 'PREPARED')

    def test_entry_success_and_equality_keep_original_inclusive_bound(self):
        for measured in (49_999_999, 50_000_000):
            with self.subTest(measured=measured):
                fixture = self.fixture(); counter, elapsed = self.ticks(fixture)
                lease = self.lease(fixture)
                with elapsed, self.entry(fixture, counter, measured):
                    with lease:
                        self.assertFalse(lease.inspection()['dispatch_admitted'])
                self.assertEqual(self.status(fixture), 'CONSUMED')
                self.assertTrue(lease.inspection()['closed'])

    def test_owner_equality_is_allowed_in_every_existing_phase(self):
        for selected in ('CAPACITY', 'CONSUMED', 'READY', 'DISPATCH'):
            with self.subTest(phase=selected):
                fixture = self.fixture(); counter, elapsed = self.ticks(fixture)
                resolution = fixture.kernel._cpu_execution.resolution
                def delay(phase):
                    if phase == selected: counter[0] += 50_000_000-2*resolution
                fixture.owners.on_execution = delay
                with elapsed:
                    with self.lease(fixture) as lease:
                        if selected == 'DISPATCH': self.arm_domain_fence(lease)
                self.assertTrue(lease.inspection()['closed'])
                self.assertEqual(self.status(fixture), 'CONSUMED')

    def test_later_owner_overruns_retain_consumed_liability_and_exact_phase(self):
        for selected in ('CONSUMED', 'READY', 'DISPATCH'):
            with self.subTest(phase=selected):
                fixture = self.fixture(); counter, elapsed = self.ticks(fixture)
                resolution = fixture.kernel._cpu_execution.resolution
                lease = self.lease(fixture)
                def delay(phase):
                    if phase == selected: counter[0] += 50_000_001-2*resolution
                fixture.owners.on_execution = delay
                with elapsed:
                    with self.assertRaisesRegex(ContractError, 'CPU_EXECUTION_OWNER_TOO_SLOW') as raised:
                        if selected == 'DISPATCH':
                            with lease: self.arm_domain_fence(lease)
                        else: lease.__enter__()
                self.diagnostic(raised.exception, selected, 50_000_001, resolution)
                self.assertIs(raised.exception.owned_cpu_execution, lease)
                self.assertFalse(lease.inspection()['dispatch_admitted'])
                self.assertTrue(lease.inspection()['closed'])
                self.assertEqual(self.status(fixture), 'CONSUMED')

    def test_timing_diagnostics_do_not_query_a_clock(self):
        with patch.object(execution.time, 'perf_counter_ns', side_effect=AssertionError('extra sample')), \
                patch.object(execution.time, 'get_clock_info', side_effect=AssertionError('extra resolution')):
            self.assertIsNone(execution._require_timing(50_000_000, 100, 'ENTRY', 'CPU_EXECUTION_ENTRY_TOO_SLOW'))
            with self.assertRaisesRegex(ContractError, 'CPU_EXECUTION_OWNER_TOO_SLOW') as raised:
                execution._require_timing(50_000_001, 100, 'DISPATCH', 'CPU_EXECUTION_OWNER_TOO_SLOW')
        self.diagnostic(raised.exception, 'DISPATCH', 50_000_001, 100)

    def test_hostile_storage_hooks_cannot_replace_timing_primary_or_lease(self):
        calls = []
        class RefusingStorage(dict):
            def refuse(self, *args, **kwargs):
                calls.append('dictionary'); raise SystemExit('dictionary hook')
            update = get = __getitem__ = __setitem__ = __contains__ = refuse
        class RefusingError(ContractError):
            def __setattr__(self, *args):
                calls.append('attribute'); raise KeyboardInterrupt('setter hook')
            @property
            def add_note(self):
                calls.append('note'); raise MemoryError('note hook')
        primary = ContractError.__new__(RefusingError)
        BaseException.__init__(primary, 'CPU_EXECUTION_OWNER_TOO_SLOW at $')
        storage = RefusingStorage(code='CPU_EXECUTION_OWNER_TOO_SLOW', path='$')
        BaseException.__dict__['__dict__'].__set__(primary, storage)
        fixture = self.fixture(); counter, elapsed = self.ticks(fixture)
        resolution = fixture.kernel._cpu_execution.resolution; lease = self.lease(fixture)
        fixture.owners.on_execution = lambda phase: counter.__setitem__(0, counter[0]+50_000_001-2*resolution)
        require = execution.require
        def reject(condition, code):
            if not condition and code == 'CPU_EXECUTION_OWNER_TOO_SLOW': raise primary
            return require(condition, code)
        with elapsed, patch.object(execution, 'require', side_effect=reject):
            try: lease.__enter__()
            except BaseException as caught: self.assertIs(caught, primary)
            else: self.fail('Timing rejection required')
        self.diagnostic(primary, 'CAPACITY', 50_000_001, resolution)
        self.assertIs(dict.get(storage, 'owned_cpu_execution'), lease)
        self.assertIs(dict.get(storage, 'owned_process'), fixture.binding._target)
        self.assertEqual(calls, []); self.assertTrue(lease.inspection()['closed'])

    def test_cleanup_secondary_and_timing_terms_survive_on_same_primary(self):
        fixture = self.fixture(); counter, elapsed = self.ticks(fixture)
        resolution = fixture.kernel._cpu_execution.resolution; lease = self.lease(fixture)
        secondary = OSError('controlled exit refusal'); fixture.owners.exit_error = secondary
        fixture.owners.on_execution = lambda phase: counter.__setitem__(0, counter[0]+50_000_001-2*resolution)
        try:
            with elapsed:
                with self.assertRaisesRegex(ContractError, 'CPU_EXECUTION_OWNER_TOO_SLOW') as raised:
                    lease.__enter__()
            data = BaseException.__dict__['__dict__'].__get__(raised.exception)
            self.diagnostic(raised.exception, 'CAPACITY', 50_000_001, resolution)
            self.assertIs(dict.get(data, 'owned_cpu_cleanup_failure'), secondary)
            self.assertIs(dict.get(data, 'owned_cpu_execution'), lease)
            self.assertTrue(lease.inspection()['pending_cleanup'])
            self.assertIs(lease.inspection()['cleanup_failure'], secondary)
        finally:
            # Explicit fixture custody retirement; product liveness stays pending.
            if fixture.owners.managers: fixture.owners.managers[-1].recover_cleanup()

    def test_diagnostic_allocation_failure_preserves_original_rejection(self):
        primary = ContractError('CPU_EXECUTION_ENTRY_TOO_SLOW')
        with patch.object(execution, 'require', side_effect=primary), \
                patch.object(execution, 'dict', side_effect=MemoryError('diagnostic allocation'), create=True):
            try: execution._require_timing(50_000_001, 100, 'ENTRY', primary.code)
            except BaseException as caught: self.assertIs(caught, primary)
            else: self.fail('Original rejection required')

    def test_control_exceptions_from_existing_predicate_are_not_replaced(self):
        for kind in (KeyboardInterrupt, SystemExit, MemoryError):
            primary = kind('controlled predicate interruption')
            with self.subTest(kind=kind.__name__), patch.object(execution, 'require', side_effect=primary):
                try: execution._require_timing(50_000_001, 100, 'ENTRY', 'CPU_EXECUTION_ENTRY_TOO_SLOW')
                except BaseException as caught: self.assertIs(caught, primary)
                else: self.fail('Original interruption required')
            self.assertNotIn('owned_cpu_timing', BaseException.__dict__['__dict__'].__get__(primary))

    def stop_during_capacity(self, fixture, counter, measured, errors, primary=None):
        resolution = fixture.kernel._cpu_execution.resolution
        def callback(phase):
            if phase != 'CAPACITY': return
            try:
                fixture.kernel.stop_owner_authority(fixture.request.request_id,
                    fixture.owners.context, 'reason:owner-stop')
            except ContractError as pending:
                errors.append(pending)
            counter[0] += measured-2*resolution
            if primary is not None: raise primary
        fixture.owners.on_execution = callback

    def test_authenticated_stop_and_slow_capacity_retains_timing_cause_without_consumption(self):
        fixture = self.fixture(); counter, elapsed = self.ticks(fixture)
        lease = self.lease(fixture); errors = []; before = fixture.store.store_position()
        self.stop_during_capacity(fixture, counter, 61_385_300, errors)
        with elapsed:
            with self.assertRaisesRegex(ContractError, 'CPU_EXECUTION_STOPPED') as raised:
                lease.__enter__()
        self.assertEqual([error.code for error in errors], ['CPU_EXECUTION_CONTROL_DURABLE_PENDING'])
        timing = BaseException.__dict__['__cause__'].__get__(raised.exception)
        self.assertIsInstance(timing, ContractError)
        self.assertEqual(timing.code, 'CPU_EXECUTION_OWNER_TOO_SLOW')
        self.diagnostic(timing, 'CAPACITY', 61_385_300, fixture.kernel._cpu_execution.resolution)
        data = BaseException.__dict__['__dict__'].__get__(raised.exception)
        self.assertIs(dict.get(data, 'owned_cpu_execution'), lease)
        self.assertIs(dict.get(data, 'owned_process'), fixture.binding._target)
        self.assertTrue(lease.inspection()['closed']); self.assertFalse(lease.inspection()['pending_cleanup'])
        self.assertTrue(lease.inspection()['stopped']); self.assertFalse(lease.inspection()['dispatch_admitted'])
        self.assertEqual(self.status(fixture), 'PREPARED'); self.assertEqual(fixture.store.store_position(), before)
        self.assertTrue(all(not manager.locked for manager in fixture.owners.managers))
        self.assertFalse(original.NATIVE_ADMISSION_RECEIPTS)

    def test_authenticated_stop_at_owner_bound_keeps_stop_without_timing_cause(self):
        fixture = self.fixture(); counter, elapsed = self.ticks(fixture)
        lease = self.lease(fixture); errors = []; before = fixture.store.store_position()
        self.stop_during_capacity(fixture, counter, 50_000_000, errors)
        with elapsed:
            with self.assertRaisesRegex(ContractError, 'CPU_EXECUTION_STOPPED') as raised:
                lease.__enter__()
        self.assertEqual([error.code for error in errors], ['CPU_EXECUTION_CONTROL_DURABLE_PENDING'])
        self.assertIsNone(BaseException.__dict__['__cause__'].__get__(raised.exception))
        self.assertEqual(self.status(fixture), 'PREPARED'); self.assertEqual(fixture.store.store_position(), before)
        self.assertTrue(lease.inspection()['closed']); self.assertFalse(lease.inspection()['dispatch_admitted'])
        self.assertEqual(execution.MAXIMUM_CHECK_NS, 50_000_000)

    def test_callback_primary_survives_matching_stop_and_controlled_overrun(self):
        for kind in (KeyboardInterrupt, SystemExit, MemoryError, OSError, ContractError):
            with self.subTest(kind=kind.__name__):
                fixture = self.fixture(); counter, elapsed = self.ticks(fixture)
                lease = self.lease(fixture); errors = []; before = fixture.store.store_position()
                primary = kind('controlled callback refusal')
                self.stop_during_capacity(fixture, counter, 61_385_300, errors, primary)
                with elapsed:
                    try: lease.__enter__()
                    except BaseException as caught: self.assertIs(caught, primary)
                    else: self.fail('Exact callback primary required')
                self.assertEqual([error.code for error in errors], ['CPU_EXECUTION_CONTROL_DURABLE_PENDING'])
                self.assertIsNone(BaseException.__dict__['__cause__'].__get__(primary))
                self.assertNotIn('owned_cpu_timing', BaseException.__dict__['__dict__'].__get__(primary))
                self.assertEqual(self.status(fixture), 'PREPARED'); self.assertEqual(fixture.store.store_position(), before)
                self.assertTrue(lease.inspection()['closed']); self.assertFalse(lease.inspection()['dispatch_admitted'])

    def test_stop_primary_keeps_timing_cause_and_exact_cleanup_secondary(self):
        fixture = self.fixture(); counter, elapsed = self.ticks(fixture)
        lease = self.lease(fixture); errors = []; before = fixture.store.store_position()
        secondary = OSError('controlled cleanup refusal'); fixture.owners.exit_error = secondary
        self.stop_during_capacity(fixture, counter, 61_385_300, errors)
        try:
            with elapsed:
                with self.assertRaisesRegex(ContractError, 'CPU_EXECUTION_STOPPED') as raised:
                    lease.__enter__()
            self.assertEqual([error.code for error in errors], ['CPU_EXECUTION_CONTROL_DURABLE_PENDING'])
            data = BaseException.__dict__['__dict__'].__get__(raised.exception)
            self.assertIs(dict.get(data, 'owned_cpu_execution'), lease)
            self.assertIs(dict.get(data, 'owned_cpu_cleanup_failure'), secondary)
            timing = BaseException.__dict__['__cause__'].__get__(raised.exception)
            self.assertEqual(timing.code, 'CPU_EXECUTION_OWNER_TOO_SLOW')
            self.diagnostic(timing, 'CAPACITY', 61_385_300, fixture.kernel._cpu_execution.resolution)
            self.assertTrue(lease.inspection()['pending_cleanup'])
            self.assertIs(lease.inspection()['cleanup_failure'], secondary)
            self.assertFalse(lease.inspection()['dispatch_admitted'])
            self.assertEqual(self.status(fixture), 'PREPARED'); self.assertEqual(fixture.store.store_position(), before)
        finally:
            if fixture.owners.managers: fixture.owners.managers[-1].recover_cleanup()
