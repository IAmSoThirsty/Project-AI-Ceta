"""P00 interruption and explicit pending-owner regressions.

Oracles: r6 P00 items 1-4/7; SPEC-08 REQ-08-01/03/04; SPEC-30
REQ-30-01/02/03. Controlled failures are injected through actual coordinator,
TaskOperatorSession and launcher calls. Compiler ports are synthetic, but held
compiler threads and task storage are real. Native cases use disposable Windows
OwnedService processes. None proves outer-interpreter survival, protected-domain
publication fencing, durable editor custody, installed or product qualification.
"""
from contextlib import ExitStack
import gc
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import weakref

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.application.lifecycle import (
    PendingShutdownOwner, ShutdownCoordinator, ShutdownIncomplete,
)
from ceta.contracts.wire import ContractError
import test_shutdown_lifecycle as existing
import test_context_intake as intake
import test_owned_service as native


class _ObservedService:
    """Controlled lifecycle port; stop requests and exit observations differ."""

    def __init__(self):
        self.state = "READY"
        self.reasons, self.stop_failures = [], []
        self.poll_failure = self.before_stop = None

    def start(self):
        pass

    def request_stop(self, reason_ref="reason:operator-stop"):
        self.reasons.append(reason_ref)
        if self.before_stop is not None:
            self.before_stop()
        if self.stop_failures:
            raise self.stop_failures.pop(0)
        if self.state != "STOPPED":
            self.state = "STOPPING"
        return {"state": self.state, "detail": "Controlled stop requested."}

    def poll(self):
        if self.poll_failure is not None:
            raise self.poll_failure
        return {"state": self.state, "detail": "Controlled observed state."}

    def observe_exit(self):
        self.state = "STOPPED"


def _ui(return_code=7, primary=None):
    class Application:
        def exec(self):
            if primary is not None:
                raise primary
            return return_code

    class Window:
        def show(self):
            pass

    return Application(), Window()


class InterruptionContractTests(unittest.TestCase):
    def test_requested_state_precedes_callback_and_retry_is_explicit(self):
        service = _ObservedService()
        shutdown = ShutdownCoordinator(service)
        seen = []

        def inside_stop():
            observed = shutdown.observation
            seen.append((observed.requested, observed.state, observed.workers_stopped))

        service.before_stop = inside_stop
        shutdown.request()
        first = shutdown.observation
        self.assertIs(shutdown.request(), first)
        self.assertEqual(len(service.reasons), 1)
        shutdown.request(retry=True)
        self.assertEqual(len(service.reasons), 2)
        self.assertEqual(seen, [(True, "STOPPING", False)] * 2)
        self.assertFalse(shutdown.advance().workers_stopped)
        service.observe_exit()
        self.assertTrue(shutdown.advance().workers_stopped)

    def test_request_interruptions_preserve_identity_after_secondary_fallback(self):
        for interruption in (KeyboardInterrupt, SystemExit):
            for fallback_error in (None, RuntimeError("private fallback detail"), SystemExit(82)):
                with self.subTest(interruption=interruption.__name__, fallback=type(fallback_error).__name__):
                    service = _ObservedService()
                    primary = interruption("controlled initiating interruption")
                    service.stop_failures = [primary] + ([] if fallback_error is None else [fallback_error])
                    shutdown = ShutdownCoordinator(service)
                    with self.assertRaises(interruption) as caught:
                        shutdown.request()
                    self.assertIs(caught.exception, primary)
                    observed = shutdown.observation
                    self.assertTrue(observed.requested)
                    self.assertFalse(observed.workers_stopped)
                    self.assertIn("SESSION_OR_SERVICE_STOP_FAILED", observed.diagnostic_codes)
                    if fallback_error is not None:
                        self.assertIn("SERVICE_STOP_FALLBACK_FAILED", observed.diagnostic_codes)
                    self.assertEqual(len(service.reasons), 2)
                    self.assertIs(shutdown.request(), observed)
                    self.assertEqual(len(service.reasons), 2)
                    owner = shutdown.pending_owner
                    self.assertIsInstance(owner, PendingShutdownOwner)
                    self.assertIs(owner, shutdown.pending_owner)
                    self.assertIs(owner.service, service)
                    self.assertIsNone(owner.session)
                    self.assertIs(owner.observation, observed)
                    self.assertNotIn("private", repr(observed))
                    service.observe_exit()
                    self.assertTrue(owner.retry(timeout_seconds=0).workers_stopped)

    def test_poll_interruptions_attempt_fallback_and_preserve_primary(self):
        for interruption in (KeyboardInterrupt, SystemExit):
            for fallback_error in (None, KeyboardInterrupt("secondary stop interruption")):
                with self.subTest(interruption=interruption.__name__, fallback=type(fallback_error).__name__):
                    service = _ObservedService()
                    shutdown = ShutdownCoordinator(service)
                    shutdown.request()
                    primary = interruption("controlled observation interruption")
                    service.poll_failure = primary
                    service.stop_failures = [] if fallback_error is None else [fallback_error]
                    with self.assertRaises(interruption) as caught:
                        shutdown.advance()
                    self.assertIs(caught.exception, primary)
                    observed = shutdown.observation
                    self.assertTrue(observed.requested)
                    self.assertFalse(observed.workers_stopped)
                    self.assertIn("SHUTDOWN_OBSERVATION_FAILED", observed.diagnostic_codes)
                    self.assertEqual(len(service.reasons), 2)
                    if fallback_error is not None:
                        self.assertIn("SERVICE_STOP_FALLBACK_FAILED", observed.diagnostic_codes)
                    service.poll_failure = None
                    service.observe_exit()
                    self.assertTrue(shutdown.pending_owner.retry(timeout_seconds=0).workers_stopped)

    def test_interrupted_observation_cannot_reuse_previous_stopped_success(self):
        service = _ObservedService()
        shutdown = ShutdownCoordinator(service)
        shutdown.request()
        service.observe_exit()
        previous = shutdown.advance()
        self.assertTrue(previous.workers_stopped)
        primary = KeyboardInterrupt("controlled later observation interruption")
        service.poll_failure = primary
        with self.assertRaises(KeyboardInterrupt) as caught:
            shutdown.advance()
        self.assertIs(caught.exception, primary)
        self.assertFalse(shutdown.observation.workers_stopped)
        self.assertIn("SHUTDOWN_OBSERVATION_FAILED", shutdown.observation.diagnostic_codes)

    def test_ordinary_failure_remains_diagnostic_and_incomplete(self):
        service = _ObservedService()
        service.stop_failures = [RuntimeError("controlled stop failure")]
        shutdown = ShutdownCoordinator(service)
        self.assertFalse(shutdown.request().workers_stopped)
        service.poll_failure = RuntimeError("controlled observation failure")
        self.assertFalse(shutdown.advance().workers_stopped)
        self.assertIn("SHUTDOWN_OBSERVATION_FAILED", shutdown.observation.diagnostic_codes)

    def test_invalid_retry_timing_issues_no_additional_stop_requests(self):
        service = _ObservedService()
        shutdown = ShutdownCoordinator(service)
        shutdown.request()
        for values in ({"timeout_seconds": True}, {"timeout_seconds": -1},
                       {"timeout_seconds": 61}, {"timeout_seconds": float("nan")},
                       {"poll_seconds": 0}, {"poll_seconds": float("inf")}):
            with self.subTest(values=values):
                before = len(service.reasons)
                with self.assertRaisesRegex(ValueError, "SHUTDOWN_TIMING_REQUIRED"):
                    shutdown.pending_owner.retry(**values)
                self.assertEqual(len(service.reasons), before)

    def test_shutdown_incomplete_keeps_legacy_constructor_and_typed_owner(self):
        shutdown = ShutdownCoordinator(_ObservedService())
        observation = shutdown.request()
        legacy = ShutdownIncomplete(observation)
        self.assertIs(legacy.observation, observation)
        self.assertIsNone(legacy.pending_owner)
        typed = ShutdownIncomplete(observation, pending_owner=shutdown.pending_owner)
        self.assertIs(typed.pending_owner, shutdown.pending_owner)
        self.assertIs(typed.observation, observation)


class LauncherInterruptionTests(unittest.TestCase):
    def bounded_drain(self, original):
        def bounded(shutdown):
            return original(shutdown, timeout_seconds=0)
        return bounded

    def test_primary_survives_every_failing_add_note_and_exports_custody(self):
        for note_error in (RuntimeError, KeyboardInterrupt, SystemExit):
            with self.subTest(note_error=note_error.__name__):
                class Primary(KeyboardInterrupt):
                    def add_note(self, note):
                        raise note_error("controlled note failure")
                primary = Primary("controlled application failure")
                service = _ObservedService()
                original = ShutdownCoordinator.drain
                with patch.object(ShutdownCoordinator, "drain", new=self.bounded_drain(original)):
                    with self.assertRaises(Primary) as caught:
                        existing.launcher()._run_owned_ui(service, lambda shutdown: _ui(primary=primary))
                self.assertIs(caught.exception, primary)
                incomplete = primary.shutdown_incomplete
                self.assertIsInstance(incomplete, ShutdownIncomplete)
                owner = incomplete.pending_owner
                self.assertIsInstance(owner, PendingShutdownOwner)
                self.assertIs(owner.service, service)
                self.assertIs(incomplete.observation, owner.observation)
                self.assertFalse(incomplete.observation.workers_stopped)
                service.observe_exit()
                self.assertTrue(owner.retry(timeout_seconds=0).workers_stopped)

    def test_normal_return_with_incomplete_cleanup_exports_typed_owner(self):
        service = _ObservedService()
        original = ShutdownCoordinator.drain
        with patch.object(ShutdownCoordinator, "drain", new=self.bounded_drain(original)):
            with self.assertRaises(ShutdownIncomplete) as caught:
                existing.launcher()._run_owned_ui(service, lambda shutdown: _ui())
        owner = caught.exception.pending_owner
        self.assertIsInstance(owner, PendingShutdownOwner)
        self.assertIs(owner.service, service)
        self.assertFalse(caught.exception.observation.workers_stopped)
        service.observe_exit()
        self.assertTrue(owner.retry(timeout_seconds=0).workers_stopped)

    def test_cleanup_interruption_is_primary_without_an_application_error(self):
        for interruption in (KeyboardInterrupt, SystemExit):
            with self.subTest(interruption=interruption.__name__):
                service = _ObservedService()
                primary = interruption("controlled cleanup interruption")
                service.stop_failures = [primary]
                original = ShutdownCoordinator.drain
                with patch.object(ShutdownCoordinator, "drain", new=self.bounded_drain(original)):
                    with self.assertRaises(interruption) as caught:
                        existing.launcher()._run_owned_ui(service, lambda shutdown: _ui())
                self.assertIs(caught.exception, primary)
                self.assertIsInstance(primary.shutdown_incomplete, ShutdownIncomplete)
                self.assertIs(primary.shutdown_incomplete.pending_owner.service, service)
                self.assertFalse(primary.shutdown_incomplete.observation.workers_stopped)

    def test_application_primary_survives_a_different_cleanup_interruption(self):
        service = _ObservedService()
        primary = RuntimeError("controlled application failure")
        service.stop_failures = [SystemExit(83)]
        original = ShutdownCoordinator.drain
        with patch.object(ShutdownCoordinator, "drain", new=self.bounded_drain(original)):
            with self.assertRaises(RuntimeError) as caught:
                existing.launcher()._run_owned_ui(service, lambda shutdown: _ui(primary=primary))
        self.assertIs(caught.exception, primary)
        self.assertIsInstance(primary.shutdown_incomplete, ShutdownIncomplete)
        self.assertIs(primary.shutdown_incomplete.pending_owner.service, service)
        self.assertFalse(primary.shutdown_incomplete.observation.workers_stopped)


class TaskSessionInterruptionTests(unittest.TestCase):
    setUp = existing.ContextShutdownTests.setUp
    tearDown = existing.ContextShutdownTests.tearDown
    until = existing.ContextShutdownTests.until
    held = existing.ContextShutdownTests.held

    def setup_session(self):
        result = existing.ContextShutdownTests.setup_session(self)
        _, service, _, _, _ = result
        original = service.request_stop

        def retain_observed_exit(reason_ref="reason:operator-stop"):
            # This is a controlled exit oracle. The real OwnedService also
            # keeps an observed, fully settled lifetime stopped on repeat Stop.
            if service.state == "STOPPED":
                return service.poll()
            return original(reason_ref)

        service.request_stop = retain_observed_exit
        return result

    def test_real_session_stop_interruption_keeps_cancelled_worker_owned(self):
        for interruption in (KeyboardInterrupt, SystemExit):
            with self.subTest(interruption=interruption.__name__):
                session, service, fixture, ports = self.held()
                before = fixture.cell(session.task_id), session.draft
                worker = session._context_job["thread"]
                shutdown = ShutdownCoordinator(service, session)
                primary = interruption("controlled service-stop interruption")
                original, attempted = service.request_stop, []

                def interrupted_once(reason_ref="reason:operator-stop"):
                    attempted.append(reason_ref)
                    if len(attempted) == 1:
                        raise primary
                    return original(reason_ref)

                with patch.object(service, "request_stop", new=interrupted_once):
                    with self.assertRaises(interruption) as caught:
                        shutdown.request()
                self.assertIs(caught.exception, primary)
                self.assertEqual(len(attempted), 2)
                self.assertTrue(session._context_job["cancel"].is_set())
                self.assertTrue(worker.is_alive())
                self.assertIs(shutdown.pending_owner.session, session)
                self.assertFalse(shutdown.observation.workers_stopped)
                service.finish_stop()
                self.assertFalse(shutdown.pending_owner.retry(timeout_seconds=0).workers_stopped)
                self.assertEqual((fixture.cell(session.task_id), session.draft), before)
                ports.render_release.set()
                self.assertTrue(shutdown.pending_owner.retry(timeout_seconds=3).workers_stopped)
                self.assertFalse(worker.is_alive())
                self.assertEqual(session.context_status, "CANCELLED")
                self.assertEqual((fixture.cell(session.task_id), session.draft), before)

    def test_real_session_poll_interruption_retains_worker_and_actual_stop_fallback(self):
        for interruption in (KeyboardInterrupt, SystemExit):
            with self.subTest(interruption=interruption.__name__):
                session, service, fixture, ports = self.held()
                before = fixture.cell(session.task_id), session.draft
                worker = session._context_job["thread"]
                shutdown = ShutdownCoordinator(service, session)
                shutdown.request()
                primary = interruption("controlled session-poll interruption")
                original, attempted = service.poll, []

                def interrupted_once():
                    attempted.append(True)
                    if len(attempted) == 1:
                        raise primary
                    return original()

                with patch.object(service, "poll", new=interrupted_once):
                    with self.assertRaises(interruption) as caught:
                        shutdown.advance()
                self.assertIs(caught.exception, primary)
                self.assertEqual(service.stop_calls, 2)
                self.assertFalse(shutdown.observation.workers_stopped)
                self.assertTrue(session._context_job["cancel"].is_set())
                self.assertTrue(worker.is_alive())
                self.assertIs(shutdown.pending_owner.session, session)
                ports.render_release.set()
                service.finish_stop()
                self.assertTrue(shutdown.pending_owner.retry(timeout_seconds=3).workers_stopped)
                self.assertFalse(worker.is_alive())
                self.assertEqual((fixture.cell(session.task_id), session.draft), before)

    def test_launcher_handoff_retains_real_worker_after_traceback_release_and_gc(self):
        session, service, fixture, ports = self.held()
        before = fixture.cell(session.task_id), session.draft
        worker = session._context_job["thread"]
        session_ref, service_ref, worker_ref = weakref.ref(session), weakref.ref(service), weakref.ref(worker)
        owner = None
        original = ShutdownCoordinator.drain

        def setup(shutdown):
            shutdown.capture_session(session)
            return _ui()

        def bounded(shutdown):
            shutdown.request()
            service.finish_stop()
            return original(shutdown, timeout_seconds=0)

        try:
            with patch.object(ShutdownCoordinator, "drain", new=bounded):
                try:
                    existing.launcher()._run_owned_ui(service, setup)
                except ShutdownIncomplete as incomplete:
                    owner = incomplete.pending_owner
                    self.assertIsInstance(owner, PendingShutdownOwner)
                    incomplete.__traceback__ = None
                else:
                    self.fail("a held compiler cannot be reported stopped")
            self.sessions.remove((session, service))
            del setup, bounded, session, service, worker
            gc.collect()
            self.assertIsNotNone(session_ref())
            self.assertIsNotNone(service_ref())
            self.assertIs(owner.session, session_ref())
            self.assertIs(owner.service, service_ref())
            observed_worker = worker_ref()
            self.assertIsNotNone(observed_worker)
            self.assertTrue(observed_worker.is_alive())
            self.assertFalse(owner.observation.workers_stopped)
            self.assertTrue(owner.session._context_job["cancel"].is_set())
            ports.render_release.set()
            observed = owner.retry(timeout_seconds=3)
            self.assertTrue(observed.workers_stopped)
            self.assertFalse(observed_worker.is_alive())
            self.assertEqual(owner.session.context_status, "CANCELLED")
            self.assertEqual((fixture.cell(owner.session.task_id), owner.session.draft), before)
        finally:
            ports.render_release.set()
            retained_session, retained_service = session_ref(), service_ref()
            if retained_session is not None and retained_service is not None:
                if (retained_session, retained_service) not in self.sessions:
                    self.sessions.append((retained_session, retained_service))


class NativeInterruptionTests(native._ServiceTestCase):
    empty_service = intake.NativeContextIntakeTests.empty_service
    task_call = intake.NativeContextIntakeTests.task_call
    response_revision = intake.NativeContextIntakeTests.response_revision
    session_fixture = intake.NativeContextIntakeTests.session_fixture
    durable_read_cut = intake.NativeContextIntakeTests.durable_read_cut

    def test_actual_native_session_interruption_stops_processes_and_retains_held_compiler(self):
        session, service, root, ports, _, _ = self.session_fixture()
        before = self.durable_read_cut(root)
        import threading
        ports.render_entered, ports.render_release = threading.Event(), threading.Event()
        session.begin_context_preview(output_tokens=8)
        self.until(lambda: (session.poll(), ports.render_entered.is_set())[1])
        worker = session._context_job["thread"]
        shutdown = ShutdownCoordinator(service, session)
        primary = KeyboardInterrupt("controlled interruption before native termination")
        original, attempted = service.request_stop, []

        def interrupted_once(reason_ref="reason:operator-stop"):
            attempted.append(reason_ref)
            if len(attempted) == 1:
                raise primary
            return original(reason_ref)

        try:
            with patch.object(service, "request_stop", new=interrupted_once):
                with self.assertRaises(KeyboardInterrupt) as caught:
                    shutdown.request()
            self.assertIs(caught.exception, primary)
            self.assertEqual(len(attempted), 2)
            self.assertTrue(session._context_job["cancel"].is_set())
            self.assertTrue(worker.is_alive())
            self.assertFalse(shutdown.pending_owner.retry(timeout_seconds=0).workers_stopped)
            ports.render_release.set()
            self.assertTrue(shutdown.pending_owner.retry(timeout_seconds=15).workers_stopped)
            self.assertFalse(worker.is_alive())
            self.assertEqual(session.context_status, "CANCELLED")
            for channel in (service._client, service._service):
                self.assertTrue(channel.observed_exited())
            self.assertEqual(service.poll()["authority"], "CLOSED")
            self.assertEqual(self.durable_read_cut(root), before)
        finally:
            ports.render_release.set()
            self.until(lambda: (session.poll(), not session.context_busy)[1])

    def test_explicit_retry_reaches_actual_native_termination_after_controlled_failure(self):
        service, root = self.empty_service()
        before = self.durable_read_cut(root)
        channels = service._client, service._service
        attempted = {id(channel): [] for channel in channels}
        shutdown = ShutdownCoordinator(service)
        with ExitStack() as patches:
            for channel in channels:
                original = channel.terminate
                counts = attempted[id(channel)]

                def fail_once(exit_code=124, original=original, counts=counts):
                    counts.append(exit_code)
                    if len(counts) == 1:
                        raise ContractError("CONTROL_TERMINATION_FIXTURE_DENIED")
                    return original(exit_code)

                patches.enter_context(patch.object(channel, "terminate", new=fail_once))
            observed = shutdown.request()
            self.assertFalse(observed.workers_stopped)
            self.assertTrue(all(channel.process.poll() is None for channel in channels))
            self.assertFalse(shutdown.advance().workers_stopped)
            self.assertEqual([len(values) for values in attempted.values()], [1, 1])
            self.assertTrue(shutdown.pending_owner.retry(timeout_seconds=15).workers_stopped)
            self.assertEqual([len(values) for values in attempted.values()], [2, 2])
        for channel in channels:
            self.assertTrue(channel.observed_exited())
        self.assertEqual(service.poll()["authority"], "CLOSED")
        self.assertEqual(self.durable_read_cut(root), before)
