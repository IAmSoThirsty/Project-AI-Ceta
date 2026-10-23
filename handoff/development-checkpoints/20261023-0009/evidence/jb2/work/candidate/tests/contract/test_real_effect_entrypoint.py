"""Pure command/lifecycle controls; no native, consent or effect acceptance.

Positive objects below are explicitly controlled instances of the original
classes. Every native constructor, loader and process entry is forbidden unless
the individual test replaces that exact constructor with a recording control.
"""
import argparse
from contextlib import contextmanager
from dataclasses import replace
import io
from pathlib import Path
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ceta.composition import real_effect_cli as cli
from ceta.composition.real_effect_service import ManualEffectLimits, ManualRealEffectSession
from ceta.composition.real_effect_runtime import ManualRealEffectProfile, ManualRuntimeSelection
from ceta.composition.native_cpu_runtime import NativeCpuRuntime
from ceta.contracts.real_effect import CAP_OPERATION
from ceta.contracts.resource_management import ResourceVector
from ceta.contracts.kernel_transactions import BudgetVector
from ceta.contracts.wire import ContractError, strict_loads
from ceta.identity.native_code_binding import CodePin
from ceta.store.outcome_capacity import OutcomeCapacityBudget

H = 'sha256:' + 'a' * 64


def budget(effects, written, wall):
    return BudgetVector.from_dict(dict(max_effects=effects, max_model_calls=0,
        max_input_tokens=0, max_output_tokens=0, max_bytes_read=32768,
        max_bytes_written=written, wall_time_ms=wall))


def limits():
    return ManualEffectLimits(budget(2, 131072, 2000), budget(1, 65536, 1000),
        ResourceVector(100, 16 * 1024 * 1024, 1048576, 2000), 65536, 32768)


def selection():
    fixture = Path(__file__).resolve().parents[2] / '.agents/fixtures/manual-entrypoint-pure'
    names = ('helper', 'helper-source', 'worker', 'observer', 'observer-source', 'capacity')
    groups = ('environment', 'source', 'environment', 'environment', 'source', 'environment')
    pins = tuple(CodePin(g, n, str(fixture / n), 'a' * 64)
        for g, n in zip(groups, names))
    return ManualRuntimeSelection(fixture / 'root',
        fixture / 'scratch', 'installation:manual', 'scope:manual', 7,
        pins, H, H, *names, 'CETA.ControlledPure',
        OutcomeCapacityBudget(1048576, 1048576, 65536), limits())


class _Context:
    def __init__(self):
        self.entered = self.exited = 0
        self.exit_error = None
    def __enter__(self):
        self.entered += 1
        return self
    def __exit__(self, kind, primary, trace):
        self.exited += 1
        if self.exit_error is not None:
            raise self.exit_error
        return False


class _Lease:
    def __init__(self):
        self.entries = self.exits = self.recoveries = 0
        self.closed = False
        self.pending = False
        self.dispatch_admitted = False
        self.denied = None
    def __enter__(self):
        self.entries += 1
        return self
    def __exit__(self, kind, primary, trace):
        self.exits += 1
        self.closed = not self.pending
    def inspection(self):
        return dict(closed=self.closed, pending_cleanup=self.pending,
            dispatch_admitted=self.dispatch_admitted, stopped=False,
            native_effect='UNESTABLISHED_BY_ADMISSION', denied_dispatch=self.denied)
    @contextmanager
    def recover_outcome(self, context):
        self.recoveries += 1
        yield self
    def record_denied_outcome(self):
        return SimpleNamespace(as_dict=lambda: {'state': 'UNCERTAIN'})


class _Fixture:
    """CONTROLLED original-class identities and recording infrastructure ports."""
    def __init__(self):
        import test_owner_authority_transactions as data
        self.calls = []
        self.tick = data.clock(1_200_000_000)
        self.context = object()
        self.guard = _Context()
        self.kernel = SimpleNamespace()
        self.profile = object.__new__(ManualRealEffectProfile)
        self.runtime = object.__new__(NativeCpuRuntime)
        self.profile.runtime = self.runtime
        self.profile._state = 'ACTIVE'
        self.profile._thread = threading.get_ident()
        self.profile._session = None
        self.profile.limits = limits()
        self.profile.adapter_commitment = H
        self.runtime._store = object()
        self.runtime._codec = object()
        self.runtime._installation = 'installation:manual'
        self.runtime._registry = SimpleNamespace(authenticate=self.authenticate,
            remaining_time=lambda context: (30_000_000_000,self.tick.latest_wall_ns+30_000_000_000))
        self.profile.registry = self.runtime._registry
        self.runtime._owner = SimpleNamespace(native_context=lambda c: self.guard,
            request_stop=lambda: self.calls.append('stop'),clock=lambda:(self.tick,self.tick))
        self.runtime.kernel = SimpleNamespace(_kernel=self.kernel)
        self.runtime._selected = lambda *a, **kw: self.calls.append(('select', kw['bookkeeping']))
        self.runtime.execute = self.execute
        self.runtime.reconcile = self.reconcile
        self.session = self.profile.command_session(self.context)
        self.session.__enter__()
        self.lease = _Lease()
        self.proof = object()
        self.request = SimpleNamespace(request_id='request:controlled', canonical_wire=b'request',
            operation=CAP_OPERATION, deadline=self.session._budget_deadline,
            as_dict=lambda: {'request_id': 'request:controlled'})
        self.kernel.owned_cpu_execution = self.admission
        self.session._request = self.request
        self.session._permit = b'prepared'
        self.session._proof = self.proof
        self.session._binding, self.session._capture = object(), object()
        self.session._approval_stage = 'PREPARED'
        self.session.inspect = self.inspect
    def authenticate(self, context):
        if context is not self.context:
            raise ContractError('CONTROLLED_FOREIGN_CONTEXT')
        self.calls.append('authenticate')
        return object()
    def admission(self, wire, permit, binding, capture, proof, context):
        assert (wire, permit, proof, context) == (b'request', b'prepared', self.proof, self.context)
        assert binding is self.session._binding and capture is self.session._capture
        self.calls.append('admission')
        return self.lease
    def execute(self, lease):
        assert lease is self.lease
        self.calls.append('execute')
        lease.dispatch_admitted = True
        return SimpleNamespace(as_dict=lambda: {'state': 'SETTLED_OBSERVED'})
    def reconcile(self, lease):
        assert lease is self.lease
        self.calls.append('reconcile')
        return SimpleNamespace(as_dict=lambda: {'state': 'UNCERTAIN'})
    def inspect(self):
        return dict(run_id=self.session.run_id, state=self.session._state)


class ManualEntrypointPureTests(unittest.TestCase):
    def setUp(self):
        self.barriers = []
        def forbidden(*args, **kwargs):
            self.fail('Native/process/profile/test effects are forbidden in this pure cohort')
        for name in ('ctypes.WinDLL', 'ctypes.CDLL', 'subprocess.Popen', 'subprocess.run',
                     'socket.socket'):
            value = patch(name, side_effect=forbidden)
            value.start()
            self.barriers.append(value)
        self.addCleanup(lambda: [value.stop() for value in reversed(self.barriers)])

    def test_selection_is_typed_and_no_cli_configuration_or_proof_flag_exists(self):
        value = selection()
        self.assertIs(type(value), ManualRuntimeSelection)
        for changes in ({'durable_epoch': True}, {'create': 1}, {'work_duration_ms': 30001},
                        {'code_pins': list(value.code_pins)}, {'private_root': Path('relative')},
                        {'appcontainer_name': 'unrestricted'}, {'capacity_budget': object()}):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                replace(value, **changes)
        for extra in ('--proof=x', '--config=x', '--yes', '--factory=x', '--private-root=x'):
            with self.subTest(extra=extra), patch('sys.stderr', new=io.StringIO()), self.assertRaises(SystemExit):
                cli.parser().parse_args(['start', '--profile', 'ceta-owned-real-effect-v1', extra])

    def test_invalid_limits_deny_before_native_construction(self):
        value = limits()
        for changes in ({'authority_budget': budget(1, 131072, 2000)},
                        {'required_outcome_bytes': 65537}, {'maximum_session_ns': 300000000001},
                        {'resource_limit': ResourceVector(0, 1, 8192, 2000)}):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                replace(value, **changes)

    def test_standalone_command_denies_without_constructing_native_owners(self):
        for command in (['start', '--profile', 'ceta-owned-real-effect-v1'],
                        ['enroll', '--run-id', 'run:invented'],
                        ['execute', '--run-id', 'run:invented', '--request-id', 'request:invented']):
            with self.subTest(command=command):
                output = io.BytesIO()
                self.assertEqual(cli.main(command, output=output), 2)
                value = strict_loads(output.getvalue().rstrip(b'\n'))
                self.assertEqual(value['code'], 'MANUAL_PROFILE_SELECTED_AUTHENTICATED_HOST_UNAVAILABLE')
                self.assertEqual(value['transition_or_effect'], 'UNESTABLISHED_BY_RESPONSE')

    def test_run_id_never_substitutes_for_live_original_context(self):
        f = _Fixture()
        args = cli.parser().parse_args(['execute', '--run-id', 'run:foreign', '--request-id', f.request.request_id])
        with self.assertRaisesRegex(ContractError, 'RUN_ID_MISMATCH'):
            cli.dispatch(args, f.session)
        self.assertNotIn('admission', f.calls)
        f.session._context = object()
        with self.assertRaisesRegex(ContractError, 'CONTROLLED_FOREIGN_CONTEXT'):
            f.session.execute(f.request.request_id)
        self.assertNotIn('admission', f.calls)

    def test_original_thread_required_before_any_admission(self):
        f = _Fixture()
        f.session._thread += 1  # No thread or process is created by this control.
        with self.assertRaisesRegex(ContractError, 'ORIGINAL_THREAD_REQUIRED'):
            f.session.execute(f.request.request_id)
        self.assertNotIn('admission', f.calls)

    def test_single_execution_uses_exact_retained_original_kernel_lease(self):
        f = _Fixture()
        result = f.session.execute(f.request.request_id)
        self.assertEqual(result['run_id'], f.session.run_id)
        self.assertEqual((f.lease.entries, f.lease.exits), (1, 1))
        self.assertEqual([x for x in f.calls if x in ('admission', 'execute')], ['admission', 'execute'])
        with self.assertRaisesRegex(ContractError, 'SINGLE_EXECUTION_REQUIRED'):
            f.session.execute(f.request.request_id)
        self.assertEqual(f.calls.count('execute'), 1)

    def test_interrupted_admission_is_not_replayed_and_retains_exact_primary(self):
        f = _Fixture()
        primary = KeyboardInterrupt('controlled-before-return')
        def failed(*args):
            raise primary
        f.kernel.owned_cpu_execution = failed
        with self.assertRaises(KeyboardInterrupt) as caught:
            f.session.execute(f.request.request_id)
        self.assertIs(caught.exception, primary)
        self.assertIs(primary.manual_real_effect_session, f.session)
        self.assertTrue(f.session._execution_attempted)
        with self.assertRaises(ContractError):
            f.session.execute(f.request.request_id)
        self.assertNotIn('execute', f.calls)

    def test_reconciliation_uses_original_recovery_borrow_and_never_execute(self):
        f = _Fixture()
        f.session._execution = f.lease
        f.session.reconcile(f.request.request_id)
        self.assertEqual(f.lease.recoveries, 1)
        self.assertEqual(f.calls.count('reconcile'), 1)
        self.assertNotIn('execute', f.calls)
        f.lease.denied = object()
        f.session.reconcile(f.request.request_id)
        self.assertEqual(f.lease.recoveries, 2)
        self.assertEqual(f.calls.count('reconcile'), 1)

    def test_pending_execution_preserves_context_guard_and_primary(self):
        f = _Fixture()
        f.session._execution = f.lease
        f.lease.pending = True
        primary = SystemExit('controlled-primary')
        self.assertIs(f.session.__exit__(type(primary), primary, None), False)
        self.assertIs(primary.manual_real_effect_session, f.session)
        self.assertEqual(f.guard.exited, 0)
        self.assertEqual(f.session._state, 'PENDING')
        self.assertIs(f.profile._session, f.session)

    def test_context_cleanup_failure_is_retained_once_without_primary_replacement(self):
        f = _Fixture()
        f.session._binding = None
        cleanup = KeyboardInterrupt('controlled-context-close')
        f.guard.exit_error = cleanup
        primary = SystemExit('controlled-body')
        self.assertFalse(f.session.__exit__(type(primary), primary, None))
        self.assertIs(primary.manual_real_effect_cleanup_errors[0], cleanup)
        self.assertEqual(f.guard.exited, 1)
        with self.assertRaisesRegex(ContractError, 'RETIREMENT_UNCERTAIN'):
            f.session.close()
        self.assertEqual(f.guard.exited, 1)

    def test_approval_uses_owner_ceremony_witness_and_canonical_prepare_record_wire(self):
        f = _Fixture()
        transcript = SimpleNamespace(canonical_wire=b'transcript')
        ceremony = SimpleNamespace(wait=lambda seconds: object())
        approval = SimpleNamespace(begin_interactive=lambda request, **kwargs: ceremony)
        def verified(session, context):
            self.assertIs(session, ceremony)
            self.assertIs(context, f.context)
            f.calls.append('genuine-origin-predicate-controlled')
            return transcript, f.proof
        f.runtime._owner.approval_owner = approval
        f.runtime._owner.retain_verified_effect = verified
        f.session._enrollment = SimpleNamespace(request_id='enrollment:controlled',deadline=f.session._budget_deadline)
        f.session._proposal = SimpleNamespace(original_wire=b'proposal')
        f.session._approval_stage = 'NEW'
        def approve(enrollment, wire, transcript_wire, proof, context):
            self.assertEqual((enrollment, wire, transcript_wire),
                ('enrollment:controlled', b'request', b'transcript'))
            self.assertIs(proof, f.proof)
            self.assertIs(context, f.context)
            f.calls.append('canonical-approve')
            return object()
        f.kernel.approve_owned_cpu = approve
        f.runtime.kernel.prepare = lambda wire, context: SimpleNamespace(record_wire=b'exact-prepared')
        f.session.approve(f.request.request_id)
        self.assertEqual(f.session._permit, b'exact-prepared')
        self.assertEqual(f.session._approval_stage, 'PREPARED')
        self.assertIn('canonical-approve', f.calls)
        self.assertNotIn('execute', f.calls)

    def test_approval_origin_rejection_never_calls_canonical_approve(self):
        f = _Fixture()
        f.session._approval_stage = 'NEW'
        f.runtime._owner.approval_owner = SimpleNamespace(begin_interactive=lambda *a, **k:
            SimpleNamespace(wait=lambda seconds: object()))
        failure = ContractError('CONTROLLED_GENUINE_ORIGIN_DENIED')
        def denied(*args):
            raise failure
        f.runtime._owner.retain_verified_effect = denied
        f.kernel.approve_owned_cpu = lambda *a: self.fail('No canonical approval after origin denial')
        with self.assertRaises(ContractError) as caught:
            f.session.approve(f.request.request_id)
        self.assertIs(caught.exception, failure)
        self.assertIs(failure.manual_real_effect_session, f.session)
        self.assertNotIn('execute', f.calls)

    def test_concrete_factory_wires_one_clock_journal_registry_and_runtime(self):
        from ceta.composition import real_effect_runtime as module
        from ceta.contracts.wire import RecordCodec
        calls = []
        def controlled(name):
            def initialize(owner, *args, **kwargs):
                calls.append((name, owner, args, kwargs))
                if name == 'observer':
                    owner._clock = kwargs['clock']
            return initialize
        kinds = [('code', module.NativeCodeBinding), ('clock', module.NativeSessionClock),
                 ('capacity', module.OutcomeCapacityRuntime), ('observer', module.NativeCpuEffectObserver),
                 ('registry', module.WindowsPeerRegistry), ('store', module.SqliteJournal),
                 ('runtime', module.NativeCpuRuntime)]
        patches = [patch.object(kind, '__init__', controlled(name)) for name,kind in kinds]
        for item in patches:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in reversed(patches)])
        codec = object.__new__(RecordCodec)
        profile = ManualRealEffectProfile(selection(), codec)
        self.assertEqual([row[0] for row in calls], [row[0] for row in kinds])
        store = next(row for row in calls if row[0] == 'store')
        self.assertIs(store[3]['outcome_runtime'], profile.capacity)
        self.assertEqual(store[3]['profile'], 'ceta-sqlite-store-v2')
        runtime = calls[-1]
        self.assertIs(runtime[2][0], profile.store)
        self.assertIs(runtime[2][1], codec)
        self.assertIs(runtime[2][3], profile.registry)
        configuration = runtime[2][4]
        self.assertIs(configuration.clock, profile.clock)
        self.assertIs(configuration.code_binding, profile.code)
        self.assertIs(configuration.observer, profile.observer)
        self.assertIs(configuration.outcome_runtime, profile.capacity)
        self.assertIsNone(profile.worker)

    def test_restricted_launch_error_is_retained_without_unrestricted_retry(self):
        from ceta.composition import real_effect_runtime as module
        f = _Fixture()
        p = f.profile
        p.selection = selection()
        p._worker_launch_attempted = False
        p._worker_launch_error = None
        p.worker = p._binding = None
        primary = KeyboardInterrupt('controlled-restrictive-create')
        retained = object()
        primary.owned_process = retained
        with patch.object(module.IsolatedWindowsWorker, 'launch', side_effect=primary) as launch:
            with self.assertRaises(KeyboardInterrupt) as caught:
                p.cpu_binding()
            self.assertIs(caught.exception, primary)
            self.assertIs(p.worker, retained)
            self.assertIs(primary.manual_real_effect_profile, p)
            with self.assertRaisesRegex(ContractError, 'RESTRICTED_WORKER_UNAVAILABLE'):
                p.cpu_binding()
            self.assertEqual(launch.call_count, 1)
            self.assertEqual(launch.call_args.kwargs['appcontainer_name'], 'CETA.ControlledPure')
            self.assertEqual(launch.call_args.args[1], ('cpu', '30000'))

    def test_real_enrollment_request_builder_uses_measured_data_and_fresh_nonce(self):
        import test_owner_authority_transactions as data
        source = data.enrollment_request()
        f = _Fixture()
        f.runtime._installation = source.installation_id
        f.runtime._configuration = SimpleNamespace(scope_id=source.scope_id,
            policy_commitment=H, code_binding=SimpleNamespace(source_commitment=H, environment_commitment=H))
        observed = SimpleNamespace(peer=SimpleNamespace(principal_id=source.principal_id,
            session_id=source.actor_session), private_root=source.private_root,
            database=source.database, owner_facts=source.owner_facts)
        f.runtime._view = SimpleNamespace(observe=lambda context: observed)
        f.runtime._owner._worker_commitment = source.worker_image_commitment
        f.runtime._owner.clock = lambda: (data.clock(1100000000), data.clock(1200000000))
        native = SimpleNamespace(challenge_id=source.challenge_id, ceremony_nonce=source.ceremony_nonce,
            helper=SimpleNamespace(identity=source.helper_identity), ui_identity=source.helper_identity,
            helper_commitment=H, ui_commitment=H)
        prepared = SimpleNamespace(enrollment_binding=native)
        first = f.session._new_enrollment(prepared)
        second = f.session._new_enrollment(prepared)
        self.assertEqual(first.owner_facts, source.owner_facts)
        self.assertEqual(first.private_root, source.private_root)
        self.assertEqual(first.database, source.database)
        self.assertEqual(first.helper_identity, source.helper_identity)
        self.assertEqual(first.clock_session_nonce, '1' * 32)
        self.assertNotEqual(first.owner_session_nonce, second.owner_session_nonce)
        self.assertNotEqual(first.request_id, second.request_id)
        self.assertEqual(first.deadline.durable_epoch, 7)
        self.assertEqual(first.deadline.issued_monotonic_ns, 1200000000)
        self.assertIs(first.deadline,f.session._budget_deadline)
        self.assertLess(first.deadline.expires_monotonic_ns,30200000000)

    def test_failed_canonical_approval_is_not_replayed(self):
        f = _Fixture()
        f.session._approval_stage = 'NEW'
        f.session._enrollment = SimpleNamespace(request_id='enrollment:controlled',deadline=f.session._budget_deadline)
        ceremony = SimpleNamespace(wait=lambda seconds: object())
        f.runtime._owner.approval_owner = SimpleNamespace(begin_interactive=lambda *a, **k: ceremony)
        f.runtime._owner.retain_verified_effect = lambda *a: (SimpleNamespace(canonical_wire=b't'), f.proof)
        primary = KeyboardInterrupt('controlled-post-commit-return')
        def failed(*args):
            raise primary
        f.kernel.approve_owned_cpu = failed
        with self.assertRaises(KeyboardInterrupt) as caught:
            f.session.approve(f.request.request_id)
        self.assertIs(caught.exception, primary)
        self.assertEqual(f.session._approval_stage, 'APPROVAL_COMMIT_ATTEMPTED')
        with self.assertRaisesRegex(ContractError, 'APPROVAL_RECOVERY_REQUIRED'):
            f.session.approve(f.request.request_id)
        self.assertNotIn('execute', f.calls)

    def test_manual_wire_and_correlated_result_are_additive_strict_data(self):
        from ceta.contracts.manual_effect import command_wire
        from ceta.contracts.local_ipc import encode_message, decode_message
        from ceta.contracts.local_results import encode_response, decode_response
        from ceta.contracts.wire import RecordCodec, canonical_bytes
        from test_owner_authority_transactions import ROOT as root
        codec = RecordCodec(strict_loads((root / 'contracts/schemas/records.schema.json').read_bytes()))
        body = command_wire('command:pure', 'scope:pure', 'run:pure', 'RUN', cpu_rate=100)
        wire = encode_message(body, codec, message_id='message:pure', sender_session='session:pure',
            receiver_generation='generation:pure', operation='manual.run',
            issued_at_ms=1000, expires_at_ms=31000)
        request = decode_message(wire, codec)
        self.assertEqual(request.record.as_dict()['cpu_rate'], 100)
        response = encode_response(request, {'state': 'SETTLED_OBSERVED', 'run_id': 'run:pure'}, codec)
        decoded = decode_response(response, request, codec)
        self.assertEqual(decoded.kind, 'MANUAL_STATE')
        self.assertEqual(decoded.manual_result_wire, response)
        for change in ({'proof': True}, {'native_configuration': {}}, {'cpu_rate': True}):
            value = dict(strict_loads(body), **change)
            with self.subTest(change=change), self.assertRaises(ContractError):
                from ceta.contracts.manual_effect import decode_command
                decode_command(canonical_bytes(value))
        changed = strict_loads(wire)
        changed['operation'] = 'manual.restore'
        with self.assertRaisesRegex(ContractError, 'MANUAL_ROUTE_BINDING'):
            decode_message(canonical_bytes(changed), codec)
        changed = strict_loads(response)
        changed['request_sha256'] = '0' * 64
        with self.assertRaises(ContractError):
            decode_response(canonical_bytes(changed), request, codec)

    def test_receiver_retains_original_context_pipe_until_exact_owner_retires(self):
        from ceta.identity.windows_pipe import WindowsPipeServer
        receiver = object.__new__(WindowsPipeServer)
        calls, context, owner = [], object(), object()
        receiver._lock = threading.Lock()
        receiver._closed, receiver._pipe = False, 405  # Pure numeric marker only.
        receiver._retained_context = None
        receiver._registry = SimpleNamespace(_invalidate=lambda value: calls.append(('invalidate', value)))
        receiver._api = SimpleNamespace(DisconnectNamedPipe=lambda value: calls.append(('disconnect', value)) or True,
            close_handle=lambda value: calls.append(('close', value)))
        receiver._context_retainer = lambda value: owner
        receiver._retire_dispatch_context(context, True, None)
        self.assertEqual(receiver._retained_context, (context, owner))
        self.assertEqual(calls, [])
        with self.assertRaisesRegex(ContractError, 'CONTEXT_RETAINED'):
            receiver.close()
        self.assertEqual(calls, [])
        receiver._context_retainer = lambda value: None
        receiver.retire_retained_context()
        self.assertIsNone(receiver._retained_context)
        self.assertEqual(calls, [('invalidate', context), ('disconnect', 405)])

    def test_retainer_failure_keeps_primary_and_original_context(self):
        from ceta.identity.windows_pipe import WindowsPipeServer
        receiver = object.__new__(WindowsPipeServer)
        context = object()
        cleanup, primary = KeyboardInterrupt('controlled-retirement'), SystemExit('controlled-body')
        def failed(context):
            raise cleanup
        receiver._context_retainer = failed
        receiver._retained_context = None
        receiver._registry = SimpleNamespace(_invalidate=lambda value: self.fail('Context must remain retained'))
        receiver._retire_dispatch_context(context, True, primary)
        self.assertIs(primary.retained_ingress, receiver)
        self.assertIs(primary.ingress_retirement_error, cleanup)
        self.assertIs(receiver._retained_context[0], context)

    def test_actual_selected_host_routes_whole_run_on_one_original_context(self):
        from ceta.composition.real_effect_host import ManualRealEffectHost
        from ceta.contracts.local_ipc import LocalMessage
        f = _Fixture()
        f.session._binding = None
        f.session.close()
        f.profile.selection = selection()
        f.runtime._owner.native_context = lambda context: _Context()
        f.profile.registry.require_message = lambda context, message: self.assertIs(context, f.context)
        host = object.__new__(ManualRealEffectHost)
        host._thread, host.run_id = threading.get_ident(), 'run:host'
        host.profile = f.profile
        host._pending = host._last_session = host._cap_session = None
        host._stopped = False
        calls = []
        request = SimpleNamespace(request_id='request:host', canonical_wire=b'owned-request',
            task_id='task:host', operation=CAP_OPERATION)
        def enroll(session):
            calls.append(('enroll', session._context))
        def prepare(session, **kwargs):
            calls.append(('prepare', session._context, kwargs))
            session._request = request
        def approve(session, request_id):
            calls.append(('approve', session._context, request_id))
        def execute(session, request_id):
            calls.append(('execute', session._context, request_id))
            session._cap_request = request
            return {'state': 'SETTLED_OBSERVED'}
        body = SimpleNamespace(as_dict=lambda: dict(kind='RUN', run_id='run:host', cpu_rate=100,
            request_id=None, reason_ref=None))
        message = LocalMessage('message:host', 'session:host', 'generation:host', 'manual.run',
            'scope:manual', 1000, 31000, body, None, b'controlled')
        with patch.object(ManualRealEffectSession, 'enroll', enroll), \
             patch.object(ManualRealEffectSession, 'prepare', prepare), \
             patch.object(ManualRealEffectSession, 'approve', approve), \
             patch.object(ManualRealEffectSession, 'execute', execute):
            result = host(message, f.context)
        self.assertEqual([row[0] for row in calls], ['enroll', 'prepare', 'approve', 'execute'])
        self.assertTrue(all(row[1] is f.context for row in calls))
        self.assertEqual(result['run_id'], 'run:host')
        self.assertTrue(host._last_session.closed)
        self.assertIs(host._cap_session._cap_request, request)
        with self.assertRaisesRegex(ContractError, 'CAP_SINGLE_ATTEMPT'):
            host(message, f.context)

    def test_failed_pre_api_constructor_can_retire_without_replaying_initialization(self):
        from ceta.composition import real_effect_runtime as module
        from ceta.contracts.wire import RecordCodec
        primary = KeyboardInterrupt('controlled-code-api-binding')
        calls = []
        def before_api(owner, pins):
            calls.append('constructor')
            owner._lock = threading.RLock()
            owner._closing, owner._closed = threading.Event(), False
            raise primary
        with patch.object(module.NativeCodeBinding, '__init__', before_api):
            with self.assertRaises(KeyboardInterrupt) as caught:
                ManualRealEffectProfile(selection(), object.__new__(RecordCodec))
        self.assertIs(caught.exception, primary)
        profile = primary.manual_real_effect_profile
        self.assertIsNotNone(profile.code)
        with self.assertRaisesRegex(ContractError, 'PARTIAL_CONSTRUCTOR_CUSTODY_PENDING'):
            profile.close()
        profile.retire_failed_constructor()
        self.assertIsNone(profile.code)
        profile.close()
        self.assertTrue(profile.closed)
        self.assertEqual(calls, ['constructor'])

    def test_remote_denial_is_exit_two_and_client_never_retries_uncertain_effect(self):
        from ceta.composition import real_effect_client as module
        from ceta.contracts.wire import RecordCodec
        from ceta.identity.windows_pipe import WindowsServerBinding
        from test_owner_authority_transactions import ROOT as root
        codec = RecordCodec(strict_loads((root / 'contracts/schemas/records.schema.json').read_bytes()))
        client = module.ManualEffectClient(codec, object.__new__(WindowsServerBinding),
            r'\\.\pipe\CETA-controlled', run_id='run:client', scope_id='scope:client',
            actor_session='session:client', receiver_generation='generation:client')
        primary = KeyboardInterrupt('controlled-lost-response')
        with patch.object(module, 'send_pipe_request', side_effect=primary) as send:
            with self.assertRaises(KeyboardInterrupt) as caught:
                client.call('RUN', cpu_rate=100)
            self.assertIs(caught.exception, primary)
            self.assertIs(primary.manual_effect_client, client)
            with self.assertRaisesRegex(ContractError, 'EFFECT_RECONCILIATION_REQUIRED'):
                client.call('RUN', cpu_rate=100)
            self.assertEqual(send.call_count, 1)
        output = io.BytesIO()
        with patch.object(client, 'call', return_value=dict(kind='DENIED_RECONCILE',
                state=None, error_code='CONTROLLED_DENIAL')):
            self.assertEqual(cli.main(['run', '--run-id', 'run:client', '--cpu-rate', '100'],
                client=client, output=output), 2)

    def test_positive_admission_requires_the_original_retained_kernel_execution(self):
        from ceta.identity.owner_session import NativeCpuOwnerSession
        from ceta.identity.owners import WindowsIdentityOwners
        self.assertIsNot(NativeCpuOwnerSession.require_admission, WindowsIdentityOwners.require_admission)
        owner = object.__new__(NativeCpuOwnerSession)
        with self.assertRaisesRegex(ContractError, 'OWNER_ADMISSION_RETAINED_EXECUTION_REQUIRED'):
            owner.require_admission(None, b'controlled-data-only', None)

    def test_canonical_service_entrypoint_selects_manual_host_before_any_ordinary_journal(self):
        from ceta.composition import service_process as service
        from ceta.composition import real_effect_host as host_module
        from ceta.contracts.wire import RecordCodec
        chosen, calls = selection(), []
        config = dict(root=str(chosen.private_root), installation=chosen.installation_scope_id,
            scopes=[chosen.installation_scope_id, chosen.scope_id], create=chosen.create,
            pipe=r'\\.\pipe\CETA-pure-service', client_pid=101, client_creation=102,
            client_image='a' * 64, principal='principal:pure', session='session:pure')
        class ControlledHost:
            def __init__(self, selected, codec, pipe, **peer):
                calls.append(('construct', selected, peer))
                self._stopped = False
            def ready(self):
                return dict(profile='ceta-owned-real-effect-v1', run_id='run:controlled')
            def receive_once(self, timeout):
                calls.append(('receive', timeout))
                self._stopped = True
            def close(self):
                calls.append(('close',))
            def _expose(self, primary):
                raise AssertionError('No failure expected in this controlled host')
        with patch.object(host_module, 'ManualRealEffectHost', ControlledHost), \
             patch.object(service, 'emit', lambda value: calls.append(('emit', value))), \
             patch.object(service, 'open_service_journal', side_effect=AssertionError('No ordinary journal')):
            self.assertEqual(service.serve_manual_profile(config, object.__new__(RecordCodec), chosen), 0)
        self.assertIs(calls[0][1], chosen)
        self.assertEqual(calls[0][2]['peer_pid'], 101)
        self.assertEqual(calls[-1], ('close',))
        self.assertEqual([x for x in calls if x[0] == 'receive'], [('receive', 30.0)])


if __name__ == '__main__':
    unittest.main()
