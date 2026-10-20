"""Two bounded independent handoff/denial checks; actual Qt/SQLite, controlled delivery."""
import unittest
import test_task_meaning_view as helper
import test_editor_retention_queue as inherited


class IndependentRetentionChecks(helper._MeaningHelpers, unittest.TestCase):
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
    typing_clock = inherited.EditorRetentionQueueTests.typing_clock

    def test_successor_uses_acknowledged_cas_without_early_durability_or_duplicate_dispatch(self):
        from ceta.contracts.task_drafts import validate_result
        from ceta.contracts.wire import canonical_bytes
        _, clock_patch = self.typing_clock()
        with clock_patch:
            view, session, service, fixture = self.view()
            self.fill(view, helper.supplied_meaning('first retained capture'))
            session.prioritize_editor_custody()
            first = service.pending['request']
            self.fill(view, helper.supplied_meaning('current raw capture'))
            latest = session.editor_local_payload()
            response = service.complete()
            first_revision = validate_result(response.task_result, first.record, first.operation)
            session.poll()
            pending = session._pending
            self.assertIsNotNone(pending)
            self.assertEqual(session.editor_recovery_status(), 'SAVING')
            self.assertNotEqual(canonical_bytes(session.editor_recovery_snapshot()['payload']), latest)
            self.assertEqual(session.editor_recovery_snapshot()['request_id'], first.record.record_id)
            self.assertEqual(pending['command'].as_dict()['editor_expected_revision'], first_revision)
            for _ in range(3):
                session.poll()
                self.assertIs(session._pending, pending)
                self.assertEqual(len(service.sent), 3)
            results = self.complete_editor_custody(session, service, view)
            self.assertEqual(len(results), 1)
            self.assertEqual(session.editor_recovery_status(), 'RETAINED')
            self.assert_raw_editor_recovery(view, session, fixture)
            self.assertEqual(fixture.meaning_cell(session.task_id).generation, 0)
            self.assertEqual(fixture.snapshot(session.task_id)['state'], 'CREATED')

    def test_old_retain_denial_never_dispatches_a_newer_capture(self):
        _, clock_patch = self.typing_clock()
        with clock_patch:
            view, session, service, fixture = self.view()
            self.fill(view, helper.supplied_meaning('held old request'))
            session.prioritize_editor_custody()
            self.fill(view, helper.supplied_meaning('newer local request'))
            latest = session.editor_local_payload()
            fixture.external_draft(session.task_id, 'New canonical task basis')
            before = fixture.store.store_position()
            response = service.complete()
            self.assertEqual(response.kind, 'DENIED_RECONCILE')
            for _ in range(3): session.poll()
            self.assertIsNone(session._pending)
            self.assertEqual(session.editor_recovery_status(), 'CONFLICT')
            self.assertEqual(session.editor_local_payload(), latest)
            self.assertEqual([message.operation for message in service.sent], ['task.create', 'task.editor_retain'])
            self.assertEqual(fixture.store.store_position(), before)
            self.assertIsNotNone(session._entry()['editor_uncertain_command'])
            self.assertEqual(fixture.meaning_cell(session.task_id).generation, 0)
