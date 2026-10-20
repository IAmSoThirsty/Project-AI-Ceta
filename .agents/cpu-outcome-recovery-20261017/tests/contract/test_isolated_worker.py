"""AC1 exact binding/fail-closed resource cleanup tests.

Successful native bypass qualification is a separate, explicitly blocked
obligation when this host refuses no-profile AppContainer creation. These tests
never reinterpret a restrictive launch failure as successful isolation.
"""
from pathlib import Path
from collections import Counter
import ctypes as C
import hashlib
import json
import os
import sys
import threading
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
NATIVE_ENVIRONMENT_RECEIPTS = []
sys.path.insert(0, str(ROOT / 'src'))
from ceta.contracts.wire import ContractError
from ceta.supervisor import isolated_worker as module
from ceta.supervisor.isolated_worker import IsolationTokenFacts, IsolatedWindowsWorker, appcontainer_sid


class IsolationFactsContractTests(unittest.TestCase):
    """Synthetic value records qualify shapes only, never OS authentication."""
    def facts(self, **changes):
        value = dict(appcontainer_sid='S-1-15-2-1-2-3-4-5-6-7', is_appcontainer=True,
                     capability_count=0, integrity_rid=4096, restricted=True, observed_monotonic_ns=10)
        value.update(changes)
        return IsolationTokenFacts(**value)

    def test_exact_low_no_capabilities_shape(self):
        self.assertEqual(self.facts().capability_count, 0)

    def test_sid_must_be_appcontainer_class(self):
        for sid in ('S-1-5-18', '', 'S-1-15-2', True):
            with self.subTest(sid=sid), self.assertRaises(ContractError): self.facts(appcontainer_sid=sid)

    def test_boolean_appcontainer_measurement_required(self):
        for value in (False, 1, None):
            with self.subTest(value=value), self.assertRaises(ContractError): self.facts(is_appcontainer=value)

    def test_capability_zero_not_boolean(self):
        for value in (1, False, None, -1):
            with self.subTest(value=value), self.assertRaises(ContractError): self.facts(capability_count=value)

    def test_exact_low_integrity(self):
        for value in (8192, 0, True, None):
            with self.subTest(value=value), self.assertRaises(ContractError): self.facts(integrity_rid=value)

    def test_restriction_and_observation_are_typed(self):
        for changes in ({'restricted': False}, {'restricted': 1}, {'observed_monotonic_ns': -1}, {'observed_monotonic_ns': True}):
            with self.subTest(changes=changes), self.assertRaises(ContractError): self.facts(**changes)

    def test_value_record_is_frozen(self):
        with self.assertRaises(AttributeError): self.facts().capability_count = 1


class NativeLocalAppDataTests(unittest.TestCase):
    """Native observation/allocation tests; never create an AppContainer profile."""
    def setUp(self):
        self.directory = Path(os.environ['CETA_AC3_TEST_ROOT']) / ('localappdata-' + uuid.uuid4().hex)
        self.directory.mkdir()
        self.api = module._IsolationAPI()
        self.real_query, self.real_free = self.api.SHGetKnownFolderPath, self.api.CoTaskMemFree
        allocate = self.api.ole.CoTaskMemAlloc
        allocate.argtypes, allocate.restype = [module.SIZE_T], C.c_void_p
        self.allocate = allocate
        self.allocations, self.freed, self.observations = [], [], []
        self.api.CoTaskMemFree = self.free

    def free(self, pointer):
        address = pointer.value if isinstance(pointer, C.c_void_p) else pointer
        self.real_free(pointer); self.freed.append(address)

    def output(self, result, text, status=0):
        raw = C.create_unicode_buffer(text)
        address = self.allocate(C.sizeof(raw)); self.assertTrue(address)
        C.memmove(address, raw, C.sizeof(raw)); self.allocations.append(address)
        C.cast(result, C.POINTER(C.c_void_p)).contents.value = address
        return status

    def tearDown(self):
        # Tests know exactly which controlled allocator calls actually ran.
        # Product UNCERTAIN records stay visible and are never relabelled closed.
        for address,count in (Counter(self.allocations)-Counter(self.freed)).items():
            for _ in range(count): self.free(C.c_void_p(address))
        NATIVE_ENVIRONMENT_RECEIPTS.append({'test_id':self.id(),
            'controlled_real_allocations':list(self.allocations),'actual_freed_addresses':list(self.freed),
            'all_controlled_allocations_released':not (Counter(self.allocations)-Counter(self.freed)),
            'product_pending_resources':list(self.api.pending_native_resources()),'observations':self.observations})

    def test_actual_known_folder_has_six_bounded_keys_and_no_pending_allocation(self):
        environment = self.api.environment(str(self.directory))
        self.assertEqual(set(environment), {'SystemRoot','WINDIR','PATH','TEMP','TMP','LOCALAPPDATA'})
        self.assertTrue(Path(environment['LOCALAPPDATA']).is_dir())
        self.assertEqual(self.api.pending_native_resources(), ())
        self.assertEqual(len(self.freed),1)
        self.observations.append({'environment':environment,'native_known_folder_allocation_freed':True})

    def test_actual_query_pins_GUID_current_user_and_no_create_flags(self):
        def observed(folder, flags, token, result):
            self.observations.append({'folder_GUID_bytes':C.string_at(folder,16).hex(),
                'flags':flags,'token':token})
            self.assertEqual(C.string_at(folder,16).hex(),'8527b3f1ba6fcf4f9d557b8e7f157091')
            self.assertEqual(flags,0x4000);self.assertIsNone(token)
            return self.real_query(folder,flags,token,result)
        self.api.SHGetKnownFolderPath = observed
        self.assertTrue(Path(self.api._local_appdata()).is_dir())
        self.assertFalse(self.api.pending_native_resources())

    def test_caller_environment_is_not_copied_into_native_allowlist(self):
        self.api.SHGetKnownFolderPath = lambda folder, flags, token, result:self.output(result,str(self.directory))
        with patch.dict(os.environ,{'LOCALAPPDATA':'PUBLIC_UNTRUSTED_PATH','PYTHONPATH':'PUBLIC_UNTRUSTED_IMPORT',
                                    'CETA_AC3_SECRET_SENTINEL':'PUBLIC_TEST_SENTINEL'}):
            environment=self.api.environment(str(self.directory))
        self.assertEqual(environment['LOCALAPPDATA'],str(self.directory))
        self.assertNotIn('PYTHONPATH',environment);self.assertNotIn('CETA_AC3_SECRET_SENTINEL',environment)

    def test_native_error_with_returned_allocation_is_freed_and_rejected(self):
        self.api.SHGetKnownFolderPath=lambda folder,flags,token,result:self.output(result,str(self.directory),-2147467259)
        with self.assertRaisesRegex(ContractError,'ISOLATION_LOCALAPPDATA_UNAVAILABLE'):self.api._local_appdata()
        self.assertEqual(self.allocations,self.freed);self.assertFalse(self.api.pending_native_resources())

    def test_native_error_without_output_is_rejected_without_free(self):
        self.api.SHGetKnownFolderPath=lambda *args:-2147467259
        with self.assertRaisesRegex(ContractError,'ISOLATION_LOCALAPPDATA_UNAVAILABLE'):self.api._local_appdata()
        self.assertFalse(self.freed);self.assertFalse(self.api.pending_native_resources())

    def test_native_success_without_output_is_rejected(self):
        self.api.SHGetKnownFolderPath=lambda *args:0
        with self.assertRaisesRegex(ContractError,'ISOLATION_LOCALAPPDATA_UNAVAILABLE'):self.api._local_appdata()
        self.assertFalse(self.api.pending_native_resources())

    def test_bool_HRESULT_does_not_replace_an_integer_success(self):
        self.api.SHGetKnownFolderPath=lambda folder,flags,token,result:self.output(result,str(self.directory),False)
        with self.assertRaisesRegex(ContractError,'ISOLATION_LOCALAPPDATA_RESPONSE_INVALID'):self.api._local_appdata()
        self.assertEqual(self.allocations,self.freed)

    def test_empty_and_overlong_native_paths_reject_and_free(self):
        for text in ('','x'*32767):
            with self.subTest(length=len(text)):
                self.api.SHGetKnownFolderPath=lambda folder,flags,token,result:self.output(result,text)
                with self.assertRaisesRegex(ContractError,'ISOLATION_LOCALAPPDATA_PATH_BOUND'):self.api._local_appdata()
        self.assertEqual(self.allocations,self.freed)

    def test_relative_UNC_missing_and_nondirectory_paths_reject_and_free(self):
        ordinary=self.directory/'ordinary.txt';ordinary.write_bytes(b'PUBLIC_AC3_TEST_SENTINEL')
        for text in ('relative',r'\\invalid.invalid\share',str(self.directory/'absent'),str(ordinary)):
            with self.subTest(text=text):
                self.api.SHGetKnownFolderPath=lambda folder,flags,token,result:self.output(result,text)
                with self.assertRaises(ContractError):self.api._local_appdata()
        self.assertEqual(self.allocations,self.freed)

    def test_query_response_loss_retains_exact_primary_and_uncertain_allocation(self):
        primary=KeyboardInterrupt('CONTROLLED_KNOWN_FOLDER_QUERY_RESPONSE_LOSS')
        def interrupted(folder,flags,token,result):
            self.output(result,str(self.directory));raise primary
        self.api.SHGetKnownFolderPath=interrupted
        with self.assertRaises(KeyboardInterrupt) as caught:self.api._local_appdata()
        self.assertIs(caught.exception,primary)
        self.assertTrue(callable(primary.isolation_cleanup.close_cleanup))
        pending=self.api.pending_native_resources()
        self.assertEqual(pending[0]['address'],self.allocations[0]);self.assertEqual(pending[0]['retry'],'UNCERTAIN')
        with self.assertRaisesRegex(ContractError,'ISOLATION_KNOWN_FOLDER_RELEASE_UNCERTAIN'):primary.isolation_cleanup.close_cleanup()
        self.assertFalse(self.freed)

    def test_free_then_response_loss_is_not_repeated(self):
        self.api.SHGetKnownFolderPath=lambda folder,flags,token,result:self.output(result,str(self.directory))
        primary=RuntimeError('CONTROLLED_KNOWN_FOLDER_FREE_RESPONSE_LOSS')
        def free_then_raise(pointer):self.free(pointer);raise primary
        self.api.CoTaskMemFree=free_then_raise
        with self.assertRaises(module.IsolatedLaunchError) as caught:self.api._local_appdata()
        self.assertIs(caught.exception.__cause__,primary)
        self.assertEqual(self.allocations,self.freed)
        with self.assertRaisesRegex(ContractError,'ISOLATION_KNOWN_FOLDER_RELEASE_UNCERTAIN'):caught.exception.close_cleanup()
        self.assertEqual(self.allocations,self.freed)

    def test_malformed_free_response_preserves_uncertainty_without_replay(self):
        self.api.SHGetKnownFolderPath=lambda folder,flags,token,result:self.output(result,str(self.directory))
        def free_then_bad(pointer):self.free(pointer);return 1
        self.api.CoTaskMemFree=free_then_bad
        with self.assertRaises(module.IsolatedLaunchError) as caught:self.api._local_appdata()
        self.assertEqual(self.api.pending_native_resources()[0]['retry'],'UNCERTAIN')
        with self.assertRaisesRegex(ContractError,'ISOLATION_KNOWN_FOLDER_RELEASE_UNCERTAIN'):caught.exception.close_cleanup()
        self.assertEqual(self.allocations,self.freed)

    def test_unknown_free_does_not_prevent_independent_native_handle_cleanup(self):
        self.api.SHGetKnownFolderPath=lambda folder,flags,token,result:self.output(result,str(self.directory))
        self.api.CoTaskMemFree=lambda pointer:(_ for _ in ()).throw(RuntimeError('CONTROLLED_BEFORE_FREE'))
        with self.assertRaises(module.IsolatedLaunchError):self.api._local_appdata()
        create=self.api.dll.CreateEventW;create.argtypes=[C.c_void_p,C.c_int32,C.c_int32,C.c_wchar_p];create.restype=module.HANDLE
        handle=create(None,True,False,None);self.assertTrue(handle);self.api.queue_handle(handle)
        with self.assertRaisesRegex(ContractError,'ISOLATION_KNOWN_FOLDER_RELEASE_UNCERTAIN'):self.api.retry_cleanup()
        flags=module.DWORD();self.assertFalse(self.api.GetHandleInformation(handle,C.byref(flags)))
        self.assertEqual(C.get_last_error(),6)
        self.assertFalse(self.freed)

    def test_environment_failure_denies_before_restricted_CreateProcess(self):
        image=Path(os.environ['CETA_AC3_IMAGE']);created=[];apis=[]
        class Refused(module._IsolationAPI):
            def __init__(inner):
                super().__init__();apis.append(inner)
                inner.SHGetKnownFolderPath=lambda *args:-2147467259
                inner.CreateProcessW=lambda *args:created.append(args)
        with patch.object(module,'_IsolationAPI',Refused),self.assertRaisesRegex(ContractError,'ISOLATION_LOCALAPPDATA_UNAVAILABLE'):
            module.IsolatedWindowsWorker.launch(str(image),('hold','100'),cwd=str(self.directory),scratch_root=str(self.directory),
                expected_image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),appcontainer_name='CETA.AC3.NoCreate')
        self.assertFalse(created);self.assertEqual(len(apis),1);self.assertFalse(apis[0].pending_native_resources())

    def test_native_queries_on_one_API_are_serialized_and_retired(self):
        values,failures=[],[]
        def sample():
            try:values.append(self.api._local_appdata())
            except BaseException as error:failures.append(type(error).__name__)
        threads=[threading.Thread(target=sample,name='AC3-known-folder-'+str(index)) for index in range(8)]
        for thread in threads:thread.start()
        for thread in threads:thread.join(3)
        self.assertFalse(any(thread.is_alive() for thread in threads));self.assertFalse(failures)
        self.assertEqual(len(values),8);self.assertEqual(len(set(values)),1)
        self.assertFalse(self.api.pending_native_resources());self.assertEqual(len(self.freed),8)


class NativeIsolatedWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        runtime = Path(os.environ['CETA_AC1_RUNTIME_ROOT']).resolve(strict=True)
        project = ROOT.parent.parent if ROOT.parent.name == '.agents' else ROOT
        permitted = project / '.agents/runtime/ac1-20261014'
        if not runtime.is_relative_to(permitted): raise AssertionError('exact AC1 runtime required')
        for parent in (runtime, *runtime.parents):
            if parent.is_symlink() or parent.is_junction(): raise AssertionError('linked review runtime denied')
        sys.path.insert(0, str(runtime))
        import native_fixture_support as helper
        cls.helper = helper
        cls.runtime = runtime

    def fixture(self): return self.helper.prepare_fixture()

    def launch(self, data, **changes):
        fixture, name, sid, image, asset, protected, setup = data
        kwargs = dict(cwd=str(fixture), scratch_root=str(fixture / 'scratch'),
                      expected_image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),
                      appcontainer_name=name)
        kwargs.update(changes)
        return IsolatedWindowsWorker.launch(str(image), ('hold', '100'), **kwargs)

    def test_actual_sid_derivation_is_stable_and_distinct(self):
        first = appcontainer_sid('CETA.AC1.ContractOne')
        self.assertEqual(first, appcontainer_sid('CETA.AC1.ContractOne'))
        self.assertNotEqual(first, appcontainer_sid('CETA.AC1.ContractTwo'))

    def test_container_name_rejects_unbounded_or_injected_input(self):
        for name in ('', 'Other.Profile', 'CETA.' + 'x' * 101, 'CETA.Bad\0Name'):
            with self.subTest(name=name), self.assertRaises(ContractError): appcontainer_sid(name)

    def test_missing_image_hash_denied_before_create(self):
        with self.assertRaisesRegex(ContractError, 'ISOLATION_IMAGE_PIN_REQUIRED'):
            self.launch(self.fixture(), expected_image_sha256=None)

    def test_mismatched_image_hash_denied_before_create(self):
        with self.assertRaisesRegex(ContractError, 'ISOLATION_IMAGE_PIN_MISMATCH'):
            self.launch(self.fixture(), expected_image_sha256='0' * 64)

    def test_invalid_handle_type_is_typed_denial(self):
        data = self.fixture()
        for handle in (True, 0, -1, [], {}):
            with self.subTest(type=type(handle).__name__), self.assertRaises(ContractError):
                self.launch(data, inherited_handles=(handle,))

    def test_excessive_handle_list_denied(self):
        with self.assertRaisesRegex(ContractError, 'ISOLATION_HANDLE_LIST_INVALID'):
            self.launch(self.fixture(), inherited_handles=tuple(range(1, 10)))

    def test_noninheritable_real_handle_denied(self):
        api = module._IsolationAPI()
        api.CreateEventW = api.dll.CreateEventW
        api.CreateEventW.argtypes = [C.c_void_p, C.c_int, C.c_int, C.c_wchar_p]
        api.CreateEventW.restype = module.HANDLE
        handle = api.CreateEventW(None, True, False, None)
        self.assertTrue(handle)
        try:
            with self.assertRaisesRegex(ContractError, 'ISOLATION_CHILD_HANDLE_NOT_INHERITABLE'):
                self.launch(self.fixture(), inherited_handles=(handle,))
        finally: api.close(handle)

    def test_standard_handles_require_exact_typed_triple(self):
        data = self.fixture()
        for handles in ([1, 2, 3], (1,), (True, 1, 2)):
            with self.subTest(handles=handles), self.assertRaises(ContractError):
                self.launch(data, standard_handles=handles)

    def test_argument_bounds_denied_before_native_create(self):
        data = self.fixture(); fixture, name, sid, image, *_ = data
        for args in (['hold', '100'], ('hold\0',), tuple('a' for _ in range(33)), ('x' * 4097,)):
            with self.subTest(kind=type(args).__name__), self.assertRaises(ContractError):
                IsolatedWindowsWorker.launch(str(image), args, cwd=str(fixture), scratch_root=str(fixture / 'scratch'),
                    expected_image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(), appcontainer_name=name)

    def test_environment_has_only_native_allowlist(self):
        data = self.fixture(); scratch = str(data[0] / 'scratch')
        with patch.dict(os.environ, {'CETA_AC1_SECRET_SENTINEL': 'PUBLIC_TEST_SENTINEL', 'PYTHONPATH': 'PUBLIC_UNTRUSTED_PATH'}):
            environment = module._IsolationAPI().environment(scratch)
        self.assertEqual(set(environment), {'SystemRoot', 'WINDIR', 'PATH', 'TEMP', 'TMP', 'LOCALAPPDATA'})
        self.assertEqual(environment['TEMP'], scratch)
        self.assertEqual(environment['TMP'], scratch)
        self.assertEqual(environment['PATH'], str(Path(environment['SystemRoot']) / 'System32'))
        self.assertTrue(Path(environment['LOCALAPPDATA']).is_dir())

    def test_sid_release_failure_retains_actual_allocation_for_recovery(self):
        api = module._IsolationAPI(); api.derive('CETA.AC1.Recovery')
        self.assertEqual(len(api.pending_sids), 1)
        real = api.FreeSid
        api.FreeSid = lambda pointer: pointer  # Explicit injected failed API return, no native free.
        try:
            with self.assertRaisesRegex(ContractError, 'ISOLATION_SID_RELEASE_UNRESOLVED'): api.release_sids()
            self.assertEqual(len(api.pending_sids), 1)
        finally:
            api.FreeSid = real; api.release_sids()
        self.assertEqual(api.pending_sids, [])

    def test_control_exception_preserved_and_real_resources_close(self):
        data = self.fixture(); observed = []
        class Interrupted(module._IsolationAPI):
            def __init__(self):
                super().__init__(); observed.append(self); self.closed_handles = []
                self.UpdateProcThreadAttribute = self.interrupt
            def interrupt(self, *args): raise KeyboardInterrupt('AC1_CONTROL_INTERRUPT')
            def close(self, handle):
                super().close(handle)
                if handle: self.closed_handles.append(handle)
        with patch.object(module, '_IsolationAPI', Interrupted):
            with self.assertRaisesRegex(KeyboardInterrupt, 'AC1_CONTROL_INTERRUPT'): self.launch(data)
        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0].pending_sids, [])
        self.assertEqual(len(observed[0].closed_handles), 3)
        for handle in observed[0].closed_handles:
            flags = module.DWORD()
            self.assertFalse(observed[0].GetHandleInformation(handle, C.byref(flags)))

    def test_primary_exception_and_failed_close_keep_exact_recoverable_cleanup(self):
        data = self.fixture(); observed = []
        class InterruptedClose(module._IsolationAPI):
            def __init__(self):
                super().__init__(); observed.append(self); self.fail_once = True
                self.UpdateProcThreadAttribute = self.interrupt
            def interrupt(self, *args): raise KeyboardInterrupt('AC1_PRIMARY')
            def close(self, handle):
                if handle and self.fail_once:
                    self.fail_once = False
                    raise ContractError('AC1_INJECTED_CLOSE_RETURN')
                return super().close(handle)
        with patch.object(module, '_IsolationAPI', InterruptedClose):
            with self.assertRaisesRegex(KeyboardInterrupt, 'AC1_PRIMARY') as result: self.launch(data)
        cleanup = result.exception.isolation_cleanup
        self.assertIsNone(cleanup.owned_process)
        self.assertIs(cleanup.isolation_api, observed[0])
        self.assertEqual(len(cleanup._cleanup_handles), 1)
        handle = cleanup._cleanup_handles[0]; flags = module.DWORD()
        self.assertTrue(observed[0].GetHandleInformation(handle, C.byref(flags)))
        cleanup.close_cleanup()
        self.assertFalse(observed[0].GetHandleInformation(handle, C.byref(flags)))
        self.assertEqual(observed[0].pending_sids, [])

    def test_actual_nonpersistent_launch_denial_and_medium_control_retirement(self):
        with self.assertRaisesRegex(ContractError, 'ISOLATION_RESTRICTED_CREATE_FAILED:2') as result:
            self.helper.run_native_probe('native-test-final')
        proof = json.loads(Path(result.exception.native_probe_receipt).read_text(encoding='utf-8'))
        self.assertEqual(proof['trusted_target']['integrity'], 'S-1-16-8192')
        self.assertIsNone(proof.get('worker_exit_code'))
        self.assertNotIn('facts', proof)
        self.assertEqual(len(proof['cleanup']), 1)
        retirement = proof['cleanup'][0]
        self.assertEqual(retirement['active_processes'], 0)
        self.assertTrue(retirement['lifetime_closed'])
        self.assertEqual(retirement['exit_code'], 125)
        # This is actual safe-denial evidence, not positive token/access/network qualification.


class NativeCleanupRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        NativeIsolatedWorkerTests.setUpClass.__func__(cls)

    def opened(self, api, handle):
        flags = module.DWORD()
        C.set_last_error(0)
        return bool(api.GetHandleInformation(handle, C.byref(flags)))

    def event(self, api):
        function = api.dll.CreateEventW
        function.argtypes = [C.c_void_p, C.c_int, C.c_int, C.c_wchar_p]
        function.restype = module.HANDLE
        handle = function(None, True, False, None)
        self.assertTrue(handle)
        return handle

    def test_independent_sid_release_continues_after_known_refusal(self):
        api = module._IsolationAPI()
        first, second = api.derive('CETA.AC2.First'), api.derive('CETA.AC2.Second')
        real_free, calls = api.FreeSid, []
        def refuse_first(pointer):
            calls.append(pointer)
            return pointer if pointer == first else real_free(pointer)
        api.FreeSid = refuse_first
        try:
            with self.assertRaisesRegex(ContractError, 'SID_RELEASE_UNRESOLVED'): api.release_sids()
            self.assertEqual(calls, [first, second])
            self.assertEqual(api.pending_sids, [first])
            self.assertTrue(api.IsValidSid(first))
        finally:
            api.FreeSid = real_free; api.release_sids()
        self.assertEqual(api.pending_native_resources(), ())

    def test_sid_free_then_control_exception_never_replays_uncertain_free(self):
        for kind in (KeyboardInterrupt, SystemExit):
            with self.subTest(control=kind.__name__):
                api = module._IsolationAPI(); pointer = api.derive('CETA.AC2.AfterFree')
                real_free, calls, primary = api.FreeSid, [], kind('AC2_AFTER_SID_FREE')
                def free_then_interrupt(value):
                    calls.append(value); self.assertIsNone(real_free(value)); raise primary
                api.FreeSid = free_then_interrupt
                with self.assertRaises(kind) as result: api.release_sids()
                self.assertIs(result.exception, primary)
                api.FreeSid = real_free
                with self.assertRaisesRegex(ContractError, 'SID_RELEASE_UNCERTAIN'): api.release_sids()
                self.assertEqual(calls, [pointer])
                self.assertEqual(api.pending_native_resources(), ({'kind': 'sid', 'address': pointer, 'retry': 'UNCERTAIN'},))
                # The real free succeeded before the injected interruption.
                # The retained unknown state is never dereferenced/freed again.

    def test_sid_text_refusal_retains_primary_and_explicit_native_recovery(self):
        api = module._IsolationAPI(); pointer = api.derive('CETA.AC2.Text')
        primary, real_free = KeyboardInterrupt('AC2_TEXT_PRIMARY'), api.LocalFree
        real_text = C.wstring_at
        api.LocalFree = lambda value: value.value
        try:
            with patch.object(C, 'wstring_at', side_effect=primary):
                with self.assertRaises(KeyboardInterrupt) as result: api.sid_text(pointer)
            self.assertIs(result.exception, primary)
            cleanup = primary.isolation_cleanup
            pending = [row for row in cleanup.pending_native_resources if row['kind'] == 'sid_text']
            self.assertEqual(len(pending), 1); self.assertEqual(pending[0]['retry'], 'PENDING')
            self.assertTrue(real_text(pending[0]['address']).startswith('S-1-15-2-'))
        finally:
            api.LocalFree = real_free; api.retry_cleanup()
        self.assertEqual(api.pending_native_resources(), ())

    def test_local_free_then_control_exception_is_not_repeated(self):
        api = module._IsolationAPI(); pointer = api.derive('CETA.AC2.TextAfterFree')
        real_free, calls = api.LocalFree, []
        primary = KeyboardInterrupt('AC2_AFTER_LOCAL_FREE')
        def free_then_interrupt(value):
            calls.append(value.value); self.assertIsNone(real_free(value)); raise primary
        api.LocalFree = free_then_interrupt
        with self.assertRaises(KeyboardInterrupt) as result: api.sid_text(pointer)
        self.assertIs(result.exception, primary)
        api.LocalFree = real_free
        with self.assertRaisesRegex(ContractError, 'SID_TEXT_RELEASE_UNCERTAIN'): primary.isolation_cleanup.close_cleanup()
        self.assertEqual(len(calls), 1)
        self.assertEqual(api.pending_sids, [])
        self.assertEqual([row['retry'] for row in api.pending_native_resources()], ['UNCERTAIN'])

    def test_reused_native_numeric_handle_is_preserved_during_cleanup_retry(self):
        api = module._IsolationAPI(); original = self.event(api)
        real_close, created = api.close, []
        primary = OSError('AC2_AFTER_HANDLE_CLOSE')
        def close_then_reuse(handle):
            real_close(handle)
            replacement = self.event(api); created.append(replacement)
            self.assertEqual(replacement, handle, 'actual native slot reuse required for this oracle')
            raise primary
        api.queue_handle(original); api.close = close_then_reuse
        try:
            with self.assertRaises(OSError) as result: api.retry_cleanup()
            self.assertIs(result.exception, primary)
            self.assertEqual(len(created), 1); self.assertTrue(self.opened(api, created[0]))
            api.close = real_close; api.retry_cleanup()
            self.assertTrue(self.opened(api, created[0]), 'retry closed a new occupant of the old numeric handle')
            self.assertEqual(api.pending_native_resources(), ())
        finally:
            api.close = real_close
            for handle in created:
                if self.opened(api, handle): api.close(handle)
            if api._pending_handles: api.retry_cleanup()

    def test_unobserved_close_return_stays_pending_until_real_native_close(self):
        api = module._IsolationAPI(); handle = self.event(api); real_close = api.close
        api.queue_handle(handle); api.close = lambda value: None
        try:
            with self.assertRaisesRegex(ContractError, 'HANDLE_CLOSE_NOT_OBSERVED'): api.retry_cleanup()
            self.assertTrue(self.opened(api, handle))
            self.assertEqual(api.pending_native_resources()[0]['handle'], handle)
        finally:
            api.close = real_close; api.retry_cleanup()
        self.assertFalse(self.opened(api, handle)); self.assertEqual(api.pending_native_resources(), ())

    def test_concurrent_explicit_recovery_closes_exact_token_once(self):
        api = module._IsolationAPI(); token = module.HANDLE()
        self.assertTrue(api.OpenProcessToken(api.GetCurrentProcess(), 8, C.byref(token)))
        real_close, calls = api.close, []
        def observed_close(handle): calls.append(handle); return real_close(handle)
        api.close = observed_close; api.queue_handle(token.value)
        cleanup = module.IsolatedLaunchError('AC2_RECOVERY', None, api)
        barrier, errors = threading.Barrier(3), []
        def recover():
            try: barrier.wait(2); cleanup.close_cleanup()
            except BaseException as error: errors.append(error)
        threads = [threading.Thread(target=recover) for _ in range(2)]
        for thread in threads: thread.start()
        barrier.wait(2)
        for thread in threads: thread.join(3); self.assertFalse(thread.is_alive())
        self.assertEqual(errors, []); self.assertEqual(calls, [token.value])
        self.assertFalse(self.opened(api, token.value)); self.assertEqual(api.pending_native_resources(), ())

    def test_attribute_delete_then_failure_keeps_uncertainty_without_replay(self):
        observed, primary = [], KeyboardInterrupt('AC2_ATTRIBUTES_PRIMARY')
        class Faulted(module._IsolationAPI):
            def __init__(self):
                super().__init__(); observed.append(self); self.deleted = 0
                self.real_delete = self.DeleteProcThreadAttributeList
                self.UpdateProcThreadAttribute = self.interrupt
                self.DeleteProcThreadAttributeList = self.delete_then_fail
            def interrupt(self, *args): raise primary
            def delete_then_fail(self, storage):
                self.real_delete(storage); self.deleted += 1; raise OSError('AC2_AFTER_DELETE')
        data = self.helper.prepare_fixture()
        with patch.object(module, '_IsolationAPI', Faulted):
            with self.assertRaises(KeyboardInterrupt) as result: NativeIsolatedWorkerTests.launch(self, data)
        self.assertIs(result.exception, primary)
        api, cleanup = observed[0], primary.isolation_cleanup
        with self.assertRaisesRegex(ContractError, 'ATTRIBUTES_RELEASE_UNCERTAIN'): cleanup.close_cleanup()
        self.assertEqual(api.deleted, 1); self.assertEqual(api.pending_sids, [])
        self.assertEqual([row['kind'] for row in cleanup.pending_native_resources], ['attributes'])

    def test_secondary_note_failure_never_replaces_primary_during_multiple_cleanup_failures(self):
        class Primary(KeyboardInterrupt):
            def add_note(self, value): raise OSError('AC2_NOTE_FAILURE')
        primary, observed = Primary('AC2_EXACT_PRIMARY'), []
        class Faulted(module._IsolationAPI):
            def __init__(self):
                super().__init__(); observed.append(self); self.refused_handle = None
                self.real_free, self.real_delete = self.FreeSid, self.DeleteProcThreadAttributeList
                self.FreeSid = lambda pointer: pointer
                self.UpdateProcThreadAttribute = self.interrupt
                self.DeleteProcThreadAttributeList = self.delete_then_fail
            def interrupt(self, *args): raise primary
            def delete_then_fail(self, storage): self.real_delete(storage); raise OSError('AC2_DELETE_FAILURE')
            def close(self, handle):
                if self.refused_handle is None:
                    self.refused_handle = handle; raise OSError('AC2_ONE_HANDLE_REFUSAL')
                return super().close(handle)
        data = self.helper.prepare_fixture()
        with patch.object(module, '_IsolationAPI', Faulted):
            with self.assertRaises(Primary) as result: NativeIsolatedWorkerTests.launch(self, data)
        self.assertIs(result.exception, primary)
        api, cleanup = observed[0], primary.isolation_cleanup
        self.assertEqual({row['kind'] for row in cleanup.pending_native_resources}, {'attributes', 'handle', 'sid'})
        self.assertEqual(len(api.last_cleanup_failures), 3)
        api.FreeSid = api.real_free
        with self.assertRaisesRegex(ContractError, 'ATTRIBUTES_RELEASE_UNCERTAIN'): cleanup.close_cleanup()
        self.assertFalse(self.opened(api, api.refused_handle)); self.assertEqual(api.pending_sids, [])
        self.assertEqual([row['kind'] for row in cleanup.pending_native_resources], ['attributes'])


    def test_secondary_handle_observation_failure_preserves_original_control_object(self):
        api = module._IsolationAPI(); handle = self.event(api)
        real_close, real_compare = api.close, api.CompareObjectHandles
        primary, secondary, comparisons = SystemExit('AC2_CLOSE_CONTROL'), OSError('AC2_COMPARE_FAILURE'), []
        def interrupted_close(value): raise primary
        def compare(first, second):
            comparisons.append((first, second))
            if len(comparisons) == 2: raise secondary
            return real_compare(first, second)
        api.close, api.CompareObjectHandles = interrupted_close, compare
        api.queue_handle(handle)
        try:
            with self.assertRaises(SystemExit) as result: api.retry_cleanup()
            self.assertIs(result.exception, primary)
            self.assertIs(primary.cleanup_observation_error, secondary)
            self.assertTrue(self.opened(api, handle))
        finally:
            api.close, api.CompareObjectHandles = real_close, real_compare
            api.retry_cleanup()
        self.assertFalse(self.opened(api, handle)); self.assertEqual(api.pending_native_resources(), ())

    def test_malformed_post_free_responses_remain_uncertain_without_double_free(self):
        api = module._IsolationAPI(); pointer = api.derive('CETA.AC2.MalformedSid')
        real_free, calls = api.FreeSid, []
        def malformed_sid(value):
            calls.append(value); self.assertIsNone(real_free(value)); return False
        api.FreeSid = malformed_sid
        with self.assertRaisesRegex(ContractError, 'SID_RELEASE_RESPONSE_INVALID'): api.release_sids()
        api.FreeSid = real_free
        with self.assertRaisesRegex(ContractError, 'SID_RELEASE_UNCERTAIN'): api.release_sids()
        self.assertEqual(calls, [pointer])

        text_api = module._IsolationAPI(); text_sid = text_api.derive('CETA.AC2.MalformedText')
        local_free, local_calls = text_api.LocalFree, []
        def malformed_local(value):
            local_calls.append(value.value); self.assertIsNone(local_free(value)); return False
        text_api.LocalFree = malformed_local
        with self.assertRaises(module.IsolatedLaunchError) as result: text_api.sid_text(text_sid)
        text_api.LocalFree = local_free
        with self.assertRaisesRegex(ContractError, 'SID_TEXT_RELEASE_UNCERTAIN'): result.exception.close_cleanup()
        self.assertEqual(len(local_calls), 1); self.assertEqual(text_api.pending_sids, [])


if __name__ == '__main__': unittest.main()
