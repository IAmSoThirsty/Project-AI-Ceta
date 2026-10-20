"""Pure acceptance checks for captured Windows isolation observations.

These checks consume observations. They do not observe Windows, issue authority,
create resources, or establish isolation without the corresponding native run.
"""

ENVIRONMENT_KEYS = frozenset(('SystemRoot', 'WINDIR', 'PATH', 'TEMP', 'TMP', 'LOCALAPPDATA'))
PROCESS_RIGHTS = frozenset(('vm_write', 'create_thread', 'duplicate_handle', 'terminate', 'write_dac'))


class QualificationError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(value, code):
    if not value:
        raise QualificationError(code)


def _mapping(value, code):
    require(type(value) is dict, code)
    return value


def _integer(value, minimum, maximum, code):
    require(type(value) is int and minimum <= value <= maximum, code)
    return value


def _restriction(facts):
    restricted = facts.get('restricted')
    require(type(restricted) is bool, 'RESTRICTION_BOOLEAN_REQUIRED')
    raw = _integer(facts.get('restriction_raw_result'), -(1 << 31), (1 << 31) - 1,
                   'RESTRICTION_RAW_RESULT_REQUIRED')
    error = _integer(facts.get('restriction_last_error'), 0, 0xffffffff,
                     'RESTRICTION_LAST_ERROR_REQUIRED')
    count = _integer(facts.get('restricted_sid_count'), 0, 4095,
                     'RESTRICTING_SID_COUNT_REQUIRED')
    require(raw != 0 or error == 0, 'RESTRICTION_QUERY_UNAVAILABLE')
    require(restricted == bool(raw) == (count > 0), 'RESTRICTION_OBSERVATIONS_DISAGREE')
    return restricted, count


def assert_token_pair(parent, worker, expected_sid):
    """Require complete, typed, consistent observations of the same container.

    IsTokenRestricted describes the restricting SID list. A measured false with
    zero last error and an independently measured empty list is valid here.
    AppContainer identity, zero capabilities and low integrity remain required.
    Last error is only an error indicator when the native BOOL result is zero.
    """
    require(type(expected_sid) is str and expected_sid.startswith('S-1-15-2-'),
            'EXPECTED_APPCONTAINER_SID_REQUIRED')
    parent = _mapping(parent, 'PARENT_TOKEN_FACTS_REQUIRED')
    worker = _mapping(worker, 'WORKER_TOKEN_FACTS_REQUIRED')
    require(worker.get('schema') == 'ceta-isolation-token-v2', 'WORKER_TOKEN_SCHEMA_REQUIRED')
    require(type(parent.get('appcontainer_sid')) is str
            and type(worker.get('appcontainer_sid')) is str
            and parent['appcontainer_sid'] == worker['appcontainer_sid'] == expected_sid,
            'EXACT_APPCONTAINER_IDENTITY_REQUIRED')
    require(parent.get('is_appcontainer') is True
            and type(worker.get('is_appcontainer')) is int and worker['is_appcontainer'] == 1,
            'APPCONTAINER_OBSERVATION_REQUIRED')
    for facts in (parent, worker):
        _integer(facts.get('capability_count'), 0, 0, 'ZERO_CAPABILITY_OBSERVATION_REQUIRED')
    _integer(parent.get('integrity_rid'), 4096, 4096, 'LOW_INTEGRITY_OBSERVATION_REQUIRED')
    require(worker.get('integrity') == 'S-1-16-4096', 'LOW_INTEGRITY_OBSERVATION_REQUIRED')
    _integer(parent.get('observed_monotonic_ns'), 0, (1 << 63) - 1, 'TOKEN_OBSERVATION_TIME_REQUIRED')
    require(_restriction(parent) == _restriction(worker), 'PARENT_WORKER_RESTRICTION_DISAGREEMENT')


def _access(row, granted, code):
    require(_mapping(row, code).get('granted') is granted, code)


def assert_isolation(result, expected_sid):
    """Keep token consistency separate from the required real denial probes."""
    result = _mapping(result, 'NATIVE_PROBE_RESULT_REQUIRED')
    facts = _mapping(result.get('facts'), 'NATIVE_WORKER_FACTS_REQUIRED')
    _integer(result.get('worker_exit_code'), 0, 0, 'WORKER_EXIT_NOT_SUCCESSFUL')
    assert_token_pair(result.get('parent_token_facts'), facts.get('token'), expected_sid)
    for key in ('job_query', 'job_member'):
        _integer(facts.get(key), 1, 1, 'ACTUAL_JOB_MEMBERSHIP_REQUIRED')
    _access(facts.get('allowed_read'), True, 'ACTUAL_ASSET_READ_REQUIRED')
    _access(facts.get('scratch_write'), True, 'ACTUAL_SCRATCH_WRITE_REQUIRED')
    require(result.get('scratch_exists') is True, 'ACTUAL_SCRATCH_RESULT_REQUIRED')
    setup = _mapping(result.get('setup'), 'NATIVE_FIXTURE_SETUP_REQUIRED')
    before = _mapping(setup.get('protected_before'), 'PROTECTED_SENTINEL_BASELINE_REQUIRED')
    after = _mapping(result.get('protected_after'), 'PROTECTED_SENTINEL_RESULT_REQUIRED')
    require(len(before) == 5 and before == after, 'PROTECTED_SENTINEL_CONTENTS_CHANGED')
    for index in range(5):
        row = _mapping(facts.get('denied_file_' + str(index)), 'PROTECTED_SENTINEL_OBSERVATION_REQUIRED')
        for mode in ('read', 'write'):
            _access(row.get(mode), False, 'PROTECTED_SENTINELS_MUST_DENY')
    rights = _mapping(facts.get('process_rights'), 'PROCESS_RIGHTS_OBSERVATIONS_REQUIRED')
    require(set(rights) == PROCESS_RIGHTS, 'COMPLETE_PROCESS_RIGHTS_REQUIRED')
    target = _mapping(result.get('trusted_target'), 'OWNED_PROCESS_TARGET_REQUIRED')
    _integer(target.get('pid'), 1, 0xffffffff, 'OWNED_PROCESS_TARGET_IDENTITY_REQUIRED')
    _integer(target.get('creation_time'), 1, (1 << 64) - 1, 'OWNED_PROCESS_TARGET_IDENTITY_REQUIRED')
    require(target.get('alive_before_worker') is True and target.get('alive_after_worker') is True,
            'OWNED_PROCESS_TARGET_LIVENESS_REQUIRED')
    for row in rights.values():
        _access(row, False, 'PROCESS_RIGHTS_MUST_DENY')
        # A failed OpenProcess is not by itself an access refusal. In this
        # fixture every protected right must report ERROR_ACCESS_DENIED(5).
        _integer(row.get('error'), 5, 5, 'PROCESS_ACCESS_DENIED_ERROR_REQUIRED')
    event = _mapping(facts.get('hidden_event'), 'EXCLUDED_HANDLE_OBSERVATIONS_REQUIRED')
    for key in ('handle_query', 'signal'):
        _integer(event.get(key), 0, 0, 'EXCLUDED_HANDLE_MUST_DENY')
    _integer(result.get('excluded_event_wait'), 258, 258, 'EXCLUDED_HANDLE_MUST_DENY')
    for key in ('child', 'breakaway'):
        require(_mapping(facts.get(key), 'CHILD_OBSERVATIONS_REQUIRED').get('created') is False,
                'CHILD_CREATION_MUST_DENY')
    for key in ('tcp_connect', 'tcp_loopback_listen', 'tcp_wildcard_listen', 'udp_loopback'):
        _access(facts.get(key), False, 'NETWORK_MUST_DENY')
    environment = facts.get('environment_keys')
    require(type(environment) is list and all(type(key) is str for key in environment)
            and len(environment) == len(ENVIRONMENT_KEYS) and set(environment) == ENVIRONMENT_KEYS,
            'BOUNDED_ENVIRONMENT_REQUIRED')
