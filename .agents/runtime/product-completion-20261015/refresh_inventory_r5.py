"""One current-state successor to reviewed r4; no product execution or publication."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import copy
import hashlib
import importlib.util
import json

F = Path('T:/00-Active/Project-AI-CETA')
R = F / '.agents/runtime/product-completion-20261015'
D = R / 'qualified-r5'
J = F / '.agents/runtime/js7-20261015'
A = J / 'amendment-fixture1'
N = F / '.agents/runtime/fn6-20261015/native-readiness/attempt-35f87ff04a88447aab3d4055d55b86a4'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


# Reuse the reviewed inventory reader and renderer. Neither main is invoked.
io = module('inventory_read_only_helpers_r5', R / 'refresh_inventory_r4.py')
read, load, digest = io.read, io.load, io.digest


def write(name, value):
    with (D / name).open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def proof(ref):
    path = F / ref['repository_relative_path']
    return load(path, ref['sha256'])


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


started = datetime.now(timezone.utc).isoformat()
if D.exists():
    raise FileExistsError('Immutable successor destination already exists')
x, predecessor = load(R / 'qualified-r4/COMPLETION-INVENTORY.json', '26e85643ade2a47598a90a84bc5e8ae26a19cb0c3e1651d5663f8a7dccef8e86')
original = copy.deepcopy(x)
prior_review, prior_review_ref = load(F / '.agents/runtime/product-completion-review-20261015/review.json',
    '3633174bcd6a47a9afd1269fb1a414ccd14a626e908f3c8faef8f47c58c669af')
assert prior_review['decision'] == 'approved'
b, bref = load(A / 'ACCEPTED-SOURCE-BASELINE.json', 'bd7af13da30e54aa916696cb9c4dbcd32539e2600e0fdc02f8af56f63d47fbbf')
m, mref = proof(b['manifest'])
amend, amend_ref = proof(b['amendment'])
assert b['Source_accepted'] is True and b['full_product_complete'] is False
assert type(b['Source_payloads']) is int and b['Source_payloads'] == 295
assert b['live_isolation_accepted'] is b['genuine_owner_effect_accepted'] is False
assert mref['sha256'] == '2386d1eb5eb7543627eca824124e797823be8a22508c8b82089a44490a69fed4'
assert amend_ref['sha256'] == 'ab391fa1ef44c76bbbe5347b4ad114e16b64e87fa856ed8c57073d3f1af7fad2'
effective = b['effective_payload_hashes']
assert effective == amend['expected_payload_hashes'] and len(effective) == 295
assert [n for n in effective if effective[n] != m['expected_payload_hashes'][n]] == [amend['changed_path']]
assert b['application_paths'] == m['application_paths'] and len(b['application_paths']) == 15
state, state_ref = load(J / 'js7-20261015/state.json')
claims, claims_ref = load(J / 'js7-20261015/claims.json')
six = {'discover', 'plan', 'implement', 'review', 'validate', 'integrate'}
assert type(state['sequence']) is int and state['sequence'] == 13 and claims == {}
assert set(state['nodes']) == six and all(state['nodes'][n]['state'] == 'SUCCEEDED' and state['nodes'][n]['claim'] is None for n in six)
local, local_ref = proof(b['integrate'])
assert local_ref['sha256'] == 'b309260af746777cf4a02bcfca34c728f3b7f77d1117271439b47d9220b4df1f'
stored, stored_ref = load(J / 'js7-20261015/receipts/integrate.json')
envelope, envelope_ref = load(J / 'js7-20261015/results/integrate.json')
assert len(local) == 12 and len(stored) == 15 and set(stored) == set(local) | {'receipt_hash', 'git_baseline', 'observed_git'}
assert {k: stored[k] for k in local} == local
fingerprint = digest(canonical({k: v for k, v in stored.items() if k != 'receipt_hash'}))
node = state['nodes']['integrate']
assert fingerprint == stored['receipt_hash'] == node['receipt_hash'] == b['integrate_fingerprint']
assert set(envelope) == {'node_id', 'receipt_hash', 'result'} and envelope == {'node_id': 'integrate', 'receipt_hash': fingerprint, 'result': local['result']}
assert local['executor_id'] == node['executor_id'] == '/root' and node['workspace'] == str(F)
assert node['validation_passed'] is True and node['receipt_ref'] == 'receipts/integrate.json'
assert local['result']['Source_accepted'] is True and local['result']['effective_payload_hashes'] == effective
assert type(local['exit_status']) is int and local['exit_status'] == 0
assert b['actual_sequence'] == 13 and b['claims'] == {} and b['all_six_states'] == {n: 'SUCCEEDED' for n in six}
chain = {}
for name in ('original_application', 'repair_application', 'original_candidate_full', 'original_candidate_launch',
             'failed_destination_full', 'failed_destination_launch', 'destination_full', 'destination_full_launch',
             'delivered_review', 'completion_helper_review'):
    value, fact = proof(b[name])
    chain[name] = {'record': value, 'source': fact}
full = chain['destination_full']['record']
assert full['tests_run'] == 1556 and all(type(full[k]) is int and full[k] == 0 for k in ('failures', 'errors', 'skips', 'exit_status'))
assert full['expected_ids'] == full['executed_ids'] == full['stopped_ids'] and full['remaining_threads'] == []
assert full['expected_payload_hashes'] == full['before_hashes'] == full['after_hashes'] == effective
outer = chain['destination_full_launch']['record']
assert type(outer['exit_status']) is int and outer['exit_status'] == 0
assert set(outer['record']['native_owner_after']) == {'closed', 'process_closed', 'thread_closed', 'job_closed', 'startup_handles_closed'}
assert all(value is True for value in outer['record']['native_owner_after'].values())
delivered = chain['delivered_review']['record']
assert delivered['decision'] == 'approved' and delivered['reviewer'] == '/root/wt1_reviewer'
assert delivered['tests_run'] == 166 and delivered['exit_status'] == 0 and delivered['owned_resources_closed'] is True
assert delivered['remaining_threads'] == delivered['remaining_resources'] == [] and delivered['expected_payload_hashes'] == effective
assert chain['failed_destination_full']['record']['failures'] == 2 and chain['failed_destination_full']['record']['exit_status'] == 1

comparison = {}
for rel, expected in effective.items():
    raw, fact = read(F / rel, expected)
    native = b['source'][rel]['native_identity']
    assert fact['python_lstat'] == {'st_dev': native['device'], 'st_ino': native['inode'], 'st_size': native['bytes'], 'st_mtime_ns': native['mtime_ns']}
    comparison[rel] = {'expected_sha256': expected, 'observed': fact, 'matches': True}
prefix = '00-Active/Project-AI-CETA/'
assert local['changed_files'] == node['changed_files'] == [prefix + n for n in m['application_paths']]
assert node['artifact_hash'] == digest(canonical({prefix + n: effective[n] for n in m['application_paths']}))
native, nref = load(N / 'c/RESULT.json', 'f486003ad5702288a7e7954aa17ca8984b3247b8077d79ec2ade4c40946eb447')
supervision, supref = load(N / 'SUPERVISION-RESULT.json', 'd79885a34e245dc4c85a16eb8d2b5928c91e5f358d2affc5ce00cf4220427361')
assert native['tests_run'] == 7 and native['failures'] == 1 and native['errors'] == native['skips'] == 0 and native['exit_status'] == 1
assert native['expected_ids'] == native['executed_ids'] == native['stopped_ids']
failure_id = native['failure_details'][0]['id']
assert failure_id.endswith('test_actual_canonical_stop_during_capacity_keeps_prepared_permit_and_zero_set')
timing = native['post_rejection_timing_diagnostics'][0]['timing']['records'][0]
assert timing['phase'] == 'CAPACITY' and timing['elapsed_ns'] == 61385300 and timing['bound_ns'] == 50000000
failed_receipt = next(r for r in native['native_admission_receipts'] if r['test_id'] == failure_id)
assert failed_receipt['class15_calls'] == []
resources = native['native_resources']
assert len(resources['owners']) == len(resources['journals']) == len(resources['clocks']) == 8
assert all(r['exact_native_retirement'] is True for r in resources['owners'])
assert all(r['exact_connection_closed_getter'] is True for r in resources['journals'])
assert all(r['state'] == 'CLOSED' and r['sampler_alive'] is False for r in resources['clocks'])
assert resources['owned_resources_closed'] is True and resources['remaining_handles'] == resources['remaining_registrations'] == native['remaining_threads'] == []
assert all(v is True for v in supervision['record']['native_owner_after'].values()) and supervision['record']['retirement_error'] is None

x['historical_source_observations'] = x.get('historical_source_observations', []) + [{
    'inventory': predecessor, 'accepted_source': copy.deepcopy(x['accepted_source']),
    'current_source_publication': copy.deepcopy(x['current_source_publication']),
    'limit': 'Exact reviewed r4 historical observation: CT4 accepted290; JS7 published295 and original destination failed. Preserved, not relabelled.'}]
x['accepted_source'] = {'record': b, 'source': bref, 'status': 'ACCEPTED_JS7_AMENDED_SOURCE295',
    'current_payload_comparison': comparison, 'all_expected_payloads_match': True,
    'actual_all_six_stage_acceptance': {'sequence': 13, 'claims': {}, 'states': b['all_six_states'],
        'state': state_ref, 'claims_source': claims_ref, 'integrate': local_ref, 'persisted_integrate': stored_ref,
        'result_envelope': envelope_ref, 'official_augmented_fingerprint': fingerprint},
    'limit': 'Scoped fifteen-path source integration plus explicit one-test-fixture amendment. No subsystem/full-product/native-owner authority completion.'}
x['current_source_publication'] = {'status': 'ACCEPTED_JS7_AMENDED_SOURCE295', 'source_root': str(F), 'payloads': 295,
    'manifest': mref, 'amendment': amend_ref, 'accepted_baseline': bref, 'application': chain['original_application']['source'],
    'repair_application': chain['repair_application']['source'], 'current_payload_comparison': comparison,
    'all_expected_payloads_match': True, 'destination_full': chain['destination_full']['source'],
    'destination_full_launch': chain['destination_full_launch']['source'], 'delivered_review': chain['delivered_review']['source'],
    'actual_integration': x['accepted_source']['actual_all_six_stage_acceptance'], 'accepted_source_baseline_created': True,
    'Source_accepted': True, 'failed_destination_full_preserved': chain['failed_destination_full']['source'],
    'original_candidate_evidence_is_original_cut_only': True, 'full_product_complete': False}
for item in x['current_source_code_index']:
    rel = Path(item['source']['path']).relative_to(F).as_posix()
    item['source'] = comparison[rel]['observed']
    item['source_cut_status'] = 'ACCEPTED_JS7_AMENDED_SOURCE295'
for c in x['canonical_components']:
    prefix_path = str(F / c['original']['path']) + '\\'
    c['actual_implementation'] = [q for q in x['current_source_code_index'] if q['source']['path'].startswith(prefix_path)]
    c['implementation_evidence'] = {'current_code': c['actual_implementation'], 'source_cut_status': 'ACCEPTED_JS7_AMENDED_SOURCE295',
        'accepted_source_reference': bref, 'limits': 'Source code presence only; original component semantics and acceptance remain unclosed.'}
for row in x['requirements']:
    row['implementation_evidence'].pop('previous_accepted_baseline', None)
    row['implementation_evidence']['source_cut_status'] = 'ACCEPTED_JS7_AMENDED_SOURCE295'
    row['implementation_evidence']['accepted_source_reference'] = bref
    row['implementation_assessment']['scope'] = 'Exact accepted JS7 amended Source295 observation. FN6 and private successors remain separate; original requirement acceptance unchanged.'
first, join = x['remaining_critical_path'][:2]
first.update(status='CLOSED_SCOPED_JS7_SOURCE_PUBLICATION_AND_DELIVERED_ACCEPTANCE',
    blocker='No remaining blocker for the exact JS7 fifteen-path publication plus reviewed fixture correction. This does not close parent WP-00/WP-01/G-A or the production authorization-to-effect chain.',
    next='Continue the separately reviewed native/authority join after repairing its measured CAPACITY Stop-versus-timeout denial precedence; retain every unclosed product requirement.',
    evidence={'accepted_baseline': bref, 'manifest': mref, 'amendment': amend_ref, 'integrate': local_ref,
        'actual_sequence': 13, 'claims': {}, 'destination_full': chain['destination_full']['source'],
        'delivered_review': chain['delivered_review']['source'], 'original_failed_full': chain['failed_destination_full']['source']},
    assessment_kind='SCOPED_SOURCE_INTEGRATION_ACCEPTED; ORIGINAL_PARENT_REQUIREMENTS_REMAIN_OPEN')
native_summary = {'result': nref, 'supervision': supref, 'tests_run': 7, 'passed': 6, 'failures': 1, 'errors': 0, 'skips': 0,
    'failure_id': failure_id, 'actual_denial': 'CPU_EXECUTION_OWNER_TOO_SLOW', 'expected_denial': 'CPU_EXECUTION_STOPPED',
    'measured_phase': 'CAPACITY', 'elapsed_ns': 61385300, 'bound_ns': 50000000, 'failed_case_class15_calls': [],
    'retirement': {'owners': 8, 'journals': 8, 'clocks': 8, 'all_retired': True, 'outer_retired': True, 'remaining_threads': []},
    'authority_limit': 'Actual owned-medium-worker/native CPU fixture qualification with controlled authority/capacity, not genuine human approval, restricted isolation, Source or public-runtime acceptance.'}
join.update(status='BLOCKED_FN6_NATIVE_CAPACITY_STOP_DENIAL_PRECEDENCE',
    blocker='The original seven native methods ran once: six passed, one failed. A latched Stop during CAPACITY was masked by CPU_EXECUTION_OWNER_TOO_SLOW after61385300ns against50000000ns. The failed case made zero class15 Set calls. All eight captured owners/journals/clocks and the outer were retired. FN6 is private and unaccepted for Source integration.',
    next='Review the private JS8 join and explicit denial-precedence repair when frozen, preserving the unchanged Stop assertion,50ms bound and original failed native evidence; satisfy the remaining native/connected/full/delivered and current accepted-source join gates before Source publication/acceptance.',
    evidence=native_summary, assessment_kind='OBSERVED_NATIVE_DENIAL_PRECEDENCE_FAILURE; REPAIR_PRIVATE_PENDING_REVIEW')
join['private_successor'] = {'name': 'JS8', 'reported_by': 'Root current task instruction', 'state': 'PRIVATE_PREPARATION_NOT_ACCEPTED',
    'scope': 'Join plus explicit denial-precedence repair', 'implementation_or_acceptance_not_inferred': True}
x['latest_native_join_qualification'] = native_summary
for c in x['candidate_catalog']:
    if c['run_id'] == 'js7-20261015':
        c['current_source_publication_observation'] = {'published': True, 'Source_accepted': True, 'manifest': mref,
            'amendment': amend_ref, 'baseline': bref, 'integrate': local_ref, 'sequence': 13, 'claims': {},
            'limits': 'Exact selected source delta accepted; original parent/subsystem/full-product gates remain open.'}
    elif c['run_id'] == 'fn6-20261015':
        c['latest_native_qualification'] = native_summary
x['observed_at'] = started
x['coverage_cardinalities']['source_payloads_in_accepted_baseline'] = 295
x['coverage_cardinalities']['published_source_payloads'] = 295
x['interpretation_limits'] = [s.replace(
    'CT4 remains the previous accepted290 baseline. Actual JS7 Source295 is published but unaccepted after two destination fixture assertions. FN6 is candidate-only. Current and historical observations remain separately source-bound.',
    'JS7 amended Source295 is now the recorded accepted baseline. CT4 and the original failed destination remain historical. FN6 native qualification failed one denial-precedence assertion and remains private; JS8 preparation is not accepted. Current observations are time-bound and scoped.') for s in x['interpretation_limits']]
x['collaborative_review'] = {'state': 'PENDING_ROOT_AND_DISTINCT_REVIEW_OF_R5', 'predecessor_review': prior_review_ref,
    'changes_after_review': 'NEW IMMUTABLE SUCCESSOR ONLY'}
x['inventory_revision'] = {'prepared_at': started, 'predecessor': predecessor, 'predecessor_review': prior_review_ref,
    'changes': ['Authenticate actual accepted JS7 amended295 baseline and terminal13/all6SUCCEEDED/claims{}.',
        'Preserve CT4/r4/original failed destination as historical; update current source evidence and scoped publication closure only.',
        'Bind the actual FN6 seven-case denial-precedence failure/retirement; JS8 remains private and unaccepted.'],
    'remaining_limit': 'All original product requirements,25 subsystems, semantic conjunct/code/oracle gaps and authorization/application/model/runtime/installed/endurance/human acceptance blockers remain.'}
x['authoritative_inventory_path'] = str(D / 'COMPLETION-INVENTORY.json')
for rel, row in comparison.items():
    _, after = read(F / rel, row['expected_sha256'])
    assert after['python_lstat'] == row['observed']['python_lstat']
x['source_read_conservation'] = {'observed_start': started, 'observed_end': datetime.now(timezone.utc).isoformat(),
    'ordinary_accepted_source_payloads': 295, 'changed_inputs': [], 'stable_accepted_source_read_bytes': True,
    'Source_accepted': True, 'historical_normative_sources': 'Preserved original normative observations, not rescanned or asserted continuously current.',
    'limits': 'Finite ordinary lstat/hash brackets only; no held native handles or whole-worktree/Git/E3 conservation claim. Native acceptance evidence belongs to Root/WT records.'}
# Preserve all non-state/evidence top-level data; no resplitting or new scope.
allowed = {'observed_at', 'accepted_source', 'historical_source_observations', 'current_source_publication',
    'current_source_code_index', 'canonical_components', 'requirements', 'remaining_critical_path',
    'latest_native_join_qualification', 'candidate_catalog', 'coverage_cardinalities', 'interpretation_limits',
    'collaborative_review', 'inventory_revision', 'authoritative_inventory_path', 'source_read_conservation'}
assert all(x[k] == original[k] for k in original if k not in allowed)
assert x['remaining_critical_path'][2:] == original['remaining_critical_path'][2:]
assert [r['original'] for r in x['requirements']] == [r['original'] for r in original['requirements']]
assert x['native_subsystems'] == original['native_subsystems'] and len(x['native_subsystems']) == 25
assert x['whole_product_complete'] is x['all_mandatory_requirements_accepted'] is False
D.mkdir(exist_ok=False)
write('COMPLETION-INVENTORY.json', x)
render = module('inventory_render_only_r5', R / 'build_inventory.py').render
rendered = render(x).replace('## Complete r6 source-location ledger', '## r6 provenance appendix — no additional work items')
rendered = rendered.replace('Every nonblank line is retained verbatim below. Original identifiers are preserved. Locators are source references, not invented normative clause IDs. Semantic conjunct closure and source-specific acceptance remain open.',
    'Every nonblank line is retained as provenance. Headings, metadata, formatting, examples and context create no coding task. Original identified obligations and unresolved semantic mapping remain explicit.')
summary = ('Current accepted source: **JS7 amended295**, actual all-six SUCCEEDED, sequence13, claims empty. The earlier CT4 baseline and failed destination are retained as history. '
    'Next integration blocker: FN6 CAPACITY Stop denial was masked by OWNER_TOO_SLOW at61,385,300ns against50,000,000ns; failed case zero Set and all captured resources retired. '
    'Private JS8 repair is not accepted. Full-product acceptance remains unverified.\n\n')
rendered = rendered.replace('## Accepted source and active work\n\n', '## Accepted source and active work\n\n' + summary)
with (D / 'COMPLETION-INVENTORY.md').open('x', encoding='utf8') as stream:
    stream.write(rendered)
write('REFRESH-RESULT.json', {'at': datetime.now(timezone.utc).isoformat(), 'exit_status': 0,
    'predecessor': predecessor, 'baseline': bref, 'amendment': amend_ref, 'integrate': local_ref,
    'JSON_sha256': digest((D / 'COMPLETION-INVENTORY.json').read_bytes()),
    'render_sha256': digest((D / 'COMPLETION-INVENTORY.md').read_bytes()),
    'Source_payloads': 295, 'sequence': 13, 'claims': {}, 'original_subsystems': 25,
    'changed_critical_path_entries': [0, 1], 'all_other_critical_path_entries_unchanged': True,
    'product_or_native_tests_executed': 0, 'Source_mutations': 0, 'full_product_complete': False})
print(json.dumps(load(D / 'REFRESH-RESULT.json')[0], indent=2))
