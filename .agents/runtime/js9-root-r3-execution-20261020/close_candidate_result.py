"""Record the real full result and retire leases without accepting a failed suite."""
from pathlib import Path
import json
import subprocess
import sys
import phase_coordinator as c

sys.path.insert(0, str(c.D))
import js9_support as j

terminal_path = c.R / 'candidate-full-TERMINAL.json'
terminal = json.loads(terminal_path.read_bytes())
assert terminal['command_returned'] is True
full_ref = j.exact_ref(c.D / 'candidate-full/RESULT.json')
_, full = j.proof(full_ref)
launch_ref = j.exact_ref(c.D / 'candidate-full-LAUNCH-RESULT.json')
_, launch = j.proof(launch_ref)
j.require_case_ids(full['expected_ids'])
assert full['tests_run'] == len(full['expected_ids']) == 2622
assert full['executed_ids'] == full['stopped_ids'] == full['expected_ids']
assert full['exit_status'] == launch['exit_status'] == terminal['exit_status'] == 1
assert full['failures'] >= 1 and full['errors'] == full['skips'] == 0
assert full['suite_aborted'] is False and full['primary_error'] is None
assert launch['record']['child_exit'] == 1
assert all(launch['record']['native_owner_after'].values())
assert launch['record']['retirement_error'] is None
_, physical = j.proof(full['physical_custody'])
_, native = j.proof(full['native_owners_proof'])
_, gate = j.proof(full['native_case_proof'])
assert gate['entered'] is True and gate['attempted'] is True and gate['passed'] is True
assert gate['precise_denial_matched'] is True and gate['release_reader_closed'] is True
assert gate['no_profile_create_delete'] is True
assert full['source_unchanged'] is True
j.verify(source='before')
assert not (c.D / 'publication').exists() and not (c.D / 'destination-full-LAUNCH-ATTEMPT.json').exists()
resources_closed = physical['owned_resources_closed'] is True and native['owned_resources_closed'] is True
command = dict(command=subprocess.list2cmdline(terminal['argv']), exit_status=terminal['exit_status'])
result = dict(disposition='FAILED_FULL_ACCEPTANCE', full_result=full_ref, full_launch=launch_ref,
    exact_tests_run=2622, failures=full['failure_details'], errors=full['error_details'], skips=full['skip_details'],
    captured_resources_closed=resources_closed, observer_failure_cause='UNRESOLVED',
    no_profile_candidate_execution_consumed=True, no_profile_candidate_case_passed=True,
    Source_publication=False, Source_accepted=False, product_acceptance=False,
    next_action='Inspect retained failure timing and perform one reviewed ordinary-observer diagnostic; no full retry authorized')
try:
    c.complete('implement', result, commands=[command],
        validations=[dict(name='full_candidate_acceptance', passed=False),
            dict(name='all_captured_resources_closed', passed=resources_closed)], exit_status=1)
except AssertionError:
    response = json.loads((c.R / 'implement-complete.json').read_bytes())['response']
    state = json.loads((c.R / c.RUN / 'state.json').read_bytes())
    claims = json.loads((c.R / c.RUN / 'claims.json').read_bytes())
    assert response['code'] == 'EXECUTION_FAILED' and response['allowed'] is False
    assert state['nodes']['implement']['state'] == 'FAILED' and 'implement' not in claims
else:
    raise AssertionError('FAILED_SUITE_MUST_NOT_COMPLETE_SUCCEEDED')
for node in ('candidate_fixtures', 'candidate_cache'):
    fixture_result = dict(disposition='OWNED_FIXTURE_RETIREMENT_WITNESS', full_result=full_ref,
        full_suite_accepted=False, captured_resources_closed=resources_closed,
        outer_process_thread_job_startup_handles_closed=True, Source_publication=False)
    try:
        c.complete(node, fixture_result,
            validations=[dict(name='captured_fixture_resources_closed', passed=resources_closed)],
            exit_status=0 if resources_closed else 1)
    except AssertionError:
        assert resources_closed is False
        current = json.loads((c.R / c.RUN / 'state.json').read_bytes())
        assert current['nodes'][node]['state'] == 'FAILED'
c.invoke('final-candidate-readiness', ['run', 'ready', c.RUN])
state = json.loads((c.R / c.RUN / 'state.json').read_bytes())
claims = json.loads((c.R / c.RUN / 'claims.json').read_bytes())
assert not claims
assert state['nodes']['implement']['state'] == 'FAILED'
assert state['nodes']['review']['state'] == 'BLOCKED'
record = dict(full_result=full_ref, actual_states={key:value['state'] for key,value in state['nodes'].items()},
    active_claims=[], captured_resources_closed=resources_closed, Source_publication=False,
    Source_accepted=False, product_acceptance=False,
    authorization_usage=dict(candidate_full_used=1, candidate_full_remaining=0,
        destination_full_used=0, destination_full_remaining=1,
        native_case_proof=full['native_case_proof']))
c.save(c.R / 'CANDIDATE-FAILED-CLOSED.json', record)
print(json.dumps(record), flush=True)
