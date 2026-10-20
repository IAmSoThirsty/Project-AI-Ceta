"""Deterministic controls only. Every Win32 function below is a local fixture."""
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
import copy
import ctypes as C
import json
import os
import unittest
from capture_core import *
from win32_debug import *
from isolated_adapter import (CreateProcessDebugHook,validate_release,KIND,F,RUNTIME,
                              WORKER_SHA256,error_record,Session,write_new,strict_json)


def native_event(code,pid=7,tid=8,**values):
    event=DEBUG_EVENT();event.code=code;event.pid=pid;event.tid=tid
    if code==CREATE_PROCESS:
        event.info.create_process.file=values.get('file',33)
        event.info.create_process.process=70;event.info.create_process.thread=71
        event.info.create_process.base=0x140000000
    elif code==LOAD_DLL:
        event.info.load.file=values.get('file',44);event.info.load.base=0x180000000
    elif code==EXCEPTION:
        event.info.exception.record.code=values.get('status',0xC0000142)
        event.info.exception.record.address=0x180001234
        event.info.exception.first_chance=values.get('first',1)
    elif code==OUTPUT_DEBUG_STRING:
        event.info.string.address=1000;event.info.string.length=values.get('length',4)
        event.info.string.unicode=values.get('unicode',1)
    elif code==EXIT_PROCESS:event.info.exit_process.code=values.get('status',0xC0000142)
    return event


class Functions:
    def __init__(self,events):
        self.events=list(events);self.error=0;self.calls=[];self.closed=[];self.continued=[]
        self.exited=False;self.pipes={11:bytearray(b'output'),12:bytearray(b'errors')}
        self.memory=b'A\x00B\x00';self.read_result=True
        self.close_result=True;self.continue_result=True
        self.wait_interrupt=False;self.close_interrupt=False
    def WaitForDebugEventEx(self,pointer,milliseconds):
        self.calls.append(('wait',int(milliseconds)))
        if not self.events:self.error=121;return 0
        event=self.events.pop(0);self.code=int(event.code)
        C.memmove(pointer,C.byref(event),C.sizeof(event))
        if self.wait_interrupt:raise KeyboardInterrupt('after native wait output')
        return 1
    def ContinueDebugEvent(self,pid,tid,status):
        self.continued.append((int(pid),int(tid),status))
        if not self.continue_result:self.error=5;return 0
        if self.code==EXIT_PROCESS:self.exited=True
        return 1
    def CloseHandle(self,handle):
        self.closed.append(handle.value)
        if self.close_interrupt:raise KeyboardInterrupt('after controlled close')
        if not self.close_result:self.error=6;return 0
        return 1
    def GetProcessId(self,handle):self.calls.append(('pid',handle.value));return 7
    def GetProcessTimes(self,handle,*values):
        self.calls.append(('times',handle.value));values[0]._obj.low=9;return 1
    def GetFileInformationByHandle(self,handle,pointer):
        self.calls.append(('file_info',handle.value));pointer._obj.volume=1;pointer._obj.index_low=22;return 1
    def GetFinalPathNameByHandleW(self,handle,buffer,size,flags):
        buffer.value='\\\\?\\C:\\Windows\\System32\\observed.dll';return len(buffer.value)
    def GetFileType(self,handle):return 3
    def GetHandleInformation(self,handle,pointer):pointer._obj.value=0;return 1
    def ReadProcessMemory(self,process,address,storage,amount,count):
        self.calls.append(('read_memory',process.value,address.value,int(amount)))
        raw=self.memory[:amount];C.memmove(storage,raw,len(raw));count._obj.value=len(raw)
        if not self.read_result:self.error=299
        return int(self.read_result)
    def PeekNamedPipe(self,handle,buffer,size,read,available,left):
        values=self.pipes[handle.value]
        if self.exited and not values:self.error=109;return 0
        available._obj.value=len(values);return 1
    def ReadFile(self,handle,storage,amount,count,overlapped):
        raw=bytes(self.pipes[handle.value][:amount]);del self.pipes[handle.value][:amount]
        C.memmove(storage,raw,len(raw));count._obj.value=len(raw);return 1


class TickingClock:
    def __init__(self):self.value=0.0
    def __call__(self):self.value+=0.001;return self.value


class CaptureTests(unittest.TestCase):
    def port(self,events,**kwargs):
        functions=Functions(events)
        port=Win32DebugPort(functions,OwnedIdentity(7,9,'a'*64),last_error=lambda:functions.error,**kwargs)
        return functions,port
    def test_native_public_x64_abi_layout(self):
        require_abi();self.assertEqual(DEBUG_EVENT.info.offset,16)
        self.assertEqual(C.sizeof(DEBUG_EVENT),176)
    def test_status_and_module_observations_keep_attribution_unknown(self):
        functions,port=self.port([native_event(CREATE_PROCESS),native_event(LOAD_DLL),native_event(EXCEPTION),native_event(EXIT_PROCESS)],
            stdout_handle=11,stderr_handle=12)
        collector=Collector(port,OwnedIdentity(7,9,'a'*64),Limits(),clock=TickingClock())
        result=collector.run()
        self.assertEqual(result['native_exit_code'],0xC0000142)
        self.assertEqual(result['failure_attribution'],'UNKNOWN');self.assertIsNone(result['failed_module'])
        self.assertEqual(functions.closed,[33,44]);self.assertNotIn(70,functions.closed);self.assertNotIn(71,functions.closed)
        self.assertEqual(bytes(collector.stdout),b'output');self.assertEqual(bytes(collector.stderr),b'errors')
        self.assertTrue(all(port.pipe_eof));self.assertTrue(result['exit_event_continued'])
        self.assertEqual(functions.continued[2][2],DBG_EXCEPTION_NOT_HANDLED)
    def test_only_one_first_chance_breakpoint_is_handled(self):
        functions,port=self.port([native_event(CREATE_PROCESS),native_event(EXCEPTION,status=BREAKPOINT),
            native_event(EXCEPTION,status=BREAKPOINT),native_event(EXIT_PROCESS,status=0)])
        result=Collector(port,OwnedIdentity(7,9,'a'*64),Limits(),clock=TickingClock()).run()
        self.assertTrue(result['initial_breakpoint_continued'])
        self.assertEqual([row[2] for row in functions.continued[1:3]],[DBG_CONTINUE,DBG_EXCEPTION_NOT_HANDLED])
    def test_second_chance_breakpoint_is_not_swallowed(self):
        functions,port=self.port([native_event(CREATE_PROCESS),native_event(EXCEPTION,status=BREAKPOINT,first=0),native_event(EXIT_PROCESS)])
        Collector(port,OwnedIdentity(7,9,'a'*64),Limits(),clock=TickingClock()).run()
        self.assertEqual(functions.continued[1][2],DBG_EXCEPTION_NOT_HANDLED)
    def test_foreign_pid_rejected_before_native_metadata_or_memory_reads(self):
        functions,port=self.port([native_event(CREATE_PROCESS,pid=999)])
        self.assertTrue(port.wait(1))
        with self.assertRaisesRegex(CaptureError,'FOREIGN_EVENT'):port.current(4)
        self.assertFalse(any(row[0] in ('pid','times','file_info','read_memory') for row in functions.calls))
        self.assertEqual(port.pending()['file_handle'],33)
    def test_creation_time_mismatch_is_not_zero_or_accepted(self):
        functions=Functions([native_event(CREATE_PROCESS)])
        port=Win32DebugPort(functions,OwnedIdentity(7,10,'a'*64),last_error=lambda:functions.error)
        port.wait(1)
        with self.assertRaisesRegex(CaptureError,'CREATION_IDENTITY'):port.current(4)
        self.assertEqual(functions.closed,[])
    def test_missing_create_event_is_refused(self):
        functions,port=self.port([native_event(LOAD_DLL)])
        with self.assertRaisesRegex(CaptureError,'CREATE_EVENT_MISSING'):
            Collector(port,OwnedIdentity(7,9,'a'*64),Limits(),clock=TickingClock()).run()
        self.assertEqual(functions.closed,[])
    def test_null_module_handle_is_unavailable(self):
        functions,port=self.port([native_event(CREATE_PROCESS,file=0)])
        port.wait(1);row=port.current(4)
        self.assertEqual(row.data['image']['state'],'UNAVAILABLE')
        port.continue_current(DBG_CONTINUE);self.assertEqual(functions.closed,[])
    def test_debug_string_uses_documented_byte_length_not_character_multiplier(self):
        functions,port=self.port([native_event(CREATE_PROCESS),native_event(OUTPUT_DEBUG_STRING,length=4)])
        port.wait(1);port.current(4);port.continue_current(DBG_CONTINUE)
        port.wait(1);event=port.current(4)
        self.assertEqual(event.data['captured_bytes'],4)
        self.assertEqual(event.data['raw_hex'],'41004200')
        self.assertEqual(event.data['utf16le_text'],'AB')
        self.assertFalse(event.data['full_length_known'])
        self.assertEqual(functions.calls[-1][-1],4)
    def test_partial_native_memory_read_preserves_partial_bytes(self):
        functions,port=self.port([native_event(CREATE_PROCESS),native_event(OUTPUT_DEBUG_STRING,length=8)])
        functions.memory=b'A\x00';functions.read_result=False
        port.wait(1);port.current(4);port.continue_current(DBG_CONTINUE)
        port.wait(1);event=port.current(8)
        self.assertEqual(event.data['read_state'],'PARTIAL_OR_UNAVAILABLE')
        self.assertEqual(event.data['raw_hex'],'4100');self.assertEqual(event.data['winerror'],299)
    def test_unknown_wait_return_keeps_buffer_and_never_replays(self):
        functions,port=self.port([native_event(CREATE_PROCESS)]);functions.wait_interrupt=True
        with self.assertRaises(KeyboardInterrupt):port.wait(1)
        self.assertEqual(port.pending()['event_state'],'WAIT_IN_FLIGHT')
        self.assertEqual(port.pending()['possible_file_handle_after_unknown_wait_return'],33)
        with self.assertRaises(CaptureError):port.wait(1)
        self.assertEqual(sum(row[0]=='wait' for row in functions.calls),1)
    def test_close_false_retains_exact_file_and_refuses_implicit_retry(self):
        functions,port=self.port([native_event(CREATE_PROCESS)]);functions.close_result=False
        port.wait(1);port.current(0)
        with self.assertRaises(CaptureError):port.continue_current(DBG_CONTINUE)
        self.assertEqual(port.pending()['file_handle'],33)
        with self.assertRaises(CaptureError):port.continue_current(DBG_CONTINUE)
        self.assertEqual(functions.closed,[33]);self.assertEqual(functions.continued,[])
    def test_response_loss_after_close_retains_uncertainty_no_double_close(self):
        functions,port=self.port([native_event(CREATE_PROCESS)]);functions.close_interrupt=True
        port.wait(1);port.current(0)
        with self.assertRaises(KeyboardInterrupt):port.continue_current(DBG_CONTINUE)
        self.assertEqual(port.pending()['file_state'],'CLOSE_IN_FLIGHT')
        with self.assertRaises(CaptureError):port.continue_current(DBG_CONTINUE)
        self.assertEqual(functions.closed,[33])
    def test_continue_failure_does_not_reclose_image_or_replay(self):
        functions,port=self.port([native_event(CREATE_PROCESS)]);functions.continue_result=False
        port.wait(1);port.current(0)
        with self.assertRaises(CaptureError):port.continue_current(DBG_CONTINUE)
        with self.assertRaises(CaptureError):port.continue_current(DBG_CONTINUE)
        self.assertEqual(functions.closed,[33]);self.assertEqual(len(functions.continued),1)
    def test_creator_thread_guard_runs_before_wait(self):
        selected=[1];functions,port=self.port([],thread_id=lambda:selected[0]);selected[0]=2
        with self.assertRaisesRegex(CaptureError,'CREATOR_THREAD'):port.wait(1)
        self.assertEqual(functions.calls,[])
    def test_deadline_exhaustion_is_single_attempt_and_retains_capture(self):
        functions,port=self.port([]);collector=Collector(port,OwnedIdentity(7,9,'a'*64),Limits(seconds=.01),clock=TickingClock())
        with self.assertRaises(CaptureError) as caught:collector.run()
        self.assertIs(caught.exception.loader_capture,collector)
        with self.assertRaisesRegex(CaptureError,'SINGLE_ATTEMPT'):collector.run()
    def test_event_count_bound_does_not_continue_unobserved_events(self):
        functions,port=self.port([native_event(CREATE_PROCESS),native_event(LOAD_DLL)])
        collector=Collector(port,OwnedIdentity(7,9,'a'*64),Limits(events=1),clock=TickingClock())
        with self.assertRaisesRegex(CaptureError,'EVENT_BOUND'):collector.run()
        self.assertEqual(len(functions.continued),1)
    def test_limit_types_reject_bool_nan_and_unbounded_values(self):
        for values in ({'seconds':True},{'seconds':float('nan')},{'events':True},{'events':4097},{'per_debug_string':65536}):
            with self.subTest(values=values),self.assertRaises(CaptureError):Limits(**values)
    def test_canonical_create_call_changes_only_debug_flag(self):
        seen=[];original=lambda *args:(seen.append(args),0)[1]
        args=('native-image',C.create_unicode_buffer('native command'),None,None,True,BASE_AC7_FLAGS,
              C.create_unicode_buffer('SystemRoot=C:\\Windows\x00\x00'),'native-cwd',object(),object())
        hook=CreateProcessDebugHook(original)
        self.assertEqual(hook(*args),0)
        self.assertEqual(seen[0][5],BASE_AC7_FLAGS|2)
        for i in range(10):
            if i!=5:self.assertIs(seen[0][i],args[i])
        self.assertEqual(hook.native_inputs['environment_buffer_hex'],
                         C.string_at(C.addressof(args[6]),C.sizeof(args[6])).hex())
        with self.assertRaises(CaptureError):hook(*args)
        self.assertEqual(len(seen),1)
    def test_noncanonical_or_descendant_debug_flags_are_refused(self):
        called=[];hook=CreateProcessDebugHook(lambda *args:called.append(args))
        args=[None]*10;args[4]=True;args[5]=BASE_AC7_FLAGS|1
        with self.assertRaises(CaptureError):hook(*args)
        self.assertEqual(called,[])
    def test_explicit_retirement_continues_pending_create_without_decoding_twice(self):
        functions,port=self.port([native_event(CREATE_PROCESS),native_event(EXIT_PROCESS,status=125)])
        port.wait(1);port.current(0)  # Already decoded when collection later fails.
        calls=[]
        owner=SimpleNamespace(pid=7,creation_time=9,image_sha256='a'*64,lifetime_closed=False,
            poll=lambda:None,active_process_count=lambda:0,terminate=lambda code:calls.append(('terminate',code)),
            wait=lambda seconds:True)
        def closed():owner.lifetime_closed=True
        owner.close=closed
        session=Session(owner,port,Limits(),Path('unused'),SimpleNamespace(native_inputs={}))
        import isolated_adapter
        prior=isolated_adapter.write_new;isolated_adapter.write_new=lambda path,raw:calls.append(('receipt',path.name))
        try:result=session.retire()
        finally:isolated_adapter.write_new=prior
        self.assertTrue(result['lifetime_closed']);self.assertEqual(functions.closed,[33])
        self.assertEqual(calls[0],('terminate',125))
        with self.assertRaisesRegex(CaptureError,'RETIRE_ALREADY'):session.retire()
    def test_unknown_native_wait_retirement_retains_owner_without_replay(self):
        functions,port=self.port([native_event(CREATE_PROCESS)]);functions.wait_interrupt=True
        with self.assertRaises(KeyboardInterrupt):port.wait(1)
        calls=[];owner=SimpleNamespace(pid=7,creation_time=9,image_sha256='a'*64,
            poll=lambda:None,active_process_count=lambda:0,terminate=lambda code:calls.append(code))
        session=Session(owner,port,Limits(),Path('unused'),SimpleNamespace(native_inputs={}))
        with self.assertRaisesRegex(CaptureError,'UNKNOWN_NATIVE') as caught:session.retire()
        self.assertIs(caught.exception.owned_process,owner)
        self.assertIs(caught.exception.loader_capture,session)
        self.assertEqual(calls,[125]);self.assertEqual(sum(row[0]=='wait' for row in functions.calls),1)


class ReleaseTests(unittest.TestCase):
    def release(self):
        return dict(schema_version=1,kind=KIND,executor='/root',repository=str(F),nonce='a'*32,
            issued_at_ns=10,expires_at_ns=100,code_manifest={},inputs={},worker_sha256=WORKER_SHA256,
            limits=asdict(Limits()),allow_debug_creation=True,allow_owned_debug_string_reads=True,
            allow_child_memory_writes=False,allow_existing_process_attach=False,
            allow_profile_creation=False,allow_profile_deletion=False,allow_global_configuration=False,
            automatic_retry=False,initial_breakpoint_policy='continue_one_first_chance_breakpoint',
            fixture_root=str(RUNTIME/'future-fixture'),parent_output_handles=[11,12])
    def test_exact_bounded_release_shape(self):self.assertIsInstance(validate_release(self.release(),20),Limits)
    def test_forbidden_effects_never_become_permissions(self):
        for name in ('allow_child_memory_writes','allow_existing_process_attach','allow_profile_creation',
                     'allow_profile_deletion','allow_global_configuration','automatic_retry'):
            value=self.release();value[name]=True
            with self.subTest(name=name),self.assertRaises(CaptureError):validate_release(value,20)
    def test_expired_wrong_image_unknown_field_and_duplicate_handles_refused(self):
        for changes in ({'expires_at_ns':15},{'worker_sha256':'b'*64},{'unexpected':True},{'parent_output_handles':[11,11]}):
            value=self.release();value.update(changes)
            with self.subTest(changes=changes),self.assertRaises(CaptureError):validate_release(value,20)
    def test_broken_exception_str_does_not_replace_diagnostic(self):
        class Bad(Exception):
            def __str__(self):raise RuntimeError('bad text')
        self.assertEqual(error_record(Bad())['message'],'<exception text unavailable>')
    def test_duplicate_json_key_cannot_replace_an_effect_boundary(self):
        with self.assertRaisesRegex(CaptureError,'DUPLICATE'):strict_json(b'{"automatic_retry":false,"automatic_retry":true}')
    def test_nonfinite_json_values_are_not_silently_accepted(self):
        for raw in (b'{"seconds":NaN}',b'{"seconds":Infinity}'):
            with self.assertRaises(CaptureError):strict_json(raw)


if __name__=='__main__':unittest.main(verbosity=2)
