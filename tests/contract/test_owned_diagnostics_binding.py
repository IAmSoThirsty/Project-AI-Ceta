"""Controlled retained-owner binding; no native launch or profile creation."""
from dataclasses import FrozenInstanceError, replace
import copy
from pathlib import Path
import sys
import threading
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from ceta.composition import owned_service as binding
from ceta.composition.owned_service import OwnedService
from ceta.contracts.wire import ContractError


GENERATION = 'a' * 64


class RetainedProcess:
    def poll(self):
        raise AssertionError('binding must not query physical lifetime under controller lock')

    def close(self):
        raise AssertionError('borrowed process must not be closed')

    def terminate(self):
        raise AssertionError('borrowed process must not be terminated')

    def resource_observation_current(self, identity):
        raise AssertionError('physical observation belongs to the collector outside this binding')


class OwnedDiagnosticsBindingTests(unittest.TestCase):
    def service(self):
        # Populate only retained controller metadata. This is not a native
        # lifetime or authorization fixture and starts no executable/store.
        service = OwnedService.__new__(OwnedService)
        service._lock = threading.RLock()
        service._generation = GENERATION
        service._state = 'READY'
        service._installation = 'installation:controlled'
        service._scopes = ('installation:controlled', 'scope:controlled')
        service._root = Path(__file__).resolve().parents[2] / '.agents/fixtures/never-created'
        service._codec = object()
        service._service = SimpleNamespace(process=RetainedProcess(), _closed=False, _process_closed=False)
        service._client = SimpleNamespace(process=RetainedProcess(), _closed=False, _process_closed=False)
        service._closed_channels = set()
        service._pending = service._send_task = service._uncertain_task_request = None
        service._workers = []
        service._launches_in_progress = 0
        service._service_launch_pending = False
        service._launch_slots = set()
        service._positions = ({'startup_only': 'must not be consumed'},)
        return service

    def unavailable(self, service):
        with self.assertRaises(ContractError) as error:
            service._diagnostics_owner_snapshot(GENERATION)
        self.assertEqual(error.exception.code, 'SERVICE_DIAGNOSTICS_OWNER_UNAVAILABLE')

    def test_snapshot_borrows_exact_fixed_owner_ports_and_is_frozen(self):
        service = self.service()
        snapshot = service._diagnostics_owner_snapshot(GENERATION)
        self.assertIs(type(snapshot), binding.OwnedDiagnosticsSnapshot)
        self.assertEqual(snapshot.generation, GENERATION)
        self.assertEqual(snapshot.installation_scope_id, 'installation:controlled')
        self.assertIs(snapshot.scopes, service._scopes)
        self.assertIs(snapshot.profile_root, service._root)
        self.assertIs(snapshot.codec, service._codec)
        self.assertIs(snapshot.service_process, service._service.process)
        self.assertIs(snapshot.client_process, service._client.process)
        self.assertTrue(service._diagnostics_owner_current(snapshot))
        self.assertFalse(hasattr(snapshot, 'positions'))
        with self.assertRaises(FrozenInstanceError):
            snapshot.generation = 'b' * 64
        self.assertFalse(service._root.exists())

    def test_generation_validation_is_exact_and_precedes_binding_work(self):
        service = self.service()
        for value in (None, True, 0, 1, '', 'a' * 63, 'a' * 65, 'A' * 64, 'g' * 64):
            with self.subTest(value=value), patch.object(service, '_diagnostics_binding_available', side_effect=AssertionError):
                with self.assertRaises(ContractError) as error:
                    service._diagnostics_owner_snapshot(value)
                self.assertEqual(error.exception.code, 'SERVICE_DIAGNOSTICS_GENERATION_INVALID')
        with self.assertRaises(ContractError) as error:
            service._diagnostics_owner_snapshot('b' * 64)
        self.assertEqual(error.exception.code, 'SERVICE_DIAGNOSTICS_GENERATION_CHANGED')

    def test_nonready_busy_uncertain_launch_and_closed_bindings_are_rejected(self):
        variants = [('_state', state) for state in ('STOPPED', 'STARTING', 'STOPPING', 'RECOVERING')]
        variants += [('_pending', {}), ('_send_task', {}), ('_uncertain_task_request', object()),
                     ('_workers', [{}]), ('_launches_in_progress', 1), ('_service_launch_pending', True),
                     ('_launch_slots', {'service'}), ('_unresolved_launch', object()),
                     ('_service', None), ('_client', None), ('_service', SimpleNamespace()),
                     ('_installation', 'installation:other')]
        for name, value in variants:
            service = self.service()
            snapshot = service._diagnostics_owner_snapshot(GENERATION)
            setattr(service, name, value)
            with self.subTest(name=name, value=value):
                self.unavailable(service)
                self.assertFalse(service._diagnostics_owner_current(snapshot))
        for role in ('_service', '_client'):
            for closure in ('_closed', '_process_closed', 'registered_closed', 'missing_process'):
                service = self.service()
                snapshot = service._diagnostics_owner_snapshot(GENERATION)
                channel = getattr(service, role)
                if closure == 'registered_closed':
                    service._closed_channels.add(id(channel))
                elif closure == 'missing_process':
                    channel.process = None
                else:
                    setattr(channel, closure, True)
                with self.subTest(role=role, closure=closure):
                    self.unavailable(service)
                    self.assertFalse(service._diagnostics_owner_current(snapshot))

    def test_same_process_cannot_supply_both_fixed_roles(self):
        service = self.service()
        service._client.process = service._service.process
        self.unavailable(service)
        service = self.service()
        service._client = service._service
        self.unavailable(service)

    def test_project_scope_and_malformed_installation_cannot_select_aggregate(self):
        for installation, scopes in (('scope:project', ('scope:project',)), ('installation:', ('installation:',)),
                ('installation:controlled', ('installation:controlled',) * 2),
                ('installation:controlled', ('installation:controlled', True))):
            service = self.service()
            service._installation, service._scopes = installation, scopes
            with self.subTest(installation=installation, scopes=scopes):
                self.unavailable(service)

    def test_generation_configuration_and_owner_replacement_invalidate_snapshot(self):
        changes = [('_generation', 'b' * 64), ('_installation', 'installation:other'),
                   ('_scopes', ('installation:controlled',)), ('_root', Path('replacement')),
                   ('_codec', object())]
        for name, value in changes:
            service = self.service()
            snapshot = service._diagnostics_owner_snapshot(GENERATION)
            setattr(service, name, value)
            with self.subTest(name=name):
                self.assertFalse(service._diagnostics_owner_current(snapshot))
        service = self.service()
        snapshot = service._diagnostics_owner_snapshot(GENERATION)
        copied = copy.copy(snapshot)
        service._service.process = RetainedProcess()
        self.assertFalse(service._diagnostics_owner_current(snapshot))
        self.assertFalse(service._diagnostics_owner_current(copied))
        renewed = service._diagnostics_owner_snapshot(GENERATION)
        self.assertTrue(service._diagnostics_owner_current(renewed))
        self.assertIsNot(renewed.service_process, snapshot.service_process)

    def test_current_refuses_structural_lookalikes_and_malformed_fields(self):
        service = self.service()
        snapshot = service._diagnostics_owner_snapshot(GENERATION)
        for value in (None, object(), SimpleNamespace(**vars(snapshot)), replace(snapshot, generation=True),
                      replace(snapshot, generation='A' * 64), replace(snapshot, installation_scope_id=object()),
                      replace(snapshot, codec=object()), replace(snapshot, scopes=('scope:foreign',)),
                      replace(snapshot, service_process=RetainedProcess()),
                      replace(snapshot, client_process=snapshot.service_process)):
            with self.subTest(value=type(value)):
                self.assertFalse(service._diagnostics_owner_current(value))

    def test_lazy_delegation_forwards_exact_keywords_without_holding_lock(self):
        service, envelope, cancelled = self.service(), object(), lambda: False
        module, observed = ModuleType('ceta.composition.resource_diagnostics'), []
        def collect(owner, **keywords):
            acquired = threading.Event()
            def independent():
                with service._lock:
                    acquired.set()
            worker = threading.Thread(target=independent)
            worker.start()
            worker.join(2)
            self.assertFalse(worker.is_alive())
            self.assertTrue(acquired.is_set(), 'controller lock spans collector callback')
            observed.append((owner, keywords))
            return 'bounded-result'
        module.collect_owned_diagnostics = collect
        with patch.dict(sys.modules, {'ceta.composition.resource_diagnostics': module}):
            result = service.resource_diagnostics(expected_generation=GENERATION, envelope=envelope,
                maximum_age_ns=300, sample_interval_ns=20, cancelled=cancelled)
        self.assertEqual(result, 'bounded-result')
        self.assertEqual(observed, [(service, dict(expected_generation=GENERATION, envelope=envelope,
            maximum_age_ns=300, sample_interval_ns=20, cancelled=cancelled))])

    def test_public_operation_has_no_caller_role_pid_or_scope_selector(self):
        service = self.service()
        for selector in ({'pid': 7}, {'role': 'foreign'}, {'scope_id': 'scope:project'}):
            with self.subTest(selector=selector), self.assertRaises(TypeError):
                service.resource_diagnostics(expected_generation=GENERATION, envelope=object(), **selector)

    def test_stop_during_collection_invalidates_owner_without_waiting_for_callback(self):
        service, entered, release = self.service(), threading.Event(), threading.Event()
        module = ModuleType('ceta.composition.resource_diagnostics')
        results, errors = [], []
        def collect(owner, **keywords):
            snapshot = owner._diagnostics_owner_snapshot(keywords['expected_generation'])
            entered.set()
            if not release.wait(2):
                raise AssertionError('controlled collector barrier timed out')
            return owner._diagnostics_owner_current(snapshot)
        module.collect_owned_diagnostics = collect
        def run():
            try:
                results.append(service.resource_diagnostics(expected_generation=GENERATION, envelope=object()))
            except BaseException as error:
                errors.append(error)
        with patch.dict(sys.modules, {'ceta.composition.resource_diagnostics': module}):
            worker = threading.Thread(target=run)
            worker.start()
            try:
                self.assertTrue(entered.wait(2))
                with service._lock:
                    service._state = 'STOPPING'
            finally:
                release.set()
                worker.join(2)
        self.assertFalse(worker.is_alive())
        self.assertEqual((results, errors), ([False], []))


if __name__ == '__main__':
    unittest.main()
