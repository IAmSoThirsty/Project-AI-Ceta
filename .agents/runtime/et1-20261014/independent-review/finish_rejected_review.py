"""Finite independent ET1 review disposition; preserve all observed failures."""
from pathlib import Path
import json, os, subprocess, sys

P = Path('T:/00-Active/Project-AI-CETA')
Q = P / '.agents/et1-20261014'
BASE = P / '.agents/runtime/et1-20261014'
D = BASE / 'independent-review'
M = D / 'replica'
RUN = 'et1-20261014'
sys.path.insert(0, str(P / '.agents/runtime/ka1-20261014'))
import ka1_support as s
s.Q = Q; s.R = D; s.RUN = RUN

setup = json.loads((D / 'PREPARATION.json').read_text())
cohort = json.loads((D / 'COHORT.json').read_text())
hostile = json.loads((D / 'CUMULATIVE-BUDGET-PROBE.json').read_text())
manifest = json.loads((Q / 'TRANSFER-MANIFEST.json').read_text())
assert s.sha(Q / 'TRANSFER-MANIFEST.json') == 'ba5f5ceea225d9b1b3f96cce04bd4f55ee24f8ad23a8d222fcd1fbd136db9cec'
assert s.sha(BASE / 'implement.json') == '5e2528ae48b18b492f36f6208c2cd24797ef41a1b9298ec2e6d7ba4b84305f19'
assert cohort['tests_run'] == 385 and cohort['exit_status'] == 0
assert cohort['expected_ids'] == cohort['executed_ids'] == cohort['stopped_ids']
assert len(set(cohort['executed_ids'])) == 385
assert cohort['failures'] == cohort['errors'] == cohort['skips'] == []
assert cohort['all_observed_resources_closed'] and not cohort['remaining_threads']
assert len(cohort['journals']) == 394 and all(item['closed'] for item in cohort['journals'])
assert len(cohort['native_process_owners']) == 6
assert all(item['closed'] and item['process_closed'] and item['job_closed'] and item['thread_closed']
           for item in cohort['native_process_owners'])
assert hostile['tests_run'] == 2 and hostile['exit_status'] == 1
assert hostile['expected_ids'] == hostile['executed_ids']
assert len(hostile['failures']) == 1 and hostile['errors'] == hostile['skips'] == []
fact, control = hostile['facts']
assert fact['operation_budget']['max_bytes_written'] == fact['required_outcome_bytes'] == 8192
assert [item['cumulative_immutable_lower_bound'] for item in fact['steps']] == [7083, 11360, 15637, 19916]
assert [item['scope_sequence'] for item in fact['steps']] == [7, 9, 11, 13]
assert [item['projection_revision'] for item in fact['steps']] == [2, 3, 4, 5]
assert all(item['charged_budget_and_reservation_unchanged'] for item in fact['steps'])
assert control['exact_retry_no_commit'] and control['actual_native_effects'] == 0
assert all(s.ordinary(Q / name) == row for name, row in setup['original_candidate'].items())
assert all(s.ordinary(M / name) == row for name, row in setup['replica'].items())
assert all(s.ordinary(P / name) == row for name, row in setup['Source290'].items())
assert s.ordinary(s.PY) == setup['python_image']
for reference in [cohort['raw'], hostile['raw'], hostile['probe'], setup['KA1_root_review']]:
    assert s.sha(P / reference['repository_relative_path']) == reference['sha256']

selected = ['src/ceta/kernel/effect_transactions.py', 'src/ceta/kernel/transactions.py',
            'tests/contract/test_owned_cpu_outcome_transactions.py', 'contracts/OWNED_CPU_OUTCOME_V1.md']
report = dict(
    recorded_at=s.utc(), decision='rejected', exit_status=1, reviewer=s.ACTOR,
    author='/root/pressure_writer', manifest_sha256=s.sha(Q / 'TRANSFER-MANIFEST.json'),
    implement_sha256=s.sha(BASE / 'implement.json'),
    source_root=str(P), original_candidate_root=str(Q), execution_replica_root=str(M),
    original_cases=385, original_passed=385, original_failures=0, original_errors=0, original_skips=0,
    additional_hostile_cases=2, hostile_passed=1, hostile_failed=1, hostile_errors=0, hostile_skips=0,
    actual_unique_executions=387, changed_candidate_files=[],
    checked_ET1_paths={name:s.ordinary(Q / name) for name in selected},
    cohort=s.reference(D / 'COHORT.json'), hostile=s.reference(D / 'CUMULATIVE-BUDGET-PROBE.json'),
    probe=s.reference(D / 'probe_cumulative_budget.py'),
    original_candidate_payloads=316, replica_payloads=316, Source_payloads=290,
    original_candidate_and_replica_and_Source_native_bytes_retained=True,
    python_image_before_after=setup['python_image'],
    native_resources=dict(observed_journal_instances=394, all_journals_closed=True,
                          observed_process_owners=6, all_retained_process_job_thread_handles_closed=True,
                          crash_observations=cohort['crash_observations'], remaining_threads=[]),
    reviewed_original_failures=s.reference(BASE / 'PRIOR-FAILURES.json'),
    author_qualification=s.reference(BASE / 'connected-r1.json'),
    author_raw=s.reference(BASE / 'connected-r1.txt'),
    reviewer_preparation_failures=s.reference(D / 'PREPARATION-ERROR-r1.json'),
    preparation_failure_classification='Reviewer metadata dereference and dependent-command sequencing errors before tests. Source290_before is a proof reference, not the payload dictionary. Original parser/driver failures retained; no product failure inferred.',
    finding=dict(
        id='ET1-R20-F01', severity='high', classification='blocking current review',
        source_path='src/ceta/kernel/effect_transactions.py', source_line=190,
        related_lines=[209,210,211], contract_path='contracts/OWNED_CPU_OUTCOME_V1.md', contract_line=69,
        invariant='The finite request max_bytes_written/evidence reservation bounds cumulative request work including bounded reconciliation; per-transaction reset is not an approved exception.',
        code='KernelEffectTransactions._commit resets row[stored_bytes] to 1, then binds and checks only the newly serialized transaction size against the unchanged request reservation. Reconciliation can append immutable journal/evidence repeatedly without accumulating prior use or charging additional capacity.',
        request_max_bytes_written=8192, required_outcome_bytes=8192,
        attempt_transaction_stored_bytes=fact['attempt_stored_bytes'],
        measured_steps=fact['steps'], immutable_bytes_after_four_reconciliations=19916,
        lower_bound_exclusions=fact['lower_bound_excludes'],
        first_established_overflow_iteration=2, immutable_bytes_at_first_overflow=11360,
        budget_and_reservation_unchanged=True,
        exact_test_id=hostile['failures'][0][0], failure=hostile['failures'][0][1],
        repair='In a fresh successor, bind cumulative request capacity to durable canonical state and CAS before each attempted write. Reserve/charge exact attempt and mandatory outcome bytes plus a finite recovery allowance without reusing spent capacity; atomically reject overflow while retaining consumed liability and existing attempt/evidence. Preserve exact settled/uncertain retry as read-only and do not introduce another ledger or issuer.',
        acceptance='Replay this unchanged actual SQLite cumulative-byte oracle against the successor. Keep the 385 retained cases, exact retry control, concurrency/CAS, overflow rollback, crash/reopen/recovery and no-refund/no-replay invariants. Any revised budget policy must be explicit in request/contract/current canonical state, not a counter reset.',
        scope_limit='Controlled owner predicates and actual disposable SQLite storage establish the accounting defect. No actual native CPU operation, genuine approval, external capture, public-runtime activation or physical disk-overhead guarantee was executed or established.'),
    verified_behavior=[
        'All385 original connected cases independently passed with exact author expected IDs, including33 ET1 methods.',
        'Strict canonical schema, full consumed-permit ownership, immutable observation bytes/indexes, separate observer identity, causal ownership limits and conservative unknown states inspected.',
        'Canonical attempt/outcome/task projection commits, rollback, CAS concurrency, two real crash/reopen children, no refund and read-only historical recovery passed in the retained cohort.',
        'Exact UNCERTAIN retry returned unchanged historical data without a new commit in the separate hostile control.',
        'Missing/Boolean/caller-fabricated positive provider remains closed by contract and tests; actual positive providers in this review are controlled domain fixtures.'
    ],
    independence=setup['authorship_disclosure'],
    prior_independent_KA1_review=setup['KA1_root_review'],
    execution_qualification=setup['execution'],
    limits=[
        'Reviewer and author share host/admin trust. Native identities/DLL/module roots in the execution replica differ explicitly from frozen Q; all316 payload bytes matched and all original Q IDs/bytes stayed exact.',
        'No live native authority/Hello/effect/independent observer wiring or public-runtime completion claim.',
        'Only Source290 and the Python image were independently rehashed here; no new whole-E3/library conservation assertion.',
        'Current ET1 documentation states transaction-level size. Root explicitly resolved this against cumulative finite request accounting; the documentation must be reconciled in the successor.'
    ],
    Source_publication=False, configuration_changes=False, genuine_native_effect_invocation=False)
s.write_new(D / 'REPORT.json', report)

sys.path.insert(0, 'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_receipts import validate_receipt, load_receipt
from taar.orchestration_runtime import _snapshot_workspace, _changed_files
claim = json.loads((BASE / RUN / 'claims.json').read_text())['review']
graph = json.loads((BASE / RUN / 'graph.json').read_text())['graph']
assert claim['executor_id'] == s.ACTOR
assert _changed_files(claim['baseline_snapshot'], _snapshot_workspace(Q, Path('T:/'))) == []
receipt = dict(
    schema_version=1, run_id=RUN, node_id='review', executor_id=s.ACTOR,
    started_at=claim['claimed_at'], finished_at=s.utc(), input_hash=claim['input_hash'], changed_files=[],
    result=dict(manifest_sha256=s.sha(Q / 'TRANSFER-MANIFEST.json'), report=s.reference(D / 'REPORT.json'),
                finding_id='ET1-R20-F01', original385_passed=True, hostile1_failed_control1_passed=True,
                immutable_bytes_lower_bound=19916, finite_request_limit=8192,
                all_observed_native_resources_retired=True, Source290_retained=True,
                candidate316_retained=True, Source_publication=False,
                independence=setup['authorship_disclosure']),
    commands=[dict(command=subprocess.list2cmdline([str(s.PY),'-B','-X','utf8',str(D/'run_cohort.py')]),exit_status=0),
              dict(command=subprocess.list2cmdline([str(s.PY),'-B','-X','utf8',str(D/'probe_cumulative_budget.py')]),exit_status=1)],
    validations=[dict(name='Original385 exact-ID cases pass with all observed resources closed',passed=True),
                 dict(name='Cumulative request evidence writes stay within8192 finite budget',passed=False),
                 dict(name='Exact uncertain retry is read-only and does not replay an effect',passed=True),
                 dict(name='Original Q316, execution replica316, Source290 and Python image retained',passed=True)],
    exit_status=1, decision='rejected')
kwargs=dict(run_id=RUN,node_id='review',executor_id=s.ACTOR,input_hash=claim['input_hash'],
            claimed_at=claim['claimed_at'],node=graph['nodes']['review'])
validate_receipt(receipt, **kwargs)
s.write_new(D / 'review.json', receipt)
validate_receipt(load_receipt(D / 'review.json'), **kwargs)
command=['powershell','-NoProfile','-File','T:/02-Config/agents/taar-orchestrate.ps1',
         'node','complete',RUN,'review',str(D/'review.json'),'--runtime-root',str(BASE)]
done=subprocess.run(command,cwd='T:/00-Active',capture_output=True,
                    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
with (D/'review-complete.stdout.txt').open('xb') as stream:stream.write(done.stdout)
with (D/'review-complete.stderr.txt').open('xb') as stream:stream.write(done.stderr)
response=json.loads(done.stdout.decode('utf-8-sig'))
s.write_new(D/'review-complete.json',dict(command_argv=command,exit_status=done.returncode,response=response))
state=json.loads((BASE/RUN/'state.json').read_text())
claims=json.loads((BASE/RUN/'claims.json').read_text())
persisted=json.loads((BASE/RUN/'receipts/review.json').read_text())
assert state['nodes']['review']['state']=='FAILED' and state['sequence']==9 and claims=={}
assert len(receipt)==13 and len(persisted)==16
assert all(persisted[key]==value for key,value in receipt.items())
assert persisted['decision']=='rejected' and done.returncode==1
s.write_new(D/'ACTUAL-READBACK.json',dict(recorded_at=s.utc(),state=state,claims=claims,
    authored_fields=13,persisted_fields=16,authored_fields_exact=True,engine_response=response,
    actual_complete_command_exit_status=done.returncode,submitted_decision='rejected',
    persisted_decision=persisted['decision'],failed_node_decision_preserved=state['nodes']['review'].get('decision'),
    review_sha256=s.sha(D/'review.json')))
files={path.relative_to(D).as_posix():s.ordinary(path) for path in D.rglob('*') if path.is_file()}
s.write_new(D/'REVIEW-SEAL.json',dict(recorded_at=s.utc(),files=files,review_sha256=s.sha(D/'review.json'),
    manifest_sha256=s.sha(Q/'TRANSFER-MANIFEST.json'),scope_released=True,Source_publication=False,decision='rejected'))
print(json.dumps(dict(review_sha256=s.sha(D/'review.json'),report_sha256=s.sha(D/'REPORT.json'),
    probe_sha256=s.sha(D/'CUMULATIVE-BUDGET-PROBE.json'),readback_sha256=s.sha(D/'ACTUAL-READBACK.json'),
    seal_sha256=s.sha(D/'REVIEW-SEAL.json'),state=state['nodes']['review']['state'],sequence=state['sequence'],
    claims=claims,complete_command_exit_status=done.returncode,engine_response=response)),flush=True)
