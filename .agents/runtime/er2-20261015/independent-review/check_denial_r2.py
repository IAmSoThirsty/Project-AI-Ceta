"""One real recovery CAS denial over controlled delivery and actual Qt/SQLite."""
import functools
import json
import os
from pathlib import Path
import sys
import threading
import unittest
import uuid
from review_support import F, Q, R, V, MANIFEST, read, s


def main():
    assert len(sys.argv) == 1
    output = V / 'denial-r2'
    output.mkdir(exist_ok=False)
    temporary = output / 'temporary'
    temporary.mkdir()
    os.environ.update(QT_QPA_PLATFORM='offscreen', TEMP=str(temporary), TMP=str(temporary))
    sys.path[:0] = [str(Q / 'src'), str(Q / 'tools'), str(Q / 'tests/contract')]
    from ceta.store.sqlite_runtime import load_sqlite, runtime_identity
    sqlite = load_sqlite()
    from resource_observer import Observer
    from run_review import FixtureRoot
    import test_task_meaning_view as helper
    from independent_retention_checks import IndependentRetentionChecks
    parent = Path(read(V / 'PREPARATION.json')['fixture_root'])
    fixture = parent / 'controlled-denial-r2'
    assert not fixture.exists()
    fixture.mkdir(exist_ok=False)
    helper.ROOT = FixtureRoot(fixture)
    observer = Observer(sqlite)
    @functools.wraps(observer.original_connect)
    def connect(*args, **kwargs): return observer.connect(*args, **kwargs)
    sqlite.connect = connect
    facts = []

    class DenialCheck(helper._MeaningHelpers, unittest.TestCase):
        @classmethod
        def setUpClass(cls): helper.TaskMeaningViewTests.setUpClass.__func__(cls)
        setUp = helper.TaskMeaningViewTests.setUp
        tearDown = helper.TaskMeaningViewTests.tearDown
        view = helper.TaskMeaningViewTests.view
        fill = helper.TaskMeaningViewTests.fill
        typing_clock = IndependentRetentionChecks.typing_clock

        def test_real_recovery_revision_conflict_keeps_latest_capture_and_requires_reconciliation(self):
            from ceta.contracts.task_drafts import command_wire
            _, clock_patch = self.typing_clock()
            with clock_patch:
                view, session, service, store = self.view()
                accepted = (store.draft_cell(session.task_id), store.kernel_cell(session.task_id),
                    store.meaning_cell(session.task_id))
                self.fill(view, helper.supplied_meaning('held old recovery'))
                first_payload = session.editor_local_payload()
                session.prioritize_editor_custody()
                held = service.pending['request']
                held_command = session._pending['command']
                self.fill(view, helper.supplied_meaning('latest raw capture stays local'))
                latest = session.editor_local_payload()
                external = command_wire('editor_retain', helper.SCOPE, 'task-command:' + uuid.uuid4().hex,
                    task_id=session.task_id, editor_payload=first_payload, editor_expected_revision=None)
                committed = store.execute(store.message(external, 'task.editor_retain',
                    session='session:independent-recovery-cas'))
                self.assertEqual(committed.kind, 'TASK_EDITOR_RETAINED')
                position = store.store.store_position()
                denied = service.complete()
                self.assertEqual(denied.kind, 'DENIED_RECONCILE')
                self.assertEqual(denied.error_code, 'EDITOR_REVISION_CONFLICT')
                for _ in range(3): session.poll()
                self.assertIsNone(session._pending)
                self.assertIsNone(service.pending)
                self.assertEqual(session.editor_recovery_status(), 'CONFLICT')
                self.assertEqual(session.editor_recovery_error(), 'EDITOR_REVISION_CONFLICT')
                self.assertEqual(session.editor_local_payload(), latest)
                self.assertIsNone(session.editor_recovery_snapshot())
                self.assertIs(session._entry()['editor_uncertain_command'], held_command)
                self.assertEqual([message.operation for message in service.sent], ['task.create', 'task.editor_retain'])
                self.assertEqual(store.store.store_position(), position)
                self.assertEqual((store.draft_cell(session.task_id), store.kernel_cell(session.task_id),
                    store.meaning_cell(session.task_id)), accepted)
                facts.append({'denial': denied.error_code, 'held_request_id': held.record.record_id,
                    'external_request_id': committed.command_id if hasattr(committed, 'command_id') else None,
                    'latest_raw_capture_preserved': True, 'current_capture_durable_claimed': False,
                    'automatic_successor_requests': 0, 'accepted_cells_unchanged': True})

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(DenialCheck)
    expected = [test.id() for test in suite]
    executed, stopped = [], []
    baseline = set(threading.enumerate())
    class Result(unittest.TextTestResult):
        def startTest(self, test): executed.append(test.id()); super().startTest(test)
        def stopTest(self, test): stopped.append(test.id()); super().stopTest(test)
    try:
        with (output / 'RAW.txt').open('x', encoding='utf-8', newline='\n') as stream:
            result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Result).run(suite)
    finally: sqlite.connect = observer.original_connect
    physical = observer.finish()
    threads = [thread.name for thread in threading.enumerate() if thread not in baseline and thread.is_alive()]
    success = (result.wasSuccessful() and not result.skipped and expected == executed == stopped
        and len(expected) == 1 and physical['sqlite'] and physical['owned_resources_closed'] and not threads)
    proof = {'at': s.utc(), 'manifest_sha256': MANIFEST, 'tests_run': result.testsRun,
        'expected_ids': expected, 'executed_ids': executed, 'stopped_ids': stopped,
        'failures': len(result.failures), 'errors': len(result.errors), 'skips': len(result.skipped),
        'failure_details': [(test.id(), detail) for test, detail in result.failures],
        'error_details': [(test.id(), detail) for test, detail in result.errors],
        'physical_resources': physical, 'remaining_threads': threads, 'facts': facts,
        'canonical_policy': 'kernel/editor_recovery.py:_next_retain121 preserves raw prior basis; apply203-204 requires exact recovery CAS.',
        'prior_incorrect_oracle': s.reference(V / 'connected-r1/RESULT.json'),
        'fixture_root': str(fixture), 'sqlite_runtime': runtime_identity(), 'raw': s.reference(output / 'RAW.txt'),
        'new_native_service_lifetimes': 0, 'Source_publication': False, 'full_gate_complete': False,
        'exit_status': 0 if success else 1}
    s.write_new(output / 'RESULT.json', proof)
    print(json.dumps({'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'sqlite_connections': len(physical['sqlite']), 'exit_status': proof['exit_status']}), flush=True)
    return proof['exit_status']


if __name__ == '__main__': sys.exit(main())
