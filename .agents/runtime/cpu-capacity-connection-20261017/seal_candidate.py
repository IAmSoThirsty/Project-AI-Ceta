"""Create a reviewed-delta candidate cut without publishing Source."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import difflib
import hashlib
import json
import sys

R = Path(__file__).resolve().parent
F = Path('T:/00-Active/Project-AI-CETA')
Q = F / '.agents/cpu-capacity-connection-20261017'
D = R / sys.argv[1]
assert D.parent == R and D.name.startswith('cut-')
D.mkdir(exist_ok=False)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
inputs = json.loads((R/'INPUTS.json').read_bytes())
changed = []
diff = []
totals = dict(source_added=0, source_removed=0, test_added=0, test_removed=0, document_added=0, document_removed=0)
paths = sorted(set(inputs['payloads']) | {p.relative_to(Q).as_posix()
    for root in (Q/'src', Q/'tests', Q/'contracts') for p in root.rglob('*') if p.is_file()})
all_pins = {}
for name in paths:
    path = Q/name
    before = inputs['payloads'].get(name)
    current = sha(path)
    all_pins[name] = current
    if before is not None:
        assert sha(Path(before['path'])) == before['sha256'], before['path']
        if current == before['sha256']: continue
        old = Path(before['path']).read_text(encoding='utf8').splitlines(keepends=True)
    else: old = []
    new = path.read_text(encoding='utf8').splitlines(keepends=True)
    kind = 'source' if name.startswith('src/') else 'test' if name.startswith('tests/') else 'document'
    added = removed = 0
    for operation, a, b, c, d in difflib.SequenceMatcher(a=old, b=new, autojunk=False).get_opcodes():
        if operation != 'equal': removed += b-a; added += d-c
    totals[kind+'_added'] += added; totals[kind+'_removed'] += removed
    diff.extend(difflib.unified_diff(old, new, fromfile='BASE/'+name, tofile='CANDIDATE/'+name))
    copy = D/'payloads'/name
    copy.parent.mkdir(parents=True, exist_ok=True)
    with copy.open('xb') as stream: stream.write(path.read_bytes())
    if path.suffix == '.py': ast.parse(path.read_text(encoding='utf8'), filename=str(path))
    changed.append(dict(path=name, before=before, after_sha256=current,
        classification='CREATE' if before is None else 'EXTEND', kind=kind,
        added_lines=added, removed_lines=removed, frozen_copy=str(copy)))
with (D/'DELTA.diff').open('x', encoding='utf8', newline='') as stream: stream.writelines(diff)
record = dict(at=datetime.now(timezone.utc).isoformat(), actor='/root/full_report_repair',
    requirement='RE-T27', source_root=str(Q), base=inputs['base_manifest'],
    inputs_sha256=sha(R/'INPUTS.json'), claim_input_hash=inputs['claim']['input_hash'],
    changed=changed, payload_hashes=all_pins, physical_line_counts=totals,
    copied_dependency_LOC_credit=0, unchanged_payloads=len(all_pins)-len(changed),
    diff_sha256=sha(D/'DELTA.diff'), syntax='PASS: exact changed Python files ast.parse',
    source_publication=False, independent_review='PENDING', native_capacity_and_effect_tests='HELD')
with (D/'MANIFEST.json').open('x', encoding='utf8') as stream:
    json.dump(record, stream, indent=2); stream.write('\n')
print(json.dumps(dict(path=str(D/'MANIFEST.json'), sha256=sha(D/'MANIFEST.json'), changed=len(changed), counts=totals)))
