"""Record bounded author self-review separately from independent acceptance."""
from pathlib import Path
import ast,hashlib,json
W=Path(__file__).resolve().parent;F=Path('T:/00-Active/Project-AI-CETA');B=W.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value):
    with (W/name).open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2);stream.write('\n')
def methods(path):
    tree=ast.parse(path.read_text(encoding='utf8'));items={}
    for node in tree.body:
        if isinstance(node,ast.ClassDef):
            for method in node.body:
                if isinstance(method,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    items[node.name+'.'+method.name]=ast.dump(method,include_attributes=False)
        elif isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
            items[node.name]=ast.dump(node,include_attributes=False)
    return items
source_changes={}
for path in sorted((W/'candidate').rglob('*.py')):
    rel=path.relative_to(W/'candidate');old=W/'seed-before'/rel
    before,after=methods(old),methods(path)
    changed=sorted(name for name in set(before)|set(after) if before.get(name)!=after.get(name))
    if changed:source_changes[rel.as_posix()]=changed
assert source_changes=={
    'src/ceta/identity/native_approval.py':['NativeApprovalSession.transcript'],
    'src/ceta/identity/owner_session.py':['NativeCpuOwnerSession.retain_verified_effect','NativeOwnerSession.retain_verified_enrollment']}
owner=methods(W/'candidate/src/ceta/identity/owner_session.py')
original=methods(W/'canonical-before/src/ceta/identity/owner_session.py')
assert owner['NativeCpuOwnerSession._effect_fence']==original['NativeCpuOwnerSession._effect_fence']
assert owner['NativeCpuOwnerSession._effect_operation']==original['NativeCpuOwnerSession._effect_operation']
report=json.loads((W/'CONTROLS-FINAL.json').read_bytes());witness=json.loads((W/'TRANSCRIPT-BUDGET-WITNESS-R2.json').read_bytes())
old=json.loads((B.parent/'jb1/work/JOINT-CONTROLS-R3.json').read_bytes())
assert len(old['selected'])==112 and set(old['selected'])<=set(report['selected'])
assert report['tests_run']==136 and report['successful'] and report['selected']==report['started']==report['stopped']
assert not any(report[n] for n in ('failures','errors','skips','expected_failures','unexpected_successes','forbidden_call_attempts'))
assert report['candidate_origins']==witness['candidate_origins'] and len(report['candidate_origins'])==5
assert witness['tests_run']==4 and witness['failures']==witness['errors']==witness['skips']==0
save('AUTHOR-SELF-REVIEW.json',dict(schema_version=1,run_id='ceta-jb23-r2',reviewer='/root/broader_successor_author',
    review_type='AUTHOR_SELF_REVIEW_ONLY',independent_approval=False,canonical_integration=False,
    source_method_delta_from_rejected_seed=source_changes,candidate_files=8,
    controls=dict(original_ids_retained=112,new_ids=sorted(set(report['selected'])-set(old['selected'])),
        total=136,failures=0,errors=0,skips=0,report_sha256=sha(W/'CONTROLS-FINAL.json'),
        process_sha256=sha(W/'CONTROLS-FINAL-PROCESS.json')),
    four_case_witness=dict(cases=witness['cases'],report_sha256=sha(W/'TRANSCRIPT-BUDGET-WITNESS-R2.json'),
        process_sha256=sha(W/'FOUR-CASE-WITNESS-R2-PROCESS.json')),
    controls_are_pure_simulation=True,no_native_person_or_hardware_acceptance=True,
    original_joint_budget_semantics_retained=True,hot_effect_fence_and_shared_operation_AST_unchanged=True,
    native_epoch_provider_gap='Unresolved; genuine measured epoch/code/peer provisioning remains required',
    prior_AC7_attempt='Consumed; worker exit 0xC0000142; failing DLL/main/API order unknown; no replay',
    admission_bound_ns=50_000_000,admission_timing_qualified=False,
    response_and_settlement_reserves='One second each; unmeasured engineering policy, not established native capacity',
    previous_failure=dict(path='TRANSCRIPT-CONTROLS-PROCESS.json',exit_status=1,
        cause='Test method was temporarily attached to the new class rather than original registry class',
        resolution='Original class/112 exact IDs restored; failed output and before-image preserved'),
    limits=['Rejected JB1 remains rejected and immutable','Fresh candidate awaits named independent review',
        'No canonical writes, Git mutation, fixture writes, process/native/socket test effects or installed dependency changes',
        'Genuine native authorization-to-effect, installed/offline/migration/endurance/human/hardware acceptance remain open',
        'No overall product completion percentage is supported']))
notes="""# JB2 original allowance consumption repair

Status: authored and controlled-tested, awaiting independent review; not applied to canonical source.

The fresh candidate retains the rejected JB1 seven-file seed and its joint-budget behavior. Only NativeApprovalSession.transcript changes within those seven files. A separately authorized eighth source input adds checks in NativeOwnerSession.retain_verified_enrollment and NativeCpuOwnerSession.retain_verified_effect. The original packet and actual implement scope are unchanged; OWNER-CONSUMER-INPUT-AMENDMENT.json binds that additional input.

Transcript consumption checks the original helper elapsed cutoff before cached verification, after native currentness and after transcript construction. Both owner consumers check the same nonrenewing allowance before use, after transcript return, after observation/binding/currentness work and before publishing the retained local witness. Effect retention finishes the existing operation guard before proof publication. Its local explicit normal-unwind path preserves the exact body exception when Python contextlib would otherwise assign a hostile exception traceback, retaining any guard cleanup fault separately. The shared guard and hot effect fence are unchanged.

The final controlled cohort contains all 112 original test IDs and 24 new tests, with 136 passes and no failures/errors/skips. A separate four-case witness checks 5 ms success, direct cached verification at 25 ms refusal, currentness advancing 10 + 20 ms refusal and expired-poll cancellation. Both executions route exactly five runtime modules to this candidate and prohibit actual native, process and socket activity. Native facts and binding ports in consumer controls are recordings, not genuine authority facts or grants. Original failed test setup and rejected JB1 evidence remain preserved.

All clocks retain their own domains. The original session/wire deadline, decreasing ceremony allowances, WAITING/cache behavior, observer clamp, uncertainty custody, no retries/refunds/extensions and 50,000,000 ns admission contract remain unchanged. One-second response and one-second settlement reserves remain an unmeasured engineering policy. Neither these checks nor prior broader regressions qualify native admission timing or complete the genuine authorization-to-native-effect route.

Genuine native epoch/provider provisioning, the consumed AC7 attempt (exit 0xC0000142, exact failing DLL/main/API order unknown), remaining application/model requirements and installed, offline, migration, endurance and human/hardware acceptance remain open. There is no defensible overall completion percentage.
"""
with (W/'REPAIR-NOTES.md').open('x',encoding='utf8',newline='\n') as stream:stream.write(notes)
print(json.dumps(dict(author_self_review=True,independent_approval=False,controls=136,new_controls=24,changed_methods=source_changes)))
