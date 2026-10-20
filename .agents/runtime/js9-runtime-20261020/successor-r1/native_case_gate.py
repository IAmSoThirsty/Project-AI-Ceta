"""One JS8 disposable no-profile case; trusted Root engineering release only.

This is an operator test consumer. It issues no CETA runtime authority. The
original F4 gate remains immutable. Native work requires an exact Root release.
"""
from pathlib import Path
import ast
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import os
import re
import sys
import threading
import time
import types

F = Path('T:/00-Active/Project-AI-CETA')
R = F / '.agents/runtime/js9-runtime-20261020/successor-r1'
RUN = 'js9-runtime-20261020'
CASE = 'test_isolated_worker.NativeIsolatedWorkerTests.test_actual_nonpersistent_launch_denial_and_medium_control_retirement'
KIND = 'JS9_DISPOSABLE_NO_PROFILE_CASE_ROOT_RELEASE_V1'
AUTHORITY = 'existing_user_authorized_disposable_acceptance_tests'
READER_SOURCE = F / '.agents/runtime/js7-20261015/publish_source.py'
READER_SHA256 = 'a536996ace058cb7d524508189d7c96de1c4ccb9e789ac61d2dc4eafc923cab3'
FIXTURE_SHA256 = 'a7247426deee70890107b9d826c7cda9209015edd5f1192f93ee3bd1e5a4314f'
IMAGE_SHA256 = '527518104fb84c430e3e9e0be61982c533b0c6fbb13e1a85e959ba1a3866ad0f'
MAX_BYTES = 65536
MAX_WINDOW_NS = 1_800_000_000_000
ABSENT_HRESULT = -2147024894  # HRESULT_FROM_WIN32(ERROR_FILE_NOT_FOUND).
INVALID = C.c_void_p(-1).value
LEGACY_LIMIT = "The unchanged ':2' regex also matches other 2xx errors; the supplemental native code is exact."


class NativeCaseError(ValueError):
    pass


def require(value, code):
    if value is not True:
        raise NativeCaseError(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def attach(primary, secondary, owner):
    """Diagnostic hooks never replace the actual primary or lose exact custody."""
    try:
        data = BaseException.__dict__['__dict__'].__get__(primary)
        previous = dict.get(data, 'native_case_gate_failures', ())
        if type(previous) is not tuple:
            previous = ()
        dict.__setitem__(data, 'native_case_gate_failures', previous + ((secondary, owner),))
    except BaseException:
        pass


def decode(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES, 'RELEASE_SIZE')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'DUPLICATE_RELEASE_KEY')
            result[key] = value
        return result
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
            parse_float=lambda _: (_ for _ in ()).throw(NativeCaseError('FLOAT_RELEASE_VALUE')),
            parse_constant=lambda _: (_ for _ in ()).throw(NativeCaseError('NONFINITE_RELEASE_VALUE')))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise NativeCaseError('RELEASE_ENCODING') from error
    require(type(value) is dict, 'RELEASE_OBJECT')
    return value


def validate_release(raw, pin, subject, now_ns):
    require(type(pin) is str and re.fullmatch('[0-9a-f]{64}', pin) is not None, 'RELEASE_PIN')
    require(digest(raw) == pin, 'RELEASE_HASH')
    value = decode(raw)
    keys = {'schema_version', 'kind', 'executor', 'authority_basis', 'run_id', 'run_nonce',
        'issued_at_ns', 'expires_at_ns', 'subject', 'execute_exact_original_case',
        'create_profiles', 'expected_denial_winerror'}
    require(set(value) == keys, 'RELEASE_KEYS')
    require(type(value['schema_version']) is int and value['schema_version'] == 1, 'RELEASE_VERSION')
    require(value['kind'] == KIND and value['executor'] == '/root', 'ROOT_ENGINEERING_RELEASE_REQUIRED')
    require(value['authority_basis'] == AUTHORITY and value['run_id'] == RUN, 'TEST_AUTHORITY_BASIS')
    require(type(value['run_nonce']) is str and re.fullmatch('[0-9a-f]{32}', value['run_nonce']) is not None, 'RELEASE_NONCE')
    require(value['execute_exact_original_case'] is True and value['create_profiles'] is False, 'NO_PROFILE_SCOPE')
    require(type(value['expected_denial_winerror']) is int and 0 < value['expected_denial_winerror'] <= 65535, 'EXACT_DENIAL_CODE')
    for key in ('issued_at_ns', 'expires_at_ns'):
        require(type(value[key]) is int and 0 < value[key] < 2**63, 'RELEASE_TIME_DOMAIN')
    require(type(now_ns) is int and 0 < now_ns < 2**63, 'HOST_TIME_DOMAIN')
    require(0 < value['expires_at_ns'] - value['issued_at_ns'] <= MAX_WINDOW_NS, 'RELEASE_WINDOW')
    require(value['issued_at_ns'] <= now_ns < value['expires_at_ns'], 'RELEASE_NOT_CURRENT')
    require(type(subject) is dict and canonical(value['subject']) == canonical(subject), 'EXACT_SUBJECT')
    require(subject['original_case_id'] == CASE and subject['run_id'] == RUN and
        subject['run_nonce'] == value['run_nonce'], 'CASE_RUN_BINDING')
    require(subject['mode'] in ('candidate-full', 'destination-full'), 'FULL_MODE')
    for key in ('payload_map_sha256', 'environment_sha256', 'tools_sha256', 'expected_ids_sha256'):
        require(type(subject[key]) is str and re.fullmatch('[0-9a-f]{64}', subject[key]) is not None, 'SUBJECT_INPUT_DIGEST')
    require(subject['fixture_helper_sha256'] == FIXTURE_SHA256 and subject['native_image_sha256'] == IMAGE_SHA256,
        'EXACT_NATIVE_FIXTURE_INPUTS')
    source = Path(subject['source_root'])
    require(source in (F, F / '.agents/js9-runtime-20261020'), 'PROJECT_SOURCE_ROOT')
    require(Path(subject['fixture_runtime']).is_relative_to(F / '.agents/runtime/js9-runtime-20261020/successor-r1'), 'PRIVATE_FIXTURE_RUNTIME')
    return value


def qualified_reader(s, ports):
    """Reuse the reviewed raw Windows reader's exact class AST, without main."""
    before = s.ordinary(READER_SOURCE)
    raw = READER_SOURCE.read_bytes()
    require(before['sha256'] == digest(raw) == READER_SHA256 and s.ordinary(READER_SOURCE) == before,
        'REVIEWED_RAW_READER_DEPENDENCY')
    names = {'FileBasic', 'FileStandard', 'FileId', 'OriginalReader'}
    nodes = [node for node in ast.parse(raw).body if isinstance(node, ast.ClassDef) and node.name in names]
    require(len(nodes) == len(names), 'RAW_READER_CLASS_CLOSURE')
    namespace = dict(ctypes=C, wintypes=W, os=os, s=s, j=ports)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(READER_SOURCE) + '#classes-only', 'exec'), namespace)
    return namespace['OriginalReader']()


class _Handle:
    def __init__(self, kind, api, raw_close):
        self.kind, self.api, self.raw_close = kind, api, raw_close
        self.handle = None
        self.output = None
        self.close_attempted = self.closed = False
        self.close_error = self.post_close_error = None
        self.diagnostic = None


class _NativeEvent:
    """Preserve the ctypes declaration assigned by the unchanged helper."""
    def __init__(self, gate, operation, api):
        object.__setattr__(self, '_gate', gate)
        object.__setattr__(self, '_operation', operation)
        object.__setattr__(self, '_api', api)
    def __getattr__(self, key):
        return getattr(self._operation, key)
    def __setattr__(self, key, value):
        setattr(self._operation, key, value)
    def __call__(self, *args, **kwargs):
        if self._gate._active != CASE:
            return self._operation(*args, **kwargs)
        owner = _Handle('event', self._api, self._api.CloseHandle)
        self._gate._handles.append(owner)
        result = self._operation(*args, **kwargs)
        error = C.get_last_error()
        try:
            owner.handle = result
        except BaseException as diagnostic:
            owner.diagnostic = diagnostic
        finally:
            C.set_last_error(error)
        return result


class _Socket:
    """Delegate one exact fixture socket; retain every accepted socket too."""
    def __init__(self, gate):
        self.gate, self.owner = gate, None
        self.close_attempted = self.closed = False
        self.error = None
    def __getattr__(self, key):
        return getattr(self.owner, key)
    def __enter__(self):
        return self
    def __exit__(self, kind, primary, trace):
        try:
            self.close()
        except BaseException as secondary:
            if primary is None:
                raise
            attach(primary, secondary, self)
        return False
    def accept(self):
        retained = _Socket(self.gate)
        self.gate._sockets.append(retained)
        retained.owner, address = self.owner.accept()
        return retained, address
    def close(self):
        require(not self.close_attempted, 'SOCKET_CLOSE_ALREADY_ATTEMPTED')
        self.close_attempted = True
        try:
            self.owner.close()
            self.closed = self.owner.fileno() == -1
        except BaseException as error:
            self.error = error
            raise


class _SocketModule:
    def __init__(self, gate, original):
        self.gate, self.original = gate, original
    def __getattr__(self, key):
        return getattr(self.original, key)
    def _allocate(self, operation, *args, **kwargs):
        if self.gate._active != CASE:
            return operation(*args, **kwargs)
        retained = _Socket(self.gate)
        self.gate._sockets.append(retained)
        retained.owner = operation(*args, **kwargs)
        return retained
    def socket(self, *args, **kwargs):
        return self._allocate(self.original.socket, *args, **kwargs)
    def create_connection(self, *args, **kwargs):
        return self._allocate(self.original.create_connection, *args, **kwargs)


class NativeCaseGate:
    @classmethod
    def capture(cls, release_path, release_sha256, *, expected_subject, snapshot, support, ports):
        require(os.name == 'nt' and not sys.flags.optimize, 'NONOPTIMIZED_WINDOWS_REQUIRED')
        path = Path(release_path)
        require(path.is_absolute() and path.is_relative_to(F / '.agents/runtime/js9-runtime-20261020/successor-r1'), 'JS8_RELEASE_PATH')
        self = cls.__new__(cls)
        self.s, self.ports, self.snapshot = support, ports, snapshot
        self.subject = json.loads(canonical(expected_subject))
        self.path, self.pin, self.raw = path, release_sha256, None
        self.reader = qualified_reader(support, ports)
        self._lock = threading.RLock()
        self._active = self._thread = self._helper = self._fixture = None
        self._started = self._entered = self._attempted = self._finished = False
        self._last_wall = self._last_mono = None
        self._diagnostic = None
        self._handles, self._sockets, self._queries, self._calls, self._issues = [], [], [], [], []
        self._probe_receipt = None
        try:
            before = support.ordinary(path)
            require(0 < before['bytes'] <= MAX_BYTES and before['sha256'] == release_sha256, 'RELEASE_INPUT_PIN')
            self.reader.open(path)
            opened = self.reader.identity()
            require(all(opened[key] == before['native_identity'][key] for key in opened), 'RELEASE_NATIVE_IDENTITY')
            self.raw = self.reader.read(before['bytes'])
            require(digest(self.raw) == release_sha256 and support.ordinary(path) == before, 'RELEASE_CAPTURE_DRIFT')
            self.record = validate_release(self.raw, release_sha256, self.subject, time.time_ns())
            self.release_identity = before
            return self
        except BaseException as primary:
            self.reader.close(primary)
            if not self.reader.closed:
                attach(primary, None, self)
            raise

    def _current(self):
        require(canonical(self.snapshot()) == canonical(self.subject), 'SOURCE_ENVIRONMENT_TOOL_DRIFT')
        wall, mono = time.time_ns(), time.perf_counter_ns()
        require(self._last_wall is None or wall >= self._last_wall, 'HOST_TIME_ROLLBACK')
        require(self._last_mono is None or mono >= self._last_mono, 'MONOTONIC_ROLLBACK')
        if self._started:
            require(mono - self._start_mono < self._duration, 'ELAPSED_RELEASE_EXPIRY')
        validate_release(self.raw, self.pin, self.subject, wall)
        self._last_wall, self._last_mono = wall, mono
        return wall, mono

    def start(self):
        with self._lock:
            require(not self._started, 'RELEASE_ALREADY_STARTED')
            wall, mono = self._current()
            markers = R / 'consumed'
            self.s.fs.safe_components(markers, allow_missing=True)
            markers.mkdir(parents=True, exist_ok=True)
            self.s.fs.safe_components(markers)
            self.s.write_new(markers / ('release-' + self.pin + '.json'), dict(
                release_sha256=self.pin, subject=self.subject, release_native_identity=self.release_identity,
                consumed_at_ns=wall, authority_basis=AUTHORITY))
            self.s.write_new(markers / ('nonce-' + self.record['run_nonce'] + '.json'), dict(
                release_sha256=self.pin, subject=self.subject))
            self._start_mono = mono
            self._duration = self.record['expires_at_ns'] - wall
            self._started = True

    def enter(self, identifier):
        with self._lock:
            require(self._started and self._active is None, 'CASE_ENTRY_STATE')
            if identifier == CASE:
                require(not self._entered and not self._finished, 'ORIGINAL_CASE_ALREADY_ENTERED')
                self._current()
                self._entered = True
                self._thread = threading.current_thread()
            self._active = identifier

    def _native_create(self, operation):
        def guarded(*args, **kwargs):
            with self._lock:
                require(self._active == CASE and self._entered and not self._finished and not self._attempted and self._fixture is not None,
                    'EXACT_CASE_SINGLE_NATIVE_ATTEMPT')
                require(threading.current_thread() is self._thread, 'ORIGINAL_CASE_THREAD')
                row = dict(step='restricted_CreateProcessW', returned=False, succeeded=None, winerror=None)
                self._calls.append(row)
                self._current()
                self._attempted = True
            response = operation(*args, **kwargs)
            error = C.get_last_error()
            try:
                dict.update(row, returned=True, succeeded=bool(response), winerror=error)
            except BaseException as diagnostic:
                self._diagnostic = diagnostic
            finally:
                C.set_last_error(error)
            return response
        return guarded

    def guard_isolation_api(self, api):
        api.CreateProcessW = self._native_create(api.CreateProcessW)
        for name in ('CreateAppContainerProfile', 'DeleteAppContainerProfile'):
            def denied(*args, _name=name, **kwargs):
                raise NativeCaseError('PROFILE_OPERATION_FORBIDDEN:' + _name)
            setattr(api.userenv, name, denied)
        api.dll.CreateEventW = _NativeEvent(self, api.dll.CreateEventW, api)

    def _close_handle(self, operation, handle):
        owners = [owner for owner in self._handles if owner.handle == handle and not owner.closed]
        if not owners:
            return operation(handle)
        owner = owners[-1]
        require(not owner.close_attempted, 'CONTROL_CLOSE_ALREADY_ATTEMPTED')
        owner.close_attempted = True
        response = operation(handle)
        error = C.get_last_error()
        try:
            owner.close_error = error
            flags = W.DWORD()
            C.set_last_error(0)
            valid = self.reader.kernel.GetHandleInformation(handle, C.byref(flags))
            owner.post_close_error = C.get_last_error()
            owner.closed = bool(response) and not valid and owner.post_close_error == 6
        except BaseException as diagnostic:
            owner.diagnostic = diagnostic
        finally:
            C.set_last_error(error)
        return response

    def _control(self, api):
        original_pipe, original_close = api.CreatePipe, api.CloseHandle
        def pipe(*args, **kwargs):
            owners = [_Handle('pipe-read', api, original_close), _Handle('pipe-write', api, original_close)]
            self._handles.extend(owners)
            owners[0].output, owners[1].output = args[0], args[1]
            response = original_pipe(*args, **kwargs)
            error = C.get_last_error()
            try:
                for owner in owners:
                    owner.handle = C.cast(owner.output, C.POINTER(W.HANDLE)).contents.value
            except BaseException as diagnostic:
                self._diagnostic = diagnostic
            finally:
                C.set_last_error(error)
            return response
        api.CreatePipe = pipe
        api.CloseHandle = lambda handle: self._close_handle(original_close, handle)
        return api

    def _folder(self, stage, name, sid):
        api = self._helper._IsolationAPI()
        operation = api.userenv.GetAppContainerFolderPath
        operation.argtypes, operation.restype = [W.LPCWSTR, C.POINTER(C.c_void_p)], C.c_int32
        ole = C.WinDLL('ole32', use_last_error=True, winmode=0x800)
        ole.CoTaskMemFree.argtypes, ole.CoTaskMemFree.restype = [C.c_void_p], None
        output = C.c_void_p()
        custody = dict(stage=stage, name=name, sid=sid, output=output, release_attempted=False,
            allocation_closed=False, primary=None, cleanup=None)
        self._queries.append(custody)
        primary = None
        try:
            result = operation(sid, C.byref(output))
            text = C.wstring_at(output) if output.value else None
            require(text is None or 0 < len(text) < 32768, 'PROFILE_FOLDER_PATH_BOUND')
            metadata = None
            if text is not None:
                try:
                    facts = Path(text).lstat()
                    metadata = dict(exists=True, device=facts.st_dev, inode=facts.st_ino, attributes=facts.st_file_attributes)
                except FileNotFoundError:
                    metadata = dict(exists=False)
            custody.update(HRESULT=result, path=text, folder_metadata=metadata,
                absent=result == ABSENT_HRESULT and output.value is None and text is None,
                folder_absent=(result == ABSENT_HRESULT and output.value is None and text is None)
                    or (type(metadata) is dict and metadata.get('exists') is False),
                observation_basis='native_file_not_found_without_output' if result == ABSENT_HRESULT and text is None
                    else 'returned_path_is_absent' if type(metadata) is dict and metadata.get('exists') is False
                    else 'returned_path_present' if type(metadata) is dict and metadata.get('exists') is True
                    else 'unresolved_native_query',
                registration_enumerated=False,
                contents_read=False, query='GetAppContainerFolderPath')
        except BaseException as error:
            primary = error
            custody['primary'] = error
            raise
        finally:
            if output.value:
                custody['release_attempted'] = True
                try:
                    ole.CoTaskMemFree(output)
                    custody['allocation_closed'] = True
                except BaseException as secondary:
                    custody['cleanup'] = secondary
                    if primary is None:
                        attach(secondary, None, custody)
                        raise
                    attach(primary, secondary, custody)
            else:
                custody['allocation_closed'] = True
        return custody

    def bind_helper(self, helper):
        require(self._started and self._helper is None, 'FIXTURE_BINDING_STATE')
        require(self.s.ordinary(Path(helper.__file__))['sha256'] == FIXTURE_SHA256, 'EXACT_FIXTURE_HELPER')
        require(str(helper.R) == self.subject['fixture_runtime'] and str(helper.Q) == self.subject['source_root'],
            'FIXTURE_RUNTIME_SOURCE_BINDING')
        self._helper = helper
        prepare, control, sockets, probe = helper.prepare_fixture, helper._ControlApi, helper.socket, helper.run_native_probe
        def prepared(*args, **kwargs):
            result = prepare(*args, **kwargs)
            if self._active != CASE:
                return result
            require(self._fixture is None and type(result) is tuple and len(result) == 7, 'SINGLE_EXACT_FIXTURE')
            fixture, name, sid, image, _, _, _ = result
            require(Path(fixture).is_relative_to(Path(self.subject['fixture_runtime']) / 'native-fixtures'), 'FRESH_PRIVATE_FIXTURE')
            require(type(name) is str and re.fullmatch(r'CETA\.AC1\.[0-9a-f]{32}', name) is not None, 'FRESH_CONTAINER_NAME')
            require(helper.appcontainer_sid(name) == sid, 'EXACT_NAME_SID_BINDING')
            require(self.s.ordinary(Path(image))['sha256'] == IMAGE_SHA256, 'EXACT_FIXTURE_IMAGE')
            pre = self._folder('before', name, sid)
            require(pre['absent'] is True and pre['allocation_closed'] is True, 'PROFILE_ABSENCE_UNQUALIFIED')
            self._fixture = result
            return result
        def controlled(*args, **kwargs):
            api = control(*args, **kwargs)
            return self._control(api) if self._active == CASE else api
        def observed_probe(*args, **kwargs):
            try:
                return probe(*args, **kwargs)
            except BaseException as primary:
                if self._active == CASE:
                    try:
                        data = BaseException.__dict__['__dict__'].__get__(primary)
                        path = dict.get(data, 'native_probe_receipt')
                        if type(path) is str:
                            path = Path(path)
                            require(self._fixture is not None and path.parent == Path(self._fixture[0]), 'PROBE_RECEIPT_SCOPE')
                            before = self.s.ordinary(path)
                            require(before['bytes'] <= MAX_BYTES, 'PROBE_RECEIPT_BOUND')
                            raw = path.read_bytes()
                            require(digest(raw) == before['sha256'] and self.s.ordinary(path) == before, 'PROBE_RECEIPT_DRIFT')
                            self._probe_receipt = dict(reference=dict(repository_relative_path=path.relative_to(F).as_posix(),
                                sha256=before['sha256']), value=decode(raw))
                    except BaseException as secondary:
                        self._diagnostic = secondary
                        attach(primary, secondary, self)
                raise
        helper.prepare_fixture, helper._ControlApi = prepared, controlled
        helper.socket, helper.run_native_probe = _SocketModule(self, sockets), observed_probe
        self._restore = (helper, prepare, control, sockets, probe)

    def finish_case(self, identifier):
        require(self._active == identifier, 'EXACT_FINISH_CASE')
        try:
            if identifier != CASE:
                return
            # Drain only exact newly returned owners with no earlier close
            # attempt. An uncertain prior native close is never replayed.
            for owner in self._handles:
                if owner.handle not in (None, 0, INVALID) and not owner.close_attempted:
                    try:
                        self._close_handle(owner.raw_close, owner.handle)
                    except BaseException as error:
                        owner.diagnostic = error
            for retained in self._sockets:
                if retained.owner is not None and not retained.close_attempted:
                    try:
                        retained.close()
                    except BaseException as error:
                        retained.error = error
            if self._fixture is not None:
                post = self._folder('after', self._fixture[1], self._fixture[2])
                require(post['absent'] is True and post['allocation_closed'] is True, 'PROFILE_AFTER_NOT_ABSENT')
        except BaseException as error:
            self._issues.append(error)
        finally:
            self._active = None

    def finish(self):
        require(self._started and self._active is None and not self._finished, 'GATE_FINISH_STATE')
        self._current()
        self._finished = True
        calls_ok = len(self._calls) == 1 and self._calls[0]['returned'] is True and self._calls[0]['succeeded'] is False
        calls_ok = calls_ok and type(self._calls[0]['winerror']) is int and self._calls[0]['winerror'] == self.record['expected_denial_winerror']
        handle_rows = [dict(kind=o.kind, handle=o.handle, close_attempted=o.close_attempted, closed=o.closed,
            close_error=o.close_error, post_close_error=o.post_close_error,
            diagnostic=None if o.diagnostic is None else type(o.diagnostic).__name__) for o in self._handles]
        socket_rows = [dict(close_attempted=o.close_attempted, closed=o.closed,
            fileno=None if o.owner is None else o.owner.fileno(),
            diagnostic=None if o.error is None else type(o.error).__name__) for o in self._sockets]
        queries = [{key:value for key,value in q.items() if key not in ('output','primary','cleanup')} | dict(
            primary=None if q['primary'] is None else type(q['primary']).__name__,
            cleanup=None if q['cleanup'] is None else type(q['cleanup']).__name__) for q in self._queries]
        probe_ok = self._probe_receipt is not None
        if probe_ok:
            receipt = self._probe_receipt['value']
            cleanup = receipt.get('cleanup', [])
            probe_ok = len(cleanup) == 1 and cleanup[0].get('kind') == 'trusted_medium_fixture'
            probe_ok = probe_ok and cleanup[0].get('active_processes') == 0 and cleanup[0].get('lifetime_closed') is True and cleanup[0].get('exit_code') == 125
        resources_ok = len(handle_rows) == 7 and all(o['closed'] is True and o['post_close_error'] == 6 for o in handle_rows)
        resources_ok = resources_ok and len(socket_rows) == 3 and all(o['closed'] is True and o['fileno'] == -1 for o in socket_rows)
        queries_ok = len(queries) == 2 and [q['stage'] for q in queries] == ['before','after'] and all(q.get('absent') is True and q['allocation_closed'] is True for q in queries)
        passed = self._entered and self._attempted and calls_ok and resources_ok and queries_ok and probe_ok and self._diagnostic is None and not self._issues
        return dict(schema_version=1, original_case_id=CASE, release=dict(repository_relative_path=self.path.relative_to(F).as_posix(), sha256=self.pin),
            run_nonce=self.record['run_nonce'], subject=self.subject, authority_basis=AUTHORITY,
            exact_native_calls=self._calls, expected_denial_winerror=self.record['expected_denial_winerror'],
            profile_folder_observations=queries, handles=handle_rows, sockets=socket_rows,
            original_probe_receipt=self._probe_receipt, entered=self._entered, attempted=self._attempted,
            issues=[type(error).__name__ for error in self._issues],
            diagnostic=None if self._diagnostic is None else type(self._diagnostic).__name__,
            owned_fixture_resources_closed=resources_ok, precise_denial_matched=calls_ok, passed=bool(passed),
            no_profile_create_delete=True, legacy_regex_limitation=LEGACY_LIMIT,
            limits=['Folder absence is the exact native FILE_NOT_FOUND/no-output observation; no missing-profile launch causality is inferred.',
                'Actual control/worker process and job retirement must additionally be bound by the enclosing runner physical resource proof; no numeric PID is reopened.',
                'Unexpected successful probe descendants and child-local handles require the enclosing bounded-job/native recorder proof; this denial result never certifies positive isolation.'],
            Source_accepted=False)

    def close(self, primary=None, *, preserve_guards=False):
        restoration = None
        try:
            if not preserve_guards and hasattr(self, '_restore'):
                helper, prepare, control, sockets, probe = self._restore
                helper.prepare_fixture, helper._ControlApi, helper.socket, helper.run_native_probe = prepare, control, sockets, probe
                del self._restore
        except BaseException as secondary:
            restoration = secondary
            if primary is not None:
                attach(primary, secondary, self)
        finally:
            if not self.reader.close_attempted:
                self.reader.close(primary if primary is not None else restoration)
            elif not self.reader.closed:
                pending = NativeCaseError('RELEASE_READER_CLOSE_UNCERTAIN')
                if primary is not None:
                    attach(primary, pending, self.reader)
                elif restoration is not None:
                    attach(restoration, pending, self.reader)
                else:
                    raise pending
        if restoration is not None and primary is None:
            raise restoration
