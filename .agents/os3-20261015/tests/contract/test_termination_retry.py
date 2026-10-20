"""P00 item 2: explicit bounded native termination and observed custody.

Source oracles: r6 P00 1-4/7; SPEC-08 REQ-08-01/03/04; SPEC-30
REQ-30-01/02/03. Every case uses actual disposable Windows OwnedService
processes and owned native handles. Faults/no-op requests/publication barriers
are controlled injections, not reproduced OS faults. No model, protected-domain
fence, outer-interpreter custody, visible UI, installed or full B-case claim.
"""
from contextlib import ExitStack
from dataclasses import FrozenInstanceError
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.application.lifecycle import ShutdownCoordinator
from ceta.composition.owned_service import OwnedService
from ceta.contracts.wire import ContractError
from ceta.supervisor.service import OwnedChannel
import test_context_intake as intake
import test_owned_service as native


class NativeTerminationRetryTests(native._ServiceTestCase):
    empty_service = intake.NativeContextIntakeTests.empty_service
    durable_read_cut = intake.NativeContextIntakeTests.durable_read_cut

    def directory(self):
        import uuid
        result = ROOT / ".agents/fixtures/termination-retry-p00" / uuid.uuid4().hex
        result.mkdir(parents=True, exist_ok=False)
        return result

    def record(self, service, channel):
        identity = channel.process.pid, channel.process.creation_time, channel.process.image_sha256
        rows = [row for row in service.termination_observations
                if (row.process_id, row.process_creation_time, row.image_sha256) == identity]
        self.assertEqual(len(rows), 1, "each exact retained native process has one observation owner")
        return rows[0]

    def original_terminators(self, service):
        return [(channel, channel.terminate) for channel in (service._client, service._service)
                if channel is not None]

    def cleanup_exact_fixtures(self, service, originals):
        # Test-fixture recovery only. A deliberate exhausted budget must not
        # leave the exact disposable children alive after a failing assertion.
        # No PID/name lookup, unrelated process, production bypass or reset.
        for channel, terminate in originals:
            if not channel.observed_exited():
                terminate(124)
        self.until(lambda: service.poll()["state"] == "STOPPED",
                   explanation="exact disposable native fixture cleanup is unresolved")
        for channel, _ in originals:
            self.assertTrue(channel.observed_exited())
            # Also close a constructor-created channel held by this test if a
            # failed publication never transferred it into a controller slot.
            channel.close()
            self.assertTrue(channel.process.lifetime_closed)

    def assert_live_handles(self, channel):
        self.assertIsNone(channel.process.poll())
        self.assertGreater(channel.process.active_process_count(), 0)
        self.assertIsNotNone(channel.process._process)
        self.assertIsNotNone(channel.process._job)
        self.assertFalse(channel.process.lifetime_closed)
        self.assertFalse(channel._process_closed)

    def test_transient_failure_then_explicit_retry_terminates_exact_native_owners(self):
        for failure in (ContractError("CONTROL_TERMINATION_FIXTURE_DENIED"), OSError(5, "private fixture detail")):
            with self.subTest(failure=type(failure).__name__):
                service, root = self.empty_service()
                before = self.durable_read_cut(root)
                originals = self.original_terminators(service)
                calls = {id(channel): [] for channel, _ in originals}
                shutdown = ShutdownCoordinator(service)
                try:
                    with ExitStack() as patches:
                        for channel, original in originals:
                            counts = calls[id(channel)]

                            def fail_once(exit_code=124, original=original, counts=counts):
                                counts.append(exit_code)
                                if len(counts) == 1:
                                    raise failure
                                return original(exit_code)

                            patches.enter_context(patch.object(channel, "terminate", new=fail_once))
                        shutdown.request()
                        first = {channel.process.pid: self.record(service, channel) for channel, _ in originals}
                        self.assertFalse(shutdown.advance().workers_stopped)
                        for channel, _ in originals:
                            self.assert_live_handles(channel)
                            self.assertEqual(self.record(service, channel).attempts[0].outcome, "FAILED")
                        self.assertEqual([len(values) for values in calls.values()], [1, 1])
                        self.assertTrue(shutdown.pending_owner.retry(timeout_seconds=15).workers_stopped)
                        self.assertEqual([len(values) for values in calls.values()], [2, 2])
                        for channel, _ in originals:
                            final = self.record(service, channel)
                            self.assertEqual(final.owner_ref, first[channel.process.pid].owner_ref)
                            self.assertEqual([attempt.outcome for attempt in final.attempts], ["FAILED", "REQUESTED"])
                            self.assertTrue(final.exit_observed)
                            self.assertTrue(final.cleanup_complete)
                            self.assertTrue(channel.observed_exited())
                        self.assertEqual(self.durable_read_cut(root), before)
                finally:
                    self.cleanup_exact_fixtures(service, originals)

    def test_permanent_failure_ceiling_survives_repeated_stop_and_poll_with_handles_retained(self):
        service, root = self.empty_service()
        before = self.durable_read_cut(root)
        originals = self.original_terminators(service)
        calls = {id(channel): [] for channel, _ in originals}
        try:
            with ExitStack() as patches:
                for channel, _ in originals:
                    counts = calls[id(channel)]

                    def permanent(exit_code=124, counts=counts):
                        counts.append(exit_code)
                        raise ContractError("CONTROL_TERMINATION_FIXTURE_DENIED")

                    patches.enter_context(patch.object(channel, "terminate", new=permanent))
                for _ in range(7):
                    self.assertEqual(service.request_stop()["state"], "STOPPING")
                    self.assertEqual(service.poll()["state"], "STOPPING")
                refs = [self.record(service, channel).owner_ref for channel, _ in originals]
                for _ in range(3):
                    service.poll()
                self.assertEqual([len(values) for values in calls.values()], [3, 3])
                self.assertEqual([self.record(service, channel).owner_ref for channel, _ in originals], refs)
                for channel, _ in originals:
                    row = self.record(service, channel)
                    self.assertEqual(row.attempt_limit, 3)
                    self.assertEqual([attempt.number for attempt in row.attempts], [1, 2, 3])
                    self.assertTrue(all(attempt.outcome == "FAILED" for attempt in row.attempts))
                    self.assertIs(row.exit_observed, False)
                    self.assertFalse(row.cleanup_complete)
                    self.assert_live_handles(channel)
                self.assertEqual(self.durable_read_cut(root), before)
        finally:
            self.cleanup_exact_fixtures(service, originals)

    def test_successful_request_without_actual_exit_is_not_stopped_or_closed(self):
        service, root = self.empty_service()
        before = self.durable_read_cut(root)
        originals = self.original_terminators(service)
        try:
            with ExitStack() as patches:
                for channel, _ in originals:
                    patches.enter_context(patch.object(channel, "terminate", return_value=None))
                for expected in (1, 2):
                    service.request_stop()
                    for _ in range(2):
                        self.assertEqual(service.poll()["state"], "STOPPING")
                    for channel, _ in originals:
                        row = self.record(service, channel)
                        self.assertEqual(len(row.attempts), expected)
                        self.assertTrue(all(attempt.outcome == "REQUESTED" for attempt in row.attempts))
                        self.assertIs(row.exit_observed, False)
                        self.assertFalse(row.cleanup_complete)
                        self.assert_live_handles(channel)
            service.request_stop()
            self.until(lambda: service.poll()["state"] == "STOPPED")
            for channel, _ in originals:
                self.assertEqual(len(self.record(service, channel).attempts), 3)
                self.assertTrue(channel.observed_exited())
            self.assertEqual(self.durable_read_cut(root), before)
        finally:
            self.cleanup_exact_fixtures(service, originals)

    def test_primary_interruption_records_failure_and_still_terminates_neighbor_owner(self):
        for interruption in (KeyboardInterrupt, SystemExit):
            with self.subTest(interruption=interruption.__name__):
                service, _ = self.empty_service()
                originals = self.original_terminators(service)
                client, server = service._client, service._service
                primary = interruption("controlled native-request interruption")
                try:
                    with patch.object(client, "terminate", side_effect=primary):
                        with self.assertRaises(interruption) as caught:
                            service.request_stop()
                    self.assertIs(caught.exception, primary)
                    self.assertEqual(service.state, "STOPPING")
                    self.assertEqual(self.record(service, client).attempts[0].outcome, "INTERRUPTED")
                    self.assertEqual(self.record(service, server).attempts[0].outcome, "REQUESTED")
                    self.assert_live_handles(client)
                    self.until(server.observed_exited)
                    self.assertIs(service._client, client)
                    self.assertIs(service._service, server)
                    shutdown = ShutdownCoordinator(service)
                    self.assertTrue(shutdown.pending_owner.retry(timeout_seconds=15).workers_stopped)
                finally:
                    self.cleanup_exact_fixtures(service, originals)

    def test_observation_error_preserves_unknown_exit_and_native_handles_until_reobserved(self):
        service, _ = self.empty_service()
        originals = self.original_terminators(service)
        client = service._client
        try:
            service.request_stop()
            self.until(lambda: all(channel.observed_exited() for channel, _ in originals))
            with patch.object(client, "observed_exited", side_effect=OSError(5, "private observation path")):
                self.assertEqual(service.poll()["state"], "STOPPING")
                row = self.record(service, client)
                self.assertIsNone(row.exit_observed)
                self.assertEqual(row.observation_error_code, "OS_ERROR_5")
                self.assertFalse(row.cleanup_complete)
                self.assertFalse(client._process_closed)
                self.assertIsNotNone(client.process._process)
                self.assertNotIn("private", repr(row))
            self.until(lambda: service.poll()["state"] == "STOPPED")
            row = self.record(service, client)
            self.assertTrue(row.exit_observed)
            self.assertTrue(row.cleanup_complete)
            self.assertIsNone(row.observation_error_code)
        finally:
            self.cleanup_exact_fixtures(service, originals)

    def test_interrupted_observation_preserves_primary_and_services_neighbor_cleanup(self):
        for interruption in (KeyboardInterrupt, SystemExit):
            with self.subTest(interruption=interruption.__name__):
                service, _ = self.empty_service()
                originals = self.original_terminators(service)
                client, server = service._client, service._service
                primary = interruption("controlled native-observation interruption")
                try:
                    service.request_stop()
                    self.until(lambda: all(channel.observed_exited() for channel, _ in originals))
                    with patch.object(client, "observed_exited", side_effect=primary):
                        with self.assertRaises(interruption) as caught:
                            service.poll()
                    self.assertIs(caught.exception, primary)
                    self.assertEqual(service.state, "STOPPING")
                    self.assertIsNone(self.record(service, client).exit_observed)
                    self.assertFalse(self.record(service, client).cleanup_complete)
                    self.assertTrue(self.record(service, server).cleanup_complete)
                    self.assertFalse(client._process_closed)
                    self.until(lambda: service.poll()["state"] == "STOPPED")
                finally:
                    self.cleanup_exact_fixtures(service, originals)

    def test_malformed_exit_observation_cannot_authorize_cleanup_or_stopped(self):
        for malformed in (None, 1, "STOPPED"):
            with self.subTest(malformed=malformed):
                service, _ = self.empty_service()
                originals = self.original_terminators(service)
                client = service._client
                try:
                    service.request_stop()
                    self.until(lambda: all(channel.observed_exited() for channel, _ in originals))
                    with patch.object(client, "observed_exited", return_value=malformed):
                        self.assertEqual(service.poll()["state"], "STOPPING")
                        row = self.record(service, client)
                        self.assertIsNone(row.exit_observed)
                        self.assertFalse(row.cleanup_complete)
                        self.assertFalse(client._process_closed)
                        self.assertIsNotNone(row.observation_error_code)
                    self.until(lambda: service.poll()["state"] == "STOPPED")
                finally:
                    self.cleanup_exact_fixtures(service, originals)

    def test_partial_cleanup_retains_observed_exit_and_retries_without_new_termination(self):
        service, _ = self.empty_service()
        originals = self.original_terminators(service)
        client, server = service._client, service._service
        try:
            service.request_stop()
            self.until(lambda: all(channel.observed_exited() for channel, _ in originals))
            with patch.object(client, "close", side_effect=ContractError("CONTROL_CLEANUP_FIXTURE_DENIED")):
                self.assertEqual(service.poll()["state"], "STOPPING")
                row = self.record(service, client)
                self.assertTrue(row.exit_observed)
                self.assertFalse(row.cleanup_complete)
                self.assertEqual(row.cleanup_error_code, "CONTROL_CLEANUP_FIXTURE_DENIED")
                self.assertFalse(client._process_closed)
                self.assertTrue(self.record(service, server).cleanup_complete)
                counts = len(row.attempts)
                service.request_stop()
                self.assertEqual(len(self.record(service, client).attempts), counts)
            self.until(lambda: service.poll()["state"] == "STOPPED")
            row = self.record(service, client)
            self.assertTrue(row.cleanup_complete)
            self.assertIsNone(row.cleanup_error_code)
            self.assertEqual(len(row.attempts), counts)
        finally:
            self.cleanup_exact_fixtures(service, originals)

    def test_public_records_are_immutable_bounded_and_do_not_export_private_error_text(self):
        service, _ = self.empty_service()
        originals = self.original_terminators(service)
        invalid_codes = ["private termination path and details", "A" * 4096]
        try:
            with ExitStack() as patches:
                for (channel, _), code in zip(originals, invalid_codes):
                    patches.enter_context(patch.object(channel, "terminate", side_effect=ContractError(code)))
                service.request_stop()
                rows = service.termination_observations
                self.assertIs(type(rows), tuple)
                self.assertEqual(len(rows), 2)
                with self.assertRaises(AttributeError):
                    service.termination_observations = ()
                for row in rows:
                    self.assertIn(row.owner_kind, {"CLIENT_CHANNEL", "SERVICE_CHANNEL"})
                    self.assertGreater(row.process_id, 0)
                    self.assertGreater(row.process_creation_time, 0)
                    self.assertRegex(row.image_sha256, r"^[0-9a-fA-F]{64}$")
                    self.assertLessEqual(len(row.owner_ref), 80)
                    self.assertEqual(row.attempt_limit, 3)
                    self.assertIs(type(row.attempts), tuple)
                    self.assertEqual(len(row.attempts), 1)
                    attempt = row.attempts[0]
                    self.assertGreater(attempt.requested_at_ns, 0)
                    self.assertEqual(attempt.number, 1)
                    self.assertEqual(attempt.outcome, "FAILED")
                    self.assertLessEqual(len(attempt.error_code or ""), 160)
                    self.assertNotIn("private", repr(row))
                    self.assertNotIn("A" * 161, repr(row))
                    with self.assertRaises(FrozenInstanceError):
                        row.exit_observed = True
                    with self.assertRaises(FrozenInstanceError):
                        attempt.outcome = "REQUESTED"
        finally:
            self.cleanup_exact_fixtures(service, originals)

    def test_termination_callback_leaves_controller_lock_available_with_in_progress_record(self):
        service, _ = self.empty_service()
        originals = self.original_terminators(service)
        client, original = originals[0]
        observations, completed = [], threading.Event()
        observer = None

        def during_native_request(exit_code=124):
            nonlocal observer

            def observe():
                observations.append((service.snapshot(), self.record(service, client)))
                completed.set()

            observer = threading.Thread(target=observe, name="ceta-test-termination-observer")
            observer.start()
            accessible = completed.wait(2)
            observations.append(accessible)
            return original(exit_code)

        try:
            with patch.object(client, "terminate", new=during_native_request):
                service.request_stop()
            self.assertIn(True, observations, "controller lock spanned the native termination callback")
            snapshot, row = next(value for value in observations if type(value) is tuple)
            self.assertEqual(snapshot["state"], "STOPPING")
            self.assertTrue(row.request_in_progress)
            self.assertEqual(row.attempts[-1].outcome, "REQUESTING")
            self.until(lambda: service.poll()["state"] == "STOPPED")
            self.assertFalse(self.record(service, client).request_in_progress)
        finally:
            if observer is not None:
                observer.join(timeout=5)
                self.assertFalse(observer.is_alive(), "owned test observation thread did not settle")
            self.cleanup_exact_fixtures(service, originals)

    def test_failing_error_code_accessor_does_not_replace_failure_or_latch_request(self):
        class BrokenDiagnostic(ContractError):
            def __init__(self):
                ValueError.__init__(self, "controlled native-request failure")

            @property
            def code(self):
                raise SystemExit("controlled secondary diagnostic interruption")

        service, _ = self.empty_service()
        originals = self.original_terminators(service)
        client, server = service._client, service._service
        try:
            with patch.object(client, "terminate", side_effect=BrokenDiagnostic()):
                self.assertEqual(service.request_stop()["state"], "STOPPING")
            row = self.record(service, client)
            self.assertFalse(row.request_in_progress)
            self.assertEqual(row.attempts[0].outcome, "FAILED")
            self.assertEqual(row.attempts[0].error_type, "ERROR_DIAGNOSTIC_UNAVAILABLE")
            self.assertIsNone(row.attempts[0].error_code)
            self.assert_live_handles(client)
            self.assertEqual(self.record(service, server).attempts[0].outcome, "REQUESTED")
            self.until(server.observed_exited)
            self.assertTrue(ShutdownCoordinator(service).pending_owner.retry(timeout_seconds=15).workers_stopped)
        finally:
            self.cleanup_exact_fixtures(service, originals)

    def test_late_real_service_publication_gets_own_budget_without_resetting_exhausted_client(self):
        root = self.directory()
        service = OwnedService(root, self.codec, native.INSTALLATION, native.SCOPES, create=True)
        self.services.append(service)
        published, release = threading.Event(), threading.Event()
        held, originals = [], []
        failures = []

        def gated_channel(executable, arguments, **options):
            channel = OwnedChannel(executable, arguments, **options)
            held.append(channel)
            if any(Path(argument).name == "service_process.py" for argument in arguments):
                published.set()
                if not release.wait(10):
                    raise AssertionError("controlled native publication gate was not released")
            return channel

        try:
            with patch("ceta.composition.owned_service.OwnedChannel", new=gated_channel):
                service.start()
                self.until(lambda: (service.poll(), published.is_set())[1])
                client = service._client
                self.assertIsNotNone(client)
                self.assertIsNone(service._service)
                originals = [(channel, channel.terminate) for channel in held]

                def exhausted(exit_code=124):
                    failures.append(exit_code)
                    raise ContractError("CONTROL_TERMINATION_FIXTURE_DENIED")

                with patch.object(client, "terminate", new=exhausted):
                    for _ in range(4):
                        self.assertEqual(service.request_stop()["state"], "STOPPING")
                    first = self.record(service, client)
                    self.assertEqual(len(first.attempts), 3)
                    self.assertEqual(len(failures), 3)
                    release.set()
                    self.until(lambda: (service.poll(), service._service is not None and not service._workers)[1])
                    server = service._service
                    later = self.record(service, server)
                    self.assertNotEqual(later.owner_ref, first.owner_ref)
                    self.assertNotEqual(later.process_id, first.process_id)
                    self.assertEqual(len(later.attempts), 1)
                    self.assertEqual(later.attempts[0].outcome, "REQUESTED")
                    self.assertEqual(self.record(service, client).owner_ref, first.owner_ref)
                    self.assertEqual(len(self.record(service, client).attempts), 3)
                    self.assertEqual(len(failures), 3)
                    self.assertEqual(service.poll()["state"], "STOPPING")
                    self.assert_live_handles(client)
        finally:
            release.set()
            self.until(lambda: (service.poll(), not service._workers and service._launches_in_progress == 0)[1])
            for channel in held:
                if all(existing is not channel for existing, _ in originals):
                    originals.append((channel, channel.terminate))
            self.cleanup_exact_fixtures(service, originals)
