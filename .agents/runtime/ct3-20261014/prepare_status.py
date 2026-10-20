"""Prepare two truthful status candidates only after accepted reservation delivery."""
from datetime import datetime, timezone
from pathlib import Path
import copy
import hashlib
import json
import os
import subprocess
import sys

R = Path(__file__).resolve().parent
F, RUN = R.parents[2], 'ct3-20261014'
Q = F / '.agents' / RUN
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()
def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
def ref(path):
    return {'repository_relative_path': path.relative_to(F).as_posix(), 'sha256': sha(path)}
def invoke(label, args):
    argv = ['powershell', '-NoProfile', '-File', r'T:\02-Config\agents\taar-orchestrate.ps1',
            *args, '--runtime-root', str(R)]
    started = now()
    done = subprocess.run(argv, capture_output=True)
    for suffix, data in (('stdout', done.stdout), ('stderr', done.stderr)):
        with (R / (label + '.' + suffix)).open('xb') as stream:
            stream.write(data)
    response = json.loads(done.stdout.decode('utf-8-sig'))
    save(R / (label + '.json'), {'argv': argv, 'started_at': started, 'finished_at': now(),
                               'exit_status': done.returncode, 'response': response})
    assert done.returncode == 0 and response['allowed'] is True, response
def accepted(package):
    root = F / '.agents/runtime' / package
    state, claims = read(root / package / 'state.json'), read(root / package / 'claims.json')
    assert state['sequence'] == 13 and claims == {}
    assert all(row['state'] == 'SUCCEEDED' for row in state['nodes'].values())
    acceptance = read(root / 'actual-acceptance.json')
    assert acceptance['integrate_receipt_sha256'] == sha(root / 'integrate.json')
    return {'run_id': package, 'sequence': 13, 'claims': {},
            'accepted_at': state['nodes']['integrate']['completed_at'],
            'integrate_receipt': ref(root / 'integrate.json'), 'acceptance': ref(root / 'actual-acceptance.json')}

assert sys.flags.optimize == 0 and not Q.exists()
packages = {name: accepted(name) for name in ('wa1-20261014', 'hd2-20261014', 'gd3-20261014',
             'rp1-20261014', 'rs-owner2-20261014', 'er1-20261014', 'hp10-20261014')}
base = F / '.agents/runtime/rs-owner2-20261014'
suite_path = base / 'active-application/destination-full-r1.json'
suite = read(suite_path)
assert read(base / 'integrate.json')['result']['destination_suite_sha256'] == sha(suite_path)
assert type(suite['tests_run']) is int and suite['tests_run'] == 1416
assert all(type(suite[key]) is int and suite[key] == 0 for key in ('failures', 'errors', 'skips', 'exit_status'))
assert suite['expected_ids'] == suite['executed_ids'] and len(set(suite['executed_ids'])) == 1416
assert suite['native_census']['exit_status'] == 0 and suite['native_census']['result']['clear'] is True
assert sha(base / 'active-application/destination-full-r1.txt') == suite['output_sha256']
assert suite['before_hashes'] == suite['after_hashes'] and len(suite['after_hashes']) == 286
assert len(suite['imports']) == 74
assert all(sha(F / relative) == value for relative, value in suite['after_hashes'].items())
destination = base / 'independent-destination/destination-review.json'
assert read(destination)['decision'] == 'approved' and read(destination)['destination_suite_sha256'] == sha(suite_path)
rb = F / '.agents/runtime/rb-task1-20261014'
rb_state, rb_claims = read(rb / 'rb-task1-20261014/state.json'), read(rb / 'rb-task1-20261014/claims.json')
assert rb_state['nodes']['review']['state'] == 'SUCCEEDED' and rb_claims == {}
observed = now()
suite_summary = {'evidence': str(suite_path.relative_to(F)).replace('\\', '/'), 'sha256': sha(suite_path),
    'passed': 1416, 'failures': 0, 'errors': 0, 'skipped': 0,
    'scope': 'ALL_CURRENT_CONTRACT_TEST_FILES_AT_RS_OWNER2_ACCEPTED_SOURCE_CUT',
    'complete_contract_suite': True, 'whole_product_acceptance': False,
    'source_root': str(F), 'source_payloads': 286, 'actual_source_modules': 74,
    'source_binding': ref(base / 'active-application/JOINED-SOURCE.json'),
    'source_ledger': packages['rs-owner2-20261014'], 'independent_destination_review': ref(destination)}
facts = {'recorded_at': observed, 'authoritative_repository': str(F), 'display_identity': 'Project-AI: CETA',
    'Git_HEAD': '8ac404cdb2dd64c2dae974fbd25e13975b09295b', 'branch': 'build/standalone',
    'accepted_source_integrations': ['APP3', 'BR1', 'WA1', 'HD2', 'GD3', 'RP1', 'RS-owner2'],
    'source_payloads': 286, 'product_modules': 74, 'current_scoped_tests': suite_summary,
    'accepted_package_ledgers': packages,
    'reservation_integrated_LOC': read(base / 'root-integration/executable-source-and-test-delta.json'),
    'budget_candidate': {'run_id': 'rb-task1-20261014', 'state': 'IMPLEMENT_AND_DISTINCT_REVIEW_SUCCEEDED_SOURCE_INTEGRATION_PENDING',
        'manifest': ref(F / '.agents/rb-task1-20261014/TRANSFER-MANIFEST.json'),
        'independent_review': ref(rb / 'independent-root-review/review.json'), 'independent_tests': 211,
        'Source_application': False, 'whole_unit_completion': False},
    'environment_follow_up': ['ER1 accepted:27 launcher repairs and exact3601 ordinary E3 files qualified',
        'PySide6 aggregate distribution metadata remains unavailable; actual Qt Essentials/modules are qualified',
        'Directory size observations vary across API methods; original missing author after-tree cause remains unresolved'],
    'history_capture': {'state': 'PARTIAL_SOURCE_AND_RELEVANT_BRANCH_CONSOLIDATION_PENDING',
        'held_installer_or_cache_entries': ['W043', 'W044', 'W045'],
        'operational_tool': packages['hp10-20261014'], 'tool_acceptance_activates_capture': False},
    'remaining_product_requirements': ['Complete authorized relevant source and branch-history consolidation',
        'Integrate reviewed budget and performance candidates with full joined regressions',
        'Physical resource provisioning and authenticated clock/principal/current-view/cleanup interfaces',
        'Public application/IPC and controlled workload/effect lifecycle integration',
        'Model runtime, accelerator/inference accounting and useful reasoning qualification',
        'All remaining specified acceptance cases, installed offline operation, endurance and human acceptance'],
    'status_scope': 'EXACT_RECORDED_SOURCE_AND_LEDGER_STATE;GLOBAL_PRODUCT_REQUIREMENT_GATES_RETAINED'}
perf_root = F / '.agents/runtime/perf1-20261014'
if (perf_root / 'perf1-20261014/state.json').exists():
    perf_state = read(perf_root / 'perf1-20261014/state.json')
    facts['performance_candidate'] = {'run_id': 'perf1-20261014', 'sequence_at_observation': perf_state['sequence'],
        'states_at_observation': {name: row['state'] for name, row in perf_state['nodes'].items()},
        'Source_application': False}
    perf_manifest = F / '.agents/perf1-20261014/TRANSFER-MANIFEST.json'
    if perf_manifest.exists():
        facts['performance_candidate']['manifest'] = ref(perf_manifest)
Q.mkdir()
sys.path.insert(0, r'T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce')
from taar.orchestration_runtime import _snapshot_workspace, _changed_files
from taar.orchestration_receipts import validate_receipt
invoke('run-init', ['run', 'init', '--root', 'T:\\', '--scope', str(Q), '--run-id', RUN])
for node in ('discover', 'plan'):
    invoke(node + '-claim', ['node', 'claim', RUN, node, '--executor', '/root', '--workspace', str(Q)])
    claim = read(R / RUN / 'claims.json')[node]
    receipt = {'schema_version': 1, 'run_id': RUN, 'node_id': node, 'executor_id': '/root',
        'started_at': claim['claimed_at'], 'finished_at': now(), 'input_hash': claim['input_hash'], 'changed_files': [],
        'result': {'scope': 'TWO_PROGRESS_AND_CONTINUITY_JSON_FILES', 'accepted_source_cut': packages['rs-owner2-20261014'],
                   'preserve': 'All prior observations, dirty originals, global states and requirement/package statuses'},
        'commands': [{'command': 'Inspect status readers and exact accepted source/ledger evidence', 'exit_status': 0}],
        'validations': [{'name': 'accepted_source_and_ledger_bound', 'passed': True}], 'exit_status': 0}
    kwargs = {'run_id': RUN, 'node_id': node, 'executor_id': '/root', 'input_hash': claim['input_hash'],
              'claimed_at': claim['claimed_at'], 'node': read(R / RUN / 'graph.json')['graph']['nodes'][node]}
    validate_receipt(receipt, **kwargs); save(R / (node + '.json'), receipt)
    invoke(node + '-complete', ['node', 'complete', RUN, node, str(R / (node + '.json'))])
invoke('implement-claim', ['node', 'claim', RUN, 'implement', '--executor', '/root', '--workspace', str(Q)])
claim = read(R / RUN / 'claims.json')['implement']
rows = []
for relative in ('build/progress.json', 'handoff/continuity.json'):
    original = (F / relative).read_bytes()
    prior = json.loads(original)
    candidate = copy.deepcopy(prior)
    history = candidate.setdefault('repository_execution_history_20261014', [])
    history.append({'preserved_at': observed, 'previous_current_observation': copy.deepcopy(prior['current_repository_execution_20261014'])})
    candidate['current_repository_execution_20261014'] = copy.deepcopy(facts)
    allowed = {'repository_execution_history_20261014', 'current_repository_execution_20261014'}
    if relative == 'handoff/continuity.json':
        preserved = candidate.setdefault('historical_fields_before_ct3_20261014', {})
        for key in ('latest_source_tests', 'latest_source_integrity', 'next_action', 'current_deliverable',
                    'current_increment_tests', 'latest_increment_working_record', 'latest_state_check_freshness'):
            preserved[key] = copy.deepcopy(prior[key])
        candidate['latest_source_tests'] = copy.deepcopy(suite_summary)
        candidate['latest_source_integrity'] = {'evidence': ref(base / 'active-application/JOINED-SOURCE.json'),
            'source_hashes': 286, 'actual_modules': 74, 'Source_ledger': packages['rs-owner2-20261014'],
            'qualification': 'Exact accepted code cut; metadata publication is a subsequent separately reviewed two-path update'}
        candidate['next_action'] = 'Integrate reviewed task-budget and performance candidates; implement the next dependency-ready code package and native owner interfaces; continue authorized source/history consolidation with current evidence.'
        candidate['current_deliverable'] = 'Project-AI: CETA accepted resource reservation accounting on the current local Source;1416 contract tests,286 payload hashes,74 modules; task-budget and performance candidates await integration; installed and whole-product qualification remain open.'
        candidate['current_increment_tests'] = '1416_CURRENT_SOURCE_CONTRACT_CASES_PASSED_ZERO_FAILURE_ERROR_SKIP_AT_RS_OWNER2_ACCEPTED_CUT;WHOLE_PRODUCT_ACCEPTANCE_OPEN'
        candidate['latest_increment_working_record'] = str((base / 'actual-acceptance.json').relative_to(F)).replace('\\', '/')
        candidate['latest_state_check_freshness'] = 'EXECUTED_RS_OWNER2_INTEGRATION_ALL_SIX_SUCCEEDED_SEQUENCE13_CLAIMS_EMPTY_AT_' + observed
        allowed.update({'historical_fields_before_ct3_20261014', 'latest_source_tests', 'latest_source_integrity', 'next_action',
                        'current_deliverable', 'current_increment_tests', 'latest_increment_working_record', 'latest_state_check_freshness'})
    assert all(candidate[key] == value for key, value in prior.items() if key not in allowed)
    assert set(candidate) - set(prior) <= allowed
    assert history[-1]['previous_current_observation'] == prior['current_repository_execution_20261014']
    before = R / 'before' / relative; before.parent.mkdir(parents=True, exist_ok=True)
    with before.open('xb') as stream:
        stream.write(original)
    save(Q / relative, candidate)
    stat = (F / relative).stat()
    rows.append({'relative_path': relative, 'active_before_sha256': sha(before), 'candidate_sha256': sha(Q / relative),
        'allowed_changed_keys': sorted(allowed), 'application_action': 'EXTEND_PRESERVE_BEFORE_IMAGE',
        'source_native_identity': {'device': stat.st_dev, 'inode': stat.st_ino, 'mode': stat.st_mode,
            'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns, 'attributes': stat.st_file_attributes}})
    assert (F / relative).read_bytes() == original
save(Q / 'TRANSFER-MANIFEST.json', {'schema_version': 'ceta.current-status.v1', 'author': '/root',
    'source_root': str(F), 'candidate_root': str(Q), 'payloads': rows,
    'application_paths': sorted(row['relative_path'] for row in rows), 'runtime_code_changes': 0,
    'global_gate_or_requirement_changes': 0, 'earlier_observations_preserved': True,
    'source_suite': ref(suite_path), 'accepted_source_ledger': packages['rs-owner2-20261014'],
    'candidate_state': 'PENDING_DISTINCT_REVIEW'})
changed = _changed_files(claim['baseline_snapshot'], _snapshot_workspace(Q, Path('T:/')))
assert len(changed) == 3
receipt = {'schema_version': 1, 'run_id': RUN, 'node_id': 'implement', 'executor_id': '/root',
    'started_at': claim['claimed_at'], 'finished_at': now(), 'input_hash': claim['input_hash'], 'changed_files': changed,
    'result': {'manifest_sha256': sha(Q / 'TRANSFER-MANIFEST.json'), 'runtime_code_changes': 0,
        'Source_application': False, 'current_source_tests': 1416, 'historical_observations_preserved': True},
    'commands': [{'command': 'Exact pinned two-JSON transformation; every nonapproved prior top-level key equal and current Source286 hashes retained', 'exit_status': 0}],
    'validations': [{'name': name, 'passed': True} for name in ('all_global_axes_preserved',
        'old_current_observation_preserved_exact', 'new_source_and_actual_ledgers_bound')], 'exit_status': 0}
validate_receipt(receipt, run_id=RUN, node_id='implement', executor_id='/root', input_hash=claim['input_hash'],
    claimed_at=claim['claimed_at'], node=read(R / RUN / 'graph.json')['graph']['nodes']['implement'])
save(R / 'implement.json', receipt)
invoke('implement-complete', ['node', 'complete', RUN, 'implement', str(R / 'implement.json')])
assert read(R / RUN / 'claims.json') == {} and read(R / RUN / 'state.json')['nodes']['review']['state'] == 'READY'
print(json.dumps({'implement': 'SUCCEEDED', 'paths': 2, 'manifest_sha256': sha(Q / 'TRANSFER-MANIFEST.json')}), flush=True)
