"""Preserve the current human approval and execute its exact reviewed scope once."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys
R=Path(__file__).resolve().parent
F=Path('T:/00-Active/Project-AI-CETA')
assert R==F/'.agents/runtime/ac2-20261014/profile-tool-repair-r2'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
tool=R/'profile_qualification_r2.py'
assert sha(tool)=='41e2bc3b5c289228bd6f9e8912474c9a6c16459543775a52aa1a5ec6e10da5bb'
assert sha(R/'independent-root-review/REVIEW.json')=='016d0c4432554c053f85c28188ac0f742caa52658f8810e779a70877724b598d'
approval={'recorded_at':datetime.now(timezone.utc).isoformat(),'source':'actual_current_human_reply',
 'question_item_id':'["request_user_input_async","call_55d98852ef064a8e8b8943a46482e9c7",0]',
 'human_reply':'Approve this exact profile creation, qualification and own-profile cleanup',
 'profile_name':'CETA.ProjectAICETA.IsolatedWorker.AC1.V1',
 'profile_sid':'S-1-15-2-695244707-3853392321-2130098501-3319658173-178928504-1880712989-1319207162',
 'user_sid':'S-1-5-21-1218874621-2294869469-207301144-1003',
 'proposal_sha256':'75c5a41afd412ab91272ced373b84bfcbe34f5941c1b6dbf95254905a65db55c',
 'prepared_script_sha256':sha(tool),'create_exact_new_profile':True,'delete_only_profile_created_by_this_run':True,
 'authorized_effects':['Create exact previously absent per-user zero-capabilities AppContainer profile',
   'Disposable CETA-owned worker and bounded access-denial probes','Delete only successfully created exact own profile after proved retirement'],
 'exclusions':['elevation','firewall changes','loopback exemptions','host-account creation'],
 'classification':'Operator engineering approval, not a CETA runtime grant or native user-authentication transcript.'}
path=R/'ACTUAL-OPERATOR-APPROVAL.json'
with path.open('x',encoding='utf-8') as out:json.dump(approval,out,indent=2);out.write('\n');out.flush();os.fsync(out.fileno())
argv=[sys.executable,'-B','-X','utf8',str(tool),'--mode','qualify','--approval-receipt',str(path),'--approval-sha256',sha(path)]
started=datetime.now(timezone.utc).isoformat();done=subprocess.run(argv,cwd=F,capture_output=True)
for label,raw in [('stdout',done.stdout),('stderr',done.stderr)]:
    with (R/('APPROVED-QUALIFICATION.'+label)).open('xb') as out:out.write(raw)
record={'started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),'argv':argv,'exit_status':done.returncode,
 'approval_sha256':sha(path),'tool_sha256':sha(tool),'stdout_sha256':sha(R/'APPROVED-QUALIFICATION.stdout'),
 'stderr_sha256':sha(R/'APPROVED-QUALIFICATION.stderr'),'automatic_retry':False}
with (R/'APPROVED-QUALIFICATION.json').open('x',encoding='utf-8') as out:json.dump(record,out,indent=2);out.write('\n')
print(json.dumps(record),flush=True)
print(done.stdout.decode('utf-8-sig'),flush=True)
print(done.stderr.decode('utf-8-sig'),file=sys.stderr,flush=True)
sys.exit(done.returncode)
