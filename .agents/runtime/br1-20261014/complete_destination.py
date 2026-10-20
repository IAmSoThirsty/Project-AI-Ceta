"""Accept exact four-path integration after actual destination execution/review."""
from datetime import datetime, timezone
from pathlib import Path
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
claim = read(R / RUN / 'claims.json')['integrate']
assert claim['executor_id'] == '/root' and claim['workspace'] == str(F)
manifest_path = Q / 'TRANSFER-MANIFEST.json'
journal_path = R / 'active-application/APPLIED.json'
suite_path = R / 'destination-desktop.json'
review_path = R / 'active-destination-review/destination-review.json'
manifest, journal, suite, review = [read(p) for p in (manifest_path, journal_path, suite_path, review_path)]
assert sha(manifest_path) == '12fe2b2a79164fc0efb180c4b8c7d043006af80b61242a707aa92b95dff9d040'
assert sha(journal_path) == '1a53057f5cd670f8edec2cb987f4d9eccb763d4f2863919519b225b51bedcfed'
assert journal['claim_input_hash'] == claim['input_hash'] and len(journal['completed']) == 4
assert suite['active_destination_root'] == str(F) and suite['tests_run'] == 118
assert suite['failures'] == suite['errors'] == suite['skips'] == suite['exit_status'] == 0
assert suite['expected_ids'] == suite['executed_ids'] and len(set(suite['executed_ids'])) == 118
assert sha(R / 'destination-desktop.txt') == suite['raw_sha256']
assert suite['actual_application_journal_sha256'] == sha(journal_path)
assert review['decision'] == 'approved' and review['exit_status'] == 0 and review['source_root'] == str(F)
assert review['manifest_sha256'] == sha(manifest_path) and review['application_journal_sha256'] == sha(journal_path)
assert review['destination_suite_sha256'] == sha(suite_path) and review['tests_run'] == suite['tests_run']
expected = {item['relative_path']: item['candidate_sha256'] for item in manifest['payloads']}
assert len(expected) == 235 and expected == suite['before_hashes'] == suite['after_hashes'] == review['expected_payload_hashes']
for relative, digest in expected.items():
    assert sha(F / relative) == sha(Q / relative) == digest
for item in journal['before_images']:
    relative = item['relative_path']
    native = R / 'active-application/native-backups' / (relative + '.original')
    logical = R / 'active-application/before' / (relative + '.source')
    assert sha(native) == sha(logical) == item['sha256']
    facts = native.stat()
    assert (facts.st_dev, facts.st_ino, facts.st_mode, facts.st_size, facts.st_mtime_ns) == (item['device'], item['inode'], item['mode'], item['bytes'], item['mtime_ns'])
print(json.dumps({'stage': 'real_active_root_snapshot', 'destination_cases': 118, 'payloads': 235}), flush=True)
changed = _changed_files(claim['baseline_snapshot'], _snapshot_workspace(F, Path('T:/')))
allowed = sorted((F / relative).relative_to(Path('T:/')).as_posix() for relative in manifest['application_paths'])
assert changed == allowed
receipt = {'schema_version': 1, 'run_id': RUN, 'node_id': 'integrate', 'executor_id': '/root',
    'started_at': journal['started_at'], 'finished_at': now(), 'input_hash': claim['input_hash'], 'changed_files': changed,
    'result': {'status': 'FOUR_ACTIVE_PRODUCT_TITLES_APPLIED_AND_INDEPENDENTLY_VERIFIED', 'source_root': str(F),
        'manifest_sha256': sha(manifest_path), 'application_journal_sha256': sha(journal_path),
        'destination_suite_sha256': sha(suite_path), 'independent_destination_review_sha256': sha(review_path),
        'tests_run': 118, 'failures': 0, 'errors': 0, 'skips': 0, 'source_payloads': 235,
        'observed_title_modules': suite['observed_title_modules'], 'source_physical_LOC': {'added': 4, 'removed': 4},
        'new_test_LOC': 0, 'native_and_logical_originals_preserved': 4,
        'public_interfaces_and_namespace_retained': True, 'title_changes': manifest['title_changes'],
        'historical_root_scope': 'APP3 full1158 source suite remains preserved; current four-title cohort and relocation proof are separately bound'},
    'commands': [{'command': 'Reviewed apply_reviewed_titles.py; four exact native replacements', 'exit_status': 0},
        {'command': 'own current e3 Python -B -X utf8 run_destination_desktop.py; actual118 connected cases and native titles', 'exit_status': 0},
        {'command': 'Distinct actual destination review bound by report SHA; source/originals/imports and tests inspected', 'exit_status': 0},
        {'command': 'Real TAAR current-root snapshot matches exactly four changed paths', 'exit_status': 0}],
    'validations': [{'name': 'current235_payloads_four_publication_paths_and_all_originals_exact', 'passed': True},
        {'name': 'actual118_tests_and_all_four_native_title_modules', 'passed': True},
        {'name': 'independent_current_destination_approval', 'passed': True}], 'exit_status': 0}
normalized = validate_receipt(receipt, run_id=RUN, node_id='integrate', executor_id=claim['executor_id'],
    input_hash=claim['input_hash'], claimed_at=claim['claimed_at'], node=read(R / RUN / 'graph.json')['graph']['nodes']['integrate'])
receipt_path = R / 'integrate.json'
with receipt_path.open('x', encoding='utf-8') as output:
    json.dump(receipt, output, indent=2)
    output.write('\n')
assert load_receipt(receipt_path) == receipt and normalized['changed_files'] == changed
argv = ['powershell', '-NoProfile', '-File', r'T:\02-Config\agents\taar-orchestrate.ps1', 'node', 'complete', RUN,
    'integrate', str(receipt_path), '--runtime-root', str(R)]
done = subprocess.run(argv, capture_output=True)
for suffix, data in (('stdout', done.stdout), ('stderr', done.stderr)):
    with (R / ('active-integrate-complete.' + suffix)).open('xb') as output:
        output.write(data)
response = json.loads(done.stdout)
assert done.returncode == 0 and response.get('allowed') is True, response
state = read(R / RUN / 'state.json')
assert set(state['nodes']) == {'discover', 'plan', 'implement', 'review', 'validate', 'integrate'}
assert all(node['state'] == 'SUCCEEDED' for node in state['nodes'].values())
assert not read(R / RUN / 'claims.json')
with (R / 'actual-acceptance.json').open('x', encoding='utf-8') as output:
    json.dump({'recorded_at': now(), 'source_root': str(F), 'sequence': state['sequence'], 'claims': {},
        'actual_states': {name: node['state'] for name, node in state['nodes'].items()},
        'integrate_receipt_sha256': sha(receipt_path), 'destination_tests': 118, 'source_payloads': 235}, output, indent=2)
    output.write('\n')
print(json.dumps({'actual_integration': 'SUCCEEDED', 'sequence': state['sequence'],
    'receipt_sha256': sha(receipt_path), 'source_title_paths': len(changed)}), flush=True)
