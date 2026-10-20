"""Observe the published but unaccepted JS7 cut and its actual destination blocker."""
from pathlib import Path
from datetime import datetime,timezone
import ast
import hashlib
import importlib.util
import json
import re

F=Path('T:/00-Active/Project-AI-CETA')
R=F/'.agents/runtime/product-completion-20261015'
D=R/'qualified-r4'
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
io=module('inventory_read_only_helpers',R/'refresh_inventory_r4.py')
read,load=io.read,io.load
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(name,value):
 with (D/name).open('x',encoding='utf-8') as s:json.dump(value,s,ensure_ascii=False,indent=2);s.write('\n')

started=datetime.now(timezone.utc).isoformat()
x,prior=load(R/'qualified-r3/COMPLETION-INVENTORY.json','1705a584b8bda52128ca04282929ae45aae6e75a807b57145992401e94c63067')
m,mref=load(F/'.agents/js7-20261015/TRANSFER-MANIFEST.json','2386d1eb5eb7543627eca824124e797823be8a22508c8b82089a44490a69fed4')
base,bref=load(F/'.agents/runtime/ct4-20261014/ACCEPTED-SOURCE-BASELINE.json','89f93db80a8fca90e7d5ac49d74aed06484d137e9689ef404e00a471e7f09e98')
j=F/'.agents/runtime/js7-20261015'
full,fref=load(j/'destination-full/RESULT.json','b427d45e9d166e82555bbe8c7f9b16671aa4c86f66bde9e8c1feb7349a15d366')
launch,lref=load(j/'destination-full-LAUNCH-RESULT.json','b6bf8b68ece25936cf0b437e6d092f0094331c7b03c2fcf8c28b2dc8f0694c31')
applied,aref=load(j/'active-application/APPLIED.json','f10a4013610456a8964e7333a26d6446b772552bdc2a692f50c0fa9ce4533a07')
state,sref=load(j/'js7-20261015/state.json');claims,cref=load(j/'js7-20261015/claims.json')
if state['sequence']!=12 or state['nodes']['integrate']['state']!='RUNNING':raise ValueError('Root integration state changed; preserve and request new finite observation')
if type(full['tests_run']) is not int or full['tests_run']!=1556 or full['failures']!=2 or full['errors']!=0 or full['skips']!=0 or full['exit_status']!=1:raise ValueError('Destination result differs')
if full['Source_accepted'] is not False or applied['Source_accepted'] is not False:raise ValueError('Source acceptance scope differs')
if applied['paths']!=m['application_paths'] or len(applied['paths'])!=15:raise ValueError('Publication mapping differs')
failure_ids=[row[0] for row in full['failure_details']]
if len(failure_ids)!=2 or any('AssertionError: 182 != 183' not in row[1] for row in full['failure_details']):raise ValueError('Expected precise blocker not present')
current={};raws={}
for rel,expected in m['expected_payload_hashes'].items():
 raw,fact=read(F/rel,expected);raws[rel]=raw
 current[rel]={'expected_sha256':expected,'observed':fact,'matches':True}
if len(current)!=295:raise ValueError('Wrong published Source count')
historical=x['accepted_source']
x['historical_source_observations']=[historical]
prior_comparison={}
for rel,expected in base['source_hashes'].items():
 if rel not in current:raise ValueError('Published cut omitted prior accepted member')
 fact=current[rel]['observed'];prior_comparison[rel]={'expected_sha256':expected,'observed':fact,'matches':fact['sha256']==expected}
x['accepted_source']={'record':base,'source':bref,'status':'PREVIOUS_ACCEPTED_CT4_BASELINE; PUBLISHED_SOURCE295_IS_UNACCEPTED',
 'current_payload_comparison':prior_comparison,'all_expected_payloads_match':all(v['matches'] for v in prior_comparison.values()),
 'limit':'This accepted historical witness is not current published Source295 acceptance. Exact changes and the failed destination result are separately recorded.'}
x['current_source_publication']={'status':'PUBLISHED_295_UNACCEPTED_DESTINATION_FULL_FAILED',
 'source_root':str(F),'payloads':295,'manifest':mref,'application':aref,
 'current_payload_comparison':current,'all_expected_payloads_match':True,
 'destination_full':fref,'destination_full_launch':lref,
 'actual_destination_result':{k:full[k] for k in ['tests_run','failures','errors','skips','exit_status','failure_details','error_details','skip_details','source_unchanged','Source_accepted']},
 'actual_integration':{'state':'RUNNING','sequence':12,'state_source':sref,'claims_source':cref,'claims':claims},
 'accepted_source_baseline_created':False,'automatic_rollback_or_retry':False,
 'failure_classification':'Two fixture-construction assertions182 !=183 inside profile(); no product runtime-effect failure or exact underlying cause is inferred.',
 'required_next':'Diagnose and repair only the exact UTF-16 target construction, preserving183 and259/260/261 oracles; independently review successor and repeat all required current candidate/destination/delivered acceptance before recording accepted baseline.'}
code=[]
for rel,raw in raws.items():
 if not rel.startswith('src/ceta/') or not rel.endswith(('.py','.rs')):continue
 text=raw.decode('utf-8-sig');fact=current[rel]['observed']
 row={'source':fact,'present':True,'source_cut_status':'PUBLISHED_UNACCEPTED',
      'semantics':'SOURCE_PRESENCE_IS_NOT_REQUIREMENT_ACCEPTANCE',
      'native_unit_mentions':sorted(set(re.findall(r'\bCETA-\d{2}\.\d{2}\.\d{2}\b',text)))}
 if rel.endswith('.py'):
  tree=ast.parse(text);row['top_level_classes']=[n.name for n in tree.body if isinstance(n,ast.ClassDef)]
  row['declared_functions']=[n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
  row['declared_functions_count']=len(row['declared_functions'])
 code.append(row)
x['current_source_code_index']=sorted(code,key=lambda q:q['source']['path'])
for c in x['canonical_components']:
 prefix=str(F/c['original']['path'])+'\\'
 c['actual_implementation']=[z for z in code if z['source']['path'].startswith(prefix)]
 c['implementation_evidence']={'current_code':c['actual_implementation'],'source_cut_status':'PUBLISHED_UNACCEPTED_SOURCE295',
    'previous_accepted_baseline':bref,'limits':'Full component semantics/acceptance not established.'}
for row in x['requirements']:
 direct=[c for c in x['canonical_components'] if c['original']['id'] in row['direct_canonical_component_ids']]
 row['implemented_source_paths']=sorted({z['source']['path'] for c in direct for z in c['actual_implementation']})
 row['implementation_evidence']['direct_source_paths']=row['implemented_source_paths']
 row['implementation_evidence']['source_cut_status']='PUBLISHED_UNACCEPTED_SOURCE295'
 row['implementation_evidence']['previous_accepted_baseline']=bref
 row['implementation_assessment']['scope']='Recorded current published Source295 is unaccepted; CT4 Source290 remains previous accepted baseline. FN6/private deltas remain separate.'
lane=next(q for q in x['remaining_critical_path'] if q['name']=='Public compiler, application/model and continuing intelligence')
lane['paths']=['tools/ceta_operator.py','src/ceta/application/task_operator.py']+[s for s in lane['paths'] if s!='src/ceta/desktop/launcher.py']
entry=[]
for rel in ['tools/ceta_operator.py','src/ceta/application/task_operator.py']:
 raw,fact=read(F/rel);lines=raw.decode('utf-8-sig').splitlines()
 entry.append({'source':fact,'callsite_lines':[{'line':n+1,'text':line.strip()} for n,line in enumerate(lines)
   if 'def main(' in line or 'create_operator_window' in line or 'compiler=None' in line or 'self.compiler is None' in line],
   'scope':'Observed actual existing caller; no caller invocation or production compiler activation.'})
lane['actual_entrypoint_evidence']=entry
first=x['remaining_critical_path'][0]
first['status']='BLOCKED_DESTINATION_FIXTURE_CONSTRUCTION_FAILURE; SOURCE295_PUBLISHED_UNACCEPTED'
first['blocker']='The15-path publication succeeded. Exact destination-full1556 has2failures/0errors/0skips: two original launcher-custody methods stop in profile() at182 !=183UTF-16 units. Integrate remains RUNNING12/claimed; previous accepted baseline is CT4. No runtime-effect failure or exact cause is inferred.'
first['next']='Reproduce the exact destination fixture construction, repair its target sizing without weakening183 or259/260/261 assertions, preserve the failed proof, review a successor and satisfy fresh full/delivered/source acceptance. Do not claim accepted Source295, automatically retry or roll back.'
first['evidence']={'publication':aref,'manifest':mref,'failed_destination_full':fref,'failed_launch':lref,
 'failing_ids':failure_ids,'integration_state':sref,'claims_source':cref,'previous_accepted_baseline':bref}
first['assessment_kind']='OBSERVED_DESTINATION_FIXTURE_ASSERTION_FAILURE; UNDERLYING_CAUSE_NOT_YET_QUALIFIED'
for c in x['candidate_catalog']:
 if c['run_id']=='js7-20261015':
  c['current_source_publication_observation']={'published':True,'Source_accepted':False,'application':aref,
   'destination_full':fref,'integration_state':'RUNNING','sequence':12,'state_source':sref,
   'limits':'Exact author manifest remains historical; publication is real but full delivered acceptance failed.'}
x['observed_at']=started
x['source_catalog_observation_scope']='Preservedr2 original input/provenance witnesses. Old code hashes there are historical and do not override current_source_publication/current_source_code_index.'
x['coverage_cardinalities']['published_source_payloads']=295
x['coverage_cardinalities']['source_payloads_in_accepted_baseline']=290
x['coverage_cardinalities']['active_source_code_files']=len(code)
x['coverage_cardinalities']['interpretation']='Source record/cardinality coverage only, never additive work counts, percentages or accepted progress.'
x['interpretation_limits']=[s.replace('All accepted source evidence is bound to CT4 exact290 until a later independently established acceptance supersedes it. Candidate and current publication observations are time-bound and separately recorded.',
 'CT4 remains the previous accepted290 baseline. Actual JS7 Source295 is published but unaccepted after two destination fixture assertions. FN6 is candidate-only. Current and historical observations remain separately source-bound.') for s in x['interpretation_limits']]
x['inventory_revision']={'prepared_at':started,'predecessor':prior,
 'changes':['Source metadata and correct per-REQ attribution fixes retained fromr3.',
 'Actual tools/ceta_operator.py/create_operator_window and application/task_operator.py compiler seam replace guessed launcher path.',
 'Current publication295/failed destination2/1556/claimed12 separately bound from accepted historicalCT4 baseline290.'],
 'remaining_limit':'Complete semantic conjunct/code/oracle reconciliation remains explicitly unresolved where not assessed. Provenance coverage does not make that work complete.'}
x['authoritative_inventory_path']=str(D/'COMPLETION-INVENTORY.json')
x['collaborative_review']['state']='PENDING_ROOT_AND_DISTINCT_REVIEW_OF_R4'
drift=[]
for rel,row in current.items():
 _,fact=read(F/rel)
 if fact['sha256']!=row['expected_sha256']:drift.append(rel)
if drift:raise ValueError('Source changed during finite publication observation')
x['source_read_conservation']={'observed_start':started,'observed_end':datetime.now(timezone.utc).isoformat(),
 'ordinary_published_source_payloads':295,'changed_inputs':drift,'stable_published_source_read_bytes':True,
 'Source_accepted':False,'historical_normative_sources':'Original source-document read conservation remains the preservedr2 observation.',
 'limits':'Ordinary lstat/hash bracketing only. This is neither full-worktree preservation nor acceptance/native retirement evidence.'}
D.mkdir(exist_ok=False)
write('COMPLETION-INVENTORY.json',x)
render_module=module('inventory_render_only',R/'build_inventory.py')
rendered=render_module.render(x)
rendered=rendered.replace('## Complete r6 source-location ledger','## r6 provenance appendix — no additional work items')
rendered=rendered.replace('Every nonblank line is retained verbatim below. Original identifiers are preserved. Locators are source references, not invented normative clause IDs. Semantic conjunct closure and source-specific acceptance remain open.',
 'Every nonblank line is retained as provenance. Headings, metadata, formatting, examples and context create no coding task. Remaining work is governed by its original registry/specification rows and exact closure lanes; unresolved semantic mapping stays explicit.')
summary=('Current published source: **295 payloads, UNACCEPTED**. Previous accepted baseline: **CT4 Source290**. '
 'Exact destination run: two profile-construction assertions182 !=183, no errors/skips; integrateRUNNING sequence12, claimed. '
 'No effect failure, acceptance, rollback or retry is inferred.\n\n')
rendered=rendered.replace('## Accepted source and active work\n\n','## Accepted source and active work\n\n'+summary)
with (D/'COMPLETION-INVENTORY.md').open('x',encoding='utf-8') as s:s.write(rendered)
print(json.dumps({'json':str(D/'COMPLETION-INVENTORY.json'),'json_sha256':sha(D/'COMPLETION-INVENTORY.json'),
 'markdown_sha256':sha(D/'COMPLETION-INVENTORY.md'),'published_payloads':295,'accepted_baseline_payloads':290,
 'source_accepted':False,'destination_failures':2,'integrate_state':'RUNNING','sequence':12},indent=2))
