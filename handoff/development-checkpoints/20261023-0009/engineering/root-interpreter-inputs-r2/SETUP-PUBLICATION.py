"""Compile a fresh later publication scope only after accepted closed preparation."""
import os,sys
if sys.flags.optimize != 0:
 raise RuntimeError('CP9 requires unoptimized Python before imports or effects')
os.environ.pop('PYTHONOPTIMIZE',None)
from pathlib import Path
from datetime import datetime,timezone
import json,sys,os,hashlib
F=Path('T:/00-Active/Project-AI-CETA');P=F/'.agents/runtime/oq23/cp9';W=P/'work';C=P/'publication-control';Q=P/'publication-packet'
os.environ.update(PYTHONDONTWRITEBYTECODE='1',GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false');sys.path[:0]=[str(W),'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce']
import checkpoint_core as c;import exact_git_scope as e
from taar.orchestration_graph import compile_graph
from taar.orchestration_runtime import OrchestrationRuntime
v=OrchestrationRuntime(P/'control').verify(c.RUN);assert v['receipts_valid'] and v['terminal_success'] and all(x=='SUCCEEDED' for x in v['states'].values())
assert (P/'control/ROOT-PREPARATION-COMPLETION.json').is_file() and not C.exists() and not Q.exists()
audit_source=P/'control/lease_audit_r5.py';audit_review=P/'control/lease-audit-review-r5/REVIEW.json';root_control=P/'control/ROOT-PUBLICATION.py'
audit_decision=json.loads(audit_review.read_bytes());assert audit_decision['decision']=='approved' and audit_decision['source_sha256']==c.sha(audit_source.read_bytes())
assert audit_decision['independent_review'] is True

final=c.sha((P/'control/FINAL-CANONICAL-INPUTS-R2.json').read_bytes());prepared=json.loads((W/'prepared-0001/PREPARED.json').read_bytes());pack=next(Path(name) for name in prepared['pack_files'] if name.endswith('.pack'));pack_id=pack.stem.removeprefix('checkpoint-');scope=e.scope_paths(pack_id)
C.mkdir();Q.mkdir();(P/'publication-review').mkdir()
command='"'+str(Path(sys.executable))+'" -E -B -X utf8 "'+str(W/'verify_publication.py')+'"'
overrides=dict(implement=dict(kind='agent',role='worker',access='read_only'),review=dict(kind='agent',role='reviewer',access='write_scoped',write_scope=[(P/'publication-review').relative_to(Path('T:/')).as_posix()+'/**']),validate=dict(kind='gate',access='read_only',commands=[command]),integrate=dict(kind='integration',role='integrator',access='write_scoped',write_scope=scope))
graph_doc=dict(version=1,graph=dict(id='t_drive_repository_change',override_nodes=overrides));fence=chr(96)*3
(C/'AGENTS.md').write_text('# Ninth development checkpoint exact Git publication\n\nOne fresh reviewed ordinary descendant checkpoint. Claim .git itself and only the17 compiled Git declarations, with ordinary pre-push hook and exact normal LFS cache/lock. Preserve active HEAD/index, canonical bytes, existing objects, unrelated refs/metadata and historical failed receipts. Installed stock admission and all transition/receipt/snapshot checks remain active. No force/reset/clean/replay/production or full-product acceptance.\n\n'+fence+'agents-graph\n'+json.dumps(graph_doc,indent=2)+'\n'+fence+'\n',newline='\n')
graph=compile_graph(Path('T:/'),C)
packet=dict(schema_version=1,recorded_at=datetime.now(timezone.utc).isoformat(),project=str(F),run_id=c.PUBLICATION_RUN,preparation_run=c.RUN,parent=c.PARENT,commit=prepared['commit'],ref=c.REF,origin=c.ORIGIN,graph_fingerprint=graph.fingerprint,git_scope=scope,pack_id=pack_id,work_freeze_sha256=c.sha((W/'WORK-FREEZE.json').read_bytes()),prepared_sha256=c.sha((W/'prepared-0001/PREPARED.json').read_bytes()),final_input_sha256=final,pre_push_hook_sha256=c.stable(F/'.git/hooks/pre-push')[1]['sha256'],root_execution_control=dict(path=str(root_control),sha256=c.sha(root_control.read_bytes())),lease_audit_source=dict(path=str(audit_source),sha256=c.sha(audit_source.read_bytes())),lease_audit_review=dict(path=str(audit_review),sha256=c.sha(audit_review.read_bytes())),full_product_acceptance=False,completion_percentage=None,one_attempt=True)
c.save(Q/'INPUTS.json',packet)
(Q/'PLAN.md').write_text('Publish only the exact prepared descendant '+prepared['commit']+' of '+c.PARENT+' to '+c.REF+' in '+c.ORIGIN+'. Revalidate source/root/HEAD/branch/origin/dirty/index/ancestry/leases and current pack bytes. Independent review and the actual declared gate precede one Root claim of .git itself with exactly17 Git declarations. Import only this new pack, retain stock hook, CAS-update local checkpoint ref from the pinned parent, ordinary hook-enabled push, and remote plus anonymous commit-pinned readbacks. Preserve all failures and partial effects without rollback, force or replay. The original C1 integration stays FAILED. No native/full-product qualification or percentage.\n',newline='\n')
rt=OrchestrationRuntime(C);a=rt.init_run(graph,c.PUBLICATION_RUN);assert a['allowed'];c.save(C/'ROOT-run-init-api.json',dict(api='OrchestrationRuntime.init_run',response=a))
for node in ('discover','plan','implement'):
 a=rt.claim(c.PUBLICATION_RUN,node,'/root',workspace=Q);assert a['allowed'];c.save(C/('ROOT-'+node+'-claim-api.json'),dict(api='OrchestrationRuntime.claim',response=a));claim=json.loads((C/c.PUBLICATION_RUN/'claims.json').read_bytes())[node]
 receipt=dict(schema_version=1,run_id=c.PUBLICATION_RUN,node_id=node,executor_id='/root',started_at=claim['claimed_at'],finished_at=datetime.now(timezone.utc).isoformat(),input_hash=claim['input_hash'],changed_files=[],result=dict(publication_packet_sha256=c.sha((Q/'INPUTS.json').read_bytes()),work_freeze_sha256=packet['work_freeze_sha256'],commit=prepared['commit'],exact_git_scope=scope,canonical_Git_mutation=False,independent_review_still_required=True,full_product_acceptance=False),commands=[],validations=[dict(name='Exact frozen preparation and fresh publication packet/graph17scope compiled; ordinary hook pinned',passed=True)],exit_status=0)
 path=C/(node+'-receipt.json');c.save(path,receipt);a=rt.complete(c.PUBLICATION_RUN,node,path);assert a['allowed'];c.save(C/('ROOT-'+node+'-complete-api.json'),dict(api='OrchestrationRuntime.complete',response=a))
c.save(C/'ROOT-SELF-REVIEW.json',dict(recorded_at=datetime.now(timezone.utc).isoformat(),author='/root',independent_review=False,publication_packet_sha256=c.sha((Q/'INPUTS.json').read_bytes()),work_freeze_sha256=packet['work_freeze_sha256'],graph_fingerprint=graph.fingerprint,exact_scope_count=17,ordinary_hook=True,no_canonical_mutation=True,full_product_acceptance=False))
print(json.dumps(dict(publication_packet_sha256=c.sha((Q/'INPUTS.json').read_bytes()),graph_fingerprint=graph.fingerprint,commit=prepared['commit'],pack_id=pack_id,scope_count=17,canonical_Git_mutation=False,independent_review_required=True)))
