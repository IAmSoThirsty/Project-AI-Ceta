"""Retain failed schema assumption and verify existing private replica exactly."""
from review_support import *
old=D/'prepare_review.py';text=old.read_text()
write(D/'PREPARATION-FAILURE-r1.json',{'recorded_at':utc(),'command':subprocess.list2cmdline([str(PY),'-B','-X','utf8',str(old)]),
    'exit_status':1,'script':ordinary(old),
    'traceback':'prepare_review.py line31 TypeError: unsupported operand type(s) for /: WindowsPath and dict',
    'classification':'Reviewer setup assumed parent payloads was a mapping; frozen EN2 uses a list of explicit relative_path rows. No product failure.',
    'partial_replica_retained':str(D/'replica'),'Q_or_Source_edit':False,'claim_or_transition_retry':False})
changes=[("M=D/'replica';assert not M.exists()","M=D/'replica';assert M.is_dir()"),
    ("M.mkdir();replica={}","replica={}"),
    ("    with target.open('xb') as out:out.write(raw);out.flush();os.fsync(out.fileno())\n", "    assert target.is_file(), 'Retained initial replica member missing'\n"),
    ("parents={name:ordinary(parent/name) for name in parent_manifest['payloads']}",
     "parent_rows={row['relative_path']:row for row in parent_manifest['payloads']}\nassert len(parent_rows)==len(parent_manifest['payloads'])==295\nparents={name:ordinary(parent/name) for name in parent_rows}\nassert all(row['sha256']==parent_rows[name]['candidate_sha256'] and row['native_identity']==parent_rows[name]['candidate_native_identity'] for name,row in parents.items())"),
    ("'Source_application':False,'native_process_profile_or_authority_operations':False})",
     "'Source_application':False,'native_process_profile_or_authority_operations':False,\n    'prior_setup_failure':ordinary(D/'PREPARATION-FAILURE-r1.json'),'retained_initial_replica_reverified':True})")]
for before,after in changes:
    assert text.count(before)==1,before
    text=text.replace(before,after)
new=D/'prepare_review_r2.py';compile(text,str(new),'exec')
with new.open('x',encoding='utf8',newline='\n') as out:out.write(text)
print(json.dumps({'new_reader':str(new),'sha256':sha(new),'old_failure_preserved':True,'no_transition_retry':True}),flush=True)
