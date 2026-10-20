"""Assemble reviewed same-project product bytes under the actual JS9 lease."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json
F=Path('T:/00-Active/Project-AI-CETA');R=Path(__file__).resolve().parent;Q=F/'.agents/js9-runtime-20261020'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
state=json.loads((R/'lease-r2/js9-runtime-r4-20261020/state.json').read_bytes())
assert state['nodes']['implement']['state']=='RUNNING' and state['nodes']['evidence']['state']=='RUNNING'
assert not any(Q.iterdir())
mp=F/'.agents/runtime/joined-runtime-readiness-20261020/MERGE-MAP-R2.json';rp=F/'.agents/runtime/reasoning-core-repair-20261020/R3-MANIFEST.json'
assert sha(mp)=='9188e21a3208d5d23c519d3b64c3d51c0693687cb661f81bd6cec4b5be21e1f4'
assert sha(rp)=='f49bda6d197182283964a036d8393851eb49ee1780fbd19137ed905e786a1fa8'
m=json.loads(mp.read_bytes());reasoning=json.loads(rp.read_bytes());bp=Path(m['source_baseline']['path'])
assert sha(bp)==m['source_baseline']['sha256'];base=json.loads(bp.read_bytes())['effective_payload_hashes']
selected={name:dict(path=str(F/name),sha256=pin,origin='accepted_JS8_Source352') for name,pin in base.items()}
for row in m['file_overlap']:selected[row['path']]={**row['incoming'],'origin':'reviewed_joined26_'+row['origin']}
for key in ['candidate_hashes','retained_vendor_hashes']:
 for name,pin in reasoning[key].items():
  assert name not in selected,name
  selected[name]=dict(path=str(F/name),sha256=pin,origin='reviewed_reasoning_R3_'+key)
name='tests/contract/reasoning/test_reasoning_integration.py';selected[name]=dict(path=str(F/name),sha256=reasoning['original21_sha256'],origin='original21_unchanged')
excluded=m['excluded_auxiliary_paths'] if 'excluded_auxiliary_paths' in m else []
for name,row in selected.items():
 p=Path(row['path']);assert p.resolve().is_relative_to(F) and sha(p)==row['sha256'],name
 dest=Q/name;assert dest.resolve().is_relative_to(Q)
 dest.parent.mkdir(parents=True,exist_ok=True)
 with dest.open('xb') as s:s.write(p.read_bytes())
 assert sha(dest)==row['sha256'],name
v=dict(at=datetime.now(timezone.utc).isoformat(),candidate=str(Q),accepted_Source352=len(base),selected_joined_inputs=26,reasoning_R3_candidate_files=7,vendor_files=150,original21_files=1,assembled_payloads=len(selected),payload_hashes={n:r['sha256'] for n,r in selected.items()},origins=selected,excluded_auxiliary11=m.get('excluded_auxiliary_paths',m.get('excluded_paths',[])),copied_LOC_authorship_credit=0,canonical_Source_written=False)
with (R/'ASSEMBLED-INPUTS.json').open('x',encoding='utf8') as s:json.dump(v,s,indent=2);s.write('\n')
print(json.dumps({k:v[k] for k in ['candidate','assembled_payloads','accepted_Source352','selected_joined_inputs','reasoning_R3_candidate_files','vendor_files','copied_LOC_authorship_credit']}))
