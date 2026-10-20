"""File-only independent verification of the single recorded AC7 attempt.

No production module, DLL, worker, profile, socket or database is loaded.
This validates retained observations, not the current Windows host state.
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

F = Path(r'T:\00-Active\Project-AI-CETA')
R = F / '.agents/runtime/ac7-token-contract-20261020'
Q = F / '.agents/ac7-token-contract-20261020'
D = F / '.agents/runtime/ac7-result-review-20261020'
A = R / 'q-6be3c32cb832461093c6d15dc9c538f8'
P = A / 'native-fixtures/ac1-ec4105bbf9af49028b30c90895b61e3d/native-profile-r2.json'
REVIEW = F / '.agents/runtime/ac7-qualification-review-20261020/R2/review.json'
SID = 'S-1-15-2-695244707-3853392321-2130098501-3319658173-178928504-1880712989-1319207162'
NAME = 'CETA.ProjectAICETA.IsolatedWorker.AC1.V1'
EXPECTED = {
    R/'OPERATOR-APPROVAL-AC7-20261020.json': '1664e04705da6ffcd9fd0bb4838811eb1890a41835737eb8667e6d292112cf01',
    R/'AC7-QUALIFICATION-MANIFEST-R4.json': '83967d7b5c00abc6461cdcb9bbe398bb63b0ab53078d8364f56f383de9b511cf',
    R/'CANDIDATE-BASELINE-R4.json': 'aa144f94637dfda5ef16e74ebd587f141630307f082da81375adbfad3a43f6ec',
    R/'PROFILE-CREATION-PROPOSAL-AC7-R4.json': 'ddb4382f6d2aa9e62d0d39a661c73730cd10e55201a0958542f0fd8829cc6071',
    Q/'tools/qualify_isolated_worker.py': '79da07922e6a7f56cca0ae9d90a2498c3d6f28a58dcb6bd3144ab56a87b5bd84',
    Q/'tools/run_one_isolation_qualification.py': 'f25ee11f38fae860ca2a21673c42c0591db62cef0937b0b57f9b6aa0eff871bd',
    Q/'tools/isolated_worker_token_oracle.py': '8f0791da2fa4879600a92f30617b79aeb3a271c89027b5a853ecb5853d5760d9',
    REVIEW: 'd90585db535e80d6d90b0d39a258bfe62504e6fbaa509048666b9ec49f7d4e01',
    R/'build-r2/isolated_worker.exe': '3df03778e1e2f6f707d38b0869e04e262926f2d4c375f1d3d10562d3456443cc',
}
prohibited_events = []
checks = []
inputs = {}

def audit(event, args):
    if (event.startswith(('ctypes.', 'subprocess.', 'socket.', 'sqlite3.', 'winreg.'))
            or event in ('os.system', 'os.startfile', 'os.exec', 'os.spawn', 'os.fork')):
        prohibited_events.append(event)
        raise RuntimeError('FORBIDDEN_OPERATION:' + event)
    if event == 'open':
        path, mode, flags = args
        write = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if write and (not isinstance(path, (str, bytes, os.PathLike))
                      or not Path(path).resolve().is_relative_to(D.resolve())):
            raise RuntimeError('OUT_OF_SCOPE_WRITE')
    if event in ('os.remove', 'os.rename', 'os.rmdir', 'os.mkdir', 'os.chmod', 'os.utime'):
        path = args[0]
        if not Path(path).resolve().is_relative_to(D.resolve()):
            raise RuntimeError('OUT_OF_SCOPE_MUTATION')

sys.addaudithook(audit)
started = datetime.now(timezone.utc).isoformat()

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def retain(path):
    digest = sha(path)
    key = str(path)
    if key in inputs:
        assert inputs[key] == digest, 'INPUT_CHANGED_DURING_REVIEW:' + key
    inputs[key] = digest
    return digest

def load(path):
    retain(path)
    return json.loads(path.read_text(encoding='utf-8'))

def check(name, condition, detail=None):
    if not condition:
        raise AssertionError(name)
    row = {'check': name, 'result': 'PASS'}
    if detail is not None:
        row['detail'] = detail
    checks.append(row)

def at(value):
    return datetime.fromisoformat(value)

try:
    for path, digest in EXPECTED.items():
        check('EXACT_PIN:' + str(path.relative_to(F)), retain(path) == digest)
    manifest = load(R/'AC7-QUALIFICATION-MANIFEST-R4.json')
    check('CANDIDATE357_FROZEN', len(manifest['payload_hashes']) == 357 and all(
        retain(Q/rel) == digest for rel, digest in manifest['payload_hashes'].items()))
    for rel, digest in manifest['evidence'].items():
        check('REVIEW_PACKET:' + rel, retain(R/rel) == digest)
    approval = load(R/'OPERATOR-APPROVAL-AC7-20261020.json')
    review = load(REVIEW)
    check('EXACT_RECORDED_HUMAN_REPLY', approval['source'] == 'actual_current_human_reply'
          and approval['human_reply'] == 'Authorize this exact AC7 attempt and own-profile cleanup')
    check('EXACT_PROFILE_APPROVAL', approval['profile_name'] == NAME and approval['profile_sid'] == SID)
    for field, path in [('proposal_sha256', R/'PROFILE-CREATION-PROPOSAL-AC7-R4.json'),
                        ('prepared_script_sha256', Q/'tools/qualify_isolated_worker.py'),
                        ('wrapper_sha256', Q/'tools/run_one_isolation_qualification.py'),
                        ('independent_review_sha256', REVIEW)]:
        check('APPROVAL_PACKET:' + field, approval[field] == retain(path))
    check('PREPARATION_REVIEW_IS_NOT_HOST_APPROVAL', review['decision'] == 'approved'
          and review['host_execution_approved'] is False and review['human_approval_issued'] is False)
    check('EXACT_ONE_ATTEMPT_LIMITS', all(type(approval[k]) is int and approval[k] == 1 for k in
          ('profile_attempt_limit', 'restricted_worker_limit', 'ordinary_control_limit'))
          and approval['automatic_retry'] is False and approval['post_cleanup_regression'] is False)
    marker = load(R/'ONE-ATTEMPT-STARTED.json')
    claim = load(R/'EXECUTION-CLAIM.json')
    command = load(R/'AUTHORIZED-AC7-COMMAND.json')
    terminal = load(R/'AUTHORIZED-AC7-TERMINAL.json')
    inner = load(R/'APPROVED-QUALIFICATION.json')
    ah = retain(R/'OPERATOR-APPROVAL-AC7-20261020.json')
    th = retain(Q/'tools/qualify_isolated_worker.py')
    rh = retain(REVIEW)
    check('MARKER_AND_EXECUTION_CLAIM_BINDINGS', marker['actual_approval_sha256'] == ah
          and claim['approval_sha256'] == ah
          and all(row['tool_sha256'] == th and row['review_sha256'] == rh
                  and row['automatic_retry'] is False for row in (marker, claim, command, inner))
          and marker['review_verified_and_decoded_payload_identical'] is True)
    e3 = str(F/'.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe')
    expected_outer = [e3, '-B', '-X', 'utf8', str(Q/'tools/run_one_isolation_qualification.py'),
                      str(R/'OPERATOR-APPROVAL-AC7-20261020.json'), ah, str(REVIEW), rh]
    expected_inner = [e3, '-B', '-X', 'utf8', str(Q/'tools/qualify_isolated_worker.py'),
                      '--mode', 'qualify', '--approval-receipt',
                      str(R/'OPERATOR-APPROVAL-AC7-20261020.json'), '--approval-sha256', ah]
    check('EXACT_OUTER_AND_INNER_COMMANDS', command['argv'] == terminal['argv'] == expected_outer
          and inner['command_argv'] == expected_inner and command['cwd'] == str(F))
    for name, metadata in [('AUTHORIZED-AC7', terminal), ('APPROVED-QUALIFICATION', inner)]:
        check(name + ':TERMINAL_FAILURE_AND_LOG_HASHES', metadata['exit_status'] == 1
              and metadata['stdout_sha256'] == retain(R/(name+'.stdout'))
              and metadata['stderr_sha256'] == retain(R/(name+'.stderr')))
    check('ONE_RECORDED_QDIRECTORY_AND_NO_REPEAT', sorted(p.name for p in R.glob('q-*') if p.is_dir()) == [A.name]
          and terminal['attempt_repeated'] is False and terminal['automatic_retry'] is False)
    baseline = load(R/'CANDIDATE-BASELINE-R4.json')
    for prefix, root, marker_key in [('SOURCE', F, 'Source352'), ('CANDIDATE', Q, 'candidate352')]:
        before = load(A/(prefix+'-BEFORE.json'))
        after = load(A/(prefix+'-AFTER.json'))
        check(prefix + ':352_HASH_AND_NATIVE_IDENTITY_MAPS_CONSERVED', len(before) == len(after) == 352
              and before == after == marker[marker_key])
        check(prefix + ':CURRENT352_FILE_HASHES_MATCH_RETAINED_CUT', all(
            retain(root/rel) == info['sha256'] for rel, info in after.items()))
        if prefix == 'CANDIDATE':
            check('CANDIDATE_BASELINE_MAP_EXACT', before == baseline['candidate352'])
    probe = load(P)
    result = load(A/'RESULT.json')
    retirement = load(A/'RETIREMENT.json')
    before_profile = load(A/'BEFORE.json')
    create_intent = load(A/'CREATE-INTENT.json')
    create_return = load(A/'CREATE-RETURN.json')
    created = load(A/'CREATED.json')
    delete_intent = load(A/'DELETE-INTENT.json')
    deleted = load(A/'DELETE-RETURN.json')
    post = load(A/'POST-DELETE-OBSERVATION.json')
    state = load(A/'PROFILE-STATE.json')
    binding = load(A/'PROBE-BINDING.json')
    check('RECORDED_PREFLIGHT_ABSENCE', before_profile['prior_folder']['HRESULT'] == -2147024894
          and before_profile['prior_folder']['path'] is None
          and marker['profile_before']['prior_folder']['HRESULT'] == -2147024894
          and marker['profile_before']['prior_folder']['path'] is None)
    check('CREATED_OWN_EXACT_PROFILE_WITH_ZERO_CAPABILITIES', create_return['HRESULT'] == 0
          and create_return['created_this_run'] is True and create_return['unknown_output_pointer'] is False
          and create_return['returned_sid_pointer'] > 0 and created['actual_SID'] == SID
          and created['name'] == NAME and created['capabilities'] == []
          and created['approval_sha256'] == create_intent['approval_sha256'] == ah)
    check('DELETE_INTENT_BINDS_CREATED_AND_RETIREMENT_RECEIPTS',
          delete_intent['created_this_run_receipt_sha256'] == retain(A/'CREATED.json')
          and delete_intent['retirement_receipt_sha256'] == retain(A/'RETIREMENT.json')
          and delete_intent['name'] == NAME and delete_intent['SID'] == SID)
    expected_tokens = {'appcontainer_sid': SID, 'is_appcontainer': True, 'capability_count': 0,
                       'integrity_rid': 4096, 'restricted': False, 'restricted_sid_count': 0,
                       'restriction_last_error': 0, 'restriction_raw_result': 0}
    check('ACTUAL_PARENT_TOKEN_RECEIPT_TYPED_VALUES', all(
        type(probe['parent_token_facts'][k]) is type(v) and probe['parent_token_facts'][k] == v
        for k, v in expected_tokens.items()) and probe['parent_token_facts']['observed_monotonic_ns'] > 0)
    check('ACTUAL_WORKER_EXIT_FAILURE_WITHOUT_USABLE_FACTS', type(probe['worker_exit_code']) is int
          and probe['worker_exit_code'] == 0xC0000142 and probe['facts'] is None and probe['stderr'] == '')
    check('FAIL_CLOSED_OUTCOME_REMAINS_REJECTED', result['primary_failure'] == {
        'type': 'QualificationError', 'text': 'NATIVE_WORKER_FACTS_REQUIRED'}
          and result['positive_isolation_qualified'] is False
          and result['Source_application'] is False and result['canonical_real_effect_accepted'] is False
          and result['journal_errors'] == [] and result['failures'] == [dict(stage='PROBE_IN_FLIGHT',
              type='QualificationError', text='NATIVE_WORKER_FACTS_REQUIRED')])
    target, worker = probe['trusted_target'], probe['worker_identity']
    check('ORDINARY_CONTROL_ACTUALLY_RECORDED_LIVE_BOTH_BRACKETS', target['pid'] == 21160
          and target['creation_time'] == 134369624980284103 and target['integrity'] == 'S-1-16-8192'
          and target['alive_before_worker'] is True and target['alive_after_worker'] is True)
    check('EXACT_WORKER_IDENTITY', worker['pid'] == 26536
          and worker['creation_time'] == 134369624986270138)
    by_pid = {row['pid']: row for row in probe['cleanup']}
    check('BOTH_RECORDED_PROCESS_LIFETIMES_CLEAN', len(by_pid) == len(probe['cleanup']) == 2
          and all(row['active_processes'] == 0 and row['lifetime_closed'] is True
                  and 'cleanup_failure' not in row and 'native_handle_cleanup_failure' not in row
                  for row in probe['cleanup'])
          and by_pid[worker['pid']]['creation_time'] == worker['creation_time']
          and by_pid[target['pid']]['creation_time'] == target['creation_time']
          and by_pid[worker['pid']]['exit_code'] == probe['worker_exit_code']
          and by_pid[target['pid']]['exit_code'] == 125)
    check('CUSTODY_ROWS_BIND_HELPER_IDENTITIES_AND_ALL_HANDLE_STATES', len(retirement['custody']) == 2
          and all(row['creation_time'] == by_pid[row['pid']]['creation_time']
                  and all(row[k] is True for k in ('lifetime_closed', 'job_closed', 'process_closed', 'thread_closed'))
                  for row in retirement['custody']))
    check('NO_RECORDED_PENDING_NATIVE_RESOURCES', len(retirement['pending_native_resources']) == 23
          and all(type(row) is list and row == [] for row in retirement['pending_native_resources'])
          and retirement['unknown_create_output_pointer'] is None
          and all(retirement[k] is True for k in ('helper_started', 'helper_retirement_recorded',
                                                'control_cleanup_clear', 'all_captured_resources_retired'))
          and all(result['retirement'][k] == v for k, v in retirement.items())
          and result['retirement']['post_delete_API_resources'] == [[] for _ in range(23)]
          and result['retirement']['all_captured_resources_retired_after_final_observation'] is True)
    check('RECORDED_OWN_PROFILE_DELETE_AND_FOLDER_ABSENCE', deleted['HRESULT'] == post['native_delete_HRESULT'] == 0
          and post['folder_observation']['HRESULT'] == -2147024894
          and post['folder_observation']['path'] is None
          and post['recursive_delete_executed'] is False and post['registry_or_perfect_erasure_claim'] is False
          and result['profile_cleanup_status'] == post['cleanup_status'] == state['cleanup_status']
              == 'DELETE_SUCCEEDED_AND_FOLDER_ABSENCE_OBSERVED'
          and state['state_after_exception_requires_operator_inspection'] is False)
    ordered = [approval['recorded_at'], command['at'], terminal['started_at'], marker['at'],
               inner['started_at'], claim['at'], before_profile['observed_at'], create_intent['at'],
               create_return['at'], created['at'], probe['started_at'], probe['finished_at'],
               retirement['at'], delete_intent['at'], deleted['at'], post['at'], state['at'],
               result['at'], inner['finished_at'], terminal['finished_at']]
    check('RECORDED_TIMESTAMP_ORDER', all(at(a) <= at(b) for a, b in zip(ordered, ordered[1:])), ordered)
    image_hash = EXPECTED[R/'build-r2/isolated_worker.exe']
    for path in (A/'build-r2/isolated_worker.exe', P.parent/'assets/isolated_worker.exe'):
        check('EXECUTED_IMAGE_COPY:' + str(path.relative_to(R)), retain(path) == image_hash)
    check('IMAGE_RECEIPT_BINDINGS', probe['image_hash'] == worker['image_sha256'] == binding['binary_sha256']
          == binding['image_copy']['sha256'] == image_hash)
    check('CAPTURED_DRIVER_AND_SUPPORT_HASHES', retain(A/'native_fixture_support.py') == binding['driver_copy']['sha256']
          == '251d0d93ef2e261d257c6622d2d18034d71ec329a345c536f69283a15458d6df'
          and retain(A/'ac3_support.py') == binding['support_copy']['sha256'])
    for rel, info in binding['captured_dependencies'].items():
        check('CAPTURED_DEPENDENCY:' + rel, retain(F/rel) == info['sha256'])
    check('RECORDED_SENTINELS_PRESERVED_WITH_NO_SCRATCH_EFFECT', len(probe['setup']['protected_before']) == 5
          and probe['setup']['protected_before'] == probe['protected_after']
          and probe['scratch_exists'] is False and probe['excluded_event_wait'] == 258)
    check('SOURCE_AND_CANDIDATE_CONSERVATION_REPORTED', result['Source352_native_and_hash_conserved'] is True
          and result['candidate352_native_and_hash_conserved'] is True)
    for line in (R/'APPROVED-QUALIFICATION.stdout').read_text(encoding='utf-8').splitlines():
        if line.startswith('{'):
            stdout_row = json.loads(line)
            if 'primary_failure' in stdout_row:
                check('STDOUT_AND_STORED_RESULT_SEMANTICALLY_AGREE',
                      {k:v for k,v in stdout_row.items() if k != 'at'} == {k:v for k,v in result.items() if k != 'at'})
                break
    else:
        raise AssertionError('MISSING_FINAL_STDOUT_SNAPSHOT')
    check('ALL_READ_INPUTS_STABLE', all(sha(Path(path)) == digest for path, digest in inputs.items()))
    check('NO_PROHIBITED_OPERATION_ATTEMPT', prohibited_events == [])
    outcome = {'schema': 'ceta-ac7-recorded-attempt-readonly-review-v1', 'status': 'PASS',
               'reviewer': '/root/recovery_join_review20', 'started_at': started,
               'finished_at': datetime.now(timezone.utc).isoformat(), 'checks': checks,
               'check_count': len(checks), 'read_input_count': len(inputs), 'inputs_sha256': inputs,
               'prohibited_events': prohibited_events, 'native_execution_performed_by_reviewer': False,
               'qualification_interpretation': 'FAILED; no positive isolation or real-effect acceptance',
               'cleanup_interpretation': 'Retained tool/helper observations report closed owned lifetimes and own-profile deletion followed by folder absence; no fresh host scan',
               'worker_exit_code': probe['worker_exit_code'], 'worker_exit_hex': hex(probe['worker_exit_code']),
               'ordinary_control_pid': target['pid'], 'restricted_worker_pid': worker['pid'],
               'outer_command': expected_outer, 'inner_command': expected_inner}
except BaseException as error:
    outcome = {'status': 'FAIL', 'started_at': started, 'finished_at': datetime.now(timezone.utc).isoformat(),
               'error': {'type': type(error).__name__, 'text': str(error)}, 'checks': checks,
               'inputs_sha256': inputs, 'prohibited_events': prohibited_events}
    (D/'FILE-REVIEW-FAILURE.json').write_text(json.dumps(outcome, indent=2)+'\n', encoding='utf-8')
    raise
(D/'FILE-REVIEW-RESULT.json').write_text(json.dumps(outcome, indent=2)+'\n', encoding='utf-8')
print(json.dumps({k:v for k,v in outcome.items() if k not in ('checks', 'inputs_sha256', 'outer_command', 'inner_command')}))
