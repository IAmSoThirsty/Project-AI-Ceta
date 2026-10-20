"""Controlled clock-domain math plus real owned medium-worker policy queries.

Controlled instances below establish domain logic, not native clock authority.
Actual Windows cases forbid every class15 write and permit only canonical
class9 setup of their own disposable worker job.
"""
from dataclasses import FrozenInstanceError, replace
import os
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ceta.effects import native_cpu_binding as module
from ceta.contracts.real_effect import OwnedCpuRequest
from ceta.contracts.resource_management import ObservationState
from ceta.contracts.temporal import ClockSample, Deadline
from ceta.contracts.wire import ContractError
from ceta.contracts.workload_throttling import CpuRateLimit, CpuRateObservation
from ceta.identity.native_clock import NativeSessionClock
from ceta.supervisor.windows_jobs import WindowsOwnedProcess
import test_real_effect_contract as data

NATIVE_RECEIPTS = []


def request(capture, duration=500_000_000, age=1_000_000_000, lifetime=3_000_000_000):
    current=capture.native_after
    return replace(data.request(),process_identity=capture.observation.identity,
        job_digest=capture.observation.job_digest,expected_limit=capture.observation,
        original_limit=capture.observation.limit,maximum_duration_ns=duration,
        maximum_observation_age_ns=age,deadline=Deadline(current.boot_id,current.durable_epoch,
            current.resume_generation,current.monotonic_ns,current.monotonic_ns+lifetime,
            current.earliest_wall_ns,current.latest_wall_ns+lifetime))


class ControlledHost:
    """No native resources or production qualification; three independent epochs."""
    def __init__(self, native=10_000_000_000,driver=500_000_000):
        self.native,self.driver,self.elapsed=native,driver,700_000_000_000
        self.previous=None;self.on_clock=self.on_query=self.on_member=self.on_elapsed=None
        self.queries=0;self.unavailable=False;self.member=True;self.driver_stamp_delta=0
        target=self.target=object.__new__(WindowsOwnedProcess)
        target._process,target._job,target._thread=101,202,303
        target._pid,target._creation_time,target._image_sha256=42,123,'a'*64
        target._cpu_job_digest=data.HASH
        target._closed=target._termination_requested=target._cpu_lifetime_unavailable=False
        target._exit_code=None;target._cpu_version=0;target._cpu_policy=CpuRateLimit(0,0)
        target._lock=threading.RLock();target.cpu_rate_observation=self.observe
        target._cpu_member_current=self.membership
        clock=self.clock=object.__new__(NativeSessionClock)
        clock._condition=threading.Condition(threading.RLock());clock._state='ACTIVE';clock._reason=None
        clock._session='1'*32;clock._epoch=1;clock._resume=0;clock._registration=111
        clock.clock=self.sample

    def advance(self, amount=1000):
        self.native+=amount;self.driver+=amount;self.elapsed+=amount

    def driver_now(self):self.advance();return self.driver
    def elapsed_now(self):
        self.advance()
        if self.on_elapsed:self.on_elapsed()
        return self.elapsed

    def sample(self):
        self.advance()
        sample=ClockSample('boot:controlled-native-session',1,self.clock._resume,self.native,
            data.WALL+self.native,10_000,True)
        previous=self.previous or sample;self.previous=sample
        if self.on_clock:self.on_clock()
        return previous,sample

    def observe(self, identity, **kwargs):
        self.queries+=1;self.advance()
        if self.on_query:self.on_query()
        return CpuRateObservation(identity,self.target._cpu_job_digest,
            ObservationState.UNAVAILABLE if self.unavailable else ObservationState.MEASURED,
            None if self.unavailable else self.target._cpu_policy,self.target._cpu_version,
            self.driver+self.driver_stamp_delta,'CONTROLLED_UNAVAILABLE' if self.unavailable else None)

    def membership(self,identity):
        if self.on_member:self.on_member()
        return self.member

    @staticmethod
    def clock_info(name):
        return SimpleNamespace(implementation='GetTickCount64()' if name=='monotonic' else 'QueryPerformanceCounter()',
            monotonic=True,adjustable=False,resolution=.001 if name=='monotonic' else .0000001)

    def binding(self, **kwargs):
        with patch.object(module.time,'get_clock_info',self.clock_info), \
             patch.object(module.time,'monotonic_ns',self.driver_now), \
             patch.object(module.time,'perf_counter_ns',self.elapsed_now):
            return module.NativeCpuBinding(self.target,self.clock,**kwargs)


class NativeCpuBindingDomainTests(unittest.TestCase):
    def fixture(self, **kwargs):
        host=ControlledHost();binding=host.binding(**kwargs)
        self.addCleanup(binding.close)
        return host,binding

    def test_measured_zero_policy_retains_both_distinct_time_domains(self):
        host,binding=self.fixture();capture=binding.capture();item=request(capture)
        self.assertEqual(capture.observation.limit,CpuRateLimit(0,0))
        self.assertEqual(capture.observation.state,ObservationState.MEASURED)
        self.assertNotEqual(capture.observation.observed_monotonic_ns,capture.original_driver_timestamp_ns)
        arguments=binding.driver_arguments(capture,item)
        self.assertEqual(arguments.expected.observed_monotonic_ns,capture.original_driver_timestamp_ns)
        self.assertEqual(arguments.expected.limit,CpuRateLimit(0,0))
        self.assertEqual(arguments.driver_domain,module.DRIVER_DOMAIN)
        self.assertIsNone(binding.require_current(capture,item))

    def test_translation_does_not_require_equal_or_positive_native_minus_driver_epoch(self):
        for native,driver in ((10_000_000_000,500_000_000),(500_000_000,10_000_000_000)):
            with self.subTest(native=native,driver=driver):
                host=ControlledHost(native,driver);binding=host.binding();self.addCleanup(binding.close)
                capture=binding.capture();item=request(capture);args=binding.driver_arguments(capture,item)
                self.assertLess(args.deadline_monotonic_ns+(native-driver),item.deadline.expires_monotonic_ns)
                self.assertGreater(args.maximum_duration_ns,0)

    def test_translation_charges_both_endpoint_resolutions_uncertainty_and_elapsed(self):
        host,binding=self.fixture();capture=binding.capture();item=request(capture)
        args=binding.driver_arguments(capture,item)
        self.assertLess(args.maximum_duration_ns,item.maximum_duration_ns-2*capture.driver_resolution_ns)
        self.assertLess(args.maximum_age_ns,item.maximum_observation_age_ns)
        self.assertLess(args.deadline_monotonic_ns+host.native-host.driver,item.deadline.expires_monotonic_ns)
        self.assertGreaterEqual(capture.acquisition_ns,2*capture.native_before.uncertainty_ns)

    def test_immutable_arguments_and_fresh_keyword_mapping(self):
        host,binding=self.fixture();capture=binding.capture();args=binding.driver_arguments(capture,request(capture))
        with self.assertRaises(FrozenInstanceError):args.maximum_age_ns=1
        with self.assertRaises(TypeError):args.keyword_arguments['maximum_age_ns']=1
        self.assertEqual(set(args.keyword_arguments),{'deadline_monotonic_ns','maximum_age_ns','maximum_duration_ns'})

    def test_equal_capture_value_copy_has_no_private_custody(self):
        host,binding=self.fixture();capture=binding.capture()
        with self.assertRaisesRegex(ContractError,'CAPTURE_NOT_OWNED'):binding.require_current(replace(capture),request(capture))

    def test_another_binding_cannot_resolve_the_capture(self):
        host,binding=self.fixture();capture=binding.capture();other=host.binding();self.addCleanup(other.close)
        with self.assertRaisesRegex(ContractError,'CAPTURE_NOT_OWNED'):other.require_current(capture,request(capture))

    def test_new_capture_invalidates_the_single_previous_identity(self):
        host,binding=self.fixture();first=binding.capture();second=binding.capture()
        self.assertEqual(second.sequence,first.sequence+1)
        with self.assertRaisesRegex(ContractError,'CAPTURE_NOT_OWNED'):binding.require_current(first,request(first))
        self.assertIsNone(binding.require_current(second,request(second)))

    def test_failed_replacement_does_not_leave_older_capture_current(self):
        host,binding=self.fixture();first=binding.capture();host.unavailable=True
        with self.assertRaisesRegex(ContractError,'POLICY_UNAVAILABLE'):binding.capture()
        host.unavailable=False
        with self.assertRaisesRegex(ContractError,'CAPTURE_NOT_OWNED'):binding.require_current(first,request(first))

    def test_public_capture_mutation_does_not_change_private_original_policy(self):
        host,binding=self.fixture();capture=binding.capture();item=request(capture)
        object.__setattr__(capture.observation.limit,'value',9)
        self.assertEqual(binding._current.measurement.original.limit,CpuRateLimit(0,0))
        with self.assertRaisesRegex(ContractError,'CAPTURE_CHANGED'):binding.require_current(capture,item)

    def test_mutation_during_final_member_read_does_not_alter_private_expectation(self):
        host,binding=self.fixture();capture=binding.capture();item=request(capture)
        host.on_member=lambda:object.__setattr__(capture.observation.limit,'value',9)
        with self.assertRaisesRegex(ContractError,'CAPTURE_CHANGED'):binding.driver_arguments(capture,item)
        self.assertEqual(binding._current.measurement.original.limit,CpuRateLimit(0,0))

    def test_request_must_bind_exact_native_observation(self):
        host,binding=self.fixture();capture=binding.capture();item=request(capture)
        bad=replace(item,expected_limit=replace(item.expected_limit,
            observed_monotonic_ns=item.expected_limit.observed_monotonic_ns+1))
        with self.assertRaisesRegex(ContractError,'REQUEST_CAPTURE_MISMATCH'):binding.require_current(capture,bad)

    def test_request_is_privately_reconstructed_before_callbacks(self):
        host,binding=self.fixture();capture=binding.capture();item=request(capture);commitment=item.input_commitment
        host.on_member=lambda:object.__setattr__(item,'request_id','effect:mutated-later')
        args=binding.driver_arguments(capture,item)
        self.assertEqual(args.request_commitment,commitment)
        self.assertNotEqual(args.request_commitment,item.input_commitment)

    def test_original_driver_timestamp_and_policy_cannot_be_replaced_through_arguments(self):
        host,binding=self.fixture();capture=binding.capture();item=request(capture)
        args=binding.driver_arguments(capture,item)
        object.__setattr__(args.expected.limit,'value',8)
        object.__setattr__(args.identity,'pid',99)
        next_args=binding.driver_arguments(capture,item)
        self.assertEqual(next_args.expected.limit,CpuRateLimit(0,0));self.assertEqual(next_args.identity.pid,42)

    def test_policy_or_version_change_rejects_old_capture_and_allows_fresh_observation(self):
        for field,value in (('_cpu_version',1),('_cpu_policy',CpuRateLimit(0,7))):
            with self.subTest(field=field):
                host,binding=self.fixture();capture=binding.capture();item=request(capture)
                setattr(host.target,field,value)
                with self.assertRaisesRegex(ContractError,'POLICY_CHANGED'):binding.require_current(capture,item)
                fresh=binding.capture();self.assertEqual(fresh.observation.limit,host.target._cpu_policy)

    def test_unavailable_policy_never_becomes_measured_zero(self):
        host,binding=self.fixture();host.unavailable=True
        with self.assertRaisesRegex(ContractError,'POLICY_UNAVAILABLE'):binding.capture()
        self.assertIsNone(binding._current)

    def test_future_driver_timestamp_outside_real_bracket_is_rejected(self):
        host,binding=self.fixture();host.driver_stamp_delta=10_000_000
        with self.assertRaisesRegex(ContractError,'TIMESTAMP_OUTSIDE_BRACKET'):binding.capture()

    def test_driver_rollback_latches_after_time_recovers(self):
        host,binding=self.fixture();capture=binding.capture();item=request(capture)
        original=binding._driver_now;binding._driver_now=lambda:binding._last_driver-1
        with self.assertRaisesRegex(ContractError,'CLOCK_ROLLBACK'):binding.require_current(capture,item)
        binding._driver_now=original
        with self.assertRaisesRegex(ContractError,'CLOCK_ROLLBACK'):binding.capture()

    def test_elapsed_rollback_latches(self):
        host,binding=self.fixture();binding.capture();binding._elapsed_now=lambda:binding._last_elapsed-1
        with self.assertRaisesRegex(ContractError,'CLOCK_ROLLBACK'):binding.capture()

    def test_stale_native_capture_is_denied(self):
        host,binding=self.fixture();capture=binding.capture();item=request(capture,age=100_000_000)
        host.advance(200_000_000)
        with self.assertRaisesRegex(ContractError,'CAPTURE_STALE'):binding.require_current(capture,item)

    def test_expired_monotonic_or_wall_deadline_is_denied(self):
        host,binding=self.fixture();capture=binding.capture();item=request(capture,lifetime=100_000_000)
        host.advance(200_000_000)
        with self.assertRaisesRegex(ContractError,'DEADLINE_EXPIRED'):binding.require_current(capture,item)

    def test_insufficient_duration_or_remaining_deadline_is_not_rounded_up(self):
        host,binding=self.fixture();capture=binding.capture()
        with self.assertRaisesRegex(ContractError,'TRANSLATION_UNAVAILABLE'):
            binding.driver_arguments(capture,request(capture,duration=1))

    def test_overlong_observation_rejects_accepted_output_without_preemption_claim(self):
        host,binding=self.fixture(maximum_capture_ns=1_000_000)
        host.on_query=lambda:host.advance(2_000_000)
        with self.assertRaisesRegex(ContractError,'OBSERVATION_TOO_SLOW'):binding.capture()

    def test_native_clock_error_latches_and_keeps_exact_primary(self):
        host,binding=self.fixture();primary=OSError('controlled unavailable')
        host.clock.clock=lambda:(_ for _ in ()).throw(primary)
        with self.assertRaises(OSError) as caught:binding.capture()
        self.assertIs(caught.exception,primary)
        with self.assertRaisesRegex(ContractError,'NATIVE_CLOCK_UNAVAILABLE'):binding.capture()

    def test_clock_control_exception_is_not_replaced_by_binding_cleanup(self):
        for primary in (KeyboardInterrupt(),SystemExit(4)):
            with self.subTest(primary=type(primary).__name__):
                host,binding=self.fixture();host.clock.clock=lambda:(_ for _ in ()).throw(primary)
                with self.assertRaises(type(primary)) as caught:binding.capture()
                self.assertIs(caught.exception,primary)

    def test_boot_resume_or_untrusted_sample_is_rejected(self):
        for changes in ({'boot_id':'boot:other'},{'resume_generation':1},{'wall_trusted':False}):
            with self.subTest(changes=changes):
                host,binding=self.fixture();capture=binding.capture();item=request(capture);original=host.clock.clock
                def changed():
                    previous,current=original();return previous,replace(current,**changes)
                host.clock.clock=changed
                with self.assertRaises(ContractError):binding.require_current(capture,item)

    def test_resume_after_last_clock_callback_is_seen_at_publication(self):
        host,binding=self.fixture();capture=binding.capture();item=request(capture)
        host.on_member=lambda:setattr(host.clock,'_resume',1)
        with self.assertRaisesRegex(ContractError,'CLOCK_SESSION_CHANGED'):binding.require_current(capture,item)

    def test_membership_or_native_handle_change_is_rejected(self):
        for callback in (lambda host:setattr(host,'member',False),lambda host:setattr(host.target,'_job',999)):
            with self.subTest(callback=repr(callback)):
                host,binding=self.fixture();capture=binding.capture();item=request(capture)
                host.on_member=lambda:callback(host)
                with self.assertRaises(ContractError):binding.require_current(capture,item)

    def test_cancellation_in_final_native_membership_callback_wins(self):
        host,binding=self.fixture();capture=binding.capture();item=request(capture)
        host.on_member=binding.cancel
        with self.assertRaisesRegex(ContractError,'CANCELLED'):binding.require_current(capture,item)

    def test_cancellation_in_final_elapsed_callback_wins(self):
        host,binding=self.fixture();capture=binding.capture();item=request(capture)
        host.on_member=lambda:setattr(host,'on_elapsed',binding.cancel)
        with self.assertRaisesRegex(ContractError,'CANCELLED'):binding.require_current(capture,item)

    def test_external_stop_in_final_callback_wins(self):
        stop=threading.Event();host,binding=self.fixture(cancel_event=stop);capture=binding.capture();item=request(capture)
        host.on_member=stop.set
        with self.assertRaisesRegex(ContractError,'CANCELLED'):binding.driver_arguments(capture,item)

    def test_close_only_local_state_and_denies_reuse(self):
        host,binding=self.fixture();capture=binding.capture();binding.close();binding.close()
        self.assertFalse(host.target._closed);self.assertEqual(host.clock._state,'ACTIVE')
        with self.assertRaisesRegex(ContractError,'CLOSED'):binding.require_current(capture,request(capture))

    def test_reentrant_failure_does_not_release_outer_busy_flag(self):
        host,binding=self.fixture();seen=[]
        def callback():
            for _ in range(2):
                with self.assertRaisesRegex(ContractError,'REENTRANT'):binding.capture()
                seen.append(binding._busy)
        host.on_query=callback;binding.capture();self.assertEqual(seen,[True,True])

    def test_concurrent_collection_is_bounded_and_stop_denies_pending_return(self):
        stop=threading.Event();host,binding=self.fixture(cancel_event=stop)
        entered,released=threading.Event(),threading.Event();out=[]
        def callback():entered.set();self.assertTrue(released.wait(3))
        host.on_query=callback
        def run():
            try:out.append(binding.capture())
            except BaseException as error:out.append(error)
        thread=threading.Thread(target=run);thread.start()
        try:
            self.assertTrue(entered.wait(3))
            with self.assertRaisesRegex(ContractError,'CPU_BINDING_BUSY'):binding.capture()
            stop.set()
        finally:released.set();thread.join(3)
        self.assertFalse(thread.is_alive());self.assertEqual(len(out),1)
        self.assertIsInstance(out[0],ContractError);self.assertEqual(out[0].code,'CPU_BINDING_CANCELLED')

    def test_unknown_clock_implementation_or_invalid_resolution_is_closed(self):
        host=ControlledHost()
        with patch.object(module.time,'get_clock_info',lambda name:SimpleNamespace(
            implementation='unqualified',monotonic=True,adjustable=False,resolution=.001)):
            with self.assertRaisesRegex(ContractError,'DOMAIN_UNQUALIFIED'):module.NativeCpuBinding(host.target,host.clock)
        for value in (float('nan'),0,True):
            info=host.clock_info('monotonic');info.resolution=value
            with self.subTest(value=value),patch.object(module.time,'get_clock_info',
                lambda name:info if name=='monotonic' else host.clock_info(name)):
                with self.assertRaisesRegex(ContractError,'RESOLUTION_UNAVAILABLE'):module.NativeCpuBinding(host.target,host.clock)


@unittest.skipUnless(os.name=='nt','Actual Windows host required')
class NativeCpuBindingWindowsTests(unittest.TestCase):
    def setUp(self):
        import test_windows_jobs as jobs
        self.fixture=jobs.WindowsJobTests();self.fixture.setUp()
        self.clock=None;self.bindings=[];self.cpu_writes=[];self.query_records=[]
        self.addCleanup(self.retire)
        self.owned,self.release,_=self.fixture.simple()
        original=self.owned._api.SetInformationJobObject
        def no_cpu_write(job,kind,*args):
            if kind==15:self.cpu_writes.append(kind);raise AssertionError('CPU policy write forbidden')
            self.assertEqual(kind,9);return original(job,kind,*args)
        self.owned._api.SetInformationJobObject=no_cpu_write
        self.clock=NativeSessionClock(1)

    def retire(self):
        for binding in self.bindings:binding.close()
        if self.clock:self.clock.close()
        self.fixture.tearDown()
        receipt=dict(test_id=self.id(),worker_pid=self.owned.pid,creation_time=self.owned.creation_time,
            worker_closed=self.owned.lifetime_closed,process_closed=self.owned._process is None,
            job_closed=self.owned._job is None,thread_closed=self.owned._thread is None,
            clock_status=None if self.clock is None else self.clock.status().state,
            clock_sampler_alive=False if self.clock is None else self.clock.status().sampler_alive,
            class15_write_calls=self.cpu_writes,observations=self.query_records,
            authority='CONTROLLED epoch1 for native metrology; no canonical enrollment/grant/effect authority.')
        NATIVE_RECEIPTS.append(receipt)
        self.assertFalse(self.cpu_writes)

    def binding(self,**kwargs):
        binding=module.NativeCpuBinding(self.owned,self.clock,maximum_capture_ns=500_000_000,**kwargs)
        self.bindings.append(binding);return binding

    def test_actual_policy_capture_and_conservative_original_driver_arguments(self):
        binding=self.binding();capture=binding.capture();item=request(capture)
        arguments=binding.driver_arguments(capture,item)
        self.assertNotEqual(capture.native_domain,capture.driver_domain)
        self.assertEqual(arguments.expected.observed_monotonic_ns,capture.original_driver_timestamp_ns)
        self.assertEqual(arguments.expected.limit,capture.observation.limit)
        self.assertIsNone(binding.require_current(capture,item))
        with self.owned._lock:
            started=self.owned._cpu_now()
            observed=self.owned._cpu_expected(arguments.identity,arguments.expected,started,
                arguments.maximum_age_ns,arguments.maximum_duration_ns,arguments.deadline_monotonic_ns)
        self.assertEqual(observed.limit,capture.observation.limit)
        self.query_records.append(dict(native_timestamp=capture.observation.observed_monotonic_ns,
            original_driver_timestamp=arguments.expected.observed_monotonic_ns,
            actual_limit=[observed.limit.control_flags,observed.limit.value],native_clock_boot=capture.native_after.boot_id,
            driver_deadline=arguments.deadline_monotonic_ns,driver_age=arguments.maximum_age_ns,
            driver_duration=arguments.maximum_duration_ns,policy_version=observed.version))

    def test_actual_final_driver_fence_checks_same_capture_then_vetoes_every_set(self):
        binding=self.binding();capture=binding.capture();item=request(capture)
        arguments=binding.driver_arguments(capture,item);seen=[]
        version=self.owned._cpu_version
        def fence():
            seen.append((capture,item));binding.require_current(capture,item)
            raise ContractError('CPU_BINDING_OBSERVATION_ONLY_VETO')
        with self.assertRaisesRegex(ContractError,'OBSERVATION_ONLY_VETO'):
            self.owned.apply_cpu_rate_limit('cpb:never-dispatch',arguments.identity,arguments.expected,item.target_limit,
                **arguments.keyword_arguments,dispatch_fence=fence)
        self.assertEqual(seen,[(capture,item)]);self.assertEqual(self.owned._cpu_version,version)
        self.assertFalse(self.cpu_writes)

    def test_actual_stop_in_driver_fence_denies_before_policy_write(self):
        stop=threading.Event();binding=self.binding(cancel_event=stop);capture=binding.capture();item=request(capture)
        arguments=binding.driver_arguments(capture,item);version=self.owned._cpu_version
        def fence():stop.set();return binding.require_current(capture,item)
        with self.assertRaisesRegex(ContractError,'CPU_BINDING_CANCELLED'):
            self.owned.apply_cpu_rate_limit('cpb:stop-before-dispatch',arguments.identity,arguments.expected,item.target_limit,
                **arguments.keyword_arguments,dispatch_fence=fence)
        self.assertEqual(self.owned._cpu_version,version);self.assertFalse(self.cpu_writes)

    def test_actual_delayed_policy_query_rejects_overlong_bound(self):
        binding=self.binding();original=self.owned._api.QueryInformationJobObject
        def delayed(*args):
            result=original(*args)
            if args[1]==15:time.sleep(.03)
            return result
        binding._maximum=5_000_000
        with patch.object(self.owned._api,'QueryInformationJobObject',delayed):
            with self.assertRaises(ContractError):binding.capture()

    def test_actual_clock_notification_invalidation_is_controlled_and_latched(self):
        binding=self.binding();capture=binding.capture();item=request(capture)
        self.clock._on_power(None,18,None)  # Controlled callback invocation, not actual host resume.
        with self.assertRaises(ContractError):binding.require_current(capture,item)
        self.assertEqual(self.clock.status().state,'LATCHED')

    def test_actual_exited_owned_lifetime_and_local_close_do_not_reopen_pid(self):
        binding=self.binding();capture=binding.capture();item=request(capture)
        self.release.signal();self.assertTrue(self.owned.wait(5))
        with self.assertRaises(ContractError):binding.require_current(capture,item)
        binding.close();self.assertEqual(self.clock.status().state,'ACTIVE')


if __name__=='__main__':unittest.main()
