from pathlib import Path
import sys,json,hashlib,importlib.util
from datetime import datetime,timezone
root=Path(r'T:\00-Active\CETA_Intelligence_Operating_System_Build_Package')
q=root/'.agents/cp1-20261014'; r=root/'.agents/runtime/cp1-20261014'
source=Path(r'T:\00-Active\CETA-NATIVE-ARCHITECTURE')
tool_path=root/'.agents/pr4-20261014/preserve_ceta_complete.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(tool_path)=='2ccbca31973ead308e1cdcc6676bbd7371cdec29a0f16178f3f55a4ab4130618'
tr=root/'.agents/runtime/pr4-20261014'
state=json.loads((tr/'pr4-20261014/state.json').read_text())
assert all(n['state']=='SUCCEEDED' for n in state['nodes'].values())
spec=importlib.util.spec_from_file_location('ceta_approved_preserver',tool_path); tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
node=sys.argv[1]; started=datetime.now(timezone.utc).isoformat()
policy_data={'schema_version':1,'source_roots':[str(source)],'git_roots':[],'capture_targets':[str(q/'checkpoint')],'restore_targets':[str(q/'independent-recovery')],'classifications':[],'declared_inputs':[{'path':str(source/name),'sha256':sha(source/name)} for name in ('README.md','PACKAGE-MANIFEST.md','PACKAGE-INTEGRITY.md')]}
policy=tool.Policy(policy_data)
assert not tool.exists(source/'.git') and not tool.exists(q/'checkpoint') and not tool.exists(q/'independent-recovery')
entries=tool.tree_inventory(source,policy)
pending=[e for e in entries if e['kind']=='pending_sensitive']
assert not pending,'Source sensitive candidates need classification before capture'
capture_policy=r/'policy.json'
if capture_policy.exists(): assert json.loads(capture_policy.read_text())==policy_data
else:capture_policy.write_text(json.dumps(policy_data,indent=2)+'\n')
proof={'at':datetime.now(timezone.utc).isoformat(),'source':str(source),'entries':entries,'ordinary_files':sum(e['kind']=='file' for e in entries),'ordinary_bytes':sum(e.get('bytes',0) for e in entries if e['kind']=='file'),'reparse_entries':sum(e['kind']=='reparse' for e in entries),'pending':pending,'tool_sha256':sha(tool_path),'tool_review_sha256':sha(tr/'review.json'),'tool_accepted_state_sequence':state['sequence']}
proof_path=r/(node+'-source-inspection.json');proof_path.write_text(json.dumps(proof,indent=2)+'\n')
claim=json.loads((r/'cp1-20261014/claims.json').read_text())[node]
receipt={'schema_version':1,'run_id':'cp1-20261014','node_id':node,'executor_id':'/root','started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),'input_hash':claim['input_hash'],'changed_files':[],'result':{'unit':'Exact authorized native architecture source capture and independent recovery','source_root':str(source),'destination_scope':str(q),'inspection':str(proof_path),'inspection_sha256':sha(proof_path),'policy':str(capture_policy),'policy_sha256':sha(capture_policy),'ordinary_files':proof['ordinary_files'],'ordinary_bytes':proof['ordinary_bytes'],'reparse_entries':proof['reparse_entries'],'pending_protected_candidates':0,'source_write_authority':'READ_ONLY_INPUT; no source writer is dispatched by this session','requirements':['Capture every exact ordinary original and seal/verify all ZIP/inventory hashes.','Independently restore to fresh destination and compare every file against source-bound inventory.','Source before/after bytes/metadata remain exact; no source edit or usable-link recreation.','No runtime import or product/status/owner promotion follows from archival preservation.','Use separate Collaborative Review before substantial capture handoff and guarded publication.'],'actual_capture':False,'tool_acceptance':{'state_sequence':state['sequence'],'review':str(tr/'review.json'),'review_sha256':sha(tr/'review.json')}} ,'commands':[{'command':'Python312 -B prepare_cp1_receipt.py '+node+'; approved exact tool, exact N roots/policy/source original hashes and protected/reparse inventory inspection','exit_status':0}],'validations':[{'name':'exact_current_native_source_controlled_targets_and_approved_tool_verified','passed':True},{'name':'all_source_entries_hashed_zero_pending_no_source_writes','passed':True}],'exit_status':0}
(r/(node+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'node':node,'files':proof['ordinary_files'],'bytes':proof['ordinary_bytes'],'reparse':proof['reparse_entries'],'pending':0,'source_inspection_sha256':sha(proof_path),'policy_sha256':sha(capture_policy)}))

