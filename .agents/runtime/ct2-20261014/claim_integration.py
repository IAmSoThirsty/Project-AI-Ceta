"""Claim the real active-root integration after the accepted display review."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess
R = Path(__file__).resolve().parent
F = R.parents[2]
Q = F / '.agents/ct1-20261014'
RUN = 'ct2-20261014'
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(R / 'independent-review/review.json') == '2c7a930f9361b83c47483eef9436546a4a92f892084432394574d6be550192b5'
assert sha(Q / 'TRANSFER-MANIFEST.json') == '6ebe98c39182233943bdce6ff26ea2ab878397abc04ed35d74a09b972e466ea9'
assert sha(R / 'apply_reviewed_status.py') == '5d60bdd28c16edf12558cdd9c4cf19fd882736b930b82d9a1aa991ea0ea26225'
assert read(R / RUN / 'state.json')['nodes']['review']['state'] == 'SUCCEEDED'
assert not read(R / RUN / 'claims.json')
for label, args in (
    ('validate-claim', ['node', 'claim', RUN, 'validate', '--executor', '/root', '--workspace', str(Q)]),
    ('validate-gate', ['node', 'run-gate', RUN, 'validate']),
    ('active-integrate-claim', ['node', 'claim', RUN, 'integrate', '--executor', '/root', '--workspace', str(F)])):
    argv = ['powershell', '-NoProfile', '-File', r'T:\02-Config\agents\taar-orchestrate.ps1', *args, '--runtime-root', str(R)]
    started = datetime.now(timezone.utc).isoformat()
    done = subprocess.run(argv, capture_output=True)
    for suffix, data in (('stdout', done.stdout), ('stderr', done.stderr)):
        with (R / (label + '.' + suffix)).open('xb') as output:
            output.write(data)
    response = json.loads(done.stdout)
    with (R / (label + '.json')).open('x', encoding='utf-8') as output:
        json.dump({'started_at': started, 'finished_at': datetime.now(timezone.utc).isoformat(),
            'argv': argv, 'exit_status': done.returncode, 'response': response}, output, indent=2)
        output.write('\n')
    assert done.returncode == 0 and response.get('allowed') is True, response
    print(json.dumps({'step': label, 'allowed': True}), flush=True)
claim = read(R / RUN / 'claims.json')['integrate']
assert claim['executor_id'] == '/root' and claim['workspace'] == str(F)
print(json.dumps({'active_claim': claim['input_hash'], 'claimed_at': claim['claimed_at']}), flush=True)
