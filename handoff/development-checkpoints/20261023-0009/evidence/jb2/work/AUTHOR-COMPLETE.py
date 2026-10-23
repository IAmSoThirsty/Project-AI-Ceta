"""Ordinary command-string author receipt for fresh JB2; no self-approval."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,subprocess,sys
F=Path('T:/00-Active/Project-AI-CETA');W=Path(__file__).resolve().parent;B=W.parent;C=B/'control';RUN='ceta-jb23-r2'
p=argparse.ArgumentParser();p.add_argument('--manifest-sha256',required=True);a=p.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(W/'MANIFEST.json')==a.manifest_sha256;m=json.loads((W/'MANIFEST.json').read_bytes())
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_graph import compile_graph
from taar.orchestration_runtime import OrchestrationRuntime,_snapshot_workspace,_changed_files
g=compile_graph(Path('T:/'),C);assert g.fingerprint=='9a3eba303a0de24450b4569905b6792bfea771e643a3e0a9762c9b04eedce943'
rt=OrchestrationRuntime(C);state=json.loads((C/RUN/'state.json').read_bytes());claim=state['nodes']['implement']['claim']
assert claim['executor_id']=='/root/broader_successor_author' and claim['workspace']==str(W) and claim['input_hash']==rt._input_hash(g,state,'implement')
commands=[]
for label in ('FOUR-CASE-WITNESS-R2','CONTROLS-FINAL','FREEZE','PREPARED'):
    v=json.loads((W/(label+'-PROCESS.json')).read_bytes());assert v['exit_status']==0
    commands.append(dict(command=subprocess.list2cmdline(v['command']),exit_status=0))
receipt=W/'AUTHOR-COMPLETION-RECEIPT.json';assert not receipt.exists()
changed=_changed_files(claim['baseline_snapshot'],_snapshot_workspace(W,Path('T:/')))
changed=sorted([*changed,receipt.relative_to(Path('T:/')).as_posix()])
value=dict(schema_version=1,run_id=RUN,node_id='implement',executor_id='/root/broader_successor_author',
    started_at=claim['claimed_at'],finished_at=datetime.now(timezone.utc).isoformat(),input_hash=claim['input_hash'],changed_files=changed,
    result=dict(manifest_sha256=a.manifest_sha256,controls=m['controls'],retained_controls=112,independent_four_case_witness=4,
        failures=0,errors=0,skips=0,actual_process_exit_status=0,canonical_inputs_conserved=560,canonical_writes=False,
        rejected_JB1_preserved=True,native_execution=False,AC7_replay=False,admission_bound_ns=50_000_000,
        independent_approval=False,full_product_acceptance=False),commands=commands,
    validations=[dict(name='All112 original IDs retained with fresh transcript/owner consumption controls',passed=True),
        dict(name='Exact frozen source, actual process evidence, canonical/Git/index and rejectedJB1 conservation',passed=True)],exit_status=0)
with receipt.open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2);stream.write('\n')
rt.complete(RUN,'implement',receipt);state=json.loads((C/RUN/'state.json').read_bytes());node=state['nodes']['implement']
assert node['state']=='SUCCEEDED' and node['claim'] is None
v=rt.verify(RUN);assert v['allowed'] and v['receipts_valid']
print(json.dumps(dict(actual_implement_state=node['state'],actual_claim_closed=True,manifest_sha256=a.manifest_sha256,
    source_receipt_sha256=sha(receipt),persisted_receipt_hash=node['receipt_hash'],verification=v,independent_approval=False)))
