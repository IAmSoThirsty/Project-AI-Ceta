"""Gate the exact reviewed cut and claim the real Source workspace."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess

R = Path(__file__).resolve().parent
F, RUN = R.parents[2], 'gd3-20261014'
Q = F / '.agents' / RUN
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(Q / 'TRANSFER-MANIFEST.json') == 'bb070146f6516f928e2ead8e590436f853332e2393ce8fa2687655f3424f5239'
assert sha(R / 'implement.json') == '6a85432d806638e98bfd9d4ad8cef3b0005af64869cd8c9301cc0acb40a3d614'
assert sha(R / 'apply_reviewed_observation.py') == '778f0429d89ca204f1e1f5eaf34477ddd2cd13b6d3893ee2c45198c683113968'
state = read(R / RUN / 'state.json')
assert state['nodes']['review']['state'] == 'SUCCEEDED' and not read(R / RUN / 'claims.json')
review = read(R / 'independent-review/review.json')
stored = read(R / RUN / 'receipts/review.json')
assert review['decision'] == 'approved' and review['exit_status'] == 0 and review['executor_id'] != '/root'
strict_keys = {'schema_version', 'run_id', 'node_id', 'executor_id', 'started_at', 'finished_at', 'input_hash', 'changed_files', 'result', 'commands', 'validations', 'exit_status', 'decision'}
assert set(review) == strict_keys and set(stored) == strict_keys | {'git_baseline', 'observed_git', 'receipt_hash'}
assert json.dumps(review, sort_keys=True, separators=(',', ':'), allow_nan=False) == json.dumps(
    {key: stored[key] for key in strict_keys}, sort_keys=True, separators=(',', ':'),
    allow_nan=False), 'Strict review differs from actual persisted receipt values or JSON types'
helper = read(R / 'independent-review/publication-helper-review.json')
assert helper['decision'] == 'approved' and helper['exit_status'] == 0
assert helper['publication_script_sha256'] == sha(R / 'apply_reviewed_observation.py')
manifest = read(Q / 'TRANSFER-MANIFEST.json')
for row in manifest['payloads']:
    relative = row['relative_path']
    assert sha(Q / relative) == row['candidate_sha256']
    assert (sha(F / relative) if (F / relative).is_file() else None) == row['active_before_sha256']
for label, args in (
    ('validate-claim', ['node', 'claim', RUN, 'validate', '--executor', '/root', '--workspace', str(Q)]),
    ('validate-gate', ['node', 'run-gate', RUN, 'validate']),
    ('active-integrate-claim', ['node', 'claim', RUN, 'integrate', '--executor', '/root', '--workspace', str(F)])):
    argv = ['powershell', '-NoProfile', '-File', r'T:\02-Config\agents\taar-orchestrate.ps1', *args, '--runtime-root', str(R)]
    started = datetime.now(timezone.utc).isoformat()
    done = subprocess.run(argv, capture_output=True)
    for suffix, data in (('stdout', done.stdout), ('stderr', done.stderr)):
        with (R / (label + '.' + suffix)).open('xb') as stream: stream.write(data)
    response = json.loads(done.stdout)
    with (R / (label + '.json')).open('x', encoding='utf-8') as stream:
        json.dump({'started_at': started, 'finished_at': datetime.now(timezone.utc).isoformat(),
                   'argv': argv, 'exit_status': done.returncode, 'response': response}, stream, indent=2); stream.write('\n')
    assert done.returncode == 0 and response.get('allowed') is True, response
    print(json.dumps({'step': label, 'allowed': True}), flush=True)
claim = read(R / RUN / 'claims.json')['integrate']
assert claim['executor_id'] == '/root' and claim['workspace'] == str(F)
print(json.dumps({'active_claim': claim['input_hash'], 'claimed_at': claim['claimed_at']}), flush=True)
