"""Disposable standard-library-only observer controls; no CETA or clock reads."""
from dataclasses import dataclass, replace
from pathlib import Path
import json
import sys
import unittest
from unittest.mock import patch
import owner_timing_observer as observer


@dataclass(frozen=True)
class Clock:
    boot_id: str = 'control-boot'
    durable_epoch: int = 7
    resume_generation: int = 0
    monotonic_ns: int = 1_100_000_000
    wall_time_ns: int = 2_000_000_000
    uncertainty_ns: int = 0
    wall_trusted: bool = True


@dataclass(frozen=True)
class Deadline:
    boot_id: str = 'control-boot'
    durable_epoch: int = 7
    resume_generation: int = 0
    issued_monotonic_ns: int = 1_000_000_000
    expires_monotonic_ns: int = 61_000_000_000
    issued_earliest_wall_ns: int = 1_900_000_000
    expires_wall_ns: int = 62_000_000_000


@dataclass(frozen=True, slots=True)
class Enrollment:
    deadline: Deadline
    request_id: str = 'enrollment:disposable-control'


class ControlError(Exception):
    def __init__(self, code):
        super().__init__('disposable observer control')
        self.code = code


class HostileStringError(ControlError):
    def __str__(self):
        raise KeyboardInterrupt('controlled refusal to format original')


class RefusingDictionary(dict):
    calls = []
    def refuse(self, *args, **kwargs):
        self.calls.append('refused dictionary callback')
        raise SystemExit('dictionary hook')
    get = items = __iter__ = __getitem__ = __setitem__ = refuse


class Owner:
    def __init__(self, kernel):
        self.k, self._resolution_ns = kernel, 100

    def commit(self, phase, enrollment, context, kind):
        return self.guard(phase, enrollment, context, kind)

    def guard(self, phase, enrollment, context, kind):
        # Pure data stand-in, not product timing or a production guard.
        previous, sample, highwater = Clock(monotonic_ns=1_000_000_000), Clock(), None
        request = None
        started = 1000
        finished = started + (50_000_001 if kind != 'deadline' else 200_000) - 2*self._resolution_ns
        elapsed = finished - started + 2*self._resolution_ns
        if kind == 'success': return None
        if kind == 'deadline': code = 'OWNER_DEADLINE_ELAPSED'
        else: code = 'OWNER_NATIVE_CHECK_TOO_SLOW'
        error = HostileStringError(code) if kind == 'hostile-string' else ControlError(code)
        if kind == 'nonstring-key':
            data = RefusingDictionary(); dict.__setitem__(data, 17, object())
            dict.__setitem__(data, 'code', code)
            BaseException.__dict__['__dict__'].__set__(error, data)
        if kind == 'missing-finished': del finished
        if kind == 'wrong-clock': sample = object()
        if kind == 'boolean-endpoint': finished = True
        raise error


class Kernel:
    def begin(self, request_context, kind):
        deadline = Deadline()
        if kind == 'deadline':
            deadline = replace(deadline, expires_monotonic_ns=1_100_100_000,
                               expires_wall_ns=2_000_100_000)
        enrollment = Enrollment(deadline)
        return Owner(self).commit('CHALLENGE', enrollment, request_context, kind)


BINDING = observer.Binding(Owner.guard.__code__, Owner.commit.__code__,
    (Kernel.begin.__code__,), Owner, Kernel, Enrollment, Clock, Deadline)


class DisposableCase(unittest.TestCase):
    __test__ = False
    def __init__(self, kind='slow', mode='error', param=None):
        super().__init__('runTest'); self.kind, self.mode, self.param = kind, mode, param
    def runTest(self):
        if self.mode == 'unrelated': raise RuntimeError('unrelated disposable error')
        if self.mode == 'subtest':
            with self.subTest(label=self.param): Kernel().begin(object(), self.kind)
        elif self.mode == 'failure':
            try: Kernel().begin(object(), self.kind)
            except ControlError: raise AssertionError('disposable outer assertion')
        else: Kernel().begin(object(), self.kind)


class ObserverControls(unittest.TestCase):
    def run_case(self, kind='slow', mode='error', param=None, sink=None, binding=BINDING):
        case = DisposableCase(kind, mode, param)
        result = observer.PostmortemResult(binding, ((case, 'disposable.observer.control'),), sink)
        case.run(result)
        return result

    def guarded(self, result):
        return next(g for item in result.observations[0]['evidence']['records']
                    for g in item['guard'] if g['status'] == 'CAPTURED')

    def test_elapsed_terms_come_from_completed_control_frame(self):
        r = self.run_case(); data = self.guarded(r)
        self.assertEqual(data['phase'], 'CHALLENGE')
        self.assertEqual(data['elapsed'], 50_000_001)
        self.assertEqual(data['resolution_ns'], 100)
        self.assertTrue(data['charge_matches']); self.assertTrue(data['context_bound'])
        self.assertEqual(data['provider_spans'], 'NOT_MEASURED')
        self.assertEqual(len(r.errors), 1); self.assertEqual(r.super_calls, ['error'])
        self.assertIs(r.originals[0][3][1].__class__, ControlError)
        self.assertEqual(r.report()['reproduction'], 'OBSERVED_OWNER_GUARD_FAILURE')

    def test_deadline_margins_are_derived_only_from_control_scalars(self):
        r = self.run_case('deadline'); data = self.guarded(r)
        self.assertEqual(data['derived']['monotonic_margin_ns'], -100_000)
        self.assertEqual(data['derived']['wall_margin_ns'], -100_000)
        self.assertTrue(data['derived_after_failure'])
        self.assertEqual(r.observations[0]['evidence']['records'][0]['code'], 'OWNER_DEADLINE_ELAPSED')

    def test_superclass_receives_identical_triple_once(self):
        original = unittest.TestResult.addError; seen = []
        def base(result, case, err): seen.append(err); return original(result, case, err)
        with patch.object(unittest.TestResult, 'addError', base): r = self.run_case()
        self.assertEqual(len(seen), 1); self.assertIs(seen[0], r.originals[0][3])

    def test_storage_fault_retains_original_and_superclass_outcome(self):
        secondary = OSError('controlled storage refusal')
        def sink(record): raise secondary
        r = self.run_case(sink=sink)
        self.assertFalse(r.coverage_complete); self.assertFalse(r.wasSuccessful())
        self.assertEqual(len(r.errors), 1); self.assertEqual(r.super_calls, ['error'])
        self.assertIs(r.faults[0][1], secondary); self.assertEqual(r.originals[0][3][1].code, 'OWNER_NATIVE_CHECK_TOO_SLOW')

    def test_collector_fault_is_secondary_and_superclass_runs_once(self):
        secondary = SystemExit('controlled collector refusal')
        with patch.object(observer, 'extract', side_effect=secondary): r = self.run_case()
        self.assertIs(r.faults[0][1], secondary); self.assertEqual(len(r.errors), 1)
        self.assertEqual(r.super_calls, ['error']); self.assertFalse(r.coverage_complete)

    def test_superclass_fault_retains_exact_secondary_and_failure_outcome(self):
        secondary = OSError('controlled superclass refusal'); calls = []
        def base(result, case, err): calls.append(err); raise secondary
        with patch.object(unittest.TestResult, 'addError', base): r = self.run_case()
        self.assertEqual(len(calls), 1); self.assertIs(calls[0], r.originals[0][3])
        self.assertIs(r.faults[0][1], secondary); self.assertEqual(len(r.errors), 1)
        self.assertFalse(r.wasSuccessful()); self.assertFalse(r.coverage_complete)

    def test_hostile_primary_formatter_cannot_replace_error(self):
        r = self.run_case('hostile-string')
        self.assertEqual(len(r.errors), 1); self.assertFalse(r.wasSuccessful())
        self.assertIs(type(r.originals[0][3][1]), HostileStringError)
        self.assertEqual(r.super_calls, ['error'])

    def test_report_encoder_failure_cannot_publish_complete_coverage(self):
        r = self.run_case(); primary = r.originals[0][3]
        def fail(*args, **kwargs): raise MemoryError('controlled report refusal')
        report = r.report(encoder=fail)
        self.assertFalse(report['coverage_complete']); self.assertFalse(report['functional_success'])
        self.assertIs(r.originals[0][3], primary); self.assertEqual(r.super_calls, ['error'])

    def test_nonstring_exception_keys_never_invoke_dictionary_hooks(self):
        RefusingDictionary.calls.clear(); r = self.run_case('nonstring-key')
        self.assertEqual(self.guarded(r)['elapsed'], 50_000_001)
        self.assertEqual(RefusingDictionary.calls, [])

    def test_failure_chain_keeps_outer_failure_and_inner_guard(self):
        r = self.run_case(mode='failure')
        self.assertEqual(len(r.failures), 1); self.assertEqual(len(r.errors), 0)
        self.assertEqual(r.super_calls, ['failure']); self.assertEqual(self.guarded(r)['elapsed'], 50_000_001)

    def test_subtest_primitive_identity_is_captured_without_formatting(self):
        r = self.run_case(mode='subtest', param='primitive')
        data = r.observations[0]['subtest_identity']
        self.assertEqual(data['status'], 'CAPTURED')
        self.assertEqual(data['parameter_layers'], [[['label', 'primitive']]])
        self.assertEqual(r.observations[0]['subtest_ordinal'], 1)
        self.assertEqual(r.super_calls, ['subtest']); self.assertEqual(len(r.errors), 1)

    def test_unsupported_subtest_value_is_never_repr_formatted_by_collector(self):
        calls = []
        class Unsupported:
            def __repr__(self): calls.append('repr'); raise KeyboardInterrupt('repr')
        r = self.run_case(mode='subtest', param=Unsupported())
        self.assertEqual(calls, []); self.assertFalse(r.coverage_complete)
        self.assertEqual(r.observations[0]['subtest_identity']['status'], 'NOT_CAPTURED')
        self.assertEqual(len(r.errors), 1)

    def test_unrelated_error_has_no_fabricated_guard_data(self):
        r = self.run_case(mode='unrelated')
        self.assertEqual(r.observations[0]['evidence']['owner_guard'], 'NOT_CAPTURED')
        self.assertEqual(r.observations[0]['evidence']['records'][0]['guard'], [])

    def test_missing_and_wrong_exact_types_are_explicitly_not_captured(self):
        for kind in ('missing-finished', 'wrong-clock', 'boolean-endpoint'):
            with self.subTest(kind=kind):
                r = self.run_case(kind)
                self.assertEqual(r.observations[0]['evidence']['owner_guard'], 'NOT_CAPTURED')
                self.assertFalse(r.coverage_complete); self.assertEqual(len(r.errors), 1)

    def test_code_identity_substitution_does_not_capture_foreign_frame(self):
        binding = replace(BINDING, guard_code=(lambda: None).__code__)
        r = self.run_case(binding=binding)
        self.assertEqual(r.observations[0]['evidence']['owner_guard'], 'NOT_CAPTURED')

    def test_cause_cycle_is_bounded(self):
        error = ControlError('CYCLE'); error.__cause__ = error
        record = observer.extract((type(error), error, None), BINDING)
        self.assertEqual(len(record['records']), 1); self.assertTrue(record['chain_complete'])

    def test_context_substitution_is_rejected(self):
        binding = replace(BINDING, entry_codes=((lambda: None).__code__,))
        r = self.run_case(binding=binding)
        guard = r.observations[0]['evidence']['records'][0]['guard'][0]
        self.assertEqual(guard['reason'], 'CONTEXT_BINDING_FAILED'); self.assertFalse(r.coverage_complete)

    def test_raw_metaclass_and_instance_properties_never_run(self):
        calls = []
        class Meta(type):
            @property
            def __mro__(cls): calls.append('mro'); raise SystemExit()
            @property
            def __dict__(cls): calls.append('classdict'); raise SystemExit()
            @property
            def __name__(cls): calls.append('name'); raise SystemExit()
            def __eq__(cls, other): calls.append('type-eq'); raise SystemExit()
        class Raw(metaclass=Meta):
            @property
            def dangerous(self): calls.append('instanceproperty'); raise SystemExit()
            @property
            def __class__(self): calls.append('classproperty'); raise SystemExit()
        value = Raw(); value.stored = 17
        self.assertEqual(observer._raw(value, Raw, 'stored'), 17)
        self.assertIs(observer._raw(value, Raw, 'dangerous'), observer._MISSING)
        self.assertFalse(observer._primitive(value))
        self.assertEqual(observer._type_name(value), 'Raw')
        self.assertEqual(calls, [])

    def test_colliding_nonstring_error_key_never_compares(self):
        calls = []
        class Collision:
            def __hash__(self): return hash('code')
            def __eq__(self, other): calls.append('key-eq'); raise SystemExit()
        error = ControlError('OLD'); data = BaseException.__dict__['__dict__'].__get__(error)
        dict.clear(data); dict.__setitem__(data, Collision(), 'unsupported')
        self.assertEqual(observer._error_code(error), 'NOT_CAPTURED')
        self.assertEqual(calls, [])

    def test_success_has_no_inferred_positive_timings(self):
        r = self.run_case('success'); report = r.report()
        self.assertTrue(r.wasSuccessful()); self.assertEqual(report['reproduction'], 'NOT_REPRODUCED')
        self.assertEqual(report['successful_guard_timings'], 'NOT_MEASURED')
        self.assertEqual(report['provider_spans'], 'NOT_MEASURED')


if __name__ == '__main__':
    label = sys.argv[1] if len(sys.argv) == 2 else 'controls-r2'
    assert label.isascii() and label.replace('-', '').isalnum(), 'simple attempt label required'
    folder = Path(__file__).resolve().parent / label
    folder.mkdir(exist_ok=False)
    target = folder / 'CONTROL-RESULT.json'
    assert not target.exists(), 'create-only control result; preserve every attempt'
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ObserverControls)
    with (target.parent/'CONTROLS.log').open('x', encoding='utf-8') as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    report = dict(scope='DISPOSABLE_STANDARD_LIBRARY_OBSERVER_CONTROLS_ONLY',
        tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        skips=result.skipped, successful=result.wasSuccessful(), canonical_test_bodies_run=0,
        native_calls=0, clock_reads=0, source_imports=0, product_result=False)
    target.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2)); raise SystemExit(0 if result.wasSuccessful() else 1)
