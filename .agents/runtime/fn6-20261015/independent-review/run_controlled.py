"""Prior72 controlled methods plus exact timing diagnostics; native7 NOT_RUN."""
from foundation_support import *
import importlib,threading,types,unittest
from unittest.mock import patch

label=sys.argv[1];assert label.replace('-','').isalnum()
mode=sys.argv[2];assert mode in ('all','diagnostics')
D=R/label;D.mkdir();(D/'tmp').mkdir()
os.environ['TEMP']=os.environ['TMP']=str(D/'tmp')
sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
from ceta.store.sqlite_runtime import load_sqlite,runtime_identity
load_sqlite();sqlite_identity=runtime_identity()
import test_owner_authority_transactions as authority
class FixtureRoot:
    def __truediv__(self,name):
        name=str(name).replace('\\','/')
        if name=='.agents/fixtures':return D/'fixtures'
        if name.startswith('.agents/fixtures/'):return D/'fixtures'/name[len('.agents/fixtures/'):]
        return Q/name
authority.ROOT=FixtureRoot()
from ceta.store.journal import SqliteJournal
journals=[];journal_init=SqliteJournal.__init__
def observed_journal(self,*args,**kwargs):
    journals.append(self);journal_init(self,*args,**kwargs)
SqliteJournal.__init__=observed_journal
from ceta.supervisor.windows_jobs import WindowsOwnedProcess
from ceta.identity.native_clock import NativeSessionClock
forbidden_native=[]
def forbidden_process(self,*args,**kwargs):
    forbidden_native.append('WindowsOwnedProcess.__init__');raise AssertionError('No native target cohort authorized')
def forbidden_clock(self,*args,**kwargs):
    forbidden_native.append('NativeSessionClock.__init__');raise AssertionError('No native clock cohort authorized')
WindowsOwnedProcess.__init__=forbidden_process;NativeSessionClock.__init__=forbidden_clock
module=importlib.import_module('test_cpu_execution_admission')
cross=importlib.import_module('test_cpu_execution_cross_kernel')
interruptions=importlib.import_module('test_cpu_execution_registration_interruptions')
diagnostics=importlib.import_module('test_cpu_execution_timing_diagnostics')
suite=unittest.TestSuite([
    unittest.defaultTestLoader.loadTestsFromTestCase(module.CpuExecutionAdmissionTests),
    unittest.defaultTestLoader.loadTestsFromTestCase(cross.CrossKernelAdmissionTests),
    unittest.defaultTestLoader.loadTestsFromTestCase(interruptions.RegistrationInterruptionTests),
    unittest.defaultTestLoader.loadTestsFromTestCase(diagnostics.CpuTimingDiagnosticTests)])
def leaves(group):
    for item in group:
        if isinstance(item,unittest.TestSuite):yield from leaves(item)
        else:yield item
if mode=='diagnostics':suite=unittest.defaultTestLoader.loadTestsFromTestCase(diagnostics.CpuTimingDiagnosticTests)
tests=list(leaves(suite));expected=[t.id() for t in tests]
assert len(expected)==len(set(expected))==(82 if mode=='all' else 10)
assert sum(t.__class__ is module.CpuExecutionAdmissionTests for t in tests)==(46 if mode=='all' else 0)
assert sum(t.__class__ is cross.CrossKernelAdmissionTests for t in tests)==(19 if mode=='all' else 0)
assert sum(t.__class__ is interruptions.RegistrationInterruptionTests for t in tests)==(7 if mode=='all' else 0)
assert sum(t.__class__ is diagnostics.CpuTimingDiagnosticTests for t in tests)==10
from ceta.kernel import cpu_execution as execution
selected='test_operation_wall_budget_bounds_total_admission_separately_from_native_duration'
selection=[t for t in tests if t.__class__ is module.CpuExecutionAdmissionTests and t._testMethodName==selected]
assert len(selection)==(1 if mode=='all' else 0)
controlled_elapsed_evidence=[]
def controlled_arithmetic(self,original=None):
    original=getattr(module.CpuExecutionAdmissionTests,selected).__get__(self)
    values=[execution.time.perf_counter_ns()]
    def domain_elapsed():
        values.append(values[-1]+1000);return values[-1]
    # Only this original method's already-injected arithmetic setup is enclosed.
    # Its body, assertions, inner deadline values and persistent guards stay exact.
    with patch.object(execution.time,'perf_counter_ns',side_effect=domain_elapsed):
        try:return original()
        finally:controlled_elapsed_evidence.append(dict(id=self.id(),samples=values,quantum_ns=1000,
            original_method_body_unchanged=True,scope='Controlled nonnative arithmetic fixture only; not natural-time qualification'))
if selection:setattr(selection[0],selected,types.MethodType(controlled_arithmetic,selection[0]))
names=set(read(R/'ASSEMBLY.json')['payloads'])
before={n:ordinary(Q/n) for n in sorted(names)};assert len(before)==352
threads=set(threading.enumerate());executed=[];stopped=[]
class Result(unittest.TextTestResult):
    def startTest(self,test):executed.append(test.id());super().startTest(test)
    def stopTest(self,test):stopped.append(test.id());super().stopTest(test)
started=utc()
with (D/'tests.txt').open('x',encoding='utf8',buffering=1) as out:
    result=unittest.TextTestRunner(stream=out,verbosity=2,resultclass=Result).run(suite)
after={n:ordinary(Q/n) for n in sorted(names)}
remaining=[t.name for t in set(threading.enumerate())-threads if t.is_alive()]
closed=all(getattr(j,'_closed',False) is True for j in journals)
metadata_free=execution._LIVENESS_LOCK.acquire(False)
if metadata_free:
    mutation_empty=not execution._MUTATING_OWNERS and not execution._MUTATING_STORES
    retained_rows=list(execution._ACTIVE_OWNERS.values())
    paired=len(retained_rows)==len(execution._ACTIVE_STORES) and all(
        execution._ACTIVE_STORES.get(id(row[1])) is row and row[2].active is row[3]
        and row[2].mutating==0 and row[2].allowed is None for row in retained_rows)
    execution._LIVENESS_LOCK.release()
else:
    mutation_empty=False;retained_rows=[];paired=False
retained=[dict(owner_id=id(row[0]),store_id=id(row[1]),coordinator_id=id(row[2]),lease_id=id(row[3]),
    pending_cleanup=row[3].inspection()['pending_cleanup'],closed=row[3].inspection()['closed'],
    controlled_retainer_locked=getattr(row[3]._retained or row[3]._manager,'locked',None)) for row in retained_rows]
pending_only=paired and all(row['pending_cleanup'] and not row['closed']
    and row['controlled_retainer_locked'] is False for row in retained)
imports={n:ordinary(Path(m.__file__)) for n,m in sys.modules.items() if (n=='ceta' or n.startswith('ceta.'))
    and getattr(m,'__file__',None)}
own_imports=all(Path(row['path']).is_relative_to(Q/'src') for row in imports.values())
passed=(result.wasSuccessful() and not result.skipped and expected==executed==stopped and before==after
    and metadata_free and closed and not remaining and not forbidden_native and not module.NATIVE_ADMISSION_RECEIPTS
    and mutation_empty and pending_only and own_imports and len(controlled_elapsed_evidence)==(1 if mode=='all' else 0))
write_new(D/'RESULT.json',dict(started_at=started,finished_at=utc(),tests_run=result.testsRun,
    expected_ids=expected,executed_ids=executed,stopped_ids=stopped,
    failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
    failure_details=[dict(id=t.id(),traceback=body) for t,body in result.failures+result.errors],
    raw=reference(D/'tests.txt'),runner=reference(Path(__file__)),sqlite_runtime=sqlite_identity,
    actual_journals=len(journals),all_journals_closed=closed,
    native_SQLite_files=[dict(path=str(j.path),closed=j._closed) for j in journals],
    controlled_elapsed_evidence=controlled_elapsed_evidence,cohort=mode,all_other_clocks_unchanged=True,
    forbidden_native_constructor_calls=forbidden_native,native_admission_receipts=module.NATIVE_ADMISSION_RECEIPTS,
    cross_kernel_entry_facts=cross.entry_facts,registration_observations=cross.REGISTRATION_OBSERVATIONS,
    mutation_registry_empty=mutation_empty,metadata_lock_nonblocking_acquired=metadata_free,
    interruption_facts=interruptions.INTERRUPTION_FACTS,retained_fixture_custody=retained,retained_pending_pairs_exact=pending_only,
    candidate_before=before,candidate_after=after,remaining_threads=remaining,
    ceta_imports=imports,all_ceta_imports_from_candidate=own_imports,
    live_Source_conservation_asserted=False,future_accepted_Source_binding_pending=True,
    original7_native_methods='NOT_RUN',connected_gate_complete=False,Source_acceptance=False,
    qualification='Controlled component repair only: exact prior46 admission plus19 cross-kernel plus7 interruption methods and new timing diagnostics; six original failure predicates retained with declared successor line mapping. Actual disposable canonical SQLite; controlled authority/capacity and nonnative targets. No native Set/profile/Hello or active Source actions.',
    exit_status=0 if passed else 1))
print(json.dumps(dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
    all_journals_closed=closed,mutation_registry_empty=mutation_empty,remaining_threads=remaining,
    deterministic_arithmetic_methods=len(controlled_elapsed_evidence),exit_status=0 if passed else 1)),flush=True)
sys.exit(0 if passed else 1)
