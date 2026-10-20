"""Independent dormant original24 runner review; no cohort execution."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import hashlib
import json

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
A = F/'.agents/runtime/cpu-outcome-recovery-20261017'
V = F/'.agents/runtime/cpu-outcome-recovery-r4-regression-20261020'
N = V/'caller24'
Q = F/'.agents/cpu-outcome-recovery-r4-20261020'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
pins = {
    'PREPARATION.json': '2653ccee8ef0fa6aed071f28f0ec9add80b5da98a59f349a129bd91b4314537a',
    'CASESET.json': '2700c815784b264158f8d351fc5c23d209c3e07eb318af5b5adad9dd63760433',
    'run_controlled.py': '3fed9083b4db8634674d6ef4edba31eff5cb274b09b58c811b9cc943e0c620da',
    'run_once.py': 'c39dc94bfc18448d7297316c794455d846ed776d2e5b4b69061f645a1f27934b',
    'scope_guard_v2.py': 'f90db473ae1abb2bea8762c8e8562f44b4df12149b0e08803025fa33d310df13',
    'RUNNER-DELTA.diff': 'b7e8985775c81b06e1460df605a33bee664759b4df930e223f0b150181b0cc38',
    'OUTER-DELTA.diff': '6f2e8325d473aca98b8ad0d700c40f3f199767955891335ae0518ce214c955e7',
}
assert all(sha(N/name) == pin for name, pin in pins.items())
old = ast.parse((A/'run_controlled.py').read_bytes())
new = ast.parse((N/'run_controlled.py').read_bytes())
def func(tree, name): return next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
def assign(tree, name): return next(node.value for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets))
for name in ('audit',): assert ast.dump(func(old, name)) == ast.dump(func(new, name))
for name in ('suite', 'passed'): assert ast.dump(assign(old, name)) == ast.dump(assign(new, name))
main = ast.parse((V/'run_once.py').read_bytes())
outer = ast.parse((N/'run_once.py').read_bytes())
for name in ('audit', 'contained'):
    assert ast.dump(func(main, name)) == ast.dump(func(outer, name))
cases = json.loads((N/'CASESET.json').read_bytes())
prior = json.loads((A/'controlled-r2/RESULT.json').read_bytes())
assert len(cases['expected_ids']) == 24 and cases['expected_ids'] == prior['expected_ids'] == cases['original24_ids']
test_file = Q/'tests/contract/test_cpu_outcome_recovery.py'
assert sha(test_file) == 'a300ccaa22c11b9d7c7e164f64798a18038b13a97542a65dc0770d320f53b5c6'
cls = next(node for node in ast.parse(test_file.read_bytes()).body if isinstance(node, ast.ClassDef) and node.name == 'CpuOutcomeRecoveryTests')
derived = ['test_cpu_outcome_recovery.CpuOutcomeRecoveryTests.'+name for name in sorted(node.name for node in cls.body if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'))]
assert derived == cases['expected_ids']
preparation = json.loads((N/'PREPARATION.json').read_bytes())
first, second = Path(preparation['sqlite_fixture_root']), Path(preparation['other_cohort_fixture_root'])
assert not first.is_relative_to(second) and not second.is_relative_to(first)
record = dict(at=datetime.now(timezone.utc).isoformat(), actor='/root/recovery_join_review20',
    reviewed_inputs=pins, exact_original24_ids=True, test_body_unchanged=True,
    inner_suite_audit_acceptance_AST_unchanged=True, outer_audit_write_guard_AST_unchanged=True,
    original24_ids_independently_derived_from_AST=True, fixture_roots_disjoint=True,
    decision='APPROVED_FOR_ONE_ROOT_RELEASED_CONTROLLED24_RUN',
    no_native_operations=True, executed_by_reviewer=False, no_product_acceptance=True,
    note='Inherited BEFORE field old_failed_regression_sha256 points to controlled-r1, which is prior successful evidence; the field label is not evidence of a failed run.')
path = R/'CALLER24-RUNNER-REVIEW-R2.json'
with path.open('x', encoding='utf8') as stream:
    json.dump(record, stream, indent=2); stream.write('\n')
print(json.dumps(dict(path=str(path), sha256=sha(path), decision=record['decision'])))
