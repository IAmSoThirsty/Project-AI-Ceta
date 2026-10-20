"""Connected intake tests: controlled timing and separate actual native cases.

ControlledContextIntakeTests uses the real task journal with synthetic identity
and delivery timing. NativeContextIntakeTests uses the actual disposable Windows
OwnedService/client/pipe path. Both use explicitly controlled compiler ports;
neither qualifies a production model, authority owner, normal profile or UI.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from fixture_paths import native_fixture_path
import sys
import threading
import time
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import test_task_drafts as native_patterns
import test_owned_service as service_patterns
import test_task_view as controlled_patterns
from test_request_compiler import _CompilerFixture, _payload, _tokens, _snapshot


class _RecordingCompiler:
    def __init__(self, fixture):
        self.fixture = fixture
        self.compiles, self.revalidations = [], []
        self.result_transform = self.revalidation_transform = None

    def compile_loaded_task(self, wire, profile, output_tokens, cancelled):
        self.compiles.append((wire, profile, output_tokens, cancelled.__self__))
        result = self.fixture.compiler.compile_loaded_task(wire, profile, output_tokens, cancelled)
        return result if self.result_transform is None else self.result_transform(result)

    def revalidate(self, prepared, cancelled):
        self.revalidations.append((prepared, cancelled.__self__))
        value = self.fixture.compiler.revalidate(prepared, cancelled)
        return value if self.revalidation_transform is None else self.revalidation_transform(value)


class ControlledContextIntakeTests(unittest.TestCase):
    def setUp(self):
        self.fixtures, self.sessions, self.gates = [], [], []

    def until(self, predicate, seconds=5):
        deadline = time.monotonic() + seconds
        while True:
            value = predicate()
            if value:
                return value
            if time.monotonic() >= deadline:
                self.fail("controlled compiler worker observation timed out")
            time.sleep(0.002)

    def setup_session(self, *, compiler=True):
        from ceta.application.task_operator import TaskOperatorSession
        fixture = controlled_patterns._TaskStoreFixture()
        self.fixtures.append(fixture)
        service = controlled_patterns._ControlledTaskService(fixture)
        ports = _CompilerFixture(codec=fixture.codec)
        recording = _RecordingCompiler(ports)
        session = TaskOperatorSession(service, controlled_patterns.SCOPE,
                                      recording if compiler else None)
        self.sessions.append((session, service))
        session.poll()
        session.set_title("Intake fixture")
        session.set_draft('NO. Do not erase "excluded".\r\nCafe\u0301\x00')
        session.create()
        service.complete()
        session.poll()
        self.assertEqual(session.persistence, "SAVED")
        return session, service, fixture, ports, recording

    def complete_preview(self, session, service, *, action=None):
        attempt = (action or session.begin_context_preview)(output_tokens=8)
        self.assertEqual(service.sent[-1].operation, "task.load")
        self.assertEqual(session.context_status, "LOADING")
        service.complete()
        session.poll()
        self.until(lambda: (session.poll(), session.context_status not in {"LOADING", "COMPILING"})[1])
        return attempt

    def tearDown(self):
        for gate in self.gates:
            gate.set()
        for session, service in self.sessions:
            session.stop()
            service.finish_stop()
            self.until(lambda: (session.poll(), session._context_job is None)[1])
            self.assertEqual(session.status, "STOPPED")
        for fixture in self.fixtures:
            fixture.close()

    def test_public_preview_requires_fresh_load_before_compiler_and_preserves_saved_bytes(self):
        from ceta.contracts.task_drafts import decode_command, validate_result
        s, service, fixture, ports, compiler = self.setup_session()
        before = fixture.store.store_position()
        submitted = len(service.sent)
        attempt = s.begin_context_preview(output_tokens=8)
        self.assertEqual(len(service.sent), submitted + 1)
        self.assertEqual(service.sent[-1].operation, "task.load")
        self.assertEqual(compiler.compiles, [])
        response = service.complete()
        s.poll()
        self.until(lambda: (s.poll(), s.context_status == "PREVIEW")[1])
        command_wire, response_wire, revision = s.context_native_observation
        self.assertEqual(decode_command(command_wire), service.sent[-1].record)
        self.assertEqual(response_wire, response.original_response)
        self.assertEqual(revision, validate_result(response.task_result, service.sent[-1].record, "task.load"))
        self.assertEqual(compiler.compiles[0][0], response.task_result.snapshot_wire)
        self.assertEqual(s.context_result.prepared.payload, _payload(s.context_result.prepared.parts))
        self.assertEqual(s.context_result.prepared.tokenization.token_ids, _tokens(s.context_result.prepared.payload))
        self.assertEqual(s.original_instruction.encode("utf8"), s.context_result.task.original)
        self.assertEqual(service.call["attempt"], attempt)
        self.assertEqual(fixture.store.store_position(), before)
        self.assertEqual(service.poll()["authority"], "CLOSED")

    def test_missing_compiler_and_dirty_draft_do_not_issue_a_load(self):
        from ceta.contracts.wire import ContractError
        s, service, _, _, _ = self.setup_session(compiler=False)
        before = len(service.sent)
        with self.assertRaises(ContractError) as caught:
            s.begin_context_preview(output_tokens=8)
        self.assertEqual(caught.exception.code, "REQUEST_COMPILER_OWNER_UNAVAILABLE")
        self.assertEqual(len(service.sent), before)
        s, service, _, _, compiler = self.setup_session()
        s.set_draft("Unsaved raw input remains here.")
        before = len(service.sent)
        with self.assertRaises(ContractError) as caught:
            s.begin_context_preview(output_tokens=8)
        self.assertEqual(caught.exception.code, "CONTEXT_SAVED_TASK_REQUIRED")
        self.assertEqual(s.draft, "Unsaved raw input remains here.")
        self.assertEqual(len(service.sent), before)
        self.assertEqual(compiler.compiles, [])

    def test_edit_during_native_load_preserves_text_and_refuses_old_basis_compilation(self):
        s, service, _, _, compiler = self.setup_session()
        s.begin_context_preview(output_tokens=8)
        s.set_draft("Newer local bytes; never replace these.")
        service.complete(); s.poll()
        self.assertEqual(s.context_status, "STALE")
        self.assertEqual(s.context_error, "CONTEXT_TASK_OR_LOCAL_CHANGED")
        self.assertEqual(s.draft, "Newer local bytes; never replace these.")
        self.assertTrue(s.dirty)
        self.assertTrue(s.has_remote)
        self.assertEqual(compiler.compiles, [])

    def test_changed_saved_task_and_a_b_a_cannot_reuse_prior_preview(self):
        s, service, fixture, _, compiler = self.setup_session()
        self.complete_preview(s, service)
        old = s.context_result
        original = s.saved_draft
        fixture.external_save(s.task_id, s.title, "B")
        fixture.external_save(s.task_id, s.title, original)
        s.begin_context_revalidation()
        service.complete(); s.poll()
        self.assertEqual(s.context_status, "STALE")
        self.assertIs(s.context_result, old)
        self.assertEqual(compiler.revalidations, [])
        self.assertNotEqual(s.revision, old.task.task_revision)
        self.assertEqual(s.draft, original)

    def test_revalidation_issues_fresh_load_and_uses_same_cancellation_owner(self):
        s, service, _, _, compiler = self.setup_session()
        self.complete_preview(s, service)
        old = s.context_result
        sent = len(service.sent)
        s.begin_context_revalidation()
        self.assertEqual(len(service.sent), sent + 1)
        self.assertEqual(service.sent[-1].operation, "task.load")
        self.assertEqual(compiler.revalidations, [])
        service.complete(); s.poll()
        self.until(lambda: (s.poll(), s.context_status == "PREVIEW")[1])
        self.assertIs(s.context_result, old)
        self.assertEqual(len(compiler.compiles), 1)
        self.assertIs(compiler.revalidations[0][0], old.prepared)
        self.assertIs(compiler.revalidations[0][1], compiler.compiles[0][3])

    def test_well_typed_foreign_task_result_is_denied_without_changing_loaded_task(self):
        from ceta.contracts.request_compiler import CompilationResult, TaskInput
        s, service, _, _, compiler = self.setup_session()
        task_id, draft = s.task_id, s.draft
        foreign = TaskInput.from_snapshot(_snapshot(task_id="task:foreign-result"))
        compiler.result_transform = lambda result: CompilationResult("DENIED", foreign,
                                                reason_code="CONTROLLED_FOREIGN_RESULT")
        self.complete_preview(s, service)
        self.assertEqual((s.context_status, s.context_error), ("DENIED", "CONTEXT_RESULT_TASK_BINDING"))
        self.assertIsNone(s.context_result)
        self.assertEqual((s.task_id, s.draft), (task_id, draft))
        self.assertIsNotNone(s.context_native_observation)

    def test_substituted_revalidation_object_is_denied_and_old_result_remains_readable(self):
        s, service, _, _, compiler = self.setup_session()
        self.complete_preview(s, service)
        old = s.context_result
        compiler.revalidation_transform = lambda prepared: replace(prepared)
        s.begin_context_revalidation()
        service.complete(); s.poll()
        self.until(lambda: (s.poll(), s.context_status != "COMPILING")[1])
        self.assertEqual((s.context_status, s.context_error), ("DENIED", "CONTEXT_REVALIDATION_SUBSTITUTED"))
        self.assertIs(s.context_result, old)
        self.assertEqual(s.context_result.prepared.payload, old.prepared.payload)

    def test_late_worker_result_stays_with_captured_task_and_preserves_new_selected_text(self):
        s, service, _, ports, _ = self.setup_session()
        old_id = s.task_id
        ports.render_entered, ports.render_release = threading.Event(), threading.Event()
        self.gates.append(ports.render_release)
        s.begin_context_preview(output_tokens=8); service.complete(); s.poll()
        self.assertTrue(ports.render_entered.wait(2))
        new_id = s.new_task()
        s.set_title("New selected title"); s.set_draft("Selected new local bytes.")
        ports.render_release.set()
        self.until(lambda: (s.poll(), s._context_job is None)[1])
        self.assertEqual((s.task_id, s.draft), (new_id, "Selected new local bytes."))
        self.assertIsNone(s.context_result)
        s.select_task(old_id)
        self.assertEqual(s.context_status, "PREVIEW")
        self.assertEqual(s.context_result.task.task_id, old_id)

    def test_stop_keeps_blocked_worker_owned_until_completion_is_observed(self):
        s, service, _, ports, _ = self.setup_session()
        ports.render_entered, ports.render_release = threading.Event(), threading.Event()
        self.gates.append(ports.render_release)
        s.begin_context_preview(output_tokens=8); service.complete(); s.poll()
        self.assertTrue(ports.render_entered.wait(2))
        worker = s._context_job["thread"]
        cancel = s._context_job["cancel"]
        s.stop(); service.finish_stop(); s.poll()
        self.assertTrue(cancel.is_set())
        self.assertTrue(worker.is_alive())
        self.assertEqual(s.status, "STOPPING")
        self.assertIsNotNone(s._context_job)
        ports.render_release.set()
        self.until(lambda: (s.poll(), s._context_job is None)[1])
        self.assertFalse(worker.is_alive())
        self.assertEqual((s.status, s.context_status), ("STOPPED", "CANCELLED"))

    def test_submitted_load_uncertainty_retains_captured_attempt_and_never_replays(self):
        from ceta.contracts.local_ipc import SubmissionUncertain
        s, service, _, _, compiler = self.setup_session()
        task_id, draft = s.task_id, s.draft
        sent = len(service.sent)
        service.raise_submission_uncertain = True
        with self.assertRaises(SubmissionUncertain) as caught:
            s.begin_context_preview(output_tokens=8)
        self.assertEqual(s.context_status, "UNCERTAIN")
        self.assertEqual(service.pending["attempt"], caught.exception.attempt)
        self.assertEqual(service.sent[-1].operation, "task.load")
        service.uncertain(); s.poll()
        for _ in range(3): s.poll()
        self.assertEqual((s.status, s.context_status), ("RECOVERING", "UNCERTAIN"))
        self.assertEqual((s.task_id, s.draft), (task_id, draft))
        self.assertEqual(len(service.sent), sent + 1)
        self.assertEqual(compiler.compiles, [])

    def test_replacement_more_than_registry_capacity_preserves_historical_bytes(self):
        s, service, _, _, compiler = self.setup_session()
        past = []
        for _ in range(70):
            self.complete_preview(s, service)
            self.assertEqual(s.context_status, "PREVIEW")
            past.append(s.context_result)
        self.assertEqual(len(compiler.compiles), 70)
        self.assertEqual(len({x.prepared.commitment for x in past}), 70)
        self.assertTrue(all(x.prepared.payload == _payload(x.prepared.parts) for x in past))
        self.assertTrue(all(x.task.original == past[0].task.original for x in past))

    def test_worker_baseexceptions_reach_terminal_denial_with_observation_and_draft_retained(self):
        for exception_type in (SystemExit, KeyboardInterrupt):
            with self.subTest(exception_type=exception_type.__name__):
                s, service, _, _, compiler = self.setup_session()
                draft, instruction, task_id = s.draft, s.original_instruction, s.task_id
                def failure(_result, exception_type=exception_type):
                    raise exception_type("private worker detail must not be returned")
                compiler.result_transform = failure
                s.begin_context_preview(output_tokens=8)
                service.complete(); s.poll()
                self.until(lambda: (s.poll(), s._context_job is None)[1])
                s.poll(); s.poll()
                self.assertEqual((s.context_status, s.context_error),
                                 ("DENIED", "CONTEXT_COMPILER_FAILED"))
                self.assertEqual((s.task_id, s.draft, s.original_instruction),
                                 (task_id, draft, instruction))
                self.assertIsNotNone(s.context_native_observation)
                self.assertIsNone(s.context_result)
                self.assertTrue(compiler.compiles[-1][3].is_set())
                self.assertNotIn("private worker detail", str(s.context_error))

    def test_worker_construction_failure_retires_absent_worker_and_preserves_prior_result(self):
        for exception_type in (RuntimeError, KeyboardInterrupt, SystemExit):
            with self.subTest(exception_type=exception_type.__name__):
                s, service, fixture, _, compiler = self.setup_session()
                self.complete_preview(s, service)
                prior = s.context_result
                draft, instruction, revision = s.draft, s.original_instruction, s.revision
                saved = fixture.cell(s.task_id)
                compiles = len(compiler.compiles)
                s.begin_context_preview(output_tokens=8)
                service.complete()
                with patch("ceta.application.task_operator.threading.Thread",
                           side_effect=exception_type("private construction detail")):
                    if issubclass(exception_type, Exception):
                        s.poll()
                    else:
                        with self.assertRaises(exception_type):
                            s.poll()
                s.poll()
                self.assertFalse(s.context_busy)
                self.assertEqual((s.context_status, s.context_error),
                                 ("DENIED", "CONTEXT_WORKER_CONSTRUCTION_FAILED"))
                self.assertIs(s.context_result, prior)
                self.assertEqual((s.draft, s.original_instruction, s.revision),
                                 (draft, instruction, revision))
                self.assertEqual(fixture.cell(s.task_id), saved)
                self.assertEqual(len(compiler.compiles), compiles)
                self.assertIsNotNone(s.context_native_observation)
                s.stop(); service.finish_stop(); s.poll()
                self.assertEqual(s.status, "STOPPED")

    def test_interrupted_start_without_visible_thread_retains_custody_until_actual_completion(self):
        for exception_type in (RuntimeError, KeyboardInterrupt):
            with self.subTest(exception_type=exception_type.__name__):
                s, service, fixture, _, compiler = self.setup_session()
                saved = fixture.cell(s.task_id)
                s.begin_context_preview(output_tokens=8)
                service.complete()
                # This controlled launch deliberately delays entry; ident=None
                # and is_alive=False must not let the application discard it.
                with patch.object(threading.Thread, "start",
                                  side_effect=exception_type("private launch detail")):
                    if issubclass(exception_type, Exception):
                        s.poll()
                    else:
                        with self.assertRaises(exception_type):
                            s.poll()
                job = s._context_job
                thread = job["thread"]
                try:
                    self.assertIsNone(thread.ident)
                    self.assertFalse(thread.is_alive())
                    self.assertFalse(job["done"].is_set())
                    s.poll()
                    self.assertEqual(s.context_status, "LAUNCH_UNCERTAIN")
                    self.assertTrue(s.context_busy)
                    self.assertIs(s._context_job, job)
                    s.stop(); service.finish_stop(); s.poll()
                    self.assertEqual(s.status, "STOPPING")
                    self.assertIn("launch is unresolved", s.detail)
                    self.assertTrue(job["cancel"].is_set())
                    self.assertEqual(compiler.compiles, [])
                    self.assertEqual(fixture.cell(s.task_id), saved)
                finally:
                    # Observe this retained launch rather than manufacturing an
                    # absence receipt in the test or clearing application state.
                    thread.start()
                self.until(lambda: (s.poll(), not s.context_busy)[1])
                self.assertFalse(thread.is_alive())
                self.assertEqual((s.status, s.context_status), ("STOPPED", "CANCELLED"))
                self.assertEqual(fixture.cell(s.task_id), saved)

    def test_start_then_raise_retains_running_worker_through_stop(self):
        for exception_type in (RuntimeError, KeyboardInterrupt):
            with self.subTest(exception_type=exception_type.__name__):
                s, service, fixture, ports, _ = self.setup_session()
                saved = fixture.cell(s.task_id)
                ports.render_entered, ports.render_release = threading.Event(), threading.Event()
                self.gates.append(ports.render_release)
                original_start = threading.Thread.start
                def start_then_raise(thread):
                    original_start(thread)
                    if not ports.render_entered.wait(2):
                        raise AssertionError("actual worker did not enter")
                    raise exception_type("private post-launch detail")
                s.begin_context_preview(output_tokens=8)
                service.complete()
                with patch.object(threading.Thread, "start", new=start_then_raise):
                    if issubclass(exception_type, Exception):
                        s.poll()
                    else:
                        with self.assertRaises(exception_type):
                            s.poll()
                job = s._context_job
                s.stop(); service.finish_stop(); s.poll()
                self.assertTrue(job["thread"].is_alive())
                self.assertEqual(s.status, "STOPPING")
                self.assertIs(s._context_job, job)
                self.assertTrue(job["cancel"].is_set())
                ports.render_release.set()
                self.until(lambda: (s.poll(), not s.context_busy)[1])
                self.assertFalse(job["thread"].is_alive())
                self.assertEqual((s.status, s.context_status), ("STOPPED", "CANCELLED"))
                self.assertEqual(fixture.cell(s.task_id), saved)

    def test_service_observed_stop_cancels_and_retains_the_live_compiler_without_session_stop(self):
        for native_state in ("STOPPING", "STOPPED"):
            with self.subTest(native_state=native_state):
                s, service, _, ports, _ = self.setup_session()
                draft, instruction = s.draft, s.original_instruction
                ports.render_entered, ports.render_release = threading.Event(), threading.Event()
                self.gates.append(ports.render_release)
                s.begin_context_preview(output_tokens=8)
                service.complete(); s.poll()
                self.until(ports.render_entered.is_set)
                job = s._context_job
                worker, cancel = job["thread"], job["cancel"]
                # Service observation models its independent timeout/exit path.
                # This deliberately does not call the session's Stop method.
                service.state, service.detail = native_state, "Independent service Stop observed."
                s.poll()
                self.assertTrue(cancel.is_set())
                self.assertTrue(worker.is_alive())
                self.assertIs(s._context_job, job)
                self.assertEqual(s.status, "STOPPING")
                self.assertEqual(service.stop_calls, 0)
                service.finish_stop(); s.poll()
                self.assertEqual(s.status, "STOPPING")
                self.assertIs(s._context_job, job)
                ports.render_release.set()
                self.until(lambda: (s.poll(), s._context_job is None and s.status == "STOPPED")[1])
                self.assertFalse(worker.is_alive())
                self.assertEqual(s.context_status, "CANCELLED")
                self.assertEqual((s.draft, s.original_instruction), (draft, instruction))
                self.assertIsNotNone(s.context_native_observation)


class NativeContextIntakeTests(service_patterns._ServiceTestCase):
    """Actual Windows transport; controlled cognitive/time/reservation ports only."""
    empty_service = native_patterns.NativeTaskDraftTests.empty_service
    task_call = native_patterns.NativeTaskDraftTests.task_call
    response_revision = native_patterns.NativeTaskDraftTests.response_revision

    def directory(self):
        result = ROOT / ".agents/fixtures/context-intake-30" / uuid.uuid4().hex
        result.mkdir(parents=True, exist_ok=False)
        return result

    def durable_read_cut(self, root):
        # Read-only, one consistent SQLite snapshot; no second journal writer.
        from ceta.store.sqlite_runtime import load_sqlite
        sqlite3 = load_sqlite()
        db = sqlite3.connect((root / "history.sqlite3").as_uri() + "?mode=ro", uri=True)
        try:
            db.execute("BEGIN")
            return tuple((table, tuple(sorted(db.execute('SELECT * FROM "' + table + '"').fetchall(), key=repr)))
                for table in ("history_meta", "history_scopes", "history_events",
                              "store_commits", "store_changes", "store_cells"))
        finally:
            db.close()

    def session_fixture(self):
        from ceta.application.task_operator import TaskOperatorSession
        service, root = self.empty_service()
        original = 'NO. Do not erase "excluded".\r\nCafe\u0301\x00'
        _, created = self.task_call(service, "create", task_id="task:native-context",
            title="Native context", instruction=original, draft=original)
        _, saved = self.task_call(service, "save", task_id="task:native-context",
            title="Native context", draft="Saved latest input only.\r\nCafe\u0301",
            expected_revision=self.response_revision(created))
        ports = _CompilerFixture(codec=self.codec)
        recording = _RecordingCompiler(ports)
        session = TaskOperatorSession(service, native_patterns.PROJECT, recording)
        session.poll(); session.load("task:native-context")
        self.until(lambda: (session.poll(), session.created and session.status == "READY"
                            and session._pending is None and service._send_task is None)[1])
        return session, service, root, ports, recording, saved

    def preview_observed(self, session):
        def observed():
            session.poll()
            if session.context_status in {"DENIED", "UNCERTAIN", "STALE", "ABSENT"}:
                self.fail("native intake outcome: " + str((session.context_status, session.context_error)))
            return session.context_result if session.context_status == "PREVIEW" else None
        return self.until(observed, explanation="actual native intake never produced controlled preview")

    def stop_session(self, session, service):
        session.stop()
        self.until(lambda: (session.poll(), session._context_job is None
                            and session.status == "STOPPED")[1])
        self.stop(service)
        self.assertEqual(service.poll()["authority"], "CLOSED")

    def test_actual_native_create_save_load_intake_has_exact_bytes_payload_and_bound_response(self):
        from ceta.contracts.local_ipc import decode_message
        from ceta.contracts.local_results import decode_response
        from ceta.contracts.request_compiler import byte_commitment
        s, service, root, _, compiler, saved = self.session_fixture()
        before = self.durable_read_cut(root)
        with patch.object(service, "begin_call", wraps=service.begin_call) as actual_load:
            attempt = s.begin_context_preview(output_tokens=8)
            result = self.preview_observed(s)
        self.assertEqual(actual_load.call_count, 1)
        self.assertEqual(actual_load.call_args.args[1], "task.load")
        request_wire = (native_fixture_path(service._spool / (attempt + ".request.json"))).read_bytes()
        response_wire = (native_fixture_path(service._spool / (attempt + ".response.json"))).read_bytes()
        request = decode_message(request_wire, self.codec)
        response = decode_response(response_wire, request, self.codec)
        self.assertEqual(request.operation, "task.load")
        self.assertEqual(response.task_result, saved.task_result)
        self.assertEqual(s.context_native_observation[0], request.record.original_wire)
        self.assertEqual(s.context_native_observation[1], response_wire)
        self.assertEqual(compiler.compiles[0][0], response.task_result.snapshot_wire)
        self.assertEqual(result.prepared.payload, _payload(result.prepared.parts))
        self.assertEqual(result.prepared.tokenization.token_ids, _tokens(result.prepared.payload))
        self.assertIn(b'NO. Do not erase "excluded".\r\nCafe\xcc\x81\x00', result.prepared.payload)
        self.assertEqual(result.prepared.context.as_dict()["payload_commitment"], byte_commitment(result.prepared.payload))
        self.assertEqual(result.prepared.context.as_dict()["objective_revision"], result.task.objective_revision)
        self.assertEqual(service.poll()["authority"], "CLOSED")
        self.assertEqual(self.durable_read_cut(root), before)
        self.stop_session(s, service)
        self.assertEqual(self.durable_read_cut(root), before)
        (root / "compiler-intake-witness.json").write_text(json.dumps({
            "qualification": "ACTUAL_NATIVE_TASK_CUSTODY_WITH_CONTROLLED_COMPILER_PORTS",
            "model_authority_qualification": "NOT_ESTABLISHED", "attempt": attempt,
            "request_sha256": hashlib.sha256(request_wire).hexdigest(),
            "response_sha256": hashlib.sha256(response_wire).hexdigest(),
            "payload_commitment": result.prepared.context.as_dict()["payload_commitment"],
            "task_revision": result.task.task_revision, "objective_revision": result.task.objective_revision,
            "tables_unchanged": 6, "cleanup": "STOPPED", "authority": "CLOSED"}, indent=2), encoding="utf8")

    def test_actual_native_stop_retires_services_but_not_a_blocked_compiler_worker(self):
        s, service, root, ports, _, _ = self.session_fixture()
        before = self.durable_read_cut(root)
        ports.render_entered, ports.render_release = threading.Event(), threading.Event()
        try:
            s.begin_context_preview(output_tokens=8)
            self.until(lambda: (s.poll(), ports.render_entered.is_set())[1])
            worker = s._context_job["thread"]
            cancel = s._context_job["cancel"]
            s.stop()
            self.until(lambda: service.poll()["state"] == "STOPPED")
            s.poll()
            self.assertTrue(cancel.is_set())
            self.assertTrue(worker.is_alive())
            self.assertEqual(s.status, "STOPPING")
            self.assertIsNotNone(s._context_job)
            ports.render_release.set()
            self.until(lambda: (s.poll(), s._context_job is None and s.status == "STOPPED")[1])
            self.assertFalse(worker.is_alive())
            self.assertEqual(s.context_status, "CANCELLED")
            self.assertEqual(service.poll()["authority"], "CLOSED")
            self.assertEqual(self.durable_read_cut(root), before)
        finally:
            ports.render_release.set()
            s.stop()
            self.until(lambda: (s.poll(), s._context_job is None)[1])

    def test_actual_successful_intake_read_does_not_clear_prior_kernel_denial_or_enable_acceptance(self):
        from ceta.contracts.wire import canonical_bytes
        from test_all_records import example
        s, service, root, _, _, _ = self.session_fixture()
        before = self.durable_read_cut(root)
        action = example(self.schema["$defs"]["ActionProposal"])
        action.update(record_id="proposal:native-context-denied", scope_id=native_patterns.PROJECT,
                      task_id=s.task_id)
        _, denial = self.call(service, canonical_bytes(action), "kernel.prepare")
        self.assertEqual((denial.kind, denial.error_code), ("DENIED_RECONCILE", "KERNEL_REQUIRED_STATE_MISSING"))
        self.until(lambda: service.poll()["state"] == "RECOVERING" and service._send_task is None)
        s.poll(); s.begin_context_preview(output_tokens=8)
        result = self.preview_observed(s)
        self.assertEqual((service.poll()["state"], service.poll()["authority"]), ("RECOVERING", "CLOSED"))
        self.assertEqual(result.reason_code, "UNACCEPTED_REQUEST_PREVIEW")
        self.assertIsNone(denial.record_wire)
        self.assertIsNone(denial.event_wire)
        self.assertEqual(self.durable_read_cut(root), before)
        self.stop_session(s, service)
        self.assertEqual(self.durable_read_cut(root), before)

    def test_controlled_missing_pipe_native_load_keeps_exact_request_and_recovery_without_replay(self):
        from ceta.contracts.local_ipc import decode_message
        s, service, root, _, compiler, _ = self.session_fixture()
        before = self.durable_read_cut(root)
        task_id, draft = s.task_id, s.draft
        original_send = service._client.send
        missing_pipe = r"\\.\pipe\CETA-" + uuid.uuid4().hex
        redirected = []
        def send_to_missing_pipe(command):
            altered = dict(command, pipe=missing_pipe, timeout_ms=100)
            redirected.append((dict(command), altered))
            return original_send(altered)
        # Controlled failure stimulus; transport/client/native API still run.
        with patch.object(service._client, "send", send_to_missing_pipe):
            attempt = s.begin_context_preview(output_tokens=8)
            self.until(lambda: (s.poll(), s.context_status == "UNCERTAIN"
                and service._send_task is None and service._pending is None)[1])
        self.assertEqual(len(redirected), 1)
        self.assertNotEqual(redirected[0][0]["pipe"], redirected[0][1]["pipe"])
        request_wire = (native_fixture_path(service._spool / (attempt + ".request.json"))).read_bytes()
        request = decode_message(request_wire, self.codec)
        self.assertEqual((request.operation, request.record.as_dict()["task_id"]), ("task.load", task_id))
        self.assertFalse((native_fixture_path(service._spool / (attempt + ".response.json"))).exists())
        self.assertEqual((s.task_id, s.draft), (task_id, draft))
        self.assertEqual(compiler.compiles, [])
        for _ in range(3): s.poll()
        self.assertEqual((s.status, s.context_status), ("RECOVERING", "UNCERTAIN"))
        fresh_attempt = s.begin_context_preview(output_tokens=8)
        self.assertNotEqual(fresh_attempt, attempt)
        self.preview_observed(s)
        self.assertEqual(service.poll()["state"], "RECOVERING")
        self.assertEqual((native_fixture_path(service._spool / (attempt + ".request.json"))).read_bytes(), request_wire)
        self.assertFalse((native_fixture_path(service._spool / (attempt + ".response.json"))).exists())
        self.assertEqual(len(compiler.compiles), 1)
        self.assertEqual(self.durable_read_cut(root), before)
        self.stop_session(s, service)
        self.assertEqual(self.durable_read_cut(root), before)
