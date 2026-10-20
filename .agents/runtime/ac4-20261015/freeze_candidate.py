"""Release the finite rejected-token diagnostic cut for distinct review."""
from pathlib import Path
import ast, difflib, json, os, stat, sys
F = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(F / '.agents/runtime/en1-20261014'))
import en1_support as s
Q = s.Q = F / '.agents/ac4-20261015'
R = s.R = F / '.agents/runtime/ac4-20261015'
s.RUN, s.ACTOR = 'ac4-20261015', '/root'
inputs = json.loads((R / 'SOURCE-INPUTS.json').read_text())
proof = json.loads((R / 'focused-r3/RESULT.json').read_text())
assert proof['exit_status'] == 0 and proof['tests_run'] == 22 and not proof['skipped']
assert proof['expected_ids'] == proof['executed_ids'] == proof['stopped_ids']
assert not any(proof['pending_native_resources']) and not proof['new_threads'] and not proof['forbidden_calls']
rows = {name: s.ordinary(Q / name) for name in sorted(proof['candidate_after'])}
assert rows == proof['candidate_before'] == proof['candidate_after'] and len(rows) == 295
source = {name: s.ordinary(F / name) for name in inputs['Source290']}
assert source == inputs['Source290']
changed = sorted(name for name, row in rows.items() if name not in inputs['candidate_before']
    or row != inputs['candidate_before'][name])
scope = ['src/ceta/supervisor/isolated_worker.py', 'tests/contract/test_isolation_token_diagnostics.py',
    'contracts/ISOLATED_WORKER_V1.md']
assert set(changed) == set(scope)
baseline = F / '.agents/runtime/er1-20261014/active-application/environment-after.json'
record = json.loads(baseline.read_text())
environment_root = Path(record['source_root']); assert environment_root == s.PY.parents[1]
environment = {}
for item in record['members']:
    path = environment_root / item['relative_path']
    if item['kind'] == 'ordinary_file':
        value = s.ordinary(path)
        assert value['sha256'] == item['sha256'] and value['native_identity'] == item['native_identity']
        environment[item['relative_path']] = value
    else:
        info = s.fs.lstat(s.fs.safe_components(path)); assert stat.S_ISDIR(info.st_mode) and not s.fs.reparse(info)
        actual, expected = s.fs.file_identity(info), item['native_identity']
        assert {key: value for key, value in actual.items() if key != 'bytes'} == {key: value for key, value in expected.items() if key != 'bytes'}
membership = set()
for directory, folders, files in os.walk(s.fs.io_path(environment_root), followlinks=False):
    normal = environment_root / Path(directory).relative_to(Path(s.fs.io_path(environment_root)))
    membership.update((normal / name).relative_to(environment_root).as_posix() for name in folders + files)
assert membership == {item['relative_path'] for item in record['members']}
assert len(environment) == 3601 and sum(row['bytes'] for row in environment.values()) == 231026067
s.write_new(R / 'CONSERVATION.json', {'at': s.utc(), 'Source290': source, 'candidate295': rows,
    'E3_accepted_baseline': s.reference(baseline), 'E3_ordinary_files': len(environment),
    'E3_ordinary_bytes': sum(row['bytes'] for row in environment.values()),
    'E3_ordinary_bytes_native_identities_membership_exact': True, 'E3_members': environment,
    'Source_application': False})

def meaningful(text):
    excluded = set()
    for node in ast.walk(ast.parse(text)):
        body = getattr(node, 'body', None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            excluded.update(range(body[0].lineno - 1, body[0].end_lineno))
    return {i for i, line in enumerate(text.splitlines()) if line.strip() and not line.lstrip().startswith('#') and i not in excluded}
def delta(before, after):
    old, new = meaningful(before), meaningful(after)
    added = removed = 0
    for tag, a, b, c, d in difflib.SequenceMatcher(a=before.splitlines(), b=after.splitlines(), autojunk=False).get_opcodes():
        if tag != 'equal':
            added += len(old.intersection(range(a, b))) * 0 + len(new.intersection(range(c, d)))
            removed += len(old.intersection(range(a, b)))
    return {'added': added, 'removed': removed}
product = scope[0]; test = scope[1]
measures = {'at': s.utc(), 'method': 'SequenceMatcher spans intersect nonblank/noncomment Python lines excluding AST docstrings; generated artifacts and inherited reuse uncredited.',
    'source': delta((R / 'before' / product).read_text(), (Q / product).read_text()),
    'tests': delta('', (Q / test).read_text()), 'integrated_source_LOC': 0, 'inherited_LOC_credit': 0}
s.write_new(R / 'LOC.json', measures)
s.write_new(R / 'PRIOR-FAILURES.json', {'at': s.utc(), 'runner_path_failure': s.reference(R / 'focused-r1/ENTRY-FAILURE.json'),
    'original_runner': s.reference(R / 'before-run_diagnostics-r1.py'),
    'controlled_fixture_signature_failure': s.reference(R / 'focused-r2/RESULT.json'),
    'controlled_fixture_before_image': s.reference(R / 'before-test-diagnostics-r2.py'),
    'classification': 'First entry failed before tests due to wrong Rust path. Next run had 21 passes/one fixture retry_cleanup signature error. Only runner path and controlled cleanup default corrected; no qualification check or original test changed.',
    'current': s.reference(R / 'focused-r3/RESULT.json')})
for name in scope:
    compile((Q / name).read_text(), str(Q / name), 'exec') if name.endswith('.py') else None
s.write_new(R / 'SELF-REVIEW.json', {'at': s.utc(), 'author': '/root', 'changed_paths': changed,
    'qualification': s.reference(R / 'focused-r3/RESULT.json'), 'LOC': s.reference(R / 'LOC.json'),
    'original_IsolationTokenFacts_AST_exact': True, 'original_test_and_Rust_bytes_exact': True,
    'public_launch_signature_unchanged': True, 'no_qualification_predicate_relaxed': True,
    'actual_native_measurement': 'Current process token rejection only; derived SID memory and two token cleanup handles retired.',
    'partial_observation_and_primary_identity_tested': True, 'positive_isolation_qualified': False,
    'profile_operations': [], 'worker_launches': [], 'Source_application': False,
    'limits': ['The historical failed AC3 token values remain unavailable.',
        'Controlled parser shapes are data only, not OS isolation authentication.',
        'The original native regression :2 regex specificity defect is preserved for separate repair.',
        'No further profile operation is authorized by this implementation.']})
manifest = {'schema_version': 1, 'cut': s.RUN, 'author': '/root', 'frozen_at': s.utc(),
    'source_root': str(F), 'candidate_root': str(Q), 'runtime_root': str(R),
    'parent_manifest': inputs['parent_manifest'], 'parent_review': inputs['parent_review'],
    'payload_count': 295, 'payloads': rows, 'author_scope': scope,
    'eligible_application_paths': [product, 'native/windows_broker/isolated_worker.rs',
        'tests/contract/test_isolated_worker.py', test, scope[2]],
    'source_inputs': s.reference(R / 'SOURCE-INPUTS.json'),
    'qualification': s.reference(R / 'focused-r3/RESULT.json'), 'self_review': s.reference(R / 'SELF-REVIEW.json'),
    'conservation': s.reference(R / 'CONSERVATION.json'), 'prior_failures': s.reference(R / 'PRIOR-FAILURES.json'),
    'LOC': measures, 'tests': {'unique_methods': 22, 'new_methods': 15, 'unchanged_shape_methods': 7,
        'failures': 0, 'errors': 0, 'skips': 0, 'native_process_token_read': True,
        'full_parent_cohort_run': False, 'profile_operations': [], 'worker_launches': []},
    'review_support': {name: s.ordinary(R / name) for name in ('run_diagnostics.py', 'freeze_candidate.py')},
    'status': 'REJECTED_TOKEN_DIAGNOSTIC_COMPONENT_AWAITING_DISTINCT_REVIEW',
    'Source_published': False, 'positive_isolation_qualified': False, 'activation_ready': False,
    'publication_rule': 'Join only the five exact worker application paths after distinct component review and required integration verification. The remaining old candidate Source files are byte-exact reuse, not overwrite authority.'}
s.write_new(Q / 'TRANSFER-MANIFEST.json', manifest)
s.complete('implement', {'manifest': s.reference(Q / 'TRANSFER-MANIFEST.json'),
    'qualification': manifest['qualification'], 'self_review': manifest['self_review'],
    'LOC': measures, 'Source_application': False, 'positive_isolation_qualified': False},
    [{'command': str(s.PY) + ' -B -X utf8 ' + str(R / 'run_diagnostics.py') + ' focused-r3', 'exit_status': 0}],
    [('22_unique_methods_pass_no_failures_errors_or_skips', True),
     ('Original_qualification_AST_and_original_tests_Rust_exact', True),
     ('Partial_measured_zero_unknown_distinction_and_exact_primary_cleanup_verified', True),
     ('Current_process_native_token_read_retired_no_profile_or_worker_launch', True),
     ('Source290_E33601_and_candidate295_conserved_prior_failures_retained', True)])
local = json.loads((R / 'implement.json').read_text())
stored = json.loads((R / s.RUN / 'receipts/implement.json').read_text())
assert len(local) == 12 and set(stored) == set(local) | {'git_baseline', 'observed_git', 'receipt_hash'}
typed = lambda item: json.dumps(item, sort_keys=True, separators=(',', ':'), allow_nan=False)
assert typed(local) == typed({name: stored[name] for name in local})
sys.path.insert(0, 'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_receipts import sha256_json
assert sha256_json({key: value for key, value in stored.items() if key != 'receipt_hash'}) == stored['receipt_hash']
state = json.loads((R / s.RUN / 'state.json').read_text())
claims = json.loads((R / s.RUN / 'claims.json').read_text())
assert state['sequence'] == 7 and claims == {}
assert state['nodes']['implement']['state'] == 'SUCCEEDED' and state['nodes']['review']['state'] == 'READY'
s.write_new(R / 'AUTHOR-READBACK.json', {'at': s.utc(), 'manifest': s.reference(Q / 'TRANSFER-MANIFEST.json'),
    'local': s.reference(R / 'implement.json'), 'persisted': s.reference(R / s.RUN / 'receipts/implement.json'),
    'strict_projection_equal': True, 'persisted_fingerprint': stored['receipt_hash'], 'state': state, 'claims': claims})
s.write_new(R / 'AUTHOR-SEAL.json', {'at': s.utc(), 'manifest': s.reference(Q / 'TRANSFER-MANIFEST.json'),
    'implement': s.reference(R / 'implement.json'), 'readback': s.reference(R / 'AUTHOR-READBACK.json'),
    'candidate_immutable': True, 'claim_released': True, 'distinct_review_required': True, 'Source_application': False})
print(json.dumps({'manifest': s.reference(Q / 'TRANSFER-MANIFEST.json'), 'implement': s.reference(R / 'implement.json'),
    'readback': s.reference(R / 'AUTHOR-READBACK.json'), 'seal': s.reference(R / 'AUTHOR-SEAL.json'), 'LOC': measures}), flush=True)
