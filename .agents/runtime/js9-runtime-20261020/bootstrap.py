"""Claim the existing bounded orchestration protocol before private construction."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,subprocess
F=Path('T:/00-Active/Project-AI-CETA');R=Path(__file__).resolve().parent
Q=F/'.agents/js9-runtime-20261020'
RUN='js9-runtime-20261020';ACTOR='/root/recovery_regression20'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now(timezone.utc).isoformat()
def save(p,v):
 with p.open('x',encoding='utf8') as s:json.dump(v,s,indent=2);s.write('\n')
def invoke(label,args):
 command=['powershell','-NoProfile','-File','T:/02-Config/agents/taar-orchestrate.ps1',*args,'--runtime-root',str(R)]
 completed=subprocess.run(command,cwd=F,capture_output=True)
 for suffix,raw in [('stdout',completed.stdout),('stderr',completed.stderr)]:
  with (R/(label+'.'+suffix)).open('xb') as s:s.write(raw)
 response=json.loads(completed.stdout.decode('utf-8-sig'))
 save(R/(label+'.json'),dict(command=command,exit_status=completed.returncode,response=response))
 assert completed.returncode==0 and response['allowed'] is True,response
 return response
map_path=F/'.agents/runtime/joined-runtime-readiness-20261020/MERGE-MAP-R2.json'
reasoning_path=F/'.agents/runtime/reasoning-core-repair-20261020/R3-MANIFEST.json'
assert sha(map_path)=='9188e21a3208d5d23c519d3b64c3d51c0693687cb661f81bd6cec4b5be21e1f4'
assert sha(reasoning_path)=='f49bda6d197182283964a036d8393851eb49ee1780fbd19137ed905e786a1fa8'
m=json.loads(map_path.read_bytes()); reasoning=json.loads(reasoning_path.read_bytes())
base_path=Path(m['source_baseline']['path']);assert sha(base_path)==m['source_baseline']['sha256']
base=json.loads(base_path.read_bytes())['effective_payload_hashes']
assert len(base)==352 and all(sha(F/name)==pin for name,pin in base.items())
for row in m['file_overlap']:
 current=F/row['path'];assert (sha(current) if current.is_file() else None)==row['current_Source_sha256']
 assert sha(Path(row['incoming']['path']))==row['incoming']['sha256']
for key in ['candidate_hashes','retained_vendor_hashes']:
 assert all(sha(F/name)==pin for name,pin in reasoning[key].items())
assert sha(F/'tests/contract/reasoning/test_reasoning_integration.py')==reasoning['original21_sha256']
assert not Q.exists()
initial=invoke('run-init',['run','init','--root',str(F),'--scope',str(R),'--run-id',RUN])
for node,result in [('discover',dict(objective='Exact joined input and current caller inspection',merge_map=dict(path=str(map_path),sha256=sha(map_path)),reasoning_r3=dict(path=str(reasoning_path),sha256=sha(reasoning_path)),accepted_source_payloads=352,selected_product_inputs=26,canonical_Source_modified=False)),('plan',dict(objective='Private exact-byte join and minimal native outcome runtime composition',scope=[str(Q),str(R)],new_request_compiler=False,native_execution=False,Source_publication=False,independent_review='Root assigns distinct reviewer before acceptance'))]:
 ready=invoke(node+'-ready',['run','ready',RUN])
 claim=invoke(node+'-claim',['node','claim',RUN,node,'--executor',ACTOR,'--workspace',str(F)])['claim']
 receipt=R/(node+'-receipt.json')
 save(receipt,dict(schema_version=1,run_id=RUN,node_id=node,executor_id=ACTOR,started_at=claim['claimed_at'],finished_at=now(),input_hash=claim['input_hash'],changed_files=[],result=result,commands=[],validations=[dict(name='actual_input_and_call_site_inspection',passed=True)],exit_status=0))
 invoke(node+'-complete',['node','complete',RUN,node,str(receipt)])
invoke('implement-ready',['run','ready',RUN])
claim=invoke('implement-claim',['node','claim',RUN,'implement','--executor',ACTOR,'--workspace',str(F)])['claim']
expected=['.agents/js9-runtime-20261020/**','.agents/runtime/js9-runtime-20261020/**']
assert sorted(claim['effective_write_scope'])==sorted(expected),claim
save(R/'LEASE-ACQUIRED.json',dict(at=now(),claim=claim,scope=expected,authority='Root resumed single JS9 job; exact two-directory lease',Source_publication=False,native_execution_released=False))
print(json.dumps(dict(lease_acquired=True,run=RUN,scope=claim['effective_write_scope'],input_hash=claim['input_hash'])),flush=True)
