"""AC1 exact binding/fail-closed resource cleanup tests.

Successful native bypass qualification is a separate, explicitly blocked
obligation when this host refuses no-profile AppContainer creation. These tests
never reinterpret a restrictive launch failure as successful isolation.
"""
from pathlib import Path
import ctypes as C
import hashlib
import json
import os
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
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
        self.assertEqual(set(environment), {'SystemRoot', 'WINDIR', 'PATH', 'TEMP', 'TMP'})
        self.assertEqual(environment['TEMP'], scratch)
        self.assertEqual(environment['TMP'], scratch)
        self.assertEqual(environment['PATH'], str(Path(environment['SystemRoot']) / 'System32'))

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


if __name__ == '__main__': unittest.main()
