"""Freeze exact private source, provenance, pure results and actual TAAR receipt."""
from pathlib import Path
from datetime import datetime, timezone
import difflib
import hashlib
import json
import subprocess

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
Q = F / '.agents/real-effect-entrypoint-20261020'
BASE = F / '.agents/js9-runtime-r5-20261020'
RUN = 'real-effect-entrypoint-20261020'
ACTOR = '/root/ac7_native_artifact_review20'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def now():
    return datetime.now(timezone.utc).isoformat()

def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')

def invoke(label, args):
    command = ['powershell', '-NoProfile', '-File', 'T:/02-Config/agents/taar-orchestrate.ps1',
        *args, '--runtime-root', str(R)]
    result = subprocess.run(command, cwd=F, capture_output=True)
    for suffix, raw in [('stdout', result.stdout), ('stderr', result.stderr)]:
        with (R / (label + '.' + suffix)).open('xb') as stream:
            stream.write(raw)
    value = json.loads(result.stdout.decode('utf-8-sig'))
    save(R / (label + '.json'), dict(command=command, exit_status=result.returncode, response=value))
    assert result.returncode == 0 and value['allowed'] is True, value
    return value

base_manifest = F / '.agents/runtime/js9-runtime-20261020/successor-r3/MANIFEST-Q5.json'
assert sha(base_manifest) == 'cce2c8e2c3a31fbedf5c2d83b2d15d499a93030c38ebe0c1e4545b868ef99acf'
base = json.loads(base_manifest.read_bytes())['payload_hashes']
assert len(base) == 541 and all(sha(BASE / name) == pin for name,pin in base.items())
payloads = {p.relative_to(Q).as_posix():sha(p) for p in sorted(Q.rglob('*')) if p.is_file()}
assert not any('__pycache__' in name or name.endswith('.pyc') for name in payloads)
authored = {name:dict(before=base.get(name), after=pin) for name,pin in payloads.items()
    if pin != base.get(name)}
assert len(payloads) == 548 and len(authored) == 13
assert set(base).issubset(payloads)
diff = []
source_added = source_deleted = test_added = test_deleted = 0
for name,row in authored.items():
    old = [] if name not in base else (BASE / name).read_text('utf8').splitlines(True)
    new = (Q / name).read_text('utf8').splitlines(True)
    delta = difflib.unified_diff(old, new, fromfile='Q5/' + name, tofile='entrypoint/' + name)
    diff.extend(delta)
    added = deleted = 0
    for operation,a,b,c,d in difflib.SequenceMatcher(None, old, new).get_opcodes():
        if operation != 'equal':
            added += d-c
            deleted += b-a
    row.update(physical_lines=len(new), added_lines=added, deleted_lines=deleted)
    if name.startswith('src/'):
        source_added += added
        source_deleted += deleted
    elif name.startswith('tests/'):
        test_added += added
        test_deleted += deleted
with (R / 'AUTHORED.diff').open('x', encoding='utf8', newline='') as stream:
    stream.write(''.join(diff))
result_path = R / 'pure_r7/RESULT.json'
result = json.loads(result_path.read_bytes())
assert result['passed'] and result['tests_run'] == len(result['expected_ids']) == 69
assert not result['boundary_attempts'] and not result['errors'] and not result['failures'] and not result['skipped']
assert all(payloads[name] == pin for name,pin in result['payload_hashes'].items())
terminal = dict(tool='exec_command', chunk_id='3a598c', exit_status=0,
    command=[str(F / '.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'),
        '-B', '-X', 'utf8', str(R / 'run_pure.py'), 'pure_r7'],
    actual_interpreter=result['executable'], base_interpreter=result['base_executable'],
    result_sha256=sha(result_path), source_unchanged=True, actual_native_execution=False)
save(R / 'PURE-TERMINAL.json', terminal)
limits = [
    dict(classification='BLOCKING_POSITIVE_EXECUTION', path='src/ceta/identity/owners.py:21',
        fact='NativeCpuOwnerSession inherits require_admission raising PROTECTED_RESOURCE_OWNER_UNAVAILABLE; canonical consume calls it at transactions.py:365 and :400. No production substitution was added.'),
    dict(classification='BLOCKING_ACTIVATION', fact='AC7 positive restricted-worker qualification failed/consumed; failing DLL remains unknown. This cut creates no profile or fresh profile-operation authority.'),
    dict(classification='REQUIRED_TRUSTED_DEPLOYMENT_INPUT', fact='The trusted parent must supply the actual canonical durable epoch, complete reviewed code/runtime selection, owned qualified assets/scratch and measured registered client/server identities. No installed deployment or normal GUI selection is fabricated.'),
    dict(classification='BLOCKING_PENDING_RUNTIME_QUALIFICATION', fact='Advancing pending recovery requires the original live request context/thread. Retaining a pipe does not extend its 30-second envelope. Cross-process/expired-context recovery and durable custody across interpreter exit remain unqualified.'),
    dict(classification='NOT_RUN', fact='No application, host, pipe listener, worker, native DLL load, SQLite connect, Hello/credential operation, profile operation, CPU effect, complete native/full/destination/product acceptance was run.')]
manifest = dict(schema='ceta.manual-effect-entrypoint-candidate.v1', frozen_at=now(),
    author=ACTOR, repository=str(F), candidate=str(Q),
    base_manifest=dict(path=str(base_manifest), sha256=sha(base_manifest)),
    base_payloads=541, inherited_unchanged=535, payload_hashes=payloads, authored_deltas=authored,
    source_added_physical_lines=source_added, source_deleted_physical_lines=source_deleted,
    test_added_physical_lines=test_added, test_deleted_physical_lines=test_deleted,
    pure_result=dict(path=str(result_path), sha256=sha(result_path), cases=69,
        native_boundary_attempts=0, command_terminal=str(R / 'PURE-TERMINAL.json')),
    authored_diff_sha256=sha(R / 'AUTHORED.diff'), limits=limits,
    self_review='IMPLEMENTED_ADDITIVE_HOST_INGRESS_CONNECTION; POSITIVE_ADMISSION_BLOCKED',
    independent_review='PENDING_ROOT_ASSIGNED_DISTINCT_REVIEWER', Source_publication=False)
save(R / 'MANIFEST.json', manifest)
claim = json.loads((R / 'LEASE-ACQUIRED.json').read_bytes())['claims']['implement']
receipt = R / 'implement-receipt.json'
save(receipt, dict(schema_version=1, run_id=RUN, node_id='implement', executor_id=ACTOR,
    started_at=claim['claimed_at'], finished_at=now(), input_hash=claim['input_hash'],
    changed_files=sorted('.agents/real-effect-entrypoint-20261020/' + name for name in payloads),
    result=dict(manifest=str(R / 'MANIFEST.json'), manifest_sha256=sha(R / 'MANIFEST.json'),
        payloads=548, authored_paths=13, inherited_unchanged=535, pure_cases=69,
        Source_publication=False, native_execution=False, independent_review='PENDING',
        positive_admission='BLOCKED_BY_EXISTING_PROTECTED_RESOURCE_OWNER_UNAVAILABLE'),
    commands=[dict(command="& '" + terminal['command'][0] + "' -B -X utf8 '" + str(R / 'run_pure.py') + "' pure_r7", exit_status=0)],
    validations=[dict(name='69_pure_cases_original_IPC_results_import_boundaries',passed=True),
        dict(name='zero_native_boundary_attempts_no_skips_exact_payload_pins',passed=True),
        dict(name='541_frozen_Q5_inputs_535_unchanged_13_authored_deltas',passed=True),
        dict(name='default_admission_denial_and_remaining_native_gates_explicit',passed=True)], exit_status=0))
invoke('implement-complete', ['node', 'complete', RUN, 'implement', str(receipt)])
save(R / 'FROZEN.json', dict(at=now(), manifest_sha256=sha(R / 'MANIFEST.json'),
    implement_receipt_sha256=sha(receipt), native_execution=False, Source_publication=False,
    independent_review='PENDING', evidence_lease='ACTIVE_UNTIL_REVIEW_HANDOFF'))
print(json.dumps(dict(manifest_sha256=sha(R / 'MANIFEST.json'),
    implement_receipt_sha256=sha(receipt), authored_paths=len(authored), payloads=len(payloads),
    source_added=source_added, source_deleted=source_deleted, test_added=test_added,
    tests=69, disposition=manifest['self_review'])), flush=True)
