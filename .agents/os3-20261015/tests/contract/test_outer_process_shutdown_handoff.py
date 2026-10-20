"""P00/D01 outer-process custody regressions.

The launcher record is deliberately tested as a restart fence rather than a
surviving owner.  Controlled cases exercise the actual coordinator/launcher
calls.  The native case uses the existing disposable Windows owned-service
fixture and observes its exact child lifetimes before terminalizing the record.
"""
import importlib.util
from pathlib import Path
import subprocess
import sys
import threading
import unittest
import uuid
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ceta.application.lifecycle import (
    LauncherCustodyIncomplete, LauncherShutdownCustody, ShutdownCoordinator,
    ShutdownObservation,
)
import test_owned_service as native


def launcher():
    spec = importlib.util.spec_from_file_location(
        "outer_process_shutdown_launcher_fixture", ROOT / "tools/ceta_operator.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def profile_directory():
    root = ROOT / ".agents/fixtures/outer-process-custody-00" / uuid.uuid4().hex
    root.mkdir(parents=True, exist_ok=False)
    return root


class _StoppingService:
    """A controlled port whose request and observed exit remain distinct."""

    def __init__(self):
        self.state = "READY"
        self.stop_calls = 0
        self._settlement_witness = object()

    def request_stop(self, reason="reason:application-exit"):
        self.stop_calls += 1
        if self.state != "STOPPED":
            self.state = "STOPPING"
        return self.poll()

    def start(self):
        pass

    def poll(self):
        return {"state": self.state, "detail": "Controlled retained lifetime."}

    def observe_exit(self):
        self.state = "STOPPED"

    def shutdown_settlement_witness(self):
        # Controlled stand-in for the real OwnedService opaque native witness.
        # It models no retained owner only after the test has explicitly
        # observed exit; raw STOPPED descriptions never return this object.
        return self._settlement_witness if self.state == "STOPPED" else None


class _LatePublishingStartService:
    """Start raises after offering a worker that can publish after Stop begins."""

    def __init__(self):
        self.state = "STOPPED"
        self.stop_requested = threading.Event()
        self.allow_retirement = threading.Event()
        self.published = threading.Event()
        self.worker = None
        self._settlement_witness = object()

    def start(self):
        def publish_late():
            self.stop_requested.wait(3)
            self.published.set()
            self.allow_retirement.wait(3)
            self.state = "STOPPED"

        self.state = "STARTING"
        self.worker = threading.Thread(target=publish_late, name="late-publication", daemon=True)
        self.worker.start()
        raise RuntimeError("CONTROL_START_UNCERTAIN")

    def request_stop(self, reason="reason:application-exit"):
        self.stop_requested.set()
        if self.state != "STOPPED":
            self.state = "STOPPING"
        return self.poll()

    def poll(self):
        if self.worker is not None and not self.worker.is_alive() and self.published.is_set():
            self.state = "STOPPED"
        return {"state": self.state, "detail": "Controlled late publication."}

    def shutdown_settlement_witness(self):
        if (self.state == "STOPPED" and self.published.is_set()
                and self.worker is not None and not self.worker.is_alive()):
            return self._settlement_witness
        return None


class LauncherRecordTests(unittest.TestCase):
    def test_constructor_absence_is_pending_not_a_no_entry_proof(self):
        root = profile_directory()
        custody = LauncherShutdownCustody(root)
        try:
            record = custody.reserve_launch()
            self.assertEqual(record["state"], "PENDING")
            self.assertEqual(record["launch_phase"], "CONSTRUCTOR_UNOBSERVED")
            self.assertEqual(record["publication_state"], "UNOBSERVED")
        finally:
            custody.close()

        restart = LauncherShutdownCustody(root)
        with self.assertRaises(LauncherCustodyIncomplete) as caught:
            restart.reserve_launch()
        self.assertEqual(caught.exception.record["state"], "PENDING")
        self.assertEqual(caught.exception.record["launch_phase"], "CONSTRUCTOR_UNOBSERVED")

    def test_raw_terminal_observations_cannot_clear_pending_or_admit_replacement(self):
        """A descriptive dataclass is never custody authority, even if complete-looking."""
        root = profile_directory()
        custody = LauncherShutdownCustody(root)
        custody.reserve_launch()
        raw_values = (
            ShutdownObservation("STOPPED", False, None, None, False, ()),
            ShutdownObservation("STOPPED", True, "STOPPED", "STOPPED", False, (),
                                poll_attempts=1),
        )
        try:
            for raw in raw_values:
                with self.subTest(raw=raw):
                    with self.assertRaisesRegex(ValueError, "LAUNCHER_CUSTODY_TERMINAL_PROOF_REQUIRED"):
                        custody.mark_termination_observed(raw)
                    self.assertEqual(custody.record["state"], "PENDING")
                    self.assertFalse(custody.terminal_observed)
        finally:
            custody.close()

        replacement = LauncherShutdownCustody(root)
        with self.assertRaises(LauncherCustodyIncomplete):
            replacement.reserve_launch()

    def test_duck_typed_service_cannot_mint_terminal_proof_or_admit_replacement(self):
        """A stable method result is not native-retirement custody proof."""
        root = profile_directory()
        custody = LauncherShutdownCustody(root)
        custody.reserve_launch()
        service = _StoppingService()
        try:
            service.observe_exit()
            shutdown = ShutdownCoordinator(service, custody_binding=custody._coordinator_binding())
            self.assertTrue(shutdown.drain(timeout_seconds=0).workers_stopped)
            with self.assertRaisesRegex(RuntimeError, "SHUTDOWN_NATIVE_RETIREMENT_WITNESS_REQUIRED"):
                shutdown.terminal_settlement()
            self.assertEqual(custody.record["state"], "PENDING")
            self.assertFalse(custody.terminal_observed)
        finally:
            custody.close()

        replacement = LauncherShutdownCustody(root)
        try:
            with self.assertRaises(LauncherCustodyIncomplete):
                replacement.reserve_launch()
        finally:
            replacement.close()

    def test_impostor_stable_witness_is_not_accepted_by_identity_alone(self):
        """Reproduce the hostile duck-typed service/witness bypass attempt."""
        root = profile_directory()
        custody = LauncherShutdownCustody(root)
        custody.reserve_launch()

        class ImpostorService:
            def __init__(self):
                self._witness = object()

            def request_stop(self, _reason="reason:application-exit"):
                return self.poll()

            def poll(self):
                return {"state": "STOPPED", "detail": "impostor reports complete"}

            def shutdown_settlement_witness(self):
                return self._witness

        service = ImpostorService()
        try:
            shutdown = ShutdownCoordinator(service, custody_binding=custody._coordinator_binding())
            self.assertTrue(shutdown.drain(timeout_seconds=0).workers_stopped)
            witness = service.shutdown_settlement_witness()
            self.assertIs(witness, service.shutdown_settlement_witness())
            with self.assertRaisesRegex(RuntimeError, "SHUTDOWN_NATIVE_RETIREMENT_WITNESS_REQUIRED"):
                shutdown.terminal_settlement()
            self.assertEqual(custody.record["state"], "PENDING")
            self.assertFalse(custody.terminal_observed)
        finally:
            custody.close()

    def test_pending_record_is_not_an_outer_exit_acknowledgement(self):
        root = profile_directory()
        custody = LauncherShutdownCustody(root)
        custody.reserve_launch()
        service = _StoppingService()
        shutdown = ShutdownCoordinator(service, custody_binding=custody._coordinator_binding())
        observed = shutdown.drain(timeout_seconds=0)
        self.assertFalse(observed.workers_stopped)
        custody.mark_unresolved(observed)

        module = launcher()
        try:
            incomplete = module.ShutdownIncomplete(observed, shutdown.pending_owner)
            self.assertFalse(module._attempt_outer_custody_settlement(
                incomplete, custody, timeout_seconds=0))
            self.assertEqual(custody.record["state"], "PENDING")
            self.assertEqual(custody.record["launch_phase"], "STOPPING")

            service.observe_exit()
            self.assertFalse(module._attempt_outer_custody_settlement(
                incomplete, custody, timeout_seconds=1))
            self.assertFalse(custody.terminal_observed)
            self.assertEqual(custody.record["state"], "PENDING")
        finally:
            custody.close()

    def test_secondary_interrupt_cannot_release_outer_custody_before_retirement(self):
        root = profile_directory()
        custody = LauncherShutdownCustody(root)
        custody.reserve_launch()
        service = _StoppingService()
        shutdown = ShutdownCoordinator(service, custody_binding=custody._coordinator_binding())
        observed = shutdown.drain(timeout_seconds=0)
        custody.mark_unresolved(observed)
        module = launcher()
        sleeps = []
        attempts = []

        def pending_then_settled(_incomplete, _custody):
            attempts.append(True)
            return len(attempts) == 2

        def interrupted_sleep(seconds):
            sleeps.append(seconds)
            self.assertEqual(len(sleeps), 1)
            raise KeyboardInterrupt("CONTROL_SECONDARY_INTERRUPTION")

        try:
            incomplete = module.ShutdownIncomplete(observed, shutdown.pending_owner)
            # This isolates the outer-loop interruption boundary.  Concrete
            # proof minting is covered by the native OwnedService tests below;
            # a duck-typed fixture must never stand in for that integration.
            with patch.object(module, "_attempt_outer_custody_settlement", new=pending_then_settled), \
                 patch.object(module.time, "sleep", new=interrupted_sleep):
                module._hold_outer_custody_until_settled(incomplete, custody)
            self.assertEqual(sleeps, [0.05])
            self.assertEqual(attempts, [True, True])
            self.assertFalse(custody.terminal_observed)
        finally:
            custody.close()

    def test_retry_interruption_cannot_release_outer_custody_before_retirement(self):
        """A signal inside PendingShutdownOwner.retry leaves durable custody pending."""
        for interruption in (KeyboardInterrupt, SystemExit):
            with self.subTest(interruption=interruption.__name__):
                root = profile_directory()
                custody = LauncherShutdownCustody(root)
                custody.reserve_launch()
                service = _StoppingService()
                shutdown = ShutdownCoordinator(service, custody_binding=custody._coordinator_binding())
                observed = shutdown.drain(timeout_seconds=0)
                custody.mark_unresolved(observed)
                module = launcher()
                calls = []

                def interrupt_retry(owner, **_kwargs):
                    calls.append(owner)
                    raise interruption("CONTROL_RETRY_INTERRUPTION")

                try:
                    incomplete = module.ShutdownIncomplete(observed, shutdown.pending_owner)
                    with patch.object(type(shutdown.pending_owner), "retry", new=interrupt_retry):
                        self.assertFalse(module._attempt_outer_custody_settlement(
                            incomplete, custody, timeout_seconds=0))
                    self.assertEqual(calls, [shutdown.pending_owner])
                    self.assertEqual(custody.record["state"], "PENDING")
                    self.assertFalse(custody.terminal_observed)
                finally:
                    custody.close()

    def test_durable_handoff_failure_cannot_replace_primary_interruption(self):
        service = _StoppingService()
        module = launcher()
        original_drain = ShutdownCoordinator.drain
        primary = KeyboardInterrupt("CONTROL_PRIMARY_INTERRUPTION")

        class FailingCustody:
            def mark_start_requested(self):
                pass

            def mark_start_returned(self):
                pass

            def mark_termination_observed(self, _observation):
                pass

            def mark_unresolved(self, _observation):
                raise RuntimeError("CONTROL_DURABLE_HANDOFF_FAILURE")

        class Application:
            def exec(self):
                raise primary

        class Window:
            def show(self):
                pass

        def bounded_drain(owner, **_kwargs):
            return original_drain(owner, timeout_seconds=0, poll_seconds=0.001)

        with patch.object(ShutdownCoordinator, "drain", new=bounded_drain):
            with self.assertRaises(KeyboardInterrupt) as caught:
                module._run_owned_ui(service, lambda owner: (Application(), Window()),
                                     custody=FailingCustody())
        self.assertIs(caught.exception, primary)
        incomplete = primary.shutdown_incomplete
        self.assertIsInstance(incomplete, module.ShutdownIncomplete)
        self.assertIsInstance(incomplete.durable_custody_error, RuntimeError)
        self.assertFalse(incomplete.observation.workers_stopped)

    def test_start_uncertainty_and_late_publication_remain_pending_until_owner_observes_exit(self):
        root = profile_directory()
        custody = LauncherShutdownCustody(root)
        service = _LatePublishingStartService()
        module = launcher()
        original_drain = ShutdownCoordinator.drain

        class Application:
            def exec(self):
                return 0

        class Window:
            def show(self):
                pass

        def bounded_drain(owner, **_kwargs):
            return original_drain(owner, timeout_seconds=0, poll_seconds=0.001)

        custody.reserve_launch()
        primary = None
        try:
            with patch.object(ShutdownCoordinator, "drain", new=bounded_drain):
                with self.assertRaisesRegex(RuntimeError, "CONTROL_START_UNCERTAIN") as caught:
                    module._run_owned_ui(service, lambda owner: (Application(), Window()), custody=custody)
            primary = caught.exception
            incomplete = primary.shutdown_incomplete
            self.assertFalse(incomplete.observation.workers_stopped)
            self.assertTrue(service.stop_requested.wait(1))
            self.assertTrue(service.published.wait(1), "late worker never reached publication boundary")
            self.assertTrue(service.worker.is_alive())
            self.assertEqual(custody.record["state"], "PENDING")
            self.assertEqual(custody.record["publication_state"], "POSSIBLE_PUBLICATION")

            # Simulate the original outer process dying after preserving the
            # PENDING record.  A replacement launcher has no licence to start.
            custody.close()
            restart = LauncherShutdownCustody(root)
            with self.assertRaises(LauncherCustodyIncomplete):
                restart.reserve_launch()

            service.allow_retirement.set()
            observed = incomplete.pending_owner.retry(timeout_seconds=3)
            self.assertTrue(observed.workers_stopped)
            self.assertFalse(service.worker.is_alive())
            custody.acquire()
            # This synthetic late-publisher remains a structural test double.
            # Even after its worker exits it cannot certify native retirement
            # to a durable launcher record; a real OwnedService owns that
            # proof path in the native tests below.
            with self.assertRaisesRegex(RuntimeError, "SHUTDOWN_NATIVE_RETIREMENT_WITNESS_REQUIRED"):
                incomplete.pending_owner.coordinator.terminal_settlement()
            self.assertEqual(custody.record["state"], "PENDING")
            self.assertFalse(custody.terminal_observed)
        finally:
            service.allow_retirement.set()
            if service.worker is not None:
                service.worker.join(timeout=3)
            custody.close()

    def test_subprocess_crash_record_blocks_main_before_service_construction(self):
        root = profile_directory()
        source = str(ROOT / "src")
        crash = "\n".join((
            "from pathlib import Path",
            "import os, sys",
            "sys.path.insert(0, sys.argv[2])",
            "from ceta.application.lifecycle import LauncherShutdownCustody",
            "custody = LauncherShutdownCustody(Path(sys.argv[1]))",
            "custody.reserve_launch()",
            "custody.mark_start_requested()",
            "os._exit(0)",
        ))
        first = subprocess.run([sys.executable, "-B", "-c", crash, str(root), source],
                               capture_output=True, text=True, timeout=20, check=False)
        self.assertEqual(first.returncode, 0, first.stderr)

        restart = "\n".join((
            "from pathlib import Path",
            "import sys",
            "sys.path.insert(0, sys.argv[2])",
            "from ceta.application.lifecycle import LauncherCustodyIncomplete, LauncherShutdownCustody",
            "try:",
            "    LauncherShutdownCustody(Path(sys.argv[1])).reserve_launch()",
            "except LauncherCustodyIncomplete as error:",
            "    print(error.record['state'] + ':' + error.record['publication_state'])",
            "    raise SystemExit(23)",
            "raise SystemExit(0)",
        ))
        second = subprocess.run([sys.executable, "-B", "-c", restart, str(root), source],
                                capture_output=True, text=True, timeout=20, check=False)
        self.assertEqual(second.returncode, 23, second.stderr)
        self.assertEqual(second.stdout.strip(), "PENDING:START_REQUESTED_UNOBSERVED")

        module = launcher()
        with patch.object(module, "OwnedService") as owned, \
             patch.object(sys, "argv", ["ceta_operator.py", "--profile", str(root)]):
            with self.assertRaises(LauncherCustodyIncomplete) as caught:
                module.main()
        self.assertEqual(caught.exception.record["state"], "PENDING")
        self.assertEqual(caught.exception.record["publication_state"], "START_REQUESTED_UNOBSERVED")
        owned.assert_not_called()

    def test_live_holder_blocks_second_launcher_before_owned_service_construction(self):
        """The second process must fail at the live custody lock, before composition."""
        root = profile_directory()
        source = str(ROOT / "src")
        holder = "\n".join((
            "from pathlib import Path",
            "import sys, time",
            "sys.path.insert(0, sys.argv[2])",
            "from ceta.application.lifecycle import LauncherShutdownCustody",
            "custody = LauncherShutdownCustody(Path(sys.argv[1]))",
            "custody.reserve_launch()",
            "print('RESERVED', flush=True)",
            "time.sleep(30)",
        ))
        contender = "\n".join((
            "from pathlib import Path",
            "import importlib.util, sys",
            "root, source, tool = map(Path, sys.argv[1:4])",
            "spec = importlib.util.spec_from_file_location('second_launcher_fixture', tool)",
            "module = importlib.util.module_from_spec(spec)",
            "spec.loader.exec_module(module)",
            "def forbidden(*_args, **_kwargs):",
            "    print('OWNED_SERVICE_CALLED', flush=True)",
            "    raise AssertionError('owned service construction must remain unreachable')",
            "module.OwnedService = forbidden",
            "sys.argv = ['ceta_operator.py', '--profile', str(root)]",
            "try:",
            "    module.main()",
            "except RuntimeError as error:",
            "    print(type(error).__name__ + ':' + str(error), flush=True)",
            "    raise SystemExit(23)",
            "raise SystemExit(0)",
        ))
        process = subprocess.Popen([sys.executable, "-B", "-c", holder, str(root), source],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(process.stdout.readline().strip(), "RESERVED")
            second = subprocess.run(
                [sys.executable, "-B", "-c", contender, str(root), source,
                 str(ROOT / "tools/ceta_operator.py")],
                capture_output=True, text=True, timeout=20, check=False)
            self.assertEqual(second.returncode, 23, second.stderr)
            self.assertEqual(second.stdout.strip(), "RuntimeError:LAUNCHER_CUSTODY_LOCK_UNAVAILABLE")
            self.assertNotIn("OWNED_SERVICE_CALLED", second.stdout)
        finally:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=20)
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()

    def test_main_routes_constructor_uncertainty_to_nonexiting_hold(self):
        root = profile_directory()
        module = launcher()

        class HoldReached(RuntimeError):
            pass

        with patch.object(module, "OwnedService", side_effect=RuntimeError("CONTROL_CONSTRUCTOR_UNCERTAIN")) as owned, \
             patch.object(module, "_hold_constructor_uncertainty", side_effect=HoldReached("hold reached")), \
             patch.object(sys, "argv", ["ceta_operator.py", "--profile", str(root)]):
            with self.assertRaises(HoldReached):
                module.main()
        owned.assert_called_once()
        record = LauncherShutdownCustody(root).record
        self.assertEqual(record["state"], "PENDING")
        self.assertEqual(record["launch_phase"], "CONSTRUCTOR_UNOBSERVED")
        self.assertIn("SERVICE_CONSTRUCTION_UNOBSERVED", record["diagnostic_codes"])

    def test_main_preserves_primary_when_final_custody_close_raises(self):
        """Lock-release diagnostics cannot replace a primary BaseException."""
        root = profile_directory()
        module = launcher()
        for primary_type in (RuntimeError, KeyboardInterrupt, SystemExit):
            for close_error in (OSError("CONTROL_CLOSE"), KeyboardInterrupt("CONTROL_CLOSE"),
                                SystemExit("CONTROL_CLOSE")):
                with self.subTest(primary=primary_type.__name__, close_error=type(close_error).__name__):
                    primary = primary_type("CONTROL_PRIMARY")

                    class FailingCloseCustody:
                        def __init__(self):
                            self.reserved = self.closed = False

                        def reserve_launch(self):
                            self.reserved = True

                        def close(self):
                            self.closed = True
                            raise close_error

                    custody = FailingCloseCustody()
                    with patch.object(module, "LauncherShutdownCustody", return_value=custody), \
                         patch.object(module, "OwnedService", return_value=object()), \
                         patch.object(module, "_run_owned_ui", side_effect=primary), \
                         patch.object(sys, "argv", ["ceta_operator.py", "--profile", str(root)]):
                        with self.assertRaises(primary_type) as caught:
                            module.main()
                    self.assertIs(caught.exception, primary)
                    self.assertIs(primary.launcher_custody_close_error, close_error)
                    self.assertTrue(custody.reserved)
                    self.assertTrue(custody.closed)

    def test_main_propagates_final_custody_close_without_primary(self):
        root = profile_directory()
        module = launcher()
        close_error = OSError("CONTROL_CLOSE_ONLY")

        class FailingCloseCustody:
            def reserve_launch(self):
                pass

            def close(self):
                raise close_error

        with patch.object(module, "LauncherShutdownCustody", return_value=FailingCloseCustody()), \
             patch.object(module, "OwnedService", return_value=object()), \
             patch.object(module, "_run_owned_ui", return_value=0), \
             patch.object(sys, "argv", ["ceta_operator.py", "--profile", str(root)]):
            with self.assertRaises(OSError) as caught:
                module.main()
        self.assertIs(caught.exception, close_error)

    def test_final_custody_close_diagnostic_survives_mutating_primary_add_note(self):
        root = profile_directory()
        module = launcher()
        close_error = OSError("CONTROL_CLOSE")

        class MutatingPrimary(RuntimeError):
            def add_note(self, _note):
                BaseException.__dict__["__dict__"].__get__(self).clear()

        class FailingCloseCustody:
            def reserve_launch(self):
                pass

            def close(self):
                raise close_error

        primary = MutatingPrimary("CONTROL_PRIMARY")
        with patch.object(module, "LauncherShutdownCustody", return_value=FailingCloseCustody()), \
             patch.object(module, "OwnedService", return_value=object()), \
             patch.object(module, "_run_owned_ui", side_effect=primary), \
             patch.object(sys, "argv", ["ceta_operator.py", "--profile", str(root)]):
            with self.assertRaises(MutatingPrimary) as caught:
                module.main()
        self.assertIs(caught.exception, primary)
        self.assertIs(primary.launcher_custody_close_error, close_error)


class NativeRetirementRecordTests(native._ServiceTestCase):
    """The terminal marker requires actual disposable Windows retirement."""

    def test_actual_native_proof_is_bound_to_its_own_live_reservation(self):
        fixture = self.fixture()
        service = self.fixture_service(fixture)
        first = LauncherShutdownCustody(fixture.root)
        second = LauncherShutdownCustody(self.directory())
        first.reserve_launch()
        second.reserve_launch()
        try:
            first.mark_start_requested()
            service.start()

            def ready():
                observed = service.poll()
                if observed["state"] == "RECOVERING":
                    self.fail("service startup denied: " + observed["detail"])
                return observed if observed["state"] == "READY" else None

            self.until(ready, explanation="real owned service never reported READY")
            first.mark_start_returned()
            shutdown = ShutdownCoordinator(service, custody_binding=first._coordinator_binding())
            self.assertTrue(shutdown.drain(timeout_seconds=15).workers_stopped)
            proof = shutdown.terminal_settlement()

            with self.assertRaisesRegex(ValueError, "LAUNCHER_CUSTODY_TERMINAL_PROOF_REQUIRED"):
                second.mark_termination_observed(proof)
            self.assertEqual(second.record["state"], "PENDING")
            self.assertFalse(second.terminal_observed)

            first.mark_termination_observed(proof)
            self.assertTrue(first.terminal_observed)
            self.assertEqual(first.record["state"], "SETTLEMENT_OBSERVED")
        finally:
            first.close()
            second.close()

    def test_actual_native_retirement_is_required_before_terminal_record(self):
        fixture = self.fixture()
        service = self.fixture_service(fixture)
        custody = LauncherShutdownCustody(fixture.root)
        custody.reserve_launch()
        try:
            custody.mark_start_requested()
            service.start()

            def ready():
                observed = service.poll()
                if observed["state"] == "RECOVERING":
                    self.fail("service startup denied: " + observed["detail"])
                return observed if observed["state"] == "READY" else None

            self.until(ready, explanation="real owned service never reported READY")
            custody.mark_start_returned()
            shutdown = ShutdownCoordinator(service, custody_binding=custody._coordinator_binding())
            observed = shutdown.drain(timeout_seconds=15)
            self.assertTrue(observed.workers_stopped)
            for channel in (service._client, service._service):
                self.assertTrue(channel.observed_exited())
            custody.mark_termination_observed(shutdown.terminal_settlement())
            record = custody.record
            self.assertEqual(record["state"], "SETTLEMENT_OBSERVED")
            self.assertEqual(record["publication_state"], "SETTLEMENT_OBSERVED")
            self.assertEqual(record["observation"]["state"], "STOPPED")
        finally:
            custody.close()

