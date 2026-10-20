"""Exact process rate/window logic and real disposable repeatable Windows work."""
from dataclasses import asdict,replace
import hashlib,json,math,sys,threading,time,unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from ceta.contracts.resource_management import (ObservationState,QuantityObservation,ProcessUsageMeasurements,
    TelemetrySourceBinding,TelemetrySample,MAX_OBSERVATION_AGE_NS)
from ceta.contracts.wire import ContractError
from ceta.resource.diagnostics import (CurrentComparisonContext,WorkloadComparisonInput,PerformanceEnvelope,
    PerformanceDiagnostics,OwnedProcessTelemetrySampler,ResourceTelemetryRecorder,ProcessRateMeasurement,ProcessRateChange)
import test_windows_jobs as jobs

def digest(value):return 'sha256:'+hashlib.sha256(value.encode()).hexdigest()
SCOPE,ENV,SOURCE,WORKLOAD=(digest(name) for name in ('perf-scope','perf-environment','perf-source','perf-workload'))
def measured(value,at,method='fixture'):return QuantityObservation(ObservationState.MEASURED,value,at,method)
def unknown(at,method='fixture',reason='NOT_OBSERVED'):return QuantityObservation(ObservationState.UNAVAILABLE,None,at,method,reason)
def frame(sequence,at,*,cpu=0,read=0,write=0,memory=1024,private=512,source=SOURCE,generation=3,workload=WORKLOAD):
    return TelemetrySample('sample:'+str(sequence),SCOPE,ENV,at,unknown(at),measured(memory,at),unknown(at),unknown(at),
        TelemetrySourceBinding(source,generation,sequence,workload),
        ProcessUsageMeasurements(at,measured(cpu,at),measured(private,at),measured(read,at),measured(write,at)))
def fixture():
    comparison=WorkloadComparisonInput('private-workload-label',WORKLOAD,
        (frame(1,1_000_000_000,cpu=100,read=20,write=10),frame(2,2_000_000_000,cpu=10_000_100,read=1020,write=510,memory=2048)),
        (frame(3,3_000_000_000,cpu=20_000_000,read=2000,write=1000),frame(4,4_000_000_000,cpu=40_000_000,read=4000,write=1000,private=1024)))
    context=CurrentComparisonContext(4_000_000_000,5_000_000_000,SCOPE,ENV,SOURCE,3,
        1_000_000_000,2_000_000_000,3_000_000_000,4_000_000_000)
    return comparison,context

class ProcessPerformanceComparisonTests(unittest.TestCase):
    def compare(self,comparison=None,context=None,**options):
        default,expected=fixture()
        return PerformanceDiagnostics().compare_process_current(comparison or default,PerformanceEnvelope(10,1000,4096),
            context=context or expected,timestamp_uncertainty_ns=options.pop('uncertainty',0),**options)

    def reject(self,comparison=None,context=None,code=None):
        result=self.compare(comparison,context)
        self.assertEqual(result.state,'PROCESS_COMPARISON_REJECTED')
        self.assertTrue(all(metric.total is None and metric.estimated_rate is None for side in (result.baseline,result.candidate) for metric in side.measurements))
        if code is not None:self.assertIn(code,result.findings)
        return result

    def test_exact_cpu_and_io_units_before_after_and_zero_write(self):
        result=self.compare()
        self.assertEqual(result.state,'MEASURED_PROCESS_COUNTER_COMPARISON')
        self.assertEqual([item.total for item in result.baseline.measurements],[10_000_000,1000,500])
        self.assertEqual([item.estimated_rate for item in result.baseline.measurements],[1000,1000,500])
        self.assertEqual([item.estimated_rate for item in result.candidate.measurements],[2000,2000,0])
        self.assertEqual([item.state for item in result.rate_changes],['INCREASED_BEYOND_BOUNDS','INCREASED_BEYOND_BOUNDS','DECREASED_BEYOND_BOUNDS'])
        self.assertEqual(result.candidate.measurements[2].state,'MEASURED')
        self.assertEqual(result.baseline.peak_working_set_bytes,2048)
        self.assertEqual(result.candidate.peak_private_bytes,1024)

    def test_declared_uncertainty_widens_integer_bounds(self):
        result=self.compare(uncertainty=100_000_000)
        value=result.baseline.measurements[0]
        self.assertEqual((value.minimum_rate,value.estimated_rate,value.maximum_rate),(833,1000,1250))
        self.assertEqual(result.timestamp_uncertainty_ns,100_000_000)

    def test_short_window_retains_totals_with_unavailable_rates(self):
        result=self.compare(uncertainty=500_000_000)
        self.assertEqual(result.state,'INCOMPLETE_PROCESS_COUNTER_COMPARISON')
        self.assertEqual(result.baseline.measurements[0].total,10_000_000)
        self.assertIsNone(result.baseline.measurements[0].estimated_rate)
        self.assertEqual(result.baseline.measurements[0].state,'MEASURED_TOTAL_RATE_UNAVAILABLE')
        self.assertIn('PROCESS_WINDOW_TOO_SHORT_FOR_RATE',result.findings)

    def test_rate_bounds_include_both_counter_probe_windows(self):
        comparison,context=fixture();a,b=comparison.baseline
        a=replace(a,process_usage=replace(a.process_usage,window_started_monotonic_ns=900_000_000))
        b=replace(b,process_usage=replace(b.process_usage,window_started_monotonic_ns=1_800_000_000))
        result=self.compare(replace(comparison,baseline=(a,b)),replace(context,baseline_start_ns=900_000_000))
        self.assertEqual((result.baseline.measurements[0].minimum_rate,result.baseline.measurements[0].estimated_rate,
                          result.baseline.measurements[0].maximum_rate),(909,1000,1250))

    def test_overlapping_counter_probe_windows_keep_rates_unavailable(self):
        comparison,context=fixture();a,b=comparison.baseline
        b=replace(b,process_usage=replace(b.process_usage,window_started_monotonic_ns=900_000_000))
        result=self.compare(replace(comparison,baseline=(a,b)),replace(context,baseline_start_ns=900_000_000))
        self.assertEqual(result.baseline.measurements[0].total,10_000_000)
        self.assertIsNone(result.baseline.measurements[0].maximum_rate)
        self.assertEqual(result.baseline.measurements[0].state,'MEASURED_TOTAL_RATE_UNAVAILABLE')

    def test_all_measured_zero_is_available_and_equal(self):
        comparison,context=fixture()
        sides=tuple(tuple(frame(sample.source.sequence,sample.observed_monotonic_ns) for sample in side) for side in (comparison.baseline,comparison.candidate))
        result=self.compare(replace(comparison,baseline=sides[0],candidate=sides[1]))
        self.assertTrue(all(item.state=='MEASURED' and item.total==item.estimated_rate==0 for side in (result.baseline,result.candidate) for item in side.measurements))
        self.assertTrue(all(item.state=='EQUAL' for item in result.rate_changes))

    def test_counter_unavailable_is_not_zero_and_other_metrics_survive(self):
        comparison,_=fixture();last=comparison.candidate[-1]
        changed=replace(last,process_usage=replace(last.process_usage,read_io_bytes=unknown(last.observed_monotonic_ns)))
        result=self.compare(replace(comparison,candidate=(comparison.candidate[0],changed)))
        self.assertEqual(result.state,'INCOMPLETE_PROCESS_COUNTER_COMPARISON')
        self.assertIsNone(result.candidate.measurements[1].total)
        self.assertEqual(result.candidate.measurements[0].state,'MEASURED')
        self.assertEqual(result.rate_changes[1].state,'UNAVAILABLE')

    def test_missing_private_or_working_set_is_explicit(self):
        comparison,_=fixture();last=comparison.baseline[-1]
        for key in ('memory_bytes','private_bytes'):
            with self.subTest(key=key):
                changed=(replace(last,memory_bytes=unknown(last.observed_monotonic_ns)) if key=='memory_bytes' else
                         replace(last,process_usage=replace(last.process_usage,private_bytes=unknown(last.observed_monotonic_ns))))
                result=self.compare(replace(comparison,baseline=(comparison.baseline[0],changed)))
                self.assertEqual(result.state,'INCOMPLETE_PROCESS_COUNTER_COMPARISON')
                self.assertIsNone(result.baseline.peak_working_set_bytes if key=='memory_bytes' else result.baseline.peak_private_bytes)

    def test_unavailable_middle_counter_prevents_endpoint_bridge(self):
        comparison,_=fixture();first,last=comparison.baseline
        middle=frame(2,1_500_000_000,cpu=1000,read=900,write=20)
        middle=replace(middle,process_usage=replace(middle.process_usage,cpu_time_100ns=unknown(middle.observed_monotonic_ns)))
        last=replace(last,sample_id='sample:3',source=replace(last.source,sequence=3))
        candidate=tuple(replace(sample,sample_id='sample:'+str(sample.source.sequence+1),source=replace(sample.source,sequence=sample.source.sequence+1)) for sample in comparison.candidate)
        result=self.compare(replace(comparison,baseline=(first,middle,last),candidate=candidate))
        self.assertIsNone(result.baseline.measurements[0].total)
        self.assertEqual(result.baseline.measurements[1].total,1000)

    def test_overlapping_bounds_do_not_assert_direction(self):
        result=self.compare(uncertainty=300_000_000)
        self.assertEqual(result.rate_changes[0].state,'MEASURED_BOUNDS_OVERLAP')
        self.assertLessEqual(result.rate_changes[0].minimum_difference,0)
        self.assertGreaterEqual(result.rate_changes[0].maximum_difference,0)

    def test_nonintegral_rate_uses_floor_and_ceiling(self):
        comparison,context=fixture()
        a,b=comparison.baseline
        b=replace(b,observed_monotonic_ns=a.observed_monotonic_ns+3,
            cpu_milli=unknown(a.observed_monotonic_ns+3),memory_bytes=measured(1024,a.observed_monotonic_ns+3),
            storage_bytes=unknown(a.observed_monotonic_ns+3),latency_ms=unknown(a.observed_monotonic_ns+3),
            process_usage=ProcessUsageMeasurements(a.observed_monotonic_ns+3,measured(101,a.observed_monotonic_ns+3),
                measured(512,a.observed_monotonic_ns+3),measured(21,a.observed_monotonic_ns+3),measured(11,a.observed_monotonic_ns+3)))
        result=self.compare(replace(comparison,baseline=(a,b)))
        self.assertEqual((result.baseline.measurements[1].minimum_rate,result.baseline.measurements[1].maximum_rate),(333_333_333,333_333_334))

    def test_large_bound_uses_exact_bounded_integer_arithmetic(self):
        comparison,_=fixture();last=comparison.baseline[-1]
        changed=replace(last,process_usage=replace(last.process_usage,read_io_bytes=measured(2**63-1,last.observed_monotonic_ns)))
        candidate=tuple(replace(sample,process_usage=replace(sample.process_usage,read_io_bytes=measured(2**63-1,sample.observed_monotonic_ns))) for sample in comparison.candidate)
        result=self.compare(replace(comparison,baseline=(comparison.baseline[0],changed),candidate=candidate))
        self.assertEqual(result.baseline.measurements[1].total,2**63-1-20)
        self.assertEqual(result.baseline.measurements[1].estimated_rate,2**63-1-20)

    def test_digest_binds_numeric_values_and_window(self):
        comparison,_=fixture();original=self.compare();last=comparison.candidate[-1]
        changed=replace(last,process_usage=replace(last.process_usage,write_io_bytes=measured(1001,last.observed_monotonic_ns)))
        result=self.compare(replace(comparison,candidate=(comparison.candidate[0],changed)))
        self.assertEqual(result.baseline.measurement_digest,original.baseline.measurement_digest)
        self.assertNotEqual(result.candidate.measurement_digest,original.candidate.measurement_digest)
        self.assertNotEqual(self.compare(uncertainty=1).baseline.measurement_digest,original.baseline.measurement_digest)

    def test_raw_ids_methods_and_reasons_do_not_enter_result(self):
        comparison,_=fixture();marker='private.prompt.secret.marker'
        def decorate(sample):
            return replace(sample,sample_id=marker+'.'+str(sample.source.sequence),cpu_milli=unknown(sample.observed_monotonic_ns,marker,marker),
                process_usage=replace(sample.process_usage,private_bytes=measured(sample.process_usage.private_bytes.value,sample.observed_monotonic_ns,marker)))
        changed=replace(comparison,workload_id=marker,baseline=tuple(map(decorate,comparison.baseline)),candidate=tuple(map(decorate,comparison.candidate)))
        result=self.compare(changed)
        self.assertNotIn(marker,json.dumps(asdict(result)))
        self.assertEqual(result.baseline.measurement_digest,self.compare().baseline.measurement_digest)

    def test_missing_latency_keeps_process_measurement_and_no_causal_claim(self):
        result=self.compare()
        self.assertEqual(result.state,'MEASURED_PROCESS_COUNTER_COMPARISON')
        self.assertIn('MEASURED_COUNTER_CHANGE_NOT_CAUSAL_BOTTLENECK',result.findings)
        self.assertIn('CALLER_BOUND_CONTEXT_NOT_AUTHENTICATED_SOURCE_PROOF',result.findings)
        self.assertFalse(hasattr(result,'reproducible'))

    def test_stale_and_future_context_reject_entire_result(self):
        comparison,context=fixture()
        for altered in (replace(context,now_monotonic_ns=10_000_000_000),replace(context,now_monotonic_ns=3_000_000_000)):
            self.reject(context=altered,code='COMPARISON_WINDOW_STALE_OR_FUTURE')

    def test_stale_nested_counter_cannot_hide_in_fresh_wrapper(self):
        comparison,_=fixture();last=comparison.candidate[-1]
        changed=replace(last,process_usage=replace(last.process_usage,window_started_monotonic_ns=0,cpu_time_100ns=measured(40_000_000,0)))
        self.reject(replace(comparison,candidate=(comparison.candidate[0],changed)),code='PROCESS_COUNTER_WINDOW_INCOHERENT')

    def test_changed_source_epoch_workload_scope_environment_reject(self):
        comparison,_=fixture();last=comparison.candidate[-1]
        variants=(replace(last,source=replace(last.source,source_digest=digest('other'))),
            replace(last,source=replace(last.source,source_generation=4)),replace(last,source=replace(last.source,workload_digest=digest('other'))),
            replace(last,scope_digest=digest('other')),replace(last,environment_digest=digest('other')))
        for changed in variants:
            with self.subTest(changed=changed.source):self.reject(replace(comparison,candidate=(comparison.candidate[0],changed)))

    def test_missing_source_or_usage_rejects_all_measurements(self):
        comparison,_=fixture();last=comparison.candidate[-1]
        for changed in (replace(last,source=None,process_usage=None),replace(last,process_usage=None)):
            self.reject(replace(comparison,candidate=(comparison.candidate[0],changed)))

    def test_reused_id_even_with_mutated_content_rejects(self):
        comparison,_=fixture();first,last=comparison.candidate
        changed=replace(last,sample_id=first.sample_id,memory_bytes=measured(700,last.observed_monotonic_ns))
        self.reject(replace(comparison,candidate=(first,changed)),code='COMPARISON_SAMPLE_REUSED_OR_DUPLICATED')

    def test_duplicate_reordered_and_gapped_sequences_reject(self):
        comparison,_=fixture();first,last=comparison.candidate
        for sequence in (2,3,5):
            with self.subTest(sequence=sequence):self.reject(replace(comparison,candidate=(first,replace(last,source=replace(last.source,sequence=sequence)))))

    def test_equal_and_rolled_back_sample_times_reject(self):
        comparison,_=fixture();first,last=comparison.candidate
        for at in (first.observed_monotonic_ns,first.observed_monotonic_ns-1):
            changed=frame(4,at,cpu=40_000_000,read=4000,write=1000)
            self.reject(replace(comparison,candidate=(first,changed)),code='PROCESS_SEQUENCE_GAP_OR_REPLAY')

    def test_overlapping_declared_windows_reject(self):
        _,context=fixture()
        self.reject(context=replace(context,candidate_start_ns=context.baseline_end_ns),code='COMPARISON_WINDOWS_NOT_ORDERED')

    def test_probe_start_outside_window_rejects(self):
        comparison,_=fixture();first,last=comparison.candidate
        changed=replace(first,process_usage=replace(first.process_usage,window_started_monotonic_ns=first.observed_monotonic_ns-1))
        self.reject(replace(comparison,candidate=(changed,last)),code='PROCESS_COUNTER_WINDOW_INCOHERENT')

    def test_counter_rollback_in_either_window_rejects_all_metrics(self):
        comparison,_=fixture();first,last=comparison.candidate
        for name in ('cpu_time_100ns','read_io_bytes','write_io_bytes'):
            changed=replace(last,process_usage=replace(last.process_usage,**{name:measured(0,last.observed_monotonic_ns)}))
            self.reject(replace(comparison,candidate=(first,changed)),code='PROCESS_COUNTER_ROLLBACK')

    def test_single_sample_is_not_counter_delta(self):
        comparison,_=fixture()
        self.reject(replace(comparison,baseline=comparison.baseline[:1]),code='PROCESS_COUNTER_BASELINE_REQUIRED')

    def test_counter_rollback_between_distinct_windows_rejects_same_epoch(self):
        comparison,_=fixture();first,last=comparison.candidate
        for name in ('cpu_time_100ns','read_io_bytes','write_io_bytes'):
            a=replace(first,process_usage=replace(first.process_usage,**{name:measured(1,first.observed_monotonic_ns)}))
            b=replace(last,process_usage=replace(last.process_usage,**{name:measured(2,last.observed_monotonic_ns)}))
            self.reject(replace(comparison,candidate=(a,b)),code='PROCESS_COUNTER_ROLLBACK')

    def test_uncertainty_and_cancellation_bounds(self):
        for uncertainty in (-1,True,1.0,MAX_OBSERVATION_AGE_NS+1):
            with self.subTest(uncertainty=uncertainty),self.assertRaises(ContractError):self.compare(uncertainty=uncertainty)
        with self.assertRaises(ContractError):self.compare(cancelled=1)

    def test_cancelled_result_has_no_measurements_or_dispatch(self):
        with patch.object(PerformanceDiagnostics,'compare_current',side_effect=AssertionError('analysis after cancellation')):
            result=self.compare(cancelled=True)
        self.assertEqual(result.state,'CANCELLED')
        self.assertTrue(all(item.state=='UNAVAILABLE' for item in result.baseline.measurements))

    def test_nested_bool_and_malformed_window_are_validated_before_math(self):
        comparison,_=fixture();last=comparison.candidate[-1]
        broken=replace(last.process_usage.read_io_bytes)
        object.__setattr__(broken,'value',True)
        changed=replace(last,process_usage=replace(last.process_usage,read_io_bytes=broken))
        with self.assertRaisesRegex(ContractError,'RESOURCE_MEASUREMENT_INVALID'):
            self.compare(replace(comparison,candidate=(comparison.candidate[0],changed)))

    def test_control_exception_during_copy_preserves_identity_and_inputs(self):
        comparison,_=fixture();before=asdict(comparison)
        for primary in (KeyboardInterrupt('synthetic analysis copy'),SystemExit(17)):
            with patch.object(PerformanceDiagnostics,'_copy_process_sample',side_effect=primary):
                try:self.compare(comparison)
                except BaseException as observed:self.assertIs(observed,primary)
                else:self.fail('control exception suppressed')
        self.assertEqual(asdict(comparison),before)

    def test_caller_mutation_after_snapshot_cannot_change_calculation(self):
        comparison,_=fixture();target=comparison.candidate[-1].process_usage.read_io_bytes
        original=PerformanceDiagnostics.compare_current
        def mutate_then_validate(engine,pinned,envelope,*,context):
            object.__setattr__(target,'value',2**63-1)
            return original(engine,pinned,envelope,context=context)
        with patch.object(PerformanceDiagnostics,'compare_current',new=mutate_then_validate):result=self.compare(comparison)
        self.assertEqual(result.candidate.measurements[1].total,2000)

    def test_concurrent_pure_comparisons_are_identical_without_owner_changes(self):
        comparison,_=fixture();outputs=[];failures=[]
        def run():
            try:outputs.append(self.compare(comparison))
            except BaseException as error:failures.append(error)
        threads=[threading.Thread(target=run) for _ in range(12)]
        for thread in threads:thread.start()
        for thread in threads:thread.join(3)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(failures,[]);self.assertEqual(len(outputs),12)
        self.assertTrue(all(result==outputs[0] for result in outputs))

    def test_rate_result_contract_rejects_bool_negative_and_unit_mismatch(self):
        good=ProcessRateMeasurement('READ_IO_BYTES',1,'BYTES_PER_SECOND',1,1,1,1,'MEASURED')
        for changes in ({'total':True},{'minimum_rate':-1},{'rate_unit':'CPU_MILLI'},{'maximum_rate':0},{'metric':[]}):
            with self.subTest(changes=changes),self.assertRaises(ContractError):replace(good,**changes)
        with self.assertRaises(ContractError):ProcessRateChange('READ_IO_BYTES',True,0,1,'MEASURED_BOUNDS_OVERLAP')


NATIVE_WORKLOAD=jobs.HELPERS+r'''
ready,first,first_done,second,second_done,release,path=sys.argv[1:]
memory=bytearray(4*1024*1024)
data=b'owned-repeatable-performance-data'*32768
signal(ready)
for begin,done in ((first,first_done),(second,second_done)):
    wait(begin)
    pathlib.Path(path).write_bytes(data)
    assert pathlib.Path(path).read_bytes()==data
    value=1
    for number in range(2000000):value=(value*1664525+1013904223)&0xffffffff
    signal(done)
wait(release)
'''
NATIVE_OBSERVATIONS=[]

class NativeProcessPerformanceComparisonTests(unittest.TestCase):
    setUp,tearDown=jobs.WindowsJobTests.setUp,jobs.WindowsJobTests.tearDown
    until,event,launch,simple=jobs.WindowsJobTests.until,jobs.WindowsJobTests.event,jobs.WindowsJobTests.launch,jobs.WindowsJobTests.simple

    def sampler(self,process,*,interval=1_000_000):
        return OwnedProcessTelemetrySampler(process,process.resource_identity,scope_digest=SCOPE,environment_digest=ENV,
            workload_digest=digest(NATIVE_WORKLOAD),source_generation=1,minimum_interval_ns=interval,maximum_age_ns=30_000_000_000)

    def test_actual_repeatable_cpu_io_workload_recorder_and_before_after_analysis(self):
        ready,first,first_done,second,second_done,release=(self.event() for _ in range(6))
        process=self.launch(('-B','-I','-c',NATIVE_WORKLOAD,ready.name,first.name,first_done.name,second.name,second_done.name,release.name,str(self.directory/'owned-io.bin')))
        ready.wait()
        try:
            sampler,recorder=self.sampler(process),ResourceTelemetryRecorder(maximum_samples=4)
            a=sampler.collect(recorder);first.signal();first_done.wait();b=sampler.collect(recorder)
            uncertainty=max(1,math.ceil(time.get_clock_info('monotonic').resolution*1_000_000_000))
            time.sleep(max(.02,2*uncertainty/1_000_000_000))
            c=sampler.collect(recorder);second.signal();second_done.wait();d=sampler.collect(recorder)
            retained=recorder.recent(now_monotonic_ns=time.monotonic_ns(),maximum_age_ns=30_000_000_000,scope_digest=SCOPE)
            self.assertEqual([sample.source.sequence for sample in retained],[1,2,3,4])
            context=CurrentComparisonContext(time.monotonic_ns(),30_000_000_000,SCOPE,ENV,process.resource_identity.source_digest,1,
                a.process_usage.window_started_monotonic_ns,b.observed_monotonic_ns,c.process_usage.window_started_monotonic_ns,d.observed_monotonic_ns)
            comparison=WorkloadComparisonInput('repeatable-owned-counter-workload',digest(NATIVE_WORKLOAD),retained[:2],retained[2:])
            result=PerformanceDiagnostics().compare_process_current(comparison,PerformanceEnvelope(5000,1_000_000,2**40),context=context,timestamp_uncertainty_ns=uncertainty)
            self.assertEqual(result.state,'MEASURED_PROCESS_COUNTER_COMPARISON')
            for window in (result.baseline,result.candidate):
                self.assertGreater(window.measurements[0].total,0)
                self.assertGreaterEqual(window.measurements[1].total,len(b'owned-repeatable-performance-data')*32768)
                self.assertGreaterEqual(window.measurements[2].total,len(b'owned-repeatable-performance-data')*32768)
                self.assertGreater(window.peak_private_bytes,0)
                self.assertTrue(all(item.minimum_rate<=item.estimated_rate<=item.maximum_rate for item in window.measurements))
            self.assertIn('MEASURED_COUNTER_CHANGE_NOT_CAUSAL_BOTTLENECK',result.findings)
            row={'test_id':self.id(),'pid':process.pid,'creation_time':process.creation_time,'workload_digest':digest(NATIVE_WORKLOAD),
                'monotonic_clock':time.get_clock_info('monotonic').implementation,'timestamp_uncertainty_ns':uncertainty,
                'scope':'Actual repeated owned CPU/read/write workload; no performance direction or cause asserted','result':asdict(result)}
            (self.directory/'performance-comparison.json').write_text(json.dumps(row,indent=2),encoding='utf-8')
            NATIVE_OBSERVATIONS.append(row)
        finally:
            first.signal();second.signal();release.signal()
            self.assertTrue(process.wait(5));self.until(lambda:process.active_process_count()==0)

    def test_actual_cached_polling_duplicates_cannot_count_as_two_windows(self):
        process,release,_=self.simple()
        try:
            sampler=self.sampler(process,interval=1_000_000_000)
            sample=sampler.sample();self.assertIs(sampler.sample(),sample)
            at=sample.observed_monotonic_ns
            context=CurrentComparisonContext(at+10,30_000_000_000,SCOPE,ENV,process.resource_identity.source_digest,1,at,at,at+1,at+2)
            comparison=WorkloadComparisonInput('duplicate-negative',digest(NATIVE_WORKLOAD),(sample,sample),(sample,sample))
            result=PerformanceDiagnostics().compare_process_current(comparison,PerformanceEnvelope(5,5000,2**40),context=context,timestamp_uncertainty_ns=0)
            self.assertEqual(result.state,'PROCESS_COMPARISON_REJECTED')
            self.assertIn('COMPARISON_SAMPLE_REUSED_OR_DUPLICATED',result.findings)
            self.assertTrue(process.resource_observation_current(process.resource_identity))
            NATIVE_OBSERVATIONS.append({'test_id':self.id(),'pid':process.pid,'creation_time':process.creation_time,
                'scope':'Actual cached native frame; synthetic declared mismatch windows for negative duplicate test only','result_state':result.state})
        finally:release.signal();self.assertTrue(process.wait(5));self.until(lambda:process.active_process_count()==0)

    def test_actual_closed_owned_source_returns_unavailable_not_zero_comparison(self):
        process,release,_=self.simple()
        sampler=self.sampler(process);sample=sampler.sample()
        release.signal();self.assertTrue(process.wait(5));self.until(lambda:process.active_process_count()==0)
        unavailable=sampler.sample()
        self.assertFalse(unavailable.memory_bytes.measured)
        self.assertIsNone(unavailable.process_usage)
        context=CurrentComparisonContext(time.monotonic_ns(),30_000_000_000,SCOPE,ENV,process.resource_identity.source_digest,1,
            sample.observed_monotonic_ns,sample.observed_monotonic_ns,sample.observed_monotonic_ns+1,unavailable.observed_monotonic_ns+1)
        comparison=WorkloadComparisonInput('closed-source-negative',digest(NATIVE_WORKLOAD),(sample,sample),(unavailable,unavailable))
        result=PerformanceDiagnostics().compare_process_current(comparison,PerformanceEnvelope(5,5000,2**40),context=context,timestamp_uncertainty_ns=0)
        self.assertEqual(result.state,'PROCESS_COMPARISON_REJECTED')
        self.assertIn('PROCESS_USAGE_UNAVAILABLE',result.findings)
        self.assertTrue(all(item.total is None for item in result.candidate.measurements))
        NATIVE_OBSERVATIONS.append({'test_id':self.id(),'pid':process.pid,'creation_time':process.creation_time,
            'scope':'Actual observed exit and unavailable producer frame; negative context uses no synthetic positive measurements','result_state':result.state})
