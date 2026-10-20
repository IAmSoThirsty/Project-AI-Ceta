"""Stream custody outside critical transitions, then run the unchanged finite suite."""
from pathlib import Path
import functools, json, os, sys, threading, unittest
D=Path(__file__).resolve().parent;R=D.parent;F=R.parents[2];Q=F/'.agents/cpb1-20261014'
sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract'),str(F/'.agents/runtime/en1-20261014')]
import en1_support as s
s.Q=Q;s.R=D
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
prep=read(D/'PREPARATION.json');execution=read(D/'EXECUTION-PREPARATION.json')
assert all(s.ordinary(Q/n)==row for n,row in prep['candidate326'].items())
assert all(s.ordinary(F/n)==row for n,row in prep['Source290'].items())
import test_windows_jobs as jobs
assert jobs.ROOT==Q
jobs.ROOT=D/'fixture-root'
import test_native_cpu_binding as tests
from ceta.supervisor.windows_jobs import WindowsOwnedProcess,_API
from ceta.identity.native_clock import NativeSessionClock
for name,module in list(sys.modules.items()):
    if name=='ceta' or name.startswith('ceta.'):
        if getattr(module,'__file__',None):assert Path(module.__file__).is_relative_to(Q/'src')
test_id=None;owners=[];clocks=[];APIs=[];errors=[];native_stream=[];process_stream=[];clock_stream=[];case_stream=[]
def stream(name,row):
    with (D/name).open('a',encoding='utf-8',newline='\n') as out:
        out.write(json.dumps(row,sort_keys=True,allow_nan=False)+'\n');out.flush();os.fsync(out.fileno())
class Receipts(list):
    def append(self,row):
        super().append(row);native_stream.append(row);stream('native-receipts.jsonl',row)
assert tests.NATIVE_RECEIPTS==[];tests.NATIVE_RECEIPTS=Receipts()
old_process=WindowsOwnedProcess.__init__
@functools.wraps(old_process)
def process_init(owner,*args,**kwargs):
    try:return old_process(owner,*args,**kwargs)
    finally:
        if hasattr(owner,'_pid'):
            owners.append(owner);row=dict(test_id=test_id,pid=owner._pid,creation_time=owner._creation_time,image_sha256=owner._image_sha256,job_digest=owner._cpu_job_digest)
            process_stream.append(row);stream('native-worker-identities.jsonl',row)
WindowsOwnedProcess.__init__=process_init
old_clock=NativeSessionClock.__init__
@functools.wraps(old_clock)
def clock_init(owner,*args,**kwargs):
    try:return old_clock(owner,*args,**kwargs)
    finally:
        if hasattr(owner,'_condition'):
            clocks.append(owner);row=dict(test_id=test_id,session=owner._session,state=owner._state,epoch=owner._epoch,registration=repr(owner._registration),backend_type=None if not hasattr(owner,'_api') else type(owner._api).__name__)
            clock_stream.append(row);stream('clock-owner-identities.jsonl',row)
NativeSessionClock.__init__=clock_init
old_api=_API.__init__
@functools.wraps(old_api)
def api_init(api,*args,**kwargs):
    old_api(api,*args,**kwargs);record=dict(test_id=test_id,closed_handles=[]);APIs.append(record);closer=api.close
    def close(handle):
        observed_handle=None if handle is None else int(handle)
        try:value=closer(handle)
        except BaseException as failure:
            record['closed_handles'].append(dict(handle=observed_handle,outcome='raised',exception=type(failure).__name__));raise
        record['closed_handles'].append(dict(handle=observed_handle,outcome='returned'));return value
    api.close=close
_API.__init__=api_init
old_start=unittest.TextTestResult.startTest;old_stop=unittest.TextTestResult.stopTest
def start(self,test):
    global test_id
    test_id=test.id();return old_start(self,test)
def stop(self,test):
    try:
        row=dict(test_id=test.id(),workers=[dict(pid=o._pid,creation_time=o._creation_time,closed=o._closed,process_closed=o._process is None,job_closed=o._job is None,thread_closed=o._thread is None) for o in owners],
            clocks=[dict(session=o._session,state=o._state,registration_owned=o._registration is not None,callbacks=o._callbacks,sampler_alive=bool(o._thread and o._thread.is_alive()),backend_type=None if not hasattr(o,'_api') else type(o._api).__name__) for o in clocks])
        case_stream.append(row);stream('per-case-custody.jsonl',row)
    except BaseException as failure:
        errors.append(dict(test_id=test.id(),exception=type(failure).__name__,message=str(failure)))
    return old_stop(self,test)
unittest.TextTestResult.startTest=start;unittest.TextTestResult.stopTest=stop
raw=(D/'run_tests.py').read_text();assert s.ordinary(D/'run_tests.py')==execution['prepared']['run_tests.py']['relocated']
original_argv=sys.argv[:];sys.argv=[str(D/'run_tests.py'),'connected-independent-r1','connected'];exit_status=None
try:exec(compile(raw,str(D/'run_tests.py'),'exec'),{'__name__':'__main__','__file__':str(D/'run_tests.py')})
except SystemExit as outcome:exit_status=outcome.code
finally:sys.argv=original_argv
assert exit_status is not None,'Runner did not exit normally'
result=read(D/'connected-independent-r1.json')
assert result['expected_ids']==result['executed_ids']==result['stopped_ids']==prep['expected_ids']
assert result['native_receipts']==native_stream and len(native_stream)==6
assert len(process_stream)==8 and len(owners)==8
assert len(clocks)==67 and len([o for o in clocks if hasattr(o,'_api') and type(o._api).__name__=='_NativeClockAPI'])==13
assert len(case_stream)==163 and not errors
assert all(s.ordinary(Q/n)==row for n,row in prep['candidate326'].items())
assert all(s.ordinary(F/n)==row for n,row in prep['Source290'].items())
proof=dict(at=s.utc(),native_worker_identities=process_stream,clock_creation_records=clock_stream,native_receipts_stream= s.reference(D/'native-receipts.jsonl'),per_case_stream=s.reference(D/'per-case-custody.jsonl'),
    workers_closed=all(o._closed and o._process is None and o._job is None and o._thread is None for o in owners),
    clocks_closed=all((o._state=='CLOSED' or not hasattr(o,'_api')) and o._registration is None and not (o._thread and o._thread.is_alive()) and o._callbacks==0 for o in clocks),
    close_calls=APIs,recorder_errors=errors,fixture_scope=str(jobs.ROOT),candidate326_native_exact=True,Source290_native_exact=True,runner_exit_status=exit_status,method_ASTs_unchanged=True,
    CPB1_native_epoch='Controlled1 with actual Windows read-only clock registrations; no canonical authority',Source_application=False)
s.write_new(D/'OBSERVED-EXECUTION.json',proof)
print(json.dumps(dict(tests=163,workers=len(owners),native_clocks=13,total_clock_constructor_records=len(clocks),native_receipts=len(native_stream),exit_status=exit_status)),flush=True)
sys.exit(exit_status)
