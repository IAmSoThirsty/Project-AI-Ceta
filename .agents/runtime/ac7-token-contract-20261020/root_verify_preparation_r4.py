"""Root's exact preparation gates and one read-only profile inspection.

This script creates no approval and invokes no qualification/profile mutation.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess
import sys

F=Path('T:/00-Active/Project-AI-CETA')
E=Path(__file__).resolve().parent
R=E/'lease-r3'
Q=F/'.agents/ac7-token-contract-20261020'
PY=F/'.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
W=F/'.agents/fixtures/ac7-token-observation-20261020'
RUN='ac7-qualification-r4-20261020'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now(timezone.utc).isoformat()

def save(path,value):
    with path.open('x',encoding='utf8') as out:json.dump(value,out,indent=2)

def execute(label,argv):
    started=now()
    done=subprocess.run(argv,cwd=F,capture_output=True)
    for suffix,raw in [('stdout',done.stdout),('stderr',done.stderr)]:
        with (E/(label+'.'+suffix)).open('xb') as out:out.write(raw)
    record=dict(started_at=started,finished_at=now(),argv=argv,exit_status=done.returncode,
        stdout_sha256=sha(E/(label+'.stdout')),stderr_sha256=sha(E/(label+'.stderr')))
    save(E/(label+'.json'),record)
    assert done.returncode==0,record
    return done

def taar(label,args):
    argv=['powershell','-NoProfile','-File','T:/02-Config/agents/taar-orchestrate.ps1',
          *args,'--runtime-root',str(R)]
    done=execute(label,argv)
    value=json.loads(done.stdout.decode('utf-8-sig'))
    assert value['allowed'] is True,value
    return value

assert Path(sys.executable)==PY and not sys.flags.optimize
manifest=E/'AC7-QUALIFICATION-MANIFEST-R4.json'
assert sha(manifest)=='83967d7b5c00abc6461cdcb9bbe398bb63b0ab53078d8364f56f383de9b511cf'
cut=json.loads(manifest.read_bytes())
review=F/'.agents/runtime/ac7-qualification-review-20261020/R2/review.json'
assert sha(review)=='d90585db535e80d6d90b0d39a258bfe62504e6fbaa509048666b9ec49f7d4e01'
approved=json.loads(review.read_bytes())
assert approved['decision']=='approved' and approved['reviewer']=='/root/recovery_join_review20'
assert approved['manifest_sha256']==sha(manifest)
tool=Q/'tools/qualify_isolated_worker.py'
wrapper=Q/'tools/run_one_isolation_qualification.py'
proposal=E/'PROFILE-CREATION-PROPOSAL-AC7-R4.json'
assert (approved['tool_sha256'],approved['wrapper_sha256'],approved['proposal_sha256'])==(sha(tool),sha(wrapper),sha(proposal))
assert all(sha(Q/n)==h for n,h in cut['payload_hashes'].items())
source=json.loads((E/'INPUTS.json').read_bytes())['payload_hashes']
assert all(sha(F/n)==h for n,h in source.items())
assert not (E/'ONE-ATTEMPT-STARTED.json').exists() and not (E/'EXECUTION-CLAIM.json').exists()
assert not list(E.glob('q-*'))
state=json.loads((R/RUN/'state.json').read_bytes())
assert state['nodes']['review']['state']=='SUCCEEDED' and state['nodes']['review']['decision']=='approved'
commands=[]
claim=taar('root-validate-claim-r4',['node','claim',RUN,'validate','--executor','/root','--workspace',str(W)])['claim']
done=execute('root-diff-check-r4',['git','-C',str(F),'diff','--check'])
commands.append(dict(command='git -C '+str(F)+' diff --check',exit_status=done.returncode))
receipt=E/'root-validate-receipt-r4.json'
save(receipt,dict(schema_version=1,run_id=RUN,node_id='validate',executor_id='/root',
    started_at=claim['claimed_at'],finished_at=now(),input_hash=claim['input_hash'],changed_files=[],
    result=dict(manifest_sha256=sha(manifest),review_sha256=sha(review),frozen_payloads=357,
        source352_unchanged=True,qualification='PREPARED_CODE_AND_CONTROLLED_TESTS_ONLY',
        profile_operations=False,source_publication=False),commands=commands,exit_status=0,
    validations=[dict(name='exact_frozen_pins_review_and_diff_gate',passed=True)]))
taar('root-validate-complete-r4',['node','complete',RUN,'validate',str(receipt)])
claim=taar('root-integrate-claim-r4',['node','claim',RUN,'integrate','--executor','/root','--workspace',str(Q)])['claim']
assert all(sha(Q/n)==h for n,h in cut['payload_hashes'].items())
receipt=E/'root-integrate-receipt-r4.json'
save(receipt,dict(schema_version=1,run_id=RUN,node_id='integrate',executor_id='/root',
    started_at=claim['claimed_at'],finished_at=now(),input_hash=claim['input_hash'],changed_files=[],
    result=dict(manifest_sha256=sha(manifest),review_sha256=sha(review),
        qualification='REVIEWED_PRIVATE_ENGINEERING_PACKET_READY_FOR_OPERATOR_DECISION',
        copied_source_LOC_credit=0,product_source_publication=False,native_qualification=False,
        actual_human_approval=None),commands=[],exit_status=0,
    validations=[dict(name='prepared_packet_preserved_without_application_or_host_mutation',passed=True)]))
taar('root-integrate-complete-r4',['node','complete',RUN,'integrate',str(receipt)])
state=json.loads((R/RUN/'state.json').read_bytes())
assert all(n['state']=='SUCCEEDED' and n['claim'] is None for n in state['nodes'].values())
# Only the reviewed inspect entry runs: source native-file checks, current-user
# token/SID reads, folder lookup and their own memory/handle retirement.
inspect=execute('ROOT-READONLY-INSPECTION-R4',[str(PY),'-B','-X','utf8',str(tool),'--mode','inspect'])
observed=json.loads(inspect.stdout.decode('utf-8-sig'))
assert observed['native_Create_or_Delete_executed'] is False
assert observed['prior_folder']['HRESULT'] in (-2147024894,-2147024893) and observed['prior_folder']['path'] is None
assert all(sha(Q/n)==h for n,h in cut['payload_hashes'].items()) and all(sha(F/n)==h for n,h in source.items())
save(E/'ROOT-PREPARATION-ACCEPTANCE-R4.json',dict(at=now(),manifest_sha256=sha(manifest),
    independent_review_sha256=sha(review),tool_sha256=sha(tool),wrapper_sha256=sha(wrapper),
    proposal_sha256=sha(proposal),sequence=state['sequence'],ledger_head=state['ledger_head'],
    nodes={n:v['state'] for n,v in state['nodes'].items()},claims=[],read_only_inspection=observed,
    source352_unchanged=True,candidate357_unchanged=True,product_source_publication=False,
    actual_operator_approval=None,profile_attempt=False,native_isolation_qualified=False))
print(json.dumps(dict(preparation_accepted=True,ledger_sequence=state['sequence'],
    all_six_nodes_succeeded=True,profile_absent=True,profile_attempt=False,
    fresh_explicit_operator_approval_required=True)),flush=True)
