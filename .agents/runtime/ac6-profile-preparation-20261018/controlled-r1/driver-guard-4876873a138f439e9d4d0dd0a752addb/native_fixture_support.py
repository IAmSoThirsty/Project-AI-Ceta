"""Disposable AC1 native qualification resources; no active profile access."""
from ac_support import *
import ctypes as C
from ctypes import wintypes as W
import socket, uuid

sys.path.insert(0, str(Q / 'src'))
from ceta.supervisor.isolated_worker import IsolatedWindowsWorker, _IsolationAPI, SID_AND_ATTRIBUTES, appcontainer_sid
from ceta.supervisor.windows_jobs import WindowsOwnedProcess, HANDLE, DWORD
from ceta.supervisor.service import _ControlApi, _Attributes


def security_api():
    api = C.WinDLL('advapi32', use_last_error=True, winmode=0x800)
    api.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [W.LPCWSTR, DWORD, C.POINTER(C.c_void_p), C.POINTER(DWORD)]
    api.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = W.BOOL
    api.GetSecurityDescriptorDacl.argtypes = [C.c_void_p, C.POINTER(W.BOOL), C.POINTER(C.c_void_p), C.POINTER(W.BOOL)]
    api.GetSecurityDescriptorDacl.restype = W.BOOL
    api.GetSecurityDescriptorSacl.argtypes = api.GetSecurityDescriptorDacl.argtypes
    api.GetSecurityDescriptorSacl.restype = W.BOOL
    api.SetNamedSecurityInfoW.argtypes = [W.LPWSTR, C.c_int, DWORD, C.c_void_p, C.c_void_p, C.c_void_p, C.c_void_p]
    api.SetNamedSecurityInfoW.restype = DWORD
    return api


def owner_sid():
    api = _IsolationAPI(); token = HANDLE()
    assert api.OpenProcessToken(api.GetCurrentProcess(), 8, C.byref(token))
    try:
        buffer = api.token_data(token, 1)
        return api.sid_text(SID_AND_ATTRIBUTES.from_buffer(buffer).sid)
    finally: api.close(token.value)


def process_integrity(process):
    api = _IsolationAPI(); token = HANDLE()
    assert api.OpenProcessToken(process._process, 8, C.byref(token))
    try:
        buffer = api.token_data(token, 25)
        return api.sid_text(SID_AND_ATTRIBUTES.from_buffer(buffer).sid)
    finally: api.close(token.value)


def assign_security(path, sddl, fixture):
    path = fs.safe_components(Path(path))
    assert path.is_relative_to(fixture) and fixture.is_relative_to(R / 'native-fixtures')
    api, native = security_api(), _IsolationAPI()
    descriptor = C.c_void_p(); length = DWORD()
    assert api.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, C.byref(descriptor), C.byref(length)), C.get_last_error()
    try:
        present, defaulted = W.BOOL(), W.BOOL()
        dacl, sacl = C.c_void_p(), C.c_void_p()
        assert api.GetSecurityDescriptorDacl(descriptor, C.byref(present), C.byref(dacl), C.byref(defaulted)) and present.value
        assert api.GetSecurityDescriptorSacl(descriptor, C.byref(present), C.byref(sacl), C.byref(defaulted)) and present.value
        for phase, flags, acl, label in (('DACL', 0x80000004, dacl, None), ('LABEL', 0x10, None, sacl)):
            error = api.SetNamedSecurityInfoW(str(path), 1, flags, None, None, acl, label)
            with (fixture / 'ACL-OPERATIONS.jsonl').open('a', encoding='utf-8') as output:
                output.write(json.dumps({'observed_at': utc(), 'path': str(path), 'phase': phase,
                                        'error': error, 'sddl': sddl}) + '\n')
                output.flush(); os.fsync(output.fileno())
            assert error == 0, ('fixture ACL/label failed', phase, error)
    finally:
        assert native.LocalFree(descriptor) is None


def prepare_fixture(build='build-r2', directory_read=False):
    base = R / 'native-fixtures'; base.mkdir(exist_ok=True)
    fs.safe_components(base)
    fixture = base / ('ac1-' + uuid.uuid4().hex); fixture.mkdir()
    name = 'CETA.ProjectAICETA.IsolatedWorker.AC1.V1'
    sid, user = appcontainer_sid(name), owner_sid()
    write_new(fixture / 'ALLOCATED.json', {'observed_at': utc(), 'fixture': str(fixture),
              'container_name': name, 'appcontainer_sid': sid, 'owner_sid': user, 'profile_installed': False})
    directories = {key: fixture / key for key in ('assets', 'scratch', 'protected')}
    for path in directories.values(): path.mkdir()
    image = directories['assets'] / 'isolated_worker.exe'
    original = R / build / 'isolated_worker.exe'
    fs.write_new(image, fs.read_bytes(original))
    assert sha(image) == '527518104fb84c430e3e9e0be61982c533b0c6fbb13e1a85e959ba1a3866ad0f'
    asset = directories['assets'] / 'allowed.txt'; fs.write_new(asset, b'CETA_AC1_ALLOWED_ASSET_V1\n')
    files = []
    for filename in ('canonical.db', 'canonical.db-wal', 'canonical.db-shm', 'policy.txt', 'source.txt'):
        path = directories['protected'] / filename
        fs.write_new(path, b'CETA_AC1_PROTECTED_SENTINEL_V1\n'); files.append(path)
    prefix = f'D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;{user})'
    traverse = prefix + f'(A;OICI;0x1200a0;;;{sid})S:(ML;;NW;;;ME)'
    read = prefix + f'(A;OICI;0x1200a9;;;{sid})S:(ML;;NW;;;ME)'
    modify = prefix + f'(A;OICI;0x1301bf;;;{sid})S:(ML;;NW;;;LW)'
    closed = prefix + 'S:(ML;;NW;;;ME)'
    assign_security(fixture, read if directory_read else traverse, fixture)
    assign_security(directories['assets'], read if directory_read else traverse, fixture)
    assign_security(directories['scratch'], modify, fixture)
    assign_security(directories['protected'], closed, fixture)
    for path in (image, asset): assign_security(path, read, fixture)
    for path in files: assign_security(path, closed, fixture)
    details = {'fixture': str(fixture), 'container_name': name, 'appcontainer_sid': sid,
               'owner_sid': user, 'image': ordinary(image), 'asset': ordinary(asset),
               'protected_before': {str(path): ordinary(path) for path in files},
               'acl_operations': 'DACL+mandatory label only fresh fixture descendants; App SID RX assets, modify low scratch, absent protected medium assets',
               'persistent_profile_install': False}
    write_new(fixture / 'SETUP.json', details)
    return fixture, name, sid, image, asset, files, details


def read_pipe(control, handle, bound=16384):
    chunks, total = [], 0
    while True:
        buffer, read = C.create_string_buffer(min(4096, bound - total + 1)), DWORD()
        if not control.ReadFile(handle, buffer, len(buffer), C.byref(read), None):
            error = C.get_last_error()
            assert error == 109, error
            break
        if read.value == 0: break
        total += read.value; assert total <= bound, 'native probe output bound'
        chunks.append(buffer.raw[:read.value])
    return b''.join(chunks)


def run_native_probe(label, build='build-r2', directory_read=False):
    fixture, name, sid, image, asset, files, setup = prepare_fixture(build, directory_read)
    check_launch_paths(fixture, image)
    control, api = _ControlApi(), _IsolationAPI()
    control.CreateEventW = api.dll.CreateEventW
    control.CreateEventW.argtypes = [C.c_void_p, W.BOOL, W.BOOL, W.LPCWSTR]
    control.CreateEventW.restype = HANDLE
    attrs = _Attributes(C.sizeof(_Attributes), None, True)
    event = control.CreateEventW(C.byref(attrs), True, False, 'Local\\CETA.AC1.' + uuid.uuid4().hex)
    assert event
    sockets = socket.socket(); sockets.bind(('127.0.0.1', 0)); sockets.listen(4)
    endpoint = sockets.getsockname(); sockets.settimeout(0.3)
    # Positive unrestricted control proves this exact owned loopback listener works.
    with socket.create_connection(endpoint, timeout=1):
        accepted, _ = sockets.accept(); accepted.close()
    scratch = fixture / 'scratch/output.txt'
    parent_input, child_input = control.pipe(child_reads=True)
    parent_output, child_output = control.pipe(child_reads=False)
    parent_error, child_error = control.pipe(child_reads=False)
    handles = [parent_input, child_input, parent_output, child_output, parent_error, child_error, event]
    trusted = worker = None; raw = b''; started = utc(); primary = None; cleanup = []; integrity = None
    try:
        trusted = WindowsOwnedProcess.launch(str(image), ('hold', '30000'), cwd=str(fixture),
                  environment=api.environment(str(fixture / 'scratch')), expected_image_sha256='527518104fb84c430e3e9e0be61982c533b0c6fbb13e1a85e959ba1a3866ad0f')
        integrity = process_integrity(trusted)
        args = ('probe', str(asset), str(scratch), *(str(path) for path in files),
                str(trusted.pid), str(endpoint[1]), str(event))
        worker = IsolatedWindowsWorker.launch(str(image), args, cwd=str(fixture),
                  scratch_root=str(fixture / 'scratch'), expected_image_sha256='527518104fb84c430e3e9e0be61982c533b0c6fbb13e1a85e959ba1a3866ad0f', appcontainer_name=name,
                  standard_handles=(child_input, child_output, child_error))
        for handle in (child_input, child_output, child_error): control.close(handle); handles.remove(handle)
        assert worker.wait(10), 'probe did not exit'
        exit_code = worker.poll()
        raw = read_pipe(control, parent_output)
        errors = read_pipe(control, parent_error)
        facts = json.loads(raw.decode('utf-8')) if raw else None
        result = {'label': label, 'started_at': started, 'finished_at': utc(),
                  'setup': setup, 'image_hash': sha(image), 'argv': args,
                  'worker_identity': {'pid': worker.pid, 'creation_time': worker.creation_time, 'image_sha256': worker.image_sha256},
                  'parent_token_facts': {key: getattr(worker.launch_token_facts, key) for key in worker.launch_token_facts.__slots__},
                  'trusted_target': {'pid': trusted.pid, 'creation_time': trusted.creation_time, 'integrity': integrity},
                  'worker_exit_code': exit_code, 'facts': facts, 'stderr': errors.decode('utf-8', 'replace'),
                  'excluded_event_wait': api.WaitForSingleObject(event, 0),
                  'protected_after': {str(path): ordinary(path) for path in files},
                  'scratch_exists': scratch.exists()}
    except BaseException as error:
        primary = error
        if worker is None: worker = getattr(error, 'owned_process', None)
        result = {'label': label, 'started_at': started, 'finished_at': utc(), 'setup': setup,
                  'failure_type': type(error).__name__, 'failure': str(error), 'raw_stdout': raw.decode('utf-8', 'replace'),
                  'trusted_target': None if trusted is None else {'pid': trusted.pid, 'creation_time': trusted.creation_time,
                                                                  'integrity': integrity}}
    finally:
        for owner, kind in ((worker, 'restricted_worker'), (trusted, 'trusted_medium_fixture')):
            if owner is None: continue
            try:
                if owner.poll() is None: owner.terminate(125)
                assert owner.wait(5), 'retirement not observed'
                code, active = owner.poll(), owner.active_process_count()
                owner.close()
                cleanup.append({'kind': kind, 'pid': owner.pid, 'creation_time': owner.creation_time,
                                'exit_code': code, 'active_processes': active, 'lifetime_closed': owner.lifetime_closed})
            except BaseException as error:
                cleanup.append({'kind': kind, 'cleanup_failure': type(error).__name__, 'message': str(error)})
                if primary is None: primary = error
        for handle in handles:
            try: control.close(handle)
            except BaseException as error:
                cleanup.append({'native_handle_cleanup_failure': type(error).__name__})
                if primary is None: primary = error
        sockets.close()
    result['cleanup'] = cleanup
    write_new(fixture / (label + '.json'), result)
    print(json.dumps({'receipt': str(fixture / (label + '.json')), 'failure': result.get('failure'),
                      'exit_code': result.get('worker_exit_code'), 'facts': result.get('facts'), 'cleanup': cleanup}, indent=2), flush=True)
    if primary is not None:
        primary.native_probe_receipt = str(fixture / (label + '.json'))
        raise primary
    return result
