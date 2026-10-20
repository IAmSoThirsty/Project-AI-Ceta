"""Joined settlement/reconciliation domain cases on actual disposable SQLite."""
from foundation_support import *
import importlib,threading,unittest
from contextlib import ExitStack
from unittest.mock import patch

label=sys.argv[1];assert label.replace('-','').isalnum()
D=R/label;D.mkdir();(D/'tmp').mkdir();os.environ['TEMP']=os.environ['TMP']=str(D/'tmp')
sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
from ceta.store import sqlite_runtime
sqlite_runtime.load_sqlite()
from ceta.store.journal import SqliteJournal
from ceta.supervisor.windows_jobs import WindowsOwnedProcess
from ceta.identity import native_approval,native_clock,native_owner_view
from ceta.effects.native_cpu_binding import NativeCpuBinding
names=set(read(R/'ASSEMBLY.json')['payloads']);before={n:ordinary(Q/n) for n in names}
forbidden=[];executed=[];stopped=[];journals=[];threads=set(threading.enumerate());original_init=SqliteJournal.__init__

def deny(*args,**kwargs):forbidden.append('worker-effect-or-owner-allocation');raise AssertionError('FN5_OUTCOME_DOMAIN_ONLY')
def observe(self,*args,**kwargs):journals.append(self);return original_init(self,*args,**kwargs)
class FixtureRoot:
    def __truediv__(self,name):
        name=str(name).replace('\\','/')
        if name=='.agents/fixtures':return D/'fixtures'
        if name.startswith('.agents/fixtures/'):return D/'fixtures'/name[len('.agents/fixtures/'):]
        return Q/name
def leaves(group):
    for item in group:
        if isinstance(item,unittest.TestSuite):yield from leaves(item)
        else:yield item
with ExitStack() as guards:
    for target,name in ((subprocess,'Popen'),(WindowsOwnedProcess,'__init__'),
        (native_approval.NativeApprovalOwner,'__init__'),(native_approval._NativeApi,'__init__'),
        (native_clock.NativeSessionClock,'__init__'),(native_owner_view._ViewAPI,'__init__'),(NativeCpuBinding,'__init__')):
        guards.enter_context(patch.object(target,name,deny))
    guards.enter_context(patch.object(SqliteJournal,'__init__',observe))
    outcome=importlib.import_module('test_owned_cpu_outcome_transactions')
    fresh=importlib.import_module('test_fresh_observer_reconciliation')
    for name,module in list(sys.modules.items()):
        if name.startswith('test_') and hasattr(module,'ROOT'):module.ROOT=FixtureRoot()
    all_tests=list(leaves(unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(outcome),
        unittest.defaultTestLoader.loadTestsFromModule(fresh)])))
    deferred=[t.id() for t in all_tests if t._testMethodName=='test_before_and_after_commit_process_crashes_reopen_without_dispatch']
    tests=[t for t in all_tests if t.id() not in deferred]
    assert len(deferred)==1
    expected=[t.id() for t in tests];assert len(expected)==len(set(expected))
    class Result(unittest.TextTestResult):
        def startTest(self,test):executed.append(test.id());super().startTest(test)
        def stopTest(self,test):stopped.append(test.id());super().stopTest(test)
    started=utc()
    with (D/'tests.txt').open('x',encoding='utf8',buffering=1) as out:
        result=unittest.TextTestRunner(stream=out,verbosity=2,resultclass=Result).run(unittest.TestSuite(tests))
after={n:ordinary(Q/n) for n in names}
remaining=[t.name for t in set(threading.enumerate())-threads if t.is_alive()]
closed=all(getattr(j,'_closed',False) is True for j in journals)
imports={name:ordinary(Path(module.__file__)) for name,module in sys.modules.items()
    if (name=='ceta' or name.startswith('ceta.')) and getattr(module,'__file__',None)}
own_imports=all(Path(row['path']).is_relative_to(Q/'src') for row in imports.values())
passed=result.wasSuccessful() and not result.skipped and expected==executed==stopped and before==after
passed=passed and not forbidden and not remaining and closed and own_imports
write_new(D/'RESULT.json',dict(started_at=started,finished_at=utc(),tests_run=result.testsRun,expected_ids=expected,
    executed_ids=executed,stopped_ids=stopped,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
    failure_details=[dict(id=t.id(),traceback=body) for t,body in result.failures+result.errors],raw=reference(D/'tests.txt'),
    explicit_targeted_exclusions=deferred,exclusion_reason='This domain-only cohort admits no child process. Original crash method body/ID is retained in normative inventory for later bounded interpreter/full qualification.',
    sqlite_runtime=sqlite_runtime.runtime_identity(),journals=len(journals),all_journals_closed=closed,
    forbidden_calls=forbidden,remaining_threads=remaining,candidate_before=before,candidate_after=after,
    ceta_imports=imports,all_imports_from_candidate=own_imports,cumulative_observations=outcome.CUMULATIVE_OBSERVATIONS,
    native_CRASH_OBSERVATIONS=outcome.CRASH_OBSERVATIONS,
    qualification='Canonical actual SQLite, atomic outcome, cumulative reserve, concurrency/recovery and advancing observation logic. Positive native proof providers are CONTROLLED; no native observer/effect, genuine authority, profile, Hello, full or Source acceptance.',
    exit_status=0 if passed else 1))
print(json.dumps(dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
    journals=len(journals),all_journals_closed=closed,remaining_threads=remaining,exit_status=0 if passed else 1)))
sys.exit(0 if passed else 1)
