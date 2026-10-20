"""Actual disposable Windows observation; requests are controlled engineering data.

Build receipts supply the two fixed native fixture paths. These tests perform
no CETA owner ceremony, canonical authorization, profile creation or publication.
"""
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
import ctypes as C
import hashlib
import os
import struct
import threading
import time
import unittest
import uuid

import ceta.effects.native_observer as observe_module
import ceta.supervisor.windows_jobs as native
from ceta.contracts.kernel_transactions import BUDGET_FIELDS, BudgetVector
from ceta.contracts.real_effect import OwnedCpuRequest, CAP_OPERATION, RESTORE_OPERATION, compare_cpu_observation
from ceta.contracts.resource_management import ObservationState
from ceta.contracts.temporal import Deadline
from ceta.contracts.workload_throttling import CpuRateLimit
from ceta.contracts.wire import ContractError
from ceta.identity.native_clock import NativeSessionClock
from ceta.supervisor.service import controlled_environment

ROOT=Path(__file__).resolve().parents[2]
NATIVE_RECEIPTS=[]
SOURCE_PIN_RECEIPTS=[]
HASH='sha256:'+'a'*64
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()


class SourceHashCustodyTests(unittest.TestCase):
    """Real read-only source pins with explicitly controlled failure responses."""
    def setUp(self):
        self.api=observe_module._API();self.real_close=self.api.close
        self.real_open=observe_module._open_image;self.real_duplicate=self.api.DuplicateHandle
        self.handles=[];self.guards=[];self.events=[];self.owners=[];self.controls=[]
        self.before=sha(Path(observe_module.__file__))
        def opened(*args):
            handle=self.real_open(*args);self.handles.append(handle);return handle
        def duplicated(*args):
            result=self.real_duplicate(*args)
            if result:self.guards.append(C.cast(args[3],C.POINTER(native.HANDLE)).contents.value)
            return result
        self.patches=[patch.object(observe_module,'_API',return_value=self.api),
            patch.object(observe_module,'_open_image',side_effect=opened),
            patch.object(self.api,'DuplicateHandle',side_effect=duplicated)]
        for item in self.patches:item.start()

    def owner(self,error):
        result=BaseException.__dict__['__dict__'].__get__(error)['source_hash_custody']
        self.owners.append(result);return result

    def event(self):
        create=self.api.dll.CreateEventW
        create.argtypes,create.restype=[C.c_void_p,C.c_int32,C.c_int32,C.c_wchar_p],native.HANDLE
        handle=create(None,True,False,None);self.assertTrue(handle);self.events.append(handle);return handle

    def tearDown(self):
        for item in reversed(self.patches):item.stop()
        for owner in self.owners:
            try:owner.close()
            except ContractError:pass  # Controlled uncertain effects stay explicit in product state.
        pending=[owner.pending_native_resources() for owner in self.owners]
        # The fixture knows which actual native allocation/close operations ran.
        # This does not convert the product's UNCERTAIN records into success.
        for handle in set(self.handles+self.guards):
            if handle not in self.events and self.api.GetHandleInformation(handle,C.byref(native.DWORD())):
                self.real_close(handle)
        for handle in self.events:
            if self.api.GetHandleInformation(handle,C.byref(native.DWORD())):self.real_close(handle)
        all_closed=all(not self.api.GetHandleInformation(handle,C.byref(native.DWORD()))
            for handle in set(self.handles+self.guards+self.events))
        self.assertTrue(all_closed);self.assertEqual(self.before,sha(Path(observe_module.__file__)))
        SOURCE_PIN_RECEIPTS.append({'test_id':self.id(),'read_only_source_handles':self.handles,
            'duplicate_guard_handles':self.guards,'replacement_events':self.events,'controls':self.controls,
            'product_owner_ids':[id(owner) for owner in self.owners],
            'product_custody_before_fixture_retirement':pending,'all_exact_fixture_native_slots_closed':all_closed,
            'source_bytes_before_after_exact':True})

    def test_actual_source_hash_returns_only_after_both_native_pins_close(self):
        self.assertEqual(observe_module._source_hash(),self.before)
        self.assertEqual(len(self.handles),1);self.assertEqual(len(self.guards),1)
        self.assertFalse(self.api.GetHandleInformation(self.handles[0],C.byref(native.DWORD())))
        self.assertFalse(self.api.GetHandleInformation(self.guards[0],C.byref(native.DWORD())))

    def test_primary_truth_and_note_hooks_cannot_replace_native_custody(self):
        class Hostile(KeyboardInterrupt):
            def __bool__(self):raise AssertionError('EXCEPTION_TRUTH_MUST_NOT_RUN')
            def __setattr__(self,name,value):raise OSError('CONTROLLED_ATTRIBUTE_DIAGNOSTIC_FAILURE')
            def add_note(self,*args):raise OSError('CONTROLLED_NOTE_FAILURE')
        primary=Hostile('CONTROLLED_HASH_PRIMARY');cleanup=OSError('CONTROLLED_CLOSE_REFUSAL')
        with patch.object(observe_module,'_hash_image',side_effect=primary),patch.object(self.api,'close',side_effect=cleanup):
            with self.assertRaises(Hostile) as caught:observe_module._source_hash()
        self.assertIs(caught.exception,primary);owner=self.owner(primary)
        self.assertTrue(owner.pending_native_resources());self.assertFalse(owner.closed)
        owner.close();self.assertTrue(owner.closed)

    def test_hash_success_and_close_refusal_return_exact_recoverable_error(self):
        primary=OSError('CONTROLLED_CLOSE_AFTER_HASH_REFUSED')
        with patch.object(self.api,'close',side_effect=primary):
            with self.assertRaises(OSError) as caught:observe_module._source_hash()
        self.assertIs(caught.exception,primary);owner=self.owner(primary)
        owner.close();self.assertTrue(owner.closed)

    def test_close_then_response_loss_preserves_replacement_native_event(self):
        primary=KeyboardInterrupt('CONTROLLED_HASH_PRIMARY');cleanup=OSError('CONTROLLED_SOURCE_CLOSE_RESPONSE_LOSS')
        hit=[]
        def close_then_raise(handle):
            if self.handles and handle==self.handles[0] and not hit:
                hit.append(handle);self.real_close(handle);event=self.event()
                self.controls.append({'actual_source_close_succeeded':True,'original_handle':handle,
                    'replacement_event':event,'numeric_slot_reused':event==handle})
                raise cleanup
            self.real_close(handle)
        with patch.object(observe_module,'_hash_image',side_effect=primary),patch.object(self.api,'close',side_effect=close_then_raise):
            with self.assertRaises(KeyboardInterrupt) as caught:observe_module._source_hash()
        self.assertIs(caught.exception,primary);owner=self.owner(primary)
        self.assertIsNone(owner.handle);owner.close();self.assertTrue(owner.closed)
        self.assertTrue(self.api.GetHandleInformation(self.events[0],C.byref(native.DWORD())))

    def test_guard_close_response_loss_is_uncertain_and_never_replayed(self):
        primary=OSError('CONTROLLED_GUARD_CLOSE_RESPONSE_LOSS');hit=[]
        def close_then_raise(handle):
            self.real_close(handle)
            if self.guards and handle==self.guards[0] and not hit:
                hit.append(handle);self.event();raise primary
        with patch.object(self.api,'close',side_effect=close_then_raise):
            with self.assertRaises(OSError) as caught:observe_module._source_hash()
        self.assertIs(caught.exception,primary);owner=self.owner(primary)
        self.assertEqual(owner.guard_state,'UNCERTAIN')
        with self.assertRaisesRegex(ContractError,'OBSERVER_SOURCE_GUARD_CLOSE_UNCERTAIN'):owner.close()
        self.assertTrue(self.api.GetHandleInformation(self.events[0],C.byref(native.DWORD())))
        self.controls.append({'actual_guard_close_succeeded':True,'response_lost':True,'product_uncertainty_retained':True})

    def test_duplicate_response_loss_keeps_output_slot_and_refuses_blind_retry(self):
        primary=KeyboardInterrupt('CONTROLLED_GUARD_DUPLICATE_RESPONSE_LOSS')
        def duplicate_then_raise(*args):
            result=self.real_duplicate(*args);self.assertTrue(result)
            self.guards.append(C.cast(args[3],C.POINTER(native.HANDLE)).contents.value)
            raise primary
        with patch.object(self.api,'DuplicateHandle',side_effect=duplicate_then_raise):
            with self.assertRaises(KeyboardInterrupt) as caught:observe_module._source_hash()
        self.assertIs(caught.exception,primary);owner=self.owner(primary)
        self.assertTrue(owner.handle);self.assertEqual(owner.guard_state,'UNCERTAIN')
        with self.assertRaisesRegex(ContractError,'OBSERVER_SOURCE_GUARD_ALLOCATION_UNCERTAIN'):owner.close()
        self.controls.append({'actual_duplicate_succeeded':True,'response_lost':True,'product_uncertainty_retained':True})

@unittest.skipUnless(os.name=='nt' and struct.calcsize('P')==8,'actual Windows x64 required')
class NativeEffectObserverTests(unittest.TestCase):
    def setUp(self):
        self.directory=ROOT/'.agents/fixtures'/('ob1-'+uuid.uuid4().hex)
        self.directory.mkdir(parents=True,exist_ok=False)
        self.worker=Path(os.environ['CETA_OWNED_WORKER_EXE']).resolve(strict=True)
        self.binary=Path(os.environ['CETA_EFFECT_OBSERVER_EXE']).resolve(strict=True)
        self.targets=[];self.observers=[];self.leases=[];self.clock=None
        self.receipt={'test_id':self.id(),'fixture':str(self.directory),'observations':[],'controls':[]}
        self.addCleanup(self.settle)
        self.clock=NativeSessionClock(1)
        self.target=self.new_target()

    def new_target(self):
        result=native.WindowsOwnedProcess.launch(str(self.worker),('hold','30000'),cwd=str(self.directory),
            environment=controlled_environment(self.directory),expected_image_sha256=sha(self.worker))
        self.targets.append(result)
        return result

    def observer(self):
        image=sha(self.binary)
        code=observe_module.observer_code_commitment(image,sha(Path(observe_module.__file__)))
        result=observe_module.NativeCpuEffectObserver(str(self.binary),image,code,clock=self.clock)
        self.observers.append(result)
        return result,code

    def request(self,code,target=None):
        target=target or self.target
        _,sample=self.clock.clock()
        prior=target.cpu_rate_observation(target.resource_identity,maximum_duration_ns=1_000_000_000)
        self.assertIs(prior.state,ObservationState.MEASURED)
        budget=BudgetVector.from_dict({name:1000 if name=='wall_time_ms' else 1 if name=='max_effects'
            else 8192 if name=='max_bytes_written' else 0 for name in BUDGET_FIELDS})
        return OwnedCpuRequest('controlled:effect','scope:ob1','task:ob1','proposal:ob1','principal:controlled',
            'session:controlled','nonce:controlled',CAP_OPERATION,target.resource_identity,prior.job_digest,
            prior,CpuRateLimit.hard_cap(100),prior.limit,HASH,HASH,HASH,HASH,HASH,code,budget,8192,
            Deadline(sample.boot_id,sample.durable_epoch,sample.resume_generation,sample.monotonic_ns,
                sample.monotonic_ns+30_000_000_000,sample.earliest_wall_ns,sample.latest_wall_ns+30_000_000_000),
            2_000_000_000,1_000_000_000,('controlled:observe','cleanup:owned'))

    def set_policy(self,flags,value):
        policy=native.CPU_RATE_CONTROL(flags,value)
        self.assertTrue(self.target._api.SetInformationJobObject(self.target._job,15,C.byref(policy),C.sizeof(policy)))
        self.receipt['controls'].append({'actual_fixture_Set_class15':(flags,value),'canonical_authority':False})

    def call(self,observer,item,**kwargs):
        try:return observer.observe(item,self.target,**kwargs)
        finally:
            if observer.last_evidence is not None:self.receipt['observations'].append(observer.last_evidence)

    def settle(self):
        failures=[]
        for observer in self.observers:
            try:observer.close_cleanup()
            except BaseException as error:failures.append(repr(error))
        for lease in self.leases:
            try:lease.close()
            except BaseException as error:failures.append(repr(error))
        for target in self.targets:
            try:
                if not target.lifetime_closed:
                    if target.poll() is None:target.terminate(125)
                    self.assertTrue(target.wait(3))
                    end=time.monotonic()+3
                    while target.active_process_count()!=0:
                        self.assertLess(time.monotonic(),end);time.sleep(.001)
                    target.close()
            except BaseException as error:failures.append(repr(error))
        if self.clock is not None:
            try:self.clock.close()
            except BaseException as error:failures.append(repr(error))
        self.receipt['closed_targets']=[{'pid':target.pid,'creation_time':target.creation_time,
            'lifetime_closed':target.lifetime_closed,'remaining_query_exports':len(target._cpu_query_exports)} for target in self.targets]
        self.receipt['clock_closed']=self.clock is None or self.clock.status().state=='CLOSED'
        self.receipt['cleanup_failures']=failures
        NATIVE_RECEIPTS.append(self.receipt)
        self.assertFalse(failures,failures)

    def mutate_response(self,observer,field,value):
        original=observer._exchange
        def changed(*args,**kwargs):
            raw,stderr,code=original(*args,**kwargs)
            parts=list(observe_module.RESPONSE.unpack(raw));parts[field]=value(parts[field])
            return observe_module.RESPONSE.pack(*parts),stderr,code
        return patch.object(observer,'_exchange',changed)

    def test_actual_disabled_zero_is_measured_by_distinct_owned_native_process(self):
        observer,code=self.observer();item=self.request(code)
        value=self.call(observer,item)
        self.assertIs(value.state,ObservationState.MEASURED)
        self.assertEqual(value.limit,CpuRateLimit(0,0))
        self.assertNotEqual(value.identity.pid,value.observer_identity.pid)
        self.assertEqual(value.method,'windows:QueryInformationJobObject:15')
        self.assertTrue(observer.last_evidence['cleanup']['closed'])

    def test_actual_cap_and_separate_exact_restoration_are_independently_observed(self):
        observer,code=self.observer();item=self.request(code)
        self.set_policy(5,100)
        capped=self.call(observer,item)
        evidence=observer.last_evidence
        self.assertEqual(compare_cpu_observation(item,capped,evidence['parent_clock_before'],evidence['parent_clock_after'],minimum_sequence=1),'VERIFIED_MATCH')
        expected=self.target.cpu_rate_observation(item.process_identity,maximum_duration_ns=1_000_000_000)
        restore=replace(item,request_id='controlled:restore',operation=RESTORE_OPERATION,
            expected_limit=expected,target_limit=item.original_limit,restoration_of=item.request_id,
            original_request_commitment=item.input_commitment)
        self.set_policy(0,0)
        restored=self.call(observer,restore)
        self.assertEqual(restored.limit,item.original_limit)
        self.assertGreater(restored.sequence,capped.sequence)

    def test_query_handles_deny_actual_Set_and_process_terminate(self):
        lease=self.target.export_cpu_query_handles(self.target.resource_identity);self.leases.append(lease)
        process,job=lease.inherited_handles
        policy=native.CPU_RATE_CONTROL(5,100)
        C.set_last_error(0)
        self.assertFalse(self.target._api.SetInformationJobObject(job,15,C.byref(policy),8))
        set_error=C.get_last_error();self.assertEqual(set_error,5)
        terminate=self.target._api.dll.TerminateProcess
        terminate.argtypes,terminate.restype=[native.HANDLE,native.DWORD],C.c_int32
        C.set_last_error(0);self.assertFalse(terminate(process,17));terminate_error=C.get_last_error()
        self.assertEqual(terminate_error,5)
        self.assertIsNone(self.target.poll())
        self.receipt['controls'].append({'query_process_handle':process,'query_job_handle':job,
            'Set_return':False,'Set_last_error':set_error,'Terminate_return':False,'Terminate_last_error':terminate_error,
            'process_rights':lease.PROCESS_RIGHTS,'job_rights':lease.JOB_RIGHTS})

    def test_target_close_is_fenced_until_query_lease_retires(self):
        lease=self.target.export_cpu_query_handles(self.target.resource_identity);self.leases.append(lease)
        self.target.terminate(125);self.assertTrue(self.target.wait(2))
        with self.assertRaisesRegex(ContractError,'WINDOWS_CPU_OBSERVER_CUSTODY_UNRESOLVED'):self.target.close()
        lease.close();self.target.close();self.assertTrue(self.target.lifetime_closed)

    def test_wrong_target_object_is_rejected(self):
        observer,code=self.observer();item=self.request(code);other=self.new_target()
        with self.assertRaisesRegex(ContractError,'OBSERVER_TARGET_IDENTITY_MISMATCH'):observer.observe(item,other)

    def test_wrong_native_target_lifetime_is_unavailable(self):
        observer,code=self.observer();item=self.request(code);original=observer._exchange
        def changed(custody,frame,*args):
            parts=list(observe_module.REQUEST.unpack(frame));parts[10]+=1
            return original(custody,observe_module.REQUEST.pack(*parts),*args)
        with patch.object(observer,'_exchange',changed):value=self.call(observer,item)
        self.assertIs(value.state,ObservationState.UNAVAILABLE);self.assertIsNone(value.limit)

    def test_wrong_observer_process_identity_is_rejected(self):
        observer,code=self.observer();item=self.request(code)
        with self.mutate_response(observer,7,lambda value:value+1),self.assertRaisesRegex(ContractError,'OBSERVER_PROCESS_IDENTITY_MISMATCH'):
            self.call(observer,item)

    def test_wrong_sequence_and_nonce_are_rejected(self):
        observer,code=self.observer();item=self.request(code)
        for field,change in ((2,lambda value:value+1),(3,lambda value:b'x'*32)):
            with self.subTest(field=field),self.mutate_response(observer,field,change),self.assertRaisesRegex(ContractError,'OBSERVER_RESPONSE_BINDING_MISMATCH'):
                self.call(observer,item)

    def test_wrong_request_job_or_code_commitment_is_rejected(self):
        observer,code=self.observer();item=self.request(code)
        for field in (4,5,6):
            with self.subTest(field=field),self.mutate_response(observer,field,lambda value:b'x'*32),self.assertRaisesRegex(ContractError,'OBSERVER_RESPONSE_BINDING_MISMATCH'):
                self.call(observer,item)

    def test_replayed_actual_response_is_rejected_after_fresh_native_run(self):
        observer,code=self.observer();item=self.request(code);self.call(observer,item)
        old=observer.last_evidence['raw_bytes'];original=observer._exchange
        def replay(*args):
            raw,stderr,exit_code=original(*args)
            return old,stderr,exit_code
        with patch.object(observer,'_exchange',replay),self.assertRaisesRegex(ContractError,'OBSERVER_RESPONSE_BINDING_MISMATCH'):
            self.call(observer,item)

    def test_missing_overlong_and_malformed_actual_result_never_become_zero(self):
        observer,code=self.observer();item=self.request(code);original=observer._exchange
        for transform in (lambda value:b'',lambda value:value+b'x',lambda value:b'BADMAGIC'+value[8:]):
            def changed(*args):
                raw,stderr,exit_code=original(*args)
                return transform(raw),stderr,exit_code
            with self.subTest(transform=transform),patch.object(observer,'_exchange',changed),self.assertRaises(ContractError):self.call(observer,item)

    def test_native_policy_disagreement_is_rejected(self):
        observer,code=self.observer();item=self.request(code)
        with self.mutate_response(observer,22,lambda value:123),self.assertRaisesRegex(ContractError,'OBSERVER_PARENT_POLICY_DISAGREEMENT'):
            self.call(observer,item)

    def test_native_clock_outside_fresh_parent_bracket_is_rejected(self):
        observer,code=self.observer();item=self.request(code)
        with self.mutate_response(observer,18,lambda value:0),self.assertRaisesRegex(ContractError,'OBSERVER_NATIVE_CLOCK_OUTSIDE_BRACKET'):
            self.call(observer,item)

    def test_invalid_native_clock_frequency_is_rejected(self):
        observer,code=self.observer();item=self.request(code)
        with self.mutate_response(observer,20,lambda value:value+1),self.assertRaisesRegex(ContractError,'OBSERVER_NATIVE_CLOCK_CALIBRATION_MISMATCH'):
            self.call(observer,item)

    def test_pre_cancelled_event_starts_no_observer(self):
        observer,code=self.observer();item=self.request(code);event=threading.Event();event.set()
        with self.assertRaisesRegex(ContractError,'OBSERVER_CANCELLED'):observer.observe(item,self.target,cancelled=event)
        self.assertIsNone(observer._custody)

    def test_cancellation_after_launch_retires_actual_observer(self):
        observer,code=self.observer();item=self.request(code);event=threading.Event()
        original=native.WindowsOwnedProcess.launch.__func__
        def launch(cls,*args,**kwargs):
            owner=original(cls,*args,**kwargs);event.set();return owner
        with patch.object(native.WindowsOwnedProcess,'launch',classmethod(launch)),self.assertRaisesRegex(ContractError,'OBSERVER_CANCELLED'):
            self.call(observer,item,cancelled=event)
        self.assertTrue(observer.last_evidence['cleanup']['closed'])

    def test_expired_deadline_prevents_observer_launch(self):
        observer,code=self.observer();item=self.request(code)
        time.sleep(.002)
        item=replace(item,deadline=replace(item.deadline,expires_monotonic_ns=item.deadline.issued_monotonic_ns+1))
        with self.assertRaisesRegex(ContractError,'DEADLINE_EXPIRED_OR_UNCERTAIN'):observer.observe(item,self.target)

    def test_wrong_clock_provider_and_wrong_native_code_are_rejected(self):
        with self.assertRaisesRegex(ContractError,'OBSERVER_NATIVE_CLOCK_REQUIRED'):
            observe_module.NativeCpuEffectObserver(self.binary,sha(self.binary),HASH,clock=object())
        with self.assertRaisesRegex(ContractError,'OBSERVER_CODE_COMMITMENT_MISMATCH'):
            observe_module.NativeCpuEffectObserver(self.binary,sha(self.binary),HASH,clock=self.clock)

    def test_concurrent_same_observer_admission_is_rejected(self):
        observer,code=self.observer();item=self.request(code)
        observer._lock.acquire()
        try:
            with self.assertRaisesRegex(ContractError,'OBSERVER_BUSY'):observer.observe(item,self.target)
        finally:observer._lock.release()

    def test_two_observers_have_distinct_lifetimes_and_independent_sequences(self):
        left,left_code=self.observer();right,right_code=self.observer()
        first=self.call(left,self.request(left_code));second=self.call(right,self.request(right_code))
        self.assertNotEqual(first.observer_identity,second.observer_identity)
        self.assertEqual(first.sequence,second.sequence)

    def test_returned_evidence_is_detached_from_retained_facts(self):
        observer,code=self.observer();self.call(observer,self.request(code))
        changed=observer.last_evidence;changed['accepted']=False;changed['cleanup']['closed']=False
        self.assertTrue(observer.last_evidence['accepted']);self.assertTrue(observer.last_evidence['cleanup']['closed'])

    def negative_observer(self,name):
        binary=Path(os.environ['CETA_OBSERVER_NEGATIVE_ROOT'])/(name+'.exe')
        image=sha(binary)
        code=observe_module.observer_code_commitment(image,sha(Path(observe_module.__file__)))
        observer=observe_module.NativeCpuEffectObserver(binary,image,code,clock=self.clock)
        self.observers.append(observer)
        self.receipt['controls'].append({'controlled_negative_native_image':str(binary),'sha256':image,
            'production_registered':False})
        return observer,code

    def test_separate_native_probe_cannot_Set_or_Terminate_through_inherited_handles(self):
        observer,code=self.negative_observer('rights');item=self.request(code)
        custody=observe_module._Custody()
        custody.lease=self.target.export_cpu_query_handles(item.process_identity)
        process,job=custody.lease.inherited_handles
        frame=observe_module.REQUEST.pack(b'CETAOB1\0',1,1,process,job,b'x'*32,
            bytes.fromhex(item.input_commitment[7:]),bytes.fromhex(item.job_digest[7:]),bytes.fromhex(code[7:]),
            item.process_identity.pid,item.process_identity.creation_time,
            bytes.fromhex(item.process_identity.image_digest[7:]),bytes.fromhex(sha(Path(observer._executable))))
        try:
            raw,stderr,exit_code=observer._exchange(custody,frame,None,time.monotonic_ns()+1_000_000_000)
            self.assertEqual(exit_code,0);self.assertEqual(stderr,b'')
            self.assertEqual(struct.unpack('<IIII',raw),(0,5,0,5))
            self.assertIsNone(self.target.poll())
            self.receipt['controls'].append({'actual_separate_PID':custody.process.pid,
                'creation_time':custody.process.creation_time,'Set_return':0,'Set_last_error':5,
                'Terminate_return':0,'Terminate_last_error':5,'native_raw':raw})
        finally:
            custody.close();self.receipt['controls'].append({'rights_probe_cleanup':custody.evidence()})

    def test_actual_overlong_native_pipe_output_is_rejected_and_retired(self):
        observer,code=self.negative_observer('overlong')
        with self.assertRaisesRegex(ContractError,'OBSERVER_OUTPUT_OVERLONG'):self.call(observer,self.request(code))
        self.assertTrue(observer.last_evidence['cleanup']['closed'])

    def test_actual_silent_native_process_times_out_and_is_retired(self):
        observer,code=self.negative_observer('silent')
        item=replace(self.request(code),maximum_duration_ns=50_000_000)
        with self.assertRaisesRegex(ContractError,'OBSERVER_PROCESS_TIMEOUT'):self.call(observer,item)
        self.assertTrue(observer.last_evidence['cleanup']['closed'])

    def test_actual_different_job_object_reports_unavailable_membership(self):
        observer,code=self.observer();item=self.request(code);other=self.new_target()
        second=other.export_cpu_query_handles(other.resource_identity);self.leases.append(second)
        other_job=second.inherited_handles[1]
        original=native.WindowsCpuQueryHandles.inherited_handles.fget
        def wrong_job(lease):
            process,job=original(lease)
            return (process,other_job) if lease.identity==item.process_identity else (process,job)
        with patch.object(native.WindowsCpuQueryHandles,'inherited_handles',property(wrong_job)):
            value=self.call(observer,item)
        self.assertIs(value.state,ObservationState.UNAVAILABLE)
        self.assertIsNone(value.limit);self.assertEqual(value.target_state,'NOT_IN_OWNED_JOB')

    def test_actual_exit_between_export_and_native_query_never_reports_measured(self):
        observer,code=self.observer();item=self.request(code);original=observer._exchange
        def exited(*args):
            self.target.terminate(17);self.assertTrue(self.target.wait(2))
            return original(*args)
        with patch.object(observer,'_exchange',exited):
            try:value=self.call(observer,item)
            except ContractError:
                self.assertFalse(observer.last_evidence['accepted'])
            else:
                self.assertIs(value.state,ObservationState.UNAVAILABLE);self.assertIsNone(value.limit)

    def test_actual_concurrent_same_observer_request_is_refused_without_extra_sequence(self):
        observer,code=self.observer();item=self.request(code)
        entered,release=threading.Event(),threading.Event();results=[];errors=[]
        original=observer._exchange
        def held(*args):
            entered.set();self.assertTrue(release.wait(2));return original(*args)
        def worker():
            try:results.append(self.call(observer,item))
            except BaseException as error:errors.append(error)
        with patch.object(observer,'_exchange',held):
            thread=threading.Thread(target=worker,name='OB1-controlled-concurrent-request');thread.start()
            try:
                self.assertTrue(entered.wait(2))
                with self.assertRaisesRegex(ContractError,'OBSERVER_BUSY'):observer.observe(item,self.target)
            finally:release.set();thread.join(3)
        self.assertFalse(thread.is_alive());self.assertFalse(errors,errors)
        self.assertEqual(len(results),1);self.assertEqual(results[0].sequence,1)

    def test_actual_query_close_response_loss_preserves_replacement_event_and_recovers(self):
        observer,code=self.observer();item=self.request(code)
        original_export=self.target.export_cpu_query_handles;original_close=self.target._api.close
        selected=[];replacement=[];hit=[];primary=RuntimeError('CONTROLLED_QUERY_CLOSE_AFTER_NATIVE_SUCCESS')
        event_api=self.target._api.dll.CreateEventW
        event_api.argtypes,event_api.restype=[C.c_void_p,C.c_int32,C.c_int32,C.c_wchar_p],native.HANDLE
        def export(identity):
            lease=original_export(identity);selected.append(lease.inherited_handles[0]);return lease
        def closed_then_raise(handle):
            if selected and handle==selected[0] and not hit:
                hit.append(handle);original_close(handle)
                event=event_api(None,True,False,None);self.assertTrue(event);replacement.append(event)
                raise primary
            original_close(handle)
        try:
            with patch.object(self.target,'export_cpu_query_handles',export),patch.object(self.target._api,'close',closed_then_raise):
                with self.assertRaises(RuntimeError) as caught:self.call(observer,item)
            self.assertIs(caught.exception,primary)
            flags=native.DWORD()
            self.assertTrue(self.target._api.GetHandleInformation(replacement[0],C.byref(flags)))
            self.assertTrue(observer.last_evidence['cleanup']['closed'])
            self.receipt['controls'].append({'actual_query_handle':selected[0],'actual_replacement_event':replacement[0],
                'numeric_slot_reused':selected[0]==replacement[0],'replacement_still_open':True,
                'primary_object_preserved':caught.exception is primary})
            fresh=self.call(observer,item)
            self.assertIs(fresh.state,ObservationState.MEASURED);self.assertEqual(fresh.sequence,2)
        finally:
            for event in replacement:original_close(event)

    def test_trusted_owned_process_subclass_preserves_actual_query_custody(self):
        class TrustedOwnedFixture(native.WindowsOwnedProcess):pass
        derived=TrustedOwnedFixture.launch(str(self.worker),('hold','30000'),cwd=str(self.directory),
            environment=controlled_environment(self.directory),expected_image_sha256=sha(self.worker))
        self.targets.append(derived)
        observer,code=self.observer();item=self.request(code,derived)
        value=observer.observe(item,derived)
        self.receipt['observations'].append(observer.last_evidence)
        self.assertEqual(value.identity,derived.resource_identity)
        self.assertIs(value.state,ObservationState.MEASURED)

    def test_cancellation_from_final_real_clock_sample_denies_publication(self):
        observer,code=self.observer();item=self.request(code);event=threading.Event()
        original=self.clock.clock;calls=[]
        def final_sample():
            pair=original();calls.append(1)
            if len(calls)==2:event.set()
            return pair
        with patch.object(self.clock,'clock',final_sample),self.assertRaisesRegex(ContractError,'OBSERVER_CANCELLED'):
            observer.observe(item,self.target,cancelled=event)
        self.receipt['observations'].append(observer.last_evidence)
        self.receipt['controls'].append({'actual_NC2_samples':len(calls),'controlled_final_sample_cancellation':True})
        self.assertTrue(observer.last_evidence['cleanup']['closed'])

    def test_secondary_evidence_failure_preserves_primary_and_releases_request_lock(self):
        observer,code=self.observer();item=self.request(code)
        primary=KeyboardInterrupt('CONTROLLED_OBSERVATION_PRIMARY');diagnostic=OSError('CONTROLLED_EVIDENCE_SECONDARY')
        with patch.object(observer,'_exchange',side_effect=primary),patch.object(observe_module._Custody,'evidence',side_effect=diagnostic):
            with self.assertRaises(KeyboardInterrupt) as caught:observer.observe(item,self.target)
        self.assertIs(caught.exception,primary)
        self.assertTrue(primary.observer_custody.closed)
        self.assertIs(primary.observer_diagnostic_error,diagnostic)
        self.assertTrue(observer._lock.acquire(blocking=False));observer._lock.release()
        self.assertFalse(observer.last_evidence['accepted'])
        value=self.call(observer,item);self.assertIs(value.state,ObservationState.MEASURED)

    def test_successful_native_result_is_not_published_after_evidence_failure(self):
        observer,code=self.observer();item=self.request(code);diagnostic=OSError('CONTROLLED_EVIDENCE_PUBLICATION_FAILURE')
        with patch.object(observe_module._Custody,'evidence',side_effect=diagnostic):
            with self.assertRaises(OSError) as caught:observer.observe(item,self.target)
        self.assertIs(caught.exception,diagnostic);self.assertTrue(diagnostic.observer_custody.closed)
        self.assertFalse(observer.last_evidence['accepted'])
        self.assertTrue(observer._lock.acquire(blocking=False));observer._lock.release()
        value=self.call(observer,item);self.assertIs(value.state,ObservationState.MEASURED)
