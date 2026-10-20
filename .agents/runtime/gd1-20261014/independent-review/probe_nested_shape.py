"""Finite malformed nested-frame investigation on an explicit synthetic port."""
from pathlib import Path
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import os
import sys
import unittest

O = Path(__file__).resolve().parent
F = O.parent.parents[2]
label = sys.argv[1]
assert label in {'candidate', 'baseline'}
SOURCE = F / '.agents/gd1-20261014' if label == 'candidate' else F
sys.dont_write_bytecode = True
sys.path[:0] = [str(SOURCE / 'src'), str(SOURCE / 'tests/contract')]
from ceta.resource.diagnostics import ResourceTelemetryRecorder
from test_process_diagnostics import ProcessDiagnosticsTests, counters, digest
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
before = sha(SOURCE / 'src/ceta/resource/diagnostics.py')
rows = []
for field in ('cpu_time_100ns', 'read_io_bytes', 'working_set_bytes'):
    for initial in (True, False):
        now, port, sampler = ProcessDiagnosticsTests().fixture()
        if not initial: sampler.sample(); now[0] = 110
        bad = counters(now[0])
        quantity = bad.working_set_bytes if field == 'working_set_bytes' else getattr(bad.usage, field)
        object.__setattr__(quantity, 'value', True)
        port.next = bad
        row = {'case': field, 'initial_frame': initial, 'stimulus': 'Explicit synthetic port returns mutated frozen nested quantity whose measured value has Python bool type'}
        try:
            sample = sampler.sample()
            row.update({'sample_returned': True, 'cpu_reason': sample.cpu_milli.reason,
                'memory_measured': sample.memory_bytes.measured, 'memory_value_type': type(sample.memory_bytes.value).__name__,
                'nested_cpu_value_type': None if sample.process_usage is None else type(sample.process_usage.cpu_time_100ns.value).__name__,
                'accepted_time': sampler._accepted_time, 'counter_bounds_types': [type(value).__name__ for value in sampler._counter_high_water]})
            try:
                ResourceTelemetryRecorder().record(sample)
                row['recorder_error'] = None
            except Exception as error:
                row['recorder_error'] = {'type': type(error).__name__, 'code': getattr(error, 'code', None)}
        except Exception as error:
            row.update({'sample_returned': False, 'sampler_error': {'type': type(error).__name__, 'code': getattr(error, 'code', None)}})
        rows.append(row)
now, port, sampler = ProcessDiagnosticsTests().fixture()
recorder = ResourceTelemetryRecorder(maximum_samples=3)
bad = counters(100)
object.__setattr__(bad.usage.cpu_time_100ns, 'value', True)
port.next = bad
try:
    sampler.collect(recorder)
    first_error = None
except Exception as error:
    first_error = {'type': type(error).__name__, 'code': getattr(error, 'code', None)}
recovery = []
for at in (110, 120):
    now[0], port.next = at, counters(at)
    sample = sampler.collect(recorder)
    recovery.append({'sequence': sample.source.sequence, 'cpu_measured': sample.cpu_milli.measured,
        'cpu_milli': sample.cpu_milli.value, 'reason': sample.cpu_milli.reason})
retained = recorder.recent(now_monotonic_ns=120, maximum_age_ns=100, scope_digest=digest('scope'))
analysis = ProcessDiagnosticsTests().analyze(retained)
report = {'executor': '/root/pressure_review', 'observed_at': datetime.now(timezone.utc).isoformat(),
    'source_root': str(SOURCE), 'source_before_sha256': before, 'source_after_sha256': sha(SOURCE / 'src/ceta/resource/diagnostics.py'),
    'stimulus_classification': 'EXPLICIT_DETERMINISTIC_MALFORMED_PORT_OUTPUT_NOT_NATIVE_OBSERVATION', 'rows': rows,
    'recovery_after_rejected_first_raw_frame': {'initial_recording_error': first_error, 'recovery_samples': recovery,
        'retained_sequences': [sample.source.sequence for sample in retained], 'analysis_measurement_state': analysis.measurement_state,
        'analysis_peak_cpu_milli': analysis.telemetry.peak_cpu_milli, 'analysis_findings': list(analysis.findings)},
    'native_children_launched': 0, 'source_changes': [], 'policy_or_authority_changes': [], 'probe_finished': True}
assert report['source_before_sha256'] == report['source_after_sha256']
with (O / ('nested-shape-' + label + '.json')).open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(report, stream, indent=2); stream.write('\n')
print(json.dumps(report, indent=2))
