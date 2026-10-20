"""One ER2 strict review completion after actual finite independent results."""
import ast
import copy
import difflib
import io
import json
from pathlib import Path
import sys
import tokenize
from review_support import F, P, Q, R, V, RUN, ACTOR, MANIFEST, read, conservation, inventory, invoke, s


def meaningful(raw):
    text = raw.decode('utf-8')
    docs = set()
    for node in ast.walk(ast.parse(text)):
        body = getattr(node, 'body', None)
        if (isinstance(body, list) and body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant) and type(body[0].value.value) is str):
            docs.update(range(body[0].lineno, body[0].end_lineno + 1))
    active = set()
    ignored = {tokenize.COMMENT, tokenize.ENCODING, tokenize.INDENT, tokenize.DEDENT,
        tokenize.NL, tokenize.NEWLINE, tokenize.ENDMARKER}
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type not in ignored and token.string.strip():
            active.update(range(token.start[0], token.end[0] + 1))
    return text.splitlines(), active - docs


def main():
    assert len(sys.argv) == 1
    before = read(V / 'BEFORE.json')
    assert conservation() == before
    preparation = read(V / 'PREPARATION.json')
    for name, pin in preparation['helpers'].items(): assert s.sha(V / name) == pin
    proof = read(V / 'connected-r1/RESULT.json')
    launch = read(V / 'LAUNCH-RESULT.json')
    assert all(type(proof[key]) is int and proof[key] == 0 for key in ('failures', 'errors', 'skips', 'exit_status'))
    assert proof['tests_run'] == len(proof['expected_ids']) == len(set(proof['expected_ids'])) == 108
    assert proof['expected_ids'] == proof['executed_ids'] == proof['stopped_ids']
    assert proof['expected_ids'][:106] == read(R / 'connected-r1/RESULT.json')['expected_ids']
    assert proof['remaining_threads'] == [] and proof['source_parent_candidate_environment_conserved'] is True
    physical = proof['physical_resources']
    assert physical['sqlite'] and physical['owned_resources_closed'] is True and physical['remaining_resources'] == []
    assert all(row['physical_closed_probe'] for row in physical['sqlite'])
    native = proof['native_fixture_captures']
    native_ids = [identifier for identifier in proof['executed_ids'] if identifier.startswith(
        ('test_editor_recovery.NativeEditorRecoveryTests.', 'test_editor_recovery.QtEditorRecoveryTests.'))]
    assert len(native_ids) == 12 and {row['test_id'] for row in native} == set(native_ids)
    assert all(row['retired'] and row['observed_live_at_return'] for row in native)
    assert all(all(row['native_designations'].values()) and type(row['observed_exit_code']) is int for row in native)
    assert len({(row['pid'], row['creation_time']) for row in native}) == len(native)
    record = launch['record']
    assert launch['exit_status'] == record['child_exit'] == 0 and launch['primary_error'] is None
    assert record['primary_error'] is record['retirement_error'] is None
    assert all(record['native_owner_after'].values())
    assert record['child_result'] == s.reference(V / 'connected-r1/RESULT.json')
    fixture = Path(preparation['fixture_root'])
    fixture_files = inventory(fixture)
    assert all(Path(row['path']).is_relative_to(fixture) for row in fixture_files.values())
    s.write_new(V / 'FIXTURE-READBACK.json', {'at': s.utc(), 'root': str(fixture),
        'created_identity': proof['fixture_native_identity'], 'files': fixture_files,
        'native_lifetimes': native, 'all_observed_connections_closed': True,
        'preexisting_fixtures_modified': False, 'fixture_LOC_credit': 0})
    manifest = read(Q / 'TRANSFER-MANIFEST.json')
    selected = set(manifest['eligible_application_paths'])
    assert selected == {'src/ceta/application/task_operator.py', 'tests/contract/test_editor_retention_queue.py',
        'contracts/EDITOR_RECOVERY_V1.md'}
    assert (manifest['REUSE'], manifest['EXTEND'], manifest['CREATE']) == (292, 2, 1)
    for name, row in manifest['payloads'].items():
        if name not in selected: assert row['candidate']['sha256'] == row['parent']['sha256']
    source_name = 'src/ceta/application/task_operator.py'
    old_tree, new_tree = ast.parse((P / source_name).read_bytes()), ast.parse((Q / source_name).read_bytes())
    restored = copy.deepcopy(new_tree)
    call = next(node for node in ast.walk(restored) if isinstance(node, ast.Call) and node.lineno == 947)
    call.keywords = [item for item in call.keywords if item.arg != 'editor_next_attempt_at']
    assert ast.dump(restored, include_attributes=False) == ast.dump(old_tree, include_attributes=False)
    old, old_lines = meaningful((P / source_name).read_bytes())
    new, new_lines = meaningful((Q / source_name).read_bytes())
    added = removed = 0
    for tag, a, b, c, d in difflib.SequenceMatcher(a=old, b=new, autojunk=False).get_opcodes():
        if tag != 'equal':
            removed += sum(n + 1 in old_lines for n in range(a, b))
            added += sum(n + 1 in new_lines for n in range(c, d))
    tests_added = len(meaningful((Q / 'tests/contract/test_editor_retention_queue.py').read_bytes())[1])
    assert (added, removed, tests_added) == (1, 1, 100)
    original_files = [name for name in read(R / 'SOURCE-INPUTS.json')['parent294'] if name.startswith('tests/')]
    assert len(original_files) == 83 and all((P / name).read_bytes() == (Q / name).read_bytes() for name in original_files)

    sys.path.insert(0, 'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
    from taar.orchestration_receipts import validate_receipt, load_receipt
    from taar.orchestration_runtime import _snapshot_workspace, _changed_files, _artifact_hash
    from taar.orchestration_persistence import sha256_json
    graph = read(R / RUN / 'graph.json')['graph']
    state = read(R / RUN / 'state.json')
    claim = read(R / RUN / 'claims.json')['review']
    assert state['sequence'] == 8 and state['nodes']['review']['state'] == 'RUNNING'
    assert claim['executor_id'] == ACTOR and Path(claim['workspace']) == Q and claim['effective_write_scope'] == []
    assert graph['policy']['prohibit_self_review'] is True
    assert state['nodes']['implement']['executor_id'] == '/root' and state['nodes']['implement']['state'] == 'SUCCEEDED'
    author, persisted_author = read(R / 'implement.json'), read(R / RUN / 'receipts/implement.json')
    assert len(author) == 12 and len(persisted_author) == 15
    normalized = validate_receipt(author, run_id=RUN, node_id='implement', executor_id='/root',
        input_hash=author['input_hash'], claimed_at=author['started_at'], node=graph['nodes']['implement'])
    normalized.pop('receipt_hash')
    author_body = dict(persisted_author)
    author_fingerprint = author_body.pop('receipt_hash')
    assert author_fingerprint == sha256_json(author_body) == state['nodes']['implement']['receipt_hash']
    assert {key: value for key, value in author_body.items() if key not in ('observed_git', 'git_baseline')} == normalized
    assert read(R / RUN / 'results/implement.json') == dict(node_id='implement', result=author['result'], receipt_hash=author_fingerprint)
    snapshot = _snapshot_workspace(Q, Path('T:/'))
    assert state['nodes']['implement']['artifact_hash'] == _artifact_hash(snapshot, author['changed_files'])
    assert _changed_files(claim['baseline_snapshot'], snapshot) == []
    report = {'at': s.utc(), 'reviewer': ACTOR, 'author': '/root', 'decision': 'approved',
        'manifest_sha256': MANIFEST, 'candidate_root': str(Q), 'selected_paths': sorted(selected),
        'scope': 'Distinct ER2 acknowledged-retain handoff component review', 'findings': [],
        'independent_unique_methods_passed': 108, 'unchanged_original_methods': 101,
        'author_new_methods': 5, 'reviewer_finite_methods': 2, 'executed_ids': proof['executed_ids'],
        'independent_result': s.reference(V / 'connected-r1/RESULT.json'),
        'closed_outer_job': s.reference(V / 'LAUNCH-RESULT.json'),
        'fixture_readback': s.reference(V / 'FIXTURE-READBACK.json'),
        'verified_source_delta': 'Only editor_next_attempt_at=0.0 is added to the existing acknowledged-old-retain/newer-complete-capture branch; deleting that keyword restores whole parent module AST.',
        'verified_behavior': ['Acknowledged older capture immediately hands off to the latest complete serialized capture.',
            'Original frozen-clock line904 failure and independent held-ack reproduction are preserved; all108 exact finite methods pass after repair.',
            'Ordinary150ms typing debounce remains exercised and unchanged.',
            'Acknowledged revision supplies successor CAS; old durable snapshot is not reported as current capture retention.',
            'Repeated polls retain the same pending owner and cannot dispatch a duplicate successor.',
            'Denied or lost old response, unserialized capture and Stop retain original denial/reconciliation guards.',
            'Canonical writer, authorization and all public signatures remain byte/AST unchanged outside the one keyword.'],
        'custody': {'actual_returned_SQLite_connections': len(physical['sqlite']),
            'all_physically_probed_closed': True, 'ordinary_native_fixture_cases': 12,
            'ordinary_native_lifetimes': len(native), 'all_captured_native_owners_retired': True,
            'remaining_threads': [], 'remaining_resources': [], 'outer_native_owner': record['native_owner'],
            'generic_unobserved_owner_limit': proof['custody_limits']},
        'component_LOC': {'source_added': added, 'source_removed': removed, 'author_test_added': tests_added,
            'borrowed_original_tests_new_credit': 0, 'copied_parent_authorship_credit': 0,
            'reviewer_product_LOC': 0, 'integrated_LOC': 0},
        'author_binding': {'raw12': s.reference(R / 'implement.json'),
            'persisted15': s.reference(R / RUN / 'receipts/implement.json'), 'official_fingerprint': author_fingerprint,
            'write_scoped_artifact_hash': state['nodes']['implement']['artifact_hash']},
        'preserved_failed_lineage': {'deterministic_before': manifest['deterministic_before'],
            'author_wrapper_preparation': manifest['prior_preparation_failure'],
            'parent_failed_complete_gate': manifest['parent_complete_gate'],
            'JS3_validate_state': 'FAILED11', 'terminal_retry': False},
        'conservation': s.reference(V / 'BEFORE.json'), 'preparation': s.reference(V / 'PREPARATION.json'),
        'limits': ['Component108 only; a fresh joined/full/destination acceptance remains required.',
            'Five new and two reviewer methods use controlled typing clock and delivery/identity/Stop fixtures over real Qt/SQLite.',
            'Twelve original methods additionally use actual newly owned disposable Windows service/client processes; these establish no native effect approval.',
            'Internal child SQLite handles are not individually wrapped; actual captured native owner/job retirement and same-process returned connections are reported separately.',
            'No host profile, Hello forwarding, CPU policy effect, active CETA instance, Source publication or product acceptance occurred.'],
        'Source_publication': False, 'full_gate_complete': False, 'Source_accepted': False}
    s.write_new(V / 'REPORT.json', report)
    receipt = {'schema_version': 1, 'run_id': RUN, 'node_id': 'review', 'executor_id': ACTOR,
        'started_at': claim['claimed_at'], 'finished_at': s.utc(), 'input_hash': claim['input_hash'],
        'changed_files': [], 'result': {'manifest_sha256': MANIFEST, 'report': s.reference(V / 'REPORT.json'),
            'independent_result': s.reference(V / 'connected-r1/RESULT.json'),
            'closed_outer_job': s.reference(V / 'LAUNCH-RESULT.json'), 'independent_unique_methods_passed': 108,
            'original106_preserved': True, 'source_added': 1, 'source_removed': 1, 'author_test_added': 100,
            'integrated_LOC': 0, 'Source_publication': False, 'full_gate_complete': False},
        'commands': [{'command': str(s.PY) + ' -B -X utf8 ' + str(V / name), 'exit_status': 0}
            for name in ('prepare_review.py', 'launch_review.py')],
        'validations': [{'name': name, 'passed': True} for name in (
            'Exact106 original plus2 independent methods pass with no failure/error/skip and unchanged original methods/deadlines',
            'Complete parent AST restored by deleting only the added handoff deadline keyword; public interfaces and canonical authority unchanged',
            'Exact returned SQLite closure and captured native process/channel/job retirement independently observed',
            'Source290/parent294/candidate295/E33601/Git and author failure lineage preserved',
            'Strict12/15 actual author/result/fingerprint/write-scoped artifact validated; no full/Source acceptance inferred')],
        'exit_status': 0, 'decision': 'approved'}
    assert len(receipt) == 13 and all(row['exit_status'] == 0 for row in receipt['commands'])
    kwargs = dict(run_id=RUN, node_id='review', executor_id=ACTOR, input_hash=claim['input_hash'],
        claimed_at=claim['claimed_at'], node=graph['nodes']['review'])
    validate_receipt(receipt, **kwargs)
    s.write_new(V / 'review.json', receipt)
    validate_receipt(load_receipt(V / 'review.json'), **kwargs)
    assert read(R / RUN / 'state.json')['nodes']['review']['state'] == 'RUNNING'
    assert read(R / RUN / 'claims.json')['review'] == claim
    invoke(['node', 'complete', RUN, 'review', str(V / 'review.json')], 'review-complete')
    final, stored = read(R / RUN / 'state.json'), read(R / RUN / 'receipts/review.json')
    assert len(stored) == 16 and {key: stored[key] for key in receipt} == receipt
    stored_body = dict(stored)
    fingerprint = stored_body.pop('receipt_hash')
    assert fingerprint == sha256_json(stored_body) == final['nodes']['review']['receipt_hash']
    assert read(R / RUN / 'results/review.json') == dict(node_id='review', result=receipt['result'], receipt_hash=fingerprint)
    artifact = sha256_json(dict(input_hash=claim['input_hash'], result=receipt['result']))
    assert final['nodes']['review']['artifact_hash'] == artifact
    assert final['nodes']['review']['state'] == 'SUCCEEDED' and final['nodes']['review']['decision'] == 'approved'
    assert final['sequence'] == 9 and read(R / RUN / 'claims.json') == {}
    assert conservation() == before
    s.write_new(V / 'REVIEW-READBACK.json', {'at': s.utc(), 'reviewer': ACTOR, 'review_state': 'SUCCEEDED',
        'sequence': 9, 'claims': {}, 'manifest_sha256': MANIFEST,
        'local13': s.reference(V / 'review.json'), 'persisted16': s.reference(R / RUN / 'receipts/review.json'),
        'official_fingerprint': fingerprint, 'artifact_hash': artifact,
        'result_envelope': s.reference(R / RUN / 'results/review.json'),
        'independent_methods': 108, 'report': s.reference(V / 'REPORT.json'),
        'Source_publication': False, 'full_gate_complete': False, 'Source_accepted': False})
    members = inventory(V)
    s.write_new(V / 'REVIEW-SEAL.json', {'at': s.utc(), 'reviewer': ACTOR, 'scope_closed': True,
        'review_state': 'SUCCEEDED', 'sequence': 9, 'claims': {}, 'members': members,
        'fixture_readback': s.reference(V / 'FIXTURE-READBACK.json'),
        'Source_publication': False, 'full_gate_complete': False, 'Source_accepted': False})
    print(json.dumps({'state': 'SUCCEEDED', 'sequence': 9, 'claims': {}, 'methods': 108,
        'review': s.reference(V / 'review.json'), 'report': s.reference(V / 'REPORT.json'),
        'readback': s.reference(V / 'REVIEW-READBACK.json'), 'seal': s.reference(V / 'REVIEW-SEAL.json'),
        'official_fingerprint': fingerprint, 'artifact_hash': artifact}), flush=True)


if __name__ == '__main__': main()
