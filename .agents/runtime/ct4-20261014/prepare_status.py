"""Prepare reviewed baseline and continuity candidates after accepted RB and PERF delivery."""
from datetime import datetime, timezone
from pathlib import Path
import copy
import hashlib
import json
import os
import subprocess
import sys

R = Path(__file__).resolve().parent
F, RUN = R.parents[2], 'ct4-20261014'
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
             'rp1-20261014', 'rs-owner2-20261014', 'er1-20261014', 'hp10-20261014', 'rb-task1-20261014', 'perf1-20261014')}
base = F / '.agents/runtime/perf1-20261014'
suite_path = base / 'active-application/destination-full-r1.json'
suite = read(suite_path)
assert read(base / 'integrate.json')['result']['destination_suite_sha256'] == sha(suite_path)
assert type(suite['tests_run']) is int and suite['tests_run'] == 1479
assert all(type(suite[key]) is int and suite[key] == 0 for key in ('failures', 'errors', 'skips', 'exit_status'))
assert suite['expected_ids'] == suite['executed_ids'] and len(set(suite['executed_ids'])) == 1479
assert suite['native_census']['exit_status'] == 0 and suite['native_census']['result']['clear'] is True
assert sha(base / 'active-application/destination-full-r1.txt') == suite['output_sha256']
assert suite['before_hashes'] == suite['after_hashes'] and len(suite['after_hashes']) == 290
assert len(suite['imports']) == 74
assert all(sha(F / relative) == value for relative, value in suite['after_hashes'].items())
destination = base / 'independent-destination/destination-review.json'
assert read(destination)['decision'] == 'approved' and read(destination)['destination_suite_sha256'] == sha(suite_path)
rb = F / '.agents/runtime/rb-task1-20261014'
rb_state, rb_claims = read(rb / 'rb-task1-20261014/state.json'), read(rb / 'rb-task1-20261014/claims.json')
assert rb_state['nodes']['review']['state'] == 'SUCCEEDED' and rb_claims == {}
observed = now()
actual_head = subprocess.run(['git','rev-parse','HEAD'],cwd=F,capture_output=True,check=True,text=True).stdout.strip()
actual_branch = subprocess.run(['git','branch','--show-current'],cwd=F,capture_output=True,check=True,text=True).stdout.strip()
assert actual_head == '8ac404cdb2dd64c2dae974fbd25e13975b09295b' and actual_branch == 'build/standalone'

suite_summary = {'evidence': str(suite_path.relative_to(F)).replace('\\', '/'), 'sha256': sha(suite_path),
    'passed': 1479, 'failures': 0, 'errors': 0, 'skipped': 0,
    'scope': 'ALL_CURRENT_CONTRACT_TEST_FILES_AT_RB_PERF_ACCEPTED_SOURCE_CUT',
    'complete_contract_suite': True, 'whole_product_acceptance': False,
    'source_root': str(F), 'source_payloads': 290, 'actual_source_modules': 74,
    'source_binding': ref(base / 'active-application/JOINED-SOURCE.json'),
    'source_ledger': packages['perf1-20261014'], 'independent_destination_review': ref(destination)}
facts = copy.deepcopy(read(F / 'build/progress.json')['current_repository_execution_20261014'])
facts.update({'recorded_at': observed, 'Git_HEAD':actual_head,'branch':actual_branch,
    'accepted_source_integrations': ['APP3','BR1','WA1','HD2','GD3','RP1','RS-owner2','RB-task1','PERF1'],
    'source_payloads':290, 'product_modules':74, 'current_scoped_tests':suite_summary, 'accepted_package_ledgers':packages})
rs = F / '.agents/runtime/rs-owner2-20261014'
old_loc = facts['reservation_integrated_LOC']
facts['reservation_integrated_LOC'] = {'source_added':379,'source_removed':0,'tests_added':916,
    'method':old_loc['LOC_method'], 'historical_preapplication_count_proof':ref(rs/'root-integration/executable-source-and-test-delta.json'),
    'accepted_integration':packages['rs-owner2-20261014'], 'actual_completion_helper':ref(rs/'root-integration/complete_destination.py'),
    'Source_application':True}
for field, package, review_directory, independent_count in (
    ('budget_candidate','rb-task1-20261014','independent-root-review',276),
    ('performance_candidate','perf1-20261014','independent-review',384)):
    root=F/'.agents/runtime'/package
    facts[field]={'run_id':package,'state':'SOURCE_INTEGRATION_ACCEPTED','ledger':packages[package],
        'manifest':ref(F/'.agents'/package/'TRANSFER-MANIFEST.json'),
        'independent_candidate_review':ref(root/review_directory/'review.json'),
        'independent_destination_review':ref(root/'independent-destination/destination-review.json'),
        'independent_current_source_tests':independent_count,'Source_application':True,'whole_unit_completion':False}
facts['newly_integrated_LOC']={}
for name in ('rb-task1-20261014','perf1-20261014'):
    count_path=F/'.agents/runtime'/name/'root-integration/executable-source-and-test-delta.json'
    counts=read(count_path)
    facts['newly_integrated_LOC'][name]={'source_added':counts['source_added'],
        'source_removed':counts['source_removed'],'tests_added':counts['tests_added'],'method':counts['method'],
        'historical_preapplication_count_proof':ref(count_path),'accepted_integration':packages[name],
        'Source_application':True}
facts['remaining_product_requirements']=[item for item in facts['remaining_product_requirements']
    if item!='Integrate reviewed budget and performance candidates with full joined regressions']
plan=F/'.agents/runtime/real-effect-20261014'
assert sha(plan/'plan-review/IMPLEMENTATION-AND-ACCEPTANCE-PLAN.md')=='d99cbc87dd5430b6287b3a77759fd75b8cdb0276a372c9a4cca8ba1bc047119c'
assert read(plan/'independent-root-review/COLLABORATIVE-REVIEW.json')['decision']=='APPROVED_FOR_BOUNDED_ENGINEERING_IMPLEMENTATION'
wt=F/'.agents/runtime/wt1-20261014'
assert read(wt/'wt1-20261014/state.json')['nodes']['review']['state']=='FAILED'
assert read(wt/'wt1-20261014/claims.json')=={}
facts['next_major_acceptance_milestone']={'name':'Real-effect governance through the public runtime',
    'state':'ENGINEERING_IN_PROGRESS_ACCEPTANCE_NOT_RUN','plan':ref(plan/'plan-review/IMPLEMENTATION-AND-ACCEPTANCE-PLAN.md'),
    'Collaborative_Review':ref(plan/'independent-root-review/COLLABORATIVE-REVIEW.json'),
    'tasks':32,'acceptance_cases':38,'activation_gates':6,'owner_approval_required_for_positive_runtime_journey':True,
    'rejected_dependency':{'run_id':'wt1-20261014','review':ref(wt/'independent-review/review.json'),
        'defect':'Final Stop inside clock fence still permits native class15 Set; unchanged failures preserved for WT2 repair.'},
    'dependency_jobs':['WT2 final Stop repair','AC1 restrictive native worker'], 'runtime_effect_acceptance':False}
baseline={'recorded_at':observed,'source_root':str(F),'display_identity':'Project-AI: CETA','Git_HEAD':facts['Git_HEAD'],'branch':facts['branch'],
    'code_scope':'Exact290 published payloads;74 current modules; all1479 current contract cases. Metadata is a subsequent separately reviewed two-path publication.',
    'source_hashes':suite['after_hashes'],'tests':suite_summary,'accepted_integrations':packages,
    'new_source_added':409,'new_source_removed':4,'new_test_added':556,'new_methods':63,
    'next_major_acceptance_milestone':facts['next_major_acceptance_milestone'],'whole_product_acceptance':False}
save(R/'ACCEPTED-SOURCE-BASELINE.json',baseline)
facts['accepted_source_baseline']=ref(R/'ACCEPTED-SOURCE-BASELINE.json')

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
        'result': {'scope': 'TWO_PROGRESS_AND_CONTINUITY_JSON_FILES', 'accepted_source_cut': packages['perf1-20261014'],
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
        preserved = candidate.setdefault('historical_fields_before_ct4_20261014', {})
        for key in ('latest_source_tests', 'latest_source_integrity', 'next_action', 'current_deliverable',
                    'current_increment_tests', 'latest_increment_working_record', 'latest_state_check_freshness'):
            preserved[key] = copy.deepcopy(prior[key])
        candidate['latest_source_tests'] = copy.deepcopy(suite_summary)
        candidate['latest_source_integrity'] = {'evidence': ref(base / 'active-application/JOINED-SOURCE.json'),
            'source_hashes': 290, 'actual_modules': 74, 'Source_ledger': packages['perf1-20261014'],
            'qualification': 'Exact accepted code cut; metadata publication is a subsequent separately reviewed two-path update'}
        candidate['next_action'] = 'Implement the reviewed real-effect plan: repaired Stop/dispatch primitive, actual isolated worker, genuine owner/time providers, canonical retained admission, independent observation and crash reconciliation. Continue existing product/source obligations with current evidence.'
        candidate['current_deliverable'] = 'Project-AI: CETA accepted RB-task1 and PERF1 Source baseline:1479 contract cases,290 payloads,74 modules. The real-effect governance milestone is planned, reviewed and in engineering implementation.'
        candidate['current_increment_tests'] = '1479_CURRENT_SOURCE_CONTRACT_CASES_PASSED_ZERO_FAILURE_ERROR_SKIP_AT_RB_PERF_ACCEPTED_CUT;WHOLE_PRODUCT_ACCEPTANCE_OPEN'
        candidate['latest_increment_working_record'] = str((base / 'actual-acceptance.json').relative_to(F)).replace('\\', '/')
        candidate['latest_state_check_freshness'] = 'EXECUTED_RB_PERF_INTEGRATION_ALL_SIX_SUCCEEDED_SEQUENCE13_CLAIMS_EMPTY_AT_' + observed
        allowed.update({'historical_fields_before_ct4_20261014', 'latest_source_tests', 'latest_source_integrity', 'next_action',
                        'current_deliverable', 'current_increment_tests', 'latest_increment_working_record', 'latest_state_check_freshness'})
    candidate['accepted_source_baseline_20261014']=ref(R/'ACCEPTED-SOURCE-BASELINE.json')
    allowed.add('accepted_source_baseline_20261014')
    if relative=='build/progress.json':
        old_ref='handoff/source_reco3nciliation_20261006_07.md'
        repaired_ref='handoff/source_reconciliation_20261006_07.md'
        assert prior['work_packages'][1]['evidence_refs'][39]==old_ref
        assert (F/repaired_ref).is_file() and not (F/old_ref).exists()
        candidate['work_packages'][1]['evidence_refs'][39]=repaired_ref
        candidate['metadata_reference_repair_20261014']={'pointer':'/work_packages/1/evidence_refs/39',
            'before':old_ref,'after':repaired_ref,'origin':'UNESTABLISHED','preserved_current_before_image':str((R/'before'/relative).relative_to(F)).replace('\\','/'),
            'observed_drift':ref(F/'.agents/runtime/rb-task1-20261014/metadata-at-integration-preparation.json')}
        allowed.update({'work_packages','metadata_reference_repair_20261014'})
        repaired_compare=copy.deepcopy(candidate['work_packages']);repaired_compare[1]['evidence_refs'][39]=old_ref
        assert repaired_compare==prior['work_packages']
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
    'source_suite': ref(suite_path), 'accepted_source_ledger': packages['perf1-20261014'],
    'candidate_state': 'PENDING_DISTINCT_REVIEW'})
changed = _changed_files(claim['baseline_snapshot'], _snapshot_workspace(Q, Path('T:/')))
assert len(changed) == 3
receipt = {'schema_version': 1, 'run_id': RUN, 'node_id': 'implement', 'executor_id': '/root',
    'started_at': claim['claimed_at'], 'finished_at': now(), 'input_hash': claim['input_hash'], 'changed_files': changed,
    'result': {'manifest_sha256': sha(Q / 'TRANSFER-MANIFEST.json'), 'runtime_code_changes': 0,
        'Source_application': False, 'current_source_tests': 1479, 'baseline_sha256':sha(R/'ACCEPTED-SOURCE-BASELINE.json'), 'historical_observations_preserved': True},
    'commands': [{'command': 'Exact pinned two-JSON transformation; every nonapproved prior top-level key equal and current Source290 hashes retained', 'exit_status': 0}],
    'validations': [{'name': name, 'passed': True} for name in ('all_global_axes_preserved',
        'old_current_observation_preserved_exact', 'new_source_and_actual_ledgers_bound')], 'exit_status': 0}
validate_receipt(receipt, run_id=RUN, node_id='implement', executor_id='/root', input_hash=claim['input_hash'],
    claimed_at=claim['claimed_at'], node=read(R / RUN / 'graph.json')['graph']['nodes']['implement'])
save(R / 'implement.json', receipt)
invoke('implement-complete', ['node', 'complete', RUN, 'implement', str(R / 'implement.json')])
assert read(R / RUN / 'claims.json') == {} and read(R / RUN / 'state.json')['nodes']['review']['state'] == 'READY'
print(json.dumps({'implement': 'SUCCEEDED', 'paths': 2, 'manifest_sha256': sha(Q / 'TRANSFER-MANIFEST.json')}), flush=True)
