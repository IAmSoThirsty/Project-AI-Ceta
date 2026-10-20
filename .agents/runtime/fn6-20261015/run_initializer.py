"""Actual private constructor/SQLite regressions with physical cleanup probes."""
from foundation_support import *
import threading,unittest
from contextlib import ExitStack
from unittest.mock import patch
from resource_observer import Observer
label=sys.argv[1];assert label.replace('-','').isalnum()
D=R/label;D.mkdir();(D/'tmp').mkdir();os.environ['TEMP']=os.environ['TMP']=str(D/'tmp')
names=set(read(R/'ASSEMBLY.json')['payloads']);before={n:ordinary(Q/n) for n in names}
sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
from ceta.store.sqlite_runtime import load_sqlite,runtime_identity
sqlite=load_sqlite()
from ceta.identity import native_approval,native_clock,native_owner_view
from ceta.effects.native_cpu_binding import NativeCpuBinding
from ceta.supervisor.windows_jobs import WindowsOwnedProcess
forbidden=[];threads=set(threading.enumerate());executed=[];stopped=[]
def deny(*args,**kwargs):forbidden.append('native-worker-profile-clock-or-approval-allocation');raise AssertionError('FN6_INITIALIZER_NO_NATIVE_EFFECT')
observer=Observer(sqlite);primary=result=None
with ExitStack() as guards:
    for target,name in ((subprocess,'Popen'),(WindowsOwnedProcess,'launch'),
        (native_approval.NativeApprovalOwner,'__init__'),(native_approval._NativeApi,'__init__'),
        (native_clock.NativeSessionClock,'__init__'),(native_owner_view._ViewAPI,'__init__'),(NativeCpuBinding,'__init__')):
        guards.enter_context(patch.object(target,name,deny))
    import test_native_owner_preparation as preparation
    import test_kernel_initializer_publication as cases
    preparation.ROOT=Q;preparation.FIXTURES=D/'fixtures'
    suite=unittest.defaultTestLoader.loadTestsFromModule(cases)
    def leaves(group):
        for item in group:
            if isinstance(item,unittest.TestSuite):yield from leaves(item)
            else:yield item
    expected=[test.id() for test in leaves(suite)];assert len(expected)==len(set(expected))==3
    class Result(unittest.TextTestResult):
        def startTest(self,test):executed.append(test.id());super().startTest(test)
        def stopTest(self,test):stopped.append(test.id());super().stopTest(test)
    observer.install()
    try:
        with (D/'tests.txt').open('x',encoding='utf8',buffering=1) as out:
            result=unittest.TextTestRunner(stream=out,verbosity=2,resultclass=Result).run(suite)
    except BaseException as error:primary=error
    finally:observer.uninstall()
resources=observer.finish();after={n:ordinary(Q/n) for n in names}
remaining=[dict(name=t.name,native_id=t.native_id) for t in set(threading.enumerate())-threads if t.is_alive()]
closed=resources['owned_resources_closed'] is True and resources['remaining_resources']==[]
closed=closed and all(row['physical_closed_probe'] for row in resources['sqlite'])
closed=closed and all(row['closed'] and row['fileno_denied'] for row in resources['streams'])
passed=primary is None and result is not None and result.wasSuccessful() and not result.skipped
passed=passed and expected==executed==stopped and before==after and closed and not remaining and not forbidden
write_new(D/'RESULT.json',dict(at=utc(),tests_run=result.testsRun if result else 0,expected_ids=expected,executed_ids=executed,stopped_ids=stopped,
    failures=len(result.failures) if result else None,errors=len(result.errors) if result else None,skips=len(result.skipped) if result else None,
    failure_details=[dict(id=t.id(),traceback=body) for t,body in result.failures+result.errors] if result else [],
    exact_reviewer_oracle_facts=cases.FACTS,physical_resources=resources,all_physical_fixture_resources_closed=closed,
    sqlite_runtime=runtime_identity(),forbidden_calls=forbidden,remaining_threads=remaining,primary_type=type(primary).__name__ if primary else None,
    candidate_before=before,candidate_after=after,raw=reference(D/'tests.txt'),original_WT_method_AST='Exact unchanged',
    qualification='Real canonical constructor and SQLite, controlled descriptor KI/SystemExit/MemoryError and native/approval facts. Positive retry must prepare through actual canonical CAS; defaults stay closed.',
    native_worker_profile_Hello_CPU_Set=False,Source_publication=False,exit_status=0 if passed else 1))
print(json.dumps(dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
    all_physical_fixture_resources_closed=closed,exit_status=0 if passed else 1)))
if primary is not None:raise primary
sys.exit(0 if passed else 1)
