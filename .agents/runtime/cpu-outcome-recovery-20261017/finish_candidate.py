"""Seal exact frozen recovery work and its actual developer implementation receipt."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess

F = Path('T:/00-Active/Project-AI-CETA')
Q = F/'.agents/cpu-outcome-recovery-20261017'
R = Path(__file__).resolve().parent
RUN, ACTOR = 'cpu-outcome-recovery-20261017', '/root/full_report_repair'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
ref = lambda p: dict(path=str(p), sha256=sha(p))
now = lambda: datetime.now(timezone.utc).isoformat()
def save(p, value):
    with p.open('x', encoding='utf8') as stream: json.dump(value, stream, indent=2); stream.write('\n')
manifest = R/'cut-r3/MANIFEST.json'
assert sha(manifest) == '463d703e0b92580d45574d2b89276af645e55d6bfb5431e3ddc71d8c9d18ca87'
m = json.loads(manifest.read_bytes())
inputs = json.loads((R/'INPUTS.json').read_bytes())
for name, pin in m['payload_hashes'].items(): assert sha(Q/name) == pin, name
for name, pin in inputs['payload_hashes'].items(): assert sha(Path(inputs['source_root'])/name) == pin, name
results = []
for name, count, cut in [('controlled-r2', 24, 'cut-r2'), ('timing-r1', 8, 'cut-r3')]:
    path = R/name/'RESULT.json'
    value = json.loads(path.read_bytes())
    assert value['exit_status'] == 0 and value['tests_run'] == count
    assert value['before'] == value['after'] and value['frozen_manifest_sha256'] == sha(R/cut/'MANIFEST.json')
    assert not value['failures'] and not value['errors'] and value['skips'] == 0
    assert value['expected_ids'] == value['executed_ids'] == value['stopped_ids']
    assert not value['prohibited_operations']
    assert all(row['closed'] and row['refusal'] == 'closed connection refusal'
        and not row['retained_capacity'] for row in value['sqlite_lifetimes'])
    results.append(dict(result=ref(path), command=value['command'], tests=count,
        raw=ref(R/name/'RAW.txt'), sqlite_lifetimes=len(value['sqlite_lifetimes'])))
failed = json.loads((R/'regression-r1/RESULT.json').read_bytes())
assert failed['exit_status'] == 1 and failed['tests_run'] == 169 and len(failed['errors']) == 1
assert not failed['failures'] and failed['skips'] == 0 and failed['before'] == failed['after']
assert all(row['closed'] and not row['retained_capacity'] for row in failed['sqlite_lifetimes'])
fixture = json.loads((R/'FIXTURE-DELTA.json').read_bytes())
assert fixture['other_method_ASTs_identical'] and fixture['product_source_unchanged']
old_manifest = json.loads((R/'cut-r2/MANIFEST.json').read_bytes())
assert [name for name in m['payload_hashes'] if m['payload_hashes'][name] != old_manifest['payload_hashes'][name]] == [fixture['path']]
counts = dict(source_added=0, source_removed=0, test_added=0, test_removed=0,
    document_added=0, document_removed=0)
for name, change in m['changes'].items():
    kind = 'source' if name.startswith('src/') else 'test' if name.startswith('tests/') else 'document'
    counts[kind+'_added'] += change['added']; counts[kind+'_removed'] += change['removed']
issues = [
    dict(classification='blocking integration', issue='The 169-case joined regression ended with one timing-fixture error and remains FAILED. The authorized deterministic one-method fixture correction and eight related timing cases passed separately. A fresh full joined regression remains mandatory before integration; no corrected 169-case PASS is claimed.'),
    dict(classification='requires separate follow-up work', issue='Independent review and Root integration with the separately frozen producer/observer/view composition remain required; no Source publication in this job.'),
    dict(classification='environment/dependency issue', issue='Real VFS/native owner/CPU-effect recovery qualification remains held for Root release; fixture identities, approval, provenance and VFS observations are CONTROLLED.'),
    dict(classification='requires separate follow-up work', issue='RE-T25 surviving supervisor/crash custody and RE-T26 restart recovery require separately qualified original native custody; this implementation preserves only in-process original context/thread/owner capability.'),
    dict(classification='requires separate follow-up work', issue='Pending writes whose observation/provenance no longer passes current canonical guard stay pending. No rewrite of retained verdict or revival of authority is provided.'),
    dict(classification='requires separate follow-up work', issue='The controlled Stop recovery test uses the original execution cancellation flag. Durable Stop/checkpoint changes and restart are not qualified by that case and may leave the original pending transaction denied.'),
    dict(classification='requires separate follow-up work', issue='Ambiguous native release, journal cleanup, lock retirement or liveness retirement stays explicit pending custody. Fresh reconciliation allocation failure has no separately qualified cleanup retry in this cut.'),
    dict(classification='not blocking current task', issue='Unconfigured physical VFS entry can now retire proven-empty custody and preserve PREPARED permit; actual execution remains denied until real capacity is configured.'),
    dict(classification='requires separate follow-up work', issue='RE-T28 restoration remains a separate request/approval/permit. UI/service recovery wiring and full-product acceptance remain outside this isolated cut.')]
handoff = dict(at=now(), actor=ACTOR, status='FROZEN_IMPLEMENTATION_READY_FOR_DISTINCT_REVIEW',
    candidate=str(Q), manifest=ref(manifest), diff=ref(R/'cut-r3/CHANGES.diff'),
    changed=m['changes'], physical_line_counts=counts, copied_dependency_LOC_credit=0,
    author_commands_and_results=results, preceding_successful_cut=ref(R/'controlled-r1/RESULT.json'),
    failed_joined_regression=ref(R/'regression-r1/RESULT.json'),
    unchanged_diagnostic_case=ref(R/'diagnostic-r1/RESULT.json'),
    fixture_only_correction=ref(R/'FIXTURE-DELTA.json'), full_joined_regression='REQUIRED BEFORE INTEGRATION',
    claim=ref(R/'implement-claim.json'), preserved_base_manifest=inputs['manifest'],
    verified_behaviors=['exact final canonical transaction retry after failed COMMIT',
        'authenticated exact journal/store readback after lost COMMIT notification, without another write',
        'bookkeeping recovery after original execution cancellation flag while redispatch stays denied',
        'immutable original denial origin and NOT_STARTED/UNCERTAIN canonical outcome',
        'fresh same-journal reservation for advancing reconciliation; exact retry allocates/writes nothing',
        'proven-empty unconfigured capacity entry retirement with PREPARED permit preserved',
        'original context/thread/provenance and single-writer custody enforced'],
    remaining=issues, source_publication=False, independent_review='PENDING',
    native_qualification='NOT_RUN', full_product_acceptance='PENDING')
save(R/'HANDOFF.json', handoff)
claim = inputs['claim']
save(R/'implement-receipt.json', dict(schema_version=1, run_id=RUN, node_id='implement', executor_id=ACTOR,
    started_at=claim['claimed_at'], finished_at=now(), input_hash=claim['input_hash'],
    changed_files=[(Q/name).relative_to(Path('T:/')).as_posix() for name in m['payload_hashes']],
    result=dict(kind='ISOLATED_CANDIDATE_IMPLEMENTATION', handoff=ref(R/'HANDOFF.json'),
        source_publication=False, final_acceptance='PENDING', remaining=issues),
    commands=[], validations=[dict(name='24_frozen_recovery_tests', passed=True),
        dict(name='8_timing_tests_after_authorized_fixture_only_correction', passed=True),
        dict(name='stable_candidate_and_base_pins_and_all_fixture_SQLite_closed', passed=True)], exit_status=0))
command = ['powershell','-NoProfile','-File','T:/02-Config/agents/taar-orchestrate.ps1',
    'node','complete',RUN,'implement',str(R/'implement-receipt.json'),'--runtime-root',str(R)]
out = subprocess.run(command, cwd=F, capture_output=True)
for suffix, raw in [('stdout', out.stdout), ('stderr', out.stderr)]:
    with (R/('implement-complete.'+suffix)).open('xb') as stream: stream.write(raw)
response = json.loads(out.stdout.decode('utf-8-sig'))
save(R/'implement-complete.json', dict(command=command, exit_status=out.returncode, response=response))
assert out.returncode == 0 and response['allowed'] is True, response
print(json.dumps(dict(handoff=ref(R/'HANDOFF.json'), implement_complete=ref(R/'implement-complete.json'), counts=counts)))
