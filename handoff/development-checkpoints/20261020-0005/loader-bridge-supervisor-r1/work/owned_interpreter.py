"""Read-only interpreter identity inside one retained canonical own job.

No native constructor, lookup or call occurs at import. NativePort uses only the
explicit held job and query/synchronize handles for its enumerated members.
"""
import ctypes as C
from ctypes import wintypes as WT
from pathlib import Path
import os
import struct

MAX_MEMBERS=64
QUERY_SYNCHRONIZE=0x101000


class IdentityError(RuntimeError):pass


def require(value,reason):
    if not value:raise IdentityError(reason)


def norm(path):return os.path.normcase(str(Path(path)))


def parse_members(raw,returned):
    require(type(raw) is bytes and type(returned) is int and 8<=returned<=len(raw)<=8+8*MAX_MEMBERS,
            'OWNED_JOB_LIST_SHORT_OR_UNBOUNDED')
    assigned,listed=struct.unpack_from('<II',raw)
    require(0<assigned==listed<=MAX_MEMBERS and returned>=8+listed*8,'OWNED_JOB_LIST_TRUNCATED')
    ids=struct.unpack_from('<'+'Q'*listed,raw,8)
    require(len(set(ids))==listed and all(0<pid<=0xffffffff for pid in ids),'OWNED_JOB_LIST_IDS_INVALID')
    return ids


def validate_hello(hello,launch_argv,redirector_pin,base_pin):
    require(type(hello) is dict and type(hello.get('pid')) is int and 0<hello['pid']<=0xffffffff,
            'OWNED_INTERPRETER_HELLO_PID')
    require(norm(hello.get('sys_executable',''))==norm(redirector_pin['path'])
            and norm(hello.get('base_executable',''))==norm(base_pin['path']),'OWNED_INTERPRETER_EXECUTABLE_MISMATCH')
    argv=hello.get('argv')
    require(type(argv) is list and all(type(x) is str for x in argv) and len(argv)==len(launch_argv)
            and norm(argv[0])==norm(base_pin['path']) and argv[1:]==list(launch_argv[1:]),
            'OWNED_INTERPRETER_ARGV_MISMATCH')


class Selection:
    """Port orchestration; synthetic ports in controls never establish native proof."""
    def __init__(self,port):
        self.port=port;self.selected=None;self.observation=None;self.retirement=None;self.finished=False;self.attempted=False

    def qualify(self,hello,launch_argv,redirector_pin,base_pin):
        require(not self.attempted and not self.finished,'OWNED_INTERPRETER_ONE_SELECTION');self.attempted=True
        validate_hello(hello,launch_argv,redirector_pin,base_pin)
        ids=self.port.members()
        require(hello['pid'] in ids,'OWNED_INTERPRETER_NOT_ENUMERATED')
        matches=[]
        for pid in ids:
            row=self.port.open_member(pid)
            keep=False;primary=None
            try:
                # Membership is the first observation on every newly opened
                # query handle. No image/time read precedes this exact check.
                require(self.port.member(row),'OWNED_INTERPRETER_NONMEMBER_OR_REUSED_PID')
                observed=self.port.observe(row)
                require(type(observed['pid']) is int and observed['pid']==pid
                        and type(observed['creation_time']) is int
                        and 0<self.port.root_creation<=observed['creation_time']<=0xffffffffffffffff,
                        'OWNED_INTERPRETER_PID_OR_CREATION_CHANGED')
                require(self.port.member(row),'OWNED_INTERPRETER_LEFT_HELD_JOB')
                if norm(observed['image_path'])==norm(base_pin['path']):
                    require(observed['image_sha256']==base_pin['sha256'],'OWNED_INTERPRETER_IMAGE_BYTES_CHANGED')
                    require(self.port.alive(row),'OWNED_INTERPRETER_ALREADY_EXITED')
                    matches.append((row,observed));keep=True
                elif norm(observed['image_path'])==norm(redirector_pin['path']):
                    require(observed['image_sha256']==redirector_pin['sha256'],'OWNED_REDIRECTOR_IMAGE_BYTES_CHANGED')
                else:raise IdentityError('OWNED_JOB_UNEXPECTED_PRE_BRIDGE_IMAGE')
            except BaseException as error:primary=error;raise
            finally:
                if not keep:
                    try:self.port.close_once(row)
                    except BaseException as cleanup:
                        if primary is None:raise
                        dict.__setitem__(BaseException.__dict__['__dict__'].__get__(primary),
                                         'owned_interpreter_cleanup_error',cleanup)
        if len(matches)!=1 or matches[0][1]['pid']!=hello['pid']:
            primary=IdentityError('OWNED_INTERPRETER_AMBIGUOUS_OR_HELLO_MISMATCH');cleanup_errors=[]
            for row,_ in matches:
                try:self.port.close_once(row)
                except BaseException as cleanup:cleanup_errors.append(cleanup)
            if cleanup_errors:
                dict.__setitem__(BaseException.__dict__['__dict__'].__get__(primary),
                                 'owned_interpreter_cleanup_errors',tuple(cleanup_errors))
            raise primary
        self.selected,self.observation=matches[0]
        return dict(self.observation,reported_argv=list(hello['argv']),launch_argv=list(launch_argv),
                    sys_executable=hello['sys_executable'],base_executable=hello['base_executable'],
                    member_of_exact_retained_job=True,rights=QUERY_SYNCHRONIZE)

    def snapshot(self):
        return dict(selection_attempted=self.attempted,retirement_attempted=self.finished,
                    selected=self.observation,retirement=self.retirement,
                    query_custody=[dict(pid=row['pid'],state=row['state'],handle_obtained=row['handle'] is not None)
                                   for row in self.port.rows],automatic_retry=False)

    def retire_once(self):
        require(not self.finished,'OWNED_INTERPRETER_RETIRE_NO_RETRY');self.finished=True
        # Includes every independently known query handle from a failed
        # selection. Unknown closes are deliberately never replayed.
        primary=None;cleanup_errors=[]
        try:
            if self.selected is not None:
                status=self.port.exited(self.selected)
                require(status['creation_time']==self.observation['creation_time']
                        and status['pid']==self.observation['pid'],'OWNED_INTERPRETER_EXIT_IDENTITY_CHANGED')
                self.retirement=dict(status,physical_exit_observed=True)
        except BaseException as error:primary=error
        for row in tuple(self.port.rows):
            if row['state']=='OWNED':
                try:self.port.close_once(row)
                except BaseException as error:
                    cleanup_errors.append(error)
                    if primary is None:primary=error
        if any(row['state']!='CLOSED' for row in self.port.rows) and primary is None:
            primary=IdentityError('OWNED_INTERPRETER_QUERY_CUSTODY_UNCERTAIN')
        if primary is not None:
            details=BaseException.__dict__['__dict__'].__get__(primary)
            dict.__setitem__(details,'owned_interpreter_custody',self)
            dict.__setitem__(details,'owned_interpreter_cleanup_errors',tuple(cleanup_errors))
            raise primary
        return dict(selected=self.observation,retirement=self.retirement,all_query_handles_closed=True,
                    physical_interpreter_exit=self.retirement is not None,automatic_retry=False)


class NativePort:
    """Existing canonical owner/API plus one local query-only OpenProcess binding."""
    def __init__(self,jobs,owner,expected_pins):
        require(type(owner) is jobs.WindowsOwnedProcess and not owner.lifetime_closed and owner._job is not None,
                'OWNED_JOB_LIVE_CANONICAL_OWNER_REQUIRED')
        require(C.sizeof(C.c_void_p)==8 and C.sizeof(WT.DWORD)==4,'OWNED_JOB_X64_LAYOUT_REQUIRED')
        self.jobs,self.owner,self.api=jobs,owner,owner._api
        self.job=owner._job;self.root_creation=owner.creation_time;self.rows=[];self.expected_pins=expected_pins
        self.member_ids=None
        self.OpenProcess=self.api.dll.OpenProcess
        self.OpenProcess.argtypes=[WT.DWORD,WT.BOOL,WT.DWORD];self.OpenProcess.restype=jobs.HANDLE

    def current_job(self):
        require(not self.owner.lifetime_closed and self.owner._job==self.job and self.job is not None,
                'OWNED_JOB_HANDLE_CHANGED')

    def members(self):
        with self.owner._lock:
            self.current_job();storage=C.create_string_buffer(8+8*MAX_MEMBERS);returned=WT.DWORD()
            require(self.api.QueryInformationJobObject(self.job,3,storage,len(storage),C.byref(returned)),
                    'OWNED_JOB_QUERY_FAILED_OR_MORE_DATA')
            self.member_ids=parse_members(bytes(storage.raw),int(returned.value));return self.member_ids

    def open_member(self,pid):
        # Selection supplies only a member from this exact completed enumeration.
        require(type(pid) is int and self.member_ids is not None and pid in self.member_ids,
                'OWNED_PROCESS_NOT_IN_BOUNDED_JOB_LIST')
        row=dict(pid=pid,handle=None,state='OPEN_IN_FLIGHT');self.rows.append(row)
        try:row['handle']=self.OpenProcess(QUERY_SYNCHRONIZE,False,pid)
        except BaseException:row['state']='OPEN_UNCERTAIN';raise
        if not row['handle']:
            row['state']='CLOSED';raise IdentityError('OWNED_MEMBER_QUERY_OPEN_FAILED')
        row['state']='OWNED';return row

    def member(self,row):
        with self.owner._lock:
            self.current_job();inside=WT.BOOL()
            require(self.api.IsProcessInJob(row['handle'],self.job,C.byref(inside)),
                    'OWNED_MEMBER_MEMBERSHIP_QUERY_FAILED')
            return bool(inside.value)

    def creation(self,row):
        times=[WT.FILETIME() for _ in range(4)]
        require(self.api.GetProcessTimes(row['handle'],*(C.byref(t) for t in times)),
                'OWNED_MEMBER_TIMES_UNAVAILABLE')
        return times[0].dwHighDateTime<<32|times[0].dwLowDateTime

    def observe(self,row):
        pid=int(self.api.GetProcessId(row['handle']))
        require(pid==row['pid'],'OWNED_MEMBER_HANDLE_PID_CHANGED')
        creation=self.creation(row);name=C.create_unicode_buffer(32768);length=WT.DWORD(len(name))
        require(self.api.QueryFullProcessImageNameW(row['handle'],0,name,C.byref(length))
                and 0<length.value<len(name) and len(name.value)==length.value,'OWNED_MEMBER_IMAGE_QUERY_SHORT')
        path=name.value
        expected=next((p for p in self.expected_pins if norm(p['path'])==norm(path)),None)
        require(expected is not None,'OWNED_JOB_UNEXPECTED_IMAGE_PATH')
        image=dict(pid=pid,handle=None,state='IMAGE_OPEN_IN_FLIGHT');self.rows.append(image)
        try:image['handle']=self.jobs._open_image(self.api,path)
        except BaseException:image['state']='OPEN_UNCERTAIN';raise
        image['state']='OWNED'
        primary=None
        try:
            identity=self.jobs._file_identity(self.api,image['handle'])
            require((identity[3]<<32|identity[4])==expected['bytes']<=16*1024*1024,'OWNED_IMAGE_SIZE_CHANGED')
            pin,identity=self.jobs._hash_image(self.api,image['handle'])
            require(pin==expected['sha256'],'OWNED_IMAGE_HASH_CHANGED')
        except BaseException as error:primary=error;raise
        finally:
            try:self.close_once(image)
            except BaseException as cleanup:
                if primary is None:raise
                dict.__setitem__(BaseException.__dict__['__dict__'].__get__(primary),
                                 'owned_interpreter_image_cleanup_error',cleanup)
        require(self.creation(row)==creation and int(self.api.GetProcessId(row['handle']))==pid,
                'OWNED_MEMBER_CREATION_CHANGED_DURING_QUERY')
        return dict(pid=pid,creation_time=creation,image_path=path,image_sha256=pin,
                    physical_image_identity=list(identity))

    def alive(self,row):return self.api.WaitForSingleObject(row['handle'],0)==258

    def exited(self,row):
        require(self.api.WaitForSingleObject(row['handle'],5000)==0,'OWNED_INTERPRETER_PHYSICAL_EXIT_PENDING')
        creation=self.creation(row);pid=int(self.api.GetProcessId(row['handle']));code=WT.DWORD()
        require(self.api.GetExitCodeProcess(row['handle'],C.byref(code)),'OWNED_INTERPRETER_EXIT_CODE_UNAVAILABLE')
        return dict(pid=pid,creation_time=creation,exit_status=int(code.value))

    def close_once(self,row):
        require(row['state']=='OWNED','OWNED_QUERY_CLOSE_UNKNOWN_NO_RETRY')
        row['state']='CLOSE_IN_FLIGHT'
        try:require(self.api.CloseHandle(row['handle']),'OWNED_QUERY_CLOSE_FAILED')
        except BaseException:row['state']='CLOSE_UNCERTAIN';raise
        row['state']='CLOSED';row['handle']=None
