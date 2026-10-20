"""Freeze a minimally corrected successor; preserve rejected parent evidence."""
import ast
from collections import Counter
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

R = Path(__file__).resolve().parent
F, RUN = R.parents[2], 'gd3-20261014'
Q, BASE = F / '.agents' / RUN, F / '.agents/gd1-20261014'
IR = F / '.agents/runtime/gd1-20261014/independent-review'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
read = lambda path: json.loads(path.read_text(encoding='utf-8'))
now = lambda: datetime.now(timezone.utc).isoformat()
def save(path, data):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2, allow_nan=False); stream.write('\n')
def ref(path):
    return {'repository_relative_path': path.relative_to(F).as_posix(), 'sha256': sha(path)}
def meaningful(text):
    docs = set()
    for node in ast.walk(ast.parse(text)):
        body = getattr(node, 'body', None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            docs.update(range(body[0].lineno, body[0].end_lineno + 1))
    return [line for i, line in enumerate(text.splitlines(), 1) if line.strip() and not line.lstrip().startswith('#') and i not in docs]
def delta(left, right):
    added = removed = 0
    for tag, i, j, k, l in difflib.SequenceMatcher(None, left, right, autojunk=False).get_opcodes():
        if tag != 'equal': added += l-k; removed += j-i
    return {'added': added, 'removed': removed, 'net': added-removed}

LAST = F / '.agents/gd2-20261014'
LASTR = F / '.agents/runtime/gd2-20261014'
assert sha(LAST / 'TRANSFER-MANIFEST.json') == 'cd51569eedb171f822defce05a21b53ad79ca2005e51a9c0ac253564b3088d8a'
last_manifest = read(LAST / 'TRANSFER-MANIFEST.json')
last_rows = {row['relative_path']: row for row in last_manifest['payloads']}
assert len(last_rows) == 281
last_state = read(LASTR / 'gd2-20261014/state.json')
assert last_state['nodes']['review']['state'] == 'FAILED' and last_state['sequence'] == 9
assert read(LASTR / 'gd2-20261014/claims.json') == {}
last_review = read(LASTR / 'independent-review/review.json')
assert sha(LASTR / 'independent-review/review.json') == 'd11ea79b07de61f24587a5b907faa098d9fa779575c8dc409dc8dda827f88653'
assert sha(LASTR / 'independent-review/actual-review-readback.json') == '32a74f80d14ed459ad5fdf62bbed5d4024e60b88442ce9951b73ec8eaa33fc9d'
assert sha(LASTR / 'independent-review/SCOPE-SEAL.json') == '92bba25dafd9847b3253413a859e789a221740450ab6620b3c2a2e810932c247'
assert last_review['decision'] == 'rejected' and last_review['exit_status'] == 1

assert sha(BASE / 'TRANSFER-MANIFEST.json') == '3f64c0dca1637ef58d6eb5bd2c64809d9af48c2c1fb691f6d558b15047cbf9b3'
parent = read(BASE / 'TRANSFER-MANIFEST.json')
assert sha(IR / 'review.json') == '9062c96d0e42de8eca84dbf22aeac67dd7c0d4e1df20514fa5e17e4564f45034'
assert sha(IR / 'actual-review-readback.json') == 'f153af188b249a9487dd7998998866026cd3043ed3214ecbaa493ed34daddf59'
assert sha(IR / 'SCOPE-SEAL.json') == '2c325b7006dd9d2eda47023da965e947718f1627162c92636b77ad74f8f7f801'
failed = read(IR / 'actual-review-readback.json')
assert failed['actual_review_state'] == 'FAILED' and failed['sequence'] == 9 and failed['claims'] == {}
assert read(IR / 'review.json')['exit_status'] == 1
claim = read(R / RUN / 'claims.json')['implement']
assert claim['executor_id'] == '/root' and claim['workspace'] == str(Q)
allowed = {'src/ceta/resource/diagnostics.py', 'contracts/PROCESS_DIAGNOSTICS_V1.md',
           'tests/contract/test_process_observation_timing.py', 'tests/contract/test_process_observation_validation.py'}
before = {row['relative_path']: row['active_before_sha256'] for row in parent['payloads']}
before['tests/contract/test_process_observation_validation.py'] = None
assert sum(value is not None for value in before.values()) == 279
for row in parent['payloads']:
    relative = row['relative_path']
    assert sha(BASE / relative) == row['candidate_sha256']
    assert sha(R / 'originals' / relative) == last_rows[relative]['candidate_sha256'] == sha(LAST / relative)
    assert (sha(F / relative) if (F / relative).is_file() else None) == row['active_before_sha256']
    if relative not in allowed: assert sha(Q / relative) == row['candidate_sha256']
assert not (F / 'tests/contract/test_process_observation_validation.py').exists()
for binding in parent['input_specification_bindings']:
    assert sha(Path(binding['path'])) == binding['sha256']
oracle = (IR / 'hostile_timing_probes.py').read_text(encoding='utf-8')
old_class = next(node for node in ast.parse(oracle).body if isinstance(node, ast.ClassDef) and node.name == 'IndependentTimingBoundaryTests')
new_test = (Q / 'tests/contract/test_process_observation_validation.py').read_text(encoding='utf-8')
classes = [node for node in ast.parse(new_test).body if isinstance(node, ast.ClassDef)]
assert ast.dump(classes[0], include_attributes=False) == ast.dump(old_class, include_attributes=False)
assert [sum(isinstance(item, ast.FunctionDef) and item.name.startswith('test_') for item in node.body) for node in classes] == [7, 6]
assert sha(Q / 'tests/contract/test_process_observation_timing.py') == sha(BASE / 'tests/contract/test_process_observation_timing.py')
final = read(R / 'final-connected-r4.json')
assert final['successful'] and final['tests_run'] == 327 and final['failures'] == final['errors'] == final['skipped'] == 0
ids = [row['id'] for row in final['cases']]
assert len(set(ids)) == len(ids) == 327 and all(row['status'] == 'PASS' for row in final['cases'])
raw_ids = re.findall(r'^test_[^\n]+\(([^)]+)\) \.\.\. ok\s*$', (R / 'final-connected-r4.txt').read_text(), re.M)
assert set(raw_ids) == set(ids) and len(raw_ids) == 327
counts = dict(Counter(name.split('.')[0] for name in ids))
assert counts == {'test_process_observation_timing': 32, 'test_process_observation_validation': 13,
                  'test_process_diagnostics': 47, 'test_resource_management': 95,
                  'test_hardware_observation': 52, 'test_workload_admission': 71,
                  'test_temporal': 14, 'test_source_coverage': 3}
assert final['source_before_sha256'] == final['source_after_sha256']
assert all(sha(Q / path) == value for path, value in final['source_after_sha256'].items())
assert final['imports'] and all(Path(path).is_relative_to(Q / 'src') for path in final['imports'].values())
historical = read(LASTR / 'hostile-baseline-r1.json')
assert historical['tests_run'] == 33 and historical['failures'] == 1 and historical['errors'] == 0
assert historical['source_before_sha256']['src/ceta/resource/diagnostics.py'] == parent['payloads'][next(i for i,row in enumerate(parent['payloads']) if row['relative_path'] == 'src/ceta/resource/diagnostics.py')]['candidate_sha256']
(R / 'diffs').mkdir(exist_ok=False)
rows = []
for relative in sorted(before):
    target = Q / relative
    active = F / relative
    old = active.read_bytes() if before[relative] is not None else b''
    current = target.read_bytes()
    changed = old != current
    assert not changed or relative in allowed
    row = {'relative_path': relative, 'active_target_relative_to_repository': relative,
           'action': ('EXTEND' if before[relative] is not None else 'CREATE') if changed else 'REUSE',
           'kind': 'functional_source' if relative.startswith('src/') else 'test_source' if relative.startswith('tests/') and relative.endswith('.py') else 'specification_or_tool_dependency',
           'active_before_sha256': before[relative], 'candidate_sha256': sha(target), 'bytes': len(current),
           'before_image': next((item['before_image'] for item in parent['payloads'] if item['relative_path'] == relative), None)}
    if changed:
        left, right = old.decode('utf-8-sig'), current.decode('utf-8-sig')
        diff = R / 'diffs' / (relative.replace('/', '__') + '.diff')
        with diff.open('x', encoding='utf-8') as stream:
            stream.write(''.join(difflib.unified_diff(left.splitlines(keepends=True), right.splitlines(keepends=True), fromfile='active/' + relative, tofile='GD3/' + relative)))
        row.update(diff=ref(diff), physical_LOC=delta(left.splitlines(), right.splitlines()),
                   meaningful_LOC=delta(meaningful(left), meaningful(right)) if relative.endswith('.py') else delta(left.splitlines(), right.splitlines()))
        if relative.endswith('.py'): compile(right, str(target), 'exec')
    rows.append(row)
assert len(rows) == 281 and sum(row['action'] == 'REUSE' for row in rows) == 277
assert {row['relative_path'] for row in rows if row['action'] != 'REUSE'} == allowed
root_delta = delta(meaningful((BASE / 'src/ceta/resource/diagnostics.py').read_text()), meaningful((Q / 'src/ceta/resource/diagnostics.py').read_text()))
assert root_delta == {'added': 3, 'removed': 0, 'net': 3}
new_test_lines = len(meaningful(ast.get_source_segment(new_test, classes[1]))) + 5
review = {'reviewed_at': now(), 'author': '/root', 'parent_rejected': ref(IR / 'review.json'),
          'parent_actual_failed_readback': ref(IR / 'actual-review-readback.json'), 'parent_scope_seal': ref(IR / 'SCOPE-SEAL.json'),
          'fault': ref(IR / 'nested-shape-candidate.json'), 'baseline_fault': ref(IR / 'nested-shape-baseline.json'),
          'minimal_successor_source_LOC': {'added': 0, 'removed': 0, 'net': 0}, 'nested_validation_repair_LOC_from_GD1': root_delta, 'new_test_meaningful_LOC': new_test_lines, 'newly_authored_source_and_tests_this_successor': 0,
          'seven_original_method_AST_exact': True, 'seven_reused_methods_new_LOC': 0,
          'timing_file_exact_parent_bytes_new_LOC': 0, 'historical33_imported26_duplicate_case_credit': 0,
          'test_edit_correction': ref(R / 'validation-test-correction.json'), 'immediate_parent_rejection': ref(LASTR / 'independent-review/review.json'), 'immediate_parent_manifest': ref(LAST / 'TRANSFER-MANIFEST.json'), 'tests': ref(R / 'final-connected-r4.json'),
          'source_current_279_exact': True, 'reused_277_exact': True,
          'limitations': parent['pending'][-1:] + ['Nested quantities are validated before derived state, with declared synthetic malformed-port tests; no native or principal isolation breach claimed']}
save(R / 'self-review.json', review)
manifest = dict(parent, job='GD3 corrected process timing and nested validation delivery', author='/root', frozen_at=now(),
                candidate_root=str(Q), payloads=rows, application_paths=sorted(allowed), self_review=ref(R / 'self-review.json'),
                tests=ref(R / 'final-connected-r4.json'), raw_tests=ref(R / 'final-connected-r4.txt'),
                native={'clock_info': final['clock_info'], 'observations': final['native_observations']}, test_counts=counts,
                parent_rejected_manifest=ref(BASE / 'TRANSFER-MANIFEST.json'), successor_added_LOC=review['minimal_successor_source_LOC'],
                successor_new_test_LOC=0, first_integration_root_nested_test_LOC=new_test_lines, prior_failures=parent['prior_failures'] + [
                    {'classification': 'GD1_NESTED_BOOLEAN_STATE_POISONING_REJECTED', 'review': ref(IR / 'review.json'), 'fault': ref(IR / 'nested-shape-candidate.json')},
                    {'classification': 'ROOT_BASELINE33_INCLUDES26_IMPORTED_FIXTURE_METHODS_AND_ONE_REAL_FAILURE', 'receipt': ref(LASTR / 'hostile-baseline-r1.json')},
                    {'classification': 'ROOT_TWO_REUSED_MISPLACED_OBSERVATION_LINES_REMOVED_WITHOUT_FUNCTIONAL_CHANGE', 'receipt': ref(R / 'validation-test-correction.json')}])
save(Q / 'TRANSFER-MANIFEST.json', manifest)
sys.path.insert(0, r'T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce')
from taar.orchestration_runtime import _snapshot_workspace, _changed_files
from taar.orchestration_receipts import validate_receipt, load_receipt
snapshot = _snapshot_workspace(Q, Path('T:/'))
changed = _changed_files(claim['baseline_snapshot'], snapshot)
assert len(snapshot) == len(changed) == 282
assert all(path.startswith('00-Active/Project-AI-CETA/.agents/gd3-20261014/') for path in changed)
save(R / 'source-freeze.json', {'manifest': ref(Q / 'TRANSFER-MANIFEST.json'), 'snapshot': snapshot,
                              'current_source': {p: v for p,v in before.items() if v is not None}, 'source_unchanged': True})
command = read(R / 'final-connected-r4-command.json')
receipt = {'schema_version': 1, 'run_id': RUN, 'node_id': 'implement', 'executor_id': '/root',
           'started_at': claim['claimed_at'], 'finished_at': now(), 'input_hash': claim['input_hash'], 'changed_files': changed,
           'result': {'status': 'FROZEN_CANDIDATE_REQUIRING_DISTINCT_REVIEW', 'manifest': ref(Q / 'TRANSFER-MANIFEST.json'),
                      'self_review': ref(R / 'self-review.json'), 'source_freeze': ref(R / 'source-freeze.json'),
                      'tests': ref(R / 'final-connected-r4.json'), 'tests_run': 327, 'failures': 0, 'errors': 0, 'skips': 0,
                      'new_source_LOC_this_successor': {'added': 0, 'removed': 0, 'net': 0}, 'new_test_LOC_this_successor': 0, 'first_integration_root_nested_test_LOC': new_test_lines,
                      'reused_method_credit': 0, 'active_source_application': False, 'independent_acceptance': False,
                      'command_evidence': ref(R / 'final-connected-r4-command.json')},
           'commands': [{'command': subprocess.list2cmdline(command['command']), 'exit_status': command['exit_status']},
                        {'command': 'Own E3 Python -B freeze_candidate.py: exact rejected parent, current279, candidate281, raw327 IDs and installed validator', 'exit_status': 0}],
           'validations': [{'name': name, 'passed': True} for name in ('exact_actual_rejected_parent_and_scope_release', 'current279_and_reused277_unchanged', 'original7_AST_and32_timing_test_bytes_exact', '327_unique_zero_skip_methods_join_raw_log', 'all5_nested_quantities_before_any_counter_adoption')], 'exit_status': 0}
kwargs = {'run_id': RUN, 'node_id': 'implement', 'executor_id': '/root', 'input_hash': claim['input_hash'],
          'claimed_at': claim['claimed_at'], 'node': read(R / RUN / 'graph.json')['graph']['nodes']['implement']}
validate_receipt(receipt, **kwargs)
save(R / 'implement.json', receipt)
validate_receipt(load_receipt(R / 'implement.json'), **kwargs)
print(json.dumps({'manifest': ref(Q / 'TRANSFER-MANIFEST.json'), 'implement': ref(R / 'implement.json'), 'source_delta': root_delta, 'new_test_meaningful_LOC': new_test_lines, 'tests': 327}), flush=True)
