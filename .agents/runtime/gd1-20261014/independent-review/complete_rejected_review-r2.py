"""Record and submit truthful rejected GD1 review using the actual review claim."""
from datetime import datetime, timezone
from pathlib import Path
import ast
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys

O = Path(__file__).resolve().parent
R = O.parent
F = R.parents[2]
Q = F / '.agents/gd1-20261014'
RUN = 'gd1-20261014'
ACTOR = '/root/pressure_review'
sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
read = lambda path: json.loads(Path(path).read_text(encoding='utf-8-sig'))
now = lambda: datetime.now(timezone.utc).isoformat()
def write_new(path, value):
    assert Path(path).is_relative_to(O)
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')
def ref(path):
    return {'repository_relative_path': Path(path).relative_to(F).as_posix(), 'sha256': sha(path)}

manifest_path = Q / 'TRANSFER-MANIFEST.json'
assert sha(manifest_path) == '3f64c0dca1637ef58d6eb5bd2c64809d9af48c2c1fb691f6d558b15047cbf9b3'
assert sha(R / 'implement.json') == 'bdade2cba4633cd602f390134ad0255f451c915edc5995fee97cd7493c1b4d85'
manifest = read(manifest_path)
connected = read(O / 'connected-independent.json')
hostile = read(O / 'hostile-timing-probes.json')
candidate_bad = read(O / 'nested-shape-candidate.json')
baseline_bad = read(O / 'nested-shape-baseline.json')
census = read(O / 'native-child-census.json')
assert connected['tests_run'] == 314 and connected['failures'] == connected['errors'] == connected['skips'] == 0
assert hostile['tests_run'] == 7 and hostile['failures'] == 1 and hostile['errors'] == hostile['skips'] == 0
assert len(hostile['failure_details']) == 1
assert all(not row['same_recorded_lifetime'] for row in census['observations'])
assert census['old_scope_breach_PID18684_present'] is False
assert connected['all_imports_own_cut'] and len(connected['imports']) == 26
assert connected['source_unchanged'] and connected['candidate_unchanged']
payloads = {row['relative_path']: row for row in manifest['payloads']}
current_source = {name: sha(F / name) for name, row in payloads.items() if row['action'] != 'CREATE'}
current_candidate = {name: sha(Q / name) for name in payloads}
assert current_source == connected['source_before'] == connected['source_after']
assert current_candidate == connected['candidate_before'] == connected['candidate_after']
baseline_text = (F / 'src/ceta/resource/diagnostics.py').read_text(encoding='utf-8')
candidate_text = (Q / 'src/ceta/resource/diagnostics.py').read_text(encoding='utf-8')
before_ast, after_ast = ast.parse(baseline_text), ast.parse(candidate_text)
classes_before = {node.name: node for node in before_ast.body if isinstance(node, ast.ClassDef)}
classes_after = {node.name: node for node in after_ast.body if isinstance(node, ast.ClassDef)}
assert set(classes_before) == set(classes_after)
unchanged_classes = []
for name in classes_before:
    if name != 'OwnedProcessTelemetrySampler':
        assert ast.dump(classes_before[name], include_attributes=False) == ast.dump(classes_after[name], include_attributes=False)
        unchanged_classes.append(name)
constructor_before = next(node for node in classes_before['OwnedProcessTelemetrySampler'].body if isinstance(node, ast.FunctionDef) and node.name == '__init__')
constructor_after = next(node for node in classes_after['OwnedProcessTelemetrySampler'].body if isinstance(node, ast.FunctionDef) and node.name == '__init__')
assert ast.dump(constructor_before.args, include_attributes=False) == ast.dump(constructor_after.args, include_attributes=False)
diff = list(difflib.ndiff(baseline_text.splitlines(), candidate_text.splitlines()))
physical_added = sum(line.startswith('+ ') for line in diff)
physical_removed = sum(line.startswith('- ') for line in diff)
assert (physical_added, physical_removed) == (82, 23)
ids = connected['expected_ids']
raw = (O / 'connected-independent-r2.txt').read_text(encoding='utf-8-sig')
raw_ids = re.findall(r'^test_\S+ \(([^)]+)\) \.\.\. ok\s*$', raw, re.MULTILINE)
assert raw_ids == ids
author = read(F / manifest['tests']['repository_relative_path'])
author_raw_path = F / manifest['raw_tests']['repository_relative_path']
assert sha(author_raw_path) == manifest['raw_tests']['sha256']
author_raw_ids = re.findall(r'^test_\S+ \(([^)]+)\) \.\.\. ok\s*$', author_raw_path.read_text(encoding='utf-8'), re.MULTILINE)
assert author_raw_ids == [row['id'] for row in author['cases']] == ids
claim = read(R / RUN / 'claims.json')['review']
assert claim['executor_id'] == ACTOR and claim['workspace'] == str(Q)
assert claim['input_hash'] == 'f1d28ee8229c88a14e1fea05023d2ff85ec88796bf412c19ff3d18e4560ec8f9'
for report in (candidate_bad, baseline_bad):
    r = report['recovery_after_rejected_first_raw_frame']
    assert r['initial_recording_error']['code'] == 'RESOURCE_MEASUREMENT_INVALID'
    assert r['recovery_samples'][0]['cpu_milli'] == 990000 and r['recovery_samples'][0]['cpu_measured'] is True
    assert r['retained_sequences'] == [2, 3] and r['analysis_measurement_state'] == 'MEASURED_PROCESS_USAGE'
    assert report['source_before_sha256'] == report['source_after_sha256']
fixture_path = F / '.agents/fixtures/windows-jobs-dd79a0fbc97549e786f288fb88fa31f0/primary.json'
assert sha(fixture_path) == '5c7231d6cf0796e2661624b23a5c6f78c0a8c5c8cc58d5584904554819685a55'
acceptance = read(R / 'acceptance-coverage.json')
assert len(acceptance['cases']) == 20
acceptance_rows = []
for row in acceptance['cases']:
    assert all(test_id in ids for test_id in row['author_test_ids'])
    acceptance_rows.append({'acceptance_id': row['acceptance_id'], 'author_state': row['state'],
        'review_state': 'MALFORMED_NESTED_FRAME_FINDING_OPEN' if row['acceptance_id'].endswith('-03') else 'BOUND_COHORT_REPRODUCED_FULL_ORIGINAL_ACCEPTANCE_REMAINS_OPEN',
        'author_remaining': row['remaining']})
finding = {'id': 'GD1-R20-F01', 'priority': 'P1', 'classification': 'blocking current task',
    'title': 'Nested quantity validation occurs after sampler state adoption, allowing malformed first-frame CPU baseline poisoning',
    'candidate_source': {'path': str(Q / 'src/ceta/resource/diagnostics.py'), 'sha256': sha(Q / 'src/ceta/resource/diagnostics.py')},
    'affected_operations': ['OwnedProcessTelemetrySampler.sample', 'OwnedProcessTelemetrySampler.collect'],
    'affected_lines': {'wrapper_only_validation': 217, 'state_adoption': 240, 'CPU_baseline_adoption': 259},
    'counterexample': 'An explicit synthetic port returns a valid frozen ProcessResourceCounters object whose nested measured CPU value was mutated to bool True. The sampler adopts it as first-frame baseline/high-water and returns it; recorder rejects RESOURCE_MEASUREMENT_INVALID. Subsequent valid unchanged CPU100 frames produce measured CPU990000 then0, and retained sequences2/3 analyze as MEASURED_PROCESS_USAGE with peak990000.',
    'additional_counterexamples': 'First-frame read_io bool enters counter high-water; working_set bool is returned as measured on both first and later frames.',
    'baseline_classification': 'Independently reproduced on active43db2dd7 baseline; existing issue persists in delivered candidate and is not ignored',
    'scope': 'Synthetic malformed port output and sampler/recorder recovery integrity; no native sensor compromise or principal-isolation claim',
    'requirements': ['AT-CETA-20.05.01-03', 'AT-CETA-20.05.02-03', 'AT-CETA-20.05.01-08', 'AT-CETA-20.05.02-08'],
    'evidence': [ref(O / 'nested-shape-candidate.json'), ref(O / 'nested-shape-baseline.json'), ref(O / 'hostile-timing-probes.json')],
    'next_executable_repair': 'In a fresh author cut, revalidate all five nested quantities inside the counter validation try before any accepted order/counter/CPU-baseline/cached-frame adoption. Preserve shared contracts/public signature/original tests. Prove malformed initial and subsequent frames raise exact contract error, invalidate reusable frame/CPU baseline, retain accepted high-water, and cannot influence valid recovery measurements.'}
report = {'schema_version': 1, 'executor': ACTOR, 'reviewed_at': now(), 'decision': 'rejected', 'exit_status': 1,
    'manifest': ref(manifest_path), 'implement_receipt': ref(R / 'implement.json'), 'claim': {key: claim[key] for key in ('executor_id', 'workspace', 'claimed_at', 'input_hash')},
    'source_root': str(F), 'candidate_root': str(Q), 'findings': [finding],
    'tests': {'connected': ref(O / 'connected-independent.json'), 'raw_connected': ref(O / 'connected-independent-r2.txt'),
        'tests_run': 314, 'failures': 0, 'errors': 0, 'skips': 0, 'unique_raw_discovered_executed_ids_joined': True,
        'hostile': ref(O / 'hostile-timing-probes.json'), 'raw_hostile': ref(O / 'hostile-timing-probes.txt'), 'hostile_methods': 7, 'hostile_passes': 6, 'hostile_failures': 1,
        'malformed_shape_candidate': ref(O / 'nested-shape-candidate.json'), 'malformed_shape_baseline': ref(O / 'nested-shape-baseline.json')},
    'verified_timing_behavior': {'native_currentness_trials': [row for row in connected['native_observations'] if row.get('case') == 'currentness'],
        'native_counter_delay': [row for row in connected['native_observations'] if row.get('case') == 'counter-return'],
        'native_clocks': connected['clock_info'], 'actual_native_cases_new': 6, 'default_public_timestamp_domain_preserved': True,
        'asymmetric_rollback_final_clock_occupancy_cache_expiry_and_state_high_water_probes': '6 independent hostile methods pass'},
    'code_inspection': {'public_constructor_signature_AST_unchanged': True, 'all_other_classes_AST_unchanged': unchanged_classes,
        'changed_source_physical_added': physical_added, 'changed_source_physical_removed': physical_removed,
        'meaningful_author_count_inspected': {'added': 72, 'removed': 23, 'net': 49},
        'original_process_methods_intact': 47, 'original_resource_methods_intact': 95, 'retained_payloads': 277,
        'current_candidate_payloads': 280, 'Source_payloads_unchanged': 279, 'observed_ceta_imports': 26, 'all_imports_own_cut': True},
    'acceptance_cases': acceptance_rows,
    'historical_fixture_scope_breach': {'metadata': ref(fixture_path), 'PID': 18684, 'creation_time_100ns': 134364536932048790,
        'current_PID_absent': True, 'classification': 'HISTORICAL_SCOPE_BREACH_RETAINED_SEPARATELY; AUTHOR_LATER_FIXTURE_SCOPE_FIXED',
        'disposition': 'Original fixture retained unchanged; neither file deletion nor host process mutation performed', 'supporting_author_record': ref(R / 'baseline-preparation-scope.json')},
    'native_custody': {'census': ref(O / 'native-child-census.json'), 'same_recorded_children_remaining': 0,
        'fresh_Q_children': connected['new_retained_native_child_names'], 'fixture_events': connected['fixture_events'],
        'all_existing_fixture_files_retained': True, 'actual_own_completed_new_native_cases': 6, 'source_or_guard_changes': False},
    'reader_limits': ['Canonical source/clock authentication, principal separation, publication, durable recovery, workload latency, queueing and causal bottleneck qualification remain open',
        'Domain/native producer measurements do not create a reservation, grant, scheduler, ledger or canonical evidence-owner integration',
        'Read-only endpoint hashes/native census and shared administrator context do not establish uninterrupted custody or isolated trust',
        'Original B-case/full installed product acceptance remains open;314 methods establish only the recorded connected cohort',
        'The failing original hostile method is an exact malformed-category expectation; first-frame and valid-recovery probes independently establish actual accepted-state poisoning'],
    'prior_failures': [ref(O / 'cohort-runner-r1-failure.json'), ref(O / 'connected-independent.txt')],
    'preparation_command_failures': ['Initial inspector used nonexistent src/ceta/resource_management path; corrected to observed src/ceta/resource',
        'An acceptance inspector attempted absent rows[] instead of observed cases[]; no tests or source mutations resulted'],
    'source_or_candidate_edits': [], 'Source_application': False, 'approval': False, 'reviewer_next_action': 'Submit actual rejected receipt and release claim for separate GD2 repair'}
assert read(O / 'REPORT.json')['manifest']['sha256'] == sha(manifest_path)
assert read(O / 'REPORT.json')['decision'] == 'rejected'

sys.path.insert(0, r'T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce')
from taar.orchestration_receipts import validate_receipt, load_receipt
from taar.orchestration_runtime import _snapshot_workspace, _changed_files
changed = _changed_files(claim['baseline_snapshot'], _snapshot_workspace(Q, Path('T:/')))
assert not changed, changed
receipt = {'schema_version': 1, 'run_id': RUN, 'node_id': 'review', 'executor_id': ACTOR,
    'started_at': claim['claimed_at'], 'finished_at': now(), 'input_hash': claim['input_hash'], 'changed_files': changed,
    'result': {'decision': 'rejected', 'approved': False, 'manifest_sha256': sha(manifest_path), 'report': ref(O / 'REPORT.json'),
        'report_markdown': ref(O / 'REPORT.md'), 'finding_ids': ['GD1-R20-F01'], 'tests_run': 314,
        'connected_passes': 314, 'hostile_methods': 7, 'hostile_passes': 6, 'hostile_failures': 1,
        'candidate_malformed_frame_proof': ref(O / 'nested-shape-candidate.json'), 'baseline_malformed_frame_proof': ref(O / 'nested-shape-baseline.json'),
        'prior_failures': report['prior_failures'] + [ref(O / 'finalizer-r1-failure.json'), ref(O / 'finalization-r1.txt')], 'native_census': ref(O / 'native-child-census.json'), 'scope_released_after_actual_readback': True},
    'commands': [
        {'command': subprocess.list2cmdline([sys.executable, '-B', '-X', 'utf8', str(O / 'run_cohort.py')]), 'exit_status': 1},
        {'command': subprocess.list2cmdline([sys.executable, '-B', '-X', 'utf8', str(O / 'run_cohort-r2.py')]), 'exit_status': 0},
        {'command': subprocess.list2cmdline([sys.executable, '-B', '-X', 'utf8', str(O / 'hostile_timing_probes.py')]), 'exit_status': 1},
        {'command': subprocess.list2cmdline([sys.executable, '-B', '-X', 'utf8', str(O / 'probe_nested_shape.py'), 'candidate']), 'exit_status': 0},
        {'command': subprocess.list2cmdline([sys.executable, '-B', '-X', 'utf8', str(O / 'probe_nested_shape.py'), 'baseline']), 'exit_status': 0}],
    'validations': [{'name': 'frozen_manifest_payload_and_actual_claim_binding', 'passed': True},
        {'name': '314_original_and_new_cases_raw_ID_join', 'passed': True},
        {'name': 'native_child_custody_and_source_conservation', 'passed': True},
        {'name': 'malformed_nested_port_quantity_validation_before_state_adoption', 'passed': False}],
    'exit_status': 1, 'decision': 'rejected'}
kwargs = {'run_id': RUN, 'node_id': 'review', 'executor_id': ACTOR, 'input_hash': claim['input_hash'],
    'claimed_at': claim['claimed_at'], 'node': read(R / RUN / 'graph.json')['graph']['nodes']['review']}
validate_receipt(receipt, **kwargs)
receipt_path = O / 'review.json'
write_new(receipt_path, receipt)
validate_receipt(load_receipt(receipt_path), **kwargs)
command = ['powershell.exe', '-NoProfile', '-File', r'T:\02-Config\agents\taar-orchestrate.ps1',
    'node', 'complete', RUN, 'review', str(receipt_path), '--runtime-root', str(R)]
done = subprocess.run(command, cwd=r'T:\00-Active', capture_output=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
for name, data in [('review-complete.stdout', done.stdout), ('review-complete.stderr', done.stderr)]:
    with (O / name).open('xb') as stream: stream.write(data)
response = json.loads(done.stdout)
write_new(O / 'review-complete-response.json', {'command_argv': command, 'exit_status': done.returncode, 'response': response})
assert done.returncode == 0 and response['allowed'] is True, response
state, claims = read(R / RUN / 'state.json'), read(R / RUN / 'claims.json')
assert state['nodes']['review']['state'] == 'FAILED' and not claims
write_new(O / 'actual-review-readback.json', {'executor': ACTOR, 'observed_at': now(), 'actual_review_state': 'FAILED',
    'sequence': state['sequence'], 'claims': claims, 'receipt_sha256': sha(receipt_path),
    'report_sha256': sha(O / 'REPORT.json'), 'changed_files': [], 'source_unchanged': True, 'candidate_unchanged': True})
print(json.dumps({'actual_review_state': 'FAILED', 'decision': 'rejected', 'allowed': True, 'sequence': state['sequence'],
    'claims': claims, 'receipt_sha256': sha(receipt_path), 'report_sha256': sha(O / 'REPORT.json'),
    'readback_sha256': sha(O / 'actual-review-readback.json'), 'candidate_nested_proof_sha256': sha(O / 'nested-shape-candidate.json'),
    'baseline_nested_proof_sha256': sha(O / 'nested-shape-baseline.json')}), flush=True)
