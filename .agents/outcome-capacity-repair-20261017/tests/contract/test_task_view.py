"""Controlled task client and real Qt regressions for durable draft custody.

TaskClientTests uses the real task use case, codec, result binding and SQLite
journal with opaque synthetic identity owners. TaskViewTests drives real Qt
controls and holds delivery explicitly. Stop probes additionally exercise the
real OwnedService controller with injected in-memory channels and a held sender.
No native process, OS authentication, ordinary profile, model or effect runs.
The full catalog response is synthetic; it tests client capacity, not storage
capacity. Exact CRLF/NFD/NUL preservation is checked at the captured use-case
boundary, because Qt's text document can normalize displayed line endings.

New application imports occur in helpers so the old application yields a
specific missing-module failure for each test, not an entire discovery error.
"""
from pathlib import Path
from fixture_paths import native_fixture_path
import sys
import threading
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
SCOPE = "project:task-view-fixture"
SESSION = "session:task-view-fixture"


class _SyntheticTaskOwners:
    """Exact opaque context/message bindings; explicitly no native identity."""

    def __init__(self):
        self.context, self.message = None, None

    def capture(self, message):
        self.context, self.message = object(), message
        return self.context

    def require_message(self, context, message):
        from ceta.contracts.kernel_transactions import require
        require(context is self.context and message == self.message,
                "FIXTURE_TASK_MESSAGE_DENIED")

    def authenticate(self, context):
        from ceta.contracts.kernel_transactions import PeerIdentity, require
        require(context is self.context and self.message is not None,
                "FIXTURE_TASK_CONTEXT_DENIED")
        return PeerIdentity("operator:task-view-fixture", self.message.sender_session)

    def task_owner_binding(self, context):
        self.authenticate(context)
        return "sha256:" + "7" * 64


class _TaskStoreFixture:
    def __init__(self):
        from ceta.contracts.wire import RecordCodec, strict_loads
        from ceta.contracts.store_transactions import STORE_PROFILE
        from ceta.store.journal import SqliteJournal
        from ceta.kernel.task_drafts import TaskDrafts
        self.root = ROOT / ".agents/fixtures/task-view-28" / uuid.uuid4().hex
        self.root.mkdir(parents=True, exist_ok=False)
        self.codec = RecordCodec(strict_loads(
            (ROOT / "contracts/schemas/records.schema.json").read_bytes()))
        self.owners = _SyntheticTaskOwners()
        self.store = SqliteJournal(self.root, self.codec, (SCOPE,),
                                   create=True, profile=STORE_PROFILE)
        self.tasks = TaskDrafts(self.store, self.codec, self.owners)

    def message(self, record_wire, operation, *, session=SESSION, attempt=None):
        from ceta.contracts.local_ipc import decode_message, encode_message
        attempt = attempt or uuid.uuid4().hex
        wire = encode_message(record_wire, self.codec,
            message_id="message:" + attempt, correlation_ref="attempt:" + attempt,
            sender_session=session, receiver_generation="f" * 64,
            operation=operation, issued_at_ms=1000, expires_at_ms=2000)
        return decode_message(wire, self.codec)

    def execute(self, message):
        context = self.owners.capture(message)
        return self.tasks(message, context)

    def response(self, message, result):
        from ceta.contracts.local_results import decode_response, encode_response
        return decode_response(encode_response(message, result, self.codec),
                               message, self.codec)

    def cell(self, task_id):
        from ceta.contracts.task_drafts import draft_key
        return self.store.snapshot((draft_key(SCOPE, task_id),))[0]

    def snapshot(self, task_id):
        from ceta.contracts.task_drafts import decode_snapshot
        return decode_snapshot(self.cell(task_id).value_wire)

    def external_save(self, task_id, title, draft):
        from ceta.contracts.task_drafts import command_wire
        wire = command_wire("save", SCOPE, "task-command:" + uuid.uuid4().hex,
            task_id=task_id, expected_revision=self.cell(task_id).revision,
            title=title, draft=draft)
        return self.execute(self.message(wire, "task.save"))

    def reopen(self):
        from ceta.contracts.store_transactions import STORE_PROFILE
        from ceta.store.journal import SqliteJournal
        from ceta.kernel.task_drafts import TaskDrafts
        self.store.close()
        self.store = SqliteJournal(self.root, self.codec, (SCOPE,), profile=STORE_PROFILE)
        self.owners = _SyntheticTaskOwners()
        self.tasks = TaskDrafts(self.store, self.codec, self.owners)

    def close(self):
        self.store.close()


class _ControlledTaskService:
    """Delivery timing port over real task storage, without a native service."""

    def __init__(self, fixture, *, session=SESSION):
        self.fixture, self.session = fixture, session
        self.state, self.detail = "READY", "Controlled task service; authority closed."
        self.pending, self.call = None, None
        self.sent, self.acknowledged = [], []
        self.stop_calls = 0
        self.raise_submission_uncertain = False
        self.observed = None

    def begin_call(self, wire, operation):
        from ceta.contracts.kernel_transactions import require
        from ceta.contracts.local_ipc import SubmissionUncertain
        require(self.pending is None and self.state in {"READY", "RECOVERING"},
                "FIXTURE_CALL_PENDING_OR_STOPPED")
        attempt = uuid.uuid4().hex
        message = self.fixture.message(wire, operation, session=self.session, attempt=attempt)
        self.pending = {"attempt": attempt, "request": message}
        self.sent.append(message)
        self.call = None
        self.state, self.detail = "ACTIVE", "Controlled delivery reserved."
        if self.raise_submission_uncertain:
            self.raise_submission_uncertain = False
            self.state, self.detail = "RECOVERING", "Controlled publication uncertain."
            raise SubmissionUncertain(attempt)
        return attempt

    def complete(self, *, result=None, error=None):
        from ceta.contracts.task_drafts import validate_result
        from ceta.contracts.wire import ContractError
        pending = self.pending
        if pending is None:
            raise AssertionError("No controlled request to complete")
        message = pending["request"]
        if error is not None:
            result = error
        elif result is None:
            try:
                result = self.fixture.execute(message)
            except ContractError as failure:
                result = failure
        response = self.fixture.response(message, result)
        self.call = {"attempt": pending["attempt"], "kind": response.kind,
                     "response": response}
        self.pending = None
        if message.operation == "task.load" and response.task_result is not None:
            self.observed = (message.record.as_dict()["task_id"],
                validate_result(response.task_result, message.record, message.operation))
        if self.state not in {"STOPPING", "STOPPED"}:
            self.state = "RECOVERING" if response.kind == "DENIED_RECONCILE" else "READY"
        self.detail = "Controlled bound result observed; authority closed."
        return response

    def uncertain(self, *, commit=False):
        pending = self.pending
        if pending is None:
            raise AssertionError("No controlled request to make uncertain")
        result = self.fixture.execute(pending["request"]) if commit else None
        self.call = {"attempt": pending["attempt"], "kind": "TRANSPORT_UNCERTAIN"}
        self.pending = None
        if self.state not in {"STOPPING", "STOPPED"}:
            self.state = "RECOVERING"
        self.detail = "Controlled acknowledgment lost; commit status requires a load."
        return result

    def acknowledge_task_reconciliation(self, task_id, revision):
        from ceta.contracts.kernel_transactions import require
        require(self.pending is None and self.observed == (task_id, revision),
                "FIXTURE_OBSERVATION_REQUIRED")
        self.acknowledged.append((task_id, revision))
        self.state, self.detail = "READY", "Controlled current revision selected explicitly."

    def request_stop(self):
        self.stop_calls += 1
        self.state, self.detail = "STOPPING", "Controlled Stop requested; exit unobserved."
        return self.poll()

    def finish_stop(self):
        self.state, self.detail = "STOPPED", "Controlled exit observation supplied."

    def poll(self):
        return {"state": self.state, "detail": self.detail, "authority": "CLOSED",
                "call": self.call,
                "pending_attempt": None if self.pending is None else self.pending["attempt"]}


class _TaskCase(unittest.TestCase):
    def setUp(self):
        self.fixtures = []

    def tearDown(self):
        for fixture in reversed(self.fixtures):
            fixture.close()

    def session(self, *, fixture=None, service=None, session_id=SESSION):
        from ceta.application.task_operator import TaskOperatorSession
        if fixture is None:
            fixture = _TaskStoreFixture()
            self.fixtures.append(fixture)
        if service is None:
            service = _ControlledTaskService(fixture, session=session_id)
        session = TaskOperatorSession(service, SCOPE)
        session.poll()
        return session, service, fixture

    def create(self, session, service, *, title="Task title", draft="Do not activate effects."):
        session.set_title(title)
        session.set_draft(draft)
        session.create()
        response = service.complete()
        self.assertEqual(response.kind, "TASK_SNAPSHOT")
        session.poll()
        self.assertEqual(session.persistence, "SAVED")
        return session.task_id


class TaskClientTests(_TaskCase):
    def test_late_create_acknowledges_submitted_bytes_but_new_edits_stay_dirty(self):
        session, service, fixture = self.session()
        captured = "Do not delete.\r\nExclude Cafe\u0301.\x00Keep this negation.\r\n"
        session.set_title("Cafe\u0301 original")
        session.set_draft(captured)
        session.create()
        session.set_title("new local title")
        session.set_draft("new local draft; do not replace")
        service.complete()
        session.poll()
        stored = fixture.snapshot(session.task_id)
        self.assertEqual(bytes.fromhex(stored["title_hex"]), "Cafe\u0301 original".encode("utf8"))
        self.assertEqual(bytes.fromhex(stored["draft_hex"]), captured.encode("utf8"))
        self.assertEqual(bytes.fromhex(stored["instruction_hex"]), captured.encode("utf8"))
        self.assertEqual(session.original_instruction, captured)
        self.assertEqual((session.title, session.draft),
                         ("new local title", "new local draft; do not replace"))
        self.assertTrue(session.dirty)
        self.assertEqual(session.persistence, "UNSAVED")
        self.assertEqual(session.revision, fixture.cell(session.task_id).revision)

    def test_late_save_keeps_new_title_and_draft_then_explicit_next_save_persists_them(self):
        session, service, fixture = self.session()
        task_id = self.create(session, service)
        original = session.original_instruction
        session.set_title("captured title")
        session.set_draft("captured draft\r\nNo deletion.\x00")
        session.save()
        session.set_title("newer title")
        session.set_draft("newer unsaved draft Cafe\u0301")
        service.complete()
        session.poll()
        stored = fixture.snapshot(task_id)
        self.assertEqual(bytes.fromhex(stored["draft_hex"]), b"captured draft\r\nNo deletion.\x00")
        self.assertEqual(stored["objective_generation"], 2)
        self.assertEqual((session.title, session.draft), ("newer title", "newer unsaved draft Cafe\u0301"))
        self.assertEqual(session.original_instruction, original)
        self.assertTrue(session.dirty)
        self.assertEqual(session.persistence, "UNSAVED")
        session.save()
        service.complete()
        session.poll()
        self.assertEqual(bytes.fromhex(fixture.snapshot(task_id)["draft_hex"]), session.draft.encode("utf8"))
        self.assertEqual(fixture.snapshot(task_id)["objective_generation"], 3)
        self.assertFalse(session.dirty)
        self.assertEqual(session.persistence, "SAVED")

    def test_dirty_load_retains_text_and_requires_explicit_current_cas_adoption(self):
        from ceta.contracts.wire import ContractError
        session, service, fixture = self.session()
        task_id = self.create(session, service)
        old_revision = session.revision
        fixture.external_save(task_id, "other writer title", "other writer draft")
        current_revision = fixture.cell(task_id).revision
        session.set_title("local title")
        session.set_draft("local bytes Cafe\u0301\r\n\x00do not infer consent")
        local = session.title, session.draft
        session.load(task_id)
        service.complete()
        session.poll()
        self.assertEqual((session.title, session.draft), local)
        self.assertEqual(session.revision, old_revision)
        self.assertTrue(session.has_remote)
        before = len(service.sent)
        with self.assertRaisesRegex(ContractError, "TASK_REMOTE_SELECTION_REQUIRED"):
            session.save()
        self.assertEqual(len(service.sent), before)
        session.adopt_current_revision()
        self.assertEqual(service.acknowledged, [(task_id, current_revision)])
        self.assertEqual(session.revision, current_revision)
        self.assertEqual((session.title, session.draft), local)
        self.assertTrue(session.dirty)
        session.save()
        service.complete()
        session.poll()
        self.assertEqual(bytes.fromhex(fixture.snapshot(task_id)["draft_hex"]), local[1].encode("utf8"))

    def test_edits_after_clean_load_dispatch_are_preserved_as_unconfirmed(self):
        session, service, fixture = self.session()
        task_id = self.create(session, service)
        old_revision = session.revision
        fixture.external_save(task_id, "remote", "current stored text")
        session.load(task_id)
        session.set_draft("typed after load dispatch")
        service.complete()
        session.poll()
        self.assertEqual(session.draft, "typed after load dispatch")
        self.assertEqual(session.revision, old_revision)
        self.assertTrue(session.has_remote)
        self.assertTrue(session.dirty)

    def test_stale_save_denial_retains_local_bytes_and_requires_load_then_choice(self):
        session, service, fixture = self.session()
        task_id = self.create(session, service)
        original = session.original_instruction
        session.set_draft("local bytes that must survive denial\r\nCafe\u0301\x00")
        local = session.draft
        fixture.external_save(task_id, "remote title", "new stored revision")
        before = fixture.cell(task_id), fixture.store.store_position()
        session.save()
        response = service.complete()
        self.assertEqual((response.kind, response.error_code),
                         ("DENIED_RECONCILE", "TASK_REVISION_CONFLICT"))
        session.poll()
        self.assertEqual(session.persistence, "CONFLICT")
        self.assertEqual(session.draft, local)
        self.assertEqual(session.original_instruction, original)
        self.assertEqual((fixture.cell(task_id), fixture.store.store_position()), before)
        session.load(task_id)
        service.complete()
        session.poll()
        self.assertEqual(session.draft, local)
        self.assertTrue(session.has_remote)
        session.adopt_current_revision()
        self.assertEqual(session.revision, before[0].revision)
        session.save()
        service.complete()
        session.poll()
        self.assertEqual(bytes.fromhex(fixture.snapshot(task_id)["draft_hex"]), local.encode("utf8"))
        self.assertEqual(session.original_instruction, original)
        self.assertEqual(session.persistence, "SAVED")

    def test_original_instruction_exact_bytes_survive_journal_reopen_and_new_session(self):
        session, service, fixture = self.session()
        original = "Do not erase.\r\nExclude Cafe\u0301.\x00No grant.\r\n"
        task_id = self.create(session, service, title="Cafe\u0301", draft=original)
        session.set_draft("a separately edited draft\r\n\x00still no consent")
        session.save()
        service.complete()
        session.poll()
        before = fixture.cell(task_id)
        fixture.reopen()
        reopened, port, _ = self.session(fixture=fixture, session_id="session:task-view-reopened")
        reopened.load(task_id)
        port.complete()
        reopened.poll()
        self.assertEqual(reopened.original_instruction.encode("utf8"), original.encode("utf8"))
        self.assertEqual(reopened.draft, "a separately edited draft\r\n\x00still no consent")
        self.assertEqual(reopened.revision, before.revision)
        reopened.set_draft("later draft")
        reopened.save()
        port.complete()
        reopened.poll()
        stored = fixture.snapshot(task_id)
        self.assertEqual(bytes.fromhex(stored["instruction_hex"]), original.encode("utf8"))
        self.assertEqual(stored["created_session"], SESSION)
        self.assertEqual(stored["updated_session"], "session:task-view-reopened")
        self.assertEqual(stored["state"], "CREATED")
        self.assertTrue(all(value is None for value in stored["meaning"].values()))

    def test_task_absent_keeps_local_bytes_until_explicit_choice_before_create(self):
        from ceta.contracts.wire import ContractError
        session, service, fixture = self.session()
        session.set_title("retained title")
        session.set_draft("Do not lose local\r\nCafe\u0301\x00")
        task_id, local = session.task_id, (session.title, session.draft)
        session.load(task_id)
        self.assertEqual(service.complete().kind, "TASK_ABSENT")
        session.poll()
        self.assertEqual((session.title, session.draft), local)
        self.assertTrue(session.has_remote)
        self.assertFalse(session.created)
        with self.assertRaisesRegex(ContractError, "TASK_REMOTE_SELECTION_REQUIRED"):
            session.create()
        session.adopt_current_revision()
        self.assertEqual(service.acknowledged, [(task_id, None)])
        self.assertEqual((session.title, session.draft), local)
        session.create()
        service.complete()
        session.poll()
        self.assertEqual(bytes.fromhex(fixture.snapshot(task_id)["instruction_hex"]), local[1].encode("utf8"))

    def test_unchanged_save_does_not_append_or_advance_revision(self):
        session, service, fixture = self.session()
        task_id = self.create(session, service)
        before = fixture.cell(task_id), fixture.store.store_position(), fixture.store.position(SCOPE)
        session.save()
        self.assertEqual(service.complete().kind, "TASK_UNCHANGED")
        session.poll()
        self.assertEqual((fixture.cell(task_id), fixture.store.store_position(),
                          fixture.store.position(SCOPE)), before)
        self.assertEqual(session.persistence, "SAVED")

    def test_controlled_full_256_catalog_is_visitable_without_placeholder_overflow(self):
        from ceta.contracts.task_drafts import TaskResult
        from ceta.contracts.wire import ContractError
        session, service, _ = self.session()
        placeholder = session.task_id
        ids = tuple("task:catalog-" + str(index) for index in range(256))
        session.list_tasks()
        service.complete(result=TaskResult("TASK_LIST", task_ids=ids))
        session.poll()
        self.assertEqual(session.task_ids, ids)
        for index, task_id in enumerate(ids):
            session.select_task(task_id)
            session.set_draft("local retained " + str(index))
        self.assertNotIn(placeholder, session.local_task_ids)
        self.assertEqual(len(session.local_task_ids), 256)
        selected, draft = session.task_id, session.draft
        with self.assertRaisesRegex(ContractError, "TASK_LOCAL_VIEW_CAPACITY"):
            session.new_task()
        self.assertEqual((session.task_id, session.draft), (selected, draft))
        for index, task_id in enumerate(ids):
            session.select_task(task_id)
            self.assertEqual(session.draft, "local retained " + str(index))

    def test_only_untouched_unsent_empty_placeholders_are_reused(self):
        session, service, _ = self.session()
        for _ in range(300):
            session.new_task()
        self.assertEqual(session.local_task_ids, (session.task_id,))
        touched = session.task_id
        session.set_draft("typed then cleared")
        session.set_draft("")
        session.new_task()
        self.assertIn(touched, session.local_task_ids)
        dispatched = session.task_id
        session.load(dispatched)
        session.new_task()
        self.assertIn(dispatched, session.local_task_ids)
        service.complete()
        session.poll()
        session.select_task(dispatched)
        self.assertTrue(session.has_remote)
        session.new_task()
        self.assertIn(dispatched, session.local_task_ids)


class TaskViewTests(_TaskCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(["ceta-task-view-tests", "-platform", "offscreen"])
            cls.app.setQuitOnLastWindowClosed(False)
        print("QT_TASK_VIEW_PLATFORM=" + cls.app.platformName(), flush=True)

    def setUp(self):
        super().setUp()
        self.windows = []

    def tearDown(self):
        from PySide6.QtWidgets import QMessageBox
        try:
            with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Close):
                for window, session, service in reversed(self.windows):
                    if isinstance(service, _ControlledTaskService):
                        service.finish_stop()
                    session.poll()
                    window.close()
                    window.deleteLater()
                self.app.processEvents()
        finally:
            super().tearDown()

    def window(self, *, session=None, service=None):
        from ceta.desktop.task_view import TaskView
        fixture = None
        if session is None:
            session, service, fixture = self.session()
        window = TaskView(session)
        # Real connected signals are driven explicitly; avoid timer races.
        window.poll_timer.stop()
        self.windows.append((window, session, service))
        window.show()
        window.activateWindow()
        self.app.processEvents()
        return window, session, service, fixture

    def click(self, button):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        self.app.processEvents()

    def poll(self, window):
        window.poll_timer.timeout.emit()
        self.app.processEvents()

    def edit(self, window, *, title="Task title", draft="Do not activate effects."):
        window.title_editor.setText(title)
        window.draft_editor.setPlainText(draft)
        self.app.processEvents()

    def test_late_create_and_save_results_do_not_replace_new_widget_text(self):
        window, session, service, fixture = self.window()
        self.edit(window, draft="captured create Cafe\u0301\nDo not erase.")
        captured = window.draft_editor.toPlainText()
        self.click(window.create_button)
        self.edit(window, title="new local title", draft="typed after create")
        service.complete()
        self.poll(window)
        self.assertEqual(bytes.fromhex(fixture.snapshot(session.task_id)["draft_hex"]), captured.encode("utf8"))
        self.assertEqual(window.draft_editor.toPlainText(), "typed after create")
        self.assertEqual(window.title_editor.text(), "new local title")
        self.assertIn("UNSAVED", window.status_label.text())
        self.assertTrue(window.original_editor.isReadOnly())
        self.assertEqual(window.original_editor.toPlainText(), captured)
        self.click(window.save_button)
        self.edit(window, title="third title", draft="typed after save")
        service.complete()
        self.poll(window)
        self.assertEqual(bytes.fromhex(fixture.snapshot(session.task_id)["draft_hex"]), b"typed after create")
        self.assertEqual(window.draft_editor.toPlainText(), "typed after save")
        self.assertEqual(window.title_editor.text(), "third title")
        self.assertIn("UNSAVED", window.status_label.text())

    def test_late_callback_for_another_task_does_not_render_into_current_task(self):
        window, session, service, fixture = self.window()
        self.edit(window, title="first", draft="first exact Cafe\u0301 draft")
        first = session.task_id
        self.click(window.create_button)
        self.click(window.new_button)
        second = session.task_id
        self.edit(window, title="second", draft="second current draft")
        service.complete()
        self.poll(window)
        self.assertEqual(session.task_id, second)
        self.assertEqual(window.draft_editor.toPlainText(), "second current draft")
        self.assertEqual(window.result_editor.toPlainText(), "")
        self.assertEqual(window.original_editor.toPlainText(), "")
        self.assertEqual(bytes.fromhex(fixture.snapshot(first)["draft_hex"]), "first exact Cafe\u0301 draft".encode("utf8"))
        window.local_task_picker.setCurrentText(first)
        self.click(window.local_select_button)
        self.assertEqual(window.draft_editor.toPlainText(), "first exact Cafe\u0301 draft")
        self.assertEqual(window.original_editor.toPlainText(), "first exact Cafe\u0301 draft")
        self.assertEqual(window.result_editor.toPlainText(), "")

    def test_dirty_local_task_can_be_returned_to_without_a_server_load(self):
        window, session, service, _ = self.window()
        first = session.task_id
        self.edit(window, title="A", draft="A exact Cafe\u0301\nDo not delete.")
        original = window.title_editor.text(), window.draft_editor.toPlainText()
        self.click(window.new_button)
        second = session.task_id
        self.edit(window, title="B", draft="B local bytes")
        self.assertEqual(service.sent, [])
        self.assertEqual(window.task_picker.count(), 0)
        window.local_task_picker.setCurrentText(first)
        # A timer refresh between the user's selection and Return must keep
        # that selection, even while the current task is still B.
        self.poll(window)
        self.assertEqual(session.task_id, second)
        self.assertEqual(window.local_task_picker.currentText(), first)
        self.click(window.local_select_button)
        self.assertEqual(session.task_id, first)
        self.assertEqual((window.title_editor.text(), window.draft_editor.toPlainText()), original)
        window.local_task_picker.setCurrentText(second)
        self.poll(window)
        self.assertEqual(window.local_task_picker.currentText(), second)
        self.click(window.local_select_button)
        self.assertEqual(window.draft_editor.toPlainText(), "B local bytes")
        self.assertEqual(service.sent, [])

    def test_dirty_reload_requires_button_selection_of_current_cas_before_save(self):
        window, session, service, fixture = self.window()
        task_id = self.create(session, service)
        self.poll(window)
        before = session.revision
        fixture.external_save(task_id, "remote title", "remote text")
        self.edit(window, title="local title", draft="local preserved text")
        self.click(window.reload_current_button)
        service.complete()
        self.poll(window)
        self.assertEqual(window.draft_editor.toPlainText(), "local preserved text")
        self.assertEqual(window.title_editor.text(), "local title")
        self.assertEqual(session.revision, before)
        self.assertFalse(window.save_button.isEnabled())
        self.assertTrue(window.rebase_button.isEnabled())
        self.click(window.rebase_button)
        self.assertEqual(session.revision, fixture.cell(task_id).revision)
        self.assertEqual(window.draft_editor.toPlainText(), "local preserved text")
        self.assertTrue(window.save_button.isEnabled())
        self.click(window.save_button)
        service.complete()
        self.poll(window)
        self.assertEqual(bytes.fromhex(fixture.snapshot(task_id)["draft_hex"]), b"local preserved text")

    def test_uncertain_uncataloged_create_can_reload_without_another_edit(self):
        window, session, service, _ = self.window()
        self.edit(window, draft="uncertain local instruction")
        task_id = session.task_id
        service.raise_submission_uncertain = True
        self.click(window.create_button)
        self.assertIn("IPC_SUBMISSION_UNCERTAIN", window.detail_label.text())
        service.uncertain(commit=False)
        self.poll(window)
        self.assertEqual(window.task_picker.count(), 0)
        self.assertEqual(session.task_id, task_id)
        self.assertTrue(window.reload_current_button.isEnabled())
        self.assertEqual(window.draft_editor.toPlainText(), "uncertain local instruction")
        self.click(window.reload_current_button)
        self.assertEqual(service.sent[-1].operation, "task.load")
        self.assertEqual(service.sent[-1].record.as_dict()["task_id"], task_id)
        self.assertEqual(service.complete().kind, "TASK_ABSENT")
        self.poll(window)
        self.assertEqual(window.draft_editor.toPlainText(), "uncertain local instruction")
        self.assertFalse(window.create_button.isEnabled())
        self.assertTrue(window.rebase_button.isEnabled())
        self.click(window.rebase_button)
        self.assertTrue(window.create_button.isEnabled())

    def test_uncertain_committed_create_reload_keeps_newer_local_text_dirty(self):
        window, session, service, fixture = self.window()
        self.edit(window, draft="captured original instruction")
        self.click(window.create_button)
        task_id = session.task_id
        service.uncertain(commit=True)
        self.poll(window)
        self.edit(window, draft="newer retained local draft")
        self.assertEqual(session.task_ids, ())
        self.click(window.reload_current_button)
        service.complete()
        self.poll(window)
        self.assertEqual(window.draft_editor.toPlainText(), "newer retained local draft")
        self.assertFalse(window.create_button.isEnabled())
        self.assertFalse(window.save_button.isEnabled())
        self.click(window.rebase_button)
        self.assertEqual(session.original_instruction, "captured original instruction")
        self.assertEqual(session.revision, fixture.cell(task_id).revision)
        self.assertTrue(session.dirty)
        self.assertTrue(window.save_button.isEnabled())

    def test_rejected_oversized_text_is_retained_and_visible_stop_remains_reachable(self):
        window, session, service, _ = self.window()
        self.edit(window, draft="valid draft")
        oversized = "x" * 257
        window.title_editor.setText(oversized)
        self.app.processEvents()
        self.assertEqual(window.title_editor.text(), oversized)
        self.assertEqual(session.title, "Task title")
        self.assertIn("TASK_TEXT_SIZE", window.detail_label.text())
        self.assertFalse(window.create_button.isEnabled())
        self.assertFalse(window.reload_current_button.isEnabled())
        self.assertFalse(window.local_select_button.isEnabled())
        self.assertTrue(window.stop_button.isEnabled())
        self.click(window.stop_button)
        self.assertEqual(service.stop_calls, 1)
        self.assertEqual(service.state, "STOPPING")
        self.assertEqual(window.title_editor.text(), oversized)
        self.assertEqual(window.draft_editor.toPlainText(), "valid draft")
        self.assertEqual(service.sent, [])

    def test_rejected_oversized_instruction_is_retained_and_escape_still_stops(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        window, session, service, _ = self.window()
        self.edit(window, draft="last valid instruction")
        invalid = "x" * 65537
        window.draft_editor.setPlainText(invalid)
        self.app.processEvents()
        self.assertEqual(window.draft_editor.toPlainText(), invalid)
        self.assertEqual(session.draft, "last valid instruction")
        self.assertIn("TASK_TEXT_SIZE", window.detail_label.text())
        self.assertFalse(window.create_button.isEnabled())
        self.assertFalse(window.new_button.isEnabled())
        window.draft_editor.setFocus()
        self.app.processEvents()
        QTest.keyClick(window.draft_editor, Qt.Key.Key_Escape)
        self.app.processEvents()
        self.assertEqual(service.stop_calls, 1)
        self.assertEqual(service.state, "STOPPING")
        self.assertEqual(window.draft_editor.toPlainText(), invalid)
        self.assertEqual(service.sent, [])

    def test_dirty_close_cancel_preserves_editor_service_and_editability(self):
        from PySide6.QtWidgets import QMessageBox
        window, session, service, _ = self.window()
        self.edit(window, draft="unsaved exact draft")
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Cancel) as prompt:
            self.assertFalse(window.close())
        prompt.assert_called_once()
        self.assertTrue(window.isVisible())
        self.assertEqual(service.state, "READY")
        self.assertEqual(service.stop_calls, 0)
        self.assertEqual(window.draft_editor.toPlainText(), "unsaved exact draft")
        self.assertFalse(window.draft_editor.isReadOnly())
        self.assertFalse(window.title_editor.isReadOnly())
        window.draft_editor.setPlainText("continued after cancel")
        self.assertEqual(session.draft, "continued after cancel")

    def test_hidden_dirty_task_requires_close_consent_when_current_task_is_empty(self):
        from PySide6.QtWidgets import QMessageBox
        window, session, service, _ = self.window()
        self.edit(window, draft="hidden draft must not disappear")
        first = session.task_id
        self.click(window.new_button)
        self.assertFalse(session.dirty)
        self.assertTrue(session.has_unconfirmed)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Cancel) as prompt:
            self.assertFalse(window.close())
        prompt.assert_called_once()
        self.assertTrue(window.isVisible())
        self.assertEqual(service.stop_calls, 0)
        window.local_task_picker.setCurrentText(first)
        self.click(window.local_select_button)
        self.assertEqual(window.draft_editor.toPlainText(), "hidden draft must not disappear")

    def test_confirmed_dirty_close_freezes_text_and_waits_for_observed_stopped(self):
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QMessageBox
        window, session, service, _ = self.window()
        self.edit(window, title="frozen title", draft="discard choice captured draft")
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Close) as prompt:
            self.assertFalse(window.close())
        prompt.assert_called_once()
        self.assertEqual(service.state, "STOPPING")
        self.assertEqual(service.stop_calls, 1)
        self.assertTrue(window.isVisible())
        self.assertTrue(window.title_editor.isReadOnly())
        self.assertTrue(window.draft_editor.isReadOnly())
        self.assertFalse(window.new_button.isEnabled())
        self.assertFalse(window.local_select_button.isEnabled())
        self.assertFalse(window.save_button.isEnabled())
        window.draft_editor.setFocus()
        self.app.processEvents()
        QTest.keyClicks(window.draft_editor, "must not append")
        QTest.keyClicks(window.title_editor, "must not append")
        self.assertEqual(window.draft_editor.toPlainText(), "discard choice captured draft")
        self.assertEqual(window.title_editor.text(), "frozen title")
        self.poll(window)
        self.assertTrue(window.isVisible())
        service.finish_stop()
        self.poll(window)
        self.assertEqual(session.status, "STOPPED")
        self.assertFalse(window.isVisible())
        self.assertFalse(window.poll_timer.isActive())

    def _stop_with_owned_sender_held(self, *, escape):
        from ceta.application.task_operator import TaskOperatorSession
        from ceta.composition.owned_service import OwnedService
        from ceta.contracts.local_ipc import decode_message
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from test_owned_service import _ChannelFixture
        fixture = _TaskStoreFixture()
        self.fixtures.append(fixture)
        service = OwnedService(fixture.root, fixture.codec, SCOPE, (SCOPE,))
        client = _ChannelFixture(exit_on_terminate=False)
        server = _ChannelFixture(exit_on_terminate=False)
        service._client, service._service = client, server
        service._generation, service._state = "f" * 64, "READY"
        entered, release = threading.Event(), threading.Event()
        def held_send(command):
            client.sent.append(command)
            entered.set()
            if not release.wait(10):
                raise AssertionError("Controlled send gate was not released")
        client.send = held_send
        session = TaskOperatorSession(service, SCOPE)
        session.poll()
        window, _, _, _ = self.window(session=session, service=service)
        # This rescue can only release this test-owned thread; a synchronous
        # regression fails the unreleased-gate assertion instead of hanging Qt.
        rescue = threading.Timer(5, release.set)
        rescue.daemon = True
        try:
            self.edit(window, draft="exact request before held sender")
            rescue.start()
            self.click(window.create_button)
            self.assertTrue(entered.wait(2), "Real controller sender did not reach controlled channel")
            self.assertFalse(release.is_set(), "Create occupied Qt until held sender completed")
            attempt = service.snapshot()["pending_attempt"]
            request_wire = (native_fixture_path(service._spool / (attempt + ".request.json"))).read_bytes()
            request = decode_message(request_wire, fixture.codec)
            self.assertEqual(bytes.fromhex(request.record.as_dict()["draft_hex"]),
                             b"exact request before held sender")
            window.draft_editor.setPlainText("new local bytes while sender blocked")
            if escape:
                window.draft_editor.setFocus()
                self.app.processEvents()
                self.assertEqual(self.app.focusWidget(), window.draft_editor)
                QTest.keyClick(window.draft_editor, Qt.Key.Key_Escape)
                self.app.processEvents()
            else:
                self.click(window.stop_button)
            self.assertFalse(release.is_set(), "Stop waited for held sender instead of requesting termination")
            self.assertEqual(service.state, "STOPPING")
            self.assertEqual(session.status, "STOPPING")
            self.assertTrue(client.process.terminations)
            self.assertTrue(server.process.terminations)
            self.assertTrue(window.stop_button.isEnabled())
            self.assertEqual(window.draft_editor.toPlainText(), "new local bytes while sender blocked")
            self.assertEqual((native_fixture_path(service._spool / (attempt + ".request.json"))).read_bytes(), request_wire)
            self.assertEqual(service.poll()["state"], "STOPPING")
            self.assertTrue(any(task["thread"] is not None and task["thread"].is_alive()
                                for task in service._workers))
        finally:
            rescue.cancel()
            release.set()
            service.request_stop()
            with service._lock:
                threads = tuple(task["thread"] for task in service._workers if task["thread"] is not None)
            for thread in threads:
                thread.join(timeout=5)
                self.assertFalse(thread.is_alive(), "Controlled sender cleanup remains unresolved")
            client.process.finish()
            server.process.finish()
            self.assertEqual(service.poll()["state"], "STOPPED")
            session.poll()

    def test_visible_stop_requests_owned_termination_while_sender_is_held(self):
        self._stop_with_owned_sender_held(escape=False)

    def test_escape_requests_owned_termination_from_editor_while_sender_is_held(self):
        self._stop_with_owned_sender_held(escape=True)


if __name__ == "__main__":
    unittest.main()
