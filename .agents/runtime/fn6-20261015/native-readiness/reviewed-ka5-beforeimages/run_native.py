"""Original seven native cases. Refuses operation without Root's exact release."""
from readiness_support import *


def rejection_timing(error, contract_type):
    """Read trusted exception storage after rejection; no clock/predicate calls."""
    pending, seen, records = [(error, 'original')], set(), []
    while pending and len(seen) < 32:
        current, link = pending.pop(0)
        if not isinstance(current, BaseException) or id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, contract_type):
            data = BaseException.__dict__['__dict__'].__get__(current)
            terms = dict.get(data, 'owned_cpu_timing')
            if isinstance(terms, dict):
                phase = dict.get(terms, 'phase')
                values = {name: dict.get(terms, name) for name in ('elapsed_ns', 'bound_ns', 'resolution_ns')}
                if (type(phase) is str and phase in ('ENTRY', 'CAPACITY', 'CONSUMED', 'READY', 'DISPATCH')
                        and all(type(v) is int and v >= 0 for v in values.values())):
                    list.append(records, dict(link=link, phase=phase, **values))
        for name in ('__cause__', '__context__'):
            other = BaseException.__dict__[name].__get__(current)
            if other is not None:
                pending.append((other, link + '/' + name))
    return dict(status='available' if records else 'unavailable', records=records,
                examined_exceptions=len(seen), chain_truncated=bool(pending),
                unavailable_reason=None if records else 'No trusted typed timing terms in observed original exception chain')


def main(argv):
    require(len(argv) == 3, 'EXACT_CHILD_ARGUMENTS_REQUIRED')
    attempt, release_sha, marker_sha = argv
    inputs, facts = preflight()
    release, release_facts, review_facts, output = release_record(inputs, facts, release_sha)
    require(attempt == release['attempt_id'], 'WRONG_CHILD_ATTEMPT')
    marker, _ = pinned_json(N / 'ONE-ATTEMPT.json', marker_sha)
    require(marker['release_sha256'] == release_sha and marker['attempt_id'] == attempt
            and marker['inputs_sha256'] == facts['sha256'] and marker['output_root'] == str(output),
            'CHILD_MARKER_MISMATCH')
    require(output.is_dir() and not (output / 'c').exists(), 'CHILD_OUTPUT_NOT_FRESH')
    D = output / 'c'
    D.mkdir()
    (D / 'tmp').mkdir()
    os.environ['TEMP'] = os.environ['TMP'] = str(D / 'tmp')
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    sys.dont_write_bytecode = True
    forbidden = []
    def audit(event, args):
        if event in ('subprocess.Popen', 'os.system', 'os.startfile', 'os.exec', 'os.posix_spawn',
                     'os.spawn', 'socket.__new__', 'socket.bind', 'socket.connect'):
            forbidden.append(event)
            raise RuntimeError('UNDECLARED_PROCESS_NETWORK_OPERATION')
        if event == 'ctypes.dlsym' and args[1] in (
                'CreateAppContainerProfile', 'DeleteAppContainerProfile', 'CreateProcessAsUserW',
                'CreateProcessWithTokenW', 'LogonUserW'):
            forbidden.append(args[1])
            raise RuntimeError('PROFILE_OR_TOKEN_OPERATION_FORBIDDEN')
    sys.addaudithook(audit)
    # No active Source path is used. No CETA import or test allocation precedes
    # the exact release, current native pins, and consumed marker checks above.
    sys.path[:0] = [str(Q / 'src'), str(Q / 'tests/contract')]
    from ceta.store.sqlite_runtime import load_sqlite, runtime_identity
    sqlite = load_sqlite()
    sqlite_identity = runtime_identity()
    import importlib
    import threading
    import unittest
    import test_owner_authority_transactions as authority
    import test_windows_jobs as jobs
    from ceta.supervisor import windows_jobs
    from ceta.identity import native_clock
    from ceta.store import journal
    module = importlib.import_module('test_cpu_execution_admission')
    import bounded_custody as custody
    from resource_witness import Witness

    fixture_root = Path(inputs['fixture_root'])
    require(fixture_root.parent == Q / '.agents/fixtures' and fixture_root.name.startswith('ka5-native-')
            and not fixture_root.exists(), 'PRIVATE_Q_FIXTURE_NOT_FRESH')
    fixture_root.mkdir(parents=True, exist_ok=False)
    fs.safe_components(fixture_root)
    class FixtureRoot:
        def __truediv__(self, name):
            name = str(name).replace('\\', '/')
            if name == '.agents/fixtures':
                return fixture_root
            if name.startswith('.agents/fixtures/'):
                return fixture_root / name[len('.agents/fixtures/'):]
            return Q / name
    authority.ROOT = jobs.ROOT = FixtureRoot()
    active = [None]
    witness = Witness(lambda: active[0])
    base = inputs['environment']['base_python']['path']
    require(str(jobs.BASE) == base, 'BASE_WORKER_PATH_MISMATCH')
    require(sha(jobs.CHILD.encode('utf8')) == inputs['worker_child_source_sha256'], 'WORKER_PROGRAM_MISMATCH')
    def worker_gate(executable, arguments, kwargs):
        require(type(executable) is str and executable == base, 'ONLY_PINNED_ORDINARY_WORKER')
        require(type(arguments) is tuple and len(arguments) == 8 and arguments[:3] == ('-B', '-I', '-c')
                and arguments[3] == jobs.CHILD and arguments[-1] == '7', 'FIXED_ORIGINAL_WORKER_ARGUMENTS')
        require(all(type(v) is str for v in arguments), 'WORKER_ARGUMENT_TYPES')
        require(all(arguments[i].startswith('Local\\CETA-Owned-Job-Test-')
                    and len(arguments[i].split('-')[-1]) == 32 for i in (4, 5)), 'OWNED_EVENT_NAMES_REQUIRED')
        cwd = Path(kwargs['cwd'])
        require(cwd.is_relative_to(fixture_root) and cwd.is_dir() and Path(arguments[6]) == cwd / 'primary.json',
                'WORKER_DISPOSABLE_ROOT_REQUIRED')
        fs.safe_components(cwd)
        require(kwargs['environment'] == {'SystemRoot': inputs['SystemRoot'], 'TEMP': str(cwd),
                'TMP': str(cwd), 'CETA_JOB_ENV': 'explicit'}, 'WORKER_ENVIRONMENT_MISMATCH')
        require(ordinary(Path(base)) == inputs['environment']['base_python'], 'BASE_WORKER_NATIVE_DRIFT')

    stream = (D / 'LIFETIMES.jsonl').open('x', encoding='utf8', buffering=1)
    def emit(owner):
        # Witness retains the exact owner before this callback. A field/IO
        # failure retires that returned owner before it can be lost to caller.
        row = dict(at=utc(), test_id=active[0], object_id=id(owner), pid=owner.pid,
                   creation_time=owner.creation_time, image_sha256=owner.image_sha256,
                   retained_process_handle=int(owner._process), retained_job_handle=int(owner._job))
        stream.write(canonical(row) + '\n')
        stream.flush()
    witness.install(windows_jobs, jobs, native_clock, journal, sqlite, custody, emit,
                    lambda p: fs.file_identity(fs.lstat(p)), worker_gate)
    tests = [module.NativeCpuExecutionAdmissionTests(name) for name in METHODS]
    expected = [test.id() for test in tests]
    require(expected == list(IDS), 'EXACT_NATIVE_ID_ORDER_REQUIRED')
    # Byte/AST pin is also checked in preflight; this verifies actual imports.
    require(Path(module.__file__) == Q / 'tests/contract/test_cpu_execution_admission.py', 'WRONG_TEST_IMPORT')
    before_threads = set(threading.enumerate())
    executed, stopped, rejection_diagnostics, diagnostic_reader_errors = [], [], [], []
    from ceta.contracts.wire import ContractError
    class Result(unittest.TextTestResult):
        def startTest(self, test):
            active[0] = test.id()
            executed.append(test.id())
            super().startTest(test)
        def _capture_rejection(self, test, error):
            try:
                list.append(rejection_diagnostics, dict(test_id=test.id(), timing=rejection_timing(error[1], ContractError)))
            except BaseException as failure:
                try:
                    list.append(diagnostic_reader_errors, failure)
                    list.append(rejection_diagnostics, dict(test_id=test.id(), timing=dict(
                        status='unavailable', records=[], unavailable_reason='Post-rejection reader raised; exact failure retained')))
                except BaseException:
                    pass
        def addFailure(self, test, error):
            super().addFailure(test, error)
            self._capture_rejection(test, error)
        def addError(self, test, error):
            super().addError(test, error)
            self._capture_rejection(test, error)
        def stopTest(self, test):
            stopped.append(test.id())
            super().stopTest(test)
            active[0] = None
    started = utc()
    primary = None
    result = None
    try:
        with (D / 'tests.txt').open('x', encoding='utf8', buffering=1) as raw:
            result = unittest.TextTestRunner(stream=raw, verbosity=2, resultclass=Result).run(unittest.TestSuite(tests))
    except BaseException as error:
        primary = error
    finally:
        try:
            stream.close()
        except BaseException as close_error:
            if primary is None:
                primary = close_error
            else:
                dict.update(BaseException.__dict__['__dict__'].__get__(primary), lifetime_stream_close_error=close_error)
    # No automatic retry of failed/uncertain inner retirement. The held outer
    # job can terminate its exact descendants on failure; that is not a claim
    # of successful inner resource cleanup.
    resources = witness.result()
    after_inputs, after_facts = preflight()
    imports = {name: ordinary(Path(item.__file__)) for name, item in sys.modules.items()
               if (name == 'ceta' or name.startswith('ceta.')) and getattr(item, '__file__', None)}
    own_imports = all(Path(row['path']).is_relative_to(Q / 'src')
                      and row['sha256'] == inputs['candidate342'][Path(row['path']).relative_to(Q).as_posix()]['sha256']
                      for row in imports.values())
    remaining = [dict(name=t.name, native_id=t.native_id) for t in set(threading.enumerate()) - before_threads if t.is_alive()]
    complete = (primary is None and result is not None and result.wasSuccessful() and not result.skipped
                and result.testsRun == 7 and expected == executed == stopped
                and len(resources['owners']) == len(resources['journals']) == len(resources['clocks']) == 8
                and len(resources['registrations']) == 8 and resources['owned_resources_closed']
                and len(module.NATIVE_ADMISSION_RECEIPTS) == 8 and not forbidden
                and not remaining and own_imports and after_inputs == inputs and after_facts == facts)
    report = dict(at=utc(), started_at=started, decision='passed' if complete else 'not_accepted',
        exit_status=0 if complete else 1, tests_run=result.testsRun if result else 0,
        expected_ids=expected, executed_ids=executed, stopped_ids=stopped,
        failures=len(result.failures) if result else None, errors=len(result.errors) if result else None,
        skips=len(result.skipped) if result else None,
        failure_details=[dict(id=t.id(), traceback=body) for t, body in result.failures + result.errors] if result else [],
        post_rejection_timing_diagnostics=rejection_diagnostics,
        post_rejection_reader_failures=len(diagnostic_reader_errors),
        timing_reader_scope='After unittest failure/error rejection only; no clock query or predicate wrapping',
        private_fixture_root=str(fixture_root),
        primary_type=type(primary).__name__ if primary else None, native_resources=resources,
        remaining_threads=remaining, native_admission_receipts=module.NATIVE_ADMISSION_RECEIPTS,
        forbidden_calls=forbidden, actual_ceta_imports=imports, all_imports_exact_candidate=own_imports,
        sqlite_runtime=sqlite_identity, release_sha256=release_sha, marker_sha256=marker_sha,
        candidate_manifest_sha256=MANIFEST_PIN, candidate342_before=inputs['candidate342'],
        candidate342_after=after_inputs['candidate342'], environment_before=inputs['environment'],
        environment_after=after_inputs['environment'], method_bodies_and_deadlines_unchanged=True,
        observer_overhead_not_removed=True, source_conservation_claim=False, Source_acceptance=False,
        authority_capacity_settlement='CONTROLLED provider fixtures; native worker/clock/class15 only',
        profile_or_Hello_execution=False, original_restricted_no_profile_case=False,
        no_automatic_inner_cleanup_retry=True)
    save(D / 'RESULT.json', report)
    print(canonical(dict(tests_run=report['tests_run'], exit_status=report['exit_status'],
                         owned_resources_closed=resources['owned_resources_closed'])), flush=True)
    return report['exit_status']


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
