from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
P = F / '.agents/runtime/cpu-outcome-provenance-20261017'
C = F / '.agents/runtime/cpu-capacity-connection-20261017'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
ref = lambda p: dict(path=str(p), sha256=sha(p))
assert sha(P / 'HANDOFF.json') == '82d45d3998da9fea9f5e0c7e30aab1593d305d6414112b4ea1cbd5907b0b378d'
assert sha(R / 'controlled-r2/RESULT.json') == 'c3be572fbce4b8c2dbd8a0f8a909d72e0dd1625e3c999150e8823ce3338ad3e3'
result = json.loads((R / 'controlled-r2/RESULT.json').read_bytes())
assert result['tests_run'] == 37 and result['exit_status'] == 0
assert result['failures'] == result['errors'] == result['prohibited_calls'] == result['remaining_threads'] == []
assert result['skips'] == 0 and result['expected_ids'] == result['executed_ids'] == result['stopped_ids']
assert result['before'] == result['after'] and all(row['closed_connection_refusal'] and not row['retained_capacity'] for row in result['sqlite'])
source = F / '.agents/runtime/js8-20261015/amendment-report1/active-application/APPLIED.json'
application = json.loads(source.read_bytes())
assert all(sha(F / name) == row['sha256'] for name, row in application['source352'].items())
inputs = json.loads((R / 'JOIN-INPUTS.json').read_bytes())
assert all(sha(row['path']) == row['sha256'] for row in inputs['selected'].values())
report = dict(at=datetime.now(timezone.utc).isoformat(), reviewer='/root', author='/root/publication_recovery_review',
    decision='APPROVED_CONTROLLED_COMPONENT_AND_CANONICAL_SQL_JOIN_NATIVE_PENDING',
    requirement_ids=['RE-T23', 'RE-T24'], handoff=ref(P / 'HANDOFF.json'),
    manifest=ref(P / 'cut-r1/MANIFEST.json'), capacity_manifest=ref(C / 'cut-r1/MANIFEST.json'),
    proposal=ref(P / 'VIEW-PROPOSAL.json'), proposal_diff=ref(P / 'NativeOwnerView.PROPOSED.diff'),
    joined_inputs=ref(R / 'JOIN-INPUTS.json'), checks=ref(R / 'controlled-r2/RESULT.json'),
    raw=ref(R / 'controlled-r2/RAW.txt'), runner=ref(R / 'run_join_checks.py'),
    rejected_reviewer_run=ref(R / 'controlled-r1/RESULT.json'),
    original_reviewer_runner=ref(R / 'controlled-r1/runner.py'),
    corrected_reviewer_error='The kernel decodes its own request. The original observer assertion incorrectly required the external fixture DTO identity. The correction requires identity with the active kernel lease request and byte equality with the submitted fixture request.',
    tests_run=37, failures=0, errors=0, skips=0, original_author_cases=33, new_join_cases=4,
    SQL_connections_physically_closed=len(result['sqlite']), joined_payloads=len(result['after']),
    source_publication_receipt=ref(source), canonical_payload_contents_unchanged=352,
    personally_inspected=['Both new source modules in full', 'All 33 author test methods',
        'Exact proposed NativeOwnerView forwarding delta', 'Capacity staging and canonical transaction call sites',
        'Native retainer outcome currentness and primary-error custody', '37-case terminal result and closed-connection refusals'],
    verified=['Original kernel request/permit/attempt/retainer/context/thread binding accepts independently decoded canonical data only with retained local proof.',
        'The existing observer origin predicate checks the original retained observation while decoded bytes match it.',
        'The actual canonical writer committed the receipt, observation and settlement with the exact staged capacity payloads.',
        'An observer exception was preserved after an actual UNCERTAIN commit.',
        'Post-dispatch Stop did not prevent canonical outcome bookkeeping or allow another dispatch.',
        'A canonical commit failure retained the exact primary, observation capture and pending capacity.'],
    limitations=['Native effects, native observation, VFS allocation and owner authentication in the join were controlled.',
        'Public application composition and genuine authorization-to-effect demonstration remain pending.',
        'The repaired observer still needs its released native qualification.',
        'Retainer-exit recovery, failed capacity entry and fresh advancing reconciliation reservation remain separate open integration requirements.',
        'The proposed view seam is applied only in the disposable review join. Original author candidates and canonical source are unchanged.'],
    Source_publication=False, Source_accepted=False, full_product_complete=False, copied_source_LOC_credit=0)
with (R / 'REVIEW.json').open('x', encoding='utf-8') as stream:
    json.dump(report, stream, indent=2, allow_nan=False)
with (R / 'REVIEW.md').open('x', encoding='utf-8') as stream:
    stream.write('The frozen producer/observer component and proposed view seam pass independent controlled review and a real canonical SQLite join. Root personally inspected the complete source, tests, seam and relevant writer/retainer call sites.\n\n')
    stream.write('All 33 author cases and four additional join cases passed. The join used the actual kernel outcome writer, capacity adapter and SQLite commit. Native observation, CPU effects, physical capacity and authentication were controlled. It therefore qualifies the connection and failure handling, while public native operation acceptance remains pending.\n\n')
    stream.write('The original reviewer run failed four join assertions because the fixture incorrectly expected identity with the submitted DTO. The kernel correctly decodes its own request. That run and runner remain preserved. The corrected assertion requires the actual active kernel lease request identity plus submitted canonical-byte equality. Product code was unchanged.\n\n')
    stream.write('The checks verified observed settlement, uncertainty committed before rethrowing the observer primary, bookkeeping after Stop, and pending capacity/capture retention after canonical commit failure. All captured SQL connections refused SELECT after close. No worker or CPU Set ran.\n\n')
    stream.write('Remaining work: native observer qualification, pending-owner recovery, fresh reconciliation reservation, public service composition, genuine owner approval, native effect/observation and installed acceptance. REVIEW.json provides exact receipts, code pins and limits.\n')
with (R / 'SEAL.json').open('x', encoding='utf-8') as stream:
    json.dump(dict(reviewer='/root', artifacts=[ref(R / name) for name in (
        'REVIEW.json', 'REVIEW.md', 'JOIN-INPUTS.json', 'controlled-r1/RESULT.json',
        'controlled-r1/runner.py', 'controlled-r2/RESULT.json', 'controlled-r2/RAW.txt', 'run_join_checks.py')]), stream, indent=2)
print(json.dumps(dict(review=ref(R / 'REVIEW.json'), seal=ref(R / 'SEAL.json'),
    closed_SQL_connections=len(result['sqlite']), production_acceptance=False)))
