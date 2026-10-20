from pathlib import Path
import json,os,subprocess,sys,threading,unittest
P=Path('T:/00-Active/Project-AI-CETA');Q=P/'.agents/cb1-20261014';BASE=P/'.agents/runtime/cb1-20261014';D=BASE/'independent-review';RUN='cb1-20261014'
sys.path.insert(0,str(P/'.agents/runtime/ka1-20261014'));import ka1_support as s
s.Q=Q;s.R=D;s.RUN=RUN
assert s.sha(Q/'TRANSFER-MANIFEST.json')=='0ab0a0762dbc840792a229ec2e9c5ee5b5107d36d4f18841845490a8fd3898e3'
assert s.sha(BASE/'implement.json')=='17c6aeae7edc2eb3e72af57bd590ede7c5ece38c7bb6896b215f6fd9f2f3e60b'
state=json.loads((BASE/RUN/'state.json').read_text());assert state['nodes']['implement']['state']=='SUCCEEDED' and state['nodes']['review']['state']=='READY'
cmd=['powershell','-NoProfile','-File','T:/02-Config/agents/taar-orchestrate.ps1','node','claim',RUN,'review','--executor',s.ACTOR,'--workspace',str(Q),'--runtime-root',str(BASE)]
r=subprocess.run(cmd,cwd='T:/00-Active',capture_output=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
(D/'review-claim.stdout.txt').write_bytes(r.stdout);(D/'review-claim.stderr.txt').write_bytes(r.stderr)
response=json.loads(r.stdout.decode('utf-8-sig'));s.write_new(D/'review-claim.json',dict(recorded_at=s.utc(),command_argv=cmd,exit_status=r.returncode,response=response));assert r.returncode==0 and response['allowed']
manifest=json.loads((Q/'TRANSFER-MANIFEST.json').read_text());inputs=json.loads((BASE/'SOURCE-INPUTS.json').read_text())
before={row['relative_path']:s.ordinary(Q/row['relative_path']) for row in manifest['payloads']}
assert len(before)==294 and all(before[row['relative_path']]['sha256']==row['candidate_sha256'] and before[row['relative_path']]['native_identity']==row['candidate_native_identity'] for row in manifest['payloads'])
source={name:s.ordinary(P/name) for name in inputs['Source290']};assert source==inputs['Source290']
E=D/'cohort-r1';E.mkdir(exist_ok=False);os.environ['TEMP']=os.environ['TMP']=str(E)
sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
import test_native_code_binding as tests
from ceta.identity import native_code_binding as binding
tests.ROOT=E
owners=[];original=binding.NativeCodeBinding.__init__
def observed(self,*args,**kwargs):
 try:original(self,*args,**kwargs)
 finally:
  if hasattr(self,'_api'):owners.append(self)
binding.NativeCodeBinding.__init__=observed
suite=unittest.defaultTestLoader.loadTestsFromModule(tests)
def ids(group):
 for item in group:
  if isinstance(item,unittest.TestSuite):yield from ids(item)
  else:yield item.id()
expected=list(ids(suite));assert len(set(expected))==len(expected)==16
executed=[];stopped=[]
class Result(unittest.TextTestResult):
 def startTest(self,test):executed.append(test.id());super().startTest(test)
 def stopTest(self,test):stopped.append(test.id());super().stopTest(test)
threads=set(threading.enumerate())
with (E/'tests.txt').open('x',encoding='utf-8') as out:result=unittest.TextTestRunner(stream=out,verbosity=2,resultclass=Result).run(suite)
remaining=[t.name for t in set(threading.enumerate())-threads if t.is_alive()]
imports={name:str(Path(module.__file__).resolve()) for name,module in sys.modules.items() if name=='ceta' or name.startswith('ceta.') if getattr(module,'__file__',None)}
assert all(Path(path).is_relative_to(Q/'src') for path in imports.values())
owned=[dict(closed=o.closed,pending=o.pending_native_resources,file_count=len(o._files),ancestor_count=len(o._ancestors)) for o in owners]
assert all(s.ordinary(Q/name)==row for name,row in before.items());assert all(s.ordinary(P/name)==row for name,row in source.items())
s.write_new(D/'COHORT.json',dict(recorded_at=s.utc(),tests_run=result.testsRun,expected_ids=expected,executed_ids=executed,stopped_ids=stopped,
 failures=[(t.id(),tb) for t,tb in result.failures],errors=[(t.id(),tb) for t,tb in result.errors],skips=result.skipped,
 raw=s.reference(E/'tests.txt'),native_receipts=tests.NATIVE_RECEIPTS,owners=owned,remaining_threads=remaining,imports=imports,
 candidate_before=before,source_before=source,fixture_scope=str(E),source_application=False))
assert result.wasSuccessful() and not result.skipped and expected==executed==stopped and not remaining
assert all(row['closed'] and not row['pending'] for row in owned)
print(json.dumps(dict(tests=16,failures=0,errors=0,skips=0,owners=len(owners),remaining_threads=remaining,cohort_sha256=s.sha(D/'COHORT.json'))),flush=True)
