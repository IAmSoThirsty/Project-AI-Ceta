"""Read/derive the exact reserved profile proposal; never create/delete profiles."""
from ac_support import *
import ctypes as C
from ctypes import wintypes as W
sys.path.insert(0, str(Q / 'src'))
from ceta.supervisor.isolated_worker import _IsolationAPI, appcontainer_sid
from native_fixture_support import owner_sid

name = 'CETA.ProjectAICETA.IsolatedWorker.AC1.V1'
sid = appcontainer_sid(name)
api = _IsolationAPI()
api.GetAppContainerFolderPath = api.userenv.GetAppContainerFolderPath
api.GetAppContainerFolderPath.argtypes = [W.LPCWSTR, C.POINTER(C.c_void_p)]
api.GetAppContainerFolderPath.restype = C.c_int32
folder = C.c_void_p()
status = api.GetAppContainerFolderPath(sid, C.byref(folder))
path = None
try:
    if status == 0 and folder.value: path = C.wstring_at(folder)
finally:
    if folder.value:
        ole = C.WinDLL('ole32', use_last_error=True, winmode=0x800)
        ole.CoTaskMemFree.argtypes = [C.c_void_p]; ole.CoTaskMemFree.restype = None
        ole.CoTaskMemFree(folder)
proposal = {
    'profile': 'ceta-ac1-reserved-native-profile-proposal-v1', 'observed_at': utc(),
    'decision': 'PROPOSED_REQUIRES_EXPLICIT_USER_APPROVAL', 'executed': False,
    'owner_user_sid': owner_sid(), 'exact_name': name, 'derived_sid': sid,
    'capabilities': [], 'capability_count': 0,
    'image': ordinary(R / 'build-r2/isolated_worker.exe'),
    'folder_query': {'api': 'GetAppContainerFolderPath', 'HRESULT': status, 'returned_path': path,
                     'content_read': False, 'created': False},
    'create_api': {'dll': 'System32/userenv.dll', 'name': 'CreateAppContainerProfile',
                   'arguments': {'pszAppContainerName': name, 'pszDisplayName': 'Project-AI: CETA isolated worker AC1',
                                 'pszDescription': 'Zero-capability local native worker isolation qualification',
                                 'pCapabilities': None, 'dwCapabilityCount': 0, 'ppSidAppContainerSid': 'owned output pointer; verify exact derived SID; FreeSid'}},
    'durable_host_effect': 'Per-current-user AppContainer profile/definition and its registered local app-data/registry namespace, created by the Windows profile API; no new account or firewall/loopback/elevation',
    'preconditions': ['Explicit current human approval for this exact name/SID/per-user host object',
                     'Fresh inspect-only prior profile existence and native caller/image/hash',
                     'If pre-existing/ERROR_ALREADY_EXISTS: preserve, do not overwrite/adopt/delete; request exact owner disposition',
                     'Zero capabilities and exact deterministic SID returned by Create compared to this independent derivation',
                     'No Source/E3/data-root ACL changes; grant only fresh qualification assets/scratch as reviewed'],
    'cleanup_proposal': {'api': 'DeleteAppContainerProfile', 'name': name,
                         'permission': 'Separately explicit cleanup authority for the profile created by this operation',
                         'guard': 'Never delete a pre-existing or unknown profile; bind successful creation receipt/current SID/exact name',
                         'order': ['Close new launch admission', 'Observe exact owned worker exit and empty job',
                                   'Observe every profile-associated test process/handle retired',
                                   'Preserve permitted fixture/source/test receipts on T:',
                                   'Invoke exact DeleteAppContainerProfile after granted cleanup',
                                   'Query exact profile registration/folder metadata and record actual absence or residual state; no recursive filesystem deletion'],
                         'limit': 'Delete return0 is a request result; verify actual profile state, report residuals. No perfect-erasure claim.'},
    'forbidden': ['Create/Delete called during this proposal', 'Download/install dependencies', 'Host account/service creation',
                  'Firewall/loopback exemption', 'Elevation or protection disable', 'Treat operator approval as CETA trusted runtime consent'],
    'cause_of_current_error2': 'UNESTABLISHED; profile requirement is documented possible dependency, not proven internal cause',
}
write_new(R / 'PROFILE-CREATION-PROPOSAL.json', proposal)
print(json.dumps({'proposal': str(R / 'PROFILE-CREATION-PROPOSAL.json'), 'name': name,
                  'sid': sid, 'folder_query': proposal['folder_query'], 'executed': False}, indent=2))
