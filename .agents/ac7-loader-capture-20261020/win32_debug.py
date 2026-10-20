"""Documented x64 Win32 debug events for a child created by this thread.

Only open_functions() loads Kernel32, and callers must validate a live Root
release before calling it. There is no attach, remote write, registry or profile
API in this module. DbgEng package availability is separate recorded metadata.
"""
from pathlib import Path
import ctypes as C
import hashlib
import os
import threading
from capture_core import (CaptureError, Event, require, CREATE_PROCESS, LOAD_DLL,
                          CREATE_THREAD, EXIT_THREAD, EXIT_PROCESS, EXCEPTION,
                          OUTPUT_DEBUG_STRING, UNLOAD_DLL, RIP, DBG_CONTINUE,
                          DBG_EXCEPTION_NOT_HANDLED, OwnedIdentity)

DWORD=C.c_uint32
WORD=C.c_uint16
HANDLE=C.c_void_p
SIZE_T=C.c_size_t
UINT_PTR=C.c_uint64
BOOL=C.c_int32


class FILETIME(C.Structure):
    _fields_=[('low',DWORD),('high',DWORD)]


class FILE_INFORMATION(C.Structure):
    _fields_=[('attributes',DWORD),('created',FILETIME),('accessed',FILETIME),
              ('written',FILETIME),('volume',DWORD),('size_high',DWORD),
              ('size_low',DWORD),('links',DWORD),('index_high',DWORD),('index_low',DWORD)]


class EXCEPTION_RECORD(C.Structure):
    _fields_=[('code',DWORD),('flags',DWORD),('record',HANDLE),('address',HANDLE),
              ('number',DWORD),('information',UINT_PTR*15)]


class EXCEPTION_INFO(C.Structure):
    _fields_=[('record',EXCEPTION_RECORD),('first_chance',DWORD)]


class CREATE_PROCESS_INFO(C.Structure):
    _fields_=[('file',HANDLE),('process',HANDLE),('thread',HANDLE),('base',HANDLE),
              ('debug_offset',DWORD),('debug_size',DWORD),('tls',HANDLE),
              ('start',HANDLE),('image_name',HANDLE),('unicode',WORD)]


class CREATE_THREAD_INFO(C.Structure):
    _fields_=[('thread',HANDLE),('tls',HANDLE),('start',HANDLE)]


class LOAD_DLL_INFO(C.Structure):
    _fields_=[('file',HANDLE),('base',HANDLE),('debug_offset',DWORD),
              ('debug_size',DWORD),('image_name',HANDLE),('unicode',WORD)]


class EXIT_INFO(C.Structure):
    _fields_=[('code',DWORD)]


class UNLOAD_INFO(C.Structure):
    _fields_=[('base',HANDLE)]


class STRING_INFO(C.Structure):
    _fields_=[('address',HANDLE),('unicode',WORD),('length',WORD)]


class RIP_INFO(C.Structure):
    _fields_=[('error',DWORD),('kind',DWORD)]


class DEBUG_UNION(C.Union):
    _fields_=[('exception',EXCEPTION_INFO),('create_thread',CREATE_THREAD_INFO),
              ('create_process',CREATE_PROCESS_INFO),('exit_thread',EXIT_INFO),
              ('exit_process',EXIT_INFO),('load',LOAD_DLL_INFO),('unload',UNLOAD_INFO),
              ('string',STRING_INFO),('rip',RIP_INFO)]


class DEBUG_EVENT(C.Structure):
    _fields_=[('code',DWORD),('pid',DWORD),('tid',DWORD),('info',DEBUG_UNION)]


def require_abi():
    require(C.sizeof(HANDLE)==8 and C.sizeof(DEBUG_EVENT)==176 and DEBUG_EVENT.info.offset==16,
            'CAPTURE_X64_DEBUG_ABI_REQUIRED')
    require(C.sizeof(EXCEPTION_RECORD)==152 and C.sizeof(CREATE_PROCESS_INFO)==72
            and C.sizeof(LOAD_DLL_INFO)==40 and C.sizeof(STRING_INFO)==16,
            'CAPTURE_DEBUG_STRUCT_LAYOUT_MISMATCH')


def file_pin(path):
    path=Path(path)
    before=path.stat()
    require(path.is_absolute() and path.is_file() and not path.is_symlink() and not path.is_junction(),
            'CAPTURE_NATIVE_DEPENDENCY_INVALID')
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1_048_576),b''):digest.update(block)
    after=path.stat()
    identity=lambda row:(row.st_dev,row.st_ino,row.st_size,row.st_mtime_ns)
    require(identity(before)==identity(after),'CAPTURE_NATIVE_DEPENDENCY_CHANGED')
    return dict(path=str(path),bytes=before.st_size,sha256=digest.hexdigest(),
                device=before.st_dev,inode=before.st_ino,mtime_ns=before.st_mtime_ns)


def open_functions(pins):
    """Instantiate only after the adapter's release/input admission succeeds."""
    require(os.name=='nt','CAPTURE_WINDOWS_REQUIRED')
    require_abi()
    require(type(pins) is dict and set(pins)=={'kernel32','kernelbase','ntdll'},
            'CAPTURE_SYSTEM_LIBRARY_PINS_REQUIRED')
    for row in pins.values():require(file_pin(row['path'])==row,'CAPTURE_SYSTEM_LIBRARY_CHANGED')
    expected=Path(os.environ['SystemRoot'])/'System32/kernel32.dll'
    require(Path(pins['kernel32']['path'])==expected,'CAPTURE_SYSTEM32_KERNEL_REQUIRED')
    dll=C.WinDLL(str(expected),use_last_error=True,winmode=0x800)
    functions=dict(
        WaitForDebugEventEx=([C.POINTER(DEBUG_EVENT),DWORD],BOOL),
        ContinueDebugEvent=([DWORD,DWORD,DWORD],BOOL),
        CloseHandle=([HANDLE],BOOL),
        GetProcessId=([HANDLE],DWORD),
        GetProcessTimes=([HANDLE,*[C.POINTER(FILETIME)]*4],BOOL),
        GetFileInformationByHandle=([HANDLE,C.POINTER(FILE_INFORMATION)],BOOL),
        GetFinalPathNameByHandleW=([HANDLE,C.c_wchar_p,DWORD,DWORD],DWORD),
        GetModuleFileNameW=([HANDLE,C.c_wchar_p,DWORD],DWORD),
        GetHandleInformation=([HANDLE,C.POINTER(DWORD)],BOOL),
        GetFileType=([HANDLE],DWORD),
        ReadProcessMemory=([HANDLE,HANDLE,HANDLE,SIZE_T,C.POINTER(SIZE_T)],BOOL),
        PeekNamedPipe=([HANDLE,HANDLE,DWORD,C.POINTER(DWORD),C.POINTER(DWORD),C.POINTER(DWORD)],BOOL),
        ReadFile=([HANDLE,HANDLE,DWORD,C.POINTER(DWORD),HANDLE],BOOL))
    for name,(args,result) in functions.items():
        function=getattr(dll,name);function.argtypes=args;function.restype=result
    path=C.create_unicode_buffer(32768)
    length=dll.GetModuleFileNameW(HANDLE(dll._handle),path,len(path))
    require(0<length<len(path) and Path(path.value)==expected,'CAPTURE_LOADED_KERNEL_IDENTITY_MISMATCH')
    for row in pins.values():require(file_pin(row['path'])==row,'CAPTURE_SYSTEM_LIBRARY_CHANGED_AFTER_LOAD')
    return dll


def native_error(operation,code):
    error=CaptureError(operation+':'+str(code))
    error.native_operation=operation
    error.winerror=int(code)
    return error


class Win32DebugPort:
    """Preallocated event buffer owns any returned event until explicit continue.

    Python interruption during a native wait/close/continue stays visible as
    IN_FLIGHT. Such a call is never automatically replayed. Debug-created process
    and thread handles are left to Windows; only hFile is explicitly closed.
    """
    def __init__(self,functions,identity,*,stdout_handle=None,stderr_handle=None,
                 thread_id=threading.get_ident,last_error=C.get_last_error):
        require_abi()
        require(type(identity) is OwnedIdentity,'CAPTURE_OWNED_IDENTITY_REQUIRED')
        self.identity=identity
        self.create_seen=False
        self.functions=functions
        self.thread_id=thread_id
        self.creator_thread=thread_id()
        self.last_error=last_error
        self.event=DEBUG_EVENT()
        self.state='IDLE'
        self.file_state='NONE'
        self.file_handle=None
        self.debug_process=None
        self.exit_continued=False
        self.pipes=(stdout_handle,stderr_handle)
        self.pipe_eof=[stdout_handle is None,stderr_handle is None]
        self.borrowed_pipe_facts=[]
        for handle in self.pipes:
            if handle is None:continue
            require(type(handle) is int and 0<handle<(1<<64)-1,'CAPTURE_PIPE_HANDLE_INVALID')
            flags=DWORD()
            require(functions.GetFileType(HANDLE(handle))==3 and
                    functions.GetHandleInformation(HANDLE(handle),C.byref(flags)) and not flags.value&1,
                    'CAPTURE_BORROWED_PARENT_PIPE_REQUIRED')
            self.borrowed_pipe_facts.append(dict(handle=handle,type='PIPE',inheritable=False,owned=False))

    def _thread(self):
        require(self.thread_id()==self.creator_thread,'CAPTURE_CREATOR_THREAD_REQUIRED')

    def wait(self,milliseconds):
        self._thread()
        require(self.state=='IDLE' and not self.exit_continued,'CAPTURE_PENDING_EVENT_CUSTODY')
        require(type(milliseconds) is int and 0<=milliseconds<=100,'CAPTURE_WAIT_BOUND_INVALID')
        C.memset(C.byref(self.event),0,C.sizeof(self.event))
        self.file_handle=None;self.file_state='NONE';self.state='WAIT_IN_FLIGHT'
        result=self.functions.WaitForDebugEventEx(C.byref(self.event),milliseconds)
        error=self.last_error()
        if not result:
            self.state='IDLE'
            if error in (121,258):return False
            raise native_error('WaitForDebugEventEx',error)
        self.state='EVENT'
        if self.event.code==CREATE_PROCESS:self.file_handle=self.event.info.create_process.file
        elif self.event.code==LOAD_DLL:self.file_handle=self.event.info.load.file
        if self.file_handle:self.file_state='OWNED'
        return True

    def _module(self,handle):
        if not handle:return dict(state='UNAVAILABLE',reason='NATIVE_EVENT_FILE_HANDLE_NULL')
        output=dict(state='OBSERVED',file_handle=int(handle))
        info=FILE_INFORMATION()
        if self.functions.GetFileInformationByHandle(HANDLE(handle),C.byref(info)):
            output['identity']=dict(volume=int(info.volume),index=int(info.index_high)<<32|int(info.index_low),
                bytes=int(info.size_high)<<32|int(info.size_low),written=int(info.written.high)<<32|int(info.written.low))
        else:output['identity_error']=self.last_error()
        path=C.create_unicode_buffer(32768)
        count=self.functions.GetFinalPathNameByHandleW(HANDLE(handle),path,len(path),0)
        if 0<count<len(path):output['path']=path.value
        else:output['path_error']=self.last_error();output['path']=None
        return output

    def _debug_string(self,info,limit):
        # Microsoft's documented field is the lower 16 bits of BYTE length.
        requested=int(info.length);amount=min(requested,max(0,limit))
        output=dict(address=int(info.address or 0),unicode=bool(info.unicode),
            reported_length_low16_bytes=requested,full_length_known=False,captured_bytes=0,
            raw_hex='',read_state='NOT_READ',truncated=amount<requested)
        if not info.address or not self.debug_process or amount==0:return output
        storage=C.create_string_buffer(amount);read=SIZE_T()
        result=self.functions.ReadProcessMemory(HANDLE(self.debug_process),HANDLE(info.address),
                                               storage,amount,C.byref(read))
        error=self.last_error()
        require(read.value<=amount,'CAPTURE_NATIVE_READ_COUNT_INVALID')
        raw=storage.raw[:read.value]
        output.update(captured_bytes=len(raw),raw_hex=raw.hex(),
            read_state='COMPLETE_REPORTED_LENGTH' if result and read.value==requested else 'PARTIAL_OR_UNAVAILABLE',
            winerror=None if result else error)
        if info.unicode:
            try:output['utf16le_text']=raw.decode('utf-16-le')
            except UnicodeError:output['utf16le_text']=None
        return output

    def current(self,debug_limit):
        self._thread()
        require(self.state=='EVENT','CAPTURE_NO_CURRENT_EVENT')
        require(type(debug_limit) is int and 0<=debug_limit<=65_535,'CAPTURE_READ_BOUND_INVALID')
        e=self.event;code=int(e.code);data={}
        require(int(e.pid)==self.identity.pid,'CAPTURE_FOREIGN_EVENT_BEFORE_NATIVE_READ')
        require(code==CREATE_PROCESS or self.create_seen,'CAPTURE_CREATE_EVENT_MISSING')
        if code==CREATE_PROCESS:
            require(not self.create_seen,'CAPTURE_DUPLICATE_CREATE_EVENT')
            info=e.info.create_process;self.debug_process=info.process
            times=[FILETIME() for _ in range(4)]
            if not self.functions.GetProcessTimes(HANDLE(info.process),*[C.byref(item) for item in times]):
                raise native_error('GetProcessTimes(debug event handle)',self.last_error())
            pid=int(self.functions.GetProcessId(HANDLE(info.process)))
            creation=int(times[0].high)<<32|int(times[0].low)
            require(pid==self.identity.pid and creation==self.identity.creation_time,'CAPTURE_CREATION_IDENTITY_MISMATCH')
            self.create_seen=True
            data=dict(base=int(info.base or 0),start_address=int(info.start or 0),
                pid_from_handle=pid,creation_time=creation,
                process_handle_ownership='WINDOWS_DEBUG_EVENT',thread_handle_ownership='WINDOWS_DEBUG_EVENT',
                image=self._module(info.file))
        elif code==LOAD_DLL:
            info=e.info.load;data=dict(base=int(info.base or 0),image=self._module(info.file))
        elif code==UNLOAD_DLL:data=dict(base=int(e.info.unload.base or 0))
        elif code==CREATE_THREAD:data=dict(start_address=int(e.info.create_thread.start or 0),thread_handle_ownership='WINDOWS_DEBUG_EVENT')
        elif code in (EXIT_PROCESS,EXIT_THREAD):data=dict(exit_code=int(e.info.exit_process.code if code==EXIT_PROCESS else e.info.exit_thread.code))
        elif code==EXCEPTION:
            info=e.info.exception;require(info.record.number<=15,'CAPTURE_EXCEPTION_PARAMETER_COUNT_INVALID')
            data=dict(exception_code=int(info.record.code),flags=int(info.record.flags),
                address=int(info.record.address or 0),first_chance=bool(info.first_chance),
                parameters=[int(value) for value in info.record.information[:info.record.number]])
        elif code==OUTPUT_DEBUG_STRING:data=self._debug_string(e.info.string,debug_limit)
        elif code==RIP:data=dict(error=int(e.info.rip.error),kind=int(e.info.rip.kind))
        return Event(code,int(e.pid),int(e.tid),data,C.string_at(C.byref(e),C.sizeof(e)))

    def continue_current(self,status):
        self._thread()
        require(self.state=='EVENT','CAPTURE_NO_CURRENT_EVENT')
        require(self.file_state in ('NONE','OWNED','CLOSED'),'CAPTURE_PENDING_FILE_CUSTODY_NO_REPLAY')
        require(status in (DBG_CONTINUE,DBG_EXCEPTION_NOT_HANDLED),'CAPTURE_CONTINUE_STATUS_INVALID')
        if self.file_state=='OWNED':
            self.file_state='CLOSE_IN_FLIGHT'
            result=self.functions.CloseHandle(HANDLE(self.file_handle))
            error=self.last_error()
            if not result:
                self.file_state='CLOSE_FAILED_KNOWN'
                raise native_error('CloseHandle(debug image)',error)
            self.file_state='CLOSED'
            self.file_handle=None
        self.state='CONTINUE_IN_FLIGHT'
        result=self.functions.ContinueDebugEvent(self.event.pid,self.event.tid,status)
        error=self.last_error()
        if not result:
            self.state='CONTINUE_FAILED_KNOWN'
            raise native_error('ContinueDebugEvent',error)
        if self.event.code==EXIT_PROCESS:
            self.exit_continued=True;self.debug_process=None
        self.state='IDLE'

    def read_stdio(self,limit):
        self._thread()
        require(type(limit) is int and 0<limit<=4_194_304,'CAPTURE_STDIO_BOUND_INVALID')
        values=[];remaining=limit
        for position,handle in enumerate(self.pipes):
            if handle is None or self.pipe_eof[position] or remaining==0:
                values.append(b'');continue
            available=DWORD()
            result=self.functions.PeekNamedPipe(HANDLE(handle),None,0,None,C.byref(available),None)
            error=self.last_error()
            if not result:
                if error in (109,232):self.pipe_eof[position]=True;values.append(b'');continue
                raise native_error('PeekNamedPipe',error)
            amount=min(int(available.value),remaining,65_536)
            if not amount:values.append(b'');continue
            storage=C.create_string_buffer(amount);read=DWORD()
            if not self.functions.ReadFile(HANDLE(handle),storage,amount,C.byref(read),None):
                raise native_error('ReadFile(capture pipe)',self.last_error())
            require(read.value<=amount,'CAPTURE_STDIO_READ_COUNT_INVALID')
            raw=storage.raw[:read.value];values.append(raw);remaining-=len(raw)
        return tuple(values)

    def pending(self):
        possible=None
        if self.state=='WAIT_IN_FLIGHT':
            if self.event.code==CREATE_PROCESS:possible=self.event.info.create_process.file
            elif self.event.code==LOAD_DLL:possible=self.event.info.load.file
        return dict(event_state=self.state,event_pid=int(self.event.pid),event_tid=int(self.event.tid),
            file_handle=self.file_handle,file_state=self.file_state,
            possible_file_handle_after_unknown_wait_return=possible,
            event_buffer_hex=C.string_at(C.byref(self.event),C.sizeof(self.event)).hex(),
            debugger_process_handle=self.debug_process,
            debugger_process_handle_owned_by='WINDOWS_UNTIL_EXIT_CONTINUE',
            exit_continued=self.exit_continued,borrowed_pipes=self.borrowed_pipe_facts,pipe_eof=self.pipe_eof,
            automatic_retry=False)
