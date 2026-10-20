"""Prepared host-profile qualification. Inspect never creates a profile; qualify requires exact recorded operator approval."""
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch
import argparse, ctypes as C, hashlib, importlib.util, json, os, stat, sys, uuid
from ctypes import wintypes as W

R = Path(__file__).resolve().parent
F = R.parents[2]
Q = F / '.agents/ac2-20261014'
NAME = 'CETA.ProjectAICETA.IsolatedWorker.AC1.V1'
SID = 'S-1-15-2-695244707-3853392321-2130098501-3319658173-178928504-1880712989-1319207162'
USER = 'S-1-5-21-1218874621-2294869469-207301144-1003'
MANIFEST = '41a2c6ab046279a581fe3ff99b126b84d7485d8369108f7abbf53634da254dda'
IMAGE = '527518104fb84c430e3e9e0be61982c533b0c6fbb13e1a85e959ba1a3866ad0f'
PROPOSAL = F / '.agents/runtime/ac1-20261014/PROFILE-CREATION-PROPOSAL.json'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
now = lambda: datetime.now(timezone.utc).isoformat()
assert os.name == 'nt' and not sys.flags.optimize
assert Path(sys.executable) == F / '.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
assert sha(Q / 'TRANSFER-MANIFEST.json') == MANIFEST
assert sha(PROPOSAL) == '75c5a41afd412ab91272ced373b84bfcbe34f5941c1b6dbf95254905a65db55c'
reader = F / '.agents/pr4-20261014/preserve_ceta_complete.py'
assert sha(reader) == '2ccbca31973ead308e1cdcc6676bbd7371cdec29a0f16178f3f55a4ab4130618'
reader_spec = importlib.util.spec_from_file_location('profile_native_file_reader', reader)
fs = importlib.util.module_from_spec(reader_spec)
sys.modules[reader_spec.name] = fs
reader_spec.loader.exec_module(fs)
def observed(path):
    path = fs.safe_components(path)
    info = fs.lstat(path)
    assert stat.S_ISREG(info.st_mode) and not fs.reparse(info)
    identity = fs.file_identity(info)
    size, pin, _ = fs.hash_file(path)
    assert size == identity['bytes'] and fs.file_identity(fs.lstat(path)) == identity
    return {'sha256': pin, 'native_identity': identity}
for relative, facts in read(Q / 'TRANSFER-MANIFEST.json')['payloads'].items():
    current = observed(Q / relative)
    assert current['sha256'] == facts['sha256'] and current['native_identity'] == facts['native_identity']
sys.path.insert(0, str(Q / 'src'))
from ceta.supervisor import isolated_worker as module
from ceta.supervisor.windows_jobs import WindowsOwnedProcess

def save(path, value):
    assert path.is_relative_to(R)
    with path.open('x', encoding='utf-8', newline='\n') as out:
        json.dump(value, out, indent=2, allow_nan=False)
        out.write('\n'); out.flush(); os.fsync(out.fileno())

def folder(api, sid):
    function = api.userenv.GetAppContainerFolderPath
    function.argtypes = [W.LPCWSTR, C.POINTER(C.c_void_p)]
    function.restype = C.c_int32
    allocation = C.c_void_p()
    result = function(sid, C.byref(allocation))
    text = None
    try:
        if allocation.value:
            text = C.wstring_at(allocation)
            assert 0 < len(text) < 32768
    finally:
        if allocation.value:
            ole = C.WinDLL('ole32', use_last_error=True, winmode=0x800)
            ole.CoTaskMemFree.argtypes, ole.CoTaskMemFree.restype = [C.c_void_p], None
            ole.CoTaskMemFree(allocation)
    metadata = None
    if text:
        try:
            info = Path(text).lstat()
            metadata = {'exists': True, 'device': info.st_dev, 'inode': info.st_ino,
                        'attributes': info.st_file_attributes, 'mode': info.st_mode}
        except FileNotFoundError:
            metadata = {'exists': False}
    return {'api': 'GetAppContainerFolderPath', 'HRESULT': result, 'path': text,
            'folder_metadata': metadata, 'contents_read': False}

def user_sid(api):
    token = module.HANDLE()
    assert api.OpenProcessToken(api.GetCurrentProcess(), 8, C.byref(token))
    try:
        data = api.token_data(token, 1)
        return api.sid_text(module.SID_AND_ATTRIBUTES.from_buffer(data).sid)
    finally:
        api.close(token.value)

def inspect():
    api = module._IsolationAPI()
    assert user_sid(api) == USER and module.appcontainer_sid(NAME) == SID
    return {'observed_at': now(), 'name': NAME, 'SID': SID, 'user_sid': USER,
            'proposal_sha256': sha(PROPOSAL), 'prepared_script_sha256': sha(Path(__file__)),
            'candidate_manifest_sha256': MANIFEST, 'prior_folder': folder(api, SID),
            'capabilities': [], 'native_Create_or_Delete_executed': False,
            'activation_ready': False}

def source_cut():
    pins = read(F / '.agents/runtime/perf1-20261014/active-application/destination-full-r1.json')['after_hashes']
    current = {relative: observed(F / relative) for relative in pins}
    assert len(current) == 290 and {name: value['sha256'] for name, value in current.items()} == pins
    return current

def prepare_probe(directory):
    source = F / '.agents/runtime/ac1-20261014/native_fixture_support.py'
    body = source.read_text(encoding='utf-8')
    needle = "    name = 'CETA.AC1.' + uuid.uuid4().hex\n"
    assert body.count(needle) == 1
    body = body.replace(needle, '    name = ' + repr(NAME) + '\n')
    directory.mkdir(exist_ok=False)
    (directory / 'build-r2').mkdir()
    binary = F / '.agents/runtime/ac1-20261014/build-r2/isolated_worker.exe'
    assert sha(binary) == IMAGE
    with (directory / 'build-r2/isolated_worker.exe').open('xb') as out:
        out.write(binary.read_bytes())
    with (directory / 'native_fixture_support.py').open('x', encoding='utf-8', newline='\n') as out:
        out.write(body)
    spec = importlib.util.spec_from_file_location('profile_qualification_ac_support', R / 'ac2_support.py')
    support = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = support; spec.loader.exec_module(support)
    import types
    shim = types.ModuleType('ac_support')
    shim.__dict__.update({k: v for k, v in vars(support).items() if not k.startswith('_')})
    shim.R = shim.D = directory
    sys.modules['ac_support'] = shim
    spec = importlib.util.spec_from_file_location('profile_owned_native_probe', directory / 'native_fixture_support.py')
    helper = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = helper; spec.loader.exec_module(helper)
    save(directory / 'PROBE-BINDING.json', {'original_driver_sha256': sha(source),
        'prepared_driver_sha256': sha(directory / 'native_fixture_support.py'),
        'only_text_change': 'Replace fresh random profile name with exact approved reserved name.',
        'binary_sha256': IMAGE, 'Source_application': False})
    return helper

def assert_isolation(result):
    facts = result['facts']
    assert result['worker_exit_code'] == 0
    assert result['parent_token_facts']['appcontainer_sid'] == SID
    assert facts['token']['appcontainer_sid'] == SID and facts['token']['is_appcontainer'] == 1
    assert facts['token']['capability_count'] == 0 and facts['token']['restricted'] is True
    assert facts['token']['integrity'] == 'S-1-16-4096'
    assert facts['job_query'] == 1 and facts['job_member'] == 1
    assert facts['allowed_read']['granted'] is True and facts['scratch_write']['granted'] is True
    assert result['scratch_exists'] is True and result['protected_after'] == result['setup']['protected_before']
    for index in range(5):
        assert facts['denied_file_' + str(index)]['read']['granted'] is False
        assert facts['denied_file_' + str(index)]['write']['granted'] is False
    assert all(row['granted'] is False for row in facts['process_rights'].values())
    assert facts['hidden_event']['handle_query'] == facts['hidden_event']['signal'] == 0
    assert result['excluded_event_wait'] == 258
    assert facts['child']['created'] is False and facts['breakaway']['created'] is False
    assert all(facts[key]['granted'] is False for key in
        ('tcp_connect', 'tcp_loopback_listen', 'tcp_wildcard_listen', 'udp_loopback'))
    assert set(facts['environment_keys']) == {'SystemRoot', 'WINDIR', 'PATH', 'TEMP', 'TMP'}

def qualify(approval_path, approval_sha):
    assert approval_path.is_relative_to(R) and sha(approval_path) == approval_sha
    info = approval_path.lstat()
    assert stat.S_ISREG(info.st_mode) and not info.st_file_attributes & 0x400
    approval = read(approval_path)
    assert approval['profile_name'] == NAME and approval['profile_sid'] == SID and approval['user_sid'] == USER
    assert approval['proposal_sha256'] == sha(PROPOSAL) and approval['prepared_script_sha256'] == sha(Path(__file__))
    assert approval['create_exact_new_profile'] is True and approval['delete_only_profile_created_by_this_run'] is True
    assert approval['source'] == 'actual_current_human_reply' and type(approval['human_reply']) is str and approval['human_reply']
    directory = R / ('profile-qualification-' + uuid.uuid4().hex)
    helper = prepare_probe(directory)
    before = inspect()
    source_before = source_cut()
    save(directory / 'BEFORE.json', before)
    save(directory / 'SOURCE-BEFORE.json', source_before)
    assert before['prior_folder']['HRESULT'] in (-2147024894, -2147024893)
    api = module._IsolationAPI()
    create = api.userenv.CreateAppContainerProfile
    create.argtypes = [W.LPCWSTR, W.LPCWSTR, W.LPCWSTR, C.c_void_p, W.DWORD, C.POINTER(C.c_void_p)]
    create.restype = C.c_int32
    delete = api.userenv.DeleteAppContainerProfile
    delete.argtypes, delete.restype = [W.LPCWSTR], C.c_int32
    save(directory / 'CREATE-INTENT.json', {'recorded_at': now(), 'name': NAME, 'SID': SID,
        'approval_sha256': approval_sha, 'capabilities': [], 'candidate_manifest_sha256': MANIFEST})
    output = C.c_void_p()
    status = create(NAME, 'Project-AI: CETA isolated worker AC1',
        'Zero-capability local native worker isolation qualification', None, 0, C.byref(output))
    save(directory / 'CREATE-RETURN.json', {'recorded_at': now(), 'HRESULT': status,
        'returned_sid_pointer': output.value, 'created_this_run': status == 0,
        'preexisting_profiles_never_adopted_or_deleted': True})
    assert status == 0, 'Create failed or profile already exists; no adoption/deletion authorized.'
    assert output.value
    api.pending_sids.append(output.value)
    actual_sid = api.sid_text(output.value)
    api.release_sids()
    assert actual_sid == SID
    save(directory / 'CREATED.json', {'recorded_at': now(), 'name': NAME, 'actual_SID': actual_sid,
        'HRESULT': status, 'capabilities': [], 'approval_sha256': approval_sha})
    owners, apis, result, failure = [], [], None, None
    cleanup_status = 'NOT_REQUESTED'
    original_owner_init, original_api_init = WindowsOwnedProcess.__init__, module._IsolationAPI.__init__
    def owner_init(owner, *args, **kwargs):
        original_owner_init(owner, *args, **kwargs); owners.append(owner)
    def api_init(instance, *args, **kwargs):
        original_api_init(instance, *args, **kwargs); apis.append(instance)
    try:
        with patch.object(WindowsOwnedProcess, '__init__', owner_init), patch.object(module._IsolationAPI, '__init__', api_init):
            result = helper.run_native_probe('native-profile-r1', directory_read=True)
        assert_isolation(result)
    except BaseException as error:
        failure = {'type': type(error).__name__, 'text': str(error),
                   'native_receipt': getattr(error, 'native_probe_receipt', None)}
    finally:
        custody = [{'pid': owner.pid, 'creation_time': owner.creation_time,
                    'lifetime_closed': owner.lifetime_closed, 'job_closed': owner._job is None,
                    'process_closed': owner._process is None, 'thread_closed': owner._thread is None}
                   for owner in owners]
        residual = [list(instance.pending_native_resources()) for instance in apis]
        probe_receipt = result
        if probe_receipt is None and failure is not None and failure['native_receipt']:
            receipt_path = Path(failure['native_receipt'])
            assert receipt_path.is_relative_to(directory)
            info = receipt_path.lstat()
            assert stat.S_ISREG(info.st_mode) and not info.st_file_attributes & 0x400
            probe_receipt = read(receipt_path)
        helper_retirement_recorded = probe_receipt is not None and 'cleanup' in probe_receipt
        control_cleanup_clear = helper_retirement_recorded and all(
            'cleanup_failure' not in row and 'native_handle_cleanup_failure' not in row
            for row in probe_receipt['cleanup'])
        retired = (control_cleanup_clear and all(all(row[key] for key in
            ('lifetime_closed', 'job_closed', 'process_closed', 'thread_closed')) for row in custody)
            and not any(residual))
        save(directory / 'RETIREMENT.json', {'recorded_at': now(), 'custody': custody,
            'pending_native_resources': residual, 'all_captured_resources_retired': retired,
            'helper_retirement_recorded': helper_retirement_recorded,
            'control_cleanup_clear': control_cleanup_clear, 'qualification_failure': failure})
        if retired:
            assert read(directory / 'CREATED.json')['actual_SID'] == SID
            assert module.appcontainer_sid(NAME) == SID and user_sid(api) == USER
            deleted = delete(NAME)
            save(directory / 'DELETE-RETURN.json', {'recorded_at': now(), 'name': NAME, 'SID': SID,
                'HRESULT': deleted, 'created_this_run_receipt_sha256': sha(directory / 'CREATED.json'),
                'actual_retirement_receipt_sha256': sha(directory / 'RETIREMENT.json')})
            post = folder(api, SID)
            cleanup_status = ('DELETE_SUCCEEDED_AND_FOLDER_ABSENCE_OBSERVED' if deleted == 0
                and post['HRESULT'] in (-2147024894, -2147024893) and post['path'] is None
                else 'DELETE_REQUEST_RESULT_OR_RESIDUAL_REQUIRES_INSPECTION')
            save(directory / 'POST-DELETE-OBSERVATION.json', {'recorded_at': now(), 'native_delete_HRESULT': deleted,
                'folder_observation': post, 'cleanup_status': cleanup_status,
                'contents_read': False, 'recursive_delete_executed': False,
                'registry_or_perfect_erasure_claim': False})
        else:
            save(directory / 'PROFILE-RETAINED.json', {'recorded_at': now(),
                'reason': 'Captured process/handle/allocation retirement unresolved; profile deletion refused.', 'name': NAME, 'SID': SID})
    source_after = source_cut()
    save(directory / 'SOURCE-AFTER.json', source_after)
    source_conserved = source_before == source_after
    save(directory / 'RESULT.json', {'recorded_at': now(), 'positive_isolation_qualified': failure is None,
        'failure': failure, 'Source_application': False, 'canonical_real_effect_accepted': False,
        'receipts': str(directory), 'all_captured_resources_retired': retired, 'profile_cleanup_status': cleanup_status,
        'Source290_native_and_hash_conserved': source_conserved})
    print(json.dumps({'receipts': str(directory), 'positive_isolation_qualified': failure is None,
                      'all_captured_resources_retired': retired, 'failure': failure,
                      'profile_cleanup_status': cleanup_status}), flush=True)
    return 0 if failure is None and retired and source_conserved and cleanup_status == 'DELETE_SUCCEEDED_AND_FOLDER_ABSENCE_OBSERVED' else 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('inspect', 'qualify'), required=True)
    parser.add_argument('--approval-receipt', type=Path)
    parser.add_argument('--approval-sha256')
    args = parser.parse_args()
    if args.mode == 'inspect':
        assert args.approval_receipt is None and args.approval_sha256 is None
        facts = inspect()
        save(R / ('PROFILE-INSPECTION-' + uuid.uuid4().hex + '.json'), facts)
        print(json.dumps(facts, indent=2))
    else:
        assert args.approval_receipt is not None and args.approval_sha256 is not None
        sys.exit(qualify(args.approval_receipt, args.approval_sha256))
