from pathlib import Path
import ast
import hashlib
import json
F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
Q = F/'.agents/cpu-outcome-recovery-20261017'
name = 'tests/contract/test_cpu_execution_admission.py'
before = (F/'.agents/cpu-capacity-connection-20261017'/name).read_bytes()
after = (Q/name).read_bytes()
target = 'test_operation_wall_budget_bounds_total_admission_separately_from_native_duration'
def strip(raw):
    tree = ast.parse(raw)
    hits = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == target]
    assert len(hits) == 1
    function = ast.dump(hits[0], include_attributes=False)
    hits[0].body = [ast.Pass()]
    return ast.dump(tree, include_attributes=False), function
a, old = strip(before); b, new = strip(after)
assert a == b and old != new
m2 = json.loads((R/'cut-r2/MANIFEST.json').read_bytes())
m3 = json.loads((R/'cut-r3/MANIFEST.json').read_bytes())
assert set(m2['payload_hashes']) == set(m3['payload_hashes'])
assert [p for p in m2['payload_hashes'] if m2['payload_hashes'][p] != m3['payload_hashes'][p]] == [name]
with (R/'FIXTURE-DELTA.json').open('x', encoding='utf8') as stream:
    json.dump(dict(path=name, before_sha256=hashlib.sha256(before).hexdigest(),
        after_sha256=hashlib.sha256(after).hexdigest(), other_method_ASTs_identical=True,
        product_source_unchanged=True, authorization='Root authorized this exact one-method deterministic counter correction'), stream, indent=2)
selected = [
    'test_stop_in_final_elapsed_callback_wins_after_all_owner_callbacks',
    'test_missing_capacity_at_final_check_and_clock_rollback_deny',
    'test_slow_final_owner_denies_and_elapsed_rollback_does_not_reset',
    'test_overlong_initial_native_retainer_is_measured_and_denied_before_consume',
    'test_final_callback_cannot_cross_either_canonical_intent_deadline_domain',
    'test_cumulative_retained_time_cannot_reset_with_each_fresh_check',
    'test_overlong_manager_entry_retires_exact_retainer_without_consuming', target]
value = (R/'run_regression.py').read_text(encoding='utf8').replace('cut-r2/MANIFEST.json', 'cut-r3/MANIFEST.json')
value = value.replace("D.name.startswith('regression-')", "D.name.startswith('timing-')")
start, end = value.index('for cls in ('), value.index('expected = [')
value = value[:start] + 'for name in '+repr(selected)+':\n    suite.addTest(admission.CpuExecutionAdmissionTests(name))\n' + value[end:]
with (R/'run_timing.py').open('x', encoding='utf8') as stream: stream.write(value)
print('Eight explicit timing cases prepared; all other method ASTs and all product bytes unchanged.')
