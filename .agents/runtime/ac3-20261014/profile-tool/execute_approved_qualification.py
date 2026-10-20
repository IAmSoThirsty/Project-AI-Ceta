"""Execute the single actually approved AC3 host operation, with no retry."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,importlib.util,json,os,subprocess,sys
F=Path('T:/00-Active/Project-AI-CETA');R=Path(__file__).resolve().parent
assert R==F/'.agents/runtime/ac3-20261014/profile-tool'
PY=F/'.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
assert Path(sys.executable)==PY and not sys.flags.optimize
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
tool=R/'profile_qualification.py'
assert sha(tool)=='8d3ce66b6ac17d2774f4c11a8852b23b45e41218df887f6b18c99ac0add05414'
assert sha(R/'ROOT-REVIEW.json')=='d80f7431b665cf2e5702a2111a5c6051d6a23ea920738b8434350d11c1a79c95'
assert sha(R/'PROFILE-CREATION-PROPOSAL-AC3.json')=='4fe4d1d15cd5c0297c8ba1e874d94845879039db316a3d2157d35b3d5e5a8941'
assert not (R/'ACTUAL-OPERATOR-APPROVAL.json').exists()
assert not list(R.glob('profile-qualification-*')), 'PRIOR_ATTEMPT_REFUSED_NO_AUTOMATIC_RETRY'
spec=importlib.util.spec_from_file_location('approved_ac3_preflight',tool)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
source_before=m.source_cut();candidate_before=m.candidate_cut();profile_before=m.inspect()
assert len(source_before)==290 and len(candidate_before)==294
assert profile_before['prior_folder']['HRESULT'] in (-2147024894,-2147024893)
assert profile_before['prior_folder']['path'] is None
m.save(R/'APPROVED-PREFLIGHT.json',{'at':m.now(),'tool_sha256':sha(tool),
    'Source290':source_before,'candidate294':candidate_before,'profile':profile_before,
    'Create_Delete_executed':False})
approval={'recorded_at':m.now(),'source':'actual_current_human_reply',
    'question_item_id':'["request_user_input_async","call_a87192bc8b344ac2b6acaab8553b1faa",0]',
    'human_reply':'Approve this exact AC3 attempt, own-profile cleanup, and bounded post-cleanup denial regression',
    'latest_plain_text_confirmation':'Approve this exact AC3 attempt, own-profile cleanup, and bounded post-cleanup denial regression',
    'repeated_confirmation_is_same_single_attempt':True,
    'profile_name':m.NAME,'profile_sid':m.SID,'user_sid':m.USER,
    'proposal_sha256':sha(m.PROPOSAL),'prepared_script_sha256':sha(tool),
    'create_exact_new_profile':True,'delete_only_profile_created_by_this_run':True,
    'authorized_effects':['One exact previously absent per-user zero-capability AppContainer profile creation',
        'One disposable restricted CETA worker and bounded denial probes with six-variable environment',
        'Cleanup only this newly created profile after verified retirement',
        'Original bounded no-profile launch-denial regression after cleanup and fresh absence recheck'],
    'additional_profile_creation_authorized':False,
    'exclusions':['elevation','firewall changes','loopback exemptions','host-account creation'],
    'classification':'Actual operator engineering approval; not a CETA runtime grant or user-authentication transcript.'}
path=R/'ACTUAL-OPERATOR-APPROVAL.json';m.save(path,approval)
argv=[str(PY),'-B','-X','utf8',str(tool),'--mode','qualify','--approval-receipt',str(path),'--approval-sha256',sha(path)]
started=m.now();done=subprocess.run(argv,cwd=F,capture_output=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
for label,raw in (('stdout',done.stdout),('stderr',done.stderr)):
    with (R/('APPROVED-QUALIFICATION.'+label)).open('xb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
record={'started_at':started,'finished_at':m.now(),'command_argv':argv,'exit_status':done.returncode,
    'approval_sha256':sha(path),'tool_sha256':sha(tool),'stdout_sha256':sha(R/'APPROVED-QUALIFICATION.stdout'),
    'stderr_sha256':sha(R/'APPROVED-QUALIFICATION.stderr'),'automatic_retry':False,
    'regression_execution':'Separate original case only after Root verifies actual cleanup and absence.'}
m.save(R/'APPROVED-QUALIFICATION.json',record)
print(json.dumps(record),flush=True)
print(done.stdout.decode('utf-8-sig'),flush=True)
if done.stderr:print(done.stderr.decode('utf-8-sig'),file=sys.stderr,flush=True)
sys.exit(done.returncode)
