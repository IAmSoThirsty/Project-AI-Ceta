"""Root exact metadata/pin application; real coordinator gates and no replay."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,importlib.util,json,os,subprocess,sys
import status_core as s
F=s.F;S=s.S;W=s.W;D=S/'delivery';C=S/'control';RUN=s.RUN

def load_prepared(pin):
 assert sys.flags.optimize==0 and s.sha(W/'MANIFEST.json')==pin
 m=json.loads((W/'MANIFEST.json').read_bytes());b=json.loads((W/'BINDING.json').read_bytes())
 for name,value in m['work_hashes'].items():assert s.sha(W/name)==value,('work drift',name)
 observed=s.snapshot(W,F,ignored=frozenset());allowed={'MANIFEST.json','PREPARED.stdout','PREPARED.stderr','PREPARED.json'}
 current={Path(name).relative_to(W.relative_to(F)).as_posix():item for name,item in observed['files'].items()}
 assert set(current)-allowed==set(m['work_hashes']) and observed['excluded_symlinks']=={},'frozen work entry drift'
 for name,item in m['work_file_native'].items():assert current[name]==item,('work native identity drift',name)
 for name,identity in m['work_directory_identity'].items():assert all(observed['directories'][name][k]==v for k,v in identity.items()),('work directory replaced',name)
 for name,value in m['external_pins'].items():assert s.sha(Path(name))==value,('support drift',name)
 b['prepared_manifest_sha256']=pin
 path=F/'.agents/runtime/oq23/jr2/work/run_canonical_journal.py';spec=importlib.util.spec_from_file_location('_accepted_record_custody',path);q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
 return b,q

def live(rt,b):
 from taar.orchestration_graph import compile_graph
 graph=compile_graph(F,C);v=rt.verify(RUN);assert v['receipts_valid'] and v['graph_fingerprint']==b['graph_fingerprint']==graph.fingerprint
 state=json.loads((C/RUN/'state.json').read_bytes());assert state['nodes']['review']['decision']=='approved' and state['nodes']['validate']['validation_passed']
 review=json.loads((C/RUN/state['nodes']['review']['receipt_ref']).read_bytes());assert review['result']['manifest_sha256']==b['prepared_manifest_sha256']
 gate=json.loads((C/RUN/state['nodes']['validate']['receipt_ref']).read_bytes());assert gate['commands']==[dict(command=command,exit_status=0) for command in graph.nodes['validate']['commands']]
 assert [dict(command=item['command'],exit_status=item['exit_status']) for item in gate['result']['commands']]==gate['commands']
 claims=json.loads((C/RUN/'claims.json').read_bytes());expected=dict(integrate=F,evidence=D)
 for node,workspace in expected.items():
  cl=claims[node];assert cl['executor_id']=='/root' and state['nodes'][node]['state']=='RUNNING' and Path(cl['workspace'])==workspace and cl['input_hash']==rt._input_hash(graph,state,node)
  scope=graph.nodes[node]['write_scope'];assert cl['effective_write_scope']==list(scope)
  if node=='integrate':assert scope==[str(x) for x in json.loads((S/'packet/INPUTS.json').read_bytes())['targets']+json.loads((S/'packet/INPUTS.json').read_bytes())['temporary_paths']]
 return {node:claims[node] for node in expected}

def expected_after(b,q):
 new=json.loads((W/'SOURCE-MANIFEST.json').read_bytes())['payload_hashes'];pins={}
 for name,before in b['source_native'].items():
  rel=Path(name).relative_to(F).as_posix();q.ancestors(F,Path(name).parent);actual,_=q.stable(Path(name))
  expected=b['targets'][rel]['candidate_sha256'] if rel in b['targets'] else before['sha256'];assert actual['sha256']==expected,('unexpected source delta',rel)
  if rel not in b['targets']:assert actual==before,('untouched native identity drift',rel)
  pins[name]=actual
 for rel,pin in new.items():assert pins[str(F/rel)]['sha256']==pin
 return dict(source_native=pins,Git=q.git_observation(b['Git']))

def apply_once(rt,b,q):
 assert not any(D.iterdir()),'delivery is not empty; no replay'
 claims=live(rt,b);before=q.source_observation(b);assert before==b['source_before']
 packet=json.loads((S/'packet/INPUTS.json').read_bytes())
 for rel in packet['temporary_paths']:assert not (F/rel).exists() and not (F/rel).is_symlink()
 s.save(D/'EXECUTION-INTENT.json',dict(recorded_at=datetime.now(timezone.utc).isoformat(),prepared_manifest_sha256=b['prepared_manifest_sha256'],claims=claims,source_before=before,one_attempt=True,exact_targets=packet['targets'],full_product_acceptance=False))
 with s.application_journal(D/'operations.jsonl',q.diagnostic) as event:
  for rel,temp_rel in zip(packet['targets'],packet['temporary_paths']):
   target=F/rel;temp=F/temp_rel;q.ancestors(F,target.parent);native,_=q.stable(target);assert native==b['source_native'][str(target)] and native['sha256']==b['targets'][rel]['before_sha256']
   raw=(W/'candidate'/rel).read_bytes();assert s.sha(W/'candidate'/rel)==b['targets'][rel]['candidate_sha256'];assert live(rt,b)==claims
   event('BEFORE_CREATE_EXCLUSIVE_TEMP',target=rel,temporary=temp_rel,before_native=native)
   with s.physical(temp).open('xb') as stream:assert stream.write(raw)==len(raw);stream.flush();os.fsync(stream.fileno())
   current,_=q.stable(target);assert current==native,'target changed before replacement'
   assert s.stable(temp)['sha256']==b['targets'][rel]['candidate_sha256']
   event('BEFORE_ATOMIC_REPLACE',target=rel,temporary=temp_rel);os.replace(s.physical(temp),s.physical(target));after,_=q.stable(target);assert after['sha256']==b['targets'][rel]['candidate_sha256'];event('AFTER_ATOMIC_REPLACE',target=rel,after_native=after)
  after=expected_after(b,q);s.save(D/'SOURCE-AFTER-BINDING.json',after);event('FOUR_EXACT_TARGETS_APPLIED_AND_ALL_OTHER_SOURCE_PRESERVED')
 sys.path[:0]=[str(F/'src'),str(F/'tests/contract')]
 import importlib,unittest
 names=['test_construction','test_allocations','test_build_measurements'];suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in names);ids=q.identities(suite);assert len(ids)==len(set(ids))==29 and not any('_FailedTest' in x for x in ids)
 origins={}
 for name in names:
  module=importlib.import_module(name);assert Path(module.__file__).resolve()==F/'tests/contract'/(name+'.py');origins[name]=q.module_origin(module)
  if 'ROOT' in vars(module):assert vars(module)['ROOT']==F
 from ceta.contracts import construction
 assert Path(construction.__file__).resolve()==F/'src/ceta/contracts/construction.py';plan=construction.ConstructionPlan((F/'build/work_packages.json').read_bytes(),(F/'build/gates.json').read_bytes());assert len(plan.packages)==28 and len(plan.gates)==8
 output=D/'record-checks';output.mkdir(exist_ok=False)
 code=q.run_observed(suite,ids,output,{},lambda:q.source_observation(after),lambda:live(rt,b),metadata=dict(scope='CANONICAL_RECORD_GATE_ALLOCATION_BUILD_MEASUREMENT_CONSISTENCY',module_sources=origins,ordinary_imports=True,module_overlay=False,ROOT_override=False,canonical_source_manifest_sha256=b['new_source_manifest_sha256'],full_product_acceptance=False))
 execution_complete=q.execution_complete(output,code)
 result=json.loads((output/'RESULT.json').read_bytes());s.save(D/'RESULT.json',dict(applied_targets=packet['targets'],strict_gate_hash_binding_preserved=True,all_original_status_values_preserved_or_copied_exactly_to_history=True,all_eight_gate_rows_unchanged=True,source_manifest=ref(W/'SOURCE-MANIFEST.json'),canonical_record_tests=ref(output/'RESULT.json'),tests_run=result['tests_run'],failures=result['failures'],errors=result['errors'],test_cohort_passed=result['test_cohort_passed'],actual_test_return_code=code,execution_complete=execution_complete,source_and_Git_index_native_preserved_outside_four_targets=True,full_product_acceptance=False,completion_percentage=None))
 return code if execution_complete else (code or 1)

def ref(path):return dict(repository_relative_path=path.relative_to(F).as_posix(),sha256=s.sha(path))
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--manifest-sha256',required=True);parser.add_argument('--lease',choices=('claim','complete','verify','ready'));parser.add_argument('--node');parser.add_argument('--workspace');parser.add_argument('--receipt');args=parser.parse_args();b,q=load_prepared(args.manifest_sha256)
 with s.qualified_runtime() as runtime:
  rt=runtime.OrchestrationRuntime(C)
  if args.lease:
   if args.lease=='claim':
    assert args.node in ('integrate','evidence');expected=F if args.node=='integrate' else D;assert Path(args.workspace)==expected;response=rt.claim(RUN,args.node,'/root',workspace=expected)
   elif args.lease=='complete':assert args.node in ('integrate','evidence') and Path(args.receipt)==C/(args.node+'-receipt.json');response=rt.complete(RUN,args.node,Path(args.receipt))
   elif args.lease=='verify':response=rt.verify(RUN)
   else:response=rt.ready(RUN)
   label='ROOT-'+(args.node+'-' if args.node else '')+args.lease+'-api.json';s.save(C/label,dict(api='OrchestrationRuntime.'+args.lease,qualified_snapshot_policy='EXPLICIT_STOCK_EXCLUSIONS; F_SOURCE_ONLY; NO_SCOPE_OVERRIDE',response=response));print(json.dumps(dict(allowed=response.get('allowed'),states=response.get('states'),receipts_valid=response.get('receipts_valid'),terminal_success=response.get('terminal_success'))));return 0 if response.get('allowed') else 1
  return apply_once(rt,b,q)
if __name__=='__main__':raise SystemExit(main())
