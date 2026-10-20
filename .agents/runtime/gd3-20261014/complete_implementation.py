import hashlib
import json
from pathlib import Path
import subprocess
from datetime import datetime, timezone

R = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
assert sha(R / 'implement.json') == '6a85432d806638e98bfd9d4ad8cef3b0005af64869cd8c9301cc0acb40a3d614'
argv = ['powershell', '-NoProfile', '-File', r'T:\02-Config\agents\taar-orchestrate.ps1',
        'node', 'complete', 'gd3-20261014', 'implement', str(R / 'implement.json'), '--runtime-root', str(R)]
done = subprocess.run(argv, capture_output=True)
for suffix, data in (('stdout', done.stdout), ('stderr', done.stderr)):
    with (R / ('implement-complete.' + suffix)).open('xb') as stream: stream.write(data)
response = json.loads(done.stdout)
with (R / 'implement-complete-response.json').open('x') as stream:
    json.dump({'argv': argv, 'exit_status': done.returncode, 'response': response}, stream, indent=2); stream.write('\n')
assert done.returncode == 0 and response['allowed']
state, claims = read(R / 'gd3-20261014/state.json'), read(R / 'gd3-20261014/claims.json')
assert state['nodes']['implement']['state'] == 'SUCCEEDED' and state['nodes']['review']['state'] == 'READY'
assert state['sequence'] == 7 and claims == {}
with (R / 'actual-implementation-readback.json').open('x') as stream:
    json.dump({'observed_at': datetime.now(timezone.utc).isoformat(), 'state': state, 'claims': claims,
               'implement_sha256': sha(R / 'implement.json'), 'receipt': read(R / 'gd3-20261014/receipts/implement.json')}, stream, indent=2); stream.write('\n')
print(json.dumps({'implement': 'SUCCEEDED', 'review': 'READY', 'sequence': state['sequence'], 'claims': claims,
                  'readback_sha256': sha(R / 'actual-implementation-readback.json')}))
