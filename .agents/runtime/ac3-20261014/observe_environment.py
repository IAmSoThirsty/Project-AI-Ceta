"""Read-only native environment/ABI/profile observations; no launch/profile API."""
from ac3_support import *
import ctypes as C
sys.path.insert(0,str(Q/'src'))
from ceta.supervisor import isolated_worker as module
from ceta.supervisor import windows_jobs as native
api=module._IsolationAPI();query=api.SHGetKnownFolderPath;observations=[]
def observed(folder,flags,token,output):
    result=query(folder,flags,token,output)
    observations.append({'GUID_bytes':C.string_at(folder,16).hex(),'flags':flags,'token':token,
        'HRESULT':result,'output_address':C.cast(output,C.POINTER(C.c_void_p)).contents.value})
    return result
api.SHGetKnownFolderPath=observed
scratch=R/'read-only-scratch';scratch.mkdir()
source_inputs=json.loads((R/'SOURCE-INPUTS.json').read_text())
before={name:ordinary(F/name) for name in source_inputs['Source_payloads']}
started=utc();environment=api.environment(str(scratch))
assert set(environment)=={'SystemRoot','WINDIR','PATH','TEMP','TMP','LOCALAPPDATA'}
assert not api.pending_native_resources()
folder=api.userenv.GetAppContainerFolderPath
folder.argtypes,folder.restype=[C.c_wchar_p,C.POINTER(C.c_void_p)],C.c_int32
output=C.c_void_p();result=folder('S-1-15-2-695244707-3853392321-2130098501-3319658173-178928504-1880712989-1319207162',C.byref(output))
text=None
try:
    text=C.wstring_at(output) if output.value else None
    assert text is None or len(text)<32768
finally:
    if output.value:api.CoTaskMemFree(output)
after={name:ordinary(F/name) for name in before};assert before==after==source_inputs['Source_payloads']
write_new(R/'READ-ONLY-NATIVE-OBSERVATION.json',{'started_at':started,'finished_at':utc(),
    'product_source':ordinary(Q/'src/ceta/supervisor/isolated_worker.py'),'environment':environment,
    'native_known_folder_calls':observations,'native_allocation_custody_after':list(api.pending_native_resources()),
    'ABI':{'GUID_bytes':C.sizeof(module._KnownFolderId),'SECURITY_CAPABILITIES_bytes':C.sizeof(module.SECURITY_CAPABILITIES),
        'SECURITY_CAPABILITIES_offsets':{name:getattr(module.SECURITY_CAPABILITIES,name).offset for name,_ in module.SECURITY_CAPABILITIES._fields_},
        'STARTUPINFOEX_bytes':C.sizeof(native.STARTUPINFOEX),'STARTUPINFOEX_attributes_offset':native.STARTUPINFOEX.attributes.offset,
        'PROCESS_INFORMATION_bytes':C.sizeof(native.PROCESS_INFORMATION),'environment_UTF16_bytes':C.sizeof(native._environment(environment))},
    'Win32_error203_message':C.FormatError(203),'reserved_profile_readonly':{'api':'GetAppContainerFolderPath','HRESULT':result,'path':text,
        'path_exists':None if text is None else Path(text).exists()},
    'historical_profile_attempt':source_inputs['historical_profile_attempt'],
    'cause_status':'UNESTABLISHED; neither native error203 nor primary documentation identifies the internal failing variable lookup.',
    'hypothesis':'The documented LOCALAPPDATA profile input is absent from the AC2 five-key environment. AC3 adds only the native-observed known folder as a bounded candidate for a later approved qualification.',
    'native_Create_or_Delete_calls':0,'restricted_CreateProcess_calls':0,'Source_native_before_after_exact':True,'Source_application':False,
    'primary_sources':['https://learn.microsoft.com/en-us/windows/win32/secauthz/implementing-an-appcontainer',
        'https://learn.microsoft.com/en-us/windows/win32/api/shlobj_core/nf-shlobj_core-shgetknownfolderpath',
        'https://learn.microsoft.com/en-us/windows/win32/api/shlobj_core/ne-shlobj_core-known_folder_flag'],
    'exit_status':0})
print(json.dumps({'native_known_folder_calls':len(observations),'environment_keys':sorted(environment),
    'profile_HRESULT':result,'cause':'UNESTABLISHED','Source':290,'Create_Delete':0}),flush=True)
