"""Actual disjoint Q/R claims; preserve the prior overly broad read-only attempt."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess
F=Path('T:/00-Active/Project-AI-CETA');R=Path(__file__).resolve().parent;L=R/'lease-r2';Q=F/'.agents/js9-runtime-20261020'
RUN='js9-runtime-r2-20261020';ACTOR='/root/recovery_regression20'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now(timezone.utc).isoformat()
def save(p,v):
 with p.open('x',encoding='utf8') as s:json.dump(v,s,indent=2);s.write('\n')
def invoke(label,args):
 command=['powershell','-NoProfile','-File','T:/02-Config/agents/taar-orchestrate.ps1',*args,'--runtime-root',str(L)]
 completed=subprocess.run(command,cwd=F,capture_output=True)
 for suffix,raw in [('stdout',completed.stdout),('stderr',completed.stderr)]:
  with (L/(label+'.'+suffix)).open('xb') as s:s.write(raw)
 response=json.loads(completed.stdout.decode('utf-8-sig'))
 save(L/(label+'.json'),dict(command=command,exit_status=completed.returncode,response=response))
 assert completed.returncode==0 and response['allowed'] is True,response
 return response
map_path=F/'.agents/runtime/joined-runtime-readiness-20261020/MERGE-MAP-R2.json'
reasoning_path=F/'.agents/runtime/reasoning-core-repair-20261020/R3-MANIFEST.json'
assert sha(map_path)=='9188e21a3208d5d23c519d3b64c3d51c0693687cb661f81bd6cec4b5be21e1f4'
assert sha(reasoning_path)=='f49bda6d197182283964a036d8393851eb49ee1780fbd19137ed905e786a1fa8'
m=json.loads(map_path.read_bytes());r=json.loads(reasoning_path.read_bytes())
base=json.loads(Path(m['source_baseline']['path']).read_bytes())['effective_payload_hashes']
assert len(base)==352 and all(sha(F/n)==p for n,p in base.items())
for row in m['file_overlap']:
 p=F/row['path'];assert (sha(p) if p.is_file() else None)==row['current_Source_sha256']
 assert sha(Path(row['incoming']['path']))==row['incoming']['sha256']
for key in ['candidate_hashes','retained_vendor_hashes']:assert all(sha(F/n)==p for n,p in r[key].items())
assert sha(F/'tests/contract/reasoning/test_reasoning_integration.py')==r['original21_sha256']
Q.mkdir(exist_ok=False)
invoke('run-init',['run','init','--root',str(F),'--scope',str(L),'--run-id',RUN])
for node,result in [('discover',dict(inputs_verified=True,Source352=352,selected26=26,reasoning_r3_manifest=sha(reasoning_path))),('plan',dict(objective='Exact private byte join and same-owner native outcome composition',candidate=str(Q),evidence=str(R),native_execution=False,Source_publication=False,review='Distinct Root-assigned reviewer required'))]:
 invoke(node+'-ready',['run','ready',RUN])
 claim=invoke(node+'-claim',['node','claim',RUN,node,'--executor',ACTOR,'--workspace',str(Q)])['claim']
 receipt=L/(node+'-receipt.json')
 save(receipt,dict(schema_version=1,run_id=RUN,node_id=node,executor_id=ACTOR,started_at=claim['claimed_at'],finished_at=now(),input_hash=claim['input_hash'],changed_files=[],result=result,commands=[],validations=[dict(name='actual_input_and_caller_inspection',passed=True)],exit_status=0))
 invoke(node+'-complete',['node','complete',RUN,node,str(receipt)])
claims={}
for node,workspace,expected in [('implement',Q,'.agents/js9-runtime-20261020/**'),('evidence',R,'.agents/runtime/js9-runtime-20261020/**')]:
 invoke(node+'-ready',['run','ready',RUN])
 claims[node]=invoke(node+'-claim',['node','claim',RUN,node,'--executor',ACTOR,'--workspace',str(workspace)])['claim']
 assert claims[node]['effective_write_scope']==[expected],claims[node]
save(R/'LEASE-ACQUIRED-R2.json',dict(at=now(),run=RUN,claims=claims,combined_scope=['.agents/js9-runtime-20261020/**','.agents/runtime/js9-runtime-20261020/**'],original_attempt='Preserved with read-only transition and lock/cancellation record; no code write scope',Source_publication=False,native_execution_released=False))
print(json.dumps(dict(actual_claims={k:dict(input_hash=v['input_hash'],scope=v['effective_write_scope']) for k,v in claims.items()},run=RUN)),flush=True)
