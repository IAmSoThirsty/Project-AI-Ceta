"""Authenticate the frozen connection input and claim only this recovery candidate."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess

F = Path('T:/00-Active/Project-AI-CETA')
BASE = F/'.agents/cpu-capacity-connection-20261017'
Q = F/'.agents/cpu-outcome-recovery-20261017'
R = Path(__file__).resolve().parent
RUN, ACTOR = 'cpu-outcome-recovery-20261017', '/root/full_report_repair'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()
def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2); stream.write('\n')
def invoke(label, args):
    command = ['powershell','-NoProfile','-File','T:/02-Config/agents/taar-orchestrate.ps1',
        *args, '--runtime-root', str(R)]
    result = subprocess.run(command, cwd=F, capture_output=True)
    for suffix, raw in [('stdout',result.stdout),('stderr',result.stderr)]:
        with (R/(label+'.'+suffix)).open('xb') as stream: stream.write(raw)
    response = json.loads(result.stdout.decode('utf-8-sig'))
    save(R/(label+'.json'),dict(command=command,exit_status=result.returncode,response=response))
    assert result.returncode == 0 and response['allowed'] is True,response
    return response
manifest = F/'.agents/runtime/cpu-capacity-connection-20261017/cut-r1/MANIFEST.json'
assert sha(manifest) == '12c6dd58311e85686f68cbb7bc18a8d631ec418428fe2ddad88f017d575f4ce1'
source = json.loads(manifest.read_bytes())
plan = F/'.agents/runtime/real-effect-20261014/plan-review/IMPLEMENTATION-AND-ACCEPTANCE-PLAN.md'
assert sha(plan) == 'd99cbc87dd5430b6287b3a77759fd75b8cdb0276a372c9a4cca8ba1bc047119c'
for name,pin in source['payload_hashes'].items(): assert sha(BASE/name) == pin,name
Q.mkdir(exist_ok=False)
invoke('run-init',['run','init','--root','T:/','--scope',str(Q),'--run-id',RUN])
for node,result in [('discover',dict(parent_manifest=str(manifest),parent_sha256=sha(manifest),
        specification=str(plan),specification_sha256=sha(plan),inspected=['owner_session','cpu_execution','effect_transactions','journal','outcome_capacity'])),
    ('plan',dict(authority='Root assigned public recovery implementation',candidate=str(Q),
        scopes=['exact same-owner bookkeeping recovery','same-journal failed outcome recovery','fresh reconciliation reservation'],
        source_publication=False,native_execution='HELD',separate_provenance_owner='/root/publication_recovery_review'))]:
    claim = invoke(node+'-claim',['node','claim',RUN,node,'--executor',ACTOR,'--workspace',str(Q)])['claim']
    path=R/(node+'-receipt.json')
    save(path,dict(schema_version=1,run_id=RUN,node_id=node,executor_id=ACTOR,
        started_at=claim['claimed_at'],finished_at=now(),input_hash=claim['input_hash'],
        changed_files=[],result=result,commands=[],validations=[dict(name='exact_inputs_and_callers_read',passed=True)],exit_status=0))
    invoke(node+'-complete',['node','complete',RUN,node,str(path)])
claim=invoke('implement-claim',['node','claim',RUN,'implement','--executor',ACTOR,'--workspace',str(Q)])['claim']
assert claim['effective_write_scope']==['00-Active/Project-AI-CETA/.agents/cpu-outcome-recovery-20261017/**']
for name,pin in source['payload_hashes'].items():
    raw=(BASE/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==pin
    dest=Q/name;dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as stream:stream.write(raw)
save(R/'INPUTS.json',dict(at=now(),actor=ACTOR,source_root=str(BASE),candidate=str(Q),
    manifest=dict(path=str(manifest),sha256=sha(manifest)),payload_hashes=source['payload_hashes'],
    plan=dict(path=str(plan),sha256=sha(plan)),claim=claim,copied_LOC_credit=0))
print(json.dumps(dict(candidate=str(Q),claim=claim['input_hash'],payloads=len(source['payload_hashes']))))
