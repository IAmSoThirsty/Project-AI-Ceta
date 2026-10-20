"""Verify only the accepted worker-snapshot repair and all pinned review inputs."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import subprocess

F = Path(r'T:\00-Active\Project-AI-CETA')
R = F / '.agents/runtime/session-resume-20261020'
O = F / '.agents/runtime/session-resume-review-20261020'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
checks = read(O / 'CHECKS.json')
for row in checks['all_input_pins']:
    assert sha(Path(row['path'])) == row['sha256']
r1 = read(R / 'continuity.json.candidate')
r2 = read(R / 'continuity.json.candidate-r2')
prepared = read(R / 'PREPARED-R2.json')
progress_hash = '8257f739a2f16f9acb4361bebaf0f81b14675f6a12e780d8eac677cf8b4594d0'
continuity_hash = 'b23f4427131d7fa392af9e286c530e6546791ed0724889600da6abe46b2ff206'
assert sha(R / 'progress.json.candidate') == prepared['progress_candidate_sha256'] == progress_hash
assert sha(R / 'continuity.json.candidate-r2') == prepared['continuity_candidate_sha256'] == continuity_hash
assert prepared['prior_continuity_sha256'] == sha(R / 'continuity.json.candidate')
assert prepared['canonical_writes'] is False
changed = {k for k in set(r1) | set(r2) if r1.get(k) != r2.get(k)}
assert changed == {'active_workers', 'active_workers_observed_at', 'active_workers_observation_basis'}
assert datetime.fromisoformat(r2['active_workers_observed_at']) == datetime.fromisoformat(prepared['at'])
assert 'Timestamped collaboration.list_agents snapshot' in r2['active_workers_observation_basis']
assert 'consult live agent status for a later time' in r2['active_workers_observation_basis']
assert r2['active_workers'] == [
    {'agent': '/root/recovery_regression20', 'job': 'JS9 R2 runner repair controls and phase handoff'},
    {'agent': '/root/recovery_join_review20', 'job': 'Independent JS9 R2 execution tool review'},
    {'agent': '/root/ac7_native_artifact_review20', 'job': 'Independent two-document resume-status review'}]
assert r2['resume_20261020'] == read(R / 'progress.json.candidate')['current_repository_execution_20261020']
js9 = read(F / r2['resume_20261020']['joined_controlled_tests']['repository_relative_path'])
assert js9['tests_run'] == js9['journals_created'] == len(js9['fixture_facts']) == 45
assert js9['all_journals_closed'] is True and js9['native_execution'] is False
assert not js9['native_boundary_attempts'] and not js9['boundary_violations'] and not js9['residual_threads']
assert all(v['sqlite_closed'] is True and v['connection_close_state'] == 'CLOSED' for v in js9['fixture_facts'])
git = ['git', '-c', 'safe.directory=T:/00-Active/Project-AI-CETA', '-C', str(F)]
for cmd, expected in [('rev-parse HEAD', checks['git']['head']), ('branch --show-current', checks['git']['branch'])]:
    assert subprocess.check_output([*git, *cmd.split()], text=True).strip() == expected
result = {'author': '/root', 'reviewer': '/root/ac7_native_artifact_review20',
    'disposition': 'APPROVED_EXACT_TWO_DOCUMENT_METADATA_CANDIDATES',
    'progress_candidate_sha256': progress_hash, 'continuity_candidate_r2_sha256': continuity_hash,
    'prepared_r2_sha256': sha(R / 'PREPARED-R2.json'), 'r2_changed_fields_from_r1': sorted(changed),
    'finding': {'id': 'RESUME-STATUS-P3-001', 'status': 'fixed',
        'basis': 'Updated assignments with explicit observed timestamp and historical-snapshot qualification; Root attests the live platform observation'},
    'historical_fields_and_all_other_r1_values_unchanged': True,
    'accepted_JS8_reference_unchanged': True, 'original_tracked_files_still_match_beforeimages': True,
    'seven_current_evidence_references_match': True, 'js9_45_case_receipt_and_cleanup_verified': True,
    'ac7_failed_consumed_attempt_recorded_cleanup_and_unknown_DLL_preserved': True,
    'full_product_native_source_publication_or_destination_acceptance_promoted': False,
    'native_or_test_reruns': False, 'canonical_writes_by_reviewer': False,
    'additional_wording_corrections_required': [], 'changed_cut_requires_new_review': True,
    'review_scope': 'Metadata truthfulness and exact two-document content only; no host execution authority issued'}
with (O / 'APPROVAL.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(result, indent=2))
