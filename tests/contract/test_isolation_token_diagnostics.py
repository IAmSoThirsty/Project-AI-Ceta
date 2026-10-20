"""Rejected-token measurements; controlled buffers never prove OS isolation."""
from pathlib import Path
import ctypes as C
import json
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from ceta.contracts.wire import ContractError
from ceta.supervisor import isolated_worker as module

SID = 'S-1-15-2-1-2-3-4-5-6-7'
NATIVE_TOKEN_DIAGNOSTIC_RECEIPTS = []


class _ControlledBuffers:
    """DATA_ONLY parser fixture: numeric handles here are never native handles."""
    def __init__(self, *, app=1, capabilities=0, integrity='S-1-16-4096',
                 restricted=True, sid=SID, matches=True, restricted_count=None, restriction_error_code=0):
        self.app, self.capabilities = app, capabilities
        self.integrity, self.restricted, self.sid, self.matches = integrity, restricted, sid, matches
        self.restricted_count = int(restricted) if restricted_count is None else restricted_count
        self.restriction_error_code = restriction_error_code
        self._pending_token_outputs, self._pending_handles = [], []
        self.calls, self.closed, self.storage = [], [], []
        self.query_error, self.query_failure, self.short_class = None, None, None
        self.cleanup_error, self.open_error, self.open_ok, self.open_value = None, None, True, 7701
        self.sid_error, self.restriction_error = None, None

    def OpenProcessToken(self, process, access, output):
        self.calls.append(('open', process, access))
        C.cast(output, C.POINTER(module.HANDLE)).contents.value = self.open_value
        if self.open_error is not None: raise self.open_error
        return self.open_ok

    def token_data(self, token, information_class):
        self.calls.append(('query', information_class))
        if information_class == self.query_failure: raise self.query_error
        if information_class == self.short_class: return C.create_string_buffer(1)
        if information_class == 29: value = module.DWORD(self.app)
        elif information_class == 31: value = C.c_void_p(101)
        elif information_class == 30: value = module.DWORD(self.capabilities)
        elif information_class == 25: value = module.SID_AND_ATTRIBUTES(202, 0)
        elif information_class == 11:
            size = module.TOKEN_GROUPS.groups.offset + self.restricted_count * C.sizeof(module.SID_AND_ATTRIBUTES)
            storage = C.create_string_buffer(max(4, size))
            module.DWORD.from_buffer(storage).value = self.restricted_count
            self.storage.append(storage)
            return storage
        else: raise AssertionError('undeclared token class')
        storage = C.create_string_buffer(C.string_at(C.byref(value), C.sizeof(value)), C.sizeof(value))
        self.storage.append(storage)
        return storage

    def EqualSid(self, actual, expected):
        self.calls.append(('equal_sid', actual, expected))
        return self.matches

    def sid_text(self, pointer):
        self.calls.append(('sid_text', pointer))
        if self.sid_error is not None: raise self.sid_error
        return self.integrity if pointer == 202 else self.sid

    def IsTokenRestricted(self, token):
        self.calls.append(('restricted',))
        if self.restriction_error is not None: raise self.restriction_error
        C.set_last_error(self.restriction_error_code)
        return self.restricted

    def queue_handle(self, handle):
        self._pending_handles.append({'handle': handle})

    def retry_cleanup(self, *, kinds=('attributes', 'handles', 'strings', 'sids', 'folders')):
        self.calls.append(('cleanup', kinds))
        if self.cleanup_error is not None: raise self.cleanup_error
        for row in self._pending_handles: self.closed.append(row['handle'])
        self._pending_handles.clear()


class IsolationTokenDiagnosticTests(unittest.TestCase):
    def observe(self, api, observed_ns=11):
        with patch.object(module.time, 'monotonic_ns', return_value=observed_ns):
            return module._IsolationAPI.token_facts(api, 55, 303)

    def rejected(self, api, *, code='ISOLATION_TOKEN_NOT_QUALIFIED', observed_ns=11):
        with self.assertRaises(ContractError) as caught: self.observe(api, observed_ns)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(api.closed, [7701])
        self.assertEqual(api._pending_handles, [])
        self.assertEqual(api._pending_token_outputs, [])
        result = caught.exception.native_isolation_token_observation
        self.assertEqual(result['classification'], 'REJECTED_NATIVE_OBSERVATION')
        self.assertLess(len(json.dumps(result, sort_keys=True)), 2048)
        return result

    def test_appcontainer_capability_integrity_predicates_keep_rejecting_measured_value(self):
        for changes, key, value in (({'app': 0}, 'is_appcontainer_dword', 0),
            ({'app': 2}, 'is_appcontainer_dword', 2),
            ({'capabilities': 1}, 'capability_count', 1),
            ({'integrity': 'S-1-16-0'}, 'integrity_rid', 0),
            ({'integrity': 'S-1-16-8192'}, 'integrity_rid', 8192)):
            with self.subTest(changes=changes):
                result = self.rejected(_ControlledBuffers(**changes))
                self.assertEqual(result[key], value)
                self.assertEqual(result['stage'], 'QUALIFY_TOKEN_FACTS')
                self.assertEqual(result['observed_monotonic_ns'], 11)

    def test_negative_measured_timestamp_keeps_original_rejection(self):
        result = self.rejected(_ControlledBuffers(), observed_ns=-1)
        self.assertEqual(result['observed_monotonic_ns'], -1)

    def test_qualified_controlled_shape_preserves_query_order_and_is_data_only(self):
        api = _ControlledBuffers()
        facts = self.observe(api)
        self.assertEqual(facts, module.IsolationTokenFacts(SID, True, 0, 4096, True, 11, 1, 0, 1))
        self.assertEqual(api.calls, [('open', 55, 8), ('query', 29), ('query', 31),
            ('equal_sid', 101, 303), ('query', 30), ('query', 25), ('sid_text', 202),
            ('sid_text', 101), ('restricted',), ('query', 11), ('cleanup', ('handles',))])
        self.assertEqual(api.closed, [7701])

    def test_partial_query_failure_omits_unobserved_values_and_preserves_primary(self):
        for information_class, stage, absent in ((29, 'QUERY_APPCONTAINER', 'is_appcontainer_dword'),
            (31, 'QUERY_APPCONTAINER_SID', 'appcontainer_sid_matches_expected'),
            (30, 'QUERY_CAPABILITIES', 'capability_count'),
            (25, 'QUERY_INTEGRITY', 'integrity_rid')):
            with self.subTest(information_class=information_class):
                api, primary = _ControlledBuffers(), SystemExit(73)
                api.query_failure, api.query_error = information_class, primary
                try: self.observe(api)
                except BaseException as error: self.assertIs(error, primary)
                else: self.fail('incomplete measurement was accepted')
                result = primary.native_isolation_token_observation
                self.assertEqual(result['stage'], stage)
                self.assertNotIn(absent, result)
                self.assertNotIn('observed_monotonic_ns', result)
                self.assertEqual(api.closed, [7701])

    def test_measured_zero_survives_later_unavailable_query(self):
        api, primary = _ControlledBuffers(), KeyboardInterrupt()
        api.query_failure, api.query_error = 25, primary
        with self.assertRaises(KeyboardInterrupt) as caught: self.observe(api)
        self.assertIs(caught.exception, primary)
        result = primary.native_isolation_token_observation
        self.assertEqual(result['capability_count'], 0)
        self.assertNotIn('integrity_rid', result)
        self.assertNotIn('is_token_restricted', result)

    def test_malformed_native_buffer_keeps_original_size_failure(self):
        for information_class, code, absent in ((29, 'ISOLATION_APPCONTAINER_QUERY_SIZE_INVALID', 'is_appcontainer_dword'),
            (31, 'ISOLATION_APPCONTAINER_QUERY_SIZE_INVALID', 'appcontainer_sid_matches_expected'),
            (30, 'ISOLATION_CAPABILITY_QUERY_SIZE_INVALID', 'capability_count'),
            (25, 'ISOLATION_INTEGRITY_QUERY_SIZE_INVALID', 'integrity_rid')):
            with self.subTest(information_class=information_class):
                api = _ControlledBuffers(); api.short_class = information_class
                self.assertNotIn(absent, self.rejected(api, code=code))

    def test_sid_mismatch_is_recorded_without_reading_later_fields(self):
        api = _ControlledBuffers(matches=False)
        result = self.rejected(api, code='ISOLATION_APPCONTAINER_SID_MISMATCH')
        self.assertIs(result['appcontainer_sid_matches_expected'], False)
        self.assertNotIn('capability_count', result)
        self.assertNotIn(('query', 30), api.calls)

    def test_invalid_sid_text_is_bounded_and_still_rejected(self):
        result = self.rejected(_ControlledBuffers(integrity='x' * 4096), code='ISOLATION_INTEGRITY_SID_INVALID')
        self.assertEqual(result['integrity_sid'], 'x' * 192)
        self.assertNotIn('integrity_rid', result)
        result = self.rejected(_ControlledBuffers(sid='x' * 4096), code='ISOLATION_APPCONTAINER_SID_REQUIRED')
        self.assertEqual(result['appcontainer_sid'], 'x' * 192)

    def test_control_with_refusing_attribute_hooks_is_the_same_raised_object(self):
        class RefusingControl(KeyboardInterrupt):
            def __setattr__(self, name, value): raise RuntimeError('diagnostic setter refused')
            def __getattribute__(self, name):
                if name in ('__dict__', 'native_isolation_token_observation'):
                    raise RuntimeError('diagnostic getter refused')
                return super().__getattribute__(name)
        api, primary = _ControlledBuffers(), RefusingControl()
        api.query_failure, api.query_error = 30, primary
        with self.assertRaises(RefusingControl) as caught: self.observe(api)
        self.assertIs(caught.exception, primary)
        raw = BaseException.__dict__['__dict__'].__get__(primary)
        self.assertEqual(raw['native_isolation_token_observation']['stage'], 'QUERY_CAPABILITIES')
        self.assertEqual(api.closed, [7701])

    def test_secondary_cleanup_failure_does_not_replace_primary_or_its_measurements(self):
        api, primary = _ControlledBuffers(), KeyboardInterrupt()
        api.query_failure, api.query_error = 30, primary
        api.cleanup_error = RuntimeError('controlled close refusal')
        with self.assertRaises(KeyboardInterrupt) as caught: self.observe(api)
        self.assertIs(caught.exception, primary)
        self.assertIs(primary.isolation_cleanup.isolation_api, api)
        self.assertEqual(api._pending_handles, [{'handle': 7701}])
        self.assertEqual(primary.native_isolation_token_observation['stage'], 'QUERY_CAPABILITIES')
        api.cleanup_error = None
        primary.isolation_cleanup.close_cleanup()
        self.assertEqual(api.closed, [7701])
        self.assertEqual(api._pending_handles, [])

    def test_interrupted_open_keeps_uncertain_output_and_exact_control(self):
        api, primary = _ControlledBuffers(), KeyboardInterrupt()
        api.open_error = primary
        with self.assertRaises(KeyboardInterrupt) as caught: self.observe(api)
        self.assertIs(caught.exception, primary)
        self.assertEqual(len(api._pending_token_outputs), 1)
        self.assertEqual(api._pending_token_outputs[0].value, 7701)
        self.assertEqual(api.closed, [])
        self.assertEqual(primary.native_isolation_token_observation['stage'], 'OPEN_PROCESS_TOKEN')

    def test_failed_open_without_allocation_keeps_no_unknown_handle(self):
        api = _ControlledBuffers(); api.open_ok, api.open_value = False, None
        with self.assertRaises(ContractError) as caught: self.observe(api)
        self.assertTrue(caught.exception.code.startswith('ISOLATION_PROCESS_TOKEN_UNAVAILABLE'))
        self.assertEqual(api._pending_token_outputs, [])
        self.assertEqual(api.closed, [])
        self.assertEqual(caught.exception.native_isolation_token_observation['stage'], 'OPEN_PROCESS_TOKEN')

    def test_restriction_query_control_keeps_only_completed_measurements(self):
        api, primary = _ControlledBuffers(), SystemExit(74)
        api.restriction_error = primary
        with self.assertRaises(SystemExit) as caught: self.observe(api)
        self.assertIs(caught.exception, primary)
        result = primary.native_isolation_token_observation
        self.assertEqual(result['integrity_rid'], 4096)
        self.assertEqual(result['appcontainer_sid'], SID)
        self.assertNotIn('is_token_restricted', result)
        self.assertNotIn('observed_monotonic_ns', result)

    def test_snapshot_is_copied_and_contains_no_native_buffers_or_addresses(self):
        api = _ControlledBuffers(app=0)
        result = self.rejected(api)
        for storage in api.storage: C.memset(storage, 255, len(storage))
        self.assertEqual(result['capability_count'], 0)
        self.assertEqual(result['integrity_rid'], 4096)
        self.assertTrue(all(type(value) in (str, int, bool) for value in result.values()))
        self.assertEqual(set(result), {'schema', 'classification', 'stage', 'is_appcontainer_dword',
            'appcontainer_sid_matches_expected', 'capability_count', 'integrity_sid', 'appcontainer_sid',
            'integrity_rid', 'is_token_restricted', 'observed_monotonic_ns',
            'restriction_raw_result', 'restriction_last_error', 'restricted_sid_count', 'restriction_query_bytes'})

    def test_false_with_successful_empty_sid_list_is_measured_not_assumed(self):
        api = _ControlledBuffers(restricted=False, restricted_count=0)
        facts = self.observe(api)
        self.assertFalse(facts.restricted)
        self.assertEqual((facts.restricted_sid_count, facts.restriction_last_error), (0, 0))
        self.assertIn(('query', 11), api.calls)
        self.assertEqual(api.closed, [7701])

    def test_false_api_error_is_unavailable_and_never_qualified(self):
        api = _ControlledBuffers(restricted=False, restriction_error_code=5)
        result = self.rejected(api, code='ISOLATION_RESTRICTION_QUERY_FAILED')
        self.assertEqual(result['restriction_last_error'], 5)
        self.assertNotIn('restricted_sid_count', result)
        self.assertNotIn(('query', 11), api.calls)

    def test_restricting_list_and_boolean_must_agree(self):
        for changes in ({'restricted': False, 'restricted_count': 1},
                        {'restricted': True, 'restricted_count': 0}):
            result = self.rejected(_ControlledBuffers(**changes), code='ISOLATION_RESTRICTION_OBSERVATIONS_DISAGREE')
            self.assertEqual(result['stage'], 'COMPARE_RESTRICTION_OBSERVATIONS')
            self.assertNotIn('observed_monotonic_ns', result)

    def test_restricting_list_query_failure_and_truncation_keep_cleanup(self):
        api, primary = _ControlledBuffers(restricted=False), SystemExit(75)
        api.query_failure, api.query_error = 11, primary
        with self.assertRaises(SystemExit) as caught: self.observe(api)
        self.assertIs(caught.exception, primary)
        result = primary.native_isolation_token_observation
        self.assertEqual(result['stage'], 'QUERY_RESTRICTED_SIDS')
        self.assertEqual(result['restriction_last_error'], 0)
        self.assertNotIn('restricted_sid_count', result)
        self.assertEqual(api.closed, [7701])
        api = _ControlledBuffers(); api.short_class = 11
        self.rejected(api, code='ISOLATION_RESTRICTION_QUERY_SIZE_INVALID')

    def test_group_count_is_bounded_without_dereferencing_any_sid(self):
        for count, size in ((1, 4), (4097, 65536), (0xffffffff, 8), (0, 65537), (4096, 65544)):
            storage = C.create_string_buffer(size)
            module.DWORD.from_buffer(storage).value = count
            with self.subTest(count=count), self.assertRaises(ContractError): module._restricted_sid_count(storage)
        zero = C.create_string_buffer(4)
        self.assertEqual(module._restricted_sid_count(zero), 0)


class DiagnosticTestCustodyControls(unittest.TestCase):
    """Execute the new diagnostic test body with DATA_ONLY API substitutions."""
    def test_exact_body_preserves_control_primary_receipt_and_recovery_custody(self):
        class Controlled(_ControlledBuffers):
            def GetCurrentProcess(self): return 55
            def pending_native_resources(self):
                return tuple({'kind': 'CONTROLLED_HANDLE', 'handle': row['handle']}
                             for row in self._pending_handles)
        for primary_kind, fail_cleanup in ((None, False), (KeyboardInterrupt, True),
                                           (SystemExit, True), (None, True)):
            api = Controlled(restricted=False, restricted_count=0)
            primary = None if primary_kind is None else primary_kind('DATA_ONLY primary')
            if primary is not None:
                api.query_failure, api.query_error = 11, primary
            secondary = RuntimeError('DATA_ONLY cleanup') if fail_cleanup else None
            api.cleanup_error = secondary
            receipts, caught = [], None
            case = NativeCurrentTokenDiagnosticTests('test_actual_current_token_restricting_list_and_immediate_error_agree')
            with patch.object(module, '_IsolationAPI', return_value=api), \
                    patch.dict(globals(), NATIVE_TOKEN_DIAGNOSTIC_RECEIPTS=receipts):
                try: case.test_actual_current_token_restricting_list_and_immediate_error_agree()
                except BaseException as error: caught = error
            with self.subTest(primary=primary_kind, cleanup_failure=fail_cleanup):
                self.assertEqual(len(receipts), 1)
                self.assertFalse(receipts[0]['isolation_qualified'])
                if primary is not None:
                    self.assertIs(caught, primary)
                elif fail_cleanup:
                    self.assertIsInstance(caught, module.IsolatedLaunchError)
                    self.assertIs(caught.__cause__, secondary)
                else:
                    self.assertIsNone(caught)
                if fail_cleanup:
                    raw = BaseException.__dict__['__dict__'].__get__(caught)
                    cleanup = raw.get('isolation_cleanup', caught)
                    self.assertIs(cleanup.isolation_api, api)
                    self.assertEqual(receipts[0]['pending_resources'],
                                     [{'kind': 'CONTROLLED_HANDLE', 'handle': 7701}])
                    api.cleanup_error = None
                    cleanup.close_cleanup()
                self.assertEqual(api.pending_native_resources(), ())
                self.assertEqual(api.closed, [7701])


class NativeCurrentTokenDiagnosticTests(unittest.TestCase):
    def test_actual_current_token_restricting_list_and_immediate_error_agree(self):
        api, token = module._IsolationAPI(), module.HANDLE()
        observation = primary = None
        try:
            self.assertTrue(api.OpenProcessToken(api.GetCurrentProcess(), 8, C.byref(token)))
            C.set_last_error(0)
            raw = int(api.IsTokenRestricted(token))
            error = C.get_last_error()
            data = api.token_data(token, 11)
            count = module._restricted_sid_count(data)
            observation = {'restriction_raw_result': raw, 'restriction_last_error': error,
                'restricted_sid_count': count, 'restriction_query_bytes': len(data)}
            if raw == 0: self.assertEqual(error, 0)
            self.assertEqual(bool(raw), count > 0)
        except BaseException as error:
            primary = error
            raise
        finally:
            if token.value: api.queue_handle(token.value)
            try:
                module._finish_cleanup(api, primary)
            finally:
                NATIVE_TOKEN_DIAGNOSTIC_RECEIPTS.append({'test_id': self.id(),
                    'operation': 'CURRENT_PROCESS_TOKEN_QUERY_ONLY', 'observation': observation,
                    'profile_operations': [], 'worker_launches': [],
                    'primary_type': None if primary is None else type(primary).__name__,
                    'pending_resources': list(api.pending_native_resources()),
                    'isolation_qualified': False})
        self.assertEqual(api.pending_native_resources(), ())

    def test_actual_current_process_rejection_and_token_sid_allocation_retirement(self):
        api = module._IsolationAPI()
        calls, real_close = [], api.CloseHandle
        def close(handle):
            result = real_close(handle)
            calls.append({'handle': handle.value if hasattr(handle, 'value') else handle, 'closed': bool(result)})
            return result
        api.CloseHandle = close
        primary = None
        try:
            sid = api.derive('CETA.ProjectAICETA.IsolationDiagnostic.AC4')
            with self.assertRaises(ContractError) as caught:
                api.token_facts(api.GetCurrentProcess(), sid)
            primary = caught.exception
            self.assertEqual(primary.code, 'ISOLATION_APPCONTAINER_SID_MISMATCH')
            observation = primary.native_isolation_token_observation
            self.assertEqual(observation['is_appcontainer_dword'], 0)
            self.assertIs(observation['appcontainer_sid_matches_expected'], False)
            self.assertNotIn('capability_count', observation)
            self.assertNotIn('is_token_restricted', observation)
            self.assertEqual(len(calls), 2)
            self.assertTrue(all(row['closed'] for row in calls))
        finally:
            api.retry_cleanup()
            NATIVE_TOKEN_DIAGNOSTIC_RECEIPTS.append({'test_id': self.id(),
                'operation': 'CURRENT_PROCESS_TOKEN_READ_AND_DERIVED_SID_MEMORY_ONLY',
                'profile_operations': [], 'worker_launches': [],
                'observation': None if primary is None else primary.native_isolation_token_observation,
                'close_calls': calls, 'pending_resources': list(api.pending_native_resources())})
        self.assertEqual(api.pending_native_resources(), ())


class NativeRejectedTokenCustodyTests(unittest.TestCase):
    def native_recovery(self, base, *, nested=False):
        class RefusingPrimary(base):
            def __setattr__(self, name, value): raise RuntimeError('primary setter refused')
            def __getattribute__(self, name):
                if name in ('__dict__', 'isolation_cleanup', 'owned_process', 'add_note', '__notes__'):
                    raise RuntimeError('primary getter refused')
                return super().__getattribute__(name)
        primary = RefusingPrimary('exact interrupted native read')
        secondary = RuntimeError('native token close is temporarily unavailable')
        api = module._IsolationAPI(); real_read, real_cleanup = api.token_data, api.retry_cleanup
        before, after, pending, captured = [], [], [], None
        cleanup = None; nested_primary = None; through_exposed_owner = False
        def interrupted(token, information_class):
            result = real_read(token, information_class)
            if information_class == 29: raise primary
            return result
        def unavailable(**kwargs): raise secondary
        try:
            sid = api.derive('CETA.ProjectAICETA.AC5.ReviewerCustody')
            api.token_data, api.retry_cleanup = interrupted, unavailable
            try: api.token_facts(api.GetCurrentProcess(), sid)
            except BaseException as error: captured = error
            raw = BaseException.__dict__['__dict__'].__get__(primary)
            cleanup = raw.get('isolation_cleanup')
            pending = list(api.pending_native_resources())
            for row in api._pending_handles:
                flags = module.DWORD(); C.set_last_error(0)
                valid = api.GetHandleInformation(row['handle'], C.byref(flags))
                before.append({'handle': row['handle'], 'valid': bool(valid), 'error': C.get_last_error()})
            if nested and cleanup is not None:
                try: cleanup.close_cleanup()
                except BaseException as error: nested_primary = error
                self.assertIs(nested_primary, secondary)
                self.assertIs(BaseException.__dict__['__dict__'].__get__(secondary)['isolation_cleanup'], cleanup)
                self.assertIs(raw['isolation_cleanup'], cleanup)
            api.token_data, api.retry_cleanup = real_read, real_cleanup
            if cleanup is not None:
                self.assertIs(cleanup.isolation_api, api)
                self.assertIs(raw['owned_process'], None)
                cleanup.close_cleanup(); through_exposed_owner = True
        finally:
            api.token_data, api.retry_cleanup = real_read, real_cleanup
            # Preserve a failing oracle's native resources even if explicit
            # custody regresses. The assertion below still rejects that path.
            if api.pending_native_resources(): real_cleanup()
            for row in before:
                flags = module.DWORD(); C.set_last_error(0)
                valid = api.GetHandleInformation(row['handle'], C.byref(flags))
                after.append({'handle': row['handle'], 'valid': bool(valid), 'error': C.get_last_error()})
            NATIVE_TOKEN_DIAGNOSTIC_RECEIPTS.append({'test_id': self.id(), 'primary_type': base.__name__,
                'exact_primary': captured is primary, 'nested_exact_primary': not nested or nested_primary is secondary,
                'pending_at_exposure': pending, 'native_before': before, 'native_after': after,
                'retired_through_exposed_cleanup': through_exposed_owner,
                'pending_resources': list(api.pending_native_resources()), 'profile_operations': [], 'worker_launches': []})
        self.assertIs(captured, primary)
        self.assertEqual(len(before), 1); self.assertTrue(before[0]['valid'])
        self.assertEqual(after, [dict(after[0], valid=False, error=6)])
        self.assertTrue(through_exposed_owner)
        self.assertEqual(api.pending_native_resources(), ())
        self.assertEqual(raw['native_isolation_token_observation']['stage'], 'QUERY_APPCONTAINER')

    def test_native_keyboard_interrupt_retires_through_exposed_cleanup(self):
        self.native_recovery(KeyboardInterrupt)

    def test_native_system_exit_retires_through_exposed_cleanup(self):
        self.native_recovery(SystemExit)

    def test_nested_native_recovery_failure_retains_exact_same_cleanup(self):
        self.native_recovery(KeyboardInterrupt, nested=True)

    def test_repeated_custody_notes_never_call_overridable_hooks(self):
        hooks = []
        class RefusingNotes(KeyboardInterrupt):
            def __setattr__(self, name, value):
                hooks.append('setattr'); raise RuntimeError('setter must not run')
            def __getattribute__(self, name):
                if name in ('add_note', '__notes__', '__dict__', 'isolation_cleanup', 'owned_process'):
                    hooks.append('getattr:' + name)
                    data = BaseException.__dict__['__dict__'].__get__(self)
                    data.pop('isolation_cleanup', None)
                    raise RuntimeError('getter must not run')
                return super().__getattribute__(name)
        primary = RefusingNotes(); raw = BaseException.__dict__['__dict__'].__get__(primary)
        raw['__notes__'] = ['existing note']
        cleanup = module.IsolatedLaunchError('CONTROLLED_CUSTODY', None, _ControlledBuffers())
        for _ in range(2): module._attach_cleanup(primary, cleanup)
        self.assertEqual(hooks, []); self.assertIs(raw['isolation_cleanup'], cleanup)
        self.assertIsNone(raw['owned_process']); self.assertEqual(raw['__notes__'][0], 'existing note')
        self.assertEqual(len(raw['__notes__']), 3)
        class HookList(list):
            def append(self, value):
                hooks.append('append'); raw.pop('isolation_cleanup', None)
                raise RuntimeError('list-subclass hook must not run')
        notes = HookList(['retained malformed note container']); raw['__notes__'] = notes
        module._attach_cleanup(primary, cleanup)
        self.assertEqual(hooks, []); self.assertIs(raw['__notes__'], notes)
        self.assertIs(raw['isolation_cleanup'], cleanup); self.assertEqual(notes, ['retained malformed note container'])


if __name__ == '__main__': unittest.main()
