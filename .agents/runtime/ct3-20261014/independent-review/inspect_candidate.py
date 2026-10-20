"""Inspect a released CT3 cut, preserving exact leaf and native/source identities."""
from ct3_support import *
import ast,copy,re
from collections import Counter

def equal(a,b):return json.dumps(a,sort_keys=True,separators=(',',':'),allow_nan=False)==json.dumps(b,sort_keys=True,separators=(',',':'),allow_nan=False)
def leaf_changes(a,b,path=''):
 if type(a) is not type(b):return [{'pointer':path,'before':a,'after':b,'change':'TYPE_OR_VALUE'}]
 if isinstance(a,dict):
  out=[]
  for key in sorted(set(a)|set(b)):
   p=path+'/'+key.replace('~','~0').replace('/','~1')
   if key not in a:out.extend(new_leaves(b[key],p,'ADDED'))
   elif key not in b:out.extend(new_leaves(a[key],p,'REMOVED'))
   else:out.extend(leaf_changes(a[key],b[key],p))
  return out
 if isinstance(a,list):
  out=[]
  for index in range(max(len(a),len(b))):
   p=path+'/'+str(index)
   if index>=len(a):out.extend(new_leaves(b[index],p,'ADDED'))
   elif index>=len(b):out.extend(new_leaves(a[index],p,'REMOVED'))
   else:out.extend(leaf_changes(a[index],b[index],p))
  return out
 return [] if equal(a,b) else [{'pointer':path,'before':a,'after':b,'change':'VALUE'}]
def new_leaves(v,path,change):
 if isinstance(v,dict) and v:return [row for k,x in sorted(v.items()) for row in new_leaves(x,path+'/'+k.replace('~','~0').replace('/','~1'),change)]
 if isinstance(v,list) and v:return [row for i,x in enumerate(v) for row in new_leaves(x,path+'/'+str(i),change)]
 return [{'pointer':path,'value':v,'change':change}]
def bound(reference):
 rel=reference['repository_relative_path'];fs.relative_name(rel);path=fs.safe_components(F/rel)
 observed=ordinary(path);assert observed['sha256']==reference['sha256'],('REFERENCE_DRIFT',rel)
 return path,observed
def actual_accepted(package):
 root=F/'.agents/runtime'/package;s=read(root/package/'state.json');c=read(root/package/'claims.json')
 assert s['sequence']==13 and not c and all(n['state']=='SUCCEEDED' for n in s['nodes'].values())
 a=read(root/'actual-acceptance.json');assert a['integrate_receipt_sha256']==sha(root/'integrate.json')
 return {'run_id':package,'sequence':s['sequence'],'states':{k:n['state'] for k,n in s['nodes'].items()},'claims':c,'integrate':ref(root/'integrate.json'),'acceptance':ref(root/'actual-acceptance.json'),'completed_at':s['nodes']['integrate']['completed_at']}

def main():
 expected_manifest=sys.argv[1];started=utc();m_path=Q/'TRANSFER-MANIFEST.json'
 assert sha(m_path)==expected_manifest;m=read(m_path)
 claim=read(R/RUN/'claims.json')['review'];assert claim['executor_id']==ACTOR and claim['workspace']==str(Q)
 assert read(R/RUN/'state.json')['nodes']['review']['state']=='RUNNING'
 assert read(R/'implement.json')['executor_id']=='/root' and read(R/'implement.json')['result']['manifest_sha256']==expected_manifest
 allowed_paths={'build/progress.json','handoff/continuity.json'}
 assert set(m['application_paths'])==allowed_paths and len(m['payloads'])==2 and {i['relative_path'] for i in m['payloads']}==allowed_paths
 assert m['runtime_code_changes']==m['global_gate_or_requirement_changes']==0 and m['earlier_observations_preserved'] is True
 assert m['source_root']==str(F) and m['candidate_root']==str(Q) and m['author']=='/root'
 candidate_files={p.relative_to(Q).as_posix() for p in Q.rglob('*') if p.is_file()}
 assert candidate_files==allowed_paths|{'TRANSFER-MANIFEST.json'}
 before={};after={};before_native={};q_native={};changes={};preserved_keys={}
 for row in m['payloads']:
  rel=row['relative_path'];bpath=R/'before'/rel;before[rel]=read(bpath);after[rel]=read(Q/rel)
  assert row['application_action']=='EXTEND_PRESERVE_BEFORE_IMAGE'
  assert ordinary(bpath)['sha256']==row['active_before_sha256'];before_native[rel]=ordinary(F/rel)
  assert before_native[rel]['sha256']==row['active_before_sha256']
  declared=dict(row['source_native_identity']);declared['mode']=stat.S_IMODE(declared['mode']);assert before_native[rel]['native_identity']==declared
  q_native[rel]=ordinary(Q/rel);assert q_native[rel]['sha256']==row['candidate_sha256']
  assert set(after[rel])-set(before[rel])<=set(row['allowed_changed_keys'])
  changes[rel]=leaf_changes(before[rel],after[rel])
  assert all(c['pointer'].split('/')[1] in row['allowed_changed_keys'] for c in changes[rel])
  for key,value in before[rel].items():
   if key not in row['allowed_changed_keys']:assert equal(after[rel][key],value),('GLOBAL_OR_HISTORY_CHANGE',rel,key)
  hist=after[rel]['repository_execution_history_20261014'];assert len(hist)==len(before[rel].get('repository_execution_history_20261014',[]))+1
  assert equal(hist[:-1],before[rel].get('repository_execution_history_20261014',[]))
  assert equal(hist[-1]['previous_current_observation'],before[rel]['current_repository_execution_20261014'])
  if rel=='handoff/continuity.json':
   expected=('latest_source_tests','latest_source_integrity','next_action','current_deliverable','current_increment_tests','latest_increment_working_record','latest_state_check_freshness')
   assert all(equal(after[rel]['historical_fields_before_ct3_20261014'][key],before[rel][key]) for key in expected)
   preserved_keys[rel]=list(expected)
 facts=after['build/progress.json']['current_repository_execution_20261014']
 assert equal(facts,after['handoff/continuity.json']['current_repository_execution_20261014'])
 assert facts['authoritative_repository']==str(F) and facts['display_identity']=='Project-AI: CETA'
 head=subprocess.run(['git','-C',str(F),'rev-parse','HEAD'],capture_output=True,check=True).stdout.decode().strip()
 branch=subprocess.run(['git','-C',str(F),'branch','--show-current'],capture_output=True,check=True).stdout.decode().strip()
 assert facts['Git_HEAD']==head and facts['branch']==branch
 assert facts['source_payloads']==286 and facts['product_modules']==74
 observed=datetime.fromisoformat(facts['recorded_at']);assert observed<=datetime.fromisoformat(claim['claimed_at'])
 assert read(R/'implement.json')['result']['Source_application'] is False
 ledgers={}
 for name,pin in facts['accepted_package_ledgers'].items():
  ledgers[name]=actual_accepted(name);assert pin['run_id']==name and pin['sequence']==13 and pin['claims']=={}
  assert pin['integrate_receipt']==ledgers[name]['integrate'] and pin['acceptance']==ledgers[name]['acceptance']
  assert pin['accepted_at']==ledgers[name]['completed_at'] and datetime.fromisoformat(pin['accepted_at'])<=observed
 assert set(ledgers)=={'wa1-20261014','hd2-20261014','gd3-20261014','rp1-20261014','rs-owner2-20261014','er1-20261014','hp10-20261014'}
 sp,_=bound(m['source_suite']);suite=read(sp);assert type(suite['tests_run']) is int and suite['tests_run']==1416
 assert all(type(suite[k]) is int and suite[k]==0 for k in ('failures','errors','skips','exit_status'))
 assert suite['expected_ids']==suite['executed_ids'] and len(suite['executed_ids'])==len(set(suite['executed_ids']))==1416
 raw=sp.with_suffix('.txt').read_bytes();assert hashlib.sha256(raw).hexdigest()==suite['output_sha256']
 ids=[]
 for line in raw.decode('utf-8-sig').splitlines():
  match=re.match(r'^([^\s]+) \(([^)]+)\)(?: |$)',line)
  if match:assert match.group(2).rsplit('.',1)[-1]==match.group(1);ids.append(match.group(2))
 assert ids==suite['expected_ids'] and sum(line.endswith(' ... ok') for line in raw.decode('utf-8-sig').splitlines())==1416
 assert len(suite['imports'])==74 and suite['native_census']['exit_status']==0 and suite['native_census']['result']['clear'] is True
 assert suite['source_unchanged'] is True and suite['before_hashes']==suite['after_hashes']==suite['expected_payload_hashes'] and len(suite['after_hashes'])==286
 source_native={rel:ordinary(F/rel) for rel in suite['after_hashes']};assert {k:v['sha256'] for k,v in source_native.items()}==suite['after_hashes']
 assert isinstance(suite['imports'],list) and len({pin['module'] for pin in suite['imports']})==74
 for pin in suite['imports']:
  path=Path(pin['actual_path']);assert path.is_relative_to(F/'src/ceta')
  assert ordinary(path)['sha256']==pin['sha256']==suite['after_hashes'][path.relative_to(F).as_posix()]
 summary=facts['current_scoped_tests'];assert summary['sha256']==sha(sp) and summary['passed']==1416 and summary['complete_contract_suite'] is True and summary['whole_product_acceptance'] is False
 assert all(summary[k]==0 for k in ('failures','errors','skipped')) and equal(summary,after['handoff/continuity.json']['latest_source_tests'])
 dest,_=bound(summary['independent_destination_review']);dr=read(dest);assert dr['decision']=='approved' and dr['destination_suite_sha256']==sha(sp)
 join,_=bound(summary['source_binding']);assert read(join)['after_hashes']==suite['after_hashes']
 rb=facts['budget_candidate'];rp,_=bound(rb['independent_review']);rd=read(rp);assert rd['decision']=='approved' and rd['result']['independently_executed_tests']==rb['independent_tests']==211
 bp,_=bound(rb['manifest']);assert rd['result']['manifest']['sha256']==sha(bp)
 rs=read(F/'.agents/runtime/rb-task1-20261014/rb-task1-20261014/state.json');rc=read(F/'.agents/runtime/rb-task1-20261014/rb-task1-20261014/claims.json')
 assert rs['nodes']['implement']['state']==rs['nodes']['review']['state']=='SUCCEEDED' and rs['nodes']['integrate']['state']=='PENDING' and not rc and rb['Source_application'] is rb['whole_unit_completion'] is False
 if 'performance_candidate' in facts:
  pp=facts['performance_candidate'];bound(pp['manifest']);assert pp['Source_application'] is False
  state=read(F/'.agents/runtime/perf1-20261014/perf1-20261014/state.json')
  assert state['sequence']>=pp['sequence_at_observation']
  for name,status in pp['states_at_observation'].items():
   node=state['nodes'][name]
   if status!=node['state']:assert node.get('completed_at') and datetime.fromisoformat(node['completed_at'])>=observed
 assert facts['history_capture']['held_installer_or_cache_entries']==['W043','W044','W045'] and facts['history_capture']['tool_acceptance_activates_capture'] is False
 assert equal(facts['reservation_integrated_LOC'],read(F/'.agents/runtime/rs-owner2-20261014/root-integration/executable-source-and-test-delta.json'))
 script=F/'tools/build_measurements.py';spec=importlib.util.spec_from_file_location('ct3_exact_measurements_consumer',script);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 docs={key:read(F/rel) for key,rel in mod.INPUTS.items()};old=copy.deepcopy(docs);new=copy.deepcopy(docs);old['progress']=before['build/progress.json'];new['progress']=after['build/progress.json']
 assert equal(mod.measurements(old),mod.measurements(new))
 global_paths=['requirements/requirements.json','build/work_packages.json','build/gates.json','standards/lifecycle_coverage.json','acceptance/scenarios.json','policies/policy_registry.json','handoff/source_authority_register.json','PACKAGE_SUMMARY.json','architecture/components.json']
 globals_observed={rel:ordinary(F/rel) for rel in global_paths}
 assert all(ordinary(F/rel)==value for rel,value in globals_observed.items())
 assert all(ordinary(F/rel)==value for rel,value in before_native.items())
 assert all(ordinary(Q/rel)==value for rel,value in q_native.items()) and sha(m_path)==expected_manifest
 assert all(ordinary(F/rel)==value for rel,value in source_native.items())
 proof={'executor':ACTOR,'started_at':started,'finished_at':utc(),'claim':{k:claim[k] for k in ('executor_id','workspace','claimed_at','input_hash')},'manifest':ref(m_path),'author_receipt':ref(R/'implement.json'),'source_suite':ref(sp),'source_raw_sha256':hashlib.sha256(raw).hexdigest(),'source286_native_observations':source_native,'source286_unchanged':True,'status_before_native':before_native,'candidate_native':q_native,'changed_json_leaf_counts':{k:len(v) for k,v in changes.items()},'changed_json_leaves':changes,'previous_observations_preserved_exact':True,'historical_pointer_keys':preserved_keys,'global_axes_files_native':globals_observed,'measurement_consumer_before_after_equal':True,'actual_accepted_ledgers':ledgers,'rb_review':ref(rp),'qualification':'Independent current byte/native/leaf/ledger/raw inspection;1416 Root methods inspected, not freshly rerun; installation/whole product/authority gates retained; no source publication','exit_status':0}
 save(V/'candidate-inspection.json',proof)
 print(json.dumps({'candidate_inspection_sha256':sha(V/'candidate-inspection.json'),'leaf_counts':proof['changed_json_leaf_counts'],'source286_exact':True,'root_raw1416_exact':True}))
if __name__=='__main__':main()
