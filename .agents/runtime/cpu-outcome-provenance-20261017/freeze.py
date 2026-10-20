"""Freeze only the new producer/adapter files and complete their real writer claim."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess
import sys

F = Path('T:/00-Active/Project-AI-CETA')
Q = F / '.agents/cpu-outcome-provenance-20261017'
R = Path(__file__).resolve().parent
RUN, ACTOR = 'cpu-outcome-provenance-20261017', '/root/publication_recovery_review'
NEW = ('src/ceta/identity/native_cpu_outcome.py', 'src/ceta/composition/native_cpu_outcome.py',
       'tests/contract/test_native_cpu_outcome_provenance.py', 'contracts/NATIVE_CPU_OUTCOME_PROVENANCE_V1.md')
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def utc(): return datetime.now(timezone.utc).isoformat()
def ref(path): return dict(path=str(path), sha256=sha(path))
def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')
inputs = read(R / 'INPUTS.json')
payloads = inputs['payloads']
assert len(payloads) == 369
assert {p.relative_to(Q).as_posix() for p in Q.rglob('*') if p.is_file()} == set(payloads) | set(NEW)
for name, row in payloads.items():
    assert sha(row['path']) == row['sha256'] and sha(Q / name) == row['sha256'], name
test = read(R / 'controlled_r2.json')
assert test['passed'] is True and test['tests_run'] == 33
assert not test['failures'] and not test['errors'] and not test['skips']
assert not test['forbidden_events'] and not test['new_threads_remaining']
assert test['expected_ids'] == test['executed_ids'] == test['completed_ids']
assert test['before'] == test['after'] == {name: sha(Q / name) for name in NEW[:3]}
assert all(value <= 50_000_000 for value in test['callback_elapsed_ns'])
assert sha(R / 'run_controlled.py') == test['runner_sha256']
proposal = read(R / 'VIEW-PROPOSAL.json')
assert len(proposal['controlled_checks']) == 4 and not proposal['forbidden_events']
assert all(sha(proposal[key]['path']) == proposal[key]['sha256'] for key in ('base', 'proposed', 'delta'))
cut = R / 'cut-r1'; cut.mkdir(exist_ok=False)
rows = []
for name in NEW:
    data = (Q / name).read_bytes(); target = cut / 'payloads' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream: assert stream.write(data) == len(data)
    lines = data.decode('utf8').splitlines()
    rows.append(dict(path=name, sha256=sha(target), kind='source' if name.startswith('src/') else
        'test' if name.startswith('tests/') else 'contract', added_physical_lines=len(lines),
        added_nonblank_lines=sum(bool(line.strip()) for line in lines), removed_lines=0, frozen_copy=str(target)))
claim = read(R / RUN / 'claims.json')['implement']
assert claim['executor_id'] == ACTOR and Path(claim['workspace']) == Q
save(cut / 'MANIFEST.json', dict(at=utc(), author=ACTOR, candidate=str(Q), inputs=ref(R / 'INPUTS.json'),
    new_paths=rows, unchanged_dependencies={name: row['sha256'] for name, row in payloads.items()},
    claim_input_hash=claim['input_hash'], status='CONTROLLED_COMPONENT_READY_FOR_INDEPENDENT_REVIEW',
    Source_publication=False, Source_accepted=False, copied_source_LOC_credit=0))
handoff = dict(at=utc(), author=ACTOR, requirements=['RE-T23', 'RE-T24'],
    status='CONTROLLED_COMPONENT_READY_FOR_INDEPENDENT_REVIEW', candidate=str(Q),
    manifest=ref(cut / 'MANIFEST.json'), inputs=ref(R / 'INPUTS.json'), changed=rows,
    tests=ref(R / 'controlled_r2.json'), raw=ref(R / 'controlled_r2.txt'),
    proposal=ref(R / 'VIEW-PROPOSAL.json'), proposal_delta=ref(R / 'NativeOwnerView.PROPOSED.diff'),
    checks=dict(controlled_cases=33, proposed_view_pure_checks=4, failures=0, errors=0, skips=0,
        callback_elapsed_ns=test['callback_elapsed_ns'], native_cases_executed=0, SQL_connections_opened=0),
    LOC={kind: dict(added_physical_lines=sum(row['added_physical_lines'] for row in rows if row['kind'] == kind),
                   added_nonblank_lines=sum(row['added_nonblank_lines'] for row in rows if row['kind'] == kind),
                   removed_lines=0) for kind in ('source', 'test', 'contract')},
    copied_source_LOC_credit=0, proposed_unapplied_LOC_credit=0,
    self_review=[
        'Original active admitted lease, consumed permit, attempt, peer/context/thread and same kernel/journal required.',
        'Original producer objects and immutable bytes reject substitution, mutation, DTO proof and observation replay.',
        'Decoded observations are compared to original retained bytes; actual origin predicate receives original observation and target.',
        'First receipt remains MAY_HAVE_EXECUTED for all native statuses and immutable over advancing observations and Stop.',
        'Actual captured native observation runs outside the pure callback; existing canonical kernel performs persistence and classification.',
        'Observer, dispatch, writer and state-recheck errors preserve exact primary and expose secondary/custody facts.',
        'Closed owner, failed/pending retainer and before-admission denial remain closed.',
        'View proposal preserves default None denial and exact view-bound callback, with exact helper type required.',
        'All 369 supplied dependency files unchanged; no Source, A2/Q2 or another candidate edited.'],
    preserved_pre_self_review=dict(source_before_images=str(R / 'self-review-r1'), controlled_run=ref(R / 'controlled_r1.json')),
    limitations=[
        'Controlled leases, native observation, dispatch and canonical write; no native or SQL integration claim.',
        'NativeOwnerView composition delta is proposed only; existing dependency file remains unchanged.',
        'Public application wiring, native qualification and canonical publication remain pending.',
        'After-exit FAILED/PENDING recovery and negative pre-dispatch producer belong to the separate recovery successor.',
        'Physical capacity and fresh advancing-reconciliation reservation belong to the capacity/recovery owner.',
        'Observer-origin successor is an explicitly pinned candidate dependency; this handoff makes no independent acceptance claim.'],
    Source_publication=False, Source_accepted=False,
    required_next=['Independent review of exact new files and proposed view delta',
                   'Coordinator-owned composition and integration', 'Coordinator-released native qualification'])
save(R / 'HANDOFF.json', handoff)
sys.path.insert(0, 'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_runtime import _snapshot_workspace, _changed_files
from taar.orchestration_receipts import validate_receipt
changes = _changed_files(claim['baseline_snapshot'], _snapshot_workspace(Q, Path('T:/')))
assert len(changes) == len(payloads) + len(NEW)
receipt = dict(schema_version=1, run_id=RUN, node_id='implement', executor_id=ACTOR,
    started_at=claim['claimed_at'], finished_at=utc(), input_hash=claim['input_hash'], changed_files=changes,
    result=dict(status=handoff['status'], handoff=ref(R / 'HANDOFF.json'), Source_publication=False,
                native_cases_executed=0, copied_source_LOC_credit=0),
    commands=[dict(command=' '.join(test['command']), exit_status=0),
              dict(command=' '.join(proposal['command']), exit_status=0)],
    validations=[dict(name='controlled33_origin_error_stop_replay_cases', passed=True),
                 dict(name='proposed_unapplied_view_seam_four_pure_checks', passed=True),
                 dict(name='369_authenticated_dependency_files_unchanged_four_new_paths_only', passed=True)], exit_status=0)
validate_receipt(receipt, run_id=RUN, node_id='implement', executor_id=ACTOR, input_hash=claim['input_hash'],
                 claimed_at=claim['claimed_at'], node=read(R / RUN / 'graph.json')['graph']['nodes']['implement'])
save(R / 'implement.json', receipt)
argv = ['powershell', '-NoProfile', '-File', 'T:/02-Config/agents/taar-orchestrate.ps1',
        'node', 'complete', RUN, 'implement', str(R / 'implement.json'), '--runtime-root', str(R)]
done = subprocess.run(argv, cwd=F, capture_output=True, timeout=120)
for suffix, raw in (('stdout', done.stdout), ('stderr', done.stderr)):
    with (R / ('implement-complete.' + suffix)).open('xb') as stream: stream.write(raw)
response = json.loads(done.stdout.decode('utf-8-sig'))
save(R / 'implement-complete.json', dict(argv=argv, exit_status=done.returncode, response=response))
assert done.returncode == 0 and response['allowed'] is True, response
assert all(sha(Q / row['path']) == row['sha256'] for row in rows)
assert all(sha(Q / name) == row['sha256'] and sha(row['path']) == row['sha256'] for name, row in payloads.items())
save(R / 'AUTHOR-SEAL.json', dict(at=utc(), author=ACTOR, handoff=ref(R / 'HANDOFF.json'),
    manifest=ref(cut / 'MANIFEST.json'), implement_receipt=ref(R / RUN / 'receipts/implement.json'),
    status=handoff['status'], Source_publication=False))
print(json.dumps(dict(handoff=ref(R / 'HANDOFF.json'), seal=ref(R / 'AUTHOR-SEAL.json'),
    manifest=ref(cut / 'MANIFEST.json'), source_and_test_LOC=handoff['LOC'], payloads=rows)))
