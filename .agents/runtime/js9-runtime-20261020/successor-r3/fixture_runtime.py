"""Existing F4 native fixture wiring for the joined root; no authority issuer.

Called only inside a separately released full-run child. NativeCaseGate is
owned and independently reviewed in native-gate, outside this writer scope.
"""
from pathlib import Path
import importlib
import os
import sys
import types
import functools
from unittest.mock import patch
from js9_support import s, Q as AMENDED_Q


def prepare(root, output, gate):
    F, S, outroot = s.F, Path(root), Path(output)
    assert S in (s.F, AMENDED_Q) and outroot.is_relative_to(s.R)
    fs, sha, ordinary, bytes_copy = s.fs, s.sha, s.ordinary, s.bytes_copy
    from js9_support import packet
    capacity=packet()['fixture_dependencies']['capacity']
    assert ordinary(Path(capacity['path']))==capacity
    os.environ.update(CETA_CPU_CAPACITY_NATIVE='1',CETA_OUTCOME_CAPACITY_NATIVE='1',
        CETA_OUTCOME_CAPACITY_HELPER=capacity['path'],CETA_OUTCOME_CAPACITY_SHA256=capacity['sha256'],
        CETA_OUTCOME_CAPACITY_FIXTURES=str(outroot/'native-capacity'),
        CETA_JS9_FIXTURE_ROOT=str(outroot/'controlled-composition'))
    (outroot/'native-capacity').mkdir();(outroot/'controlled-composition').mkdir()
    # Both unchanged native classes create their own fixture directory with
    # exist_ok=False. Select a distinct owned environment path before invoking
    # each original setUpClass body; no method/assertion is substituted.
    capacity_tests=importlib.import_module('test_outcome_capacity')
    capacity_setup_bindings=[]
    for selected_class in (capacity_tests.NativeOutcomeCapacityTests,capacity_tests.NativeCapacityCustodyTests):
        original_setup=selected_class.setUpClass.__func__
        def owned_setup(cls,_original=original_setup):
            location=outroot/'native-capacity'/cls.__name__
            prior=os.environ['CETA_OUTCOME_CAPACITY_FIXTURES']
            os.environ['CETA_OUTCOME_CAPACITY_FIXTURES']=str(location)
            try:
                capacity_setup_bindings.append(dict(class_name=cls.__name__,fixture_root=str(location),original_body_called=True))
                return _original(cls)
            finally:os.environ['CETA_OUTCOME_CAPACITY_FIXTURES']=prior
        selected_class.setUpClass=classmethod(owned_setup)
    isolation_harness = outroot/'isolation-harness'
    native_runtime = isolation_harness/'.agents/runtime/ac1-20261014'
    native_runtime.mkdir(parents=True); (native_runtime/'build-r2').mkdir()
    source = F/'.agents/runtime/ac1-20261014/native_fixture_support.py'
    binary = F/'.agents/runtime/ac1-20261014/build-r2/isolated_worker.exe'
    assert sha(source) == 'a7247426deee70890107b9d826c7cda9209015edd5f1192f93ee3bd1e5a4314f'
    assert sha(binary) == '527518104fb84c430e3e9e0be61982c533b0c6fbb13e1a85e959ba1a3866ad0f'
    bytes_copy(source,native_runtime/'native_fixture_support.py')
    bytes_copy(binary,native_runtime/'build-r2/isolated_worker.exe')
    for name in ('src/ceta/supervisor/windows_jobs.py','src/ceta/supervisor/isolated_worker.py'):
        bytes_copy(S/name,isolation_harness/name)
    shim = types.ModuleType('ac_support')
    shim.__dict__.update({key:value for key,value in s.__dict__.items() if not key.startswith('_')})
    shim.Q=S; shim.R=shim.D=native_runtime; sys.modules['ac_support']=shim
    os.environ.update(CETA_AC1_RUNTIME_ROOT=str(native_runtime),CETA_AC3_TEST_ROOT=str(outroot),CETA_AC3_IMAGE=str(binary))
    isolation_tests=importlib.import_module('test_isolated_worker')
    isolation_tests.ROOT=isolation_harness
    isolation=importlib.import_module('ceta.supervisor.isolated_worker')
    original_api_init=isolation._IsolationAPI.__init__
    def guarded_api(api,*args,**kwargs):
        original_api_init(api,*args,**kwargs)
        gate.guard_isolation_api(api)
    isolation._IsolationAPI.__init__=guarded_api
    sys.path.insert(0,str(native_runtime))
    helper=importlib.import_module('native_fixture_support')
    assert Path(helper.__file__)==native_runtime/'native_fixture_support.py'
    gate.bind_helper(helper)
    importlib.import_module('test_native_owner_view').ROOT=outroot
    importlib.import_module('test_native_code_binding').ROOT=outroot

    # These are the existing root-guarded fixture locations, never a live
    # application profile or an old fixture selected by PID/path.
    fixture_root=S/'.agents/fixtures'; fs.safe_components(fixture_root,allow_missing=True)
    fixture_root.mkdir(parents=True,exist_ok=True); fs.safe_components(fixture_root)
    class FixtureRoot:
        def __fspath__(self):return str(S)
        def __str__(self):return str(S)
        def __truediv__(self,value):
            value=str(value).replace('\\','/')
            if value=='.agents/fixtures':return fixture_root
            if value.startswith('.agents/fixtures/'):return fixture_root/value[len('.agents/fixtures/'):]
            return S/value
    importlib.import_module('test_native_owner_preparation').FIXTURES=outroot/'owner-preparation'
    for name in ('test_windows_jobs','test_kernel_transactions','test_resource_reservations','test_owner_authority_transactions','test_windows_pipe',
                 'test_owned_cpu_outcome_transactions','test_native_effect_observer'):
        importlib.import_module(name).ROOT=FixtureRoot()
    child_scripts=outroot/'crash-fixture-scripts'; child_scripts.mkdir()
    proxy=("from pathlib import Path\nimport sys\nS=Path("+repr(str(S))+")\nD=Path("+repr(str(fixture_root))+")\n"
        "sys.path.append(str(S/'tests/contract'))\nclass FixtureRoot:\n def __fspath__(self):return str(S)\n def __str__(self):return str(S)\n"
        " def __truediv__(self,value):\n  value=str(value).replace('\\\\','/')\n"
        "  if value=='.agents/fixtures':return D\n"
        "  if value.startswith('.agents/fixtures/'):return D/value[len('.agents/fixtures/'):]\n"
        "  return S/value\nROOT=FixtureRoot()\n")
    fs.write_new(child_scripts/'_fixture_paths.py',proxy.encode())
    import ast
    fixture_copies={}
    for name in ('test_kernel_transactions.py','test_resource_reservations.py'):
        origin=S/'tests/contract'/name; raw=origin.read_text(encoding='utf8')
        assignment='ROOT = Path(__file__).resolve().parents[2]'; assert raw.count(assignment)==1
        target=child_scripts/name
        fs.write_new(target,raw.replace(assignment,'from _fixture_paths import ROOT').encode())
        methods=lambda text:{n.name:ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(text))
                            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
        assert methods(raw)==methods(target.read_text(encoding='utf8'))
        fixture_copies[name]=dict(original=s.reference(origin),copy=s.reference(target),all_method_ASTs_unchanged=True)
    reservation_tests=importlib.import_module('test_resource_reservations')
    original_subprocess=reservation_tests.subprocess; commands=[]
    class FixtureSubprocess:
        def __getattr__(self,name):return getattr(original_subprocess,name)
        def Popen(self,argv,*args,**kwargs):
            actual=list(argv)
            if len(actual)>5 and actual[4]==str(S/'tests/contract/test_resource_reservations.py') and actual[5]=='--reservation-crash':
                actual[4]=str(child_scripts/'test_resource_reservations.py')
                commands.append(dict(original_requested_argv=list(argv),actual_owned_fixture_argv=actual.copy()))
            return original_subprocess.Popen(actual,*args,**kwargs)
    reservation_tests.subprocess=FixtureSubprocess()

    approval_tests=importlib.import_module('test_native_owner_approval')
    build_path=F/'.agents/runtime/na2-20261014/build-r1/build.json'; build=s.read(build_path)
    assert ordinary(build['native_executable']['path'])==build['native_executable']
    assert sha(S/'native/windows_broker/owner_approval.cpp')==build['source']['sha256']
    for cls,folder in ((approval_tests.NativeApprovalNativeTests,'cpu'),(approval_tests.NativeEnrollmentNativeTests,'enrollment')):
        directory=outroot/('native-approval-'+folder); directory.mkdir()
        cls.helper_path=build['native_executable']['path']; cls.helper_sha256=build['native_executable']['sha256']
        cls.fixture_root=directory; cls.observations=[]
    approval_tests.NativeEnrollmentNativeTests.helper_source_commitment='sha256:'+build['source']['sha256']
    observer_reuse=F/'.agents/runtime/ob2-20261014/build-reuse/BUILD-REUSE.json'
    observer_build=s.read(observer_reuse)
    assert observer_build['status']=='BYTE_EXACT_REUSE_NO_NEW_COMPILATION'
    assert ordinary(observer_build['native_image']['path'])==observer_build['native_image']
    assert sha(S/'native/windows_broker/effect_observer.rs')==observer_build['candidate_source']['sha256']
    os.environ.update(CETA_EFFECT_OBSERVER_EXE=observer_build['native_image']['path'],CETA_OWNED_WORKER_EXE=str(binary),
        CETA_OBSERVER_NEGATIVE_ROOT=str(F/'.agents/runtime/ob2-20261014/negative-reuse'))
    sessions=importlib.import_module('test_native_owner_session')
    sessions.HELPER=build['native_executable']['path']; sessions.HELPER_SHA=build['native_executable']['sha256']
    sessions.HELPER_SOURCE=build['source']['path']; sessions.HELPER_SOURCE_SHA=build['source']['sha256']
    sessions.WORKER=binary; sessions.WORKER_SHA=sha(binary)
    sessions.FIXTURES=outroot/'native-owner-session'; sessions.FIXTURES.mkdir()
    for name in ('test_process_diagnostics','test_process_observation_timing','test_process_observation_validation','test_process_performance_comparison'):
        module=importlib.import_module(name)
        if hasattr(module,'ROOT'):module.ROOT=FixtureRoot()
    return dict(fixture_copies=fixture_copies,fixture_commands=commands,capacity_setup_bindings=capacity_setup_bindings,
        native_helper=ordinary(binary),approval_build=s.reference(build_path),observer_build=s.reference(observer_reuse))


def configure_suite(suite):
    """The one previously approved, already injected nonnative arithmetic seam."""
    import unittest
    from ceta.kernel import cpu_execution as execution
    module=importlib.import_module('test_cpu_execution_admission')
    name='test_operation_wall_budget_bounds_total_admission_separately_from_native_duration'
    evidence=[]
    def leaves(group):
        if isinstance(group,unittest.TestSuite):
            for child in group:yield from leaves(child)
        else:yield group
    selected=[test for test in leaves(suite) if test.__class__ is module.CpuExecutionAdmissionTests and test._testMethodName==name]
    assert len(selected)==1
    def controlled(self):
        method=getattr(module.CpuExecutionAdmissionTests,name).__get__(self)
        values=[execution.time.perf_counter_ns()]
        def elapsed():values.append(values[-1]+1000);return values[-1]
        with patch.object(execution.time,'perf_counter_ns',side_effect=elapsed):
            try:return method()
            finally:evidence.append(dict(id=self.id(),samples=values,quantum_ns=1000,
                original_method_body_unchanged=True,scope='Existing controlled nonnative arithmetic only; no native clock substitution'))
    setattr(selected[0],name,types.MethodType(controlled,selected[0]))
    return evidence


def native_report_data(value):
    """Lossless JSON values for the exact native receipt types; no authority.

    Bytes retain their full hexadecimal payload, length and digest. The four
    typed value records retain their qualified type and every dataclass field.
    Unknown types, non-string keys, non-finite numbers and cycles fail closed.
    Tuple sequences follow JSON's existing array representation. Input objects
    are only read; no as_dict, deepcopy, repr or string-conversion hook runs.
    """
    import hashlib
    import math
    from dataclasses import fields
    from ceta.contracts.temporal import ClockSample
    from ceta.contracts.resource_management import ObservationState, ProcessResourceIdentity
    from ceta.contracts.workload_throttling import CpuRateLimit, CpuRateObservation
    records = (ClockSample, ProcessResourceIdentity, CpuRateLimit, CpuRateObservation)
    active = set()

    def encode(item, path):
        kind = type(item)
        if item is None or any(kind is known for known in (str, bool, int)):
            return item
        if kind is float:
            if not math.isfinite(item):
                raise ValueError('NATIVE_REPORT_NONFINITE at ' + path)
            return item
        if kind is bytes:
            return {'encoding': 'hex', 'hex': item.hex(), 'bytes': len(item),
                    'sha256': hashlib.sha256(item).hexdigest()}
        if kind is ObservationState:
            return item.value
        if not any(kind is known for known in (dict, list, tuple, *records)):
            raise TypeError('NATIVE_REPORT_UNSUPPORTED at ' + path)
        identity = id(item)
        if identity in active:
            raise ValueError('NATIVE_REPORT_CYCLE at ' + path)
        active.add(identity)
        try:
            if kind is dict:
                if any(type(key) is not str for key in item):
                    raise TypeError('NATIVE_REPORT_NONSTRING_KEY at ' + path)
                return {key: encode(child, path + '[' + ascii(key) + ']')
                        for key, child in item.items()}
            if kind is list or kind is tuple:
                return [encode(child, path + '[' + str(index) + ']')
                        for index, child in enumerate(item)]
            return {'dataclass': kind.__module__ + '.' + kind.__qualname__,
                    'fields': {field.name: encode(object.__getattribute__(item, field.name),
                                                 path + '.' + field.name)
                               for field in fields(kind)}}
        finally:
            active.remove(identity)

    return encode(value, '$')


class NativeObservations:
    """The existing F4 exact-owner observation; no numeric-PID adoption."""
    def __init__(self):
        self.active_case = None
        self.owners, self.clocks, self.stores, self.codes, self.journals, self.apis = [], [], [], [], [], []
        self.originals = []

    def install(self):
        from ceta.supervisor import isolated_worker, windows_jobs
        from ceta.identity import native_clock, native_owner_view, native_code_binding
        from ceta.store.journal import SqliteJournal
        def observe(cls, target, qualifies):
            original = cls.__init__
            def expose(primary, owner, secondary, attempted):
                try:
                    data=BaseException.__dict__['__dict__'].__get__(primary)
                    dict.update(data,review_observation_owner=owner,
                        review_observation_registration_error=secondary,
                        review_observation_retirement_attempted=attempted,
                        review_observation_automatic_retry=False)
                except BaseException:
                    pass
            @functools.wraps(original)
            def wrapped(owner, *args, **kwargs):
                try:
                    original(owner, *args, **kwargs)
                except BaseException as primary:
                    secondary=None
                    try:
                        if qualifies(owner):target.append((self.active_case, owner))
                    except BaseException as error:secondary=error
                    expose(primary,owner,secondary,False)
                    raise
                try:
                    if qualifies(owner):
                        target.append((self.active_case, owner))
                except BaseException as primary:
                    secondary=None;attempted=False
                    try:
                        close=getattr(owner,'close',None)
                        if not callable(close):close=owner.retry_cleanup
                        attempted=True
                        close()
                    except BaseException as error:secondary=error
                    expose(primary,owner,secondary,attempted)
                    raise
            self.originals.append((cls, original, wrapped))
            cls.__init__ = wrapped
        observe(windows_jobs.WindowsOwnedProcess, self.owners, lambda o:hasattr(o, '_process'))
        observe(native_clock.NativeSessionClock, self.clocks, lambda o:hasattr(o, '_api') and hasattr(o, '_condition'))
        observe(native_owner_view.NativeStoreBinding, self.stores, lambda o:hasattr(o, '_api'))
        observe(native_code_binding.NativeCodeBinding, self.codes, lambda o:hasattr(o, '_api'))
        observe(SqliteJournal, self.journals, lambda o:hasattr(o, '_closed'))
        observe(isolated_worker._IsolationAPI,self.apis,lambda o:True)

    def uninstall(self):
        # The gate's constructor wrapper is local to this disposable runner;
        # remove it together with our observations after all original cleanup.
        for cls, original, _ in reversed(self.originals):
            cls.__init__ = original

    def finish(self):
        owner_rows = [dict(test_id=case,pid=o.pid,creation_time=o.creation_time,
            image_sha256=o.image_sha256,lifetime_closed=o.lifetime_closed,
            process_closed=o._process is None,thread_closed=o._thread is None,job_closed=o._job is None,
            remaining_query_exports=len(getattr(o,'_cpu_query_exports',[]))) for case,o in self.owners]
        clocks = []
        for case, owner in self.clocks:
            status = owner.status()
            clocks.append(dict(test_id=case,state=status.state,registered=status.registration_owned,
                sampler_alive=status.sampler_alive,sampler_native_id=status.sampler_native_id))
        bindings = [dict(test_id=case,kind=kind,closed=o.closed,pending=o.pending_native_resources,
            controlled_API=(kind=='store' and o._api is not None and type(o._api).__name__=='SimpleNamespace'))
            for kind,items in (('store',self.stores),('code',self.codes)) for case,o in items]
        apis = [dict(test_id=case,pending=o.pending_native_resources()) for case,o in self.apis]
        journals = [dict(test_id=case,path=str(o.path),closed=o._closed) for case,o in self.journals]
        allowed = {'test_isolated_worker.NativeCleanupRecoveryTests.'+name for name in (
            'test_attribute_delete_then_failure_keeps_uncertainty_without_replay',
            'test_secondary_note_failure_never_replaces_primary_during_multiple_cleanup_failures',
            'test_sid_free_then_control_exception_never_replays_uncertain_free',
            'test_local_free_then_control_exception_is_not_repeated',
            'test_malformed_post_free_responses_remain_uncertain_without_double_free')}
        allowed |= {'test_isolated_worker.NativeLocalAppDataTests.'+name for name in (
            'test_query_response_loss_retains_exact_primary_and_uncertain_allocation',
            'test_free_then_response_loss_is_not_repeated',
            'test_malformed_free_response_preserves_uncertainty_without_replay',
            'test_unknown_free_does_not_prevent_independent_native_handle_cleanup')}
        accounted = all(not row['pending'] or (row['test_id'] in allowed and all(
            item['retry']=='UNCERTAIN' and item['kind'] in ('attributes','sid','sid_text','known_folder_path')
            for item in row['pending'])) for row in apis)
        approval = importlib.import_module('test_native_owner_approval')
        effect = importlib.import_module('test_native_effect_observer')
        session = importlib.import_module('test_native_owner_session')
        binding = importlib.import_module('test_native_cpu_binding')
        isolation = importlib.import_module('test_isolated_worker')
        throttling = importlib.import_module('test_windows_throttling')
        admission = importlib.import_module('test_cpu_execution_admission')
        capacity = importlib.import_module('test_outcome_capacity')
        connection = importlib.import_module('test_cpu_capacity_connection')
        composition = importlib.import_module('test_native_runtime_composition')
        obligations = dict(
            exact_process_job_handles_closed=all(all(row[k] for k in ('lifetime_closed','process_closed','thread_closed','job_closed'))
                and row['remaining_query_exports']==0 for row in owner_rows),
            clocks_retired=all(row['state']=='CLOSED' and not row['registered'] and not row['sampler_alive'] for row in clocks),
            bindings_closed=all(row['closed'] and not row['pending'] or
                row['controlled_API'] and row['kind']=='store' and row['test_id']==
                'test_native_runtime_composition.NativeRuntimeCompositionTests.test_interrupted_native_open_preserves_unknown_output_without_false_closure'
                and not row['closed'] and len(row['pending'])==1 and row['pending'][0]['kind']=='file_open'
                and row['pending'][0]['retry']=='UNCERTAIN' and row['pending'][0]['handle'] is None
                for row in bindings),
            pending_API_custody_accounted=accounted,
            controlled_allocations_released=all(row['all_controlled_allocations_released'] for row in isolation.NATIVE_ENVIRONMENT_RECEIPTS),
            approval_lifetimes_closed=all(row['closed'] for row in approval.NativeApprovalNativeTests.observations)
                and all(row['all_closed'] for row in approval.NativeEnrollmentNativeTests.observations),
            observer_lifetimes_closed=all(row['clock_closed'] and not row['cleanup_failures'] and all(
                target['lifetime_closed'] and target['remaining_query_exports']==0 for target in row['closed_targets']) for row in effect.NATIVE_RECEIPTS),
            observer_source_handles_closed=all(row['all_exact_fixture_native_slots_closed'] for row in effect.SOURCE_PIN_RECEIPTS),
            session_lifetimes_closed=all(all(row[k] for k in ('owner_closed','code_closed','store_binding_closed','clock_closed','journal_closed'))
                and not row['cleanup_errors'] and all(c['closed'] and c['lifetime_closed'] for c in row['sessions'])
                and all(c['exit_code']==0 and c['streams_closed'] for c in row['client_lifetimes']) for row in session.NATIVE_RECEIPTS),
            CPU_binding_lifetimes_closed=all(all(row[k] for k in ('worker_closed','process_closed','job_closed','thread_closed'))
                and row['clock_status']=='CLOSED' and not row['clock_sampler_alive'] and not row['class15_write_calls'] for row in binding.NATIVE_RECEIPTS),
            throttling_lifetimes_closed=all(row['all_owned_lifetimes_closed'] for row in throttling.NATIVE_RECEIPTS),
            admission_lifetimes_closed=all(all(row[k] for k in ('lifetime_closed','process_closed','thread_closed','job_closed'))
                and row['clock_state']=='CLOSED' for row in admission.NATIVE_ADMISSION_RECEIPTS),
            native_capacity_lifetimes_closed=bool(capacity.NATIVE_RECEIPTS) and all(
                row.get('connection_closed')=='CLOSED' and row.get('vfs_closed') is True
                and 'pending' not in row for row in capacity.NATIVE_RECEIPTS),
            native_capacity_custody_retired=bool(capacity.NATIVE_CUSTODY_RECEIPTS) and all(
                row['native_after_fixture_cleanup']['state']==4 and not row['registered_after_fixture_cleanup']
                for row in capacity.NATIVE_CUSTODY_RECEIPTS),
            connection_fixture_lifetimes_closed=bool(connection.FACTS) and all(
                row['sqlite_closed'] and row['connection_state']=='CLOSED' and row['vfs_closed'] for row in connection.FACTS),
            composition_journals_closed=len(composition.FACTS)==45 and all(
                row['sqlite_closed'] and row['connection_close_state']=='CLOSED' for row in composition.FACTS))
        return native_report_data(dict(native_owners=owner_rows,clock_owners=clocks,bindings=bindings,native_APIs=apis,journals=journals,
            obligations=obligations,owned_resources_closed=all(obligations.values()),
            journal_logical_flags_are_observations_only=True,
            physical_SQLite_closure_required_separately='PHYSICAL-CUSTODY.json plus unchanged constructor/postconstruction receipt predicates',
            all_API_cleanup_records_empty=all(not row['pending'] for row in apis),
            controlled_uncertainty_cases=sorted(allowed),native_admission_receipts=admission.NATIVE_ADMISSION_RECEIPTS,
            observer_receipts=effect.NATIVE_RECEIPTS,session_receipts=session.NATIVE_RECEIPTS,
            controlled_binding_uncertainty=[row for row in bindings if row['controlled_API'] and row['pending']],
            native_capacity_receipts=capacity.NATIVE_RECEIPTS,native_capacity_custody_receipts=capacity.NATIVE_CUSTODY_RECEIPTS,
            capacity_connection_receipts=connection.FACTS,composition_receipts=composition.FACTS,
            qualification='Actual native bindings must close; the one exact pure no-return control remains explicitly pending. Exact captured Python owners plus original component receipts; no historical PID/path cleanup or claim that controlled uncertain records are empty.'))
