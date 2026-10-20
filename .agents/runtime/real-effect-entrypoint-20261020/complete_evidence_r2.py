"""Close the evidence lease so a different actor can claim exact-cut review."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
RUN = 'real-effect-entrypoint-20261020'
ACTOR = '/root/ac7_native_artifact_review20'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()

def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')

manifest = R / 'MANIFEST.json'
assert sha(manifest) == 'd33e2b09c1492fe4cb6b0cce233d567bccf7ac5e3de0e62fd11d270368e657a1'
claim = json.loads((R / 'LEASE-ACQUIRED.json').read_bytes())['claims']['evidence']
baseline = claim['baseline_snapshot']
receipt = R / 'evidence-receipt-r2.json'
changed = []
for path in R.rglob('*'):
    if path.is_file():
        name = path.relative_to(F).as_posix()
        if baseline.get(name) != sha(path):
            changed.append(name)
changed.append(receipt.relative_to(F).as_posix())
changed.append((R / RUN / '.state.lock').relative_to(F).as_posix())
save(receipt, dict(schema_version=1, run_id=RUN, node_id='evidence', executor_id=ACTOR,
    started_at=claim['claimed_at'], finished_at=now(), input_hash=claim['input_hash'],
    changed_files=sorted(set(changed)),
    result=dict(manifest=str(manifest), manifest_sha256=sha(manifest),
        implement_receipt_sha256=sha(R / 'implement-receipt.json'),
        pure_result_sha256=sha(R / 'pure_r7/RESULT.json'),
        observed_pure_command_tool_chunk='3a598c', native_execution=False,
        failed_receipts_preserved=True, Source_publication=False,
        distinct_review='REQUIRED_AND_PENDING_ROOT_ASSIGNMENT'),
    commands=[dict(command="& 'T:\\00-Active\\Project-AI-CETA\\.agents\\source-assembly-20261014T021300Z\\.agents\\e3\\Scripts\\python.exe' -B -X utf8 '.agents/runtime/real-effect-entrypoint-20261020/run_pure.py' pure_r7", exit_status=0)],
    validations=[dict(name='69_pure_cases_zero_boundary_attempts_exact_source_hashes',passed=True),
        dict(name='actual_TAAR_implement_SUCCEEDED_receipt_bound',passed=True),
        dict(name='failed_lease_and_failed_author_control_runs_preserved',passed=True)], exit_status=0))
command = ['powershell', '-NoProfile', '-File', 'T:/02-Config/agents/taar-orchestrate.ps1',
    'node', 'complete', RUN, 'evidence', str(receipt), '--runtime-root', str(R)]
result = subprocess.run(command, cwd=F, capture_output=True)
for suffix, raw in [('stdout', result.stdout), ('stderr', result.stderr)]:
    with (R / ('evidence-complete-r2.' + suffix)).open('xb') as stream:
        stream.write(raw)
value = json.loads(result.stdout.decode('utf-8-sig'))
save(R / 'evidence-complete-r2.json', dict(command=command, exit_status=result.returncode, response=value))
assert result.returncode == 0 and value['allowed'] is True, value
print(json.dumps(dict(allowed=value['allowed'], review_state=value['nodes']['review']['state'],
    evidence_receipt_sha256=sha(receipt))), flush=True)
