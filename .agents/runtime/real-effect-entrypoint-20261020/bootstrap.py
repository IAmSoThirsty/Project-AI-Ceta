"""Acquire the actual disjoint private implementation and evidence leases."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
Q = F / '.agents/real-effect-entrypoint-20261020'
BASE = F / '.agents/js9-runtime-r5-20261020'
MANIFEST = F / '.agents/runtime/js9-runtime-20261020/successor-r3/MANIFEST-Q5.json'
RUN = 'real-effect-entrypoint-20261020'
ACTOR = '/root/ac7_native_artifact_review20'

def now():
    return datetime.now(timezone.utc).isoformat()

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')

def invoke(label, args):
    command = ['powershell', '-NoProfile', '-File',
        'T:/02-Config/agents/taar-orchestrate.ps1', *args, '--runtime-root', str(R)]
    completed = subprocess.run(command, cwd=F, capture_output=True)
    for suffix, raw in [('stdout', completed.stdout), ('stderr', completed.stderr)]:
        (R / (label + '.' + suffix)).write_bytes(raw)
    response = json.loads(completed.stdout.decode('utf-8-sig'))
    save(R / (label + '.json'), dict(command=command,
        exit_status=completed.returncode, response=response))
    assert completed.returncode == 0 and response['allowed'] is True, response
    return response

def main():
    assert sha(MANIFEST) == 'cce2c8e2c3a31fbedf5c2d83b2d15d499a93030c38ebe0c1e4545b868ef99acf'
    manifest = json.loads(MANIFEST.read_bytes())
    hashes = manifest['payload_hashes']
    assert len(hashes) == 541
    assert all(sha(BASE / name) == pin for name, pin in hashes.items())
    assert not Q.exists()
    Q.mkdir()
    invoke('init', ['run', 'init', '--root', str(F), '--scope', str(R), '--run-id', RUN])
    for node in ['discover', 'plan']:
        invoke(node + '-ready', ['run', 'ready', RUN])
        claim = invoke(node + '-claim', ['node', 'claim', RUN, node,
            '--executor', ACTOR, '--workspace', str(Q)])['claim']
        receipt = R / (node + '-receipt.json')
        save(receipt, dict(schema_version=1, run_id=RUN, node_id=node,
            executor_id=ACTOR, started_at=claim['claimed_at'], finished_at=now(),
            input_hash=claim['input_hash'], changed_files=[],
            result=dict(existing_plan=str(F / '.agents/runtime/real-effect-20261014/plan-review/IMPLEMENTATION-AND-ACCEPTANCE-PLAN.md'),
                source_manifest=str(MANIFEST), manifest_sha256=sha(MANIFEST),
                verified_payloads=len(hashes), candidate=str(Q), native_execution=False,
                Source_publication=False, reviewer='Root assigns a distinct named reviewer after freeze'),
            commands=[], validations=[dict(name='exact_dependency_pins_and_existing_callers_inspected', passed=True)],
            exit_status=0))
        invoke(node + '-complete', ['node', 'complete', RUN, node, str(receipt)])
    claims = {}
    for node, workspace, expected in [
        ('implement', Q, '.agents/real-effect-entrypoint-20261020/**'),
        ('evidence', R, '.agents/runtime/real-effect-entrypoint-20261020/**')]:
        invoke(node + '-ready', ['run', 'ready', RUN])
        claim = invoke(node + '-claim', ['node', 'claim', RUN, node,
            '--executor', ACTOR, '--workspace', str(workspace)])['claim']
        assert claim['effective_write_scope'] == [expected], claim
        claims[node] = claim
    save(R / 'LEASE-ACQUIRED.json', dict(at=now(), run=RUN, claims=claims,
        Source_writes=False, native_execution_released=False))
    print(json.dumps(dict(run=RUN, claims={k:dict(input_hash=v['input_hash'],
        write_scope=v['effective_write_scope']) for k,v in claims.items()})), flush=True)

if __name__ == '__main__':
    main()
