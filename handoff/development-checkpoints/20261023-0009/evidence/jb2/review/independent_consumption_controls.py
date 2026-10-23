"""Independent JB2 consumption controls; recorded ports, no native authority claim."""
from pathlib import Path
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch
import ctypes,hashlib,importlib,importlib.abc,importlib.util,json,os,socket,subprocess,sys,threading,unittest
F=Path('T:/00-Active/Project-AI-CETA');J=F/'.agents/runtime/oq23/jb2';W=J/'work';R=J/'review';C=W/'candidate'
sys.dont_write_bytecode=True
NAMES=('ceta.identity.windows_pipe','ceta.composition.real_effect_service','ceta.identity.native_approval','ceta.effects.native_observer','ceta.identity.owner_session')
MODULES={n:C/'src'/Path(*n.split('.')).with_suffix('.py') for n in NAMES}
class Finder(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname in MODULES:return importlib.util.spec_from_file_location(fullname,MODULES[fullname])
sys.meta_path.insert(0,Finder());sys.path[:0]=[str(F/'tests/contract'),str(F/'src')]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((W/'MANIFEST.json').read_bytes());assert sha(W/'MANIFEST.json')=='e9b0ac804a3bcebad266e400e6ce41a8fbb113749026230baf6e4ed59f93db72'
pins={str(W/rel):v['sha256'] for rel,v in m['files'].items()};pins.update(m['external_pins'])
assert all(sha(Path(p))==h for p,h in pins.items())
forbidden=[]
def deny(*a,**k):forbidden.append(dict(args=repr(a),kwargs=repr(k)));raise AssertionError('INDEPENDENT_PURE_CONTROL_FORBIDS_NATIVE_PROCESS_SOCKET')
def audit(event,args):
 if event in ('subprocess.Popen','os.system','os.startfile','socket.__new__','ctypes.dlopen'):forbidden.append({'event':event});raise AssertionError(event)
 if event=='open':
  p,mode,flags=args;write=(isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
  if write and not isinstance(p,int):assert Path(p).resolve().is_relative_to(R),('out_of_review_write',str(p))
sys.addaudithook(audit)
barriers=[patch(n,side_effect=deny) for n in ('ctypes.WinDLL','ctypes.CDLL','subprocess.Popen','subprocess.run','socket.socket')]
for b in barriers:b.start()
from ceta.identity import native_approval as ap,owner_session as own
from ceta.contracts.wire import ContractError
import ceta.contracts.real_effect as ec
import test_native_owner_approval as ad
import test_owner_authority_transactions as ed
for n in NAMES:importlib.import_module(n)
origins={n:dict(path=str(Path(sys.modules[n].__file__).resolve()),sha256=sha(MODULES[n])) for n in NAMES}
assert all(v['path']==str(MODULES[n].resolve()) for n,v in origins.items())
class Ticks:
 def __init__(self):self.origin=7_000_000_000_000_000;self.elapsed=0
 def perf_counter_ns(self):return self.origin+self.elapsed
 def get_clock_info(self,name):return SimpleNamespace(resolution=1e-9)
 def advance(self,ns):self.elapsed+=ns
class Hostile(KeyboardInterrupt):
 def __setattr__(self,name,value):raise RuntimeError('Refused exception attribute mutation')
 @property
 def add_note(self):raise OSError('Refused diagnostic getter')
def storage(e):return BaseException.__dict__['__dict__'].__get__(e)
class IndependentConsumptionTests(unittest.TestCase):
 def helper(self,before=4_000_000,during=0):
  clock=Ticks();p=patch.object(ap,'time',clock);p.start();self.addCleanup(p.stop)
  anchor=ad.ClockSample('boot:fixture',1,0,ad.MONO,ad.WALL,0,True)
  def pair():return anchor,replace(anchor,monotonic_ns=anchor.monotonic_ns+clock.elapsed,wall_time_ns=anchor.wall_time_ns+clock.elapsed)
  h=SimpleNamespace(helper_source_commitment=ad.HASH,_clock=pair)
  frame,req=ap._frame('inspect','challenge:one',bytes([1])*32,ad.request(),20)
  context=object();s=ap.NativeApprovalSession(h,'interactive',req,context,20,frame)
  s._launching=False;s.process=SimpleNamespace(poll=lambda:None);s.helper_evidence=ad.evidence();s.native_facts['interop_library']={'sha256':'a'*64}
  calls=[]
  def current(*a):calls.append(a);clock.advance(during)
  s._current=current;s._result=replace(ad.parse(ad.response()),mode='interactive',status='VERIFIED',authentication_invoked=True,hardware_click=True,display_exact=True,native_hresult=0,native_result=0,effective_cancelled=False)
  clock.advance(before)
  return SimpleNamespace(s=s,clock=clock,calls=calls,deadline=s._deadline_at,request_wire=req.canonical_wire,context=context)
 def consumer(self,kind):
  h=self.helper();s=h.s;transcript=s.transcript();s._native_exited=True;s.native_facts.update(empty_job=True,exit_code=0);s._owner._active=s
  owner=object.__new__(own.NativeOwnerSession if kind=='enrollment' else own.NativeCpuOwnerSession)
  owner._approval=s._owner;owner._stopped=threading.Event();owner._closed=False;events=[]
  owner._require_dispatch=lambda context:events.append('dispatch')
  anchor=s._owner._clock()[1];owner._anchor=anchor;owner.clock=lambda:(anchor,replace(anchor,monotonic_ns=anchor.monotonic_ns+h.clock.elapsed,wall_time_ns=anchor.wall_time_ns+h.clock.elapsed))
  if kind=='enrollment':
   s._enrollment=True;owner._expected=ed.enrollment_request();owner._proof=None;transcript=ed.enrollment_transcript(owner._expected)
   owner._require_native=lambda *a,**kw:events.append('native') or SimpleNamespace(current_clock=anchor)
   binding=patch.object(own,'require_enrollment_transcript_binding',side_effect=lambda *a:events.append('binding'))
   invoke=lambda:own.NativeOwnerSession.retain_verified_enrollment(owner,s,h.context);slot='_proof';constructor='_CeremonyWitness'
  else:
   owner._effect_busy=False;owner._effect_retaining=False;owner._effect_proof=None;owner._effect=SimpleNamespace(wire=h.request_wire)
   owner._effect_lease=s._lease=SimpleNamespace(active=True,helper=s.helper_evidence)
   owner._require_effect=lambda *a:events.append('native') or (s.request,None);owner._effect_fence=lambda *a:events.append('fence')
   binding=patch.object(ec,'require_approval_binding',side_effect=lambda *a:events.append('binding'))
   invoke=lambda:own.NativeCpuOwnerSession.retain_verified_effect(owner,s,h.context);slot='_effect_proof';constructor='_NativeEffectWitness'
  binding.start();self.addCleanup(binding.stop);s.transcript=lambda:events.append('transcript') or transcript
  return SimpleNamespace(h=h,s=s,clock=h.clock,owner=owner,events=events,invoke=invoke,slot=slot,constructor=constructor,kind=kind,transcript=transcript)
 def refused(self,f,pattern='BUDGET_EXPIRED'):
  with self.assertRaisesRegex(ContractError,pattern) as c:f.invoke()
  self.assertIsNone(getattr(f.owner,f.slot));self.assertEqual(f.s._deadline_at,f.h.deadline)
  self.assertIs(storage(c.exception)['owned_session'],f.s)
  if f.kind=='effect':self.assertFalse(f.owner._effect_busy);self.assertFalse(f.owner._effect_retaining)
  return c.exception
 def patch_constructor(self,f,action):
  original=getattr(own,f.constructor)
  def make(*a,**k):v=original(*a,**k);action(v);return v
  p=patch.object(own,f.constructor,make);p.start();self.addCleanup(p.stop)
 def guarded_exit(self,f,action):
  original=f.owner._effect_operation;events=f.events
  class Exit:
   def __enter__(self):self.real=original(f.h.context,retained_current=True);value=self.real.__enter__();events.append('guard-entered');return value
   def __exit__(self,*triple):events.append(('exit-triple',triple));value=self.real.__exit__(*triple);events.append('guard-unwound');action();return value
  f.owner._effect_operation=lambda *a,**kw:Exit()
 def test_transcript_on_time_keeps_original_wire_and_deadline(self):
  h=self.helper();t=h.s.transcript();self.assertEqual(t.reported_outcome,'REPORTED_VERIFIED');self.assertEqual(h.s.request.canonical_wire,h.request_wire);self.assertEqual(h.s._deadline_at,h.deadline);self.assertFalse(h.s._stop.is_set());self.assertEqual(len(h.calls),1)
 def test_direct_expired_cached_result_is_not_consumed(self):
  h=self.helper(25_000_000)
  with self.assertRaisesRegex(ContractError,'BUDGET_EXPIRED') as c:h.s.transcript()
  self.assertTrue(h.s._stop.is_set());self.assertEqual(h.calls,[]);self.assertIs(storage(c.exception)['owned_process'],h.s.process)
 def test_currentness_duration_crossing_cutoff_is_charged(self):
  h=self.helper(10_000_000,20_000_000)
  with self.assertRaisesRegex(ContractError,'BUDGET_EXPIRED'):h.s.transcript()
  self.assertEqual(h.clock.elapsed,30_000_000);self.assertTrue(h.s._stop.is_set());self.assertEqual(h.s._deadline_at,h.deadline)
 def test_computed_transcript_is_withheld_after_constructor_cost(self):
  h=self.helper();original=ap.NativeApprovalTranscript;computed=[]
  def make(*a):v=original(*a);computed.append(v);h.clock.advance(20_000_000);return v
  with patch.object(ap,'NativeApprovalTranscript',make),self.assertRaisesRegex(ContractError,'BUDGET_EXPIRED'):h.s.transcript()
  self.assertEqual(len(computed),1);self.assertTrue(h.s._stop.is_set())
 def test_conservative_original_cutoff_has_no_roundup(self):
  for ns,good in [(19_999_997,True),(19_999_998,False),(20_000_000,False)]:
   with self.subTest(elapsed_ns=ns):
    h=self.helper(ns)
    if good:self.assertEqual(h.s.transcript().reported_outcome,'REPORTED_VERIFIED')
    else:
     with self.assertRaisesRegex(ContractError,'BUDGET_EXPIRED'):h.s.transcript()
    self.assertEqual(h.s._deadline_at,h.deadline)
 def test_hostile_clock_primary_and_cancel_secondary_keep_identity(self):
  h=self.helper();primary=Hostile('clock primary');secondary=OSError('cancel secondary')
  h.clock.perf_counter_ns=lambda:(_ for _ in ()).throw(primary);h.s.cancel=lambda:(_ for _ in ()).throw(secondary)
  with self.assertRaises(Hostile) as c:h.s.transcript()
  self.assertIs(c.exception,primary);self.assertEqual(storage(primary)['cleanup_errors'],(secondary,));self.assertIs(storage(primary)['owned_session'],h.s)
 def test_hostile_currentness_keeps_original_exception(self):
  h=self.helper();primary=Hostile('native currentness')
  h.s._current=lambda *a:(_ for _ in ()).throw(primary)
  with self.assertRaises(Hostile) as c:h.s.transcript()
  self.assertIs(c.exception,primary);self.assertIs(storage(primary)['owned_session'],h.s)
 def test_on_time_enrollment_retains_only_its_opaque_witness(self):
  f=self.consumer('enrollment');t,w=f.invoke();self.assertIs(t,f.transcript);self.assertIs(w,f.owner._proof);self.assertIs(w.session,f.s);self.assertEqual(f.s._deadline_at,f.h.deadline)
 def test_on_time_effect_retains_after_real_guard_unwinds(self):
  f=self.consumer('effect');self.guarded_exit(f,lambda:None);t,w=f.invoke();self.assertIs(w,f.owner._effect_proof);self.assertFalse(f.owner._effect_busy);self.assertFalse(f.owner._effect_retaining);self.assertIn('guard-unwound',f.events)
 def test_both_consumers_refuse_before_cached_value_when_expired(self):
  for kind in ['enrollment','effect']:
   with self.subTest(kind=kind):
    f=self.consumer(kind);f.clock.advance(21_000_000);self.refused(f);self.assertNotIn('transcript',f.events);self.assertTrue(f.s._stop.is_set())
 def test_native_retention_observation_cost_prevents_both_publications(self):
  for kind in ['enrollment','effect']:
   with self.subTest(kind=kind):
    f=self.consumer(kind)
    def native(*a,**kw):f.clock.advance(20_000_000);return SimpleNamespace(current_clock=f.owner._anchor) if kind=='enrollment' else (f.s.request,None)
    if kind=='enrollment':f.owner._require_native=native
    else:f.owner._require_effect=native
    self.refused(f);self.assertNotIn('binding',f.events)
 def test_binding_cost_prevents_both_publications(self):
  for kind in ['enrollment','effect']:
   with self.subTest(kind=kind):
    f=self.consumer(kind);target=own if kind=='enrollment' else ec;name='require_enrollment_transcript_binding' if kind=='enrollment' else 'require_approval_binding'
    with patch.object(target,name,side_effect=lambda *a:f.clock.advance(20_000_000)):self.refused(f)
 def test_witness_construction_cost_prevents_both_publications(self):
  for kind in ['enrollment','effect']:
   with self.subTest(kind=kind):
    f=self.consumer(kind);self.patch_constructor(f,lambda v:f.clock.advance(20_000_000));self.refused(f)
 def test_real_guard_unwind_cost_is_charged_before_effect_publication(self):
  f=self.consumer('effect');self.guarded_exit(f,lambda:f.clock.advance(20_000_000));self.refused(f);self.assertIn('guard-unwound',f.events)
 def test_hostile_body_is_not_replaced_by_actual_generator_guard(self):
  f=self.consumer('effect');primary=Hostile('body exact');f.owner._require_effect=lambda *a:(_ for _ in ()).throw(primary)
  with self.assertRaises(Hostile) as c:f.invoke()
  self.assertIs(c.exception,primary);self.assertFalse(f.owner._effect_busy);self.assertFalse(f.owner._effect_retaining);self.assertIsNone(f.owner._effect_proof)
 def test_combined_body_and_guard_secondary_remain_separate(self):
  f=self.consumer('effect');primary=Hostile('body exact');secondary=OSError('guard exact');self.guarded_exit(f,lambda:(_ for _ in ()).throw(secondary));f.owner._require_effect=lambda *a:(_ for _ in ()).throw(primary)
  with self.assertRaises(Hostile) as c:f.invoke()
  self.assertIs(c.exception,primary);self.assertEqual(storage(primary)['cleanup_errors'],(secondary,));self.assertIn(('exit-triple',(None,None,None)),f.events);self.assertIsNone(f.owner._effect_proof);self.assertFalse(f.owner._effect_busy)
 def test_cleanup_only_hostile_error_withholds_computed_proof(self):
  f=self.consumer('effect');primary=Hostile('cleanup exact');self.guarded_exit(f,lambda:(_ for _ in ()).throw(primary))
  with self.assertRaises(Hostile) as c:f.invoke()
  self.assertIs(c.exception,primary);self.assertIsNone(f.owner._effect_proof);self.assertIs(storage(primary)['owned_session'],f.s)
 def test_enrollment_body_hostile_error_keeps_session_custody(self):
  f=self.consumer('enrollment');primary=Hostile('observation exact');f.owner._require_native=lambda *a,**kw:(_ for _ in ()).throw(primary)
  with self.assertRaises(Hostile) as c:f.invoke()
  self.assertIs(c.exception,primary);self.assertIsNone(f.owner._proof);self.assertIs(storage(primary)['owned_session'],f.s)
 def test_stop_in_constructed_witness_never_publishes(self):
  for kind in ['enrollment','effect']:
   with self.subTest(kind=kind):
    f=self.consumer(kind);self.patch_constructor(f,lambda v:f.s._stop.set());self.refused(f,'STOPPED')
 def test_consumer_hostile_clock_cancel_failure_does_not_replace_primary(self):
  for kind in ['enrollment','effect']:
   with self.subTest(kind=kind):
    f=self.consumer(kind);primary=Hostile('elapsed exact');secondary=OSError('cancel exact');f.clock.perf_counter_ns=lambda:(_ for _ in ()).throw(primary);f.s.cancel=lambda:(_ for _ in ()).throw(secondary)
    with self.assertRaises(Hostile) as c:f.invoke()
    self.assertIs(c.exception,primary);self.assertEqual(storage(primary)['cleanup_errors'],(secondary,));self.assertIsNone(getattr(f.owner,f.slot))
 def test_second_retention_never_replays_successful_effect(self):
  f=self.consumer('effect');f.invoke();calls=len(f.events)
  with self.assertRaisesRegex(ContractError,'GENUINE_CEREMONY_REQUIRED'):f.invoke()
  self.assertEqual(len(f.events),calls+1);self.assertEqual(f.s._deadline_at,f.h.deadline)
class Result(unittest.TextTestResult):
 def __init__(self,*a,**k):super().__init__(*a,**k);self.started=[];self.stopped=[]
 def startTest(self,t):self.started.append(t.id());super().startTest(t)
 def stopTest(self,t):self.stopped.append(t.id());super().stopTest(t)
suite=unittest.defaultTestLoader.loadTestsFromTestCase(IndependentConsumptionTests);selected=[t.id() for t in suite]
with (R/'INDEPENDENT-CONSUMPTION.unittest.log').open('x',encoding='utf8') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
unchanged=all(sha(Path(p))==h for p,h in pins.items());assert unchanged
report=dict(schema_version=1,run_id='ceta-jb23-r2',reviewer='/root/independent_broader_review',selected=selected,started=result.started,stopped=result.stopped,tests_run=result.testsRun,failures=[dict(test=t.id(),trace=tr) for t,tr in result.failures],errors=[dict(test=t.id(),trace=tr) for t,tr in result.errors],skips=[dict(test=t.id(),reason=why) for t,why in result.skipped],expected_failures=[t.id() for t,_ in result.expectedFailures],unexpected_successes=[t.id() for t in result.unexpectedSuccesses],forbidden_call_attempts=forbidden,candidate_origins=origins,pins_unchanged=unchanged,pin_count=len(pins),native_or_canonical_or_fixture_effects=False,qualification='Independently authored control bodies exercise actual candidate transcript and owner retention methods with recorded typed helper/results/transcript data and controlled native/clock/binding ports. Native facts are synthetic; no person authenticated, authority granted, native process launched, journal mutated, deadline qualified or product accepted.',successful=result.wasSuccessful())
with (R/'INDEPENDENT-CONSUMPTION.json').open('x',encoding='utf8') as h:json.dump(report,h,indent=2);h.write('\n')
print(json.dumps(dict(tests_run=result.testsRun,successful=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),forbidden_calls=len(forbidden),pins_unchanged=unchanged)));raise SystemExit(0 if result.wasSuccessful() and selected==result.started==result.stopped and not result.skipped and not forbidden else 1)
