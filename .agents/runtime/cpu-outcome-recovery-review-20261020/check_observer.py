"""Independent pure review of the regression SQLite path observer; no DB opens."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import importlib.util
import json

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
V = F/'.agents/runtime/cpu-outcome-recovery-regression-20261020'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
pins = {
    'scope_guard_v2.py': 'f90db473ae1abb2bea8762c8e8562f44b4df12149b0e08803025fa33d310df13',
    'run_once_v2.py': 'b79af3eb755a79079594784e025ee191f3ce0e58a17dbda34297501767259cdf',
    'OBSERVER-REPAIR.diff': '13ad357fc29e3056cb8875e6b66b1fb9534a043c59a568ee8e8cfab8389a8ef9',
    'OBSERVER-REPAIR-PURE-CHECKS.json': '96be7b0291be5f8e0345dc4ecced51b7591acb2dea8cefc930e7b2d50ba99164',
    'run_regression.py': '117321a526ce414e0599161cbd0451d28c6ce6f7e85511913852082af380c358',
}
assert all(sha(V/name) == expected for name, expected in pins.items())
assert (V/'attempt-r2/run_regression.py').read_bytes() == (V/'run_regression.py').read_bytes()
spec = importlib.util.spec_from_file_location('review_scope_guard', V/'scope_guard_v2.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
root = V/'attempt-r2'
author = json.loads((V/'OBSERVER-REPAIR-PURE-CHECKS.json').read_bytes())
checks = []
for item in author['checks']:
    actual = module.sqlite_contained(item['input'], root)
    checks.append(dict(name=item['name'], expected=item['expected'], actual=actual))
uri = (root/'fixtures/review.db').as_uri()
extra = [
    ('fragment denied', uri+'#ignored', False),
    ('sibling prefix denied', str(root)+'-outside/review.db', False),
    ('raw traversal denied', str(root/'..'/'outside.db'), False),
    ('encoded backslash traversal denied', root.as_uri()+'/%2e%2e%5coutside.db', False),
    ('URI drive replacement denied', 'file:///C:/Windows/review.db', False),
    ('byte path accepted', str(root/'fixtures/bytes.db').encode(), True),
    ('invalid object denied', object(), False),
]
for name, value, expected in extra:
    checks.append(dict(name=name, expected=expected, actual=module.sqlite_contained(value, root)))
assert len(checks) == 19 and all(c['actual'] is c['expected'] for c in checks)
result = dict(at=datetime.now(timezone.utc).isoformat(), actor='/root/recovery_join_review20',
    review='Independent observer-only URI parser reproduction', pins=pins, checks=checks,
    passed=len(checks), failed=0, candidate_tests_changed=False, sqlite_connections_opened=0,
    profile_operations=0, native_process_operations=0,
    limitations=['Python audit observer is test instrumentation, not an OS security boundary.',
        'No corrected product regression execution is established by these parser checks.'])
path = R/'OBSERVER-PURE-REVIEW.json'
with path.open('x', encoding='utf8') as stream:
    json.dump(result, stream, indent=2); stream.write('\n')
print(json.dumps(dict(result=str(path), sha256=sha(path), passed=len(checks))))
