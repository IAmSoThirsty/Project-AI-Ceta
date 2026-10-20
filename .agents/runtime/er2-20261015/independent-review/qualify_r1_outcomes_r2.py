"""Authenticate exact original106 outcomes without relabeling failed108 process."""
import ast
import json
import re
from review_support import Q, R, V, MANIFEST, read, s


def main():
    path = V / 'connected-r1/RESULT.json'
    assert s.sha(path) == '06dd10b7d307a4f04c8ff7b3a4f5eab566222c08108c9e526a865f7f2364d631'
    result = read(path)
    raw_path = V / 'connected-r1/RAW.txt'
    assert result['raw'] == s.reference(raw_path)
    preparation = read(V / 'PREPARATION.json')
    for name, pin in preparation['helpers'].items(): assert s.sha(V / name) == pin
    original = read(R / 'connected-r1/RESULT.json')['expected_ids']
    assert len(original) == len(set(original)) == 106
    assert result['tests_run'] == len(result['expected_ids']) == 108
    assert result['expected_ids'] == result['executed_ids'] == result['stopped_ids']
    assert result['expected_ids'][:106] == original
    assert result['manifest_sha256'] == MANIFEST
    assert result['failures'] == result['exit_status'] == 1 and result['errors'] == result['skips'] == 0
    invalid = 'independent_retention_checks.IndependentRetentionChecks.test_old_retain_denial_never_dispatches_a_newer_capture'
    positive = 'independent_retention_checks.IndependentRetentionChecks.test_successor_uses_acknowledged_cas_without_early_durability_or_duplicate_dispatch'
    assert result['expected_ids'][106:] == [invalid, positive]
    assert len(result['failure_details']) == 1 and result['failure_details'][0][0] == invalid
    assert "'TASK_EDITOR_RETAINED' != 'DENIED_RECONCILE'" in result['failure_details'][0][1]
    assert result['error_details'] == [] and result['remaining_threads'] == []
    raw = raw_path.read_text(encoding='utf-8')
    passing = original + [positive]
    outcomes = []
    for identifier in passing:
        method = identifier.rsplit('.', 1)[1]
        module, cls, _ = identifier.split('.')
        source = (Q / 'tests/contract' / (module + '.py')) if identifier in original else (V / (module + '.py'))
        definition = next(node for node in ast.parse(source.read_bytes()).body if isinstance(node, ast.ClassDef) and node.name == cls)
        function = next(node for node in definition.body if isinstance(node, ast.FunctionDef) and node.name == method)
        documentation = ast.get_docstring(function)
        description = method + ' (' + identifier + ')'
        if documentation: description += '\n' + documentation.split('\n')[0].strip()
        pattern = '^' + re.escape(description + ' ... ok') + '$'
        assert len(re.findall(pattern, raw, re.MULTILINE)) == 1, identifier
        outcomes.append({'test_id': identifier, 'outcome': 'PASS', 'source': 'immutable exact TextTestResult raw line'})
    assert len(re.findall('^' + re.escape(invalid.rsplit('.', 1)[1] + ' (' + invalid + ') ... FAIL') + '$', raw, re.MULTILINE)) == 1
    physical = result['physical_resources']
    assert len(physical['sqlite']) == 141 and all(row['physical_closed_probe'] for row in physical['sqlite'])
    assert physical['remaining_resources'] == [] and physical['owned_resources_closed'] is True
    native = result['native_fixture_captures']
    assert len(native) == 48 and all(row['retired'] and row['observed_live_at_return'] for row in native)
    native_cases = {identifier for identifier in original if identifier.startswith(
        ('test_editor_recovery.NativeEditorRecoveryTests.', 'test_editor_recovery.QtEditorRecoveryTests.'))}
    assert len(native_cases) == 12 and {row['test_id'] for row in native} == native_cases
    outer = read(V / 'LAUNCH-RESULT.json')
    assert outer['exit_status'] == outer['record']['child_exit'] == 1
    assert outer['primary_error'] is None and outer['record']['retirement_error'] is None
    assert all(outer['record']['native_owner_after'].values())
    assert outer['record']['child_result'] == s.reference(path)
    proof = {'at': s.utc(), 'manifest_sha256': MANIFEST, 'qualification_exit_status': 0,
        'actual_cohort_tests_run': 108, 'actual_cohort_exit_status': 1,
        'actual_cohort_failures': 1, 'actual_cohort_errors': 0, 'actual_cohort_skips': 0,
        'original106': outcomes[:106], 'additional_positive': outcomes[106],
        'original106_outcomes_independently_authenticated': True,
        'invalid_reviewer_oracle': {'test_id': invalid, 'outcome': 'FAIL',
            'classification': 'Reviewer test-model error; fixed by separately named supported recovery-CAS stimulus.',
            'canonical_policy': 'kernel/editor_recovery.py121-129 deliberately retains raw prior task basis; apply203-204 enforces recovery CAS.'},
        'all_141_observed_SQLite_connections_closed': True, 'all_48_native_lifetimes_retired': True,
        'result': s.reference(path), 'raw': s.reference(raw_path), 'outer': s.reference(V / 'LAUNCH-RESULT.json'),
        'native_fixture_repetition': False, 'full_gate_complete': False, 'Source_publication': False}
    s.write_new(V / 'R1-OUTCOME-QUALIFICATION.json', proof)
    print(json.dumps({'qualifier_exit_status': 0, 'original_passed': 106, 'additional_positive_passed': 1,
        'original108_process_exit_status': 1, 'reviewer_invalid_oracles': 1,
        'proof': s.reference(V / 'R1-OUTCOME-QUALIFICATION.json')}), flush=True)


if __name__ == '__main__': main()
