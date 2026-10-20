"""Owned shutdown regressions, including real disposable Windows service exit.

Compiler timing and injected UI failures are controlled fixtures. Native cases
use authenticated Windows IPC and real owned child lifetimes. Neither scope
qualifies model, effects, persisted editor recovery, or original acceptance.
"""
import importlib.util
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.application.lifecycle import ShutdownCoordinator, ShutdownIncomplete
import test_context_intake as intake
import test_owned_service as native


def launcher():
    spec = importlib.util.spec_from_file_location("lifecycle_operator_fixture", ROOT / "tools/ceta_operator.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _ControlledService:
    """State injection only; actual compiler/native cases appear below."""
    def __init__(self):
        self.state, self.reasons = "READY", []
        self.started = False
        self.start_error = self.poll_error = None

    def request_stop(self, reason="reason:session-stop"):
        self.reasons.append(reason)
        self.state = "STOPPED"
        return self.poll()

    def poll(self):
        if self.poll_error is not None:
            raise self.poll_error
        return {"state": self.state, "detail": "Controlled lifetime fixture."}

    def start(self):
        self.started = True
        if self.start_error is not None:
            raise self.start_error


class ShutdownContractTests(unittest.TestCase):
    def test_request_is_idempotent_and_exit_does_not_claim_reconciliation(self):
        service = _ControlledService()
        shutdown = ShutdownCoordinator(service)
        with self.assertRaisesRegex(RuntimeError, "SHUTDOWN_NOT_REQUESTED"):
            shutdown.advance()
        shutdown.request(); shutdown.request()
        self.assertEqual(len(service.reasons), 1)
        observed = shutdown.advance()
        self.assertTrue(observed.workers_stopped)
        self.assertEqual(observed.reconciliation, "NOT_ESTABLISHED_BY_PROCESS_EXIT")

    def test_observation_failure_and_deadline_never_manufacture_stopped(self):
        service = _ControlledService()
        service.poll_error = RuntimeError("private polling detail")
        shutdown = ShutdownCoordinator(service)
        observed = shutdown.drain(timeout_seconds=0)
        self.assertFalse(observed.workers_stopped)
        self.assertEqual(observed.state, "OBSERVATION_FAILED")
        self.assertIn("SHUTDOWN_DEADLINE_EXPIRED", observed.diagnostic_codes)
        self.assertNotIn("private", repr(observed))
        service.poll_error = None
        self.assertTrue(shutdown.advance().workers_stopped)

    def test_timing_and_late_owner_replacement_are_rejected(self):
        for duration in (True, -1, 61, float("nan"), float("inf"), "1"):
            with self.subTest(duration=duration):
                service = _ControlledService()
                shutdown = ShutdownCoordinator(service)
                with self.assertRaisesRegex(ValueError, "SHUTDOWN_TIMING_REQUIRED"):
                    shutdown.drain(timeout_seconds=duration)
                self.assertEqual(service.reasons, [])
        shutdown = ShutdownCoordinator(_ControlledService())
        shutdown.request()
        with self.assertRaisesRegex(RuntimeError, "SHUTDOWN_SESSION_ALREADY_CAPTURED"):
            shutdown.capture_session(object())

    def test_launcher_cleans_up_setup_show_start_and_event_loop_failures(self):
        module = launcher()
        for phase in ("setup", "show", "start", "event_loop"):
            with self.subTest(phase=phase):
                service = _ControlledService()
                failure = RuntimeError("controlled " + phase)
                class Window:
                    def show(self):
                        if phase == "show":
                            raise failure
                class Application:
                    def exec(self):
                        if phase == "event_loop":
                            raise failure
                        return 7
                def setup(shutdown):
                    if phase == "setup":
                        raise failure
                    return Application(), Window()
                if phase == "start":
                    service.start_error = failure
                with self.assertRaises(RuntimeError) as caught:
                    module._run_owned_ui(service, setup)
                self.assertIs(caught.exception, failure)
                self.assertEqual(service.state, "STOPPED")
                self.assertEqual(len(service.reasons), 1)
                self.assertEqual(service.started, phase in {"start", "event_loop"})

    def test_launcher_normal_return_keeps_actual_exit_code(self):
        service = _ControlledService()
        class Application:
            def exec(self): return 7
        class Window:
            def show(self): pass
        self.assertEqual(launcher()._run_owned_ui(service, lambda owner: (Application(), Window())), 7)
        self.assertEqual(service.state, "STOPPED")


class ContextShutdownTests(unittest.TestCase):
    setUp = intake.ControlledContextIntakeTests.setUp
    tearDown = intake.ControlledContextIntakeTests.tearDown
    until = intake.ControlledContextIntakeTests.until

    def setup_session(self):
        class LifecycleTaskService(intake.controlled_patterns._ControlledTaskService):
            # The task fixture is already READY. Supply the lifecycle port's
            # complete signature without claiming that this fixture starts OS
            # processes; NativeShutdownTests exercises the actual launcher.
            def start(self):
                pass

            def request_stop(self, reason_ref="reason:operator-stop"):
                self.stop_reason = reason_ref
                return super().request_stop()
        with patch.object(intake.controlled_patterns, "_ControlledTaskService", LifecycleTaskService):
            return intake.ControlledContextIntakeTests.setup_session(self)

    def held(self):
        session, service, fixture, ports, _ = self.setup_session()
        ports.render_entered, ports.render_release = threading.Event(), threading.Event()
        self.gates.append(ports.render_release)
        session.begin_context_preview(output_tokens=8)
        service.complete(); session.poll()
        self.assertTrue(ports.render_entered.wait(2))
        return session, service, fixture, ports

    def test_native_stopped_is_insufficient_while_real_compiler_thread_is_held(self):
        session, service, fixture, ports = self.held()
        saved, draft = fixture.cell(session.task_id), session.draft
        worker = session._context_job["thread"]
        shutdown = ShutdownCoordinator(service, session)
        shutdown.request()
        self.assertTrue(session._context_job["cancel"].is_set())
        service.finish_stop()
        observed = shutdown.drain(timeout_seconds=0)
        self.assertEqual(observed.service_state, "STOPPED")
        self.assertEqual(observed.session_state, "STOPPING")
        self.assertTrue(observed.context_pending)
        self.assertFalse(observed.workers_stopped)
        self.assertTrue(worker.is_alive())
        self.assertEqual((fixture.cell(session.task_id), session.draft), (saved, draft))
        ports.render_release.set()
        observed = shutdown.drain(timeout_seconds=3)
        self.assertTrue(observed.workers_stopped)
        self.assertFalse(worker.is_alive())
        self.assertEqual(session.context_status, "CANCELLED")
        self.assertEqual((fixture.cell(session.task_id), session.draft), (saved, draft))

    def test_failed_session_stop_still_requests_actual_service_termination(self):
        session, service, _, ports = self.held()
        shutdown = ShutdownCoordinator(service, session)
        with patch.object(session, "stop", side_effect=RuntimeError("private draft callback failure")):
            shutdown.request()
        self.assertEqual(service.stop_calls, 1)
        service.finish_stop()
        observed = shutdown.advance()
        self.assertTrue(session._context_job["cancel"].is_set())
        self.assertFalse(observed.workers_stopped)
        self.assertIn("SESSION_OR_SERVICE_STOP_FAILED", observed.diagnostic_codes)
        ports.render_release.set()
        self.assertTrue(shutdown.drain(timeout_seconds=3).workers_stopped)

    def test_primary_event_loop_failure_preserves_unresolved_compiler_custody(self):
        module = launcher()
        session, service, fixture, ports = self.held()
        saved, draft = fixture.cell(session.task_id), session.draft
        primary = KeyboardInterrupt("controlled primary event-loop failure")
        class Application:
            def exec(self): raise primary
        class Window:
            def show(self): pass
        def setup(shutdown):
            shutdown.capture_session(session)
            return Application(), Window()
        real_drain = ShutdownCoordinator.drain
        def bounded(shutdown):
            shutdown.request()
            service.finish_stop()
            return real_drain(shutdown, timeout_seconds=0)
        with patch.object(ShutdownCoordinator, "drain", new=bounded):
            with self.assertRaises(KeyboardInterrupt) as caught:
                module._run_owned_ui(service, setup)
        self.assertIs(caught.exception, primary)
        self.assertIn("APPLICATION_CLEANUP_UNRESOLVED: ShutdownIncomplete", primary.__notes__)
        self.assertTrue(session.context_busy)
        self.assertEqual(session.status, "STOPPING")
        self.assertEqual((fixture.cell(session.task_id), session.draft), (saved, draft))
        ports.render_release.set()
        self.until(lambda: (session.poll(), not session.context_busy and session.status == "STOPPED")[1])
        self.assertEqual(session.status, "STOPPED")


class NativeShutdownTests(native._ServiceTestCase):
    empty_service = intake.NativeContextIntakeTests.empty_service
    task_call = intake.NativeContextIntakeTests.task_call
    response_revision = intake.NativeContextIntakeTests.response_revision
    session_fixture = intake.NativeContextIntakeTests.session_fixture
    durable_read_cut = intake.NativeContextIntakeTests.durable_read_cut

    def test_actual_native_service_and_compiler_exit_are_both_observed(self):
        session, service, root, ports, _, _ = self.session_fixture()
        before = self.durable_read_cut(root)
        ports.render_entered, ports.render_release = threading.Event(), threading.Event()
        session.begin_context_preview(output_tokens=8)
        self.until(lambda: (session.poll(), ports.render_entered.is_set())[1])
        worker = session._context_job["thread"]
        shutdown = ShutdownCoordinator(service, session)
        try:
            shutdown.request()
            observed = shutdown.drain(timeout_seconds=0)
            self.assertFalse(observed.workers_stopped)
            self.assertTrue(worker.is_alive())
            self.assertTrue(session._context_job["cancel"].is_set())
            ports.render_release.set()
            observed = shutdown.drain(timeout_seconds=15)
            self.assertTrue(observed.workers_stopped)
            self.assertFalse(worker.is_alive())
            for channel in (service._client, service._service):
                self.assertTrue(channel.observed_exited())
            self.assertEqual(service.poll()["authority"], "CLOSED")
            self.assertEqual(self.durable_read_cut(root), before)
        finally:
            ports.render_release.set()
            self.until(lambda: (session.poll(), not session.context_busy)[1])

    def test_actual_service_is_stopped_after_window_setup_failure(self):
        service, root = self.empty_service()
        before = self.durable_read_cut(root)
        failure = RuntimeError("controlled window construction failure")
        def setup(owner):
            raise failure
        with self.assertRaises(RuntimeError) as caught:
            launcher()._run_owned_ui(service, setup)
        self.assertIs(caught.exception, failure)
        self.assertEqual(service.poll()["state"], "STOPPED")
        self.assertEqual(service.poll()["authority"], "CLOSED")
        for channel in (service._client, service._service):
            self.assertTrue(channel.observed_exited())
        self.assertEqual(self.durable_read_cut(root), before)
