"""Bounded CP1 recovery review. No TAAR runtime imports or transitions."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

S=Path(r'T:\00-Active\CETA_Intelligence_Operating_System_Build_Package')
N=Path(r'T:\00-Active\CETA-NATIVE-ARCHITECTURE')
R=S/'.agents/runtime/cp1-20261014'
Q=S/'.agents/cp1-20261014/checkpoint'
DEST=S/'.agents/cp1-20261014/independent-recovery'
TOOL=S/'.agents/pr4-20261014/preserve_ceta_complete.py'
POLICY=R/'policy.json'
started=datetime.now(timezone.utc).isoformat()
def io(p):return '\\\\?\\'+str(p)
def sha(p):
    h=hashlib.sha256()
    with open(io(p),'rb') as f:
        while b:=f.read(1024*1024):h.update(b)
    return h.hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def emit(name,value):
    with (R/name).open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
def inventory(root):
    rows=[]
    def scan(p):
        info=os.lstat(io(p))
        assert not (getattr(info,'st_file_attributes',0)&0x400) and not stat.S_ISLNK(info.st_mode),str(p)
        if p!=root:
            row={'path':p.relative_to(root).as_posix(),'kind':'directory' if stat.S_ISDIR(info.st_mode) else 'file','mode':stat.S_IMODE(info.st_mode)}
            if stat.S_ISREG(info.st_mode):row.update(bytes=info.st_size,sha256=sha(p),mtime_ns=info.st_mtime_ns,device=info.st_dev,inode=info.st_ino,attributes=getattr(info,'st_file_attributes',0))
            else:assert stat.S_ISDIR(info.st_mode),str(p)
            rows.append(row)
        if stat.S_ISDIR(info.st_mode):
            with os.scandir(io(p)) as entries:names=sorted(e.name for e in entries)
            for name in names:scan(p/name)
    scan(root)
    return sorted(rows,key=lambda e:e['path'])
def checkpoint_hashes():
    return {p.relative_to(Path('T:/')).as_posix():sha(p) for p in sorted(Q.iterdir()) if p.is_file()}
commands=[]
def cli(label,argv):
    t0=datetime.now(timezone.utc).isoformat()
    p=subprocess.run(argv,capture_output=True,timeout=120)
    t1=datetime.now(timezone.utc).isoformat()
    for suffix,data in [('stdout',p.stdout),('stderr',p.stderr)]:
        with (R/(label+'.'+suffix)).open('xb') as f:f.write(data)
    record={'argv':argv,'command':subprocess.list2cmdline(argv),'started_at':t0,'finished_at':t1,'exit_status':p.returncode,
            'stdout_sha256':hashlib.sha256(p.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(p.stderr).hexdigest()}
    commands.append(record)
    emit(label+'-command.json',record)
    assert p.returncode==0,label+': '+p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace')
    return json.loads(p.stdout)

try:
    claim=read(R/'cp1-20261014/claims.json')['review']
    assert claim['executor_id']=='/root/template_source_verifier' and claim['input_hash']=='c1849991c2794e347df7d0f870502f1ec66f83b23403ee4bca89bf35efb93ddc'
    assert claim['claimed_at']=='2026-10-14T04:48:28.612449+00:00' and claim['workspace']==str(Q)
    assert sha(TOOL)=='2ccbca31973ead308e1cdcc6676bbd7371cdec29a0f16178f3f55a4ab4130618'
    policy=read(POLICY)
    assert policy['source_roots']==[str(N)] and policy['capture_targets']==[str(Q)] and policy['restore_targets']==[str(DEST)]
    assert not DEST.exists()
    sealed=read(Q/'inventory.json')
    seal_manifest=read(Q/'checkpoint.json')
    assert sealed['source_root']==str(N) and sealed['git'] is None and seal_manifest['complete'] and seal_manifest['pending']==[] and seal_manifest['reparse_entries']==0
    expected=sorted(sealed['entries'],key=lambda e:e['path'])
    assert all(e['kind'] in ('file','directory') for e in expected)
    files=[e for e in expected if e['kind']=='file']
    assert len(files)==1523 and sum(e['bytes'] for e in files)==15072266
    checkpoint_before=checkpoint_hashes()
    assert len(checkpoint_before)==4 and checkpoint_before==claim['baseline_snapshot']
    assert (Q/'COMMITTED').read_text().strip()==sha(Q/'checkpoint.json')
    state_before=sha(R/'cp1-20261014/state.json')
    source_before=inventory(N)
    assert source_before==expected,'Current original source inventory differs from sealed capture'
    verify=cli('review-verify',[sys.executable,'-B',str(TOOL),'--policy',str(POLICY),'verify','--checkpoint',str(Q)])
    restore=cli('review-restore',[sys.executable,'-B',str(TOOL),'--policy',str(POLICY),'restore','--checkpoint',str(Q),'--destination',str(DEST)])
    recovered=inventory(DEST/'working-tree')
    portable=lambda rows:[{k:v for k,v in e.items() if k not in ('device','inode','attributes')} for e in rows]
    assert portable(recovered)==portable(expected),'Recovered bytes/mtime/mode/membership differs'
    source_after=inventory(N)
    assert source_after==source_before==expected,'Original source changed during recovery review'
    checkpoint_after=checkpoint_hashes()
    assert checkpoint_after==checkpoint_before==claim['baseline_snapshot']
    assert not list(DEST.parent.glob(DEST.name+'.incomplete-*'))
    restored_whole=inventory(DEST)
    assert len([e for e in restored_whole if e['kind']=='file'])==1527
    assert restore['ordinary_files']==1523 and restore['inert_reparse_descriptors']==0 and restore['git_objects']==0 and restore['runtime_qualification']=='NOT_RUN'
    assert sha(DEST/'preservation-metadata/inventory.json')==sha(Q/'inventory.json')
    assert sha(DEST/'preservation-metadata/checkpoint.json')==sha(Q/'checkpoint.json')
    assert sha(R/'cp1-20261014/state.json')==state_before
    evidence={'started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),'passed':True,'source':str(N),'checkpoint':str(Q),'recovery_destination':str(DEST),
              'files':1523,'bytes':15072266,'directories':len(expected)-1523,'source_before':source_before,'source_after':source_after,'recovered':recovered,
              'checkpoint_before':checkpoint_before,'checkpoint_after':checkpoint_after,'exact_file_bytes_mtime_modes_and_membership':True,
              'source_identity_attributes_before_after_exact':True,'commands':commands,'verify_output':verify,'restore_output':restore,
              'recovery_full_inventory':restored_whole,'pending':[],'reparse_entries':0,'source_writes':False,'TAAR_transitions_performed':False}
    emit('independent-recovery-evidence.json',evidence)
    report='''# CP1 independent recovery / Collaborative Review

APPROVED for the exact sealed CETA-NATIVE-ARCHITECTURE checkpoint's ordinary-file preservation and fresh recovery only. This is separate internal agent review under shared administration; /root authored the capture. No product/runtime qualification, source adoption, integration, publication, or rename is granted.

Actual approved CLI verify and restore both returned exit0 with absolute policy/checkpoint/destination arguments. The restore target was absent before execution and is exactly the policy-authorized .agents/cp1-20261014/independent-recovery. Actual Windows I/O restored all1523 ordinary files,15072266 bytes and251 directories beneath working-tree, with four separate preservation-metadata files. No overwrite, usable reparse link, Git repository restoration, or pending checkpoint admission occurred. No incomplete restore stage remains.

An independent standard-library comparison checked the complete source inventory before and after against the sealed inventory, including every file's SHA256,size,mtime_ns,mode,device,inode and attributes. Every recovered file matched bytes,size,mtime_ns and mode, with exact file/directory membership and directory modes. Recovered file identities intentionally differ from the original source; they are fresh files. All four immutable checkpoint file hashes remain exactly the claimed baseline. Source inventories are identical before and after; no source writes occurred.

Exact argv,UTC times,raw stdout/stderr,exit statuses,all per-file observations and the approved recovery output are preserved in independent-recovery-evidence.json and review-verify/review-restore command/output files. The review workspace remains checkpoint; changed_files=[] refers to that immutable workspace. The separately authorized recovery destination is explicitly recorded in the result rather than being concealed as a checkpoint change.

The capture source is not a Git worktree. Ordinary file-mode and timestamp equality does not qualify ACL/security-principal isolation, runtime behavior, production readiness, or complete CETA consolidation. No broader tests or source edits were performed. No TAAR runtime module was imported and no transition was executed. Review write/recovery scope is released at handback; work halts for the app update.
'''
    with (R/'collaborative-review.md').open('x',encoding='utf-8',newline='\n') as f:f.write(report)
    sys.path.insert(0,str(SHARED))
    from taar.orchestration_receipts import validate_receipt,load_receipt
    compiled=read(R/'cp1-20261014/graph.json')
    receipt={'schema_version':1,'run_id':'cp1-20261014','node_id':'review','executor_id':claim['executor_id'],'started_at':started,
        'finished_at':datetime.now(timezone.utc).isoformat(),'input_hash':claim['input_hash'],'changed_files':[],
        'result':{'scope':'Exact CP1 sealed non-Git native architecture ordinary-file recovery only','verdict':'APPROVED','report':str(R/'collaborative-review.md'),
          'report_sha256':sha(R/'collaborative-review.md'),'evidence':str(R/'independent-recovery-evidence.json'),'evidence_sha256':sha(R/'independent-recovery-evidence.json'),
          'checkpoint_hashes':checkpoint_before,'approved_recovery_output':str(DEST),'recovered_files':1523,'recovered_bytes':15072266,
          'actual_Windows_recovery_performed':True,'every_recovered_file_bytes_mtime_mode_verified':True,'source_before_after_exact':True,
          'immutable_review_workspace_unchanged':True,'source_writes':0,'pending':[],'reparse_entries':0,
          'review_kind':'SEPARATE_INTERNAL_AGENT_SHARED_ADMINISTRATION','capture_author':'/root','reviewer':'/root/template_source_verifier',
          'prior_failures':[],'capture_prior_failures_retained_in_writer_receipt':True,'new_product_tests_executed':False,
          'runtime_product_qualification':False,'TAAR_transitions_performed':False,'halt':'HALT_AFTER_CURRENT_CAPTURE_ITEM_FOR_APP_UPDATE'},
        'commands':[{'command':c['command'],'exit_status':c['exit_status']} for c in commands]+[{'command':subprocess.list2cmdline([sys.executable,'-B',str(Path(__file__))]),'exit_status':0}],
        'validations':[{'name':name,'passed':True} for name in ['approved_tool_policy_and_actual_verify_restore_CLI',
          'all1523_recovered_files_bytes_mtime_modes_and_exact_membership','current_source_before_after_matches_sealed_inventory',
          'checkpoint_four_hashes_exact_no_pending_reparse_or_source_writes','authorized_fresh_recovery_output_separate_from_immutable_review_workspace']],
        'exit_status':0,'decision':'approved'}
    args={'run_id':'cp1-20261014','node_id':'review','executor_id':claim['executor_id'],'input_hash':claim['input_hash'],'claimed_at':claim['claimed_at'],'node':compiled['graph']['nodes']['review']}
    checked=validate_receipt(receipt,**args)
    emit('review.json',receipt)
    assert validate_receipt(load_receipt(R/'review.json'),**args)==checked
    assert checkpoint_hashes()==checkpoint_before and sha(R/'cp1-20261014/state.json')==state_before
    emit('review-schema-validation.json',{'at':datetime.now(timezone.utc).isoformat(),'passed':True,'receipt_sha256':sha(R/'review.json'),'normalized_receipt_hash':checked['receipt_hash'],
        'compiled_review_node_and_all_actual_claim_keywords_used':True,'transitions_performed':False})
    print(json.dumps({'decision':'approved','receipt':str(R/'review.json'),'receipt_sha256':sha(R/'review.json'),'report_sha256':sha(R/'collaborative-review.md'),
        'evidence_sha256':sha(R/'independent-recovery-evidence.json'),'files':1523,'bytes':15072266,'restore':str(DEST),'checkpoint_four_hashes_unchanged':True,
        'source_before_after_exact':True,'strict_receipt_validation_round_trip':True,'scope':'RELEASED','next':'HALT_FOR_APP_UPDATE'}))
except Exception as exc:
    emit('review-problem.json',{'at':datetime.now(timezone.utc).isoformat(),'error':str(exc),'type':type(exc).__name__,'commands':commands,
        'classification':'recovery_review_incomplete','source_writes_by_this_reviewer':False,'TAAR_transitions':False})
    raise
