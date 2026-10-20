"""Truthful failed AC1 independent review and one installed completion."""
from ac_support import *

assert len(sys.argv) == 2 and sys.argv[1] in ('prepare', 'complete')
mode = sys.argv[1]
if mode == 'prepare':
    baseline = json.loads((D / 'initial-observation.json').read_text())
    original = json.loads((D / 'original-r1.json').read_text())
    hostile = json.loads((D / 'hostile-cleanup-r1.json').read_text())
    current = candidate_cut(); source = source_cut()
    assert current == baseline['candidate'] == original['candidate_before'] == original['candidate_after']
    assert current == hostile['candidate_before'] == hostile['candidate_after']
    assert baseline['source'] == source == original['source_before'] == original['source_after']
    assert hostile['source_before'] == hostile['source_after'] == source
    assert original['tests_run'] == 39 and original['exit_status'] == 0
    assert original['expected_executed_equal'] and len(set(original['executed_ids'])) == 39
    assert not original['failures'] and not original['errors'] and not original['skipped']
    assert hostile['tests_run'] == 3 and len(hostile['failures']) == 6 and not hostile['errors'] and not hostile['skipped']
    assert len(hostile['native_facts']) == 6
    assert all(not row['primary_identity_preserved'] and not row['caller_visible_cleanup'] for row in hostile['native_facts'])
    for row in hostile['native_facts']:
        if 'all_captured_handles_closed' in row: assert row['all_captured_handles_closed']
        if 'pending_sids_after' in row: assert row['pending_sids_after'] == []
        if 'native_closed_after_recovery' in row: assert row['native_closed_after_recovery'] == [True]
    joined_path = F / '.agents/runtime/perf1-20261014/active-application/JOINED-SOURCE.json'
    assert sha(joined_path) == '700fafa5f50f536a363700edf714e60a6d32bf1358424142a9a7b12706470f57'
    joined = json.loads(joined_path.read_text())
    joined_now = {name: ordinary(F / name) for name in joined['after_hashes']}
    differences = [{'relative_path': name, 'expected_sha256': expected,
                    'observed_sha256': joined_now[name]['sha256']}
                   for name, expected in joined['after_hashes'].items() if joined_now[name]['sha256'] != expected]
    # Source normative bytes observed before/after all tests are already exact;
    # current wider joined requirements/tools evidence is identified separately.
    write_new(D / 'final-conservation.json', {'observed_at': utc(), 'candidate': current,
        'candidate_payloads': 249, 'retained_fixture_files': 20, 'manifest_files': 1, 'total_candidate_files': len(current),
        'candidate_bytes_native_identities_membership_exact': True,
        'test_interval_source_payloads_before_after_exact': len(source),
        'source_test_interval_baseline': reference(D / 'initial-observation.json'),
        'source_current': source, 'root_joined_cut': reference(joined_path),
        'root_joined_current_payloads': joined_now, 'root_joined_differences': differences,
        'wider_joined_interval_limit': 'Root join comparison is a current observation; only the 255 source-prefix members have this review before/after interval proof',
        'environment': reference(D / 'environment-conservation.json'),
        'scope': 'Only reviewer D files/disposable fixture descendants changed; Q, Source, E3 and external roots not written'})
    findings = [
        {'id': 'AC1-F01', 'path': 'src/ceta/supervisor/isolated_worker.py', 'line': 318,
         'classification': 'blocking current task', 'severity': 'high',
         'verified': 'After actual attribute deletion the injected finalizer error replaces both original control exception identities and bypasses cleanup of three actual file/directory/job handles plus one derived SID. The empty job has no child.',
         'oracle': '__main__.FinalizationCustodyTests.test_attribute_finalization_preserves_control_and_native_cleanup',
         'repair': 'Guard attribute finalization, keep the original exception, continue independent cleanup, and expose exact pending resources with explicit retry/uncertainty semantics.'},
        {'id': 'AC1-F02', 'path': 'src/ceta/supervisor/isolated_worker.py', 'line': 184,
         'classification': 'blocking current task', 'severity': 'high',
         'verified': 'The public SID helper masks KeyboardInterrupt/SystemExit with SID-release ContractError and exposes no cleanup object while its real valid SID allocation remains pending.',
         'oracle': '__main__.FinalizationCustodyTests.test_public_sid_derivation_preserves_primary_and_pending_allocation',
         'repair': 'Keep exact unresolved SID custody accessible through the primary exception; make explicit retry perform only known still-pending operations.'},
        {'id': 'AC1-F03', 'path': 'src/ceta/supervisor/isolated_worker.py', 'line': 131,
         'classification': 'blocking current task', 'severity': 'high',
         'verified': 'A read-only token query opened a real reviewer-process query-token handle. Injected final-close failure masks KeyboardInterrupt/SystemExit and leaves that handle open without caller-visible cleanup custody.',
         'oracle': '__main__.FinalizationCustodyTests.test_token_query_preserves_primary_and_exact_open_handle_on_close_failure',
         'repair': 'Retain the exact pending token handle and preserve the primary exception while other cleanup continues.'}
    ]
    record = {'observed_at': utc(), 'author': '/root/history_preservation', 'reviewer': ACTOR,
        'decision': 'rejected', 'manifest': reference(Q / 'TRANSFER-MANIFEST.json'),
        'findings': findings, 'hostile_evidence': reference(D / 'hostile-cleanup-r1.json'),
        'hostile_raw': reference(D / 'hostile-cleanup-r1.txt'), 'hostile_code': reference(D / 'hostile_cleanup.py'),
        'original_evidence': reference(D / 'original-r1.json'), 'original_raw': reference(D / 'original-r1.txt'),
        'actual_native_recovery': 'All six probe subcases retain their exact pre-recovery resources and independently observed reviewer recovery; no unresolved reviewer handle/SID remains.',
        'threat_model': 'Current-process interruption and native cleanup failure; trusted library caller; no hostile arbitrary PID or protected host asset targeting',
        'strengths': ['39 unchanged unique original methods pass, zero skipped.',
            'No unrestricted fallback on actual restrictive CreateProcessW error 2.',
            'Actual no-profile SID derivation; bounded typed argument/handle/environment validation.',
            'Declared fixture-only DACL and low-label changes, medium canaries remain byte-exact in native setup/result receipts.',
            'Canonical trusted control lifetimes are observed exited/empty/closed.'],
        'limits': ['Fault injection follows actual native allocation and deliberately refused finalization; it is not an observed spontaneous OS failure.',
            'Positive restricted token/file/process/network/escape behavior remains NOT_EXECUTED; error 2 cause remains unestablished.',
            'No post-create restrictive-worker retirement or concurrent successful restricted-worker qualification.',
            'The attribute-deletion native API has no error return; the injected Python wrapper throws after actual deletion.',
            'Other untested allocation-to-custody interruption seams are not claimed as verified defects.',
            'No Source publication, policy activation, persistent profile, host ACL/configuration or environment changes.'],
        'independence': 'Reviewer authored no AC1 payload. Approved shared native reader, actual E3 and canonical job code are reused dependencies; reviewer support and failure oracles are distinct.',
        'count_correction': 'Frozen manifest and complete filesystem inventory contain 20 fixture files, not the 21 stated in the author chat handoff; 249 normative payloads +20 fixtures +1 manifest =270 exact members.',
        'dictionary_scope': 'Review and completion are used in the repo-defined technical receipt scope; no full-isolation or product-completion claim.',
        'primary_api_sources': [
            'https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-freesid',
            'https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-deleteprocthreadattributelist'],
        'external_reader_limit': 'First memoryapi LocalFree URL was unavailable; no claim relies on that page.',
        'conservation': reference(D / 'final-conservation.json'), 'next_action': 'Fresh separately authorized successor repairs all three oracles before another distinct review.'}
    write_new(D / 'REVIEW-FINDINGS.json', record)
    current_claim = json.loads((AUTHOR_R / RUN / 'claims.json').read_text())['review']
    assert current_claim['executor_id'] == ACTOR
    sys.path.insert(0, 'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
    from taar.orchestration_receipts import validate_receipt, load_receipt
    from taar.orchestration_runtime import _snapshot_workspace, _changed_files
    graph = json.loads((AUTHOR_R / RUN / 'graph.json').read_text())['graph']
    changed = _changed_files(current_claim['baseline_snapshot'], _snapshot_workspace(Q, Path('T:/')))
    assert changed == []
    receipt = {'schema_version': 1, 'run_id': RUN, 'node_id': 'review', 'executor_id': ACTOR,
        'started_at': current_claim['claimed_at'], 'finished_at': utc(), 'input_hash': current_claim['input_hash'],
        'changed_files': changed, 'result': {'decision': 'rejected', 'manifest': reference(Q / 'TRANSFER-MANIFEST.json'),
            'findings': reference(D / 'REVIEW-FINDINGS.json'), 'conservation': reference(D / 'final-conservation.json'),
            'actual_original_tests': 39, 'actual_hostile_methods': 3, 'actual_failed_control_subcases': 6,
            'positive_isolation_qualified': False, 'source_published': False,
            'prior_failures': [{'command': str(PY) + ' -B -X utf8 ' + str(D / 'hostile_cleanup.py'),
                                'exit_status': 1, 'proof': reference(D / 'hostile-cleanup-r1.json')}],
            'recovery': 'All exact reviewer-owned resources recovered; blocking defects remain in immutable candidate'},
        'commands': [
            {'command': str(PY) + ' -B -X utf8 ' + str(D / 'run_original.py'), 'exit_status': 0},
            {'command': str(PY) + ' -B -X utf8 ' + str(D / 'environment_census.py') + ' after', 'exit_status': 0}],
        'validations': [{'name': 'original_39_unique_tests_pass', 'passed': True},
                        {'name': 'candidate_and_environment_conserved', 'passed': True},
                        {'name': 'native_reviewer_cleanup_settled', 'passed': True},
                        {'name': 'primary_exception_and_native_custody_invariants', 'passed': False}],
        'exit_status': 1, 'decision': 'rejected'}
    kwargs = {'run_id': RUN, 'node_id': 'review', 'executor_id': ACTOR, 'input_hash': current_claim['input_hash'],
              'claimed_at': current_claim['claimed_at'], 'node': graph['nodes']['review']}
    validate_receipt(receipt, **kwargs); write_new(D / 'review.json', receipt)
    validate_receipt(load_receipt(D / 'review.json'), **kwargs)
    print(json.dumps({'decision': 'rejected', 'original_tests': 39, 'hostile_methods': 3,
                      'failed_subcases': 6, 'candidate_files': len(current), 'joined_differences': differences,
                      'receipt': reference(D / 'review.json')}), flush=True)
else:
    submitted = json.loads((D / 'review.json').read_text())
    assert submitted['decision'] == 'rejected' and submitted['exit_status'] == 1
    done, response = invoke(['node', 'complete', RUN, 'review', str(D / 'review.json')], 'review-complete')
    assert not response['allowed'] and response['code'] == 'EXECUTION_FAILED'
    stored_path = AUTHOR_R / RUN / 'receipts/review.json'
    stored = json.loads(stored_path.read_text())
    assert len(submitted) == 13 and set(stored) == set(submitted) | {'git_baseline', 'observed_git', 'receipt_hash'}
    def typed(value): return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)
    assert all(typed(stored[key]) == typed(value) for key,value in submitted.items())
    state = json.loads((AUTHOR_R / RUN / 'state.json').read_text())
    claims = json.loads((AUTHOR_R / RUN / 'claims.json').read_text())
    assert state['nodes']['review']['state'] == 'FAILED' and not claims
    assert candidate_cut() == json.loads((D / 'initial-observation.json').read_text())['candidate']
    write_new(D / 'actual-review-readback.json', {'observed_at': utc(), 'run_id': RUN, 'reviewer': ACTOR,
        'actual_review_state': 'FAILED', 'claims': claims, 'submitted': reference(D / 'review.json'),
        'persisted': reference(stored_path), 'actual_completion': reference(D / 'review-complete.json'),
        'strict_13_fields_type_exact': True, 'candidate_conserved': True,
        'manifest': reference(Q / 'TRANSFER-MANIFEST.json'), 'decision': 'rejected'})
    seal_rows = {}
    for path in sorted(D.rglob('*')):
        if path.is_file(): seal_rows[path.relative_to(D).as_posix()] = ordinary(path)
    write_new(D / 'REVIEW-SEAL.json', {'sealed_at': utc(), 'reviewer': ACTOR, 'decision': 'rejected',
        'scope': str(D), 'readback': reference(D / 'actual-review-readback.json'), 'ordinary_members': seal_rows,
        'source_or_environment_publication': False, 'claims_released': True})
    print(json.dumps({'review_state': 'FAILED', 'claims': claims,
        'readback': reference(D / 'actual-review-readback.json'), 'seal': reference(D / 'REVIEW-SEAL.json')}), flush=True)
