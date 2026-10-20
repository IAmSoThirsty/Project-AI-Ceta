"""Three finite actual-AST observer controls; no CETA import or native call."""
from readiness_support import *
import builtins
import io
import unittest


def declaration(path, name, cls=False):
    tree = ast.parse(Path(path).read_bytes())
    return next(node for node in ast.walk(tree) if isinstance(node, ast.ClassDef if cls else ast.FunctionDef)
                and node.name == name)


namespace = {'__builtins__': builtins.__dict__}
exec(compile(ast.Module(body=[declaration(Q / 'src/ceta/contracts/wire.py', 'ContractError', True)],
                        type_ignores=[]), 'exact-candidate-ContractError', 'exec'), namespace)
ContractError = namespace['ContractError']
exec(compile(ast.Module(body=[declaration(N / 'run_native.py', 'rejection_timing')], type_ignores=[]),
             'exact-timing-reader', 'exec'), namespace)
read = namespace['rejection_timing']


def terms(error, phase='CAPACITY'):
    data = BaseException.__dict__['__dict__'].__get__(error)
    dict.__setitem__(data, 'owned_cpu_timing', dict(phase=phase, elapsed_ns=50_000_001,
                 bound_ns=50_000_000, resolution_ns=1))


class TimingReaderControls(unittest.TestCase):
    def test_trusted_original_cause_context_and_hostile_dictionary_are_observed(self):
        class Dict(dict):
            def get(self, *a): raise AssertionError('no dynamic get')
            def items(self): raise AssertionError('no dynamic items')
        class Hostile(ContractError):
            def __getattribute__(self, name):
                if name in ('__dict__', '__context__', '__cause__', 'owned_cpu_timing'):
                    raise AssertionError('no dynamic exception getter')
                return super().__getattribute__(name)
        error = Hostile('CPU_EXECUTION_OWNER_TOO_SLOW')
        terms(error)
        data = BaseException.__dict__['__dict__'].__get__(error)
        dict.__setitem__(data, 'owned_cpu_timing', Dict(dict.get(data, 'owned_cpu_timing')))
        cause, context = RuntimeError('retained cause'), AssertionError('retained context')
        BaseException.__dict__['__cause__'].__set__(context, error)
        BaseException.__dict__['__context__'].__set__(cause, context)
        result = read(cause, ContractError)
        self.assertEqual(result['status'], 'available')
        self.assertEqual(result['records'], [dict(link='original/__context__/__cause__', phase='CAPACITY',
            elapsed_ns=50_000_001, bound_ns=50_000_000, resolution_ns=1)])
        self.assertIs(BaseException.__dict__['__cause__'].__get__(context), error)
        self.assertIs(BaseException.__dict__['__context__'].__get__(cause), context)

    def test_missing_invalid_and_bounded_cyclic_chains_report_unavailable(self):
        for change in (lambda d: d.clear(), lambda d: d.update(elapsed_ns=True),
                       lambda d: d.update(phase='unknown'), lambda d: d.update(resolution_ns=-1)):
            error = ContractError('CONTROLLED')
            terms(error)
            change(BaseException.__dict__['__dict__'].__get__(error)['owned_cpu_timing'])
            self.assertEqual(read(error, ContractError)['status'], 'unavailable')
        errors = [RuntimeError() for _ in range(34)]
        for index, error in enumerate(errors):
            BaseException.__dict__['__context__'].__set__(error, errors[(index + 1) % len(errors)])
        result = read(errors[0], ContractError)
        self.assertEqual(result['examined_exceptions'], 32)
        self.assertTrue(result['chain_truncated'])
        self.assertEqual(result['status'], 'unavailable')

    def test_actual_result_reports_original_rejection_before_reader_and_retains_reader_failure(self):
        diagnostics, reader_errors = [], []
        failure = MemoryError('CONTROLLED post-rejection reader')
        def refused(*args):
            self.assertEqual(len(result.failures), 1)
            raise failure
        bindings = dict(__builtins__=builtins.__dict__, unittest=unittest, ContractError=ContractError,
            rejection_timing=refused, rejection_diagnostics=diagnostics, diagnostic_reader_errors=reader_errors)
        exec(compile(ast.Module(body=[declaration(N / 'run_native.py', 'Result', True)], type_ignores=[]),
                     'exact-native-result-observer', 'exec'), bindings)
        result = bindings['Result'](unittest.runner._WritelnDecorator(io.StringIO()), True, 2)
        test = unittest.FunctionTestCase(lambda: None)
        primary = ContractError('CPU_EXECUTION_OWNER_TOO_SLOW')
        terms(primary)
        try:
            raise primary
        except ContractError:
            rejected = sys.exc_info()
            result.addFailure(test, rejected)
        self.assertEqual(len(result.failures), 1)
        self.assertIs(rejected[1], primary)
        self.assertIs(reader_errors[0], failure)
        self.assertEqual(diagnostics[0]['timing']['status'], 'unavailable')
        self.assertEqual(dict.get(BaseException.__dict__['__dict__'].__get__(primary), 'owned_cpu_timing')['elapsed_ns'], 50_000_001)


if __name__ == '__main__':
    forbidden = []
    def audit(event, args):
        if event in ('subprocess.Popen', 'os.system', 'os.startfile') or (event == 'ctypes.dlsym' and args[1] in (
                'CreateProcessW', 'CreateAppContainerProfile', 'DeleteAppContainerProfile', 'SetInformationJobObject')):
            forbidden.append(event)
            raise RuntimeError('NO_NATIVE_OPERATION_IN_TIMING_READER_CONTROL')
    sys.addaudithook(audit)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TimingReaderControls)
    expected = [test.id() for test in suite]
    executed, stopped = [], []
    class Result(unittest.TextTestResult):
        def startTest(self, test): executed.append(test.id()); super().startTest(test)
        def stopTest(self, test): stopped.append(test.id()); super().stopTest(test)
    out = N / ('timing-controls-' + sys.argv[1])
    out.mkdir(exist_ok=False)
    with (out / 'tests.txt').open('x', encoding='utf8') as raw:
        result = unittest.TextTestRunner(stream=raw, verbosity=2, resultclass=Result).run(suite)
    complete = result.wasSuccessful() and not result.skipped and expected == executed == stopped and not forbidden
    save(out / 'RESULT.json', dict(at=utc(), tests_run=result.testsRun, failures=len(result.failures),
        errors=len(result.errors), skips=len(result.skipped), expected_ids=expected, executed_ids=executed,
        stopped_ids=stopped, forbidden_calls=forbidden, actual_CETA_imports=[name for name in sys.modules if name == 'ceta' or name.startswith('ceta.')],
        source_kind='Exact function/class ASTs in controlled namespace; no original native test body',
        failure_details=[dict(id=t.id(), traceback=body) for t, body in result.failures + result.errors],
        native_execution='NOT_RUN', exit_status=0 if complete else 1))
    print(canonical(dict(tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors), exit_status=0 if complete else 1)))
    sys.exit(0 if complete else 1)
