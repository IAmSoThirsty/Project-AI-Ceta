"""Read-only candidate inputs; materialize an exclusive reviewer-owned test join."""
from pathlib import Path
import hashlib
import json

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
Q = R / 'joined-candidate'
C = F / '.agents/runtime/cpu-capacity-connection-20261017'
P = F / '.agents/runtime/cpu-outcome-provenance-20261017'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

assert sha(C / 'cut-r1/MANIFEST.json') == '12c6dd58311e85686f68cbb7bc18a8d631ec418428fe2ddad88f017d575f4ce1'
assert sha(P / 'cut-r1/MANIFEST.json') == 'af4c6a8650cff46cf757f0b2d0b775a0046eabd95f705f80255360a01e44bac8'
assert sha(P / 'HANDOFF.json') == '82d45d3998da9fea9f5e0c7e30aab1593d305d6414112b4ea1cbd5907b0b378d'
assert sha(P / 'VIEW-PROPOSAL.json') == '1d6750e50d3f8e4072554d5caf38e84ca6cac92563c2233eb13e03263d2d79ec'
capacity = json.loads((C / 'cut-r1/MANIFEST.json').read_bytes())
provenance = json.loads((P / 'cut-r1/MANIFEST.json').read_bytes())
inputs = json.loads((P / 'INPUTS.json').read_bytes())
proposal = json.loads((P / 'VIEW-PROPOSAL.json').read_bytes())
selected = {name: dict(path=str(Path(capacity['source_root']) / name), sha256=digest,
                       origin='frozen-capacity-cut-r1') for name, digest in capacity['payload_hashes'].items()}
retained = {'src/ceta/identity/native_owner_view.py', 'src/ceta/kernel/cpu_execution.py',
            'src/ceta/kernel/effect_transactions.py'}
observer = {'src/ceta/effects/native_observer.py', 'contracts/NATIVE_EFFECT_OBSERVER_V1.md',
            'tests/contract/test_native_observer_origin.py'}
overlays = []
for name, row in inputs['payloads'].items():
    old = selected.get(name)
    if old is not None and old['sha256'] == row['sha256']:
        continue
    if name in retained:
        continue
    assert name in observer, ('UNPLANNED_OVERLAP', name)
    overlays.append(dict(path=name, before=old, after=row, reason='repaired-observer-origin-dependency'))
    selected[name] = row
for row in provenance['new_paths']:
    name = row['path']
    assert name not in selected
    selected[name] = dict(path=row['frozen_copy'], sha256=row['sha256'], origin='frozen-provenance-cut-r1')
name = 'src/ceta/identity/native_owner_view.py'
assert selected[name]['sha256'] == proposal['base']['sha256']
overlays.append(dict(path=name, before=selected[name], after=proposal['proposed'],
                     reason='exact-reviewed-proposed-forwarding-seam'))
selected[name] = proposal['proposed']
for name, row in selected.items():
    relative = Path(name)
    assert not relative.is_absolute() and '..' not in relative.parts
    path = Path(row['path'])
    assert path.resolve(strict=True).is_relative_to(F / '.agents')
    assert not path.is_symlink() and not path.is_junction() and sha(path) == row['sha256']
Q.mkdir(exist_ok=False)
for name, row in selected.items():
    destination = Q / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(Path(row['path']).read_bytes())
    assert sha(destination) == row['sha256']
with (R / 'JOIN-INPUTS.json').open('x', encoding='utf-8') as stream:
    json.dump(dict(reviewer='/root', source_root=str(F), candidate=str(Q), selected=selected,
        overlays=overlays, mode='REVIEW_ONLY_CONTROLLED_JOIN', Source_publication=False,
        copied_source_LOC_credit=0, source_accepted=False), stream, indent=2)
print(json.dumps(dict(payloads=len(selected), overlays=[r['path'] for r in overlays],
    inputs_sha256=sha(R / 'JOIN-INPUTS.json'), Source_publication=False)))
