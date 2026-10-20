"""Correct only test attribution; retain every functional byte of GD2."""
from datetime import datetime, timezone
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

R = Path(__file__).resolve().parent
F, RUN = R.parents[2], 'gd3-20261014'
Q, BASE = F / '.agents' / RUN, F / '.agents/gd2-20261014'
PREV = F / '.agents/runtime/gd2-20261014'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
now = lambda: datetime.now(timezone.utc).isoformat()
def save(path, data):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2); stream.write('\n')
def step(label, args):
    argv = ['powershell', '-NoProfile', '-File', r'T:\02-Config\agents\taar-orchestrate.ps1', *args, '--runtime-root', str(R)]
    done = subprocess.run(argv, capture_output=True)
    for suffix, data in (('stdout', done.stdout), ('stderr', done.stderr)):
        with (R / (label + '.' + suffix)).open('xb') as stream: stream.write(data)
    response = json.loads(done.stdout)
    save(R / (label + '.json'), {'argv': argv, 'exit_status': done.returncode, 'response': response})
    assert done.returncode == 0 and response.get('allowed') is True, response
    print(label + ': allowed', flush=True)

assert sha(BASE / 'TRANSFER-MANIFEST.json') == 'cd51569eedb171f822defce05a21b53ad79ca2005e51a9c0ac253564b3088d8a'
manifest = read(BASE / 'TRANSFER-MANIFEST.json')
assert len(manifest['payloads']) == 281 and not Q.exists()
for row in manifest['payloads']:
    relative = row['relative_path']
    assert sha(BASE / relative) == row['candidate_sha256']
    assert (sha(F / relative) if (F / relative).is_file() else None) == row['active_before_sha256']
Q.mkdir(exist_ok=False)
save(R / 'source-inputs.json', {'base_manifest_sha256': sha(BASE / 'TRANSFER-MANIFEST.json'), 'source_root': str(F),
    'source_payloads': 279, 'candidate_payloads': 281, 'new_source_LOC': 0, 'new_test_LOC': 0,
    'correction': 'Remove misplaced duplicate rollback observation from unavailable-mutation test; two reused lines receive zero new LOC credit',
    'publication': 'Requires actual persisted review binding and native original identity checks; Source publication remains pending'})
sys.path.insert(0, r'T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce')
from taar.orchestration_receipts import validate_receipt
step('run-init', ['run', 'init', '--root', 'T:\\', '--scope', str(Q), '--run-id', RUN])
for node in ('discover', 'plan'):
    step(node + '-claim', ['node', 'claim', RUN, node, '--executor', '/root', '--workspace', str(Q)])
    claim = read(R / RUN / 'claims.json')[node]
    receipt = {'schema_version': 1, 'run_id': RUN, 'node_id': node, 'executor_id': '/root', 'started_at': claim['claimed_at'],
               'finished_at': now(), 'input_hash': claim['input_hash'], 'changed_files': [],
               'result': {'source_inputs_sha256': sha(R / 'source-inputs.json'), 'existing_plan_reused': True},
               'commands': [{'command': 'Root checked exact GD2 candidate and current279 source before two-line test correction', 'exit_status': 0}],
               'validations': [{'name': 'exact_predecessor_and_current_source', 'passed': True}], 'exit_status': 0}
    validate_receipt(receipt, run_id=RUN, node_id=node, executor_id='/root', input_hash=claim['input_hash'],
                     claimed_at=claim['claimed_at'], node=read(R / RUN / 'graph.json')['graph']['nodes'][node])
    save(R / (node + '.json'), receipt)
    step(node + '-complete', ['node', 'complete', RUN, node, str(R / (node + '.json'))])
step('implement-claim', ['node', 'claim', RUN, 'implement', '--executor', '/root', '--workspace', str(Q)])
for row in manifest['payloads']:
    relative = row['relative_path']; data = (BASE / relative).read_bytes()
    target, original = Q / relative, R / 'originals' / relative
    for parent in (target.parent, original.parent): parent.mkdir(parents=True, exist_ok=True)
    for path in (target, original):
        with path.open('xb') as stream: stream.write(data)
test = Q / 'tests/contract/test_process_observation_validation.py'
text = test.read_text()
bad = "        observations.append({'case': 'asymmetric_precise_rollback', 'retained_public_high_water': sampler._last_clock,\n            'retained_precise_high_water': sampler._last_elapsed, 'counter_calls': port.calls})"
assert text.count(bad) == 2 and text.endswith(bad + '\n')
test.write_text(text[:-len(bad + '\n')], encoding='utf-8', newline='\n')
classes = [node for node in ast.parse(test.read_text()).body if isinstance(node, ast.ClassDef)]
assert [sum(isinstance(n, ast.FunctionDef) and n.name.startswith('test_') for n in c.body) for c in classes] == [7, 6]
save(R / 'validation-test-correction.json', {'prior_correction': str(PREV / 'validation-test-correction.json'),
    'removed_duplicate_lines': 2, 'corrected_new_test_meaningful_LOC': 131, 'new_functional_source_LOC': 0,
    'before_sha256': sha(R / 'originals/tests/contract/test_process_observation_validation.py'), 'after_sha256': sha(test),
    'original_seven_AST': 'Retained exact; only misplaced duplicate under sixth new method removed'})
runner = (PREV / 'run_tests.py').read_text().replace('gd2-20261014', 'gd3-20261014')
with (R / 'run_tests.py').open('x', encoding='utf-8', newline='\n') as stream: stream.write(runner)
print(json.dumps({'implement': 'RUNNING', 'source_payload_changes': 0, 'test_lines_removed': 2, 'candidate_payloads': 281}), flush=True)
