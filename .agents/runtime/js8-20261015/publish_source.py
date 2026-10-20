"""Dormant exact15-path publisher; retained native originals, no acceptance claim."""
from pathlib import Path
import argparse,ctypes,importlib.util,json,os,sys
from ctypes import wintypes
import js8_support as j
from js8_support import s,F,Q,R
OUT=R/'active-application'

def absent(path):
    s.fs.safe_components(path,allow_missing=True)
    try:s.fs.lstat(path)
    except FileNotFoundError:return
    raise AssertionError('CREATE_ONLY_ENTRY_EXISTS:'+str(path))
def event(stream,value):
    text=json.dumps(value,allow_nan=False)+'\n';count=stream.write(text)
    assert type(count) is int and count==len(text),'SHORT_EVENT_WRITE'
    stream.flush();os.fsync(stream.fileno())
class FileBasic(ctypes.Structure):
    _fields_=[('creation',ctypes.c_longlong),('access',ctypes.c_longlong),
        ('write',ctypes.c_longlong),('change',ctypes.c_longlong),('attributes',wintypes.DWORD)]

class FileStandard(ctypes.Structure):
    _fields_=[('allocation',ctypes.c_longlong),('size',ctypes.c_longlong),('links',wintypes.DWORD),
        ('delete_pending',ctypes.c_ubyte),('directory',ctypes.c_ubyte)]

class FileId(ctypes.Structure):
    _fields_=[('volume',ctypes.c_ulonglong),('file_id',ctypes.c_ubyte*16)]

class OriginalReader:
    """Exact raw-file handle custody; no context manager/CRT ownership transfer.

    Ordinary/file-path/share checks retain P4's boundary. The local read uses
    bounded synchronous ReadFile and measured full volume/file identity. A
    failed/uncertain close is retained and never automatically repeated.
    """
    def __init__(self):
        self.handle=None;self.close_attempted=False;self.closed=False
        self.kernel=ctypes.WinDLL('kernel32.dll',use_last_error=True,winmode=0x800)
        self.kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,
            ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
        self.kernel.CreateFileW.restype=wintypes.HANDLE
        self.kernel.CloseHandle.argtypes=[wintypes.HANDLE];self.kernel.CloseHandle.restype=wintypes.BOOL
        self.kernel.GetFileInformationByHandleEx.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
        self.kernel.GetFileInformationByHandleEx.restype=wintypes.BOOL
        self.kernel.GetFinalPathNameByHandleW.argtypes=[wintypes.HANDLE,wintypes.LPWSTR,wintypes.DWORD,wintypes.DWORD]
        self.kernel.GetFinalPathNameByHandleW.restype=wintypes.DWORD
        self.kernel.GetHandleInformation.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
        self.kernel.GetHandleInformation.restype=wintypes.BOOL
        self.kernel.ReadFile.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p]
        self.kernel.ReadFile.restype=wintypes.BOOL

    def open(self,path):
        expected_final=os.path.realpath(s.fs.io_path(path),strict=True)
        s.fs.safe_components(path)
        self.path=path;self.expected_final=expected_final
        self.handle=self.kernel.CreateFileW(s.fs.io_path(path),0x80000000,1,None,3,0x00200000,None)
        if self.handle==ctypes.c_void_p(-1).value or self.handle is None:
            self.handle=None
            raise ctypes.WinError(ctypes.get_last_error())
        # All diagnostics/inspection occur after acquisition inside preserve's
        # retirement region. Native handles are noninheritable and deny writes.
        flags=wintypes.DWORD()
        assert self.kernel.GetHandleInformation(self.handle,ctypes.byref(flags)) and not flags.value & 1,'INHERITABLE_SOURCE_HANDLE'
        self.require_path()
        return self

    def require_path(self):
        final=ctypes.create_unicode_buffer(32768)
        length=self.kernel.GetFinalPathNameByHandleW(self.handle,final,len(final),0)
        assert 0<length<len(final),'OPENED_SOURCE_PATH_UNAVAILABLE'
        assert os.path.normcase(final.value)==os.path.normcase(self.expected_final),'OPENED_SOURCE_PATH_CHANGED'
        s.fs.safe_components(self.path)

    def identity(self):
        self.require_path()
        basic=FileBasic();standard=FileStandard();identity=FileId()
        for kind,value in ((0,basic),(1,standard),(18,identity)):
            assert self.kernel.GetFileInformationByHandleEx(self.handle,kind,ctypes.byref(value),ctypes.sizeof(value)),'OPENED_FILE_INSPECTION_FAILED'
        assert not basic.attributes & (s.fs.REPARSE|0x10) and not standard.directory,'OPENED_SOURCE_REPARSE_OR_DIRECTORY'
        assert not standard.delete_pending and standard.size>=0,'OPENED_SOURCE_UNAVAILABLE'
        return dict(device=identity.volume,inode=int.from_bytes(bytes(identity.file_id),'little'),
            bytes=standard.size,mtime_ns=(basic.write-116444736000000000)*100,attributes=basic.attributes)

    def read(self,expected_size):
        assert type(expected_size) is int and 0<=expected_size<=64*1024*1024,'ORIGINAL_SIZE_BOUND'
        parts=[];remaining=expected_size+1
        while remaining:
            amount=min(remaining,65536);buffer=ctypes.create_string_buffer(amount);read=wintypes.DWORD()
            if not self.kernel.ReadFile(self.handle,buffer,amount,ctypes.byref(read),None):
                raise ctypes.WinError(ctypes.get_last_error())
            assert read.value<=amount,'IMPOSSIBLE_NATIVE_READ_COUNT'
            if not read.value:break
            parts.append(buffer.raw[:read.value]);remaining-=read.value
        return b''.join(parts)

    def close(self,primary):
        if self.close_attempted:
            error=RuntimeError('ORIGINAL_READER_CLOSE_ALREADY_ATTEMPTED')
            j.retain(error,error,'original-reader-repeat-close',self);raise error
        self.close_attempted=True
        try:
            if self.handle is not None:
                if not self.kernel.CloseHandle(self.handle):
                    raise ctypes.WinError(ctypes.get_last_error())
            self.closed=True
        except BaseException as secondary:
            j.retain(primary if primary is not None else secondary,secondary,'original-reader-close',self)
            if primary is None:raise

def descriptor_matches(reader,row):
    facts=reader.identity()
    assert all(facts[k]==row['native_identity'][k] for k in ('device','inode','bytes','mtime_ns','attributes'))
    return facts

def preserve(original,target,expected):
    assert s.ordinary(original)==expected
    owner=OriginalReader();primary=None
    try:
        owner.open(original)
        facts=descriptor_matches(owner,expected);raw=owner.read(expected['bytes'])
        assert s.digest(raw)==expected['sha256'] and len(raw)==expected['bytes']
        assert owner.identity()==facts
    except BaseException as error:primary=error;raise
    finally:owner.close(primary)
    assert s.ordinary(original)==expected
    j.write_bytes(target,raw)
    assert s.ordinary(target)['sha256']==expected['sha256']

def require_originals(m,v):
    for name in m['application_paths']:
        if name in v['Source295']:assert s.ordinary(F/name)==v['Source295'][name]
        else:absent(F/name)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--release-path',type=Path,required=True)
    parser.add_argument('--release-sha256',required=True);args=parser.parse_args()
    release=j.require_release(args.release_path,args.release_sha256,'publish')
    m=j.manifest();v=j.verify();claim=j.require_current_claim()
    full_path,full=j.proof(release['candidate_full']);launch_path,launch=j.proof(release['candidate_full_launch'])
    assert full_path==R/'candidate-full/RESULT.json' and launch_path==R/'candidate-full-LAUNCH-RESULT.json'
    j.require_full(full,launch,'candidate-full',release['candidate_full'])
    j.require_validation(release['candidate_full'],release['candidate_full_launch'])
    assert release['claim_input_hash']==claim['input_hash'] and release['claim_started_at']==claim['claimed_at']
    assert release['application_paths']==m['application_paths']
    absent(OUT);require_originals(m,v)
    primitive=F/'.agents/runtime/rs2-20261014/apply_joined_source.py'
    assert s.sha(primitive)=='4592a2ccee83904c6fd698a2145d82279e07c0cc27cabb45fd1c13b844baec77'
    spec=importlib.util.spec_from_file_location('js3_reviewed_native_publication',primitive)
    io=importlib.util.module_from_spec(spec);spec.loader.exec_module(io)
    OUT.mkdir(exist_ok=False);stream=primary=None;completed=[]
    try:
        j.write_bytes(OUT/'ATTEMPT.json',(json.dumps({'at':s.utc(),'executor':'/root','manifest':j.exact_ref(Q/'TRANSFER-MANIFEST.json'),
            'release':j.exact_ref(args.release_path),'claim':claim,'candidate_full':release['candidate_full'],
            'candidate_full_launch':release['candidate_full_launch'],'application_paths':m['application_paths'],
            'automatic_retry':False,'Source_accepted':False,'destination_full_required':m['expected_test_count']},indent=2)+'\n').encode())
        for name in m['application_paths']:
            for prefix in ('staged','before','native-backups'):
                path=OUT/prefix/name;s.fs.safe_components(path.parent,allow_missing=True)
                path.parent.mkdir(parents=True,exist_ok=True);s.fs.safe_components(path.parent)
            raw=j.pinned_bytes(Q/name,m['expected_payload_hashes'][name]);j.write_bytes(OUT/'staged'/name,raw)
            if name in v['Source295']:preserve(F/name,OUT/'before'/name,v['Source295'][name])
        j.verify();assert j.canonical(j.require_current_claim())==j.canonical(claim)
        stream=(OUT/'APPLICATION-EVENTS.jsonl').open('x',encoding='utf-8')
        for name in m['application_paths']:
            expected=v['Source295'].get(name)
            if expected is None:absent(F/name)
            else:assert s.ordinary(F/name)==expected,'ORIGINAL_NATIVE_IDENTITY_DRIFT'
            assert j.canonical(j.require_current_claim())==j.canonical(claim)
            try:
                io.publish_prepared(OUT/'staged'/name,F/name,OUT/'native-backups'/name,
                    expected['sha256'] if expected is not None else None,m['expected_payload_hashes'][name])
            except BaseException as error:
                try:event(stream,{'at':s.utc(),'path':name,'state':'UNCERTAIN_REQUIRES_RECONCILIATION','type':type(error).__name__})
                except BaseException as secondary:j.retain(error,secondary,'uncertain-event',stream)
                raise
            if expected is not None:
                backup=s.ordinary(OUT/'native-backups'/name)
                assert backup['sha256']==expected['sha256'] and backup['native_identity']==expected['native_identity']
            completed.append(name)
            event(stream,{'at':s.utc(),'path':name,'state':'APPLIED','sha256':s.ordinary(F/name)['sha256']})
        closing=stream;stream=None
        j.close(closing,None,'application-event-close')
        j.verify(source='after');native_backups={}
        for name in m['application_paths']:
            expected=v['Source295'].get(name)
            if expected is not None:
                backup=s.ordinary(OUT/'native-backups'/name)
                assert backup['native_identity']==expected['native_identity'] and backup['sha256']==expected['sha256']
                assert s.ordinary(OUT/'before'/name)['sha256']==expected['sha256'];native_backups[name]=backup
        j.write_bytes(OUT/'APPLIED.json',(json.dumps({'at':s.utc(),'paths':completed,'source352':{
            name:s.ordinary(F/name) for name in m['expected_payload_hashes']},'native_backups':native_backups,
            'manifest':j.exact_ref(Q/'TRANSFER-MANIFEST.json'),'claim_input_hash':claim['input_hash'],
            'release':j.exact_ref(args.release_path),'events':j.exact_ref(OUT/'APPLICATION-EVENTS.jsonl'),
            'Source_accepted':False,'destination_full_required':m['expected_test_count'],
            'distinct_delivered_review_required':True,'automatic_retry':False},indent=2)+'\n').encode())
    except BaseException as error:
        primary=error
        try:j.write_bytes(OUT/'FAILED.json',(json.dumps({'at':s.utc(),'completed':completed,'error_type':type(error).__name__,
            'status':'PRESERVED_PARTIAL_OR_UNCERTAIN_REQUIRES_RECONCILIATION','Source_accepted':False,'automatic_retry':False})+'\n').encode())
        except BaseException as secondary:j.retain(error,secondary,'failure-journal')
        try:
            data=BaseException.__dict__['__dict__'].__get__(error)
            dict.__setitem__(data,'publication_attempt_root',OUT)
        except BaseException:pass
        raise
    finally:
        if stream is not None:j.close(stream,primary,'application-event-close')
    print(json.dumps({'applied':len(completed),'Source_accepted':False,'record':j.exact_ref(OUT/'APPLIED.json')}),flush=True)
if __name__=='__main__':main()
