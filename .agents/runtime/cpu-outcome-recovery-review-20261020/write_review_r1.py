"""Freeze the independent review against the exact recovery cut; no publication."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

F = Path('T:/00-Active/Project-AI-CETA')
Q = F/'.agents/cpu-outcome-recovery-20261017'
A = F/'.agents/runtime/cpu-outcome-recovery-20261017'
V = F/'.agents/runtime/cpu-outcome-recovery-regression-20261020'
R = Path(__file__).resolve().parent
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
def ref(path):
    return dict(path=str(path), sha256=sha(path))
manifest = json.loads((A/'cut-r3/MANIFEST.json').read_bytes())
base_path = F/'.agents/runtime/js8-20261015/amendment-report1/ACCEPTED-SOURCE-BASELINE.json'
baseline = json.loads(base_path.read_bytes())
assert sha(A/'HANDOFF.json') == '1669814ed47186d8774fbbc9b124bfd2b9c1e3f2b3ec5aab0d2f0096b3a4bbfa'
assert sha(A/'cut-r3/MANIFEST.json') == '463d703e0b92580d45574d2b89276af645e55d6bfb5431e3ddc71d8c9d18ca87'
assert sha(base_path) == '5d001e3144805864048edf165e7124fdba21f8d99fc01b36e1f7463877b68bb0'
assert all(sha(Q/path) == pin for path, pin in manifest['payload_hashes'].items())
assert all(sha(F/path) == pin for path, pin in baseline['effective_payload_hashes'].items())
finding = dict(id='RJR20-01', category='confirmed defect', severity='P1',
    classification='blocking current task', state='OPEN_REPAIR_REQUIRED',
    subject='Recovery liveness registration is not exception safe',
    source='src/ceta/kernel/cpu_execution.py', lines=[372, 385],
    decisive_lines=[382, 383, 384, 385],
    caller='src/ceta/kernel/cpu_outcome_recovery.py:255-285',
    source_sha256=manifest['payload_hashes']['src/ceta/kernel/cpu_execution.py'],
    trigger='The owner-map publication succeeds and the following store-map publication raises.',
    observed='The exact frozen method leaves the owner row registered while coordinator.active is None and no store row exists. The original MemoryError has no custody attachment. require_selected_coordinator then raises CPU_EXECUTION_OTHER_KERNEL_ACTIVE.',
    consequence='Recovery cannot publish its active lease or acknowledge surviving registration custody. Later admission and mutation on the owner are denied by an orphan registration. The outer recovery caller tests active is lease before retirement, so this partial-publication state follows its no-retirement branch.',
    severity_basis='A fault in the recovery admission path can permanently block the affected owner in the running interpreter and leave custody undisclosed. The reproduction uses deliberate failure injection; it does not estimate real-world failure probability or establish unauthorized effect execution.',
    evidence=ref(R/'REGISTRATION-FAILURE-REPRODUCTION.json'),
    reproduction=ref(R/'probe_recovery_registration.py'),
    requirements=['r6 C06', 'r6 C12', 'RE-T20', 'RE-T27', 'RE-30', 'RE-33', 'COMMON_CONTRACT lifetime and recovery'],
    assigned_repair_owner='/root integration coordinator must assign a separate bounded writer',
    repair='Protect the complete recovery-registration publication, retiring only exact owned partial rows on every BaseException. Preserve the original exception. If exact retirement cannot be established, retain and expose the original lease and partial registration state so later guarded cleanup can operate. Use the existing normal claim_liveness/release_liveness discipline without enabling dispatch or clearing a competing registration.',
    closure='Fresh distinct tests at both registration publications, after partial publication, exact-own cleanup failure, competing-row preservation, and primary-exception retention. Re-freeze changed bytes, rerun the affected recovery/cross-kernel cohort, and obtain a new independent disposition before integration.',
    reopening='Any change to registration publication, cleanup, caller retirement, global liveness ownership or exception handling.')
strengths = [
    dict(id='S1', claim='Original context, thread and consumed invocation remain required; recovery does not dispatch.', evidence=['cpu_outcome_recovery.py:217-250', 'cpu_execution.py:503-505', 'cpu_execution.py:653-654', 'cpu_execution.py:678-679', 'owner_session.py:683-704'], limits='Native identity/provenance in the controlled cohort remain controlled.'),
    dict(id='S2', claim='A failed canonical outcome retains final event/check/projection inputs and retries only exact original bytes.', evidence=['cpu_outcome_recovery.py:17-71', 'effect_transactions.py:250-267', 'effect_transactions.py:351-361', 'test_cpu_outcome_recovery.py:74-87', 'test_cpu_outcome_recovery.py:152-175']),
    dict(id='S3', claim='Lost COMMIT notification uses exact same-journal authenticated readback instead of another write.', evidence=['journal.py:459-539', 'state.py:152-200', 'test_cpu_outcome_recovery.py:89-99', 'test_cpu_outcome_recovery.py:310-330'], limits='This readback deliberately refuses changed heads/projections; it does not reconstruct lost native custody.'),
    dict(id='S4', claim='Exact durable retry allocates nothing; advancing reconciliation obtains a fresh reservation on the same journal and preserves consumed permit.', evidence=['cpu_outcome_capacity.py:177-237', 'test_cpu_outcome_recovery.py:187-245']),
    dict(id='S5', claim='Post-mark final-fence denial has an original typed origin and records NOT_STARTED with UNCERTAIN settlement.', evidence=['cpu_outcome_recovery.py:75-133', 'owner_session.py:707-734', 'test_cpu_outcome_recovery.py:248-276'], limits='This claim is the tested post-mark final-fence case. The pre-mark denial outcome path has not been established by this review.'),
    dict(id='S6', claim='Proven empty unconfigured entry retirement preserves PREPARED and checks original context/locks/custody.', evidence=['cpu_outcome_recovery.py:142-206', 'test_cpu_outcome_recovery.py:288-308', 'test_cpu_outcome_recovery.py:341-351']),
]
coverage = [
    dict(requirement='RE-T20 / original-context handoff', current='Implemented in-process with reviewed guards; blocked from integration by RJR20-01.', decisive='Original context/thread/native owner and lock-borrow tests; exact changed-cut regression.'),
    dict(requirement='RE-T26 / RE-26, RE-27, RE-32', current='Partial in-process capability only. Surviving supervisor and cross-process startup recovery remain open.', decisive='Actual native surviving custody, service restart and canonical query without replay.'),
    dict(requirement='RE-T27 / RE-30, RE-33', current='Exact retry, durable readback and fresh same-journal reconciliation implemented; RJR20-01 blocks acceptance.', decisive='Repair registration-fault path, then native storage and recovery qualification.'),
    dict(requirement='RE-T29 / RE-31', current='Capability methods exist. Production callers/UI/service wiring absent in inspected candidate; tested callers are controlled contract tests.', decisive='Public inspect/reconcile control through canonical application with zero Set replay.'),
    dict(requirement='RE-T25 / RE-35, RE-36', current='Unfinished dependency; not satisfied by this cut.', decisive='Surviving native supervisor/observer handle custody and actual retirement.'),
    dict(requirement='RE-T28 / RE-28, RE-29', current='Separate restoration authority remains required and unchanged.', decisive='Distinct genuine approved restore, independent observation and settlement.'),
    dict(requirement='r6 C11-C12 / RE-T31-T32', current='This independent review preserves failures and rejects the frozen cut. Final regression receipt is separately bound when terminal.', decisive='New repaired frozen cut, separate tests/review and Root destination integration.'),
]
regression = dict(first_20261020_attempt=ref(V/'OUTER-RESULT.json'),
    first_result=ref(V/'regression-r1/RESULT.json'),
    first_status='FAILED observer control: SQLite file URI misparsed; no product regression conclusion.',
    observer_repair=ref(R/'OBSERVER-PURE-REVIEW.json'),
    observer_disposition='APPROVED bounded test instrumentation at exact guard/wrapper pins; 19 independent pure parser cases passed.',
    corrected_terminal_at_review=False)
if (V/'attempt-r2/OUTER-RESULT.json').is_file():
    regression['corrected_terminal_at_review'] = True
    regression['corrected_outer'] = ref(V/'attempt-r2/OUTER-RESULT.json')
    regression['corrected_result'] = ref(V/'attempt-r2/regression-r1/RESULT.json')
else:
    regression['corrected_status'] = 'No terminal corrected-run receipt inspected yet; verifier owns released session88449.'
result = dict(at=datetime.now(timezone.utc).isoformat(), actor='/root/recovery_join_review20',
    role='Distinct Collaborative Reviewer, source ROLE-04 Critic', coordinator='/root',
    project=str(F), branch_observed='candidate/societal-reasoning-v1',
    Git_HEAD_observed='83fc9432b4a37ee7f91d6c5b0d358a015548aed4',
    preserved_tracked_modifications=14, job='Independent frozen CPU outcome recovery component integration review',
    scope='Six production deltas, one contract, two test deltas; callers and canonical journal/provenance/cleanup semantics.',
    exclusions=['No reasoning adapter authority or source review.', 'No Source/candidate mutation.',
        'No profile, network, native worker, CPU Set or production approval operations.',
        'No public/native/full-product acceptance claim.'],
    candidate=ref(A/'cut-r3/MANIFEST.json'), handoff=ref(A/'HANDOFF.json'), diff=ref(A/'cut-r3/CHANGES.diff'),
    accepted_Source_baseline=ref(base_path),
    candidate_payloads_verified=len(manifest['payload_hashes']),
    accepted_Source_payloads_verified=len(baseline['effective_payload_hashes']),
    all_candidate_payload_hashes_match=True, all_accepted_Source_payload_hashes_match=True,
    changed_paths=manifest['changes'], findings=[finding], supported_strengths=strengths,
    requirement_coverage=coverage, regression=regression,
    preserved_author_evidence=[ref(A/'controlled-r2/RESULT.json'), ref(A/'timing-r1/RESULT.json'),
        ref(A/'regression-r1/RESULT.json'), ref(A/'FIXTURE-DELTA.json')],
    remaining=[
        dict(classification='blocking current task', issue='RJR20-01 requires a new frozen repair and review before integration.'),
        dict(classification='requires separate follow-up work', issue='Native positive recovery, surviving supervisor/crash custody, cross-process restart and public control composition remain unqualified.'),
        dict(classification='requires separate follow-up work', issue='Durable Stop/checkpoint changes, expired/changed provenance, ambiguous lock/native/liveness cleanup and fresh reservation failure recovery remain explicit open paths in the authored contract/handoff.'),
        dict(classification='not blocking current task', issue='No new authority issuer, scheduler or evidence store was introduced in inspected recovery code.'),
    ],
    independence=dict(authored_candidate_production_files=False, authored_candidate_tests=False,
        reviewer_authored='Only report/pure review probes in assigned new review directory.',
        shared_dependencies='Same host, tools, architecture and model family; internal Collaborative Review, not independent administrative domain or external audit.'),
    commands=[dict(command='E3 -B -X utf8 .agents/runtime/cpu-outcome-recovery-review-20261020/check_observer.py', exit_status=0, result=ref(R/'OBSERVER-PURE-REVIEW.json')),
        dict(command='E3 -B -X utf8 .agents/runtime/cpu-outcome-recovery-review-20261020/probe_recovery_registration.py', exit_status=0, result=ref(R/'REGISTRATION-FAILURE-REPRODUCTION.json'))],
    dictionary_basis=dict(review='Merriam-Webster review verb4a: examine critically or deliberately; https://www.merriam-webster.com/dictionary/review',
        integrate='https://www.merriam-webster.com/dictionary/integrate',
        technical_status='REPAIR_REQUIRED is this explicit reviewer disposition, not a dictionary-defined CETA schema status.'),
    decision='REPAIR_REQUIRED', Source_publication_approved=False,
    runtime_acceptance=False, full_product_complete=False,
    next_action='Assign exact registration publication/cleanup repair with separate tests, freeze a successor, then re-review and run required joined/native/destination validation under Root integration.')
path = R/'REVIEW-R1.json'
with path.open('x', encoding='utf8') as stream:
    json.dump(result, stream, indent=2); stream.write('\n')
print(json.dumps(dict(review=str(path), sha256=sha(path), decision=result['decision'],
    candidate_payloads=result['candidate_payloads_verified'], Source_payloads=result['accepted_Source_payloads_verified'],
    corrected_regression_terminal=regression['corrected_terminal_at_review'])))
