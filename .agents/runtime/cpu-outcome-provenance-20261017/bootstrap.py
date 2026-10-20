"""Authenticate dependencies and claim the isolated producer/provenance work."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess

F = Path('T:/00-Active/Project-AI-CETA')
Q = F / '.agents/cpu-outcome-provenance-20261017'
R = Path(__file__).resolve().parent
B = F / '.agents/js8-amendment-report1-20261017'
RUN, ACTOR = 'cpu-outcome-provenance-20261017', '/root/publication_recovery_review'
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def utc(): return datetime.now(timezone.utc).isoformat()
def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')
def invoke(label, args):
    argv = ['powershell', '-NoProfile', '-File', 'T:/02-Config/agents/taar-orchestrate.ps1',
            *args, '--runtime-root', str(R)]
    result = subprocess.run(argv, cwd=F, capture_output=True, timeout=120)
    for suffix, raw in (('stdout', result.stdout), ('stderr', result.stderr)):
        with (R / (label + '.' + suffix)).open('xb') as stream: stream.write(raw)
    response = json.loads(result.stdout.decode('utf-8-sig'))
    save(R / (label + '.json'), dict(argv=argv, exit_status=result.returncode, response=response))
    assert result.returncode == 0 and response['allowed'] is True, response
    return response

manifest = B / 'TRANSFER-MANIFEST.json'
assert sha(manifest) == '2a3abde78bd4ab25af268ad1b16cef9eeaf9e2c30586c06fac4600876ba3c7c6'
paths = {name: dict(path=str(B / name), sha256=pin, origin='Q2')
         for name, pin in read(manifest)['expected_payload_hashes'].items()}
staged = read(F / '.agents/runtime/js8-20261015/amendment-report1/STAGED.json')
paths.update({name: dict(path=str(B / name), sha256=row['sha256'], origin='Q2-auxiliary')
              for name, row in staged['auxiliary_copies11'].items()})
reviews = {
    '.agents/runtime/owner-retainer-acceptance-review-20261017/REVIEW.json':
        '37104be42d3ba9d01004c5afe80e48a48d0bd277ba01a40e7c8fe15b74d5ddb0',
    '.agents/runtime/outcome-capacity-review-20261017/REVIEW.json':
        '680ea752a1fe63b3a60e795b03e09ddcc6a10965f713df42e08041d334b41f40'}
for name, pin in reviews.items(): assert sha(F / name) == pin
owner, capacity = (read(F / name) for name in reviews)
assert owner['decision'] == 'APPROVED'
assert capacity['decision'] == 'APPROVED_SCOPED_COMPONENT_SUCCESSOR_FOR_INTEGRATION'
replaced = {}
for row in owner['candidate']:
    name = Path(row['path']).relative_to(Path(owner['candidate_root'])).as_posix()
    if name in paths: replaced[name] = paths[name]
    paths[name] = dict(path=row['path'], sha256=row['sha256'], origin='approved-owner-retainer')
for row in capacity['files']:
    name = row['path']
    if name in paths: replaced[name] = paths[name]
    paths[name] = dict(path=str(Path(capacity['candidate']) / name), sha256=row['sha256'], origin='approved-capacity-r3')
observer_path = F / '.agents/runtime/observer-origin-repair-20261017/HANDOFF.json'
assert sha(observer_path) == '78f0d235e41a59028c870c263e390a9024d63639a7e39cf8b9c6e7ed0d0fcf15'
observer = read(observer_path)
for name in ('src/ceta/effects/native_observer.py', 'contracts/NATIVE_EFFECT_OBSERVER_V1.md',
             'tests/contract/test_native_observer_origin.py'):
    if name in paths: replaced[name] = paths[name]
    paths[name] = dict(path=str(Path(observer['candidate']) / name),
        sha256=observer['candidate_payload_hashes'][name], origin='observer-successor-pending-independent-and-native')
for name, row in paths.items(): assert sha(row['path']) == row['sha256'], name
Q.mkdir(exist_ok=False)
invoke('run-init', ['run', 'init', '--root', 'T:/', '--scope', str(Q), '--run-id', RUN])
for node, result in (
    ('discover', dict(requirements=['RE-T23', 'RE-T24'], inputs=reviews, base_manifest_sha256=sha(manifest),
        observer_dependency=dict(path=str(observer_path), sha256=sha(observer_path), acceptance='PENDING'),
        exact_seam='View-bound outcome provenance called by existing same-owner retained lease')),
    ('plan', dict(changes=['new same-owner producer/origin helper', 'new bounded dispatch/observation adapter',
        'new deterministic controlled tests and contract', 'proposed integration delta only for other owner'],
        protected=['NativeOwnerView', 'cpu_execution.py', 'effect_transactions.py', 'all prior candidates', 'Source'],
        native_execution='HELD_FOR_ROOT_RELEASE', Source_publication=False))):
    claim = invoke(node + '-claim', ['node', 'claim', RUN, node, '--executor', ACTOR, '--workspace', str(Q)])['claim']
    receipt = dict(schema_version=1, run_id=RUN, node_id=node, executor_id=ACTOR,
        started_at=claim['claimed_at'], finished_at=utc(), input_hash=claim['input_hash'], changed_files=[],
        result=result, commands=[], validations=[dict(name='requirements_interfaces_and_exact_inputs_inspected', passed=True)], exit_status=0)
    save(R / (node + '.json'), receipt)
    invoke(node + '-complete', ['node', 'complete', RUN, node, str(R / (node + '.json'))])
claim = invoke('implement-claim', ['node', 'claim', RUN, 'implement', '--executor', ACTOR, '--workspace', str(Q)])['claim']
assert claim['effective_write_scope'] == ['00-Active/Project-AI-CETA/.agents/cpu-outcome-provenance-20261017/**']
for name, row in paths.items():
    data = Path(row['path']).read_bytes()
    assert hashlib.sha256(data).hexdigest() == row['sha256']
    target = Q / name
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream: assert stream.write(data) == len(data)
save(R / 'INPUTS.json', dict(at=utc(), actor=ACTOR, project=str(F), candidate=str(Q),
    base_manifest=dict(path=str(manifest), sha256=sha(manifest)), reviews=reviews, payloads=paths,
    replaced_dependency_inputs=replaced, claim=claim, copied_source_LOC_credit=0,
    observer_dependency_acceptance='PENDING', Source_publication=False, native_execution=False))
print(json.dumps(dict(candidate=str(Q), payloads=len(paths), claim=claim['input_hash'], inputs_sha256=sha(R / 'INPUTS.json'))))
