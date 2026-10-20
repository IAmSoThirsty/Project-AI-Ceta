"""Resume only the unstarted copy after the preserved bootstrap argument error."""
from pathlib import Path
import json
import shutil
import sys

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
Q, P = F / '.agents/er1-20261015', F / '.agents/js2-20261015'
sys.dont_write_bytecode = True
sys.path.insert(0, str(F / '.agents/runtime/ka1-20261014'))
import ka1_support as s
s.Q, s.R, s.RUN, s.ACTOR = Q, R, Q.name, '/root'
inputs = json.loads((R / 'SOURCE-INPUTS.json').read_bytes())
assert json.loads((R / s.RUN / 'state.json').read_bytes())['nodes']['implement']['state'] == 'RUNNING'
assert json.loads((R / s.RUN / 'claims.json').read_bytes())['implement']['executor_id'] == '/root'
assert list(Q.iterdir()) == []
s.write_new(R / 'BOOTSTRAP-COPY-FAILURE-R1.json', {
    'at': s.utc(), 'script': s.reference(R / 'bootstrap.py'), 'exit_status': 1,
    'type': 'TypeError', 'message': "safe_components() got an unexpected keyword argument 'missing_ok'",
    'scope': 'Before first copied payload; actual implement remains RUNNING; no lifecycle completion retry',
    'repair': 'Use existing allow_missing parameter and resume only copying'})
for name, row in inputs['parent292'].items():
    assert s.ordinary(P / name) == row
    target = s.fs.safe_components(Q / name, allow_missing=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(P / name, target)
    assert s.ordinary(target)['sha256'] == row['sha256']
    assert s.ordinary(P / name) == row
s.write_new(R / 'COPIED-INPUTS.json', {'at': s.utc(), 'candidate292': {
    name: s.ordinary(Q / name) for name in inputs['parent292']}, 'copied_code_credit': 0,
    'bootstrap_failure': s.reference(R / 'BOOTSTRAP-COPY-FAILURE-R1.json'), 'Source_publication': False})
print(json.dumps({'implement': 'RUNNING', 'copied_payloads': 292, 'Source_publication': False}))
