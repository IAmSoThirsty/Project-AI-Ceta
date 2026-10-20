"""Resolve the measured final initializer allocation gap; no other behavior."""
from foundation_support import *
import ast

p=Q/'src/ceta/kernel/transactions.py';old=p.read_text()
before="""        from ceta.identity.owner_session import NativeCpuOwnerSession
        if type(owners) is NativeCpuOwnerSession:
            NativeCpuOwnerSession._bind_preparation_kernel(owners, self)
            self._preparation_owner = owners
        self._preparation_check = (NativeCpuOwnerSession.require_prepared_basis.__get__(owners)
            if self._preparation_owner is not None else None)
"""
after="""        from ceta.identity.owner_session import NativeCpuOwnerSession
        self._preparation_check = None
        if type(owners) is NativeCpuOwnerSession:
            self._preparation_check = NativeCpuOwnerSession.require_prepared_basis.__get__(owners)
            self._preparation_owner = owners
            # Publish only after every initializer allocation and binding.
            NativeCpuOwnerSession._bind_preparation_kernel(owners, self)
"""
assert old.count(before)==1;new=old.replace(before,after,1);compile(new,str(p),'exec')
with p.open('wb') as stream:stream.write(new.encode('utf8'))
oracle=read(R/'INPUTS.json')['failure_probe'];source=safe_proof(oracle).read_text()
cls=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=='InitializerBindingTests')
literal=ast.get_source_segment(source,cls)
header='''"""Canonical SQLite constructor-publication regressions; native facts controlled."""
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

'''
more='''

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
'''
path=Q/'tests/contract/test_kernel_initializer_publication.py'
raw=(header+literal+'\n'+more).encode('utf8');compile(raw,str(path),'exec');fs.write_new(path,raw)
test=next(n for n in ast.parse(raw).body if isinstance(n,ast.ClassDef) and n.name=='InitializerBindingTests')
assert ast.dump(test,include_attributes=False)==ast.dump(cls,include_attributes=False)
write_new(R/'REPAIR.json',dict(at=utc(),parent_failure=read(R/'INPUTS.json')['failure_result'],
    source=ordinary(p),test=ordinary(path),exact_WT_oracle_AST=True,
    delta='Only precompute/store the captured preparation check and owner field before final owner/kernel publication.',
    no_borrowed_store_cleanup_or_authority_change=True,Source_publication=False))
print(json.dumps(dict(repaired_source=str(p),new_normative_tests=3,unchanged_reviewer_oracle=True)))
