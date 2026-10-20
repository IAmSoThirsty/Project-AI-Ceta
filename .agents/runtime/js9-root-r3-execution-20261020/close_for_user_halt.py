"""Close the failed run and preserve a restart checkpoint; run no product tests."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import base64
import subprocess
import sys
import phase_coordinator as c

sys.path.insert(0, str(c.D))
import js9_support as j


def reference(path):
    raw = path.read_bytes()
    return dict(repository_relative_path=path.relative_to(c.F).as_posix(),
                sha256=hashlib.sha256(raw).hexdigest())


terminal_path = c.R / 'candidate-full-TERMINAL.json'
terminal = json.loads(terminal_path.read_bytes())
full_path = c.D / 'candidate-full/RESULT.json'
full = json.loads(full_path.read_bytes())
launch_path = c.D / 'candidate-full-LAUNCH-RESULT.json'
launch = json.loads(launch_path.read_bytes())
assert terminal['command_returned'] is True
assert terminal['exit_status'] == full['exit_status'] == launch['exit_status'] == 1
assert full['suite_aborted'] is True
assert full['primary_error']['type'] == 'KeyError'
assert full['primary_error']['message'] == "'native_after_fixture_cleanup'"
assert launch['record']['retirement_error'] is None
assert all(launch['record']['native_owner_after'].values())
assert not (c.D / 'publication').exists()
assert not (c.D / 'destination-full-LAUNCH-ATTEMPT.json').exists()
events_path = c.D / 'candidate-full/CASE-EVENTS.jsonl'
events = [json.loads(line) for line in events_path.read_text(encoding='utf-8').splitlines() if line.strip()]
event_counts = dict(Counter(row['event'] for row in events))
event_ids = {kind: [row['test_id'] for row in events if row['event'] == kind]
             for kind in ('PREPARE', 'START', 'STOP')}
gate_path, gate = j.proof(full['native_case_proof'])
assert gate['entered'] is True and gate['attempted'] is True and gate['passed'] is True
assert gate['no_profile_create_delete'] is True
source_observation = dict(checked_at=datetime.now(timezone.utc).isoformat())
try:
    j.verify(source='before')
except Exception as error:
    source_observation.update(verified=False, error_type=type(error).__name__, error=str(error))
else:
    source_observation.update(verified=True,
        scope='Exact R3 Source-before targets, candidate541, declared environment, Git and pinned fixture dependencies')
result = dict(disposition='FAILED_VERIFICATION_HALTED_AT_USER_REQUEST',
    full_result=reference(full_path), launch_result=reference(launch_path),
    terminal=reference(terminal_path), case_events=reference(events_path),
    recorded_case_event_counts=event_counts,
    event_inventory_matches_expected=all(ids == full['expected_ids'] for ids in event_ids.values()),
    final_report_tests_run=full['tests_run'], final_report_suite_aborted=full['suite_aborted'],
    reporting_error=full['primary_error'],
    recorded_case_failures=[row for row in events if row['event'] in ('FAILURE', 'ERROR', 'SKIP')],
    outer_owned_runner_and_handles_retired=True,
    inner_native_cleanup_summary='UNAVAILABLE_REPORT_CONSTRUCTION_FAILED',
    inner_native_cleanup_accepted=False,
    source_before_verification=source_observation,
    Source_publication=False, Source_accepted=False, product_acceptance=False,
    authorization_usage=dict(candidate_full_used=1, candidate_full_remaining=0,
        destination_full_used=0, destination_full_remaining=1, native_case_proof=reference(gate_path)),
    additional_test_or_diagnostic_started=False)
for node in ('implement', 'candidate_fixtures', 'candidate_cache'):
    try:
        c.complete(node, result,
            commands=[dict(command=subprocess.list2cmdline(terminal['argv']), exit_status=terminal['exit_status'])],
            validations=[dict(name='full_acceptance_and_complete_inner_cleanup_proof', passed=False)],
            exit_status=1)
    except AssertionError:
        response = json.loads((c.R / (node + '-complete.json')).read_bytes())['response']
        state = json.loads((c.R / c.RUN / 'state.json').read_bytes())
        claims = json.loads((c.R / c.RUN / 'claims.json').read_bytes())
        assert response['code'] == 'EXECUTION_FAILED' and response['allowed'] is False
        assert state['nodes'][node]['state'] == 'FAILED' and node not in claims
    else:
        raise AssertionError('FAILED_RUN_MUST_NOT_COMPLETE_SUCCEEDED')
c.invoke('user-halt-readiness', ['run', 'ready', c.RUN])
state = json.loads((c.R / c.RUN / 'state.json').read_bytes())
claims = json.loads((c.R / c.RUN / 'claims.json').read_bytes())
assert not claims and state['nodes']['review']['state'] == 'BLOCKED'
result.update(at=datetime.now(timezone.utc).isoformat(), state='HALTED_BY_EXPLICIT_USER_REQUEST',
    user_resume_required=True, active_root_claims=[],
    actual_coordinator_states={key: value['state'] for key, value in state['nodes'].items()},
    canonical_project='T:/00-Active/Project-AI-CETA',
    next_action='After explicit user resume: repair the final evidence aggregation against actual receipt shapes; review the frozen observer diagnostic before one ordinary diagnostic; freeze complete negative-image input lineage before any successor full run. A new candidate no-profile execution needs a fresh explicit grant. Preserve the unused destination grant and accepted JS8 baseline.',
    preserved_private_lanes=dict(
        manual_runtime='Implemented private host/ingress cut; positive admission remains blocked by inherited require_admission denial. Review exact cut and implement genuine canonical admission connection before claiming effect execution.',
        loader_capture='Private debug tooling with deterministic tests; no live debugger/profile execution authorized or performed.',
        observer_diagnostic='Frozen dormant one-case diagnostic; not executed.'))
checkpoint = c.R / 'USER-HALT-CHECKPOINT.json'
c.save(checkpoint, result)
for relative in ('build/progress.json', 'handoff/continuity.json'):
    path = c.F / relative
    raw = path.read_bytes()
    c.save(c.R / (path.name + '-BEFORE-USER-HALT.json'),
        dict(source=relative, sha256=hashlib.sha256(raw).hexdigest(), bytes_base64=base64.b64encode(raw).decode('ascii')))
    value = json.loads(raw)
    value['latest_user_halt_20261020'] = dict(at=result['at'], state=result['state'],
        checkpoint=reference(checkpoint), user_resume_required=True,
        active_root_claims=[], joined_source_accepted=False,
        inner_native_cleanup_summary='UNAVAILABLE_REPORT_CONSTRUCTION_FAILED')
    if relative == 'handoff/continuity.json':
        value['goal_status'] = 'PAUSED_AT_EXPLICIT_USER_REQUEST'
        value['first_next_action'] = 'Await explicit user resume after Codex restart; read latest_user_halt_20261020.checkpoint before any further execution.'
        value['next_action'] = value['first_next_action']
    else:
        value['goal_state'] = 'PAUSED_AT_EXPLICIT_USER_REQUEST'
    assert path.read_bytes() == raw
    updated = (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
    with path.open('r+b') as stream:
        assert stream.read() == raw
        stream.seek(0)
        assert stream.write(updated) == len(updated)
        stream.truncate()
        stream.flush()
    assert json.loads(path.read_bytes()) == value
c.save(c.R / 'USER-HALT-STATUS-PUBLICATION.json',
    dict(checkpoint=reference(checkpoint), metadata=[reference(c.F / rel)
         for rel in ('build/progress.json', 'handoff/continuity.json')]))
print(json.dumps(dict(checkpoint=reference(checkpoint), root_claims=[], halted=True)), flush=True)
