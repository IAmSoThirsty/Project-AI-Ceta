"""F-only sampled snapshot with one handle-derived directory metadata provider.

Raw path/handle metadata remains explicit provenance. LastAccessTime is observed
reference data under the pinned policy; every other queried field is compared.
No retry, time rewrite, hook, installation or write is performed by this module.
"""
from pathlib import Path
import copy,ctypes as C,hashlib,importlib.util,json,os,stat,sys
F=Path('T:/00-Active/Project-AI-CETA');W=Path(__file__).resolve().parent
LEGACY=F/'.agents/runtime/oq23/st2/work/status_core.py'
LEGACY_SHA='19668309370195f7d6c765d0da708e9159844814c40cd6a56bd8f8f7dcd40691'
POLICY_SHA='5d0c1ead3cfe6d7893874bcda7f8a508764d99c9b37e50994ca1b33de5d4662c'
assert hashlib.sha256(LEGACY.read_bytes()).hexdigest()==LEGACY_SHA
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('_ds1_readonly_legacy_status_core',LEGACY)
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
EXPECTED_IGNORED=legacy.EXPECTED_IGNORED
DWORD=C.c_uint32;BOOL=C.c_int32;HANDLE=C.c_void_p
class Basic(C.Structure):
    _fields_=[('CreationTime',C.c_int64),('LastAccessTime',C.c_int64),('LastWriteTime',C.c_int64),('ChangeTime',C.c_int64),('FileAttributes',DWORD)]
class Standard(C.Structure):
    _fields_=[('AllocationSize',C.c_int64),('EndOfFile',C.c_int64),('NumberOfLinks',DWORD),('DeletePending',C.c_ubyte),('Directory',C.c_ubyte)]
class Identity(C.Structure):
    _fields_=[('VolumeSerialNumber',C.c_uint64),('FileId',C.c_ubyte*16)]
assert (C.sizeof(Basic),C.sizeof(Standard),C.sizeof(Identity))==(40,24,24)
def physical(path):
    path=Path(path)
    assert path.is_absolute() and path.is_relative_to(F) and '..' not in path.parts
    assert not str(path).startswith('\\\\')
    assert all(not item.endswith(('.', ' ')) and ':' not in item for item in path.parts[1:])
    return Path('\\\\?\\'+str(path))
def raw(info):
    return {name:getattr(info,name) for name in dir(info) if name.startswith('st_') and isinstance(getattr(info,name),(int,float))}
def ns(ticks):return (ticks-116444736000000000)*100
def security(value):
    # This is a distinct comparison view, never a rewritten native observation.
    return dict(basic={key:value for key,value in value['basic'].items() if key!='LastAccessTime'},
        standard=dict(value['standard']),identity=dict(value['identity']))
def path_security(value):return {key:item for key,item in value.items() if key not in ('st_size','st_atime','st_atime_ns')}
def custody(primary,secondary,observation):
    if primary is None and not secondary:return False
    body=primary is not None
    if primary is None:primary=secondary[0]
    error=primary[1];storage=BaseException.__dict__['__dict__'].__get__(error)
    # The first (innermost) custodian and original triple remain recoverable.
    if not dict.__contains__(storage,'directory_snapshot_primary_exc_info'):
        dict.update(storage,directory_snapshot_primary_exc_info=primary,
            directory_snapshot_observation=observation,directory_snapshot_handle=observation.handle,
            directory_snapshot_close=observation.close)
    previous=dict.get(storage,'directory_snapshot_secondary_exc_info',())
    if type(previous) is not tuple:
        dict.__setitem__(storage,'directory_snapshot_prior_secondary_value',previous);previous=()
    dict.__setitem__(storage,'directory_snapshot_secondary_exc_info',previous+tuple(secondary))
    frames=dict.get(storage,'directory_snapshot_custody',())
    if type(frames) is not tuple:
        dict.__setitem__(storage,'directory_snapshot_prior_custody_value',frames);frames=()
    frame=dict(primary_exc_info=primary,secondary_exc_info=tuple(secondary),observation=observation,
        handle=observation.handle,closed=observation.closed,close_cleanup=observation.close)
    dict.__setitem__(storage,'directory_snapshot_custody',frames+(frame,))
    if not body:raise BaseException.with_traceback(error,primary[2])
    return False
class WinProvider:
    def __init__(self):
        assert sys.platform=='win32' and sys.flags.optimize==0
        self.api=C.WinDLL('kernel32',use_last_error=True)
        self.api.CreateFileW.argtypes=[C.c_wchar_p,DWORD,DWORD,C.c_void_p,DWORD,DWORD,HANDLE];self.api.CreateFileW.restype=HANDLE
        self.api.GetFileInformationByHandleEx.argtypes=[HANDLE,C.c_int,C.c_void_p,DWORD];self.api.GetFileInformationByHandleEx.restype=BOOL
        self.api.CloseHandle.argtypes=[HANDLE];self.api.CloseHandle.restype=BOOL
    def path_stat(self,path):return raw(os.lstat(physical(path)))
    def open(self,path):
        handle=self.api.CreateFileW(str(physical(path)),0x80,7,None,3,0x02200000,None)
        assert handle not in (None,C.c_void_p(-1).value),C.WinError(C.get_last_error())
        return handle
    def query(self,handle):
        values={};completed=[];number=None
        try:
            for number,kind,name in ((0,Basic,'basic'),(1,Standard,'standard'),(18,Identity,'identity')):
                data=kind();assert self.api.GetFileInformationByHandleEx(handle,number,C.byref(data),C.sizeof(data)),C.WinError(C.get_last_error())
                values[name]={key:(bytes(getattr(data,key)).hex() if key=='FileId' else int(getattr(data,key))) for key,_ in kind._fields_}
                completed.append(number)
            return values
        except BaseException as error:
            storage=BaseException.__dict__['__dict__'].__get__(error)
            prior=dict.get(storage,'directory_handle_query_failures',())
            if type(prior) is not tuple:
                dict.__setitem__(storage,'directory_handle_query_prior_failure_value',prior);prior=()
            record=dict(provider=self,handle=handle,metadata=copy.deepcopy(values),completed_classes=tuple(completed),
                failed_class=number,exc_info=sys.exc_info())
            dict.__setitem__(storage,'directory_handle_query_failures',prior+(record,))
            raise
    def close(self,handle):assert self.api.CloseHandle(handle),C.WinError(C.get_last_error())
    def children(self,path):
        # Explicit close protocol preserves an original exception with hostile setters.
        stream=os.scandir(physical(path));primary=None;secondary=[]
        try:return sorted(entry.name for entry in stream)
        except BaseException:
            primary=sys.exc_info();raise
        finally:
            try:stream.close()
            except BaseException:
                secondary.append(sys.exc_info())
                if primary is None:raise
                storage=BaseException.__dict__['__dict__'].__get__(primary[1])
                dict.update(storage,directory_scandir_primary_exc_info=primary,
                    directory_scandir_secondary_exc_info=tuple(secondary),directory_scandir_stream=stream)
class Directory:
    def __init__(self,path,provider):
        self.path=Path(path);self.provider=provider;self.handle=None;self.closed=False;self.entered=False
        self.raw_paths=[];self.raw_handles=[];self.baseline=self.path_baseline=None
    def bind(self,path,native):
        b,s,i=native['basic'],native['standard'],native['identity']
        assert stat.S_ISDIR(path['st_mode']) and not path['st_file_attributes']&0x400 and path.get('st_reparse_tag',0)==0,('directory reparse/type',str(self.path))
        assert s['Directory']==1 and s['DeletePending']==0 and s['NumberOfLinks']>=1
        assert s['EndOfFile']>=0 and s['AllocationSize']>=0 and b['FileAttributes']&0x10 and not b['FileAttributes']&0x400
        assert path['st_dev']==i['VolumeSerialNumber'] and path['st_ino']==int.from_bytes(bytes.fromhex(i['FileId']),'little'),('directory identity binding',str(self.path))
        assert path['st_file_attributes']==b['FileAttributes'] and path['st_nlink']==s['NumberOfLinks'],('directory attributes/links binding',str(self.path))
        assert path['st_mtime_ns']==ns(b['LastWriteTime']) and path['st_birthtime_ns']==ns(b['CreationTime']),('directory time binding',str(self.path))
        assert path['st_size'] in (0,s['EndOfFile']),('unqualified directory path-size provider',str(self.path),path['st_size'],s['EndOfFile'])
        if self.path_baseline is not None:
            assert path_security(path)==path_security(self.path_baseline),('directory path security changed',str(self.path))
        if self.baseline is not None:
            assert security(native)==security(self.baseline),('directory handle security changed',str(self.path))
    def checkpoint(self,stage):
        try:native=self.provider.query(self.handle)
        except BaseException as error:
            storage=BaseException.__dict__['__dict__'].__get__(error)
            failures=dict.get(storage,'directory_handle_query_failures',())
            if type(failures) is tuple and failures:
                last=failures[-1]
                if type(last) is dict and last.get('provider') is self.provider and last.get('handle')==self.handle:
                    self.raw_handles.append(dict(stage=stage,complete=False,metadata=copy.deepcopy(last['metadata']),
                        completed_classes=last['completed_classes'],failed_class=last['failed_class']))
            raise
        self.raw_handles.append(dict(stage=stage,metadata=copy.deepcopy(native)))
        path=self.provider.path_stat(self.path)
        self.raw_paths.append(dict(stage=stage,metadata=copy.deepcopy(path)))
        self.bind(path,native)
        return native,path
    def __enter__(self):
        assert not self.entered;self.entered=True
        first=self.provider.path_stat(self.path);self.raw_paths.append(dict(stage='BEFORE_OPEN',metadata=copy.deepcopy(first)))
        try:
            self.handle=self.provider.open(self.path)
            native,path=self.checkpoint('AFTER_OPEN')
            self.bind(first,native);self.baseline=copy.deepcopy(native);self.path_baseline=copy.deepcopy(first)
            return self
        except BaseException:
            primary=sys.exc_info();secondary=[]
            if self.handle is not None:
                try:self.close()
                except BaseException:secondary.append(sys.exc_info())
            custody(primary,secondary,self);raise
    def names(self,stage):
        self.checkpoint(stage+'_BEFORE_ENUMERATION')
        names=self.provider.children(self.path)
        self.checkpoint(stage+'_AFTER_ENUMERATION')
        assert len(names)==len(set(names)) and names==sorted(names),'duplicate or unordered directory names'
        assert all(name not in ('.','..') and '/' not in name and '\\' not in name for name in names),'invalid physical name'
        return names
    def record(self):
        b,s,i=self.baseline['basic'],self.baseline['standard'],self.baseline['identity']
        return dict(device=i['VolumeSerialNumber'],inode=int.from_bytes(bytes.fromhex(i['FileId']),'little'),
            bytes=s['EndOfFile'],mtime_ns=ns(b['LastWriteTime']),mode=self.path_baseline['st_mode'],attributes=b['FileAttributes'])
    def provenance(self):
        return dict(raw_path_observations=self.raw_paths,raw_handle_observations=self.raw_handles,
            access_time_policy_sha256=POLICY_SHA,comparison_provider='GET_FILE_INFORMATION_BY_HANDLE_EX_BASIC_STANDARD_ID',
            path_size_qualification='Only raw zero or exact same-handle EOF; raw values retained',
            access_times='OBSERVED_REFERENCE_ONLY; NOT_REWRITTEN',handle_security_fields='ALL_EXCEPT_LastAccessTime')
    def close(self):
        assert self.handle is not None and not self.closed
        self.provider.close(self.handle);self.closed=True
    def __exit__(self,kind,error,traceback):
        secondary=[]
        try:self.close()
        except BaseException:secondary.append(sys.exc_info())
        return custody(None if error is None else (kind,error,traceback),secondary,self)
def _snapshot_tree(workspace,graph_root,ignored,provider):
    workspace=Path(workspace);graph_root=Path(graph_root)
    assert workspace.is_relative_to(F) and graph_root==F and type(ignored) is frozenset
    files={};directories={};excluded_symlinks={};observations={};aliases=set();seen=set()
    def visit(directory):
        with Directory(directory,provider) as opened:
            names=opened.names('INITIAL');info=opened.record();rel=directory.relative_to(graph_root).as_posix()
            identity=(info['device'],info['inode']);assert identity not in seen,'physical directory alias';seen.add(identity)
            directories[rel]=info
            skip=directory.relative_to(workspace).parts[:2]==('.project-ai','automation')
            if not skip:
                for name in names:
                    path=directory/name;key=path.relative_to(graph_root).as_posix();fold=key.casefold()
                    assert fold not in aliases,'case alias';aliases.add(fold)
                    probe=os.lstat(physical(path))
                    if name in ignored and stat.S_ISDIR(probe.st_mode):continue
                    if stat.S_ISLNK(probe.st_mode):
                        before=(probe.st_dev,probe.st_ino,probe.st_size,probe.st_mtime_ns,probe.st_mode,getattr(probe,'st_file_attributes',0))
                        target=os.readlink(physical(path));after=os.lstat(physical(path))
                        assert before==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_mode,getattr(after,'st_file_attributes',0)),'symlink changed during observation'
                        excluded_symlinks[key]=dict(device=probe.st_dev,inode=probe.st_ino,bytes=probe.st_size,
                            mtime_ns=probe.st_mtime_ns,mode=probe.st_mode,attributes=getattr(probe,'st_file_attributes',0),link_text=target,target_followed=False)
                        continue
                    item=legacy.native(path)
                    if stat.S_ISDIR(item['mode']):visit(path)
                    else:files[key]=legacy.stable(path)
            again=opened.names('FINAL');assert names==again,('directory names changed across subtree',str(directory))
            observations[rel]=opened.provenance()
    visit(workspace)
    return dict(files=files,directories=directories,excluded_symlinks=excluded_symlinks,directory_observations=observations,
        policy=dict(ignored_directory_names=sorted(ignored),ignored_root_relative_subtree='.project-ai/automation',
            symlinks='EXCLUDED_AS_STOCK; OWN_IDENTITY_RECORDED; NEVER_FOLLOWED',unignored_nonsymlink_reparse='REFUSE',
            root_and_nested_enumeration='FAIL_CLOSED',extended_paths=True,
            coverage='ALL_ORDINARY_ENTRIES_UNDER_EXPLICIT_STOCK_POLICY; NOT_IGNORED_REPOSITORY_COMPLETENESS',
            directory_security_provider='WIN32_BASIC_STANDARD_ID_SAME_HANDLE_ACROSS_SUBTREE',
            access_time_observation_policy_sha256=POLICY_SHA,atomic_filesystem_snapshot=False))
def snapshot(workspace,graph_root,ignored=EXPECTED_IGNORED):
    """Exact F-only integration interface; all other workspace calls are refused."""
    assert Path(workspace)==F and Path(graph_root)==F and ignored==EXPECTED_IGNORED
    policy=W/'ACCESS-TIME-OBSERVATION-POLICY.json'
    assert hashlib.sha256(policy.read_bytes()).hexdigest()==POLICY_SHA
    return _snapshot_tree(F,F,ignored,WinProvider())
def file_map(observation):return legacy.file_map(observation)
