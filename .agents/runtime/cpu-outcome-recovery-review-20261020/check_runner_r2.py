"""Read-only evidence checks for old169 and dormant r4 successor177."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import hashlib
import json

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
V = F/'.agents/runtime/cpu-outcome-recovery-regression-20261020'
N = F/'.agents/runtime/cpu-outcome-recovery-r4-regression-20261020'
A = F/'.agents/runtime/cpu-outcome-recovery-repair-20261020'
Q = F/'.agents/cpu-outcome-recovery-r4-20261020'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
read = lambda path: json.loads(path.read_bytes())
def ref(path): return dict(path=str(path), sha256=sha(path))
def write(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2); stream.write('\n')
pins = {
    V/'HANDOFF.json': '8f9201fc2ca7ea43c2f168c423ceeb18ad354cd468db6145085bb8d4b5f76c7c',
    V/'attempt-r2/regression-r1/RESULT.json': 'dc82d38fbc435b6d3d5c739b70db03a97d0d97d09a5cc6dcd858750a22a6ea1e',
    V/'attempt-r2/OUTER-RESULT.json': 'ae41916e893c905fde00945585e5732fb9975f6ff5a5df064c86ab8bfdb31ecb',
    V/'attempt-r2/regression-r1/RAW.txt': 'ab8f4e773d9b3429ace5152649b4869d49bc2c9074b07e6515c4395edf6098aa',
    A/'MANIFEST.json': 'aa1ee89d9d0d63051b090590fea1d4391f9a4aad77ff8d8e92c6bfd04abe270e',
    N/'PREPARATION.json': '006ee88d8f7b42702813a9f35430fbb6144bcdd62b7bdba10647f072274a1201',
    N/'CASESET.json': 'cffdc35adcb195e8cff7edc8d7b5c87cd1cb52f3ed3477d014b7d346773f2403',
    N/'run_regression.py': 'dfad428cf103551d2d78a7953435c10582f171c90a252ad0267084eebbcc4d5c',
    N/'run_once.py': '5a93f0ee72f536d02cb26ea143a7eef1bbdff901d6e11d8f02161b3c69c2e862',
    N/'scope_guard_v2.py': 'f90db473ae1abb2bea8762c8e8562f44b4df12149b0e08803025fa33d310df13',
    N/'RUNNER-DELTA.diff': 'dae27f2bf2b69ea9abf229027d3a3d1358f815e51632fa1f619d5774d925e178',
    N/'OUTER-DELTA.diff': '45705934c5f768acef3dd3812ed0194bc68ae132a12deae5da5f5c66c3713940',
}
assert all(sha(path) == expected for path, expected in pins.items())
handoff = read(V/'HANDOFF.json')
old = read(V/'attempt-r2/regression-r1/RESULT.json')
outer = read(V/'attempt-r2/OUTER-RESULT.json')
assert old['exit_status'] == outer['exit_status'] == outer['runner_exit_status'] == 0
assert old['tests_run'] == 169 and not old['failures'] and not old['errors'] and old['skips'] == 0
ids = old['expected_ids']
assert ids == old['executed_ids'] == old['stopped_ids'] and len(set(ids)) == 169
assert handoff['exact_original169_sequence'] and handoff['candidate_acceptance'] == 'BLOCKED_BY_RJR20_01'
assert outer['candidate_unchanged'] and outer['Source_unchanged']
assert not any(outer[key] for key in ('diagnostics', 'residual_threads', 'scope_violations'))
assert len(old['sqlite_lifetimes']) == 266
assert all(row['closed'] and not row['retained_capacity'] and row['refusal'] == 'closed connection refusal'
    for row in old['sqlite_lifetimes'])
events = [json.loads(line) for line in (V/'attempt-r2/EVENTS.jsonl').read_text(encoding='utf8').splitlines()]
assert len(events) == 338
assert [(event['event'], event['id']) for event in events] == [pair for identifier in ids for pair in (('START', identifier), ('STOP', identifier))]
assert [row['id'] for row in handoff['coverage']] == ids
for row in handoff['coverage']:
    path = Path(row['source_path'])
    assert sha(path) == row['source_sha256'] and row['result'] == 'PASS'
    method = row['id'].rsplit('.', 1)[-1]
    assert any(isinstance(node, ast.FunctionDef) and node.name == method and node.lineno == row['line']
        for node in ast.walk(ast.parse(path.read_bytes())))
for key in ('result', 'outer_result', 'raw', 'before', 'events', 'command_record',
            'prior_failed_attempt', 'observer_repair', 'pure_checks', 'distinct_observer_review',
            'original_gates_self_check', 'terminal_session'):
    item = handoff[key]
    assert sha(Path(item['path'])) == item['sha256']
supplement = dict(at=datetime.now(timezone.utc).isoformat(), actor='/root/recovery_join_review20',
    supplements=ref(R/'REVIEW-R1.json'), result=ref(V/'attempt-r2/regression-r1/RESULT.json'),
    outer=ref(V/'attempt-r2/OUTER-RESULT.json'), handoff=ref(V/'HANDOFF.json'),
    disposition='ACCEPTED_CONTROLLED169_EVIDENCE_ONLY', exact_ids=169, ordered_start_stop_events=338,
    sqlite_connections_observed_closed=266, candidate_payloads=374, accepted_Source_payloads=352,
    frozen_cut='cut-r3; no result transfer to r4', outstanding='RJR20-01 remains open on this cut.',
    candidate_integration_approved=False, native_qualification=False, full_product_complete=False)
supplement_path = R/'REVIEW-R1-REGRESSION-SUPPLEMENT.json'
write(supplement_path, supplement)

cases = read(N/'CASESET.json')
assert cases['original169_ids'] == ids
test_path = Q/'tests/contract/test_cpu_recovery_registration.py'
tree = ast.parse(test_path.read_bytes())
cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'RecoveryRegistrationTests')
new_ids = ['test_cpu_recovery_registration.RecoveryRegistrationTests.' + name
    for name in sorted(node.name for node in cls.body if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'))]
assert len(new_ids) == 8 and new_ids == cases['registration8_ids']
assert cases['expected_ids'] == ids + new_ids and len(set(cases['expected_ids'])) == 177
assert cases['excluded_ids'] == old['excluded_ids']
manifest = read(A/'MANIFEST.json')
assert len(manifest['payload_hashes']) == 375
assert all(sha(Q/name) == expected for name, expected in manifest['payload_hashes'].items())
old_tree = ast.parse((V/'attempt-r2/run_regression.py').read_bytes())
new_tree = ast.parse((N/'run_regression.py').read_bytes())
def top_function(tree, name): return next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
def top_assignment(tree, name): return next(node.value for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets))
assert ast.dump(top_function(old_tree, 'audit')) == ast.dump(top_function(new_tree, 'audit'))
assert ast.dump(top_assignment(old_tree, 'passed')) == ast.dump(top_assignment(new_tree, 'passed'))
assert ast.dump(top_assignment(old_tree, 'suite')) == ast.dump(top_assignment(new_tree, 'suite'))
old_outer = ast.parse((V/'run_once_v2.py').read_bytes())
new_outer = ast.parse((N/'run_once.py').read_bytes())
assert ast.dump(top_function(old_outer, 'audit')) == ast.dump(top_function(new_outer, 'audit'))
assert ast.dump(top_function(old_outer, 'contained')) == ast.dump(top_function(new_outer, 'contained'))
record = dict(at=datetime.now(timezone.utc).isoformat(), actor='/root/recovery_join_review20',
    pins={str(path): pin for path, pin in pins.items() if path.is_relative_to(N)},
    frozen_candidate=ref(A/'MANIFEST.json'), ordered_cases=ref(N/'CASESET.json'),
    review='Full dormant runner and wrapper, exact diff, case ASTs, unchanged guards and acceptance predicates inspected.',
    original169_prefix_unchanged=True, eight_new_case_ids_derived_from_AST=True,
    native_exclusion_unchanged=True, inner_acceptance_AST_unchanged=True,
    outer_audit_and_write_scope_AST_unchanged=True, outer_exact_case_gate_strengthened=True,
    candidate_payloads=375, all_candidate_hashes_match=True,
    decision='APPROVED_FOR_ONE_ROOT_RELEASED_CONTROLLED177_RUN', executed_by_reviewer=False,
    no_product_acceptance=True, no_Source_publication=True,
    remaining='The24 CpuOutcomeRecoveryTests require their own affected r4 run before component acceptance.')
path = R/'RUNNER-REVIEW-R2.json'
write(path, record)
print(json.dumps(dict(runner_review=ref(path), old169_supplement=ref(supplement_path),
    decision=record['decision'])))
