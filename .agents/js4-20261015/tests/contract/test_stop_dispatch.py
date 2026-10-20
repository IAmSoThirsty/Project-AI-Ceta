"""Stop/dispatch regressions with controlled scheduling; NOT QUALIFIED.

The controller, channel, operator, codecs and Qt view are actual application
objects. Process lifetimes, native launch, control writes and result publication
are explicitly injected fixtures. No native service, OS authentication, effect,
normal profile, independent observer or original acceptance is exercised here.
Every blocked fixture has a bounded wait and an unconditional release/join path.
"""
import ctypes as C
import hashlib
from pathlib import Path
from fixture_paths import native_fixture_path
import sys
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ceta.application.operator import OperatorSession
from ceta.composition.owned_service import OwnedService
from ceta.contracts.local_ipc import SubmissionUncertain, decode_message
from ceta.contracts.local_results import encode_response
from ceta.contracts.wire import ContractError, canonical_bytes
from ceta.desktop.operator_view import create_operator_window
from ceta.supervisor.service import OwnedChannel
from test_all_records import example
from test_kernel_transactions import INSTALLATION, PROJECT, SCOPES
from test_owned_service import (_ServiceTestCase, _ChannelFixture,
                               _ControlApiFixture, _ProcessFixture)

THREAD = threading.Thread


class _Probe:
    """A bounded test-owned caller; errors remain visible to the assertions."""
    def __init__(self, action):
        self.done, self.values, self.errors = threading.Event(), [], []
        def run():
            try:
                self.values.append(action())
            except BaseException as error:
                self.errors.append(error)
            finally:
                self.done.set()
        self.thread = THREAD(target=run, daemon=True)

    def start(self):
        self.thread.start()
        return self


class _WriteGate(_ChannelFixture):
    """Controlled send occupancy; the fake lifetime may exit before send returns."""
    def __init__(self, *, failure=None):
        super().__init__()
        self.entered, self.release = threading.Event(), threading.Event()
        self.workers, self.returned = [], threading.Event()
        self.failure, self.close_during_send = failure, False

    def send(self, command):
        self.sent.append(dict(command))
        self.workers.append(threading.current_thread())
        self.entered.set()
        try:
            if not self.release.wait(5):
                raise AssertionError("owned test write gate was not released")
            if self.failure is not None:
                raise self.failure
        finally:
            self.returned.set()

    def close(self):
        if self.entered.is_set() and not self.returned.is_set():
            self.close_during_send = True
        return super().close()


class _DispatchGate:
    """Bounded test-owned scheduling before an actual worker operation."""
    def __init__(self, action):
        self.action = action
        self.entered, self.release = threading.Event(), threading.Event()
        self.workers = []

    def __call__(self, *args, **kwargs):
        self.workers.append(threading.current_thread())
        self.entered.set()
        if not self.release.wait(5):
            raise AssertionError("test-owned dispatch gate was not released")
        return self.action(*args, **kwargs)


class _ThreadConstructorAbort(BaseException):
    """Controlled constructor interruption, not a native or OS failure."""


class _NativeWriteGate(_ControlApiFixture):
    """Actual OwnedChannel code, simulated Win32 WriteFile and handle ownership."""
    def __init__(self):
        super().__init__()
        self.entered, self.release = threading.Event(), threading.Event()
        self.workers, self.writes = [], []

    def WriteFile(self, handle, buffer, size, count, overlapped):
        self.writes.append((handle, C.string_at(buffer, size)))
        self.workers.append(threading.current_thread())
        self.entered.set()
        if not self.release.wait(5):
            raise AssertionError("owned simulated native write was not released")
        count._obj.value = size
        return True


class _LaunchGate:
    """Only an owned constructor is gated; no real process is created."""
    def __init__(self, channel):
        self.channel = channel
        self.entered, self.release = threading.Event(), threading.Event()
        self.workers = []

    def __call__(self, *args, **kwargs):
        self.workers.append(threading.current_thread())
        self.entered.set()
        if not self.release.wait(5):
            raise AssertionError("owned test launch gate was not released")
        return self.channel


class _StopDispatchCase(_ServiceTestCase):
    """Reuse only the same-project helper base, which defines no test methods."""
    def setUp(self):
        super().setUp()
        self.gates, self.probes = [], []

    def tearDown(self):
        for gate in self.gates:
            gate.release.set()
        threads = {probe.thread for probe in self.probes}
        for gate in self.gates:
            threads.update(gate.workers)
        for thread in threads:
            if thread is not threading.current_thread() and thread.ident is not None:
                thread.join(timeout=5)
        remaining = [thread.name for thread in threads
                     if thread is not threading.current_thread() and thread.is_alive()]
        try:
            super().tearDown()
        finally:
            self.assertEqual(remaining, [], "test-owned scheduling work did not retire")

    def probe(self, action):
        result = _Probe(action)
        self.probes.append(result)
        return result.start()

    def gate(self, value):
        self.gates.append(value)
        return value

    def ready_controlled(self, *, failure=None, call_seconds=4.0):
        service = OwnedService(self.directory(), self.codec, INSTALLATION, SCOPES,
                               call_seconds=call_seconds, session_id="session:controlled-stop")
        self.services.append(service)
        client, server = self.gate(_WriteGate(failure=failure)), _ChannelFixture()
        service._client, service._service = client, server
        service._generation, service._state = "d" * 64, "READY"
        return service, client, server

    def record(self, kind="ActionProposal"):
        value = example(self.schema["$defs"][kind])
        value.update(record_id="record:controlled-stop", scope_id=PROJECT)
        return canonical_bytes(value)

    def entered(self, gate):
        self.assertTrue(gate.entered.wait(2), "the real call path did not enter the fixture gate")

    def prompt(self, probe, purpose):
        self.assertTrue(probe.done.wait(0.5), purpose)

    def retire(self, gate):
        gate.release.set()
        for thread in tuple(gate.workers):
            if thread is not threading.current_thread():
                thread.join(timeout=3)
                self.assertFalse(thread.is_alive(), "released test-owned worker remains active")

    def response(self, service, client, attempt):
        request = decode_message((native_fixture_path(service._spool / (attempt + ".request.json"))).read_bytes(), self.codec)
        wire = encode_response(request, ContractError("CONTROLLED_RESULT_DENIAL"), self.codec)
        (native_fixture_path(service._spool / (attempt + ".response.json"))).write_bytes(wire)
        client.events.append({"event": "call_result", "attempt": attempt,
                              "response_sha256": hashlib.sha256(wire).hexdigest()})
        return wire


class StopDispatchTests(_StopDispatchCase):
    def test_begin_call_returns_before_owned_control_write_gate_releases(self):
        service, client, _ = self.ready_controlled()
        call = self.probe(lambda: service.begin_call(self.record(), "kernel.prepare"))
        try:
            self.entered(client)
            self.prompt(call, "begin_call occupied its caller while the owned send was blocked")
            self.assertEqual(call.errors, [])
            attempt = call.values[0]
            self.assertEqual(service.snapshot()["pending_attempt"], attempt)
            self.assertFalse(client.returned.is_set())
            self.assertEqual(len(client.sent), 1)
            with self.assertRaises(ContractError):
                service.begin_call(self.record(), "kernel.prepare")
        finally:
            self.retire(client)

    def test_stop_returns_independently_of_blocked_write_and_late_failure_cannot_revive_it(self):
        service, client, server = self.ready_controlled(failure=OSError("controlled late write failure"))
        call = self.probe(lambda: service.begin_call(self.record(), "kernel.prepare"))
        try:
            self.entered(client)
            stop = self.probe(service.request_stop)
            self.prompt(stop, "Stop was blocked behind the control writer")
            self.assertEqual(stop.errors, [])
            self.assertEqual(stop.values[0]["state"], "STOPPING")
            self.assertTrue(client.process.terminations)
            self.assertTrue(server.process.terminations)
            with self.assertRaises(ContractError):
                service.begin_call(self.record(), "kernel.prepare")
        finally:
            self.retire(client)
        self.assertTrue(call.done.wait(2))
        self.assertEqual(service.poll()["state"], "STOPPED")
        self.assertFalse(client.close_during_send)
        self.assertEqual(service.snapshot()["call"]["kind"], "TRANSPORT_UNCERTAIN")

    def test_poll_keeps_stopping_and_writer_handles_until_send_thread_observed_retired(self):
        service, client, _ = self.ready_controlled()
        call = self.probe(lambda: service.begin_call(self.record(), "kernel.prepare"))
        try:
            self.entered(client)
            stop = self.probe(service.request_stop)
            self.prompt(stop, "Stop could not publish independently of send occupancy")
            self.assertEqual(stop.errors, [])
            self.assertFalse(client.process.alive, "the lifetime fixture must already be exited")
            poll = self.probe(service.poll)
            self.prompt(poll, "poll waited for an unfinished writer")
            self.assertEqual(poll.errors, [])
            self.assertEqual(poll.values[0]["state"], "STOPPING")
            self.assertFalse(client.closed, "process exit alone cannot release active writer handles")
            self.assertFalse(client.close_during_send)
        finally:
            self.retire(client)
        self.assertTrue(call.done.wait(2))
        self.assertEqual(service.poll()["state"], "STOPPED")

    def test_late_successful_write_and_valid_reply_never_revive_stopping(self):
        service, client, _ = self.ready_controlled()
        call = self.probe(lambda: service.begin_call(self.record(), "kernel.prepare"))
        try:
            self.entered(client)
            self.prompt(call, "submission did not hand its writer to owned work")
            self.assertEqual(call.errors, [])
            attempt = call.values[0]
            service.request_stop()
            self.response(service, client, attempt)
            self.assertEqual(service.poll()["state"], "STOPPING")
            self.assertFalse(client.closed)
        finally:
            self.retire(client)
        final = service.poll()
        self.assertEqual(final["state"], "STOPPED")
        self.assertEqual(final["authority"], "CLOSED")
        self.assertEqual(final["call"]["kind"], "DENIED_RECONCILE")

    def test_validated_reply_before_writer_retirement_is_retained_and_second_send_denied(self):
        service, client, _ = self.ready_controlled()
        call = self.probe(lambda: service.begin_call(self.record(), "kernel.prepare"))
        try:
            self.entered(client)
            self.prompt(call, "submission must return while its writer remains owned")
            self.assertEqual(call.errors, [])
            attempt = call.values[0]
            response = self.response(service, client, attempt)
            observation = service.poll()
            self.assertEqual(observation["call"]["response"].original_response, response)
            self.assertFalse(client.returned.is_set())
            second = self.probe(lambda: service.begin_call(self.record("OperationPermit"), "kernel.recover_permit"))
            self.prompt(second, "second dispatch must promptly deny while first writer is active")
            self.assertEqual(len(second.errors), 1)
            self.assertIsInstance(second.errors[0], ContractError)
            self.assertEqual(len(client.sent), 1)
        finally:
            self.retire(client)
        final = service.poll()
        self.assertEqual(final["call"]["attempt"], attempt)
        self.assertEqual(final["call"]["response"].original_response, response)
        self.assertEqual(len(tuple(service._spool.glob("*.request.json"))), 1)

    def test_async_failure_keeps_operator_attempt_draft_and_later_valid_result_upgrade(self):
        service, client, _ = self.ready_controlled(failure=OSError("controlled async failure"))
        operator = OperatorSession(service, self.codec)
        draft = self.record().decode("utf8")
        operator.set_draft(draft)
        submit = self.probe(lambda: operator.submit("kernel.prepare"))
        try:
            self.entered(client)
            self.prompt(submit, "operator submission waited for the controlled write")
            self.assertEqual(submit.errors, [])
            attempt = submit.values[0]
            self.assertEqual(operator._attempt, attempt)
            self.assertEqual(operator.draft, draft)
        finally:
            self.retire(client)
        observation = operator.poll()
        self.assertEqual(observation["call"]["attempt"], attempt)
        self.assertEqual(observation["call"]["kind"], "TRANSPORT_UNCERTAIN")
        request_wire = (native_fixture_path(service._spool / (attempt + ".request.json"))).read_bytes()
        self.assertEqual(decode_message(request_wire, self.codec).record.original_wire, draft.encode("utf8"))
        self.assertEqual(service.snapshot()["pending_attempt"], attempt)
        response = self.response(service, client, attempt)
        operator.poll()
        self.assertEqual(operator.result_text, response.decode("utf8"))
        self.assertEqual(operator.draft, draft)
        self.assertEqual(len(client.sent), 1)
        self.assertEqual(len(tuple(service._spool.glob("*.request.json"))), 1)

    def test_dispatch_thread_start_failure_is_typed_uncertainty_with_exact_scope_and_draft(self):
        service, client, _ = self.ready_controlled()
        client.release.set()
        operator = OperatorSession(service, self.codec)
        draft = self.record().decode("utf8")
        operator.set_draft(draft)
        # The test has no caller thread to start in this patch. Only production
        # dispatch's Thread.start is faulted; no native/global OS fault injection.
        with patch("ceta.composition.owned_service.threading.Thread.start",
                   side_effect=RuntimeError("controlled owned-thread start failure")):
            with self.assertRaises(SubmissionUncertain) as caught:
                operator.submit("kernel.prepare")
        attempt = caught.exception.attempt
        self.assertEqual(caught.exception.code, "IPC_SUBMISSION_UNCERTAIN")
        self.assertEqual(operator._attempt, attempt)
        self.assertEqual(operator.draft, draft)
        self.assertEqual(client.sent, [])
        pending = service._pending
        self.assertEqual(pending["attempt"], attempt)
        request = decode_message(pending["request_wire"], self.codec)
        self.assertEqual(request.scope_id, PROJECT)
        self.assertEqual(request.record.original_wire, draft.encode("utf8"))
        self.assertEqual(pending["request"].original_message, pending["request_wire"])
        self.assertFalse(native_fixture_path(Path(pending["request_path"])).exists(), "no worker wrote this request file")
        self.assertIsInstance(caught.exception.__cause__, RuntimeError)
        self.assertEqual(service.snapshot()["pending_attempt"], attempt)
        self.assertEqual(service.snapshot()["call"]["kind"], "TRANSPORT_UNCERTAIN")
        worker = service._send_task
        thread = worker["thread"]
        try:
            service.request_stop()
            self.assertEqual(service.poll()["state"], "STOPPING")
            self.assertFalse(worker["done"])
            self.assertTrue(worker["launch_uncertain"])
            self.assertIn(worker, service._workers)
            self.assertFalse(client.closed)
        finally:
            # The deliberate no-entry fixture releases its captured target now.
            # This is test cleanup, not a production absence settlement/retry.
            thread.start()
            thread.join(timeout=3)
            self.assertFalse(thread.is_alive())
        self.assertEqual(service.poll()["state"], "STOPPED")
        self.assertEqual(native_fixture_path(Path(pending["request_path"])).read_bytes(), pending["request_wire"])
        self.assertIs(service._pending, pending, "Stop must retain the unpersisted exact request")
        self.assertEqual(service.snapshot()["pending_attempt"], attempt)
        self.assertEqual(operator.draft, draft)
        self.assertEqual(client.sent, [])

    def test_dispatch_start_exception_after_entry_keeps_worker_until_actual_exit(self):
        for failure in (RuntimeError("controlled post-entry failure"),
                        KeyboardInterrupt("controlled post-entry interrupt")):
            with self.subTest(failure=type(failure).__name__):
                service, client, server = self.ready_controlled()
                original_start = THREAD.start
                def started_then_failed(thread):
                    original_start(thread)
                    self.assertTrue(client.entered.wait(2))
                    raise failure
                try:
                    with patch("ceta.composition.owned_service.threading.Thread.start", new=started_then_failed):
                        with self.assertRaises(SubmissionUncertain) as caught:
                            service.begin_call(self.record(), "kernel.prepare")
                    worker, pending = service._send_task, service._pending
                    thread = worker["thread"]
                    self.assertIs(caught.exception.__cause__, failure)
                    self.assertTrue(thread.is_alive())
                    self.assertTrue(worker["launch_uncertain"])
                    self.assertFalse(worker["done"])
                    service.request_stop()
                    self.assertEqual(service.poll()["state"], "STOPPING")
                    self.assertIn(worker, service._workers)
                    self.assertFalse(client.closed or server.closed)
                    self.assertEqual(native_fixture_path(Path(pending["request_path"])).read_bytes(), pending["request_wire"])
                    self.assertEqual(len(client.sent), 1)
                finally:
                    self.retire(client)
                self.assertEqual(service.poll()["state"], "STOPPED")
                self.assertFalse(thread.is_alive())
                self.assertEqual(len(client.sent), 1)
                self.assertIs(service._pending, pending)

    def test_service_launch_start_failure_retains_unobserved_publication_until_target_exit(self):
        service, client, server = self.ready_controlled()
        service._service = None
        service._state = "STARTING"
        service._client_ready = True
        service._started_deadline = time.monotonic() + 10
        client.release.set()
        with patch("ceta.composition.owned_service.threading.Thread.start",
                   side_effect=RuntimeError("controlled service launch start failure")):
            self.assertEqual(service.poll()["state"], "RECOVERING")
        worker = service._workers[0]
        thread = worker["thread"]
        try:
            self.assertEqual(worker["kind"], "launch_service")
            self.assertTrue(worker["launch_uncertain"])
            self.assertTrue(service._service_launch_pending)
            service.request_stop()
            self.assertEqual(service.poll()["state"], "STOPPING")
            self.assertFalse(client.closed)
        finally:
            # Running the captured test target after Stop cannot launch an owner:
            # the actual _launch_owned guard denies before native construction.
            with patch("ceta.composition.owned_service.OwnedChannel") as constructor:
                thread.start()
                thread.join(timeout=3)
                self.assertFalse(thread.is_alive())
                constructor.assert_not_called()
        self.assertFalse(service._service_launch_pending)
        self.assertEqual(service.poll()["state"], "STOPPED")
        self.assertEqual(service._workers, [])
        self.assertIsNone(service._service)

    def test_stop_wins_before_worker_send_admission_without_control_dispatch(self):
        service, client, server = self.ready_controlled()
        record_wire = self.record()
        gate = self.gate(_DispatchGate(service._send_call))
        with patch.object(service, "_send_call", side_effect=gate):
            call = self.probe(lambda: service.begin_call(record_wire, "kernel.prepare"))
            try:
                self.entered(gate)
                self.prompt(call, "reservation must return before the send worker enters admission")
                self.assertEqual(call.errors, [])
                attempt = call.values[0]
                pending = service._pending
                request_wire = pending["request_wire"]
                self.assertEqual(pending["attempt"], attempt)
                self.assertEqual(decode_message(request_wire, self.codec).record.original_wire, record_wire)
                self.assertFalse(native_fixture_path(Path(pending["request_path"])).exists())
                stop = self.probe(service.request_stop)
                self.prompt(stop, "Stop must win before the queued worker enters send admission")
                self.assertEqual(stop.errors, [])
                self.assertEqual(stop.values[0]["state"], "STOPPING")
                self.assertTrue(client.process.terminations and server.process.terminations)
                self.assertEqual(client.sent, [])
                self.assertFalse(client.entered.is_set())
                self.assertEqual(service.poll()["state"], "STOPPING")
                self.assertFalse(client.closed)
            finally:
                self.retire(gate)
        final = service.poll()
        self.assertEqual(final["state"], "STOPPED")
        self.assertEqual(final["pending_attempt"], attempt)
        self.assertIs(service._pending, pending)
        self.assertEqual(pending["request_wire"], request_wire)
        self.assertEqual(native_fixture_path(Path(pending["request_path"])).read_bytes(), request_wire)
        self.assertEqual(client.sent, [], "a stopped reserved attempt cannot be dispatched after release")
        self.assertEqual(final["call"]["attempt"], attempt)
        self.assertEqual(final["call"]["kind"], "TRANSPORT_UNCERTAIN")
        with self.assertRaises(ContractError):
            service.begin_call(record_wire, "kernel.prepare")

    def test_request_preservation_failure_keeps_exact_memory_and_never_sends_control(self):
        service, client, _ = self.ready_controlled()
        operator = OperatorSession(service, self.codec)
        draft = self.record().decode("utf8")
        operator.set_draft(draft)
        original_open = Path.open
        failure = OSError("controlled request-preservation failure")
        def fail_open(*args, **kwargs):
            raise failure
        gate = self.gate(_DispatchGate(fail_open))
        def selected_open(path, mode="r", *args, **kwargs):
            if mode == "xb" and path.parent == native_fixture_path(service._spool) and path.name.endswith(".request.json"):
                return gate(path, mode, *args, **kwargs)
            return original_open(path, mode, *args, **kwargs)
        with patch("ceta.composition.owned_service.Path.open", new=selected_open):
            submit = self.probe(lambda: operator.submit("kernel.prepare"))
            try:
                self.entered(gate)
                self.prompt(submit, "file preservation must not occupy the submission caller")
                self.assertEqual(submit.errors, [])
                attempt = submit.values[0]
                pending = service._pending
                request_wire = pending["request_wire"]
                self.assertEqual(operator._attempt, attempt)
                self.assertEqual(operator.draft, draft)
                self.assertEqual(client.sent, [])
            finally:
                self.retire(gate)
        observation = operator.poll()
        self.assertEqual(observation["state"], "RECOVERING")
        self.assertEqual(observation["call"]["attempt"], attempt)
        self.assertEqual(observation["call"]["kind"], "TRANSPORT_UNCERTAIN")
        self.assertIs(service._pending, pending)
        request = decode_message(request_wire, self.codec)
        self.assertEqual(request.scope_id, PROJECT)
        self.assertEqual(request.record.original_wire, draft.encode("utf8"))
        self.assertEqual(pending["request"].original_message, request_wire)
        self.assertFalse(native_fixture_path(Path(pending["request_path"])).exists())
        self.assertEqual(client.sent, [], "failed request preservation cannot admit a control send")
        service.request_stop()
        stopped = service.poll()
        self.assertEqual(stopped["state"], "STOPPED")
        self.assertEqual(stopped["pending_attempt"], attempt)
        self.assertIs(service._pending, pending, "Stop must preserve an unpersisted request in memory")
        self.assertEqual(pending["request_wire"], request_wire)
        self.assertEqual(operator.draft, draft)
        self.assertEqual(client.sent, [])

    def test_dispatch_thread_constructor_baseexception_preserves_attempt_and_cleanup(self):
        service, client, server = self.ready_controlled()
        operator = OperatorSession(service, self.codec)
        draft = self.record().decode("utf8")
        operator.set_draft(draft)
        failure = _ThreadConstructorAbort("controlled thread constructor interruption")
        with patch("ceta.composition.owned_service.threading.Thread", side_effect=failure):
            with self.assertRaises(SubmissionUncertain) as caught:
                operator.submit("kernel.prepare")
        attempt = caught.exception.attempt
        pending = service._pending
        self.assertIs(caught.exception.__cause__, failure)
        self.assertEqual(caught.exception.code, "IPC_SUBMISSION_UNCERTAIN")
        self.assertEqual(operator._attempt, attempt)
        self.assertEqual(operator.draft, draft)
        self.assertEqual(pending["attempt"], attempt)
        request = decode_message(pending["request_wire"], self.codec)
        self.assertEqual(request.scope_id, PROJECT)
        self.assertEqual(request.record.original_wire, draft.encode("utf8"))
        self.assertFalse(native_fixture_path(Path(pending["request_path"])).exists())
        self.assertEqual(client.sent, [])
        self.assertEqual(operator.poll()["call"]["kind"], "TRANSPORT_UNCERTAIN")
        service.request_stop()
        stopped = service.poll()
        self.assertEqual(stopped["state"], "STOPPED", "an absent constructor owns no running thread")
        self.assertEqual(stopped["pending_attempt"], attempt)
        self.assertIs(service._pending, pending)
        self.assertEqual(pending["request_wire"], request.original_message)
        self.assertTrue(client.closed and server.closed)
        self.assertTrue(client.process.terminations and server.process.terminations)
        self.assertEqual(client.sent, [])

    def test_direct_owned_channel_close_denies_active_write_lease_after_process_exit(self):
        process, api = _ProcessFixture(), self.gate(_NativeWriteGate())
        with patch("ceta.supervisor.service._ControlApi", return_value=api), \
                patch("ceta.supervisor.service.WindowsOwnedProcess.launch", return_value=process):
            channel = OwnedChannel("controlled-image", (), cwd="controlled-cwd", environment={})
        parent_handles = {channel._input, channel._output, channel._error}
        writer = self.probe(lambda: channel.send({"profile": "controlled-lease"}))
        try:
            self.entered(api)
            process.finish()
            closer = self.probe(channel.close)
            self.prompt(closer, "channel close must deny promptly rather than wait for the active writer")
            self.assertEqual(len(closer.errors), 1)
            self.assertIsInstance(closer.errors[0], ContractError)
            self.assertFalse(process.closed)
            self.assertFalse(parent_handles & api.closed)
        finally:
            self.retire(api)
            writer.thread.join(timeout=3)
            process.finish()
            channel.close()
        self.assertEqual(writer.errors, [])
        self.assertTrue(parent_handles.issubset(api.closed))
        self.assertEqual(len(api.writes), 1)

    def test_exact_selected_lifetime_envelope_and_control_deadlines_are_captured_before_send(self):
        service, client, server = self.ready_controlled(call_seconds=1.25)
        expected = server.process.pid, server.process.creation_time, server.process.image_sha256
        generation, session, pipe = service.generation, service._session, service._pipe
        record_wire = self.record()
        with patch("ceta.composition.owned_service.time.time_ns", return_value=1_800_000_000_000_000_000), \
                patch("ceta.composition.owned_service.time.monotonic", return_value=123.0):
            call = self.probe(lambda: service.begin_call(record_wire, "kernel.prepare"))
            try:
                self.entered(client)
                command = client.sent[0]
                attempt = command["attempt"]
                request_wire = (native_fixture_path(service._spool / (attempt + ".request.json"))).read_bytes()
                request = decode_message(request_wire, self.codec)
                self.assertEqual((command["server_pid"], command["server_creation"], command["server_image"]), expected)
                self.assertEqual(command["timeout_ms"], 1250)
                self.assertEqual(command["pipe"], pipe)
                self.assertEqual(command["request_sha256"], hashlib.sha256(request_wire).hexdigest())
                self.assertEqual(request.record.original_wire, record_wire)
                self.assertEqual(request.sender_session, session)
                self.assertEqual(request.receiver_generation, generation)
                self.assertEqual(request.issued_at_ms, 1_800_000_000_000)
                self.assertEqual(request.expires_at_ms, request.issued_at_ms + 10000)
                self.assertEqual(service._pending["deadline"], 125.25)
            finally:
                self.retire(client)
        self.assertTrue(call.done.wait(2))
        self.assertEqual(call.errors, [])
        self.assertEqual(len(client.sent), 1)

    def test_start_returns_while_owned_native_launch_is_blocked_and_stop_retains_late_owner(self):
        service = self.service(self.directory())
        channel = _ChannelFixture()
        gate = self.gate(_LaunchGate(channel))
        with patch("ceta.composition.owned_service.OwnedChannel", side_effect=gate):
            start = self.probe(service.start)
            try:
                self.entered(gate)
                self.prompt(start, "start occupied its caller inside native launch")
                self.assertEqual(start.errors, [])
                stop = self.probe(service.request_stop)
                self.prompt(stop, "Stop blocked behind asynchronous startup")
                self.assertEqual(stop.errors, [])
                self.assertEqual(service.poll()["state"], "STOPPING")
                self.assertFalse(channel.closed)
                with self.assertRaises(ContractError):
                    service.begin_call(self.record(), "kernel.prepare")
            finally:
                self.retire(gate)
            self.assertEqual(service.poll()["state"], "STOPPED")
            self.assertTrue(channel.process.terminations)
            self.assertTrue(channel.closed)

    def test_poll_returns_while_service_launch_is_blocked_and_stop_owns_publication(self):
        service = self.service(self.directory())
        client, server = _ChannelFixture(), _ChannelFixture()
        service._client, service._client_ready = client, True
        service._state, service._start_claimed = "STARTING", True
        service._started_deadline = time.monotonic() + 15
        gate = self.gate(_LaunchGate(server))
        with patch("ceta.composition.owned_service.OwnedChannel", side_effect=gate):
            poll = self.probe(service.poll)
            try:
                self.entered(gate)
                self.prompt(poll, "poll occupied its caller inside service native launch")
                self.assertEqual(poll.errors, [])
                stop = self.probe(service.request_stop)
                self.prompt(stop, "Stop waited for service native launch")
                self.assertEqual(stop.errors, [])
                self.assertEqual(service.poll()["state"], "STOPPING")
            finally:
                self.retire(gate)
            self.assertEqual(service.poll()["state"], "STOPPED")
            self.assertTrue(client.closed and server.closed)
            self.assertTrue(server.process.terminations)


class QtStopDispatchTests(_StopDispatchCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(["ceta-stop-dispatch-tests", "-platform", "offscreen"])
        cls.app.setQuitOnLastWindowClosed(False)

    def test_real_qt_view_and_operator_keep_stop_reachable_during_owned_send(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        service, client, _ = self.ready_controlled()
        operator = OperatorSession(service, self.codec)
        operator.poll()
        draft = self.record().decode("utf8")
        operator.set_draft(draft)
        window = create_operator_window(operator)
        window.show()
        self.app.processEvents()
        cancel, watchdog_released = threading.Event(), threading.Event()
        def watchdog():
            if not cancel.wait(2):
                watchdog_released.set()
                client.release.set()
        watchdog_thread = THREAD(target=watchdog, daemon=True)
        watchdog_thread.start()
        try:
            self.assertEqual(self.app.platformName(), "offscreen", "this fixture qualifies only offscreen Qt controls")
            # On the synchronous baseline this click is released by the external
            # watchdog. It cannot leave the Qt test blocked indefinitely.
            QTest.mouseClick(window.submit_button, Qt.MouseButton.LeftButton)
            self.entered(client)
            self.assertFalse(watchdog_released.is_set(), "Submit blocked Qt until the external release watchdog")
            QTest.mouseClick(window.stop_button, Qt.MouseButton.LeftButton)
            self.app.processEvents()
            self.assertTrue(client.process.terminations)
            self.assertEqual(operator.status, "STOPPING")
            self.assertIn("STOPPING", window.status_label.text())
            self.assertTrue(window.stop_button.isEnabled())
            self.assertFalse(window.submit_button.isEnabled())
            self.assertEqual(window.draft_editor.toPlainText(), draft)
            self.assertEqual(operator.draft, draft)
            self.assertFalse(client.returned.is_set())
            self.assertFalse(client.closed)
            window.activateWindow()
            window.stop_button.setFocus()
            self.app.processEvents()
            before_esc = len(client.process.terminations)
            QTest.keyClick(window, Qt.Key.Key_Escape)
            self.app.processEvents()
            self.assertGreater(len(client.process.terminations), before_esc,
                               "Esc must call the real operator Stop while the writer remains held")
            self.assertEqual(operator.status, "STOPPING")
            self.assertEqual(window.draft_editor.toPlainText(), draft)
            self.assertFalse(client.returned.is_set())
            self.assertFalse(client.closed)
        finally:
            cancel.set()
            try:
                self.retire(client)
            finally:
                try:
                    watchdog_thread.join(timeout=3)
                finally:
                    try:
                        service.request_stop()
                        self.until(lambda: service.poll()["state"] == "STOPPED", seconds=3)
                        operator.poll()
                    finally:
                        try:
                            window.close()
                        finally:
                            # QObject deletion is test disposal, not a false STOPPED publication.
                            window.deleteLater()
                            self.app.processEvents()
        self.assertFalse(watchdog_thread.is_alive())


if __name__ == "__main__":
    unittest.main()
