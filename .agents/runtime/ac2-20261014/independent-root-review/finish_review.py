"""Complete distinct AC2 library/cleanup review with positive isolation explicitly unqualified."""
from ac2_support import *

claim = json.loads((R.parent / RUN / 'claims.json').read_text())['review']
assert claim['executor_id'] == '/root'
original = json.loads((R / 'original-r1.json').read_text())
closure = json.loads((R / 'closure-r1/hostile-cleanup-r1.json').read_text())
assert original['tests_run'] == 50 and original['exit_status'] == 0
assert original['failures'] == original['errors'] == original['skipped'] == []
assert original['expected_ids'] == original['executed_ids']
assert original['candidate_before'] == original['candidate_after']
assert closure['tests_run'] == 3 and closure['exit_status'] == 0
assert closure['failures'] == closure['errors'] == closure['skipped'] == []
assert closure['expected_ids'] == closure['executed_ids'] and len(closure['native_facts']) == 6
assert closure['candidate_before'] == closure['candidate_after']
assert closure['source_before'] == closure['source_after']
assert all(row['primary_identity_preserved'] and row['caller_visible_cleanup'] for row in closure['native_facts'])
for row in closure['native_facts']:
    if 'all_captured_handles_closed' in row:
        assert row['all_captured_handles_closed'] is True and row['pending_sids_after'] == []
        assert row['captured_job_native_status'][0]['native_open'] is False
        assert row['captured_job_native_status'][0]['last_error'] == 6
    if 'native_closed_after_recovery' in row:
        assert row['native_closed_after_recovery'] == [True]
for name, value in closure['candidate_after'].items():
    assert ordinary(Q / name) == value
for name, value in closure['source_after'].items():
    assert ordinary(F / name) == value
assert len(closure['candidate_after']) == 294 and len(closure['source_after']) == 290
assert all(row['lifetime_closed'] and row['job_closed'] and row['process_closed']
           for row in original['canonical_job_census'])
environment = json.loads((R.parent / 'environment-after.json').read_text())
env_root = Path(environment['root'])
env_after = {name: ordinary(env_root / name) for name in environment['ordinary_files']}
assert len(env_after) == 3601
assert all(value['sha256'] == environment['ordinary_files'][name]['sha256']
           and value['native_identity'] == environment['ordinary_files'][name]['native_identity']
           for name, value in env_after.items())
write_new(R / 'environment-conservation.json', {'recorded_at': utc(), 'ordinary_files': 3601,
    'ordinary_bytes': sum(value['bytes'] for value in env_after.values()),
    'all_recorded_ordinary_hashes_and_native_identities_conserved': True, 'members': env_after})
report = {'reviewer': '/root', 'recorded_at': utc(), 'decision': 'approved',
    'scope': 'AC2 additive trusted-composition library and cleanup repair only; positive AppContainer launch/isolation remains unqualified.',
    'manifest': reference(Q / 'TRANSFER-MANIFEST.json'),
    'personally_inspected': ['Complete isolated_worker.py and Rust fixed-worker source',
        'All11 new cleanup method bodies and unchanged39 inherited methods/paths',
        'Exact original/adapted oracle diff: closed job metadata/error6 and retained duplicate-token explicit recovery',
        'All6 current native cleanup raw facts plus actual restrictive denial/medium control retirement'],
    'cohort': reference(R / 'original-r1.json'), 'closure': reference(R / 'closure-r1/hostile-cleanup-r1.json'),
    'tests': {'unique_methods': 53, 'original_cohort': 50, 'closure_methods': 3, 'closure_control_subcases': 6,
              'failures': 0, 'errors': 0, 'skips': 0},
    'confirmed': ['Primary exception identity survives attribute/SID/token cleanup refusal',
        'Independent cleanup continues; caller-visible exact pending custody remains recoverable',
        'Actual event handle numeric reuse leaves replacement object open',
        'Uncertain post-free responses prevent a blind replay',
        'All observed reviewer-owned process lifetimes and query handles retired'],
    'limitations': ['Restrictive CreateProcessW still returns error2; internal cause UNESTABLISHED.',
        'No successful AppContainer worker/token/asset/scratch/process/network/handle-isolation qualification.',
        'No CreateAppContainerProfile/DeleteAppContainerProfile or host configuration operation executed.',
        'No selected runtime profile, canonical admission, genuine owner approval or whole-component acceptance.'],
    'Source_changes': [], 'activation_ready': False, 'positive_isolation_qualified': False,
    'source_library_integration_permitted_after_required_validate': True}
write_new(R / 'REPORT.json', report)
sys.path.insert(0, 'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_runtime import _snapshot_workspace, _changed_files
from taar.orchestration_receipts import validate_receipt
assert _changed_files(claim['baseline_snapshot'], _snapshot_workspace(Q, Path('T:/'))) == []
receipt = {'schema_version': 1, 'run_id': RUN, 'node_id': 'review', 'executor_id': '/root',
    'started_at': claim['claimed_at'], 'finished_at': utc(), 'input_hash': claim['input_hash'], 'changed_files': [],
    'result': {'manifest_sha256': sha(Q / 'TRANSFER-MANIFEST.json'), 'report': reference(R / 'REPORT.json'),
               'unique_methods_passed': 53, 'positive_isolation_qualified': False, 'activation_ready': False, 'Source_application': False},
    'commands': [{'command': str(PY) + ' -B -X utf8 ' + str(R / 'run_original.py'), 'exit_status': 0},
                 {'command': str(PY) + ' -B -X utf8 ' + str(R / 'run_prepared_closure.py'), 'exit_status': 0}],
    'validations': [{'name': name, 'passed': True} for name in (
        'frozen_candidate294_Source290_E33601_conserved', 'all53_methods_exactly_executed_and_passed',
        'six_native_failure_custody_closures_passed', 'closed_defaults_and_positive_isolation_unqualified_remain_explicit')],
    'exit_status': 0, 'decision': 'approved'}
assert len(receipt) == 13
kwargs = dict(run_id=RUN, node_id='review', executor_id='/root', input_hash=claim['input_hash'],
    claimed_at=claim['claimed_at'], node=json.loads((R.parent / RUN / 'graph.json').read_text())['graph']['nodes']['review'])
validate_receipt(receipt, **kwargs)
write_new(R / 'review.json', receipt)
validate_receipt(json.loads((R / 'review.json').read_text()), **kwargs)
argv = ['powershell', '-NoProfile', '-File', 'T:/02-Config/agents/taar-orchestrate.ps1',
        'node', 'complete', RUN, 'review', str(R / 'review.json'), '--runtime-root', str(R.parent)]
done = subprocess.run(argv, cwd=F, capture_output=True)
for suffix, raw in [('stdout', done.stdout), ('stderr', done.stderr)]:
    with (R / ('review-complete.' + suffix)).open('xb') as out:
        out.write(raw)
response = json.loads(done.stdout.decode('utf-8-sig'))
write_new(R / 'review-complete.json', {'argv': argv, 'exit_status': done.returncode, 'response': response})
assert done.returncode == 0 and response['allowed']
run_root = R.parent / RUN
state = json.loads((run_root / 'state.json').read_text())
claims = json.loads((run_root / 'claims.json').read_text())
assert state['sequence'] == 9 and state['nodes']['review']['state'] == 'SUCCEEDED' and claims == {}
relative = Path(state['nodes']['review']['receipt_ref'])
assert not relative.is_absolute() and '..' not in relative.parts
persisted = json.loads((run_root / relative).read_text())
assert len(persisted) == 16 and all(type(persisted[k]) is type(v) and persisted[k] == v for k,v in receipt.items())
write_new(R / 'ACTUAL-REVIEW-READBACK.json', {'recorded_at': utc(), 'sequence': 9, 'claims': claims,
    'actual_review_state': 'SUCCEEDED', 'decision': 'approved', 'submitted13_persisted16_equal': True,
    'review': reference(R / 'review.json'), 'Source_application': False, 'positive_isolation_qualified': False})
print(json.dumps({'actual_review': 'SUCCEEDED', 'sequence': 9, 'claims': claims,
    'review_sha256': sha(R / 'review.json'), 'tests': 53, 'positive_isolation_qualified': False}), flush=True)
