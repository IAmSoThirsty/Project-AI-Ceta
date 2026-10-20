"""Check the concrete metadata/task and cross-requirement repair, not product behavior."""
from pathlib import Path
import hashlib
import json
import re
from datetime import datetime,timezone

R=Path('T:/00-Active/Project-AI-CETA/.agents/runtime/product-completion-20261015')
D=R/'qualified-r3'
x=json.loads((D/'COMPLETION-INVENTORY.json').read_text(encoding='utf-8'))
prior=json.loads((R/'qualified-r2/COMPLETION-INVENTORY.json').read_text(encoding='utf-8'))
checks=[]
def check(name,yes):
 checks.append({'name':name,'passed':bool(yes)})
 if not yes:raise AssertionError(name)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
check('r2_exact_frozen_predecessor',sha(R/'qualified-r2/COMPLETION-INVENTORY.json')=='746a3438b1d8cf2ff4a0d90e924a43a89dbc19715a032751cd32fb53e6900f0d')
check('all_13_existing_executable_closure_lanes_preserved',len(x['remaining_critical_path'])==13 and [v['name'] for v in x['remaining_critical_path']]==[v['name'] for v in prior['remaining_critical_path']])
check('all_original_REQ_records_unchanged',[r['original'] for r in x['requirements']]==[r['original'] for r in prior['requirements']])
check('all_original_WP_and_B_records_unchanged',[r['original'] for r in x['work_packages']]==[r['original'] for r in prior['work_packages']] and [r['original'] for r in x['original_B_cases']]==[r['original'] for r in prior['original_B_cases']])
check('five_user_rules_exact',x['current_user_direction_verbatim']==prior['current_user_direction_verbatim'])
check('all_r6_source_blocks_unchanged',[(r['line_start'],r['line_end'],r['text']) for r in x['r6']['blocks']]==[(r['line_start'],r['line_end'],r['text']) for r in prior['r6']['blocks']])
for row in x['requirements']:
 ident=row['original']['id'];sections=row['detailed_specification']['sections']
 check(ident+'_exact_own_section_only',len(sections)==1 and re.search(re.escape(ident)+r'(?![0-9-])',sections[0]['heading']) is not None)
 check(ident+'_section_owner_correct',all(s['actual_requirement_section_id']==ident for s in sections[0]['statements']))
 check(ident+'_no_foreign_REQ_definition',not any(s['text'].startswith('### REQ-') and ident not in s['text'] for s in sections[0]['statements']))
 check(ident+'_source_semantics_not_inferred_missing',row['actual_blocker']['uninspected_is_not_missing_implementation'] is True)
 check(ident+'_no_inherited_foreign_evidence',row['containing_document_is_not_per_requirement_evidence'] is True)
check('43_complete_SPEC_context_documents_preserved_once',len(x['original_specification_documents'])==43)
for path,doc in x['original_specification_documents'].items():
 original=next(r['detailed_specification'] for r in prior['requirements'] if r['detailed_specification']['source']['path']==path)
 check('full_SPEC_source_lines_retained_'+path,[(s['source_lines'],[(v['line_number'],v['text']) for v in s['statements']]) for s in doc['sections']]==[(s['source_lines'],[(v['line_number'],v['text']) for v in s['statements']]) for s in original['sections']])
metadata_count=0;examples=0;source_statements=0
def walk(o):
 global metadata_count,examples,source_statements
 if isinstance(o,dict):
  if 'record_kind' in o and ('line_number' in o or o['record_kind']=='SOURCE_SECTION_PROVENANCE'):
   source_statements+=1
   check('source_locator_never_mints_work_'+str(source_statements),o.get('completion_work_item') is False)
   check('no_generic_blocker_or_action_for_source_locator_'+str(source_statements),all(k not in o for k in ['actual_blocker','next_executable_closure','implementation_evidence','governing_obligation']))
   if o['record_kind'].endswith('PROVENANCE'):metadata_count+=1
   if 'EXAMPLE' in o['record_kind']:examples+=1
  for v in o.values():walk(v)
 elif isinstance(o,list):
  for v in o:walk(v)
walk(x)
first=x['requirements'][0]['detailed_specification']['sections'][0]
check('Root_F01_heading_is_provenance',first['statements'][0]['record_kind']=='HEADING_PROVENANCE' and first['statements'][0]['completion_work_item'] is False)
full=x['original_specification_documents'][x['requirements'][0]['detailed_specification']['source']['path']]
document_metadata=[s for sec in full['sections'] for s in sec['statements'] if '**Document ID:**' in s['text'] or '**Package edition:**' in s['text']]
check('Root_F01_document_metadata_has_no_executable_task',len(document_metadata)>=2 and all(v['record_kind']=='DOCUMENT_METADATA_PROVENANCE' for v in document_metadata))
check('PW_F02_REQ0002_definition_not_attributed_to_REQ0001',all('REQ-00-02' not in s['text'] for s in first['statements'] if s['text'].startswith('###')))
second=next(r for r in x['requirements'] if r['original']['id']=='REQ-00-02')
check('PW_F02_actual_REQ0002_body_owner_correct',all(s['actual_requirement_section_id']=='REQ-00-02' for s in second['detailed_specification']['sections'][0]['statements']))
known=x['known_native_owner_interface_gap']
names={name for f in known['facts'] for methods in f['owner_class_declared_methods'].values() for name in methods}
check('inspected_retainer_capabilities_absent_in_native_owner_class',not any(n in names for n in known['required_capabilities']))
check('inspected_canonical_capability_capture_callers_retained',all(any(n in line['text'] for f in known['facts'] for line in f['capability_callsite_lines']) for n in known['required_capabilities']))
check('historical_Source_observation_is_not_refreshed_during_publication',x['accepted_source']==prior['accepted_source'] and x['source_read_conservation']==prior['source_read_conservation'])
check('inventory_does_not_claim_semantic_mapping_finished','not a claim' in x['inventory_revision']['remaining_limit'])
result={'at':datetime.now(timezone.utc).isoformat(),'decision':'AUTHOR_SEMANTIC_CLASSIFICATION_REPAIR_CHECKS_PASSED',
 'exit_status':0,'checks':len(checks),'source_records_checked':source_statements,'metadata_records':metadata_count,'example_records':examples,
 'json_sha256':sha(D/'COMPLETION-INVENTORY.json'),'markdown_sha256':sha(D/'COMPLETION-INVENTORY.md'),
 'checks_detail':checks,'limits':['No product test, native operation or current Source equality check was run.',
 'R3 is preliminary semantic repair; final current-state cut waits actual Root acceptance.',
 'Source classification and exact defining IDs are checked. Complete semantic fulfillment of every compound requirement is not claimed.']}
with (D/'VALIDATION.json').open('x',encoding='utf-8') as s:json.dump(result,s,indent=2);s.write('\n')
print(json.dumps({k:v for k,v in result.items() if k!='checks_detail'},indent=2))
