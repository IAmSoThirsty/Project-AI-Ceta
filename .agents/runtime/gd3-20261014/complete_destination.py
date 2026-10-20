"""Accept the exact delivered cut only after full Source proof and distinct review."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

R = Path(__file__).resolve().parent
F, RUN = R.parents[2], 'gd3-20261014'
Q = F / '.agents' / RUN
ALLOWED = {'src/ceta/resource/diagnostics.py', 'contracts/PROCESS_DIAGNOSTICS_V1.md',
           'tests/contract/test_process_observation_timing.py', 'tests/contract/test_process_observation_validation.py'}
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()
def save(path, data):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2, allow_nan=False); stream.write('\n')

claim = read(R / RUN / 'claims.json')['integrate']
assert claim['executor_id'] == '/root' and claim['workspace'] == str(F)
manifest_path = Q / 'TRANSFER-MANIFEST.json'
assert sha(manifest_path) == 'bb070146f6516f928e2ead8e590436f853332e2393ce8fa2687655f3424f5239'
assert sha(R / 'apply_reviewed_observation.py') == '778f0429d89ca204f1e1f5eaf34477ddd2cd13b6d3893ee2c45198c683113968'
assert sha(R / 'run_destination_full.py') == '87b90049cbe22cd44860769abd203a022ab96807583cfe12e15a9daee785200c'
journal_path = R / 'active-application/APPLIED.json'
suite_path = R / 'active-application/destination-full-r1.json'
review_path = R / 'independent-destination/destination-review.json'
manifest, journal, suite, review = map(read, (manifest_path, journal_path, suite_path, review_path))
assert journal['manifest_sha256'] == sha(manifest_path) and journal['claim_input_hash'] == claim['input_hash']
assert {row['relative_path'] for row in journal['completed']} == ALLOWED and len(journal['completed']) == 4
assert len(journal['before_images']) == 2
assert sha(R / 'independent-review/review.json') == journal['review_sha256']
assert sha(R / 'independent-review/publication-helper-review.json') == journal['helper_review_sha256']
assert suite['root'] == str(F) and suite['tests_run'] == 1326
assert all(type(suite[key]) is int and suite[key] == 0 for key in ('failures', 'errors', 'skips', 'exit_status'))
assert suite['expected_ids'] == suite['executed_ids'] and len(set(suite['executed_ids'])) == 1326
assert suite['native_census']['exit_status'] == 0 and suite['native_census']['result']['clear'] is True
assert sha(R / 'active-application/destination-full-r1.txt') == suite['output_sha256']
assert not (R / 'active-application/destination-full-r1-writer-failure.json').exists()
assert review['decision'] == 'approved' and review['exit_status'] == 0 and review['source_root'] == str(F)
assert review['manifest_sha256'] == sha(manifest_path) and review['application_journal_sha256'] == sha(journal_path)
assert review['destination_suite_sha256'] == sha(suite_path) and review['tests_run'] == 1326
assert review['independently_executed_tests'] == 327
completion_review = read(R / 'independent-destination/completion-helper-review.json')
assert completion_review['decision'] == 'approved' and completion_review['exit_status'] == 0
assert completion_review['completion_script_sha256'] == sha(Path(__file__))
expected = {row['relative_path']: row['candidate_sha256'] for row in manifest['payloads']}
assert len(expected) == 281
assert expected == suite['before_hashes'] == suite['after_hashes'] == review['expected_payload_hashes']
for relative, digest in expected.items():
    assert sha(F / relative) == sha(Q / relative) == digest
assert len(suite['imports']) == 72
for item in suite['imports']:
    path = Path(item['actual_path'])
    assert path.is_relative_to(F / 'src') and sha(path) == item['sha256']
for original in journal['before_images']:
    relative = original['relative_path']
    backup = R / 'active-application/native-backups' / (relative + '.original')
    logical = R / 'active-application/before' / (relative + '.source')
    with backup.open('rb') as stream:
        facts = os.fstat(stream.fileno())
        assert hashlib.sha256(stream.read()).hexdigest() == sha(logical) == original['sha256']
    assert (facts.st_dev, facts.st_ino, facts.st_mode, facts.st_size, facts.st_mtime_ns) == (
        original['device'], original['inode'], original['mode'], original['bytes'], original['mtime_ns'])
sys.path.insert(0, r'T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce')
from taar.orchestration_runtime import _snapshot_workspace, _changed_files
from taar.orchestration_receipts import validate_receipt, load_receipt
print(json.dumps({'stage': 'actual_full_Source_snapshot', 'tests': 1326, 'payloads': 281}), flush=True)
changed = _changed_files(claim['baseline_snapshot'], _snapshot_workspace(F, Path('T:/')))
assert changed == sorted((F / path).relative_to(Path('T:/')).as_posix() for path in ALLOWED), changed
receipt = {'schema_version': 1, 'run_id': RUN, 'node_id': 'integrate', 'executor_id': '/root',
           'started_at': journal['started_at'], 'finished_at': now(), 'input_hash': claim['input_hash'], 'changed_files': changed,
           'result': {'status': 'FOUR_DELIVERED_SOURCE_PATHS_VERIFIED_WITH_DISTINCT_REVIEW', 'source_root': str(F),
                      'manifest_sha256': sha(manifest_path), 'application_journal_sha256': sha(journal_path),
                      'destination_suite_sha256': sha(suite_path), 'independent_destination_review_sha256': sha(review_path),
                      'tests_run': 1326, 'failures': 0, 'errors': 0, 'skips': 0, 'source_payloads': 281,
                      'current_source_modules': 72, 'independent_current_source_cases': 327,
                      'meaningful_integrated_source_added': 75, 'meaningful_integrated_source_removed': 23,
                      'meaningful_integrated_test_added': 653, 'novel_ROOT_repair_source_LOC': 3,
                      'novel_ROOT_nested_test_LOC': 131, 'GD3_newly_authored_LOC': 0,
                      'native_and_logical_originals': 2, 'reviewed_application_paths': sorted(ALLOWED),
                      'qualification_limits': manifest['pending'][-1:]},
           'commands': [{'command': 'Reviewed exact native publisher; two replacements and two no-overwrite creates', 'exit_status': 0},
                        {'command': 'Own E3 Python -B -X utf8 run_destination_full.py; actual1326 Source cases', 'exit_status': 0},
                        {'command': 'Wholly distinct reviewer reproduced actual327 Source cases and inspected281 hashes/imports/native originals', 'exit_status': 0},
                        {'command': 'Actual installed Source snapshot delta equals exactly four reviewed paths', 'exit_status': 0}],
           'validations': [{'name': name, 'passed': True} for name in ('exact281_Source_and_two_native_originals', '1326_full_Source_zero_skip_and_closed_native_census', 'distinct327_Source_and_whole_DELIVERY_review', 'exact_fourpath_installed_snapshot_delta')], 'exit_status': 0}
kwargs = {'run_id': RUN, 'node_id': 'integrate', 'executor_id': '/root', 'input_hash': claim['input_hash'],
          'claimed_at': claim['claimed_at'], 'node': read(R / RUN / 'graph.json')['graph']['nodes']['integrate']}
validate_receipt(receipt, **kwargs)
save(R / 'integrate.json', receipt)
validate_receipt(load_receipt(R / 'integrate.json'), **kwargs)
argv = ['powershell', '-NoProfile', '-File', r'T:\02-Config\agents\taar-orchestrate.ps1', 'node', 'complete', RUN,
        'integrate', str(R / 'integrate.json'), '--runtime-root', str(R)]
done = subprocess.run(argv, capture_output=True)
for suffix, data in (('stdout', done.stdout), ('stderr', done.stderr)):
    with (R / ('active-integrate-complete.' + suffix)).open('xb') as stream: stream.write(data)
response = json.loads(done.stdout)
save(R / 'active-integrate-complete.json', {'argv': argv, 'exit_status': done.returncode, 'response': response})
assert done.returncode == 0 and response['allowed'] is True
state, claims = read(R / RUN / 'state.json'), read(R / RUN / 'claims.json')
assert state['sequence'] == 13 and claims == {} and all(node['state'] == 'SUCCEEDED' for node in state['nodes'].values())
save(R / 'actual-acceptance.json', {'recorded_at': now(), 'source_root': str(F), 'sequence': 13, 'claims': claims,
     'actual_states': {name: node['state'] for name,node in state['nodes'].items()},
     'integrate_receipt_sha256': sha(R / 'integrate.json'), 'destination_tests': 1326, 'source_payloads': 281,
     'reviewed_source_paths': sorted(ALLOWED)})
print(json.dumps({'all6': 'SUCCEEDED', 'sequence': 13, 'claims': claims, 'integrate_sha256': sha(R / 'integrate.json')}), flush=True)
