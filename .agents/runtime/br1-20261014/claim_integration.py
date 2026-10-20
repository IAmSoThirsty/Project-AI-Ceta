"""Claim the real active-root integration after the accepted display review."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess
R = Path(__file__).resolve().parent
F = R.parents[2]
Q = F / '.agents/br1-20261014'
RUN = 'br1-20261014'
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(R / 'independent-review/review.json') == 'fff491bbab60d4e92856cbb737b34fb1095490431fd8010247f7d6ddd90a9934'
assert sha(Q / 'TRANSFER-MANIFEST.json') == '12fe2b2a79164fc0efb180c4b8c7d043006af80b61242a707aa92b95dff9d040'
assert sha(R / 'apply_reviewed_titles.py') == 'a5787a1dba9f8fd816f0d9394c5bda10f07a731552505378423c5bd81d6275e6'
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
