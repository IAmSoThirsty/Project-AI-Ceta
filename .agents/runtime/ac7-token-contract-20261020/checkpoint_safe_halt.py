from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,os
F=Path('T:/00-Active/Project-AI-CETA');R=F/'.agents/runtime/ac7-token-contract-20261020';E=F/'.agents/runtime/reasoning-core-repair-20261020'
D=R/'safe-halt-20261020';D.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest(); now=lambda:datetime.now(timezone.utc).isoformat()
def save(p,v):
    with p.open('x',encoding='utf8',newline='\n') as s:json.dump(v,s,indent=2,ensure_ascii=False);s.write('\n')
def ref(p):return dict(path=str(p),sha256=sha(p))
base=F/'.agents/runtime/js8-20261015/amendment-report1/ACCEPTED-SOURCE-BASELINE.json'
b=json.loads(base.read_bytes())['effective_payload_hashes'];assert len(b)==352 and all(sha(F/n)==h for n,h in b.items())
manifest=E/'R3-MANIFEST.json';m=json.loads(manifest.read_bytes());assert all(sha(F/n)==h for n,h in m['candidate_hashes'].items())
statepath=E/'lease-r3/reasoning-adapter-repair-r3-20261020/state.json';state=json.loads(statepath.read_bytes());assert state['sequence']==13 and all(s['state']=='SUCCEEDED' and s['claim'] is None for s in state['nodes'].values())
complete=E/'lease-r3/integrate-complete-r2.json';assert json.loads(complete.read_bytes())['response']['allowed'] is True
ac7statepath=R/'ac7-token-contract-20261020/state.json';ac7state=json.loads(ac7statepath.read_bytes());assert ac7state['nodes']['implement']['state']=='CANCELLED' and all(s['claim'] is None for s in ac7state['nodes'].values())
q=F/'.agents/ac7-token-contract-20261020';inputs=json.loads((R/'INPUTS.json').read_bytes())['payload_hashes'];candidate={n:sha(q/n) for n in inputs};changed=[n for n,h in inputs.items() if candidate[n]!=h]
expected=['contracts/ISOLATED_WORKER_V1.md','native/windows_broker/isolated_worker.rs','src/ceta/supervisor/isolated_worker.py','tests/contract/test_isolated_worker.py','tests/contract/test_isolation_token_diagnostics.py'];assert sorted(changed)==expected
save(D/'AC7-PARTIAL-MANIFEST.json',dict(at=now(),candidate=str(q),payload_hashes=candidate,changed_paths=changed,Source_publication=False,accepted=False))
record=dict(at=now(),state='SAFELY_HALTED_AT_EXPLICIT_USER_REQUEST',reason='Codex restart to load new skills',project=str(F),branch=subprocess.check_output(['git','branch','--show-current'],cwd=F).decode().strip(),head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=F).decode().strip(),
    accepted_Source_baseline=ref(base),accepted352_hashes_unchanged=True,
    reasoning=dict(manifest=ref(manifest),result=ref(E/'R3-FINAL-RESULT.json'),review=ref(F/'.agents/runtime/reasoning-core-review-20261020/R3/FINAL-DISPOSITION.json'),ledger=ref(statepath),sequence=state['sequence'],ledger_head=state['ledger_head'],all_six_nodes='SUCCEEDED',active_claims=[],tests=50,independent_assertions=20,sqlite_closed_writer=20,sqlite_closed_reviewer=4,scope='Bounded advisory adapter repair present in canonical source',canonical_application_attached=False,model_inference=False,accepted352_amended=False,summary_helper_issue=dict(classification='not blocking safe halt; requires separate reporting-helper repair',issue='finish_r3_integration.py reached successful integrate completion, then raised KeyError reading nonexistent top-level claims from state.json',do_not_rerun_completed_transitions=True,actual_integrate_complete=ref(complete))),
    recovery=dict(manifest=ref(F/'.agents/runtime/cpu-outcome-recovery-repair-20261020/MANIFEST.json'),handoff=ref(F/'.agents/runtime/cpu-outcome-recovery-r4-regression-20261020/HANDOFF.json'),review=ref(F/'.agents/runtime/cpu-outcome-recovery-review-20261020/REVIEW-R2.json'),tests=dict(regression=177,original_callers=24),sqlite_lifetimes_closed=291,Source_published=False,remaining='Joined native/full/destination verification and public/runtime/restart requirements; private same-lease repeat defensive gap remains recorded'),
    AC6=dict(result=ref(F/'.agents/runtime/ac6-readiness-20261020/EXECUTION-RESULT.json'),independent_review=ref(F/'.agents/runtime/reasoning-core-review-20261020/AC6-RESULT-REVIEW/REVIEW-R1.md'),outcome='FAILED_PRE_RESUME_TOKEN_QUALIFICATION',approval='CONSUMED_ONE_ATTEMPT',profile_cleanup='OWN_PROFILE_DELETE_AND_ABSENCE_SUPPORTED',restricted_worker_resumed=False,additional_profile_operations_authorized=False),
    AC7=dict(candidate=str(q),partial_manifest=ref(D/'AC7-PARTIAL-MANIFEST.json'),lease_ledger=ref(ac7statepath),lease_state='CANCELLED_ON_USER_HALT',active_claims=[],controlled_parent=ref(R/'CONTROLLED-PARENT-R1.json'),controlled_parent_tests=27,build=ref(R/'build-r1/BUILD.json'),pure_Rust_tests=5,worker_sha256=sha(R/'build-r1/isolated_worker.exe'),restricted_worker_execution=False,host_profile_operations=False,Source_published=False,independent_candidate_review='NOT_STARTED',unfinished=['Qualification oracle, pinned successor tool/wrapper and proposal not prepared','New native current-token query case written but NOT RUN','Candidate final review and native isolation qualification pending'],next='After explicit resume, read checkpoint/new skills and recheck pins, obtain a successor bounded lease, finish coherent oracle/tool/tests; obtain independent review and fresh exact operator approval before any profile attempt'),
    JS9=dict(agent_checkpoint=ref(F/'.agents/runtime/js9-runtime-20261020/SAFE-HALT-recovery-regression20-20261020T082046850780Z.json'),merge_map=ref(F/'.agents/runtime/joined-runtime-readiness-20261020/MERGE-MAP-R2.json'),candidate_exists=(F/'.agents/js9-runtime-20261020').exists(),construction_started=False,lease_claimed=False,next='After explicit resume, obtain exclusive two-directory lease; exact-byte assemble the26 product paths and reviewed reasoning; implement journal capacity/observer/provenance composition and required validation'),
    worker_status='All three delegated agents completed and halted; all Root-owned execution handles polled terminal',product_complete=False,
    user_resume_required=True,protected_work='Dirty tracked, untracked, ignored, historical evidence, other projects and unrelated host processes preserved')
save(D/'CHECKPOINT.json',record)
checkpoint=ref(D/'CHECKPOINT.json')
for relative in ['handoff/continuity.json','build/progress.json']:
    path=F/relative;raw=path.read_bytes();save(D/(path.name+'.before.meta.json'),dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest()))
    with (D/(path.name+'.before')).open('xb') as s:s.write(raw)
    value=json.loads(raw);value['safe_halt_20261020']=dict(at=record['at'],state=record['state'],checkpoint=checkpoint,user_resume_required=True)
    if relative.startswith('handoff/'):
        value['active_workers']=[]
        value['first_next_action']='Paused at explicit user request for Codex restart. Read '+str(D/'CHECKPOINT.json')+' and the newly available applicable skills after explicit resume. AC6 approval is consumed; AC7 partial work is preserved under a cancelled lease and needs a successor lease, coherent qualification tool, independent review and fresh approval before any profile attempt. JS9 construction has not started. Reasoning R3 gates all succeeded at sequence13; preserve its scope and the accepted JS8 Source352 baseline.'
        value['next_action']=value['first_next_action']
    output=(json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode('utf8')
    assert path.read_bytes()==raw,'Concurrent status change; refusing overwrite'
    with path.open('wb') as s:s.write(output);s.flush();os.fsync(s.fileno())
    assert json.loads(path.read_bytes())==value
save(D/'STATUS-UPDATE-RECEIPT.json',dict(at=now(),checkpoint=checkpoint,updated={n:sha(F/n) for n in ['handoff/continuity.json','build/progress.json']},before_images_preserved=True,Source352_unchanged=all(sha(F/n)==h for n,h in b.items()),reasoning_seven_unchanged=all(sha(F/n)==h for n,h in m['candidate_hashes'].items())))
print(json.dumps(dict(checkpoint=str(D/'CHECKPOINT.json'),sha256=sha(D/'CHECKPOINT.json'),reasoning_all_six='SUCCEEDED',AC7_claims_cleared=True,status_registers_updated=True,Source352_unchanged=True)),flush=True)
