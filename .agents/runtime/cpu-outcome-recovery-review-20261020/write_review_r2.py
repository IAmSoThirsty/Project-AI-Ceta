"""Final distinct r4 component review, joined to terminal201 evidence and actual TAAR state."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import hashlib
import json

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
V = F/'.agents/runtime/cpu-outcome-recovery-r4-regression-20261020'
A = F/'.agents/runtime/cpu-outcome-recovery-repair-20261020'
Q = F/'.agents/cpu-outcome-recovery-r4-20261020'
P = A/'cpu-outcome-recovery-r4-20261020'
B = F/'.agents/runtime/js8-20261015/amendment-report1/ACCEPTED-SOURCE-BASELINE.json'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
read = lambda path: json.loads(path.read_bytes())
def ref(path): return dict(path=str(path), sha256=sha(path))
assert sha(A/'MANIFEST.json') == 'aa1ee89d9d0d63051b090590fea1d4391f9a4aad77ff8d8e92c6bfd04abe270e'
assert sha(V/'HANDOFF.json') == 'b13b464140353ad943c5d1aacbbe1e71914ddcdb3bb10205f23df18c5ea74712'
assert sha(B) == '5d001e3144805864048edf165e7124fdba21f8d99fc01b36e1f7463877b68bb0'
manifest, baseline, handoff = read(A/'MANIFEST.json'), read(B), read(V/'HANDOFF.json')
assert len(manifest['payload_hashes']) == 375
assert all(sha(Q/name) == pin for name,pin in manifest['payload_hashes'].items())
assert len(baseline['effective_payload_hashes']) == 352
assert all(sha(F/name) == pin for name,pin in baseline['effective_payload_hashes'].items())

records, all_ids = [], []
for cohort in handoff['cohorts']:
    for key in ('terminal', 'result', 'raw', 'outer_result', 'before', 'events', 'cases'):
        item = cohort[key]; assert sha(Path(item['path'])) == item['sha256']
    data, outer, before, cases = (read(Path(cohort[key]['path'])) for key in ('result', 'outer_result', 'before', 'cases'))
    ids = data['expected_ids']
    assert len(ids) == cohort['tests'] and ids == data['executed_ids'] == data['stopped_ids'] == cases['expected_ids']
    assert data['tests_run'] == cohort['tests'] and len(set(ids)) == len(ids)
    assert data['exit_status'] == outer['exit_status'] == outer['runner_exit_status'] == 0
    assert not data['failures'] and not data['errors'] and data['skips'] == 0
    assert not data['prohibited_operations'] and not outer['primary_exception']
    assert not any(outer[key] for key in ('diagnostics', 'residual_threads', 'scope_violations'))
    assert outer['candidate_unchanged'] and outer['Source_unchanged']
    assert before['candidate'] == outer['after_candidate'] == manifest['payload_hashes']
    assert before['Source'] == outer['after_Source'] == baseline['effective_payload_hashes']
    assert data['frozen_manifest_sha256'] == sha(A/'MANIFEST.json')
    assert len(data['sqlite_lifetimes']) == cohort['sqlite_lifetimes']
    assert all(row['closed'] and not row['retained_capacity'] and row['refusal'] == 'closed connection refusal'
        for row in data['sqlite_lifetimes'])
    events = [json.loads(line) for line in Path(cohort['events']['path']).read_text(encoding='utf8').splitlines()]
    assert [(row['event'], row['id']) for row in events] == [pair for identifier in ids for pair in (('START', identifier), ('STOP', identifier))]
    terminal = read(Path(cohort['terminal']['path']))
    assert terminal['exit_code'] == 0
    assert data['raw_sha256'] == cohort['raw']['sha256']
    command_path = Path(cohort['outer_result']['path']).parent/'COMMAND.json'
    command = read(command_path)
    assert command['command'] == cohort['command'] == outer['command']
    assert command['cwd'] == str(F)
    records.append(dict(name=cohort['name'], tests=len(ids), failures=0, errors=0, skips=0,
        sqlite_connections_observed_closed=len(data['sqlite_lifetimes']), ordered_start_stop_events=len(events),
        command=command['command'], command_record=ref(command_path), pid=command['pid'],
        started_at=outer['started_at'], finished_at=outer['finished_at'],
        terminal=cohort['terminal'], result=cohort['result'], raw=cohort['raw'],
        outer=cohort['outer_result'], before=cohort['before'], events=cohort['events'], cases=cohort['cases']))
    all_ids.extend(ids)
assert len(all_ids) == len(set(all_ids)) == 201
assert [row['id'] for row in handoff['coverage']] == all_ids
for row in handoff['coverage']:
    path = Path(row['source']['path'])
    assert sha(path) == row['source']['sha256'] and row['state'] == 'PASS'
    method = row['id'].rsplit('.',1)[-1]
    assert any(isinstance(node, ast.FunctionDef) and node.name == method and node.lineno == row['line']
        for node in ast.walk(ast.parse(path.read_bytes())))

receipt_path = P/'receipts/implement.json'
receipt, state = read(receipt_path), read(P/'state.json')
embedded = receipt.pop('receipt_hash')
canonical = hashlib.sha256(json.dumps(receipt, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf8')).hexdigest()
assert canonical == embedded == state['nodes']['implement']['receipt_hash']
assert state['nodes']['implement']['state'] == 'SUCCEEDED' and state['nodes']['implement']['validation_passed']
assert receipt['input_hash'] == '7f5f156bd823bc0ae9304c04781d9f7aff4fa63044b284680b28735fa56288ce'
assert receipt['result']['manifest_sha256'] == sha(A/'MANIFEST.json')
assert read(A/'implement-complete-r2.json')['exit_status'] == 0
assert read(A/'implement-complete-r2.json')['response']['allowed'] is True
assert read(A/'implement-complete.json')['response']['code'] == 'MALFORMED_RECEIPT'
proofs = read(R/'REGISTRATION-REPAIR-PROOFS-R2.json')
assert proofs['passed_repair_cases'] == 16 and proofs['failed_repair_cases'] == 0
assert proofs['additional_edge']['actual_public_repeat_guard_preserves_rows']

result = dict(at=datetime.now(timezone.utc).isoformat(), actor='/root/recovery_join_review20',
    role='Distinct internal Collaborative Reviewer, ROLE-04 Critic', coordinator='/root', project=str(F),
    decision='approved',
    approval_scope='The frozen r4 recovery component is eligible for joined integration validation. Source publication still requires Root native/full/destination qualification and required dependencies.',
    candidate=ref(A/'MANIFEST.json'), candidate_root=str(Q),
    production_method_sha256=manifest['payload_hashes']['src/ceta/kernel/cpu_execution.py'],
    production_change='Only claim_recovery_liveness AST changed relative to cut-r3; one registration test module added.',
    authored_changes=manifest['authored_changes'],
    accepted_Source_baseline=ref(B), candidate_payloads_verified=375, accepted_Source_payloads_verified=352,
    all_candidate_and_accepted_Source_hashes_match=True,
    Source_hash_scope='Exact accepted352 set; separately assigned reasoning changes are excluded from this review.',
    preceding_rejection=ref(R/'REVIEW-R1.json'), old169_result_supplement=ref(R/'REVIEW-R1-REGRESSION-SUPPLEMENT.json'),
    original_defect_reproduction=ref(R/'REGISTRATION-FAILURE-REPRODUCTION.json'),
    repair_proofs=ref(R/'REGISTRATION-REPAIR-PROOFS-R2.json'),
    independent_runner_reviews=[ref(R/name) for name in ('RUNNER-REVIEW-R2.json', 'CALLER24-RUNNER-REVIEW-R2.json', 'CALLER24-METADATA-SUPPLEMENT-R2.json')],
    actual_TAAR_implementation=dict(state='SUCCEEDED', canonical_receipt_hash=canonical,
        stored_receipt=ref(receipt_path), external_receipt=ref(A/'implement-receipt-r2.json'),
        complete_result=ref(A/'implement-complete-r2.json'),
        original_failed_complete=ref(A/'implement-complete.json'),
        ledger=ref(P/'state.json'), sequence=state['sequence'], ledger_head=state['ledger_head'], claims=read(P/'claims.json'),
        canonical_hash_method='SHA256 sorted compact UTF8 JSON with receipt_hash omitted; matches embedded and actual ledger hash.'),
    combined_verifier_handoff=ref(V/'HANDOFF.json'), cohorts=records,
    exact_disjoint_test_ids=201, SQLite_connections_observed_closed=291, ordered_start_stop_events=402,
    finding_disposition=[dict(id='RJR20-01', state='CLOSED_ON_R4_WITHIN_COMPONENT_REVIEW',
        basis='Original fault retires exact partial rows; uncertain cleanup retains exact lease and primary. Sixteen distinct pure probes,177 affected regression and24 original caller cases pass at exact r4 pins.',
        old_cut='cut-r3 remains rejected; no pass transfer.'),
        dict(id='exact-same-private-repeat', category='internal defensive gap', classification='requires separate follow-up work',
            state='OPEN_INTERNAL_HELPER_EDGE_NO_PUBLIC_FAILURE_PATH_ESTABLISHED',
            source='src/ceta/kernel/cpu_execution.py:372-394',
            observed='A direct second private claim of its exact already-active lease reaches denial cleanup and retires that registration. Actual public recovery entry rejects earlier and preserves both rows/current lease.',
            evidence=ref(R/'REGISTRATION-REPAIR-PROOFS-R2.json'),
            owner='/root integration coordinator',
            next_action='Distinguish new publication from pre-existing exact-lease liveness before cleanup; preserve the public repeat guard and add a direct-denial regression in a separate bounded repair.',
            current_review_effect='Does not invalidate the demonstrated RJR20-01 closure or current guarded public recovery entry; remains unfinished system work.')],
    supported_scope=['Original context/thread/consumed permit retained; no redispatch through recovery.',
        'Exact canonical transaction retry and same-store authenticated lost-COMMIT-notification readback.',
        'Fresh same-writer reconciliation capacity; exact durable retry allocates/writes nothing.',
        'Typed captured post-mark denial and proven empty unconfigured entry retirement.'],
    remaining=[dict(classification='requires separate follow-up work', issue='Join separately reviewed retainer/capacity/observer/provenance and this component; then execute required native/full/destination validation before Source publication.'),
        dict(classification='requires separate follow-up work', issue='Genuine owner approval, canonical public compiler/effect controls, positive native recovery and independent observation remain open.'),
        dict(classification='requires separate follow-up work', issue='RE-T25 surviving supervisor and RE-T26 cross-process startup recovery remain unqualified; RE-T28 restoration requires a distinct request/approval/permit.'),
        dict(classification='requires separate follow-up work', issue='Expired/changed pending proof, durable Stop/checkpoint changes, ambiguous native/lock/liveness release and fresh reservation failure recovery remain explicit open paths.'),
        dict(classification='not blocking current task', issue='The combined handoff has a null old169 supplement field; this final review binds the actual immutable supplement directly.')],
    exclusions=['No Source/candidate edits by reviewer.', 'No native/profile/network/CPU Set operation by reviewer.',
        'Controlled native identities/provenance/authority/VFS do not establish native product acceptance.',
        'Endpoint hashes do not establish uninterrupted custody.'],
    independence='Reviewer authored only review reports/probes; Root authored r4 repair; recovery_regression20 independently executed the frozen controlled cohorts. Shared host/tools/model family; internal review, not a separate administrative-domain or external audit.',
    source_publication_approved=False, runtime_acceptance=False, full_product_complete=False,
    next_action='Root may construct and qualify the joined successor under the existing architecture; carry the internal defensive gap and native/public/restart requirements into its remaining inventory.')
path = R/'REVIEW-R2.json'
with path.open('x', encoding='utf8') as stream:
    json.dump(result, stream, indent=2); stream.write('\n')
print(json.dumps(dict(path=str(path), sha256=sha(path), decision=result['decision'],
    tests=201, SQLite_closed=291, candidate=375, accepted_Source=352,
    Source_publication_approved=False)))
