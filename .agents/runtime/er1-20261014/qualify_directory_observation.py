"""Compare observed directory stat values with retained native handle queries."""
from er1_support import *
import ctypes as C
from ctypes import wintypes as W
class FileId(C.Structure):_fields_=[('volume',C.c_ulonglong),('identifier',C.c_ubyte*16)]
class Standard(C.Structure):_fields_=[('allocation',C.c_longlong),('end_of_file',C.c_longlong),('links',W.DWORD),('delete_pending',C.c_ubyte),('directory',C.c_ubyte)]
assert C.sizeof(FileId)==24 and C.sizeof(Standard)==24
api=C.WinDLL('kernel32.dll',use_last_error=True,winmode=0x800)
api.CreateFileW.argtypes=[W.LPCWSTR,W.DWORD,W.DWORD,C.c_void_p,W.DWORD,W.DWORD,W.HANDLE];api.CreateFileW.restype=W.HANDLE
api.GetFileInformationByHandleEx.argtypes=[W.HANDLE,C.c_int,C.c_void_p,W.DWORD];api.GetFileInformationByHandleEx.restype=W.BOOL
api.CloseHandle.argtypes=[W.HANDLE];api.CloseHandle.restype=W.BOOL
def identity(path):
    path=fs.safe_components(path);a=fs.lstat(path);assert stat.S_ISDIR(a.st_mode) and not fs.reparse(a)
    handle=api.CreateFileW(fs.io_path(path),0x80,7,None,3,0x02200000,None);assert handle!=C.c_void_p(-1).value
    try:
        identifier=FileId();standard=Standard()
        assert api.GetFileInformationByHandleEx(handle,18,C.byref(identifier),C.sizeof(identifier))
        assert api.GetFileInformationByHandleEx(handle,1,C.byref(standard),C.sizeof(standard))
        assert standard.directory and not standard.delete_pending
        return {'volume_serial':identifier.volume,'file_id_128':bytes(identifier.identifier).hex(),'file_id_low_64':int.from_bytes(bytes(identifier.identifier)[:8],'little'),
                'standard_information_allocation_size':standard.allocation,'standard_information_end_of_file':standard.end_of_file,'stat_before':fs.file_identity(a),'stat_after':fs.file_identity(fs.lstat(path))}
    finally:assert api.CloseHandle(handle)
drift=json.loads((R/'source-drift-r3.json').read_text());rows=[]
for row in drift['differences']:
    a,b=row['before'],row['after'];assert a['kind']==b['kind']=='directory'
    difference=[key for key in a['native_identity'] if a['native_identity'][key]!=b['native_identity'][key]];assert difference==['bytes']
    native=identity(E3/row['relative_path'])
    assert native['volume_serial']==a['native_identity']['device']==b['native_identity']['device']
    assert native['file_id_low_64']==a['native_identity']['inode']==b['native_identity']['inode']
    assert all(native['stat_after'][key]==a['native_identity'][key] for key in a['native_identity'] if key!='bytes')
    rows.append({'relative_path':row['relative_path'],'historical_before':a['native_identity'],'historical_after':b['native_identity'],'fresh_native_handle':native})
result={'observed_at':utc(),'source_drift':reference(R/'source-drift-r3.json'),'directory_count':len(rows),'native_directory_identity_matches':True,
        'ordinary_file_changes':0,'only_observed_directory_stat_size_varies':True,'directories':rows,
        'qualification':'All original names/native IDs/timestamps/modes/attributes and every ordinary file hash are retained. These raw directory size observations are not ordinary file contents. No exact OS-internal cause is asserted; native handle query forms and retained stat observations are provided. A fresh file-byte/native-ID cut will retain the old snapshots and this limitation.',
        'exit_status':0}
write_new(R/'directory-observation-proof.json',result)
print(json.dumps({'directories':len(rows),'native_IDs_match':True,'ordinary_changes':0,'native_allocation_sizes':sorted({row['fresh_native_handle']['standard_information_allocation_size'] for row in rows}),
                  'native_end_of_file_sizes':sorted({row['fresh_native_handle']['standard_information_end_of_file'] for row in rows}),'proof_sha256':sha(R/'directory-observation-proof.json')}))
