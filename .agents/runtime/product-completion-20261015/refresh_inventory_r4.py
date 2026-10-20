"""Final observation only after Root's exact JS7 Source acceptance; no publication."""
from pathlib import Path
from datetime import datetime,timezone
import argparse
import ast
import hashlib
import importlib.util
import json
import os
import re
import stat

F=Path('T:/00-Active/Project-AI-CETA')
R=F/'.agents/runtime/product-completion-20261015'
D=R/'qualified-r4'
def digest(raw):return hashlib.sha256(raw).hexdigest()
def read(path,expected=None):
 p=Path(path)
 if '..' in p.parts:raise ValueError('Parent traversal rejected')
 p.relative_to(F)
 before=p.lstat()
 if not stat.S_ISREG(before.st_mode) or before.st_file_attributes&0x400:raise ValueError('Nonordinary input')
 raw=p.read_bytes();after=p.lstat()
 if any(getattr(before,k)!=getattr(after,k) for k in ('st_dev','st_ino','st_size','st_mtime_ns')):raise ValueError('Changed input')
 if expected is not None and digest(raw)!=expected:raise ValueError('Pinned bytes differ')
 fact={'path':str(p),'bytes':len(raw),'sha256':digest(raw),'observed_at':datetime.now(timezone.utc).isoformat(),
       'python_lstat':{k:getattr(after,k) for k in ('st_dev','st_ino','st_size','st_mtime_ns')},'handle_held':False}
 return raw,fact
def load(path,expected=None):
 raw,fact=read(path,expected);return json.loads(raw.decode('utf-8-sig')),fact
def write(name,obj):
 with (D/name).open('x',encoding='utf-8') as s:json.dump(obj,s,ensure_ascii=False,indent=2);s.write('\n')
def main():
 parser=argparse.ArgumentParser()
 parser.add_argument('--baseline',required=True)
 parser.add_argument('--baseline-sha256',required=True)
 args=parser.parse_args()
 start=datetime.now(timezone.utc).isoformat()
 x,predecessor=load(R/'qualified-r3/COMPLETION-INVENTORY.json','1705a584b8bda52128ca04282929ae45aae6e75a807b57145992401e94c63067')
 baseline,bref=load(Path(args.baseline),args.baseline_sha256)
 if baseline.get('Source_accepted') is not True or baseline.get('Source_payloads')!=295 or baseline.get('full_product_complete') is not False:raise ValueError('Wrong accepted baseline scope')
 m,mref=load(F/'.agents/js7-20261015/TRANSFER-MANIFEST.json','2386d1eb5eb7543627eca824124e797823be8a22508c8b82089a44490a69fed4')
 run=F/'.agents/runtime/js7-20261015/js7-20261015'
 state,sref=load(run/'state.json');claims,cref=load(run/'claims.json')
 required={'discover','plan','implement','review','validate','integrate'}
 if state['sequence']!=13 or claims!={} or set(state['nodes'])!=required or any(state['nodes'][n]['state']!='SUCCEEDED' for n in required):raise ValueError('Actual six-stage Source acceptance not terminal')
 local,lref=load(F/'.agents/runtime/js7-20261015/integrate.json')
 stored,stref=load(run/'receipts/integrate.json')
 fp=digest(json.dumps({k:v for k,v in stored.items() if k!='receipt_hash'},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())
 if not fp==stored['receipt_hash']==state['nodes']['integrate']['receipt_hash']:raise ValueError('Official augmented fingerprint differs')
 envelope,eref=load(run/'results/integrate.json')
 if envelope!={'node_id':'integrate','receipt_hash':fp,'result':local['result']}:raise ValueError('Actual result envelope differs')
 if type(local['exit_status']) is not int or local['exit_status']!=0 or local['result'].get('Source_accepted') is not True:raise ValueError('Source integration did not succeed')
 if baseline['manifest']['sha256']!=mref['sha256'] or baseline['integrate']['sha256']!=lref['sha256']:raise ValueError('Baseline integration chain differs')
 comparison={};raw_cache={}
 for rel,expected in m['expected_payload_hashes'].items():
  raw,fact=read(F/rel,expected);raw_cache[rel]=raw
  comparison[rel]={'expected_sha256':expected,'observed':fact,'matches':True}
 if len(comparison)!=295:raise ValueError('Wrong Source payload count')
 old_source=x['accepted_source'];x['historical_source_observations']=[old_source]
 x['accepted_source']={'record':baseline,'source':bref,'current_payload_comparison':comparison,'all_expected_payloads_match':True,
   'actual_all_six_stage_acceptance':{'sequence':13,'claims':{},'states':{k:state['nodes'][k]['state'] for k in sorted(required)},
     'state':sref,'claims_source':cref,'integrate':lref,'persisted_integrate':stref,'result_envelope':eref,'official_augmented_fingerprint':fp},
   'limit':'Exact accepted Source295 scoped defect/integration cut; original subsystem/B/AT/full-product gates remain unclosed.'}
 # Refresh the actual Source code index from this accepted cut, without imports or test execution.
 code=[]
 for rel,raw in raw_cache.items():
  if not rel.startswith('src/ceta/') or not rel.endswith(('.py','.rs')):continue
  item={'source':comparison[rel]['observed'],'present':True,'semantics':'PRESENCE_IS_NOT_REQUIREMENT_ACCEPTANCE',
        'native_unit_mentions':sorted(set(re.findall(r'\bCETA-\d{2}\.\d{2}\.\d{2}\b',raw.decode('utf-8-sig'))))}
  if rel.endswith('.py'):
   tree=ast.parse(raw.decode('utf-8-sig'));item['top_level_classes']=[n.name for n in tree.body if isinstance(n,ast.ClassDef)]
   item['declared_functions']=[n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
   item['declared_functions_count']=len(item['declared_functions'])
  code.append(item)
 x['current_source_code_index']=sorted(code,key=lambda z:z['source']['path'])
 for c in x['canonical_components']:
  prefix=str(F/c['original']['path'])+'\\'
  c['actual_implementation']=[z for z in code if z['source']['path'].startswith(prefix)]
  c['implementation_evidence']={'current_code':c['actual_implementation'],'accepted_source_reference':bref,
    'limits':'Exact Source295 code presence; full component semantics/acceptance not established.'}
 for req in x['requirements']:
  direct=[c for c in x['canonical_components'] if c['original']['id'] in req['direct_canonical_component_ids']]
  req['implemented_source_paths']=sorted({z['source']['path'] for c in direct for z in c['actual_implementation']})
  req['implementation_evidence']['direct_source_paths']=req['implemented_source_paths']
  req['implementation_evidence']['accepted_source_reference']=bref
  req['implementation_assessment']['scope']='Exact recorded accepted Source295 observation; remaining FN6/private deltas are separate.'
 # Correct the exact reviewed caller path; never create a guessed launcher.
 lane=next(z for z in x['remaining_critical_path'] if z['name']=='Public compiler, application/model and continuing intelligence')
 lane['paths']=['tools/ceta_operator.py','src/ceta/application/task_operator.py']+[s for s in lane['paths'] if s!='src/ceta/desktop/launcher.py']
 entry_facts=[]
 for rel in ['tools/ceta_operator.py','src/ceta/application/task_operator.py']:
  raw,fact=read(F/rel);body=raw.decode('utf-8-sig').splitlines()
  entry_facts.append({'source':fact,'callsite_lines':[{'line':i+1,'text':line.strip()} for i,line in enumerate(body)
     if 'def main(' in line or 'create_operator_window' in line or 'compiler=None' in line or 'self.compiler is None' in line]})
 lane['actual_entrypoint_evidence']=entry_facts
 first=x['remaining_critical_path'][0]
 first['status']='CLOSED_SCOPED_JS7_SOURCE_PUBLICATION_AND_DELIVERED_ACCEPTANCE'
 first['blocker']='No remaining blocker for this exact15-path publication. Its scoped closure does not complete WP-00/WP-01/G-A or the production authorization-to-effect chain.'
 first['next']='Proceed to the separately reviewed FN6 candidate reconciliation against this accepted Source295 baseline; retain all unclosed production/runtime/product requirements.'
 first['evidence']={'accepted_baseline':bref,'manifest':mref,'integrate':lref,'actual_sequence':13,'claims':{},
    'closed_recorded_scope':'JS2 journal cleanup, ER1 launcher custody, LP2Q1 codec scanning and ER2 editor-retention retry defects; four original component identities and exact15-path map preserved.'}
 first['assessment_kind']='SCOPED_SOURCE_INTEGRATION_ACCEPTED; ORIGINAL_PARENT_REQUIREMENTS_REMAIN_OPEN'
 for c in x['candidate_catalog']:
  if c['run_id']=='js7-20261015':
   c['joined_source_adoption']={'accepted':True,'exact_manifest':mref,'baseline':bref,'selected_paths':m['application_paths'],
      'limits':'Joined selected deltas accepted; original component parent requirements/full product not closed.'}
   c['integration_observation']={'state':'SUCCEEDED','sequence':13,'claims':{},'integrate':lref,'all_six_states':{k:state['nodes'][k]['state'] for k in sorted(required)}}
 x['observed_at']=start
 x['coverage_cardinalities']['active_source_code_files']=len(code)
 x['coverage_cardinalities']['source_payloads_in_accepted_baseline']=295
 x['coverage_cardinalities']['interpretation']='Source/provenance cardinalities only; never remaining-work or completion percentages.'
 x['interpretation_limits']=[s.replace('All accepted source evidence is bound to CT4 exact290 until a later independently established acceptance supersedes it. Candidate and current publication observations are time-bound and separately recorded.',
   'The exact JS7 Source295 acceptance now supersedes CT4 Source290 for the recorded15-path integrated cut. FN6 remains candidate-only. Every source/current-publication observation is time-bound and scoped.') for s in x['interpretation_limits']]
 x['inventory_revision']={'prepared_at':start,'predecessor':predecessor,
   'changes':['Root/PW semantic classification/REQ ownership fixes retained fromr3.',
              'Correct actual launcher/caller instead of guessed desktop/launcher.py.',
              'Fresh terminal Root Source295/actualall6SUCCEEDED13/claims{} acceptance and exact ordinary current hashes.'],
   'remaining_limit':'Original compound requirement semantic mapping/oracle qualification stays explicitly open where unassessed. This is not total-product or full-semantic-reconciliation completion.'}
 x['authoritative_inventory_path']=str(D/'COMPLETION-INVENTORY.json')
 x['collaborative_review']['state']='PENDING_ROOT_AND_DISTINCT_REVIEW_OF_R4'
 # Final byte conservation of only this refreshed Source read-set.
 drift=[]
 for rel,row in comparison.items():
  _,current=read(F/rel)
  if current['sha256']!=row['expected_sha256']:drift.append(rel)
 if drift:raise ValueError('Source changed during refreshed observation: '+str(drift))
 x['source_read_conservation']={'observed_start':start,'observed_end':datetime.now(timezone.utc).isoformat(),
  'ordinary_source_payloads':295,'changed_inputs':drift,'stable_accepted_source_read_bytes':True,
  'historical_normative_sources':'Original normative/source-document conservation is the preservedr2 observation; no unobserved uninterrupted equality claim.',
  'limits':'Ordinary lstat/hash bracketing only; Root native accepted-source proofs remain the native evidence.'}
 D.mkdir(exist_ok=False)
 write('COMPLETION-INVENTORY.json',x)
 spec=importlib.util.spec_from_file_location('inventory_render_only',R/'build_inventory.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 rendered=mod.render(x).replace('## Complete r6 source-location ledger','## r6 provenance appendix — no additional work items')
 rendered=rendered.replace('Every nonblank line is retained verbatim below. Original identifiers are preserved. Locators are source references, not invented normative clause IDs. Semantic conjunct closure and source-specific acceptance remain open.',
    'Every nonblank line is retained as provenance. Headings, metadata, formatting, examples and context create no coding task. The remaining obligations are the original identified registry/specification rows and their concrete closure lanes; unresolved semantic mapping remains explicit.')
 with (D/'COMPLETION-INVENTORY.md').open('x',encoding='utf-8') as s:s.write(rendered)
 print(json.dumps({'json':str(D/'COMPLETION-INVENTORY.json'),'json_sha256':digest((D/'COMPLETION-INVENTORY.json').read_bytes()),
  'markdown_sha256':digest((D/'COMPLETION-INVENTORY.md').read_bytes()),'source_payloads':295,'actual_sequence':13,'claims':{},'native_or_product_tests_executed':0},indent=2))
if __name__=='__main__':main()
