"""Canonical SQLite constructor-publication regressions; native facts controlled."""
from pathlib import Path
import json,unittest
from unittest.mock import patch
import test_native_owner_preparation as preparation
from ceta.contracts.wire import ContractError
from ceta.identity import owner_session
from ceta.identity.owners import WindowsIdentityOwners
from ceta.kernel import transactions
Q=Path(__file__).resolve().parents[2]
FACTS=[]

class InitializerBindingTests(unittest.TestCase):
    def test_failed_final_bound_method_allocation_must_leave_owner_unbound(self):
        schema = json.loads((Q / 'contracts/schemas/records.schema.json').read_bytes())
        for kind in (KeyboardInterrupt, SystemExit, MemoryError):
            with self.subTest(kind=kind.__name__):
                f = preparation.Fixture(schema)
                original = f.owner._preparation_kernel
                f.owner._preparation_kernel = None
                primary = kind('CONTROLLED final bound-method allocation refusal')
                captures = []
                class BindingRefusal:
                    def __get__(self, owner, cls=None):
                        if owner is None: return self
                        captures.append(owner)
                        raise primary
                try:
                    with patch.object(owner_session.NativeCpuOwnerSession, 'require_prepared_basis', BindingRefusal()):
                        try:
                            transactions.KernelTransactions(f.store, f.codec, preparation.data.INSTALLATION, f.owner)
                        except BaseException as caught:
                            self.assertIs(caught, primary)
                        else: self.fail('original constructor must reject')
                    poisoned = f.owner._preparation_kernel
                    retry_error = None
                    try: transactions.KernelTransactions(f.store, f.codec, preparation.data.INSTALLATION, f.owner)
                    except BaseException as caught: retry_error = caught
                    row = dict(control=kind.__name__, exact_primary=True, manual_binding_calls=len(captures),
                        exact_owner=captures == [f.owner], owner_unbound=poisoned is None,
                        incomplete_kernel_id=id(poisoned), original_kernel_id=id(original),
                        published_kernel_is_original=poisoned is original,
                        bound_kernel_missing_preparation_check=poisoned is not None and not hasattr(poisoned, '_preparation_check'),
                        next_constructor_error=str(retry_error) if retry_error is not None else None,
                        borrowed_store_stays_open=not f.store._closed,
                        borrowed_connection_object_id=id(f.store._connection),
                        borrowed_connection_executes_select=f.store._connection.execute('SELECT 1').fetchone() == (1,),
                        transaction_open=f.store._connection.in_transaction,
                        fixture_controlled_native_and_approval=True, actual_native_calls=0)
                    FACTS.append(row)
                    self.assertIsNone(poisoned, 'Failed final binding must not publish an incomplete kernel onto the owner')
                finally:
                    # Only this controlled fixture's original owner link is
                    # restored to retire its borrowed test store normally.
                    f.owner._preparation_kernel = original
                    f.close()


class InitializerPublicationTests(unittest.TestCase):
    def schema(self):
        return json.loads((Q/'contracts/schemas/records.schema.json').read_bytes())

    def test_refused_descriptor_then_positive_reuse_publishes_only_a_complete_kernel(self):
        for kind in (KeyboardInterrupt,SystemExit,MemoryError):
            with self.subTest(kind=kind.__name__):
                f=preparation.Fixture(self.schema());original=f.owner._preparation_kernel
                f.owner._preparation_kernel=None;primary=kind('controlled allocation refusal')
                class Refusal:
                    def __get__(self,owner,cls=None):
                        if owner is None:return self
                        raise primary
                try:
                    with patch.object(owner_session.NativeCpuOwnerSession,'require_prepared_basis',Refusal()):
                        try:transactions.KernelTransactions(f.store,f.codec,preparation.data.INSTALLATION,f.owner)
                        except BaseException as caught:self.assertIs(caught,primary)
                        else:self.fail('missing exact original primary')
                    self.assertIsNone(f.owner._preparation_kernel)
                    self.assertFalse(f.store._closed)
                    self.assertEqual(f.store._connection.execute('SELECT 1').fetchone(),(1,))
                    self.assertFalse(f.store._connection.in_transaction)
                    publish=owner_session.NativeCpuOwnerSession._bind_preparation_kernel;seen=[]
                    def complete(owner,kernel):
                        self.assertIsNone(owner._preparation_kernel)
                        self.assertIs(kernel._preparation_owner,owner)
                        self.assertIs(kernel._preparation_check.__self__,owner)
                        self.assertIs(kernel._preparation_check.__func__,owner_session.NativeCpuOwnerSession.require_prepared_basis)
                        self.assertIs(kernel._cpu_execution.kernel,kernel)
                        self.assertIs(kernel._cpu_execution.store,f.store)
                        self.assertIsNone(kernel._preparation_invocation)
                        self.assertIsNotNone(kernel._events)
                        self.assertIsNotNone(kernel._control);self.assertIsNotNone(kernel._registry)
                        seen.append(kernel);return publish(owner,kernel)
                    with patch.object(owner_session.NativeCpuOwnerSession,'_bind_preparation_kernel',complete):
                        retry=transactions.KernelTransactions(f.store,f.codec,preparation.data.INSTALLATION,f.owner)
                    self.assertEqual(seen,[retry]);self.assertIs(f.owner._preparation_kernel,retry)
                    result=retry.prepare(f.proposal.canonical_wire,f.context)
                    self.assertEqual(f.codec.decode(result.record_wire).as_dict()['status'],'PREPARED')
                    self.assertIsNone(retry._preparation_invocation)
                    self.assertIsNone(f.owner._preparation_invocation)
                    self.assertFalse(f.store._connection.in_transaction)
                    self.assertEqual(retry._cpu_execution.mutating,0)
                    with self.assertRaises(ContractError):retry.require_runtime_admission()
                finally:
                    f.owner._preparation_kernel=original;f.close()

    def test_non_native_constructor_preserves_closed_defaults_and_borrowed_store(self):
        f=preparation.Fixture(self.schema())
        try:
            default=WindowsIdentityOwners(object())
            kernel=transactions.KernelTransactions(f.store,f.codec,preparation.data.INSTALLATION,default)
            self.assertIsNone(kernel._preparation_owner);self.assertIsNone(kernel._preparation_check)
            self.assertIsNone(kernel._preparation_invocation)
            self.assertIs(f.owner._preparation_kernel,f.kernel)
            self.assertIs(kernel._store,f.store);self.assertFalse(f.store._closed)
            self.assertEqual(f.store._connection.execute('SELECT 1').fetchone(),(1,))
            self.assertFalse(f.store._connection.in_transaction)
            with self.assertRaises(ContractError):kernel.require_runtime_admission()
        finally:f.close()
