from pathlib import Path
from datetime import datetime, timezone
import ast
import difflib
import hashlib
import json
import sys

F = Path('T:/00-Active/Project-AI-CETA')
Q = F/'.agents/cpu-outcome-recovery-20261017'
BASE = F/'.agents/cpu-capacity-connection-20261017'
R = Path(__file__).resolve().parent
D = R/sys.argv[1]
assert D.parent == R and D.name.startswith('cut-')
D.mkdir(exist_ok=False)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
inputs = json.loads((R/'INPUTS.json').read_bytes())
for name, pin in inputs['payload_hashes'].items():
    assert sha(BASE/name) == pin, name
payloads = {p.relative_to(Q).as_posix():sha(p) for p in Q.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
changes, differences = {}, []
for name, pin in payloads.items():
    if name.endswith('.py'): ast.parse((Q/name).read_bytes(), filename=name)
    if inputs['payload_hashes'].get(name) != pin:
        target = D/'payloads'/name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((Q/name).read_bytes())
        old = [] if not (BASE/name).exists() else (BASE/name).read_text(encoding='utf-8-sig').splitlines(True)
        new = (Q/name).read_text(encoding='utf-8-sig').splitlines(True)
        delta = list(difflib.unified_diff(old, new, fromfile='base/'+name, tofile='candidate/'+name))
        differences.extend(delta)
        changes[name] = dict(before=inputs['payload_hashes'].get(name), after=pin,
            added=sum(s.startswith('+') and not s.startswith('+++') for s in delta),
            removed=sum(s.startswith('-') and not s.startswith('---') for s in delta))
(D/'CHANGES.diff').write_text(''.join(differences), encoding='utf8')
record = dict(at=datetime.now(timezone.utc).isoformat(), actor='/root/full_report_repair',
    base_manifest=inputs['manifest'], candidate=str(Q), payload_hashes=payloads, changes=changes,
    syntax='PASS', source_publication=False, new_native_execution=False)
(D/'MANIFEST.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf8')
print(json.dumps(dict(manifest=str(D/'MANIFEST.json'), sha256=sha(D/'MANIFEST.json'), changes=list(changes))))
