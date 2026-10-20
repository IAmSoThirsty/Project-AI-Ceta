"""Finite exact-ID runner; records failures, source cut and owned resources."""
from pathlib import Path
import importlib,json,os,sys,threading,unittest
P=Path('T:/00-Active/Project-AI-CETA');Q=P/'.agents/cpb1-20261014';R=P/'.agents/runtime/cpb1-20261014'
sys.path.insert(0,str(P/'.agents/runtime/ka1-20261014'));import ka1_support as s
s.Q=Q;s.R=R
label=sys.argv[1];selection=sys.argv[2]
sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
setup=json.loads((R/'SOURCE-INPUTS.json').read_text())
import test_native_cpu_binding as tests
if selection=='domain':suite=unittest.defaultTestLoader.loadTestsFromTestCase(tests.NativeCpuBindingDomainTests)
elif selection=='all':suite=unittest.defaultTestLoader.loadTestsFromModule(tests)
elif selection=='connected':
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(name)) for name in
        ('test_native_cpu_binding','test_native_session_clock','test_real_effect_contract','test_temporal','test_wire','test_all_records'))
    # Only unchanged observation/negative WT4 cases; CPU Set/apply/restore cases
    # are outside this job's scope and are not counted as executed.
    wt=importlib.import_module('test_windows_throttling')
    suite.addTests(wt.WindowsThrottleTests(name) for name in (
        'test_actual_slow_query_rejects_subtick_elapsed_window',
        'test_query_oserror_and_wrong_payload_size_are_unavailable'))
else:raise AssertionError('Unknown finite cohort')
def ids(group):
    for item in group:
        if isinstance(item,unittest.TestSuite):yield from ids(item)
        else:yield item.id()
expected=list(ids(suite));assert len(expected)==len(set(expected))
before={name:s.ordinary(Q/name) for name in s.source_inventory() if (Q/name).exists()}
for name in ('src/ceta/effects/native_cpu_binding.py','tests/contract/test_native_cpu_binding.py','contracts/NATIVE_CPU_BINDING_V1.md',
             'src/ceta/identity/native_clock.py','src/ceta/contracts/real_effect.py','src/ceta/contracts/workload_throttling.py'):
    before[name]=s.ordinary(Q/name)
threads=set(threading.enumerate());executed=[];stopped=[];started=s.utc()
class Recorded(unittest.TextTestResult):
    def startTest(self,test):executed.append(test.id());super().startTest(test)
    def stopTest(self,test):stopped.append(test.id());super().stopTest(test)
with (R/(label+'.txt')).open('x',encoding='utf-8',buffering=1) as raw:
    result=unittest.TextTestRunner(stream=raw,verbosity=2,resultclass=Recorded).run(suite)
remaining=[dict(name=t.name,native_id=t.native_id) for t in set(threading.enumerate())-threads if t.is_alive()]
assert all(s.ordinary(Q/name)==row for name,row in before.items())
assert all(s.ordinary(P/name)==row for name,row in setup['Source290'].items())
native=tests.NATIVE_RECEIPTS
closed=all(row['worker_closed'] and row['process_closed'] and row['job_closed'] and row['thread_closed']
    and row['clock_status']=='CLOSED' and not row['clock_sampler_alive'] and not row['class15_write_calls'] for row in native)
passed=result.wasSuccessful() and not result.skipped and expected==executed==stopped and not remaining and closed
s.write_new(R/(label+'.json'),dict(started_at=started,finished_at=s.utc(),tests_run=result.testsRun,
    expected_ids=expected,executed_ids=executed,stopped_ids=stopped,
    failures=[dict(test=t.id(),traceback=body) for t,body in result.failures],
    errors=[dict(test=t.id(),traceback=body) for t,body in result.errors],skips=result.skipped,
    native_receipts=native,all_recorded_native_owners_closed=closed,remaining_threads=remaining,
    source290_native_bytes_retained=True,candidate_before=before,raw=s.reference(R/(label+'.txt')),
    driver_and_clock_info={name:vars(__import__('time').get_clock_info(name)) for name in ('monotonic','perf_counter')},
    exit_status=0 if passed else 1))
print(json.dumps(dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
    native_cases=len(native),remaining_threads=remaining,exit_status=0 if passed else 1)),flush=True)
sys.exit(0 if passed else 1)
