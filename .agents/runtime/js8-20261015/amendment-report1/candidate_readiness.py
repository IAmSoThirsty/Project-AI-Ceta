"""Bounded publication readiness; prior candidate full remains FAILED."""
from pathlib import Path
import json
import math
import re
import amendment_support as j

OLD = j.PARENT / 'amendment-order1'
OLD_Q = j.F / '.agents/js8-amendment-order1-20261017'
HISTORY = {
    'result': 'candidate-full/RESULT.json',
    'launch': 'candidate-full-LAUNCH-RESULT.json',
    'command': 'candidate-full-COMMAND.json',
    'preflight': 'candidate-full/PREFLIGHT.json',
    'raw': 'candidate-full/RAW.txt',
    'events': 'candidate-full/CASE-EVENTS.jsonl',
    'physical': 'candidate-full/PHYSICAL-CUSTODY.json',
    'native': 'candidate-full/NATIVE-CASE-PROOF.json',
    'sqlite_receipts': 'candidate-full/SQLITE-RECEIPTS.json',
}


def require_case_evidence(raw, events, required):
    """Read every original case, including unittest's two-line descriptions."""
    assert type(raw) is str and type(events) is list
    assert len(events) == len(required) * 3, 'CASE_EVENT_COUNT'
    last_elapsed = -1
    for offset, identifier in enumerate(required):
        for position, kind in enumerate(('PREPARE', 'START', 'STOP')):
            row = events[offset * 3 + position]
            assert type(row) is dict and set(row) == {'event', 'test_id', 'at', 'elapsed_seconds'}
            assert row['event'] == kind and row['test_id'] == identifier, 'CASE_EVENT_ORDER'
            elapsed = row['elapsed_seconds']
            assert type(elapsed) in (int, float) and math.isfinite(elapsed) and elapsed >= last_elapsed
            assert type(row['at']) is str and row['at']
            last_elapsed = elapsed
    lines = raw.splitlines()
    position = multiline = 0
    for identifier in required:
        method = identifier.rsplit('.', 1)[1]
        header = method + ' (' + identifier + ')'
        assert position < len(lines), 'RAW_CASE_MISSING'
        line = lines[position]
        position += 1
        if line == header + ' ... ok':
            continue
        assert line == header, 'RAW_CASE_ID_OR_RESULT_MISMATCH'
        assert position < len(lines), 'RAW_DESCRIPTION_RESULT_MISSING'
        description = lines[position]
        position += 1
        assert description and description.endswith(' ... ok'), 'RAW_CASE_NOT_OK'
        assert not description.startswith('test_'), 'RAW_DESCRIPTION_IS_ANOTHER_CASE'
        multiline += 1
    terminal = '\n'.join(lines[position:])
    match = re.fullmatch(r'\n-{70}\nRan ' + str(len(required)) + r' tests in ([0-9]+\.[0-9]+)s\n\nOK', terminal)
    assert match is not None, 'RAW_TERMINAL_NOT_EXACT_OK'
    elapsed = float(match.group(1))
    assert 0 < elapsed < 3600
    return dict(case_count=len(required), ordered_prepare_start_stop=True,
        every_raw_case_ok=True, multiline_descriptions=multiline,
        raw_terminal='OK', raw_elapsed_seconds=elapsed,
        terminal_candidate_acceptance='FAILED')


def check_prior_failed_candidate():
    a = j.current_json(j.R / 'AMENDMENT.json')
    refs = a['prior_failed_candidate']
    assert type(refs) is dict and set(refs) == set(HISTORY)
    values = {}
    for key, name in HISTORY.items():
        path, data = j.proof_bytes(refs[key])
        assert path == OLD / name
        values[key] = data if key in ('raw', 'events') else json.loads(data)
    failed, launch, command = values['result'], values['launch'], values['command']
    assert failed['phase'] == 'candidate-full' and failed['exit_status'] == 1
    assert type(failed['exit_status']) is int and failed['suite_aborted'] is True
    assert failed['primary_error'] == {'type': 'TypeError'} and failed['tests_run'] == 0
    assert failed['Source_publication'] is failed['Source_accepted'] is False
    assert launch['phase'] == 'candidate-full' and type(launch['exit_status']) is int and launch['exit_status'] == 1
    assert command['exit_status'] == 1 and type(command['exit_status']) is int
    assert launch['Source_accepted'] is False and launch['own_job_only'] is True
    child = launch['record']
    assert child['child_exit'] == 1 and type(child['child_exit']) is int
    assert child['retirement_error'] is None and child['automatic_cleanup_retry'] is False
    closed = child['native_owner_after']
    assert set(closed) == {'closed', 'process_closed', 'thread_closed', 'job_closed', 'startup_handles_closed'}
    assert all(item is True for item in closed.values())
    expected_outer_error = {'type': 'KeyError', 'message': "'expected_ids'"}
    assert child['primary_error'] == child['child_result_read_error'] == launch['primary_error'] == expected_outer_error
    assert child['child_result'] is None
    v, m = j.inputs(), j.manifest()
    for name, pin in m['expected_payload_hashes'].items():
        assert j.s.ordinary(OLD_Q / name)['sha256'] == pin, ('PRIOR_CANDIDATE_CHANGED', name)
    preflight = values['preflight']
    assert preflight['phase'] == 'candidate-full' and preflight['root'] == str(OLD_Q)
    assert preflight['manifest_sha256'] == a['prior_manifest']['sha256']
    required = j.require_case_ids(preflight['expected_ids'])
    assert preflight['before_hashes'] == m['expected_payload_hashes']
    assert preflight['test_order_amendment'] == a['prior_amendment']
    expected_interpreter = dict(sys_executable=v['python']['path'], sys_base_executable=v['base_python']['path'],
        python=v['python'], base_python=v['base_python'])
    assert preflight['interpreter'] == launch['interpreter'] == expected_interpreter
    release_ref = preflight['release']
    assert command['release'] == launch['release'] == release_ref
    release_path, release = j.proof(release_ref)
    assert release_path == OLD / 'releases/candidate-full.json'
    assert release['amendment'] == a['prior_amendment'] and release['manifest_sha256'] == a['prior_manifest']['sha256']
    assert release['Source_publication'] is False and release['automatic_retry'] is False
    arguments = ['candidate-full', '--release-path', str(release_path), '--release-sha256', release_ref['sha256']]
    assert command['command'] == [v['python']['path'], '-B', '-X', 'utf8', str(OLD / 'launch_full.py'), *arguments]
    assert launch['argv'] == [v['base_python']['path'], '-B', '-X', 'utf8', str(OLD / 'launch_full.py'), *arguments]
    assert launch['child_argv'] == [v['python']['path'], '-B', '-X', 'utf8', str(OLD / 'run_full.py'), *arguments]
    assert preflight['argv'] == [v['base_python']['path'], '-B', '-X', 'utf8', str(OLD / 'run_full.py'), *arguments]
    assert child['native_owner']['image_sha256'] == v['python']['sha256']
    _, original_review = j.proof(command['review'])
    assert original_review['decision'] == 'approved' and original_review['exit_status'] == 0
    assert original_review['author'] == '/root' and original_review['reviewer'] == '/root/integration_amendment_review'
    assert original_review['amendment'] == a['prior_amendment'] and original_review['manifest_sha256'] == a['prior_manifest']['sha256']
    _, old_amendment = j.proof(a['prior_amendment'])
    assert release['reviewed_scripts'] == original_review['reviewed_scripts'] == old_amendment['reviewed_scripts']
    for name, pin in old_amendment['reviewed_scripts'].items():
        assert j.s.ordinary(OLD / name)['sha256'] == pin
    physical = values['physical']
    assert physical['owned_resources_closed'] is True and physical['remaining_resources'] == []
    assert physical['no_logical_journal_closed_flags_used'] is True
    assert physical['sqlite'] and all(row['physical_closed_probe'] is True for row in physical['sqlite'])
    assert physical['streams'] and all(row['closed'] is True and row['fileno_denied'] is True for row in physical['streams'])
    assert all(row['closed'] is True for row in physical['os_descriptors'])
    assert physical['native_owners'] == []  # This observer did not capture process owners.
    sql = values['sqlite_receipts']
    assert sql['test_journal_constructor_cleanup'] and sql['test_journal_postconstruction_cleanup']
    assert all(row['all_fixture_native_connections_closed'] is True for row in sql['test_journal_constructor_cleanup'])
    assert all(row['all_exact_native_connections_closed'] is True for row in sql['test_journal_postconstruction_cleanup'])
    native = values['native']
    assert failed['native_case_proof'] == refs['native']
    assert native['passed'] is False and native['precise_denial_matched'] is False
    assert native['owned_fixture_resources_closed'] is True and native['release_reader_closed'] is True
    assert native['no_profile_create_delete'] is True and native['Source_accepted'] is False
    assert native['issues'] == [] and native['diagnostic'] is None
    assert native['original_case_id'] == m['native_gate']['original_case_id']
    assert native['release'] == release['native_case_release'] == preflight['native_case_release']
    native_path, native_release = j.proof(native['release'])
    assert native_path == OLD / 'releases/candidate-full-native.json'
    assert native_release['create_profiles'] is False and native_release['execute_exact_original_case'] is True
    assert native_release['expected_denial_winerror'] == native['expected_denial_winerror'] == 267
    assert native['exact_native_calls'] == [dict(step='restricted_CreateProcessW', returned=True, succeeded=False, winerror=2)]
    assert native['run_nonce'] == native_release['run_nonce']
    assert native['subject'] == native_release['subject']
    assert native['subject']['source_root'] == str(OLD_Q) and native['subject']['mode'] == 'candidate-full'
    assert native['subject']['run_id'] == j.RUN and native['subject']['expected_ids_sha256'] == m['case_set']['sha256']
    assert all(row['allocation_closed'] is True and row['absent'] is True and row['folder_absent'] is True
        for row in native['profile_folder_observations'])
    assert all(row['closed'] is True for row in native['handles'] + native['sockets'])
    case_summary = require_case_evidence(values['raw'].decode('utf-8'),
        [json.loads(line) for line in values['events'].decode('utf-8').splitlines()], required)
    return dict(prior_failed_candidate=refs, qualification_kind='SOURCE_PUBLICATION_PREFLIGHT',
        candidate_full_status='FAILED', final_acceptance='PENDING',
        native_case_status='FAILED_EXACT_DENIAL_MISMATCH', native_denial_actual_winerror=2,
        native_denial_required_winerror=267, native_owner_proof_available=False,
        prior_terminal_error='TypeError', prior_fallback_tests_run=0,
        ordered_case_evidence=case_summary, captured_sqlite_and_stream_resources_closed=True,
        bounded_native_fixture_resources_closed=True, outer_owned_runner_retired=True,
        Source_accepted=False)


def require_candidate_readiness(reference, *, source='before'):
    path, value = j.proof(reference)
    assert path == j.R / 'SOURCE-PUBLICATION-PREFLIGHT.json'
    assert type(value['exit_status']) is int and value['exit_status'] == 0
    assert value['executor'] == '/root' and value['manifest_sha256'] == j.s.sha(j.Q / 'TRANSFER-MANIFEST.json')
    assert value['amendment'] == j.exact_ref(j.R / 'AMENDMENT.json') and value['reviewed_scripts'] == j.scripts()
    assert value['Source_publication'] is False and value['current_source_phase'] == 'before'
    expected = check_prior_failed_candidate()
    assert all(value[key] == item for key, item in expected.items())
    assert value['expected_payload_hashes'] == j.manifest()['expected_payload_hashes']
    assert value['Source_before_map_sha256'] == j.manifest()['Source_before_map_sha256']
    j.require_release(j.F / value['release']['repository_relative_path'], value['release']['sha256'], 'publication-preflight')
    j.verify(source=source)
    return value
