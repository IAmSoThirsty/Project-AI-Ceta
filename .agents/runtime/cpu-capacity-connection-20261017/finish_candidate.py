"""Record the actual bounded result and release only this candidate's claim."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess

R = Path(__file__).resolve().parent
F = Path('T:/00-Active/Project-AI-CETA')
Q = F / '.agents/cpu-capacity-connection-20261017'
RUN = 'cpu-capacity-connection-20261017'
ACTOR = '/root/full_report_repair'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()
def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2); stream.write('\n')
def ref(path): return dict(path=str(path), sha256=sha(path))

manifest_path = R/'cut-r1/MANIFEST.json'
assert sha(manifest_path) == '12c6dd58311e85686f68cbb7bc18a8d631ec418428fe2ddad88f017d575f4ce1'
m = json.loads(manifest_path.read_bytes())
for name, pin in m['payload_hashes'].items(): assert sha(Q/name) == pin, name
for row in m['changed']:
    assert sha(Path(row['frozen_copy'])) == row['after_sha256'], row['path']
    if row['before'] is not None:
        assert sha(Path(row['before']['path'])) == row['before']['sha256'], row['path']
accepted = {}
for label, count in [('controlled-r5', 20), ('regression-r2', 149)]:
    path = R/label/'RESULT.json'
    value = json.loads(path.read_bytes())
    assert value['tests_run'] == count and value['exit_status'] == 0
    assert not value['failures'] and not value['errors'] and not value['skips']
    assert value['before'] == value['after']
    assert value['expected_ids'] == value['executed_ids'] == value['stopped_ids']
    assert not value['prohibited_operations'] and value['native_CPU_Set_operations'] == 0
    assert all(row['closed'] and row['refusal'] == 'closed connection refusal'
               and not row['retained_capacity'] for row in value['sqlite_lifetimes'])
    assert sha(R/label/'RAW.txt') == value['raw_sha256']
    for name, pin in value['after'].items(): assert m['payload_hashes'][name] == pin, name
    accepted[label] = dict(result=ref(path), raw=ref(R/label/'RAW.txt'),
        tests_run=count, command=value['command'], exit_status=0,
        scope='controlled canonical SQLite, no native capacity/effect/provenance acceptance')

issues = [
    dict(requirements=['RE-T25','RE-T27','RE-T28'], classification='OPEN_INTEGRATION',
         issue='Public recovery for post-mark Stop/timing denial or failed outcome commit',
         evidence='CapacityConnectionTests.test_stop_after_mark_precedes_dispatch_and_preserves_uncertainty and test_failed_commit_keeps_exact_primary_slot_and_journal_custody',
         exact_state='OutcomeCapacityLease PENDING/non-durable; adapter PENDING; _NativeCpuExecutionRetainer FAILED/pending; kernel execution retains liveness',
         blocker='finish_reconciliation requires a matching durable commit; approved owner retainer has no public re-entry/recovery port after failed retirement; raw journal writes are not authorized public recovery',
         next='Implement separately reviewed canonical recovery entry with original authority/current-context checks and exact pending-custody retirement'),
    dict(requirements=['RE-T27','RE-T28'], classification='OPEN_INTEGRATION',
         issue='Advancing UNCERTAIN/DISCREPANCY observation needs a fresh qualified reservation',
         evidence='CapacityConnectionTests.test_advancing_reconciliation_needs_a_new_qualified_reservation',
         blocker='CPU_CAPACITY_RECONCILIATION_RESERVATION_REQUIRED; durable one-shot slot is not reused',
         next='Compose a separately qualified reservation on the same canonical writer for recovery; preserve exact retry as no-write'),
    dict(requirements=['RE-T25','RE-T27'], classification='DEPENDENCY_PENDING',
         issue='Production producer and independent observer provenance composition',
         evidence='CapacityConnectionTests.test_missing_provenance_stays_denied_with_real_capacity_factory',
         blocker='Real NativeOwnerView has no composed require_owned_cpu_outcome_provenance; OWNER_EXECUTION_PROVENANCE_UNAVAILABLE',
         next='Integrate separately reviewed real-origin helper and then qualify the concrete owner'),
    dict(requirements=['RE-T27'], classification='QUALIFICATION_HELD',
         issue='Native VFS allocation and consequential CPU execution with this connection',
         blocker='Root held native/process/effect qualification during canonical destination full',
         next='Root release, exact pinned runtime on disposable Windows files, then native owner/effect acceptance with actual authorization and observation'),
]
failed = {}
for label in ('controlled-r4','regression-r1'):
    path = R/label/'RESULT.json'
    value = json.loads(path.read_bytes())
    assert value['exit_status'] == 1
    failed[label] = dict(result=ref(path), raw=ref(R/label/'RAW.txt'),
        status='FAILED_RETAINED', pins_match=value['before'] == value['after'])
self_review = dict(at=now(), actor=ACTOR, manifest=ref(manifest_path),
    class_qualification='AUTHOR_SELF_REVIEW_ONLY',
    findings_fixed=[
        'Included physical mark in measured dispatch interval before final pure decision',
        'Scoped exact capacity requirement to native owner/subclasses or selected physical reservation, preserving generic owner port',
        'Kept exact first-outcome retry no-write; explicit denial for unqualified advancing reservation reuse',
        'Corrected new retry assertion to compare actual OwnedCpuOutcome data fields',
    ],
    preserved_failure='regression-r1 also failed its source pin stability check because the repair was edited during that already imported run; no acceptance uses it',
    changed_dependencies=False, open_issues=issues)
save(R/'SELF-REVIEW.json', self_review)
handoff = dict(at=now(), actor=ACTOR, status='SCOPED_IMPLEMENTATION_READY_FOR_DISTINCT_REVIEW',
    candidate=str(Q), manifest=ref(manifest_path), delta=ref(R/'cut-r1/DELTA.diff'),
    changed=m['changed'], physical_line_counts=m['physical_line_counts'], copied_dependency_LOC_credit=0,
    requirement_completion='RE-T27 partial connection implemented; full recovery/native acceptance remains open',
    evidence=accepted, failed_evidence=failed, self_review=ref(R/'SELF-REVIEW.json'),
    original_claim=ref(R/'implement-claim.json'), open_issues=issues,
    source_publication=False, independent_review=False, native_capacity_acceptance=False,
    governed_effect_acceptance=False,
    exact_next_commands='Root release required before CETA_CPU_CAPACITY_NATIVE=1 native class; run controlled tests with the recorded runner commands for independent verification')
save(R/'HANDOFF.json', handoff)
inputs = json.loads((R/'INPUTS.json').read_bytes())
claim = inputs['claim']
receipt = dict(schema_version=1, run_id=RUN, node_id='implement', executor_id=ACTOR,
    started_at=claim['claimed_at'], finished_at=now(), input_hash=claim['input_hash'],
    changed_files=[(Q/name).relative_to(Path('T:/')).as_posix() for name in m['payload_hashes']],
    result=dict(kind='ISOLATED_CANDIDATE_IMPLEMENTATION', handoff=ref(R/'HANDOFF.json'),
        source_publication=False, final_acceptance='PENDING', open_issues=issues),
    commands=[], validations=[dict(name='exact_changed_python_syntax', passed=True),
        dict(name='20_new_controlled_connection_tests', passed=True),
        dict(name='149_unchanged_controlled_regression_tests', passed=True),
        dict(name='stable_candidate_pins_and_fixture_SQLite_retirement', passed=True)], exit_status=0)
save(R/'implement-receipt.json', receipt)
command = ['powershell', '-NoProfile', '-File', 'T:/02-Config/agents/taar-orchestrate.ps1',
    'node', 'complete', RUN, 'implement', str(R/'implement-receipt.json'), '--runtime-root', str(R)]
out = subprocess.run(command, cwd=F, capture_output=True)
for suffix, raw in [('stdout',out.stdout), ('stderr',out.stderr)]:
    with (R/('implement-complete.'+suffix)).open('xb') as stream: stream.write(raw)
response = json.loads(out.stdout.decode('utf-8-sig'))
save(R/'implement-complete.json', dict(command=command, exit_status=out.returncode, response=response))
assert out.returncode == 0 and response['allowed'] is True, response
print(json.dumps(dict(handoff=ref(R/'HANDOFF.json'), implement_complete=ref(R/'implement-complete.json'))))
