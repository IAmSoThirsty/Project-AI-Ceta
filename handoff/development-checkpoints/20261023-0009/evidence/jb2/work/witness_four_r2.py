"""Fresh controlled four-case witness; original rejected-JB1 witness is read-only."""
from pathlib import Path
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch
import ctypes,hashlib,importlib,importlib.abc,importlib.util,json,os,socket,subprocess,sys
F=Path('T:/00-Active/Project-AI-CETA');W=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path[:0]=[str(W/'candidate/tests/contract'),str(F/'tests/contract'),str(F/'src'),str(W)]
modules={name:W/'candidate/src'/Path(*name.split('.')).with_suffix('.py') for name in (
    'ceta.identity.windows_pipe','ceta.composition.real_effect_service','ceta.identity.native_approval','ceta.effects.native_observer','ceta.identity.owner_session')}
assert len(modules)==5 and all(p.is_file() for p in modules.values())
class Finder(importlib.abc.MetaPathFinder):
    def find_spec(self,name,path=None,target=None):
        if name in modules:return importlib.util.spec_from_file_location(name,modules[name])
sys.meta_path.insert(0,Finder())
def audit(event,args):
    if event in ('subprocess.Popen','os.system','os.startfile','socket.__new__','ctypes.dlopen'):raise AssertionError('Forbidden effect: '+event)
    if event=='open':
        path,mode,flags=args
        writes=(isinstance(mode,str) and any(ch in mode for ch in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        if writes and not isinstance(path,int) and not Path(path).resolve().is_relative_to(W):raise AssertionError('Out of scope write')
sys.addaudithook(audit)
def deny(*a,**kw):raise AssertionError('Native/process/socket entry forbidden')
barriers=[patch(name,side_effect=deny) for name in ('ctypes.WinDLL','ctypes.CDLL','subprocess.Popen','subprocess.run','socket.socket')]
for p in barriers:p.start()
from ceta.identity import native_approval as na
from ceta.contracts.temporal import ClockSample
import test_native_owner_approval as data
class Clock:
    def __init__(self):self.origin=900_000_000_000_000;self.elapsed=0
    def perf_counter_ns(self):return self.origin+self.elapsed
    def get_clock_info(self,name):return SimpleNamespace(resolution=1e-9)
    def advance(self,ns):self.elapsed+=ns
rows=[]
for label,before,during,poll_first,refuse in [('valid_control',5_000_000,0,False,False),
    ('expired_before_direct_transcript',25_000_000,0,False,True),
    ('expiry_inside_transcript_currentness',10_000_000,20_000_000,False,True),
    ('expired_cached_poll_control',25_000_000,0,True,True)]:
    clock=Clock();checks=[];context=object()
    def pair():
        anchor=ClockSample('boot:fixture',1,0,data.MONO,data.WALL,0,True)
        return anchor,replace(anchor,monotonic_ns=data.MONO+clock.elapsed,wall_time_ns=data.WALL+clock.elapsed)
    owner=SimpleNamespace(helper_source_commitment=data.HASH,_clock=pair)
    with patch.object(na,'time',clock):
        wire,frozen=na._frame('inspect','challenge:one',b'\x01'*32,data.request(),20)
        s=na.NativeApprovalSession(owner,'interactive',frozen,context,20,wire)
        s._launching=False;s.process=SimpleNamespace(poll=lambda:None);s.helper_evidence=data.evidence()
        s.native_facts['interop_library']=dict(sha256='a'*64)
        def current(*args):checks.append(args);clock.advance(during)
        s._current=current
        s._result=replace(data.parse(data.response()),mode='interactive',status='VERIFIED',authentication_invoked=True,
            hardware_click=True,display_exact=True,native_hresult=0,native_result=0,effective_cancelled=False)
        assert s._result.reported_verified;original=s._deadline_at;clock.advance(before)
        if poll_first:assert s.poll().effective_cancelled
        transcript=error=None
        try:transcript=s.transcript()
        except BaseException as exc:error=dict(type=type(exc).__name__,args=BaseException.__dict__['args'].__get__(exc))
        verified=transcript is not None and transcript.reported_outcome=='REPORTED_VERIFIED'
        row=dict(case=label,elapsed_before_ns=before,currentness_duration_ns=during,original_deadline_perf_ns=original,
            finished_perf_ns=clock.perf_counter_ns(),stop_set=s._stop.is_set(),native_currentness_calls=len(checks),
            returned_reported_verified=verified,error=error,expected_refusal=refuse,
            case_passed=(transcript is None and error is not None) if refuse else verified,
            original_deadline_unchanged=s._deadline_at==original,native_authentication_performed=False)
        rows.append(row);print(json.dumps(row))
report=dict(run_id='ceta-jb23-r2',cases=rows,selected=[r['case'] for r in rows],started=[r['case'] for r in rows],
    stopped=[r['case'] for r in rows],tests_run=4,failures=sum(not r['case_passed'] for r in rows),errors=0,skips=0,
    source_sha256=hashlib.sha256(modules['ceta.identity.native_approval'].read_bytes()).hexdigest(),
    candidate_origins={n:dict(path=str(Path(importlib.import_module(n).__file__).resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for n,p in modules.items()},
    original_rejected_witness_sha256='666804b69ff520a832c059c1bef24cfb2f7e1fc7908ccdaebfc82346a91f9610',
    pure_controls_only=True,native_execution=False,independent_approval=False,full_product_acceptance=False)
with (W/'TRANSCRIPT-BUDGET-WITNESS-R2.json').open('x',encoding='utf8') as stream:json.dump(report,stream,indent=2);stream.write('\n')
sys.exit(0 if report['failures']==0 else 1)
