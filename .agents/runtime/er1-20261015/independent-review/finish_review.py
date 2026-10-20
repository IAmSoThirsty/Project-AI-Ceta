"""Exact ER1 static/receipt checks, bounded approval, installed completion/readback."""
import ast
import difflib
import json
import sys
from pathlib import Path
from review_support import F, Q, P, R, V, RUN, ACTOR, MANIFEST, s, read, conservation, invoke, function


def indexed_nodes(path):
    result = {}
    for index, node in enumerate(ast.parse(path.read_bytes()).body):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            key = ('declaration', node.name)
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            key = ('assignment', node.targets[0].id)
        elif isinstance(node, ast.Import):
            key = ('import', tuple((item.name, item.asname) for item in node.names))
        elif isinstance(node, ast.ImportFrom):
            key = ('from', node.module, tuple((item.name, item.asname) for item in node.names))
        else:
            key = ('other', index)
        assert key not in result
        result[key] = ast.dump(node, include_attributes=False)
    return result


def main():
    assert len(sys.argv) == 1
    baseline = read(V / 'CONSERVATION-BEFORE.json')
    assert conservation() == baseline
    manifest = read(Q / 'TRANSFER-MANIFEST.json')
    selected = set(manifest['eligible_application_paths'])
    assert selected == {'contracts/EDITOR_RECOVERY_V1.md', 'src/ceta/contracts/editor_recovery.py',
        'src/ceta/contracts/task_drafts.py', 'src/ceta/contracts/wire.py', 'tests/contract/test_wire_scanning.py'}
    counts = {kind: sum(row['classification'] == kind for row in manifest['payloads'].values())
        for kind in ('REUSE', 'EXTEND', 'CREATE')}
    assert counts == {'REUSE': 288, 'EXTEND': 4, 'CREATE': 1}
    allowed = {
        'src/ceta/contracts/wire.py': ({'_preflight'}, {'_JSON_STRUCTURAL'}, False),
        'src/ceta/contracts/editor_recovery.py': ({'_hex_bytes'}, {'_LOWER_HEX'}, True),
        'src/ceta/contracts/task_drafts.py': ({'text_value', 'decode_command'}, {'_LOWER_HEX'}, True)}
    static = {}
    for name, (declarations, assignments, re_import) in allowed.items():
        previous, current = indexed_nodes(P / name), indexed_nodes(Q / name)
        changed = {key for key in previous if previous[key] != current.get(key)}
        added = set(current) - set(previous)
        assert changed == {('declaration', value) for value in declarations}
        expected_added = {('assignment', value) for value in assignments}
        if re_import:
            expected_added.add(('import', (('re', None),)))
        assert added == expected_added and not (set(previous) - set(current))
        for function_name in declarations:
            assert ast.dump(function(P / name, function_name).args, include_attributes=False) == ast.dump(
                function(Q / name, function_name).args, include_attributes=False)
        static[name] = {'parent': s.ordinary(P / name), 'candidate': s.ordinary(Q / name),
            'changed_declarations': sorted(declarations), 'added_regex_assignments': sorted(assignments),
            'all_other_declarations_and_constants_AST_exact': True,
            'declaration_lines': {value: function(Q / name, value).lineno for value in declarations}}
    for name, row in manifest['payloads'].items():
        if name not in selected:
            assert row['candidate']['sha256'] == row['parent']['sha256']
        if name.startswith('tests/') and row['parent'] is not None:
            assert (Q / name).read_bytes() == (P / name).read_bytes()
    new_tests = Q / 'tests/contract/test_wire_scanning.py'
    prior_oracle = function(P / 'src/ceta/contracts/wire.py', '_preflight')
    copied_oracle = function(new_tests, 'retained_preflight')
    assert ast.dump(ast.Module(body=copied_oracle.body[1:], type_ignores=[]), include_attributes=False) == ast.dump(
        ast.Module(body=prior_oracle.body, type_ignores=[]), include_attributes=False)
    events = [json.loads(line) for line in (R / RUN / 'events.jsonl').read_text().splitlines()]
    implement_events = [row for row in events if row['node_id'] == 'implement']
    assert len([row for row in implement_events if row['event_type'] == 'node_claimed']) == 1
    assert not any(row['new_state'] == 'FAILED' for row in implement_events)
    failure = read(R / 'BOOTSTRAP-COPY-FAILURE-R1.json')
    assert failure['exit_status'] == 1 and "unexpected keyword argument 'missing_ok'" in failure['message']
    profiles = [read(R / name) for name in ('CODEC-PROFILE-R1.json', 'CODEC-PROFILE-AFTER-R1.json')]
    assert profiles[0]['request'] == profiles[1]['request']
    assert profiles[0]['profiling_overhead_included'] is True and profiles[1]['profiling_overhead_included'] is True
    replay = read(V / 'REPLAY-READBACK.json')
    hostile = read(V / 'HOSTILE-R1.json')
    assert replay['tests_run'] == 85 and hostile['tests_run'] == 7
    assert all(proof[field] == 0 for proof in (replay, hostile) for field in ('failures', 'errors', 'skips'))
    original_ids = read(V / 'pure-independent-r1/RESULT.json')['executed_ids']
    assert len(set(original_ids) | set(hostile['executed_ids'])) == 92
    sys.path.insert(0, 'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
    from taar.orchestration_receipts import validate_receipt, load_receipt
    from taar.orchestration_runtime import _snapshot_workspace, _changed_files, _artifact_hash
    from taar.orchestration_persistence import sha256_json
    graph = read(R / RUN / 'graph.json')['graph']
    state = read(R / RUN / 'state.json')
    claims = read(R / RUN / 'claims.json')
    claim = claims['review']
    assert claim['executor_id'] == ACTOR and state['nodes']['review']['state'] == 'RUNNING'
    assert graph['policy']['prohibit_self_review'] is True and state['nodes']['implement']['executor_id'] == '/root'
    raw_implement = read(R / 'implement.json')
    persisted_implement = read(R / RUN / 'receipts/implement.json')
    assert len(raw_implement) == 12 and len(persisted_implement) == 15
    normalized_implement = validate_receipt(raw_implement, run_id=RUN, node_id='implement', executor_id='/root',
        input_hash=raw_implement['input_hash'], claimed_at=raw_implement['started_at'], node=graph['nodes']['implement'])
    normalized_implement.pop('receipt_hash')
    persisted_body = dict(persisted_implement)
    stored_implement_fingerprint = persisted_body.pop('receipt_hash')
    assert sha256_json(persisted_body) == stored_implement_fingerprint == state['nodes']['implement']['receipt_hash']
    assert {key: value for key, value in persisted_body.items() if key not in ('observed_git', 'git_baseline')} == normalized_implement
    snapshot = _snapshot_workspace(Q, Path('T:/'))
    assert _changed_files(claim['baseline_snapshot'], snapshot) == []
    assert _artifact_hash(snapshot, raw_implement['changed_files']) == state['nodes']['implement']['artifact_hash']
    report = {'at': s.utc(), 'reviewer': ACTOR, 'author': '/root', 'decision': 'approved',
        'scope': 'ER1 five-path pure-contract performance/semantic component, not the failed JS2 full gate',
        'manifest_sha256': MANIFEST, 'selected_paths': sorted(selected), 'classifications': counts,
        'static_source_review': static, 'original_parent_tests_byte_exact': True,
        'copied_original_scanner_body_AST_exact': True, 'public_signatures_preserved': True,
        'independent_unique_methods_passed': 92, 'original85': s.reference(V / 'REPLAY-READBACK.json'),
        'additional7': s.reference(V / 'HOSTILE-R1.json'), 'findings': [],
        'reasoning': ['The structural character regex is a fixed one-character class, with no nested quantifier or backtracking branch.',
            'Absolute escaped_at positions consume only the immediately escaped code point; skipped ordinary spans cannot move the escape to a later structural character.',
            'Strict UTF8 decoding and byte limit remain before preflight; json.loads still enforces syntax/duplicates/numbers, then original NFC/scalar/int/depth tree checks run.',
            'Hex exact-type, length and width predicates precede fullmatch; ASCII lowercase fullmatch rejects whitespace, newline, uppercase, confusables and surrogate glyphs.',
            'No schema, authority, timing, state-store, owner or public interface change is present in these three modules.',
            'Updated editor documentation matches the pre-existing bounded inline/reference/chunk constants and STAGING/RETAINED checks.'],
        'retained532455_request': hostile['retained_request_decode'],
        'author_profile_observations': {'baseline_elapsed_ns': profiles[0]['elapsed_ns'], 'baseline_calls': profiles[0]['calls'],
            'candidate_elapsed_ns': profiles[1]['elapsed_ns'], 'candidate_calls': profiles[1]['calls'],
            'profiling_overhead_included': True, 'independent_performance_benchmark': False},
        'preserved_bootstrap_failure': s.reference(R / 'BOOTSTRAP-COPY-FAILURE-R1.json'),
        'implement_claim_count': 1, 'terminal_retry_observed': False,
        'author_implement_binding': {'raw12': s.reference(R / 'implement.json'),
            'persisted15': s.reference(R / RUN / 'receipts/implement.json'),
            'official_normalized_fingerprint': stored_implement_fingerprint,
            'artifact_hash': state['nodes']['implement']['artifact_hash']},
        'conservation': s.reference(V / 'CONSERVATION-BEFORE.json'),
        'LOC': manifest['LOC'],
        'qualification_limits': ['92 passing pure methods and bounded static review qualify only this exact component.',
            'The two single author profile samples include cProfile overhead; no general speedup ratio or deadline guarantee is established.',
            'Historical fullR2 Qt timeout cause remains unresolved; prior complete JS2 validation is FAILED11 and integration BLOCKED.',
            'No journal, native worker, Qt, profile, Hello, class15 effect, installed product, complete suite or Source publication was executed here.'],
        'Source_publication': False, 'full_gate_complete': False, 'Source_accepted': False}
    s.write_new(V / 'REPORT.json', report)
    receipt = {'schema_version': 1, 'run_id': RUN, 'node_id': 'review', 'executor_id': ACTOR,
        'started_at': claim['claimed_at'], 'finished_at': s.utc(), 'input_hash': claim['input_hash'],
        'changed_files': [], 'result': {'manifest_sha256': MANIFEST, 'report': s.reference(V / 'REPORT.json'),
            'independent_unique_methods_passed': 92, 'author_implement_raw_sha256': s.sha(R / 'implement.json'),
            'author_implement_fingerprint': stored_implement_fingerprint, 'Source_publication': False,
            'full_gate_complete': False, 'prior_JS2_complete_gate': 'FAILED'},
        'commands': [
            {'command': str(s.PY) + ' -B -X utf8 ' + str(V / 'replay_original_pure.py'), 'exit_status': 0},
            {'command': str(s.PY) + ' -B -X utf8 ' + str(V / 'run_hostile.py'), 'exit_status': 0}],
        'validations': [
            {'name': 'Exact original85 and7 independent pure methods pass without skips or noncontract imports', 'passed': True},
            {'name': 'Exact five-path scope, old scanner AST, original tests and public signatures conserved', 'passed': True},
            {'name': 'Strict canonical/depth/hex semantics and exact retained request commitment preserved', 'passed': True},
            {'name': 'Source290 parent292 candidate293 E3 and sealed prior evidence conserved', 'passed': True},
            {'name': 'Author12to15 receipt and actual official fingerprint/artifact verified', 'passed': True}],
        'exit_status': 0, 'decision': 'approved'}
    assert len(receipt) == 13
    kwargs = {'run_id': RUN, 'node_id': 'review', 'executor_id': ACTOR, 'input_hash': claim['input_hash'],
        'claimed_at': claim['claimed_at'], 'node': graph['nodes']['review']}
    validate_receipt(receipt, **kwargs)
    s.write_new(V / 'review.json', receipt)
    validate_receipt(load_receipt(V / 'review.json'), **kwargs)
    response = invoke(['node', 'complete', RUN, 'review', str(V / 'review.json')], 'review-complete')
    final = read(R / RUN / 'state.json')
    persisted = read(R / RUN / 'receipts/review.json')
    envelope = read(R / RUN / 'results/review.json')
    assert len(persisted) == 16 and {key: persisted[key] for key in receipt} == receipt
    body = dict(persisted)
    fingerprint = body.pop('receipt_hash')
    assert fingerprint == sha256_json(body) == final['nodes']['review']['receipt_hash']
    assert final['nodes']['review']['artifact_hash'] == sha256_json({'input_hash': claim['input_hash'], 'result': receipt['result']})
    assert envelope == {'node_id': 'review', 'result': receipt['result'], 'receipt_hash': fingerprint}
    assert final['nodes']['review']['state'] == 'SUCCEEDED' and final['nodes']['review']['decision'] == 'approved'
    assert final['sequence'] == 9 and read(R / RUN / 'claims.json') == {}
    assert conservation() == baseline
    readback = {'at': s.utc(), 'reviewer': ACTOR, 'decision': 'approved', 'sequence': final['sequence'],
        'review_state': final['nodes']['review']['state'], 'claims': {}, 'local13': s.reference(V / 'review.json'),
        'persisted16': s.reference(R / RUN / 'receipts/review.json'), 'result_envelope': s.reference(R / RUN / 'results/review.json'),
        'official_normalized_fingerprint': fingerprint, 'artifact_hash': final['nodes']['review']['artifact_hash'],
        'report': s.reference(V / 'REPORT.json'), 'Source_publication': False, 'full_gate_complete': False}
    s.write_new(V / 'REVIEW-READBACK.json', readback)
    members = {path.name: s.ordinary(path) for path in sorted(V.iterdir()) if path.is_file()}
    for path in sorted((V / 'pure-independent-r1').iterdir()):
        if path.is_file():
            members[path.relative_to(V).as_posix()] = s.ordinary(path)
    s.write_new(V / 'REVIEW-SEAL.json', {'at': s.utc(), 'reviewer': ACTOR,
        'members': members, 'scope_closed': True, 'claims': {}, 'Source_publication': False, 'full_gate_complete': False})
    print(json.dumps({'review': s.reference(V / 'review.json'), 'report': s.reference(V / 'REPORT.json'),
        'readback': s.reference(V / 'REVIEW-READBACK.json'), 'seal': s.reference(V / 'REVIEW-SEAL.json'),
        'official_normalized_fingerprint': fingerprint, 'sequence': final['sequence'],
        'review_state': final['nodes']['review']['state'], 'claims': {}, 'methods_passed': 92}), flush=True)


if __name__ == '__main__':
    main()
