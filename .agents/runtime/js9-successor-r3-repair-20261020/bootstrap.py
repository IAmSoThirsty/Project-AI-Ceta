"""Acquire the Root-authorized successor-r3 repair scope with external runtime."""
from pathlib import Path
from datetime import datetime, timezone
import json, subprocess
F=Path('T:/00-Active/Project-AI-CETA');E=Path(__file__).resolve().parent
C=E/'control';W=F/'.agents/runtime/js9-runtime-20261020/successor-r3'
RUN='js9-successor-r3-repair-20261020';ACTOR='/root/recovery_regression20'
def save(path,value):
    with path.open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2);stream.write('\n')
def invoke(label,args):
    argv=['powershell','-NoProfile','-File','T:/02-Config/agents/taar-orchestrate.ps1',*args,'--runtime-root',str(C)]
    result=subprocess.run(argv,cwd=F,capture_output=True)
    for suffix,raw in [('stdout',result.stdout),('stderr',result.stderr)]:
        with (C/(label+'.'+suffix)).open('xb') as stream:stream.write(raw)
    response=json.loads(result.stdout.decode('utf-8-sig'))
    save(C/(label+'.json'),dict(command=argv,exit_status=result.returncode,response=response))
    assert result.returncode==0 and response['allowed'] is True,response
    return response
assert not W.exists();W.mkdir();C.mkdir()
invoke('init',['run','init','--root',str(F),'--scope',str(E),'--run-id',RUN])
invoke('ready',['run','ready',RUN])
claim=invoke('claim',['node','claim',RUN,'repair','--executor',ACTOR,'--workspace',str(W)])['claim']
assert claim['effective_write_scope']==['.agents/runtime/js9-runtime-20261020/successor-r3/**']
save(C/'LEASE-ACQUIRED.json',dict(at=datetime.now(timezone.utc).isoformat(),run=RUN,claim=claim,
    Source_Q_R2_writes=False,native_or_full_execution=False))
print(json.dumps(dict(run=RUN,input_hash=claim['input_hash'],scope=claim['effective_write_scope'])),flush=True)
