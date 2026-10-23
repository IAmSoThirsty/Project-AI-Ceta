"""Deterministic local budget controls; all clocks and OS ports are controlled.

These tests do not authenticate a person, launch a helper/worker/observer, write
an application journal or qualify native timing. The harness forbids those effects.
"""
from dataclasses import dataclass,replace
import ctypes as C
import hashlib,struct,threading,unittest
from types import SimpleNamespace
from unittest.mock import patch

from ceta.composition import real_effect_service as service
from ceta.identity import native_approval as approval,windows_pipe as pipe,owner_session as owner_module
from ceta.effects import native_observer as observer
from ceta.contracts.temporal import Deadline
from ceta.contracts.wire import ContractError
import test_real_effect_entrypoint as entry
import test_native_owner_approval as approval_data
import test_native_observer_origin as observer_data
import test_owner_authority_transactions as data

NS=1_000_000_000
class Clock:
    """Separate controlled epochs, exact integer elapsed increments."""
    def __init__(self,origin=900_000_000_000_000):
        self.origin=origin;self.elapsed=0;self.wall=data.WALL+1_200_000_000
    def perf_counter_ns(self):return self.origin+self.elapsed
    def monotonic_ns(self):return self.origin+self.elapsed
    def monotonic(self):return (self.origin+self.elapsed)/NS
    def time_ns(self):return self.wall+self.elapsed
    def get_clock_info(self,name):return SimpleNamespace(resolution=1/NS)
    def sleep(self,seconds):self.elapsed+=round(seconds*NS)
    def advance(self,nanoseconds):self.elapsed+=nanoseconds

class Hostile(KeyboardInterrupt):
    def __setattr__(self,name,value):raise RuntimeError('hostile attribute setter')
    @property
    def add_note(self):raise RuntimeError('hostile diagnostic getter')

def storage(error):return BaseException.__dict__['__dict__'].__get__(error)

class ManualJointBudgetTests(unittest.TestCase):
    def fixture(self,origin=900_000_000_000_000):
        clock=Clock(origin)
        control=patch.object(service,'time',clock);control.start();self.addCleanup(control.stop)
        fixture=entry._Fixture()
        anchor=fixture.tick
        fixture.runtime._owner.clock=lambda:(anchor,replace(anchor,
            monotonic_ns=anchor.monotonic_ns+clock.elapsed,wall_time_ns=anchor.wall_time_ns+clock.elapsed))
        expiry=anchor.latest_wall_ns+30*NS
        fixture.runtime._registry.remaining_time=lambda context:(30*NS-clock.elapsed,expiry)
        return fixture,clock

    def test_original_anchor_precedes_helper_and_waiting_never_renews(self):
        f,clock=self.fixture();s=f.session;s._request=None
        initial=s._budget_deadline;calls=[]
        enrollment=SimpleNamespace(request_id='enrollment:controlled',canonical_wire=b'enrollment',deadline=initial)
        prepared=SimpleNamespace()
        def prepare(**kw):calls.append(('prepare',kw['timeout_ms']));clock.advance(3*NS);return prepared
        def begin(*a,**kw):calls.append(('gate',initial));clock.advance(2*NS)
        def wait(timeout):calls.append(('wait',timeout));clock.advance(NS);return None
        prepared.begin_enrollment,prepared.wait=begin,wait
        f.runtime._owner.approval_owner=SimpleNamespace(prepare_enrollment=prepare)
        f.runtime._owner.designate_enrollment=lambda *a:None
        f.kernel.begin_owner_enrollment=lambda *a:calls.append(('challenge',initial))
        s._new_enrollment=lambda p:enrollment
        s.enroll();clock.advance(9*NS);s.enroll()
        waits=[row[1] for row in calls if row[0]=='wait']
        self.assertEqual(len([row for row in calls if row[0]=='prepare']),1)
        self.assertLess(waits[1],waits[0]);self.assertIs(s._deadline(replace(f.tick,
            monotonic_ns=f.tick.monotonic_ns+clock.elapsed,wall_time_ns=f.tick.wall_time_ns+clock.elapsed)),initial)
        self.assertEqual(s._enrollment_stage,'WAITING')
        self.assertEqual(s._budget_trace[0]['stage'],'ANCHOR')

    def test_later_approval_receives_remaining_allowance_and_one_original_ceremony(self):
        f,clock=self.fixture();s=f.session;calls=[]
        s._enrollment=SimpleNamespace(request_id='enrollment:controlled',deadline=s._budget_deadline)
        s._approval_stage='NEW'
        def wait(seconds):calls.append(('wait',seconds));clock.advance(NS);return None
        def begin(*a,**kw):calls.append(('begin',kw['timeout_ms']));clock.advance(NS);return SimpleNamespace(wait=wait)
        f.runtime._owner.approval_owner=SimpleNamespace(begin_interactive=begin)
        clock.advance(12*NS);s.approve(f.request.request_id);clock.advance(2*NS);s.approve(f.request.request_id)
        self.assertEqual(len([x for x in calls if x[0]=='begin']),1)
        self.assertLess(calls[0][1],20_000)
        waits=[x[1] for x in calls if x[0]=='wait'];self.assertLess(waits[1],waits[0])

    def test_twenty_millisecond_boundary_is_floored_never_rounded_up(self):
        for allowance in (0,19_999_999,20_000_000,20_999_999):
            with self.subTest(allowance=allowance):
                f,clock=self.fixture();s=f.session
                s._budget_end=clock.perf_counter_ns()+s._later_work_reserve()+allowance
                if allowance<20_000_000:
                    with self.assertRaises(ContractError):s._ceremony_timeout('BOUNDARY')
                else:self.assertEqual(s._ceremony_timeout('BOUNDARY'),20)

    def test_incompatible_initial_limits_deny_before_any_helper(self):
        f,clock=self.fixture();f.session._binding=None;f.session.close()
        f.profile.limits=replace(f.profile.limits,maximum_session_ns=4*NS)
        s=f.profile.command_session(f.context)
        with self.assertRaisesRegex(ContractError,'JOINT_BUDGET_INSUFFICIENT') as caught:s.__enter__()
        self.assertIs(storage(caught.exception)['manual_real_effect_session'],s)
        self.assertIs(f.profile._session,s);self.assertEqual(s._state,'PENDING')
        self.assertIsNone(s._enrollment_session)

    def test_expired_preparation_never_constructs_worker(self):
        f,clock=self.fixture();s=f.session;s._request=None;s._capture=None;s._binding=None
        s._enrollment=SimpleNamespace(deadline=s._budget_deadline);s._enrollment_stage='ENROLLED'
        f.profile.cpu_binding=lambda:self.fail('No worker after original budget expiry')
        clock.advance(30*NS)
        with self.assertRaises(ContractError):s.prepare(cpu_rate=100)
        self.assertIsNone(s._capture)

    def test_overlong_capture_preserves_actual_binding_without_constructing_request(self):
        f,clock=self.fixture();s=f.session;s._request=None
        s._enrollment=SimpleNamespace(deadline=s._budget_deadline);s._enrollment_stage='ENROLLED'
        captured=object()
        def capture():clock.advance(27*NS);return captured
        binding=SimpleNamespace(capture=capture)
        f.profile.cpu_binding=lambda:binding
        with self.assertRaises(ContractError) as caught:s.prepare(cpu_rate=100)
        self.assertIs(s._binding,binding);self.assertIs(s._capture,captured);self.assertIsNone(s._request)
        self.assertIs(storage(caught.exception)['manual_real_effect_session'],s)

    def test_clock_epochs_are_not_subtracted_or_required_equal(self):
        observations=[]
        for offset in (10_000,900_000_000_000_000):
            f,clock=self.fixture(offset);s=f.session
            clock.advance(5*NS);observations.append(s._ceremony_timeout('OFFSET'))
            self.assertNotEqual(clock.perf_counter_ns(),f.tick.monotonic_ns)
        self.assertEqual(observations,[20_000,20_000])

    def test_resume_boot_epoch_untrusted_and_elapsed_rollback_latch(self):
        variants=(dict(boot_id='boot:changed'),dict(durable_epoch=8),dict(resume_generation=1),dict(wall_trusted=False))
        for variant in variants:
            with self.subTest(variant=variant):
                f,clock=self.fixture();f.runtime._owner.clock=lambda:(f.tick,replace(f.tick,**variant))
                with self.assertRaises(ContractError) as first:f.session._remaining('BAD_CLOCK')
                f.runtime._owner.clock=lambda:(f.tick,f.tick)
                with self.assertRaises(ContractError) as second:f.session._remaining('NO_RECOVERY')
                self.assertIs(first.exception,second.exception)
        f,clock=self.fixture();clock.advance(-1)
        with self.assertRaisesRegex(ContractError,'ELAPSED_ROLLBACK'):f.session._remaining('ROLLBACK')

    def test_wall_uncertainty_can_exhaust_budget_before_monotonic(self):
        f,clock=self.fixture();s=f.session
        f.runtime._owner.clock=lambda:(f.tick,replace(f.tick,uncertainty_ns=30*NS))
        with self.assertRaisesRegex(ContractError,'EXPIRED_OR_UNCERTAIN'):s._remaining('UNCERTAIN_WALL')

    def test_restoration_deadline_is_intersection_not_enrollment_renewal(self):
        f,clock=self.fixture();s=f.session;original=s._budget_deadline
        enrollment=SimpleNamespace(deadline=replace(original,expires_monotonic_ns=f.tick.monotonic_ns+5*NS,
            expires_wall_ns=f.tick.latest_wall_ns+5*NS))
        s._enrollment=enrollment;clock.advance(NS);s._remaining('RESTORE')
        result=s._effect_deadline(enrollment)
        self.assertEqual(result.expires_monotonic_ns,enrollment.deadline.expires_monotonic_ns)
        self.assertEqual(result.expires_wall_ns,enrollment.deadline.expires_wall_ns)
        self.assertIs(s._budget_deadline,original)

    def test_timeout_after_admitted_dispatch_retains_outcome_and_never_replays(self):
        f,clock=self.fixture();calls=[]
        def execute(lease):
            calls.append(lease);lease.dispatch_admitted=True;clock.advance(30*NS)
            return SimpleNamespace(as_dict=lambda:dict(state='SETTLED_OBSERVED_CONTROLLED'))
        f.runtime.execute=execute
        with self.assertRaises(ContractError) as caught:f.session.execute(f.request.request_id)
        self.assertEqual(len(calls),1);self.assertTrue(f.session._execution_attempted)
        self.assertIsNotNone(f.session._outcome);self.assertIs(f.session._execution,f.lease)
        self.assertIs(storage(caught.exception)['manual_real_effect_session'],f.session)
        with self.assertRaisesRegex(ContractError,'SINGLE_EXECUTION'):f.session.execute(f.request.request_id)
        self.assertEqual(len(calls),1)

    def test_hostile_dispatch_primary_and_pending_cleanup_remain_original(self):
        f,clock=self.fixture();primary=Hostile('original body');f.lease.pending=True
        def execute(lease):lease.dispatch_admitted=True;clock.advance(30*NS);raise primary
        f.runtime.execute=execute
        with self.assertRaises(Hostile) as caught:f.session.execute(f.request.request_id)
        self.assertIs(caught.exception,primary)
        self.assertFalse(f.session.__exit__(type(primary),primary,BaseException.__traceback__.__get__(primary)))
        self.assertIs(storage(primary)['manual_real_effect_session'],f.session)
        self.assertTrue(storage(primary)['manual_real_effect_cleanup_errors'])
        self.assertEqual(f.session._state,'PENDING');self.assertFalse(f.lease.closed)

@dataclass(frozen=True)
class Result:
    effective_cancelled: bool=False

class ApprovalJointBudgetTests(unittest.TestCase):
    def session(self,*,timeout=20000,mode='inspect'):
        clock=Clock();control=patch.object(approval,'time',clock);control.start();self.addCleanup(control.stop)
        item=approval_data.request()
        wire,frozen=approval._frame('inspect','challenge:one',b'\x01'*32,item,timeout)
        session=approval.NativeApprovalSession(SimpleNamespace(),mode,frozen,object(),timeout,wire)
        session._launching=False;session.process=SimpleNamespace(poll=lambda:None)
        session._read=lambda:None
        return session,clock

    def test_startup_is_charged_to_gate_frame_without_new_deadline(self):
        s,clock=self.session();original=s._deadline_at;clock.advance(6*NS)
        frame,_=s._gate_frame('inspect',s.request)
        self.assertEqual(struct.unpack('<II',frame[8:16])[1],13999)
        self.assertEqual(s._deadline_at,original)

    def test_preparation_timeout_denies_read_and_authentication_gate(self):
        s,clock=self.session(timeout=20,mode='prepared');clock.advance(20_000_000)
        s._read=lambda:self.fail('No read after preparation budget expired')
        with self.assertRaisesRegex(ContractError,'BUDGET_EXPIRED'):s._receive_preparation()
        self.assertTrue(s._stop.is_set());self.assertFalse(s._gate_may_open)

    def test_repeated_wait_is_bounded_by_original_cutoff_and_retains_process(self):
        s,clock=self.session(timeout=40);original=s._deadline_at
        self.assertIsNone(s.wait(.01));self.assertEqual(clock.elapsed,10_000_000)
        self.assertIsNone(s.wait(360));self.assertLessEqual(clock.elapsed,40_000_000)
        self.assertEqual(s._deadline_at,original);self.assertTrue(s._stop.is_set())
        self.assertIsNotNone(s.process);self.assertFalse(s._closed)

    def test_cached_verification_after_timeout_is_effectively_cancelled(self):
        s,clock=self.session(timeout=20);s._result=Result();clock.advance(20_000_000)
        result=s.poll();self.assertTrue(result.effective_cancelled);self.assertTrue(s._stop.is_set())

    def test_exact_minimum_gate_and_subminimum_do_not_round_up(self):
        for remaining in (19_999_999,20_000_000,20_999_999):
            with self.subTest(remaining=remaining):
                s,clock=self.session(timeout=40)
                clock.advance(40_000_000-remaining-2*s._elapsed_resolution)
                if remaining<20_000_000:
                    with self.assertRaisesRegex(ContractError,'BUDGET_EXPIRED'):s._gate_frame('inspect',s.request)
                else:self.assertEqual(struct.unpack('<II',s._gate_frame('inspect',s.request)[0][8:16])[1],20)

    def test_clock_failure_keeps_hostile_primary_and_cancel_secondary(self):
        s,clock=self.session();primary=Hostile('clock interrupt');secondary=OSError('cancel signal')
        clock.perf_counter_ns=lambda:(_ for _ in ()).throw(primary)
        s.cancel=lambda:(_ for _ in ()).throw(secondary)
        with self.assertRaises(Hostile) as caught:s.poll()
        self.assertIs(caught.exception,primary);self.assertIs(storage(primary)['owned_session'],s)
        self.assertEqual(storage(primary)['cleanup_errors'],(secondary,))

    def test_elapsed_rollback_latches_even_after_clock_recovers(self):
        s,clock=self.session();clock.advance(-1)
        with self.assertRaisesRegex(ContractError,'ELAPSED_ROLLBACK') as first:s._remaining_budget()
        clock.advance(NS)
        with self.assertRaises(ContractError) as second:s._remaining_budget()
        self.assertIs(first.exception,second.exception)

    def prepared(self,after_write=None,cleanup=()):
        s,clock=self.session(timeout=100,mode='prepared')
        value=approval_data.NativeEnrollmentDataTests().value()
        s._enrollment=True
        # Semantic enrollment nonce is deliberately distinct from the 32-byte transport nonce.
        s.ceremony_nonce=value.ceremony_nonce
        s.helper_evidence=approval_data.evidence()
        s._enrollment_binding=SimpleNamespace(helper=approval_data.evidence(),helper_commitment=value.helper_commitment,
            interop_module='CONTROLLED')
        s._measure_helper=lambda:None;s._pin_interop=lambda *a:None
        s._code_commitment=lambda:value.helper_commitment
        s._handles=dict(input=11,gate=12);events=[]
        def write(handle,buffer,count,returned,overlap):
            C.cast(returned,C.POINTER(C.c_uint32)).contents.value=count
            events.append('write');return 1
        def close(name):
            events.append('close-input')
            if after_write is not None:after_write(s,clock)
        s._close_named=close;s._api=SimpleNamespace(WriteFile=write,SetEvent=lambda handle:events.append(('gate',handle)) or 1)
        s._cleanup_after_failure=lambda:list(cleanup)
        return s,clock,value,events

    def test_original_gate_body_never_opens_after_write_consumes_budget(self):
        s,clock,value,events=self.prepared(after_write=lambda s,c:c.advance(100_000_000))
        with self.assertRaises(approval.NativeApprovalError):s._bind_enrollment('inspect',value,None)
        self.assertEqual(events,['write','close-input']);self.assertFalse(s._gate_may_open)

    def test_body_interrupt_and_cleanup_failure_preserve_original_exception(self):
        primary=Hostile('input response lost');secondary=OSError('cleanup failed')
        def lost(s,c):raise primary
        s,clock,value,events=self.prepared(after_write=lost,cleanup=(secondary,))
        with self.assertRaises(Hostile) as caught:s._bind_enrollment('inspect',value,None)
        self.assertIs(caught.exception,primary);self.assertIs(storage(primary)['owned_session'],s)
        self.assertEqual(storage(primary)['cleanup_errors'],(secondary,));self.assertFalse(s._gate_may_open)

    def test_final_interactive_currentness_is_rechecked_before_gate_and_charged(self):
        s,clock,value,events=self.prepared();checks=[]
        class Guard:
            def __enter__(self):return self
            def __exit__(self,*a):return False
            def require_current(self,*args):
                checks.append(args)
                if len(checks)==2:clock.advance(100_000_000)
        anchor=data.clock(1_100_000_000)
        s._owner._retain_enrollment=lambda *a:Guard()
        s._owner._clock=lambda:(anchor,anchor)
        with self.assertRaises(approval.NativeApprovalError):s._bind_enrollment('interactive',value,object())
        self.assertEqual(len(checks),2)
        self.assertEqual(events,['write','close-input']);self.assertFalse(s._gate_may_open)

class ObserverJointBudgetTests(unittest.TestCase):
    def fixture(self,offset=800_000_000_000_000):
        fixture=observer_data.ControlledObserverOriginTests('test_success_retains_exact_object_and_allows_canonical_request_decode')
        fixture.setUp();self.addCleanup(fixture.doCleanups)
        clock=Clock(offset);control=patch.object(observer,'time',clock);control.start();self.addCleanup(control.stop)
        return fixture,clock

    def test_exchange_clamps_preparation_and_arbitrary_elapsed_epoch(self):
        deadlines=[]
        for offset in (10_000,800_000_000_000_000):
            f,clock=self.fixture(offset);old=f.exchange
            def handles(*a):clock.advance(400_000_000);return SimpleNamespace(inherited_handles=(101,102))
            f.target.export_cpu_query_handles=handles
            def exchange(custody,frame,cancelled,deadline):
                deadlines.append(deadline-clock.monotonic_ns());return old(custody,frame,cancelled,deadline)
            f.observer._exchange=exchange;value=f.observe();f.require_origin(value)
        self.assertEqual(deadlines,[600_000_000-2,600_000_000-2])

    def test_elapsed_preparation_exhaustion_never_enters_observer_transport(self):
        f,clock=self.fixture()
        def handles(*a):clock.advance(NS);return SimpleNamespace(inherited_handles=(101,102))
        f.target.export_cpu_query_handles=handles
        f.observer._exchange=lambda *a:self.fail('No observer transport after original budget expired')
        with self.assertRaisesRegex(ContractError,'REMAINING_BUDGET_EXPIRED'):f.observe()
        self.assertIsNone(f.observer._origin)

    def test_canonical_remaining_deadline_can_be_stricter_than_duration_ceiling(self):
        f,clock=self.fixture();start=data.clock(1_100_000_000)
        f.request=replace(f.request,deadline=replace(f.request.deadline,
            expires_monotonic_ns=start.monotonic_ns+50_000_000,
            expires_wall_ns=start.latest_wall_ns+50_000_000))
        called=[];old=f.exchange
        def exchange(custody,frame,cancelled,deadline):called.append(deadline-clock.monotonic_ns());return old(custody,frame,cancelled,deadline)
        f.observer._exchange=exchange
        with self.assertRaises(ContractError):f.observe()  # final fresh native sample also crosses deadline
        self.assertEqual(called,[50_000_000-2]);self.assertIsNone(f.observer._origin)

    def test_expiry_during_diagnostic_cleanup_never_publishes_computed_origin(self):
        f,clock=self.fixture();f.on_evidence=lambda:clock.advance(NS)
        with self.assertRaisesRegex(ContractError,'REMAINING_BUDGET_EXPIRED'):f.observe()
        self.assertIsNone(f.observer._origin);self.assertFalse(f.observer.last_evidence['accepted'])

    def test_hostile_observer_primary_and_cleanup_remain_owned(self):
        f,clock=self.fixture();primary=Hostile('observer response loss');secondary=OSError('cleanup')
        f.observer._exchange=lambda *a:(_ for _ in ()).throw(primary)
        f.close_failure=secondary;f.fail_close_number=1
        with self.assertRaises(Hostile) as caught:f.observe()
        self.assertIs(caught.exception,primary);self.assertIsNone(f.observer._origin)
        self.assertIn('observer_custody',storage(primary))

class RegistryAndResponseBudgetTests(unittest.TestCase):
    def registry(self):
        clock=Clock();control=patch.object(pipe,'time',clock);control.start();self.addCleanup(control.stop)
        registry=object.__new__(pipe.WindowsPeerRegistry)
        registry._lock=threading.RLock();registry._closed=False
        registry._api=SimpleNamespace(GetCurrentThreadId=lambda:123)
        context=object();entry=object();facts=object()
        message=SimpleNamespace(issued_at_ms=clock.wall//1_000_000-1,expires_at_ms=(clock.wall+30*NS)//1_000_000)
        active=pipe._Active(entry,object(),123,message,facts,clock.monotonic()+30)
        registry._active={context:active};registry._pipe_peer=lambda *a:(entry,facts)
        return registry,context,clock,active

    def test_remaining_read_rechecks_after_peer_query_and_preserves_original_bounds(self):
        r,c,clock,active=self.registry();first=r.remaining_time(c)
        clock.advance(3*NS);second=r.remaining_time(c)
        self.assertLess(second[0],first[0]);self.assertEqual(first[1],second[1])
        self.assertIs(r._active[c],active);self.assertLess(second[0],27*NS)
        with self.assertRaises(ContractError):r.remaining_time(object())

    def test_peer_query_crossing_monotonic_or_envelope_deadline_denies_duration(self):
        for axis in ('monotonic','wall'):
            with self.subTest(axis=axis):
                r,c,clock,active=self.registry()
                def peer(*a):
                    if axis=='monotonic':clock.advance(30*NS)
                    else:clock.wall+=30*NS
                    return active.entry,active.message_facts
                r._pipe_peer=peer
                with self.assertRaises(ContractError):r.remaining_time(c)

    def receiver(self,expire_response=False):
        clock=Clock();control=patch.object(pipe,'time',clock);control.start();self.addCleanup(control.stop)
        s=object.__new__(pipe.WindowsPipeServer);s._lock=threading.Lock()
        s._retained_context=None;s._closed=False;s._pipe=object();s._api=object();s._codec=None
        context=object();message=SimpleNamespace();entry=SimpleNamespace(registration=SimpleNamespace(
            session_id='session:controlled',allowed_operations=(),allowed_scopes=()))
        s._registry=SimpleNamespace(_header_peer=lambda *a:(entry,()),_activate=lambda *a:context,require_message=lambda *a:None)
        s._ingress=SimpleNamespace(accept=lambda *a,**kw:None);calls=[];deadlines=[];body=b'abc';response=b'ok'
        s._handler=lambda m,c:calls.append(('handler',c)) or 'CONTROLLED_ADMITTED_OUTCOME'
        def encode(*a):
            if expire_response:clock.advance(11*NS)
            return response
        s._response_encoder=encode;s._retire_dispatch_context=lambda c,*a:calls.append(('retire',c))
        reads=iter((struct.pack('>I',len(body)),body,hashlib.sha256(response).digest()))
        def io(api,operation,handle,deadline,buffer=None,count=None):
            deadlines.append((operation,deadline))
            if clock.monotonic()>=deadline:raise ContractError('WINDOWS_PIPE_TIMEOUT')
            if operation=='connect':return 0,False
            if operation=='write':return count,False
            raw=next(reads);C.memmove(buffer,raw,len(raw));return len(raw),len(raw)==4
        for item in (patch.object(pipe,'_io',io),patch.object(pipe,'decode_message',return_value=message)):
            item.start();self.addCleanup(item.stop)
        return s,clock,calls,deadlines,context

    def test_connect_response_and_ack_share_one_original_deadline(self):
        s,clock,calls,deadlines,context=self.receiver()
        start=clock.monotonic();self.assertEqual(s.receive_once(10),'CONTROLLED_ADMITTED_OUTCOME')
        self.assertEqual([x[0] for x in deadlines],['connect','read','read','write','read'])
        self.assertTrue(all(deadline==start+10 for _,deadline in deadlines))
        self.assertEqual(calls,[('handler',context),('retire',context)])


    def test_response_overrun_does_not_renew_deadline_or_reexecute_handler(self):
        s,clock,calls,deadlines,context=self.receiver(expire_response=True)
        start=clock.monotonic()
        with self.assertRaisesRegex(ContractError,'WINDOWS_PIPE_TIMEOUT'):s.receive_once(10)
        self.assertTrue(all(deadline==start+10 for _,deadline in deadlines))
        self.assertEqual(calls,[('handler',context),('retire',context)])


class TranscriptConsumptionBudgetTests(unittest.TestCase):
    """Fresh four-case successor to the independent rejected-JB1 witness."""
    def session(self,before=0,during=0):
        clock=Clock();control=patch.object(approval,'time',clock);control.start();self.addCleanup(control.stop)
        anchor=approval_data.ClockSample('boot:fixture',1,0,approval_data.MONO,approval_data.WALL,0,True)
        def pair():return anchor,replace(anchor,monotonic_ns=anchor.monotonic_ns+clock.elapsed,wall_time_ns=anchor.wall_time_ns+clock.elapsed)
        owner=SimpleNamespace(helper_source_commitment=approval_data.HASH,_clock=pair)
        wire,frozen=approval._frame('inspect','challenge:one',b'\x01'*32,approval_data.request(),20)
        s=approval.NativeApprovalSession(owner,'interactive',frozen,object(),20,wire)
        s._launching=False;s.process=SimpleNamespace(poll=lambda:None);s.helper_evidence=approval_data.evidence()
        s.native_facts['interop_library']=dict(sha256='a'*64);checks=[]
        def current(*args):checks.append(args);clock.advance(during)
        s._current=current
        observed=approval_data.parse(approval_data.response())
        s._result=replace(observed,mode='interactive',status='VERIFIED',authentication_invoked=True,
            hardware_click=True,display_exact=True,native_hresult=0,native_result=0,effective_cancelled=False)
        self.assertTrue(s._result.reported_verified)
        clock.advance(before)
        return s,clock,checks

    def test_independent_witness_valid_control_5ms(self):
        s,clock,checks=self.session(5_000_000)
        original=s._deadline_at;value=s.transcript()
        self.assertEqual(value.reported_outcome,'REPORTED_VERIFIED');self.assertFalse(s._stop.is_set())
        self.assertEqual(len(checks),1);self.assertEqual(s._deadline_at,original)

    def test_independent_witness_direct_cached_verification_25ms_refused(self):
        s,clock,checks=self.session(25_000_000)
        with self.assertRaisesRegex(ContractError,'BUDGET_EXPIRED') as caught:s.transcript()
        self.assertTrue(s._stop.is_set());self.assertEqual(checks,[])
        self.assertIs(storage(caught.exception)['owned_session'],s)
        self.assertIs(storage(caught.exception)['owned_process'],s.process)

    def test_independent_witness_currentness_10_plus20ms_refused(self):
        s,clock,checks=self.session(10_000_000,20_000_000)
        with self.assertRaisesRegex(ContractError,'BUDGET_EXPIRED'):s.transcript()
        self.assertEqual(clock.elapsed,30_000_000);self.assertTrue(s._stop.is_set());self.assertEqual(len(checks),1)

    def test_independent_witness_expired_poll_control_still_refuses(self):
        s,clock,checks=self.session(25_000_000)
        self.assertTrue(s.poll().effective_cancelled)
        with self.assertRaises(ContractError):s.transcript()
        self.assertTrue(s._stop.is_set());self.assertEqual(checks,[])

    def test_conservative_boundary_and_exact_cutoff_never_round_up(self):
        for before,accept in ((19_999_997,True),(19_999_998,False),(20_000_000,False)):
            with self.subTest(before=before):
                s,clock,checks=self.session(before)
                if accept:self.assertEqual(s.transcript().reported_outcome,'REPORTED_VERIFIED')
                else:
                    with self.assertRaises(ContractError):s.transcript()

    def test_expiry_in_transcript_construction_denies_publication(self):
        s,clock,checks=self.session(5_000_000);original=approval.NativeApprovalTranscript;computed=[]
        def make(*args,**kwargs):
            value=original(*args,**kwargs);computed.append(value);clock.advance(20_000_000);return value
        with patch.object(approval,'NativeApprovalTranscript',make),self.assertRaisesRegex(ContractError,'BUDGET_EXPIRED'):s.transcript()
        self.assertEqual(len(computed),1);self.assertTrue(s._stop.is_set())

    def test_transcript_expiry_preserves_cancel_failure_and_actual_session(self):
        s,clock,checks=self.session(25_000_000);secondary=OSError('cancel signal failed')
        s.cancel=lambda:(_ for _ in ()).throw(secondary)
        with self.assertRaisesRegex(ContractError,'BUDGET_EXPIRED') as caught:s.transcript()
        self.assertEqual(storage(caught.exception)['cleanup_errors'],(secondary,))
        self.assertIs(storage(caught.exception)['owned_session'],s)

    def test_transcript_hostile_clock_primary_preserves_cancel_secondary(self):
        s,clock,checks=self.session(5_000_000);primary=Hostile('original clock');secondary=OSError('cancel')
        clock.perf_counter_ns=lambda:(_ for _ in ()).throw(primary)
        s.cancel=lambda:(_ for _ in ()).throw(secondary)
        with self.assertRaises(Hostile) as caught:s.transcript()
        self.assertIs(caught.exception,primary);self.assertEqual(storage(primary)['cleanup_errors'],(secondary,))
        self.assertIs(storage(primary)['owned_session'],s);self.assertIs(storage(primary)['owned_process'],s.process)

    def test_transcript_currentness_hostile_primary_is_not_replaced(self):
        s,clock,checks=self.session(5_000_000);primary=Hostile('native currentness interrupted')
        s._current=lambda *a:(_ for _ in ()).throw(primary)
        with self.assertRaises(Hostile) as caught:s.transcript()
        self.assertIs(caught.exception,primary);self.assertIs(storage(primary)['owned_session'],s)


class OwnerConsumptionBudgetTests(unittest.TestCase):
    """Real retention methods with recorded native/binding ports, no authority grant.

    The actual typed helper session and transcript are retained. Native facts and
    binding/currentness calls are controlled seams; their semantic validation is
    covered by the retained validator cohorts, not claimed as native proof here.
    """
    def fixture(self,kind):
        fixture=TranscriptConsumptionBudgetTests()
        session,clock,checks=fixture.session(5_000_000);self.addCleanup(fixture.doCleanups)
        transcript=session.transcript();events=[]
        session._native_exited=True;session.native_facts.update(empty_job=True,exit_code=0)
        session._owner._active=session
        cls=owner_module.NativeOwnerSession if kind=='enrollment' else owner_module.NativeCpuOwnerSession
        owner=object.__new__(cls);owner._approval=session._owner;owner._stopped=threading.Event()
        owner._require_dispatch=lambda context:events.append(('dispatch',context))
        owner._anchor=clock_pair=session._owner._clock()[1]
        owner.clock=lambda:(clock_pair,replace(clock_pair,monotonic_ns=clock_pair.monotonic_ns+clock.elapsed,
            wall_time_ns=clock_pair.wall_time_ns+clock.elapsed))
        context=session._context
        if kind=='enrollment':
            session._enrollment=True;owner._expected=data.enrollment_request();owner._proof=None
            transcript=data.enrollment_transcript(owner._expected)
            owner._require_native=lambda *a,**kw:events.append('native') or SimpleNamespace(current_clock=clock_pair)
            binding=patch.object(owner_module,'require_enrollment_transcript_binding',
                side_effect=lambda *a:events.append('binding'))
            invoke=lambda:owner.retain_verified_enrollment(session,context)
            slot='_proof';proof_name='_CeremonyWitness'
        else:
            owner._effect_busy=False;owner._effect_retaining=False;owner._effect_proof=None
            owner._effect=SimpleNamespace(wire=session.request.canonical_wire)
            owner._effect_lease=session._lease=SimpleNamespace(active=True,helper=session.helper_evidence)
            owner._require_effect=lambda *a:events.append('native') or (session.request,None)
            owner._effect_fence=lambda *a:events.append('fence')
            import ceta.contracts.real_effect as effect_contract
            binding=patch.object(effect_contract,'require_approval_binding',side_effect=lambda *a:events.append('binding'))
            invoke=lambda:owner.retain_verified_effect(session,context)
            slot='_effect_proof';proof_name='_NativeEffectWitness'
        binding.start();self.addCleanup(binding.stop)
        session.transcript=lambda:events.append('transcript') or transcript
        return SimpleNamespace(kind=kind,session=session,clock=clock,owner=owner,events=events,
            transcript=transcript,invoke=invoke,slot=slot,proof_name=proof_name)

    def refused(self,f):
        with self.assertRaisesRegex(ContractError,'BUDGET_EXPIRED') as caught:f.invoke()
        self.assertIsNone(getattr(f.owner,f.slot));self.assertTrue(f.session._stop.is_set())
        self.assertIs(storage(caught.exception)['owned_session'],f.session)
        self.assertIs(storage(caught.exception)['owned_process'],f.session.process)
        if f.kind=='effect':self.assertFalse(f.owner._effect_retaining);self.assertFalse(f.owner._effect_busy)
        return caught.exception

    def test_on_time_enrollment_publishes_only_retained_local_witness(self):
        f=self.fixture('enrollment');transcript,proof=f.invoke()
        self.assertIs(transcript,f.transcript);self.assertIs(proof,f.owner._proof)
        self.assertIs(proof.session,f.session);self.assertFalse(f.session._stop.is_set())

    def test_on_time_effect_publishes_only_after_original_guard_unwinds(self):
        f=self.fixture('effect');transcript,proof=f.invoke()
        self.assertIs(transcript,f.transcript);self.assertIs(proof,f.owner._effect_proof)
        self.assertIs(proof.session,f.session);self.assertFalse(f.owner._effect_busy)
        self.assertFalse(f.owner._effect_retaining);self.assertFalse(f.session._stop.is_set())

    def test_already_expired_retention_never_calls_cached_transcript(self):
        for kind in ('enrollment','effect'):
            with self.subTest(kind=kind):
                f=self.fixture(kind);f.clock.advance(20_000_000);self.refused(f)
                self.assertNotIn('transcript',f.events);self.assertNotIn('native',f.events)

    def test_expiry_during_cached_transcript_denies_further_native_work(self):
        for kind in ('enrollment','effect'):
            with self.subTest(kind=kind):
                f=self.fixture(kind)
                def transcript():f.clock.advance(20_000_000);return f.transcript
                f.session.transcript=transcript;self.refused(f);self.assertNotIn('native',f.events)

    def test_expiry_during_native_retention_observation_never_publishes(self):
        for kind in ('enrollment','effect'):
            with self.subTest(kind=kind):
                f=self.fixture(kind)
                if kind=='enrollment':
                    def native(*a,**kw):f.clock.advance(20_000_000);return SimpleNamespace(current_clock=f.owner._anchor)
                    f.owner._require_native=native
                else:
                    def native(*a):f.clock.advance(20_000_000);return f.session.request,None
                    f.owner._require_effect=native
                self.refused(f)
                self.assertNotIn('binding',f.events);self.assertNotIn('fence',f.events)

    def test_effect_binding_expiry_never_enters_later_currentness_fence(self):
        f=self.fixture('effect')
        import ceta.contracts.real_effect as effect_contract
        point=patch.object(effect_contract,'require_approval_binding',
            side_effect=lambda *a:f.clock.advance(20_000_000))
        point.start();self.addCleanup(point.stop);self.refused(f)
        self.assertNotIn('fence',f.events)

    def test_expiry_during_binding_or_final_currentness_never_publishes(self):
        for kind in ('enrollment','effect'):
            with self.subTest(kind=kind):
                f=self.fixture(kind)
                if kind=='enrollment':
                    point=patch.object(owner_module,'require_enrollment_transcript_binding',
                        side_effect=lambda *a:f.clock.advance(20_000_000))
                else:
                    point=patch.object(f.owner,'_effect_fence',side_effect=lambda *a:f.clock.advance(20_000_000))
                point.start();self.addCleanup(point.stop);self.refused(f)

    def test_expiry_during_witness_construction_is_charged_before_publication(self):
        for kind in ('enrollment','effect'):
            with self.subTest(kind=kind):
                f=self.fixture(kind);original=getattr(owner_module,f.proof_name);computed=[]
                def make(*a):
                    value=original(*a);computed.append(value);f.clock.advance(20_000_000);return value
                point=patch.object(owner_module,f.proof_name,side_effect=make);point.start();self.addCleanup(point.stop)
                self.refused(f);self.assertEqual(len(computed),1)

    def test_consumer_exact_conservative_boundary_is_not_renewed(self):
        for kind in ('enrollment','effect'):
            for elapsed,accept in ((19_999_997,True),(19_999_998,False),(20_000_000,False)):
                with self.subTest(kind=kind,elapsed=elapsed):
                    f=self.fixture(kind);f.clock.advance(elapsed-f.clock.elapsed);deadline=f.session._deadline_at
                    if accept:self.assertIs(f.invoke()[1],getattr(f.owner,f.slot))
                    else:self.refused(f)
                    self.assertEqual(f.session._deadline_at,deadline)

    def test_hostile_elapsed_primary_keeps_cancel_secondary_at_both_consumers(self):
        for kind in ('enrollment','effect'):
            with self.subTest(kind=kind):
                f=self.fixture(kind);primary=Hostile('elapsed read interrupted');secondary=OSError('cancel failed')
                f.clock.perf_counter_ns=lambda:(_ for _ in ()).throw(primary)
                f.session.cancel=lambda:(_ for _ in ()).throw(secondary)
                with self.assertRaises(Hostile) as caught:f.invoke()
                self.assertIs(caught.exception,primary);self.assertIsNone(getattr(f.owner,f.slot))
                self.assertEqual(storage(primary)['cleanup_errors'],(secondary,))
                self.assertIs(storage(primary)['owned_session'],f.session)
                if kind=='effect':self.assertFalse(f.owner._effect_retaining)

    def test_hostile_retention_body_error_survives_actual_local_guard(self):
        for kind in ('enrollment','effect'):
            with self.subTest(kind=kind):
                f=self.fixture(kind);primary=Hostile('retention native observation interrupted')
                fail=lambda *a,**kw:(_ for _ in ()).throw(primary)
                if kind=='enrollment':f.owner._require_native=fail
                else:f.owner._require_effect=fail
                with self.assertRaises(Hostile) as caught:f.invoke()
                self.assertIs(caught.exception,primary);self.assertIsNone(getattr(f.owner,f.slot))
                self.assertIs(storage(primary)['owned_session'],f.session)
                if kind=='effect':self.assertFalse(f.owner._effect_busy);self.assertFalse(f.owner._effect_retaining)

    def test_effect_hostile_body_and_guard_cleanup_keep_original_primary(self):
        f=self.fixture('effect');primary=Hostile('body interrupted');secondary=OSError('guard exit failed');exits=[]
        class Guard:
            def __enter__(self):return self
            def __exit__(self,*triple):exits.append(triple);raise secondary
        f.owner._effect_operation=lambda *a,**kw:Guard()
        f.owner._require_effect=lambda *a:(_ for _ in ()).throw(primary)
        with self.assertRaises(Hostile) as caught:f.invoke()
        self.assertIs(caught.exception,primary);self.assertEqual(exits,[(None,None,None)])
        self.assertEqual(storage(primary)['cleanup_errors'],(secondary,))
        self.assertIs(storage(primary)['owned_session'],f.session)
        self.assertIsNone(f.owner._effect_proof);self.assertFalse(f.owner._effect_retaining)

    def test_effect_cleanup_only_failure_precedes_proof_publication(self):
        f=self.fixture('effect');primary=Hostile('cleanup alone interrupted')
        class Guard:
            def __enter__(self):return self
            def __exit__(self,*triple):raise primary
        f.owner._effect_operation=lambda *a,**kw:Guard()
        with self.assertRaises(Hostile) as caught:f.invoke()
        self.assertIs(caught.exception,primary);self.assertIsNone(f.owner._effect_proof)
        self.assertIs(storage(primary)['owned_session'],f.session);self.assertFalse(f.owner._effect_retaining)

    def test_effect_guard_cleanup_consumes_the_original_budget(self):
        f=self.fixture('effect')
        class Guard:
            def __enter__(self):return self
            def __exit__(self,*triple):f.clock.advance(20_000_000);return False
        f.owner._effect_operation=lambda *a,**kw:Guard();self.refused(f)

    def test_stop_during_witness_construction_never_publishes(self):
        for kind in ('enrollment','effect'):
            with self.subTest(kind=kind):
                f=self.fixture(kind);original=getattr(owner_module,f.proof_name)
                def make(*a):
                    value=original(*a);f.session._stop.set();return value
                point=patch.object(owner_module,f.proof_name,side_effect=make);point.start();self.addCleanup(point.stop)
                with self.assertRaisesRegex(ContractError,'STOPPED'):f.invoke()
                self.assertIsNone(getattr(f.owner,f.slot))

