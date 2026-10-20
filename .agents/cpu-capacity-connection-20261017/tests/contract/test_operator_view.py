"""Actual Qt controls with an injected controlled session, not original B cases.

These focused development tests do not launch native services, read profiles,
exercise real approvals/effects or qualify B113/B115/B116. The controlled
session owns callback correlation; root's service tests verify that real seam.
"""
from pathlib import Path
import sys
import unittest

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QPlainTextEdit, QPushButton

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts.wire import ContractError
from ceta.desktop.operator_view import OPERATIONS, create_operator_window


class ControlledSession:
    """Deterministic test port, explicitly no process/termination evidence."""

    def __init__(self):
        self.view_ref = "view:first"
        self.view_generation = 1
        self.views = {"view:first": "first draft", "view:second": "second draft"}
        self.draft = self.views[self.view_ref]
        self.status = "READY"
        self.detail = "Development fixture service; positive authority unavailable."
        self.result_text = ""
        self.submitted = []
        self.stop_calls = 0
        self.poll_calls = 0
        self.ignored_callbacks = 0
        self.pending = []
        self.fail_draft = False
        self.fail_submit = False
        self.fail_stop = False
        self.fail_poll = False
        self.fail_select = False

    def set_draft(self, text):
        if self.fail_draft:
            raise ContractError("DRAFT_UNAVAILABLE", "$/private/fixture")
        self.draft = text
        self.views[self.view_ref] = text

    def submit(self, operation):
        self.submitted.append((operation, self.draft, self.view_generation))
        if self.fail_submit:
            self.status = "RECOVERING"
            self.detail = "Returned denial; prior mutation is unresolved."
            raise ContractError("TRANSPORT_RESULT_UNAVAILABLE", "$/private/fixture")
        self.status = "ACTIVE"
        self.detail = "Awaiting actual correlated result."

    def stop(self):
        self.stop_calls += 1
        if self.fail_stop:
            self.status = "DEGRADED"
            raise ContractError("STOP_UNAVAILABLE", "$/private/fixture")
        self.view_generation += 1
        self.status = "STOPPING"
        self.detail = "Stop requested; exit not observed."

    def poll(self):
        self.poll_calls += 1
        if self.fail_poll:
            raise ContractError("POLL_UNAVAILABLE", "$/private/fixture")
        rows, self.pending = self.pending, []
        for token, text in rows:
            if token != (self.view_ref, self.view_generation) or self.status in {"STOPPING", "STOPPED"}:
                self.ignored_callbacks += 1
                continue
            self.result_text = text
            self.status = "READY"
            self.detail = "Controlled correlated result observed."

    def select_view(self, view_ref):
        if self.fail_select:
            raise ContractError("VIEW_UNAVAILABLE", "$/private/fixture")
        self.views[self.view_ref] = self.draft
        self.view_ref = view_ref
        self.view_generation += 1
        self.draft = self.views.get(view_ref, "")
        self.result_text = ""
        self.status = "READY"
        self.detail = "Selected development view."


class OperatorViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            # A test-owned Qt application; no normal desktop or global config.
            cls.app = QApplication(["ceta-operator-view-tests", "-platform", "offscreen"])
            cls.app.setQuitOnLastWindowClosed(False)
        print("QT_OPERATOR_VIEW_PLATFORM=" + cls.app.platformName(), flush=True)

    def setUp(self):
        self.session = ControlledSession()
        self.window = create_operator_window(self.session)
        self.window.show()
        self.window.activateWindow()
        self.app.processEvents()
        self.draft = self.window.findChild(QPlainTextEdit, "record_draft")
        self.picker = self.window.findChild(QComboBox, "operation_picker")
        self.submit = self.window.findChild(QPushButton, "submit_request")
        self.stop = self.window.findChild(QPushButton, "stop_service")
        self.result = self.window.findChild(QPlainTextEdit, "operation_result")
        self.status = self.window.findChild(QLabel, "operator_status")
        self.detail = self.window.findChild(QLabel, "operator_detail")

    def tearDown(self):
        self.session.fail_draft = self.session.fail_stop = self.session.fail_poll = False
        self.session.status = "STOPPED"
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def poll_now(self):
        # Dispatch the real connected Qt signal without relying on wall timing.
        self.window.poll_timer.timeout.emit()
        self.app.processEvents()

    def click(self, button):
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        self.app.processEvents()

    def test_edit_and_real_submit_preserve_draft_on_transport_denial(self):
        text = '{"synthetic":"draft retained"}\n'
        self.draft.setPlainText(text)
        self.session.fail_submit = True
        self.click(self.submit)
        self.assertEqual(self.draft.toPlainText(), text)
        self.assertEqual(self.session.draft, text)
        self.assertEqual(self.session.submitted[0][1], text)
        self.assertIn("RECOVERING", self.status.text())
        self.assertIn("TRANSPORT_RESULT_UNAVAILABLE", self.detail.text())
        self.assertIn("unresolved", self.detail.text())
        self.assertNotIn("private/fixture", self.detail.text())

    def test_draft_rejection_preserves_editor_and_does_not_submit(self):
        self.session.fail_draft = True
        text = "local unsaved draft"
        self.draft.setPlainText(text)
        self.click(self.submit)
        self.assertEqual(self.draft.toPlainText(), text)
        self.assertEqual(self.session.submitted, [])
        self.assertIn("DRAFT_UNAVAILABLE", self.detail.text())

    def test_each_current_operation_picker_calls_only_injected_session(self):
        self.assertEqual(tuple(self.picker.itemText(i) for i in range(self.picker.count())), OPERATIONS)
        self.assertEqual(len(OPERATIONS), 6)
        self.assertIn("kernel.recover_preparation", OPERATIONS)
        for operation in OPERATIONS:
            self.session.status = "READY"
            self.poll_now()
            self.picker.setCurrentText(operation)
            self.click(self.submit)
            self.assertEqual(self.session.submitted[-1][0], operation)

    def test_active_request_disables_duplicate_submission_but_keeps_stop_enabled(self):
        self.click(self.submit)
        self.assertEqual(self.session.status, "ACTIVE")
        self.assertFalse(self.submit.isEnabled())
        self.assertTrue(self.stop.isEnabled())
        self.click(self.submit)
        self.assertEqual(len(self.session.submitted), 1)

    def test_visible_stop_remains_available_when_draft_save_fails(self):
        self.session.fail_draft = True
        self.draft.setPlainText("unsaved retained text")
        self.click(self.stop)
        self.assertEqual(self.session.stop_calls, 1)
        self.assertEqual(self.session.status, "STOPPING")
        self.assertEqual(self.draft.toPlainText(), "unsaved retained text")
        self.assertIn("DRAFT_UNAVAILABLE", self.detail.text())

    def test_escape_stops_owned_session_from_editor_focus(self):
        self.draft.setFocus()
        self.app.processEvents()
        self.assertEqual(self.app.focusWidget(), self.draft)
        QTest.keyClick(self.draft, Qt.Key.Key_Escape)
        self.app.processEvents()
        self.assertEqual(self.session.stop_calls, 1)
        self.assertEqual(self.session.status, "STOPPING")
        self.assertTrue(self.stop.isVisible())

    def test_timer_polls_session_without_overwriting_current_editor(self):
        text = "still typing this draft"
        self.draft.setPlainText(text)
        # Even a stale session draft field cannot be loaded by ordinary refresh.
        self.session.draft = "stale callback draft"
        before = self.session.poll_calls
        self.poll_now()
        self.assertGreater(self.session.poll_calls, before)
        self.assertEqual(self.draft.toPlainText(), text)
        self.assertTrue(self.window.poll_timer.isActive())

    def test_actual_timer_delivers_poll_on_qt_event_loop(self):
        before = self.session.poll_calls
        QTest.qWait(100)
        self.assertGreater(self.session.poll_calls, before)

    def test_per_view_drafts_survive_switch_and_late_result_is_not_rendered(self):
        self.draft.setPlainText("first retained draft")
        token = (self.session.view_ref, self.session.view_generation)
        self.click(self.submit)
        self.window.select_view("view:second")
        self.assertEqual(self.draft.toPlainText(), "second draft")
        self.draft.setPlainText("second current draft")
        self.session.pending.append((token, "STALE FIRST VIEW RESULT"))
        self.poll_now()
        self.assertEqual(self.session.ignored_callbacks, 1)
        self.assertEqual(self.draft.toPlainText(), "second current draft")
        self.assertNotIn("STALE FIRST VIEW RESULT", self.result.toPlainText())
        self.window.select_view("view:first")
        self.assertEqual(self.draft.toPlainText(), "first retained draft")
        self.assertEqual(self.session.views["view:second"], "second current draft")

    def test_view_selection_error_leaves_current_draft_and_result_intact(self):
        self.draft.setPlainText("retained view draft")
        self.session.result_text = "previous genuine fixture result"
        self.poll_now()
        self.session.fail_select = True
        self.window.select_view("view:second")
        self.assertEqual(self.session.view_ref, "view:first")
        self.assertEqual(self.draft.toPlainText(), "retained view draft")
        self.assertEqual(self.result.toPlainText(), "previous genuine fixture result")
        self.assertIn("VIEW_UNAVAILABLE", self.detail.text())

    def test_close_waits_for_observed_stopped_and_cancellation_ignores_late_result(self):
        self.draft.setPlainText("draft before close")
        token = (self.session.view_ref, self.session.view_generation)
        self.click(self.submit)
        self.assertFalse(self.window.close())
        self.app.processEvents()
        self.assertTrue(self.window.isVisible())
        self.assertEqual(self.session.status, "STOPPING")
        self.assertEqual(self.session.stop_calls, 1)
        self.assertIn("Waiting for observed", self.detail.text())
        self.session.pending.append((token, "LATE CANCELLED RESULT"))
        self.poll_now()
        self.assertNotIn("LATE CANCELLED RESULT", self.result.toPlainText())
        self.assertTrue(self.window.isVisible())
        self.session.status = "STOPPED"  # Fixture observation, no real process proof.
        self.poll_now()
        self.assertFalse(self.window.isVisible())
        self.assertFalse(self.window.poll_timer.isActive())
        self.assertEqual(self.session.views["view:first"], "draft before close")

    def test_close_stop_failure_stays_open_and_visible_stop_can_retry(self):
        self.session.fail_stop = True
        self.assertFalse(self.window.close())
        self.assertTrue(self.window.isVisible())
        self.assertIn("STOP_UNAVAILABLE", self.detail.text())
        self.assertTrue(self.stop.isEnabled())
        self.session.fail_stop = False
        self.click(self.stop)
        self.assertEqual(self.session.stop_calls, 2)
        self.assertEqual(self.session.status, "STOPPING")

    def test_poll_error_preserves_draft_result_and_close_uncertainty(self):
        self.draft.setPlainText("retained despite poll failure")
        self.session.result_text = "retained result"
        self.poll_now()
        self.session.fail_poll = True
        self.poll_now()
        self.assertEqual(self.draft.toPlainText(), "retained despite poll failure")
        self.assertEqual(self.result.toPlainText(), "retained result")
        self.assertIn("POLL_UNAVAILABLE", self.detail.text())
        self.assertTrue(self.stop.isEnabled())

    def test_unsaved_draft_failure_keeps_stopped_window_open_until_draft_is_saved(self):
        self.session.status = "STOPPED"
        self.session.fail_draft = True
        self.draft.setPlainText("must not disappear on close")
        self.assertFalse(self.window.close())
        self.assertTrue(self.window.isVisible())
        self.assertEqual(self.draft.toPlainText(), "must not disappear on close")
        self.session.fail_draft = False
        self.assertTrue(self.window.close())
        self.assertEqual(self.session.draft, "must not disappear on close")

    def test_accessible_names_focus_order_plain_status_and_read_only_result(self):
        controls = (self.draft, self.picker, self.submit, self.stop, self.result, self.status, self.detail)
        self.assertTrue(all(widget.accessibleName() for widget in controls))
        self.assertTrue(self.result.isReadOnly())
        self.assertEqual(self.status.textFormat(), Qt.TextFormat.PlainText)
        self.assertEqual(self.detail.textFormat(), Qt.TextFormat.PlainText)
        self.assertEqual(self.status.text(), "Service status: READY")
        self.assertEqual(self.window.stop_shortcut.context(), Qt.ShortcutContext.WindowShortcut)
        self.assertFalse(self.window.stop_shortcut.autoRepeat())
        self.draft.setFocus()
        self.app.processEvents()
        for expected in (self.picker, self.submit, self.stop, self.result):
            QTest.keyClick(self.app.focusWidget(), Qt.Key.Key_Tab)
            self.app.processEvents()
            self.assertEqual(self.app.focusWidget(), expected)
        self.assertNotIn("Approve", " ".join(button.text() for button in self.window.findChildren(QPushButton)))

    def test_service_phases_are_textual_and_stop_remains_reachable(self):
        for state in ("STARTING", "READY", "ACTIVE", "RECOVERING", "STOPPING", "STOPPED", "DEGRADED"):
            with self.subTest(state=state):
                self.session.status = state
                self.poll_now()
                self.assertEqual(self.status.text(), "Service status: " + state)
                self.assertTrue(self.stop.isEnabled())
                self.assertTrue(self.stop.isVisible())
                self.assertEqual(self.submit.isEnabled(), state in {"READY", "RECOVERING", "DEGRADED"})


if __name__ == "__main__":
    unittest.main()
