"""Finite final inventory lineage/current-state/semantic-classification checks."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
import json
import re

R=Path('T:/00-Active/Project-AI-CETA/.agents/runtime/product-completion-20261015')
D=R/'qualified-r4'
x=json.loads((D/'COMPLETION-INVENTORY.json').read_text(encoding='utf-8'))
prior=json.loads((R/'qualified-r3/COMPLETION-INVENTORY.json').read_text(encoding='utf-8'))
checks=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(name,value):
 checks.append({'name':name,'passed':bool(value)})
 if not value:raise AssertionError(name)
check('all13closure_lanes_retained',len(x['remaining_critical_path'])==13 and [r['name'] for r in x['remaining_critical_path']]==[r['name'] for r in prior['remaining_critical_path']])
for field in ['requirements','work_packages','global_gates','original_B_cases','source_lifecycle','policies','architecture_decisions','atomic_tickets']:
 check(field+'_original_records_unchanged',[r['original'] for r in x[field]]==[r['original'] for r in prior[field]])
check('all432_original_units_and4320ATs',len(x['native_units'])==432 and len({t for r in x['native_units'] for t in r['supplemental_acceptance_ids']})==4320)
check('all25_subsystems',len(x['native_subsystems'])==25)
check('all43context_documents',len(x['original_specification_documents'])==43)
for row in x['requirements']:
 ident=row['original']['id'];sections=row['detailed_specification']['sections']
 check(ident+'_only_own_definition',len(sections)==1 and ident in sections[0]['heading'] and all(s['actual_requirement_section_id']==ident for s in sections[0]['statements']))
 check(ident+'_evidence_uninspected_not_missing',row['actual_blocker']['uninspected_is_not_missing_implementation'] is True)
 check(ident+'_current_source_is_unaccepted',row['implementation_evidence']['source_cut_status']=='PUBLISHED_UNACCEPTED_SOURCE295')
count=0
def walk(v):
 global count
 if isinstance(v,dict):
  if 'record_kind' in v and ('line_number' in v or v['record_kind']=='SOURCE_SECTION_PROVENANCE'):
   count+=1
   check('source_record_is_not_minted_work_'+str(count),v['completion_work_item'] is False and all(k not in v for k in ['actual_blocker','next_executable_closure','implementation_evidence','governing_obligation']))
  for child in v.values():walk(child)
 elif isinstance(v,list):
  for child in v:walk(child)
walk(x)
pub=x['current_source_publication'];old=x['accepted_source']
check('current_publication295notaccepted290',pub['payloads']==295 and pub['status']=='PUBLISHED_295_UNACCEPTED_DESTINATION_FULL_FAILED' and pub['accepted_source_baseline_created'] is False and len(old['record']['source_hashes'])==290)
check('current_published295hashes',len(pub['current_payload_comparison'])==295 and all(r['matches'] for r in pub['current_payload_comparison'].values()))
check('old_accepted_baseline_not_current',old['all_expected_payloads_match'] is False)
check('actualclaimed12state_not_terminal_acceptance',pub['actual_integration']['state']=='RUNNING' and pub['actual_integration']['sequence']==12 and 'integrate' in pub['actual_integration']['claims'])
result=pub['actual_destination_result']
check('actual_destination2failures1556no_errors_skips',result['tests_run']==1556 and result['failures']==2 and result['errors']==0 and result['skips']==0 and result['exit_status']==1 and result['Source_accepted'] is False)
check('actual182not183failures_preserved',len(result['failure_details'])==2 and all('AssertionError: 182 != 183' in v[1] for v in result['failure_details']))
check('first_lane_exact_failure_action',all(t in x['remaining_critical_path'][0]['blocker'] for t in ['182 !=183','RUNNING12','CT4']))
check('no_effect_failure_inference','no product runtime-effect failure' in pub['failure_classification'])
lane=next(r for r in x['remaining_critical_path'] if r['name']=='Public compiler, application/model and continuing intelligence')
check('no_guessed_launcher_path','src/ceta/desktop/launcher.py' not in lane['paths'] and 'tools/ceta_operator.py' in lane['paths'] and 'src/ceta/application/task_operator.py' in lane['paths'])
check('real_launcher_main_and_compiler_seams_measured',len(lane['actual_entrypoint_evidence'])==2 and all(row['callsite_lines'] for row in lane['actual_entrypoint_evidence']))
check('real_launcher_sourcefacts_match_pins',all(sha(row['source']['path'])==row['source']['sha256'] for row in lane['actual_entrypoint_evidence']))
for key in ['application','destination_full','destination_full_launch']:
 check('actual_'+key+'_source_pin',sha(pub[key]['path'])==pub[key]['sha256'])
check('R3_source_text_and_user_rules_unchanged',x['current_user_direction_verbatim']==prior['current_user_direction_verbatim'] and [(b['line_start'],b['line_end'],b['text']) for b in x['r6']['blocks']]==[(b['line_start'],b['line_end'],b['text']) for b in prior['r6']['blocks']])
check('current_source_observation_conserved_unaccepted',x['source_read_conservation']['stable_published_source_read_bytes'] is True and x['source_read_conservation']['changed_inputs']==[] and x['source_read_conservation']['Source_accepted'] is False)
check('no_completion_promotion',x['whole_product_complete'] is False and x['all_mandatory_requirements_accepted'] is False)
report={'at':datetime.now(timezone.utc).isoformat(),'decision':'AUTHOR_FINAL_CURRENT_STATE_INVENTORY_CHECKS_PASSED',
 'exit_status':0,'checks':len(checks),'json_sha256':sha(D/'COMPLETION-INVENTORY.json'),'markdown_sha256':sha(D/'COMPLETION-INVENTORY.md'),
 'checks_detail':checks,'limits':['Inventory checks only; no native or product test was executed.',
 'Current Source295 is published/unaccepted. Previous CT4Source290 stays the accepted historical witness.',
 'Actual mutable state12 is bound to its observation time, not promised unchanged after this report.',
 'Unassessed semantic conjunct/code/oracle closure remains an explicit inventory gap, not claimed complete.']}
with (D/'VALIDATION.json').open('x',encoding='utf-8') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in report.items() if k!='checks_detail'},indent=2))
