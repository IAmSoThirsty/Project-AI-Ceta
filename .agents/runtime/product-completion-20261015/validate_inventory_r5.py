"""Existing inventory preservation and changed-current-state checks, not product tests."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json

R = Path('T:/00-Active/Project-AI-CETA/.agents/runtime/product-completion-20261015')
D = R / 'qualified-r5'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
x = json.loads((D / 'COMPLETION-INVENTORY.json').read_bytes())
prior = json.loads((R / 'qualified-r4/COMPLETION-INVENTORY.json').read_bytes())
checks = []


def check(name, value):
    checks.append({'name': name, 'passed': bool(value)})
    assert value, name


check('immutable_r4_json_retained', sha(R / 'qualified-r4/COMPLETION-INVENTORY.json') == '26e85643ade2a47598a90a84bc5e8ae26a19cb0c3e1651d5663f8a7dccef8e86')
check('immutable_r4_render_retained', sha(R / 'qualified-r4/COMPLETION-INVENTORY.md') == '83136c40e41b1d8f80cd71d0a619bfa969bbe0c5cfceef9384d7a0c01bf55a4d')
check('all25_subsystems_unchanged', len(x['native_subsystems']) == 25 and x['native_subsystems'] == prior['native_subsystems'])
for field in ('atomic_tickets', 'work_packages', 'global_gates', 'native_units', 'native_component_specifications',
              'native_interfaces', 'native_e2e_scenarios', 'native_acceptance_requirements', 'original_B_cases',
              'source_lifecycle', 'policies', 'architecture_decisions', 'source_volumes', 'canonical_routes',
              'original_specification_documents', 'r6', 'known_native_owner_interface_gap', 'current_user_direction_verbatim'):
    check(field + '_exactly_preserved', x[field] == prior[field])
check('all175_requirements_retained', len(x['requirements']) == len(prior['requirements']) == 175)
req_only_source_evidence = True
for row, old in zip(x['requirements'], prior['requirements']):
    a, b = copy.deepcopy(row), copy.deepcopy(old)
    for item in (a, b):
        item.pop('implementation_evidence')
        item['implementation_assessment'].pop('scope')
    req_only_source_evidence &= a == b
check('all_requirement_acceptance_blockers_semantic_ownership_unchanged', req_only_source_evidence)
check('all25_canonical_components_retained', len(x['canonical_components']) == len(prior['canonical_components']) == 25)
check('canonical_only_source_evidence_changed', all(
    {k: v for k, v in row.items() if k not in ('actual_implementation', 'implementation_evidence')} ==
    {k: v for k, v in old.items() if k not in ('actual_implementation', 'implementation_evidence')}
    for row, old in zip(x['canonical_components'], prior['canonical_components'])))
check('all13_critical_path_identities_retained', len(x['remaining_critical_path']) == 13 and
    [r['name'] for r in x['remaining_critical_path']] == [r['name'] for r in prior['remaining_critical_path']])
check('remaining11_original_closure_lanes_unchanged', x['remaining_critical_path'][2:] == prior['remaining_critical_path'][2:])
check('scoped_source_lane_closed_only', x['remaining_critical_path'][0]['status'] == 'CLOSED_SCOPED_JS7_SOURCE_PUBLICATION_AND_DELIVERED_ACCEPTANCE')
b = x['accepted_source']
check('exact_accepted_baseline_pin', b['source']['sha256'] == 'bd7af13da30e54aa916696cb9c4dbcd32539e2600e0fdc02f8af56f63d47fbbf')
check('exact_amended295_acceptance_scope', b['record']['Source_payloads'] == 295 and b['record']['Source_accepted'] is True and b['record']['full_product_complete'] is False and b['record']['live_isolation_accepted'] is False and b['record']['genuine_owner_effect_accepted'] is False)
accept = b['actual_all_six_stage_acceptance']
check('actual_terminal13_all6_emptyclaims', accept['sequence'] == 13 and accept['claims'] == {} and len(accept['states']) == 6 and set(accept['states'].values()) == {'SUCCEEDED'})
check('source295_map_is_explicit_amended_effective_map', len(b['current_payload_comparison']) == 295 and all(row['matches'] for row in b['current_payload_comparison'].values()) and
    {n: r['expected_sha256'] for n, r in b['current_payload_comparison'].items()} == b['record']['effective_payload_hashes'])
history = x['historical_source_observations'][-1]
check('r4_publication_failure_and_ct4_retained_verbatim', history['current_source_publication'] == prior['current_source_publication'] and history['accepted_source'] == prior['accepted_source'])
check('original_failed_destination_not_promoted', b['record']['failed_destination_full']['sha256'] == 'b427d45e9d166e82555bbe8c7f9b16671aa4c86f66bde9e8c1feb7349a15d366')
n = x['latest_native_join_qualification']
check('fn6_result_and_supervision_pins', n['result']['sha256'] == 'f486003ad5702288a7e7954aa17ca8984b3247b8077d79ec2ade4c40946eb447' and n['supervision']['sha256'] == 'd79885a34e245dc4c85a16eb8d2b5928c91e5f358d2affc5ce00cf4220427361')
check('native_failure_denial_timing_no_set_retained', n['tests_run'] == 7 and n['passed'] == 6 and n['failures'] == 1 and n['errors'] == n['skips'] == 0 and n['elapsed_ns'] == 61385300 and n['bound_ns'] == 50000000 and n['failed_case_class15_calls'] == [] and n['retirement']['all_retired'] is True and n['retirement']['outer_retired'] is True)
check('js8_not_accepted', x['remaining_critical_path'][1]['private_successor']['state'] == 'PRIVATE_PREPARATION_NOT_ACCEPTED')
check('no_product_completion_or_mandatory_gate_promotion', x['whole_product_complete'] is False and x['all_mandatory_requirements_accepted'] is False)
check('finite_source_observation_scope', x['source_read_conservation']['stable_accepted_source_read_bytes'] is True and x['source_read_conservation']['ordinary_accepted_source_payloads'] == 295 and x['source_read_conservation']['changed_inputs'] == [])
check('actual_launcher_references_preserved', x['remaining_critical_path'][5] == prior['remaining_critical_path'][5] and 'tools/ceta_operator.py' in x['remaining_critical_path'][5]['paths'])
md = (D / 'COMPLETION-INVENTORY.md').read_text(encoding='utf8')
check('render_current_baseline_and_open_native_blocker', 'Current accepted source: **JS7 amended295**' in md and '61,385,300ns against50,000,000ns' in md and 'Private JS8 repair is not accepted.' in md)
report = {'at': datetime.now(timezone.utc).isoformat(), 'decision': 'AUTHOR_BOUNDED_REFRESH_CHECKS_PASSED',
    'exit_status': 0, 'checks': len(checks), 'checks_detail': checks,
    'json_sha256': sha(D / 'COMPLETION-INVENTORY.json'), 'render_sha256': sha(D / 'COMPLETION-INVENTORY.md'),
    'limits': ['Inventory/state-preservation checks only; zero product or native tests.',
        'Original requirements, acceptance statuses, semantic granularity and remaining eleven closure lanes are unchanged.',
        'Accepted JS7 amended295 is a scoped source cut. FN6 native qualification is failed, JS8 remains private, and full-product acceptance is unverified.']}
with (D / 'VALIDATION.json').open('x', encoding='utf8') as stream:
    json.dump(report, stream, indent=2)
    stream.write('\n')
print(json.dumps({k: v for k, v in report.items() if k != 'checks_detail'}, indent=2))
