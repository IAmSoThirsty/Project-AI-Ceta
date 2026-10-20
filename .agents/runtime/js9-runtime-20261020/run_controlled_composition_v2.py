"""One explicitly requested controlled composition attempt; no native release."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,contextlib,hashlib,json,os,sys,threading,traceback,unittest
from unittest.mock import patch
from scope_guard_v2 import sqlite_contained
F=Path('T:/00-Active/Project-AI-CETA');R=Path(__file__).resolve().parent;Q=F/'.agents/js9-runtime-20261020'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now(timezone.utc).isoformat()
def save(p,v):
 with p.open('x',encoding='utf8') as s:json.dump(v,s,indent=2);s.write('\n')
p=argparse.ArgumentParser();p.add_argument('--attempt',required=True);p.add_argument('--manifest',required=True);p.add_argument('--cases',required=True);a=p.parse_args()
assert a.attempt.isidentifier()
manifest_path=R/a.manifest;case_path=R/a.cases
assert manifest_path.resolve().is_relative_to(R) and case_path.resolve().is_relative_to(R)
m=json.loads(manifest_path.read_bytes());cases=json.loads(case_path.read_bytes())['test_ids']
assert sha(R/'scope_guard_v2.py')=='f90db473ae1abb2bea8762c8e8562f44b4df12149b0e08803025fa33d310df13'
base=json.loads((F/'.agents/runtime/js8-20261015/amendment-report1/ACCEPTED-SOURCE-BASELINE.json').read_bytes())['effective_payload_hashes']
assert all(sha(Q/n)==pin for n,pin in m['payload_hashes'].items())
assert all(sha(F/n)==pin for n,pin in base.items())
O=R/a.attempt;O.mkdir(exist_ok=False);fixture=O/'fixtures';fixture.mkdir()
command=list(sys.orig_argv);start=now()
interpreter=dict(executable=sys.executable,base_executable=sys._base_executable,prefix=sys.prefix,base_prefix=sys.base_prefix,orig_argv=list(sys.orig_argv))
save(O/'COMMAND.json',dict(at=start,command=command,interpreter=interpreter,cwd=str(F),pid=os.getpid(),manifest_sha256=sha(manifest_path),cases_sha256=sha(case_path),runner_sha256=sha(Path(__file__)),native_execution_released=False))
violations=[];native=[];sql=[];events=[];journals=[]
def contained(value):
 return isinstance(value,int) or Path(os.fsdecode(value)).resolve().is_relative_to(O)
def audit(event,args):
 bad=False
 if event=='open':
  path,mode,flags=args
  if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):bad=not contained(path)
 elif event in ('os.mkdir','os.remove','os.rmdir','os.chmod','os.utime','os.truncate'):bad=not contained(args[0])
 elif event in ('os.rename','os.link','os.symlink'):bad=not contained(args[0]) or not contained(args[1])
 elif event.startswith('socket.') or event in ('subprocess.Popen','os.system','os.posix_spawn','os.spawn'):bad=True
 elif event=='sqlite3.connect':
  sql.append(str(args[0]));bad=not sqlite_contained(args[0],O)
 if bad:
  violations.append(dict(event=event,args=repr(args)));raise RuntimeError('JS9_CONTROLLED_BOUNDARY_VIOLATION')
sys.addaudithook(audit);os.environ['CETA_JS9_FIXTURE_ROOT']=str(fixture)
sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
def deny(*args,**kwargs):
 native.append('Denied native execution boundary');raise RuntimeError('JS9_NATIVE_EXECUTION_NOT_RELEASED')
import ceta.identity.native_clock as clock_module
import ceta.identity.native_owner_view as view_module
from ceta.identity.native_approval import NativeApprovalOwner
from ceta.identity.windows_pipe import WindowsPeerRegistry,WindowsPipeServer
from ceta.supervisor.windows_jobs import WindowsOwnedProcess
from ceta.store.outcome_capacity import OutcomeCapacityRuntime
from ceta.store.journal import SqliteJournal
import ceta.identity.native_cpu_outcome as producer_module
import ceta.kernel.cpu_execution as execution_module
original_init=SqliteJournal.__init__
def journal_init(owner,*args,**kwargs):
 journals.append(owner);return original_init(owner,*args,**kwargs)
threads_before={(t.ident,t.name,t.daemon) for t in threading.enumerate()}
exception=None;result=None
with (O/'stdout.txt').open('x',encoding='utf8') as stdout,(O/'stderr.txt').open('x',encoding='utf8') as stderr,contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr),contextlib.ExitStack() as stack:
 for owner,name,value in [(clock_module._NativeClockAPI,'__init__',deny),(view_module._ViewAPI,'__init__',deny),(WindowsPeerRegistry,'__init__',deny),(WindowsPipeServer,'__init__',deny),(NativeApprovalOwner,'_start_session',deny),(WindowsOwnedProcess,'launch',staticmethod(deny)),(OutcomeCapacityRuntime,'__init__',deny),(producer_module,'_OBSERVE',deny),(execution_module,'_APPLY',deny),(execution_module,'_RESTORE',deny),(SqliteJournal,'__init__',journal_init)]:stack.enter_context(patch.object(owner,name,value))
 try:
  import test_native_runtime_composition as tests
  suite=unittest.defaultTestLoader.loadTestsFromTestCase(tests.NativeRuntimeCompositionTests)
  actual=sorted(t.id() for t in suite)
  assert actual==sorted(cases),(actual,cases)
  class Result(unittest.TextTestResult):
   def startTest(self,test):events.append(dict(event='START',test_id=test.id(),at=now()));super().startTest(test)
   def stopTest(self,test):events.append(dict(event='STOP',test_id=test.id(),at=now()));super().stopTest(test)
  result=unittest.TextTestRunner(stream=stderr,verbosity=2,resultclass=Result).run(suite)
 except BaseException as error:
  exception=dict(type=type(error).__name__,text=str(error));traceback.print_exc()
threads_after={(t.ident,t.name,t.daemon) for t in threading.enumerate()}
unchanged=all(sha(Q/n)==pin for n,pin in m['payload_hashes'].items())
source_unchanged=all(sha(F/n)==pin for n,pin in base.items())
closed=all(getattr(j,'_closed',False) and getattr(j,'_connection_close_state',None)=='CLOSED' for j in journals)
rows=[] if result is None else [dict(test_id=t.id(),traceback=tb) for t,tb in result.errors+result.failures]
value=dict(started_at=start,finished_at=now(),pid=os.getpid(),command=command,interpreter=interpreter,manifest_sha256=sha(manifest_path),case_sha256=sha(case_path),runner_sha256=sha(Path(__file__)),tests_run=0 if result is None else result.testsRun,failures=rows,skipped=[] if result is None else [(t.id(),reason) for t,reason in result.skipped],unexpected_successes=0 if result is None else len(result.unexpectedSuccesses),exception=exception,events=events,sqlite_connect_uris=sql,journals_created=len(journals),all_journals_closed=closed,threads_before=sorted(threads_before),threads_after=sorted(threads_after),residual_threads=sorted(threads_after-threads_before),boundary_violations=violations,native_boundary_attempts=native,candidate_unchanged=unchanged,Source352_unchanged=source_unchanged,fixture_facts=[] if 'tests' not in locals() else tests.FACTS,native_execution=False,scope='Controlled composition; real SQLite, controlled native origins')
value['passed']=bool(result is not None and result.wasSuccessful() and result.testsRun==len(cases) and not result.skipped and not result.unexpectedSuccesses and exception is None and closed and unchanged and source_unchanged and threads_before==threads_after and not native and not violations)
save(O/'RESULT.json',value)
print(json.dumps({k:value[k] for k in ['passed','tests_run','journals_created','all_journals_closed','candidate_unchanged','Source352_unchanged','exception','residual_threads','boundary_violations','native_boundary_attempts']}),flush=True)
raise SystemExit(0 if value['passed'] else 1)
