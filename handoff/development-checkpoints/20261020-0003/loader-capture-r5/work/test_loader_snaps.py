"""Controlled native-function fixtures only; no kernel/DLL/child is invoked."""
from dataclasses import asdict
from types import SimpleNamespace
import ctypes as C
import struct
import unittest
from contextlib import contextmanager
from capture_core import CaptureError, OwnedIdentity, Collector, Limits, CREATE_PROCESS, EXIT_PROCESS
from loader_snaps import (LoaderSnaps, PebLayout, PROCESS_BASIC_INFORMATION, initialization_evidence,
                          pe_codeview, pdb_codeview, match_codeview,resolve_layout, SYMBOL_INFOW, prepare_producer)
from test_loader_capture import Functions, native_event, TickingClock
from win32_debug import Win32DebugPort


class patch:
    @staticmethod
    @contextmanager
    def object(target,name,*,return_value):
        before=getattr(target,name)
        setattr(target,name,lambda *args,**kwargs:return_value)
        try:yield
        finally:setattr(target,name,before)


class SnapsFunctions:
    def __init__(self):
        self.flags=0x100;self.calls=[];self.query_status=0;self.read_ok=True;self.write_ok=True
        self.write_count=4;self.write_interrupt=False;self.readback_wrong=False;self.creation=9
    def GetProcessId(self,handle):self.calls.append(('pid',handle.value));return 7
    def GetProcessTimes(self,handle,*values):values[0]._obj.low=self.creation;return 1
    def NtQueryInformationProcess(self,handle,kind,pointer,size,length):
        self.calls.append(('query',handle.value,kind,size));pointer._obj.peb=0x10000
        pointer._obj.pid=7;length._obj.value=C.sizeof(PROCESS_BASIC_INFORMATION);return self.query_status
    def ReadProcessMemory(self,handle,address,pointer,size,count):
        self.calls.append(('read',handle.value,address.value,size));count._obj.value=4
        pointer._obj.value=self.flags if not self.readback_wrong or len(self.calls)<5 else 0
        return self.read_ok
    def WriteProcessMemory(self,handle,address,pointer,size,count):
        self.calls.append(('write',handle.value,address.value,size,pointer._obj.value))
        self.flags=pointer._obj.value;count._obj.value=self.write_count
        if self.write_interrupt:raise KeyboardInterrupt('controlled lost write return')
        return self.write_ok


def producer(functions=None,**kwargs):
    functions=functions or SnapsFunctions()
    return functions,LoaderSnaps(functions,functions,OwnedIdentity(7,9,'a'*64),
        PebLayout('b'*64,'c'*64,0x800,0xbc,4),authorized=True,**kwargs)


def rows(lines,*,module=r'C:\Windows\System32\example.dll',unicode=True):
    result=[dict(index=0,event_code=6,pid=7,tid=8,data=dict(image=dict(state='OBSERVED',path=module)))]
    for line in lines:
        raw=line.encode('utf-16-le' if unicode else 'ascii')
        result.append(dict(index=len(result),event_code=8,pid=7,tid=8,data=dict(
            read_state='COMPLETE_REPORTED_LENGTH',truncated=False,unicode=unicode,raw_hex=raw.hex())))
    return result


FAIL='7:8 @ 100 - LdrpInitializeNode - ERROR: Init routine 00007FFE00001000 for DLL "C:\\Windows\\System32\\example.dll" failed during DLL_PROCESS_ATTACH\n'
STATUS='7:8 @ 101 - LdrpInitializationFailure - ERROR: Process initialization failed with status 0xc0000142\n'
PRODUCER=dict(state='READBACK_CONFIRMED',pid=7,creation_time=9)


class ProducerTests(unittest.TestCase):
    def test_exact_stdio_budget_can_retire_eof_without_reading_extra_bytes(self):
        functions=Functions([native_event(CREATE_PROCESS),native_event(EXIT_PROCESS)])
        port=Win32DebugPort(functions,OwnedIdentity(7,9,'a'*64),stdout_handle=11,stderr_handle=12,
                            last_error=lambda:functions.error)
        report=Collector(port,OwnedIdentity(7,9,'a'*64),Limits(stdio_bytes=12),clock=TickingClock()).run()
        self.assertTrue(report['finished']);self.assertEqual(report['stdout_bytes']+report['stderr_bytes'],12)
    def test_exact_x64_pbi_and_flags_read_modify_readback(self):
        api,capture=producer();report=capture.enable(70,7,9)
        self.assertEqual(C.sizeof(PROCESS_BASIC_INFORMATION),48)
        self.assertEqual(report['state'],'READBACK_CONFIRMED')
        self.assertEqual((report['before'],report['after']),(0x100,0x102))
        self.assertEqual([row for row in api.calls if row[0]=='write'],[('write',70,0x100bc,4,0x102)])
        with self.assertRaisesRegex(CaptureError,'SINGLE_ATTEMPT'):capture.enable(70,7,9)
    def test_already_enabled_flag_is_verified_without_write(self):
        api,capture=producer();api.flags=0x102;capture.enable(70,7,9)
        self.assertFalse(any(row[0]=='write' for row in api.calls))
    def test_foreign_identity_refused_before_queries(self):
        api,capture=producer()
        with self.assertRaisesRegex(CaptureError,'OWNED_CREATE'):capture.enable(70,999,9)
        self.assertEqual(api.calls,[])
    def test_creation_time_refused_before_peb_query(self):
        api,capture=producer();api.creation=10
        with self.assertRaisesRegex(CaptureError,'CREATION_CHANGED'):capture.enable(70,7,9)
        self.assertFalse(any(row[0]=='query' for row in api.calls))
    def test_query_failure_never_writes(self):
        api,capture=producer();api.query_status=-1
        with self.assertRaisesRegex(CaptureError,'EXACT_PBI'):capture.enable(70,7,9)
        self.assertFalse(any(row[0]=='write' for row in api.calls))
    def test_short_write_and_known_failure_do_not_continue_or_retry(self):
        for changes in ({'write_count':2},{'write_ok':False}):
            api,capture=producer()
            for name,value in changes.items():setattr(api,name,value)
            with self.subTest(changes=changes),self.assertRaisesRegex(CaptureError,'FLAG_WRITE'):capture.enable(70,7,9)
            with self.assertRaisesRegex(CaptureError,'SINGLE_ATTEMPT'):capture.enable(70,7,9)
            self.assertEqual(sum(row[0]=='write' for row in api.calls),1)
    def test_unknown_write_return_preserves_exact_custody_without_retry(self):
        api,capture=producer();api.write_interrupt=True
        with self.assertRaises(KeyboardInterrupt):capture.enable(70,7,9)
        self.assertEqual(capture.report()['state'],'WRITE_IN_FLIGHT')
        self.assertEqual((capture.report()['process_handle'],capture.report()['address']),(70,0x100bc))
        with self.assertRaises(CaptureError):capture.enable(70,7,9)
        self.assertEqual(sum(row[0]=='write' for row in api.calls),1)
    def test_readback_disagreement_is_not_initialization_enablement(self):
        api,capture=producer();api.readback_wrong=True
        with self.assertRaisesRegex(CaptureError,'READBACK_MISMATCH'):capture.enable(70,7,9)
        self.assertEqual(capture.report()['state'],'POST_READ_IN_FLIGHT')
        with self.assertRaises(CaptureError):capture.enable(70,7,9)
    def test_wrong_thread_refused_before_native_boundary(self):
        thread=[1];api,capture=producer(thread_id=lambda:thread[0]);thread[0]=2
        with self.assertRaisesRegex(CaptureError,'CREATOR_THREAD'):capture.enable(70,7,9)
        self.assertEqual(api.calls,[])
    def test_effect_authorization_is_literal_and_layout_bounded(self):
        with self.assertRaisesRegex(CaptureError,'EXPLICIT_MEMORY'):prepare_producer(None,{})
        for offset in (-1,1,0x800):
            with self.subTest(offset=offset),self.assertRaises(CaptureError):PebLayout('b'*64,'c'*64,0x800,offset,4)
    def test_producer_is_called_at_verified_create_stop_before_continue(self):
        functions=Functions([native_event(CREATE_PROCESS),native_event(EXIT_PROCESS)])
        api,capture=producer()
        port=Win32DebugPort(functions,OwnedIdentity(7,9,'a'*64),loader_snaps=capture,last_error=lambda:functions.error)
        report=Collector(port,OwnedIdentity(7,9,'a'*64),Limits(),clock=TickingClock()).run()
        self.assertEqual(report['native_pending']['loader_snaps']['state'],'READBACK_CONFIRMED')
        self.assertEqual(len(functions.continued),2)
    def test_failed_instrumentation_retains_event_and_never_continues(self):
        functions=Functions([native_event(CREATE_PROCESS)])
        api,capture=producer();api.write_count=1
        port=Win32DebugPort(functions,OwnedIdentity(7,9,'a'*64),loader_snaps=capture,last_error=lambda:functions.error)
        with self.assertRaises(CaptureError):Collector(port,OwnedIdentity(7,9,'a'*64),Limits(),clock=TickingClock()).run()
        self.assertEqual(functions.continued,[]);self.assertEqual(port.pending()['file_handle'],33)
    def test_failed_instrumentation_has_explicit_owner_retirement_path(self):
        from isolated_adapter import Session
        functions=Functions([native_event(CREATE_PROCESS),native_event(EXIT_PROCESS,status=125)])
        api,capture=producer();api.write_count=1
        port=Win32DebugPort(functions,OwnedIdentity(7,9,'a'*64),loader_snaps=capture,last_error=lambda:functions.error)
        with self.assertRaises(CaptureError):Collector(port,OwnedIdentity(7,9,'a'*64),Limits(),clock=TickingClock()).run()
        calls=[]
        owner=SimpleNamespace(pid=7,creation_time=9,image_sha256='a'*64,lifetime_closed=False,
            poll=lambda:None,active_process_count=lambda:0,terminate=lambda code:calls.append(('terminate',code)),
            wait=lambda seconds:True)
        owner.close=lambda:setattr(owner,'lifetime_closed',True)
        session=Session(owner,port,Limits(),__import__('pathlib').Path('unused'),SimpleNamespace(native_inputs={}))
        import isolated_adapter
        original=isolated_adapter.write_new
        isolated_adapter.write_new=lambda path,raw:calls.append(('receipt',path.name))
        try:result=session.retire()
        finally:isolated_adapter.write_new=original
        self.assertTrue(result['lifetime_closed']);self.assertEqual(calls[0],('terminate',125))
        self.assertEqual(sum(row[0]=='write' for row in api.calls),1)
        self.assertEqual(len(functions.continued),2)


class AttributionTests(unittest.TestCase):
    def evidence(self,events,producer=PRODUCER,status=0xc0000142):
        return initialization_evidence(events,OwnedIdentity(7,9,'a'*64),status,producer)
    def test_explicit_module_phase_status_and_raw_span_are_retained(self):
        result=self.evidence(rows([FAIL,STATUS]))
        self.assertEqual(result['failure_attribution'],'EXPLICIT_OWNED_CHILD_INITIALIZATION_DIAGNOSTIC')
        self.assertEqual(result['failed_module'],r'C:\Windows\System32\example.dll')
        self.assertEqual(result['failed_phase'],'DLL_PROCESS_ATTACH')
        self.assertEqual(result['initialization_status'],0xc0000142)
        self.assertEqual(result['evidence'][0]['raw_line'],FAIL.rstrip('\n'))
        self.assertEqual(result['root_cause'],'UNKNOWN')
    def test_module_order_or_plain_status_does_not_attribute(self):
        for lines in ([STATUS],['loaded example.dll\n',STATUS],[FAIL]):
            with self.subTest(lines=lines):self.assertEqual(self.evidence(rows(lines))['failure_attribution'],'UNKNOWN')
    def test_disabled_or_unverified_producer_keeps_unknown(self):
        for value in (None,{},dict(PRODUCER,state='WRITE_IN_FLIGHT'),dict(PRODUCER,pid=999)):
            with self.subTest(value=value):self.assertEqual(self.evidence(rows([FAIL,STATUS]),value)['failure_attribution'],'UNKNOWN')
    def test_foreign_text_identity_or_wrong_status_is_not_accepted(self):
        for lines in ([FAIL.replace('7:8','9:8'),STATUS],[FAIL,STATUS.replace('0142','0005')],
                      [FAIL,STATUS.replace('7:8','7:9')],[STATUS,FAIL]):
            with self.subTest(lines=lines):self.assertEqual(self.evidence(rows(lines))['failure_attribution'],'UNKNOWN')
    def test_unterminated_partial_invalid_unicode_and_unobserved_module_remain_unknown(self):
        cases=[rows([FAIL.rstrip('\n'),STATUS]),rows([FAIL,STATUS],module=r'C:\Windows\System32\other.dll')]
        partial=rows([FAIL,STATUS]);partial[1]['data']['read_state']='PARTIAL_OR_UNAVAILABLE';cases.append(partial)
        truncated=rows([FAIL,STATUS]);truncated[1]['data']['truncated']=True;cases.append(truncated)
        invalid=rows([FAIL,STATUS]);invalid[1]['data']['raw_hex']='00';cases.append(invalid)
        for events in cases:
            with self.subTest(events=events):self.assertEqual(self.evidence(events)['failure_attribution'],'UNKNOWN')
    def test_multiple_explicit_failed_modules_remain_ambiguous(self):
        events=rows([FAIL,FAIL.replace('example.dll','second.dll'),STATUS])
        self.assertEqual(self.evidence(events)['failure_attribution'],'UNKNOWN')
    def test_ascii_and_nt_path_module_observation_match_without_basename_guess(self):
        result=self.evidence(rows([FAIL,STATUS],module=r'\\?\C:\Windows\System32\example.dll',unicode=False))
        self.assertEqual(result['failed_phase'],'DLL_PROCESS_ATTACH')
    def test_explicit_ansi_debug_exception_transport_is_preserved(self):
        events=rows([FAIL,STATUS],unicode=False)
        for row in events[1:]:
            output=row['data'];row['event_code']=1
            row['data']=dict(exception_code=0x40010006,first_chance=True,debug_output=output)
        self.assertEqual(self.evidence(events)['failed_phase'],'DLL_PROCESS_ATTACH')
        events[1]['data']['first_chance']=False
        self.assertEqual(self.evidence(events)['failure_attribution'],'UNKNOWN')
    def test_raw_debug_exception_read_does_not_swallow_the_exception(self):
        event=native_event(1,status=0x40010006)
        event.info.exception.record.number=2
        event.info.exception.record.information[0]=len(FAIL)
        event.info.exception.record.information[1]=1000
        functions=Functions([native_event(CREATE_PROCESS),event,native_event(EXIT_PROCESS)])
        functions.memory=FAIL.encode('ascii')
        port=Win32DebugPort(functions,OwnedIdentity(7,9,'a'*64),last_error=lambda:functions.error)
        result=Collector(port,OwnedIdentity(7,9,'a'*64),Limits(),clock=TickingClock()).run()
        self.assertEqual(result['debug_bytes'],len(FAIL))
        self.assertEqual(result['events'][1]['data']['debug_output']['raw_hex'],FAIL.encode('ascii').hex())
        self.assertEqual(functions.continued[1][2],0x80010001)


class CallerTests(unittest.TestCase):
    def fake(self,fail=None,retire_fail=False):
        calls=[]
        class Session:
            owner=object();persist_started=False
            def collect(self):
                calls.append('collect');self.persist_started=True
                if fail=='collect':raise ValueError('primary collection')
                return {'status':'captured'}
            def persist(self,error):calls.append('persist');self.persist_started=True
            def retire(self):
                calls.append('retire')
                if retire_fail:raise RuntimeError('secondary retirement')
                return {'lifetime_closed':True}
        return calls,Session()
    def test_existing_caller_closes_child_pipe_ends_before_pumping(self):
        import owned_caller
        calls,session=self.fake()
        with patch.object(owned_caller,'launch_isolated_capture',return_value=session):
            result=owned_caller.execute_prepared_capture(release_path='unused',release_sha256='a'*64,
                launch_arguments={},stdout_handle=11,stderr_handle=12,close_child_pipe_ends=lambda:calls.append('close'))
        self.assertEqual(calls,['close','collect','retire']);self.assertFalse(result['native_qualification'])
    def test_primary_error_preserved_with_secondary_custody_and_no_replay(self):
        import owned_caller
        calls,session=self.fake(fail='collect',retire_fail=True)
        with patch.object(owned_caller,'launch_isolated_capture',return_value=session),self.assertRaises(ValueError) as caught:
            owned_caller.execute_prepared_capture(release_path='unused',release_sha256='a'*64,
                launch_arguments={},stdout_handle=11,stderr_handle=12,close_child_pipe_ends=lambda:calls.append('close'))
        self.assertIs(caught.exception.owned_process,session.owner)
        self.assertIsInstance(caught.exception.loader_capture_secondary[0],RuntimeError)
        self.assertEqual(calls,['close','collect','retire'])


def pe_fixture(guid=bytes(range(16)),age=7):
    raw=bytearray(0x1400);raw[:2]=b'MZ';struct.pack_into('<I',raw,0x3c,0x80)
    raw[0x80:0x84]=b'PE\x00\x00';struct.pack_into('<HH',raw,0x84,0x8664,1)
    struct.pack_into('<H',raw,0x94,0xf0);struct.pack_into('<H',raw,0x98,0x20b)
    struct.pack_into('<I',raw,0x98+108,16)
    struct.pack_into('<II',raw,0x98+112+6*8,0x1100,28)
    struct.pack_into('<IIII',raw,0x188+8,0x1000,0x1000,0x1000,0x400)
    rsds=b'RSDS'+guid+struct.pack('<I',age)+b'ntdll.pdb\x00'
    struct.pack_into('<IIII',raw,0x500+12,2,len(rsds),0x1200,0x600)
    raw[0x600:0x600+len(rsds)]=rsds
    return bytes(raw)


def pdb_fixture(guid=bytes(range(16)),age=7,dbi_age=7):
    raw=bytearray(4096);raw[:32]=b'Microsoft C/C++ MSF 7.00\r\n\x1aDS\x00\x00\x00'
    struct.pack_into('<6I',raw,32,512,1,8,28,0,2)
    struct.pack_into('<I',raw,2*512,3)
    struct.pack_into('<7I',raw,3*512,4,0,28,0,64,4,5)
    struct.pack_into('<III',raw,4*512,20000404,1,age)
    raw[4*512+12:4*512+28]=guid
    struct.pack_into('<iII',raw,5*512,-1,19990903,dbi_age)
    struct.pack_into('<H',raw,5*512+58,0x8664)
    return bytes(raw)


class SymbolFunctions:
    def __init__(self):
        self.calls=[];self.offset=0xbc;self.length=4;self.child_count=1;self.cleanup=True
        self.name=C.create_unicode_buffer('NtGlobalFlag')
    def SymInitializeW(self,*args):self.calls.append('initialize');return 1
    def SymLoadModuleExW(self,*args):self.calls.append(('load',args[2]));return args[4]
    def SymGetTypeFromNameW(self,context,base,name,pointer):
        self.calls.append(('type',name));pointer._obj.type_index=10;return 1
    def SymGetTypeInfo(self,context,base,index,kind,pointer):
        self.calls.append(('query',index,kind))
        if (index,kind)==(10,2):pointer._obj.value=0x800
        elif (index,kind)==(10,13):pointer._obj.value=self.child_count
        elif (index,kind)==(10,7):pointer._obj.children[0]=11
        elif (index,kind)==(11,1):pointer._obj.value=C.addressof(self.name)
        elif (index,kind)==(11,10):pointer._obj.value=self.offset
        elif (index,kind)==(11,4):pointer._obj.value=12
        elif (index,kind)==(12,2):pointer._obj.value=self.length
        else:return 0
        return 1
    def LocalFree(self,pointer):self.calls.append('free-name');return None
    def SymCleanup(self,*args):self.calls.append('cleanup');return self.cleanup


class SymbolTests(unittest.TestCase):
    def resolve(self,api):
        return resolve_layout(api,api,context=1,pdb_path=r'T:\private-fixture\ntdll.pdb',
            module_base=0x10000000,module_size=0x300000,ntdll_sha256='b'*64,pdb_sha256='c'*64)
    def test_pe_pdb_codeview_guids_and_age_match_as_binary_data(self):
        image=pe_codeview(pe_fixture())
        self.assertEqual(match_codeview(image,pdb_codeview(pdb_fixture()))['image_age'],7)
        self.assertEqual(match_codeview(image,pdb_codeview(pdb_fixture(age=8)))['info_age'],8)
        with self.assertRaisesRegex(CaptureError,'MISMATCH'):match_codeview(image,pdb_codeview(pdb_fixture(guid=b'X'*16)))
    def test_pe_malformed_rva_and_wrong_machine_rejected(self):
        for mutate in ('machine','rva','size','truncated'):
            raw=bytearray(pe_fixture())
            if mutate=='machine':struct.pack_into('<H',raw,0x84,0x14c)
            elif mutate=='rva':struct.pack_into('<I',raw,0x98+112+6*8,0xffffffff)
            elif mutate=='size':struct.pack_into('<I',raw,0x500+16,0xffffffff)
            else:raw=raw[:100]
            with self.subTest(mutate=mutate),self.assertRaises(CaptureError):pe_codeview(bytes(raw))
    def test_pdb_corruption_and_out_of_range_streams_rejected(self):
        for mutate in ('header','blocks','directory','stream'):
            raw=bytearray(pdb_fixture())
            if mutate=='header':raw[0]=0
            elif mutate=='blocks':struct.pack_into('<I',raw,40,0xffffffff)
            elif mutate=='directory':struct.pack_into('<I',raw,52,0xffffffff)
            else:struct.pack_into('<I',raw,3*512+20,0xffffffff)
            with self.subTest(mutate=mutate),self.assertRaises(CaptureError):pdb_codeview(bytes(raw))
    def test_ntglobalflag_offset_is_resolved_not_fixed(self):
        api=SymbolFunctions();api.offset=0xc0;layout=self.resolve(api)
        self.assertEqual(layout.offset,0xc0);self.assertEqual(layout.field_size,4)
        self.assertEqual(api.calls[1],('load',r'T:\private-fixture\ntdll.pdb'))
        self.assertIn('free-name',api.calls);self.assertEqual(api.calls[-1],'cleanup')
    def test_wrong_field_size_or_missing_type_is_not_a_fallback_offset(self):
        for changes in ({'length':8},{'child_count':0}):
            api=SymbolFunctions()
            for name,value in changes.items():setattr(api,name,value)
            with self.subTest(changes=changes),self.assertRaises(CaptureError):self.resolve(api)
            self.assertEqual(api.calls[-1],'cleanup')
    def test_type_failure_retains_secondary_cleanup_failure(self):
        api=SymbolFunctions();api.child_count=0;api.cleanup=False
        with self.assertRaises(CaptureError) as caught:self.resolve(api)
        self.assertIn('CHILD_COUNT',str(caught.exception))
        self.assertIn('CLEANUP_PENDING',str(caught.exception.loader_capture_secondary[0]))
    def test_unknown_symbol_initialize_or_load_return_is_not_replayed_or_cleaned(self):
        for operation in ('SymInitializeW','SymLoadModuleExW'):
            api=SymbolFunctions()
            def interrupted(*args):raise KeyboardInterrupt('controlled lost '+operation+' return')
            setattr(api,operation,interrupted)
            with self.subTest(operation=operation),self.assertRaises(KeyboardInterrupt) as caught:self.resolve(api)
            self.assertEqual(caught.exception.loader_symbol_custody['state'],operation+'_IN_FLIGHT')
            self.assertIs(caught.exception.loader_symbol_api,api)
            self.assertNotIn('cleanup',api.calls)


if __name__=='__main__':unittest.main(verbosity=2)
