"""Finite engineering authorization and exact F4 runner amendment, not CETA authority."""
from dataclasses import dataclass
import ast
import hashlib
import json
from pathlib import Path
import re
import threading
import time

CASE = 'test_isolated_worker.NativeIsolatedWorkerTests.test_actual_nonpersistent_launch_denial_and_medium_control_retirement'
PARENT_RUNNER = '693d22abdceba34f057fbfa5b0a4a24f0a9efe91deb548f2325fdd1daaa4177d'
PARENT_COMPLETE = '6e0c1bdd649dd93857c8d14e86ae7f9f7faab2cf979b8b03e61ec732eb1bb1b0'
PARENT_MANIFEST = '98b49f825ab4f5d8b23ed980b93dd3c90a82be1869a93e034047f0fafcffb8bb'
MAX_RECORD_BYTES = 65536
MAX_WINDOW_NS = 1_800_000_000_000
MAX_INT = 2**63 - 1
LEGACY_LIMIT = "Original assertRaisesRegex suffix ':2' also matches ':267'; its PASS alone does not prove exact WinError2 or a missing-profile cause."


class GateError(ValueError):
    pass


def require(value, code):
    if value is not True:
        raise GateError(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'DUPLICATE_RECORD_KEY')
        result[key] = value
    return result


def decode_document(raw, limit):
    require(type(limit) is int and 0 < limit <= 16*1024*1024, 'DOCUMENT_BOUND')
    require(type(raw) is bytes and 0 < len(raw) <= limit, 'RECORD_SIZE')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                           parse_float=lambda _: (_ for _ in ()).throw(GateError('FLOAT_FORBIDDEN')),
                           parse_constant=lambda _: (_ for _ in ()).throw(GateError('NONFINITE_FORBIDDEN')))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise GateError('RECORD_ENCODING') from error
    require(type(value) is dict, 'RECORD_OBJECT')
    return value


def decode_record(raw):
    return decode_document(raw, MAX_RECORD_BYTES)


def exact_equal(left, right):
    return canonical(left) == canonical(right)


def validate_record(raw, expected_sha256, context, now_ns):
    require(type(expected_sha256) is str and re.fullmatch('[0-9a-f]{64}', expected_sha256) is not None, 'RECORD_PIN')
    require(digest(raw) == expected_sha256, 'RECORD_HASH_MISMATCH')
    record = decode_record(raw)
    keys = {'schema_version', 'kind', 'source', 'human_reply', 'run_nonce', 'issued_at_ns', 'expires_at_ns',
            'subject', 'execute_exact_original_case', 'create_profiles', 'expected_denial_winerror'}
    require(set(record) == keys, 'RECORD_KEYS')
    require(type(record['schema_version']) is int and record['schema_version'] == 1, 'RECORD_VERSION')
    require(record['kind'] == 'F4_ENGINEERING_ORIGINAL_NO_PROFILE_CASE_V1' and type(record['kind']) is str, 'RECORD_KIND')
    require(record['source'] == 'actual_current_human_reply' and type(record['source']) is str, 'HUMAN_ORIGIN_REQUIRED')
    require(type(record['human_reply']) is str and 0 < len(record['human_reply'].strip()) <= 4096, 'HUMAN_REPLY_REQUIRED')
    require(type(record['run_nonce']) is str and re.fullmatch('[0-9a-f]{32}', record['run_nonce']) is not None, 'RUN_NONCE')
    require(record['execute_exact_original_case'] is True and record['create_profiles'] is False, 'EXACT_CASE_NO_PROFILE_AUTHORITY')
    for name in ('issued_at_ns', 'expires_at_ns'):
        require(type(record[name]) is int and 0 < record[name] <= MAX_INT, 'RECORD_TIME_DOMAIN')
    require(type(now_ns) is int and 0 < now_ns <= MAX_INT, 'HOST_TIME_DOMAIN')
    require(0 < record['expires_at_ns'] - record['issued_at_ns'] <= MAX_WINDOW_NS, 'AUTHORIZATION_WINDOW')
    require(record['issued_at_ns'] <= now_ns < record['expires_at_ns'], 'AUTHORIZATION_NOT_CURRENT')
    require(type(record['expected_denial_winerror']) is int and 0 < record['expected_denial_winerror'] <= 65535, 'EXACT_DENIAL_REQUIRED')
    require(type(record['subject']) is dict and exact_equal(record['subject'], context), 'EXACT_RUN_SUBJECT_REQUIRED')
    require(context['original_case_id'] == CASE and context['run_nonce'] == record['run_nonce'], 'EXACT_CASE_NONCE_REQUIRED')
    return record


def select_ids(full_ids, *, authorized, partial):
    require(type(authorized) is bool and type(partial) is bool, 'SELECTION_FLAGS')
    require(type(full_ids) is list and all(type(name) is str for name in full_ids), 'TEST_IDS')
    require(len(full_ids) == len(set(full_ids)) and full_ids.count(CASE) == 1, 'EXACT_ORIGINAL_METHOD_REQUIRED')
    if authorized:
        require(not partial, 'AUTHORIZED_PARTIAL_CONFLICT')
        return full_ids.copy(), []
    require(partial, 'EXPLICIT_OPERATOR_AUTHORIZATION_REQUIRED')
    return [name for name in full_ids if name != CASE], [CASE]


@dataclass(frozen=True)
class ApprovalCapture:
    raw: bytes
    sha256: str
    native_identity: dict
    path: str


class ExecutionGate:
    """One local command/one original test/one native attempt; no refund/retry."""
    def __init__(self, capture, context, *, snapshot, write_new, root, now=time.time_ns, monotonic=time.perf_counter_ns):
        self.capture = capture
        self.context = json.loads(canonical(context))
        self.snapshot, self.write_new, self.root = snapshot, write_new, Path(root)
        self.now, self.monotonic = now, monotonic
        self._lock = threading.RLock()
        self._started = self._entered = self._attempted = False
        self._last_wall = self._last_mono = None
        self._diagnostic_failure = None
        self.native_calls = []
        self.record = validate_record(capture.raw, capture.sha256, self.context, now())
        self._authorization_duration = None

    def _current(self):
        observed = self.snapshot()
        require(exact_equal(observed, self.context), 'CURRENT_SOURCE_ENVIRONMENT_TOOL_DRIFT')
        wall, mono = self.now(), self.monotonic()
        require(type(mono) is int and mono >= 0, 'MONOTONIC_UNAVAILABLE')
        require(self._last_wall is None or wall >= self._last_wall, 'HOST_WALL_ROLLBACK')
        require(self._last_mono is None or mono >= self._last_mono, 'MONOTONIC_ROLLBACK')
        if self._started:
            require(mono - self._start_mono < self._authorization_duration, 'ELAPSED_AUTHORIZATION_EXPIRED')
        validate_record(self.capture.raw, self.capture.sha256, self.context, wall)
        self._last_wall, self._last_mono = wall, mono
        return wall, mono

    def start(self):
        with self._lock:
            require(not self._started, 'AUTHORIZATION_ALREADY_STARTED')
            wall, mono = self._current()
            # Two independent create-only identities: copying the same approval
            # or choosing the same nonce never produces another admission.
            self.write_new(self.root/'consumed-authorizations'/(self.capture.sha256+'.json'),
                {'schema_version':1, 'authorization_sha256':self.capture.sha256, 'run_nonce':self.context['run_nonce'],
                 'started_at_ns':wall, 'subject':self.context, 'approval_native_identity':self.capture.native_identity})
            self.write_new(self.root/'consumed-nonces'/(self.context['run_nonce']+'.json'),
                {'authorization_sha256':self.capture.sha256, 'subject':self.context})
            self._start_mono = mono
            self._authorization_duration = self.record['expires_at_ns'] - wall
            self._started = True

    def enter(self, test_id):
        with self._lock:
            require(test_id == CASE and self._started and not self._entered, 'ORIGINAL_CASE_ADMISSION')
            self._current()
            self._entered = True

    def wrap_native_create(self, operation, get_error, set_error):
        def guarded(*args, **kwargs):
            with self._lock:
                require(self._entered and not self._attempted, 'NATIVE_CASE_SINGLE_ATTEMPT')
                self._current()
                # Reserve diagnostic storage before the irreversible call. A
                # later diagnostic failure must not hide the native return and
                # prevent the canonical launcher from retaining its handles.
                row = {'returned':False, 'succeeded':None, 'winerror':None}
                self.native_calls.append(row)
                self._attempted = True
            response = operation(*args, **kwargs)
            error = get_error()
            try:
                row.update(returned=True, succeeded=bool(response), winerror=error)
            except BaseException as diagnostic:
                self._diagnostic_failure = diagnostic
            finally:
                set_error(error)
            return response
        return guarded

    def finish(self):
        with self._lock:
            self._current()
            require(self._started and self._entered and self._attempted, 'ORIGINAL_CASE_NOT_EXECUTED')
            require(self._diagnostic_failure is None, 'NATIVE_DIAGNOSTIC_UNAVAILABLE')
            require(len(self.native_calls) == 1, 'EXACT_ONE_NATIVE_ATTEMPT')
            row = self.native_calls[0]
            require(row['returned'] is True and row['succeeded'] is False and
                    type(row['winerror']) is int and row['winerror'] == self.record['expected_denial_winerror'],
                    'EXACT_NATIVE_DENIAL_NOT_OBSERVED')
            return {'authorization_sha256':self.capture.sha256, 'run_nonce':self.context['run_nonce'],
                    'original_case_id':CASE, 'actual_native_call':dict(row), 'expected_winerror':self.record['expected_denial_winerror'],
                    'precise_denial_matched':True, 'legacy_method_unchanged':True, 'legacy_regex_limitation':LEGACY_LIMIT,
                    'single_use_markers_root':str(self.root), 'host_wall_assumption':'Trusted local operator host time; no external UTC attestation.'}


def _replace_once(text, old, new):
    require(text.count(old) == 1, 'PARENT_AMENDMENT_ANCHOR')
    return text.replace(old, new)


def amend_runner(raw):
    require(digest(raw) == PARENT_RUNNER, 'EXACT_F4_RUNNER_REQUIRED')
    text = raw.decode('utf-8')
    text = _replace_once(text, "outroot=R/('tests-'+label);outroot.mkdir(exist_ok=False)",
                         'outroot=__gate_output;outroot.mkdir(exist_ok=False)')
    old = "authorization_path=R/'NATIVE-EXECUTION-AUTHORIZATION.json';native_authorization=None\nassert not authorization_path.exists(), 'This private candidate job has no restricted-worker operator authorization'\ndeferred_ids=[] if native_authorization else [name for name in full_expected_ids if name==deferred_case]"
    new = "authorization_path=__gate_authorization_path;native_authorization=__gate_authorization\n__gate_selected,deferred_ids=__gate_select(full_expected_ids,authorized=native_authorization is not None,partial=__gate_partial)"
    text = _replace_once(text, old, new)
    text = _replace_once(text, "if mode=='targeted':assert set(cohort_inputs['required_parent_ids'])==set(expected_ids) and len(expected_ids)==1294",
        "if mode=='targeted':assert set(cohort_inputs['required_parent_ids'])|({deferred_case} if native_authorization else set())==set(expected_ids) and len(expected_ids)==1294+(1 if native_authorization else 0)")
    text = _replace_once(text, '        active_case_id=test.id();executed.append(test.id());super().startTest(test)',
        '        active_case_id=test.id()\n        if active_case_id==deferred_case:__execution_gate.enter(active_case_id)\n        executed.append(test.id());super().startTest(test)')
    text = _replace_once(text, '        self.CreateProcessW=denied\n    for operation',
        '        self.CreateProcessW=denied\n    else:\n        self.CreateProcessW=__execution_gate.wrap_native_create(self.CreateProcessW,C.get_last_error,C.set_last_error)\n    for operation')
    text = _replace_once(text, 'proof=normalize(proof)',
        "proof=normalize(proof)\nproof['engineering_gate_status']='COMPLETE_TEST_RUN' if not deferred_ids else 'PARTIAL_NOT_ACCEPTED'\nproof['operator_gate_provenance']=__gate_provenance\nproof['precise_original_denial']=None if __execution_gate is None else __execution_gate.finish()\nproof['Source_acceptance']=False\nproof['F4_metadata109_unwaived']=True")
    compile(text, '<pinned-F4-runner-successor>', 'exec')
    return text


def require_full_result(value, required_ids, provenance):
    require(type(value) is dict and len(required_ids) == 2053 and len(set(required_ids)) == 2053, 'FULL2053_REQUIRED')
    require(value['exit_status'] == 0 and type(value['exit_status']) is int, 'RUN_NOT_PASSED')
    require(all(type(value[key]) is int and value[key] == 0 for key in ('failures','errors','skips')), 'FAILING_FULL_GATE')
    require(value['mandatory_full_gate_complete'] is True and value['deferred_ids'] == [], 'DEFERRED_FULL_GATE')
    require(value['full_expected_ids'] == value['expected_ids'] == value['executed_ids'] == value['stopped_ids'] == required_ids, 'EXACT_FULL_ID_SEQUENCE')
    require(type(value['tests_run']) is int and value['tests_run'] == 2053, 'FULL_TEST_COUNT')
    require(value['engineering_gate_status'] == 'COMPLETE_TEST_RUN' and exact_equal(value['operator_gate_provenance'], provenance), 'SUCCESSOR_PROVENANCE')
    denial = value['precise_original_denial']
    require(type(denial) is dict and denial['precise_denial_matched'] is True and denial['original_case_id'] == CASE, 'PRECISE_DENIAL_GATE')
    require(denial['authorization_sha256'] == provenance['authorization_sha256'] and denial['run_nonce'] == provenance['run_nonce'], 'APPROVAL_RESULT_BINDING')
    require(value['F4_metadata109_unwaived'] is True and value['Source_acceptance'] is False, 'UNRESOLVED_BOUNDARY_RETAINED')
    return value


def amend_completion(raw):
    require(digest(raw) == PARENT_COMPLETE, 'EXACT_F4_COMPLETION_REQUIRED')
    text = raw.decode('utf-8')
    text = _replace_once(text, "    assert approved['result']['reviewed_scripts']['complete_source.py']==sha(Path(__file__))",
        "    assert approved['result']['reviewed_scripts']['complete_source.py']==sha(R/'complete_source.py')\n    assert __successor_delivery_verified is True")
    text = _replace_once(text, "    full_path=R/'tests-source-r1/RESULT.json';full=read(full_path)",
        "    full_path=__successor_full_path;full=read(full_path)\n    __require_successor_result(full)")
    text = _replace_once(text, "      [{'command':str(PY)+' -B -X utf8 '+str(R/'run_joined.py')+' destination source-r1','exit_status':0}],",
        "      [{'command':__successor_actual_command,'exit_status':0}],")
    text = _replace_once(text, "    delivered_path=R/'independent-review/DELIVERED-REVIEW.json';delivered=read(delivered_path)",
        "    delivered_path=__successor_delivery_path;delivered=read(delivered_path)")
    # Keep the old run ledger/APPLIED/native-original references exact. Only
    # the new completion outputs and their own references move to this scope.
    text = text.replace("R/'ACCEPTED-SOURCE-BASELINE.json'", "__completion_runtime/'ACCEPTED-SOURCE-BASELINE.json'")
    text = _replace_once(text, "    write_new(R/'ACTUAL-ACCEPTANCE.json'", "    write_new(__completion_runtime/'ACTUAL-ACCEPTANCE.json'")
    text = _replace_once(text, "    write_new(__completion_runtime/'ACCEPTED-SOURCE-BASELINE.json',result)",
        "    result['successor_full_gate']=__successor_gate_bindings\n    result['whole_fixture_preservation_accepted']=False\n    result['metadata_issue_waived']=False\n    write_new(__completion_runtime/'ACCEPTED-SOURCE-BASELINE.json',result)")
    # All original full-suite, native closure, source/hash/native-original,
    # actual review, delivered review, and installed transition assertions stay.
    compile(text, '<pinned-F4-completion-successor>', 'exec')
    return text
