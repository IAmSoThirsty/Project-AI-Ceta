"""Gate the exact reviewed cut and claim the real Source workspace."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess

R = Path(__file__).resolve().parent
F, RUN = R.parents[2], 'gd2-20261014'
Q = F / '.agents' / RUN
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(Q / 'TRANSFER-MANIFEST.json') == 'cd51569eedb171f822defce05a21b53ad79ca2005e51a9c0ac253564b3088d8a'
assert sha(R / 'implement.json') == '7f76cf5e45dd8726bbf66bbfb398651205a277bf7aa52141a3cbd688027ce98a'
assert sha(R / 'apply_reviewed_observation.py') == 'f6a9dcbbada985fc5495c7af3b46c46039bcbd8c5c5fa668e39e1c4732230599'
state = read(R / RUN / 'state.json')
assert state['nodes']['review']['state'] == 'SUCCEEDED' and not read(R / RUN / 'claims.json')
review = read(R / 'independent-review/review.json')
stored = read(R / RUN / 'receipts/review.json')
assert review['decision'] == 'approved' and review['exit_status'] == 0 and review['executor_id'] != '/root'
assert all(stored.get(key) == value for key, value in review.items()), 'Strict review differs from actual persisted receipt'
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
