"""Independent deterministic boundary challenges; no native producer claim."""
from pathlib import Path
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import os
import sys
import time
import unittest
from unittest.mock import patch

O = Path(__file__).resolve().parent
R = O.parent
F = R.parents[2]
Q = F / '.agents/gd1-20261014'
sys.dont_write_bytecode = True
sys.path[:0] = [str(Q / 'src'), str(Q / 'tests/contract')]
from ceta.resource.diagnostics import ResourceTelemetryRecorder
from ceta.contracts.wire import ContractError
from test_process_observation_timing import ProcessObservationTimingTests
from test_process_diagnostics import counters
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
observations = []

class IndependentTimingBoundaryTests(unittest.TestCase):
    fixture = ProcessObservationTimingTests.fixture

    def test_after_public_precise_rollback_keeps_both_high_waters(self):
        now, elapsed, port, sampler = self.fixture()
        sampler.sample()
        now[0] = 110
        sequence = iter((1020, 1019))
        sampler._elapsed_clock = lambda: next(sequence)
        denied = sampler.sample()
        self.assertEqual(denied.cpu_milli.reason, 'PROCESS_CLOCK_ROLLBACK')
        self.assertEqual((sampler._last_clock, sampler._last_elapsed, port.calls), (110, 1020, 1))
        sampler._elapsed_clock = lambda: elapsed[0]
        for stamp in (1018, 1019):
            now[0], elapsed[0] = now[0] + 1, stamp
            self.assertFalse(sampler.sample().memory_bytes.measured)
            self.assertEqual(sampler._last_elapsed, 1020)
        now[0], elapsed[0] = 120, 1030
        self.assertEqual(sampler.sample().cpu_milli.reason, 'PROCESS_CPU_BASELINE_REQUIRED')
        observations.append({'case': 'asymmetric_precise_rollback', 'retained_public_high_water': sampler._last_clock,
            'retained_precise_high_water': sampler._last_elapsed, 'counter_calls': port.calls})

    def test_precise_read_exception_does_not_reset_public_high_water(self):
        now, elapsed, port, sampler = self.fixture()
        sampler.sample()
        now[0] = 110
        interruption = SystemExit(19)
        calls = [0]
        def elapsed_read():
            calls[0] += 1
            if calls[0] == 2: raise interruption
            return 1020
        sampler._elapsed_clock = elapsed_read
        with self.assertRaises(SystemExit) as caught: sampler.sample()
        self.assertIs(caught.exception, interruption)
        self.assertEqual((sampler._last_clock, sampler._last_elapsed), (110, 1020))
        self.assertIsNone(sampler._cached)
        sampler._elapsed_clock = lambda: elapsed[0]
        now[0], elapsed[0] = 109, 1030
        self.assertEqual(sampler.sample().cpu_milli.reason, 'PROCESS_CLOCK_ROLLBACK')
        now[0], elapsed[0] = 120, 1040
        self.assertEqual(sampler.sample().cpu_milli.reason, 'PROCESS_CPU_BASELINE_REQUIRED')

    def test_final_public_clock_lookup_time_invalidates_counter_frame(self):
        now, elapsed, port, sampler = self.fixture()
        sampler.sample()
        original_bounds = (sampler._accepted_time, tuple(sampler._counter_high_water))
        now[0], elapsed[0] = 110, 1010
        calls = [0]
        def public():
            calls[0] += 1
            if calls[0] == 3: elapsed[0] += 31
            return now[0]
        sampler._clock = public
        denied = sampler.sample()
        self.assertEqual(denied.cpu_milli.reason, 'PROCESS_PROBE_TOO_SLOW')
        self.assertEqual((sampler._accepted_time, tuple(sampler._counter_high_water)), original_bounds)
        self.assertIsNone(denied.process_usage)
        self.assertEqual(port.calls, 2)

    def test_unaccepted_large_counter_does_not_poison_accepted_counter_high_water(self):
        now, elapsed, port, sampler = self.fixture()
        sampler.sample()
        now[0], elapsed[0] = 110, 1010
        def slow_large_frame():
            elapsed[0] += 31
            return counters(110, cpu=9999, read=9999, write=9999)
        with patch.object(port, 'resource_counters', side_effect=slow_large_frame):
            denied = sampler.sample()
        self.assertEqual(denied.cpu_milli.reason, 'PROCESS_PROBE_TOO_SLOW')
        self.assertEqual(tuple(sampler._counter_high_water), (100, 100, 50))
        now[0], elapsed[0] = 120, 1050
        recovered = sampler.sample()
        self.assertTrue(recovered.memory_bytes.measured)
        self.assertEqual(recovered.cpu_milli.reason, 'PROCESS_CPU_BASELINE_REQUIRED')

    def test_recorder_delay_never_extends_cached_frame_lifetime(self):
        now, elapsed, port, sampler = self.fixture(interval=50, age=200, window=100)
        recorder = ResourceTelemetryRecorder(maximum_samples=2)
        original = recorder.record
        def late_retention(frame):
            elapsed[0] += 75
            return original(frame)
        with patch.object(recorder, 'record', side_effect=late_retention): first = sampler.collect(recorder)
        now[0] = 101
        second = sampler.collect(recorder)
        self.assertIsNot(second, first)
        self.assertEqual((first.source.sequence, second.source.sequence, port.calls), (1, 2, 2))

    def test_quantization_cache_age_boundary_is_inclusive_then_reprobed(self):
        now, elapsed, port, sampler = self.fixture(interval=90, age=100, window=100, resolution=5)
        first = sampler.sample()
        now[0], elapsed[0] = 195, 1040
        self.assertIs(sampler.sample(), first)
        now[0], elapsed[0] = 196, 1041
        refreshed = sampler.sample()
        self.assertIsNot(refreshed, first)
        self.assertEqual((port.calls, refreshed.cpu_milli.reason, refreshed.memory_bytes.measured),
                         (2, 'PROCESS_CPU_BASELINE_REQUIRED', True))

    def test_malformed_frame_interrupts_cache_without_erasing_accepted_bounds(self):
        now, elapsed, port, sampler = self.fixture()
        sampler.sample()
        original_bounds = sampler._accepted_time, tuple(sampler._counter_high_water)
        bad = counters(110)
        object.__setattr__(bad.usage.cpu_time_100ns, 'value', True)
        now[0], elapsed[0], port.next = 110, 1010, bad
        with self.assertRaises(ContractError): sampler.sample()
        self.assertIsNone(sampler._cached)
        self.assertEqual((sampler._accepted_time, tuple(sampler._counter_high_water)), original_bounds)
        now[0], elapsed[0], port.next = 120, 1020, counters(120)
        self.assertEqual(sampler.sample().cpu_milli.reason, 'PROCESS_CPU_BASELINE_REQUIRED')

before = sha(Q / 'src/ceta/resource/diagnostics.py')
suite = unittest.defaultTestLoader.loadTestsFromTestCase(IndependentTimingBoundaryTests)
expected = [test.id() for test in suite]
executed = []
class Result(unittest.TextTestResult):
    def startTest(self, test): executed.append(test.id()); super().startTest(test)
begin = time.perf_counter()
result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2, resultclass=Result).run(suite)
after = sha(Q / 'src/ceta/resource/diagnostics.py')
passed = result.wasSuccessful() and not result.skipped and before == after and expected == executed
data = {'executor': '/root/pressure_review', 'recorded_at': datetime.now(timezone.utc).isoformat(),
    'tests_run': result.testsRun, 'expected_ids': expected, 'executed_ids': executed, 'failures': len(result.failures),
    'errors': len(result.errors), 'skips': len(result.skipped), 'seconds': time.perf_counter() - begin,
    'failure_details': [{'test_id': test.id(), 'traceback': trace} for test, trace in result.failures + result.errors],
    'observations': observations, 'source_before_sha256': before, 'source_after_sha256': after,
    'classification': 'INDEPENDENT_DETERMINISTIC_BOUNDARY_PROBES_EXPLICIT_INJECTED_COUNTERS_AND_CLOCKS',
    'native_tests_in_this_script': 0, 'production_integration_claim': False, 'exit_status': 0 if passed else 1}
with (O / 'hostile-timing-probes.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(data, stream, indent=2); stream.write('\n')
print(json.dumps({'independent_boundary_tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
    'skips': len(result.skipped), 'receipt_sha256': sha(O / 'hostile-timing-probes.json'), 'exit_status': data['exit_status']}))
raise SystemExit(data['exit_status'])
