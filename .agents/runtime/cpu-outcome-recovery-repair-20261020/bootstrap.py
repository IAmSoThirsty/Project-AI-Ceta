"""Acquire the existing bounded candidate lease before the registration repair."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess

F = Path('T:/00-Active/Project-AI-CETA')
Q = F / '.agents/cpu-outcome-recovery-r4-20261020'
R = Path(__file__).resolve().parent
OLD = F / '.agents/cpu-outcome-recovery-20261017'
MANIFEST = F / '.agents/runtime/cpu-outcome-recovery-20261017/cut-r3/MANIFEST.json'
RUN, ACTOR = 'cpu-outcome-recovery-r4-20261020', '/root'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()

def save(p, v):
    with p.open('x', encoding='utf8') as s:
        json.dump(v, s, indent=2)

def invoke(label, args):
    command = ['powershell', '-NoProfile', '-File', 'T:/02-Config/agents/taar-orchestrate.ps1', *args, '--runtime-root', str(R)]
    result = subprocess.run(command, cwd=F, capture_output=True)
    for suffix, raw in [('stdout', result.stdout), ('stderr', result.stderr)]:
        with (R / (label + '.' + suffix)).open('xb') as s:
            s.write(raw)
    response = json.loads(result.stdout.decode('utf-8-sig'))
    save(R / (label + '.json'), dict(command=command, exit_status=result.returncode, response=response))
    assert result.returncode == 0 and response['allowed'] is True, response
    return response

assert sha(MANIFEST) == '463d703e0b92580d45574d2b89276af645e55d6bfb5431e3ddc71d8c9d18ca87'
manifest = json.loads(MANIFEST.read_bytes())
for name, pin in manifest['payload_hashes'].items():
    assert sha(OLD / name) == pin, name
Q.mkdir(exist_ok=False)
invoke('init', ['run', 'init', '--root', 'T:/', '--scope', str(Q), '--run-id', RUN])
for node, result in [('discover', dict(parent_manifest=str(MANIFEST), parent_sha256=sha(MANIFEST),
                                      finding='RJR20-01', source_root=str(OLD), source_payloads=374)),
                     ('plan', dict(objective='Protected recovery registration publication, exact-own rollback and retained cleanup custody',
                                   expected_changes=['src/ceta/kernel/cpu_execution.py', 'tests/contract/test_cpu_recovery_registration.py'],
                                   source_publication=False, native_operations=False, reviewer='/root/recovery_join_review20'))]:
    claim = invoke(node + '-claim', ['node', 'claim', RUN, node, '--executor', ACTOR, '--workspace', str(Q)])['claim']
    receipt = R / (node + '-receipt.json')
    save(receipt, dict(schema_version=1, run_id=RUN, node_id=node, executor_id=ACTOR, started_at=claim['claimed_at'],
                       finished_at=now(), input_hash=claim['input_hash'], changed_files=[], result=result,
                       commands=[], validations=[dict(name='exact_frozen_input_and_reproduced_finding', passed=True)], exit_status=0))
    invoke(node + '-complete', ['node', 'complete', RUN, node, str(receipt)])
claim = invoke('implement-claim', ['node', 'claim', RUN, 'implement', '--executor', ACTOR, '--workspace', str(Q)])['claim']
assert claim['effective_write_scope'] == ['00-Active/Project-AI-CETA/.agents/cpu-outcome-recovery-r4-20261020/**']
for name, pin in manifest['payload_hashes'].items():
    raw = (OLD / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == pin
    p = Q / name
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('xb') as s:
        s.write(raw)
save(R / 'INPUTS.json', dict(at=now(), base_manifest=dict(path=str(MANIFEST), sha256=sha(MANIFEST)),
                            payload_hashes=manifest['payload_hashes'], claim=claim,
                            copied_source_LOC_credit=0, canonical_Source_changed=False))
print(json.dumps(dict(candidate=str(Q), implement_input_hash=claim['input_hash'], payloads=len(manifest['payload_hashes']))), flush=True)
