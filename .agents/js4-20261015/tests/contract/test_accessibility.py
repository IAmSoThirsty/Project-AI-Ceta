"""Real Qt widgets and controlled notification delivery, without UIA qualification."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from PySide6.QtCore import Qt
from PySide6.QtGui import QAccessible
from PySide6.QtWidgets import QApplication, QLabel, QPlainTextEdit, QPushButton, QWidget
from ceta.desktop.accessibility import AccessibleBindings


class AccessibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["ceta-a11y-tests", "-platform", "offscreen"])

    def setUp(self):
        self.owner = QWidget()
        self.label = QLabel("Actual status", self.owner)
        self.binding = AccessibleBindings(self.owner, self.label, name="Public state", interval_ms=50)
        self.addCleanup(self.owner.deleteLater)
        self.addCleanup(self.binding.close)

    def observed(self, state, context="task:one"):
        self.binding.bind_state(context_id=context, state=state)

    def delivered(self, callback):
        events = []
        def observe(event):
            events.append((event.message(), event.politeness(), event.object()))
        with patch.object(self.binding, "_foreground", return_value=True), \
                patch.object(QAccessible, "updateAccessibility", side_effect=observe):
            callback(events)
        return events

    def test_disabled_reason_is_semantic_and_cannot_enable_action(self):
        button = QPushButton("Action", self.owner)
        button.setEnabled(False)
        self.binding.describe_action(button, name="Save draft", description="Request persistence.",
                                     unavailable_reason="A stored task is required.")
        self.assertFalse(button.isEnabled())
        self.assertEqual(button.accessibleName(), "Save draft")
        self.assertIn("Unavailable: A stored task is required.", button.accessibleDescription())
        button.setEnabled(True)
        self.binding.describe_action(button, name="Save draft", description="Request persistence.")
        self.assertEqual(button.accessibleDescription(), "Request persistence.")

    def test_missing_disabled_reason_and_oversize_text_fail_before_mutating_widget(self):
        button = QPushButton("Action", self.owner)
        button.setEnabled(False)
        for kwargs in ({"description": "Request"},
                       {"description": "x" * 1024, "unavailable_reason": "reason"}):
            with self.subTest(kwargs=tuple(kwargs)), self.assertRaises(ValueError):
                self.binding.describe_action(button, name="Action", **kwargs)
            self.assertEqual(button.accessibleName(), "")
            self.assertFalse(button.isEnabled())

    def test_foreign_widgets_and_duplicate_focus_order_are_refused(self):
        foreign = QWidget()
        self.addCleanup(foreign.deleteLater)
        with self.assertRaises(ValueError):
            self.binding.describe_action(foreign, name="Foreign", description="Outside")
        with self.assertRaises(ValueError):
            self.binding.set_focus_order((self.label, self.label))
        with self.assertRaises(ValueError):
            AccessibleBindings(self.owner, QLabel("Outside", foreign), name="Outside")

    def test_native_focus_order_and_read_only_text_retain_documents(self):
        first, editor, last = QPushButton("First", self.owner), QPlainTextEdit(self.owner), QPushButton("Last", self.owner)
        editor.setReadOnly(True)
        editor.setPlainText("Original retained instruction")
        self.binding.set_focus_order((first, editor, self.label, last))
        self.assertIs(first.nextInFocusChain(), editor)
        self.assertTrue(editor.tabChangesFocus())
        self.assertTrue(editor.isReadOnly())
        self.assertEqual(editor.toPlainText(), "Original retained instruction")
        self.assertEqual(self.label.focusPolicy(), Qt.FocusPolicy.StrongFocus)

    def test_invalid_state_bounds_and_duplicate_fields_are_rejected(self):
        for state in ([], (), (("State", "x" * 161),), (("State", "READY"), ("State", "STOPPED")),
                      (("State", "\ud800"),), (("State", "\0"),)):
            with self.subTest(state_type=type(state).__name__), self.assertRaises(ValueError):
                self.observed(state)
        self.assertEqual(self.binding.observed_state, ())

    def test_latest_state_coalesces_without_restarting_active_timer(self):
        def action(events):
            self.observed((("Service", "READY"),))
            timer_id = self.binding._timer.timerId()
            for i in range(50):
                self.observed((("Service", "READY"), ("Count", str(i))))
                self.assertEqual(self.binding._timer.timerId(), timer_id)
            self.assertTrue(self.binding.announce_delta())
            self.assertEqual(len(events), 1)
            self.assertIn("Count: 49", events[0][0])
            self.assertIs(events[0][2], self.label)
        self.delivered(action)

    def test_unchanged_poll_and_return_to_announced_state_are_silent(self):
        def action(events):
            ready = (("Service", "READY"),)
            self.observed(ready)
            self.assertTrue(self.binding.announce_delta())
            for _ in range(100):
                self.observed(ready)
            self.assertFalse(self.binding.announce_delta())
            self.observed((("Service", "STOPPING"),))
            self.observed(ready)
            self.assertFalse(self.binding.announce_delta())
            self.assertEqual(len(events), 1)
        self.delivered(action)

    def test_context_switch_cancels_old_pending_state(self):
        def action(events):
            self.observed((("Service", "STOPPING"),), "task:old")
            self.observed((("Service", "READY"),), "task:new")
            self.assertTrue(self.binding.announce_delta())
            self.assertEqual(events[0][0], "Public state. Service: READY")
        self.delivered(action)

    def test_urgent_and_normal_states_request_explicit_politeness(self):
        def action(events):
            self.observed((("Service", "READY"),))
            self.binding.announce_delta()
            self.observed((("Service", "STOPPING"),))
            self.binding.announce_delta()
            self.assertEqual([item[1] for item in events],
                [QAccessible.AnnouncementPoliteness.Polite, QAccessible.AnnouncementPoliteness.Assertive])
        self.delivered(action)

    def test_hidden_native_widget_does_not_emit(self):
        self.owner.hide()
        self.observed((("Service", "READY"),))
        with patch.object(QAccessible, "updateAccessibility") as update:
            self.assertFalse(self.binding.announce_delta())
        update.assert_not_called()

    def test_native_delivery_failure_is_sanitized_and_same_state_can_retry(self):
        self.observed((("Service", "READY"),))
        with patch.object(self.binding, "_foreground", return_value=True), \
                patch.object(QAccessible, "updateAccessibility", side_effect=RuntimeError("PRIVATE DETAIL")):
            self.assertFalse(self.binding.announce_delta())
        self.assertEqual(self.binding.last_error, "ACCESSIBILITY_ANNOUNCEMENT_FAILED")
        events = self.delivered(lambda _events: self.assertTrue(self.binding.announce_delta()))
        self.assertEqual(len(events), 1)
        self.assertIsNone(self.binding.last_error)

    def test_close_cancels_only_pending_notification(self):
        state = (("Service", "READY"),)
        self.observed(state)
        self.binding.close()
        self.assertEqual(self.binding.observed_state, state)
        self.assertFalse(self.binding.announce_delta())
        self.assertFalse(self.binding._timer.isActive())

    def test_actual_qt_accepts_native_announcement_request(self):
        self.observed((("Service", "READY"),))
        with patch.object(self.binding, "_foreground", return_value=True):
            self.assertTrue(self.binding.announce_delta())
        self.assertIsNone(self.binding.last_error)


class ConnectedAccessibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["ceta-a11y-connected", "-platform", "offscreen"])

    def setUp(self):
        import test_task_view as fixtures
        from ceta.application.task_operator import TaskOperatorSession
        self.fixture = fixtures._TaskStoreFixture()
        self.service = fixtures._ControlledTaskService(self.fixture)
        self.session = TaskOperatorSession(self.service, fixtures.SCOPE)
        self.session.poll()
        self.session.set_title("PRIVATE TITLE")
        self.session.set_draft("PRIVATE DRAFT BODY")
        self.session.create()
        self.service.complete()
        self.session.poll()
        self.views = []

    def tearDown(self):
        self.session.stop()
        if self.service.pending is not None:
            self.service.complete()
        self.service.finish_stop()
        self.session.poll()
        for view in self.views:
            if hasattr(view, "poll_timer"):
                view.poll_timer.stop()
            view.accessibility.close()
            if hasattr(view, "inspector"):
                view.inspector.accessibility.close()
            view.hide()
            view.deleteLater()
        self.app.processEvents()
        self.fixture.close()

    def test_task_controls_are_named_and_stop_precedes_notification_work(self):
        from ceta.desktop.task_view import TaskView
        view = TaskView(self.session)
        self.views.append(view)
        view.poll_timer.stop()
        self.assertEqual(view.stop_button.accessibleName(), "Stop owned service")
        self.assertTrue(view.original_editor.isReadOnly())
        self.assertTrue(view.original_editor.tabChangesFocus())
        state_text = repr(view.accessibility.observed_state)
        self.assertNotIn("PRIVATE TITLE", state_text)
        self.assertNotIn("PRIVATE DRAFT BODY", state_text)
        seen = []
        original = view.accessibility.bind_state
        def observe(**kwargs):
            seen.append(self.service.stop_calls)
            return original(**kwargs)
        with patch.object(view.accessibility, "bind_state", side_effect=observe):
            view.stop_button.click()
        self.assertTrue(seen)
        self.assertTrue(all(value == 1 for value in seen))

    def test_meaning_fields_keep_focus_and_closed_authority_descriptions(self):
        from ceta.desktop.meaning_view import MeaningView
        view = MeaningView(self.session)
        self.views.append(view)
        view.poll_timer.stop()
        self.assertIn("unaccepted", view.propose_button.accessibleName())
        self.assertIn("does not accept", view.propose_button.accessibleDescription())
        self.assertTrue(view.original_editor.tabChangesFocus())
        self.assertNotIn("PRIVATE DRAFT BODY", repr(view.accessibility.observed_state))

    def test_unavailable_compiler_is_explained_without_enabling_preparation(self):
        from ceta.desktop.preparation_view import PreparationView
        view = PreparationView(self.session)
        self.views.append(view)
        view.poll_timer.stop()
        self.assertFalse(view.prepare_button.isEnabled())
        self.assertIn("No compiler owner", view.prepare_button.accessibleDescription())
        self.assertIn(("Compiler", "Unavailable"), view.accessibility.observed_state)
        self.assertNotIn("PRIVATE DRAFT BODY", repr(view.accessibility.observed_state))

    def test_evidence_pages_announce_only_page_numbers_and_keep_actual_bytes(self):
        from ceta.desktop.preparation_view import ByteInspector
        view = ByteInspector()
        self.views.append(view)
        raw = b"PRIVATE EVIDENCE BYTES" * 800
        view.set_items({"PRIVATE SOURCE TITLE": ("bytes", raw)})
        self.assertEqual({name for name, _ in view.accessibility.observed_state}, {"Page", "Total pages"})
        self.assertEqual(dict(view.accessibility.observed_state)["Page"], "1")
        self.assertTrue(view.next_button.isEnabled())
        view.next_button.click()
        self.assertEqual(dict(view.accessibility.observed_state)["Page"], "2")
        self.assertNotIn("PRIVATE", repr(view.accessibility.observed_state))
        self.assertEqual(view._items["PRIVATE SOURCE TITLE"], ("bytes", raw))


if __name__ == "__main__":
    unittest.main()
