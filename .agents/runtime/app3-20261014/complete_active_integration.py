"""Bind exact active publication, full execution and separate review to real claim."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys

R = Path(__file__).resolve().parent
S = R.parents[2]
Q = S / '.agents/app3-20261014'
RUN = 'app3-20261014'
P4 = S / '.agents/pr4-20261014/preserve_ceta_complete.py'
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()
assert sha(P4) == '2ccbca31973ead308e1cdcc6676bbd7371cdec29a0f16178f3f55a4ab4130618'
spec = importlib.util.spec_from_file_location('ceta_app3_completion_io', P4)
fs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fs)

def exact_sha(path):
    with fs.open_source(fs.safe_components(path), exclusive=True) as stream:
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
        return digest.hexdigest()

def save(path, data):
    with path.open('x', encoding='utf-8') as output:
        json.dump(data, output, indent=2)
        output.write('\n')

sys.path.insert(0, r'T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce')
from taar.orchestration_receipts import load_receipt, validate_receipt
from taar.orchestration_runtime import _snapshot_workspace, _changed_files

claim = read(R / RUN / 'claims.json')['integrate']
state = read(R / RUN / 'state.json')
graph = read(R / RUN / 'graph.json')['graph']
assert claim['executor_id'] == '/root' and claim['workspace'] == str(S)
assert state['nodes']['integrate']['state'] == 'RUNNING'
assert state['nodes']['review']['state'] == state['nodes']['validate']['state'] == 'SUCCEEDED'
manifest_path = Q / 'TRANSFER-MANIFEST.json'
journal_path = R / 'active-application/APPLICATION.json'
full_path = S / '.agents/runtime/rs2-20261014/active-application/destination-full-r2.json'
review_path = R / 'active-destination-review/destination-review.json'
manifest = read(manifest_path)
journal = read(journal_path)
full = read(full_path)
review = read(review_path)
assert exact_sha(manifest_path) == '491955891bd35135579fd525b312c3f7b54e727ee2be55d189eb76293606ed0b'
assert exact_sha(journal_path) == '308dcd7bc20bf807e32ea114aa1e61088c9d39ee34be3532ea58feb279b23e2d'
assert exact_sha(S / '.agents/runtime/rs2-20261014/apply_joined_source.py') == '4592a2ccee83904c6fd698a2145d82279e07c0cc27cabb45fd1c13b844baec77'
assert journal['claim_input_hash'] == claim['input_hash']
assert datetime.fromisoformat(journal['started_at']) >= datetime.fromisoformat(claim['claimed_at'])
assert full['exit_status'] == 0 and full['tests_run'] > 0
assert full['failures'] == full['errors'] == full['skips'] == 0
assert full['source_unchanged'] is True and full['native_census']['exit_status'] == 0
assert full['native_census']['result']['clear'] is True
assert full['root'] == str(S)
assert full['expected_ids'] == full['executed_ids']
assert len(full['expected_ids']) == full['tests_run'] == len(set(full['expected_ids']))
assert exact_sha(full_path.with_suffix('.txt')) == full['output_sha256']
assert review['decision'] == 'approved' and review['exit_status'] == 0
assert review['source_root'] == str(S)
assert review['manifest_sha256'] == exact_sha(manifest_path)
assert review['application_journal_sha256'] == exact_sha(journal_path)
assert review['full_suite_sha256'] == exact_sha(full_path)
assert review['full_suite_tests_run'] == full['tests_run']
expected = {item['relative_path']: item['candidate_sha256'] for item in manifest['payloads']}
assert len(expected) == len(manifest['payloads']) == 235
assert expected == full['expected_payload_hashes'] == full['before_hashes'] == full['after_hashes']
assert expected == review['expected_payload_hashes']
for relative, digest in expected.items():
    assert exact_sha(Q / relative) == exact_sha(S / relative) == digest, relative
application_paths = set(manifest['application_paths'])
assert len(application_paths) == 7
assert {item['relative_path'] for item in journal['completed']} == application_paths
assert len(journal['before_images']) == 5
for item in journal['before_images']:
    relative = item['relative_path']
    assert relative in application_paths
    original = R / 'active-application/native-backups' / (relative + '.original')
    logical = R / 'active-application/before' / (relative + '.source')
    assert exact_sha(original) == exact_sha(logical) == item['sha256']
    facts = original.stat()
    assert facts.st_dev == item['device'] and facts.st_ino == item['inode']
    assert facts.st_size == item['bytes'] and facts.st_mtime_ns == item['mtime_ns']
    assert facts.st_mode == item['mode']

print(json.dumps({'stage': 'active_workspace_snapshot', 'tests_run': full['tests_run'],
                  'payloads': len(expected), 'review_sha256': exact_sha(review_path)}), flush=True)
snapshot_started = now()
after = _snapshot_workspace(S, Path('T:/'))
changed = _changed_files(claim['baseline_snapshot'], after)
expected_changed = sorted((S / relative).relative_to(Path('T:/')).as_posix()
                          for relative in application_paths)
assert changed == expected_changed, {'observed': changed, 'expected': expected_changed}
receipt = {
    'schema_version': 1, 'run_id': RUN, 'node_id': 'integrate', 'executor_id': '/root',
    'started_at': journal['started_at'], 'finished_at': now(), 'input_hash': claim['input_hash'],
    'changed_files': changed,
    'result': {
        'status': 'ACTIVE_SOURCE_APPLIED_FULL_SUITE_AND_INDEPENDENT_DESTINATION_VERIFIED',
        'source_root': str(S), 'candidate_root': str(Q), 'publication_paths': sorted(application_paths),
        'transfer_manifest': str(manifest_path), 'transfer_manifest_sha256': exact_sha(manifest_path),
        'application_journal': str(journal_path), 'application_journal_sha256': exact_sha(journal_path),
        'independent_review': str(review_path), 'independent_review_sha256': exact_sha(review_path),
        'full_suite': str(full_path), 'full_suite_sha256': exact_sha(full_path),
        'full_suite_raw_output_sha256': full['output_sha256'], 'tests_run': full['tests_run'],
        'failures': 0, 'errors': 0, 'skips': 0, 'payloads_verified': len(expected),
        'original_files_preserved': len(journal['before_images']), 'native_census': full['native_census'],
        'physical_source_transfer_LOC': {'added': 348, 'removed': 4},
        'physical_test_transfer_LOC': {'added': 805, 'removed': 9},
        'physical_contract_document_transfer_LOC': {'added': 74, 'removed': 0},
        'baseline_and_current_actual_snapshot_changes': changed,
        'snapshot_started_at': snapshot_started,
        'historical_failure_preservation': {
            'RS2_failed_source_integration': str(S / '.agents/runtime/rs2-20261014/integrate.json'),
            'sha256': exact_sha(S / '.agents/runtime/rs2-20261014/integrate.json'),
            'state': 'FAILED',
            'RD1_rejected_candidate_is_retained': True,
        },
        'next_dependency': 'Fresh whole-repository rename preservation and seven conditional identity applications',
    },
    'commands': [
        {'command': 'Python312 -B -X utf8 .agents/runtime/rs2-20261014/apply_joined_source.py', 'exit_status': 0},
        {'command': 'own e3 python -B -X utf8 .agents/runtime/rs2-20261014/run_destination-r3.py r2 app3-20261014', 'exit_status': full['exit_status']},
        {'command': 'Separate reviewer active destination byte/import/native/test verification; bound report ' + str(review_path), 'exit_status': review['exit_status']},
        {'command': 'Real TAAR _snapshot_workspace and exact seven-path baseline comparison', 'exit_status': 0},
    ],
    'validations': [
        {'name': 'actual_active_claim_and_exact235_payload_hashes', 'passed': True},
        {'name': 'exact_seven_changes_only_and_five_native_originals_preserved', 'passed': True},
        {'name': 'all_discovered_actual_source_test_ids_executed_without_failures_errors_skips', 'passed': True},
        {'name': 'independent_actual_destination_review_and_native_custody_clear', 'passed': True},
        {'name': 'historical_failed_and_rejected_evidence_preserved', 'passed': True},
    ],
    'exit_status': 0,
}
validated = validate_receipt(receipt, run_id=RUN, node_id='integrate',
    executor_id=claim['executor_id'], input_hash=claim['input_hash'],
    claimed_at=claim['claimed_at'], node=graph['nodes']['integrate'])
receipt_path = R / 'integrate.json'
save(receipt_path, receipt)
assert load_receipt(receipt_path) == receipt
assert validated['changed_files'] == changed
save(R / 'integrate-strict-validation.json', {'recorded_at': now(), 'validated': True,
    'receipt_sha256': exact_sha(receipt_path), 'normalized_receipt_hash': validated['receipt_hash'],
    'actual_changed_files': changed})
argv = ['powershell', '-NoProfile', '-File', r'T:\02-Config\agents\taar-orchestrate.ps1',
    'node', 'complete', RUN, 'integrate', str(receipt_path), '--runtime-root', str(R)]
started = now()
done = subprocess.run(argv, capture_output=True)
for suffix, data in (('stdout', done.stdout), ('stderr', done.stderr)):
    with (R / ('active-integrate-complete.' + suffix)).open('xb') as stream:
        stream.write(data)
response = json.loads(done.stdout)
save(R / 'active-integrate-complete.json', {'started_at': started, 'finished_at': now(),
    'argv': argv, 'exit_status': done.returncode, 'response': response})
assert done.returncode == 0 and response.get('allowed') is True, response
final_state = read(R / RUN / 'state.json')
assert all(node['state'] == 'SUCCEEDED' for node in final_state['nodes'].values())
assert not read(R / RUN / 'claims.json')
save(R / 'actual-acceptance.json', {'recorded_at': now(), 'run_id': RUN, 'source_root': str(S),
    'actual_states': {name: node['state'] for name, node in final_state['nodes'].items()},
    'sequence': final_state['sequence'], 'claims': {}, 'integrate_receipt_sha256': exact_sha(receipt_path),
    'source_payloads': len(expected), 'full_tests': full['tests_run'],
    'application_journal_remains_unchanged_sha256': exact_sha(journal_path)})
print(json.dumps({'actual_source_integration': 'SUCCEEDED', 'tests_run': full['tests_run'],
    'changed_paths': len(changed), 'sequence': final_state['sequence'],
    'receipt_sha256': exact_sha(receipt_path)}), flush=True)
