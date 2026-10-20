"""Close the observed failed R2 run without converting native passes into acceptance."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess
import sys

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
RUN = 'js9-root-execution-20261020'
D = F / '.agents/runtime/js9-runtime-20261020/successor-r2'
claim = json.loads((R / RUN / 'claims.json').read_bytes())['implement']
assert claim['executor_id'] == '/root' and Path(claim['workspace']) == D
terminal = json.loads((R / 'candidate-full-TERMINAL.json').read_bytes())
result = json.loads((D / 'candidate-full/RESULT.json').read_bytes())
native = json.loads((D / 'candidate-full/NATIVE-CASE-PROOF.json').read_bytes())
assert terminal['exit_status'] == 1 and result['tests_run'] == 0
assert native['entered'] is False and native['attempted'] is False
assert all(not native[name] for name in ('exact_native_calls', 'handles', 'sockets', 'profile_folder_observations'))
sys.path.insert(0, 'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_runtime import _snapshot_workspace, _changed_files
changed = _changed_files(claim['baseline_snapshot'], _snapshot_workspace(D, F))
commands = []
for phase in ('native-store', 'native-observer', 'candidate-full'):
    observed = json.loads((R / (phase + '-TERMINAL.json')).read_bytes())
    commands.append(dict(command=subprocess.list2cmdline(observed['argv']), exit_status=observed['exit_status']))
receipt = dict(schema_version=1, run_id=RUN, node_id='implement', executor_id='/root',
    started_at=claim['claimed_at'], finished_at=datetime.now(timezone.utc).isoformat(),
    input_hash=claim['input_hash'], changed_files=changed,
    result=dict(disposition='FAILED_BEFORE_TEST_EXECUTION', native_store_cases_passed=18,
        native_observer_cases_passed=6, full_tests_run=0, no_profile_attempt_consumed=False,
        publication_performed=False, Source_accepted=False,
        terminal_sha256=hashlib.sha256((R / 'candidate-full-TERMINAL.json').read_bytes()).hexdigest(),
        cause='Missing two same-project test helper dependencies; actual discovery records retained separately',
        successor='Fresh dependency-complete candidate and corrected runner; frozen R2 preserved'),
    commands=commands, validations=[dict(name='full_candidate_acceptance', passed=False),
        dict(name='authorized_no_profile_case_was_not_entered_or_attempted', passed=True)], exit_status=1)
receipt_path = R / 'implement-failure-receipt.json'
with receipt_path.open('x', encoding='utf-8') as stream:
    json.dump(receipt, stream, indent=2)
    stream.write('\n')
argv = ['powershell', '-NoProfile', '-File', 'T:/02-Config/agents/taar-orchestrate.ps1',
    'node', 'complete', RUN, 'implement', str(receipt_path), '--runtime-root', str(R)]
completed = subprocess.run(argv, cwd=F, capture_output=True)
for name, raw in (('stdout', completed.stdout), ('stderr', completed.stderr)):
    with (R / ('failure-complete.' + name)).open('xb') as stream:
        stream.write(raw)
response = json.loads(completed.stdout.decode('utf-8-sig'))
state = json.loads((R / RUN / 'state.json').read_bytes())
claims = json.loads((R / RUN / 'claims.json').read_bytes())
assert completed.returncode != 0 and response['allowed'] is False, response
assert state['nodes']['implement']['state'] == 'FAILED' and 'implement' not in claims, (state, claims)
record = dict(argv=argv, exit_status=completed.returncode, response=response,
    observed_state=state['nodes']['implement']['state'], claim_released=True,
    Source_publication=False, no_profile_attempt_consumed=False)
with (R / 'FAILED-EXECUTION-CLOSED.json').open('x', encoding='utf-8') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
print(json.dumps(record))
