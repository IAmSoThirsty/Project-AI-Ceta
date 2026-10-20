"""Acquire disjoint private code/evidence leases before construction."""
from pathlib import Path
from datetime import datetime,timezone
import json,subprocess
F=Path('T:/00-Active/Project-AI-CETA');R=Path(__file__).resolve().parent
Q=F/'.agents/ac7-loader-capture-20261020';W=R/'records';C=R/'control'
RUN='ac7-loader-capture-20261020';ACTOR='/root/recovery_regression20'
def save(path,value):
    with path.open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2);stream.write('\n')
def invoke(label,args):
    argv=['powershell','-NoProfile','-File','T:/02-Config/agents/taar-orchestrate.ps1',*args,'--runtime-root',str(C)]
    proc=subprocess.run(argv,cwd=F,capture_output=True)
    for suffix,raw in [('stdout',proc.stdout),('stderr',proc.stderr)]:
        with (C/(label+'.'+suffix)).open('xb') as stream:stream.write(raw)
    response=json.loads(proc.stdout.decode('utf-8-sig'))
    save(C/(label+'.json'),dict(command=argv,exit_status=proc.returncode,response=response))
    assert proc.returncode==0 and response['allowed'] is True,response
    return response
assert not Q.exists();Q.mkdir();W.mkdir();C.mkdir()
invoke('init',['run','init','--root',str(F),'--scope',str(R),'--run-id',RUN])
claims={}
for node,workspace in [('implement',Q),('evidence',W)]:
    invoke(node+'-ready',['run','ready',RUN])
    claims[node]=invoke(node+'-claim',['node','claim',RUN,node,'--executor',ACTOR,'--workspace',str(workspace)])['claim']
save(C/'LEASE-ACQUIRED.json',dict(at=datetime.now(timezone.utc).isoformat(),run=RUN,claims=claims,
    debugger_native_profile_or_host_operations=False))
print(json.dumps({name:dict(input_hash=row['input_hash'],scope=row['effective_write_scope']) for name,row in claims.items()}),flush=True)
