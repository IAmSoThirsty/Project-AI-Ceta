"""Execute the single AC7 attempt authorized by the actual current user reply."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import subprocess

F=Path('T:/00-Active/Project-AI-CETA')
R=Path(__file__).resolve().parent
Q=F/'.agents/ac7-token-contract-20261020'
PY=F/'.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now(timezone.utc).isoformat()

def save(path,value):
    with path.open('x',encoding='utf8',newline='\n') as out:
        json.dump(value,out,indent=2);out.write('\n');out.flush();os.fsync(out.fileno())

tool=Q/'tools/qualify_isolated_worker.py'
wrapper=Q/'tools/run_one_isolation_qualification.py'
review=F/'.agents/runtime/ac7-qualification-review-20261020/R2/review.json'
proposal=R/'PROFILE-CREATION-PROPOSAL-AC7-R4.json'
assert sha(tool)=='79da07922e6a7f56cca0ae9d90a2498c3d6f28a58dcb6bd3144ab56a87b5bd84'
assert sha(review)=='d90585db535e80d6d90b0d39a258bfe62504e6fbaa509048666b9ec49f7d4e01'
assert sha(proposal)=='ddb4382f6d2aa9e62d0d39a661c73730cd10e55201a0958542f0fd8829cc6071'
reviewed=json.loads(review.read_bytes())
assert reviewed['decision']=='approved' and reviewed['wrapper_sha256']==sha(wrapper)
prepared=json.loads((R/'ROOT-PREPARATION-ACCEPTANCE-R4.json').read_bytes())
assert prepared['sequence']==13 and prepared['actual_operator_approval'] is None
assert not (R/'ONE-ATTEMPT-STARTED.json').exists() and not (R/'EXECUTION-CLAIM.json').exists()
assert not list(R.glob('q-*'))
p=json.loads(proposal.read_bytes())
approval=R/'OPERATOR-APPROVAL-AC7-20261020.json'
save(approval,dict(recorded_at=now(),source='actual_current_human_reply',
    question_item_id='["request_user_input_async","call_01f68902e4e44f39a8afa32d8c3dbc9d",0]',
    human_reply='Authorize this exact AC7 attempt and own-profile cleanup',
    profile_name=p['name'],profile_sid=p['SID'],user_sid=p['user_sid'],
    proposal_sha256=sha(proposal),prepared_script_sha256=sha(tool),wrapper_sha256=sha(wrapper),
    independent_review_sha256=sha(review),create_exact_new_profile=True,
    delete_only_profile_created_by_this_run=True,profile_attempt_limit=1,
    restricted_worker_limit=1,ordinary_control_limit=1,capabilities=[],
    fixture_labels_only=True,bounded_local_listener=True,
    elevation=False,firewall_change=False,loopback_exemption=False,account_creation=False,
    automatic_retry=False,post_cleanup_regression=False,
    all_CETA_files_and_receipts_under=str(F)))
argv=[str(PY),'-B','-X','utf8',str(wrapper),str(approval),sha(approval),str(review),sha(review)]
save(R/'AUTHORIZED-AC7-COMMAND.json',dict(at=now(),argv=argv,cwd=str(F),
    actual_approval_sha256=sha(approval),tool_sha256=sha(tool),review_sha256=sha(review),
    automatic_retry=False,attempt_limit=1))
started=now()
with (R/'AUTHORIZED-AC7.stdout').open('xb') as out,(R/'AUTHORIZED-AC7.stderr').open('xb') as err:
    done=subprocess.run(argv,cwd=F,stdout=out,stderr=err,
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
save(R/'AUTHORIZED-AC7-TERMINAL.json',dict(started_at=started,finished_at=now(),argv=argv,
    exit_status=done.returncode,stdout_sha256=sha(R/'AUTHORIZED-AC7.stdout'),
    stderr_sha256=sha(R/'AUTHORIZED-AC7.stderr'),automatic_retry=False,
    actual_approval_sha256=sha(approval),attempt_repeated=False))
print(json.dumps(dict(exit_status=done.returncode,approval_sha256=sha(approval),
    attempt_repeated=False,evidence_root=str(R))),flush=True)
raise SystemExit(done.returncode)
