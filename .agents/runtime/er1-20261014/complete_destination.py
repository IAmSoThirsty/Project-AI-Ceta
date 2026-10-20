"""Record actual thirty-file environment acceptance after distinct destination review."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

R = Path(__file__).resolve().parent
F = R.parents[2]
Q = F / '.agents/er1-20261014'
E3 = F / '.agents/source-assembly-20261014T021300Z/.agents/e3'
RUN = 'er1-20261014'
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()
assert Path(sys.executable) == E3 / 'Scripts/python.exe' and sys.flags.optimize == 0
sys.path.insert(0, r'T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce')
from taar.orchestration_receipts import validate_receipt
from taar.orchestration_runtime import _snapshot_workspace, _changed_files

claim = read(R / RUN / 'claims.json')['integrate']
assert claim['executor_id'] == '/root' and claim['workspace'] == str(E3)
manifest_path = Q / 'TRANSFER-MANIFEST.json'
journal_path = R / 'active-application/APPLIED.json'
verification_path = R / 'active-application/destination-verification.json'
review_path = R / 'independent-destination/destination-review.json'
assert sha(manifest_path) == '7325582b9fa18972dc2e6337e66e55fa3c7ae1ee5db600824aedeca58bb73f83'
assert sha(journal_path) == '4b0c716f31661701d10541922f96cadc301589a57935ec0bdf209ca353886c9b'
assert sha(verification_path) == '91aa912566bcecd7abd52496375db071d02c6d8042b0b60dd89fbeda3af525aa'
assert sha(R / 'apply_reviewed_environment.py') == 'f25e7967d5cfba5e90819490ec0f2f19320b2d5ebc8df95e2a8d9020064b8cec'
assert sha(R / 'verify_destination.py') == '01a6ea2408cffc240596a9c27f9416c8a9b59e23ea122db773ee3a8f8be5c09e'
assert sha(R / 'independent-review/review.json') == '8322051dbf2b0efac25a46ea2af47ce1fcab2cf62f42d41776a28e677a94e0b3'
assert sha(R / 'independent-review/publication-helper-review.json') == '5b64b0fb41053faf8a11a56b0d08f0d3419243bae4092fbe4b3d3d703c3f9ff8'
manifest, journal, verification, review = map(read, (manifest_path, journal_path, verification_path, review_path))
assert journal['claim_input_hash'] == claim['input_hash']
assert len(journal['completed']) == len(journal['before_images']) == len(manifest['payloads']) == 30
assert verification['environment_root'] == str(E3) and verification['exit_status'] == 0
assert verification['safe_native_cli_invocations'] == len(verification['commands']) == 5
assert len(verification['imports']) == 27
assert all(command['oracle_passed'] and command['owner_closed'] and command['observed_empty_job']
    for command in verification['commands'])
assert review['decision'] == 'approved' and review['exit_status'] == 0
assert review['environment_root'] == str(E3) and review['manifest_sha256'] == sha(manifest_path)
assert review['application_journal_sha256'] == sha(journal_path)
assert review['destination_verification_sha256'] == sha(verification_path)
assert review['independent_safe_cli_invocations'] >= 5
completion_review = read(R / 'independent-destination/completion-helper-review.json')
assert completion_review['decision'] == 'approved' and completion_review['exit_status'] == 0
assert completion_review['completion_script_sha256'] == sha(Path(__file__))
expected = verification['expected_environment_files']
assert len(expected) == 3601 and expected == review['expected_environment_files']
sys.path.insert(0, str(R))
assert sha(R / 'er1_support.py') == '38721b1fa0c112f568a4e957b5ae3a1ecd747645c83ec5882228947805a198d5'
import er1_support as support
fresh = support.snapshot_tree()
assert {row['relative_path']: row for row in fresh['members'] if row['kind'] == 'ordinary_file'} == expected
originals = {row['relative_path']: row for row in journal['before_images']}
allowed = set()
for row in manifest['payloads']:
    target = Path(row['source_path'])
    assert target.is_relative_to(E3)
    relative = target.relative_to(E3).as_posix()
    allowed.add(relative)
    assert sha(target) == sha(Q / row['candidate_relative_path']) == row['candidate_sha256']
    original = originals[relative]
    native = R / 'active-application/native-backups' / (relative + '.original')
    logical = R / 'active-application/before' / (relative + '.source')
    assert sha(native) == sha(logical) == original['sha256'] == row['source_sha256']
    with support.fs.open_source(support.fs.safe_components(native), exclusive=True) as stream:
        facts = os.fstat(stream.fileno())
    assert (facts.st_dev, facts.st_ino, facts.st_mode, facts.st_size, facts.st_mtime_ns) == (
        original['device'], original['inode'], original['mode'], original['bytes'], original['mtime_ns'])
assert len(allowed) == 30 and allowed == {row['relative_path'] for row in journal['completed']}
changed = _changed_files(claim['baseline_snapshot'], _snapshot_workspace(E3, Path('T:/')))
assert changed == sorted((E3 / relative).relative_to(Path('T:/')).as_posix() for relative in allowed), changed
receipt = {'schema_version': 1, 'run_id': RUN, 'node_id': 'integrate', 'executor_id': '/root',
    'started_at': journal['started_at'], 'finished_at': now(), 'input_hash': claim['input_hash'],
    'changed_files': changed, 'result': {
        'status': 'EXACT_THIRTY_ENVIRONMENT_FILES_APPLIED_AND_INDEPENDENTLY_VERIFIED',
        'source_root': str(F), 'environment_root': str(E3), 'manifest_sha256': sha(manifest_path),
        'application_journal_sha256': sha(journal_path), 'destination_verification_sha256': sha(verification_path),
        'distinct_destination_review_sha256': sha(review_path), 'native_originals': 30,
        'ordinary_environment_files': 3601, 'unrelated_ordinary_files_preserved': 3571,
        'safe_cli_invocations': 5, 'independent_safe_cli_invocations': review['independent_safe_cli_invocations'],
        'callable_imports': 27, 'new_product_source_LOC': 0,
        'remaining_limits': ['23 Qt GUI/server/deployment functions remain unexecuted',
            'Aggregate PySide6 distribution metadata remains unavailable',
            'Directory allocation-size query variation remains unresolved',
            'Thirty individual replacements are qualified; interruption recovery requires exact-path reconciliation']},
    'commands': [{'command': 'Actual reviewed thirty-file native E3 publisher with complete original preservation', 'exit_status': 0},
        {'command': 'Actual own E3 five safe CLI calls and3601 file conservation verification', 'exit_status': 0},
        {'command': 'Distinct current E3 destination review and independently owned safe CLI calls', 'exit_status': 0},
        {'command': 'Fresh3601-file rehash and actual installed E3 snapshot prove exact30 changed paths', 'exit_status': 0}],
    'validations': [{'name': 'exact30_candidate_and_native_original_bindings', 'passed': True},
        {'name': 'actual_native_cli_exit_empty_job_and_closed_owner', 'passed': True},
        {'name': 'all3571_unrelated_files_and27_callable_entrypoints_preserved', 'passed': True}], 'exit_status': 0}
validate_receipt(receipt, run_id=RUN, node_id='integrate', executor_id='/root',
    input_hash=claim['input_hash'], claimed_at=claim['claimed_at'],
    node=read(R / RUN / 'graph.json')['graph']['nodes']['integrate'])
receipt_path = R / 'integrate.json'
with receipt_path.open('x', encoding='utf-8') as stream:
    json.dump(receipt, stream, indent=2); stream.write('\n')
done = subprocess.run(['powershell', '-NoProfile', '-File', r'T:\02-Config\agents\taar-orchestrate.ps1',
    'node', 'complete', RUN, 'integrate', str(receipt_path), '--runtime-root', str(R)], capture_output=True)
for suffix, data in (('stdout', done.stdout), ('stderr', done.stderr)):
    with (R / ('active-integrate-complete.' + suffix)).open('xb') as stream: stream.write(data)
response = json.loads(done.stdout)
assert done.returncode == 0 and response.get('allowed') is True, response
state = read(R / RUN / 'state.json')
assert all(node['state'] == 'SUCCEEDED' for node in state['nodes'].values())
assert not read(R / RUN / 'claims.json')
with (R / 'actual-acceptance.json').open('x', encoding='utf-8') as stream:
    json.dump({'recorded_at': now(), 'environment_root': str(E3), 'sequence': state['sequence'], 'claims': {},
        'actual_states': {name: node['state'] for name, node in state['nodes'].items()},
        'integrate_receipt_sha256': sha(receipt_path), 'native_originals': 30,
        'ordinary_environment_files': 3601, 'unrelated_ordinary_files_preserved': 3571}, stream, indent=2)
    stream.write('\n')
print(json.dumps({'actual_integration': 'SUCCEEDED', 'sequence': state['sequence'],
    'receipt_sha256': sha(receipt_path), 'environment_paths': 30}), flush=True)
