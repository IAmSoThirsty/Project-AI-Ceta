"""Dormant concrete port for the canonical AC7 fixture and R5 owned caller.

No native object is constructed on import. The production command reaches this
module only after capture_bridge.preflight; controls never execute NativePort.
The original driver/helper/class definitions are retained without monkeypatches.
"""
from pathlib import Path
import importlib.util
import json
import os
import sys
import threading
import time
import types

from capture_bridge import (F, W, R5, BridgeError, canonical, digest, require, reference,
    read_bytes, read_reference, strict_json, ordinary_path, validate_lease, derive_release,
    persisted_capture, file_sha, preflight)


def load_exact(name, path, pin, *, fresh_dependency=False):
    """Use original source/filename/loader; reject a conflicting preloaded name."""
    require(file_sha(path)['sha256'] == pin, 'BRIDGE_MODULE_BYTES_CHANGED:' + name)
    existing = sys.modules.get(name)
    if existing is not None:
        require(fresh_dependency and type(existing) is types.ModuleType and Path(existing.__file__) == path,
                'BRIDGE_FOREIGN_MODULE_ALREADY_LOADED:' + name)
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, 'BRIDGE_SOURCE_LOADER_UNAVAILABLE')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        # Preserve the failed source module for inspection; never silently retry.
        raise
    return module


def save_new(path, value):
    path = ordinary_path(path)
    raw = canonical(value) + b'\n'
    with path.open('xb') as stream:
        require(stream.write(raw) == len(raw), 'BRIDGE_SHORT_EVIDENCE_WRITE')
        stream.flush()
        os.fsync(stream.fileno())


def error_record(error):
    try:
        message = str(error)
    except BaseException:
        message = '<exception text unavailable>'
    return dict(type=type(error).__name__, message=message[:8192])


def retire_ordinary(owner):
    """One known ordinary owner's retirement; closed handles are never polled."""
    if owner.lifetime_closed:
        return dict(pid=owner.pid, creation_time=owner.creation_time, lifetime_closed=True,
                    already_closed=True, native_handle_repoll=False)
    if owner.poll() is None:
        owner.terminate(125)
    require(owner.wait(5), 'BRIDGE_ORDINARY_RETIREMENT_NOT_OBSERVED')
    code, count = owner.poll(), owner.active_process_count()
    require(code is not None and count == 0, 'BRIDGE_ORDINARY_JOB_NOT_EMPTY')
    owner.close()
    require(owner.lifetime_closed, 'BRIDGE_ORDINARY_HANDLES_NOT_CLOSED')
    return dict(pid=owner.pid, creation_time=owner.creation_time, lifetime_closed=True,
                exit_code=code, active_processes=count, native_handle_repoll=False)


def validate_unwrapped_canonical(boundary, inputs):
    admitted = boundary.validate_ceta_modules(inputs)
    # R5's general admission deliberately defers its two possible custody
    # wrappers. This bridge uses only originals and must check those NOW,
    # before importing the original driver or reaching profile preparation.
    for module, raw in admitted.values():
        boundary.validate_definitions(module, raw)
    return admitted


class NativePort:
    """One attempt with explicit custody. Uncertain resources remain retained."""
    def __init__(self, plan):
        self.plan = plan
        self.directory = plan.paths['directory']
        self.started_ns = time.monotonic_ns()
        self.driver = self.helper = self.adapter = self.boundary = self.owned = None
        self.creator = self.control = self.api = None
        self.trusted = self.listener = None
        self.handles = []
        self.handle_in_flight = None
        self.closure = None
        self.fixture = self.setup = self.files = self.scratch = None
        self.created = self.sid_verified = self.created_recorded = False
        self.create_called = self.delete_called = False
        self.output = None
        self.unknown = False
        self.capture_called = False
        self.capture_evidence = None
        self.primary = None
        self.failures = []
        self.cleanup = []
        self.cleanup_started = False
        self.retired = False
        self.profile_cleanup = 'NOT_CREATED'
        self.oracle_passed = False
        self.result = None
        self.inputs_before = None
        self.inputs_conserved = False
        self.phase = 'ADMISSION'
        self.authorized = False

    def fail(self, error, stage):
        if self.primary is None:
            self.primary = error
        self.failures.append(dict(stage=stage, **error_record(error)))

    def record(self, name, value):
        require(self.directory is not None and Path(name).name == name, 'BRIDGE_OWN_RECORD_PATH')
        save_new(self.directory / name, value)

    def live(self):
        require(self.authorized, 'BRIDGE_NATIVE_PORT_NOT_ADMITTED')
        require(time.time_ns() < self.plan.request['expires_at_ns'], 'BRIDGE_GRANT_EXPIRED')
        require(time.monotonic_ns() - self.started_ns < 120_000_000_000, 'BRIDGE_OUTER_ADMISSION_DEADLINE')
        validate_lease(self.plan.request['lease'], self.plan.request['nonce'])

    def source_cut(self):
        pins = self.plan.source_inputs
        result = {str(R5 / name): file_sha(R5 / name) for name in
                  read_reference(self.plan.inputs['loader_freeze'])['python_hashes']}
        for name in pins['ac7_payload_hashes']:
            path = Path(pins['ac7_candidate']) / name
            result[str(path)] = file_sha(path)
        for row in pins['caller_contract'].values():
            result[row['path']] = file_sha(row['path'])
        return result

    def load(self):
        self.live()
        # Pin every dependency before importing dormant definitions. Existing
        # canonical CETA modules must retain their actual source identity.
        sys.dont_write_bytecode = True
        manifest = read_reference(self.plan.inputs['loader_code_manifest'])
        sys.path.insert(0, str(R5))
        require(not any(name in sys.modules for name in ('capture_core', 'loader_snaps', 'win32_debug',
            'caller_boundary', 'isolated_adapter', 'owned_caller', 'ac6_single_attempt_preflight',
            'profile_r2_captured_native_probe', 'profile_r2_captured_ac_support', 'ac_support',
            'profile_r2_native_reader', 'ac2_qualified_native_reader')),
            'BRIDGE_FRESH_CAPTURE_MODULE_NAMESPACE_REQUIRED')
        for name in ('capture_core', 'loader_snaps', 'win32_debug', 'caller_boundary',
                     'isolated_adapter', 'owned_caller'):
            # Only imports performed inside this fresh pinned dependency cut may
            # already have imported another member of that same six-module cut.
            load_exact(name, R5 / (name + '.py'), manifest['code_hashes'][name + '.py'], fresh_dependency=True)
        self.adapter = sys.modules['isolated_adapter']
        self.boundary = sys.modules['caller_boundary']
        self.owned = sys.modules['owned_caller']
        # Existing source-matching CETA modules are allowed only after the
        # already reviewed pure source/default/alias validation, before even
        # the original driver's read-only native file-reader initialization.
        validate_unwrapped_canonical(self.boundary, self.plan.source_inputs)
        caller = self.plan.source_inputs['caller_contract']['driver']
        self.driver = load_exact('ac6_single_attempt_preflight', Path(caller['path']), caller['sha256'])
        # The directory is a fresh child of the original driver's evidence root.
        require(self.directory.parent == self.driver.R, 'BRIDGE_CANONICAL_DRIVER_EVIDENCE_ROOT')
        self.inputs_before = self.source_cut()

    def create_profile(self):
        import ctypes as C
        from ctypes import wintypes as WT
        driver = self.driver
        self.live()
        before = driver.inspect()
        self.record('PROFILE-BEFORE.json', before)
        require(before['prior_folder']['HRESULT'] in (-2147024894, -2147024893)
                and before['prior_folder']['path'] is None, 'BRIDGE_PREEXISTING_OR_UNKNOWN_PROFILE_REFUSED')
        self.creator = driver.module._IsolationAPI()
        self.output = C.c_void_p()
        create = self.creator.userenv.CreateAppContainerProfile
        create.argtypes = [WT.LPCWSTR, WT.LPCWSTR, WT.LPCWSTR, C.c_void_p, WT.DWORD, C.POINTER(C.c_void_p)]
        create.restype = C.c_int32
        self.record('PROFILE-CREATE-INTENT.json', dict(name=driver.NAME, SID=driver.SID,
            capabilities=[], original_human_grant=self.plan.request['owner_grant']))
        self.create_called = True
        status = None
        try:
            status = create(driver.NAME, 'Project-AI: CETA owned loader diagnostic',
                'One fresh zero-capability canonical fixture diagnostic', None, 0, C.byref(self.output))
            self.created = type(status) is int and status == 0
        finally:
            if self.output.value:
                if self.created:
                    self.creator.pending_sids.append(self.output.value)
                else:
                    self.unknown = True
            if status is None:
                self.unknown = True
        self.record('PROFILE-CREATE-RETURN.json', dict(HRESULT=status, created_this_attempt=self.created,
            returned_sid_pointer=self.output.value, unknown_output=self.unknown, adoption=False))
        require(self.created and self.output.value, 'BRIDGE_PROFILE_CREATE_NOT_EXACT_SUCCESS')
        sid = self.creator.sid_text(self.output.value)
        require(sid == driver.SID, 'BRIDGE_PROFILE_RETURNED_SID_MISMATCH')
        self.sid_verified = True
        # Existing canonical cleanup makes one attempt per known operation and
        # retains uncertainty. No new retry loop is introduced here.
        self.creator.retry_cleanup()
        self.record('PROFILE-CREATED.json', dict(name=driver.NAME, actual_SID=sid,
            capabilities=[], original_human_grant=self.plan.request['owner_grant']))
        self.created_recorded = True

    def pipe(self, *, child_reads):
        self.handle_in_flight = 'CreatePipe'
        pair = self.control.pipe(child_reads=child_reads)
        # Register both exact returned handles before further operations.
        self.handles.extend(pair)
        self.handle_in_flight = None
        return pair

    def prepare_call(self):
        import ctypes as C
        from ctypes import wintypes as WT
        import socket
        helper = self.helper
        self.live()
        self.fixture, name, sid, image, asset, self.files, self.setup = helper.prepare_fixture('build-r2', True)
        helper.check_launch_paths(self.fixture, image)
        self.control = helper._ControlApi()
        self.api = helper._IsolationAPI()
        self.control.CreateEventW = self.api.dll.CreateEventW
        self.control.CreateEventW.argtypes = [C.c_void_p, WT.BOOL, WT.BOOL, WT.LPCWSTR]
        self.control.CreateEventW.restype = helper.HANDLE
        attrs = helper._Attributes(C.sizeof(helper._Attributes), None, True)
        self.handle_in_flight = 'CreateEventW'
        event = self.control.CreateEventW(C.byref(attrs), True, False,
            'Local\\CETA.AC1.' + self.plan.request['nonce'])
        require(type(event) is int and event > 0, 'BRIDGE_EVENT_CREATE_FAILED')
        self.handles.append(event)
        self.handle_in_flight = None
        self.listener = socket.socket()
        self.listener.bind(('127.0.0.1', 0))
        self.listener.listen(4)
        endpoint = self.listener.getsockname()
        self.listener.settimeout(0.3)
        with socket.create_connection(endpoint, timeout=1):
            accepted, _ = self.listener.accept()
            accepted.close()
        self.record('ORDINARY-LOOPBACK-CONTROL.json', dict(connected=True, accepted=True,
            endpoint=list(endpoint), original_control='run_native_probe ordinary socket connection'))
        parent_input, child_input = self.pipe(child_reads=True)
        parent_output, child_output = self.pipe(child_reads=False)
        parent_error, child_error = self.pipe(child_reads=False)
        self.scratch = self.fixture / 'scratch/output.txt'
        self.live()
        self.trusted = helper.WindowsOwnedProcess.launch(str(image), ('hold', '30000'), cwd=str(self.fixture),
            environment=self.api.environment(str(self.fixture / 'scratch')),
            expected_image_sha256=self.plan.source_inputs['worker']['sha256'])
        integrity = helper.process_integrity(self.trusted)
        require(self.trusted.poll() is None, 'BRIDGE_ORDINARY_TARGET_EXITED_BEFORE_WORKER')
        self.target = dict(pid=self.trusted.pid, creation_time=self.trusted.creation_time,
                           integrity=integrity, alive_before_worker=True)
        args = ('probe', str(asset), str(self.scratch), *(str(p) for p in self.files),
                str(self.trusted.pid), str(endpoint[1]), str(event))
        children = (child_input, child_output, child_error)
        self.closure = self.boundary.ChildPipeClosure(self.control, children, self.handles)
        context = self.boundary.PreparedCaller(self.helper, sys.modules['profile_r2_captured_ac_support'],
            sys.modules['ac_support'], self.driver, self.control, self.handles, self.closure,
            self.directory, threading.get_ident(), qualification_run=None)
        launch = dict(executable=str(image), arguments=args, cwd=str(self.fixture),
            scratch_root=str(self.fixture / 'scratch'), expected_image_sha256=self.plan.source_inputs['worker']['sha256'],
            appcontainer_name=name, inherited_handles=(), standard_handles=children)
        return context, launch, (parent_output, parent_error), event

    def capture(self, context, launch, parents):
        self.live()
        release_seed = dict(fixture_root=str(self.fixture), parent_output_handles=list(parents))
        _, binding = self.boundary.validate_prepared(context, self.plan.source_inputs, release_seed,
            launch, *parents, self.closure, match_release=False)
        native = self.boundary.native_control_members(self.control)
        bound_owner = self.directory / 'BOUND-OWNER-APPROVAL.json'
        owner_ref = dict(repository_relative_path=bound_owner.relative_to(F).as_posix(), sha256='0' * 64)
        release, owner = derive_release(self.plan, fixture=self.fixture, launch=launch, parents=parents,
            binding=binding, native_control=native, owner_reference=owner_ref)
        save_new(bound_owner, owner)
        release['owner_approval'] = reference(bound_owner)
        save_new(self.plan.paths['release'], release)
        release_ref = reference(self.plan.paths['release'])
        # Full existing R5 admission executes before its attempt marker/provider.
        self.adapter.admission(self.plan.paths['release'], release_ref['sha256'])
        self.record('FRESH-BINDING.json', dict(prepared_launch=release['prepared_launch'],
            caller_binding=binding, caller_native_control=native, release=release_ref,
            bound_owner=release['owner_approval'], original_human_grant=self.plan.request['owner_grant'],
            new_human_consent_claim=False))
        self.live()
        self.capture_called = True
        try:
            self.owned.execute_prepared_capture(release_path=self.plan.paths['release'],
                release_sha256=release_ref['sha256'], launch_arguments=launch,
                stdout_handle=parents[0], stderr_handle=parents[1], caller_context=context,
                close_child_pipe_ends=self.closure)
        finally:
            # This is evidence readback, not a retry of collect or retirement.
            try:
                self.capture_evidence = persisted_capture(self.plan)
                self.record('CAPTURE-READBACK.json', dict(references=self.capture_evidence['references'],
                    stdout_sha256=digest(self.capture_evidence['stdout']),
                    stderr_sha256=digest(self.capture_evidence['stderr']), exact_attempt=True,
                    closed_handle_polling=False))
            except BaseException as error:
                self.unknown = True
                self.fail(error, 'capture_readback_or_retirement')

    def observe(self, launch, event):
        evidence = self.capture_evidence
        require(evidence is not None, 'BRIDGE_NO_COMPLETE_CAPTURE_EVIDENCE')
        self.target['alive_after_worker'] = self.trusted.poll() is None
        require(self.target['alive_after_worker'], 'BRIDGE_ORDINARY_TARGET_EXITED_DURING_WORKER')
        facts, parse_error = None, None
        if evidence['stdout']:
            try:
                facts = strict_json(evidence['stdout'])
            except BaseException as error:
                parse_error = error_record(error)
        report = evidence['result']
        result = dict(label='owned-loader-bridge-v1', setup=self.setup,
            image_hash=self.plan.source_inputs['worker']['sha256'], argv=launch['arguments'],
            worker_identity=report['identity'], parent_token_facts=report['parent_launch_token_facts'],
            trusted_target=self.target, worker_exit_code=report['native_exit_code'], facts=facts,
            stderr=evidence['stderr'].decode('utf-8', 'replace'),
            excluded_event_wait=self.api.WaitForSingleObject(event, 0),
            protected_after={str(p): self.helper.ordinary(p) for p in self.files},
            scratch_exists=self.scratch.exists(), actual_capture=evidence['references'],
            stdout_parse_error=parse_error, original_capture_error=report.get('primary_error'))
        self.result = result
        self.record('NATIVE-PROBE-OBSERVATIONS.json', result)
        # Preserve the actual oracle, including its token, rights, sentinel,
        # network and environment requirements. Diagnostic failure stays failed.
        self.driver.assert_isolation(result)
        self.oracle_passed = True

    def cleanup_once(self):
        require(not self.cleanup_started, 'BRIDGE_CLEANUP_ALREADY_ATTEMPTED_NO_RETRY')
        self.cleanup_started = True
        capture_clear = not self.capture_called or self.capture_evidence is not None
        if self.handle_in_flight is not None:
            self.unknown = True
        if self.trusted is not None:
            try:
                self.cleanup.append(dict(kind='ordinary_target', **retire_ordinary(self.trusted)))
            except BaseException as error:
                self.unknown = True
                self.fail(error, 'ordinary_target_retirement')
        if self.listener is not None:
            try:
                self.listener.close()
                descriptor = self.listener.fileno()
                require(type(descriptor) is int and descriptor == -1, 'BRIDGE_LISTENER_CLOSE_UNPROVEN')
                self.cleanup.append(dict(kind='ordinary_loopback_listener', closed=True,
                                         descriptor_after_close=descriptor))
            except BaseException as error:
                self.unknown = True
                self.fail(error, 'listener_close')
        # An in-flight child close or unretired capture cannot be retried by
        # closing numeric handles here. Preserve the complete unresolved list.
        closure_clear = self.closure is None or self.closure.state in ('NOT_ATTEMPTED', 'CLOSED')
        if self.control is not None and capture_clear and closure_clear and self.handle_in_flight is None:
            for handle in tuple(self.handles):
                try:
                    self.control.close(handle)
                    self.handles.remove(handle)
                    self.cleanup.append(dict(kind='known_native_handle', handle=handle, closed=True))
                except BaseException as error:
                    self.unknown = True
                    self.fail(error, 'native_handle_close')
                    # Do not retry this handle even if CloseHandle returned then raised.
        residual = []
        for api in (self.creator, self.api):
            if api is not None:
                try:
                    residual.extend(api.pending_native_resources())
                    residual.extend(getattr(api, '_profile_folder_outputs', []))
                except BaseException as error:
                    self.unknown = True
                    self.fail(error, 'native_resource_observation')
        self.retired = capture_clear and closure_clear and not self.handles and not residual and not self.unknown
        self.record('BRIDGE-RETIREMENT.json', dict(all_owned_resources_retired=self.retired,
            capture_retirement_readback=self.capture_evidence is not None, cleanup=self.cleanup,
            unresolved_handles=list(self.handles), residual_native_resources=residual,
            unknown_native_operation=self.unknown, child_closure_state=None if self.closure is None else self.closure.state,
            closed_capture_handles_polled=False, automatic_retry=False))
        if not self.created:
            self.profile_cleanup = 'NOT_CREATED_OR_CREATE_RESULT_UNCERTAIN'
            return
        self.profile_cleanup = 'RETAINED_PROFILE_CUSTODY_OR_IDENTITY_UNPROVEN'
        if not (self.retired and self.sid_verified and self.created_recorded):
            return
        driver = self.driver
        require(read_reference(reference(self.directory / 'PROFILE-CREATED.json'))['actual_SID'] == driver.SID,
                'BRIDGE_PROFILE_CREATED_RECEIPT_CHANGED')
        require(driver.module.appcontainer_sid(driver.NAME) == driver.SID
                and driver.user_sid(self.creator) == driver.USER, 'BRIDGE_DELETE_IDENTITY_CHANGED')
        require(not self.creator.pending_native_resources() and not getattr(self.creator, '_profile_folder_outputs', []),
                'BRIDGE_DELETE_CALLER_CUSTODY_PENDING')
        self.record('PROFILE-DELETE-INTENT.json', dict(name=driver.NAME, SID=driver.SID,
            created_receipt=reference(self.directory / 'PROFILE-CREATED.json'),
            retirement=reference(self.directory / 'BRIDGE-RETIREMENT.json')))
        from ctypes import wintypes as WT
        import ctypes as C
        delete = self.creator.userenv.DeleteAppContainerProfile
        delete.argtypes, delete.restype = [WT.LPCWSTR], C.c_int32
        self.delete_called = True
        status = delete(driver.NAME)
        self.record('PROFILE-DELETE-RETURN.json', dict(HRESULT=status, name=driver.NAME, SID=driver.SID))
        post = driver.folder(self.creator, driver.SID)
        self.profile_cleanup = ('DELETE_SUCCEEDED_AND_FOLDER_ABSENCE_OBSERVED'
            if type(status) is int and status == 0 and post['HRESULT'] in (-2147024894, -2147024893)
            and post['path'] is None else 'DELETE_RESULT_OR_ABSENCE_UNPROVEN')
        self.record('PROFILE-AFTER.json', dict(observation=post, cleanup_status=self.profile_cleanup,
            contents_read=False, recursive_delete=False, perfect_erasure_claim=False))
        require(not self.creator.pending_native_resources() and not getattr(self.creator, '_profile_folder_outputs', []),
                'BRIDGE_POST_DELETE_CUSTODY_PENDING')

    def execute(self):
        # Admission already checked absence; create-only is the durable one-nonce
        # fence. Even failure after mkdir cannot be reused automatically.
        # Direct use of this concrete port cannot skip the public admission.
        self.plan = preflight(self.plan.request_reference)
        self.directory = self.plan.paths['directory']
        self.authorized = True
        self.live()
        ordinary_path(self.directory).mkdir(exist_ok=False)
        self.record('BRIDGE-ATTEMPT.json', dict(request=self.plan.request_reference,
            original_human_grant=self.plan.request['owner_grant'], nonce=self.plan.request['nonce'],
            lease=self.plan.lease_evidence, automatic_retry=False, native_qualification=False))
        try:
            self.phase = 'LOAD_PINNED_DEFINITIONS'
            self.load()
            identity = self.driver.fs.file_identity(self.driver.fs.lstat(self.driver.fs.safe_components(self.directory)))
            self.phase = 'CANONICAL_PREPARE_PROBE'
            self.helper = self.driver.prepare_probe(self.directory, owned_identity=identity)
            self.phase = 'PROFILE_CREATION'
            self.create_profile()
            self.phase = 'CANONICAL_PREPARE_CALL'
            context, launch, parents, event = self.prepare_call()
            self.phase = 'OWNED_CAPTURE'
            self.capture(context, launch, parents)
            self.phase = 'ORACLE_OBSERVATION'
            self.observe(launch, event)
        except BaseException as error:
            self.fail(error, self.phase)
            if self.phase in ('CANONICAL_PREPARE_PROBE', 'PROFILE_CREATION', 'CANONICAL_PREPARE_CALL'):
                # Original helpers retain their own cleanup rules. Without a
                # returned complete resource inventory, this bridge cannot
                # establish that an interrupted native allocation was empty.
                self.unknown = True
            data = BaseException.__dict__['__dict__'].__get__(error)
            if data.get('owned_process') is not None and self.capture_evidence is None:
                # Do not adopt, poll or retry a constructor/debug cleanup owner.
                self.unknown = True
        finally:
            try:
                self.cleanup_once()
            except BaseException as error:
                self.unknown = True
                self.retired = False
                self.fail(error, 'cleanup_once')
            try:
                self.inputs_conserved = self.inputs_before is not None and self.inputs_before == self.source_cut()
                require(self.inputs_conserved, 'BRIDGE_PINNED_SOURCES_CHANGED_DURING_ATTEMPT')
            except BaseException as error:
                self.fail(error, 'source_conservation')
        summary = dict(kind='CETA_CANONICAL_OWNED_LOADER_DIAGNOSTIC_RESULT_V1',
            request=self.plan.request_reference, nonce=self.plan.request['nonce'],
            diagnostic_completed=self.capture_evidence is not None and self.inputs_conserved,
            isolation_oracle_passed=self.oracle_passed, failures=self.failures,
            all_owned_resources_retired=self.retired, profile_cleanup=self.profile_cleanup,
            create_called=self.create_called, created_this_attempt=self.created,
            delete_called=self.delete_called, pinned_source_bytes_conserved=self.inputs_conserved,
            capture_references=None if self.capture_evidence is None else self.capture_evidence['references'],
            original_human_grant=self.plan.request['owner_grant'], automatic_retry=False,
            native_qualification=False, product_acceptance=False,
            causality='Only explicit captured loader diagnostics may narrow UNKNOWN; fresh diagnostic is not historic timeout proof')
        self.record('BRIDGE-RESULT.json', summary)
        return summary
