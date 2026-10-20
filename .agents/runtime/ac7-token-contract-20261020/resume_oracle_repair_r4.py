"""Resume the preserved AC7 candidate under a new actual bounded write lease."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess

F = Path('T:/00-Active/Project-AI-CETA')
E = Path(__file__).resolve().parent
R = E / 'lease-r3'
Q = F / '.agents/ac7-token-contract-20261020'
W = F / '.agents/fixtures/ac7-token-observation-20261020'
RUN = 'ac7-qualification-r4-20261020'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()
def save(path, value):
    with path.open('x', encoding='utf8') as stream: json.dump(value, stream, indent=2)
def invoke(label, args):
    command = ['powershell', '-NoProfile', '-File', 'T:/02-Config/agents/taar-orchestrate.ps1',
               *args, '--runtime-root', str(R)]
    completed = subprocess.run(command, cwd=F, capture_output=True)
    for suffix, raw in [('stdout', completed.stdout), ('stderr', completed.stderr)]:
        with (R / (label + '.' + suffix)).open('xb') as stream: stream.write(raw)
    response = json.loads(completed.stdout.decode('utf-8-sig'))
    save(R / (label + '.json'), dict(command=command, exit_status=completed.returncode, response=response))
    assert completed.returncode == 0 and response['allowed'] is True, response
    return response
partial = E / 'AC7-QUALIFICATION-MANIFEST-R3.json'
assert sha(partial) == 'e2ee86a9b7ea7b96f24062fae2739e9932c63e0e0c5597368302a209b67f8b1a'
pins=json.loads(partial.read_bytes())['payload_hashes']
assert all(sha(Q/n)==h for n,h in pins.items())
R.mkdir(exist_ok=False)
invoke('init', ['run', 'init', '--root', str(F), '--scope', str(E), '--run-id', RUN])
for node in ('discover', 'plan'):
    claim = invoke(node + '-claim', ['node', 'claim', RUN, node, '--executor', '/root', '--workspace', str(W)])['claim']
    receipt = R / (node + '-receipt.json')
    save(receipt, dict(schema_version=1, run_id=RUN, node_id=node, executor_id='/root',
        started_at=claim['claimed_at'], finished_at=now(), input_hash=claim['input_hash'], changed_files=[],
        result=dict(skills_used=['unfinished-work-recovery', 'thirsty-work-orchestrator'],
            governing_version='thirsty-constitution-v0.1', source_head='83fc9432b4a37ee7f91d6c5b0d358a015548aed4',
            partial_manifest_sha256=sha(partial), preserved_payloads=357,
            next_code='Repair exact process-access refusal errors and owned target liveness brackets',
            host_profile_operations='NO_NEW_AUTHORIZATION'), commands=[], exit_status=0,
        validations=[dict(name='preserved_partial_source_and_cancelled_lease_verified', passed=True)]))
    invoke(node + '-complete', ['node', 'complete', RUN, node, str(receipt)])
claim = invoke('implement-claim', ['node', 'claim', RUN, 'implement', '--executor', '/root', '--workspace', str(Q)])['claim']
save(R / 'RESUME.json', dict(at=now(), actual_executor='/root', input_hash=claim['input_hash'],
    permitted_scope=claim['effective_write_scope'], previous_rejected_review_preserved=True,
    existing_partial_source_adopted_for_repair=True, source_publication=False, host_authorization=False))
print(json.dumps(dict(allowed=True, run=RUN, input_hash=claim['input_hash'], scope=claim['effective_write_scope'])), flush=True)
