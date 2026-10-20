"""Finite checks on the one inventory; no CETA imports, effects or acceptance promotion."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
from datetime import datetime,timezone

F=Path('T:/00-Active/Project-AI-CETA')
R=F/'.agents/runtime/product-completion-20261015'
D=R/'qualified-r2'
P=D/'COMPLETION-INVENTORY.json'
x=json.loads(P.read_text(encoding='utf-8'))
checks=[]
def check(name, predicate, detail=None):
    checks.append(dict(name=name,passed=bool(predicate),detail=detail))
    if not predicate: raise AssertionError(name)
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def original_subset(actual,expected):
    if isinstance(expected,dict):
        return isinstance(actual,dict) and all(k in actual and original_subset(actual[k],v) for k,v in expected.items())
    if isinstance(expected,list):return isinstance(actual,list) and len(actual)==len(expected) and all(original_subset(a,b) for a,b in zip(actual,expected))
    return type(actual) is type(expected) and actual==expected
def reg(rel,key):return json.loads((F/rel).read_text(encoding='utf-8-sig'))[key]
for field,rel,key,expected in [
 ('requirements','requirements/requirements.json','requirements',175),
 ('atomic_tickets','requirements/atomic_tickets.json','tickets',35),
 ('work_packages','build/work_packages.json','packages',28),
 ('global_gates','build/gates.json','gates',8),
 ('original_B_cases','acceptance/scenarios.json','scenarios',128),
 ('canonical_components','architecture/components.json','components',25),
 ('source_lifecycle','standards/lifecycle_coverage.json','sections',406),
 ('policies','policies/policy_registry.json','policies',24),
 ('architecture_decisions','decisions/decision_register.json','decisions',22)]:
 original=reg(rel,key);rows=x[field]
 check(field+'_cardinality',len(rows)==len(original)==expected)
 check(field+'_original_records_preserved',all(original_subset(a['original'],b) for a,b in zip(rows,original)))
 for i,row in enumerate(rows):
    check(field+f'_row_{i}_complete',all(k in row for k in ['acceptance_status','implementation_evidence','missing_evidence','actual_blocker','next_executable_closure']))
check('all25_original_subsystems',set(r['original_id'] for r in x['native_subsystems'])=={f'{i:02}' for i in range(25)})
units=x['native_units'];check('432_unique_units',len(units)==len({u['original_id'] for u in units})==432)
ats={a for u in units for a in u['supplemental_acceptance_ids']};check('4320_original_AT_IDs',len(ats)==4320 and all(len(u['supplemental_acceptance_ids'])==10 for u in units))
check('432_original_unit_hashes',all(u['original_hash_matches'] for u in units))
check('14_numbered_sections_per_unit',all(sum(bool(re.match(r'^## \d+\.',s.get('heading') or '')) for s in u['specification']['sections'])==14 for u in units))
check('20_real_E2E_scenarios_not_README',len(x['native_e2e_scenarios'])==20 and all('/E2E-' in r['original_path'] for r in x['native_e2e_scenarios']))
check('43_native_interfaces',len(x['native_interfaces'])==43)
cards=reg('.local-build-cache/increment-31-verification-forward-plan-20261011-01/acceptance-code-plan.json','case_cards')
check('128_original_case_cards_retained',all(original_subset(a['original_case_card'],b) for a,b in zip(x['original_B_cases'],cards)))
check('803_original_variants',sum(len(v['variant_matrix']) for v in cards)==x['coverage_cardinalities']['original_planned_B_variants']==803)
r6=Path(x['r6']['source']['path']).read_text(encoding='utf-8-sig').splitlines()
kept={}
for b in x['r6']['blocks']:
 for n,line in enumerate(b['text'].splitlines(),b['line_start']):
    check(f'r6_line_{n}_exact',r6[n-1]==line)
    check(f'r6_line_{n}_unique',n not in kept);kept[n]=line
check('r6_every_nonblank_line_retained',set(kept)=={n+1 for n,s in enumerate(r6) if s.strip()})
for field in ['native_subsystems','native_units','native_interfaces','native_e2e_scenarios','native_acceptance_requirements','canonical_routes']:
 for i,row in enumerate(x[field]):
    check(field+f'_closure_row_{i}',all(k in row for k in ['acceptance_status','implementation_evidence','missing_evidence','actual_blocker','next_executable_closure']))
check('161_canonical_routes',len(x['canonical_routes'])==161)
check('20_source_volumes',len(x['source_volumes']['volumes'])==20)
check('85_candidates_no_omitted_reader_errors',len(x['candidate_catalog'])==85 and not x['inventory_errors'])
check('no_boolean_completion_or_acceptance',x['whole_product_complete'] is False and x['all_mandatory_requirements_accepted'] is False)
check('Source290_exact_at_inventory_observation',len(x['accepted_source']['current_payload_comparison'])==290 and x['accepted_source']['all_expected_payloads_match'] is True)
check('all_normative_read_bytes_conserved',x['source_read_conservation']['stable_normative_input_bytes'] is True and x['source_read_conservation']['changed_inputs']==[])
j=x['candidate_integration_join']
check('candidate_forward_join_counts',len(j['shared_equal'])==291 and len(j['shared_different'])==4 and len(j['added_by_fn6'])==57 and j['missing_from_fn6']==[] and j['js7_publication_paths_match_fn6'] is True)
check('WP21_retained_outside_WP27_ancestry',any(w['original']['id']=='WP-21' for w in x['work_packages']) and 'WP-21' not in next(w for w in x['work_packages'] if w['original']['id']=='WP-27')['original']['depends_on'])
literal=[
'Freeze the product scope. No new features, subsystems, or architectural expansions beyond what the established full-product specification requires.',
'Produce one authoritative completion inventory. All 25 subsystems, every remaining requirement, its current implementation evidence, its acceptance status, and its actual blocker. No invented percentages.',
'Put everything on one critical path. Repair source publication and integration first. Then finish the canonical authorization-to-effect chain, followed by the remaining application, model, and runtime requirements.',
'Stop using test counts as progress toward completion by themselves. Every accepted change must close a specific outstanding product requirement. Defects still get repaired, but the work must demonstrably reduce the remaining backlog.',
'Finish with the real product acceptance. Installed, offline, functioning through its intended interfaces, executing authorized operations, refusing unauthorized ones, recovering properly, and satisfying its specified endurance and human acceptance requirements.']
check('five_current_user_rules_verbatim',x['current_user_direction_verbatim']==literal)
spec=importlib.util.spec_from_file_location('inventory_render_only',R/'build_inventory.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
check('readable_rendering_derived_exactly_from_JSON',(D/'COMPLETION-INVENTORY.md').read_bytes()==m.render(x).encode('utf-8'))
check('scope_guard_rejects_old_external_path_before_probe',not any(str(v['path']).startswith('T:\\00-Active\\CETA-desktop') for v in x['source_catalog'].values()))
result=dict(recorded_at=datetime.now(timezone.utc).isoformat(),decision='AUTHOR_INVENTORY_VALIDATION_PASSED',
 exit_status=0,checks=len(checks),failures=0,json_sha256=sha(P),markdown_sha256=sha(D/'COMPLETION-INVENTORY.md'),
 generator_sha256=sha(R/'build_inventory.py'),validator_sha256=sha(Path(__file__)),
 coverage=x['coverage_cardinalities'],details=checks,
 limits=['These are inventory consistency checks, not product tests or requirement acceptance.',
 'Original records/variants retain every original key/value; added inventory annotations do not grant acceptance.',
 'Clause/source retention is exhaustive mechanically; semantic conjunct-to-code/oracle closure remains explicitly unresolved.',
 'The earlier out-of-root read and draft schema/count errors remain in preserved author failure records.'])
with (D/'VALIDATION.json').open('x',encoding='utf-8') as s: json.dump(result,s,ensure_ascii=False,indent=2);s.write('\n')
print(json.dumps({k:v for k,v in result.items() if k!='details'},indent=2))
