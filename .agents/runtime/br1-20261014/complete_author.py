"""Complete the actual writer claim only after exact code and native UI proof."""
from datetime import datetime, timezone
from pathlib import Path
import ast
import hashlib
import json
import subprocess
import sys

R = Path(__file__).resolve().parent
F = R.parents[2]
Q = F / '.agents/br1-20261014'
RUN = 'br1-20261014'
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()
sys.path.insert(0, r'T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce')
from taar.orchestration_receipts import validate_receipt, load_receipt
from taar.orchestration_runtime import _snapshot_workspace, _changed_files
manifest_path = Q / 'TRANSFER-MANIFEST.json'
manifest = read(manifest_path)
proof_path = R / 'connected-desktop.json'
proof = read(proof_path)
assert proof['manifest_sha256'] == sha(manifest_path) == '12fe2b2a79164fc0efb180c4b8c7d043006af80b61242a707aa92b95dff9d040'
assert proof['tests_run'] == 118 and proof['failures'] == proof['errors'] == proof['skips'] == proof['exit_status'] == 0
assert proof['expected_ids'] == proof['executed_ids'] and len(set(proof['executed_ids'])) == 118
assert proof['raw_sha256'] == sha(R / 'connected-desktop.txt')
ast_checks = []
for item in manifest['payloads']:
    relative = item['relative_path']
    assert sha(Q / relative) == item['candidate_sha256']
    assert sha(F / relative) == item['active_before_sha256']
    if relative in manifest['application_paths']:
        before = R / 'before' / (relative + '.source')
        assert sha(before) == item['active_before_sha256']
        old, new = manifest['title_changes'][relative]
        expected = before.read_bytes().replace(('setWindowTitle("' + old + '")').encode(),
                                               ('setWindowTitle("' + new + '")').encode(), 1)
        assert expected == (Q / relative).read_bytes()
        left, right = ast.parse(before.read_text()), ast.parse((Q / relative).read_text())
        replaced = 0
        for node in ast.walk(left):
            if isinstance(node, ast.Constant) and node.value == old:
                node.value = new
                replaced += 1
        assert replaced == 1 and ast.dump(left, include_attributes=False) == ast.dump(right, include_attributes=False)
        ast_checks.append({'path': relative, 'only_one_title_literal_changed': True})
assert len(ast_checks) == 4
claim = read(R / RUN / 'claims.json')['implement']
assert claim['executor_id'] == '/root' and claim['workspace'] == str(Q)
changed = _changed_files(claim['baseline_snapshot'], _snapshot_workspace(Q, Path('T:/')))
assert len(changed) == 236
receipt = {'schema_version': 1, 'run_id': RUN, 'node_id': 'implement', 'executor_id': '/root',
    'started_at': read(R / 'implementation-started.json')['started_at'], 'finished_at': now(),
    'input_hash': claim['input_hash'], 'changed_files': changed,
    'result': {'source_root': str(F), 'candidate_root': str(Q), 'manifest': str(manifest_path),
        'manifest_sha256': sha(manifest_path), 'payload_count': 235, 'changed_source_paths': manifest['application_paths'],
        'unchanged_dependencies': 231, 'physical_source_LOC': {'added': 4, 'removed': 4}, 'new_test_LOC': 0,
        'source_ast_checks': ast_checks, 'tests_run': 118, 'failures': 0, 'errors': 0, 'skips': 0,
        'test_receipt': str(proof_path), 'test_receipt_sha256': sha(proof_path),
        'raw_test_output_sha256': proof['raw_sha256'], 'actual_native_title_modules': proof['observed_title_modules'],
        'actual_source_unchanged': True, 'current_application': 'PENDING_DISTINCT_REVIEW_AND_FRESH_ACTIVE_SOURCE_CAS'},
    'commands': [{'command': 'own F e3 Python -B -X utf8 run_connected_desktop.py; existing connected118 desktop regressions and actual Qt windowTitle observations', 'exit_status': 0},
                 {'command': 'complete_author.py; exact235 hashes and four title-only AST equivalences; actual Q snapshot and strict receipt validation', 'exit_status': 0}],
    'validations': [{'name': 'exact235_candidate_and_active_before_payloads', 'passed': True},
                    {'name': 'four_title_constants_only_with_public_interfaces_retained', 'passed': True},
                    {'name': 'all118_connected_regressions_and_four_native_title_modules', 'passed': True}],
    'exit_status': 0}
validate_receipt(receipt, run_id=RUN, node_id='implement', executor_id=claim['executor_id'],
    input_hash=claim['input_hash'], claimed_at=claim['claimed_at'], node=read(R / RUN / 'graph.json')['graph']['nodes']['implement'])
receipt_path = R / 'implement.json'
with receipt_path.open('x', encoding='utf-8') as output:
    json.dump(receipt, output, indent=2)
    output.write('\n')
assert load_receipt(receipt_path) == receipt
argv = ['powershell', '-NoProfile', '-File', r'T:\02-Config\agents\taar-orchestrate.ps1', 'node', 'complete', RUN,
        'implement', str(receipt_path), '--runtime-root', str(R)]
done = subprocess.run(argv, capture_output=True)
for suffix, data in (('stdout', done.stdout), ('stderr', done.stderr)):
    with (R / ('implement-complete.' + suffix)).open('xb') as output:
        output.write(data)
response = json.loads(done.stdout)
assert done.returncode == 0 and response.get('allowed') is True, response
assert read(R / RUN / 'state.json')['nodes']['implement']['state'] == 'SUCCEEDED'
assert not read(R / RUN / 'claims.json')
print(json.dumps({'actual_implement_state': 'SUCCEEDED', 'source_paths': 4, 'tests': 118,
                  'receipt_sha256': sha(receipt_path)}))
