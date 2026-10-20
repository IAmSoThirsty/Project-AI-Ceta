"""P00 task-session and launcher custody under controlled callback failures.

The TaskOperatorSession, compiler threads, task journal, launcher and offscreen
TaskView are actual callers. Cancellation/service faults and compiler ports are
controlled fixtures. These tests do not prove native OS faults, visible installed
UI, durable rejected editor recovery or custody after interpreter death.
Oracles: r6 P00 1/3/4/7, SPEC-08 REQ-08-01/03/04 and SPEC-30 REQ-30-01/02/03.
"""
from contextlib import ExitStack
import gc
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch
import weakref

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.application.lifecycle import PendingShutdownOwner, ShutdownCoordinator, ShutdownIncomplete
from ceta.contracts.wire import ContractError
import test_context_intake as intake
import test_shutdown_interruptions as prior
import test_shutdown_lifecycle as lifecycle


class _TaskSessionCase(unittest.TestCase):
    """Reuse real journal/compiler fixtures without inheriting prior tests."""

    until = prior.TaskSessionInterruptionTests.until
    setup_session = prior.TaskSessionInterruptionTests.setup_session
    held = prior.TaskSessionInterruptionTests.held

    def setUp(self):
        prior.TaskSessionInterruptionTests.setUp(self)
        self.windows = []

    def tearDown(self):
        try:
            # This releases every renderer, observes compiler settlement and
            # closes the actual fixture journal after all fault patches exit.
            prior.TaskSessionInterruptionTests.tearDown(self)
        finally:
            if self.windows:
                from PySide6.QtWidgets import QMessageBox
                with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Close):
                    for window in reversed(self.windows):
                        window.poll_timer.stop()
                        window.close()
                        window.deleteLater()
                self.app.processEvents()

    def custody_cut(self, session, fixture):
        return tuple((task_id, fixture.cell(task_id), entry["title"], entry["draft"], entry["instruction"])
                     for task_id, entry in session._entries.items())

    def two_retained_cancellations(self):
        session, service, fixture, ports, _ = self.setup_session()
        intake.ControlledContextIntakeTests.complete_preview(self, session, service)
        first_cancel = session._entry()["context_cancel"]
        session.new_task()
        session.set_title("Second actual task")
        session.set_draft('NO. Keep the second exclusion.\r\nCafe\u0301\x00')
        session.create()
        service.complete()
        session.poll()
        ports.render_entered, ports.render_release = threading.Event(), threading.Event()
        self.gates.append(ports.render_release)
        session.begin_context_preview(output_tokens=8)
        service.complete()
        session.poll()
        self.assertTrue(ports.render_entered.wait(2))
        active_cancel = session._context_job["cancel"]
        self.assertIsNot(first_cancel, active_cancel)
        return session, service, fixture, ports, first_cancel, active_cancel

    def assert_held_custody(self, session, worker, fixture, before):
        self.assertEqual(session.status, "STOPPING")
        self.assertTrue(session.stop_requested)
        self.assertTrue(session.context_busy)
        self.assertIs(session._context_job["thread"], worker)
        self.assertTrue(worker.is_alive())
        self.assertEqual(self.custody_cut(session, fixture), before)


class SessionFailureTests(_TaskSessionCase):
    def test_stop_publishes_intent_and_attempts_all_cancellations_and_service_despite_failures(self):
        for initiating in (ContractError, KeyboardInterrupt, SystemExit):
            with self.subTest(initiating=initiating.__name__):
                session, service, fixture, ports, cached_cancel, active_cancel = self.two_retained_cancellations()
                before = self.custody_cut(session, fixture)
                worker = session._context_job["thread"]
                primary = initiating("CONTROL_ACTIVE_CANCELLATION_FAILED")
                secondary = SystemExit("controlled cached-cancellation interruption")
                service_error = RuntimeError("controlled service-stop failure")
                calls = []

                def failed_cancel(label, failure):
                    def attempt():
                        calls.append((label, session.status, session.stop_requested))
                        raise failure
                    return attempt

                def failed_service(reason_ref="reason:operator-stop"):
                    calls.append(("service", session.status, session.stop_requested))
                    raise service_error

                with ExitStack() as faults:
                    faults.enter_context(patch.object(active_cancel, "set", new=failed_cancel("active", primary)))
                    faults.enter_context(patch.object(cached_cancel, "set", new=failed_cancel("cached", secondary)))
                    faults.enter_context(patch.object(service, "request_stop", new=failed_service))
                    with self.assertRaises(initiating) as caught:
                        session.stop()
                self.assertIs(caught.exception, primary)
                self.assertEqual([label for label, _, _ in calls], ["active", "cached", "service"])
                self.assertTrue(all(status == "STOPPING" and requested for _, status, requested in calls))
                self.assert_held_custody(session, worker, fixture, before)
                self.assertIn("SESSION_CANCELLATION_FAILED", session.shutdown_diagnostic_codes)
                self.assertIn("SESSION_SERVICE_STOP_FAILED", session.shutdown_diagnostic_codes)
                with self.assertRaises(AttributeError):
                    session.stop_requested = False
                with self.assertRaises(AttributeError):
                    session.shutdown_diagnostic_codes = ()
                session.stop()
                service.finish_stop()
                ports.render_release.set()
                self.until(lambda: (session.poll(), session.status == "STOPPED" and not session.context_busy)[1])
                self.assertFalse(worker.is_alive())
                self.assertEqual(self.custody_cut(session, fixture), before)

    def test_service_stopped_with_failed_cancellation_never_sets_session_stopped(self):
        for failure_type in (ContractError, KeyboardInterrupt, SystemExit):
            with self.subTest(failure_type=failure_type.__name__):
                session, service, fixture, ports = self.held()
                before = self.custody_cut(session, fixture)
                worker, cancel = session._context_job["thread"], session._context_job["cancel"]
                primary = failure_type("CONTROL_CANCELLATION_FAILED")
                service.finish_stop()
                with patch.object(cancel, "set", side_effect=primary):
                    with self.assertRaises(failure_type) as caught:
                        session.poll()
                self.assertIs(caught.exception, primary)
                self.assertEqual(service.state, "STOPPED")
                self.assert_held_custody(session, worker, fixture, before)
                self.assertIn("SESSION_CONTEXT_OBSERVATION_FAILED", session.shutdown_diagnostic_codes)
                self.assertIs(ShutdownCoordinator(service, session).pending_owner.session, session)
                ports.render_release.set()
                self.until(lambda: (session.poll(), session.status == "STOPPED" and not session.context_busy)[1])
                self.assertFalse(worker.is_alive())
                self.assertEqual(self.custody_cut(session, fixture), before)

    def test_service_poll_interruption_remains_primary_when_cancellation_also_interrupts(self):
        for failure_type in (ContractError, KeyboardInterrupt, SystemExit):
            with self.subTest(failure_type=failure_type.__name__):
                session, service, fixture, ports = self.held()
                before = self.custody_cut(session, fixture)
                worker, cancel = session._context_job["thread"], session._context_job["cancel"]
                session.stop()
                primary = failure_type("CONTROL_SERVICE_OBSERVATION_FAILED")
                with patch.object(service, "poll", side_effect=primary), \
                        patch.object(cancel, "set", side_effect=SystemExit("controlled secondary cancellation")):
                    with self.assertRaises(failure_type) as caught:
                        session.poll()
                self.assertIs(caught.exception, primary)
                self.assert_held_custody(session, worker, fixture, before)
                self.assertIn("SESSION_SERVICE_OBSERVATION_FAILED", session.shutdown_diagnostic_codes)
                self.assertIn("SESSION_CANCELLATION_FAILED", session.shutdown_diagnostic_codes)
                service.finish_stop()
                ports.render_release.set()
                self.until(lambda: (session.poll(), session.status == "STOPPED" and not session.context_busy)[1])
                self.assertFalse(worker.is_alive())

    def test_malformed_service_observation_preserves_stopping_and_worker_owner(self):
        for malformed in (None, "STOPPED", {"state": "STOPPED"}, {"state": 1, "detail": "invalid"}):
            with self.subTest(malformed=malformed):
                session, service, fixture, ports = self.held()
                before = self.custody_cut(session, fixture)
                worker = session._context_job["thread"]
                session.stop()
                with patch.object(service, "poll", return_value=malformed):
                    with self.assertRaises(ContractError):
                        session.poll()
                self.assert_held_custody(session, worker, fixture, before)
                self.assertIn("SESSION_SERVICE_OBSERVATION_FAILED", session.shutdown_diagnostic_codes)
                service.finish_stop()
                ports.render_release.set()
                self.until(lambda: (session.poll(), session.status == "STOPPED" and not session.context_busy)[1])
                self.assertFalse(worker.is_alive())

    def test_context_observation_interruption_retains_stopping_and_exact_worker(self):
        for failure_type in (ContractError, KeyboardInterrupt, SystemExit):
            with self.subTest(failure_type=failure_type.__name__):
                session, service, fixture, ports = self.held()
                before = self.custody_cut(session, fixture)
                job = session._context_job
                worker = job["thread"]
                session.stop()
                service.finish_stop()
                primary = failure_type("CONTROL_WORKER_OBSERVATION_FAILED")
                with patch.object(job["done"], "is_set", side_effect=primary):
                    with self.assertRaises(failure_type) as caught:
                        session.poll()
                self.assertIs(caught.exception, primary)
                self.assertIs(session._context_job, job)
                self.assert_held_custody(session, worker, fixture, before)
                self.assertIn("SESSION_CONTEXT_OBSERVATION_FAILED", session.shutdown_diagnostic_codes)
                ports.render_release.set()
                self.until(lambda: (session.poll(), session.status == "STOPPED" and not session.context_busy)[1])
                self.assertFalse(worker.is_alive())


class TaskViewFailureTests(_TaskSessionCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(["ceta-shutdown-session-failures", "-platform", "offscreen"])
        cls.app.setQuitOnLastWindowClosed(False)

    def test_actual_offscreen_view_ignores_close_and_retains_draft_when_cancellation_fails(self):
        from PySide6.QtGui import QCloseEvent
        from ceta.desktop.task_view import TaskView
        for failure_type in (ContractError, KeyboardInterrupt):
            with self.subTest(failure_type=failure_type.__name__):
                session, service, fixture, ports = self.held()
                worker, cancel = session._context_job["thread"], session._context_job["cancel"]
                before = self.custody_cut(session, fixture)
                window = TaskView(session)
                window.poll_timer.stop()
                self.windows.append(window)
                window.show()
                self.app.processEvents()
                widget_before = window.draft_editor.toPlainText().encode("utf8", "surrogatepass")
                primary = failure_type("CONTROL_CANCELLATION_FAILED")
                service.finish_stop()
                with patch.object(cancel, "set", side_effect=primary):
                    if failure_type is ContractError:
                        window._poll()
                    else:
                        with self.assertRaises(failure_type) as caught:
                            window._poll()
                        self.assertIs(caught.exception, primary)
                    self.assert_held_custody(session, worker, fixture, before)
                    self.assertTrue(window.isVisible())
                    self.assertEqual(window.draft_editor.toPlainText().encode("utf8", "surrogatepass"), widget_before)
                    close_event = QCloseEvent()
                    if failure_type is ContractError:
                        window.closeEvent(close_event)
                    else:
                        with self.assertRaises(failure_type) as caught:
                            window.closeEvent(close_event)
                        self.assertIs(caught.exception, primary)
                    self.assertFalse(close_event.isAccepted())
                    self.assertTrue(window.isVisible())
                    self.assertTrue(window._close_requested)
                    self.assert_held_custody(session, worker, fixture, before)
                window._poll()
                self.assertTrue(window.isVisible())
                self.assertTrue(window.draft_editor.isReadOnly())
                self.assertFalse(window.save_button.isEnabled())
                self.assertEqual(window.draft_editor.toPlainText().encode("utf8", "surrogatepass"), widget_before)
                ports.render_release.set()
                self.until(lambda: (window._poll(), not session.context_busy and session.status == "STOPPED")[1])
                self.assertFalse(worker.is_alive())
                self.assertFalse(window.isVisible())
                self.assertEqual(self.custody_cut(session, fixture), before)
                self.assertEqual(window.draft_editor.toPlainText().encode("utf8", "surrogatepass"), widget_before)


class LauncherDiagnosticMutationTests(_TaskSessionCase):
    def test_clearing_or_replacing_primary_dictionary_cannot_erase_typed_worker_custody(self):
        for mutation in ("clear", "replace"):
            for note_error in (None, RuntimeError, KeyboardInterrupt):
                with self.subTest(mutation=mutation, note_error=getattr(note_error, "__name__", "returns")):
                    mutation_calls = []
                    class Primary(KeyboardInterrupt):
                        def add_note(self, note):
                            dictionary = BaseException.__dict__["__dict__"].__get__(self)
                            if mutation == "clear":
                                dictionary.clear()
                            else:
                                self.__dict__ = {"controlled_note_mutation": True}
                            mutation_calls.append(mutation)
                            if note_error is not None:
                                raise note_error("controlled diagnostic failure")

                    session, service, fixture, ports = self.held()
                    before = self.custody_cut(session, fixture)
                    worker = session._context_job["thread"]
                    session_ref, service_ref, worker_ref = weakref.ref(session), weakref.ref(service), weakref.ref(worker)
                    primary = Primary("controlled application failure")
                    owner = None
                    original = ShutdownCoordinator.drain

                    def setup(shutdown):
                        shutdown.capture_session(session)
                        class Application:
                            def exec(self):
                                raise primary
                        class Window:
                            def show(self):
                                pass
                        return Application(), Window()

                    def bounded(shutdown):
                        shutdown.request()
                        service.finish_stop()
                        return original(shutdown, timeout_seconds=0)

                    try:
                        with patch.object(ShutdownCoordinator, "drain", new=bounded):
                            try:
                                lifecycle.launcher()._run_owned_ui(service, setup)
                            except Primary as error:
                                self.assertIs(error, primary)
                                incomplete = error.shutdown_incomplete
                                self.assertIsInstance(incomplete, ShutdownIncomplete)
                                owner = incomplete.pending_owner
                                self.assertIsInstance(owner, PendingShutdownOwner)
                                self.assertIs(owner.session, session)
                                self.assertIs(owner.service, service)
                                self.assertFalse(incomplete.observation.workers_stopped)
                                error.__traceback__ = error.__context__ = error.__cause__ = None
                                incomplete.__traceback__ = incomplete.__context__ = incomplete.__cause__ = None
                            else:
                                self.fail("primary application failure was suppressed")
                        self.sessions.remove((session, service))
                        self.assertEqual(mutation_calls, [mutation], "the controlled dictionary mutation was not reached")
                        del setup, bounded, primary, incomplete, session, service, worker
                        gc.collect()
                        self.assertIs(owner.session, session_ref())
                        self.assertIs(owner.service, service_ref())
                        observed_worker = worker_ref()
                        self.assertIsNotNone(observed_worker)
                        self.assertTrue(observed_worker.is_alive())
                        self.assertEqual(owner.session.status, "STOPPING")
                        self.assertTrue(owner.session.context_busy)
                        self.assertEqual(self.custody_cut(owner.session, fixture), before)
                        ports.render_release.set()
                        self.assertTrue(owner.retry(timeout_seconds=3).workers_stopped)
                        self.assertFalse(observed_worker.is_alive())
                        self.assertEqual(self.custody_cut(owner.session, fixture), before)
                    finally:
                        ports.render_release.set()
                        retained_session, retained_service = session_ref(), service_ref()
                        if retained_session is not None and retained_service is not None:
                            if (retained_session, retained_service) not in self.sessions:
                                self.sessions.append((retained_session, retained_service))
