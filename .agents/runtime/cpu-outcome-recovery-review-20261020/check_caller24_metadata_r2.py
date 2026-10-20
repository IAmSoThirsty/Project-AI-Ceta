from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
N = F/'.agents/runtime/cpu-outcome-recovery-r4-regression-20261020/caller24'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
pins = {
    'run_once.py': 'c39dc94bfc18448d7297316c794455d846ed776d2e5b4b69061f645a1f27934b',
    'run_once_v2.py': '4330e9053809aa7985f859266135fce8c0c1399e5510034d0e2dea6cd74b2ed0',
    'METADATA-CORRECTION.diff': '99d47df2aa44194c708f69c2f0195c20c56c4f7ea2ad129d224fe3b3f1c7e788',
    'OUTER-DELTA-R2.diff': '0a99b489c92483e03025581e98ea27e9ba2767f56b89efbd4becf6f84b5448ab',
    'PREPARATION-R2.json': '7e6858874c757ea499d1c6c3bf4bf7b2c2966700aabae48fb6b0d2df62b448cc',
    'run_controlled.py': '3fed9083b4db8634674d6ef4edba31eff5cb274b09b58c811b9cc943e0c620da',
    'CASESET.json': '2700c815784b264158f8d351fc5c23d209c3e07eb318af5b5adad9dd63760433',
    'scope_guard_v2.py': 'f90db473ae1abb2bea8762c8e8562f44b4df12149b0e08803025fa33d310df13',
}
assert all(sha(N/name) == pin for name,pin in pins.items())
old, new = (N/'run_once.py').read_bytes(), (N/'run_once_v2.py').read_bytes()
before = b"old_failed_regression_sha256=sha(OLD/'controlled-r1/RESULT.json')"
after = b"old_failed_regression_sha256=sha(OLD/'regression-r1/RESULT.json')"
assert old.count(before) == 1 and old.replace(before, after) == new
compile(new, str(N/'run_once_v2.py'), 'exec')
prior_failure = json.loads((F/'.agents/runtime/cpu-outcome-recovery-20261017/regression-r1/RESULT.json').read_bytes())
assert prior_failure['exit_status'] != 0
record = dict(at=datetime.now(timezone.utc).isoformat(), actor='/root/recovery_join_review20',
    supplements=dict(path=str(R/'CALLER24-RUNNER-REVIEW-R2.json'), sha256=sha(R/'CALLER24-RUNNER-REVIEW-R2.json')),
    reviewed_inputs=pins, sole_change='Historical failure pointer restored to exact original failed169 result.',
    byte_delta_exactly_one_replacement=True, tests_or_acceptance_gates_changed=False,
    decision='APPROVED_FOR_ONE_ROOT_RELEASED_CONTROLLED24_RUN_USING_V2',
    reviewer_executed_cohort=False, Source_publication_approved=False)
path = R/'CALLER24-METADATA-SUPPLEMENT-R2.json'
with path.open('x', encoding='utf8') as stream:
    json.dump(record, stream, indent=2); stream.write('\n')
print(json.dumps(dict(path=str(path), sha256=sha(path), decision=record['decision'])))
