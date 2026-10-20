"""Controlled original-object tests; no SQL, native process, consent or Set.

Exact production classes are populated with explicitly controlled retained
state. Native observation and canonical dispatch/write calls are substituted;
these checks qualify the local binding logic, not production integration.
"""
import copy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import threading
import time
import unittest
from unittest.mock import patch

from ceta.contracts.kernel_transactions import PeerIdentity
from ceta.contracts.real_effect import CpuEffectObservation, decode_cpu_effect_observation, decode_owned_cpu_request
from ceta.contracts.resource_management import ObservationState, ProcessResourceIdentity
from ceta.contracts.wire import ContractError, RecordCodec, canonical_bytes, strict_loads
from ceta.contracts.workload_throttling import CpuRateChange, CpuRateObservation
from ceta.identity.native_clock import NativeSessionClock
from ceta.identity.native_cpu_outcome import NativeCpuOutcomeProvenance
import ceta.identity.native_cpu_outcome as module
import ceta.composition.native_cpu_outcome as adapter_module
from ceta.effects.native_observer import NativeCpuEffectObserver, _ObservationOrigin
from ceta.kernel.cpu_execution import _CpuExecutionCoordinator, _RetainedCpuExecution
from ceta.kernel.effect_transactions import OwnedCpuOutcome
from ceta.kernel.transactions import KernelTransactions
from ceta.store.journal import SqliteJournal
from ceta.identity.native_owner_view import NativeOwnerView
from ceta.identity.owner_session import NativeCpuOwnerSession, _NativeCpuExecutionRetainer
from ceta.supervisor.windows_jobs import WindowsOwnedProcess
import test_owner_authority_transactions as data

ROOT = Path(__file__).resolve().parents[2]
TIMINGS = []


class CpuOutcomeProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.codec = RecordCodec(strict_loads((ROOT / 'contracts/schemas/records.schema.json').read_bytes()))

    def setUp(self):
        self.request = data.effect_request(data.enrollment_request())
        self.clock = object.__new__(NativeSessionClock)
        self.view = object.__new__(NativeOwnerView)
        self.view._clock = self.clock
        self.view._store = SimpleNamespace(_database_path=Path('CONTROLLED-NOT-OPENED.sqlite3'))
        self.store = object.__new__(SqliteJournal)
        self.store.path, self.store._lock = self.view._store._database_path, threading.RLock()
        self.store._closed, self.store._read_only, self.store._codec = False, False, self.codec
        self.kernel = object.__new__(KernelTransactions)
        self.owner = object.__new__(NativeCpuOwnerSession)
        self.kernel._owners, self.kernel._store, self.kernel._codec = self.owner, self.store, self.codec
        self.owner._view, self.owner._native_clock, self.owner._preparation_kernel = self.view, self.clock, self.kernel
        self.owner._closed = False
        self.coordinator = object.__new__(_CpuExecutionCoordinator)
        self.coordinator.kernel, self.coordinator.store, self.coordinator.owners = self.kernel, self.store, self.owner
        self.coordinator.stop_lock, self.coordinator.stopped = self.store._lock, threading.Event()
        self.kernel._cpu_execution = self.coordinator
        self.context, self.binding, self.capture, self.approval = object(), object(), object(), object()
        self.target = object.__new__(WindowsOwnedProcess)
        self.peer = PeerIdentity(self.request.principal_id, self.request.actor_session)
        p = dict(record_type='OperationPermit', schema_version='1', record_id='permit:controlled',
            scope_id=self.request.scope_id, causation_ref='event:issued', grant_ref='grant:controlled',
            task_id=self.request.task_id, proposal_ref=self.request.proposal_id, adapter_id='adapter:cpu',
            adapter_commitment=self.request.adapter_commitment, operation=self.request.operation,
            arguments_commitment=self.request.input_commitment, input_commitment=data.H,
            candidate_commitment=None, resources=[dict(resource_id='worker:controlled', revision=None,
            access='WRITE', scope_id=self.request.scope_id)], policy_commitment=data.H, review_refs=[],
            approval_evidence_ref=None, environment_commitment=data.H, authority_generation=0,
            fence_generation=0, nonce='nonce:controlled', expires_at='2026-10-18T12:00:00Z',
            reservation_ref='reservation:controlled', issuance_evidence_ref='event:issued',
            consume_event_ref='event:consumed', status='CONSUMED')
        permit = self.codec.decode(canonical_bytes(p))
        self.lease = object.__new__(_RetainedCpuExecution)
        for name, value in dict(_owner=self.coordinator, _request=self.request, _wire=self.request.canonical_wire,
            _permit=permit, _attempt=OwnedCpuOutcome(canonical_bytes(dict(state='ATTEMPT_COMMITTED',
                attempt_index=dict(event_id='event:actual-attempt'))), None, None, None),
            _consumption=SimpleNamespace(consumed_permit_wire=permit.canonical_wire),
            _target=self.target, _binding=self.binding, _capture=self.capture, _proof=self.approval,
            _context=self.context, _thread=threading.get_ident(), _entered=True, _closed=False,
            _pending_cleanup=False, _dispatch=True, _called=True, _dispatching=False, _change=None).items():
            setattr(self.lease, name, value)
        self.coordinator.active = self.lease
        self.retained = object.__new__(_NativeCpuExecutionRetainer)
        self.owner._dispatch = (self.context, threading.get_ident(), object())
        for name, value in dict(owner=self.owner, coordinator=self.coordinator, kernel=self.kernel,
            lease=self.lease, state='ACTIVE', pending=False, thread=threading.get_ident(),
            context=self.context, dispatch=self.owner._dispatch, target=self.target, binding=self.binding,
            capture=self.capture, proof=self.approval, wire=self.lease._wire, peer=self.peer).items():
            setattr(self.retained, name, value)
        self.owner._execution = self.lease._retained = self.lease._manager = self.retained
        self.observer = object.__new__(NativeCpuEffectObserver)
        self.observer._clock, self.observer._lock = self.clock, threading.Lock()
        self.observer._executable, self.observer._image, self.observer._driver_sha = 'CONTROLLED-NOT-LAUNCHED', 'b'*64, 'c'*64
        self.observer._commitment = self.request.observer_commitment
        self.observer._origin, self.observer._sequence = None, 0
        self.producer = self.view._cpu_outcome = NativeCpuOutcomeProvenance(self.view, self.observer)
        self.sequence, self.observe_error, self.return_substitute = 0, None, None
        self.observed = []
        control = patch.object(module, '_OBSERVE', self.controlled_observe)
        control.start(); self.addCleanup(control.stop)

    def controlled_observe(self, observer, request, target):
        self.assertIs(observer, self.observer); self.assertIs(request, self.request); self.assertIs(target, self.target)
        observer._origin = None
        if self.observe_error is not None: raise self.observe_error
        self.sequence += 1
        value = CpuEffectObservation(request.input_commitment, request.request_id, request.process_identity,
            request.job_digest, ProcessResourceIdentity(105, 100, 'sha256:' + 'b'*64),
            request.observer_commitment, self.sequence, data.clock(1_200_000_000 + self.sequence*1_000_000),
            ObservationState.MEASURED, request.target_limit, 'LIVE_IN_OWNED_JOB')
        observer._sequence = value.sequence
        observer._origin = _ObservationOrigin(observer, target, request.canonical_wire, value, value.canonical_wire, value.sequence)
        self.observed.append(value)
        return value if self.return_substitute is None else self.return_substitute(value)

    def collect(self): return self.producer.collect(self.lease)

    def callback(self, capture, **changes):
        values = dict(view=self.view, request=decode_owned_cpu_request(self.request.canonical_wire),
            permit=self.codec.decode(self.lease._permit.canonical_wire), receipt=self.codec.decode(capture.receipt_wire),
            observation=None if capture.observation_wire is None else decode_cpu_effect_observation(capture.observation_wire),
            proof=capture.proof, peer=PeerIdentity(self.peer.principal_id, self.peer.session_id),
            context=self.context, retained=self.retained)
        values.update(changes)
        return self.producer.require_current(**values)

    def test_original_producer_accepts_decoded_dtos_and_uses_original_observation(self):
        captured = self.collect()
        with patch.object(module, '_ORIGIN', wraps=module._ORIGIN) as origin:
            self.assertIsNone(self.callback(captured))
        self.assertIs(origin.call_args.args[3], self.observed[-1])
        self.assertIs(origin.call_args.args[2], self.target)
        receipt = strict_loads(captured.receipt_wire)
        self.assertEqual(receipt['dispatch_event_ref'], 'event:actual-attempt')
        self.assertEqual(receipt['permit_ref'], self.lease._permit.record_id)
        self.assertEqual(receipt['effect_status'], 'MAY_HAVE_EXECUTED')
        self.assertIsNone(receipt['exit_code']); self.assertIsNone(receipt['started_at'])

    def test_caller_boolean_digest_object_or_copied_capture_cannot_supply_origin(self):
        captured = self.collect()
        for fake in (True, False, data.H, object(), copy.copy(captured)):
            with self.subTest(fake=type(fake).__name__), self.assertRaises(ContractError):
                self.callback(captured, proof=fake)

    def test_forged_receipt_equal_operation_with_altered_claim_is_rejected(self):
        captured = self.collect()
        for field, value in (('effect_status', 'OBSERVED_EFFECT'), ('exit_code', 0),
                             ('dispatch_event_ref', 'event:invented'), ('record_id', 'receipt:other')):
            raw = strict_loads(captured.receipt_wire); raw[field] = value
            with self.subTest(field=field), self.assertRaises(ContractError):
                self.callback(captured, receipt=self.codec.decode(canonical_bytes(raw)))

    def test_changed_request_permit_peer_context_retainer_or_view_is_rejected(self):
        captured = self.collect()
        changed_permit = self.lease._permit.as_dict(); changed_permit['nonce'] = 'nonce:other'
        cases = dict(request=replace(self.request, task_id='task:other'),
            permit=self.codec.decode(canonical_bytes(changed_permit)), peer=PeerIdentity('owner:other', self.peer.session_id),
            context=object(), retained=object(), view=object())
        for key, value in cases.items():
            with self.subTest(key=key), self.assertRaises(ContractError): self.callback(captured, **{key: value})

    def test_lease_flags_deny_before_dispatch_during_dispatch_and_after_retirement(self):
        for field, value in (('_dispatch', False), ('_called', False), ('_dispatching', True),
                             ('_entered', False), ('_closed', True), ('_pending_cleanup', True)):
            original = getattr(self.lease, field); setattr(self.lease, field, value)
            try:
                with self.subTest(field=field), self.assertRaises(ContractError): self.collect()
            finally: setattr(self.lease, field, original)
        self.assertEqual(self.observed, [])

    def test_coordinator_store_owner_and_retainer_substitution_is_rejected(self):
        captured = self.collect()
        cases = ((self.coordinator, 'active', object()), (self.kernel, '_store', object()),
            (self.kernel, '_owners', object()), (self.owner, '_view', object()),
            (self.lease, '_retained', object()), (self.retained, 'target', object()),
            (self.view, '_cpu_outcome', object()), (self.lease, '_context', object()))
        for owner, field, value in cases:
            original = getattr(owner, field); setattr(owner, field, value)
            try:
                with self.subTest(field=field), self.assertRaises(ContractError): self.callback(captured)
            finally: setattr(owner, field, original)

    def test_original_thread_is_required(self):
        captured = self.collect(); errors = []
        def other():
            try: self.callback(captured)
            except BaseException as error: errors.append(error)
        thread = threading.Thread(target=other); thread.start(); thread.join(3)
        self.assertFalse(thread.is_alive()); self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], ContractError)

    def test_mutating_retained_request_observation_and_change_is_rejected(self):
        observed = CpuRateObservation(self.request.process_identity, self.request.job_digest,
            ObservationState.MEASURED, self.request.target_limit, 2, 1_100_000_000)
        self.lease._change = CpuRateChange(self.request.request_id, self.request.process_identity,
            self.request.job_digest, self.request.original_limit, self.request.target_limit, observed, 'APPLIED', 'NATIVE_OBSERVED')
        captured = self.collect()
        for owner, name, value in ((self.request, 'task_id', 'task:mutated'),
            (self.observed[-1], 'operation_id', 'request:mutated'), (self.lease._change, 'reason', 'MUTATED')):
            original = getattr(owner, name); object.__setattr__(owner, name, value)
            try:
                with self.subTest(name=name), self.assertRaises(ContractError): self.callback(captured)
            finally: object.__setattr__(owner, name, original)

    def test_equal_replacement_of_original_change_or_permit_is_rejected(self):
        captured = self.collect()
        original = self.lease._permit
        self.lease._permit = self.codec.decode(original.canonical_wire)
        try:
            with self.assertRaises(ContractError): self.callback(captured)
        finally: self.lease._permit = original

    def test_copy_returned_by_observer_is_not_original_provenance(self):
        self.return_substitute = copy.copy
        captured = self.collect()
        self.assertIsInstance(captured.observation_error, ContractError)
        self.assertIsNone(captured.observation_wire)
        self.assertIsNone(self.callback(captured))
        with self.assertRaises(ContractError): self.callback(captured, observation=self.observed[-1])

    def test_missing_observation_is_honest_uncertainty_with_exact_error(self):
        primary = KeyboardInterrupt('CONTROLLED_OBSERVER_UNAVAILABLE'); self.observe_error = primary
        captured = self.collect()
        self.assertIs(captured.observation_error, primary); self.assertIsNone(captured.observation_wire)
        self.assertEqual(strict_loads(captured.receipt_wire)['effect_status'], 'MAY_HAVE_EXECUTED')
        self.assertIsNone(self.callback(captured))

    def test_advancing_observation_keeps_original_receipt_and_retires_prior_proof(self):
        first = self.collect(); second = self.collect()
        self.assertEqual(first.receipt_wire, second.receipt_wire)
        self.assertNotEqual(first.observation_wire, second.observation_wire)
        with self.assertRaises(ContractError): self.callback(first)
        self.assertIsNone(self.callback(second))

    def test_observer_current_sequence_and_identity_binding_are_required(self):
        captured = self.collect(); self.observer._sequence += 1
        with self.assertRaises(ContractError): self.callback(captured)
        self.observer._sequence -= 1
        self.observer._image = 'd'*64
        with self.assertRaises(ContractError): self.callback(captured)

    def test_refresh_failure_cannot_keep_old_success_proof(self):
        first = self.collect(); self.observe_error = OSError('CONTROLLED_REFRESH_FAILURE')
        second = self.collect()
        self.assertEqual(first.receipt_wire, second.receipt_wire)
        with self.assertRaises(ContractError): self.callback(first)
        self.assertIsNone(self.callback(second))

    def test_observer_replay_is_not_promoted(self):
        first = self.collect(); self.sequence = 0
        second = self.collect()
        self.assertIsInstance(second.observation_error, ContractError)
        self.assertIsNone(second.observation_wire)
        self.assertEqual(second.receipt_wire, first.receipt_wire)

    def test_stop_after_dispatch_keeps_bookkeeping_and_original_receipt(self):
        first = self.collect(); self.coordinator.stopped.set()
        self.assertIsNone(self.callback(first))
        second = self.collect()
        self.assertEqual(second.receipt_wire, first.receipt_wire)
        self.assertEqual(strict_loads(first.receipt_wire)['cancellation_state'], 'NONE')
        self.assertIsNone(self.callback(second))

    def test_stop_before_first_receipt_is_recorded_as_requested_not_observed_stopped(self):
        self.coordinator.stopped.set(); capture = self.collect()
        self.assertEqual(strict_loads(capture.receipt_wire)['cancellation_state'], 'REQUESTED')
        self.assertEqual(strict_loads(capture.receipt_wire)['effect_status'], 'MAY_HAVE_EXECUTED')

    def test_callback_is_pure_and_measured_below_existing_gate(self):
        captured = self.collect()
        with patch.object(module, '_OBSERVE', side_effect=AssertionError('NATIVE_QUERY')), \
                patch.object(self.kernel, '_peer', side_effect=AssertionError('AUTH')), \
                patch.object(self.store, 'snapshot', create=True, side_effect=AssertionError('SQL')), \
                patch.object(time, 'sleep', side_effect=AssertionError('WAIT')):
            started = time.perf_counter_ns(); self.callback(captured); elapsed = time.perf_counter_ns() - started
        TIMINGS.append(elapsed)
        self.assertLessEqual(elapsed, 50_000_000)

    def test_busy_owner_refuses_without_wait(self):
        captured = self.collect(); self.producer._lock.acquire()
        try:
            with self.assertRaisesRegex(ContractError, 'CPU_OUTCOME_BUSY'): self.callback(captured)
        finally: self.producer._lock.release()

    def test_owner_cannot_be_copied_or_deep_copied(self):
        for copier in (copy.copy, copy.deepcopy):
            with self.assertRaises(ContractError): copier(self.producer)

    def test_adapter_dispatches_once_then_uses_existing_record_method(self):
        adapter = adapter_module.NativeCpuOutcomeAdapter(self.view)
        self.lease._called = self.lease._dispatch = False
        events = []
        def dispatch(lease):
            self.assertIs(lease, self.lease); events.append('dispatch')
            lease._called = lease._dispatch = True
        def record(lease, receipt, observation, proof):
            events.append('record')
            capture = module.CpuOutcomeCapture(receipt, observation, proof, None)
            self.callback(capture)
            return 'CONTROLLED_CANONICAL_RESULT'
        with patch.object(adapter_module, '_DISPATCH', dispatch), patch.object(adapter_module, '_RECORD', record):
            self.assertEqual(adapter.execute(self.lease), 'CONTROLLED_CANONICAL_RESULT')
            with self.assertRaises(ContractError): adapter.execute(self.lease)
        self.assertEqual(events, ['dispatch', 'record'])

    def test_adapter_keeps_primary_dispatch_error_when_observation_and_writer_fail(self):
        adapter = adapter_module.NativeCpuOutcomeAdapter(self.view)
        self.lease._called = self.lease._dispatch = False
        primary, secondary, tertiary = KeyboardInterrupt('DISPATCH'), OSError('OBSERVER'), RuntimeError('WRITER')
        self.observe_error = secondary
        def dispatch(lease):
            lease._called = lease._dispatch = True
            raise primary
        with patch.object(adapter_module, '_DISPATCH', dispatch), patch.object(adapter_module, '_RECORD', side_effect=tertiary):
            with self.assertRaises(KeyboardInterrupt) as caught: adapter.execute(self.lease)
        self.assertIs(caught.exception, primary)
        self.assertIs(primary.owned_cpu_execution, self.lease)
        self.assertIn(secondary, primary.cpu_outcome_secondary_errors)
        self.assertIn(tertiary, secondary.cpu_outcome_secondary_errors)

    def test_adapter_never_observes_or_records_when_dispatch_not_admitted(self):
        adapter = adapter_module.NativeCpuOutcomeAdapter(self.view)
        self.lease._called = self.lease._dispatch = False
        primary = SystemExit('NOT_ADMITTED')
        with patch.object(adapter_module, '_DISPATCH', side_effect=primary), \
                patch.object(adapter_module, '_RECORD', side_effect=AssertionError('MUST_NOT_WRITE')):
            with self.assertRaises(SystemExit) as caught: adapter.execute(self.lease)
        self.assertIs(caught.exception, primary); self.assertEqual(self.observed, [])

    def test_adapter_records_uncertainty_and_reraises_exact_observer_error(self):
        adapter = adapter_module.NativeCpuOutcomeAdapter(self.view)
        primary = KeyboardInterrupt('OBSERVER'); self.observe_error = primary
        def record(lease, receipt, observation, proof):
            self.assertIsNone(observation)
            self.callback(module.CpuOutcomeCapture(receipt, observation, proof, primary))
            return 'CONTROLLED_UNCERTAIN_OUTCOME'
        with patch.object(adapter_module, '_RECORD', record):
            with self.assertRaises(KeyboardInterrupt) as caught: adapter.reconcile(self.lease)
        self.assertIs(caught.exception, primary)
        self.assertEqual(primary.cpu_recorded_outcome, 'CONTROLLED_UNCERTAIN_OUTCOME')

    def test_reconciliation_never_redispatches(self):
        adapter = adapter_module.NativeCpuOutcomeAdapter(self.view)
        wires = []
        def record(lease, receipt, observation, proof):
            wires.append(receipt); self.callback(module.CpuOutcomeCapture(receipt, observation, proof, None))
            return 'CONTROLLED_RECONCILIATION'
        with patch.object(adapter_module, '_DISPATCH', side_effect=AssertionError('REPLAY')), \
                patch.object(adapter_module, '_RECORD', record):
            adapter.reconcile(self.lease); adapter.reconcile(self.lease)
        self.assertEqual(wires[0], wires[1])


if __name__ == '__main__': unittest.main()
