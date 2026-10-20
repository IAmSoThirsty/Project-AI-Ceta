"""Owned Windows service integration and explicitly controlled regressions.

NativeOwnedServiceTests starts the real service and authenticated native client
in fresh rebuild_ios/.agents/fixtures fixtures. Positive records are seeded
by KernelFixture's synthetic owners before its parent writer closes; the child
uses the unchanged identity-only owners, whose positive authority stays closed.
ControlledOwnedServiceTests injects local launch/control/cleanup fixtures. Those
tests exercise actual controller/channel/operator logic but are not native
failure reproductions, authentication proof or original acceptance evidence.
All cases remain IMPLEMENTED_NOT_QUALIFIED; no model, effect, normal profile,
installed service, external independence or product qualification is claimed.
"""
from pathlib import Path
from fixture_paths import native_fixture_path
import hashlib
import os
import pickle
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ceta.application.operator import OperatorSession
from ceta.composition.owned_service import (OwnedService,
                                            owned_service_shutdown_settlement_witness_is_current)
from ceta.contracts.local_ipc import SubmissionUncertain, decode_message
from ceta.contracts.local_results import encode_response
from ceta.contracts.wire import ContractError, RecordCodec, strict_loads
from ceta.supervisor.service import (OwnedChannel, OwnedChannelError,
                                     controlled_environment)
from ceta.supervisor.windows_jobs import WindowsLaunchError
from test_kernel_transactions import INSTALLATION, SCOPES, KernelFixture


class _ServiceTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if sys.platform != "win32" or sys.version_info[:2] != (3, 12):
            raise AssertionError("Requires the declared Windows Python3.12 interpreter")
        cls.schema = strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes())
        cls.codec = RecordCodec(cls.schema)

    def setUp(self):
        self.services, self.fixtures, self.foreign = [], [], []
        self.foreign_readers = []

    def until(self, predicate, *, seconds=20.0, explanation="condition unobserved"):
        deadline = time.monotonic() + seconds
        while True:
            value = predicate()
            if value:
                return value
            if time.monotonic() >= deadline:
                self.fail(explanation)
            time.sleep(0.005)

    def stop(self, service):
        service.request_stop("reason:test-stop")
        result = self.until(lambda: (value if (value := service.poll())["state"] == "STOPPED" else None),
                            explanation="owned lifetimes/cleanup did not reach STOPPED")
        self.assertEqual(result["authority"], "CLOSED")
        for channel in (service._client, service._service):
            if channel is not None:
                self.assertTrue(channel.observed_exited())
        return result

    def tearDown(self):
        failures = []
        for service in reversed(self.services):
            try:
                self.stop(service)
            except BaseException as error:
                failures.append(repr(error))
        for process in self.foreign:
            try:
                if process.poll() is None:
                    # Only the exact Popen-created disposable fixture is killed.
                    process.kill()
                process.wait(timeout=5)
                if process.stdin is not None:
                    process.stdin.close()
            except BaseException as error:
                failures.append(repr(error))
        for reader, stream in self.foreign_readers:
            try:
                reader.join(timeout=5)
                if reader.is_alive():
                    failures.append('foreign publication reader did not terminate')
                else:
                    stream.close()
            except BaseException as error:
                failures.append(repr(error))
        for fixture in self.fixtures:
            try:
                fixture.store.close()
            except BaseException as error:
                failures.append(repr(error))
        if failures:
            self.fail("fixture cleanup remains unresolved: " + repr(failures))

    def directory(self):
        result = ROOT / ".agents/fixtures/owned-service-24" / uuid.uuid4().hex
        result.mkdir(parents=True, exist_ok=False)
        return result

    def fixture(self):
        result = KernelFixture(self.schema)
        self.fixtures.append(result)
        return result

    def service(self, root, *, principal="operator:development", session=None):
        result = OwnedService(root, self.codec, INSTALLATION, SCOPES,
                              principal_id=principal, session_id=session)
        self.services.append(result)
        return result

    def fixture_service(self, fixture, *, principal=None, session=None):
        # No parent connection remains while the actual child owns this writer.
        fixture.store.close()
        self.assertTrue(fixture.store._closed)
        return self.service(fixture.root,
            principal=fixture.owners.worker.principal_id if principal is None else principal,
            session=fixture.owners.worker.session_id if session is None else session)

    def ready(self, service):
        service.start()
        def observed():
            value = service.poll()
            if value["state"] == "RECOVERING":
                self.fail("service startup denied: " + value["detail"])
            return value if value["state"] == "READY" else None
        return self.until(observed, explanation="real service never reported READY")

    def call(self, service, wire, operation):
        attempt = service.begin_call(wire, operation)
        def observed():
            value = service.poll().get("call")
            return value if value is not None and value["attempt"] == attempt else None
        result = self.until(observed, explanation="exact submitted attempt has no result")
        self.assertIn("response", result, "transport uncertainty is not a kernel result")
        return attempt, result["response"]

    def reopen_unchanged(self, fixture, before, keys=()):
        fixture.reopen()
        self.assertEqual((fixture.cut(keys), fixture.budget()), before)

    def history_bytes(self, root):
        # Exact database/companion roles only, not controller transport artifacts.
        return {name: hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
                for name in ("history.sqlite3", "history.sqlite3-wal", "history.sqlite3-shm",
                             "history.sqlite3-journal")
                for path in (root / name,)}


class NativeOwnedServiceTests(_ServiceTestCase):
    """Real Windows jobs, service/client processes, IPC and v2 SQLite."""

    def test_actual_startup_reports_selected_lifetimes_fresh_generation_and_closed_authority(self):
        fixture = self.fixture()
        before = fixture.cut(), fixture.budget()
        service = self.fixture_service(fixture)
        observation = self.ready(service)
        self.assertRegex(observation["generation"], r"\A[0-9a-f]{64}\Z")
        self.assertEqual(observation["authority"], "CLOSED")
        self.assertEqual(tuple(row["scope_id"] for row in observation["positions"]), SCOPES)
        expected_image = hashlib.sha256(Path(sys._base_executable).read_bytes()).hexdigest()
        selected = (service._client.process, service._service.process)
        self.assertNotEqual(selected[0].pid, selected[1].pid)
        for process in selected:
            self.assertGreater(process.pid, 0)
            self.assertGreater(process.creation_time, 0)
            self.assertEqual(process.image_sha256, expected_image)
            self.assertIsNone(process.poll())
            self.assertGreaterEqual(process.active_process_count(), 1)
        self.stop(service)
        self.reopen_unchanged(fixture, before)

    def test_actual_preparation_returns_correlated_closed_owner_denial_without_store_change(self):
        fixture = self.fixture()
        before = fixture.cut(), fixture.budget()
        service = self.fixture_service(fixture)
        self.ready(service)
        attempt, response = self.call(service, fixture.proposal_wire, "kernel.prepare")
        self.assertEqual(response.kind, "DENIED_RECONCILE")
        self.assertEqual(response.error_code, "TRUSTED_PREPARATION_OWNER_UNAVAILABLE")
        self.assertIsNone(response.record_wire)
        self.assertIsNone(response.event_wire)
        request = decode_message((native_fixture_path(service._spool / (attempt + ".request.json"))).read_bytes(), self.codec)
        self.assertEqual(request.record.original_wire, fixture.proposal_wire)
        self.assertEqual(request.receiver_generation, service.generation)
        self.assertEqual(service.snapshot()["state"], "RECOVERING")
        with self.assertRaisesRegex(ContractError, "SERVICE_RECONCILIATION_REQUIRED"):
            service.begin_call(fixture.proposal_wire, "kernel.prepare")
        self.stop(service)
        self.reopen_unchanged(fixture, before)

    def test_actual_prepared_recovery_reads_exact_record_without_admission_or_charge(self):
        fixture = self.fixture()
        prepared = fixture.prepare()
        keys = fixture.permit_keys(prepared.record_wire)
        before = fixture.cut(keys), fixture.budget()
        service = self.fixture_service(fixture)
        self.ready(service)
        _, response = self.call(service, prepared.record_wire, "kernel.recover_permit")
        self.assertEqual(response.kind, "CURRENT_RECORD")
        self.assertEqual(response.record_wire, prepared.record_wire)
        self.assertIsNone(response.event_wire)
        self.assertEqual(self.codec.decode(response.record_wire).as_dict()["status"], "PREPARED")
        self.assertEqual(service.snapshot()["authority"], "CLOSED")
        self.stop(service)
        self.reopen_unchanged(fixture, before, keys)

    def test_actual_consumed_recovery_and_evidence_readback_do_not_repeat_consumption(self):
        fixture = self.fixture()
        prepared = fixture.prepare()
        consumed = fixture.service.consume(prepared.record_wire, fixture.owners.worker_context)
        keys = fixture.permit_keys(prepared.record_wire)
        before = fixture.cut(keys), fixture.budget()
        service = self.fixture_service(fixture)
        self.ready(service)
        _, recovered = self.call(service, prepared.record_wire, "kernel.recover_permit")
        self.assertEqual(recovered.kind, "CURRENT_RECORD")
        self.assertEqual(recovered.record_wire, consumed.record_wire)
        _, evidence = self.call(service, recovered.record_wire, "kernel.resolve_consumption")
        self.assertEqual(evidence.kind, "EVIDENCE")
        self.assertEqual(evidence.record_wire, consumed.record_wire)
        self.assertEqual(evidence.event_wire, consumed.event_wire)
        self.assertEqual(evidence.prior_position, consumed.prior_position)
        _, duplicate = self.call(service, prepared.record_wire, "kernel.consume")
        self.assertEqual(duplicate.kind, "DENIED_RECONCILE")
        self.assertEqual(duplicate.error_code, "KERNEL_PERMIT_NOT_PREPARED")
        self.stop(service)
        self.reopen_unchanged(fixture, before, keys)

    def test_actual_recovery_rejects_different_launcher_bound_principal_without_changes(self):
        fixture = self.fixture()
        prepared = fixture.prepare()
        keys = fixture.permit_keys(prepared.record_wire)
        before = fixture.cut(keys), fixture.budget()
        service = self.fixture_service(fixture, principal="worker:another-selected-principal")
        self.ready(service)
        _, response = self.call(service, prepared.record_wire, "kernel.recover_permit")
        self.assertEqual(response.kind, "DENIED_RECONCILE")
        self.assertEqual(response.error_code, "KERNEL_PEER_BINDING_MISMATCH")
        self.stop(service)
        self.reopen_unchanged(fixture, before, keys)

    def test_actual_recovery_rejects_different_launcher_bound_session_without_changes(self):
        fixture = self.fixture()
        prepared = fixture.prepare()
        keys = fixture.permit_keys(prepared.record_wire)
        before = fixture.cut(keys), fixture.budget()
        service = self.fixture_service(fixture, session="session:another-selected-session")
        self.ready(service)
        _, response = self.call(service, prepared.record_wire, "kernel.recover_permit")
        self.assertEqual(response.kind, "DENIED_RECONCILE")
        self.assertEqual(response.error_code, "KERNEL_PEER_BINDING_MISMATCH")
        self.stop(service)
        self.reopen_unchanged(fixture, before, keys)

    def test_actual_missing_store_startup_preserves_absence_and_unknown_file(self):
        root = self.directory()
        sentinel = root / "unknown-fixture.bin"
        sentinel.write_bytes(b"owned-service missing-store preservation fixture\x00")
        before = self.history_bytes(root), sentinel.read_bytes()
        service = self.service(root)
        service.start()
        self.until(lambda: service.poll()["state"] == "RECOVERING",
                   explanation="missing store startup was not denied")
        self.assertIsNone(service.generation)
        self.stop(service)
        self.assertEqual((self.history_bytes(root), sentinel.read_bytes()), before)

    def test_actual_corrupt_store_startup_preserves_exact_database_bytes(self):
        root = self.directory()
        (root / "history.sqlite3").write_bytes(b"not a SQLite database; synthetic corrupt fixture\x00")
        before = self.history_bytes(root)
        service = self.service(root)
        service.start()
        self.until(lambda: service.poll()["state"] == "RECOVERING",
                   explanation="corrupt store startup was not denied")
        self.assertIsNone(service.generation)
        self.stop(service)
        self.assertEqual(self.history_bytes(root), before)

    def test_actual_stop_observes_owned_jobs_and_preserves_foreign_same_executable_process(self):
        fixture = self.fixture()
        service = self.fixture_service(fixture)
        self.ready(service)
        marker = fixture.root / "foreign-created-by-test.json"
        pending = marker.with_suffix(".pending")
        code = ("import json,os,pathlib,sys; "
                "marker=pathlib.Path(sys.argv[1]); pending=marker.with_suffix('.pending'); "
                "pending.write_bytes(b''); sys.stdin.buffer.read(1); "
                "pending.write_text(json.dumps({'pid':os.getpid()}),encoding='utf8'); "
                "pending.rename(marker); "
                "sys.stdout.buffer.write(b'published\\n'); sys.stdout.buffer.flush(); "
                "sys.stdin.buffer.read(1)")
        foreign = subprocess.Popen((sys._base_executable, "-I", "-B", "-c", code, str(marker)),
            cwd=str(ROOT), env=controlled_environment(fixture.root), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=0x08000000)
        self.foreign.append(foreign)
        # Pause with an empty unpublished file: path existence must not expose
        # an incomplete readiness record. Publish only after the write closes.
        self.until(pending.exists, explanation="foreign disposable fixture staging unobserved")
        self.assertFalse(marker.exists())
        self.assertEqual(pending.read_bytes(), b"")
        self.assertIsNone(foreign.poll())
        foreign.stdin.write(b"p"); foreign.stdin.flush()
        publication = []
        reader = threading.Thread(target=lambda: publication.append(foreign.stdout.readline()),
                                  name='foreign-publication-reader', daemon=True)
        self.foreign_readers.append((reader, foreign.stdout))
        reader.start()
        self.until(lambda: bool(publication),
                   explanation='foreign child did not acknowledge completed marker publication')
        self.assertEqual(publication, [b'published\n'])
        reader.join(timeout=5)
        self.assertFalse(reader.is_alive())
        self.assertTrue(marker.exists())
        self.assertFalse(pending.exists())
        self.assertEqual(strict_loads(marker.read_bytes())["pid"], foreign.pid)
        self.assertNotIn(foreign.pid, (service._client.process.pid, service._service.process.pid))
        channels = service._client, service._service
        self.stop(service)
        self.assertTrue(all(channel.observed_exited() for channel in channels))
        self.assertIsNone(foreign.poll(), "STOP must not select other processes by image/name")
        foreign.stdin.write(b"x"); foreign.stdin.flush()
        self.assertEqual(foreign.wait(timeout=5), 0)

    def test_actual_restart_has_new_generation_and_never_auto_replays_preserved_request(self):
        fixture = self.fixture()
        before = fixture.cut(), fixture.budget()
        first = self.fixture_service(fixture)
        initial = self.ready(first)
        attempt, response = self.call(first, fixture.proposal_wire, "kernel.prepare")
        self.assertEqual(response.kind, "DENIED_RECONCILE")
        request_path = first._spool / (attempt + ".request.json")
        original_request = native_fixture_path(request_path).read_bytes()
        self.stop(first)
        second = self.service(fixture.root, principal=fixture.owners.worker.principal_id,
                              session=fixture.owners.worker.session_id)
        restarted = self.ready(second)
        self.assertNotEqual(restarted["generation"], initial["generation"])
        self.assertEqual(restarted["positions"], initial["positions"])
        self.assertIsNone(restarted["call"])
        self.assertIsNone(restarted["pending_attempt"])
        self.assertEqual(tuple(second._spool.iterdir()), ())
        self.assertEqual(native_fixture_path(request_path).read_bytes(), original_request)
        self.stop(second)
        self.reopen_unchanged(fixture, before)


class _ProcessFixture:
    """In-memory lifetime fixture, not an OS identity or process."""
    def __init__(self, *, exit_on_terminate=True):
        self.pid = 10000 + int(uuid.uuid4().hex[:4], 16)
        self.creation_time, self.image_sha256 = 1, "0" * 64
        self.alive, self.closed, self.terminations = True, False, []
        self.exit_on_terminate = exit_on_terminate
        self.poll_attempts, self.job_observations = 0, 0
        self.residual_cleanup = None

    @property
    def lifetime_closed(self):
        return self.closed

    def poll(self):
        self.poll_attempts += 1
        if self.closed:
            raise ContractError("FIXTURE_CLOSED_LIFETIME_REVISITED")
        return None if self.alive else 124

    def active_process_count(self):
        self.job_observations += 1
        if self.closed:
            raise ContractError("FIXTURE_CLOSED_LIFETIME_REVISITED")
        return int(self.alive)

    def terminate(self, code=124):
        self.terminations.append(code)
        if self.closed:
            raise ContractError("FIXTURE_CLOSED_LIFETIME_REVISITED")
        if self.exit_on_terminate:
            self.alive = False

    def finish(self):
        self.alive = False

    def close(self):
        if self.alive:
            raise ContractError("FIXTURE_LIFETIME_UNOBSERVED")
        self.closed = True
        if self.residual_cleanup is not None:
            self.residual_cleanup()
            self.residual_cleanup = None


class _ChannelFixture:
    """Controlled control channel; no native calls or authentication."""
    def __init__(self, *, exit_on_terminate=True, ready=False):
        self.process = _ProcessFixture(exit_on_terminate=exit_on_terminate)
        self.events = [{"event": "ready", "pid": self.process.pid}] if ready else []
        self.closed, self.sent, self.send_error = False, [], None

    def poll(self):
        values, self.events = self.events, []
        return values

    def send(self, command):
        self.sent.append(command)
        if self.send_error is not None:
            raise self.send_error

    def terminate(self, code=124):
        self.process.terminate(code)

    def observed_exited(self):
        return self.closed or not self.process.alive

    def close(self):
        self.process.close()
        self.closed = True


class _ControlApiFixture:
    """Tracks each fake handle and makes a selected close fail exactly once."""
    def __init__(self, *, fail_once=()):
        self.next_handle, self.created = 101, []
        self.fail_once, self.attempted, self.closed = set(fail_once), [], set()

    def pipe(self, *, child_reads):
        parent, child = self.next_handle, self.next_handle + 1
        self.next_handle += 2
        self.created.extend((parent, child))
        return parent, child

    def close(self, handle):
        if handle is None:
            return
        self.attempted.append(handle)
        if handle in self.fail_once:
            self.fail_once.remove(handle)
            raise ContractError("FIXTURE_HANDLE_CLOSE_FAILED")
        if handle in self.closed:
            raise ContractError("FIXTURE_DOUBLE_CLOSE")
        self.closed.add(handle)

    def PeekNamedPipe(self, handle, buffer, count, read, available, left):
        # A failed but retained channel has no queued fixture control output.
        available._obj.value = 0
        return True


class ControlledOwnedServiceTests(_ServiceTestCase):
    """Injected failure/scheduling probes, explicitly separate from native cases."""

    def controlled_service(self):
        return self.service(self.directory())

    def test_shutdown_settlement_witness_is_opaque_and_requires_exact_service_evidence(self):
        """A public STOPPED string or observation cannot mint terminal proof."""
        service = self.controlled_service()
        prestart = service.shutdown_settlement_witness()
        self.assertIs(prestart, service.shutdown_settlement_witness())
        self.assertEqual(repr(prestart), "<OwnedService shutdown settlement witness>")
        with self.assertRaises(TypeError):
            pickle.dumps(prestart)

        # A caller-controlled state string after a claimed launch has no
        # retained native-owner proof and must not be treated as pre-start.
        unproven = self.controlled_service()
        unproven._start_claimed, unproven._state = True, "STOPPED"
        self.assertIsNone(unproven.shutdown_settlement_witness())

        client, server = _ChannelFixture(ready=True), _ChannelFixture()
        with patch("ceta.composition.owned_service.OwnedChannel", side_effect=(client, server)):
            service.start()
            self.until(lambda: (service.poll() and service._service is server), seconds=5,
                       explanation="controlled service owner was not published")
            self.join_background(service)
            self.assertIsNone(service.shutdown_settlement_witness())
            service.request_stop()
            self.assertTrue(self.until(lambda: service.poll()["state"] == "STOPPED", seconds=5))

        observations = service.termination_observations
        self.assertTrue(observations)
        self.assertTrue(all(item.exit_observed is True and item.cleanup_complete for item in observations))
        terminal = service.shutdown_settlement_witness()
        self.assertIsNotNone(terminal)
        self.assertIs(terminal, service.shutdown_settlement_witness())
        self.assertIsNot(terminal, prestart)
        self.assertTrue(owned_service_shutdown_settlement_witness_is_current(service, terminal))
        self.assertFalse(owned_service_shutdown_settlement_witness_is_current(service, object()))

        class ImpostorService:
            def shutdown_settlement_witness(self):
                return terminal

        self.assertFalse(owned_service_shutdown_settlement_witness_is_current(ImpostorService(), terminal))

    def ready_fixture(self):
        service = self.controlled_service()
        client, server = _ChannelFixture(), _ChannelFixture()
        service._client, service._service = client, server
        service._generation, service._state = "f" * 64, "READY"
        return service, client, server

    def join_background(self, service):
        # Controlled tests retain actual worker objects from this inspected
        # controller cut. A finally flag alone is not observed thread exit.
        # No exact scheduling or callback count is asserted, and no controller
        # lock is held while joining these disposable fixture workers.
        with service._lock:
            threads = tuple(task["thread"] for task in service._workers
                            if task["thread"] is not None)
        for thread in threads:
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive(), "owned fixture worker did not retire")

    def blocked_launch(self, service, starter, factory):
        entered, release, stop_done = threading.Event(), threading.Event(), threading.Event()
        launch_errors, stop_errors, workers = [], [], []
        def gated(*args, **kwargs):
            workers.append(threading.current_thread())
            entered.set()
            if not release.wait(10):
                raise AssertionError("test launch gate was not released")
            return factory(*args, **kwargs)
        def starting():
            try:
                starter()
            except BaseException as error:
                launch_errors.append(error)
        def stopping():
            try:
                service.request_stop()
            except BaseException as error:
                stop_errors.append(error)
            finally:
                stop_done.set()
        launch_thread = threading.Thread(target=starting)
        stop_thread = threading.Thread(target=stopping)
        with patch("ceta.composition.owned_service.OwnedChannel", side_effect=gated):
            launch_thread.start()
            try:
                self.assertTrue(entered.wait(5), "launch did not enter the owned scheduling gate")
                stop_thread.start()
                self.assertTrue(stop_done.wait(3), "STOP blocked behind an unpublished launch")
                self.assertEqual(stop_errors, [])
                self.assertEqual(service.poll()["state"], "STOPPING",
                                 "unpublished owner cannot be reported stopped")
                with self.assertRaises(ContractError):
                    service.begin_call(b"{}", "kernel.prepare")
            finally:
                release.set()
                launch_thread.join(timeout=5)
                if stop_thread.ident is not None:
                    stop_thread.join(timeout=5)
                for worker in workers:
                    worker.join(timeout=5)
        self.assertFalse(launch_thread.is_alive())
        self.assertFalse(stop_thread.is_alive())
        for worker in workers:
            self.assertFalse(worker.is_alive(), "unpublished launch worker did not retire")
        self.assertEqual(launch_errors, [])
        self.assertEqual(stop_errors, [])
        self.assertEqual(self.until(lambda: service.poll()["state"] == "STOPPED", seconds=5), True)

    def failed_channel(self, *, launch_error=None):
        process = _ProcessFixture(exit_on_terminate=False)
        api = _ControlApiFixture(fail_once=(102,))
        if launch_error is None:
            selected = {"return_value": process}
        else:
            launch_error = WindowsLaunchError("WINDOWS_LAUNCH_CLEANUP_UNRESOLVED", process)
            selected = {"side_effect": launch_error}
        with patch("ceta.supervisor.service._ControlApi", return_value=api), \
                patch("ceta.supervisor.service.WindowsOwnedProcess.launch", **selected):
            with self.assertRaises(OwnedChannelError) as caught:
                OwnedChannel("controlled-executable", (), cwd="controlled-cwd", environment={})
        return caught.exception, process, api, launch_error

    def test_controlled_stop_waits_for_pending_client_publication_and_terminates_late_owner(self):
        service = self.controlled_service()
        channel = _ChannelFixture()
        self.blocked_launch(service, service.start, lambda *a, **kw: channel)
        self.assertTrue(channel.process.terminations)
        self.assertTrue(channel.closed)

    def test_controlled_stop_before_launch_reservation_denies_instance_reuse_and_stale_launch(self):
        service = self.controlled_service()
        original = service._launch_owned
        entered, release, second_done = threading.Event(), threading.Event(), threading.Event()
        first_errors, second_errors, worker_errors, workers = [], [], [], []
        def gated(slot, arguments):
            workers.append(threading.current_thread())
            entered.set()
            if not release.wait(10):
                raise AssertionError("pre-reservation gate was not released")
            try:
                return original(slot, arguments)
            except BaseException as error:
                worker_errors.append(error)
                raise
        def first_start():
            try:
                service.start()
            except BaseException as error:
                first_errors.append(error)
        def second_start():
            try:
                service.start()
            except BaseException as error:
                second_errors.append(error)
            finally:
                second_done.set()
        first = threading.Thread(target=first_start)
        second = threading.Thread(target=second_start)
        with patch.object(service, "_launch_owned", side_effect=gated), \
                patch("ceta.composition.owned_service.OwnedChannel", return_value=_ChannelFixture()) as native_launch:
            first.start()
            try:
                self.assertTrue(entered.wait(5))
                service.request_stop()
                self.assertEqual(service.poll()["state"], "STOPPING",
                                 "an outstanding worker must remain owned before launch reservation")
                native_launch.assert_not_called()
                second.start()
                self.assertTrue(second_done.wait(3), "reusing a claimed instance attempted another launch")
                self.assertEqual(len(second_errors), 1)
                self.assertIsInstance(second_errors[0], ContractError)
                self.assertEqual(second_errors[0].code, "SERVICE_ALREADY_STARTED_OR_OWNERSHIP_RETAINED")
                native_launch.assert_not_called()
            finally:
                release.set()
                first.join(timeout=5)
                if second.ident is not None:
                    second.join(timeout=5)
                for worker in workers:
                    worker.join(timeout=5)
            self.assertFalse(first.is_alive())
            self.assertFalse(second.is_alive())
            for worker in workers:
                self.assertFalse(worker.is_alive(), "stale-start worker did not retire")
            self.assertEqual(first_errors, [], "start returned before its owned worker reached the launch seam")
            self.assertEqual(len(worker_errors), 1)
            self.assertIsInstance(worker_errors[0], ContractError)
            self.assertEqual(worker_errors[0].code, "SERVICE_LAUNCH_CANCELLED_OR_OWNER_RETAINED")
            native_launch.assert_not_called()
        self.assertIsNone(service._client)
        self.assertIsNone(service._service)
        self.assertEqual(self.until(lambda: service.poll()["state"] == "STOPPED", seconds=5), True)

    def test_controlled_stop_waits_for_pending_service_publication_and_terminates_late_owner(self):
        service = self.controlled_service()
        client, server = _ChannelFixture(ready=True), _ChannelFixture()
        with patch("ceta.composition.owned_service.OwnedChannel", return_value=client):
            service.start()
            self.until(lambda: service._client is client, seconds=5,
                       explanation="owned client publication was not observed")
            self.join_background(service)
        self.blocked_launch(service, service.poll, lambda *a, **kw: server)
        self.assertTrue(client.process.terminations)
        self.assertTrue(server.process.terminations)
        self.assertTrue(server.closed)

    def test_controlled_late_startup_denial_preserves_stopping_until_lifetimes_exit(self):
        service = self.controlled_service()
        client = _ChannelFixture(exit_on_terminate=False, ready=True)
        server = _ChannelFixture(exit_on_terminate=False)
        with patch("ceta.composition.owned_service.OwnedChannel", side_effect=(client, server)):
            service.start()
            self.until(lambda: (service.poll() and service._service is server), seconds=5,
                       explanation="owned service publication was not observed")
            self.join_background(service)
        service.request_stop()
        server.events.append({"event": "startup_denied", "code": "FIXTURE_STARTUP_DENIED"})
        self.assertEqual(service.poll()["state"], "STOPPING")
        self.assertFalse(client.closed)
        self.assertFalse(server.closed)
        client.process.finish(); server.process.finish()
        self.assertEqual(self.until(lambda: service.poll()["state"] == "STOPPED", seconds=5), True)
        self.assertTrue(client.closed and server.closed)

    def test_controlled_constructor_cleanup_error_retains_live_owner_and_every_handle(self):
        error, process, api, _ = self.failed_channel()
        try:
            self.assertIs(error.owned_channel.process, process)
            self.assertIs(error.owned_process, process)
            self.assertFalse(error.owned_channel.observed_exited())
            self.assertEqual(set(api.attempted), {102, 104, 106})
            with self.assertRaisesRegex(ContractError, "FIXTURE_LIFETIME_UNOBSERVED"):
                error.close_cleanup()
            self.assertFalse(process.closed)
        finally:
            process.finish(); error.close_cleanup()
        self.assertEqual(api.closed, set(api.created))
        self.assertEqual(api.attempted.count(102), 2)
        self.assertTrue(error.owned_channel.observed_exited())

    def test_controlled_launch_error_survives_secondary_handle_failure_and_retains_cleanup(self):
        error, process, api, original = self.failed_channel(launch_error=True)
        try:
            self.assertIs(error.primary_error, original)
            self.assertIs(error.launch_error, original)
            self.assertIs(error.owned_process, process)
            self.assertTrue(error.cleanup_errors)
            self.assertEqual(error.cleanup_errors[0].code, "FIXTURE_HANDLE_CLOSE_FAILED")
            self.assertFalse(error.owned_channel.observed_exited())
        finally:
            process.finish(); error.close_cleanup()
        self.assertEqual(api.closed, set(api.created))
        self.assertTrue(process.closed)

    def test_controlled_partial_channel_close_retries_only_residual_handles(self):
        process, api = _ProcessFixture(), _ControlApiFixture(fail_once=(101,))
        with patch("ceta.supervisor.service._ControlApi", return_value=api), \
                patch("ceta.supervisor.service.WindowsOwnedProcess.launch", return_value=process):
            channel = OwnedChannel("controlled-executable", (), cwd="controlled-cwd", environment={})
        process.finish()
        try:
            with self.assertRaisesRegex(ContractError, "CONTROL_CLEANUP_PENDING"):
                channel.close()
            self.assertTrue(channel.observed_exited())
            self.assertIn(101, set(api.created) - api.closed)
            channel.close(); channel.close()
        finally:
            channel.close()
        self.assertEqual(api.closed, set(api.created))
        self.assertEqual(api.attempted.count(101), 2)
        self.assertEqual(api.attempted.count(103), 1)
        self.assertEqual(api.attempted.count(105), 1)

    def test_controlled_closed_launcher_lifetime_keeps_residual_image_cleanup_reachable(self):
        service = self.controlled_service()
        process = _ProcessFixture()
        process.finish(); process.close()
        api = _ControlApiFixture(fail_once=(901,))
        api.created.append(901)  # The launcher's retained startup-image handle.
        process.residual_cleanup = lambda: api.close(901)
        original = WindowsLaunchError("WINDOWS_LAUNCH_FINALIZATION_UNRESOLVED", process)
        with patch("ceta.supervisor.service._ControlApi", return_value=api), \
                patch("ceta.supervisor.service.WindowsOwnedProcess.launch", side_effect=original):
            with self.assertRaises(OwnedChannelError) as caught:
                OwnedChannel("controlled-executable", (), cwd="controlled-cwd", environment={})
        error = caught.exception
        self.assertIs(error.owned_process, process)
        self.assertIs(error.launch_error, original)
        with patch("ceta.composition.owned_service.OwnedChannel", side_effect=error):
            service.start()
            self.until(lambda: service.poll()["state"] == "RECOVERING"
                       and service._client is error.owned_channel, seconds=5,
                       explanation="failed client owner was not published")
            self.join_background(service)
        self.assertIs(service._client, error.owned_channel)
        self.assertTrue(error.owned_channel.observed_exited())
        service.request_stop()
        self.assertEqual(service.poll()["state"], "STOPPING",
                         "unclosed startup image must retain a cleanup obligation")
        self.assertNotIn(901, api.closed)
        self.assertEqual(self.until(lambda: service.poll()["state"] == "STOPPED", seconds=5), True)
        self.assertEqual(api.attempted.count(901), 2)
        self.assertEqual(api.closed, set(api.created))
        self.assertEqual(process.poll_attempts, 0)
        self.assertEqual(process.job_observations, 0)
        self.assertEqual(process.terminations, [])
        self.assertTrue(error.owned_channel.observed_exited())

    def test_controlled_failed_client_launch_retains_complete_channel_until_observed_exit(self):
        service = self.controlled_service()
        error, process, api, _ = self.failed_channel()
        with patch("ceta.composition.owned_service.OwnedChannel", side_effect=error):
            service.start()
            self.until(lambda: service.poll()["state"] == "RECOVERING"
                       and service._client is error.owned_channel, seconds=5,
                       explanation="failed client owner was not published")
            self.join_background(service)
        self.assertIs(service._client, error.owned_channel)
        service.request_stop()
        self.assertTrue(process.terminations)
        self.assertEqual(service.poll()["state"], "STOPPING")
        process.finish()
        self.assertEqual(self.until(lambda: service.poll()["state"] == "STOPPED", seconds=5), True)
        self.assertEqual(api.closed, set(api.created))

    def test_controlled_failed_service_launch_retains_complete_channel_until_observed_exit(self):
        service = self.controlled_service()
        client = _ChannelFixture(ready=True)
        error, process, api, _ = self.failed_channel()
        with patch("ceta.composition.owned_service.OwnedChannel", side_effect=(client, error)):
            service.start()
            self.until(lambda: service.poll()["state"] == "RECOVERING"
                       and service._service is error.owned_channel, seconds=5,
                       explanation="failed service owner was not published")
            self.join_background(service)
            self.assertEqual(service.poll()["state"], "RECOVERING")
        self.assertIs(service._service, error.owned_channel)
        service.request_stop()
        self.assertTrue(process.terminations)
        self.assertEqual(service.poll()["state"], "STOPPING")
        process.finish()
        self.assertEqual(self.until(lambda: service.poll()["state"] == "STOPPED", seconds=5), True)
        self.assertEqual(api.closed, set(api.created))

    def uncertain_operator(self):
        fixture = self.fixture()
        service, client, _ = self.ready_fixture()
        client.send_error = OSError("controlled fixture write failure; not a native failure")
        operator = OperatorSession(service, self.codec)
        draft = fixture.proposal_wire.decode("utf8")
        operator.set_draft(draft)
        attempt = operator.submit("kernel.prepare")
        self.until(lambda: ((value := operator.poll()).get("call") is not None
                   and value["call"].get("attempt") == attempt
                   and value["call"].get("kind") == "TRANSPORT_UNCERTAIN"), seconds=5,
                   explanation="async send failure did not preserve the exact uncertain attempt")
        self.join_background(service)
        return operator, service, client, attempt, draft

    def late_response(self, service, client, attempt):
        request_path = service._spool / (attempt + ".request.json")
        request = decode_message(native_fixture_path(request_path).read_bytes(), self.codec)
        response = encode_response(request, ContractError("FIXTURE_LATE_DENIAL"), self.codec)
        (native_fixture_path(service._spool / (attempt + ".response.json"))).write_bytes(response)
        client.events.append({"event": "call_result", "attempt": attempt,
                              "response_sha256": hashlib.sha256(response).hexdigest()})
        return response

    def test_controlled_uncertain_submission_keeps_exact_operator_attempt_and_draft(self):
        operator, service, client, attempt, draft = self.uncertain_operator()
        self.assertEqual(operator.draft, draft)
        self.assertEqual(service.snapshot()["pending_attempt"], attempt)
        request_wire = (native_fixture_path(service._spool / (attempt + ".request.json"))).read_bytes()
        request = decode_message(request_wire, self.codec)
        self.assertEqual(request.record.original_wire, draft.encode("utf8"))
        self.assertEqual(request.message_id, "message:" + attempt)
        self.assertEqual(client.sent[0]["attempt"], attempt)
        self.assertEqual(client.sent[0]["request_sha256"], hashlib.sha256(request_wire).hexdigest())
        observation = operator.poll()
        visible = strict_loads(operator.result_text.encode("utf8"))
        self.assertEqual(visible["attempt"], attempt)
        self.assertEqual(visible["kind"], "TRANSPORT_UNCERTAIN")
        self.assertEqual(observation["state"], "RECOVERING")
        self.assertEqual(observation["authority"], "CLOSED")
        with self.assertRaises(ContractError):
            operator.submit("kernel.prepare")
        self.assertEqual(len(client.sent), 1)
        self.assertEqual(operator.draft, draft)

    def test_controlled_later_result_for_uncertain_attempt_is_displayed_without_replay(self):
        operator, service, client, attempt, draft = self.uncertain_operator()
        operator.poll()
        self.assertEqual(strict_loads(operator.result_text.encode("utf8"))["kind"], "TRANSPORT_UNCERTAIN")
        response = self.late_response(service, client, attempt)
        observation = operator.poll()
        self.assertEqual(operator.result_text, response.decode("utf8"))
        self.assertEqual(observation["call"]["attempt"], attempt)
        self.assertEqual(observation["call"]["kind"], "DENIED_RECONCILE")
        self.assertIsNone(observation["pending_attempt"])
        self.assertEqual(operator.draft, draft)
        self.assertEqual(len(client.sent), 1)
        self.assertEqual(len(tuple(service._spool.glob("*.request.json"))), 1)
        self.assertEqual(observation["authority"], "CLOSED")

    def test_controlled_late_result_cannot_overwrite_another_view_or_its_draft(self):
        operator, service, client, attempt, draft = self.uncertain_operator()
        operator.select_view("view:other")
        operator.set_draft("new view draft, retained exactly")
        self.late_response(service, client, attempt)
        operator.poll()
        self.assertEqual(operator.result_text, "")
        self.assertEqual(operator.draft, "new view draft, retained exactly")
        operator.select_view("view:default")
        self.assertEqual(operator.draft, draft)
        self.assertEqual(len(client.sent), 1)

    def test_controlled_returning_to_same_view_does_not_accept_older_callback_generation(self):
        operator, service, client, attempt, draft = self.uncertain_operator()
        operator.select_view("view:other")
        operator.select_view("view:default")
        self.late_response(service, client, attempt)
        operator.poll()
        self.assertEqual(operator.result_text, "")
        self.assertEqual(operator.draft, draft)
        self.assertEqual(len(client.sent), 1)
