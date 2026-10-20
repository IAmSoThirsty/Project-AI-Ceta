"""Distinct AC5 cleanup repair review with unchanged native hostile closure."""
from pathlib import Path
import ast, json, os, subprocess, sys
F = Path(__file__).resolve().parents[4]
BASE = F / '.agents/runtime/ac5-20261015'; Q = F / '.agents/ac5-20261015'; D = Path(__file__).resolve().parent
sys.path.insert(0, str(F / '.agents/runtime/en1-20261014'))
import en1_support as s
s.Q, s.R, s.RUN, s.ACTOR = Q, BASE, 'ac5-20261015', '/root'
setup = json.loads((D / 'PREPARATION.json').read_text())
main = json.loads((D / 'cohort-r1/RESULT.json').read_text())
literal = json.loads((D / 'literal-r1.json').read_text())
assert main['exit_status'] == literal['exit_status'] == 0 and main['tests_run'] == 26 and literal['tests_run'] == 2
assert main['expected_ids'] == main['executed_ids'] == main['stopped_ids']
assert not main['failures'] and not main['errors'] and not main['skipped'] and not main['new_threads']
assert not any(main['pending_native_resources']) and not main['forbidden_calls']
assert not literal['failures'] and not literal['errors'] and not literal['skips'] and not literal['new_threads']
assert literal['all_owned_native_resources_retired'] and not literal['forbidden_calls']
assert s.sha(Q / 'TRANSFER-MANIFEST.json') == '22263a72a8208e4024b94088ba95cf651846f542c44fa6fe44a68957eb29aa3e'
assert s.sha(BASE / 'implement.json') == '7bda9c9a505a5a9accde3690350d47b102f8c42f7a110b613746a92577d5a15b'
assert all(s.ordinary(Q / name) == row for name, row in setup['candidate295'].items())
assert all(s.ordinary(F / name) == row for name, row in setup['Source290'].items())
parent = F / '.agents/ac4-20261015'
product = 'src/ceta/supervisor/isolated_worker.py'
def definitions(path):
    tree = ast.parse(path.read_text())
    return {item.name: ast.dump(item, include_attributes=False) for item in tree.body if isinstance(item, (ast.FunctionDef, ast.ClassDef))}
before, after = definitions(parent / product), definitions(Q / product)
assert set(before) == set(after) and [name for name in before if before[name] != after[name]] == ['_attach_cleanup']
test = 'tests/contract/test_isolation_token_diagnostics.py'
def methods(path):
    return {(node.name, item.name): ast.dump(item, include_attributes=False) for node in ast.parse(path.read_text()).body if isinstance(node, ast.ClassDef)
        for item in node.body if isinstance(item, ast.FunctionDef) and item.name.startswith('test_')}
old_methods, new_methods = methods(parent / test), methods(Q / test)
assert len(old_methods) == 15 and all(new_methods[name] == value for name, value in old_methods.items())
for name in ('tests/contract/test_isolated_worker.py', 'native/windows_broker/isolated_worker.rs'):
    assert (parent / name).read_bytes() == (Q / name).read_bytes()
assert all(not row['pending_resources'] for row in main['native_observations'])
recoveries = [row for row in main['native_observations'] if 'retired_through_exposed_cleanup' in row]
assert len(recoveries) == 3 and all(row['retired_through_exposed_cleanup'] and row['exact_primary'] and row['nested_exact_primary'] for row in recoveries)
assert all(row['caller_visible_cleanup_present'] and row['exact_primary_preserved'] and row['all_owned_native_resources_retired'] for row in literal['observations'])
report = {'at': s.utc(), 'reviewer': '/root', 'author': '/root/pressure_writer', 'decision': 'approved',
    'manifest': s.reference(Q / 'TRANSFER-MANIFEST.json'), 'implement': s.reference(BASE / 'implement.json'),
    'reviewed_scope': 'AC5 exact cleanup-custody repair and unchanged AC4 token diagnostics/qualification dependency.',
    'finding_closed': 'AC4-F01', 'source_changed_definition': '_attach_cleanup',
    'verified': ['Exact cleanup owner and owned_process survive refused primary attribute setters/getters.',
        'Best-effort notes use base storage/exact built-in lists and invoke no overridable hooks.',
        'Native token handles are measured live at error exposure and retired through the exposed cleanup owner.',
        'Nested recovery failure retains the same exact cleanup and primary for explicit retry.',
        'Both original native hostile methods pass unchanged; rejected AC4 result remains preserved.',
        'Every token qualification predicate, native launch/class implementation, other function AST and Rust byte remains exact.'],
    'cohort': s.reference(D / 'cohort-r1/RESULT.json'), 'cohort_unique_methods': 26,
    'literal_native_probe': s.reference(D / 'literal-r1.json'), 'additional_literal_methods': 2,
    'actual_current_process_token_observations': len(main['native_observations']) + len(literal['observations']),
    'actual_native_recovery_through_exposed_cleanup': len(recoveries),
    'all_recorded_resources_retired': True, 'new_threads': [],
    'Source290_native_bytes_exact': True, 'candidate295_native_bytes_exact': True,
    'E3': {'author_conservation': s.reference(BASE / 'INPUT-CONSERVATION.json') if (BASE / 'INPUT-CONSERVATION.json').exists() else s.reference(BASE / 'AUTHOR-SEAL.json'),
        'independent_reviewer_full_environment_rehash': False},
    'original22_method_conservation': s.reference(BASE / 'FINAL-ID-CONSERVATION.json'),
    'new_delta': {'source_added': 9, 'source_removed': 5, 'test_added': 92, 'integrated_source_LOC': 0},
    'independence': setup['authorship_disclosure'],
    'existing_issues': [{'id': 'AC3-LIVE-TOKEN-QUALIFICATION', 'classification': 'blocking positive isolation acceptance',
        'status': 'Historical rejected token values remain unavailable; future separately approved tool must record new measured fields.'},
        {'id': 'AC3-NO-PROFILE-REGEX', 'classification': 'requires separate follow-up',
        'status': 'Historical unanchored :2 regex also accepted267; exact native error2 is not established.'}],
    'profile_operations': [], 'worker_launches': [], 'Source_application': False,
    'positive_isolation_qualified': False, 'runtime_activation': False}
s.write_new(D / 'REPORT.json', report)
sys.path.insert(0, 'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_receipts import validate_receipt, load_receipt, sha256_json
from taar.orchestration_runtime import _snapshot_workspace, _changed_files
claim = json.loads((BASE / s.RUN / 'claims.json').read_text())['review']
graph = json.loads((BASE / s.RUN / 'graph.json').read_text())['graph']
assert claim['executor_id'] == '/root' and _changed_files(claim['baseline_snapshot'], _snapshot_workspace(Q, Path('T:/'))) == []
receipt = {'schema_version': 1, 'run_id': s.RUN, 'node_id': 'review', 'executor_id': '/root',
    'started_at': claim['claimed_at'], 'finished_at': s.utc(), 'input_hash': claim['input_hash'], 'changed_files': [],
    'result': {'manifest': s.reference(Q / 'TRANSFER-MANIFEST.json'), 'report': s.reference(D / 'REPORT.json'),
        'finding': 'AC4-F01_CLOSED_BY_AC5', 'cohort26_passed': True, 'literal2_passed': True,
        'Source290_candidate295_retained': True, 'Source_application': False},
    'commands': [{'command': str(s.PY) + ' -B -X utf8 ' + str(D / name) + args, 'exit_status': 0}
        for name, args in (('run_diagnostics.py', ' cohort-r1'), ('run_literal_probe.py', ' literal-r1'))],
    'validations': [{'name': name, 'passed': True} for name in ('26original_and_added_methods_pass',
        'Literal_native2_failures_now_pass_without_oracle_change', 'Exact_primary_custody_and_exposed_native_recovery_verified',
        'All_original_token_predicates_and_other_module_ASTs_exact', 'Source290_candidate295_retained_no_profile_or_worker')],
    'exit_status': 0, 'decision': 'approved'}
kwargs = {'run_id': s.RUN, 'node_id': 'review', 'executor_id': '/root', 'input_hash': claim['input_hash'], 'claimed_at': claim['claimed_at'], 'node': graph['nodes']['review']}
validate_receipt(receipt, **kwargs); s.write_new(D / 'review.json', receipt); validate_receipt(load_receipt(D / 'review.json'), **kwargs)
s.invoke(['node', 'complete', s.RUN, 'review', str(D / 'review.json')], 'root-review-complete')
stored = json.loads((BASE / s.RUN / 'receipts/review.json').read_text())
state = json.loads((BASE / s.RUN / 'state.json').read_text()); claims = json.loads((BASE / s.RUN / 'claims.json').read_text())
result = json.loads((BASE / s.RUN / 'results/review.json').read_text())
typed = lambda item: json.dumps(item, sort_keys=True, separators=(',', ':'), allow_nan=False)
assert len(receipt) == 13 and len(stored) == 16 and typed(receipt) == typed({name: stored[name] for name in receipt})
fingerprint = sha256_json({name: value for name, value in stored.items() if name != 'receipt_hash'})
assert fingerprint == stored['receipt_hash'] == state['nodes']['review']['receipt_hash'] == result['receipt_hash']
assert result['result'] == receipt['result'] and state['sequence'] == 9 and state['nodes']['review']['state'] == 'SUCCEEDED' and claims == {}
s.write_new(D / 'ACTUAL-READBACK.json', {'at': s.utc(), 'state': state, 'claims': claims, 'result': result,
    'strict13_persisted16_exact': True, 'fingerprint': fingerprint, 'review': s.reference(D / 'review.json')})
s.write_new(D / 'REVIEW-SEAL.json', {'at': s.utc(), 'review': s.reference(D / 'review.json'),
    'manifest': s.reference(Q / 'TRANSFER-MANIFEST.json'), 'report': s.reference(D / 'REPORT.json'),
    'readback': s.reference(D / 'ACTUAL-READBACK.json'), 'cohort': report['cohort'],
    'literal': report['literal_native_probe'], 'claim_released': True, 'Source_application': False})
print(json.dumps({'decision': 'approved', 'review': s.reference(D / 'review.json'), 'report': s.reference(D / 'REPORT.json'),
    'readback': s.reference(D / 'ACTUAL-READBACK.json'), 'seal': s.reference(D / 'REVIEW-SEAL.json'), 'claims': claims}), flush=True)
