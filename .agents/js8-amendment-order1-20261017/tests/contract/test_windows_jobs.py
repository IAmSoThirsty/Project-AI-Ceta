"""Real disposable Windows jobs; narrow lifecycle fixtures, not B-case proof.

Named events provide readiness/release barriers. Retained test metadata stays
under rebuild_ios/.agents/fixtures. No normal profile, installed service,
security configuration, arbitrary PID selection, or external executable is used.
"""
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch
import uuid

from ceta.contracts.wire import ContractError
from ceta.supervisor.windows_jobs import WindowsOwnedProcess, WindowsLaunchError, _API, DWORD

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(sys._base_executable).resolve()
HELPERS = r'''
import ctypes as C
from ctypes import wintypes as W
import json, os, pathlib, sys
k=C.WinDLL('kernel32',use_last_error=True,winmode=0x800)
k.OpenEventW.argtypes=[W.DWORD,W.BOOL,W.LPCWSTR];k.OpenEventW.restype=W.HANDLE
k.SetEvent.argtypes=[W.HANDLE];k.SetEvent.restype=W.BOOL
k.WaitForSingleObject.argtypes=[W.HANDLE,W.DWORD];k.WaitForSingleObject.restype=W.DWORD
k.CloseHandle.argtypes=[W.HANDLE];k.CloseHandle.restype=W.BOOL
k.GetProcessTimes.argtypes=[W.HANDLE,C.POINTER(W.FILETIME),C.POINTER(W.FILETIME),C.POINTER(W.FILETIME),C.POINTER(W.FILETIME)];k.GetProcessTimes.restype=W.BOOL
def creation(h):
    a,b,c,d=[W.FILETIME() for _ in range(4)]
    assert k.GetProcessTimes(h,C.byref(a),C.byref(b),C.byref(c),C.byref(d))
    return (a.dwHighDateTime<<32)|a.dwLowDateTime
def signal(name):
    h=k.OpenEventW(2,False,name);assert h
    try: assert k.SetEvent(h)
    finally: assert k.CloseHandle(h)
def wait(name):
    h=k.OpenEventW(0x100000,False,name);assert h
    try: assert k.WaitForSingleObject(h,20000)==0
    finally: assert k.CloseHandle(h)
'''
CHILD = HELPERS + r'''
ready,release,metadata,code=sys.argv[1:5]
pathlib.Path(metadata).write_text(json.dumps({'pid':os.getpid(),'creation':creation(-1),'argv':sys.argv[5:]}),encoding='utf-8')
signal(ready)
wait(release)
os._exit(int(code))
'''
TREE = HELPERS + r'''
import subprocess
base,child_code,ready,release,grand_ready,grand_release,metadata,grand_metadata,root_code=sys.argv[1:]
p=subprocess.Popen([base,'-B','-I','-c',child_code,grand_ready,grand_release,grand_metadata,'0'],env=dict(os.environ),creationflags=0x08000000)
pathlib.Path(metadata).write_text(json.dumps({'pid':os.getpid(),'child_pid':p.pid,'child_creation':creation(int(p._handle))}),encoding='utf-8')
signal(ready)
wait(release)
os._exit(int(root_code))
'''
PARENT = HELPERS + r'''
source,site,base,child_code,child_ready,child_release,child_metadata,parent_ready,parent_release,metadata,cwd=sys.argv[1:]
sys.path[:0]=[source,site]
from ceta.supervisor.windows_jobs import WindowsOwnedProcess
owned=WindowsOwnedProcess.launch(base,('-B','-I','-c',child_code,child_ready,child_release,child_metadata,'0'),cwd=cwd,environment=dict(os.environ))
pathlib.Path(metadata).write_text(json.dumps({'pid':owned.pid,'creation':owned.creation_time}),encoding='utf-8')
signal(parent_ready)
wait(parent_release)
os._exit(23)  # Actual parent death, not an explicit child terminate/close call.
'''


class Event:
    def __init__(self, api):
        self.api = api
        self.name = 'Local\\CETA-Owned-Job-Test-' + uuid.uuid4().hex
        self.handle = api.CreateEventW(None, True, False, self.name)
        if not self.handle or C.get_last_error() == 183:
            raise RuntimeError('fixture event ownership unavailable')

    def wait(self, seconds=8):
        if self.api.WaitForSingleObject(self.handle, int(seconds * 1000)) != 0:
            raise AssertionError('readiness barrier not observed: ' + self.name)

    def signal(self):
        if not self.api.SetEvent(self.handle):
            raise RuntimeError('fixture release failed')


@unittest.skipUnless(os.name == 'nt' and struct.calcsize('P') == 8, 'real Windows x64 required')
class WindowsJobTests(unittest.TestCase):
    def setUp(self):
        self.api = _API()
        declarations = {
            'CreateEventW': ([C.c_void_p,W.BOOL,W.BOOL,W.LPCWSTR],W.HANDLE),
            'SetEvent': ([W.HANDLE],W.BOOL),
            'OpenProcess': ([W.DWORD,W.BOOL,W.DWORD],W.HANDLE),
            'GetProcessHandleCount': ([W.HANDLE,C.POINTER(W.DWORD)],W.BOOL),
            'CreatePipe': ([C.POINTER(W.HANDLE),C.POINTER(W.HANDLE),C.c_void_p,W.DWORD],W.BOOL),
        }
        for name,(arguments,result) in declarations.items():
            function=getattr(self.api.dll,name)
            function.argtypes,function.restype=arguments,result
            setattr(self.api,name,function)
        self.directory=ROOT/'.agents/fixtures'/('windows-jobs-'+uuid.uuid4().hex)
        self.directory.mkdir(parents=True,exist_ok=False)
        self.environment={'SystemRoot':os.environ['SystemRoot'],'TEMP':str(self.directory),
                          'TMP':str(self.directory),'CETA_JOB_ENV':'explicit'}
        self.events,self.owned,self.foreign,self.handles=[],[],[],[]

    def tearDown(self):
        failures=[]
        for owned in reversed(self.owned):
            try:
                if owned.poll() is None or owned.active_process_count():
                    owned.terminate(126)
                    if not owned.wait(5):
                        raise AssertionError('owned fixture exit unobserved')
                self.until(lambda:owned.active_process_count()==0)
                owned.close()
            except BaseException as failure:
                # Test failures must not silently pretend ownership was settled.
                failures.append(str(failure))
        for process in self.foreign:
            if process.poll() is None:
                process.kill()  # Exact Popen-created fixture handle only.
            process.wait(timeout=5)
        for handle in self.handles:
            self.api.close(handle)
        for event in self.events:
            self.api.close(event.handle)
        if failures:
            self.fail('unresolved owned fixture cleanup: '+repr(failures))

    def event(self):
        event=Event(self.api)
        self.events.append(event)
        return event

    def until(self,predicate,seconds=5):
        deadline=time.monotonic()+seconds
        while not predicate():
            if time.monotonic()>=deadline:
                self.fail('bounded condition not observed')
            # Success requires the condition, never elapsed sleep alone.
            time.sleep(0.001)

    def launch(self,arguments,**kwargs):
        owned=WindowsOwnedProcess.launch(str(BASE),arguments,cwd=str(self.directory),
             environment=kwargs.pop('environment',self.environment),**kwargs)
        self.owned.append(owned)
        return owned

    def simple(self,exit_code=7,extra=()):
        ready,release=self.event(),self.event()
        metadata=self.directory/'primary.json'
        owned=self.launch(('-B','-I','-c',CHILD,ready.name,release.name,str(metadata),str(exit_code),*extra))
        ready.wait()
        return owned,release,json.loads(metadata.read_text(encoding='utf-8'))

    def selected_process(self,pid,expected_creation):
        handle=self.api.OpenProcess(0x100000|0x1000,False,pid)
        self.assertTrue(handle)
        self.handles.append(handle)
        values=[W.FILETIME() for _ in range(4)]
        self.assertTrue(self.api.GetProcessTimes(handle,*[C.byref(v) for v in values]))
        self.assertEqual((values[0].dwHighDateTime<<32)|values[0].dwLowDateTime,expected_creation)
        self.assertEqual(self.api.GetProcessId(handle),pid)
        return handle

    def members(self,owned,expected_lifetimes):
        # Console processes created with CREATE_NO_WINDOW can own a conhost.
        # Enumerate the exact job instead of assuming one PID per Python role.
        buffer,used=C.create_string_buffer(1024),DWORD()
        self.assertTrue(self.api.QueryInformationJobObject(owned._job,3,buffer,len(buffer),C.byref(used)))
        assigned,listed=(DWORD*2).from_buffer(buffer)
        self.assertEqual(assigned,listed)
        self.assertLessEqual(listed,(len(buffer)-8)//C.sizeof(C.c_size_t))
        rows=[]
        for pid in (C.c_size_t*listed).from_buffer(buffer,8):
            handle=self.api.OpenProcess(0x1000,False,pid)
            self.assertTrue(handle)
            try:
                member=W.BOOL()
                self.assertTrue(self.api.IsProcessInJob(handle,owned._job,C.byref(member)))
                self.assertTrue(member.value)
                self.assertEqual(self.api.GetProcessId(handle),pid)
                values=[W.FILETIME() for _ in range(4)]
                self.assertTrue(self.api.GetProcessTimes(handle,*[C.byref(v) for v in values]))
                creation=(values[0].dwHighDateTime<<32)|values[0].dwLowDateTime
                name,capacity=C.create_unicode_buffer(32768),DWORD(32768)
                self.assertTrue(self.api.QueryFullProcessImageNameW(handle,0,name,C.byref(capacity)))
                rows.append({'pid':pid,'creation_time':creation,'image_path':name.value})
            finally:
                self.api.close(handle)
        self.assertEqual(owned.active_process_count(),len(rows))
        selected={row['pid']:row for row in rows}
        self.assertTrue(set(expected_lifetimes)<=set(selected))
        for pid,creation in expected_lifetimes.items():
            self.assertEqual(selected[pid]['creation_time'],creation)
            self.assertEqual(os.path.normcase(selected[pid]['image_path']),os.path.normcase(str(BASE)))
        # This profile's additional processes are measured console hosts, not an
        # allowance for arbitrary new workers. Membership/empty-job checks persist.
        system_directory=self.api.dll.GetSystemDirectoryW
        system_directory.argtypes,system_directory.restype=[W.LPWSTR,W.UINT],W.UINT
        name=C.create_unicode_buffer(32768)
        self.assertTrue(0<system_directory(name,len(name))<len(name))
        console=os.path.normcase(str(Path(name.value)/'conhost.exe'))
        for row in rows:
            if row['pid'] not in expected_lifetimes:
                self.assertEqual(os.path.normcase(row['image_path']),console)
                self.assertGreater(row['creation_time'],0)
        (self.directory/('job-members-'+uuid.uuid4().hex+'.json')).write_text(json.dumps(rows,indent=2),encoding='utf-8')
        return rows

    def tree(self,root_code=9):
        ready,release,grand_ready,grand_release=(self.event() for _ in range(4))
        metadata,grand_metadata=self.directory/'tree.json',self.directory/'grandchild.json'
        args=('-B','-I','-c',TREE,str(BASE),CHILD,ready.name,release.name,grand_ready.name,
              grand_release.name,str(metadata),str(grand_metadata),str(root_code))
        owned=self.launch(args)
        ready.wait();grand_ready.wait()
        saved=json.loads(metadata.read_text(encoding='utf-8'))
        selected=self.selected_process(saved['child_pid'],saved['child_creation'])
        member=W.BOOL()
        self.assertTrue(self.api.IsProcessInJob(selected,owned._job,C.byref(member)))
        self.assertTrue(member.value)
        self.members(owned,{owned.pid:owned.creation_time,saved['child_pid']:saved['child_creation']})
        return owned,release,selected

    def test_real_readiness_release_exit_and_image_identity(self):
        owned,release,metadata=self.simple(7,('a space','"quoted"','backslash\\','Unicode-\u03a9',''))
        self.assertEqual(owned.pid,metadata['pid'])
        self.assertEqual(owned.creation_time,metadata['creation'])
        self.assertEqual(owned.image_sha256,hashlib.sha256(BASE.read_bytes()).hexdigest())
        self.assertEqual(metadata['argv'],['a space','"quoted"','backslash\\','Unicode-\u03a9',''])
        self.assertIsNone(owned.poll())
        self.assertFalse(owned.wait(0))
        release.signal()
        self.assertTrue(owned.wait(8))
        self.assertEqual(owned.poll(),7)
        self.assertFalse(owned.termination_requested)

    def test_exit_259_is_not_mistaken_for_still_active(self):
        owned,release,_=self.simple(259)
        release.signal()
        self.assertTrue(owned.wait(8))
        self.assertEqual(owned.poll(),259)

    def test_close_rejects_live_primary_without_losing_ownership(self):
        owned,release,_=self.simple()
        self.assertFalse(owned.lifetime_closed)
        with self.assertRaisesRegex(ContractError,'WINDOWS_OWNED_LIFETIME_UNRESOLVED'):
            owned.close()
        self.assertFalse(owned.lifetime_closed)
        self.assertIsNone(owned.poll())
        self.members(owned,{owned.pid:owned.creation_time})
        release.signal()
        self.assertTrue(owned.wait(8))

    def test_owned_child_membership_and_job_termination(self):
        owned,_,child=self.tree()
        owned.terminate(81)
        self.assertTrue(owned.termination_requested)
        self.assertTrue(owned.wait(8))
        self.assertEqual(self.api.WaitForSingleObject(child,8000),0)
        self.until(lambda:owned.active_process_count()==0)
        self.assertEqual(owned.poll(),81)

    def test_primary_exit_does_not_authorize_closing_live_descendant(self):
        owned,release,child=self.tree(9)
        release.signal()
        self.assertTrue(owned.wait(8))
        self.assertEqual(owned.poll(),9)
        self.assertEqual(self.api.WaitForSingleObject(child,0),258)
        with self.assertRaisesRegex(ContractError,'WINDOWS_OWNED_LIFETIME_UNRESOLVED'):
            owned.close()
        owned.terminate(82)
        self.assertEqual(self.api.WaitForSingleObject(child,8000),0)
        self.until(lambda:owned.active_process_count()==0)

    def test_disposable_parent_crash_kills_owned_child(self):
        child_ready,child_release,parent_ready,parent_release=(self.event() for _ in range(4))
        metadata,child_metadata=self.directory/'parent.json',self.directory/'child.json'
        args=[str(BASE),'-B','-I','-c',PARENT,str(ROOT/'src'),str(ROOT/'.venv/Lib/site-packages'),str(BASE),
              CHILD,child_ready.name,child_release.name,str(child_metadata),parent_ready.name,parent_release.name,
              str(metadata),str(self.directory)]
        parent=subprocess.Popen(args,cwd=self.directory,env=self.environment,creationflags=0x08000000)
        self.foreign.append(parent)
        parent_ready.wait();child_ready.wait()
        saved=json.loads(metadata.read_text(encoding='utf-8'))
        selected=self.selected_process(saved['pid'],saved['creation'])
        self.assertEqual(self.api.WaitForSingleObject(selected,0),258)
        parent_release.signal()
        self.assertEqual(parent.wait(timeout=8),23)
        self.assertEqual(self.api.WaitForSingleObject(selected,8000),0)

    def test_same_executable_foreign_process_is_preserved(self):
        foreign_ready,foreign_release=self.event(),self.event()
        foreign_metadata=self.directory/'foreign.json'
        foreign=subprocess.Popen([str(BASE),'-B','-I','-c',CHILD,foreign_ready.name,foreign_release.name,
                                  str(foreign_metadata),'0'],cwd=self.directory,env=self.environment,creationflags=0x08000000)
        self.foreign.append(foreign)
        foreign_ready.wait()
        owned,_,_=self.simple()
        member=W.BOOL()
        self.assertTrue(self.api.IsProcessInJob(int(foreign._handle),owned._job,C.byref(member)))
        self.assertFalse(member.value)
        owned.terminate(83)
        self.assertTrue(owned.wait(8))
        self.assertIsNone(foreign.poll())
        foreign_release.signal()
        self.assertEqual(foreign.wait(timeout=8),0)

    def test_explicit_standard_handle_list_environment_and_no_job_inheritance(self):
        read,write=W.HANDLE(),W.HANDLE()
        self.assertTrue(self.api.CreatePipe(C.byref(read),C.byref(write),None,0))
        self.handles.append(read.value)
        self.assertTrue(self.api.SetHandleInformation(write,1,1))
        null=self.api.CreateFileW('NUL',0x80000000|0x40000000,3,None,3,0x80,None)
        self.assertNotIn(null,(None,0,C.c_void_p(-1).value))
        self.handles.append(null)
        self.assertTrue(self.api.SetHandleInformation(null,1,1))
        ready,release=self.event(),self.event()
        job_metadata=self.directory/'actual-parent-job.json'
        code=HELPERS+r'''
k.GetStdHandle.argtypes=[W.DWORD];k.GetStdHandle.restype=W.HANDLE
k.QueryInformationJobObject.argtypes=[W.HANDLE,C.c_int,C.c_void_p,W.DWORD,C.c_void_p];k.QueryInformationJobObject.restype=W.BOOL
out={'stdin':int(k.GetStdHandle(-10)),'stdout':int(k.GetStdHandle(-11)),'stderr':int(k.GetStdHandle(-12)),
     'env':os.environ.get('CETA_JOB_ENV'),'unselected':os.environ.get('CETA_UNSELECTED_JOB_ENV')}
buffer=C.create_string_buffer(48)
signal(sys.argv[1]);wait(sys.argv[2])
job=json.loads(pathlib.Path(sys.argv[3]).read_text(encoding='utf-8'))['job']
out['inherited_parent_job']=bool(k.QueryInformationJobObject(job,1,buffer,48,None))
os.write(1,json.dumps(out).encode('utf-8'))
'''
        old=os.environ.get('CETA_UNSELECTED_JOB_ENV')
        os.environ['CETA_UNSELECTED_JOB_ENV']='must-not-cross'
        try:
            owned=self.launch(('-B','-I','-c',code,ready.name,release.name,str(job_metadata)),inherited_handles=(write.value,),
                              standard_handles=(null,write.value,write.value))
        finally:
            if old is None: os.environ.pop('CETA_UNSELECTED_JOB_ENV',None)
            else: os.environ['CETA_UNSELECTED_JOB_ENV']=old
            self.api.close(write.value)
        ready.wait()
        job_metadata.write_text(json.dumps({'job':owned._job}),encoding='utf-8')
        release.signal()
        self.assertTrue(owned.wait(8))
        self.assertEqual(owned.poll(),0)
        flags=DWORD()
        self.assertTrue(self.api.GetHandleInformation(owned._job,C.byref(flags)))
        self.assertEqual(flags.value&1,0)
        buffer,count=C.create_string_buffer(4096),DWORD()
        self.assertTrue(self.api.ReadFile(read,buffer,len(buffer),C.byref(count),None))
        saved=json.loads(buffer.raw[:count.value])
        self.assertEqual((saved['stdin'],saved['stdout'],saved['stderr']),(null,write.value,write.value))
        self.assertEqual(saved['env'],'explicit')
        self.assertIsNone(saved['unselected'])
        self.assertFalse(saved['inherited_parent_job'])

    def test_noninheritable_selected_handle_denied_before_launch(self):
        event=self.event()
        with self.assertRaisesRegex(ContractError,'WINDOWS_LAUNCH_CHILD_HANDLE_NOT_INHERITABLE'):
            self.launch(('-B','-I','-c','pass'),inherited_handles=(event.handle,))

    def test_expected_executable_bytes_mismatch_denied(self):
        with self.assertRaisesRegex(ContractError,'WINDOWS_LAUNCH_IMAGE_HASH_MISMATCH'):
            self.launch(('-B','-I','-c','pass'),expected_image_sha256='0'*64)

    def test_invalid_launch_inputs_are_typed_denials(self):
        cases=[{'arguments':['-c','pass']},{'arguments':(True,)},{'arguments':('\x00',)},
               {'environment':{'Path':'a','PATH':'b'}},{'environment':{'BAD=KEY':'v'}},
               {'environment':{'A':'\x00'}},{'inherited_handles':(True,)},
               {'inherited_handles':([],)},{'standard_handles':(1,2)},
               {'expected_image_sha256':'A'*64},{'cwd':'.'}]
        for change in cases:
            with self.subTest(change=repr(change)):
                values={'executable':str(BASE),'arguments':('-B','-I','-c','pass'),
                        'cwd':str(self.directory),'environment':self.environment}
                values.update(change)
                with self.assertRaises(ContractError):
                    WindowsOwnedProcess.launch(**values)

    def test_actual_createprocess_failure_releases_parent_handles(self):
        file=self.directory/'not-an-executable.bin'
        file.write_bytes(b'owned non executable fixture')
        before=DWORD()
        self.assertTrue(self.api.GetProcessHandleCount(self.api.GetCurrentProcess(),C.byref(before)))
        for _ in range(3):
            with self.assertRaisesRegex(ContractError,'WINDOWS_PROCESS_CREATE_FAILED'):
                WindowsOwnedProcess.launch(str(file),(),cwd=str(self.directory),environment=self.environment)
        after=DWORD()
        self.assertTrue(self.api.GetProcessHandleCount(self.api.GetCurrentProcess(),C.byref(after)))
        self.assertEqual(before.value,after.value)

    def test_resume_failure_cleans_real_suspended_owned_process(self):
        api=_API()
        real_create=api.CreateProcessW
        observed=[]
        def capture(*arguments):
            result=real_create(*arguments)
            if result:
                # Capture the exact created lifetime before cleanup, no PID lookup.
                from ceta.supervisor.windows_jobs import PROCESS_INFORMATION
                info=C.cast(arguments[-1],C.POINTER(PROCESS_INFORMATION)).contents
                retained=W.HANDLE()
                process=api.GetCurrentProcess()
                self.assertTrue(api.DuplicateHandle(process,info.process,process,C.byref(retained),0,False,2))
                observed.append(retained.value)
                self.handles.append(retained.value)
            return result
        api.CreateProcessW=capture
        api.ResumeThread=lambda handle:0xFFFFFFFF  # Owned instance fault before execution.
        sentinel=self.directory/'must-not-execute'
        with patch('ceta.supervisor.windows_jobs._API',return_value=api):
            with self.assertRaisesRegex(ContractError,'WINDOWS_PROCESS_RESUME_FAILED'):
                self.launch(('-B','-I','-c','from pathlib import Path;Path('+repr(str(sentinel))+').write_text("executed")'))
        self.assertEqual(len(observed),1)
        self.assertEqual(api.WaitForSingleObject(observed[0],0),0)
        self.assertFalse(sentinel.exists())

    def test_terminate_remains_available_during_real_process_wait(self):
        owned,_,_=self.simple()
        entered=threading.Event()
        native_wait=owned._api.WaitForSingleObject
        result=[]
        def observed_wait(handle,timeout):
            if timeout==10000: entered.set()
            return native_wait(handle,timeout)
        owned._api.WaitForSingleObject=observed_wait
        worker=threading.Thread(target=lambda:result.append(owned.wait(10)))
        worker.start()
        try:
            self.assertTrue(entered.wait(5))
            owned.terminate(84)
            worker.join(5)
            self.assertFalse(worker.is_alive())
            self.assertEqual(result,[True])
        finally:
            if worker.is_alive():
                owned.terminate(126)
                worker.join(11)
            owned._api.WaitForSingleObject=native_wait
        self.assertFalse(worker.is_alive())

    def test_post_resume_finalization_error_retains_real_live_owner(self):
        api=_API()
        real_open,real_close=api.CreateFileW,api.close
        opened=[]
        failed=[False]
        def capture(*arguments):
            handle=real_open(*arguments)
            opened.append(handle)
            return handle
        def closing(handle):
            if opened and handle==opened[0] and not failed[0]:
                failed[0]=True
                raise ContractError('OWNED_FIXTURE_CLOSE_FAILED')
            return real_close(handle)
        api.CreateFileW,api.close=capture,closing
        ready,release=self.event(),self.event()
        metadata=self.directory/'retained-live-owner.json'
        with patch('ceta.supervisor.windows_jobs._API',return_value=api):
            with self.assertRaisesRegex(WindowsLaunchError,'WINDOWS_LAUNCH_FINALIZATION_UNRESOLVED') as caught:
                self.launch(('-B','-I','-c',CHILD,ready.name,release.name,str(metadata),'0'))
        owned=caught.exception.owned_process
        self.assertIsNotNone(owned)
        self.owned.append(owned)
        ready.wait()
        self.assertIsNone(owned.poll())
        self.assertFalse(owned.lifetime_closed)
        with self.assertRaisesRegex(ContractError,'WINDOWS_OWNED_LIFETIME_UNRESOLVED'):
            caught.exception.close_cleanup()
        owned.terminate(85)
        self.assertTrue(owned.wait(8))
        self.until(lambda:owned.active_process_count()==0)
        caught.exception.close_cleanup()
        self.assertTrue(owned.lifetime_closed)
        self.owned.remove(owned)
        self.assertTrue(failed[0])

    def test_failed_resume_retains_closed_lifetime_and_retryable_image_cleanup(self):
        api=_API()
        real_create,real_open,real_close=api.CreateProcessW,api.CreateFileW,api.close
        observed,opened,failed=[],[],[False]
        def creating(*arguments):
            result=real_create(*arguments)
            if result:
                from ceta.supervisor.windows_jobs import PROCESS_INFORMATION
                info=C.cast(arguments[-1],C.POINTER(PROCESS_INFORMATION)).contents
                retained=W.HANDLE()
                process=api.GetCurrentProcess()
                self.assertTrue(api.DuplicateHandle(process,info.process,process,C.byref(retained),0,False,2))
                observed.append(retained.value)
                self.handles.append(retained.value)
            return result
        def opening(*arguments):
            handle=real_open(*arguments)
            opened.append(handle)
            return handle
        def closing(handle):
            if opened and handle==opened[0] and not failed[0]:
                failed[0]=True
                raise ContractError('OWNED_FIXTURE_IMAGE_CLOSE_FAILED')
            return real_close(handle)
        api.CreateProcessW,api.CreateFileW,api.close=creating,opening,closing
        api.ResumeThread=lambda handle:0xFFFFFFFF
        sentinel=self.directory/'closed-owner-must-not-execute'
        with patch('ceta.supervisor.windows_jobs._API',return_value=api):
            with self.assertRaisesRegex(WindowsLaunchError,'WINDOWS_LAUNCH_FINALIZATION_UNRESOLVED') as caught:
                self.launch(('-B','-I','-c','from pathlib import Path;Path('+repr(str(sentinel))+').write_text("executed")'))
        owned=caught.exception.owned_process
        self.assertIsNotNone(owned)
        try:
            self.assertEqual(len(observed),1)
            self.assertEqual(api.WaitForSingleObject(observed[0],0),0)
            code=DWORD()
            self.assertTrue(api.GetExitCodeProcess(observed[0],C.byref(code)))
            self.assertEqual(code.value,125)
            self.assertFalse(sentinel.exists())
            self.assertTrue(failed[0])
            self.assertTrue(owned.lifetime_closed)
            with self.assertRaises(AttributeError):
                owned.lifetime_closed=False
            with self.assertRaisesRegex(ContractError,'WINDOWS_OWNED_PROCESS_CLOSED'):
                owned.poll()
            flags=DWORD()
            self.assertTrue(api.GetHandleInformation(opened[0],C.byref(flags)))
            self.assertEqual(owned._cleanup_handles,[opened[0]])
            caught.exception.close_cleanup()
            self.assertTrue(owned.lifetime_closed)
            self.assertEqual(owned._cleanup_handles,[])
            self.assertFalse(api.GetHandleInformation(opened[0],C.byref(flags)))
            self.assertEqual(C.get_last_error(),6)
            caught.exception.close_cleanup()
        finally:
            api.close=real_close
            if not owned.lifetime_closed:
                owned.terminate(126)
                self.assertTrue(owned.wait(5))
                self.until(lambda:owned.active_process_count()==0)
            caught.exception.close_cleanup()

    def test_partial_close_error_can_retry_after_observed_exit(self):
        owned,release,_=self.simple()
        release.signal()
        self.assertTrue(owned.wait(8))
        self.until(lambda:owned.active_process_count()==0)
        real_close=owned._api.close
        failed=[False]
        def closing(handle):
            if handle==owned._job and not failed[0]:
                failed[0]=True
                raise ContractError('OWNED_FIXTURE_JOB_CLOSE_FAILED')
            return real_close(handle)
        owned._api.close=closing
        with self.assertRaisesRegex(ContractError,'OWNED_FIXTURE_JOB_CLOSE_FAILED'):
            owned.close()
        self.assertEqual(owned.poll(),7)
        self.assertEqual(owned.active_process_count(),0)
        owned.close()
        owned.close()
        self.owned.remove(owned)
        self.assertTrue(failed[0])

    def test_strict_wait_and_termination_bounds(self):
        owned,release,_=self.simple()
        for value in (True,-1,float('inf'),float('nan'),86401,1<<10000):
            with self.subTest(value=type(value).__name__):
                with self.assertRaisesRegex(ContractError,'WINDOWS_PROCESS_TIMEOUT_REQUIRED'):
                    owned.wait(value)
        for value in (True,-1,1<<32,'1'):
            with self.assertRaisesRegex(ContractError,'WINDOWS_TERMINATION_CODE_REQUIRED'):
                owned.terminate(value)
        self.assertFalse(owned.termination_requested)
        release.signal()
        self.assertTrue(owned.wait(8))


if __name__=='__main__':
    unittest.main()
