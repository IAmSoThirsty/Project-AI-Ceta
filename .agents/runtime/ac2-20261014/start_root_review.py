"""Root's distinct AC2 review claim and explicitly reused test-driver preparation."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, subprocess, sys

R = Path(__file__).resolve().parent
F = R.parents[2]
D = R / 'independent-root-review'
Q = F / '.agents/ac2-20261014'
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def save(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as out:
        json.dump(value, out, indent=2, allow_nan=False)
        out.write('\n')
assert sha(Q / 'TRANSFER-MANIFEST.json') == '41a2c6ab046279a581fe3ff99b126b84d7485d8369108f7abbf53634da254dda'
assert sha(R / 'implement.json') == '176258929d282c5d716e1a43c292d445f68ec1f192362cfa1e74435b24ecc360'
assert read(R / 'ac2-20261014/state.json')['sequence'] == 7
assert read(R / 'ac2-20261014/claims.json') == {}
D.mkdir(exist_ok=False)
stub = '''"""Reuse inspected AC2 native test infrastructure; Root evidence root only."""
from pathlib import Path
import importlib.util, sys
author_path = Path(__file__).resolve().parent.parent / 'ac2_support.py'
spec = importlib.util.spec_from_file_location('ac2_root_reused_support', author_path)
support = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = support
spec.loader.exec_module(support)
globals().update({key: value for key, value in vars(support).items() if not key.startswith('_')})
R = D = Path(__file__).resolve().parent
ACTOR = '/root'
'''
with (D / 'ac2_support.py').open('x', encoding='utf-8', newline='\n') as out:
    out.write(stub)
copies = {}
for name in ('run_original.py', 'prepare_closure.py', 'ac_support.py', 'source-inputs.json'):
    with (D / name).open('xb') as out:
        out.write((R / name).read_bytes())
    copies[name] = {'author_sha256': sha(R / name), 'reused_sha256': sha(D / name)}
    assert copies[name]['author_sha256'] == copies[name]['reused_sha256']
save(D / 'REUSED-DRIVER-BINDING.json', {'reviewer': '/root', 'recorded_at': datetime.now(timezone.utc).isoformat(),
    'exact_driver_reuse': copies, 'support_override': 'Only reviewer evidence/harness root and actor rebound; product imports remain frozen AC2.',
    'own_independent_scope': str(D), 'Source_application': False})
argv = ['powershell', '-NoProfile', '-File', 'T:/02-Config/agents/taar-orchestrate.ps1',
        'node', 'claim', 'ac2-20261014', 'review', '--executor', '/root', '--workspace', str(Q), '--runtime-root', str(R)]
done = subprocess.run(argv, cwd=F, capture_output=True)
for suffix, data in [('stdout', done.stdout), ('stderr', done.stderr)]:
    with (D / ('review-claim.' + suffix)).open('xb') as out:
        out.write(data)
response = json.loads(done.stdout.decode('utf-8-sig'))
save(D / 'actual-review-claim.json', {'argv': argv, 'exit_status': done.returncode, 'response': response})
assert done.returncode == 0 and response['allowed'] and response['claim']['executor_id'] == '/root'
print(json.dumps({'review_claimed': True, 'input_hash': response['claim']['input_hash'], 'driver_reuse': copies}))
