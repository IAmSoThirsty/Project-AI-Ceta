"""Freeze approved corrected qualification review and complete its ordinary node."""
from pathlib import Path
from datetime import datetime,timezone
import json,os,subprocess,sys
F=Path('T:/00-Active/Project-AI-CETA');B=F/'.agents/runtime/oq23/ds2';W=B/'work';C=B/'control-r2';R=B/'review-r2';OLD=B/'review';RUN='ceta-ds23-r2-gate-r2';PIN='736a2a3ef8639bf99acced85d0ce3950b74b01bf9f23d856148ca7a7061df2f6';GRAPH='997829e1616609bafc88eea12f601eba7d715ad0e03b27e55a3f1af59a0d51ed';HELPER='f17cd2b8214f9076cdcfa87683253a5a486bbd31c6d41d2f4887dd0cd9ccd858';AMEND='83713b152c26a24624ec6de6ef3243a58b8b1bd6303fa3a2092a1b369292a658'
os.environ.update(PYTHONDONTWRITEBYTECODE='1',GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false');sys.path[:0]=[str(W),'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce']
import directory_snapshot as d,conservation
from taar.orchestration_graph import compile_graph
from taar.orchestration_runtime import OrchestrationRuntime,_snapshot_workspace
s=d.legacy;assert s.sha(W/'MANIFEST.json')==PIN and s.sha(C/'ROOT-CLOSE-QUALIFICATION-R2.py')==HELPER and s.sha(B/'packet-r2/ROOT-CLOSURE-RELOCATION-AMENDMENT.json')==AMEND
review=json.loads((R/'REVIEW.json').read_bytes());assert review['decision']=='approved' and review['manifest_sha256']==PIN and review['graph_fingerprint']==GRAPH and review['root_candidate_closure_sha256']==HELPER and review['root_closure_relocation_amendment_sha256']==AMEND and not review['findings']
m=json.loads((W/'MANIFEST.json').read_bytes());old=json.loads((OLD/'MANIFEST.json').read_bytes())
for rel,pin in m['files'].items():assert s.stable(W/rel)==pin
for path,pin in m['external_pins'].items():assert s.sha(Path(path))==pin
for rel,pin in old['files'].items():assert s.sha(OLD/rel)==pin
for path,pin in old['external_pins'].items():assert s.sha(Path(path))==pin
assert old['decision']=='rejected';conservation.observe()
graph=compile_graph(Path('T:/'),C);assert graph.fingerprint==GRAPH
state=json.loads((C/RUN/'state.json').read_bytes());claim=json.loads((C/RUN/'claims.json').read_bytes())['review'];assert state['nodes']['review']['state']=='RUNNING' and claim['executor_id']=='/root/status_packet_review' and Path(claim['workspace'])==R
assert not any((B/'delivery').iterdir()) and not (C/'ROOT-QUALIFICATION-COMPLETION.json').exists()
observed=_snapshot_workspace(R,Path('T:/'));receipt_rel=(R/'REVIEW-RECEIPT.json').relative_to(Path('T:/')).as_posix();manifest_rel=(R/'MANIFEST.json').relative_to(Path('T:/')).as_posix();changed=sorted(set(observed)|{receipt_rel,manifest_rel})
commands=[]
for name in ('ADMISSION-READBACK-R4-PROCESS.json','EXACT-DS2-VERIFIER-PROCESS.json','ROOT-HELPER-CONTROLS-PROCESS.json'):
 p=json.loads((R/name).read_bytes());assert p['actual_process_exit_status']==0;commands.append(dict(command=subprocess.list2cmdline(p['argv']),exit_status=0))
for name in ('ADMISSION-READBACK-PROCESS.json','ADMISSION-READBACK-R2-PROCESS.json','ADMISSION-READBACK-R3-PROCESS.json'):assert json.loads((R/name).read_bytes())['actual_process_exit_status']==1
receipt=dict(schema_version=1,run_id=RUN,node_id='review',executor_id='/root/status_packet_review',started_at=claim['claimed_at'],finished_at=datetime.now(timezone.utc).isoformat(),input_hash=claim['input_hash'],changed_files=changed,decision='approved',result=dict(decision='approved',manifest_sha256=PIN,review_sha256=s.sha(R/'REVIEW.json'),root_candidate_closure_sha256=HELPER,root_closure_relocation_amendment_sha256=AMEND,graph_fingerprint=GRAPH,review_evidence_manifest=str(R/'MANIFEST.json'),root_candidate_closure_approved=True,original_DS2_review_remains_rejected=True,retained_source_controls=50,retained_independent_provider_repair_cases=6,current_synthetic_helper_boundary_cases=10,no_retained_source_control_or_full_F_replay=True,canonical_test_bodies_executed=0,ST2_execution_authorized=False,full_product_acceptance=False),commands=commands,validations=[dict(name='Exact frozen source and prior independent repair controls, successful source qualification and all historical rejections conserved',passed=True),dict(name='Corrected graph declares exact pinned DS2 verifier and read-only adoption is actually SUCCEEDED and closed',passed=True),dict(name='Exact relocated Root helper origin/approval/receipt boundaries and amendment bindings independently checked',passed=True),dict(name='All failed independent probe attempts retained, separately named successor checks passed',passed=True)],exit_status=0)
s.save(R/'REVIEW-RECEIPT.json',receipt)
full=s.snapshot(R,F,ignored=frozenset());assert full['excluded_symlinks']=={};base=R.relative_to(F);leaves={Path(name).relative_to(base).as_posix():native for name,native in full['files'].items()};assert 'MANIFEST.json' not in leaves
external={str(W/rel):pin['sha256'] for rel,pin in m['files'].items()};external.update(m['external_pins']);external[str(W/'MANIFEST.json')]=PIN
external.update({str(OLD/rel):pin for rel,pin in old['files'].items()});external.update(old['external_pins']);external[str(OLD/'MANIFEST.json')]=s.sha(OLD/'MANIFEST.json')
for rel in m['permitted_postfreeze_outputs']:
 path=W/rel
 if path.is_file():external[str(path)]=s.sha(path)
adoption=json.loads((C/'ADOPTION-RECEIPT.json').read_bytes());external.update(adoption['result']['source_and_rejection_input_pins'])
additional=[C/'AGENTS.md',C/'ADOPTION-RECEIPT.json',C/RUN/'receipts/implement.json',C/'ROOT-CLOSE-QUALIFICATION.py',C/'ROOT-CLOSE-QUALIFICATION-R2.py',B/'packet-r2/INPUTS.json',B/'packet-r2/ROOT-CLOSURE-RELOCATION-AMENDMENT.json',Path(adoption['result']['preserved_author_pin_assertion_failure']['path']),Path('T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce/taar/orchestration_graph.py')]
for path in additional:external[str(path)]=s.sha(path)
manifest=dict(decision='approved',reviewer='/root/status_packet_review',candidate_manifest_sha256=PIN,run_id=RUN,graph_fingerprint=GRAPH,root_candidate_closure_sha256=HELPER,root_closure_relocation_amendment_sha256=AMEND,root_candidate_closure_approved=True,review_sha256=s.sha(R/'REVIEW.json'),files={name:native['sha256'] for name,native in leaves.items()},file_native=leaves,directory_identity={name:{key:native[key] for key in ('device','inode','mode')} for name,native in full['directories'].items()},external_pins=external,explicit_self_exclusion='MANIFEST.json; exact external handoff SHA256',all_physical_review_leaves_pinned=True,canonical_or_installed_Git_mutation=False,ST2_execution_amendment_approved=False,full_product_acceptance=False)
s.save(R/'MANIFEST.json',manifest)
assert _snapshot_workspace(R,Path('T:/')).keys()==set(changed)
for name,pin in manifest['files'].items():assert s.sha(R/name)==pin
for name,pin in external.items():assert s.sha(Path(name))==pin
runtime=OrchestrationRuntime(C);answer=runtime.complete(RUN,'review',R/'REVIEW-RECEIPT.json');assert answer['allowed']
v=runtime.verify(RUN);assert v['allowed'] and v['receipts_valid'] and v['states']['review']=='SUCCEEDED' and v['states']['validate']=='READY' and not v['terminal_success']
state=json.loads((C/RUN/'state.json').read_bytes());assert state['nodes']['review']['claim'] is None and json.loads((C/RUN/'claims.json').read_bytes())=={}
normalized=C/RUN/state['nodes']['review']['receipt_ref'];norm=json.loads(normalized.read_bytes());assert norm['decision']=='approved' and norm['result']['root_candidate_closure_sha256']==HELPER and norm['result']['root_closure_relocation_amendment_sha256']==AMEND
print(json.dumps(dict(decision='approved',actual_review_state='SUCCEEDED',receipts_valid=True,states=v['states'],manifest_sha256=s.sha(R/'MANIFEST.json'),review_sha256=s.sha(R/'REVIEW.json'),actual_persisted_receipt_raw_sha256=s.sha(normalized),actual_normalized_receipt_hash=norm['receipt_hash'],supplied_receipt_sha256=s.sha(R/'REVIEW-RECEIPT.json'),root_candidate_closure_sha256=HELPER,root_closure_relocation_amendment_sha256=AMEND,frozen_review_files_excluding_manifest=len(leaves),external_pins=len(external),claims_empty=True,ST2_execution_authorized=False,full_product_acceptance=False)))
