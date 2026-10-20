"""Unchanged HP9 oracle; reused class/method count as zero new authored LOC."""
from pathlib import Path
import hashlib,inspect,os,threading,time,unittest,uuid
from unittest.mock import patch
import preserve_ceta_complete as tool
import legacy_cache_validation as legacy
import test_legacy_cache_validation as original
Q=Path(__file__).resolve().parent
R=Q.parent/'runtime'/Q.name
FIXTURES=R/'native-review-fixtures'/('ordinary-oracle-'+uuid.uuid4().hex)
FIXTURES.mkdir()
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
FACTS=[]

class OrdinaryPendingCustodyTests(unittest.TestCase):
    def test_oserror_with_fenced_pending_sender_preserves_returned_typed_and_caller_custody(self):
        gate,entered=threading.Event(),threading.Event()
        actual_start,actual_run=threading.Thread.start,threading.Thread.run
        port=legacy._port(tool)
        actual_wait=port.wait
        primary=OSError('synthetic first native wait failure')
        waits=[];senders=[];state={};opened=[];observed=None;caller_error=None;fact={}
        fixture_case=original.LegacyCacheTests(methodName='test_accepted_proof_is_exact_finite_structural_basis')
        original.LegacyCacheTests.setUpClass()
        fixture_case.setUp()
        def held_run(thread):
            if thread in senders:
                state['descriptor']=inspect.getclosurevars(thread._target).nonlocals['in_write']
                entered.set()
                if not gate.wait(20):raise AssertionError('owned sender release missing')
            return actual_run(thread)
        def tracked_start(thread):
            if getattr(getattr(thread,'_target',None),'__name__','')=='send':
                senders.append(thread);actual_start(thread)
                self.assertTrue(entered.wait(3))
                return None
            return actual_start(thread)
        def first_wait_failed(owned,seconds):
            waits.append(owned.pid)
            if len(waits)==1:raise primary
            result=actual_wait(owned,seconds)
            deadline=time.perf_counter()+2
            while result and owned.active_process_count() and time.perf_counter()<deadline:time.sleep(.005)
            return result
        try:
            with original.watch_native(self.id()) as launched:
                with patch.object(threading.Thread,'run',held_run),patch.object(threading.Thread,'start',tracked_start),patch.object(port,'wait',first_wait_failed):
                    try:legacy._exchange(tool,b'{}')
                    except BaseException as error:observed=error
                self.assertIsInstance(observed,legacy.LegacyValidationError)
                self.assertEqual(observed.code,'LEGACY_NATIVE_OPERATION_FAILED')
                self.assertIs(observed.primary_failure,primary)
                sender=senders[0];descriptor=state['descriptor']
                fact={'request_kind':'SYNTHETIC_EMPTY_JSON_ONLY','actual_native_wait_called_after_injected_first_fault':len(waits)>1,
                    'returned_type':type(observed).__name__,'returned_code':observed.code,
                    'returned_threads_count':len(observed.threads),'returned_has_cleanup':hasattr(observed,'close_cleanup'),
                    'primary_error_threads_count':len(getattr(primary,'threads',())),
                    'primary_error_has_cleanup':hasattr(primary,'close_cleanup'),
                    'sender_alive_at_return':sender.is_alive(),'sender_registered_on_returned_error':sender in observed.threads,
                    'sender_registered_on_primary_error':sender in getattr(primary,'threads',()),
                    'sender_ident':sender.ident,'descriptor':descriptor,
                    'entry_fenced':all(slot.fenced for slot in getattr(primary,'pipe_custody',())),
                    'returned_worker_lease':observed.worker_lease is not None,
                    'primary_worker_lease':getattr(primary,'worker_lease',None) is not None,
                    'native_lifetimes_at_return':[dict(row) for _,row in launched]}
                with self.assertRaises(OSError):os.fstat(descriptor)
                # Reuse only our own retired FD to prove entry fencing holds even
                # while the unresolved thread is omitted from the typed wrapper.
                for number in range(30):
                    path=FIXTURES/('reused-'+str(number)+'.synthetic')
                    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);opened.append((fd,path))
                    if fd==descriptor:state['reused']=path;break
                self.assertIn('reused',state)
                fact['reused_own_file_before']={'path':str(state['reused']),'bytes':state['reused'].stat().st_size,'sha256':sha(state['reused']),
                    'native_identity':tool.file_identity(os.fstat(descriptor))}
                obj,entry=fixture_case.synthetic_provenance()
                with patch.object(legacy,'verify',side_effect=observed):
                    try:obj.cache_constraints(entry,fixture_case.cache,lambda _:fixture_case.source)
                    except BaseException as error:caller_error=error
                fact.update(caller_return_type=type(caller_error).__name__,caller_retains_exact_typed_error=caller_error is observed,
                            caller_has_owned_threads=bool(getattr(caller_error,'threads',())),
                            caller_has_cleanup=hasattr(caller_error,'close_cleanup'))
                gate.set();sender.join(5)
                self.assertFalse(sender.is_alive())
                self.assertEqual(state['reused'].read_bytes(),b'')
                os.fstat(descriptor)
                fact['reused_own_file_after']={'bytes':state['reused'].stat().st_size,'sha256':sha(state['reused']),
                    'native_identity':tool.file_identity(os.fstat(descriptor))}
                recovery=primary.close_cleanup() if hasattr(primary,'close_cleanup') else None
                self.assertIsNotNone(recovery)
                self.assertFalse(recovery['pending_threads'] or recovery['pipe_descriptors'])
                self.assertTrue(all(row['closed'] and row['active_processes_before_close']==0 and row['exit_status'] is not None for _,row in launched))
                fact.update(no_late_write=True,no_late_close=True,all_owned_thread_process_lease_recovered=True,
                            native_lifetimes_after_recovery=[dict(row) for _,row in launched])
                # These are custody assertions, not a claim of unsafe late IO.
                self.assertIn(sender,observed.threads,'Returned typed error omitted a real pending sender; custody exists only on its original OSError')
                self.assertTrue(callable(observed.close_cleanup))
                self.assertIs(caller_error,observed)
        finally:
            gate.set()
            for thread in senders:thread.join(5)
            if hasattr(primary,'close_cleanup'):primary.close_cleanup()
            for fd,path in opened:os.close(fd)
            original.LegacyCacheTests.tearDownClass()
            fact['all_owned_senders_joined_after_recovery']=all(not thread.is_alive() for thread in senders)
            FACTS.append(fact)
