"""Deterministic retention handoffs over Qt and real fixture SQLite.

The delivery, identity and Stop observations are explicitly controlled. Only
the application's typing-coalescing clock is replaced; protocol/deadline
checks keep their original implementation. Shared fixture helpers and the
original regression body are reused without new authorship credit.
"""
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import test_task_meaning_view as helper


class EditorRetentionQueueTests(helper._MeaningHelpers, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        helper.TaskMeaningViewTests.setUpClass.__func__(cls)

    setUp = helper.TaskMeaningViewTests.setUp
    tearDown = helper.TaskMeaningViewTests.tearDown
    view = helper.TaskMeaningViewTests.view
    poll = helper.TaskMeaningViewTests.poll
    fill = helper.TaskMeaningViewTests.fill
    complete_editor_custody = helper.TaskMeaningViewTests.complete_editor_custody
    assert_raw_editor_recovery = helper.TaskMeaningViewTests.assert_raw_editor_recovery

    def typing_clock(self):
        import ceta.application.task_operator as operator
        clock = SimpleNamespace(value=100.0)
        return clock, patch.object(operator, 'time',
            SimpleNamespace(monotonic=lambda: clock.value))

    def test_original_invalid_field_repair_under_frozen_typing_clock(self):
        _, clock_patch = self.typing_clock()
        with clock_patch:
            # Execute the exact retained original body with this fixture owner.
            helper.TaskMeaningViewTests.test_invalid_last_field_preserves_whole_prior_form_until_atomic_repair(self)

    def test_ordinary_idle_typing_still_coalesces_until_its_deadline(self):
        clock, clock_patch = self.typing_clock()
        with clock_patch:
            view, session, service, fixture = self.view()
            self.fill(view, helper.supplied_meaning('ordinary valid typing'))
            self.poll(view)
            self.assertIsNone(session._pending)
            self.assertEqual(session.editor_recovery_status(), 'QUEUED')
            self.assertEqual([message.operation for message in service.sent], ['task.create'])
            clock.value += .149
            self.poll(view)
            self.assertIsNone(session._pending)
            clock.value += .002
            self.poll(view)
            self.assertIsNotNone(session._pending)
            self.complete_editor_custody(session, service, view)
            self.assert_raw_editor_recovery(view, session, fixture)

    def test_held_acknowledgement_immediately_hands_off_only_the_latest_capture(self):
        _, clock_patch = self.typing_clock()
        with clock_patch:
            view, session, service, fixture = self.view()
            self.fill(view, helper.supplied_meaning('held first capture'))
            session.prioritize_editor_custody()
            self.assertIsNotNone(session._pending)
            self.fill(view, helper.supplied_meaning('superseded intermediate capture'))
            self.fill(view, helper.supplied_meaning('latest complete capture'))
            latest = session.editor_local_payload()
            first = service.complete()
            self.assertEqual(first.kind, 'TASK_EDITOR_RETAINED')
            session.poll()
            self.assertIsNotNone(session._pending)
            self.assertEqual(session.editor_local_payload(), latest)
            self.assertEqual(session.editor_recovery_status(), 'SAVING')
            results = self.complete_editor_custody(session, service, view)
            self.assertEqual(len(results), 1)
            self.assertEqual([message.operation for message in service.sent],
                ['task.create', 'task.editor_retain', 'task.editor_retain'])
            self.assert_raw_editor_recovery(view, session, fixture)
            self.assertEqual(fixture.meaning_cell(session.task_id).generation, 0)
            self.assertEqual(fixture.snapshot(session.task_id)['state'], 'CREATED')

    def test_lost_response_after_commit_keeps_newer_capture_uncertain(self):
        _, clock_patch = self.typing_clock()
        with clock_patch:
            view, session, service, fixture = self.view()
            self.fill(view, helper.supplied_meaning('committed older capture'))
            session.prioritize_editor_custody()
            self.fill(view, helper.supplied_meaning('locally held newer capture'))
            latest = session.editor_local_payload()
            self.assertEqual(service.complete().kind, 'TASK_EDITOR_RETAINED')
            # The real fixture commit happened; its delivery is now lost.
            service.call = {**service.call, 'response': None}
            session.poll()
            self.assertEqual(session.editor_recovery_status(), 'UNCERTAIN')
            self.assertIsNone(session._pending)
            self.assertEqual(session.editor_local_payload(), latest)
            self.assertIsNone(session.editor_recovery_snapshot())
            self.assertEqual([message.operation for message in service.sent],
                ['task.create', 'task.editor_retain'])
            self.assertEqual(fixture.meaning_cell(session.task_id).generation, 0)

    def test_stop_observation_prevents_successor_dispatch_after_acknowledgement(self):
        _, clock_patch = self.typing_clock()
        with clock_patch:
            view, session, service, fixture = self.view()
            self.fill(view, helper.supplied_meaning('held before Stop'))
            session.prioritize_editor_custody()
            self.fill(view, helper.supplied_meaning('newer local capture'))
            latest = session.editor_local_payload()
            service.request_stop()
            self.assertEqual(service.complete().kind, 'TASK_EDITOR_RETAINED')
            session.poll()
            self.assertIsNone(session._pending)
            self.assertEqual(session.editor_local_payload(), latest)
            self.assertEqual([message.operation for message in service.sent],
                ['task.create', 'task.editor_retain'])
            self.assertEqual(fixture.meaning_cell(session.task_id).generation, 0)


if __name__ == '__main__':
    unittest.main()
