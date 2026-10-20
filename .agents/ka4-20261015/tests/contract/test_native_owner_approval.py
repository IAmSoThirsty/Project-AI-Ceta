"""Actual no-prompt native tests and labelled data/owner fixtures; no genuine approval."""
from contextlib import closing
import ctypes as C
from dataclasses import replace
import hashlib
import struct
import threading
import time
import unittest
from unittest.mock import patch
import uuid
from pathlib import Path

from ceta.contracts.kernel_transactions import BUDGET_FIELDS, BudgetVector
from ceta.contracts.real_effect import OwnedCpuRequest, CAP_OPERATION, approval_display_bytes, approval_display_commitment
from ceta.contracts.resource_management import ObservationState, ProcessResourceIdentity
from ceta.contracts.temporal import ClockSample, Deadline
from ceta.contracts.wire import ContractError, canonical_bytes, strict_loads
from ceta.contracts.workload_throttling import CpuRateLimit, CpuRateObservation
from ceta.identity import native_approval as na

HASH = 'sha256:' + 'a' * 64
MONO, WALL = 1_000_000_000, 1_700_000_000_000_000_000
DWORD, HANDLE = C.c_uint32, C.c_void_p


def handle_state(handle):
    kernel = C.WinDLL('kernel32.dll', use_last_error=True, winmode=0x800)
    call = kernel.GetHandleInformation
    call.restype, call.argtypes = BOOL, [HANDLE, C.POINTER(DWORD)]
    flags = DWORD(); C.set_last_error(0)
    observed = call(handle, C.byref(flags))
    return bool(observed), C.get_last_error(), flags.value


def request():
    identity = ProcessResourceIdentity(11, 2**53 + 33, HASH)
    expected = CpuRateObservation(identity, HASH, ObservationState.MEASURED, CpuRateLimit(0, 7), 0, MONO)
    budget = BudgetVector.from_dict({name: 1000 if name == 'wall_time_ms' else 1 if name == 'max_effects'
        else 8192 if name == 'max_bytes_written' else 0 for name in BUDGET_FIELDS})
    return OwnedCpuRequest('effect:one', 'scope:one', 'task:one', 'proposal:one', 'principal:one',
        'session:one', 'nonce:one', CAP_OPERATION, identity, HASH, expected, CpuRateLimit.hard_cap(1000),
        expected.limit, HASH, HASH, HASH, HASH, HASH, HASH, budget, 8192,
        Deadline('boot:fixture', 1, 0, MONO, MONO + 10_000_000_000, WALL - 1, WALL + 10_000_000_000),
        500_000_000, 100_000_000, ('cpu:reduced', 'restore:separate', 'cleanup:owned'))


def evidence():
    return na.NativeProcessEvidence(ProcessResourceIdentity(22, 44, HASH), 'S-1-5-21-1000',
        'S-1-5-5-1-2', (5, 0), 1, False, 0, 'S-1-16-8192', 96, 3, 0, (8, 0), (9, 0))


def response(item=None, mode='inspect', **changes):
    item = request() if item is None and mode != 'availability' else item
    body = b'' if item is None else item.canonical_wire
    display = b'' if item is None else approval_display_bytes(item)
    value = {'authentication_invoked': False, 'availability': 0,
        'body_sha256': hashlib.sha256(body).hexdigest(), 'challenge_id': 'challenge:one',
        'display_commitment': '' if item is None else approval_display_commitment(item),
        'display_exact': mode == 'inspect', 'display_sha256': hashlib.sha256(display).hexdigest(),
        'hardware_click': False, 'mode': na._MODES[mode], 'native_hresult': 0, 'native_result': None,
        'nonce': '01' * 32, 'protocol': na.PROTOCOL,
        'request_commitment': '' if item is None else item.input_commitment,
        'status': 'AVAILABLE' if mode == 'availability' else 'DISPLAY_BOUND_UNSHOWN',
        'started_qpc': 10, 'finished_qpc': 20, 'qpc_frequency': 1000, 'provenance': evidence().as_dict()}
    value.update(changes)
    wire = canonical_bytes(value)
    return na._RESPONSE_MAGIC + struct.pack('<I', len(wire)) + wire


def parse(wire, item=None, mode='inspect', **changes):
    return na._response(wire, mode=mode, challenge_id='challenge:one', nonce=b'\x01' * 32,
        request=(request() if item is None and mode != 'availability' else item),
        helper=evidence(), cancelled=False, **changes)


def mutated_response(**changes):
    value = strict_loads(response()[12:]); value.update(changes)
    raw = canonical_bytes(value)
    return na._RESPONSE_MAGIC + struct.pack('<I', len(raw)) + raw


class NativeApprovalDataTests(unittest.TestCase):
    def test_exact_body_frame_retains_large_integer_and_complete_display(self):
        item = request()
        wire, frozen = na._frame('inspect', 'challenge:one', b'\x01' * 32, item, 5000)
        self.assertIn(str(2**53 + 33).encode(), wire)
        self.assertIn(item.canonical_wire, wire)
        self.assertEqual(frozen, item)
        self.assertIsNot(frozen, item)
        self.assertEqual(parse(response()).display_commitment, approval_display_commitment(item))

    def test_unvalidated_body_enrollment_and_approved_boolean_are_rejected(self):
        for item in ({'approved': True}, request().as_dict(), request().canonical_wire, True, None):
            with self.subTest(item=type(item).__name__), self.assertRaises(ContractError):
                na._frame('inspect', 'challenge:one', b'\x01' * 32, item, 5000)

    def test_frame_identity_entropy_mode_and_timeout_bounds(self):
        for nonce in (bytes(32), b'x', bytearray(b'x' * 32)):
            with self.subTest(nonce=type(nonce).__name__), self.assertRaises(ContractError):
                na._frame('inspect', 'challenge:one', nonce, request(), 5000)
        for timeout in (True, False, 19, 300001, 1.5):
            with self.subTest(timeout=timeout), self.assertRaises(ContractError):
                na._frame('inspect', 'challenge:one', b'\x01' * 32, request(), timeout)
        for mode in ('enroll', '', True):
            with self.assertRaises(ContractError): na._frame(mode, 'challenge:one', b'\x01' * 32, request(), 5000)
        with self.assertRaises(ContractError): na._frame('availability', 'challenge:one', b'\x01' * 32, request(), 5000)

    def test_native_response_is_data_not_a_noninteractive_approval(self):
        item = parse(response())
        self.assertFalse(item.reported_verified)
        for mode in ('availability', 'inspect', 'cancel'):
            wire = response(mode=mode, status='VERIFIED', authentication_invoked=True,
                hardware_click=True, display_exact=True, native_result=0)
            with self.subTest(mode=mode), self.assertRaises(ContractError): parse(wire, mode=mode)

    def test_response_rejects_unknown_duplicate_trailing_and_oversized_fields(self):
        for wire in (response(extra=True), response() + b' ', b'bad',
                na._RESPONSE_MAGIC + struct.pack('<I', na.MAX_OUTPUT + 1) + bytes(na.MAX_OUTPUT + 1)):
            with self.subTest(length=len(wire)), self.assertRaises(ContractError): parse(wire)
        raw = response()[12:]
        raw = raw.replace(b'{', b'{"mode":2,', 1)
        with self.assertRaises(ContractError): parse(na._RESPONSE_MAGIC + struct.pack('<I', len(raw)) + raw)

    def test_each_response_identity_and_commitment_is_exactly_bound(self):
        for field, value in (('nonce', '02' * 32), ('challenge_id', 'challenge:two'),
                ('request_commitment', HASH), ('display_commitment', HASH), ('body_sha256', '0' * 64),
                ('display_sha256', '0' * 64), ('protocol', 'untrusted'), ('mode', 1)):
            with self.subTest(field=field), self.assertRaises(ContractError): parse(mutated_response(**{field: value}))

    def test_boolean_integer_native_result_and_time_corruption_is_rejected(self):
        for field, value in (('mode', True), ('native_hresult', True), ('native_hresult', 1),
                ('native_result', True), ('native_result', 0), ('availability', True),
                ('authentication_invoked', 0), ('display_exact', 1), ('hardware_click', 0),
                ('started_qpc', False), ('finished_qpc', 9), ('qpc_frequency', 0)):
            with self.subTest(field=field, value=value), self.assertRaises(ContractError): parse(mutated_response(**{field: value}))

    def test_process_user_logon_session_and_token_changes_are_rejected(self):
        baseline = evidence().as_dict()
        for field in baseline:
            value = dict(baseline)
            current = value[field]
            value[field] = not current if type(current) is bool else current + 1 if type(current) is int else current + ':changed'
            with self.subTest(field=field), self.assertRaises(ContractError): parse(response(provenance=value))
        value = dict(baseline); value['terminal_session'] = True
        with self.assertRaises(ContractError): parse(response(provenance=value))

    def test_verified_report_requires_native_click_display_and_result(self):
        base = dict(status='VERIFIED', display_exact=True, authentication_invoked=True, hardware_click=True, native_result=0)
        # Controlled output is parser data only, never an authenticated ceremony.
        self.assertTrue(parse(response(mode='interactive', **base), mode='interactive').reported_verified)
        for field, value in (('display_exact', False), ('hardware_click', False),
                ('authentication_invoked', False), ('native_result', None), ('native_result', 6), ('availability', 1)):
            changed = dict(base); changed[field] = value
            with self.subTest(field=field), self.assertRaises(ContractError):
                parse(response(mode='interactive', **changed), mode='interactive')
        wire = response(mode='interactive', **base)
        result = na._response(wire, mode='interactive', challenge_id='challenge:one', nonce=b'\x01' * 32,
            request=request(), helper=evidence(), cancelled=True)
        self.assertFalse(result.reported_verified)

    def test_native_error_has_no_grant_and_rejects_foreign_provenance(self):
        value = {'error': 'NATIVE_PROTOCOL_OR_RUNTIME_REJECTED', 'status': 'ERROR', 'provenance': evidence().as_dict()}
        raw = canonical_bytes(value); wire = na._RESPONSE_MAGIC + struct.pack('<I', len(raw)) + raw
        with self.assertRaisesRegex(ContractError, 'APPROVAL_NATIVE_REJECTED'): parse(wire)
        value['provenance']['pid'] += 1
        raw = canonical_bytes(value)
        with self.assertRaisesRegex(ContractError, 'PROVENANCE'): parse(na._RESPONSE_MAGIC + struct.pack('<I', len(raw)) + raw)

    def test_sid_and_native_evidence_reject_malformed_bounds(self):
        self.assertEqual(na._sid_text(b'\x01\x01\x00\x00\x00\x00\x00\x10\x00\x20\x00\x00'), 'S-1-16-8192')
        for raw in (b'', b'\x01\x02' + bytes(10), bytes(12), bytearray(12)):
            with self.assertRaises(ContractError): na._sid_text(raw)
        for field, value in (('terminal_session', True), ('ui_access', 2), ('restricted', 1),
                ('token_id', (1, 2**31)), ('authentication_id', [1, 0]), ('elevation_type', 0)):
            with self.subTest(field=field), self.assertRaises(ContractError): replace(evidence(), **{field: value})

    def _controlled_session(self, *, current=None, clock=None):
        # Pure seam fixture. No helper launch, prompt, OS authentication or issuer.
        owner = type('ControlledOwner', (), {})()
        owner._clock = clock
        item = request()
        frame, frozen = na._frame('interactive', 'challenge:one', b'\x01' * 32, item, 5000)
        session = na.NativeApprovalSession(owner, 'interactive', frozen, object(), 5000, frame)
        session.helper_evidence = evidence(); session._current = current
        return session

    def test_canonical_clock_pair_is_required_and_rollback_persists(self):
        first = ClockSample('boot:fixture', 1, 0, MONO, WALL, 1, True)
        times = iter(((first, replace(first, monotonic_ns=MONO + 10)),
            (first, replace(first, monotonic_ns=MONO + 5))))
        session = self._controlled_session(current=lambda *args: None, clock=lambda: next(times))
        session._clock_current()
        with self.assertRaisesRegex(ContractError, 'ROLLBACK'): session._clock_current()
        for pair in (first, (first,), [first, first], (first, True)):
            session = self._controlled_session(current=lambda *args: None, clock=lambda: pair)
            with self.subTest(pair=type(pair).__name__), self.assertRaises(ContractError): session._clock_current()

    def test_canonical_context_uses_exact_opaque_object_and_rejects_boolean(self):
        tick = ClockSample('boot:fixture', 1, 0, MONO, WALL, 1, True)
        seen = []
        session = self._controlled_session(current=lambda *args: seen.append(args), clock=lambda: (tick, tick))
        session._require_current()
        self.assertIs(seen[0][-1], session._context)
        self.assertEqual(seen[0][0], request().canonical_wire)
        self.assertEqual(seen[0][1:3], ('challenge:one', '01' * 32))
        for bad in (True, False, 0, {}, 'approved'):
            session._current = lambda *args: bad
            with self.subTest(bad=bad), self.assertRaises(ContractError): session._require_current()

    def test_expired_untrusted_and_changed_boot_clock_denies_before_native_work(self):
        first = ClockSample('boot:fixture', 1, 0, MONO, WALL, 1, True)
        for current in (replace(first, wall_trusted=False), replace(first, boot_id='boot:changed'),
                replace(first, monotonic_ns=MONO + 10_000_000_000), replace(first, durable_epoch=2)):
            session = self._controlled_session(current=lambda *args: self.fail('lease consulted after bad time'),
                clock=lambda: (first, current))
            with self.subTest(current=current), self.assertRaises(ContractError): session._require_current()


class NativeApprovalNativeTests(unittest.TestCase):
    # The runner supplies a hash-bound actual built helper. Missing native build
    # is an error, never a skipped/claimed production test.
    helper_path = helper_sha256 = fixture_root = None
    observations = []

    def setUp(self):
        self.assertIsNotNone(self.helper_path, 'Actual reviewed native build binding required')
        self.fixture = Path(self.fixture_root) / uuid.uuid4().hex
        self.fixture.mkdir()
        self.owner = na.NativeApprovalOwner(self.helper_path, self.helper_sha256, temporary_root=self.fixture)
        self.sessions = []

    def tearDown(self):
        for session in self.sessions:
            if not session._closed:
                session.cancel()
                if session.process is not None and not session.process.lifetime_closed:
                    if session.process.poll() is None:
                        # These tests never open an interactive gate.
                        self.assertFalse(session.mode == 'interactive' and session._gate_may_open)
                        session.process.terminate(124)
                    self.assertTrue(session.process.wait(5))
                    self.assertEqual(session.process.active_process_count(), 0)
                session._launching = False
                session.close()
            self.observations.append({'test_id': self.id(), 'fixture': str(self.fixture),
                'mode': session.mode, 'gate_may_open': session._gate_may_open,
                'closed': session._closed, 'native_facts': dict(session.native_facts)})
            self.assertFalse(session.pending_native_cleanup)
            self.assertFalse(session._handles)
            self.assertFalse(session._child_handles)
            self.assertIsNone(session._token)
            self.assertIsNone(session._image)
            self.assertIsNone(session._interop_image)

    def started(self, method, *args, **kwargs):
        try:
            session = method(*args, **kwargs)
        except BaseException as error:
            if getattr(error, 'owned_session', None) is not None:
                self.sessions.append(error.owned_session)
            raise
        self.sessions.append(session)
        return session

    def finish(self, session):
        result = session.wait(15)
        self.assertIsNotNone(result)
        self.assertFalse(result.authentication_invoked)
        self.assertFalse(result.hardware_click)
        self.assertIsNone(result.native_result)
        self.assertFalse(result.reported_verified)
        self.assertEqual(session.process.poll(), 0)
        self.assertEqual(session.process.active_process_count(), 0)
        session.close()
        self.assertTrue(session.process.lifetime_closed)
        return result

    def test_actual_availability_measures_private_helper_and_system_interop_library(self):
        session = self.started(self.owner.availability)
        result = self.finish(session)
        self.assertIn(result.status, ('AVAILABLE', 'UNAVAILABLE'))
        self.assertEqual(result.helper.identity.pid, session.native_facts['pid'])
        self.assertEqual(result.helper.identity.creation_time, session.native_facts['creation_time'])
        self.assertEqual(result.helper.identity.image_digest, 'sha256:' + self.helper_sha256)
        self.assertEqual(session.native_facts['inherited_handles'], 4)
        self.assertRegex(session.native_facts['interop_library']['sha256'], r'^[0-9a-f]{64}$')

    def test_actual_hidden_complete_display_preserves_integer_above_double_precision(self):
        item = request()
        session = self.started(self.owner.inspect_request, item)
        result = self.finish(session)
        # Host preflight says Available. A changed host is an explicit failure,
        # never a substitute positive isolation/authentication assertion.
        self.assertEqual(result.availability, 0)
        self.assertEqual(result.status, 'DISPLAY_BOUND_UNSHOWN')
        self.assertTrue(result.display_exact)
        self.assertEqual(result.request_commitment, item.input_commitment)
        self.assertEqual(result.display_commitment, approval_display_commitment(item))

    def test_actual_cancel_mode_uses_no_authentication_or_availability_operation(self):
        session = self.started(self.owner.cancel_without_prompt, request())
        result = self.finish(session)
        self.assertEqual(result.status, 'CANCELLED')
        self.assertIsNone(result.availability)
        self.assertIsNone(result.interop_module)

    def test_default_interactive_and_enrollment_remain_unavailable(self):
        with self.assertRaisesRegex(ContractError, 'CANONICAL_INTEGRATION_UNAVAILABLE'):
            self.owner.begin_interactive(request(), original_context=object())
        with self.assertRaisesRegex(ContractError, 'ENROLLMENT_BODY_AND_KERNEL_UNAVAILABLE'):
            self.owner.begin_enrollment({'approved': True})
        self.assertIsNone(self.owner._active)

    def test_invalid_request_and_hash_cannot_launch_fallback(self):
        with self.assertRaises(ContractError): self.owner.inspect_request({'approved': True})
        self.owner.helper_sha256 = '0' * 64
        with self.assertRaises(na.NativeApprovalError) as caught:
            self.started(self.owner.availability)
        self.assertIsNone(caught.exception.owned_process)
        self.assertTrue(caught.exception.owned_session._closed)
        self.assertIsNone(self.owner._active)

    def test_native_rejects_extra_bytes_before_any_prompt(self):
        original = na._frame
        def altered(*args, **kwargs):
            wire, item = original(*args, **kwargs)
            return wire + b'not-a-request', item
        with patch.object(na, '_frame', altered): session = self.started(self.owner.availability)
        with self.assertRaisesRegex(ContractError, 'NATIVE_REJECTED'): session.wait(15)
        self.assertEqual(session.process.poll(), 0)
        self.assertEqual(session.process.active_process_count(), 0)
        session.close()

    def test_native_rejects_changed_request_digest_and_recovers_next_request(self):
        original = na._frame
        def altered(*args, **kwargs):
            wire, item = original(*args, **kwargs)
            return wire.replace(item.input_commitment.encode(), HASH.encode(), 1), item
        with patch.object(na, '_frame', altered): session = self.started(self.owner.inspect_request, request())
        with self.assertRaisesRegex(ContractError, 'NATIVE_REJECTED'): session.wait(15)
        session.close()
        self.finish(self.started(self.owner.availability))

    def test_native_rejects_noncanonical_and_undeclared_body(self):
        original = na._frame
        for body_change in (lambda body: b' ' + body, lambda body: body.replace(b'ceta-owned-real-effect-v1', b'ceta-owned-real-effect-v9')):
            def altered(*args, **kwargs):
                wire, item = original(*args, **kwargs)
                body = item.canonical_wire; changed = body_change(body)
                marker = struct.pack('<I', len(body)) + body
                return wire.replace(marker, struct.pack('<I', len(changed)) + changed, 1), item
            with self.subTest(change=body_change.__code__.co_firstlineno):
                with patch.object(na, '_frame', altered): session = self.started(self.owner.inspect_request, request())
                with self.assertRaisesRegex(ContractError, 'NATIVE_REJECTED'): session.wait(15)
                session.close()

    def test_stop_during_lifetime_capture_keeps_gate_closed_and_cleans_real_owner(self):
        original = na.NativeApprovalSession._measure_helper
        def stop(session):
            original(session)
            session._owner.cancel_current()
        with patch.object(na.NativeApprovalSession, '_measure_helper', stop):
            with self.assertRaises(na.NativeApprovalError) as caught: self.started(self.owner.availability)
        session = caught.exception.owned_session
        self.assertFalse(session._gate_may_open)
        self.assertTrue(session._closed)
        self.assertTrue(session.process.lifetime_closed)
        self.assertIsNone(self.owner._active)

    def test_control_exception_identity_survives_real_child_and_secondary_token_close_failure(self):
        primary = KeyboardInterrupt('native-approval-test-primary')
        original_close = na._TokenApi.close_handle
        failed = []
        def interrupted(*args):
            raise primary
        def fail_first(api, handle):
            if not failed:
                failed.append(handle)
                raise OSError('native-approval-test-secondary')
            return original_close(api, handle)
        with patch.object(na, '_token_facts', interrupted), patch.object(na._TokenApi, 'close_handle', fail_first):
            with self.assertRaises(KeyboardInterrupt) as caught: self.started(self.owner.availability)
        self.assertIs(caught.exception, primary)
        session = primary.owned_session
        self.assertEqual(session._token, failed[0])
        self.assertTrue(primary.cleanup_errors)
        self.assertTrue(session.process.lifetime_closed)
        self.assertTrue(handle_state(failed[0])[0])
        primary.close_cleanup()
        self.assertIsNone(session._token)
        self.assertTrue(session._closed)
        self.assertEqual(handle_state(failed[0])[:2], (False, 6))

    def test_start_systemexit_retains_primary_and_recoverable_session(self):
        primary = SystemExit(97)
        def fail(session): raise primary
        with patch.object(na.NativeApprovalSession, '_measure_helper', fail):
            with self.assertRaises(SystemExit) as caught: self.started(self.owner.availability)
        self.assertIs(caught.exception, primary)
        self.assertTrue(primary.owned_session._closed)
        self.assertTrue(primary.owned_session.process.lifetime_closed)

    def test_native_handle_outputs_remain_owned_when_duplicate_raises_after_success(self):
        original = na._NativeApi
        created = []
        def factory():
            api = original(); duplicate = api.DuplicateHandle
            def interrupted(*args):
                outcome = duplicate(*args)
                if outcome and not created:
                    created.append(C.cast(args[3], C.POINTER(HANDLE)).contents.value)
                    raise KeyboardInterrupt('native-duplicate-after-output')
                return outcome
            api.DuplicateHandle = interrupted
            return api
        with patch.object(na, '_NativeApi', factory):
            with self.assertRaises(KeyboardInterrupt) as caught: self.started(self.owner.availability)
        self.assertEqual(len(created), 1)
        self.assertTrue(caught.exception.owned_session._closed)
        self.assertFalse(caught.exception.owned_session._child_handles)
        self.assertEqual(handle_state(created[0])[:2], (False, 6))

    def test_pipe_outputs_survive_control_exception_after_actual_native_allocation(self):
        original = na._NativeApi
        created = []
        def factory():
            api = original(); create = api.CreatePipe
            def interrupted(*args):
                outcome = create(*args)
                if outcome:
                    created.extend(C.cast(arg, C.POINTER(HANDLE)).contents.value for arg in args[:2])
                    raise SystemExit(96)
                return outcome
            api.CreatePipe = interrupted
            return api
        with patch.object(na, '_NativeApi', factory):
            with self.assertRaises(SystemExit) as caught: self.started(self.owner.availability)
        self.assertEqual(len(created), 2)
        self.assertTrue(caught.exception.owned_session._closed)
        for handle in created:
            self.assertEqual(handle_state(handle)[:2], (False, 6))

    def test_close_then_raise_never_closes_a_reused_foreign_native_handle(self):
        session = self.started(self.owner.availability)
        self.assertIsNotNone(session.wait(15))
        target = session._handles['output']
        original_close = session._api.close
        primary = KeyboardInterrupt('native-close-completed-before-control')
        foreign, raised = [], []
        def interrupted(handle):
            if handle == target and not raised:
                raised.append(True)
                original_close(handle)
                # Only our own disposable events are allocated; no foreign host
                # process or arbitrary handle is selected or closed.
                for _ in range(256):
                    value = session._api.CreateEventW(None, True, False, None)
                    self.assertTrue(value); foreign.append(value)
                    if value == target: break
                raise primary
            return original_close(handle)
        try:
            with patch.object(session._api, 'close', interrupted):
                with self.assertRaises(KeyboardInterrupt) as caught: session.close()
            self.assertIs(caught.exception, primary)
            self.assertIs(primary.owned_session, session)
            self.assertTrue(foreign)
            session.close()
            self.assertTrue(session._closed)
            for handle in foreign:
                self.assertTrue(handle_state(handle)[0])
            self.observations.append({'test_id': self.id(), 'actual_reused_slot': target in foreign,
                'original_handle': target, 'owned_foreign_handles': list(foreign),
                'foreign_survived_recovery': True, 'closed': True})
            self.assertIn(target, foreign, 'This exact native slot-reuse oracle requires observed reuse')
        finally:
            for handle in foreign: original_close(handle)

    def test_close_failure_continues_independent_handles_and_recovery(self):
        session = self.started(self.owner.availability)
        self.assertIsNotNone(session.wait(15))
        primary = OSError('native-process-close-once')
        with patch.object(session.process, 'close', side_effect=primary):
            with self.assertRaises(OSError) as caught: session.close()
        self.assertIs(caught.exception, primary)
        self.assertFalse(session._handles)
        self.assertIsNone(session._image)
        self.assertIsNone(session._interop_image)
        self.assertFalse(session._closed)
        session.close()
        self.assertTrue(session._closed)
        self.assertTrue(session.process.lifetime_closed)

    def test_one_ceremony_is_owned_while_concurrent_start_is_rejected(self):
        entered, release = threading.Event(), threading.Event()
        original = na.NativeApprovalSession._launch
        results, errors = [], []
        def held(session):
            entered.set(); self.assertTrue(release.wait(5)); original(session)
        def start():
            try: results.append(self.started(self.owner.availability))
            except BaseException as error: errors.append(error)
        with patch.object(na.NativeApprovalSession, '_launch', held):
            thread = threading.Thread(target=start); thread.start()
            try:
                self.assertTrue(entered.wait(5))
                with self.assertRaisesRegex(ContractError, 'ALREADY_OWNED'): self.owner.availability()
            finally:
                release.set(); thread.join(10)
        self.assertFalse(thread.is_alive()); self.assertFalse(errors)
        self.assertEqual(len(results), 1); self.finish(results[0])

    def test_stop_does_not_wait_for_a_blocked_observation_lock(self):
        session = self.started(self.owner.availability)
        entered, release = threading.Event(), threading.Event()
        original, errors = session._read, []
        def read():
            entered.set(); self.assertTrue(release.wait(5)); return original()
        def poll():
            try: session.poll()
            except BaseException as error: errors.append(error)
        with patch.object(session, '_read', read):
            thread = threading.Thread(target=poll); thread.start()
            try:
                self.assertTrue(entered.wait(5))
                started = time.perf_counter_ns(); session.cancel()
                self.assertLess(time.perf_counter_ns() - started, 250_000_000)
            finally:
                release.set(); thread.join(10)
        self.assertFalse(thread.is_alive()); self.assertFalse(errors)
        try:
            result = session.wait(15)
        except ContractError as error:
            # Stop can win before the native reader binds the challenge. That
            # exact native rejection supplies no result/approval and still has
            # to settle the actual exclusively owned helper lifetime.
            self.assertIn('APPROVAL_NATIVE_REJECTED', str(error))
            self.assertTrue(session._stop.is_set())
            self.assertEqual(strict_loads(session._response_bytes[12:])['status'], 'ERROR')
            self.assertEqual(session.process.poll(), 0)
            self.assertEqual(session.process.active_process_count(), 0)
            session.close()
        else:
            self.assertIsNotNone(result)
            self.assertTrue(result.effective_cancelled)
            self.assertFalse(result.authentication_invoked)
            self.assertFalse(result.reported_verified)
            session.close()

    def test_close_refuses_live_native_lifetime_and_cancel_can_settle_it(self):
        original = na._NativeApi
        def factory():
            api = original(); real_set = api.SetEvent
            # Intercept only this no-prompt test's start gate; cancellation is real.
            def set_event(handle):
                active = self.owner._active
                if active is not None and handle == active._handles.get('gate'): return 1
                return real_set(handle)
            api.SetEvent = set_event
            return api
        with patch.object(na, '_NativeApi', factory): session = self.started(self.owner.availability)
        self.assertIsNone(session.process.poll())
        with self.assertRaisesRegex(ContractError, 'LIFETIME_PENDING'): session.close()
        session.cancel()
        with self.assertRaisesRegex(ContractError, 'NATIVE_REJECTED'): session.wait(15)
        self.assertEqual(session.process.active_process_count(), 0)
        session.close(); self.assertTrue(session._closed)

    def test_hidden_result_cannot_be_promoted_by_transcript_or_later_poll(self):
        session = self.started(self.owner.inspect_request, request())
        self.assertIsNotNone(session.wait(15))
        with self.assertRaisesRegex(ContractError, 'VERIFIED_CEREMONY_REQUIRED'): session.transcript()
        session.cancel(); self.assertTrue(session.poll().effective_cancelled)
        session.close()

    def test_poll_control_exception_keeps_owned_response_and_recovers(self):
        session = self.started(self.owner.availability)
        primary = KeyboardInterrupt('native-poll-primary')
        with patch.object(session, '_read', side_effect=primary):
            with self.assertRaises(KeyboardInterrupt) as caught: session.poll()
        self.assertIs(caught.exception, primary)
        self.assertIs(primary.owned_session, session)
        self.finish(session)


BOOL = C.c_int32


class NativeEnrollmentDataTests(unittest.TestCase):
    """Controlled data parsing; reported verification does not authenticate it."""
    def value(self, **changes):
        import test_owner_enrollment as enrollment
        return enrollment.request(helper_identity=evidence().identity, ui_identity=evidence().identity,
            challenge_id='challenge:one', **changes)

    def encoded(self, value, **changes):
        from ceta.contracts.owner_enrollment import enrollment_display_bytes, enrollment_display_commitment
        fields = strict_loads(response()[12:])
        fields.update(body_sha256=hashlib.sha256(value.canonical_wire).hexdigest(),
            request_commitment=value.input_commitment,
            display_sha256=hashlib.sha256(enrollment_display_bytes(value)).hexdigest(),
            display_commitment=enrollment_display_commitment(value))
        fields.update(changes)
        raw = canonical_bytes(fields)
        return na._RESPONSE_MAGIC + struct.pack('<I', len(raw)) + raw

    def test_enrollment_is_a_separate_explicit_frame_domain_with_canonical_backslashes(self):
        value = self.value()
        with self.assertRaises(ContractError): na._frame('inspect', 'challenge:one', b'\x01'*32, value, 5000)
        wire, frozen = na._frame('inspect', 'challenge:one', b'\x01'*32, value, 5000, enrollment=True)
        self.assertEqual(frozen, value);self.assertIsNot(frozen, value)
        self.assertIn(value.canonical_wire, wire)
        self.assertIn(b'\\\\', value.canonical_wire)
        with self.assertRaises(ContractError): na._frame('inspect', 'challenge:one', b'\x01'*32, request(), 5000, enrollment=True)
        for invalid in (0,1,'enrollment',None):
            with self.assertRaises(ContractError):na._frame('inspect','challenge:one',b'\x01'*32,value,5000,enrollment=invalid)

    def test_transport_and_semantic_nonces_have_distinct_exact_bindings(self):
        value = self.value()
        result = na._response(self.encoded(value), mode='inspect', challenge_id='challenge:one',
            nonce=b'\x01'*32, request=value, helper=evidence(), cancelled=False)
        self.assertEqual(result.ceremony_nonce, value.ceremony_nonce)
        self.assertEqual(len(result.ceremony_nonce), 32)
        self.assertNotEqual(result.ceremony_nonce, '01'*32)
        with self.assertRaises(ContractError):
            na._response(self.encoded(value, nonce=value.ceremony_nonce), mode='inspect', challenge_id='challenge:one',
                nonce=b'\x01'*32, request=value, helper=evidence(), cancelled=False)

    def test_enrollment_response_cannot_bind_foreign_helper_or_challenge(self):
        value = self.value()
        for changed in (replace(value, helper_identity=ProcessResourceIdentity(23,44,HASH)),
                replace(value, ui_identity=ProcessResourceIdentity(23,44,HASH)),
                replace(value, challenge_id='challenge:other')):
            with self.subTest(change=changed.input_commitment), self.assertRaises(ContractError):
                na._response(self.encoded(changed), mode='inspect', challenge_id='challenge:one',
                    nonce=b'\x01'*32, request=changed, helper=evidence(), cancelled=False)

    def test_primary_exposure_uses_real_exception_storage_after_refusing_diagnostics(self):
        owner = type('ControlledOwner', (), {})()
        wire, frozen = na._frame('inspect', 'challenge:one', b'\x01'*32, request(), 5000)
        session = na.NativeApprovalSession(owner, 'inspect', frozen, None, 5000, wire)
        class Primary(KeyboardInterrupt):
            def __setattr__(self, name, value): raise RuntimeError('refused attribute')
            @property
            def add_note(self): raise RuntimeError('refused diagnostic lookup')
        primary = Primary('original')
        session._expose(primary, (OSError('secondary'),))
        storage = BaseException.__dict__['__dict__'].__get__(primary)
        self.assertIs(storage['owned_session'], session)
        self.assertEqual(len(storage['cleanup_errors']),1)
        self.assertIs(storage['close_cleanup'].__self__, session)

    def test_callback_cannot_silently_replace_byte_frozen_request_or_original_context(self):
        baseline = NativeApprovalDataTests()
        tick = ClockSample('boot:fixture', 1, 0, MONO, WALL, 1, True)
        session = baseline._controlled_session(current=lambda *args: None, clock=lambda:(tick,tick))
        session.request = replace(session.request, request_id='effect:changed')
        with self.assertRaisesRegex(ContractError,'FROZEN_REQUEST_OR_CONTEXT_CHANGED'): session._require_current()
        session = baseline._controlled_session(current=lambda *args: None, clock=lambda:(tick,tick))
        session._context = object()
        with self.assertRaisesRegex(ContractError,'FROZEN_REQUEST_OR_CONTEXT_CHANGED'): session._require_current()


class NativeEnrollmentNativeTests(unittest.TestCase):
    helper_path = helper_sha256 = helper_source_commitment = fixture_root = None
    observations = []

    def setUp(self):
        self.h = NativeApprovalNativeTests('test_actual_availability_measures_private_helper_and_system_interop_library')
        self.h.helper_path, self.h.helper_sha256, self.h.fixture_root = self.helper_path, self.helper_sha256, self.fixture_root
        self.h.setUp()
        self.owner = self.h.owner
        self.owner.helper_source_commitment = self.helper_source_commitment
        self.binding = self.registry = self.clock = None

    def tearDown(self):
        try:
            self.h.tearDown()
        finally:
            for item in (self.binding, self.registry, self.clock):
                if item is not None:item.close()
        self.observations.append({'test_id':self.id(),
            'sessions':[{'pid':s.process.pid if s.process else None,'creation_time':s.process.creation_time if s.process else None,
              'closed':s._closed,'empty_job':s.process is None or s.process.lifetime_closed,
              'gate_may_open':s._gate_may_open,'mode':s.mode,'native_facts':s.native_facts} for s in self.h.sessions],
            'all_closed':all(s._closed and not s.pending_native_cleanup for s in self.h.sessions),
            'genuine_authentication_requested':False})

    def prepare(self, owner=None):
        return self.h.started((owner or self.owner).prepare_enrollment, timeout_ms=5000)

    def actual_request(self, session):
        # The enrollment body uses actual owned SQLite objects, current test
        # process/token, native clock and prepared helper/UI lifetime. These
        # native observations do not enroll this controlled principal.
        import os,sys
        import test_owner_enrollment as enrollment
        from ceta.identity.native_clock import NativeSessionClock
        from ceta.identity.native_owner_view import NativeStoreBinding, registration_token_facts
        from ceta.identity.windows_pipe import WindowsPeerRegistry, _creation, _image_name
        from ceta.store.sqlite_runtime import load_sqlite
        self.clock = self.clock or NativeSessionClock(7)
        directory=self.h.fixture/('store-'+uuid.uuid4().hex[:8]);directory.mkdir()
        with closing(load_sqlite().connect(directory/'history.sqlite3')) as store, store:store.execute('CREATE TABLE witness (value)')
        self.binding=NativeStoreBinding(directory)
        self.registry=WindowsPeerRegistry();api=self.registry._api
        native_image=Path(_image_name(api,api.GetCurrentProcess()))
        registration=self.registry.register(os.getpid(),'owner1','interactive1',allowed_operations=('kernel.prepare',),
            allowed_scopes=('project1',),expected_image_sha256=hashlib.sha256(native_image.read_bytes()).hexdigest(),
            expected_creation_time=_creation(api,api.GetCurrentProcess()))
        _,current=self.clock.clock()
        deadline=Deadline(current.boot_id,current.durable_epoch,current.resume_generation,current.monotonic_ns,
            current.monotonic_ns+30_000_000_000,current.earliest_wall_ns,current.latest_wall_ns+30_000_000_000)
        binding=session.enrollment_binding
        return enrollment.request(challenge_id=binding.challenge_id,ceremony_nonce=binding.ceremony_nonce,
            helper_identity=binding.helper.identity,ui_identity=binding.ui_identity,
            helper_commitment=binding.helper_commitment,ui_commitment=binding.ui_commitment,
            private_root=self.binding.private_root,database=self.binding.database,
            owner_facts=registration_token_facts(registration),clock_session_nonce=current.boot_id.rsplit(':',1)[1],deadline=deadline)

    def finish(self, session):
        result=self.h.finish(session)
        self.assertFalse(result.authentication_invoked)
        return result

    def test_actual_preparation_measures_live_helper_and_interop_before_any_body_or_window(self):
        session=self.prepare();binding=session.enrollment_binding
        self.assertEqual(binding.availability,0)
        self.assertEqual(binding.helper.identity,session.process.resource_identity)
        self.assertEqual(binding.ui_identity,binding.helper.identity)
        self.assertEqual(len(binding.ceremony_nonce),32)
        self.assertEqual(len(session._nonce),32)
        self.assertEqual(binding.helper_commitment,binding.ui_commitment)
        self.assertFalse(session._gate_may_open)
        self.assertFalse(session.native_facts['body_bound'])
        self.assertIsNone(session.process.poll())
        with self.assertRaisesRegex(ContractError,'ENROLLMENT_BINDING_REQUIRED'):session.poll()

    def test_actual_hidden_enrollment_displays_every_field_and_measured_prepared_identity(self):
        from ceta.contracts.owner_enrollment import enrollment_display_commitment
        session=self.prepare();value=self.actual_request(session)
        self.assertIs(session.inspect_enrollment(value),session)
        result=self.finish(session)
        self.assertEqual(result.status,'DISPLAY_BOUND_UNSHOWN')
        self.assertTrue(result.display_exact)
        self.assertEqual(result.request_commitment,value.input_commitment)
        self.assertEqual(result.display_commitment,enrollment_display_commitment(value))
        self.assertEqual(result.helper.identity,value.helper_identity)
        self.assertEqual(result.ceremony_nonce,value.ceremony_nonce)
        self.assertFalse(result.reported_verified)

    def test_actual_enrollment_cancel_mode_retains_binding_without_authentication(self):
        session=self.prepare();value=self.actual_request(session)
        session.cancel_enrollment(value);result=self.finish(session)
        self.assertEqual(result.status,'CANCELLED')
        self.assertEqual(result.request_commitment,value.input_commitment)
        self.assertIsNone(result.native_result)

    def test_actual_prepared_process_cannot_accept_another_helper_or_semantic_nonce(self):
        session=self.prepare();value=self.actual_request(session)
        for changes in ({'ceremony_nonce':'1'*32},{'challenge_id':'enrollment:foreign'},
                {'helper_identity':replace(value.helper_identity,pid=value.helper_identity.pid+1)},
                {'ui_commitment':HASH}):
            with self.subTest(fields=list(changes)),self.assertRaises(ContractError):session.inspect_enrollment(replace(value,**changes))
            self.assertFalse(session._gate_may_open)
        self.finish(session.inspect_enrollment(value))

    def test_default_canonical_enrollment_port_denies_before_interactive_gate(self):
        session=self.prepare();value=self.actual_request(session)
        with self.assertRaisesRegex(ContractError,'CANONICAL_INTEGRATION_UNAVAILABLE'):
            session.begin_enrollment(value,original_context=object())
        self.assertFalse(session._gate_may_open)
        self.assertFalse(session.native_facts['body_bound'])

    def test_cpu_and_raw_approved_bodies_cannot_bind_an_enrollment_preparation(self):
        session=self.prepare()
        for value in (request(),{'approved':True},b'{}',True,None):
            with self.subTest(type=type(value).__name__),self.assertRaises(ContractError):session.inspect_enrollment(value)
        self.assertFalse(session._gate_may_open)

    def test_only_one_preparation_is_owned_and_binding_cannot_be_replayed(self):
        session=self.prepare();value=self.actual_request(session)
        with self.assertRaisesRegex(ContractError,'CEREMONY_ALREADY_OWNED'):self.owner.prepare_enrollment(timeout_ms=5000)
        session.inspect_enrollment(value)
        with self.assertRaisesRegex(ContractError,'ALREADY_BOUND_OR_CLOSED'):session.inspect_enrollment(value)
        self.finish(session)

    def test_actual_stop_before_body_binding_keeps_gate_closed_and_owned_lifetime(self):
        session=self.prepare();value=self.actual_request(session)
        session.cancel()
        with self.assertRaisesRegex(ContractError,'CANCELLED_BEFORE_GATE'):session.inspect_enrollment(value)
        self.assertFalse(session._gate_may_open)

    def test_actual_canonical_owner_boolean_is_denied_and_exact_original_context_is_retained(self):
        from ceta.identity.native_clock import NativeSessionClock
        self.clock=NativeSessionClock(7);seen=[];context=object()
        class Lease:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def require_current(self,*args):seen.append(args);return True
        class Owner:
            def retain_native_enrollment(self,wire,original):
                self_request.append((wire,original));return Lease()
        self_request=[]
        owner=na.NativeApprovalOwner(self.helper_path,self.helper_sha256,temporary_root=self.h.fixture,
            canonical_owner=Owner(),clock_owner=self.clock,helper_source_commitment=self.helper_source_commitment)
        session=self.prepare(owner);value=self.actual_request(session)
        with self.assertRaises(na.NativeApprovalError):session.begin_enrollment(value,original_context=context)
        self.assertEqual(len(seen),1)
        self.assertIs(seen[0][-1],context);self.assertIs(self_request[0][1],context)
        self.assertEqual(seen[0][0],value.canonical_wire)
        self.assertEqual(seen[0][1:3],(value.challenge_id,value.ceremony_nonce))
        self.assertEqual(seen[0][3].identity,value.helper_identity)
        self.assertFalse(session._gate_may_open)

    def test_actual_native_enrollment_profile_and_display_digest_corruption_are_rejected(self):
        original=na._frame
        for change in ('profile','display'):
            session=self.prepare();value=self.actual_request(session)
            def corrupt(*args,**kwargs):
                wire,frozen=original(*args,**kwargs)
                if change=='display':wire=wire.replace(na._display_commitment(frozen).encode(),HASH.encode(),1)
                else:wire=wire.replace(b'ceta-owner-enrollment-data-v1',b'ceta-owner-enrollment-data-v9',1)
                return wire,frozen
            with patch.object(na,'_frame',corrupt):session.inspect_enrollment(value)
            with self.assertRaisesRegex(ContractError,'NATIVE_REJECTED'):session.wait(15)
            session.close()
            # Every next body must observe a fresh helper and fresh native store.
            for item in (self.binding,self.registry,self.clock):item.close()
            self.binding=self.registry=self.clock=None

    def test_startup_primary_property_getters_cannot_replace_original_control_exception(self):
        class Primary(KeyboardInterrupt):
            @property
            def control_handles(self):raise RuntimeError('refused control diagnostic')
            @property
            def owned_process(self):raise RuntimeError('refused process diagnostic')
            @property
            def close_cleanup(self):raise RuntimeError('refused cleanup diagnostic')
        primary=Primary('original startup control')
        with patch.object(na.NativeApprovalSession,'_launch',side_effect=primary):
            with self.assertRaises(Primary) as caught:self.h.started(self.owner.availability)
        self.assertIs(caught.exception,primary)
        storage=BaseException.__dict__['__dict__'].__get__(primary)
        self.assertTrue(storage['owned_session']._closed)
        self.assertIsNone(storage['owned_process'])
        self.assertIsNone(self.owner._active)

    def test_actual_handle_observation_diagnostic_preserves_primary_pending_custody_and_recovery(self):
        class Primary(SystemExit):
            def __setattr__(self,name,value):
                if name=='cleanup_observation_error':raise RuntimeError('refused diagnostic setter')
                super().__setattr__(name,value)
        session=self.h.started(self.owner.availability)
        result=session.wait(15);self.assertIsNotNone(result)
        self.assertFalse(result.authentication_invoked)
        witness=session._api.CreateEventW(None,True,False,None)
        self.assertTrue(witness);session._handles['witness']=witness
        primary=Primary('original handle close');secondary=OSError('secondary observation')
        compare=session._api.CompareObjectHandles;close=session._api.close;calls=[]
        def observed(a,b):
            if a==witness:
                calls.append((a,b))
                if len(calls)==2:raise secondary
            return compare(a,b)
        def closing(handle):
            if handle==witness:raise primary
            return close(handle)
        with patch.object(session._api,'CompareObjectHandles',side_effect=observed),patch.object(session._api,'close',side_effect=closing):
            with self.assertRaises(Primary) as caught:session.close()
        self.assertIs(caught.exception,primary)
        storage=BaseException.__dict__['__dict__'].__get__(primary)
        self.assertIs(storage['cleanup_observation_error'],secondary)
        self.assertIs(storage['owned_session'],session)
        self.assertTrue(session.pending_native_cleanup)
        self.assertTrue(handle_state(witness)[0])
        storage['close_cleanup']()
        self.assertTrue(session._closed);self.assertFalse(session.pending_native_cleanup)
        self.assertEqual(handle_state(witness)[:2],(False,6))

    def test_two_native_enrollment_bindings_compete_for_one_irreversible_gate(self):
        session=self.prepare();value=self.actual_request(session)
        entered,release,attempted=threading.Event(),threading.Event(),threading.Event()
        original=session._measure_helper;results=[];errors=[]
        def held():
            entered.set();self.assertTrue(release.wait(5));return original()
        def bind(second=False):
            if second:attempted.set()
            try:results.append(session.inspect_enrollment(value))
            except BaseException as error:errors.append(error)
        with patch.object(session,'_measure_helper',side_effect=held):
            first=threading.Thread(target=bind);second=threading.Thread(target=bind,args=(True,))
            first.start()
            try:
                self.assertTrue(entered.wait(5));second.start();self.assertTrue(attempted.wait(5))
            finally:
                release.set();first.join(10)
                if second.ident is not None:second.join(10)
        self.assertFalse(first.is_alive());self.assertFalse(second.is_alive())
        self.assertEqual(results,[session]);self.assertEqual(len(errors),1)
        self.assertIsInstance(errors[0],ContractError)
        self.assertIn('ALREADY_BOUND_OR_CLOSED',str(errors[0]))
        self.assertEqual(self.finish(session).status,'DISPLAY_BOUND_UNSHOWN')

    def test_stop_during_actual_helper_remeasurement_denies_final_gate(self):
        session=self.prepare();value=self.actual_request(session);original=session._measure_helper
        def stopped():
            original();self.owner.cancel_current()
        with patch.object(session,'_measure_helper',side_effect=stopped):
            with self.assertRaises(na.NativeApprovalError) as caught:session.inspect_enrollment(value)
        self.assertIn('CANCELLED_BEFORE_GATE',str(caught.exception.__cause__))
        self.assertTrue(session._stop.is_set());self.assertFalse(session._gate_may_open)
        self.assertTrue(session._closed);self.assertTrue(session.process.lifetime_closed)

    def test_primary_during_actual_helper_remeasurement_retains_owned_cleanup(self):
        session=self.prepare();value=self.actual_request(session);original=session._measure_helper
        primary=KeyboardInterrupt('after actual prepared-helper remeasurement')
        def interrupted():
            original();raise primary
        with patch.object(session,'_measure_helper',side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt) as caught:session.inspect_enrollment(value)
        self.assertIs(caught.exception,primary)
        storage=BaseException.__dict__['__dict__'].__get__(primary)
        self.assertIs(storage['owned_session'],session)
        self.assertIs(storage['owned_process'],session.process)
        self.assertTrue(session._closed);self.assertTrue(session.process.lifetime_closed)
        self.assertFalse(session._gate_may_open)

    def test_actual_preparation_response_corruption_never_opens_gate_or_loses_custody(self):
        original=na.NativeApprovalSession._read
        for change in ('authentication','foreign-pid','bool-availability','rollback','extra-field','trailing'):
            changed=[]
            def corrupt(session):
                original(session)
                raw=session._response_bytes
                if changed or len(raw)<12:return
                size=struct.unpack('<I',raw[8:12])[0]
                if len(raw)!=size+12:return
                fields=strict_loads(raw[12:])
                if fields.get('phase')!='PREPARED':return
                changed.append(True)
                if change=='authentication':fields['authentication_invoked']=True
                elif change=='foreign-pid':fields['provenance']['pid']+=1
                elif change=='bool-availability':fields['availability']=False
                elif change=='rollback':fields['finished_qpc']=fields['started_qpc']-1
                elif change=='extra-field':fields['approved']=True
                payload=canonical_bytes(fields)
                session._response_bytes=na._RESPONSE_MAGIC+struct.pack('<I',len(payload))+payload
                if change=='trailing':session._response_bytes+=b'!'
            with self.subTest(change=change),patch.object(na.NativeApprovalSession,'_read',corrupt):
                with self.assertRaises(na.NativeApprovalError) as caught:self.prepare()
                session=caught.exception.owned_session
                self.assertEqual(changed,[True])
                self.assertFalse(session._gate_may_open)
                self.assertTrue(session._closed);self.assertTrue(session.process.lifetime_closed)

    def test_mutating_original_enrollment_dto_cannot_change_bound_native_body(self):
        from ceta.contracts.owner_enrollment import enrollment_display_commitment
        session=self.prepare();value=self.actual_request(session)
        expected,display=value.input_commitment,enrollment_display_commitment(value)
        session.inspect_enrollment(value)
        object.__setattr__(value,'challenge_id','enrollment:mutated-after-binding')
        result=self.finish(session)
        self.assertNotEqual(value.challenge_id,session.request.challenge_id)
        self.assertEqual(result.request_commitment,expected)
        self.assertEqual(result.display_commitment,display)
        self.assertFalse(result.reported_verified)
