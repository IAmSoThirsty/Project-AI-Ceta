"""Caller-visible ordinary/control custody on real disposable native workers."""
from pathlib import Path
import inspect
import os
import threading
import time
import unittest
from unittest.mock import patch

import preserve_ceta_complete as tool
import legacy_cache_validation as legacy
import test_legacy_cache_validation as original

HANDOFF_OBSERVATIONS=[]

class ExceptionHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):original.LegacyCacheTests.setUpClass()

    @classmethod
    def tearDownClass(cls):original.LegacyCacheTests.tearDownClass()

    def setUp(self):
        self.caller_case=original.LegacyCacheTests(methodName='test_accepted_proof_is_exact_finite_structural_basis')
        self.caller_case.setUp()

    def caller_error(self,error):
        self.caller_case.setUp()
        obj,entry=self.caller_case.synthetic_provenance()
        observed=None
        with patch.object(legacy,'verify',side_effect=error):
            try:obj.cache_constraints(entry,self.caller_case.cache,lambda _:self.caller_case.source)
            except BaseException as returned:observed=returned
        return observed

    def pending_wait(self,primary,*,concurrent=False,pending_retry=False):
        gate,entered=threading.Event(),threading.Event()
        actual_run,actual_start=threading.Thread.run,threading.Thread.start
        port=legacy._port(tool);actual_wait=port.wait
        senders,state,waits,callbacks,results,failures=[],{},[],[],[],[]
        observed=None
        def held_run(thread):
            if thread in senders:
                state['descriptor']=inspect.getclosurevars(thread._target).nonlocals['in_write']
                entered.set()
                if not gate.wait(30):raise AssertionError('owned pre-entry sender release missing')
            return actual_run(thread)
        def tracked_start(thread):
            if getattr(getattr(thread,'_target',None),'__name__','')=='send':
                senders.append(thread);actual_start(thread)
                self.assertTrue(entered.wait(3))
                return None
            return actual_start(thread)
        def first_wait(owned,seconds):
            waits.append(owned.pid)
            if len(waits)==1:raise primary
            done=actual_wait(owned,seconds)
            deadline=time.perf_counter()+2
            while done and owned.active_process_count() and time.perf_counter()<deadline:time.sleep(.005)
            return done
        try:
            with original.watch_native(self.id()) as launched:
                with patch.object(threading.Thread,'run',held_run),patch.object(threading.Thread,'start',tracked_start),patch.object(port,'wait',first_wait):
                    try:legacy._exchange(tool,b'{}')
                    except BaseException as error:observed=error
                sender=senders[0]
                self.assertTrue(sender.is_alive())
                if isinstance(primary,Exception) and not isinstance(primary,legacy.LegacyValidationError):
                    self.assertIsInstance(observed,legacy.LegacyValidationError)
                    self.assertEqual(observed.code,'LEGACY_NATIVE_OPERATION_FAILED')
                    self.assertIs(observed.primary_failure,primary)
                    self.assertIn(sender,primary.threads)
                    self.assertIs(primary.close_cleanup,observed.close_cleanup)
                else:self.assertIs(observed,primary)
                self.assertIn(sender,observed.threads)
                self.assertTrue(callable(observed.close_cleanup))
                self.assertTrue(all(slot.fenced and slot.retired for slot in observed.pipe_custody))
                self.assertFalse(tuple(observed.pipe_descriptors))
                self.assertIsNone(observed.owned_process)
                self.assertIsNone(observed.worker_lease)
                with self.assertRaises(OSError):os.fstat(state['descriptor'])
                self.assertIs(self.caller_error(observed),observed)
                pending=None
                if pending_retry:
                    pending=observed.close_cleanup()
                    self.assertIn(sender,pending['pending_threads'])
                    self.assertTrue(pending['future_pipe_IO_fenced'])
                    self.assertFalse(pending['pipe_descriptors'])
                    self.assertIsNone(pending['worker_lease'])
                gate.set();sender.join(5)
                self.assertFalse(sender.is_alive())
                def cleanup():
                    try:results.append(observed.close_cleanup())
                    except BaseException as error:failures.append(error)
                if concurrent:
                    callbacks=[threading.Thread(target=cleanup) for _ in range(4)]
                    for callback in callbacks:callback.start()
                    for callback in callbacks:callback.join(5)
                    self.assertTrue(all(not callback.is_alive() for callback in callbacks))
                else:cleanup()
                self.assertEqual(failures,[])
                self.assertEqual(len(results),4 if concurrent else 1)
                self.assertTrue(all(not row['pending_threads'] and not row['pipe_descriptors'] and row['owned_process'] is None and row['worker_lease'] is None for row in results))
                self.assertIn(sender,observed.threads)
                self.assertIs(self.caller_error(observed),observed)
                self.assertTrue(all(row['closed'] and row['active_processes_before_close']==0 and row['exit_status'] is not None for _,row in launched))
                HANDOFF_OBSERVATIONS.append({'test_id':self.id(),'original_failure_type':type(primary).__name__,
                    'exact_control_or_typed_identity':observed is primary,'ordinary_primary_failure_exact':getattr(observed,'primary_failure',None) is primary,
                    'pending_sender_handed_to_caller':True,'pending_cleanup_observed':pending is not None,
                    'settled_cleanup_calls':len(results),'cleanup_thread_ids':[callback.ident for callback in callbacks],
                    'all_cleanup_threads_joined':all(not callback.is_alive() for callback in callbacks),
                    'actual_sender_ident':sender.ident,'all_native_lifetimes':[dict(row) for _,row in launched],
                    'qualification':'Actual native empty-JSON exchange; injected first wait failure and pre-entry hold; synthetic caller seam'})
        finally:
            gate.set()
            for sender in senders:sender.join(5)
            for callback in callbacks:callback.join(5)
            if observed is not None and hasattr(observed,'close_cleanup'):observed.close_cleanup()

    def test_runtime_error_pending_retry_retains_typed_caller_handoff(self):
        self.pending_wait(RuntimeError('synthetic ordinary pending wait'),pending_retry=True)

    def test_oserror_four_concurrent_cleanups_retain_exact_wrapper(self):
        self.pending_wait(OSError('synthetic concurrent pending wait'),concurrent=True)

    def test_typed_legacy_pending_error_retains_same_object(self):
        self.pending_wait(legacy.LegacyValidationError('SYNTHETIC_NATIVE_WAIT_FAILURE'))

    def test_keyboard_interrupt_pending_handoff_preserves_identity(self):
        self.pending_wait(KeyboardInterrupt('synthetic pending control wait'))

    def test_system_exit_pending_handoff_preserves_identity(self):
        self.pending_wait(SystemExit(23))

    def test_settled_ordinary_failure_keeps_primary_and_safe_caller_conversion(self):
        port=legacy._port(tool);actual_wait=port.wait
        primary=OSError('synthetic fully settled wait failure');calls=[];observed=None
        def waited_then_failed(owned,seconds):
            calls.append(owned.pid)
            done=actual_wait(owned,seconds)
            deadline=time.perf_counter()+2
            while done and owned.active_process_count() and time.perf_counter()<deadline:time.sleep(.005)
            if len(calls)==1:
                self.assertTrue(done)
                raise primary
            return done
        with original.watch_native(self.id()) as launched:
            with patch.object(port,'wait',waited_then_failed):
                try:legacy._exchange(tool,b'{}')
                except BaseException as error:observed=error
            self.assertIsInstance(observed,legacy.LegacyValidationError)
            self.assertEqual(observed.code,'LEGACY_NATIVE_OPERATION_FAILED')
            self.assertIs(observed.primary_failure,primary)
            self.assertEqual(observed.threads,())
            self.assertFalse(observed.pipe_descriptors)
            self.assertIsNone(observed.owned_process)
            self.assertIsNone(observed.worker_lease)
            self.assertFalse(hasattr(observed,'close_cleanup'))
            caller=self.caller_error(observed)
            self.assertIsInstance(caller,tool.PreservationError)
            self.assertIsNot(caller,observed)
            self.assertTrue(all(row['closed'] and row['active_processes_before_close']==0 and row['exit_status'] is not None for _,row in launched))
            HANDOFF_OBSERVATIONS.append({'test_id':self.id(),'all_native_lifetimes':[dict(row) for _,row in launched],
                'ordinary_primary_failure_exact':True,'no_pending_owner_exported':True,'safe_caller_conversion':True})

    def test_entered_sender_ordinary_cleanup_failure_retains_fd_lease_and_primary(self):
        gate,entered=threading.Event(),threading.Event()
        actual_start,actual_write=threading.Thread.start,os.write
        port=legacy._port(tool);actual_wait=port.wait
        primary=OSError('synthetic entered-sender wait failure')
        senders,state,waits=[],{},[];observed=None
        def held_write(descriptor,data):
            if threading.current_thread() in senders:
                state['descriptor']=descriptor;entered.set()
                if not gate.wait(20):raise AssertionError('owned entered sender release missing')
            return actual_write(descriptor,data)
        def tracked_start(thread):
            if getattr(getattr(thread,'_target',None),'__name__','')=='send':
                senders.append(thread);actual_start(thread)
                self.assertTrue(entered.wait(3));return None
            return actual_start(thread)
        def first_wait(owned,seconds):
            waits.append(owned.pid)
            if len(waits)==1:raise primary
            done=actual_wait(owned,seconds)
            deadline=time.perf_counter()+2
            while done and owned.active_process_count() and time.perf_counter()<deadline:time.sleep(.005)
            return done
        try:
            with original.watch_native(self.id()) as launched:
                with patch.object(threading.Thread,'start',tracked_start),patch.object(os,'write',held_write),patch.object(port,'wait',first_wait):
                    try:legacy._exchange(tool,b'{}')
                    except BaseException as error:observed=error
                self.assertIsInstance(observed,legacy.LegacyValidationError)
                self.assertEqual(observed.code,'LEGACY_PIPE_CUSTODY_UNRESOLVED')
                self.assertIs(observed.primary_failure,primary)
                self.assertIsInstance(observed.cleanup_failure,legacy.LegacyValidationError)
                self.assertIn(senders[0],observed.threads)
                self.assertTrue(senders[0].is_alive())
                descriptor=state['descriptor'];os.fstat(descriptor)
                self.assertIn(descriptor,tuple(observed.pipe_descriptors))
                self.assertIsNotNone(observed.worker_lease)
                self.assertIs(self.caller_error(observed),observed)
                gate.set();senders[0].join(5)
                self.assertFalse(senders[0].is_alive())
                self.assertNotIn(descriptor,tuple(observed.pipe_descriptors))
                result=observed.close_cleanup()
                self.assertFalse(result['pending_threads'] or result['pipe_descriptors'])
                self.assertIsNone(observed.worker_lease)
                self.assertIsNone(observed.owned_process)
                with self.assertRaises(OSError):os.fstat(descriptor)
                self.assertTrue(all(row['closed'] and row['active_processes_before_close']==0 and row['exit_status'] is not None for _,row in launched))
                HANDOFF_OBSERVATIONS.append({'test_id':self.id(),'all_native_lifetimes':[dict(row) for _,row in launched],
                    'ordinary_primary_failure_exact':True,'entered_sender_descriptor_and_worker_lease_retained':True,
                    'caller_retains_exact_cleanup_error':True,'after_join_all_owned_IO_recovered':True,'actual_sender_ident':senders[0].ident})
        finally:
            gate.set()
            for sender in senders:sender.join(5)
            if observed is not None and hasattr(observed,'close_cleanup'):observed.close_cleanup()
