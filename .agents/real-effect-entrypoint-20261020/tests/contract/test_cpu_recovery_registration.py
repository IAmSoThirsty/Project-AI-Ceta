"""Actual recovery registration under controlled allocation/cleanup failures."""
from types import SimpleNamespace
import threading
import unittest
from unittest.mock import patch

from ceta.kernel import cpu_execution as module


class _FailingTable(dict):
    def __init__(self, primary=None, *, after_publish=False, cleanup_error=None):
        super().__init__()
        self.primary = primary
        self.after_publish = after_publish
        self.cleanup_error = cleanup_error

    def __setitem__(self, key, value):
        if self.after_publish:
            super().__setitem__(key, value)
        if self.primary is not None:
            raise self.primary
        if not self.after_publish:
            super().__setitem__(key, value)

    def __delitem__(self, key):
        if self.cleanup_error is not None:
            raise self.cleanup_error
        super().__delitem__(key)


class RecoveryRegistrationTests(unittest.TestCase):
    def fixture(self):
        coordinator = object.__new__(module._CpuExecutionCoordinator)
        coordinator.owners, coordinator.store = object(), object()
        coordinator.kernel = SimpleNamespace(_owners=coordinator.owners, _store=coordinator.store)
        coordinator.active, coordinator.mutating = None, 0
        lease = object.__new__(module._RetainedCpuExecution)
        lease._owner, lease._recovery = coordinator, object()
        lease._called, lease._dispatching = True, False
        lease._thread, lease._closed = threading.get_ident(), True
        lease._pending_cleanup, lease._cleanup_failure = False, None
        return coordinator, lease

    def maps(self, owners, stores):
        return patch.multiple(module, _ACTIVE_OWNERS=owners, _ACTIVE_STORES=stores,
                              _MUTATING_OWNERS={}, _MUTATING_STORES={})

    def assert_failure_retired(self, owners, stores, primary):
        coordinator, lease = self.fixture()
        with self.maps(owners, stores):
            try:
                coordinator.claim_recovery_liveness(lease)
            except BaseException as error:
                self.assertIs(error, primary)
            else:
                self.fail('publication failure was not propagated')
            self.assertEqual(owners, {})
            self.assertEqual(stores, {})
            self.assertIsNone(coordinator.active)
            coordinator.require_selected_coordinator()
            self.assertFalse(lease._pending_cleanup)

    def test_owner_publication_failure_before_insert(self):
        primary = MemoryError('controlled first publication')
        self.assert_failure_retired(_FailingTable(primary), {}, primary)

    def test_owner_publication_failure_after_insert(self):
        primary = MemoryError('controlled first publication after insertion')
        self.assert_failure_retired(_FailingTable(primary, after_publish=True), {}, primary)

    def test_store_publication_failure_before_insert(self):
        primary = MemoryError('controlled second publication')
        self.assert_failure_retired({}, _FailingTable(primary), primary)

    def test_store_publication_failure_after_insert(self):
        primary = MemoryError('controlled second publication after insertion')
        self.assert_failure_retired({}, _FailingTable(primary, after_publish=True), primary)

    def test_control_exception_identity_survives(self):
        for primary in (KeyboardInterrupt(), SystemExit(17)):
            with self.subTest(primary=type(primary).__name__):
                self.assert_failure_retired({}, _FailingTable(primary), primary)

    def test_cleanup_failure_retains_exact_lease_and_primary(self):
        coordinator, lease = self.fixture()
        primary = MemoryError('controlled publication')
        secondary = RuntimeError('controlled cleanup')
        owners = _FailingTable(cleanup_error=secondary)
        stores = _FailingTable(primary)
        with self.maps(owners, stores):
            with self.assertRaises(MemoryError) as caught:
                coordinator.claim_recovery_liveness(lease)
            self.assertIs(caught.exception, primary)
            self.assertIs(owners[id(coordinator.owners)][3], lease)
            self.assertTrue(lease._pending_cleanup)
            self.assertIs(lease._cleanup_failure, secondary)
            data = BaseException.__dict__['__dict__'].__get__(primary)
            self.assertIn(lease, data['cpu_registration_custody'])
            self.assertIs(data['cpu_registration_cleanup_failures'][0][0], secondary)
            with self.assertRaisesRegex(module.ContractError, 'OTHER_KERNEL_ACTIVE'):
                coordinator.require_selected_coordinator()
            owners.cleanup_error = None
            coordinator.release_liveness(lease)
            self.assertEqual(owners, {})
            self.assertEqual(stores, {})
            coordinator.require_selected_coordinator()

    def test_denied_claim_preserves_other_lease_registration(self):
        coordinator, lease = self.fixture()
        winner = object()
        row = (coordinator.owners, coordinator.store, coordinator, winner)
        owners, stores = {id(coordinator.owners): row}, {id(coordinator.store): row}
        with self.maps(owners, stores):
            with self.assertRaisesRegex(module.ContractError, 'OTHER_KERNEL_ACTIVE'):
                coordinator.claim_recovery_liveness(lease)
            self.assertIs(owners[id(coordinator.owners)][3], winner)
            self.assertIs(stores[id(coordinator.store)][3], winner)
            self.assertIsNone(coordinator.active)

    def test_success_and_exact_release(self):
        coordinator, lease = self.fixture()
        owners, stores = {}, {}
        with self.maps(owners, stores):
            coordinator.claim_recovery_liveness(lease)
            self.assertIs(coordinator.active, lease)
            self.assertIs(owners[id(coordinator.owners)][3], lease)
            self.assertIs(stores[id(coordinator.store)][3], lease)
            coordinator.require_selected_coordinator()
            coordinator.release_liveness(lease)
            self.assertIsNone(coordinator.active)
            self.assertEqual(owners, {})
            self.assertEqual(stores, {})
