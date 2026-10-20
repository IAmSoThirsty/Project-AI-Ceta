"""Exact operator-side profile qualification; imports/inspect never create a profile.

The CLI requires a separately preserved actual operator reply for Create and
own-profile cleanup. This engineering tool does not issue CETA authority.
"""
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch
from ctypes import wintypes as W
import argparse, ctypes as C, hashlib, importlib.util, json, os, stat, sys, types, uuid

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
ORIGINAL_R = F / '.agents/runtime/ac5-profile-tool-20261015'
assert R == F / '.agents/runtime/ac6-profile-preparation-20261018'
Q = F  # The execution view is the canonical published source, not a private candidate.
PY = F / '.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
NAME = 'CETA.ProjectAICETA.IsolatedWorker.AC1.V1'
SID = 'S-1-15-2-695244707-3853392321-2130098501-3319658173-178928504-1880712989-1319207162'
USER = 'S-1-5-21-1218874621-2294869469-207301144-1003'
MANIFEST = 'b22b2f404a8373be3eb7bcd2ab9c974f5dba187aed2c787fb62f54fac7508a87'
IMAGE = '527518104fb84c430e3e9e0be61982c533b0c6fbb13e1a85e959ba1a3866ad0f'
PROPOSAL = R / 'PROFILE-CREATION-PROPOSAL-AC6.json'
SOURCE_BASELINE = F / '.agents/runtime/js8-20261015/amendment-report1/active-application/APPLIED.json'
SOURCE_BASELINE_SHA = 'b22b2f404a8373be3eb7bcd2ab9c974f5dba187aed2c787fb62f54fac7508a87'
DEPENDENCIES = {'.agents/runtime/ac1-20261014/native_fixture_support.py': {'sha256': 'a7247426deee70890107b9d826c7cda9209015edd5f1192f93ee3bd1e5a4314f', 'native_identity': {'bytes': 11669, 'mtime_ns': 1792014367595050300, 'mode': 438, 'device': 154504856318070761, 'inode': 281474979591669, 'attributes': 32}}, '.agents/runtime/ac3-20261014/ac3_support.py': {'sha256': 'cb44b9f5d4cc50764b486181ad01c41bfee970e91af64338481134c42640096b', 'native_identity': {'bytes': 4455, 'mtime_ns': 1792022240997454800, 'mode': 438, 'device': 154504856318070761, 'inode': 1125899909775469, 'attributes': 32}}, '.agents/runtime/ac1-20261014/build-r2/isolated_worker.exe': {'sha256': '527518104fb84c430e3e9e0be61982c533b0c6fbb13e1a85e959ba1a3866ad0f', 'native_identity': {'bytes': 4872045, 'mtime_ns': 1792013561672587700, 'mode': 511, 'device': 154504856318070761, 'inode': 562949956302187, 'attributes': 32}}}

digest = lambda payload: hashlib.sha256(payload).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()

def require(value, text):
    if not value: raise AssertionError(text)

require(os.name == 'nt' and not sys.flags.optimize and Path(sys.executable) == PY, 'EXACT_UNOPTIMIZED_WINDOWS_E3_REQUIRED')
sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
reader = F / '.agents/pr4-20261014/preserve_ceta_complete.py'
require(digest(reader.read_bytes()) == '2ccbca31973ead308e1cdcc6676bbd7371cdec29a0f16178f3f55a4ab4130618', 'NATIVE_READER_PIN_MISMATCH')
spec = importlib.util.spec_from_file_location('profile_r2_native_reader', reader)
fs = importlib.util.module_from_spec(spec); sys.modules[spec.name] = fs; spec.loader.exec_module(fs)

def capture(path, expected_sha=None, expected_native=None):
    """One captured payload, bracketed by qualified native identity observations."""
    path = fs.safe_components(Path(path))
    info = fs.lstat(path)
    require(stat.S_ISREG(info.st_mode) and not fs.reparse(info), 'ORDINARY_NONREPARSE_FILE_REQUIRED')
    before = fs.file_identity(info)
    if expected_native is not None: require(before == expected_native, 'DEPENDENCY_NATIVE_IDENTITY_CHANGED')
    payload = fs.read_bytes(path)
    after = fs.file_identity(fs.lstat(path))
    pin = digest(payload)
    require(before == after and len(payload) == before['bytes'], 'NATIVE_FILE_CHANGED_DURING_CAPTURE')
    if expected_sha is not None: require(pin == expected_sha, 'CAPTURED_PAYLOAD_HASH_MISMATCH')
    return payload, {'sha256': pin, 'native_identity': after}

def observed(path): return capture(path)[1]
def read(path): return json.loads(capture(path)[0].decode('utf-8-sig'))
def sha(path): return capture(path)[1]['sha256']
def save(path, value):
    path = Path(path)
    require(path.is_relative_to(R), 'OWNED_EVIDENCE_PATH_REQUIRED')
    fs.safe_components(path.parent)
    with path.open('x', encoding='utf-8', newline='\n') as output:
        json.dump(value, output, indent=2, allow_nan=False)
        output.write('\n'); output.flush(); os.fsync(output.fileno())

def write_payload(path, payload, expected_sha):
    require(digest(payload) == expected_sha, 'WRITE_PAYLOAD_PIN_MISMATCH')
    fs.safe_components(path.parent)
    with path.open('xb') as output:
        output.write(payload); output.flush(); os.fsync(output.fileno())
    _, facts = capture(path, expected_sha)
    return facts

capture(PY, '0b471133e110cfb53a061cad528ce8e517d7b9ac41a0a396c39ad795a487fc14')
capture(PY.parent.parent / 'pyvenv.cfg', 'd471caff87816219aa10a2ee14142f300327d54746744b67ab517dff51cf58fa')
manifest_payload, _ = capture(SOURCE_BASELINE, MANIFEST)
capture(PROPOSAL, 'aa849834a68cd670928ea8f17dc446a50354442b2dbd658ed8889c0cdc982f49')
FROZEN = json.loads(manifest_payload.decode('utf-8-sig'))['source352']
require(len(FROZEN) == 352, 'SOURCE352_EXECUTION_VIEW_REQUIRED')
for relative, facts in FROZEN.items(): capture(Q / relative, facts['sha256'], facts['native_identity'])
for relative, facts in DEPENDENCIES.items(): capture(F / relative, facts['sha256'], facts['native_identity'])
sys.path.insert(0, str(Q / 'src'))
from ceta.supervisor import isolated_worker as module
from ceta.supervisor.windows_jobs import WindowsOwnedProcess

def source_cut():
    payload, _ = capture(SOURCE_BASELINE, SOURCE_BASELINE_SHA)
    pins = json.loads(payload.decode('utf-8-sig'))['source352']
    require(len(pins) == 352, 'SOURCE352_REQUIRED')
    return {relative: capture(F / relative, facts['sha256'], facts['native_identity'])[1] for relative, facts in pins.items()}

def candidate_cut():
    capture(SOURCE_BASELINE, MANIFEST)
    return {relative: capture(Q / relative, facts['sha256'], facts['native_identity'])[1]
            for relative, facts in FROZEN.items()}

def folder(api, sid):
    function = api.userenv.GetAppContainerFolderPath
    function.argtypes, function.restype = [W.LPCWSTR, C.POINTER(C.c_void_p)], C.c_int32
    ole = C.WinDLL('ole32', use_last_error=True, winmode=0x800)
    ole.CoTaskMemFree.argtypes, ole.CoTaskMemFree.restype = [C.c_void_p], None
    allocation, row, primary = C.c_void_p(), None, None
    try:
        result = function(sid, C.byref(allocation))
        if allocation.value:
            row = {'kind': 'folder_path', 'address': allocation.value, 'state': 'OWNED'}
            api._profile_folder_outputs = getattr(api, '_profile_folder_outputs', []) + [row]
        text = C.wstring_at(allocation) if allocation.value else None
        require(text is None or 0 < len(text) < 32768, 'PROFILE_FOLDER_PATH_BOUND')
    except BaseException as error:
        primary = error
        raise
    finally:
        if allocation.value:
            if row is None:
                row = {'kind': 'folder_path', 'address': allocation.value, 'state': 'UNCERTAIN'}
                api._profile_folder_outputs = getattr(api, '_profile_folder_outputs', []) + [row]
            row['state'] = 'RELEASE_UNCERTAIN'
            try:
                ole.CoTaskMemFree(allocation)
                api._profile_folder_outputs.remove(row)
            except BaseException as cleanup_error:
                if primary is None: raise
                try: primary.profile_folder_cleanup_error = cleanup_error
                except BaseException: pass
    metadata = None
    if text:
        try:
            info = Path(text).lstat()
            metadata = {'exists': True, 'device': info.st_dev, 'inode': info.st_ino,
                        'attributes': info.st_file_attributes, 'mode': info.st_mode}
        except FileNotFoundError: metadata = {'exists': False}
    return {'api': 'GetAppContainerFolderPath', 'HRESULT': result, 'path': text,
            'folder_metadata': metadata, 'contents_read': False}

def user_sid(api):
    token = module.HANDLE()
    primary = None
    try:
        ok = api.OpenProcessToken(api.GetCurrentProcess(), 8, C.byref(token))
        if token.value: api.queue_handle(token.value)
        require(ok and token.value, 'CALLER_TOKEN_UNAVAILABLE')
        data = api.token_data(token, 1)
        return api.sid_text(module.SID_AND_ATTRIBUTES.from_buffer(data).sid)
    except BaseException as error:
        primary = error
        raise
    finally:
        if token.value: api.queue_handle(token.value)
        try: api.retry_cleanup(kinds=('handles', 'strings', 'sids'))
        except BaseException as cleanup_error:
            if primary is None: raise
            try: primary.profile_token_cleanup_error = cleanup_error
            except BaseException: pass

def inspect():
    api = module._IsolationAPI()
    require(user_sid(api) == USER and module.appcontainer_sid(NAME) == SID, 'CALLER_OR_PROFILE_IDENTITY_CHANGED')
    return {'observed_at': now(), 'name': NAME, 'SID': SID, 'user_sid': USER,
            'proposal_sha256': sha(PROPOSAL), 'prepared_script_sha256': sha(Path(__file__)),
            'candidate_manifest_sha256': MANIFEST, 'prior_folder': folder(api, SID),
            'capabilities': [], 'native_Create_or_Delete_executed': False, 'activation_ready': False}


def _native_path(path, *, directory):
    """Observe one owned ordinary path; the existing API retains handle cleanup."""
    path = fs.safe_components(Path(path))
    require(path.is_relative_to(R), 'OWNED_PROBE_PATH_REQUIRED')
    info = fs.lstat(path)
    require((stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            and not fs.reparse(info), 'ORDINARY_PROBE_PATH_REQUIRED')
    api, primary = module._IsolationAPI(), None
    try:
        handle = api.CreateFileW(str(path), 0x80, 3, None, 3,
                                0x00200000 | (0x02000000 if directory else 0), None)
        require(handle not in (None, 0, module.INVALID_HANDLE), 'PROBE_PATH_HANDLE_UNAVAILABLE')
        api.queue_handle(handle)
        return api.native_volume_path(handle)
    except BaseException as error:
        primary = error
        raise
    finally:
        module._finish_cleanup(api, primary)

def check_launch_paths(directory, image=None):
    base = _native_path(directory, directory=True)
    predicted = image is None
    native_directory = base + '\\native-fixtures\\ac1-' + '0' * 32 if predicted else base
    native_image = native_directory + '\\assets\\isolated_worker.exe' if predicted else _native_path(image, directory=False)
    require(len(native_directory) < 258 and len(native_image) < 258, 'PROBE_NATIVE_PATH_TOO_LONG')
    facts = {'at': now(), 'native_directory': native_directory, 'native_image': native_image,
             'native_directory_length': len(native_directory), 'native_image_length': len(native_image),
             'predicted_fixture_suffix': predicted, 'limit_exclusive': 258,
             'qualification_claim': False, 'missing_profile_causality_claim': False}
    save(Path(directory) / ('PATH-LAYOUT.json' if predicted else 'LAUNCH-PATHS.json'), facts)
    return facts

def prepare_probe(directory, *, owned_identity=None):
    """Execute only verified, single-capture helper bytes and pin every copied image."""
    if owned_identity is None:
        directory.mkdir(exist_ok=False)
    else:
        current = fs.file_identity(fs.lstat(fs.safe_components(directory)))
        require(all(current[key] == owned_identity[key] for key in ('device', 'inode', 'mode', 'attributes')),
                'OWNED_DIRECTORY_IDENTITY_CHANGED')
    fs.safe_components(directory)
    captured = {name: capture(F / name, facts['sha256'], facts['native_identity'])
                for name, facts in DEPENDENCIES.items()}
    driver_name = '.agents/runtime/ac1-20261014/native_fixture_support.py'
    support_name = '.agents/runtime/ac3-20261014/ac3_support.py'
    image_name = '.agents/runtime/ac1-20261014/build-r2/isolated_worker.exe'
    original = captured[driver_name][0].decode('utf-8').replace('\r\n', '\n')
    needle = "    name = 'CETA.AC1.' + uuid.uuid4().hex\n"
    require(original.count(needle) == 1, 'EXACT_DRIVER_NAME_TRANSFORM_REQUIRED')
    body = original.replace(needle, '    name = ' + repr(NAME) + '\n')
    copy_needle = '    fs.write_new(image, fs.read_bytes(original))\n'
    require(body.count(copy_needle) == 1 and body.count('expected_image_sha256=sha(image)') == 2,
            'EXACT_DRIVER_IMAGE_TRANSFORM_REQUIRED')
    body = body.replace(copy_needle, copy_needle + '    assert sha(image) == ' + repr(IMAGE) + '\n')
    body = body.replace('expected_image_sha256=sha(image)', 'expected_image_sha256=' + repr(IMAGE))
    check_launch_paths(directory)
    probe_needle = '    control, api = _ControlApi(), _IsolationAPI()\n'
    require(body.count(probe_needle) == 1, 'PROBE_PATH_GUARD_BINDING_CHANGED')
    body = body.replace(probe_needle, '    check_launch_paths(fixture, image)\n' + probe_needle)
    driver_payload = body.encode('utf-8')
    (directory / 'build-r2').mkdir()
    image_copy = write_payload(directory / 'build-r2/isolated_worker.exe', captured[image_name][0], IMAGE)
    driver_copy = write_payload(directory / 'native_fixture_support.py', driver_payload, digest(driver_payload))
    support_copy = write_payload(directory / 'ac3_support.py', captured[support_name][0], DEPENDENCIES[support_name]['sha256'])
    support = types.ModuleType('profile_r2_captured_ac_support')
    support.__file__ = str(directory / 'ac3_support.py')
    sys.modules[support.__name__] = support
    exec(compile(captured[support_name][0], support.__file__, 'exec'), support.__dict__)
    shim = types.ModuleType('ac_support')
    shim.__dict__.update({key: value for key, value in vars(support).items() if not key.startswith('_')})
    support.Q, support.R, support.D = Q, directory, directory
    def owned_write_new(path, value):
        require(Path(path).is_relative_to(directory), 'OWNED_PROBE_EVIDENCE_REQUIRED')
        save(path, value)
    support.write_new = shim.write_new = owned_write_new
    shim.Q, shim.R, shim.D = Q, directory, directory
    sys.modules['ac_support'] = shim
    helper = types.ModuleType('profile_r2_captured_native_probe')
    helper.__file__ = str(directory / 'native_fixture_support.py')
    helper.check_launch_paths = check_launch_paths
    sys.modules[helper.__name__] = helper
    exec(compile(driver_payload, helper.__file__, 'exec'), helper.__dict__)
    save(directory / 'PROBE-BINDING.json', {'captured_dependencies': {
        name: facts for name, (_, facts) in captured.items()}, 'image_copy': image_copy,
        'driver_copy': driver_copy, 'support_copy': support_copy,
        'transforms': ['Normalize driver CRLF to LF if present', 'Use exact reserved profile name',
            'Check projected native path lengths before profile creation; actual native paths before launch',
            'Verify copied fixture image equals IMAGE', 'Both launches require fixed IMAGE, not a freshly computed hash'],
        'imports_execute_captured_verified_bytes': True, 'binary_sha256': IMAGE, 'Source_application': False})
    return helper

def assert_isolation(result):
    facts = result['facts']
    require(result['worker_exit_code'] == 0 and result['parent_token_facts']['appcontainer_sid'] == SID, 'WORKER_EXIT_OR_PARENT_TOKEN')
    require(facts['token']['appcontainer_sid'] == SID and facts['token']['is_appcontainer'] == 1
            and facts['token']['capability_count'] == 0 and facts['token']['restricted'] is True
            and facts['token']['integrity'] == 'S-1-16-4096', 'ACTUAL_ISOLATION_TOKEN_REQUIRED')
    require(facts['job_query'] == 1 and facts['job_member'] == 1, 'ACTUAL_JOB_MEMBERSHIP_REQUIRED')
    require(facts['allowed_read']['granted'] is True and facts['scratch_write']['granted'] is True
            and result['scratch_exists'] is True and result['protected_after'] == result['setup']['protected_before'], 'ACTUAL_ASSET_SCRATCH_PROTECTION_REQUIRED')
    require(all(facts['denied_file_' + str(index)][mode]['granted'] is False
                for index in range(5) for mode in ('read', 'write')), 'PROTECTED_SENTINELS_MUST_DENY')
    require(all(row['granted'] is False for row in facts['process_rights'].values()), 'PROCESS_RIGHTS_MUST_DENY')
    require(facts['hidden_event']['handle_query'] == facts['hidden_event']['signal'] == 0
            and result['excluded_event_wait'] == 258, 'EXCLUDED_HANDLE_MUST_DENY')
    require(facts['child']['created'] is False and facts['breakaway']['created'] is False, 'CHILD_CREATION_MUST_DENY')
    require(all(facts[key]['granted'] is False for key in
        ('tcp_connect', 'tcp_loopback_listen', 'tcp_wildcard_listen', 'udp_loopback')), 'NETWORK_MUST_DENY')
    require(set(facts['environment_keys']) == {'SystemRoot', 'WINDIR', 'PATH', 'TEMP', 'TMP', 'LOCALAPPDATA'}, 'BOUNDED_ENVIRONMENT_REQUIRED')

def describe(error):
    try: text = str(error)
    except BaseException: text = '<exception text unavailable>'
    result = {'type': type(error).__name__, 'text': text}
    try:
        measured = BaseException.__dict__['__dict__'].__get__(error).get('native_isolation_token_observation')
        if measured is not None:
            allowed = {'schema', 'classification', 'stage', 'is_appcontainer_dword',
                'appcontainer_sid_matches_expected', 'capability_count', 'integrity_sid',
                'appcontainer_sid', 'integrity_rid', 'is_token_restricted', 'observed_monotonic_ns'}
            require(type(measured) is dict and set(measured) <= allowed and
                measured.get('schema') == 'ceta-rejected-isolation-token-v1' and
                measured.get('classification') == 'REJECTED_NATIVE_OBSERVATION', 'TOKEN_DIAGNOSTIC_SHAPE_INVALID')
            require(all(type(value) is bool or type(value) is int and -(2**63) <= value < 2**64
                or type(value) is str and len(value) <= 256 for value in measured.values()), 'TOKEN_DIAGNOSTIC_VALUE_BOUND')
            result['native_isolation_token_observation'] = dict(measured)
    except BaseException as diagnostic_error:
        result['token_diagnostic_capture_failure'] = {'type': type(diagnostic_error).__name__,
            'classification': 'DIAGNOSTIC_UNAVAILABLE_PRIMARY_PRESERVED'}
    return result

class _QualificationRun:
    """Private custody owner. Only qualify validates actual operator provenance."""
    def __init__(self, directory, approval_sha):
        self.directory, self.approval_sha = directory, approval_sha
        self.primary_error, self.errors, self.journal_errors = None, [], []
        self.apis, self.owners, self.creator = [], [], None
        self.output, self.create_status = C.c_void_p(), None
        self.create_called, self.created_this_run, self.sid_verified, self.created_recorded = False, False, False, False
        self.unknown_output_pointer, self.helper_started = False, False
        self.result, self.probe_receipt, self.retirement = None, None, None
        self.source_before, self.candidate_before = None, None
        self.source_conserved, self.candidate_conserved = False, False
        self.positive_isolation_qualified, self.retired = False, False
        self.cleanup_status, self.delete_called = 'NOT_REQUESTED', False
        self.phase, self.final_report = 'PREPARING', None
        self.directory_identity = None

    def fail(self, error, stage):
        if self.primary_error is None: self.primary_error = error
        self.errors.append({'stage': stage, **describe(error)})

    def record(self, name, value, *, critical=False):
        try:
            require(self.directory_identity is not None, 'EVIDENCE_DIRECTORY_NOT_OWNED')
            current = fs.file_identity(fs.lstat(fs.safe_components(self.directory)))
            require(all(current[key] == self.directory_identity[key] for key in ('device', 'inode', 'mode', 'attributes')),
                    'EVIDENCE_DIRECTORY_IDENTITY_CHANGED')
            save(self.directory / name, value)
            return True
        except BaseException as error:
            self.journal_errors.append({'file': name, **describe(error)})
            self.fail(error, 'journal:' + name)
            if critical: raise
            return False

    def api_init(self, original, instance, *args, **kwargs):
        self.apis.append(instance)
        original(instance, *args, **kwargs)

    def owner_init(self, original, owner, *args, **kwargs):
        self.owners.append(owner)
        original(owner, *args, **kwargs)

    def effect(self):
        helper = prepare_probe(self.directory, owned_identity=self.directory_identity)
        before = inspect()
        self.source_before, self.candidate_before = source_cut(), candidate_cut()
        self.record('BEFORE.json', before, critical=True)
        self.record('SOURCE-BEFORE.json', self.source_before, critical=True)
        self.record('CANDIDATE-BEFORE.json', self.candidate_before, critical=True)
        prior = before['prior_folder']
        require(prior['HRESULT'] in (-2147024894, -2147024893) and prior['path'] is None,
                'PREEXISTING_OR_UNKNOWN_PROFILE_REFUSED')
        self.creator = module._IsolationAPI()
        create = self.creator.userenv.CreateAppContainerProfile
        create.argtypes = [W.LPCWSTR, W.LPCWSTR, W.LPCWSTR, C.c_void_p, W.DWORD, C.POINTER(C.c_void_p)]
        create.restype = C.c_int32
        self.record('CREATE-INTENT.json', {'at': now(), 'name': NAME, 'SID': SID,
            'approval_sha256': self.approval_sha, 'capabilities': [], 'candidate_manifest_sha256': MANIFEST}, critical=True)
        self.phase, self.create_called = 'CREATE_IN_FLIGHT', True
        try:
            self.create_status = create(NAME, 'Project-AI: CETA isolated worker AC1',
                'Zero-capability local native worker isolation qualification', None, 0, C.byref(self.output))
            self.created_this_run = type(self.create_status) is int and self.create_status == 0
        finally:
            # Register before any logging, conversion or further fallible call.
            if self.output.value:
                if self.created_this_run:
                    self.creator.pending_sids.append(self.output.value)
                else: self.unknown_output_pointer = True
        self.phase = 'CREATE_RETURNED'
        self.record('CREATE-RETURN.json', {'at': now(), 'HRESULT': self.create_status,
            'returned_sid_pointer': self.output.value, 'created_this_run': self.created_this_run,
            'unknown_output_pointer': self.unknown_output_pointer,
            'preexisting_profiles_never_adopted_or_deleted': True}, critical=True)
        require(self.created_this_run, 'CREATE_FAILED_OR_ALREADY_EXISTS_NO_ADOPTION')
        require(self.output.value, 'SUCCESSFUL_CREATE_RETURNED_NO_SID_POINTER')
        actual_sid = self.creator.sid_text(self.output.value)
        require(actual_sid == SID, 'CREATED_SID_MISMATCH')
        self.sid_verified = True
        self.creator.retry_cleanup()
        self.created_recorded = self.record('CREATED.json', {'at': now(), 'name': NAME,
            'actual_SID': actual_sid, 'HRESULT': self.create_status, 'capabilities': [],
            'approval_sha256': self.approval_sha}, critical=True)
        self.phase, self.helper_started = 'PROBE_IN_FLIGHT', True
        self.result = helper.run_native_probe('native-profile-r2', directory_read=True)
        self.probe_receipt = self.result
        assert_isolation(self.result)
        self.positive_isolation_qualified = True
        self.phase = 'PROBE_RETURNED'

    def capture_failure_receipt(self, error):
        try:
            path = getattr(error, 'native_probe_receipt', None)
            if path:
                path = fs.safe_components(Path(path))
                require(path.resolve(strict=True).is_relative_to(self.directory.resolve(strict=True)), 'FOREIGN_NATIVE_RECEIPT_REFUSED')
                self.probe_receipt = read(path)
        except BaseException as secondary: self.fail(secondary, 'failure_receipt')

    def retire(self):
        identity_current = False
        if self.created_this_run and self.sid_verified and self.created_recorded:
            try:
                require(read(self.directory / 'CREATED.json')['actual_SID'] == SID, 'CREATION_RECEIPT_BINDING_CHANGED')
                require(module.appcontainer_sid(NAME) == SID and user_sid(self.creator) == USER, 'DELETE_IDENTITY_CHANGED')
                identity_current = True
            except BaseException as error: self.fail(error, 'delete_identity_guard')
        custody, residual = [], []
        for owner in self.owners:
            try:
                if not owner.lifetime_closed:
                    if owner.poll() is None: owner.terminate(125)
                    require(owner.wait(5), 'OWNED_LIFETIME_RETIREMENT_UNOBSERVED')
                    require(owner.poll() is not None and owner.active_process_count() == 0, 'OWNED_JOB_NOT_EMPTY')
                    owner.close()
                row = {'pid': owner.pid, 'creation_time': owner.creation_time,
                    'lifetime_closed': owner.lifetime_closed, 'job_closed': owner._job is None,
                    'process_closed': owner._process is None, 'thread_closed': owner._thread is None}
                custody.append(row)
            except BaseException as error:
                self.fail(error, 'owner_retirement'); custody.append({'unresolved': describe(error)})
        for api in self.apis:
            try: api.retry_cleanup()
            except BaseException as error: self.fail(error, 'native_API_cleanup')
            try:
                pending = list(api.pending_native_resources()) + list(getattr(api, '_profile_folder_outputs', []))
                residual.append(pending)
            except BaseException as error:
                self.fail(error, 'native_API_residual_observation'); residual.append([{'unresolved': describe(error)}])
        cleanup = self.probe_receipt.get('cleanup') if isinstance(self.probe_receipt, dict) else None
        helper_clear = (not self.helper_started or type(cleanup) is list and all(
            type(row) is dict and 'cleanup_failure' not in row and 'native_handle_cleanup_failure' not in row for row in cleanup))
        closed = all('unresolved' not in row and all(row[key] is True for key in
            ('lifetime_closed', 'job_closed', 'process_closed', 'thread_closed')) for row in custody)
        self.retired = helper_clear and closed and not any(residual) and not self.unknown_output_pointer
        self.retirement = {'at': now(), 'custody': custody, 'pending_native_resources': residual,
            'unknown_create_output_pointer': self.output.value if self.unknown_output_pointer else None,
            'helper_started': self.helper_started, 'helper_retirement_recorded': type(cleanup) is list,
            'control_cleanup_clear': helper_clear, 'all_captured_resources_retired': self.retired}
        retirement_recorded = self.record('RETIREMENT.json', self.retirement)
        if not (identity_current and self.created_this_run and self.sid_verified and self.created_recorded and self.retired and retirement_recorded):
            self.cleanup_status = 'RETAINED_OR_UNKNOWN_PROFILE_NO_DELETE'
            return
        try:
            require(not self.creator.pending_native_resources() and not getattr(self.creator, '_profile_folder_outputs', []), 'DELETE_CALLER_RESOURCES_NOT_RETIRED')
            self.record('DELETE-INTENT.json', {'at': now(), 'name': NAME, 'SID': SID,
                'created_this_run_receipt_sha256': sha(self.directory / 'CREATED.json'),
                'retirement_receipt_sha256': sha(self.directory / 'RETIREMENT.json')}, critical=True)
            delete = self.creator.userenv.DeleteAppContainerProfile
            delete.argtypes, delete.restype = [W.LPCWSTR], C.c_int32
            self.phase, self.delete_called = 'DELETE_IN_FLIGHT', True
            status = delete(NAME)
            self.cleanup_status = 'DELETE_RETURNED_STATE_NOT_YET_OBSERVED'
            self.record('DELETE-RETURN.json', {'at': now(), 'name': NAME, 'SID': SID, 'HRESULT': status})
            post = folder(self.creator, SID)
            self.cleanup_status = ('DELETE_SUCCEEDED_AND_FOLDER_ABSENCE_OBSERVED'
                if type(status) is int and status == 0 and post['HRESULT'] in (-2147024894, -2147024893) and post['path'] is None
                else 'DELETE_REQUEST_RESULT_OR_RESIDUAL_REQUIRES_INSPECTION')
            self.record('POST-DELETE-OBSERVATION.json', {'at': now(), 'native_delete_HRESULT': status,
                'folder_observation': post, 'cleanup_status': self.cleanup_status, 'contents_read': False,
                'recursive_delete_executed': False, 'registry_or_perfect_erasure_claim': False})
        except BaseException as error:
            self.fail(error, 'delete_or_post_delete_observation')
            self.cleanup_status = 'DELETE_OR_OBSERVATION_UNRESOLVED' if self.delete_called else 'RETAINED_PROFILE_DELETE_GUARD_FAILED'

    def final_observations(self):
        final_pending = []
        for api in self.apis:
            try:
                final_pending.append(list(api.pending_native_resources()) + list(getattr(api, '_profile_folder_outputs', [])))
            except BaseException as error:
                self.fail(error, 'final_API_residual_observation')
                final_pending.append([{'unresolved': describe(error)}])
        self.retired = self.retired and not any(final_pending)
        if self.retirement is not None:
            self.retirement = dict(self.retirement, post_delete_API_resources=final_pending,
                all_captured_resources_retired_after_final_observation=self.retired)
        for name, function, before, flag in (
            ('SOURCE-AFTER.json', source_cut, self.source_before, 'source_conserved'),
            ('CANDIDATE-AFTER.json', candidate_cut, self.candidate_before, 'candidate_conserved')):
            try:
                after = function()
                setattr(self, flag, before is not None and before == after)
                self.record(name, after)
            except BaseException as error: self.fail(error, name)
        self.record('PROFILE-STATE.json', {'at': now(), 'name': NAME, 'SID': SID,
            'create_called': self.create_called, 'create_HRESULT': self.create_status,
            'created_this_run': self.created_this_run, 'exact_returned_SID_verified': self.sid_verified,
            'delete_called': self.delete_called, 'cleanup_status': self.cleanup_status,
            'state_after_exception_requires_operator_inspection': self.cleanup_status != 'DELETE_SUCCEEDED_AND_FOLDER_ABSENCE_OBSERVED'})
        if self.cleanup_status != 'DELETE_SUCCEEDED_AND_FOLDER_ABSENCE_OBSERVED':
            self.record('PROFILE-RETAINED-OR-UNKNOWN.json', {'at': now(), 'name': NAME, 'SID': SID,
                'created_this_run': self.created_this_run, 'create_called': self.create_called,
                'cleanup_status': self.cleanup_status, 'reason': 'Deletion refused or unobserved; preserve profile and inspect exact recorded state.'})

    def snapshot(self):
        return {'at': now(), 'name': NAME, 'SID': SID, 'receipts': str(self.directory),
            'phase': self.phase, 'primary_failure': None if self.primary_error is None else describe(self.primary_error),
            'failures': list(self.errors), 'journal_errors': list(self.journal_errors),
            'created_this_run': self.created_this_run, 'exact_returned_SID_verified': self.sid_verified,
            'delete_called': self.delete_called, 'profile_cleanup_status': self.cleanup_status,
            'positive_isolation_qualified': self.positive_isolation_qualified,
            'all_captured_resources_retired': self.retired, 'retirement': self.retirement,
            'Source352_native_and_hash_conserved': self.source_conserved,
            'execution_source352_native_and_hash_conserved': self.candidate_conserved,
            'Source_application': False, 'canonical_real_effect_accepted': False}

    def execute(self):
        original_api, original_owner = module._IsolationAPI.__init__, WindowsOwnedProcess.__init__
        def api_init(instance, *args, **kwargs): self.api_init(original_api, instance, *args, **kwargs)
        def owner_init(instance, *args, **kwargs): self.owner_init(original_owner, instance, *args, **kwargs)
        with patch.object(module._IsolationAPI, '__init__', api_init), patch.object(WindowsOwnedProcess, '__init__', owner_init):
            try:
                self.directory.mkdir(exist_ok=False)
                self.directory_identity = fs.file_identity(fs.lstat(fs.safe_components(self.directory)))
                self.effect()
            except BaseException as error:
                self.fail(error, self.phase); self.capture_failure_receipt(error)
            finally:
                try: self.retire()
                except BaseException as error:
                    self.fail(error, 'outer_retirement'); self.cleanup_status = 'RETAINED_OR_UNKNOWN_PROFILE_RETIREMENT_UNRESOLVED'
                try: self.final_observations()
                except BaseException as error: self.fail(error, 'outer_final_observations')
        self.final_report = self.snapshot()
        if not self.record('RESULT.json', self.final_report):
            self.final_report = self.snapshot()
            self.record('FINAL-FAILURE.json', self.final_report)
        self.final_report = self.snapshot()
        try: print(json.dumps(self.final_report, allow_nan=False), flush=True)
        except BaseException as error:
            self.fail(error, 'stdout'); self.final_report = self.snapshot()
            try: print(json.dumps(self.final_report, allow_nan=False), file=sys.stderr, flush=True)
            except BaseException: pass
        return 0 if (self.primary_error is None and self.positive_isolation_qualified and self.retired
            and self.source_conserved and self.candidate_conserved
            and self.cleanup_status == 'DELETE_SUCCEEDED_AND_FOLDER_ABSENCE_OBSERVED') else 1

def validate_operator_record(path, expected_sha):
    require(Path(path).is_relative_to(R), 'OWNED_OPERATOR_RECORD_REQUIRED')
    path = fs.safe_components(Path(path))
    require(path.resolve(strict=True).is_relative_to(R.resolve(strict=True)), 'OWNED_OPERATOR_RECORD_REQUIRED')
    payload, _ = capture(path, expected_sha)
    value = json.loads(payload.decode('utf-8-sig'))
    require(value['profile_name'] == NAME and value['profile_sid'] == SID and value['user_sid'] == USER, 'EXACT_OPERATOR_PROFILE_IDENTITY_REQUIRED')
    require(value['proposal_sha256'] == sha(PROPOSAL) and value['prepared_script_sha256'] == sha(Path(__file__)), 'EXACT_OPERATOR_PROPOSAL_AND_TOOL_REQUIRED')
    require(value['create_exact_new_profile'] is True and value['delete_only_profile_created_by_this_run'] is True, 'EXPLICIT_CREATE_AND_OWN_CLEANUP_REQUIRED')
    require(value['source'] == 'actual_current_human_reply' and type(value['human_reply']) is str and bool(value['human_reply'].strip()), 'ACTUAL_CURRENT_OPERATOR_REPLY_REQUIRED')
    return value

def qualify(approval_path, approval_sha):
    validate_operator_record(approval_path, approval_sha)
    return _QualificationRun(R / ('q-' + uuid.uuid4().hex), approval_sha).execute()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('inspect', 'qualify'), required=True)
    parser.add_argument('--approval-receipt', type=Path)
    parser.add_argument('--approval-sha256')
    args = parser.parse_args()
    if args.mode == 'inspect':
        require(args.approval_receipt is None and args.approval_sha256 is None, 'INSPECT_TAKES_NO_APPROVAL')
        facts = inspect(); save(R / ('PROFILE-INSPECTION-' + uuid.uuid4().hex + '.json'), facts)
        print(json.dumps(facts, indent=2))
    else:
        require(args.approval_receipt is not None and args.approval_sha256 is not None, 'EXPLICIT_APPROVAL_RECORD_REQUIRED')
        sys.exit(qualify(args.approval_receipt, args.approval_sha256))
