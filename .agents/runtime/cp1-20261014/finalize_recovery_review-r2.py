"""Metadata-only finalization after completed verify/restore/file comparison."""
from datetime import datetime,timezone
import hashlib,json,subprocess,sys
from pathlib import Path
S=Path(r'T:\00-Active\CETA_Intelligence_Operating_System_Build_Package')
R=S/'.agents/runtime/cp1-20261014'
Q=S/'.agents/cp1-20261014/checkpoint'
DEST=S/'.agents/cp1-20261014/independent-recovery'
SHARED=Path(r'T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce')
sys.path.insert(0,str(SHARED))
from taar.orchestration_receipts import validate_receipt,load_receipt
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
def emit(name,value):
    with (R/name).open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
def checkpoint_hashes():return {p.relative_to(Path('T:/')).as_posix():sha(p) for p in sorted(Q.iterdir()) if p.is_file()}
claim=read(R/'cp1-20261014/claims.json')['review']
compiled=read(R/'cp1-20261014/graph.json')
evidence=read(R/'independent-recovery-evidence.json')
failed_command=read(R/'review-native-recovery-command.json')
problem=read(R/'review-problem.json')
assert failed_command['exit_status']==1 and problem['type']=='NameError' and 'SHARED' in problem['error']
assert sha(R/'review-native-recovery.stdout')==failed_command['stdout_sha256']
assert sha(R/'review-native-recovery.stderr')==failed_command['stderr_sha256']
assert evidence['passed'] and evidence['files']==1523 and evidence['bytes']==15072266
assert evidence['source_before']==evidence['source_after']
expected=sorted(read(Q/'inventory.json')['entries'],key=lambda e:e['path'])
portable=lambda rows:[{k:v for k,v in e.items() if k not in ('device','inode','attributes')} for e in rows]
assert expected==evidence['source_before'] and portable(expected)==portable(evidence['recovered'])
assert checkpoint_hashes()==evidence['checkpoint_before']==evidence['checkpoint_after']==claim['baseline_snapshot']
assert len(checkpoint_hashes())==4 and evidence['pending']==[] and evidence['reparse_entries']==0
assert all(c['exit_status']==0 for c in evidence['commands']) and len(evidence['commands'])==2
state_pin=sha(R/'cp1-20261014/state.json')
report_before=(R/'collaborative-review.md').read_bytes()
with (R/'collaborative-review-r1.md').open('xb') as f:f.write(report_before)
old='No TAAR runtime module was imported and no transition was executed.'
new='Only the installed TAAR strict receipt validator was imported for validation; no orchestration runtime service or transition was executed.'
report=report_before.decode('utf-8')
assert report.count(old)==1
report=report.replace(old,new)
report+='\nThe first reviewer script completed verify, restore and all per-file comparisons, then failed only at receipt finalization because SHARED was undefined. Its exact script, raw output and problem record are retained under result.prior_failures. This metadata-only finalizer repaired the validation import path without rerunning restore or altering the checkpoint, original source or recovery.\n'
with (R/'collaborative-review-r2.md').open('x',encoding='utf-8',newline='\n') as f:f.write(report)
(R/'collaborative-review.md').write_bytes((R/'collaborative-review-r2.md').read_bytes())
failure={'classification':'fixed_now','operation':'Reviewer receipt finalization after completed recovery comparison',
    'command':failed_command['command'],'exit_status':1,'error':problem['error'],'type':problem['type'],
    'raw_command_receipt':str(R/'review-native-recovery-command.json'),'raw_command_receipt_sha256':sha(R/'review-native-recovery-command.json'),
    'raw_stdout_sha256':failed_command['stdout_sha256'],'raw_stderr_sha256':failed_command['stderr_sha256'],
    'failed_script_sha256':failed_command['script_sha256'],'problem_sha256':sha(R/'review-problem.json'),
    'repair':'Fresh R-only finalizer declares installed TAAR validation path; actual verify/restore and all file comparisons retained without replay.',
    'recovery_defect':False}
receipt={'schema_version':1,'run_id':'cp1-20261014','node_id':'review','executor_id':claim['executor_id'],
 'started_at':evidence['started_at'],'finished_at':datetime.now(timezone.utc).isoformat(),'input_hash':claim['input_hash'],'changed_files':[],
 'result':{'scope':'Exact CP1 sealed non-Git native architecture ordinary-file recovery only','verdict':'APPROVED',
 'report':str(R/'collaborative-review.md'),'report_sha256':sha(R/'collaborative-review.md'),
 'evidence':str(R/'independent-recovery-evidence.json'),'evidence_sha256':sha(R/'independent-recovery-evidence.json'),
 'checkpoint_hashes':checkpoint_hashes(),'approved_recovery_output':str(DEST),'recovered_files':1523,'recovered_bytes':15072266,'recovered_directories':251,
 'actual_Windows_recovery_performed':True,'every_recovered_file_bytes_mtime_mode_verified':True,'source_before_after_exact':True,
 'immutable_review_workspace_unchanged':True,'source_writes':0,'pending':[],'reparse_entries':0,
 'review_kind':'SEPARATE_INTERNAL_AGENT_SHARED_ADMINISTRATION','capture_author':'/root','reviewer':claim['executor_id'],
 'prior_failures':[failure],'capture_prior_failures_retained_in_writer_receipt':True,'new_product_tests_executed':False,
 'runtime_product_qualification':False,'TAAR_transitions_performed':False,'validation_only_tool_import':True,
 'halt':'HALT_AFTER_CURRENT_CAPTURE_ITEM_FOR_APP_UPDATE'},
 'commands':[{'command':c['command'],'exit_status':0} for c in evidence['commands']]+[{'command':subprocess.list2cmdline([sys.executable,'-B',str(Path(__file__))]),'exit_status':0}],
 'validations':[{'name':name,'passed':True} for name in ['approved_tool_policy_and_actual_verify_restore_CLI',
 'all1523_recovered_files_bytes_mtime_modes_and_exact_membership','current_source_before_after_matches_sealed_inventory',
 'checkpoint_four_hashes_exact_no_pending_reparse_or_source_writes','authorized_fresh_recovery_output_separate_from_immutable_review_workspace']],
 'exit_status':0,'decision':'approved'}
args={'run_id':'cp1-20261014','node_id':'review','executor_id':claim['executor_id'],'input_hash':claim['input_hash'],
 'claimed_at':claim['claimed_at'],'node':compiled['graph']['nodes']['review']}
checked=validate_receipt(receipt,**args)
emit('review.json',receipt)
assert validate_receipt(load_receipt(R/'review.json'),**args)==checked
assert checkpoint_hashes()==claim['baseline_snapshot'] and sha(R/'cp1-20261014/state.json')==state_pin
emit('review-schema-validation.json',{'at':datetime.now(timezone.utc).isoformat(),'passed':True,'receipt_sha256':sha(R/'review.json'),
 'normalized_receipt_hash':checked['receipt_hash'],'compiled_review_node_and_all_actual_claim_keywords_used':True,
 'all_current_commands_zero_exit':True,'prior_failure_retained':True,'checkpoint_and_state_unchanged':True,
 'restore_replayed':False,'validation_only_tool_import':True,'transitions_performed':False})
print(json.dumps({'decision':'approved','receipt_sha256':sha(R/'review.json'),'report_sha256':sha(R/'collaborative-review.md'),
 'evidence_sha256':sha(R/'independent-recovery-evidence.json'),'files':1523,'bytes':15072266,'recovery':str(DEST),
 'checkpoint_four_hashes_unchanged':True,'source_before_after_exact':True,'strict_validation_round_trip':True,
 'prior_metadata_failure_preserved':True,'restore_replayed':False,'scope':'RELEASED','next':'HALT_FOR_APP_UPDATE'}))
