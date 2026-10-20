"""AC7 launch adapter: original atomic isolation construction plus debug events.

This is qualification tooling. A Root-issued, independently reviewed live
release is mandatory and is never issued here. Existing profile preparation is
outside this adapter. It adds no profile, credential, registry or attach path.
"""
from dataclasses import asdict
from pathlib import Path
import ctypes as C
import hashlib
import importlib
import json
import os
import sys
import threading
import time
import traceback
from capture_core import (Collector, Limits, OwnedIdentity, CaptureError, require,
                          retain, BASE_AC7_FLAGS, DEBUG_ONLY_THIS_PROCESS,
                          EXCEPTION, EXIT_PROCESS, DBG_CONTINUE, DBG_EXCEPTION_NOT_HANDLED)
from win32_debug import Win32DebugPort, open_functions, file_pin

F=Path('T:/00-Active/Project-AI-CETA')
CODE=Path(__file__).resolve().parent
RUNTIME=F/'.agents/runtime/ac7-loader-capture-20261020'
WORKER_SHA256='3df03778e1e2f6f707d38b0869e04e262926f2d4c375f1d3d10562d3456443cc'
KIND='CETA_AC7_OWNED_DEBUG_CAPTURE_V1'
_active=False


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf8')


def strict_json(raw):
    def pairs(entries):
        value={}
        for key,item in entries:
            require(key not in value,'CAPTURE_DUPLICATE_JSON_KEY')
            value[key]=item
        return value
    def constant(value):raise CaptureError('CAPTURE_NONFINITE_JSON_CONSTANT:'+value)
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=constant)


def read_reference(reference):
    require(type(reference) is dict and set(reference)=={'repository_relative_path','sha256'},
            'CAPTURE_REFERENCE_SHAPE_INVALID')
    name=reference['repository_relative_path'];pin=reference['sha256']
    require(type(name) is str and name==name.replace('\\','/') and ':' not in name
            and all(part not in ('','.','..') for part in name.split('/')),
            'CAPTURE_REFERENCE_PATH_INVALID')
    path=F/name
    require(path.resolve().is_relative_to(F),'CAPTURE_REFERENCE_ESCAPE')
    current=F
    for part in Path(name).parts:
        current=current/part
        require(not current.is_symlink() and not current.is_junction(),'CAPTURE_REFERENCE_REPARSE')
    raw=path.read_bytes()
    require(hashlib.sha256(raw).hexdigest()==pin,'CAPTURE_REFERENCE_PIN_MISMATCH')
    return path,strict_json(raw)


def validate_release(value,now):
    required={'schema_version','kind','executor','repository','nonce','issued_at_ns','expires_at_ns',
              'code_manifest','inputs','worker_sha256','limits','allow_debug_creation',
              'allow_owned_debug_string_reads','allow_child_memory_writes','allow_existing_process_attach',
              'allow_profile_creation','allow_profile_deletion','allow_global_configuration',
              'automatic_retry','initial_breakpoint_policy','fixture_root','parent_output_handles'}
    require(type(value) is dict and set(value)==required,'CAPTURE_RELEASE_FIELDS_INVALID')
    require(type(value['schema_version']) is int and value['schema_version']==1
            and value['kind']==KIND and value['executor']=='/root' and value['repository']==str(F),
            'CAPTURE_ROOT_RELEASE_REQUIRED')
    require(type(value['nonce']) is str and len(value['nonce'])==32
            and all(c in '0123456789abcdef' for c in value['nonce']),'CAPTURE_NONCE_INVALID')
    require(type(value['issued_at_ns']) is int and type(value['expires_at_ns']) is int
            and 0<value['expires_at_ns']-value['issued_at_ns']<=1_800_000_000_000
            and value['issued_at_ns']<=now<value['expires_at_ns'],'CAPTURE_RELEASE_EXPIRED_OR_UNBOUNDED')
    require(value['worker_sha256']==WORKER_SHA256,'CAPTURE_AC7_IMAGE_REQUIRED')
    require(value['allow_debug_creation'] is True and value['allow_owned_debug_string_reads'] is True,
            'CAPTURE_DEBUG_EFFECT_NOT_AUTHORIZED')
    for field in ('allow_child_memory_writes','allow_existing_process_attach','allow_profile_creation',
                  'allow_profile_deletion','allow_global_configuration','automatic_retry'):
        require(value[field] is False,'CAPTURE_FORBIDDEN_EFFECT:'+field)
    require(value['initial_breakpoint_policy']=='continue_one_first_chance_breakpoint',
            'CAPTURE_BREAKPOINT_POLICY_UNREVIEWED')
    require(type(value['fixture_root']) is str and Path(value['fixture_root']).is_absolute()
            and Path(value['fixture_root']).resolve().is_relative_to(RUNTIME),
            'CAPTURE_PRIVATE_FIXTURE_ROOT_REQUIRED')
    handles=value['parent_output_handles']
    require(type(handles) is list and len(handles)==2 and len(set(handles))==2
            and all(type(item) is int and 0<item<(1<<64)-1 for item in handles),
            'CAPTURE_EXACT_BORROWED_OUTPUT_HANDLES_REQUIRED')
    require(type(value['limits']) is dict and set(value['limits'])==set(Limits.__dataclass_fields__),
            'CAPTURE_RELEASE_LIMITS_REQUIRED')
    return Limits(**value['limits'])


def error_record(error):
    try:message=str(error)
    except BaseException:message='<exception text unavailable>'
    try:trace=''.join(traceback.format_exception(type(error),error,error.__traceback__))
    except BaseException:trace='<exception traceback unavailable>'
    return dict(type=type(error).__name__,message=message,traceback=trace)


def write_new(path,raw):
    stream=path.open('xb');primary=None
    try:
        require(stream.write(raw)==len(raw),'CAPTURE_SHORT_WRITE')
        stream.flush();os.fsync(stream.fileno())
    except BaseException as error:primary=error;raise
    finally:
        try:stream.close()
        except BaseException as secondary:
            if primary is None:raise
            retain(primary,secondary=secondary)


def admission(release_path,release_sha256):
    path=Path(release_path)
    require(path.resolve().is_relative_to(RUNTIME),'CAPTURE_RELEASE_OUTSIDE_TOOL_SCOPE')
    raw=path.read_bytes()
    require(hashlib.sha256(raw).hexdigest()==release_sha256,'CAPTURE_RELEASE_PIN_MISMATCH')
    value=strict_json(raw);limits=validate_release(value,time.time_ns())
    _,manifest=read_reference(value['code_manifest'])
    require(manifest['author']=='/root/recovery_regression20' and manifest['native_execution'] is False,
            'CAPTURE_REVIEWED_CODE_MANIFEST_REQUIRED')
    require(set(manifest['code_hashes'])=={'capture_core.py','win32_debug.py','isolated_adapter.py'},
            'CAPTURE_COMPLETE_CODE_MANIFEST_REQUIRED')
    for name,pin in manifest['code_hashes'].items():
        candidate=CODE/name
        require(candidate.resolve().is_relative_to(CODE) and hashlib.sha256(candidate.read_bytes()).hexdigest()==pin,
                'CAPTURE_CODE_CHANGED')
    _,inputs=read_reference(value['inputs'])
    require(Path(sys.executable)==F/'.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
            and file_pin(sys.executable)==inputs['python'],'CAPTURE_PINNED_INTERPRETER_REQUIRED')
    for row in inputs['native_system_libraries'].values():
        require(file_pin(row['path'])==row,'CAPTURE_NATIVE_LIBRARY_INPUT_CHANGED')
    frozen=Path(inputs['ac7_candidate'])
    require(frozen==F/'.agents/ac7-token-contract-20261020','CAPTURE_FROZEN_AC7_CANDIDATE_REQUIRED')
    _,ac7_manifest=read_reference(inputs['ac7_manifest'])
    require(ac7_manifest['root']==str(frozen) and ac7_manifest['payload_hashes']==inputs['ac7_payload_hashes']
            and len(inputs['ac7_payload_hashes'])==357,'CAPTURE_COMPLETE_FROZEN_AC7_INPUTS_REQUIRED')
    for name,pin in inputs['ac7_payload_hashes'].items():
        require(hashlib.sha256((frozen/name).read_bytes()).hexdigest()==pin,'CAPTURE_FROZEN_AC7_INPUT_CHANGED')
    directory=RUNTIME/('capture-'+value['nonce'])
    directory.mkdir(exist_ok=False)
    write_new(directory/'ATTEMPT.json',canonical(dict(release_path=str(path),release_sha256=release_sha256,
        nonce=value['nonce'],worker_sha256=WORKER_SHA256,automatic_retry=False)))
    return value,limits,inputs,directory


class CreateProcessDebugHook:
    """The original call's only native input change is flag 0x2.

    The original output-pointer object is retained before the native call. No
    post-call observer runs before the canonical constructor receives its result.
    """
    def __init__(self,original,startup_type=None):
        self.original=original
        self.startup_type=startup_type
        self.calls=0
        self.arguments=None
        self.information_pointer=None
        self.state='NOT_CALLED'
        self.native_inputs=None
        self.creator_thread=threading.get_ident()

    def __call__(self,*arguments):
        require(threading.get_ident()==self.creator_thread and self.calls==0,'CAPTURE_ONE_CREATOR_CALL_REQUIRED')
        require(len(arguments)==10 and arguments[5]==BASE_AC7_FLAGS,'CAPTURE_CANONICAL_CREATION_FLAGS_REQUIRED')
        require(type(arguments[4]) is bool,'CAPTURE_CANONICAL_INHERITANCE_REQUIRED')
        require(isinstance(arguments[6],C.Array) and arguments[6]._type_ is C.c_wchar
                and C.sizeof(arguments[6])<=131_072,'CAPTURE_BOUNDED_NATIVE_ENVIRONMENT_REQUIRED')
        require(type(arguments[0]) is str and type(arguments[7]) is str,
                'CAPTURE_NATIVE_PATH_STRINGS_REQUIRED')
        require(isinstance(arguments[1],C.Array) and arguments[1]._type_ is C.c_wchar
                and len(arguments[1])<=32768,'CAPTURE_NATIVE_COMMAND_BUFFER_REQUIRED')
        environment=C.string_at(C.addressof(arguments[6]),C.sizeof(arguments[6]))
        self.native_inputs=dict(application=arguments[0],command_line=arguments[1].value,
            cwd=arguments[7],inherit_handles=arguments[4],flags_before=arguments[5],
            flags_after=arguments[5]|DEBUG_ONLY_THIS_PROCESS,environment_buffer_hex=environment.hex(),
            environment_buffer_sha256=hashlib.sha256(environment).hexdigest())
        if self.startup_type is not None:
            startup=C.cast(arguments[8],C.POINTER(self.startup_type)).contents
            self.native_inputs['startup']=dict(flags=int(startup.startup.flags),
                stdin=int(startup.startup.stdin or 0),stdout=int(startup.startup.stdout or 0),
                stderr=int(startup.startup.stderr or 0))
        self.arguments=arguments
        self.information_pointer=arguments[9]
        changed=list(arguments);changed[5]=BASE_AC7_FLAGS|DEBUG_ONLY_THIS_PROCESS
        self.calls=1
        self.state='NATIVE_CALL_ISSUED_RETURN_OBSERVED_BY_CANONICAL_LAUNCHER'
        return self.original(*changed)


class Session:
    def __init__(self,owner,port,limits,directory,hook):
        self.owner,self.port,self.directory,self.hook=owner,port,directory,hook
        self.identity=OwnedIdentity(owner.pid,owner.creation_time,owner.image_sha256)
        self.collector=Collector(port,self.identity,limits)
        self.report=None
        self.retirement_started=False

    def collect(self):
        primary=None
        try:
            self.report=self.collector.run()
            return self.report
        except BaseException as error:
            primary=error
            retain(error,capture=self,owner=self.owner)
            raise
        finally:
            try:self.persist(primary)
            except BaseException as secondary:
                if primary is None:retain(secondary,capture=self,owner=self.owner);raise
                retain(primary,capture=self,owner=self.owner,secondary=secondary)

    def persist(self,primary=None):
        report=self.collector.report()
        report.update(primary_error=None if primary is None else error_record(primary),
            original_launch_environment=list(self.owner.launch_environment),
            parent_launch_token_facts={name:getattr(self.owner.launch_token_facts,name)
                                     for name in self.owner.launch_token_facts.__slots__},
            native_creation_flags_before=BASE_AC7_FLAGS,
            native_creation_flags_after=BASE_AC7_FLAGS|DEBUG_ONLY_THIS_PROCESS,
            native_create_inputs=self.hook.native_inputs,
            original_isolation_job_token_handle_path_construction=True,
            lifetime_retired=False,native_qualification=False)
        self.report=report
        raw_events=b''.join(canonical(row)+b'\n' for row in report['events'])
        for name,raw in (('events.jsonl',raw_events),('stdout.bin',bytes(self.collector.stdout)),
                         ('stderr.bin',bytes(self.collector.stderr))):
            write_new(self.directory/name,raw)
        write_new(self.directory/'RESULT.json',json.dumps(report,indent=2,allow_nan=False).encode('utf8')+b'\n')

    def retire(self,seconds=5.0):
        """One explicit bounded retirement; unknown native calls are not replayed."""
        require(type(seconds) in (int,float) and 0<seconds<=5,'CAPTURE_RETIRE_BOUND_INVALID')
        require(not self.retirement_started,'CAPTURE_RETIRE_ALREADY_ATTEMPTED')
        self.retirement_started=True
        try:
            if self.owner.poll() is None or self.owner.active_process_count():self.owner.terminate(125)
            deadline=time.monotonic()+seconds;count=0
            while not self.port.exit_continued:
                require(time.monotonic()<deadline and count<128,'CAPTURE_RETIRE_DEBUG_EVENTS_PENDING')
                require(self.port.state in ('IDLE','EVENT'),'CAPTURE_RETIRE_UNKNOWN_NATIVE_CALL_NO_REPLAY')
                if self.port.state=='IDLE' and not self.port.wait(50):continue
                require(int(self.port.event.pid)==self.identity.pid,'CAPTURE_RETIRE_FOREIGN_EVENT')
                code=int(self.port.event.code)
                require(code in range(1,10),'CAPTURE_RETIRE_UNKNOWN_EVENT')
                status=DBG_EXCEPTION_NOT_HANDLED if code==EXCEPTION else DBG_CONTINUE
                self.port.continue_current(status);count+=1
            require(self.owner.wait(max(0.0,deadline-time.monotonic())),'CAPTURE_RETIRE_PROCESS_PENDING')
            require(self.owner.active_process_count()==0,'CAPTURE_RETIRE_JOB_PENDING')
            self.owner.close()
            require(self.owner.lifetime_closed,'CAPTURE_RETIRE_NATIVE_HANDLES_PENDING')
            result=dict(lifetime_closed=True,debug_exit_continued=True,native_pending=self.port.pending(),
                        pid=self.identity.pid,creation_time=self.identity.creation_time)
            write_new(self.directory/'RETIREMENT.json',canonical(result))
            return result
        except BaseException as primary:
            retain(primary,capture=self,owner=self.owner)
            raise


def launch_isolated_capture(*,release_path,release_sha256,launch_arguments,
                            stdout_handle,stderr_handle):
    """Call the frozen AC7 launcher; return before pumping so child pipe ends close.

    The caller closes its child pipe ends exactly as the existing AC7 driver
    does, then calls collect(), consumes stdout/stderr bytes, and calls retire()
    in a finally block. These parent read handles remain borrowed throughout.
    """
    global _active
    require(not _active,'CAPTURE_PROCESS_LOCAL_SINGLE_LAUNCH_REQUIRED')
    release,limits,inputs,directory=admission(release_path,release_sha256)
    require(not any(name=='ceta' or name.startswith('ceta.') for name in sys.modules),
            'CAPTURE_FRESH_QUALIFICATION_INTERPRETER_REQUIRED')
    require(type(launch_arguments) is dict and launch_arguments.get('expected_image_sha256')==WORKER_SHA256,
            'CAPTURE_EXACT_AC7_LAUNCH_REQUIRED')
    require(set(launch_arguments)=={'executable','arguments','cwd','scratch_root','expected_image_sha256',
                                  'appcontainer_name','inherited_handles','standard_handles'},
            'CAPTURE_LAUNCH_INTERFACE_CHANGED')
    require([stdout_handle,stderr_handle]==release['parent_output_handles'],
            'CAPTURE_OUTPUT_HANDLES_CHANGED')
    fixture=Path(release['fixture_root']).resolve()
    for name in ('executable','cwd','scratch_root'):
        require(Path(launch_arguments[name]).resolve().is_relative_to(fixture),
                'CAPTURE_LAUNCH_OUTSIDE_RELEASED_FIXTURE:'+name)
    sys.path.insert(0,str(Path(inputs['ac7_candidate'])/'src'))
    isolation=importlib.import_module('ceta.supervisor.isolated_worker')
    for name,module in tuple(sys.modules.items()):
        if name=='ceta' or name.startswith('ceta.'):
            actual=Path(module.__file__).resolve()
            require(actual.is_relative_to(Path(inputs['ac7_candidate'])),
                    'CAPTURE_CETA_IMPORT_ORIGIN_CHANGED:'+name)
            relative=actual.relative_to(Path(inputs['ac7_candidate'])).as_posix()
            require(hashlib.sha256(actual.read_bytes()).hexdigest()==inputs['ac7_payload_hashes'][relative],
                    'CAPTURE_CETA_IMPORTED_BYTES_CHANGED:'+name)
    for name in ('src/ceta/supervisor/isolated_worker.py','src/ceta/supervisor/windows_jobs.py'):
        require(hashlib.sha256((Path(inputs['ac7_candidate'])/name).read_bytes()).hexdigest()==inputs['ac7_payload_hashes'][name],
                'CAPTURE_CANONICAL_LAUNCHER_CHANGED')
    original=isolation._IsolationAPI
    hooks=[]
    def api_factory():
        api=original();hook=CreateProcessDebugHook(api.CreateProcessW,isolation.STARTUPINFOEX)
        hooks.append(hook);api.CreateProcessW=hook
        return api
    functions=open_functions(inputs['native_system_libraries'])
    owner=None
    _active=True
    isolation._IsolationAPI=api_factory
    port=None
    try:
        owner=isolation.IsolatedWindowsWorker.launch(**launch_arguments)
    except BaseException as primary:
        # The canonical exception/cleanup owner is preserved unchanged. No numeric
        # PID is opened and no uncertain constructor cleanup is repeated here.
        data=BaseException.__dict__['__dict__'].__get__(primary)
        dict.update(data,loader_capture_launch_hooks=hooks,loader_capture_directory=str(directory),
                    loader_capture_automatic_retry=False)
        try:write_new(directory/'LAUNCH-FAILURE.json',canonical(error_record(primary)))
        except BaseException as secondary:retain(primary,secondary=secondary)
        raise
    finally:
        isolation._IsolationAPI=original
    try:
        require(len(hooks)==1 and hooks[0].calls==1,'CAPTURE_CANONICAL_SINGLE_CREATE_NOT_OBSERVED')
        identity=OwnedIdentity(owner.pid,owner.creation_time,owner.image_sha256)
        port=Win32DebugPort.__new__(Win32DebugPort)
        Win32DebugPort.__init__(port,functions,identity,stdout_handle=stdout_handle,stderr_handle=stderr_handle)
        return Session(owner,port,limits,directory,hooks[0])
    except BaseException as primary:
        retain(primary,owner=owner)
        data=BaseException.__dict__['__dict__'].__get__(primary)
        dict.update(data,loader_capture_launch_hooks=hooks,loader_capture_directory=str(directory),
                    loader_capture_port=port)
        raise
