"""Selected joined journal/codec/retention consumers; no worker or effect."""
from foundation_support import *
import importlib,threading,unittest
from contextlib import ExitStack
from unittest.mock import patch

label=sys.argv[1];assert label.replace('-','').isalnum()
D=R/label;D.mkdir();(D/'tmp').mkdir()
os.environ['TEMP']=os.environ['TMP']=str(D/'tmp');os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
from ceta.store import sqlite_runtime
sqlite_runtime.load_sqlite();sqlite_identity=sqlite_runtime.runtime_identity()
from ceta.store.journal import SqliteJournal
from ceta.supervisor.windows_jobs import WindowsOwnedProcess
from ceta.identity import native_approval,native_clock,native_owner_view
from ceta.effects.native_cpu_binding import NativeCpuBinding
names=set(read(R/'ASSEMBLY.json')['payloads'])
before={n:ordinary(Q/n) for n in names};threads=set(threading.enumerate())
forbidden=[];executed=[];stopped=[];journals=[];original_init=SqliteJournal.__init__

def deny(*args,**kwargs):
    forbidden.append('native-worker-effect-or-owner-allocation');raise AssertionError('FN5_NATIVE_WORKER_NOT_AUTHORIZED')

def observe_journal(self,*args,**kwargs):
    journals.append(self);return original_init(self,*args,**kwargs)

class FixtureRoot:
    def __truediv__(self,name):
        name=str(name).replace('\\','/')
        if name=='.agents/fixtures':return D/'fixtures'
        if name.startswith('.agents/fixtures/'):return D/'fixtures'/name[len('.agents/fixtures/'):]
        return Q/name

with ExitStack() as guards:
    for target,name in ((subprocess,'Popen'),(WindowsOwnedProcess,'__init__'),
        (native_approval.NativeApprovalOwner,'__init__'),(native_approval._NativeApi,'__init__'),
        (native_clock.NativeSessionClock,'__init__'),(native_owner_view._ViewAPI,'__init__'),(NativeCpuBinding,'__init__')):
        guards.enter_context(patch.object(target,name,deny))
    guards.enter_context(patch.object(SqliteJournal,'__init__',observe_journal))
    module_names=('test_wire_scanning','test_journal_constructor_cleanup','test_journal_postconstruction_cleanup',
        'test_projections','test_editor_retention_queue')
    modules=[importlib.import_module(name) for name in module_names]
    for name,module in list(sys.modules.items()):
        if name.startswith('test_') and hasattr(module,'ROOT'):module.ROOT=FixtureRoot()
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m) for m in modules)
    def leaves(group):
        for item in group:
            if isinstance(item,unittest.TestSuite):yield from leaves(item)
            else:yield item
    expected=[t.id() for t in leaves(suite)];assert len(expected)==len(set(expected))
    class Result(unittest.TextTestResult):
        def startTest(self,test):executed.append(test.id());super().startTest(test)
        def stopTest(self,test):stopped.append(test.id());super().stopTest(test)
    started=utc()
    with (D/'tests.txt').open('x',encoding='utf8',buffering=1) as out:
        result=unittest.TextTestRunner(stream=out,verbosity=2,resultclass=Result).run(suite)
after={n:ordinary(Q/n) for n in names}
remaining=[t.name for t in set(threading.enumerate())-threads if t.is_alive()]
constructor=modules[1].NATIVE_CONNECTION_RECEIPTS;post=modules[2].NATIVE_RECEIPTS
constructor_closed=all(row['all_native_connections_closed'] for row in constructor)
post_closed=all(row['all_exact_native_connections_closed'] for row in post)
closed=all(getattr(j,'_closed',False) for j in journals)
imports={name:ordinary(Path(module.__file__)) for name,module in sys.modules.items()
    if (name=='ceta' or name.startswith('ceta.')) and getattr(module,'__file__',None)}
own_imports=all(Path(row['path']).is_relative_to(Q/'src') for row in imports.values())
passed=result.wasSuccessful() and not result.skipped and expected==executed==stopped and before==after
passed=passed and not forbidden and not remaining and constructor_closed and post_closed and own_imports
write_new(D/'RESULT.json',dict(started_at=started,finished_at=utc(),tests_run=result.testsRun,
    expected_ids=expected,executed_ids=executed,stopped_ids=stopped,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
    failure_details=[dict(id=t.id(),traceback=body) for t,body in result.failures+result.errors],raw=reference(D/'tests.txt'),
    sqlite_runtime=sqlite_identity,forbidden_native_calls=forbidden,remaining_threads=remaining,
    journal_instances=len(journals),all_product_journals_claimed_closed=closed,
    constructor_connection_receipts=constructor,constructor_native_connections_closed=constructor_closed,
    postconstruction_connection_receipts=post,postconstruction_native_connections_closed=post_closed,
    candidate_before=before,candidate_after=after,ceta_imports=imports,all_ceta_imports_from_candidate=own_imports,
    qualification='Actual disposable canonical SQLite with controlled cleanup/delivery/identity seams and offscreen Qt. Exact original test bodies; ROOT globals route only fixture writes to this runtime. No native worker, profile, Hello, CPU Set, genuine authority, full or Source acceptance.',
    Source_publication=False,exit_status=0 if passed else 1))
print(json.dumps(dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
    forbidden_native_calls=forbidden,remaining_threads=remaining,constructor_native_connections_closed=constructor_closed,
    postconstruction_native_connections_closed=post_closed,exit_status=0 if passed else 1)))
sys.exit(0 if passed else 1)
