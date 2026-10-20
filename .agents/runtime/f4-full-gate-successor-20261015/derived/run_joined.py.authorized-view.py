"""Execute the actual joined or published code with fresh disposable native fixtures."""
from foundation_support import *
from contextlib import redirect_stdout,redirect_stderr
import threading,types,unittest,importlib,pkgutil

mode,label=sys.argv[1:]
assert mode in ('targeted','destination') and label.replace('-','').isalnum()
S=Q if mode=='targeted' else F
outroot=__gate_output;outroot.mkdir(exist_ok=False)
temporary=outroot/'tmp';temporary.mkdir()
os.environ['TEMP']=os.environ['TMP']=str(temporary)
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
sys.path[:0]=[str(S/'src'),str(S/'tools'),str(S/'tests/contract')]
import ceta
all_modules=sorted('.'.join(path.relative_to(S/'src').parts[:-1]+(() if path.stem=='__init__' else (path.stem,)))
    for path in (S/'src/ceta').rglob('*.py'))
assert len(all_modules)==len(set(all_modules))==87
for name in all_modules:importlib.import_module(name)
# The canonical project DLL must load before test modules import stdlib sqlite3.
from ceta.store.sqlite_runtime import load_sqlite,runtime_identity
load_sqlite();sqlite_identity=runtime_identity()
joined=read(R/'STAGED-JOIN.json')
expected_pins={name:value['sha256'] for name,value in joined['candidate_payloads'].items()}
before={name:ordinary(S/name) for name in expected_pins}
assert len(before)==336 and {name:value['sha256'] for name,value in before.items()}==expected_pins
protected_source_before={name:ordinary(F/name) for name in joined['preserved_current_source']} if mode=='targeted' else None
auxiliary=read(R/'AUXILIARY-TEST-TOOLS.json')
auxiliary_before={name:ordinary(S/name) for name in auxiliary['members']}
assert all(row==auxiliary['members'][name]['candidate' if mode=='targeted' else 'source'] for name,row in auxiliary_before.items())


# Only the fixture-runtime ROOT constant is relocated. Actual product imports
# remain the exact S/src, including the current canonical Windows process owner.
isolation_harness=outroot/'isolation-harness'
native_runtime=isolation_harness/'.agents/runtime/ac1-20261014'
native_runtime.mkdir(parents=True);(native_runtime/'build-r2').mkdir()
fixture_source=F/'.agents/runtime/ac1-20261014/native_fixture_support.py'
binary=F/'.agents/runtime/ac1-20261014/build-r2/isolated_worker.exe'
assert sha(fixture_source)=='a7247426deee70890107b9d826c7cda9209015edd5f1192f93ee3bd1e5a4314f'
assert sha(binary)=='527518104fb84c430e3e9e0be61982c533b0c6fbb13e1a85e959ba1a3866ad0f'
bytes_copy(fixture_source,native_runtime/'native_fixture_support.py')
bytes_copy(binary,native_runtime/'build-r2/isolated_worker.exe')
for name in ('src/ceta/supervisor/windows_jobs.py','src/ceta/supervisor/isolated_worker.py'):
    bytes_copy(S/name,isolation_harness/name)
shim=types.ModuleType('ac_support')
shim.__dict__.update({key:value for key,value in globals().copy().items() if not key.startswith('_')})
shim.Q=S;shim.R=shim.D=native_runtime
sys.modules['ac_support']=shim
os.environ.update(CETA_AC1_RUNTIME_ROOT=str(native_runtime),CETA_AC3_TEST_ROOT=str(outroot),CETA_AC3_IMAGE=str(binary))
import test_isolated_worker
test_isolated_worker.ROOT=isolation_harness
import test_native_owner_view
test_native_owner_view.ROOT=outroot
import test_native_code_binding
test_native_code_binding.ROOT=outroot

# Fixture outputs are owned by this runtime, including the existing crash
# subprocess seam. Actual product imports and unmodified test method bodies
# continue to resolve against S; no candidate or Source fixtures are created.
fixture_root=S/'.agents/fixtures';fs.safe_components(fixture_root,allow_missing=True)
fixture_root.mkdir(parents=True,exist_ok=True);fs.safe_components(fixture_root)
class FixtureRoot:
    def __fspath__(self):return str(S)
    def __str__(self):return str(S)
    def __truediv__(self,value):
        value=str(value).replace('\\','/')
        if value=='.agents/fixtures':return fixture_root
        if value.startswith('.agents/fixtures/'):return fixture_root/value[len('.agents/fixtures/'):]
        return S/value
for module_name in ('test_windows_jobs','test_kernel_transactions','test_resource_reservations','test_owner_authority_transactions','test_windows_pipe'):
    importlib.import_module(module_name).ROOT=FixtureRoot()
child_scripts=outroot/'crash-fixture-scripts';child_scripts.mkdir()
proxy_source=("from pathlib import Path\nimport sys\nS=Path("+repr(str(S))+")\nD=Path("+repr(str(fixture_root))+")\n"
 "sys.path.append(str(S/'tests/contract'))\nclass FixtureRoot:\n def __fspath__(self):return str(S)\n def __str__(self):return str(S)\n"
 " def __truediv__(self,value):\n  value=str(value).replace('\\\\','/')\n"
 "  if value=='.agents/fixtures':return D\n"
 "  if value.startswith('.agents/fixtures/'):return D/value[len('.agents/fixtures/'):]\n"
 "  return S/value\nROOT=FixtureRoot()\n")
fs.write_new(child_scripts/'_fixture_paths.py',proxy_source.encode())
fixture_copies={}
for name in ('test_kernel_transactions.py','test_resource_reservations.py'):
    origin=S/'tests/contract'/name;body=origin.read_text(encoding='utf-8')
    assignment='ROOT = Path(__file__).resolve().parents[2]'
    assert body.count(assignment)==1
    target=child_scripts/name
    fs.write_new(target,body.replace(assignment,'from _fixture_paths import ROOT').encode())
    # Only a module-level fixture root assignment changes in these copies.
    import ast
    methods=lambda text:{node.name:ast.dump(node,include_attributes=False) for node in ast.walk(ast.parse(text))
       if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))}
    assert methods(body)==methods(target.read_text(encoding='utf-8'))
    fixture_copies[name]={'original':reference(origin),'copy':reference(target),'all_method_ASTs_unchanged':True}
import test_resource_reservations
fixture_commands=[]
real_subprocess=test_resource_reservations.subprocess
class FixtureSubprocess:
    def __getattr__(self,name):return getattr(real_subprocess,name)
    def Popen(self,argv,*args,**kwargs):
        actual=list(argv)
        if len(actual)>5 and actual[4]==str(S/'tests/contract/test_resource_reservations.py') and actual[5]=='--reservation-crash':
            actual[4]=str(child_scripts/'test_resource_reservations.py')
            fixture_commands.append({'original_requested_argv':list(argv),'actual_owned_fixture_argv':actual.copy()})
        return real_subprocess.Popen(actual,*args,**kwargs)
test_resource_reservations.subprocess=FixtureSubprocess()

import test_native_owner_approval as approval_tests
native_build_path=F/'.agents/runtime/na2-20261014/build-r1/build.json';native_build=read(native_build_path)
assert ordinary(native_build['native_executable']['path'])==native_build['native_executable']
assert sha(S/'native/windows_broker/owner_approval.cpp')==native_build['source']['sha256']
for cls,folder in ((approval_tests.NativeApprovalNativeTests,'cpu'),(approval_tests.NativeEnrollmentNativeTests,'enrollment')):
    fixture=outroot/('native-approval-'+folder);fixture.mkdir()
    cls.helper_path=native_build['native_executable']['path'];cls.helper_sha256=native_build['native_executable']['sha256']
    cls.fixture_root=fixture;cls.observations=[]
approval_tests.NativeEnrollmentNativeTests.helper_source_commitment='sha256:'+native_build['source']['sha256']

# Original component cohort IDs are retained rather than replaced by a guessed count.
cohort_inputs=read(R/'COHORT-INPUTS.json')
import ast,copy,ctypes as C
from unittest.mock import patch
from ceta.contracts.workload_throttling import CpuRateLimit
from ceta.contracts.wire import ContractError
from ceta.supervisor.windows_jobs import CPU_RATE_CONTROL
from test_windows_throttling import WindowsThrottleTests,NATIVE_RECEIPTS
sys.modules['review_support']=types.SimpleNamespace(Q=S)
oracle_refs={}
for oracle_name,oracle_path in (
    ('review_hostile',F/'.agents/runtime/wt1-20261014/independent-review/review_hostile.py'),
    ('hostile_native',F/'.agents/runtime/wt2-20261014/independent-root-review/hostile_native.py')):
    oracle_refs[oracle_name]=reference(oracle_path)
    spec=importlib.util.spec_from_file_location(oracle_name,oracle_path)
    loaded=importlib.util.module_from_spec(spec);sys.modules[oracle_name]=loaded;spec.loader.exec_module(loaded)
known_path=F/'.agents/runtime/wt3-20261014/independent-review/probe_known_exit.py'
assert sha(known_path)=='a8553c6e8744a31a7ca8d95becfbbbcf1d5d53354df5e1999bd43f856aae0dce'
known_class=next(node for node in ast.parse(known_path.read_text(encoding='utf-8')).body
    if isinstance(node,ast.ClassDef) and node.name=='KnownNaturalExitTests')
import time
observations=[]
exec(compile(ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(known_class)],type_ignores=[])),str(known_path),'exec'),globals())
oracle_refs['KnownNaturalExitTests']=dict(source=reference(known_path),class_AST_sha256=digest(ast.dump(known_class,include_attributes=False).encode()))
clock_oracle=F/'.agents/runtime/nc3-20261015/parent-probe-primary-cleanup.py'
independent_shim=types.ModuleType('run_independent');independent_shim.unittest=unittest;independent_shim.sys=sys
sys.modules['run_independent']=independent_shim
clock_spec=importlib.util.spec_from_file_location('nc2_parent_probe',clock_oracle)
clock_probe=importlib.util.module_from_spec(clock_spec);sys.modules['nc2_parent_probe']=clock_probe;clock_spec.loader.exec_module(clock_probe)
oracle_refs['nc2_parent_probe']=reference(clock_oracle)

# Reuse the actual compiled native observer, never an unbuilt or mocked sensor.
observer_reuse=F/'.agents/runtime/ob2-20261014/build-reuse/BUILD-REUSE.json'
observer_build=read(observer_reuse)
assert observer_build['status']=='BYTE_EXACT_REUSE_NO_NEW_COMPILATION'
assert ordinary(observer_build['native_image']['path'])==observer_build['native_image']
assert sha(S/'native/windows_broker/effect_observer.rs')==observer_build['candidate_source']['sha256']
os.environ.update(CETA_EFFECT_OBSERVER_EXE=observer_build['native_image']['path'],
    CETA_OWNED_WORKER_EXE=str(binary),
    CETA_OBSERVER_NEGATIVE_ROOT=str(F/'.agents/runtime/ob2-20261014/negative-reuse'))
import test_native_effect_observer as observer_tests
observer_tests.ROOT=FixtureRoot()
import test_isolation_token_diagnostics as diagnostic_tests
import test_native_owner_session as session_tests
session_tests.HELPER=native_build['native_executable']['path']
session_tests.HELPER_SHA=native_build['native_executable']['sha256']
session_tests.HELPER_SOURCE=native_build['source']['path']
session_tests.HELPER_SOURCE_SHA=native_build['source']['sha256']
session_tests.WORKER=binary;session_tests.WORKER_SHA=sha(binary)
session_tests.FIXTURES=outroot/'native-owner-session';session_tests.FIXTURES.mkdir()
import test_owned_cpu_outcome_transactions as outcome_tests
outcome_tests.ROOT=FixtureRoot()
import test_native_cpu_binding as cpu_binding_tests
for module_name in ('test_process_diagnostics','test_process_observation_timing','test_process_observation_validation',
                    'test_process_performance_comparison'):
    module=importlib.import_module(module_name)
    if hasattr(module,'ROOT'):module.ROOT=FixtureRoot()
if mode=='targeted':
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in cohort_inputs['module_names'])
    suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name) for name in cohort_inputs['runtime_oracle_ids'])
else:
    suite=unittest.defaultTestLoader.discover(str(S/'tests/contract'),pattern='test_*.py')
def ids(item):
    if isinstance(item,unittest.TestSuite):
        for child in item:yield from ids(child)
    else:yield item.id()
def flatten(group):
    for item in group:
        if isinstance(item,unittest.TestSuite):yield from flatten(item)
        else:yield item
all_cases=list(flatten(suite));full_expected_ids=[item.id() for item in all_cases]
assert len(full_expected_ids)==len(set(full_expected_ids)) and not any('_FailedTest' in name for name in full_expected_ids)
deferred_case='test_isolated_worker.NativeIsolatedWorkerTests.test_actual_nonpersistent_launch_denial_and_medium_control_retirement'
authorization_path=__gate_authorization_path;native_authorization=__gate_authorization
__gate_selected,deferred_ids=__gate_select(full_expected_ids,authorized=native_authorization is not None,partial=__gate_partial)
assert sum(name==deferred_case for name in full_expected_ids)==1
suite=unittest.TestSuite(item for item in all_cases if item.id() not in deferred_ids)
expected_ids=list(ids(suite))
if mode=='targeted':assert set(cohort_inputs['required_parent_ids'])|({deferred_case} if native_authorization else set())==set(expected_ids) and len(expected_ids)==1294+(1 if native_authorization else 0)


if mode=='destination':
    baseline=read(F/'.agents/runtime/perf1-20261014/active-application/destination-full-r1.json')['expected_ids']
    assert len(baseline)==1479 and set(baseline)<=set(full_expected_ids)
    assert full_expected_ids==read(R/'REQUIRED-SOURCE-TESTS.json')['required_ids']
executed,stopped=[],[]
native_stream=outroot/'native-lifetimes.jsonl'
with native_stream.open('x',encoding='utf-8') as stream:stream.flush();os.fsync(stream.fileno())
native_stream_rows=[]
def owned_process_facts(owner):
    return dict(pid=getattr(owner,'pid',None),creation_time=getattr(owner,'creation_time',None),
        image_sha256=getattr(owner,'image_sha256',None),lifetime_closed=owner.lifetime_closed,
        process_closed=owner._process is None,thread_closed=owner._thread is None,job_closed=owner._job is None)
class Result(unittest.TextTestResult):
    def startTest(self,test):
        global active_case_id
        active_case_id=test.id()
        if active_case_id==deferred_case:__execution_gate.enter(active_case_id)
        executed.append(test.id());super().startTest(test)
    def stopTest(self,test):
        stopped.append(test.id())
        rows=[dict(recorded_at=utc(),test_id=test.id(),**owned_process_facts(owner)) for owner in native_owners
            if owner_case_ids[id(owner)]==test.id()]
        if rows:
            with native_stream.open('a',encoding='utf-8') as stream:
                for row in rows:stream.write(json.dumps(row,allow_nan=False)+'\n')
                stream.flush();os.fsync(stream.fileno())
            native_stream_rows.extend(rows)
        super().stopTest(test)

# Test-owner observers delegate to the real objects. They do not mint authority.
from ceta.supervisor import isolated_worker as isolation, windows_jobs as jobs_native
from ceta.identity import native_clock, native_owner_view, native_code_binding
from ceta.store.journal import SqliteJournal
import functools
apis=[];api_case_ids={};native_owners=[];owner_case_ids={};clock_owners=[];store_bindings=[];code_bindings=[];journals=[];forbidden=[];active_case_id=None
api_init=isolation._IsolationAPI.__init__
def guarded_api(self,*args,**kwargs):
    api_init(self,*args,**kwargs);apis.append(self);api_case_ids[id(self)]=active_case_id
    if not native_authorization:
        def denied(*args):forbidden.append('restricted_CreateProcessW');raise AssertionError('NATIVE_OPERATOR_TEST_AUTHORITY_PENDING')
        self.CreateProcessW=denied
    else:
        self.CreateProcessW=__execution_gate.wrap_native_create(self.CreateProcessW,C.get_last_error,C.set_last_error)
    for operation in ('CreateAppContainerProfile','DeleteAppContainerProfile'):
        def denied_profile(*args,_operation=operation):forbidden.append(_operation);raise AssertionError('NO_PROFILE_MUTATION_IN_JOINED_RUNNER')
        setattr(self.userenv,operation,denied_profile)
isolation._IsolationAPI.__init__=guarded_api
def observe_constructor(cls,target,qualifies):
    original=cls.__init__
    @functools.wraps(original)
    def observed(self,*args,**kwargs):
        try:original(self,*args,**kwargs)
        finally:
            if qualifies(self):
                target.append(self)
                if cls is jobs_native.WindowsOwnedProcess:owner_case_ids[id(self)]=active_case_id
    cls.__init__=observed
observe_constructor(jobs_native.WindowsOwnedProcess,native_owners,lambda o:hasattr(o,'_process'))
observe_constructor(native_clock.NativeSessionClock,clock_owners,lambda o:hasattr(o,'_api') and hasattr(o,'_condition'))
observe_constructor(native_owner_view.NativeStoreBinding,store_bindings,lambda o:hasattr(o,'_api'))
observe_constructor(native_code_binding.NativeCodeBinding,code_bindings,lambda o:hasattr(o,'_api'))
observe_constructor(SqliteJournal,journals,lambda o:hasattr(o,'_closed'))

started=utc();threads_before=set(threading.enumerate())
write_new(outroot/'PREFLIGHT.json',{'started_at':started,'root':str(S),'mode':mode,'expected_ids':expected_ids,
    'expected_payload_hashes':expected_pins,'imported_product_modules':all_modules,
    'fixture_runtime':str(native_runtime),'full_expected_ids':full_expected_ids,'deferred_ids':deferred_ids,
    'native_execution_authorization':None if native_authorization is None else reference(authorization_path),
    'fixture_support_sha256':sha(native_runtime/'native_fixture_support.py'),
    'native_binary_sha256':sha(native_runtime/'build-r2/isolated_worker.exe'),
    'test_harness_change':'Only fixture outputs/ROOT and exact crash-child module ROOT assignment relocated; all product imports remain actual S/src.', 'fixture_copies':fixture_copies,'cohort_inputs':reference(R/'COHORT-INPUTS.json'),'unchanged_runtime_oracles':oracle_refs})
with (outroot/'tests.txt').open('x',encoding='utf-8',buffering=1) as raw:
    with redirect_stdout(raw),redirect_stderr(raw):
        result=unittest.TextTestRunner(stream=raw,verbosity=2,resultclass=Result).run(suite)
after={name:ordinary(S/name) for name in expected_pins}
protected_source_after={name:ordinary(F/name) for name in joined['preserved_current_source']} if mode=='targeted' else None
auxiliary_after={name:ordinary(S/name) for name in auxiliary['members']}
assert auxiliary_before==auxiliary_after
imports={name:ordinary(Path(module.__file__)) for name,module in sys.modules.items()
    if (name=='ceta' or name.startswith('ceta.')) and getattr(module,'__file__',None)}
assert all(Path(value['path']).is_relative_to(S/'src') for value in imports.values())
remaining=[{'name':thread.name,'native_id':thread.native_id} for thread in set(threading.enumerate())-threads_before if thread.is_alive()]
from test_windows_throttling import NATIVE_RECEIPTS
closed=all(row['all_owned_lifetimes_closed'] for row in NATIVE_RECEIPTS)

owner_facts=[dict(test_id=owner_case_ids[id(owner)],**owned_process_facts(owner)) for owner in native_owners]
clock_facts=[dict(state=o.status().state,registered=o.status().registration_owned,sampler_alive=o.status().sampler_alive,
    sampler_native_id=o.status().sampler_native_id) for o in clock_owners]
binding_facts=[dict(kind=kind,closed=o.closed,pending=o.pending_native_resources) for kind,objects in
    (('store',store_bindings),('code',code_bindings)) for o in objects]
api_facts=[dict(test_id=api_case_ids[id(o)],pending=o.pending_native_resources()) for o in apis]
journal_facts=[dict(path=str(o.path),closed=o._closed) for o in journals]
all_native_closed=all(o['lifetime_closed'] and o['process_closed'] and o['thread_closed'] and o['job_closed'] for o in owner_facts)
all_native_closed=all_native_closed and all(o['state']=='CLOSED' and not o['registered'] and not o['sampler_alive'] for o in clock_facts)
all_native_closed=all_native_closed and all(o['closed'] and not o['pending'] for o in binding_facts)
all_native_closed=all_native_closed and all(o['closed'] for o in journal_facts)
# These exact negative oracles preserve uncertain PRODUCT records after a
# controlled native free/delete response loss. They are not empty/closed records.
expected_uncertainty={'test_isolated_worker.NativeCleanupRecoveryTests.'+name for name in (
 'test_attribute_delete_then_failure_keeps_uncertainty_without_replay',
 'test_secondary_note_failure_never_replaces_primary_during_multiple_cleanup_failures',
 'test_sid_free_then_control_exception_never_replays_uncertain_free',
 'test_local_free_then_control_exception_is_not_repeated',
 'test_malformed_post_free_responses_remain_uncertain_without_double_free')}
expected_uncertainty|={'test_isolated_worker.NativeLocalAppDataTests.'+name for name in (
 'test_query_response_loss_retains_exact_primary_and_uncertain_allocation',
 'test_free_then_response_loss_is_not_repeated',
 'test_malformed_free_response_preserves_uncertainty_without_replay',
 'test_unknown_free_does_not_prevent_independent_native_handle_cleanup')}
api_accounted=all(not row['pending'] or (row['test_id'] in expected_uncertainty and all(
 item['retry']=='UNCERTAIN' and item['kind'] in ('attributes','sid','sid_text','known_folder_path') for item in row['pending'])) for row in api_facts)
environment_receipts=test_isolated_worker.NATIVE_ENVIRONMENT_RECEIPTS
allocation_receipts_complete=all(row['all_controlled_allocations_released'] for row in environment_receipts)
approval_native_closed=all(row['closed'] for row in approval_tests.NativeApprovalNativeTests.observations)
approval_native_closed=approval_native_closed and all(row['all_closed'] for row in approval_tests.NativeEnrollmentNativeTests.observations)

observer_native_closed=all(row['clock_closed'] and not row['cleanup_failures'] and
    all(target['lifetime_closed'] and target['remaining_query_exports']==0 for target in row['closed_targets'])
    for row in observer_tests.NATIVE_RECEIPTS)
observer_source_closed=all(row['all_exact_fixture_native_slots_closed'] for row in observer_tests.SOURCE_PIN_RECEIPTS)
session_native_closed=all(all(row[k] for k in ('owner_closed','code_closed','store_binding_closed','clock_closed','journal_closed'))
    and not row['cleanup_errors'] and all(c['closed'] and c['lifetime_closed'] for c in row['sessions'])
    and all(c['exit_code']==0 and c['streams_closed'] for c in row['client_lifetimes']) for row in session_tests.NATIVE_RECEIPTS)
binding_native_closed=all(row['worker_closed'] and row['process_closed'] and row['job_closed'] and row['thread_closed']
    and row['clock_status']=='CLOSED' and not row['clock_sampler_alive'] and not row['class15_write_calls'] for row in cpu_binding_tests.NATIVE_RECEIPTS)
all_query_exports_released=all(not getattr(owner,'_cpu_query_exports',[]) for owner in native_owners)
passed=observer_native_closed and observer_source_closed and session_native_closed and binding_native_closed and all_query_exports_released and result.wasSuccessful() and not result.skipped and expected_ids==executed==stopped and before==after and protected_source_before==protected_source_after and closed and all_native_closed and api_accounted and allocation_receipts_complete and approval_native_closed and not forbidden and not remaining
proof={'started_at':started,'finished_at':utc(),'mode':mode,'root':str(S),'tests_run':result.testsRun,
    'expected_ids':expected_ids,'full_expected_ids':full_expected_ids,'deferred_ids':deferred_ids,
    'native_execution_authorization':None if native_authorization is None else reference(authorization_path),'mandatory_full_gate_complete':not deferred_ids,
    'cohort_inputs':reference(R/'COHORT-INPUTS.json'),'required_parent_ids_retained':set(cohort_inputs['required_parent_ids'])<=set(expected_ids),
    'streamed_native_lifetimes':reference(native_stream),'streamed_native_lifetime_rows':native_stream_rows,
    'parent_native_clock_cleanup_observations':clock_probe.OBSERVATIONS,
    'stream_qualification':'Exact owned-process PID/creation and after-test custody facts; no historical r4 retirement backfill or PID-based cleanup.',
    'unchanged_runtime_oracles':oracle_refs,'known_exit_observations':observations,
    'observer_build':reference(observer_reuse),'observer_native_receipts':observer_tests.NATIVE_RECEIPTS,
    'observer_source_pin_receipts':observer_tests.SOURCE_PIN_RECEIPTS,'observer_native_closed':observer_native_closed,
    'observer_source_closed':observer_source_closed,'session_native_receipts':session_tests.NATIVE_RECEIPTS,
    'session_native_closed':session_native_closed,'cpu_binding_native_receipts':cpu_binding_tests.NATIVE_RECEIPTS,
    'cpu_binding_native_closed':binding_native_closed,'all_query_exports_released':all_query_exports_released,
    'isolation_token_diagnostics':diagnostic_tests.NATIVE_TOKEN_DIAGNOSTIC_RECEIPTS,
    'outcome_crash_observations':outcome_tests.CRASH_OBSERVATIONS,'outcome_cumulative_observations':outcome_tests.CUMULATIVE_OBSERVATIONS,
    'native_owners':owner_facts,'clock_owners':clock_facts,'retained_bindings':binding_facts,'native_apis':api_facts,'sqlite_journals':journal_facts,
    'all_owned_lifetimes_store_clock_bindings_closed':all_native_closed,
    'native_API_custody_accounted':api_accounted,'all_API_cleanup_records_empty':all(not row['pending'] for row in api_facts),
    'native_environment_receipts':environment_receipts,'all_controlled_allocations_released':allocation_receipts_complete,
    'native_approval_observations':approval_tests.NativeApprovalNativeTests.observations,
    'native_enrollment_observations':approval_tests.NativeEnrollmentNativeTests.observations,
    'all_native_approval_lifetimes_closed':approval_native_closed,'native_build':reference(native_build_path),'forbidden_calls':forbidden,'executed_ids':executed,'stopped_ids':stopped,'failures':len(result.failures),
    'errors':len(result.errors),'skips':len(result.skipped),'before':before,'after':after,
    'auxiliary_tools_before':auxiliary_before,'auxiliary_tools_after':auxiliary_after,
    'before_hashes':{name:value['sha256'] for name,value in before.items()},
    'after_hashes':{name:value['sha256'] for name,value in after.items()},'imports':imports,
    'all_product_module_count':len(all_modules),'sqlite_runtime_identity':sqlite_identity,
    'source_unchanged':before==after,'protected_source_before':protected_source_before,'protected_source_after':protected_source_after,
    'fixture_subprocess_commands':fixture_commands,'native_throttle_receipts':NATIVE_RECEIPTS,'all_native_throttle_lifetimes_closed':closed,
    'remaining_new_threads':remaining,'failure_details':[{'id':test.id(),'traceback':trace} for test,trace in result.failures+result.errors],
    'raw':reference(outroot/'tests.txt'),'exit_status':0 if passed else 1,
    'qualification':'Joined native libraries, pure contracts, actual disposable Windows resources and regression cases. Default public effect admission stays closed; genuine owner approval, positive worker isolation and governed real effect are not accepted here.'}
import dataclasses
def normalize(value):
    if dataclasses.is_dataclass(value):return normalize(dataclasses.asdict(value))
    if isinstance(value,bytes):return {'hex':value.hex(),'bytes':len(value),'sha256':digest(value)}
    if isinstance(value,dict):return {str(key):normalize(item) for key,item in value.items()}
    if isinstance(value,(list,tuple)):return [normalize(item) for item in value]
    return value
proof=normalize(proof)
proof['engineering_gate_status']='COMPLETE_TEST_RUN' if not deferred_ids else 'PARTIAL_NOT_ACCEPTED'
proof['operator_gate_provenance']=__gate_provenance
proof['precise_original_denial']=None if __execution_gate is None else __execution_gate.finish()
proof['Source_acceptance']=False
proof['F4_metadata109_unwaived']=True
write_new(outroot/'RESULT.json',proof)
print(json.dumps({key:proof[key] for key in ('mode','root','tests_run','failures','errors','skips','source_unchanged','exit_status')}),flush=True)
sys.exit(proof['exit_status'])
