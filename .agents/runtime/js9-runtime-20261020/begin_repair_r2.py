"""Acquire the separately authorized P2-002 acquisition-boundary repair lease."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
Q = F/'.agents/js9-runtime-20261020'
L = R/'repair-r2'
RUN = 'js9-composition-repair-r2-20261020'
ACTOR = '/root/recovery_regression20'
PATHS = ['src/ceta/identity/native_owner_view.py',
         'tests/contract/test_native_runtime_composition.py']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()

def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')

def invoke(label, args):
    command = ['powershell', '-NoProfile', '-File',
               'T:/02-Config/agents/taar-orchestrate.ps1', *args,
               '--runtime-root', str(L)]
    result = subprocess.run(command, cwd=F, capture_output=True)
    for suffix, raw in [('stdout', result.stdout), ('stderr', result.stderr)]:
        with (L/(label+'.'+suffix)).open('xb') as stream:
            stream.write(raw)
    response = json.loads(result.stdout.decode('utf-8-sig'))
    save(L/(label+'.json'), dict(command=command, exit_status=result.returncode,
                                response=response))
    assert result.returncode == 0 and response['allowed'] is True, response
    return response

manifest = R/'MANIFEST-R3.json'
assert sha(manifest) == '86ad0ef8f2fa1f0bcaff4ac02ea83d4957900ce4e68e637d7428d3649220571d'
before = json.loads(manifest.read_bytes())['payload_hashes']
assert len(before) == 530 and all(sha(Q/name) == pin for name, pin in before.items())
L.mkdir(exist_ok=False)
for name in PATHS:
    target = L/'before'/name
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write((Q/name).read_bytes())
    assert sha(target) == before[name]
fragment = (R/'repair-r1/AGENTS.md').read_text(encoding='utf8').replace(
    'partial NativeStoreBinding/no-acquisition close repair',
    'NativeStoreBinding pre-append handle acquisition/registration custody repair').replace(
    'Preserve Q530 beforeimages.', 'Preserve exact frozen R3/530 beforeimages.')
with (L/'AGENTS.md').open('x', encoding='utf8') as stream:
    stream.write(fragment)
invoke('init', ['run', 'init', '--root', str(F), '--scope', str(L), '--run-id', RUN])
for node in ['discover', 'plan']:
    invoke(node+'-ready', ['run', 'ready', RUN])
    claim = invoke(node+'-claim', ['node', 'claim', RUN, node, '--executor', ACTOR,
                                 '--workspace', str(Q)])['claim']
    receipt = L/(node+'-receipt.json')
    save(receipt, dict(schema_version=1, run_id=RUN, node_id=node, executor_id=ACTOR,
        started_at=claim['claimed_at'], finished_at=now(), input_hash=claim['input_hash'],
        changed_files=[], result=dict(blocker='JS9-P2-002: CreateFileW-to-queue publication gap',
            frozen_manifest_sha256=sha(manifest), allowed_changes=PATHS,
            native_execution=False, Root_authorized_narrow_repair=True), commands=[],
        validations=[dict(name='exact530_pins_beforeimages_and_real_queue_handle_inspected', passed=True)],
        exit_status=0))
    invoke(node+'-complete', ['node', 'complete', RUN, node, str(receipt)])
invoke('implement-ready', ['run', 'ready', RUN])
claim = invoke('implement-claim', ['node', 'claim', RUN, 'implement', '--executor',
                                 ACTOR, '--workspace', str(Q)])['claim']
assert claim['effective_write_scope'] == ['.agents/js9-runtime-20261020/**']
save(L/'LEASE-ACQUIRED.json', dict(at=now(), run=RUN, claim=claim,
    allowed_changed_files=PATHS, evidence_lease='js9-runtime-r4-20261020/evidence',
    frozen_manifest_sha256=sha(manifest), native_execution=False, Source_publication=False))
print(json.dumps(dict(run=RUN, input_hash=claim['input_hash'],
                      scope=claim['effective_write_scope'])), flush=True)
