"""One ordinary own-job Python supervisor for a separately approved bridge.

Data-only until both this request and the unchanged bridge's preflight pass.
This consumes existing custody and Root provenance; it issues no authority.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import stat
import sys
import time
import types

F=Path('T:/00-Active/Project-AI-CETA')
W=Path(__file__).resolve().parent
INPUTS=W/'INPUTS.json'
KIND='CETA_CANONICAL_BRIDGE_OUTER_REQUEST_V1'
EFFECTS=['one_pinned_ordinary_own_job_python_child','bounded_outer_stdout_stderr_results_and_temp',
         'exact_owned_job_interpreter_readonly_query_identity_and_exit',
         'terminate_and_retire_only_exact_returned_outer_job_once','no_profile_cleanup_by_supervisor']
JSON_BOUND=1048576
LOG_BOUND=1048576
CHILD_BOUND=262144
_entered=False


class SupervisorError(RuntimeError):pass


def require(value,reason):
    if not value:raise SupervisorError(reason)


def digest(raw):return hashlib.sha256(raw).hexdigest()


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf8')


def safe(path):
    path=Path(path)
    require(path.is_absolute() and path.is_relative_to(F),'OUTER_PROJECT_PATH_REQUIRED')
    current=F
    for part in path.relative_to(F).parts:
        require(part not in ('','.','..') and ':' not in part,'OUTER_PATH_COMPONENT')
        current/=part
        try:info=current.lstat()
        except FileNotFoundError:continue
        require(not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&0x400,'OUTER_REPARSE_REFUSED')
    return path


def read(path,bound=JSON_BOUND):
    path=safe(path);before=path.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_size<=bound,'OUTER_READ_BOUND')
    with path.open('rb') as stream:raw=stream.read(bound+1)
    after=path.stat()
    require(len(raw)==before.st_size<=bound and all(getattr(before,k)==getattr(after,k) for k in
        ('st_dev','st_ino','st_size','st_mtime_ns')),'OUTER_FILE_CHANGED')
    return raw


def strict(raw):
    require(type(raw) is bytes and len(raw)<=JSON_BOUND,'OUTER_JSON_BOUND')
    def pairs(rows):
        result={}
        for k,v in rows:
            require(k not in result,'OUTER_DUPLICATE_JSON_KEY');result[k]=v
        return result
    def constant(_):raise SupervisorError('OUTER_NONFINITE_JSON')
    try:return json.loads(raw,object_pairs_hook=pairs,parse_constant=constant)
    except (ValueError,RecursionError) as error:raise SupervisorError('OUTER_BAD_JSON') from error


def ref(path):
    path=safe(path);return dict(repository_relative_path=path.relative_to(F).as_posix(),sha256=digest(read(path)))


def ref_path(value):
    require(type(value) is dict and set(value)=={'repository_relative_path','sha256'},'OUTER_REFERENCE_FIELDS')
    name,pin=value['repository_relative_path'],value['sha256']
    require(type(name) is str and '\\' not in name and ':' not in name and not name.startswith('/')
        and all(p not in ('','.','..') for p in name.split('/')),'OUTER_REFERENCE_PATH')
    require(type(pin) is str and len(pin)==64 and all(c in '0123456789abcdef' for c in pin),'OUTER_REFERENCE_HASH')
    return safe(F/name)


def read_ref(value):
    raw=read(ref_path(value));require(digest(raw)==value['sha256'],'OUTER_REFERENCE_CHANGED');return strict(raw)


def save_new(path,value):
    raw=canonical(value)+b'\n';require(len(raw)<=JSON_BOUND,'OUTER_EVIDENCE_BOUND')
    with safe(path).open('xb') as stream:
        require(stream.write(raw)==len(raw),'OUTER_SHORT_WRITE');stream.flush();os.fsync(stream.fileno())


def error_record(error):
    try:message=str(error)
    except BaseException:message='<exception text unavailable>'
    return dict(type=type(error).__name__,message=message[:8192])


def attach(primary,**values):dict.update(BaseException.__dict__['__dict__'].__get__(primary),values)


def load_exact(name,path,pin):
    require(name not in sys.modules,'OUTER_PRELOADED_MODULE_REFUSED:'+name)
    require(digest(read(path))==pin,'OUTER_MODULE_BYTES_CHANGED')
    spec=importlib.util.spec_from_file_location(name,path)
    require(spec is not None and spec.loader is not None,'OUTER_SOURCE_LOADER_REQUIRED')
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    spec.loader.exec_module(module)
    return module


def own_paths(nonce):
    require(type(nonce) is str and len(nonce)==32 and all(c in '0123456789abcdef' for c in nonce),'OUTER_NONCE')
    directory=W.parent/'native-attempts'/('outer-'+nonce)
    return dict(directory=directory,temp=directory/'tmp',envelope=directory/'ENVELOPE.json',
        marker=directory/'ATTEMPT.json',owner=directory/'OWNER.json',owner_ready=directory/'OWNER.READY.json',
        hello=directory/'HELLO.json',hello_ready=directory/'HELLO.READY.json',stdout=directory/'stdout.bin',
        stderr=directory/'stderr.bin',child=directory/'CHILD-RESULT.json',terminal=directory/'TERMINAL.json')


def extra_scopes(nonce):
    root=own_paths(nonce)['directory']
    return sorted([root.parent.relative_to(Path('T:/')).as_posix(),root.relative_to(Path('T:/')).as_posix()+'/**'])


def validate_domain(request,bridge_plan,action,anchor,inputs,now):
    required={'schema_version','kind','repository','executor','nonce','issued_at_ns','expires_at_ns',
        'bridge_request','bridge_freeze','supervisor_freeze','action_review','root_ingress','lease',
        'filesystem_scopes','timeout_seconds','stdio_bound','child_result_bound'}
    require(type(request) is dict and set(request)==required and type(request['schema_version']) is int
        and request['schema_version']==1 and request['kind']==KIND,'OUTER_REQUEST_FIELDS')
    require(request['repository']==str(F) and request['executor']=='/root','OUTER_REPOSITORY_EXECUTOR')
    paths=own_paths(request['nonce']);bridge=bridge_plan.request
    require(request['nonce']==bridge['nonce'] and request['bridge_freeze']==bridge['bridge_freeze']
        and request['lease']==bridge['lease'],'OUTER_BRIDGE_JOIN_MISMATCH')
    require(type(request['issued_at_ns']) is int and type(request['expires_at_ns']) is int
        and request['issued_at_ns']<=now<request['expires_at_ns']<=bridge['expires_at_ns']
        and 0<request['expires_at_ns']-request['issued_at_ns']<=1800_000_000_000
        and request['expires_at_ns']-now>=150_000_000_000,'OUTER_EXPIRY')
    require(type(request['timeout_seconds']) is int and 1<=request['timeout_seconds']<=100,'OUTER_WAIT_BOUND')
    require(type(request['stdio_bound']) is int and 1<=request['stdio_bound']<=LOG_BOUND
        and type(request['child_result_bound']) is int and 1<=request['child_result_bound']<=CHILD_BOUND,'OUTER_LOG_BOUNDS')
    expected=sorted(bridge['filesystem_scopes']+extra_scopes(request['nonce']))
    require(request['filesystem_scopes']==expected,'OUTER_EXACT_FS_SCOPES')
    require(request['root_ingress']==bridge_plan.inputs['trusted_owner_ingress_reference'],
        'OUTER_SAME_TRUSTED_ROOT_INGRESS_REQUIRED')
    authorization=anchor.get('outer_supervisor')
    require(type(authorization) is dict and authorization.get('code_hashes')==inputs['code_hashes']
        and authorization.get('nonce')==request['nonce'] and authorization.get('effects')==EFFECTS
        and authorization.get('filesystem_scopes')==expected
        and type(authorization.get('maximum_timeout_seconds')) is int
        and request['timeout_seconds']<=authorization['maximum_timeout_seconds'],
        'OUTER_EXPLICIT_ROOT_INGRESS_EFFECTS_REQUIRED')
    require(type(action) is dict and action.get('decision')=='approve' and type(action.get('exit_status')) is int
        and action['exit_status']==0 and action.get('executor_id') not in (None,'','/root/review')
        and type(action.get('result')) is dict,'OUTER_DISTINCT_ACTION_REVIEW_REQUIRED')
    result=action['result']
    for name in ('supervisor_freeze','bridge_freeze','root_ingress','bridge_request'):
        require(result.get(name)==request[name],'OUTER_ACTION_BINDING:'+name)
    require(result.get('bridge_action_review')==bridge['action_review'] and result.get('effects')==EFFECTS
        and result.get('filesystem_scopes')==expected
        and result.get('scope')=='ONE_ORDINARY_SUPERVISOR_AND_ONE_CANONICAL_BRIDGE_ATTEMPT',
        'OUTER_ACTION_SCOPE')
    return paths


def verify_supervisor_freeze(value):
    require(ref_path(value)==W/'FROZEN.json','OUTER_OWN_REVIEWED_FREEZE_REQUIRED')
    frozen=read_ref(value)
    require(frozen['kind']=='CETA_LOADER_BRIDGE_SUPERVISOR_FREEZE_V1' and frozen['author']=='/root/review'
        and frozen['native_execution'] is False,'OUTER_FREEZE_KIND')
    require({'supervisor.py','child_entry.py','owned_interpreter.py','INPUTS.json'}<=set(frozen['files']),
        'OUTER_FREEZE_REQUIRED_FILES')
    for name,pin in frozen['files'].items():require(digest(read(W/name))==pin,'OUTER_FROZEN_BYTES_CHANGED:'+name)


def verify_base_python(pin):
    # This separately declared installed interpreter is a permitted dependency,
    # never an inferred project/source location. No executable is loaded here.
    expected=Path('C:/Users/Quencher/AppData/Local/Programs/Python/Python312/python.exe')
    require(type(pin) is dict and Path(pin.get('path',''))==expected,'OUTER_EXACT_BASE_PYTHON_PATH')
    require(type(pin.get('bytes')) is int and 0<pin['bytes']<=16*1024*1024,'OUTER_BASE_PYTHON_SIZE_BOUND')
    for path in (expected,*expected.parents):
        info=path.lstat()
        require(not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&0x400,
                'OUTER_BASE_PYTHON_REPARSE_REFUSED')
    before=expected.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_size==pin['bytes'],'OUTER_BASE_PYTHON_SIZE_CHANGED')
    with expected.open('rb') as stream:raw=stream.read(pin['bytes']+1)
    after=expected.stat()
    require(len(raw)==pin['bytes'] and digest(raw)==pin['sha256']
        and all(getattr(before,k)==getattr(after,k) for k in ('st_dev','st_ino','st_size','st_mtime_ns')),
        'OUTER_BASE_PYTHON_BYTES_OR_IDENTITY_CHANGED')


def validate_extra_lease(b,request):
    b.validate_lease(request['lease'],request['nonce'])
    lease=request['lease'];root=F/lease['control_root']/lease['run_id']
    claims=b.strict_json(b.read_bytes(root/'claims.json'));graph=b.strict_json(b.read_bytes(root/'graph.json'))['graph']
    claim=claims[lease['node_id']]
    for needed in extra_scopes(request['nonce']):
        require(any(b.scope_covers(s,needed) for s in claim['effective_write_scope'])
            and any(b.scope_covers(s,needed) for s in graph['nodes'][lease['node_id']]['write_scope']),
            'OUTER_ADDITIONAL_PATH_NOT_LEASED:'+needed)


def admission(request_ref,*,child=False):
    request=read_ref(request_ref);inputs=strict(read(INPUTS))
    verify_supervisor_freeze(request['supervisor_freeze'])
    require(inputs['bridge_review'] is not None,'OUTER_ACCEPTED_BRIDGE_REVIEW_PENDING')
    review=read_ref(inputs['bridge_review'])
    require(review['decision']=='approved' and review['exit_status']==0 and review['executor_id']!='/root/review',
        'OUTER_ACCEPTED_BRIDGE_REVIEW_REQUIRED')
    base=read_ref(inputs['bridge_base_freeze']);future=read_ref(request['bridge_freeze'])
    require(review['result']['source_freeze']['sha256']==inputs['bridge_base_freeze']['sha256']
        and review['result']['exact_python_hashes']==base['python_hashes'],'OUTER_BRIDGE_REVIEW_SOURCE_MISMATCH')
    for record in inputs['bridge_acceptance_records']:read_ref(record)
    terminal=read_ref(inputs['bridge_terminal_verification'])['response']
    require(terminal['receipts_valid'] is True and terminal['terminal_success'] is True
        and set(terminal['states'])=={'discover','plan','implement','review','validate','integrate'}
        and all(v=='SUCCEEDED' for v in terminal['states'].values()),'OUTER_BRIDGE_TERMINAL_ACCEPTANCE_REQUIRED')
    require(future['kind']==base['kind'] and future['python_hashes']==base['python_hashes'],
        'OUTER_UNREVIEWED_BRIDGE_CODE_CHANGED')
    # A successor may join fresh Root ingress into immutable inputs; its source
    # remains the independently reviewed exact bridge source. No files are edited.
    bridge_root=ref_path(request['bridge_freeze']).parent
    require(all(digest(read(bridge_root/name))==pin for name,pin in base['python_hashes'].items()),
        'OUTER_BRIDGE_SOURCE_BYTES_CHANGED')
    require('capture_bridge' not in sys.modules,'OUTER_FRESH_BRIDGE_MODULE_REQUIRED')
    b=load_exact('capture_bridge',bridge_root/'capture_bridge.py',base['python_hashes']['capture_bridge.py'])
    # Crucially, NULL trusted ingress refuses here before custody import,
    # canonical constructors, outer directory creation or native child launch.
    bridge_plan=b.preflight(request['bridge_request'])
    verify_base_python(inputs['base_python_pin'])
    action=read_ref(request['action_review']);anchor=read_ref(request['root_ingress'])
    paths=validate_domain(request,bridge_plan,action,anchor,inputs,time.time_ns())
    validate_extra_lease(b,request)
    require(not paths['directory'].exists() if not child else paths['directory'].is_dir(),
        'OUTER_ONE_ATTEMPT_DIRECTORY_STATE')
    return dict(request=request,request_reference=request_ref,inputs=inputs,bridge=b,bridge_plan=bridge_plan,paths=paths)


def publish_owner(paths,owner,*,write=save_new,link=os.link):
    # save_new returns only after complete write/flush/fsync/close. A hard link
    # publishes that already complete inode atomically and refuses overwrite.
    write(paths['owner'],owner)
    link(safe(paths['owner']),safe(paths['owner_ready']))


def execute_custody(custody,launch,emit,read_child,write_terminal,*,timeout):
    """Preserve original outcome even if terminal evidence cannot be persisted."""
    primary=None;report=None
    try:report=custody.run_owned(launch,emit,read_child,timeout=timeout)
    except BaseException as error:
        primary=error
        data=BaseException.__dict__['__dict__'].__get__(error)
        report=dict.get(data,'full_runner_report')
    child=report.get('child_result') if type(report) is dict else None
    exit_consistent=(type(report) is dict and type(child) is dict and type(report.get('child_exit')) is int
        and type(child.get('exit_status')) is int and report['child_exit']==child['exit_status'])
    terminal=dict(kind='CETA_LOADER_BRIDGE_OUTER_TERMINAL_V1',custody=report,
        original_error=None if primary is None else error_record(primary),
        supervisor_custody_proven=type(report) is dict and type(report.get('native_owner_after')) is dict
            and bool(report['native_owner_after']) and all(v is True for v in report['native_owner_after'].values())
            and report.get('retirement_error') is None,
        child_exit_consistent=exit_consistent,
        child_receipt_valid=type(child) is dict and child.get('receipt_valid') is True and exit_consistent,
        profile_state_requires_operator_inspection=primary is not None or type(report) is not dict
            or report.get('child_exit')!=0 or type(report.get('child_result')) is not dict
            or report['child_result'].get('profile_cleanup_proven') is not True,
        profile_cleanup_by_supervisor=False,automatic_retry=False,native_qualification=False,product_acceptance=False)
    try:write_terminal(terminal)
    except BaseException as evidence_error:
        if primary is not None:
            attach(primary,outer_terminal_evidence_error=evidence_error,outer_terminal=terminal)
        else:
            attach(evidence_error,outer_terminal=terminal,original_custody_report=report)
            raise
    if primary is not None:
        attach(primary,outer_terminal=terminal)
        raise primary
    return terminal


def load_native_owner(plan):
    """Lazy original constructor validation; no provider is loaded by import."""
    inputs=plan['bridge_plan'].source_inputs;b=plan['bridge']
    root=b.R5;code=b.read_reference(plan['bridge_plan'].inputs['loader_code_manifest'])
    require('caller_boundary' not in sys.modules,'OUTER_FRESH_CALLER_BOUNDARY_REQUIRED')
    sys.path.insert(0,str(root))
    boundary=load_exact('caller_boundary',root/'caller_boundary.py',code['code_hashes']['caller_boundary.py'])
    admitted=boundary.validate_ceta_modules(inputs)
    for module,raw in admitted.values():boundary.validate_definitions(module,raw)
    return sys.modules['ceta.supervisor.windows_jobs'].WindowsOwnedProcess


def child_argv(plan,envelope_reference=None):
    p=plan['paths'];python=plan['bridge_plan'].source_inputs['python']['path']
    return (python,'-I','-B','-X','utf8',str(W/'child_entry.py'),'--envelope',str(p['envelope']),
            '--sha256',(envelope_reference or ref(p['envelope']))['sha256'])


def read_child_receipt(plan):
    p=plan['paths'];request=plan['request'];result=strict(read(p['child'],request['child_result_bound']))
    require(result['kind']=='CETA_LOADER_BRIDGE_OUTER_CHILD_V1' and result['nonce']==request['nonce']
        and result['outer_request']==plan['request_reference'] and result['bridge_request']==request['bridge_request'],
        'OUTER_CHILD_RESULT_BINDING')
    owner=read_ref(ref(p['owner']))
    require(result['pid']==owner['interpreter']['pid']
        and result['parent_observed_creation_time']==owner['interpreter']['creation_time'],
        'OUTER_CHILD_IDENTITY_MISMATCH')
    require(result['supervisor_freeze']==request['supervisor_freeze']
        and result['argv']==owner['interpreter']['reported_argv'],
        'OUTER_CHILD_SOURCE_OR_ARGV_MISMATCH')
    for name in ('stdout','stderr'):
        raw=read(p[name],request['stdio_bound'])
        require(result[name+'_sha256']==digest(raw) and result[name+'_bytes']==len(raw),'OUTER_CHILD_STDIO_CHANGED')
    require(result['stdio_bound_exceeded'] is False and result['stdio_uncertain'] is False,
        'OUTER_CHILD_STDIO_BOUND_OR_UNCERTAIN')
    bridge=result.get('bridge_result');capture_valid=False;cleanup=False
    if type(bridge) is dict:
        bridge_plan=plan['bridge_plan'];b=plan['bridge']
        require(bridge.get('kind')=='CETA_CANONICAL_OWNED_LOADER_DIAGNOSTIC_RESULT_V1'
            and bridge.get('nonce')==request['nonce'] and bridge.get('request')==request['bridge_request'],
            'OUTER_INNER_BRIDGE_RESULT_BINDING')
        actual=b.strict_json(b.read_bytes(bridge_plan.paths['directory']/'BRIDGE-RESULT.json'))
        require(actual==bridge,'OUTER_INNER_BRIDGE_RECEIPT_CHANGED')
        if bridge.get('capture_references') is not None:
            captured=b.persisted_capture(bridge_plan)
            require(captured['references']==bridge['capture_references'],'OUTER_CAPTURE_RECEIPT_REFERENCE_CHANGED')
            capture_valid=True
        if bridge.get('all_owned_resources_retired') is True and bridge.get('profile_cleanup')=='DELETE_SUCCEEDED_AND_FOLDER_ABSENCE_OBSERVED':
            d=bridge_plan.paths['directory']
            created=b.strict_json(b.read_bytes(d/'PROFILE-CREATED.json'))
            retired=b.strict_json(b.read_bytes(d/'BRIDGE-RETIREMENT.json'))
            intent=b.strict_json(b.read_bytes(d/'PROFILE-DELETE-INTENT.json'))
            deleted=b.strict_json(b.read_bytes(d/'PROFILE-DELETE-RETURN.json'))
            post=b.strict_json(b.read_bytes(d/'PROFILE-AFTER.json'))
            require(created['original_human_grant']==bridge_plan.request['owner_grant']
                and intent['created_receipt']==b.reference(d/'PROFILE-CREATED.json')
                and intent['retirement']==b.reference(d/'BRIDGE-RETIREMENT.json')
                and created['actual_SID']==intent['SID']==deleted['SID']
                and retired['all_owned_resources_retired'] is True
                and type(deleted['HRESULT']) is int and deleted['HRESULT']==0
                and post['cleanup_status']==bridge['profile_cleanup']
                and post['observation']['HRESULT'] in (-2147024894,-2147024893)
                and post['observation']['path'] is None,'OUTER_PROFILE_CLEANUP_RECEIPTS_UNPROVEN')
            cleanup=True
    return dict(receipt_valid=True,reference=ref(p['child']),exit_status=result['exit_status'],
        original_error=result['original_error'],bridge_result=bridge,bridge_capture_receipts_valid=capture_valid,
        profile_cleanup_proven=cleanup,
        stdout=ref(p['stdout']),stderr=ref(p['stderr']))


def succeeded(terminal):
    """One success rule; process truth cannot be replaced by child prose."""
    if type(terminal) is not dict:return False
    report=terminal.get('custody');child=report.get('child_result') if type(report) is dict else None
    if type(report) is not dict or type(child) is not dict:return False
    return (terminal.get('supervisor_custody_proven') is True and terminal.get('child_receipt_valid') is True
        and terminal.get('child_exit_consistent') is True and terminal.get('original_error') is None
        and terminal.get('profile_state_requires_operator_inspection') is False
        and type(report.get('child_exit')) is int and report['child_exit']==0
        and type(child) is dict and type(child.get('exit_status')) is int and child['exit_status']==0
        and child.get('original_error') is None and child.get('profile_cleanup_proven') is True
        and child.get('bridge_capture_receipts_valid') is True and child.get('interpreter_custody_proven') is True)


def supervise(request_ref):
    global _entered
    require(not _entered,'OUTER_PROCESS_SINGLE_ATTEMPT')
    plan=admission(request_ref);_entered=True
    p=plan['paths'];request=plan['request'];b=plan['bridge']
    # All paths were explicitly admitted before first ordinary filesystem/native effect.
    safe(p['directory'].parent).mkdir(exist_ok=True)
    safe(p['directory']).mkdir(exist_ok=False);p['temp'].mkdir()
    save_new(p['marker'],dict(outer_request=request_ref,nonce=request['nonce'],automatic_retry=False))
    save_new(p['envelope'],dict(kind='CETA_LOADER_BRIDGE_OUTER_ENVELOPE_V1',outer_request=request_ref,
        supervisor_freeze=request['supervisor_freeze'],nonce=request['nonce'],supervisor_file=ref(W/'supervisor.py')))
    custody_row=plan['inputs']['existing_custody_primitive']
    custody=load_exact('loader_bridge_bounded_custody',ref_path(custody_row),custody_row['sha256'])
    owner_type=load_native_owner(plan)
    identity=load_exact('loader_bridge_owned_interpreter',W/'owned_interpreter.py',
        plan['inputs']['code_hashes']['owned_interpreter.py'])
    argv=child_argv(plan)
    environment={k:str(p['temp']) for k in ('TEMP','TMP','LOCALAPPDATA')}
    windows=str(Path(plan['bridge_plan'].source_inputs['native_system_libraries']['kernel32']['path']).parent.parent)
    environment.update(SystemRoot=windows,WINDIR=windows,PATH=str(Path(windows)/'System32'))
    save_new(p['directory']/'LAUNCH.json',dict(argv=list(argv),python_pin=plan['bridge_plan'].source_inputs['python'],
        supervisor_freeze=request['supervisor_freeze'],bridge_freeze=request['bridge_freeze'],
        environment=environment,inherited_handles=[],standard_handles=None,timeout_seconds=request['timeout_seconds'],
        nonce=request['nonce'],root_ingress=request['root_ingress'],native_qualification=False))
    state=dict(owner=None,selection=None,interpreter_retirement=None)
    def launch():
        # Current source, grant, clock and live scopes are checked again without
        # re-importing or altering any canonical class/launcher binding.
        validate_extra_lease(b,request)
        require(time.time_ns()<request['expires_at_ns'],'OUTER_EXPIRED_BEFORE_LAUNCH')
        b.verify_file(plan['bridge_plan'].source_inputs['python'])
        verify_base_python(plan['inputs']['base_python_pin'])
        owner=owner_type.launch(argv[0],tuple(argv[1:]),cwd=str(p['directory']),environment=environment,
            inherited_handles=(),standard_handles=None,
            expected_image_sha256=plan['bridge_plan'].source_inputs['python']['sha256'])
        state['owner']=owner;return owner
    def emit(root_owner):
        deadline=time.monotonic()+5
        while not p['hello_ready'].exists():
            require(time.monotonic()<deadline,'OUTER_INTERPRETER_HELLO_MISSING');time.sleep(.01)
        hello=read_ref(ref(p['hello_ready']))
        require(hello['nonce']==request['nonce'] and hello['outer_request']==request_ref
            and ref(p['hello'])['sha256']==ref(p['hello_ready'])['sha256'],'OUTER_INTERPRETER_HELLO_BINDING')
        jobs=sys.modules['ceta.supervisor.windows_jobs'];base=plan['inputs']['base_python_pin']
        port=identity.NativePort(jobs,state['owner'],[plan['bridge_plan'].source_inputs['python'],base])
        selection=identity.Selection(port);state['selection']=selection
        interpreter=selection.qualify(hello,argv,plan['bridge_plan'].source_inputs['python'],base)
        publish_owner(p,dict(root_redirector=root_owner,interpreter=interpreter,nonce=request['nonce'],outer_request=request_ref))
    def read_child():
        selection=state['selection']
        require(selection is not None,'OUTER_INTERPRETER_IDENTITY_NOT_OBSERVED')
        state['interpreter_retirement']=selection.retire_once()
        receipt=read_child_receipt(plan)
        exit_observation=state['interpreter_retirement']['retirement']
        require(type(exit_observation) is dict and exit_observation['exit_status']==receipt['exit_status'],
            'OUTER_INTERPRETER_ACTUAL_EXIT_MISMATCH')
        receipt['interpreter_custody_proven']=True
        return receipt
    def terminal(report):
        report['interpreter_retirement']=state['interpreter_retirement']
        report['launch_argv']=list(argv)
        report['interpreter_identity']=None if state['selection'] is None else state['selection'].observation
        report['interpreter_query_custody']=None if state['selection'] is None else state['selection'].snapshot()
        if state['interpreter_retirement'] is None or state['interpreter_retirement']['physical_interpreter_exit'] is not True:
            report['supervisor_custody_proven']=False
        save_new(p['terminal'],report)
    return execute_custody(custody,launch,emit,read_child,terminal,timeout=request['timeout_seconds'])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--request',type=Path,required=True)
    parser.add_argument('--sha256',required=True);args=parser.parse_args()
    try:
        request_ref=dict(repository_relative_path=args.request.relative_to(F).as_posix(),sha256=args.sha256)
        result=supervise(request_ref);print(json.dumps(result,allow_nan=False))
        return 0 if succeeded(result) else 1
    except BaseException as error:
        print(json.dumps(dict(outcome='REFUSED_OR_FAILED',original_error=error_record(error),
            native_qualification=False,product_acceptance=False)),file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
