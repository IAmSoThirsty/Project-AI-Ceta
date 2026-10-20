"""Create the explicitly assigned candidate and obtain its actual TAAR claim."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess

F = Path('T:/00-Active/Project-AI-CETA')
Q = F / '.agents/cpu-capacity-connection-20261017'
R = Path(__file__).resolve().parent
BASE = F / '.agents/js8-amendment-report1-20261017'
RUN = 'cpu-capacity-connection-20261017'
ACTOR = '/root/full_report_repair'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()

def write(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2); stream.write('\n')

def invoke(label, args):
    command = ['powershell', '-NoProfile', '-File', 'T:/02-Config/agents/taar-orchestrate.ps1',
               *args, '--runtime-root', str(R)]
    result = subprocess.run(command, cwd=F, capture_output=True)
    for suffix, raw in [('stdout', result.stdout), ('stderr', result.stderr)]:
        with (R / (label + '.' + suffix)).open('xb') as stream: stream.write(raw)
    value = json.loads(result.stdout.decode('utf-8-sig'))
    write(R / (label + '.json'), dict(command=command, exit_status=result.returncode, response=value))
    assert result.returncode == 0 and value['allowed'] is True, value
    return value

manifest_path = BASE / 'TRANSFER-MANIFEST.json'
assert sha(manifest_path) == '2a3abde78bd4ab25af268ad1b16cef9eeaf9e2c30586c06fac4600876ba3c7c6'
m = json.loads(manifest_path.read_bytes())
paths = {name: dict(path=str(BASE / name), sha256=pin, origin='Q2')
         for name, pin in m['expected_payload_hashes'].items()}
staged = json.loads((F / '.agents/runtime/js8-20261015/amendment-report1/STAGED.json').read_bytes())
paths.update({name: dict(path=str(BASE / name), sha256=row['sha256'], origin='Q2-auxiliary')
              for name, row in staged['auxiliary_copies11'].items()})
reviews = {
    '.agents/runtime/owner-retainer-acceptance-review-20261017/REVIEW.json':
        '37104be42d3ba9d01004c5afe80e48a48d0bd277ba01a40e7c8fe15b74d5ddb0',
    '.agents/runtime/outcome-capacity-review-20261017/REVIEW.json':
        '680ea752a1fe63b3a60e795b03e09ddcc6a10965f713df42e08041d334b41f40',
}
for name, pin in reviews.items(): assert sha(F / name) == pin
owner = json.loads((F / next(iter(reviews))).read_bytes())
capacity = json.loads((F / list(reviews)[1]).read_bytes())
assert owner['decision'] == 'APPROVED'
assert capacity['decision'] == 'APPROVED_SCOPED_COMPONENT_SUCCESSOR_FOR_INTEGRATION'
before_dependency = {}
for row in owner['candidate']:
    name = Path(row['path']).relative_to(Path(owner['candidate_root'])).as_posix()
    if name in paths: before_dependency[name] = paths[name]
    paths[name] = dict(path=row['path'], sha256=row['sha256'], origin='approved-owner-retainer')
for row in capacity['files']:
    name = row['path']
    if name in paths: before_dependency[name] = paths[name]
    paths[name] = dict(path=str(Path(capacity['candidate']) / name), sha256=row['sha256'], origin='approved-capacity-r3')
for name, row in paths.items(): assert sha(row['path']) == row['sha256'], name
Q.mkdir(exist_ok=False)
invoke('run-init', ['run', 'init', '--root', 'T:/', '--scope', str(Q), '--run-id', RUN])
for node, result in (
    ('discover', dict(requirement='RE-T27', exact_sources=reviews, base_manifest_sha256=sha(manifest_path),
                     inspected_callers=['NativeOwnerView', 'NativeCpuOwnerSession', 'KernelCpuExecution', 'KernelEffectTransactions', 'OutcomeCapacityLease'])),
    ('plan', dict(authority='Root exclusive RE-T27 task', candidate=str(Q),
                 changes=['native owner same-journal capacity binding', 'pre-Set dispatch mark', 'exact final outcome payload staging'],
                 source_publication=False, native_effect_tests='HELD_FOR_ROOT_RELEASE')),
):
    claim = invoke(node + '-claim', ['node', 'claim', RUN, node, '--executor', ACTOR, '--workspace', str(Q)])['claim']
    receipt = dict(schema_version=1, run_id=RUN, node_id=node, executor_id=ACTOR,
        started_at=claim['claimed_at'], finished_at=now(), input_hash=claim['input_hash'],
        changed_files=[], result=result, commands=[], validations=[dict(name='exact_task_and_inputs_inspected', passed=True)], exit_status=0)
    receipt_path = R / (node + '-receipt.json'); write(receipt_path, receipt)
    invoke(node + '-complete', ['node', 'complete', RUN, node, str(receipt_path)])
claim = invoke('implement-claim', ['node', 'claim', RUN, 'implement', '--executor', ACTOR, '--workspace', str(Q)])['claim']
assert claim['effective_write_scope'] == ['00-Active/Project-AI-CETA/.agents/cpu-capacity-connection-20261017/**']
for name, row in paths.items():
    raw = Path(row['path']).read_bytes(); assert hashlib.sha256(raw).hexdigest() == row['sha256']
    target = Q / name; target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream: stream.write(raw)
write(R / 'INPUTS.json', dict(at=now(), actor=ACTOR, project=str(F), candidate=str(Q),
    base_manifest=dict(path=str(manifest_path), sha256=sha(manifest_path)), reviews=reviews,
    payloads=paths, replaced_dependency_inputs=before_dependency, claim=claim,
    copied_source_LOC_credit=0, source_publication=False, native_execution=False))
print(json.dumps(dict(candidate=str(Q), payloads=len(paths), claim=claim['input_hash'], inputs_sha256=sha(R/'INPUTS.json'))))
