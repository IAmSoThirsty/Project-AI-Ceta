"""Finite owned-native-resource exception/custody oracles for frozen AC1.

Faults are injected after real allocations. No restrictive child is substituted
with an unrestricted one, no profile is installed, and the reviewer explicitly
settles only the handles/allocations it captured for its own probes.
"""
from ac_support import *
import ctypes as C
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Q / 'src'))
from ceta.contracts.wire import ContractError
from ceta.supervisor import isolated_worker as module

FACTS = []
def caught(call):
    try: call()
    except BaseException as error: return error
    raise AssertionError('injected operation unexpectedly returned')

def visible_cleanup(error):
    value = getattr(error, 'isolation_cleanup', None)
    return value is not None and callable(getattr(value, 'close_cleanup', None))

def handle_open(api, handle):
    flags = module.DWORD()
    return bool(api.GetHandleInformation(handle, C.byref(flags)))

class FinalizationCustodyTests(unittest.TestCase):
    def test_attribute_finalization_preserves_control_and_native_cleanup(self):
        for primary in (KeyboardInterrupt('AC1_ATTRIBUTE_PRIMARY'), SystemExit('AC1_ATTRIBUTE_PRIMARY')):
            with self.subTest(primary=type(primary).__name__):
                fixture = D / ('attribute-' + type(primary).__name__)
                fixture.mkdir()
                image = fixture / 'isolated_worker.exe'
                fs.write_new(image, fs.read_bytes(D / 'build-r2/isolated_worker.exe'))
                observed = []
                class Faulted(module._IsolationAPI):
                    def __init__(self):
                        super().__init__(); observed.append(self); self.handles = []; self.jobs = []
                        self.real_delete = self.DeleteProcThreadAttributeList
                        self.real_create_file = self.CreateFileW
                        self.real_create_job = self.CreateJobObjectW
                        self.CreateFileW = self.track_file
                        self.CreateJobObjectW = self.track_job
                        self.UpdateProcThreadAttribute = self.interrupt
                        self.DeleteProcThreadAttributeList = self.delete_then_fail
                    def track_file(self, *args):
                        handle = self.real_create_file(*args)
                        if handle not in (None, 0, module.INVALID_HANDLE): self.handles.append(handle)
                        return handle
                    def track_job(self, *args):
                        handle = self.real_create_job(*args)
                        if handle: self.handles.append(handle); self.jobs.append(handle)
                        return handle
                    def interrupt(self, *args): raise primary
                    def delete_then_fail(self, attributes):
                        self.real_delete(attributes)
                        raise OSError('AC1_ATTRIBUTE_SECONDARY')
                with patch.object(module, '_IsolationAPI', Faulted):
                    error = caught(lambda: module.IsolatedWindowsWorker.launch(str(image), (),
                        cwd=str(fixture), scratch_root=str(fixture), expected_image_sha256=sha(image),
                        appcontainer_name='CETA.AC1.Review.Attribute'))
                api = observed[0]
                open_before = [h for h in api.handles if handle_open(api, h)]
                pending_before = list(api.pending_sids)
                # No CreateProcessW was reached: this is an actual empty-job and
                # file-handle cleanup test, not successful worker isolation.
                active = []; observed_job_status = []
                try:
                    for job in api.jobs:
                        C.set_last_error(0)
                        is_open = handle_open(api, job)
                        status = C.get_last_error()
                        if is_open:
                            accounting = C.create_string_buffer(48); used = module.DWORD()
                            self.assertTrue(api.QueryInformationJobObject(job, 1, accounting, len(accounting), C.byref(used)))
                            active.append(module.DWORD.from_buffer(accounting, 40).value)
                        else:
                            self.assertEqual(status, 6)
                        observed_job_status.append({'handle': job, 'native_open': is_open, 'last_error': status})
                    self.assertTrue(all(value == 0 for value in active))
                finally:
                    for handle in open_before: api.close(handle)
                    api.release_sids()
                row = {'oracle': self.id(), 'primary': type(primary).__name__,
                       'outgoing_type': type(error).__name__, 'outgoing_message': str(error),
                       'primary_identity_preserved': error is primary,
                       'caller_visible_cleanup': visible_cleanup(error),
                       'open_handles_before_reviewer_recovery': open_before,
                       'pending_sid_allocations_before_reviewer_recovery': pending_before,
                       'empty_job_observations': active, 'captured_job_native_status': observed_job_status,
                       'all_captured_handles_closed': all(not handle_open(api, h) for h in open_before),
                       'pending_sids_after': list(api.pending_sids), 'restricted_child_created': False}
                FACTS.append(row)
                self.assertTrue(row['all_captured_handles_closed']); self.assertEqual(row['pending_sids_after'], [])
                self.assertIs(error, primary, 'secondary attribute deletion replaced the original control exception')
                self.assertTrue(visible_cleanup(error), 'unresolved resources must have caller-visible custody')

    def test_public_sid_derivation_preserves_primary_and_pending_allocation(self):
        for primary in (KeyboardInterrupt('AC1_SID_PRIMARY'), SystemExit('AC1_SID_PRIMARY')):
            with self.subTest(primary=type(primary).__name__):
                observed = []
                class Faulted(module._IsolationAPI):
                    def __init__(self):
                        super().__init__(); observed.append(self); self.real_free = self.FreeSid
                        self.FreeSid = lambda pointer: pointer  # Explicit refusal: no native free occurs.
                    def sid_text(self, pointer): raise primary
                with patch.object(module, '_IsolationAPI', Faulted):
                    error = caught(lambda: module.appcontainer_sid('CETA.AC1.Review.Sid'))
                api = observed[0]; pending = list(api.pending_sids)
                valid_before = [bool(api.IsValidSid(pointer)) for pointer in pending]
                api.FreeSid = api.real_free
                api.release_sids()
                row = {'oracle': self.id(), 'primary': type(primary).__name__,
                       'outgoing_type': type(error).__name__, 'outgoing_message': str(error),
                       'primary_identity_preserved': error is primary,
                       'caller_visible_cleanup': visible_cleanup(error),
                       'pending_sid_allocations_before_reviewer_recovery': pending,
                       'native_sid_valid_before_recovery': valid_before,
                       'pending_sids_after': list(api.pending_sids), 'native_release_returned_success': True}
                FACTS.append(row)
                self.assertEqual(valid_before, [True]); self.assertEqual(api.pending_sids, [])
                self.assertIs(error, primary, 'public SID helper masked the primary and hid pending allocation')
                self.assertTrue(visible_cleanup(error), 'public helper must retain unresolved SID cleanup')

    def test_token_query_preserves_primary_and_exact_open_handle_on_close_failure(self):
        for primary in (KeyboardInterrupt('AC1_TOKEN_PRIMARY'), SystemExit('AC1_TOKEN_PRIMARY')):
            with self.subTest(primary=type(primary).__name__):
                api = module._IsolationAPI(); real_open, real_close = api.OpenProcessToken, api.close
                opened = []
                def open_token(process, access, output):
                    ok = real_open(process, access, output)
                    if ok: opened.append(C.cast(output, C.POINTER(module.HANDLE)).contents.value)
                    return ok
                def query(*args): raise primary
                def fail_close(handle): raise OSError('AC1_TOKEN_CLOSE_SECONDARY')
                api.OpenProcessToken, api.token_data, api.close = open_token, query, fail_close
                error = caught(lambda: api.token_facts(api.GetCurrentProcess(), None))
                open_before = [handle_open(api, handle) for handle in opened]
                api.close = real_close
                cleanup = getattr(error, 'isolation_cleanup', None)
                if cleanup is not None: cleanup.close_cleanup()
                for handle, is_open in zip(opened, open_before):
                    if is_open and handle_open(api, handle): api.close(handle)
                row = {'oracle': self.id(), 'primary': type(primary).__name__,
                       'outgoing_type': type(error).__name__, 'outgoing_message': str(error),
                       'primary_identity_preserved': error is primary,
                       'caller_visible_cleanup': visible_cleanup(error),
                       'token_handles': opened, 'native_open_before_recovery': open_before,
                       'native_closed_after_recovery': [not handle_open(api, handle) for handle in opened],
                       'process_scope': 'Read-only query token of reviewer process; no process mutation or AppContainer fact claim'}
                FACTS.append(row)
                self.assertEqual(open_before, [True]); self.assertEqual(row['native_closed_after_recovery'], [True])
                self.assertIs(error, primary, 'token close failure replaced the original control exception')
                self.assertTrue(visible_cleanup(error), 'exact unresolved token handle must remain caller-visible')

if __name__ == '__main__':
    before = candidate_cut(); source_before = source_cut()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FinalizationCustodyTests)
    expected = [case.id() for case in suite]; executed = []
    class Recorder(unittest.TextTestResult):
        def startTest(self, case): executed.append(case.id()); super().startTest(case)
    started = utc()
    with (D / 'hostile-cleanup-r1.txt').open('x', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Recorder).run(suite)
    after = candidate_cut(); assert before == after
    record = {'started_at': started, 'finished_at': utc(), 'tests_run': result.testsRun,
              'expected_ids': expected, 'executed_ids': executed, 'expected_executed_equal': expected == executed,
              'failures': [{'id':case.id(),'traceback':text} for case,text in result.failures],
              'errors': [{'id':case.id(),'traceback':text} for case,text in result.errors],
              'skipped': result.skipped, 'exit_status': 0 if result.wasSuccessful() else 1,
              'native_facts': FACTS, 'candidate_before': before, 'candidate_after': after,
              'source_before': source_before, 'source_after': source_cut(),
              'raw': reference(D / 'hostile-cleanup-r1.txt'),
              'qualification': 'Injected finalizer failures after actual native resource allocations; reviewer-owned recovery; no restrictive worker or positive isolation'}
    write_new(D / 'hostile-cleanup-r1.json', record)
    print(json.dumps({'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
                      'skips': len(result.skipped), 'facts': len(FACTS), 'exit_status': record['exit_status']}), flush=True)
    sys.exit(record['exit_status'])
