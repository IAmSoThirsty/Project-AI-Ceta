"""Bounded controlled successor qualification, with native process/profile APIs forbidden."""
from pathlib import Path
import ctypes
import importlib.abc
import json
import os
import stat
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

F=Path('T:/00-Active/Project-AI-CETA');R=Path(__file__).resolve().parent;Q=R/'candidate'
sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
sys.path.insert(0,str(F/'.agents/runtime/ka1-20261014'));import ka1_support as s
s.Q=Q;s.R=R;s.RUN='f4-full-gate-successor-20261015';s.ACTOR='/root/history_preservation'
label=sys.argv[1];assert label.replace('-','').isalnum();out=R/label;out.mkdir(exist_ok=False)
sys.path.insert(0,str(Q))
started=s.utc();inputs=json.loads((R/'INPUTS.json').read_text())
source_before={name:s.ordinary(F/name) for name in inputs['Source290']}
assert source_before==inputs['Source290']
parent_before={name:s.ordinary(row['path']) for name,row in inputs['parent_scripts'].items()}
assert parent_before==inputs['parent_scripts']
f4_manifest=F/'.agents/re-foundation4-20261015/TRANSFER-MANIFEST.json'
f4_data=json.loads(f4_manifest.read_text());f4_before={name:s.ordinary(F/'.agents/re-foundation4-20261015'/name) for name in f4_data['payloads']}
assert len(f4_before)==336 and all(v['sha256']==f4_data['payloads'][n]['candidate']['sha256'] for n,v in f4_before.items())
candidate_before={p.relative_to(Q).as_posix():s.ordinary(p) for p in Q.iterdir() if p.is_file()}
forbidden=[]
operations={'CreateProcessW','CreateProcessA','CreateProcessAsUserW','CreateProcessWithTokenW','CreateAppContainerProfile','DeleteAppContainerProfile',
 'SetInformationJobObject','SetSystemTime','SetLocalTime','NtSetSystemTime'}
real_win_dll=ctypes.WinDLL
class GuardedDLL:
 def __init__(self,library):self.library=library
 def __getattr__(self,name):
  if name in operations:
   def deny(*args,**kwargs):forbidden.append(name);raise AssertionError('FORBIDDEN_NATIVE_EFFECT:'+name)
   return deny
  return getattr(self.library,name)
def guarded_dll(*args,**kwargs):return GuardedDLL(real_win_dll(*args,**kwargs))
def denied_process(*args,**kwargs):forbidden.append('subprocess.Popen');raise AssertionError('NO_CHILD_IN_CONTROLLED_TESTS')
class CetaImportDenied(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname=='ceta' or fullname.startswith('ceta.'):
   forbidden.append('CETA_IMPORT:'+fullname);raise AssertionError('NO_CETA_NATIVE_IMPORT_IN_CONTROLLED_QUALIFICATION')
  return None
blocker=CetaImportDenied();sys.meta_path.insert(0,blocker)
import test_full_gate as tests
suite=unittest.defaultTestLoader.loadTestsFromTestCase(tests.GateTests)
expected=[test.id() for test in suite];executed=[];stopped=[]
class Result(unittest.TextTestResult):
 def startTest(self,test):executed.append(test.id());super().startTest(test)
 def stopTest(self,test):stopped.append(test.id());super().stopTest(test)
threads=set(threading.enumerate())
try:
 with patch.object(ctypes,'WinDLL',guarded_dll),patch.object(subprocess,'Popen',denied_process):
  with (out/'tests.txt').open('x',encoding='utf-8',buffering=1) as raw:
   result=unittest.TextTestRunner(stream=raw,verbosity=2,resultclass=Result).run(suite)
finally:
 sys.meta_path.remove(blocker)
candidate_after={name:s.ordinary(Q/name) for name in candidate_before}
source_after={name:s.ordinary(F/name) for name in source_before}
parent_after={name:s.ordinary(row['path']) for name,row in parent_before.items()}
f4_after={name:s.ordinary(F/'.agents/re-foundation4-20261015'/name) for name in f4_before}
remaining=[{'name':t.name,'native_id':t.native_id} for t in set(threading.enumerate())-threads if t.is_alive()]
passed=result.wasSuccessful() and not result.skipped and expected==executed==stopped and not forbidden and not remaining and candidate_before==candidate_after and source_before==source_after and parent_before==parent_after and f4_before==f4_after
proof={'started_at':started,'finished_at':s.utc(),'tests_run':result.testsRun,'expected_ids':expected,'executed_ids':executed,'stopped_ids':stopped,
 'failures':[{'id':test.id(),'traceback':tb} for test,tb in result.failures],
 'errors':[{'id':test.id(),'traceback':tb} for test,tb in result.errors],'skips':result.skipped,
 'candidate_before':candidate_before,'candidate_after':candidate_after,'Source290_before':source_before,'Source290_after':source_after,
 'F4_parent_scripts_before':parent_before,'F4_parent_scripts_after':parent_after,'F4_candidate336_before':f4_before,'F4_candidate336_after':f4_after,
 'forbidden_native_and_process_calls':forbidden,'remaining_threads':remaining,'CETA_product_imports':[],
 'raw':s.reference(out/'tests.txt'),'driver':s.reference(Path(__file__)),'exit_status':0 if passed else 1,
 'original_restricted_no_profile_case':'NOT_RUN','real_operator_authorization_created':False,'actual_CETA_native_or_Source_execution':False,
 'qualification':'Synthetic engineering records and controlled functions. Actual native ordinary-file capture/read-only sharing is tested only on fresh owned synthetic files. No profile/process/CPU/Hello effect.',
 'metadata109_issue_waived':False,'full_Source2053_executed':False}
s.write_new(out/'RESULT.json',proof)
print(json.dumps({'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),'forbidden_calls':len(forbidden),'exit_status':proof['exit_status']}))
sys.exit(proof['exit_status'])
