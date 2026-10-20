"""Owned SQLite/domain qualification; all process/profile/Hello/Set paths denied."""
from foundation_support import *
import importlib,threading,unittest
from unittest.mock import patch
label,cohort=sys.argv[1:3];assert label.replace('-','').isalnum()
D=R/label;D.mkdir();baseline=cohort=='baseline'
assert not baseline;product=Q
sys.path[:0]=[str(product/'src'),str(Q/'tests/contract'),str(product/'tests/contract')]
from ceta.store import sqlite_runtime
sqlite_runtime.load_sqlite()
from ceta.identity import native_approval,native_clock,native_owner_view
from ceta.effects.native_cpu_binding import NativeCpuBinding
from ceta.supervisor.windows_jobs import WindowsOwnedProcess
inputs=read(R/'INPUTS.json')
names=set(read(R/'ASSEMBLY.json')['payloads'])
before={n:ordinary(product/n) for n in names}
forbidden=[];executed=[];stopped=[];threads=set(threading.enumerate())
def deny(*args,**kwargs):forbidden.append('process-profile-auth-or-native-owner-allocation');raise AssertionError('OS5_FORBIDDEN_NATIVE_EFFECT')
from contextlib import ExitStack
with ExitStack() as guards:
 for target,name in ((subprocess,'Popen'),(WindowsOwnedProcess,'launch'),(native_approval.NativeApprovalOwner,'__init__'),
     (native_approval._NativeApi,'__init__'),(native_clock.NativeSessionClock,'__init__'),
     (native_owner_view._ViewAPI,'__init__'),(NativeCpuBinding,'__init__')):
  guards.enter_context(patch.object(target,name,deny))
 new=importlib.import_module('test_native_owner_preparation');new.ROOT=product;new.FIXTURES=D/'fixtures'
 modules=[new]
 if cohort=='joined':modules=[importlib.import_module('test_preparation_coordination')]
 if cohort=='connected':
  mirror=D/'fixtures'
  bytes_copy(product/'contracts/schemas/records.schema.json',mirror/'contracts/schemas/records.schema.json')
  for name in ('test_kernel_transactions','test_kernel_authority','test_owner_authority_transactions',
      'test_owner_session_cleanup','test_owner_session_context_boundary','test_owner_enrollment'):
   module=importlib.import_module(name);module.ROOT=mirror
   # Byte-exact schema mirror allows unchanged old test ASTs to allocate only R.
   modules.append(module)
 if cohort=='writerreentry':
  suite=unittest.TestSuite([new.NativeOwnerPreparationTests('test_existing_writer_callback_denies_before_native_observation_or_nested_sql')])
 elif cohort=='reentry':
  suite=unittest.TestSuite([new.NativeOwnerPreparationTests('test_private_reentry_cannot_publish_a_permit_from_clock_callback')])
 elif baseline:
  suite=unittest.TestSuite([new.NativeOwnerPreparationTests('test_real_canonical_approval_prepares_without_parallel_basis_cache')])
 else:
  groups=[]
  for m in modules:
   if cohort=='connected' and m.__name__=='test_kernel_authority':
    groups.append(unittest.defaultTestLoader.loadTestsFromTestCase(m.KernelCommitAuthorityTests))
   else:groups.append(unittest.defaultTestLoader.loadTestsFromModule(m))
  suite=unittest.TestSuite(groups)
 def ids(group):
  for item in group:
   if isinstance(item,unittest.TestSuite):yield from ids(item)
   else:yield item.id()
 expected=list(ids(suite));assert len(expected)==len(set(expected))
 class Result(unittest.TextTestResult):
  def startTest(self,test):executed.append(test.id());super().startTest(test)
  def stopTest(self,test):stopped.append(test.id());super().stopTest(test)
 started=utc()
 with (D/'tests.txt').open('x',encoding='utf8',buffering=1) as out:
  result=unittest.TextTestRunner(stream=out,verbosity=2,resultclass=Result).run(suite)
after={n:ordinary(product/n) for n in names}
remaining=[t.name for t in set(threading.enumerate())-threads if t.is_alive()]
imports={n:str(Path(m.__file__).resolve()) for n,m in sys.modules.items() if n=='ceta' or n.startswith('ceta.')
 if getattr(m,'__file__',None)}
assert all(Path(p).is_relative_to(product/'src') for p in imports.values())
passed=result.wasSuccessful() and not result.skipped and expected==executed==stopped and before==after
passed=passed and not remaining and not forbidden and all(f['closed'] and not f['transaction_open']
 and not f['kernel_invocation'] and not f['owner_invocation'] for f in new.FACTS)
write_new(D/'RESULT.json',dict(started_at=started,finished_at=utc(),cohort=cohort,product_root=str(product),tests_run=result.testsRun,
 expected_ids=expected,executed_ids=executed,stopped_ids=stopped,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
 failure_details=[dict(id=t.id(),traceback=trace) for t,trace in result.failures+result.errors],forbidden_calls=forbidden,
 remaining_threads=remaining,candidate_before=before,candidate_after=after,sqlite=sqlite_runtime.runtime_identity(),
 imports=imports,fixture_facts=new.FACTS,raw=reference(D/'tests.txt'),Source_conservation_gate=False,Source_application=False,
 qualification='Actual canonical SQLite and selected preparation code. Native owner/code/clock/target observations and genuine approval predicate are CONTROLLED; no native launch/profile/Hello/Set/full or live authority qualification.',
 explicitly_unexecuted=['test_kernel_authority.NativeAuthorityResolutionTests (3 native OwnedService methods; original development-root guard retained; no native launch authorized in this OS5 job).'] if cohort=='connected' else [],
 exit_status=0 if passed else 1))
print(json.dumps(dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
 forbidden_calls=forbidden,remaining_threads=remaining,exit_status=0 if passed else 1)))
sys.exit(0 if passed else 1)
