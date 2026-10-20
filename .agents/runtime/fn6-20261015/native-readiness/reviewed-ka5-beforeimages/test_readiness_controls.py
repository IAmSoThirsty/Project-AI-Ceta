"""CONTROLLED guard/custody checks; no CETA import or native worker execution."""
from readiness_support import *
from datetime import timedelta
import builtins
import copy
import tempfile
import threading
import types
import unittest
from unittest.mock import patch
import bounded_custody as custody
from resource_witness import Witness, retained_return, storage


def function_from(path, name, bindings):
    tree = ast.parse(Path(path).read_bytes())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    namespace = {'__builtins__': builtins.__dict__, **bindings}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace[name]


class ReleaseControls(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.inputs = {'scripts': {name: {'sha256': 'a' * 64} for name in SCRIPTS}, 'environment': {'x': 'y'}}
        self.pin = 'b' * 64
        self.release = dict(schema_version=1, kind='KA5_SEVEN_NATIVE_ENGINEERING', executor='/root',
            issued_at=(self.now - timedelta(seconds=1)).isoformat(), expires_at=(self.now + timedelta(seconds=300)).isoformat(),
            attempt_id='c' * 32, inputs_sha256=self.pin,
            scripts_sha256={name: row['sha256'] for name, row in self.inputs['scripts'].items()},
            candidate_manifest_sha256=MANIFEST_PIN, test_ids=list(IDS),
            environment_digest=sha(canonical(self.inputs['environment']).encode('utf8')),
            output_root=str(N / ('attempt-' + 'c' * 32)), child_wait_seconds=WAIT_SECONDS,
            allowed_effects=['OWNED_ORDINARY_WORKERS', 'CLASS9_JOB_SETUP', 'ORIGINAL_SEVEN_CLASS15_CASES',
                            'DISPOSABLE_SQLITE', 'NATIVE_CLOCK_REGISTRATION', 'OWNED_EVENTS_THREADS'],
            review_path=str(N / 'ROOT-REVIEW.json'), review_sha256='d' * 64)
        self.review = dict(decision='approved', exit_status=0, reviewer='/root', author='/root/wt1_reviewer',
                           inputs_sha256=self.pin, scripts_sha256=self.release['scripts_sha256'])

    def valid(self, release=None, review=None):
        return validate_release(release or self.release, review or self.review, self.inputs, self.pin, self.now)

    def test_exact_controlled_release_is_reachable(self):
        self.assertEqual(self.valid(), N / ('attempt-' + 'c' * 32))

    def test_missing_and_unknown_fields_denied(self):
        for key in self.release:
            with self.subTest(missing=key):
                bad = copy.deepcopy(self.release); del bad[key]
                with self.assertRaises(RuntimeError): self.valid(bad)
        bad = copy.deepcopy(self.release); bad['extra'] = True
        with self.assertRaises(RuntimeError): self.valid(bad)

    def test_wrong_source_scripts_environment_or_ids_denied(self):
        variants = [('inputs_sha256', 'e' * 64), ('candidate_manifest_sha256', 'e' * 64),
                    ('environment_digest', 'e' * 64), ('test_ids', list(IDS[:-1])),
                    ('test_ids', list(reversed(IDS))), ('scripts_sha256', {})]
        for key, value in variants:
            with self.subTest(field=key, value=value):
                bad = copy.deepcopy(self.release); bad[key] = value
                with self.assertRaises(RuntimeError): self.valid(bad)

    def test_stale_future_naive_overlong_release_denied(self):
        for start, end in ((-601, -1), (1, 2), (-1, 1000)):
            bad = copy.deepcopy(self.release)
            bad['issued_at'] = (self.now + timedelta(seconds=start)).isoformat()
            bad['expires_at'] = (self.now + timedelta(seconds=end)).isoformat()
            with self.assertRaises(RuntimeError): self.valid(bad)
        bad = copy.deepcopy(self.release); bad['issued_at'] = '2026-10-15T00:00:00'
        with self.assertRaises((RuntimeError, TypeError)): self.valid(bad)

    def test_boolean_schema_deadline_and_review_status_denied(self):
        for key in ('schema_version', 'child_wait_seconds'):
            bad = copy.deepcopy(self.release); bad[key] = True
            with self.assertRaises(RuntimeError): self.valid(bad)
        bad = dict(self.review, exit_status=False)
        with self.assertRaises(RuntimeError): self.valid(review=bad)

    def test_caller_output_path_profile_effect_or_self_review_denied(self):
        for key, value in (('output_root', str(F)), ('review_path', str(F / 'README.md')),
                           ('allowed_effects', ['PROFILE_CREATE']), ('executor', '/root/history_preservation')):
            bad = copy.deepcopy(self.release); bad[key] = value
            with self.assertRaises(RuntimeError): self.valid(bad)
        bad = dict(self.review, reviewer='/root/history_preservation')
        with self.assertRaises(RuntimeError): self.valid(review=bad)


class MarkerControls(unittest.TestCase):
    def test_create_only_marker_and_output_second_use_denied(self):
        with tempfile.TemporaryDirectory(dir=N, prefix='controlled-marker-') as temp:
            root = Path(temp); output = root / 'attempt'
            writes = []
            def model_save(path, value):
                with Path(path).open('x', encoding='utf8') as stream:
                    json.dump(value, stream)
                writes.append(str(path))
            claim = function_from(N / 'supervise_native.py', 'claim_attempt', dict(N=root, require=require,
                save=model_save, utc=utc, ordinary=lambda path: {'path': str(path), 'sha256': sha(path.read_bytes())}))
            args = ({'attempt_id': 'x'}, {'sha256': 'r'}, {'sha256': 'review'}, {'sha256': 'i'}, output)
            first = claim(*args)
            self.assertTrue(output.is_dir()); self.assertEqual(len(writes), 1)
            with self.assertRaisesRegex(RuntimeError, 'ALREADY_CONSUMED'): claim(*args)
            self.assertEqual(len(writes), 1); self.assertEqual(first['sha256'], sha((root / 'ONE-ATTEMPT.json').read_bytes()))

    def test_existing_output_blocks_before_consuming_marker(self):
        with tempfile.TemporaryDirectory(dir=N, prefix='controlled-existing-') as temp:
            root = Path(temp); output = root / 'attempt'; output.mkdir()
            claim = function_from(N / 'supervise_native.py', 'claim_attempt', dict(N=root, require=require,
                save=lambda *a: self.fail('must not write'), utc=utc, ordinary=lambda p: None))
            with self.assertRaisesRegex(RuntimeError, 'ALREADY_CONSUMED'):
                claim({'attempt_id': 'x'}, {}, {}, {}, output)


class BeforeImportControls(unittest.TestCase):
    def child(self, change=None):
        with tempfile.TemporaryDirectory(dir=N, prefix='controlled-child-') as temp:
            root = Path(temp); output = root / 'attempt'; output.mkdir()
            release = {'attempt_id': 'c' * 32}
            marker = dict(release_sha256='r', attempt_id='c' * 32, inputs_sha256='i', output_root=str(output))
            if change: change(release, marker)
            imports, audit_hooks = [], []
            actual_import = builtins.__import__
            def no_ceta(name, *args, **kwargs):
                if name == 'ceta' or name.startswith('ceta.'):
                    imports.append(name); raise RuntimeError('QUALIFIED_BEFORE_FIRST_CETA_IMPORT')
                return actual_import(name, *args, **kwargs)
            bindings = dict(require=require, N=root, Path=Path, preflight=lambda: ({}, {'sha256': 'i'}),
                release_record=lambda *a: (release, {}, {}, output), pinned_json=lambda *a: (marker, {}),
                os=types.SimpleNamespace(environ={}), sys=types.SimpleNamespace(dont_write_bytecode=True,
                path=[], addaudithook=audit_hooks.append), Q=Q)
            main = function_from(N / 'run_native.py', 'main', bindings)
            with patch('builtins.__import__', side_effect=no_ceta):
                with self.assertRaises(RuntimeError) as caught:
                    main(['c' * 32, 'r', 'm'])
            return str(caught.exception), imports

    def test_legitimate_child_control_reaches_import_sentinel_without_import(self):
        message, calls = self.child()
        self.assertEqual(message, 'QUALIFIED_BEFORE_FIRST_CETA_IMPORT')
        self.assertEqual(calls, ['ceta.store.sqlite_runtime'])

    def test_wrong_attempt_and_marker_deny_before_import(self):
        for change in (lambda r, m: r.update(attempt_id='wrong'),
                       lambda r, m: m.update(release_sha256='wrong'),
                       lambda r, m: m.update(inputs_sha256='wrong'),
                       lambda r, m: m.update(output_root=str(F))):
            with self.subTest(change=change):
                message, calls = self.child(change)
                self.assertNotEqual(message, 'QUALIFIED_BEFORE_FIRST_CETA_IMPORT'); self.assertEqual(calls, [])

    def test_missing_release_denies_supervisor_before_import_or_marker(self):
        calls = []
        def absent(*args):
            calls.append('release'); raise RuntimeError('NO_ROOT_NATIVE_RELEASE')
        main = function_from(N / 'supervise_native.py', 'main', dict(require=require,
            preflight=lambda: ({}, {}), release_record=absent,
            claim_attempt=lambda *a: self.fail('marker must not be consumed')))
        with self.assertRaisesRegex(RuntimeError, 'NO_ROOT_NATIVE_RELEASE'): main([])
        self.assertEqual(calls, ['release'])

    def test_valid_supervisor_control_reaches_import_sentinel(self):
        with tempfile.TemporaryDirectory(dir=N, prefix='controlled-wrapper-') as temp:
            output = Path(temp); imported = []; writes = []
            bindings = dict(require=require, N=N, Q=Q, PY=PY, WAIT_SECONDS=WAIT_SECONDS,
                preflight=lambda: ({'SystemRoot': 'CONTROLLED', 'environment':
                    {'E3/Scripts/python.exe': {'sha256': 'p'}}}, {'sha256': 'i'}),
                release_record=lambda *a: ({'attempt_id': 'c' * 32}, {'sha256': 'r'}, {}, output),
                claim_attempt=lambda *a: {'sha256': 'm'}, utc=utc,
                save=lambda p, v: writes.append((p.name, v)), sys=types.SimpleNamespace(path=[]))
            main = function_from(N / 'supervise_native.py', 'main', bindings)
            actual_import = builtins.__import__
            def sentinel(name, *args, **kwargs):
                if name.startswith('ceta.'):
                    imported.append(name); raise RuntimeError('SUPERVISOR_BEFORE_FIRST_CETA_IMPORT')
                return actual_import(name, *args, **kwargs)
            with patch('builtins.__import__', side_effect=sentinel):
                with self.assertRaisesRegex(RuntimeError, 'SUPERVISOR_BEFORE_FIRST_CETA_IMPORT'): main([])
            self.assertEqual(imported, ['ceta.supervisor.windows_jobs'])
            self.assertEqual([name for name, value in writes], ['COMMAND.json'])


class FakeOwner:
    def __init__(self, *, cleanup_error=None):
        self.cleanup_error = cleanup_error; self.retire_calls = 0
        self.pid = 1; self.creation_time = 2; self.image_sha256 = '0' * 64
        self.lifetime_closed = False; self._process = 11; self._thread = None; self._job = 12
        self._cleanup_handles = []; self.waits = []
    def poll(self): return 0
    def active_process_count(self): return 0
    def wait(self, seconds): self.waits.append(seconds); return True
    def close(self):
        self.retire_calls += 1
        if self.cleanup_error: raise self.cleanup_error
        self.lifetime_closed = True; self._process = self._thread = self._job = None


class CustodyControls(unittest.TestCase):
    def test_exact_return_positive_does_not_retire(self):
        owner = FakeOwner(); observed = []
        actual = retained_return(owner, observed.append, lambda o: observed.append(o), custody.retire)
        self.assertIs(actual, owner); self.assertEqual(observed, [owner, owner]); self.assertEqual(owner.retire_calls, 0)

    def test_registry_failure_and_logger_controls_preserve_primary(self):
        for site in ('registry', 'logger'):
            for kind in (KeyboardInterrupt, SystemExit, MemoryError):
                with self.subTest(site=site, kind=kind.__name__):
                    owner = FakeOwner(); primary = kind('CONTROLLED')
                    def fail(value): raise primary
                    register, emit = (fail, lambda o: None) if site == 'registry' else (lambda o: None, fail)
                    with self.assertRaises(kind) as caught:
                        retained_return(owner, register, emit, custody.retire)
                    self.assertIs(caught.exception, primary); self.assertIs(storage(primary)['exact_recorder_owner'], owner)
                    self.assertTrue(owner.lifetime_closed); self.assertEqual(owner.retire_calls, 1)

    def test_simultaneous_cleanup_refusal_retains_exact_secondary_without_retry(self):
        for kind in (KeyboardInterrupt, SystemExit):
            owner = FakeOwner(cleanup_error=OSError('CONTROLLED close refusal')); primary = kind('CONTROLLED')
            def fail(value): raise primary
            with self.assertRaises(kind) as caught:
                retained_return(owner, fail, lambda o: None, custody.retire)
            self.assertIs(caught.exception, primary)
            self.assertIs(storage(primary)['recorder_cleanup_error'], owner.cleanup_error)
            self.assertIs(storage(primary)['exact_recorder_owner'], owner)
            self.assertEqual(owner.retire_calls, 1); self.assertFalse(owner.lifetime_closed)

    def test_reviewed_outer_custody_retires_before_reading_child(self):
        owner = FakeOwner(); facts = []
        def child():
            self.assertTrue(owner.lifetime_closed); facts.append('child'); return {'controlled': True}
        report = custody.run_owned(lambda: owner, lambda r: facts.append('emit'), child, timeout=3)
        self.assertEqual(facts, ['emit', 'child']); self.assertEqual(report['child_exit'], 0)
        self.assertTrue(all(report['native_owner_after'].values()))

    def test_reviewed_outer_emit_failure_does_not_mask_control(self):
        owner = FakeOwner(); primary = KeyboardInterrupt('CONTROLLED outer logger')
        def emit(row): raise primary
        with self.assertRaises(KeyboardInterrupt) as caught:
            custody.run_owned(lambda: owner, emit, lambda: {}, timeout=3)
        self.assertIs(caught.exception, primary); self.assertTrue(owner.lifetime_closed)
        self.assertIs(storage(primary)['full_runner_owner'], owner); self.assertEqual(owner.retire_calls, 1)

    def test_handle_value_reuse_retains_distinct_allocation_identity(self):
        witness = Witness(); api = object()
        first = witness.acquire(api, 21, 'event', witness.row('create'))
        witness.closed(api, 21, witness.row('close'))
        second = witness.acquire(api, 21, 'event', witness.row('create'))
        self.assertIsNot(first, second); self.assertNotEqual(first['allocation'], second['allocation'])
        self.assertIs(witness.find(api, 21), second); self.assertIsNotNone(first['closed_at'])
        self.assertIsNone(second['closed_at'])

    def test_remaining_handle_fails_even_without_logical_owners(self):
        witness = Witness(); witness.sqlite = types.SimpleNamespace(ProgrammingError=ValueError)
        witness.acquire(object(), 12, 'job', witness.row('create'))
        report = witness.result()
        self.assertFalse(report['owned_resources_closed']); self.assertEqual(len(report['remaining_handles']), 1)

    def test_complete_controlled_native_facts_required_beyond_closed_flags(self):
        witness = Witness(); api = object()
        process = witness.acquire(api, 11, 'process', witness.row('CreateProcessW'))
        job = witness.acquire(api, 12, 'job', witness.row('CreateJobObjectW'))
        owner = FakeOwner(); owner.close()
        witness.owners.append(dict(owner=owner, process_allocation=process, job_allocation=job,
            test_id='CONTROLLED', pid=1, image_sha256='0' * 64, initial_process=11, initial_job=12, initial_thread=None))
        witness.row('WaitForSingleObject', root=process['root'], result=0)
        witness.row('GetExitCodeProcess', root=process['root'], native_success=True, exit_code=126)
        witness.row('GetProcessTimes', root=process['root'], native_success=True, creation_time=2)
        witness.row('QueryInformationJobObject', allocation=job['allocation'], native_success=True, active_processes=0)
        witness.closed(api, 11, witness.row('CloseHandle')); witness.closed(api, 12, witness.row('CloseHandle'))
        class ClosedError(Exception): pass
        class Connection:
            @property
            def in_transaction(self): raise ClosedError('CONTROLLED actual getter model')
        connection = Connection()
        witness.sqlite = types.SimpleNamespace(ProgrammingError=ClosedError)
        witness.journals.append(dict(owner=types.SimpleNamespace(path='CONTROLLED', _closed=True),
                                     connection=connection, test_id='CONTROLLED'))
        thread = types.SimpleNamespace(native_id=5, name='CONTROLLED', is_alive=lambda: False)
        clock = types.SimpleNamespace(_api=api, _registration=None, _callbacks=0, _thread=thread,
                                      status=lambda: types.SimpleNamespace(state='CLOSED'))
        witness.clocks.append(dict(owner=clock, test_id='CONTROLLED'))
        witness.registrations.append(dict(api_id=id(api), handle=99, register_status=0,
                                           registration_sequence=5, unregistered_at=6))
        witness.threads.append(dict(thread=thread, test_id='CONTROLLED', start_returned=True,
                                    joins=[dict(returned=True, alive_after=False)]))
        self.assertTrue(witness.result()['owned_resources_closed'])
        job['closed_at'] = None
        self.assertFalse(witness.result()['owned_resources_closed'])

    def test_post_native_observation_fault_does_not_steal_canonical_result(self):
        import ctypes as C
        class Api:
            def __init__(self):
                for name in ('CreateJobObjectW', 'CreateFileW', 'CreateProcessW', 'DuplicateHandle',
                             'CloseHandle', 'WaitForSingleObject', 'GetExitCodeProcess',
                             'GetProcessTimes',
                             'QueryInformationJobObject', 'SetInformationJobObject'):
                    setattr(self, name, lambda *a: 0)
                def created(*args): C.set_last_error(137); return 21
                self.CreateJobObjectW = created
        class Owner:
            @classmethod
            def launch(cls, *args, **kwargs): raise AssertionError('no launch in this control')
        class Fixture:
            def setUp(self): raise AssertionError('no fixture in this control')
        class Journal:
            def __init__(self, *a, **k): raise AssertionError('no SQLite in this control')
        class Clock:
            def __init__(self, *a, **k): raise AssertionError('no clock in this control')
        class ClockApi:
            def __init__(self): raise AssertionError('no native API in this control')
        witness = Witness(); primary = KeyboardInterrupt('CONTROLLED observer')
        def refused(*args): raise primary
        witness.acquire = refused
        saved_start, saved_join = threading.Thread.start, threading.Thread.join
        try:
            witness.install(types.SimpleNamespace(_API=Api, WindowsOwnedProcess=Owner),
                types.SimpleNamespace(WindowsJobTests=Fixture),
                types.SimpleNamespace(NativeSessionClock=Clock, _NativeClockAPI=ClockApi),
                types.SimpleNamespace(SqliteJournal=Journal), object(), custody,
                lambda o: None, lambda p: {}, lambda *a: None)
            api = Api()
            self.assertEqual(api.CreateJobObjectW(None, None), 21)
            self.assertEqual(C.get_last_error(), 137)
            self.assertIs(witness.observation_errors[0], primary)
        finally:
            threading.Thread.start, threading.Thread.join = saved_start, saved_join


if __name__ == '__main__':
    forbidden = []
    original_import = builtins.__import__
    def import_guard(name, *args, **kwargs):
        if name == 'ceta' or name.startswith('ceta.'):
            forbidden.append('IMPORT:' + name); raise RuntimeError('PURE_CONTROLS_NO_CETA_IMPORT')
        return original_import(name, *args, **kwargs)
    def audit_guard(event, args):
        if event in ('subprocess.Popen', 'os.system', 'os.startfile') or (event == 'ctypes.dlsym' and args[1] in (
                'CreateProcessW', 'CreateProcessAsUserW', 'CreateAppContainerProfile',
                'DeleteAppContainerProfile', 'SetInformationJobObject')):
            forbidden.append(event); raise RuntimeError('PURE_CONTROLS_NATIVE_EFFECT_FORBIDDEN')
    sys.addaudithook(audit_guard)
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls)
        for cls in (ReleaseControls, MarkerControls, BeforeImportControls, CustodyControls))
    expected = []
    for group in suite:
        expected.extend(test.id() for test in group)
    executed, stopped = [], []
    class Result(unittest.TextTestResult):
        def startTest(self, test): executed.append(test.id()); super().startTest(test)
        def stopTest(self, test): stopped.append(test.id()); super().stopTest(test)
    out = N / ('pure-controls-' + sys.argv[1])
    out.mkdir(exist_ok=False)
    with patch('builtins.__import__', side_effect=import_guard), (out / 'tests.txt').open('x', encoding='utf8') as raw:
        result = unittest.TextTestRunner(stream=raw, verbosity=2, resultclass=Result).run(suite)
    passed = result.wasSuccessful() and not result.skipped and expected == executed == stopped and not forbidden
    save(out / 'RESULT.json', dict(at=utc(), qualification='CONTROLLED engineering only; zero native or CETA import',
        tests_run=result.testsRun, expected_ids=expected, executed_ids=executed, stopped_ids=stopped,
        failures=len(result.failures), errors=len(result.errors), skips=len(result.skipped), forbidden_calls=forbidden,
        failure_details=[dict(id=t.id(), traceback=body) for t, body in result.failures + result.errors],
        native_execution='NOT_RUN', exit_status=0 if passed else 1))
    print(canonical(dict(tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                         skips=len(result.skipped), exit_status=0 if passed else 1)), flush=True)
    sys.exit(0 if passed else 1)
