"""One reviewed native qualification child, using the exact retained job helper."""
from readiness_support import *


def claim_attempt(release, release_facts, review_facts, inputs_facts, output):
    require(not (N / 'ONE-ATTEMPT.json').exists() and not output.exists(), 'ATTEMPT_ALREADY_CONSUMED')
    # The marker is the irrevocable engineering-attempt boundary, before any
    # CETA import/native creation. Failed publication/launch is never retried.
    save(N / 'ONE-ATTEMPT.json', dict(at=utc(), attempt_id=release['attempt_id'],
        release_sha256=release_facts['sha256'], release_native=release_facts,
        review_native=review_facts, inputs_sha256=inputs_facts['sha256'],
        output_root=str(output), automatic_retry=False, scope='Engineering qualification only'))
    output.mkdir(exist_ok=False)
    (output / 'tmp').mkdir()
    return ordinary(N / 'ONE-ATTEMPT.json')


def main(argv):
    require(argv == [], 'NO_CALLER_SELECTED_SCRIPT_OR_PATH')
    inputs, input_facts = preflight()
    release, release_facts, review_facts, output = release_record(inputs, input_facts)
    marker = claim_attempt(release, release_facts, review_facts, input_facts, output)
    environment = {'SystemRoot': inputs['SystemRoot'], 'TEMP': str(output / 'tmp'), 'TMP': str(output / 'tmp'),
                   'PYTHONDONTWRITEBYTECODE': '1'}
    args = ('-B', '-X', 'utf8', str(N / 'run_native.py'), release['attempt_id'],
            release_facts['sha256'], marker['sha256'])
    save(output / 'COMMAND.json', dict(at=utc(), executable=str(PY), arguments=list(args),
        cwd=str(output), environment=environment, expected_image_sha256=inputs['environment']['E3/Scripts/python.exe']['sha256'],
        child_wait_seconds=WAIT_SECONDS, inherited_handles=[], standard_handles=None,
        original_seven_deadlines_unchanged=True, outer_wait_is_not_synchronous_native_preemption=True))
    sys.path.insert(0, str(Q / 'src'))
    from ceta.supervisor.windows_jobs import WindowsOwnedProcess
    import bounded_custody as custody
    require(ordinary(N / 'bounded_custody.py')['sha256'] == CUSTODY_PIN, 'CUSTODY_HELPER_DRIFT')
    def launch():
        return WindowsOwnedProcess.launch(str(PY), args, cwd=str(output), environment=environment,
            expected_image_sha256=inputs['environment']['E3/Scripts/python.exe']['sha256'])
    def emit(row):
        save(output / 'OWNED-RUNNER.json', dict(at=utc(), **row))
    def read_child():
        path = output / 'c/RESULT.json'
        child, child_facts = pinned_json(path, ordinary(path)['sha256'])
        require(type(child['exit_status']) is int and child['exit_status'] == 0
                and child['tests_run'] == 7 and child['failures'] == child['errors'] == child['skips'] == 0
                and child['expected_ids'] == child['executed_ids'] == child['stopped_ids'] == list(IDS)
                and child['native_resources']['owned_resources_closed'] is True
                and child['remaining_threads'] == [] and child['forbidden_calls'] == []
                and child['release_sha256'] == release_facts['sha256']
                and child['marker_sha256'] == marker['sha256'], 'NATIVE_CHILD_NOT_ACCEPTED')
        return child_facts
    primary = None
    record = None
    try:
        record = custody.run_owned(launch, emit, read_child, timeout=WAIT_SECONDS)
        require(type(record['child_exit']) is int and record['child_exit'] == 0, 'NATIVE_CHILD_EXIT_NONZERO')
    except BaseException as error:
        primary = error
        record = dict.get(BaseException.__dict__['__dict__'].__get__(error), 'full_runner_report', record)
    final_inputs, final_input_facts = preflight()
    unchanged = final_inputs == inputs and final_input_facts == input_facts
    report = dict(at=utc(), exit_status=0 if primary is None and unchanged else 1,
        decision='qualification_passed' if primary is None and unchanged else 'not_accepted',
        primary=None if primary is None else custody.failure(primary), record=record,
        candidate352_and_environment_exact=unchanged,
        release_native=release_facts, review_native=review_facts, marker_native=marker,
        no_historical_pid_operations=True, no_profile_Hello=True,
        scope='Seven original ordinary-worker/native CPU tests with controlled authority; no Source acceptance',
        no_automatic_cleanup_retry=True, synchronous_native_launch_close_not_preempted=True)
    save(output / 'SUPERVISION-RESULT.json', report)
    print(canonical(dict(exit_status=report['exit_status'], decision=report['decision'])), flush=True)
    if primary is not None:
        raise primary
    require(unchanged, 'FINAL_NATIVE_INPUT_DRIFT')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
