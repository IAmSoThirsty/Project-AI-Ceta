"""Actual Windows file identities/SQLite/pipe peers; no grants or native consent."""
from dataclasses import replace
from contextlib import closing
from pathlib import Path
import ctypes as C
import os
import sqlite3
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from ceta.contracts.wire import ContractError
from ceta.identity import native_owner_view as view
from ceta.identity.native_clock import NativeSessionClock
from ceta.identity.windows_pipe import WindowsPeerRegistry, WindowsPipeServer
import test_windows_pipe as pipe_tests

ROOT = Path(__file__).resolve().parents[2]
NATIVE_RECEIPTS = []


class NativeStoreBindingTests(unittest.TestCase):
    def setUp(self):
        self.directory = ROOT / '.agents/fixtures' / ('nv-' + uuid.uuid4().hex)
        self.directory.mkdir(parents=True)
        self.database = self.directory / 'history.sqlite3'
        with closing(sqlite3.connect(self.database)) as store, store:
            store.execute('CREATE TABLE witness (value INTEGER NOT NULL)')
        self.bindings = []

    def tearDown(self):
        for binding in self.bindings:
            binding.close()
            self.assertTrue(binding.closed)
            self.assertFalse(binding.pending_native_resources)
        NATIVE_RECEIPTS.append({'test_id':self.id(),'directory':str(self.directory),
            'all_bindings_closed':all(binding.closed for binding in self.bindings)})

    def opened(self, **kwargs):
        try: binding = view.NativeStoreBinding(self.directory, **kwargs)
        except BaseException as error:
            retained = BaseException.__dict__['__dict__'].__get__(error).get('native_owner_view')
            if retained is not None: self.bindings.append(retained)
            raise
        self.bindings.append(binding)
        return binding

    def test_actual_volume_and_file_ids_are_distinct_full_width_and_current(self):
        binding = self.opened()
        self.assertEqual(binding.private_root.kind, 'directory')
        self.assertEqual(binding.database.kind, 'file')
        self.assertEqual(binding.database.path, binding.private_root.path + '\\history.sqlite3')
        self.assertEqual(binding.private_root.volume_serial_hex, binding.database.volume_serial_hex)
        self.assertNotEqual(binding.private_root.file_id_hex, binding.database.file_id_hex)
        self.assertEqual(len(binding.database.file_id_hex), 32)
        self.assertEqual(len(binding.database.volume_serial_hex), 16)
        self.assertIsNone(binding.require_current())

    def test_reopen_exact_native_expectation_observes_same_objects(self):
        first = self.opened()
        second = self.opened(expected_root=first.private_root, expected_database=first.database)
        self.assertEqual(second.private_root, first.private_root)
        self.assertEqual(second.database, first.database)

    def test_sqlite_writes_continue_on_the_same_canonical_database_identity(self):
        binding = self.opened(); before = binding.database
        with closing(sqlite3.connect(self.database)) as store, store:
            store.execute('INSERT INTO witness VALUES (?)', (37,))
            store.commit()
            self.assertEqual(store.execute('SELECT value FROM witness').fetchall(), [(37,)])
        self.assertIsNone(binding.require_current())
        self.assertEqual(binding.database, before)

    def test_actual_replacement_is_denied_while_retained_and_detected_after_release(self):
        binding = self.opened(); old_root, old_database = binding.private_root, binding.database
        replacement = self.directory / 'replacement.sqlite3'
        replacement.write_bytes(self.database.read_bytes())
        with self.assertRaises(OSError): os.replace(replacement, self.database)
        self.assertTrue(replacement.exists()); binding.require_current()
        binding.close()
        os.replace(replacement, self.database)
        with self.assertRaisesRegex(ContractError, 'EXPECTED_OBJECT_MISMATCH'):
            self.opened(expected_root=old_root, expected_database=old_database)

    def test_exact_native_expectation_refuses_different_file_id_and_root(self):
        binding = self.opened()
        for root, database in ((replace(binding.private_root, file_id_hex='0'*32), binding.database),
                (binding.private_root, replace(binding.database, file_id_hex='0'*32))):
            with self.subTest(root=root.file_id_hex, database=database.file_id_hex), self.assertRaises(ContractError):
                self.opened(expected_root=root, expected_database=database)

    def test_missing_database_is_denied_without_creation_and_all_handles_retire(self):
        directory = self.directory / 'missing'; directory.mkdir()
        with self.assertRaises(ContractError) as caught: view.NativeStoreBinding(directory)
        binding = caught.exception.native_owner_view
        self.bindings.append(binding)
        self.assertFalse((directory/'history.sqlite3').exists())
        self.assertTrue(binding.closed); self.assertFalse(binding.pending_native_resources)

    def test_directory_instead_of_database_is_denied_and_never_repurposed(self):
        directory = self.directory / 'directory-db'; directory.mkdir(); (directory/'history.sqlite3').mkdir()
        with self.assertRaises(ContractError) as caught: view.NativeStoreBinding(directory)
        self.bindings.append(caught.exception.native_owner_view)
        self.assertTrue((directory/'history.sqlite3').is_dir())

    def test_all_retained_native_file_handles_are_noninheritable(self):
        binding = self.opened()
        for row in binding._pins:
            flags = view.DWORD(999)
            self.assertTrue(binding._api.GetHandleInformation(row['handle'], C.byref(flags)))
            self.assertEqual(flags.value & 1, 0)

    def test_failed_current_observation_never_becomes_a_measured_match(self):
        binding = self.opened(); original = binding._read
        def changed(row):
            result = original(row)
            return replace(result, file_id_hex='0'*32) if row is binding._pins[-1] else result
        with patch.object(binding, '_read', side_effect=changed):
            with self.assertRaisesRegex(ContractError, 'IDENTITY_CHANGED'): binding.require_current()
        binding.require_current()

    def test_slow_observation_is_rejected_without_claiming_native_preemption(self):
        binding = self.opened()
        with patch.object(view.time, 'perf_counter_ns', side_effect=(1, view.MAXIMUM_OBSERVATION_NS+2)):
            with self.assertRaisesRegex(ContractError, 'OBSERVATION_STALE'): binding.require_current()
        binding.require_current()

    def test_actual_two_second_native_observation_cannot_round_down_to_success(self):
        binding = self.opened(); original = binding._read
        def delayed(row):
            observed = original(row)
            if row is binding._pins[-1]: time.sleep(2.001)
            return observed
        before = time.perf_counter_ns()
        with patch.object(binding, '_read', side_effect=delayed):
            with self.assertRaisesRegex(ContractError, 'OBSERVATION_STALE'): binding.require_current()
        self.assertGreater(time.perf_counter_ns() - before, 2_000_000_000)
        self.assertEqual(view.MAXIMUM_OBSERVATION_NS, 2_000_000_000)
        binding.require_current()

    def test_stopwatch_charges_both_endpoint_resolutions_at_inclusive_boundary(self):
        binding = self.opened()
        info = SimpleNamespace(implementation='QueryPerformanceCounter()', monotonic=True,
            adjustable=False, resolution=1e-7)
        with patch.object(view.time, 'get_clock_info', return_value=info):
            for excess in (0, 1):
                with self.subTest(excess=excess), patch.object(view.time, 'perf_counter_ns',
                        side_effect=(1000, 1000 + view.MAXIMUM_OBSERVATION_NS - 200 + excess)):
                    if excess:
                        with self.assertRaisesRegex(ContractError, 'OBSERVATION_STALE'): binding.require_current()
                    else: self.assertIsNone(binding.require_current())

    def test_stopwatch_invalid_unavailable_or_coarse_sources_are_denied(self):
        valid = dict(implementation='QueryPerformanceCounter()', monotonic=True,
            adjustable=False, resolution=1e-7)
        changes = (dict(implementation='GetTickCount64()'), dict(monotonic=False),
            dict(monotonic=1), dict(adjustable=True), dict(adjustable=0),
            dict(resolution=0), dict(resolution=-1), dict(resolution=float('nan')),
            dict(resolution=float('inf')), dict(resolution=True), dict(resolution=1),
            dict(resolution='1e-7'))
        for change in changes:
            with self.subTest(change=change), patch.object(view.time, 'get_clock_info',
                    return_value=SimpleNamespace(**(valid | change))):
                with self.assertRaisesRegex(ContractError, 'STOPWATCH_UNAVAILABLE'): view._stopwatch_start()
        for error in (OSError('unavailable'), ValueError('unavailable')):
            with patch.object(view.time, 'get_clock_info', side_effect=error):
                with self.assertRaisesRegex(ContractError, 'STOPWATCH_UNAVAILABLE'): view._stopwatch_start()

    def test_stopwatch_tick_type_rollback_and_control_failure_remain_explicit(self):
        for value in (True, -1, 1.5, None):
            with self.subTest(value=value), patch.object(view.time, 'perf_counter_ns', return_value=value):
                with self.assertRaisesRegex(ContractError, 'STOPWATCH_UNAVAILABLE'): view._stopwatch_start()
        with patch.object(view.time, 'perf_counter_ns', side_effect=(10, 9)):
            start = view._stopwatch_start()
            with self.assertRaisesRegex(ContractError, 'STOPWATCH_ROLLBACK'): view._stopwatch_elapsed(start)
        with patch.object(view.time, 'perf_counter_ns', side_effect=OSError('unavailable')):
            with self.assertRaisesRegex(ContractError, 'STOPWATCH_UNAVAILABLE'): view._stopwatch_start()
        primary = KeyboardInterrupt('STOPWATCH_CONTROL')
        with patch.object(view.time, 'perf_counter_ns', side_effect=primary):
            with self.assertRaises(KeyboardInterrupt) as caught: view._stopwatch_start()
        self.assertIs(caught.exception, primary)

    def test_control_exception_with_refusing_attributes_keeps_exact_primary_and_custody(self):
        binding = self.opened()
        class Primary(KeyboardInterrupt):
            def __setattr__(self, name, value): raise RuntimeError('CONTROLLED_REFUSING_SETTER')
            @property
            def add_note(self): raise RuntimeError('CONTROLLED_REFUSING_NOTE_LOOKUP')
        primary = Primary('CONTROLLED_FILE_CLEANUP_PRIMARY')
        with patch.object(binding._api, 'retry_cleanup', side_effect=primary):
            with self.assertRaises(Primary) as caught: binding.close()
        self.assertIs(caught.exception, primary)
        storage = BaseException.__dict__['__dict__'].__get__(primary)
        self.assertIs(storage['native_owner_view'], binding)
        self.assertTrue(binding.pending_native_resources)
        storage['close_cleanup']()
        self.assertTrue(binding.closed)

    def test_context_primary_survives_cleanup_denial_and_can_recover(self):
        binding = self.opened(); primary = SystemExit('CONTROLLED_CONTEXT_PRIMARY')
        with patch.object(binding._api, 'retry_cleanup', side_effect=OSError('CONTROLLED_CLEANUP_REFUSAL')):
            with self.assertRaises(SystemExit) as caught:
                with binding: raise primary
        self.assertIs(caught.exception, primary)
        self.assertIs(primary.native_owner_view, binding)
        binding.close()

    def test_close_is_idempotent_and_closed_view_never_revalidates(self):
        binding = self.opened(); binding.close(); binding.close()
        with self.assertRaisesRegex(ContractError, 'CLOSED'): binding.require_current()

    def test_file_currentness_and_close_are_serialized_without_lost_custody(self):
        binding = self.opened(); barrier = threading.Barrier(2); outcomes = []
        def check():
            barrier.wait()
            try: binding.require_current(); outcomes.append('CURRENT')
            except ContractError as error: outcomes.append(error.code)
        thread = threading.Thread(target=check); thread.start(); barrier.wait(); binding.close(); thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(outcomes), 1)
        self.assertIn(outcomes[0], ('CURRENT', 'OWNER_VIEW_CLOSED'))


class NativeOwnerRequestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): pipe_tests.WindowsPipeTests.setUpClass()

    def setUp(self):
        self.fixture = pipe_tests.WindowsPipeTests('test_registered_os_peer_reaches_handler_and_context_expires_after_dispatch')
        self.fixture.setUp()
        self.directory = ROOT / '.agents/fixtures' / ('np-' + uuid.uuid4().hex)
        self.directory.mkdir(parents=True)
        with closing(sqlite3.connect(self.directory/'history.sqlite3')) as store, store:
            store.execute('CREATE TABLE witness (value)')
        self.binding = view.NativeStoreBinding(self.directory)
        self.clock = NativeSessionClock(0)
        self.native_view = view.NativeOwnerView(self.fixture.registry, self.clock, self.binding)

    def tearDown(self):
        self.fixture.tearDown(); self.clock.close(); self.binding.close()
        self.assertFalse(self.binding.pending_native_resources)
        self.assertFalse(self.clock.status().sampler_alive)
        NATIVE_RECEIPTS.append({'test_id':self.id(),'directory':str(self.directory),
            'all_bindings_closed':self.binding.closed,'clock_closed':self.clock.status().state == 'CLOSED'})

    def test_actual_registered_pipe_context_observes_owner_and_rejects_after_dispatch(self):
        fixture = self.fixture; contexts = []
        def handler(message, context):
            contexts.append(context)
            return self.native_view.observe(context)
        fixture.server.close()
        fixture.server = WindowsPipeServer(fixture.pipe_name, fixture.registry, handler, fixture.codec)
        fixture.generation = fixture.server.receiver_generation
        client = fixture.client()
        success, observed, answer = fixture.send(client, fixture.message())
        self.assertTrue(success, str(observed))
        self.assertEqual(observed.owner_facts, view.registration_token_facts(client.registration))
        self.assertEqual(observed.owner_facts.process_identity.pid, client.process.pid)
        self.assertEqual(observed.database, self.binding.database)
        self.assertEqual(observed.peer.principal_id, fixture.principal)
        self.assertEqual(answer, {'sent':True, 'returned_none':True})
        with self.assertRaises(ContractError): self.native_view.observe(contexts[0])

    def test_actual_registered_context_is_denied_from_another_native_thread(self):
        fixture = self.fixture; denied = []
        def handler(message, context):
            def other():
                try: self.native_view.observe(context)
                except ContractError as error: denied.append(error.code)
            thread = threading.Thread(target=other); thread.start(); thread.join(5)
            self.assertFalse(thread.is_alive())
            return self.native_view.observe(context)
        fixture.server.close()
        fixture.server = WindowsPipeServer(fixture.pipe_name, fixture.registry, handler, fixture.codec)
        fixture.generation = fixture.server.receiver_generation
        success, result, _ = fixture.send(fixture.client(), fixture.message())
        self.assertTrue(success, str(result))
        self.assertEqual(denied, ['WINDOWS_REQUEST_CONTEXT_UNAVAILABLE'])

    def test_fabricated_context_or_fake_provider_does_not_establish_owner(self):
        with self.assertRaises(ContractError): self.native_view.observe(object())
        for arguments in ((object(),self.clock,self.binding), (self.fixture.registry,object(),self.binding),
                (self.fixture.registry,self.clock,object())):
            with self.subTest(argument_types=[type(value).__name__ for value in arguments]), self.assertRaises(ContractError):
                view.NativeOwnerView(*arguments)

    def test_native_fact_codec_preserves_full_luid_bits_and_rejects_invalid_input(self):
        self.assertEqual(view._luid_hex((0xFFFFFFFF,-1)), 'ffffffffffffffff')
        self.assertEqual(view._luid_hex((0,0)), '0000000000000000')
        for pair in ((True,0),(0,2**31),[0,0]):
            with self.subTest(pair=pair), self.assertRaises(ContractError): view._luid_hex(pair)
        for raw in (b'', bytes(12), bytearray(12)):
            with self.assertRaises(ContractError): view._sid_text(raw)


if __name__ == '__main__': unittest.main()
