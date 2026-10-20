"""Joined canonical SQLite/coordination probes with controlled native facts."""
import threading,unittest
from unittest.mock import patch
import test_native_owner_preparation as preparation
from ceta.contracts.kernel_transactions import ZERO_BUDGET,budget_key,logical_key,read_budget
from ceta.contracts.wire import ContractError
from ceta.identity import owner_session
from ceta.identity.owners import WindowsIdentityOwners
from ceta.kernel import cpu_execution,transactions
from ceta.kernel.owner_authority import grant_key_for

OBSERVATIONS=[]

class PreparationCoordinationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        preparation.NativeOwnerPreparationTests.setUpClass.__func__(cls)

    def fixture(self):
        f=preparation.Fixture(self.schema);self.addCleanup(f.close);return f

    def retired(self,f):
        self.assertIsNone(f.kernel._preparation_invocation)
        self.assertIsNone(f.owner._preparation_invocation)
        self.assertEqual(f.kernel._cpu_execution.mutating,0)
        self.assertNotIn(id(f.owner),cpu_execution._MUTATING_OWNERS)
        self.assertNotIn(id(f.store),cpu_execution._MUTATING_STORES)
        self.assertFalse(f.store._connection.in_transaction)

    def test_registered_prepare_releases_metadata_locks_before_owner_observation(self):
        f=self.fixture();original=f.view.observe;seen=[]
        def observe(context):
            self.assertIs(context,f.context)
            self.assertEqual(f.kernel._cpu_execution.mutating,1)
            self.assertIs(cpu_execution._MUTATING_OWNERS[id(f.owner)][0],f.owner)
            self.assertIs(cpu_execution._MUTATING_STORES[id(f.store)][0],f.store)
            locks=[]
            def other_thread():
                for lock in (cpu_execution._LIVENESS_LOCK,f.kernel._cpu_execution.lock):
                    acquired=lock.acquire(False);locks.append(acquired)
                    if acquired:lock.release()
            worker=threading.Thread(target=other_thread);worker.start();worker.join(5)
            self.assertFalse(worker.is_alive());self.assertEqual(locks,[True,True])
            self.assertFalse(f.store._connection.in_transaction);seen.append(True)
            return original(context)
        f.view.observe=observe;f.prepare();self.assertEqual(seen,[True]);self.retired(f)

    def test_same_store_other_coordinator_cannot_admit_while_preparation_mutates(self):
        f=self.fixture();other=transactions.KernelTransactions(f.store,f.codec,
            preparation.data.INSTALLATION,WindowsIdentityOwners(object()))
        original=f.view.observe;seen=[]
        def observe(context):
            with self.assertRaisesRegex(ContractError,'SHARED_MUTATION_BUSY'):
                other._cpu_execution.require_available()
            with self.assertRaisesRegex(ContractError,'STOPPED_OR_BUSY'):
                f.kernel._cpu_execution.require_available()
            seen.append(True);return original(context)
        f.view.observe=observe;f.prepare();self.assertEqual(seen,[True]);self.retired(f)
        other._cpu_execution.require_available()

    def test_final_writer_preserves_private_invocation_and_coordinator_registration(self):
        f=self.fixture();seen=[]
        def in_writer():
            token=f.kernel._preparation_invocation
            self.assertIs(token,f.owner._preparation_invocation)
            self.assertEqual(token.phase,'PREPARING');self.assertIs(token.context,f.context)
            self.assertTrue(f.store._connection.in_transaction)
            self.assertEqual(f.kernel._cpu_execution.mutating,1)
            self.assertEqual(f.native_calls,['owner-observe','binding-current']);seen.append(True)
        f.fault=in_writer;f.prepare();self.assertEqual(seen,[True]);self.retired(f)

    def test_authorized_nested_canonical_stop_prevents_preparation_without_consumption(self):
        f=self.fixture();original=f.view.observe;seen=[]
        def observe(context):
            value=original(context)
            f.kernel.stop_owner_authority(f.enrollment.request_id,f.context,'reason:joined-stop')
            seen.append(f.row()['state']);return value
        f.view.observe=observe
        with self.assertRaises(ContractError):f.prepare()
        self.assertEqual(seen,['STOPPED'])
        self.assertEqual(f.cell(logical_key('projection',preparation.data.PROJECT,'issuance',f.request.proposal_id)).generation,0)
        key=budget_key(grant_key_for(f.enrollment));_,_,held,charged=read_budget(f.cell(key).value_wire,key)
        self.assertEqual((held,charged),(ZERO_BUDGET,ZERO_BUDGET));self.retired(f)

    def test_denied_nested_stop_cannot_poison_selected_preparation(self):
        f=self.fixture();original=f.view.observe;denied=[]
        def observe(context):
            with self.assertRaises(ContractError):
                f.kernel.stop_owner_authority(f.enrollment.request_id,object(),'reason:denied-stop')
            denied.append(True);return original(context)
        f.view.observe=observe;result=f.prepare()
        self.assertEqual(denied,[True]);self.assertEqual(f.codec.decode(result.record_wire).as_dict()['status'],'PREPARED')
        self.assertEqual(f.row()['state'],'ACTIVE');self.assertFalse(f.kernel._cpu_execution.stopped.is_set())
        self.retired(f)

    def test_coordinator_constructor_control_failure_precedes_owner_binding(self):
        for kind in (KeyboardInterrupt,SystemExit,MemoryError):
            with self.subTest(kind=kind.__name__):
                f=self.fixture();original=f.owner._preparation_kernel;primary=kind('coordinator-construction')
                f.owner._preparation_kernel=None
                try:
                    with patch.object(transactions,'_CpuExecutionCoordinator',side_effect=primary):
                        try:transactions.KernelTransactions(f.store,f.codec,preparation.data.INSTALLATION,f.owner)
                        except BaseException as caught:self.assertIs(caught,primary)
                        else:self.fail('constructor must reject')
                    self.assertIsNone(f.owner._preparation_kernel)
                    self.assertFalse(f.store._closed);self.assertFalse(f.store._connection.in_transaction)
                    self.assertIsNone(f.owner._preparation_invocation)
                finally:f.owner._preparation_kernel=original
                self.retired(f)

    def test_primary_and_owner_cleanup_secondary_do_not_leak_mutation_registration(self):
        f=self.fixture();primary=KeyboardInterrupt('joined-observation');secondary=OSError('joined-retirement')
        original=owner_session.NativeCpuOwnerSession._end_preparation
        def observe(context):raise primary
        def ending(owner,token):original(owner,token);raise secondary
        f.view.observe=observe
        with patch.object(owner_session.NativeCpuOwnerSession,'_end_preparation',ending):
            try:f.prepare()
            except BaseException as caught:self.assertIs(caught,primary)
            else:self.fail('missing original primary')
        data=BaseException.__dict__['__dict__'].__get__(primary)
        self.assertIs(dict.__getitem__(data,'native_preparation_owner'),f.owner)
        self.assertEqual(dict.__getitem__(data,'native_preparation_cleanup_errors'),(secondary,))
        self.retired(f)

    def test_successful_preparation_does_not_open_dispatch_or_runtime(self):
        f=self.fixture();result=f.prepare()
        with self.assertRaises(ContractError):f.kernel.require_runtime_admission()
        with self.assertRaises(ContractError):f.kernel.consume(result.record_wire,f.context)
        self.assertIsNone(f.kernel._cpu_execution.active)
        self.assertEqual(f.kernel.recover_preparation(f.proposal.canonical_wire,f.context).canonical_wire,result.record_wire)
        self.retired(f)
