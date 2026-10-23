"""Complete bounded-tree observations; extended Windows I/O, logical report keys.

No ignored names or silent enumeration errors. This is a stable sampled file tree,
not an atomic filesystem/ACL/alternate-stream snapshot. Directory identity/mode
must survive; its recorded size/mtime may change when fresh children are added.
"""
from pathlib import Path
import hashlib,json,os,stat,sys

def logical(path):
    raw=str(path)
    assert not raw.startswith(('\\\\?\\','\\\\.\\','\\\\')),'physical/UNC alias is not a logical input'
    p=Path(raw)
    assert p.is_absolute() and '..' not in p.parts,'absolute normalized logical path required'
    assert all(not part.endswith(('.', ' ')) and ':' not in part for part in p.parts[1:]),'ambiguous Windows component'
    return p

def physical(path):
    p=logical(path)
    return Path('\\\\?\\'+str(p)) if sys.platform=='win32' else p

def plain(path):
    s=physical(path).lstat()
    assert not stat.S_ISLNK(s.st_mode) and not getattr(s,'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT,('reparse/link',str(path))
    assert stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode),('unsupported entry',str(path))
    return s

def ancestors(root,path):
    root=logical(root);path=logical(path);assert path.is_relative_to(root)
    while True:
        assert stat.S_ISDIR(plain(path).st_mode)
        if str(path)==str(root):return
        path=path.parent

def native(s):
    return dict(device=s.st_dev,inode=s.st_ino,bytes=s.st_size,mtime_ns=s.st_mtime_ns,mode=s.st_mode,links=s.st_nlink)

def refusal(phase,path,expected,observed):
    """Primitive attributes survive the accepted bounded raw diagnostic.

    Dict-valued exception args are deliberately unsupported by that reporter.
    Field names and value tuples retain raw metadata without unsafe formatting.
    """
    keys=tuple(sorted(set(expected)|set(observed)));text=str(path)
    error=AssertionError('file observation refused: '+phase+' path='+text)
    storage=BaseException.__dict__['__dict__'].__get__(error)
    fields=dict(observer_phase=phase,observer_path=text,observer_path_full_sha256=hashlib.sha256(text.encode('utf8')).hexdigest(),
        observer_path_exceeds_report_scalar_bound=len(text)>512,
        observer_differing_fields=tuple(k for k in keys if expected.get(k)!=observed.get(k)),
        observer_native_fields=keys,observer_expected_values=tuple(expected.get(k) for k in keys),
        observer_observed_values=tuple(observed.get(k) for k in keys))
    for key,value in fields.items():dict.__setitem__(storage,key,value)
    raise error

def cross_api(path,path_view,handle_view):
    """Directional CPython Win32 suffix synthesis, never a mode mask.

    CPython3.12 Modules/posixmodule.c update_st_mode_from_path adds 0111 for
    .exe/.bat/.cmd/.com. This comparison is not an ACL or execution-right claim.
    Both raw records are retained and each API must independently stay stable.
    """
    if path_view==handle_view:return 'EXACT'
    if (sys.platform=='win32' and path.suffix.casefold() in {'.exe','.bat','.cmd','.com'}
        and stat.S_ISREG(path_view['mode']) and stat.S_ISREG(handle_view['mode'])
        and path_view['links']==handle_view['links']==1
        and path_view==dict(handle_view,mode=handle_view['mode']|0o111)):
        return 'CPYTHON_WIN32_SUFFIX_EXECUTE_BITS'
    refusal('cross_API_path_handle',path,path_view,handle_view)

def custody(primary_info,secondary,prefix):
    """Record raw exception identities without invoking hostile setters.

    A body error leaves by __exit__ returning False. Only a cleanup-only fault
    is raised here; the interpreter, never contextlib, restores its traceback.
    """
    body_failed=primary_info is not None
    if primary_info is None:
        if not secondary:return False
        primary_info=secondary[0]
    fault=primary_info[1];storage=BaseException.__dict__['__dict__'].__get__(fault)
    dict.__setitem__(storage,prefix+'_primary_exc_info',primary_info)
    dict.__setitem__(storage,prefix+'_secondary_errors',tuple(info[1] for info in secondary))
    dict.__setitem__(storage,prefix+'_secondary_exc_info',tuple(secondary))
    if not body_failed:raise BaseException.with_traceback(fault,primary_info[2])
    return False

class _FileStream:
    def __init__(self,path):self.path=path;self.entered=False;self.closed=False
    def __enter__(self):
        assert not self.entered,'file observation context reused'
        self.entered=True
        self.stream=physical(self.path).open('rb')
        return self.stream
    def __exit__(self,kind,error,traceback):
        assert self.entered and not self.closed,'file observation context not active'
        self.closed=True;secondary=[]
        try:self.stream.close()
        except BaseException:secondary.append(sys.exc_info())
        primary=None if error is None else (kind,error,traceback)
        return custody(primary,secondary,'observer')

def file_stream(path):
    """Explicit exit never assigns an existing body's __traceback__."""
    return _FileStream(path)

def stable(path):
    path=logical(path);before=plain(path)
    assert stat.S_ISREG(before.st_mode) and before.st_nlink==1,('file alias/type',str(path))
    path_before=native(before);digest=hashlib.sha256();count=0
    with file_stream(path) as stream:
        handle_before=native(os.fstat(stream.fileno()))
        qualification=cross_api(path,path_before,handle_before)
        while block:=stream.read(min(1024*1024,before.st_size-count+1)):
            count+=len(block)
            if count>before.st_size:refusal('read_exceeds_bound',path,{'bytes':before.st_size},{'bytes':count})
            digest.update(block)
        handle_after=native(os.fstat(stream.fileno()))
        if handle_before!=handle_after:refusal('handle_before_after',path,handle_before,handle_after)
        cross_api(path,path_before,handle_after)
    after=plain(path);path_after=native(after)
    if path_before!=path_after:refusal('path_before_after',path,path_before,path_after)
    if count!=after.st_size:refusal('read_count',path,{'bytes':after.st_size},{'bytes':count})
    return dict(kind='file',**path_after,sha256=digest.hexdigest(),
        api_metadata=dict(path_before=path_before,handle_before=handle_before,
            handle_after=handle_after,path_after=path_after),cross_api_qualification=qualification)

def snapshot(base):
    """Every root/dir/file including ignored/empty directories, or exact error.

    Physical I/O is always extended-path on Windows. Keys are uniquely normalized
    logical base-relative names. Native duplicate identities/hard links and
    case-fold collisions refuse an observation rather than aliasing two entries.
    Each directory is enumerated before and after its descendants to detect churn.
    """
    base=logical(base);ancestors(Path(base.anchor),base)
    out={};identities=set();names=set()
    def add(key,record):
        folded=key.rstrip('/').casefold();identity=(record['device'],record['inode'])
        assert folded not in names and identity not in identities,('entry alias',key)
        names.add(folded);identities.add(identity);out[key]=record
    def children(directory):
        # scandir exceptions are deliberately uncaught and retain exact identity.
        with os.scandir(physical(directory)) as stream:return sorted(entry.name for entry in stream)
    def visit(directory,key):
        first=plain(directory);assert stat.S_ISDIR(first.st_mode)
        before=children(directory)
        record=dict(kind='directory',**native(first))
        add(key,record)
        for name in before:
            child=directory/name;info=plain(child)
            relative=child.relative_to(base).as_posix()
            if stat.S_ISDIR(info.st_mode):visit(child,relative+'/')
            else:add(relative,stable(child))
        last=plain(directory)
        assert native(first)==native(last) and before==children(directory),('directory changed during observation',str(directory))
    visit(base,'.')
    return out

def preservation(before,after):
    for key,record in before.items():
        assert key in after,('preexisting entry disappeared',key)
        current=after[key]
        if record['kind']=='file':assert current==record,('preexisting file/native metadata changed',key)
        else:assert all(current[k]==record[k] for k in ('kind','device','inode','mode')),('directory replaced/changed',key)
    return True

def projection(base,graph_root):
    """Stock snapshot interface, complete keys and deterministic string values.

    Directory value retains identity/mode, excluding mutable child-addition
    metadata. The full observation still records that metadata. File values bind
    bytes and native metadata. Every key is exactly one graph-relative path.
    """
    base=logical(base);root=logical(graph_root);assert base.is_relative_to(root)
    out={};folded=set()
    for key,record in snapshot(base).items():
        target=base if key=='.' else base/key.rstrip('/')
        name=target.relative_to(root).as_posix()
        assert name.casefold() not in folded and name not in out,'projection alias'
        assert target.is_relative_to(base),'projection escaped workspace'
        folded.add(name.casefold())
        value=record if record['kind']=='file' else {k:record[k] for k in ('kind','device','inode','mode')}
        out[name]=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
    return out
