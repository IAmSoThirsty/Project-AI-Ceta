"""Pressure lifecycle/recovery and real native consumer qualification.

Synthetic clocks/records/policies are explicit controls. No new reservation
owner, principal authentication, queue/thermal source or workload is created.
Native tests use only fresh disposable T: children and ordinary host queries.
"""
from dataclasses import replace
from pathlib import Path
import hashlib
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from ceta.contracts.resource_management import (AdmissionState,BudgetEnvelope,CapacitySnapshot,ObservationState,PressureLevel,
    QuantityObservation,ResourceKind,ResourceVector)
from ceta.contracts.wire import ContractError
from ceta.resource.pressure import ResourcePressureDetector,PressureThresholds
from ceta.resource.hardware import SamplingPolicy,StorageCapacityMonitor,WindowsComputeAvailabilityMonitor,WindowsHardwareProfiler
from ceta.resource.admission import AdmissionRequest,WorkloadAdmissionController,WorkloadEstimate

NATIVE_OBSERVATIONS=[]

def frame(sequence,at,value=400,*,kind=ResourceKind.CPU,method='pressure-test-control'):
    def q(amount):return QuantityObservation(ObservationState.MEASURED,amount,at,method)
    return CapacitySnapshot(kind,q(1000),q(500),q(400),q(value),sequence)

class PressureLifecycleTests(unittest.TestCase):
    def error_code(self,code,call):
        with self.assertRaises(ContractError) as raised:call()
        self.assertEqual(raised.exception.code,code)

    def test_threshold_policy_shape_rejected_before_clock(self):
        calls=[]
        for policy in (None,{},'untrusted',object()):
            self.error_code('RESOURCE_PRESSURE_THRESHOLDS_INVALID',lambda:ResourcePressureDetector(policy,clock=lambda:calls.append(1) or 100))
        forged=PressureThresholds();object.__setattr__(forged,'recovery_samples',0)
        self.error_code('RESOURCE_PRESSURE_THRESHOLDS_INVALID',lambda:ResourcePressureDetector(forged,clock=lambda:calls.append(1) or 100))
        self.assertEqual(calls,[])

    def test_nested_shape_bounds_revalidated_before_clock(self):
        calls=[];detector=ResourcePressureDetector(clock=lambda:calls.append(1) or 100)
        changes=[('total','observed_monotonic_ns',-1,'RESOURCE_OBSERVATION_TIME_INVALID'),
                 ('free','value',True,'RESOURCE_MEASUREMENT_INVALID'),
                 ('reservable','method','', 'RESOURCE_OBSERVATION_METHOD_INVALID'),
                 ('utilization_milli','state','MEASURED','RESOURCE_OBSERVATION_STATE_INVALID')]
        for member,field,value,code in changes:
            bad=frame(1,90);object.__setattr__(getattr(bad,member),field,value)
            self.error_code(code,lambda:detector.observe(bad,current=True))
        self.assertEqual(calls,[])

    def test_clock_invalid_type_negative_and_overflow_close_uncertainty(self):
        for value in (-1,True,'100',2**63):
            now=[100];detector=ResourcePressureDetector(clock=lambda:now[0]);first=frame(1,90)
            self.assertTrue(detector.observe(first,current=True).admission_open)
            now[0]=value;self.error_code('RESOURCE_PRESSURE_CLOCK_INVALID',lambda:detector.observe(frame(2,91),current=True))
            now[0]=101
            cached=detector.observe(first,current=True)
            self.assertEqual((cached.level,cached.admission_open,cached.recovery_samples_remaining),(PressureLevel.UNKNOWN,False,3))
            fresh=detector.observe(frame(3,92),current=True)
            self.assertEqual((fresh.reason,fresh.recovery_samples_remaining),('RECOVERY_HYSTERESIS',2))

    def test_clock_oserror_preserves_primary_and_prior_replay_bounds(self):
        fault=[False];primary=OSError('controlled clock failure')
        def clock():
            if fault[0]:raise primary
            return 100
        detector=ResourcePressureDetector(clock=clock);first=frame(10,90)
        detector.observe(first,current=True);fault[0]=True
        with self.assertRaises(OSError) as caught:detector.observe(frame(11,91),current=True)
        self.assertIs(caught.exception,primary);fault[0]=False
        self.assertFalse(detector.observe(first,current=True).admission_open)
        old=detector.observe(frame(9,89),current=True)
        self.assertEqual(old.reason,'OBSERVATION_ORDER_INVALID')
        for sequence in (12,13):self.assertFalse(detector.observe(frame(sequence,sequence+80),current=True).admission_open)
        self.assertTrue(detector.observe(frame(14,94),current=True).admission_open)

    def test_clock_interruption_releases_lock_and_requires_fresh_recovery(self):
        fault=[None]
        def clock():
            if fault[0] is not None:raise fault[0]
            return 100
        for primary in (KeyboardInterrupt('controlled cancellation'),SystemExit('controlled stop')):
            detector=ResourcePressureDetector(clock=clock);first=frame(1,90);detector.observe(first,current=True)
            fault[0]=primary
            with self.assertRaises(type(primary)) as caught:detector.observe(frame(2,91),current=True)
            self.assertIs(caught.exception,primary);fault[0]=None
            results=[];thread=threading.Thread(target=lambda:results.append(detector.observe(first,current=True)))
            thread.start();thread.join(2);self.assertFalse(thread.is_alive())
            self.assertFalse(results[0].admission_open)
            for seq in (2,3):self.assertFalse(detector.observe(frame(seq,89+seq),current=True).admission_open)
            self.assertTrue(detector.observe(frame(4,93),current=True).admission_open)

    def test_critical_severity_latches_across_threshold_jitter(self):
        detector=ResourcePressureDetector(clock=lambda:1000)
        values=[950,850,930,801,799,651,850]
        decisions=[detector.observe(frame(seq,seq,amount),current=True) for seq,amount in enumerate(values,1)]
        self.assertTrue(all(item.level is PressureLevel.CRITICAL and not item.admission_open for item in decisions))
        self.assertEqual(decisions[1].reason,'CRITICAL_HYSTERESIS')
        for seq in (8,9):self.assertFalse(detector.observe(frame(seq,seq,650),current=True).admission_open)
        recovered=detector.observe(frame(10,10,650),current=True)
        self.assertEqual((recovered.level,recovered.reason),(PressureLevel.NORMAL,'RECOVERED_AFTER_HYSTERESIS'))

    def test_elevated_can_escalate_and_critical_recovery_is_not_shortened(self):
        detector=ResourcePressureDetector(PressureThresholds(800,925,650,3),clock=lambda:100)
        self.assertEqual(detector.observe(frame(1,90,800),current=True).level,PressureLevel.ELEVATED)
        self.assertEqual(detector.observe(frame(2,91,925),current=True).level,PressureLevel.CRITICAL)
        self.assertEqual(detector.observe(frame(3,92,0),current=True).recovery_samples_remaining,2)
        held=detector.observe(frame(4,93,800),current=True)
        self.assertEqual((held.level,held.recovery_samples_remaining),(PressureLevel.CRITICAL,3))
        for seq in (5,6):self.assertFalse(detector.observe(frame(seq,89+seq,0),current=True).admission_open)
        self.assertTrue(detector.observe(frame(7,96,0),current=True).admission_open)

    def test_single_stale_frame_does_not_reopen_with_duplicate_relabel(self):
        now=[100];detector=ResourcePressureDetector(clock=lambda:now[0],maximum_observation_age_ns=10)
        first=frame(1,100,0);self.assertTrue(detector.observe(first,current=True).admission_open)
        now[0]=111;self.assertFalse(detector.observe(first,current=True).admission_open)
        now[0]=112
        for _ in range(20):self.assertFalse(detector.observe(first,current=True).admission_open)
        for seq in (2,3):
            now[0]=110+seq;self.assertFalse(detector.observe(frame(seq,now[0],0),current=True).admission_open)
        now[0]=114;self.assertTrue(detector.observe(frame(4,114,0),current=True).admission_open)

    def test_future_rejection_cannot_count_after_clock_catches_up(self):
        now=[100];detector=ResourcePressureDetector(clock=lambda:now[0]);future=frame(1,110,0)
        self.assertFalse(detector.observe(future,current=True).admission_open)
        now[0]=110
        self.assertEqual(detector.observe(future,current=True).reason,'DUPLICATE_OBSERVATION')
        for seq in (2,3):
            now[0]=109+seq;self.assertFalse(detector.observe(frame(seq,now[0],0),current=True).admission_open)
        now[0]=113;self.assertTrue(detector.observe(frame(4,113,0),current=True).admission_open)

    def test_kind_method_and_sequence_source_changes_close_without_reset(self):
        for changed in (frame(2,91,0,kind=ResourceKind.STORAGE),frame(2,91,0,method='replacement'),frame(1,91,0)):
            detector=ResourcePressureDetector(clock=lambda:100);detector.observe(frame(1,90,0),current=True)
            self.assertFalse(detector.observe(changed,current=True).admission_open)
            self.assertFalse(detector.observe(frame(1,90,0),current=True).admission_open)
            self.assertEqual(detector.observe(frame(2,92,0),current=True).recovery_samples_remaining,2)

    def test_current_false_invalidates_previous_allow_and_duplicate_recovery(self):
        detector=ResourcePressureDetector(clock=lambda:100);first=frame(1,90,0)
        self.assertTrue(detector.observe(first,current=True).admission_open)
        self.assertFalse(detector.observe(first,current=False).admission_open)
        self.assertFalse(detector.observe(first,current=True).admission_open)
        self.assertEqual(detector.observe(frame(2,91,0),current=True).recovery_samples_remaining,2)

    def test_measurement_zero_is_valid_and_unavailable_never_zero(self):
        detector=ResourcePressureDetector(clock=lambda:100)
        zero=detector.observe(frame(1,90,0),current=True)
        self.assertEqual((zero.observed_milli,zero.level,zero.admission_open),(0,PressureLevel.NORMAL,True))
        unknown=QuantityObservation(ObservationState.UNAVAILABLE,None,91,'pressure-test-control','NOT_OBSERVED')
        absent=replace(frame(2,91),utilization_milli=unknown)
        decision=detector.observe(absent,current=True)
        self.assertEqual((decision.observed_milli,decision.level,decision.admission_open),(None,PressureLevel.UNKNOWN,False))

    def test_reason_output_does_not_echo_private_source_labels(self):
        label='restricted-context-label';detector=ResourcePressureDetector(clock=lambda:100)
        unknown=QuantityObservation(ObservationState.UNAVAILABLE,None,90,label,'restricted-observer-detail')
        sample=replace(frame(1,90,method=label),utilization_milli=unknown)
        decision=detector.observe(sample,current=True)
        self.assertNotIn(label,repr(decision));self.assertNotIn('restricted-observer-detail',repr(decision))
        self.assertEqual(decision.reason,'OBSERVATION_UNAVAILABLE_OR_STALE')

    def test_concurrent_critical_elevated_frames_never_downgrade_latched_severity(self):
        detector=ResourcePressureDetector(clock=lambda:1000);detector.observe(frame(1,1,950),current=True)
        barrier=threading.Barrier(16);results=[];failures=[]
        def call():
            try:barrier.wait(2);results.append(detector.observe(frame(2,2,850),current=True))
            except BaseException as error:failures.append(type(error).__name__)
        threads=[threading.Thread(target=call) for _ in range(16)]
        for thread in threads:thread.start()
        for thread in threads:thread.join(3)
        self.assertFalse(any(thread.is_alive() for thread in threads));self.assertEqual(failures,[])
        self.assertEqual(len(results),16);self.assertTrue(all(item.level is PressureLevel.CRITICAL for item in results))
        self.assertTrue(all(item.recovery_samples_remaining==3 and not item.admission_open for item in results))

    def test_constant_size_replay_state_after_many_ordered_frames(self):
        detector=ResourcePressureDetector(clock=lambda:10000);fields=set(vars(detector));before=time.perf_counter_ns()
        for seq in range(1,1001):detector.observe(frame(seq,seq,0),current=True)
        elapsed=time.perf_counter_ns()-before
        self.assertEqual(set(vars(detector)),fields)
        self.assertEqual(sum(type(value) is CapacitySnapshot for value in vars(detector).values()),2)
        self.assertFalse(any(type(value) in (list,dict,set) for value in vars(detector).values()))
        self.assertGreaterEqual(elapsed,0)  # measured local duration; no fabricated hard latency guarantee

class NativePressureLifecycleTests(unittest.TestCase):
    def fixture(self):
        self.assertEqual(os.name,'nt');directory=ROOT/'.agents/fixtures';directory.mkdir(parents=True,exist_ok=True)
        return tempfile.TemporaryDirectory(prefix='rp1-native-',dir=directory)

    def wait_fresh(self,snapshot,policy):
        started=time.perf_counter_ns();deadline=time.perf_counter()+1
        # The native sampler also fences cache interval with high-resolution
        # QPC. A GetTickCount64 tick can advance before this actual interval.
        while (time.monotonic_ns()-snapshot.total.observed_monotonic_ns<policy.minimum_interval_ns
               or time.perf_counter_ns()-started<policy.minimum_interval_ns):
            self.assertLess(time.perf_counter(),deadline);time.sleep(.002)

    def denied_owner(self):
        class NoDispatchControl:
            calls=0
            def reserve(port,request):port.calls+=1;raise AssertionError('no concrete canonical reservation owner is supplied')
        return NoDispatchControl()

    def native_admission(self,snapshot,decision,current=True):
        port=self.denied_owner();controller=WorkloadAdmissionController(port);zero=ResourceVector(0,0,0,0)
        budget=BudgetEnvelope('budget.rp1',zero,zero,zero,zero,0)
        estimate=WorkloadEstimate('workload.rp1',None,0,'explicit-unresolved-native-test',state='UNRESOLVED',confidence_milli=0,
                                  reason_code='CANONICAL_PROFILE_NOT_AVAILABLE')
        result=controller.admit(AdmissionRequest('request.rp1',budget,estimate,snapshot.sequence,snapshot.total.observed_monotonic_ns,current,decision.level))
        self.assertEqual(port.calls,0);self.assertNotEqual(result.state,AdmissionState.ADMITTED)
        return result

    def test_native_storage_stable_pressure_uses_actual_reads_and_admission_block(self):
        with self.fixture() as folder:
            path=Path(folder);payload=path/'owned-pressure.bin';payload.write_bytes(b'ceta-rp1\0'*8192)
            sha=hashlib.sha256(payload.read_bytes()).hexdigest()
            policy=SamplingPolicy(minimum_interval_ns=1_000_000,control_storage_bytes=4096)
            monitor=StorageCapacityMonitor(path=path,policy=policy)
            # Explicit low fixture thresholds classify existing measured use;
            # this does not claim the host is unsafe under production thresholds.
            detector=ResourcePressureDetector(PressureThresholds(1,2,0,3));observations=[]
            for _ in range(3):
                sample=monitor.sample();self.assertTrue(sample.utilization_milli.measured)
                decision=detector.observe(sample,current=True);result=self.native_admission(sample,decision)
                observations.append({'sequence':sample.sequence,'observed_ns':sample.total.observed_monotonic_ns,'utilization_milli':sample.utilization_milli.value,
                                     'pressure':decision.level.value,'admission':result.state.value,'reason_codes':result.reason_codes})
                self.wait_fresh(sample,policy)
            self.assertEqual(len({row['sequence'] for row in observations}),3)
            self.assertTrue(all(row['pressure']=='CRITICAL' for row in observations))
            self.assertEqual(hashlib.sha256(payload.read_bytes()).hexdigest(),sha)
            NATIVE_OBSERVATIONS.append({'test_id':self.id(),'fixture_path':str(path),'fixture_sha256':sha,'method':'python:shutil.disk_usage',
                 'thresholds':{'elevated':1,'critical':2,'recover':0},'observations':observations,'positive_authority_integration':False})
        self.assertFalse(path.exists());NATIVE_OBSERVATIONS[-1]['owned_fixture_removed']=True

    def test_native_normal_storage_cannot_dispatch_without_canonical_profile(self):
        with self.fixture() as folder:
            path=Path(folder);sample=StorageCapacityMonitor(path=path).sample();decision=ResourcePressureDetector().observe(sample,current=True)
            result=self.native_admission(sample,decision)
            self.assertEqual(result.state,AdmissionState.UNCERTAIN if decision.level is PressureLevel.NORMAL else AdmissionState.BLOCKED)
            NATIVE_OBSERVATIONS.append({'test_id':self.id(),'fixture_path':str(path),'method':sample.total.method,
                'pressure':decision.level.value,'admission':result.state.value,'reason_codes':result.reason_codes,'owner_dispatches':0})
        self.assertFalse(path.exists());NATIVE_OBSERVATIONS[-1]['owned_fixture_removed']=True

    def test_native_delayed_storage_recovery_keeps_stale_samples_out_of_gate(self):
        with self.fixture() as folder:
            path=Path(folder);delayed=[True]
            def read(target):
                usage=shutil.disk_usage(target)
                if delayed[0]:time.sleep(.04)
                return usage
            policy=SamplingPolicy(maximum_age_ns=200_000_000,minimum_interval_ns=1_000_000,maximum_probe_window_ns=10_000_000)
            monitor=StorageCapacityMonitor(path=path,policy=policy,disk_usage=read)
            detector=ResourcePressureDetector();late=monitor.sample();rejected=detector.observe(late,current=True)
            self.assertFalse(rejected.admission_open);self.assertIsNone(rejected.observed_milli)
            self.assertEqual(late.free.reason,'RESOURCE_PROBE_WINDOW_EXCEEDED');delayed[0]=False
            decisions=[]
            for _ in range(3):
                self.wait_fresh(late,policy);fresh=monitor.sample();decision=detector.observe(fresh,current=True);decisions.append(decision)
                self.assertGreater(fresh.sequence,late.sequence);late=fresh
            if late.utilization_milli.value<800:
                self.assertEqual([row.recovery_samples_remaining for row in decisions],[2,1,0]);self.assertTrue(decisions[-1].admission_open)
            else:self.assertTrue(all(not row.admission_open for row in decisions))
            self.native_admission(late,decisions[-1])
            NATIVE_OBSERVATIONS.append({'test_id':self.id(),'fixture_path':str(path),'method':'python:shutil.disk_usage','injected_delay_ns':40_000_000,
                'first_unknown':rejected.level.value,'recovery_levels':[row.level.value for row in decisions],
                'actual_latest_utilization_milli':late.utilization_milli.value,'positive_owner_integration':False})
        self.assertFalse(path.exists());NATIVE_OBSERVATIONS[-1]['owned_fixture_removed']=True

    def test_native_memory_profile_pressure_and_unresolved_admission(self):
        with self.fixture() as folder:
            path=Path(folder);profile=WindowsHardwareProfiler(storage_path=path).profile('profile.rp1.native')
            sample=profile.memory;decision=ResourcePressureDetector().observe(sample,current=True)
            result=self.native_admission(sample,decision,current=sample.utilization_milli.measured)
            self.assertEqual(sample.total.method,'windows:GlobalMemoryStatusEx')
            self.assertEqual(decision.observed_milli,sample.utilization_milli.value)
            NATIVE_OBSERVATIONS.append({'test_id':self.id(),'fixture_path':str(path),'method':sample.total.method,
                'total_measured':sample.total.measured,'utilization_measured':sample.utilization_milli.measured,
                'pressure':decision.level.value,'admission':result.state.value,'owner_dispatches':0})
        self.assertFalse(path.exists());NATIVE_OBSERVATIONS[-1]['owned_fixture_removed']=True

    def test_native_cpu_baseline_cached_and_measured_pressure_consumer(self):
        policy=SamplingPolicy(minimum_interval_ns=10_000_000,maximum_probe_window_ns=500_000_000)
        monitor=WindowsComputeAvailabilityMonitor(policy=policy);detector=ResourcePressureDetector();first=monitor.sample()
        self.assertFalse(detector.observe(first,current=True).admission_open);measured=[];all_frames=[]
        scope=WindowsComputeAvailabilityMonitor._native_processor_scope()
        if scope is None or scope[1]!=os.cpu_count():
            self.assertEqual(first.free.reason,'CPU_PROCESSOR_GROUP_SCOPE_UNAVAILABLE')
            self.native_admission(first,detector.observe(first,current=True),current=False)
        else:
            self.assertEqual(first.free.reason,'CPU_BASELINE_REQUIRED')
            for _ in range(4):
                self.wait_fresh(first,policy);sample=monitor.sample();decision=detector.observe(sample,current=True)
                self.native_admission(sample,decision,current=sample.utilization_milli.measured)
                all_frames.append({'sequence':sample.sequence,'observed_ns':sample.total.observed_monotonic_ns,
                                   'measured':sample.utilization_milli.measured,'reason':sample.free.reason,'pressure':decision.level.value})
                if sample.utilization_milli.measured:measured.append({'sequence':sample.sequence,'utilization_milli':sample.utilization_milli.value,'pressure':decision.level.value})
                first=sample
        NATIVE_OBSERVATIONS.append({'test_id':self.id(),'method':'windows:GetSystemTimes','processor_scope':scope,'measured_frames':measured,
            'all_frames':all_frames,'unavailable_reason':first.free.reason,'owner_dispatches':0,'actual_clock_or_principal_authentication':False})
        if scope is not None and scope[1]==os.cpu_count():self.assertTrue(measured)

if __name__=='__main__':unittest.main(verbosity=2)
