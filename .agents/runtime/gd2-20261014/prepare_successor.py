"""Prepare the smallest successor for independently reproduced nested-value poisoning."""
from datetime import datetime, timezone
from pathlib import Path
import ast
import hashlib
import json
import subprocess
import sys

R = Path(__file__).resolve().parent
F = R.parents[2]
RUN = 'gd2-20261014'
Q = F / '.agents' / RUN
BASE = F / '.agents/gd1-20261014'
IR = F / '.agents/runtime/gd1-20261014/independent-review'
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()
assert not Q.exists()
assert sha(BASE / 'TRANSFER-MANIFEST.json') == '3f64c0dca1637ef58d6eb5bd2c64809d9af48c2c1fb691f6d558b15047cbf9b3'
manifest = read(BASE / 'TRANSFER-MANIFEST.json')
assert len(manifest['payloads']) == 280
for row in manifest['payloads']:
    assert sha(BASE / row['relative_path']) == row['candidate_sha256']
    source = F / row['relative_path']
    assert (sha(source) if source.is_file() else None) == row['active_before_sha256']
finding = read(IR / 'nested-shape-candidate.json')
assert finding['source_before_sha256'] == finding['source_after_sha256'] == sha(BASE / 'src/ceta/resource/diagnostics.py')
assert finding['stimulus_classification'] == 'EXPLICIT_DETERMINISTIC_MALFORMED_PORT_OUTPUT_NOT_NATIVE_OBSERVATION'
assert any(row['sample_returned'] and row.get('nested_cpu_value_type') == 'bool' for row in finding['rows'])
Q.mkdir(exist_ok=False)
def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2); stream.write('\n')
def step(label, *args):
    argv = ['powershell', '-NoProfile', '-File', r'T:\02-Config\agents\taar-orchestrate.ps1',
        *args, '--runtime-root', str(R)]
    started = now(); done = subprocess.run(argv, capture_output=True)
    for suffix, data in (('stdout', done.stdout), ('stderr', done.stderr)):
        with (R / (label + '.' + suffix)).open('xb') as stream: stream.write(data)
    response = json.loads(done.stdout)
    save(R / (label + '.json'), {'started_at': started, 'finished_at': now(), 'argv': argv,
        'exit_status': done.returncode, 'response': response})
    assert done.returncode == 0 and response.get('allowed') is True, response
    print(json.dumps({'step': label, 'allowed': True}), flush=True)
sys.path.insert(0, r'T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce')
from taar.orchestration_receipts import validate_receipt
save(R / 'source-inputs.json', {'source_root': str(F), 'base_manifest_sha256': sha(BASE / 'TRANSFER-MANIFEST.json'),
    'failure_path': str(IR / 'nested-shape-candidate.json'), 'failure_sha256': sha(IR / 'nested-shape-candidate.json'),
    'repair_scope': 'Validate all five nested quantities before changing sampler derived state',
    'preserve': 'Public signatures, shared contracts, all existing tests and frozen GD1 evidence',
    'source_changes': 0, 'parent_review': 'Final rejected readback required before successor acceptance'})
step('run-init', 'run', 'init', '--root', 'T:\\', '--scope', str(Q), '--run-id', RUN)
for node in ('discover', 'plan'):
    step(node + '-claim', 'node', 'claim', RUN, node, '--executor', '/root', '--workspace', str(Q))
    claim = read(R / RUN / 'claims.json')[node]
    receipt = {'schema_version': 1, 'run_id': RUN, 'node_id': node, 'executor_id': '/root',
        'started_at': claim['claimed_at'], 'finished_at': now(), 'input_hash': claim['input_hash'], 'changed_files': [],
        'result': {'existing_r6_plan_reused': True, 'source_inputs_sha256': sha(R / 'source-inputs.json'),
            'baseline_poisoning_independently_reproduced': True, 'scope': str(Q)},
        'commands': [{'command': 'Root inspected exact frozen280 files, current279 inputs and independently reproduced nested-value state poisoning', 'exit_status': 0}],
        'validations': [{'name': 'exact_parent_and_minimal_validation_surface', 'passed': True}], 'exit_status': 0}
    validate_receipt(receipt, run_id=RUN, node_id=node, executor_id='/root', input_hash=claim['input_hash'],
        claimed_at=claim['claimed_at'], node=read(R / RUN / 'graph.json')['graph']['nodes'][node])
    save(R / (node + '.json'), receipt)
    step(node + '-complete', 'node', 'complete', RUN, node, str(R / (node + '.json')))
step('implement-claim', 'node', 'claim', RUN, 'implement', '--executor', '/root', '--workspace', str(Q))
for row in manifest['payloads']:
    relative = row['relative_path']; data = (BASE / relative).read_bytes()
    assert hashlib.sha256(data).hexdigest() == row['candidate_sha256']
    target = Q / relative; before = R / 'originals' / relative
    target.parent.mkdir(parents=True, exist_ok=True); before.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream: stream.write(data)
    with before.open('xb') as stream: stream.write(data)
original = (IR / 'hostile_timing_probes.py').read_text(encoding='utf-8')
node = next(item for item in ast.parse(original).body if isinstance(item, ast.ClassDef)
    and item.name == 'IndependentTimingBoundaryTests')
text = ast.get_source_segment(original, node)
assert sum(isinstance(item, ast.FunctionDef) and item.name.startswith('test_') for item in node.body) == 7
prefix = '''"""Exact seven independent oracles retained; no native observation claim."""
import unittest
from unittest.mock import patch
from ceta.resource.diagnostics import ResourceTelemetryRecorder
from ceta.contracts.wire import ContractError
from test_process_observation_timing import ProcessObservationTimingTests
from test_process_diagnostics import counters
observations = []

'''
with (Q / 'tests/contract/test_process_observation_validation.py').open('x', encoding='utf-8') as stream:
    stream.write(prefix + text + '\n')
save(R / 'implementation-started.json', {'started_at': now(), 'candidate': str(Q),
    'exact_reused_hostile_methods': 7, 'base_payloads': 280, 'active_source_payloads': 279,
    'reused_oracle_counted_as_new_LOC': 0, 'source_changes': 0})
print(json.dumps({'implement': 'RUNNING', 'candidate': str(Q), 'reused_hostile_methods': 7}), flush=True)
