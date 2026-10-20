"""Actual native worker and pipe recovery; synthetic empty JSON requests only."""
from pathlib import Path
import hashlib
import inspect
import json
import os
import threading
import time
import unittest
from unittest.mock import patch
import uuid

import preserve_ceta_complete as tool
import legacy_cache_validation as legacy
from test_legacy_cache_validation import watch_native

Q = Path(__file__).resolve().parent
R = Q.parent / 'runtime' / Q.name
FIXTURES = R / 'native-review-fixtures'
RECOVERY_OBSERVATIONS = []

class NativeTransportRecoveryTests(unittest.TestCase):
    def active_sender(self, primary, concurrent=False):
        gate, entered = threading.Event(), threading.Event()
        actual_start, actual_write = threading.Thread.start, os.write
        senders, failures, state = [], [], {}
        def held_write(descriptor, data):
            if threading.current_thread() in senders:
                state['descriptor'] = descriptor
                entered.set()
                if not gate.wait(15): raise AssertionError('owned active sender release missing')
            return actual_write(descriptor, data)
        def start_then_interrupt(thread):
            if getattr(getattr(thread, '_target', None), '__name__', '') == 'send':
                senders.append(thread)
                actual_start(thread)
                self.assertTrue(entered.wait(3))
                raise primary
            return actual_start(thread)
        try:
            with watch_native(self.id()) as launched:
                with patch.object(threading.Thread, 'start', start_then_interrupt), patch.object(os, 'write', held_write):
                    observed = None
                    try: legacy._exchange(tool, b'{}')
                    except BaseException as error: observed = error
                    self.assertIs(observed, primary)
                    self.assertTrue(senders[0].is_alive())
                    self.assertTrue(any(slot.entered and not slot.retired for slot in observed.pipe_custody))
                    descriptor = state['descriptor']
                    os.fstat(descriptor)
                    self.assertIn(descriptor, tuple(observed.pipe_descriptors))
                    self.assertIsNotNone(observed.worker_lease)
                    self.assertTrue(callable(observed.close_cleanup))
                    gate.set()
                    senders[0].join(5)
                    self.assertFalse(senders[0].is_alive())
                    self.assertNotIn(descriptor, tuple(observed.pipe_descriptors))
                results = []
                def recover():
                    try: results.append(observed.close_cleanup())
                    except BaseException as error: failures.append(error)
                if concurrent:
                    threads = [threading.Thread(target=recover) for _ in range(4)]
                    for thread in threads: thread.start()
                    for thread in threads: thread.join(5)
                    self.assertFalse(any(thread.is_alive() for thread in threads))
                else: recover()
                self.assertEqual(failures, [])
                self.assertTrue(results)
                self.assertTrue(all(not row['pending_threads'] and not row['pipe_descriptors'] for row in results))
                self.assertIsNone(observed.worker_lease)
                self.assertIsNone(observed.owned_process)
                with self.assertRaises(OSError): os.fstat(descriptor)
                self.assertTrue(all(row['closed'] and row['active_processes_before_close'] == 0 for _, row in launched))
                RECOVERY_OBSERVATIONS.append({'case': type(primary).__name__, 'actual_entered_sender': True,
                    'descriptor_retained_while_active': True, 'dynamic_descriptor_retired_after_join': True,
                    'primary_identity_preserved': True, 'cleanup_calls': len(results),
                    'native_lifetimes': [dict(row) for _, row in launched], 'all_owned_IO_recovered': True})
        finally:
            gate.set()
            for sender in senders: sender.join(5)
            if observed is not None and hasattr(observed, 'close_cleanup'): observed.close_cleanup()

    def test_active_sender_keyboard_interrupt_preserves_fd_and_file_lease(self):
        self.active_sender(KeyboardInterrupt('synthetic active sender interruption'))

    def test_active_sender_system_exit_concurrent_cleanup_is_exact_once(self):
        self.active_sender(SystemExit(23), concurrent=True)

    def test_ident_none_delayed_native_start_cannot_touch_reused_descriptor(self):
        gate, queued = threading.Event(), threading.Event()
        actual_start = threading.Thread.start
        state, helpers, opened = {}, [], []
        primary = KeyboardInterrupt('synthetic delayed actual start')
        area = FIXTURES / ('delayed-start-' + uuid.uuid4().hex)
        area.mkdir()
        def delayed_start(thread):
            if getattr(getattr(thread, '_target', None), '__name__', '') != 'send': return actual_start(thread)
            state['sender'] = thread
            state['descriptor'] = inspect.getclosurevars(thread._target).nonlocals['in_write']
            def later():
                queued.set()
                if not gate.wait(15): raise AssertionError('delayed startup release missing')
                actual_start(thread)
            helper = threading.Thread(target=later)
            helpers.append(helper)
            actual_start(helper)
            self.assertTrue(queued.wait(3))
            self.assertIsNone(thread.ident)
            raise primary
        observed = None
        try:
            with watch_native(self.id()) as launched:
                with patch.object(threading.Thread, 'start', delayed_start):
                    try: legacy._exchange(tool, b'{}')
                    except BaseException as error: observed = error
                self.assertIs(observed, primary)
                self.assertIn(state['sender'], observed.threads)
                self.assertIn(state['sender'], observed.thread_start_ambiguity)
                descriptor = state['descriptor']
                self.assertTrue(all(slot.fenced for slot in observed.pipe_custody))
                self.assertFalse(tuple(observed.pipe_descriptors))
                for number in range(30):
                    path = area / (str(number) + '.synthetic')
                    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    opened.append((fd, path))
                    if fd == descriptor:
                        state['reused'] = path
                        break
                self.assertIn('reused', state)
                gate.set()
                for helper in helpers: helper.join(5)
                state['sender'].join(5)
                self.assertFalse(state['sender'].is_alive())
                self.assertEqual(state['reused'].read_bytes(), b'')
                os.fstat(descriptor)  # A cancelled target must not close the new file either.
                result = observed.close_cleanup()
                self.assertFalse(result['pending_threads'] or result['pipe_descriptors'])
                self.assertTrue(all(row['closed'] and row['active_processes_before_close'] == 0 for _, row in launched))
                RECOVERY_OBSERVATIONS.append({'case': 'ident-none-delayed-native-start', 'real_start_after_parent_exception': True,
                    'entry_fenced_before_descriptor_retirement': True, 'own_descriptor_reuse': True,
                    'late_write': False, 'late_close': False, 'native_lifetimes': [dict(row) for _, row in launched]})
        finally:
            gate.set()
            for helper in helpers: helper.join(5)
            if 'sender' in state and state['sender'].ident is not None: state['sender'].join(5)
            if observed is not None and hasattr(observed, 'close_cleanup'): observed.close_cleanup()
            for fd, path in opened: os.close(fd)

    def test_each_receive_start_interrupt_fences_the_exact_pipe(self):
        for label in ('stdout', 'stderr'):
            with self.subTest(label=label):
                gate, entered = threading.Event(), threading.Event()
                actual_start, actual_run = threading.Thread.start, threading.Thread.run
                selected = []
                primary = SystemExit(29)
                def held_run(thread):
                    if thread in selected:
                        entered.set()
                        if not gate.wait(15): raise AssertionError('owned receive release missing')
                    return actual_run(thread)
                def interrupted(thread):
                    if getattr(getattr(thread, '_target', None), '__name__', '') == 'receive' and thread._args[0] == label:
                        selected.append(thread)
                        actual_start(thread)
                        self.assertTrue(entered.wait(3))
                        raise primary
                    return actual_start(thread)
                observed = None
                try:
                    with watch_native(self.id()) as launched:
                        with patch.object(threading.Thread, 'run', held_run), patch.object(threading.Thread, 'start', interrupted):
                            try: legacy._exchange(tool, b'{}')
                            except BaseException as error: observed = error
                            self.assertIs(observed, primary)
                            self.assertIn(selected[0], observed.threads)
                            self.assertTrue(all(slot.fenced for slot in observed.pipe_custody))
                            gate.set()
                            selected[0].join(5)
                        result = observed.close_cleanup()
                        self.assertFalse(result['pending_threads'] or result['pipe_descriptors'])
                        self.assertTrue(all(row['closed'] and row['active_processes_before_close'] == 0 for _, row in launched))
                        RECOVERY_OBSERVATIONS.append({'case': 'receive-' + label, 'primary_identity_preserved': True,
                            'native_lifetimes': [dict(row) for _, row in launched], 'all_owned_IO_recovered': True})
                finally:
                    gate.set()
                    for thread in selected: thread.join(5)
                    if observed is not None and hasattr(observed, 'close_cleanup'): observed.close_cleanup()


class DeclaredNativeFailureBoundaryTests(unittest.TestCase):
    """Explicit synthetic canonical-owner contract; no worker is launched."""
    def test_partial_native_failure_keeps_original_owner_and_delegates_cleanup(self):
        port = legacy._port(tool)
        from ceta.supervisor.windows_jobs import WindowsLaunchError
        class DeclaredOwner:
            ready = closed = False
            calls = 0
            def close(self):
                self.calls += 1
                if not self.ready: raise OSError('synthetic retained native close')
                self.closed = True
        owner = DeclaredOwner()
        native_failure = WindowsLaunchError('WINDOWS_LAUNCH_CLEANUP_UNRESOLVED', owner)
        observed = None
        try:
            with patch.object(port, 'launch', side_effect=native_failure):
                with self.assertRaises(legacy.LegacyValidationError) as caught:
                    legacy._exchange(tool, b'{}')
                observed = caught.exception
            self.assertEqual(observed.code, 'LEGACY_NATIVE_CUSTODY_UNRESOLVED')
            self.assertIs(observed.owned_process, owner)
            self.assertIs(observed.native_failure, native_failure)
            self.assertIsNotNone(observed.worker_lease)
            self.assertTrue(tuple(observed.pipe_descriptors))
            owner.ready = True
            result = observed.close_cleanup()
            self.assertTrue(owner.closed)
            self.assertEqual(owner.calls, 2)
            self.assertFalse(result['pipe_descriptors'] or result['pending_threads'])
            self.assertIsNone(observed.owned_process)
            self.assertIsNone(observed.native_failure)
            self.assertIsNone(observed.worker_lease)
        finally:
            owner.ready = True
            native_failure.close_cleanup()
            if observed is not None and hasattr(observed, 'close_cleanup'): observed.close_cleanup()
