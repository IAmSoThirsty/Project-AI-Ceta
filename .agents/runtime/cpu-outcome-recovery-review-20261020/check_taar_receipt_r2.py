from pathlib import Path
import hashlib
import json

F = Path('T:/00-Active/Project-AI-CETA')
A = F/'.agents/runtime/cpu-outcome-recovery-repair-20261020'
P = A/'cpu-outcome-recovery-r4-20261020'
v = json.loads((P/'receipts/implement.json').read_bytes())
embedded = v.pop('receipt_hash')
digest = hashlib.sha256(json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf8')).hexdigest()
state = json.loads((P/'state.json').read_bytes())
print(json.dumps(dict(computed=digest, embedded=embedded, matches=digest == embedded,
    state_matches=state['nodes']['implement']['receipt_hash'] == embedded,
    state=state['nodes']['implement']['state'], claims=json.loads((P/'claims.json').read_bytes()))))
