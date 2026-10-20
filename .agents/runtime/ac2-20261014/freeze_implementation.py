"""Freeze exact AC2 delivery and truthfully complete its author node once."""
from ac2_support import *

inputs = json.loads((R / 'source-inputs.json').read_text())
scope = inputs['scope']; names = set(inputs['source_payloads']) | set(scope)
rows = {name: ordinary(Q / name) for name in sorted(names)}
assert len(rows) == 294
for name,row in inputs['source_payloads'].items():
    assert rows[name]['sha256'] == row['sha256'] and ordinary(F / name) == row
for name in scope:
    try: fs.lstat(F / name)
    except FileNotFoundError: pass
    else: raise AssertionError('CREATE target now occupied: ' + name)

test = json.loads((R / 'original-r4.json').read_text())
closure_root = R / 'closure-r4'
closure = json.loads((closure_root / 'hostile-cleanup-r1.json').read_text())
assert test['tests_run'] == 50 and test['exit_status'] == 0 and test['expected_executed_equal']
assert len(set(test['executed_ids'])) == 50 and not test['failures'] and not test['errors'] and not test['skipped']
assert test['candidate_before'] == rows == test['candidate_after']
assert closure['tests_run'] == 3 and closure['exit_status'] == 0 and closure['expected_executed_equal']
assert len(closure['native_facts']) == 6 and not closure['failures'] and not closure['errors'] and not closure['skipped']
assert closure['candidate_before'] == rows == closure['candidate_after']
assert all(row['primary_identity_preserved'] and row['caller_visible_cleanup'] for row in closure['native_facts'])
assert test['ceta_import_bindings'] and all(Path(row['path']).is_relative_to(Q / 'src') for row in test['ceta_import_bindings'].values())
measure = json.loads((R / 'implementation-measures.json').read_text())
assert measure['new_source_LOC'] == 182 and measure['removed_parent_source_LOC'] == 35 and measure['new_test_LOC'] == 211

for name in ('src/ceta/supervisor/isolated_worker.py', 'tests/contract/test_isolated_worker.py', 'contracts/ISOLATED_WORKER_V1.md'):
    done = subprocess.run(['git', '-c', 'core.autocrlf=false', 'diff', '--no-index', '--check', str(PARENT / name), str(Q / name)],
                          cwd='T:/00-Active', capture_output=True)
    key = name.replace('/', '__')
    for suffix, raw in [('stdout.txt', done.stdout), ('stderr.txt', done.stderr)]:
        with (R / ('diff-check-r2-' + key + '.' + suffix)).open('xb') as output: output.write(raw)
    expected_difference_exit = int(fs.read_bytes(PARENT / name) != fs.read_bytes(Q / name))
    assert done.returncode == expected_difference_exit and not done.stdout and not done.stderr, (name, done.stdout, done.stderr)

source_now = {name: ordinary(F / name) for name in inputs['source_payloads']}
write_new(R / 'publication-before-images.json', {'observed_at': utc(), 'source_root': str(F),
    'eligible': {name: {'application_action': 'CREATE', 'before_sha256': None, 'absence_observed': True,
                        'candidate_sha256': rows[name]['sha256'],
                        'parent_before_image': reference(R / 'AC1-before-images' / name)} for name in scope},
    'reuse_290': source_now, 'actual_source_writes': []})
manifest = {'schema_version': 1, 'cut': RUN, 'frozen_at': utc(), 'author': ACTOR,
    'candidate_root': str(Q), 'source_root': str(F), 'runtime_root': str(R),
    'functional_status': 'CLEANUP_REPAIR_IMPLEMENTED_AWAITING_DISTINCT_REVIEW',
    'isolation_qualified': False, 'activation_ready': False, 'whole_unit_completion': False, 'source_published': False,
    'eligible_paths': scope, 'classifications': {name: 'CREATE' for name in scope},
    'payloads': rows, 'payload_count': 294, 'current_source_REUSE_count': 290,
    'reused_application_eligible': False, 'parent_manifest': reference(PARENT / 'TRANSFER-MANIFEST.json'),
    'author_delta_changed_paths': [name for name,row in measure['by_path'].items() if not row['byte_exact_reuse']],
    'native_rust_byte_exact_reuse': reference(PARENT / 'native/windows_broker/isolated_worker.rs'),
    'native_binary_byte_exact_reuse': ordinary(PRIOR_R / 'build-r2/isolated_worker.exe'),
    'native_build_provenance': reference(PRIOR_R / 'build-r2/build.json'),
    'tests': {'cohort_methods': 50, 'original_methods': 39, 'new_methods': 11,
              'adverse_methods': 3, 'adverse_control_subcases': 6, 'failures': 0, 'errors': 0, 'skips': 0},
    'cohort': reference(R / 'original-r4.json'), 'cohort_raw': reference(R / 'original-r4.txt'),
    'adverse_closure': reference(closure_root / 'hostile-cleanup-r1.json'),
    'adverse_raw': reference(closure_root / 'hostile-cleanup-r1.txt'),
    'adverse_oracle_binding': reference(closure_root / 'closure-oracle-binding.json'),
    'adverse_oracle_diff': reference(closure_root / 'oracle-adaptation.diff'),
    'source_inputs': reference(R / 'source-inputs.json'),
    'before_images': reference(R / 'publication-before-images.json'),
    'input_conservation': reference(R / 'input-conservation.json'),
    'self_review': reference(R / 'SELF-REVIEW.json'), 'measurements': reference(R / 'implementation-measures.json'),
    'review_support': {name: ordinary(R / name) for name in (
        'ac2_support.py', 'ac_support.py', 'run_original.py', 'prepare_closure.py',
        'reproduce_baseline.py', 'self_review_and_measure.py', 'conserve_inputs.py', 'freeze_implementation.py')},
    'source_LOC_new_since_AC1': 182, 'source_LOC_removed_from_AC1': 35, 'test_LOC_new_since_AC1': 211,
    'reused_Rust_or_generated_artifacts_LOC_credit': 0,
    'prior_failures': [reference(R / 'baseline-reproduction.json'),
        reference(R / 'failed-cuts/dll-binding-r1/failure.json'),
        reference(R / 'closure-r1/hostile-cleanup-r1.json'),
        reference(R / 'failed-cuts/freeze-check-r1/failure.json')],
    'prior_review_strength_qualification': reference(R / 'prior-review-sentinel-qualification.json'),
    'unresolved': ['Actual no-profile restrictive CreateProcessW still returns error2; cause unestablished.',
        'Positive restricted worker token/access/process/network/escape/post-create cleanup qualification remains NOT_EXECUTED.',
        'Unknown completion of a free/deletion remains retained UNCERTAIN state, not a successful retirement claim.',
        'Canonical production authority/evidence/runtime wiring and any profile decision remain open.'],
    'reviewer_fixture_guidance': 'Load exact Q test bytes on Q imports, rebind only test module ROOT to a fresh own harness; original39 ASTs stay exact. Relocate existing fixture support and compiled native helper into the own runtime, never author R or Q fixtures.'}
write_new(Q / 'TRANSFER-MANIFEST.json', manifest)
handoff = {'observed_at': utc(), 'author': ACTOR, 'manifest': reference(Q / 'TRANSFER-MANIFEST.json'),
    'source': 'Three changed parent paths plus exact unchanged Rust; all four active targets CREATE and still absent',
    'tests': manifest['tests'], 'cohort': manifest['cohort'], 'adverse': manifest['adverse_closure'],
    'review_required': 'A distinct reviewer must claim actual READY review before acceptance or Source publication.',
    'actual_source_changes': [], 'source_LOC_new': 182, 'test_LOC_new': 211,
    'profile_installed': False, 'isolation_qualified': False, 'activation_ready': False}
write_new(R / 'HANDOFF.json', handoff)
commands = [
    {'command': subprocess.list2cmdline([str(PY), '-B', '-X', 'utf8', str(R / 'run_original.py'), 'original-r4']), 'exit_status': 0},
    {'command': subprocess.list2cmdline([str(PY), '-B', '-X', 'utf8', str(R / 'prepare_closure.py'), 'closure-r4']), 'exit_status': 0},
    {'command': subprocess.list2cmdline([str(PY), '-B', '-X', 'utf8', str(R / 'self_review_and_measure.py')]), 'exit_status': 0},
    {'command': subprocess.list2cmdline([str(PY), '-B', '-X', 'utf8', str(R / 'conserve_inputs.py')]), 'exit_status': 0}]
complete('implement', {'manifest': reference(Q / 'TRANSFER-MANIFEST.json'), 'handoff': reference(R / 'HANDOFF.json'),
    'tests': manifest['tests'], 'prior_failures': manifest['prior_failures'],
    'scope': 'Three measured cleanup defect repairs; separate review, Source admission and positive isolation remain open',
    'new_source_LOC': 182, 'new_test_LOC': 211, 'source_published': False, 'isolation_qualified': False}, commands,
    [('All original39 plus11 native tests and three closure methods pass on final294 payloads', True),
     ('Current Source290, frozen parent and E3 bytes/native identities conserved', True),
     ('Original test bodies and public launch/SID interfaces preserved', True),
     ('Unknown finalizer completion stays retained without blind replay', True),
     ('Positive isolation remains unqualified and no protected host effect occurred', True)])
print(json.dumps({'manifest': reference(Q / 'TRANSFER-MANIFEST.json'), 'implement': reference(R / 'implement.json'),
                  'payloads': 294, 'tests': manifest['tests']}), flush=True)
