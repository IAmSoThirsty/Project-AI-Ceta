"""Existing bounded ID discovery; forbid native work, tests and new threads."""
from pathlib import Path
from unittest.mock import patch
import ast,ctypes,importlib,json,os,subprocess,sys,threading,unittest
from foundation_support import *
import js8_support as j

label,=sys.argv[1:];assert label.replace('-','').isalnum()
v=read(R/'INPUTS.json');names=read(R/'ASSEMBLY.json')['payloads']
before={name:ordinary(Q/name) for name in names};assert len(before)==352
sys.path[:0]=[str(Q/'src'),str(Q/'tools'),str(Q/'tests/contract')]
os.environ['QT_QPA_PLATFORM']='offscreen';blocked=[];threads=set(threading.enumerate())
operations={'CreateProcessW','CreateProcessA','CreateProcessAsUserW','CreateProcessWithTokenW','CreateAppContainerProfile',
 'DeleteAppContainerProfile','CreateJobObjectW','CreateThread','CreateRemoteThread','CreatePipe','CreateNamedPipeW','CreateEventW',
 'SetInformationJobObject','TerminateProcess','TerminateJobObject','SetEvent','PowerRegisterSuspendResumeNotification',
 'SetSystemTime','SetLocalTime','NtSetSystemTime'}
real_dll=ctypes.WinDLL
class GuardedDLL:
 def __init__(self,library):self.library=library
 def __getattr__(self,name):
  if name in operations:
   def deny(*a,**k):blocked.append('NATIVE:'+name);raise AssertionError('DISCOVERY_NATIVE_ALLOCATION_FORBIDDEN:'+name)
   return deny
  return getattr(self.library,name)
def dll(*a,**k):return GuardedDLL(real_dll(*a,**k))
def forbidden(kind):
 def deny(*a,**k):blocked.append(kind);raise AssertionError('DISCOVERY_FORBIDDEN:'+kind)
 return deny

modules=[];expected=[];primary=None;sqlite_identity=None;cases=None
try:
 with patch.object(ctypes,'WinDLL',dll),patch.object(subprocess,'Popen',forbidden('PROCESS')), \
      patch.object(threading.Thread,'start',forbidden('THREAD')),patch.object(unittest.TestCase,'run',forbidden('TEST_BODY')):
  from ceta.store.sqlite_runtime import load_sqlite,runtime_identity
  load_sqlite();sqlite_identity=runtime_identity()
  for path in sorted((Q/'src/ceta').rglob('*.py')):
   parts=list(path.relative_to(Q/'src').with_suffix('').parts)
   if parts[-1]=='__init__':parts.pop()
   module=importlib.import_module('.'.join(parts));assert Path(module.__file__).resolve()==path;modules.append(ordinary(path))
  assert len(modules)==88
  loader=unittest.TestLoader();suite=loader.discover(str(Q/'tests/contract'),pattern='test_*.py')
  expected=list(j.ids(suite));assert not loader.errors and not any('_FailedTest' in name for name in expected)
  assert len(expected)==len(set(expected))
  parent=read(F/'.agents/runtime/js7-20261015/APPROVED-CASESET.json')
  parent_ids=parent['expected_ids'];assert len(parent_ids)==1556
  assert [name for name in expected if name in set(parent_ids)]==parent_ids
  grouped={}
  for name in expected:grouped.setdefault(name.split('.')[0],[]).append(name)
  new=[name for name in expected if name not in set(parent_ids)]
  parent1479=parent['parent1479_ids'];assert len(parent1479)==1479
  methods={}
  for name in names:
   if name.startswith('tests/') and name.endswith('.py'):
    for node in ast.walk(ast.parse((Q/name).read_bytes())):
     if isinstance(node,ast.ClassDef):
      for method in node.body:
       if isinstance(method,ast.FunctionDef) and method.name.startswith('test_'):
        methods[name+'::'+node.name+'.'+method.name]=digest(ast.dump(method,include_attributes=False).encode())
  parent_methods={}
  parent_payloads=read(F/'.agents/js7-20261015/TRANSFER-MANIFEST.json')['payloads']
  for name in parent_payloads:
   if name.startswith('tests/') and name.endswith('.py'):
    for node in ast.walk(ast.parse((F/'.agents/js7-20261015'/name).read_bytes())):
     if isinstance(node,ast.ClassDef):
      for method in node.body:
       if isinstance(method,ast.FunctionDef) and method.name.startswith('test_'):
        key=name+'::'+node.name+'.'+method.name
        parent_methods[key]=digest(ast.dump(method,include_attributes=False).encode())
  assert all(methods[name]==pin for name,pin in parent_methods.items())
  cases=dict(schema_version=1,at=utc(),expected_count=len(expected),expected_ids=expected,
   parent1479_ids=parent1479,parent1556_ids=parent_ids,added_ids=new,
   added_module_counts={name:len(group) for name,group in grouped.items() if any(x in new for x in group)},
   all_module_counts={name:len(group) for name,group in grouped.items()},
   test_payload_hashes={name:before[name]['sha256'] for name in names if name.startswith('tests/')},
   method_ast_sha256=methods,parent_method_ast_sha256=parent_methods,
   parent_method_ASTs_exact=True,original_seven_status='Root separately qualified exact source subject; full execution still pending',
   original_restricted_case='Included unchanged; separately reviewed fresh Root gate required for full execution',
   parent_cases=reference(F/'.agents/runtime/js7-20261015/APPROVED-CASESET.json'))
 assert not blocked
 assert {name:ordinary(Q/name) for name in names}==before
 assert not [t for t in set(threading.enumerate())-threads if t.is_alive()]
except BaseException as error:primary=error
record=dict(at=utc(),classification='IMPORT_AND_TEST_ID_DISCOVERY_ONLY',expected_ids=expected,tests_discovered=len(expected),
 product_modules=modules,test_bodies_executed=0,blocked_calls=blocked,native_workers_allocated=0,
 sqlite_runtime=sqlite_identity,Source_publication=False,full_validation=False,
 primary_error=None if primary is None else dict(type=type(primary).__name__,message=str(primary)),
 exit_status=0 if primary is None else 1)
write_new(R/(label+'.json'),record)
if primary is None:write_new(R/'APPROVED-CASESET.json',cases)
print(canonical(dict(tests_discovered=len(expected),modules=len(modules),blocked=blocked,exit_status=record['exit_status'])))
if primary is not None:raise primary
