"""Independent finite controlled review; no production/native effect qualification."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import ctypes  # Initialize the standard library before the native-operation audit.
import gc
import hashlib
import json
import os
import sys
import threading
import unittest
from unittest.mock import patch

F = Path('T:/00-Active/Project-AI-CETA')
Q = F / '.agents/cpu-capacity-connection-20261017'
A = F / '.agents/runtime/cpu-capacity-connection-20261017'
R = Path(__file__).resolve().parent
assert R == F / '.agents/runtime/cpu-capacity-connection-review-20261017'
D = R / 'controlled-r2'
D.mkdir(exist_ok=False)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
assert sha(A/'HANDOFF.json') == '6ccb88f545dee169faf3c86b97eb8ab96679256a34eafa1dd66c2fc67de48542'
assert sha(A/'cut-r1/MANIFEST.json') == '12c6dd58311e85686f68cbb7bc18a8d631ec418428fe2ddad88f017d575f4ce1'
manifest, handoff, inputs = read(A/'cut-r1/MANIFEST.json'), read(A/'HANDOFF.json'), read(A/'INPUTS.json')
assert sha(A/'INPUTS.json') == manifest['inputs_sha256']
assert sha(A/'cut-r1/DELTA.diff') == manifest['diff_sha256']
assert sha(Path(manifest['base']['path'])) == manifest['base']['sha256']
for path, pin in inputs['reviews'].items():
    assert sha(F/path) == pin
for row in inputs['payloads'].values():
    assert Path(row['path']).is_relative_to(F) and sha(Path(row['path'])) == row['sha256']
expected = {name: row['sha256'] for name,row in inputs['payloads'].items()}
for row in manifest['changed']:
    assert sha(Path(row['frozen_copy'])) == row['after_sha256']
    if row['before'] is not None:
        assert sha(Path(row['before']['path'])) == row['before']['sha256']
    expected[row['path']] = row['after_sha256']
    if row['path'].endswith('.py'):
        ast.parse((Q/row['path']).read_text(encoding='utf-8-sig'))
assert expected == manifest['payload_hashes'] and len(expected) == 371
candidate_hashes = lambda: {name: sha(Q/name) for name in expected}
before = candidate_hashes()
assert before == expected
source_names = read(Path(manifest['base']['path']))['expected_payload_hashes']
source_before = {name: sha(F/name) for name in source_names}
history = {}
for label,row in handoff['failed_evidence'].items():
    for key in ('result','raw'):
        path=Path(row[key]['path']); assert sha(path) == row[key]['sha256']
    history[label] = row
started = datetime.now(timezone.utc).isoformat()
prohibited = []


def audit(event, args):
    forbidden = event in ('subprocess.Popen','os.system','os.startfile','socket.connect','socket.bind')
    forbidden |= event == 'ctypes.dlsym' and args[1] in (
        'CreateProcessW','CreateProcessAsUserW','CreateAppContainerProfile','DeleteAppContainerProfile',
        'SetInformationJobObject','OpenProcess','TerminateProcess')
    if forbidden:
        prohibited.append(dict(event=event))
        raise RuntimeError('INDEPENDENT_REVIEW_NATIVE_PROCESS_NETWORK_FORBIDDEN')
    if event == 'open' and not isinstance(args[0], int):
        mode, flags = args[1], args[2]
        writing = (isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        if writing:
            assert Path(args[0]).resolve().is_relative_to(D), ('WRITE_OUTSIDE_REVIEW_CUT',args[0])


sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path[:0] = [str(Q/'src'),str(Q/'tests/contract')]
sys.addaudithook(audit)
from ceta.store.journal import SqliteJournal
stores=[]
original_init=SqliteJournal.__init__
def construct(store,*args,**kwargs):
    root=Path(args[0] if args else kwargs['root']).resolve()
    assert root.is_relative_to(D), ('SQLITE_OUTSIDE_DISPOSABLE_CUT',str(root))
    try:
        original_init(store,*args,**kwargs)
    finally:
        if getattr(store,'_connection',None) is not None:
            stores.append((store,store._connection))
SqliteJournal.__init__=construct
import test_cpu_capacity_connection as connection
import test_native_owner_execution as owner_tests
import test_native_owner_preparation as preparation
import test_owned_cpu_outcome_transactions as outcomes
import test_cpu_execution_admission as admission
import test_owner_authority_transactions as authority
from ceta.contracts.wire import ContractError
from ceta.store import outcome_capacity as capacity
from ceta.identity.owner_session import NativeCpuOwnerSession
from ceta.identity.cpu_outcome_capacity import stage_owned_cpu_outcome
preparation.FIXTURES=D/'fixtures/preparation'
authority.ROOT=D/'fixtures/authority'


class IndependentChallenges(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema=connection.strict_loads((Q/'contracts/schemas/records.schema.json').read_bytes())

    fixture=connection.CapacityConnectionTests.fixture
    runtime=None

    def test_hostile_primary_commit_failure_keeps_exact_primary_and_custody(self):
        class Primary(KeyboardInterrupt):
            def __getattribute__(self,name):
                if name in ('__dict__','__traceback__','add_note','with_traceback'):
                    raise OSError('controlled hostile diagnostic hook')
                return super().__getattribute__(name)
        f=self.fixture(); primary=Primary('controlled commit interruption'); actual=None
        def fail(): raise primary
        try:
            with f.lease() as execution:
                f.fence(execution); binding=execution._outcome_capacity; f.fault=fail
                execution.record_outcome(*f.evidence())
        except BaseException as error: actual=error
        finally: f.fault=None
        self.assertIs(actual,primary)
        data=BaseException.__dict__['__dict__'].__get__(primary)
        self.assertIs(data['owned_cpu_capacity'],binding)
        self.assertIs(data['outcome_capacity_custody'],binding.lease)
        self.assertIs(f.store._capacity_active,binding.lease)
        self.assertEqual(binding.lease.state,'PENDING')
        self.assertFalse(binding.lease.durable)

    def test_primary_survives_adapter_exit_failure_with_secondary_and_liveness(self):
        f=self.fixture(); primary=SystemExit('controlled body'); secondary=OSError('controlled capacity exit'); actual=None
        def fail(*args): raise secondary
        with patch.object(capacity.OutcomeCapacityLease,'__exit__',fail):
            try:
                with f.lease() as execution:
                    binding=execution._outcome_capacity
                    raise primary
            except BaseException as error: actual=error
        self.assertIs(actual,primary)
        self.assertIs(primary.owned_cpu_capacity_cleanup_error,secondary)
        self.assertIs(binding.cleanup_error,secondary)
        self.assertEqual(binding.state,'PENDING')
        self.assertIs(f.store._capacity_active,binding.lease)
        self.assertIs(f.kernel._cpu_execution.active,execution)
        self.assertTrue(execution._pending_cleanup)

    def test_mismatched_staged_bytes_never_mark_real_commit_durable(self):
        f=self.fixture(); stage=capacity.OutcomeCapacityLease.stage_outcome
        def mismatched(held,payloads):
            return stage(held,(payloads[0]+b' ',)+payloads[1:])
        with self.assertRaisesRegex(ContractError,'DURABLE_OUTCOME_PENDING'):
            with f.lease() as execution:
                f.fence(execution); binding=execution._outcome_capacity
                position=f.store.store_position()
                with patch.object(capacity.OutcomeCapacityLease,'stage_outcome',mismatched):
                    result=execution.record_outcome(*f.evidence())
                self.assertEqual(result.as_dict()['state'],'SETTLED_OBSERVED')
                self.assertNotEqual(f.store.store_position(),position)
                self.assertFalse(binding.lease.durable)
        self.assertEqual(binding.lease.state,'PENDING')
        self.assertIs(f.store._capacity_active,binding.lease)

    def test_native_subclass_cannot_use_generic_capacity_dispatch(self):
        generic=admission.CpuExecutionAdmissionTests();generic.schema=self.schema
        self.addCleanup(generic.doCleanups);f=generic.fixture()
        class NativeSubclass(NativeCpuOwnerSession): pass
        with generic.lease(f) as execution:
            owner=execution._owner;original=owner.owners
            owner.owners=object.__new__(NativeSubclass)
            execution._called=execution._dispatching=True
            try:
                with self.assertRaisesRegex(ContractError,'PHYSICAL_CAPACITY_REQUIRED'):
                    execution.dispatch_fence()
                self.assertFalse(execution._dispatch)
            finally:
                owner.owners=original;execution._dispatching=False

    def test_staging_rejects_foreign_kernel_identity(self):
        f=self.fixture()
        with f.lease() as execution:
            f.fence(execution)
            from types import SimpleNamespace
            foreign=SimpleNamespace(_cpu_execution=f.kernel._cpu_execution,_store=f.store)
            with self.assertRaisesRegex(ContractError,'OUTCOME_OWNER_REQUIRED'):
                stage_owned_cpu_outcome(foreign,(b'foreign',))
            self.assertEqual(execution._outcome_capacity.lease.retained_payloads(),())
            execution.record_outcome(*f.evidence())

    def test_closed_adapter_rejects_stage_mark_and_reentry(self):
        f=self.fixture()
        with f.lease() as execution:
            binding=execution._outcome_capacity
        for operation in (binding.__enter__,lambda:binding.mark_dispatch(execution),lambda:binding.stage_outcome((b'x',))):
            with self.assertRaises(ContractError): operation()
        self.assertEqual(binding.state,'CLOSED')
        self.assertIsNone(f.store._capacity_active)


    def test_public_view_constructor_keeps_positional_call_and_checks_budget(self):
        from ceta.identity.native_owner_view import NativeOwnerView, NativeStoreBinding
        from ceta.identity.windows_pipe import WindowsPeerRegistry
        from ceta.identity.native_clock import NativeSessionClock
        registry=object.__new__(WindowsPeerRegistry)
        clock=object.__new__(NativeSessionClock)
        store=object.__new__(NativeStoreBinding)
        legacy=NativeOwnerView(registry,clock,store)
        self.assertIsNone(legacy._outcome_budget)
        budget=capacity.OutcomeCapacityBudget(65536,65536,65536,8192)
        current=NativeOwnerView(registry,clock,store,outcome_budget=budget)
        self.assertIs(current._outcome_budget,budget)
        with self.assertRaisesRegex(ContractError,'CONFIGURATION_REQUIRED'):
            NativeOwnerView(registry,clock,store,outcome_budget=object())
        self.assertIs(current.retain_owned_cpu_outcome_capacity.__self__,current)

    def test_unconfigured_entry_preserves_explicit_pending_owner_for_recovery(self):
        f=self.fixture();saved=f.store._capacity_vfs;f.store._capacity_vfs=None
        execution=f.lease()
        try:
            with self.assertRaisesRegex(ContractError,'NOT_CONFIGURED'):
                execution.__enter__()
            bound=execution._outcome_capacity
            self.assertIsNone(bound.lease)
            self.assertEqual(bound.state,'FAILED')
            self.assertIsNone(f.store._capacity_active)
            self.assertEqual(f.status(),'PREPARED')
            self.assertTrue(f.owner._execution.pending)
            self.assertEqual(f.owner._execution.state,'FAILED')
            self.assertIs(f.kernel._cpu_execution.active,execution)
            self.assertTrue(execution._pending_cleanup)
        finally:f.store._capacity_vfs=saved
        with self.assertRaises(ContractError):
            f.lease().__enter__()


suite=unittest.TestSuite();excluded=[]
for cls in [IndependentChallenges]:
    for test in unittest.defaultTestLoader.loadTestsFromTestCase(cls):
        if test._testMethodName not in ('test_public_view_constructor_keeps_positional_call_and_checks_budget', 'test_unconfigured_entry_preserves_explicit_pending_owner_for_recovery'): continue
        if test._testMethodName=='test_before_and_after_commit_process_crashes_reopen_without_dispatch':
            excluded.append(dict(id=test.id(),reason='Root native/process hold'))
        else:suite.addTest(test)
case_ids=[test.id() for test in suite];executed=[];stopped=[]
class Result(unittest.TextTestResult):
    def startTest(self,test):
        gc.collect();executed.append(test.id());super().startTest(test)
    def stopTest(self,test):
        stopped.append(test.id());super().stopTest(test)
with (D/'RAW.txt').open('x',encoding='utf-8') as stream:
    result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
after=candidate_hashes()
source_after={name:sha(F/name) for name in source_names}
closure=[]
for store,handle in stores:
    refusal=None
    try:handle.execute('SELECT 1')
    except store._sqlite.ProgrammingError:refusal='closed connection refusal'
    except BaseException as error:refusal=type(error).__name__
    closure.append(dict(path=str(store.path),closed=store._closed,refusal=refusal,
        retained_capacity=store._capacity_active is not None))
imports={name:str(Path(module.__file__).resolve()) for name,module in sys.modules.items()
    if name.startswith('ceta.') and getattr(module,'__file__',None)}
threads=[dict(name=t.name,daemon=t.daemon) for t in threading.enumerate() if t is not threading.current_thread()]
passed=(result.wasSuccessful() and not result.skipped and not prohibited and not threads
    and expected==before==after and source_before==source_after and executed==stopped==case_ids
    and all(Path(path).is_relative_to(Q) for path in imports.values())
    and all(row['closed'] and row['refusal']=='closed connection refusal' and not row['retained_capacity'] for row in closure))
record=dict(started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),reviewer='/root/native_denial_diagnosis',
    command=list(sys.orig_argv),candidate=str(Q),handoff_sha256=sha(A/'HANDOFF.json'),manifest_sha256=sha(A/'cut-r1/MANIFEST.json'),
    dependencies=inputs,source_before=source_before,source_after=source_after,before=before,after=after,
    expected_ids=case_ids,executed_ids=executed,stopped_ids=stopped,excluded_ids=excluded,
    tests_run=result.testsRun,failures=[dict(id=t.id(),traceback=trace) for t,trace in result.failures],
    errors=[dict(id=t.id(),traceback=trace) for t,trace in result.errors],skips=len(result.skipped),
    sqlite_lifetimes=closure,fixture_disposal=connection.FACTS,remaining_threads=threads,
    prohibited_operations=prohibited,import_origins=imports,original_failed_evidence=history,
    raw_sha256=sha(D/'RAW.txt'),exit_status=0 if passed else 1,
    actual_canonical_SQLite=True,physical_native_capacity=False,CPU_effect=False,source_publication=False,
    provenance='Controlled native/approval/producer/observer fixture facts; real candidate kernel, journal, lease and adapter',
    real_recovery_and_advancing_reservation='OPEN')
with (D/'RESULT.json').open('x',encoding='utf-8') as stream:
    json.dump(record,stream,indent=2);stream.write('\n')
print(json.dumps(dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
    exit_status=record['exit_status'],result=str(D/'RESULT.json'),sha256=sha(D/'RESULT.json'),remaining_threads=threads)))
sys.exit(record['exit_status'])
