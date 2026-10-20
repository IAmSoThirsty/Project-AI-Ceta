"""DATA_ONLY actual-tool controls and input freeze. Does not import/run the driver."""
from pathlib import Path
from datetime import datetime,timezone
import ast,copy,functools,hashlib,json,stat,types
F=Path('T:/00-Active/Project-AI-CETA');D=F/'.agents/runtime/js9-runtime-20261020/successor-r3'
Q=F/'.agents/js9-runtime-r5-20261020';O=Path(__file__).resolve().parent
TOOL=O/'observer_diagnostic.py';CASE='test_native_effect_observer.NativeEffectObserverTests.test_actual_overlong_native_pipe_output_is_rejected_and_retired'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(repository_relative_path=p.relative_to(F).as_posix(),sha256=sha(p))
def ordinary(p):
    s=p.lstat();assert not s.st_file_attributes&1024
    return dict(path=str(p),bytes=s.st_size,sha256=sha(p),native_identity=dict(bytes=s.st_size,mtime_ns=s.st_mtime_ns,mode=stat.S_IMODE(s.st_mode),device=s.st_dev,inode=s.st_ino,attributes=s.st_file_attributes))
def save(name,v):
    with (O/name).open('x',encoding='utf8') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
tree=ast.parse(TOOL.read_text(encoding='utf8'))
test_tree=ast.parse((Q/'tests/contract/test_native_effect_observer.py').read_text(encoding='utf8'))
testclass=next(n for n in test_tree.body if isinstance(n,ast.ClassDef) and n.name=='NativeEffectObserverTests')
method=next(n for n in testclass.body if isinstance(n,ast.FunctionDef) and n.name==CASE.split('.')[-1])
packet=json.loads((D/'PACKET.json').read_bytes());negative=F/'.agents/runtime/ob2-20261014/negative-reuse'
reuse=json.loads((negative/'REUSE.json').read_bytes());build_ref=reuse['original_build'];build=json.loads((F/build_ref['repository_relative_path']).read_bytes())
assert sha(F/build_ref['repository_relative_path'])==build_ref['sha256']
for name,row in reuse['images'].items():assert ordinary(Path(row['path']))==row
source=ordinary(Path(build['source']['path']));assert source==build['source']
manifest=dict(schema_version=1,at=datetime.now(timezone.utc).isoformat(),state='DORMANT_PENDING_ROOT_PERSONAL_REVIEW',
    author='/root/recovery_join_review20',tool_sha256=sha(TOOL),case=CASE,original_method_ast_sha256=hashlib.sha256(ast.dump(method,include_attributes=False).encode()).hexdigest(),
    packet=ref(D/'PACKET.json'),candidate_manifest=packet['candidate_manifest'],environment=packet['environment'],Source_before=packet['Source_before'],
    bounded_custody=ref(D/'bounded_custody.py'),worker=packet['fixture_dependencies']['worker'],observer=packet['fixture_dependencies']['observer'],
    negative_images=reuse['images'],negative_reuse=ref(negative/'REUSE.json'),negative_build=build_ref,negative_source=source,
    output_root=str(O/'run-once'),max_attempts=1,ordinary_processes_max=2,profiles=False,no_profile_grant_consumed=False,
    controlled_changes=['Original tests.ROOT fixture path selects new output descendants.',
        'Transparent wrappers around original exchange/launch/pipe methods record values and restore ctypes last error.',
        'No original case/request/deadline/method body or production source is changed.'],
    measurement_limits=['Added observations cost time. A repeat does not by itself prove the cause of the earlier timeout.'],
    authorization='Root will personally review and execute once after the main full run retires, under existing ordinary native-observer authority. This manifest issues no permission.')

# The following compile only the driver's exact nested wrappers with synthetic dependencies.
rows=[]
def check(name,value):assert value,name;rows.append(dict(name=name,passed=True))
child=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='child')
names={'capture','event','api_init','launch','exchange'}
nodes=[n for n in child.body if isinstance(n,ast.FunctionDef) and n.name in names]
assert {n.name for n in nodes}==names
class FakeC:
    def __init__(self):self.error=17
    def get_last_error(self):return self.error
    def set_last_error(self,v):self.error=v
    def cast(self,v,t):return types.SimpleNamespace(contents=types.SimpleNamespace(value=v))
    def POINTER(self,t):return object
fake=FakeC()
def tick():fake.error=999;return 1000
env=dict(C=fake,time=types.SimpleNamespace(monotonic_ns=tick),copy=copy,functools=functools,
    native=types.SimpleNamespace(DWORD=object),Path=Path,m=manifest,
    notes=[],capture_errors=[],capture_failed=[False],exchanges=[],launches=[],owners=[],original_errors=[])
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(TOOL),'exec'),env)
def api_original(api):
    for name in ('PeekNamedPipe','ReadFile','WriteFile'):
        def call(*a,**kw):fake.error=42;return 1
        call.argtypes=['synthetic'];call.restype='synthetic';setattr(api,name,call)
env['original_api_init']=api_original
api=types.SimpleNamespace();env['api_init'](api)
for name,args,key in [('PeekNamedPipe',(1,None,0,None,289,None),'available'),('ReadFile',(1,None,10,10,None),'transferred'),('WriteFile',(1,None,240,240,None),'transferred')]:
    fake.error=17;got=getattr(api,name)(*args)
    check('original_pipe_return_and_error:'+name,got==1 and fake.error==42)
    check('actual_postcall_output_captured:'+name,env['notes'][-1][key]==(289 if name=='PeekNamedPipe' else args[2]))
    check('pipe_C_function_signature_preserved:'+name,getattr(api,name).argtypes==['synthetic'] and getattr(api,name).restype=='synthetic')
class RefuseAppend(list):
    def append(self,v):raise RuntimeError('CONTROLLED_DIAGNOSTIC_APPEND_FAILURE')
token=object()
def exchange_success(*a):fake.error=57;return token
env['original_exchange']=exchange_success;custody=types.SimpleNamespace(transport_state=dict(poll_count=0,stdout_available=0))
fake.error=17;got=env['exchange'](object(),custody,b'x',None,777)
check('exchange_return_identity_and_last_error',got is token and fake.error==57)
check('deadline_forwarded_without_change',env['exchanges'][-1]['deadline_ns']==777)
custody.transport_state['poll_count']=9
check('pre_cleanup_state_is_detached_snapshot',env['exchanges'][-1]['pre_cleanup_transport_state']['poll_count']==0)
primary=KeyboardInterrupt('CONTROLLED_ORIGINAL_EXCHANGE')
def exchange_failure(*a):fake.error=87;raise primary
env['original_exchange']=exchange_failure;env['original_errors']=RefuseAppend()
try:env['exchange'](object(),custody,b'x',None,777)
except BaseException as error:exact=error is primary
check('broken_error_diagnostic_keeps_original_exception_and_error',exact and fake.error==87 and env['capture_failed'][0] is True)
owner=types.SimpleNamespace(pid=123,creation_time=456)
calls=[]
def launch_original(*a,**kw):calls.append(1);fake.error=58;return owner
env.update(original_launch=launch_original,launches=[],owners=[],capture_failed=[False])
fake.error=17
got=env['launch'](object(),manifest['worker']['path'],('hold','30000'),expected_image_sha256=manifest['worker']['sha256'])
check('returned_owner_identity_and_error_preserved',got is owner and fake.error==58)
check('returned_owner_has_pre_reserved_observation_custody',env['owners']==[owner])
try:env['launch'](object(),manifest['worker']['path'],('hold','30000'),expected_image_sha256=manifest['worker']['sha256'])
except AssertionError:second_denied=True
else:second_denied=False
check('second_same_image_launch_denied_before_dispatch',second_denied and len(calls)==1)
env.update(launches=[],owners=RefuseAppend(),capture_failed=[False]);count=len(calls)
try:env['launch'](object(),manifest['worker']['path'],('hold','30000'),expected_image_sha256=manifest['worker']['sha256'])
except RuntimeError:reserve_denied=True
else:reserve_denied=False
check('reservation_failure_precedes_native_launch',reserve_denied and len(calls)==count and env['capture_failed'][0] is True)
check('tool_syntax_complete',bool(tree.body))
save('MANIFEST.json',manifest)
save('PURE-CONTROLS.json',dict(mode='DATA_ONLY_EXACT_WRAPPER_AST_WITH_SYNTHETIC_DISPATCH',passed=len(rows),failed=0,controls=rows,
    tool_sha256=sha(TOOL),wrapper_ASTs={n.name:hashlib.sha256(ast.dump(n,include_attributes=False).encode()).hexdigest() for n in nodes},
    no_driver_import=True,no_product_test_native_API_or_child_execution=True))
save('PREPARATION.json',dict(at=datetime.now(timezone.utc).isoformat(),manifest=ref(O/'MANIFEST.json'),tool=ref(TOOL),controls=ref(O/'PURE-CONTROLS.json'),
    command=[str(F/'.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'),'-B','-X','utf8',str(TOOL),'parent','--manifest-sha256',sha(O/'MANIFEST.json'),'--execute-once'],
    command_executed=False,Root_review_required=True,Source_publication=False,profile_operations=False))
print(json.dumps(dict(manifest=ref(O/'MANIFEST.json'),tool=ref(TOOL),controls=ref(O/'PURE-CONTROLS.json'),pure_passed=len(rows),command_executed=False)))
