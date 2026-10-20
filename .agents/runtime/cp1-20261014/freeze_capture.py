from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, json, subprocess, sys

S=Path(r'T:\00-Active\CETA_Intelligence_Operating_System_Build_Package')
Q=S/'.agents/cp1-20261014'; R=S/'.agents/runtime/cp1-20261014'
T=S/'.agents/pr4-20261014/preserve_ceta_complete.py'
sys.path.insert(0,r'T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce')
from taar.orchestration_runtime import _snapshot_workspace, _changed_files
from taar.orchestration_receipts import validate_receipt, load_receipt
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(T)=='2ccbca31973ead308e1cdcc6676bbd7371cdec29a0f16178f3f55a4ab4130618'
claim=read(R/'cp1-20261014/claims.json')['implement']
assert claim['executor_id']=='/root' and claim['workspace']==str(Q)
spec=importlib.util.spec_from_file_location('ceta_approved_capture',T)
tool=importlib.util.module_from_spec(spec); spec.loader.exec_module(tool)
policy=tool.Policy(read(R/'policy.json'))
manifest, inventory=tool.verify_checkpoint(Q/'checkpoint',policy)
before=read(R/'plan-source-inspection.json')['entries']
after=tool.tree_inventory(Path(manifest['source_root']),policy)
assert before==after==inventory['entries']
assert manifest['complete'] and manifest['source_unchanged'] and not manifest['pending']
assert inventory['git'] is None and sum(e['kind']=='file' for e in after)==1523
result={'status':'CAPTURED_SEALED_VERIFIED_AWAITING_INDEPENDENT_RECOVERY',
 'source':manifest['source_root'],'checkpoint':str(Q/'checkpoint'),
 'checkpoint_sha256':sha(Q/'checkpoint/checkpoint.json'),
 'inventory_sha256':sha(Q/'checkpoint/inventory.json'),
 'archive_sha256':sha(Q/'checkpoint/working-tree.zip'),
 'approved_tool_sha256':sha(T),'source_before_after_inventory_exact':True,
 'files':1523,'bytes':sum(e.get('bytes',0) for e in after if e['kind']=='file'),
 'pending_protected_candidates':[],'source_writes':0,
 'recovery_performed':False,'runtime_product_qualification':False,
 'capture_started_at':manifest['started_at'],'capture_finished_at':manifest['finished_at'],
 'prior_failures':[{'operation':'CLI verify with relative policy argument','exit_status':1,
  'error':'path must be absolute: .agents\\runtime\\cp1-20261014\\policy.json',
  'chunk':'4bb5c2','classification':'fixed_now',
  'repair':'Retried verify with exact absolute policy/checkpoint paths; actual exit0 chunk a79f57.'}]}
snapshot=_snapshot_workspace(Q)
changed=sorted(_changed_files(claim['baseline_snapshot'],snapshot))
receipt={'schema_version':1,'run_id':'cp1-20261014','node_id':'implement',
 'executor_id':'/root','started_at':manifest['started_at'],
 'finished_at':datetime.now(timezone.utc).isoformat(),'input_hash':claim['input_hash'],
 'changed_files':changed,'result':result,
 'commands':[{'command':'Python312 -B approved preserve_ceta_complete.py --policy ABSOLUTE_POLICY capture --source EXACT_NATIVE_ROOT --output EXACT_FRESH_CHECKPOINT','exit_status':0},
 {'command':'Python312 -B approved preserve_ceta_complete.py --policy ABSOLUTE_POLICY verify --checkpoint EXACT_CHECKPOINT','exit_status':0},
 {'command':'Python312 -B freeze_capture.py; seal/archive/full source before-after bytes and installed runtime snapshot readback','exit_status':0}],
 'validations':[{'name':'all1523_source_files_exact_before_after_capture_and_sealed_inventory','passed':True},
 {'name':'approved_exact_tool_zero_pending_protected_candidates_no_source_writes','passed':True}],
 'exit_status':0}
graph=read(R/'cp1-20261014/graph.json')['graph']['nodes']['implement']
validate_receipt(receipt,node=graph)
out=R/'implement.json'
with out.open('x',encoding='utf-8') as stream:json.dump(receipt,stream,indent=2);stream.write('\n')
validate_receipt(load_receipt(out),node=graph)
print(json.dumps({'changed_files':changed,'receipt_sha256':sha(out),'result':result}))
