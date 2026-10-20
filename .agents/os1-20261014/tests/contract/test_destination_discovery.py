"""Native metadata discovery must resume after explicit local custody clears."""
import sys
import unittest
from unittest.mock import patch

from fixture_paths import native_fixture_path
import test_task_drafts as native_tasks
from test_owned_service import _ServiceTestCase


class DestinationDiscoveryTests(_ServiceTestCase):
    empty_service = native_tasks.NativeTaskDraftTests.empty_service
    task_call = native_tasks.NativeTaskDraftTests.task_call
    durable_cut = native_tasks.NativeTaskDraftTests.durable_cut

    @classmethod
    def setUpClass(cls):
        _ServiceTestCase.setUpClass.__func__(cls)
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(
            ["ceta-native-discovery-regression", "-platform", "offscreen"])

    def test_actual_native_restart_catalog_and_editor_metadata_resume_after_local_draft_guard_clears(self):
        from ceta.application.task_operator import TaskOperatorSession
        from ceta.contracts.local_ipc import decode_message
        from ceta.desktop.task_view import TaskView
        from PySide6.QtWidgets import QMessageBox

        initial, root = self.empty_service()
        stored_task = "task:destination-discovery"
        _, created = self.task_call(initial, "create", task_id=stored_task,
            title="Existing stored task", instruction="Do not dispatch work.", draft="Stored draft")
        self.assertEqual(created.kind, "TASK_SNAPSHOT")
        self.stop(initial)
        before = self.durable_cut(root)
        service, _ = self.empty_service(root=root)
        session = TaskOperatorSession(service, native_tasks.PROJECT)
        session.poll()
        session.set_title("Unconfirmed local draft")
        session.set_draft("Keep this local text while the discovery guard holds.")
        placeholder = session.task_id
        view = TaskView(session)
        view.poll_timer.stop()
        try:
            for _ in range(3):
                view._poll()
            self.assertTrue(session.has_unconfirmed)
            self.assertIsNone(session._pending)
            self.assertFalse(view._catalog_recovery_discovery_started)
            self.assertEqual(tuple(service._spool.glob("*.request.json")), ())
            self.assertEqual(session.draft, "Keep this local text while the discovery guard holds.")

            # This explicit fixture disposition clears exactly the guard; it
            # neither stores the blank draft nor changes the retained task.
            session.set_title("")
            session.set_draft("")
            self.assertFalse(session.has_unconfirmed)
            view._poll()
            self.assertTrue(view._catalog_recovery_discovery_started)
            self.assertEqual(session._pending["kind"], "list")

            def metadata_observed():
                view._poll()
                self.app.processEvents()
                return (stored_task in session.task_ids
                    and session.editor_recovery_status(stored_task) == "ABSENT"
                    and session._pending is None and service._send_task is None)

            self.until(metadata_observed, explanation="actual native catalog/editor discovery did not resume")
            operations = tuple(decode_message(native_fixture_path(path).read_bytes(), self.codec).operation
                for path in service._spool.glob("*.request.json"))
            self.assertCountEqual(operations, ("task.list", "task.editor_load"))
            self.assertEqual(session.task_id, placeholder)
            self.assertFalse(session.created)
            self.assertEqual((session.title, session.draft), ("", ""))
            self.assertEqual(service.snapshot()["authority"], "CLOSED")
            self.stop(service)
            self.assertEqual(self.durable_cut(root), before)
        finally:
            self.stop(service)
            view.poll_timer.stop()
            with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Close):
                view.close()
            view.deleteLater()
            self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
