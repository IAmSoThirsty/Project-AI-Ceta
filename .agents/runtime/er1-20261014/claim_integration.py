"""Claim exact environment application only after Source's prior claim is released."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess

R = Path(__file__).resolve().parent
F = R.parents[2]
Q = F / '.agents/er1-20261014'
E3 = F / '.agents/source-assembly-20261014T021300Z/.agents/e3'
RUN = 'er1-20261014'
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()
prior = F / '.agents/runtime/hd2-20261014/hd2-20261014'
assert all(node['state'] == 'SUCCEEDED' for node in read(prior / 'state.json')['nodes'].values())
assert not read(prior / 'claims.json')
assert sha(Q / 'TRANSFER-MANIFEST.json') == '7325582b9fa18972dc2e6337e66e55fa3c7ae1ee5db600824aedeca58bb73f83'
assert sha(R / 'independent-review/review.json') == '8322051dbf2b0efac25a46ea2af47ce1fcab2cf62f42d41776a28e677a94e0b3'
assert sha(R / 'apply_reviewed_environment.py') == 'f25e7967d5cfba5e90819490ec0f2f19320b2d5ebc8df95e2a8d9020064b8cec'
helper_path = R / 'independent-review/publication-helper-review.json'
assert sha(helper_path) == '5b64b0fb41053faf8a11a56b0d08f0d3419243bae4092fbe4b3d3d703c3f9ff8'
helper = read(helper_path)
assert helper['decision'] == 'approved' and helper['exit_status'] == 0
assert helper['publication_script_sha256'] == sha(R / 'apply_reviewed_environment.py')
assert read(R / RUN / 'state.json')['nodes']['review']['state'] == 'SUCCEEDED'
assert not read(R / RUN / 'claims.json')
for label, args in (
    ('active-validate-claim', ['node', 'claim', RUN, 'validate', '--executor', '/root', '--workspace', str(Q)]),
    ('active-validate-gate', ['node', 'run-gate', RUN, 'validate']),
    ('active-environment-integrate-claim', ['node', 'claim', RUN, 'integrate', '--executor', '/root', '--workspace', str(E3)])):
    argv = ['powershell', '-NoProfile', '-File', r'T:\02-Config\agents\taar-orchestrate.ps1', *args, '--runtime-root', str(R)]
    started = now()
    done = subprocess.run(argv, capture_output=True)
    for suffix, data in (('stdout', done.stdout), ('stderr', done.stderr)):
        with (R / (label + '.' + suffix)).open('xb') as stream: stream.write(data)
    response = json.loads(done.stdout)
    with (R / (label + '.json')).open('x', encoding='utf-8') as stream:
        json.dump({'started_at': started, 'finished_at': now(), 'argv': argv,
            'exit_status': done.returncode, 'response': response}, stream, indent=2)
        stream.write('\n')
    assert done.returncode == 0 and response.get('allowed') is True, response
    print(json.dumps({'step': label, 'allowed': True}), flush=True)
claim = read(R / RUN / 'claims.json')['integrate']
assert claim['executor_id'] == '/root' and claim['workspace'] == str(E3)
print(json.dumps({'environment_claim': claim['input_hash'], 'claimed_at': claim['claimed_at']}), flush=True)
