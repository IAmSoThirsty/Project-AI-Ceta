"""Seal distinct ET2 review against the actual author cut and own executions."""
from et_support import *
import ast
D = R / 'independent-root-review'; M = D / 'replica'
setup = json.loads((D / 'PREPARATION.json').read_text())
main = json.loads((D / 'connected-r1.json').read_text())
closure = json.loads((D / 'literal-closure-r2.json').read_text())
native = json.loads((D / 'native-custody-r1/RESULT.json').read_text())
manifest = json.loads((Q / 'TRANSFER-MANIFEST.json').read_text())
assert sha(Q / 'TRANSFER-MANIFEST.json') == '4d85e8cdf9dafec3c10e923875e0dd9949938d473facb611ac75ae0400f33e60'
assert main['exit_status'] == closure['exit_status'] == native['exit_status'] == 0
assert main['tests_run'] == 394 and main['failures'] == main['errors'] == main['skips'] == 0
assert main['expected_ids'] == main['executed_ids'] == main['stopped_ids']
assert main['expected_ids'] == json.loads((R / 'connected-r1.json').read_text())['expected_ids']
assert main['all_fixture_stores_closed'] and not main['new_threads_remaining']
assert closure['tests_run'] == 2 and closure['all_fixture_stores_closed']
assert native['tests_run'] == 3 and native['all_recorded_custody_closed'] and not native['new_threads']
assert all(ordinary(Q / name) == row for name, row in setup['author_payloads'].items())
assert all(ordinary(M / name) == row for name, row in setup['replica'].items())
assert all(ordinary(F / name) == row for name, row in setup['Source290'].items())
assert all(Path(name).is_relative_to(M / 'src') for name in main['source_imports'].values())
parent_probe = F / '.agents/runtime/et1-20261014/independent-review/probe_cumulative_budget.py'
probe_class = next(item for item in ast.parse(parent_probe.read_text()).body if isinstance(item, ast.ClassDef) and item.name == 'CumulativeBudgetProbe')
assert digest(ast.dump(probe_class, include_attributes=False).encode()) == closure['literal_class_ast_sha256']
environment_base = F / '.agents/runtime/er1-20261014/active-application/environment-after.json'
environment = json.loads(environment_base.read_text()); E3 = Path(environment['source_root'])
observed = {}
for row in environment['members']:
    if row['kind'] == 'ordinary_file':
        actual = ordinary(E3 / row['relative_path'])
        assert actual['sha256'] == row['sha256'] and actual['native_identity'] == row['native_identity']
        observed[row['relative_path']] = actual
assert len(observed) == 3601 and sum(row['bytes'] for row in observed.values()) == 231026067
write_new(D / 'CONSERVATION.json', {'at': utc(), 'Source290': setup['Source290'],
    'author316': setup['author_payloads'], 'replica316': setup['replica'],
    'ordinary_bytes_native_identities_exact': True,
    'E3_accepted_reference': reference(environment_base), 'E3_ordinary_files': observed,
    'E3_ordinary_count': 3601, 'E3_ordinary_bytes': 231026067,
    'E3_membership_directory_reaudit': False, 'qualification': 'All baseline E3 ordinary files independently rehashed; this reviewer makes no new complete directory-membership claim.',
    'Source_application': False})
report = {'at': utc(), 'reviewer': '/root', 'author': '/root/pressure_writer', 'decision': 'approved',
    'manifest': reference(Q / 'TRANSFER-MANIFEST.json'), 'implement': reference(R / 'implement.json'),
    'reviewed_paths': manifest['eligible_application_paths'], 'changed_parent_paths': manifest['changed_parent_payloads'],
    'personally_inspected': ['Complete effect_transactions.py including _row/_commit/_recover/canonical guard paths',
        'Owned CPU outcome contract and controlled fixture budget change',
        'Actual-writes SQL reader and nine new capacity/rollback/reopen/concurrency/tamper/retry tests',
        'Unchanged parent hostile probe and explicit finite closure adaptations'],
    'verified': [
        'Cumulative counter retains prior durable logical bytes; no per-transaction reset.',
        'Initial attempt count is independently retained and decision-bound; latest settlement binds total, preceding total and original attempt charge.',
        'Recovery authenticates attempt/settlement decisions and reconstructs the latest batch from exact indexed events/payloads and projection values.',
        'Actual SQL retained logical-value totals equal stored_bytes across advancing uncertainty until finite overflow.',
        'Overflow, CAS concurrency and rollback retain prior evidence, charged liability and historical uncertainty.',
        'Exact retries and reopened historical recovery produce no new effect or capacity refund.',
        'The original 8KiB request is now an atomic denial; successful controlled inputs explicitly reserve32KiB within unchanged contracts.'],
    'connected': reference(D / 'connected-r1.json'), 'connected_unique_cases': 394,
    'literal_closure': reference(D / 'literal-closure-r2.json'), 'additional_closure_cases': 2,
    'native_custody_subset': reference(D / 'native-custody-r1/RESULT.json'),
    'native_custody_repeated_existing_methods': 3, 'native_lifetimes': native['native_lifetimes'],
    'crash_observations': main['crash_observations'], 'journals_in_connected_run': len(main['fixture_stores']),
    'all_recorded_journals_closed': True, 'new_threads': [],
    'new_source_LOC': 50, 'source_removed': 13, 'new_test_LOC': 149, 'integrated_source_LOC': 0,
    'conservation': reference(D / 'CONSERVATION.json'),
    'reviewer_metadata_failure': reference(D / 'CLOSURE-METADATA-FAILURE-r1.json'),
    'reviewer_metadata_repair': 'Original closure bodies passed; final JSON construction referenced a missing copied baseline. Only the historical author-baseline reference was corrected before a new finite2case execution.',
    'historical_capture_limit': native['full394_prior_PID_capture'],
    'independence': 'Root did not author ET1/ET2. Root authored RC2 contract dependency and earlier reviewed KA1; this is distinct review of the ET2 cumulative repair under that disclosed shared dependency.',
    'remaining': [
        'Native producer/observer/currentness integration remains controlled and default closed.',
        'Actual effect admission must establish capacity for required outcome/evidence before dispatch; a durable attempt alone grants no dispatch authority.',
        'Logical value accounting does not qualify physical SQLite metadata/copies/index/page/WAL/free-space or power-loss overhead.',
        'Guarded Source integration and delivered-source regression have not occurred.'],
    'Source_publication': False, 'profile_operations': [], 'genuine_native_effect_invocation': False}
write_new(D / 'REPORT.json', report)
sys.path.insert(0, 'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_receipts import validate_receipt, load_receipt, sha256_json
from taar.orchestration_runtime import _snapshot_workspace, _changed_files
claim = json.loads((R / RUN / 'claims.json').read_text())['review']
graph = json.loads((R / RUN / 'graph.json').read_text())['graph']
assert claim['executor_id'] == '/root' and _changed_files(claim['baseline_snapshot'], _snapshot_workspace(Q, Path('T:/'))) == []
receipt = {'schema_version': 1, 'run_id': RUN, 'node_id': 'review', 'executor_id': '/root',
    'started_at': claim['claimed_at'], 'finished_at': utc(), 'input_hash': claim['input_hash'], 'changed_files': [],
    'result': {'manifest': reference(Q / 'TRANSFER-MANIFEST.json'), 'report': reference(D / 'REPORT.json'),
        'connected394_passed': True, 'literal_closure2_passed': True, 'native_subset3_passed_6closed': True,
        'Source290_retained': True, 'candidate316_retained': True, 'Source_publication': False},
    'commands': [{'command': str(PY) + ' -B -X utf8 ' + str(D / name) + args, 'exit_status': 0}
        for name, args in (('run_tests.py', ' connected-r1 connected'), ('run_parent_closure.py', ' literal-closure-r2'), ('run_native_custody.py', ''))],
    'validations': [{'name': name, 'passed': True} for name in (
        '394_original_plus9 IDs pass without failures errors skips', 'Literal8KiB overflow and32KiB exact retry closure pass',
        'Cumulative SQL equality concurrent CAS reopen tamper rollback and no-refund inspected and verified',
        'All observed journals and separate exact6native lifetimes retired no new threads',
        'Source290 and author316 and replica316 and baselineE33601 ordinary native bytes retained')],
    'exit_status': 0, 'decision': 'approved'}
kwargs = {'run_id': RUN, 'node_id': 'review', 'executor_id': '/root', 'input_hash': claim['input_hash'],
    'claimed_at': claim['claimed_at'], 'node': graph['nodes']['review']}
validate_receipt(receipt, **kwargs); write_new(D / 'review.json', receipt)
validate_receipt(load_receipt(D / 'review.json'), **kwargs)
complete = invoke(['node', 'complete', RUN, 'review', str(D / 'review.json')], 'root-review-complete')
stored = json.loads((R / RUN / 'receipts/review.json').read_text())
state = json.loads((R / RUN / 'state.json').read_text())
claims = json.loads((R / RUN / 'claims.json').read_text())
result = json.loads((R / RUN / 'results/review.json').read_text())
assert len(receipt) == 13 and set(stored) == set(receipt) | {'git_baseline', 'observed_git', 'receipt_hash'}
typed = lambda item: json.dumps(item, sort_keys=True, separators=(',', ':'), allow_nan=False)
assert typed(receipt) == typed({key: stored[key] for key in receipt})
fingerprint = sha256_json({key: value for key, value in stored.items() if key != 'receipt_hash'})
assert fingerprint == stored['receipt_hash'] == result['receipt_hash'] == state['nodes']['review']['receipt_hash']
assert result['result'] == receipt['result']
assert state['sequence'] == 9 and state['nodes']['review']['state'] == 'SUCCEEDED' and claims == {}
write_new(D / 'ACTUAL-READBACK.json', {'at': utc(), 'state': state, 'claims': claims, 'result': result,
    'strict_local13_persisted16_typed_exact': True, 'fingerprint': fingerprint, 'review': reference(D / 'review.json')})
write_new(D / 'REVIEW-SEAL.json', {'at': utc(), 'reviewer': '/root', 'manifest': reference(Q / 'TRANSFER-MANIFEST.json'),
    'members': {name: reference(D / name) for name in ('REPORT.json', 'review.json', 'ACTUAL-READBACK.json',
        'CONSERVATION.json', 'connected-r1.json', 'literal-closure-r2.json', 'native-custody-r1/RESULT.json',
        'CLOSURE-METADATA-FAILURE-r1.json')}, 'claim_released': True, 'Source_application': False})
print(json.dumps({'decision': 'approved', 'review': reference(D / 'review.json'), 'report': reference(D / 'REPORT.json'),
    'readback': reference(D / 'ACTUAL-READBACK.json'), 'seal': reference(D / 'REVIEW-SEAL.json'), 'claims': claims}), flush=True)
