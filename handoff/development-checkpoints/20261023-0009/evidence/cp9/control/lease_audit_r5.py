"""Read-only bounded lease audit with complete RUNNING-node custody and hash-bound own publication receipts."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,subprocess,sys
F=Path('T:/00-Active/Project-AI-CETA');ROOT=Path('T:/');C=F/'.agents/runtime/oq23/cp9/control';R=F/'.agents/runtime'
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_graph import scopes_may_overlap

def key(p):return str(Path(p).resolve()).replace('\\','/').rstrip('/').casefold()
def stable(p):
 a=p.stat();raw=p.read_bytes();b=p.stat();assert (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(b.st_dev,b.st_ino,b.st_size,b.st_mtime_ns),('changed during read',str(p))
 return json.loads(raw),hashlib.sha256(raw).hexdigest()
def audit(own=None):
 own_spec=None
 if own is not None:
  sys.path.insert(0,str(C.parent/'work'))
  import exact_git_scope as exact
  own_spec=exact.packet(own['publication_packet_sha256'])
  assert key(own['claims_path'])==key(exact.CONTROL/'ceta-cp9-publication-20261023/claims.json') and own['graph_fingerprint']==own_spec['graph_fingerprint']
  assert own['claim']['effective_write_scope']==own_spec['git_scope'] and own['claim']['node_id']=='integrate' and own['claim']['executor_id']=='/root' and key(own['claim']['workspace'])==key(F/'.git')
 prior,prior_pin=stable(C/'lease-diagnostic/REPORT.json');assert prior_pin=='93f5661122237c3a4e74d7d3e9ea358705067b6e454eb73d58c52d508a016670'
 known_synthetic={key(x['path']):x for x in prior['synthetic']};known_saved={key(x['path']):x for x in prior['saved_observations']}
 for g in prior['synthetic_factory_provenance'].values():assert hashlib.sha256(Path(g['path']).read_bytes()).hexdigest()==g['sha256']
 args=['rg','--files','--hidden','--no-ignore','--max-depth','8','-g','claims.json','-g','!**/independent-review/**','-g','!**/review/**','-g','!**/work/**','-g','!**/delivery/**','-g','!**/*fixtures*/**','-g','!**/controls*/**','-g','!**/candidate/**','-g','!**/before*/**',str(R)]
 p=subprocess.run(args,cwd=F,capture_output=True,check=False);assert p.returncode==0,(p.returncode,p.stderr.decode('utf8',errors='replace'))
 result=dict(recorded_at=datetime.now(timezone.utc).isoformat(),project=str(F),policy='Current-project main runtime records depth<=8 with exact disclosed exclusions, actual RunStore storage identity and graph/state/claim bindings. Scope and storage may differ. Recorded RUNNING claims retained regardless of age. Not a machine-wide lease registry or process-liveness assessment.',search_argv=args,search_actual_exit_status=p.returncode,search_stdout_sha256=hashlib.sha256(p.stdout).hexdigest(),diagnostic_provenance_sha256=prior_pin,coordinators=[],synthetic_probe_records=[],saved_observations=[],unresolved=[],active_claims=[],git_scope_conflicts=[],permitted_current_publication_claim=[],existing_Git_lock_files=[],canonical_or_coordinator_mutation=False,process_liveness='NOT_ASSESSED')
 for text in sorted(p.stdout.decode('utf8').splitlines()):
  path=Path(text);row=dict(path=str(path))
  try:
   assert path.resolve().is_relative_to(R.resolve());claims,cp=stable(path);state,sp=stable(path.with_name('state.json'));row.update(claims_sha256=cp,state_sha256=sp)
   if 'scope' not in state:
    saved=known_synthetic.get(key(path));assert saved and (cp,sp)==(saved['claims_sha256'],saved['state_sha256']),('unresolved nonstock schema',str(path))
    assert state=={'nodes':{'review':{'state':'SUCCEEDED'},'validate':{'state':'SUCCEEDED'}}} and set(claims)=={'integrate'}
    fixture=path.parent.parent.parent;cl=claims['integrate'];assert set(cl)=={'executor_id','workspace','input_hash'} and cl['executor_id'] in ('/root','/root/history_preservation') and cl['input_hash']=='owned-native-fixture' and key(cl['workspace'])==key(F)
    assert not path.with_name('graph.json').exists() and not path.with_name('events.jsonl').exists() and (fixture/'physical-targets').is_dir() and (path.parent/'receipts/review.json').is_file()
    row.update(classification='EXACT_PRESERVED_SYNTHETIC_PROBE',factory_group=saved['factory_group']);result['synthetic_probe_records'].append(row);continue
   if path.parent.name != state.get('run_id'):
    saved=known_saved.get(key(path));assert saved and (cp,sp)==(saved['claims_sha256'],saved['state_sha256']) and not path.with_name('graph.json').exists() and not path.with_name('events.jsonl').exists(),('unresolved storage identity',str(path))
    row.update(classification='EXACT_PRESERVED_SAVED_OBSERVATION',embedded_run_id=state.get('run_id'));result['saved_observations'].append(row);continue
   graph,gp=stable(path.with_name('graph.json'));assert state['schema_version']==1 and path.with_name('events.jsonl').is_file()
   assert graph['scope']==state['scope'] and graph['root']==state['graph_root'] and graph['fingerprint']==state['graph_fingerprint']
   assert isinstance(claims,dict) and isinstance(state['nodes'],dict)
   assert {n:e['claim'] for n,e in state['nodes'].items() if e.get('claim') is not None}==claims,('claim-state disagreement',str(path))
   assert {n for n,e in state['nodes'].items() if e['state']=='RUNNING'}==set(claims),('recorded RUNNING node missing its persisted claim',str(path))
   graph_root=Path(state['graph_root']);assert key(graph_root) in (key(ROOT),key(F))
   row.update(run_id=state['run_id'],graph_sha256=gp,scope=state['scope'],graph_root=state['graph_root'],scope_equals_storage_parent=key(state['scope'])==key(path.parent.parent))
   for node,cl in claims.items():
    assert state['nodes'][node]['state']=='RUNNING' and state['nodes'][node]['claim']==cl and cl['node_id']==node
    entry=state['nodes'][node];assert entry['effective_write_scope']==cl['effective_write_scope'] and entry['executor_id']==cl['executor_id'] and entry['workspace']==cl['workspace'],('contradictory persisted claim mirrors',str(path),node)
    scopes=cl['effective_write_scope'];assert isinstance(scopes,list) and all(isinstance(x,str) for x in scopes)
    prefix='' if key(graph_root)==key(ROOT) else '00-active/project-ai-ceta/'
    normalized=[prefix+x.replace('\\','/').casefold() for x in scopes];overlap=scopes_may_overlap(normalized,['00-active/project-ai-ceta/.git/**','00-active/project-ai-ceta/.git'])
    active=dict(path=str(path),run_id=state['run_id'],node=node,executor=cl['executor_id'],workspace=cl['workspace'],claimed_at=cl['claimed_at'],effective_write_scope=scopes,normalized_scope=normalized,claims_sha256=cp,state_sha256=sp,graph_sha256=gp,graph_fingerprint=state['graph_fingerprint'],claim=cl,git_scope_overlap=overlap)
    result['active_claims'].append(active)
    if overlap:
     permitted=own is not None and key(path)==key(own['claims_path']) and node=='integrate' and cl==own['claim'] and cl['executor_id']=='/root' and key(cl['workspace'])==key(F/'.git') and state['graph_fingerprint']==own['graph_fingerprint'] and state['run_id']=='ceta-cp9-publication-20261023'
     if permitted:
      assert own_spec is not None and graph['graph']['nodes']['integrate']['write_scope']==own_spec['git_scope'] and state['nodes']['review']['state']=='SUCCEEDED' and state['nodes']['review']['decision']=='approved' and state['nodes']['validate']['state']=='SUCCEEDED' and state['nodes']['validate']['validation_passed'] is True
      from taar.orchestration_persistence import sha256_json
      own_receipts={}
      for receipt_node in ('review','validate'):
       saved_node=state['nodes'][receipt_node];executor=saved_node['executor_id'];assert saved_node['receipt_ref']=='receipts/'+receipt_node+'.json' and type(executor) is str and executor and (executor=='/root' if receipt_node=='validate' else executor!='/root')
       saved_receipt,_=stable(path.parent/saved_node['receipt_ref']);body=dict(saved_receipt);saved_hash=body.pop('receipt_hash',None)
       assert saved_hash==sha256_json(body)==saved_node['receipt_hash'],('own publication receipt hash mismatch',receipt_node)
       assert saved_receipt['run_id']==state['run_id'] and saved_receipt['node_id']==receipt_node and saved_receipt['executor_id']==executor
       assert type(saved_receipt['exit_status']) is int and saved_receipt['exit_status']==0
       assert type(saved_receipt['validations']) is list and all(type(x) is dict and type(x['name']) is str and x['name'] and x['passed'] is True for x in saved_receipt['validations'])
       if receipt_node=='validate':assert saved_receipt['validations'] and saved_node['validation_passed'] is True
       assert all(type(x['exit_status']) is int and x['exit_status']==0 for x in saved_receipt['commands'])
       own_receipts[receipt_node]=saved_receipt
      review=own_receipts['review'];gate=own_receipts['validate']
      assert review['decision']=='approved' and review['result']['publication_packet_sha256']==own['publication_packet_sha256'] and review['result']['work_freeze_sha256']==own_spec['work_freeze_sha256']
      expected_gate=[dict(command=x,exit_status=0) for x in graph['graph']['nodes']['validate']['commands']];assert gate['commands']==expected_gate
     result['permitted_current_publication_claim' if permitted else 'git_scope_conflicts'].append(active)
   _,cp2=stable(path);_,sp2=stable(path.with_name('state.json'));_,gp2=stable(path.with_name('graph.json'));assert (cp,sp,gp)==(cp2,sp2,gp2),('coordinator moved across read',str(path))
   result['coordinators'].append(row)
  except BaseException as exc:
   row.update(exception_type=type(exc).__name__,message=str(exc));result['unresolved'].append(row)
 def fail(e):raise e
 for directory,dirs,files in os.walk(F/'.git',followlinks=False,onerror=fail):
  for name in dirs:assert not (Path(directory)/name).is_symlink(),('Git directory symlink',directory,name)
  for name in files:
   if name.endswith('.lock'):result['existing_Git_lock_files'].append((Path(directory)/name).relative_to(F).as_posix())
 if own is not None:assert len(result['permitted_current_publication_claim'])==1,'current exact publication claim not established'
 result['clear_for_exact_Git_publication']=not result['unresolved'] and not result['git_scope_conflicts'] and not result['existing_Git_lock_files']
 result['summary']={k:len(result[k]) for k in ('coordinators','synthetic_probe_records','saved_observations','unresolved','active_claims','git_scope_conflicts','permitted_current_publication_claim','existing_Git_lock_files')}
 return result
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--output',required=True);a.add_argument('--own-claim');ns=a.parse_args();own=json.loads(Path(ns.own_claim).read_bytes()) if ns.own_claim else None;value=audit(own)
 with Path(ns.output).open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')
 print(json.dumps(dict(summary=value['summary'],clear_for_exact_Git_publication=value['clear_for_exact_Git_publication'],bounded_inventory_only=True)));raise SystemExit(0 if value['clear_for_exact_Git_publication'] else 1)
