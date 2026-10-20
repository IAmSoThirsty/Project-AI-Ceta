"""FN6 seven-case engineering qualification inputs; no CETA imports on import."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import hashlib
import importlib.util
import json
import os
import stat
import sys

N = Path(__file__).resolve().parent
R = N.parent
F = R.parents[2]
Q = F / '.agents/fn6-20261015'
E3 = F / '.agents/source-assembly-20261014T021300Z/.agents/e3'
PY = E3 / 'Scripts/python.exe'
MANIFEST_PIN = '6bd87db98906075971ecde1bd07444d28b3a957ba017cef2836cde097737eb24'
REVIEW_PIN = 'bd66972d7883b50e9e49b46d1cbd76c8ab85283dd89f38d9172b5004daf5d669'  # Actual distinct FN6 approval; claims released.
CUSTODY_PIN = '715b88ab286a524f5815ec3c47b987ba82cc50709272fdc467b7ddc76eeba1b4'
P4_PIN = '2ccbca31973ead308e1cdcc6676bbd7371cdec29a0f16178f3f55a4ab4130618'
METHODS = tuple(sorted((
    'test_actual_kernel_retained_apply_then_separate_approved_restore',
    'test_actual_last_owner_stop_denies_every_native_set',
    'test_actual_set_then_primary_exception_burns_attempt_and_preserves_recovery',
    'test_actual_matching_threaded_stop_wins_last_owner_barrier_before_set',
    'test_actual_canonical_revocation_after_dispatch_keeps_effect_and_consumed_liability',
    'test_actual_set_with_hostile_exception_dictionary_retains_exact_change_and_primary',
    'test_actual_canonical_stop_during_capacity_keeps_prepared_permit_and_zero_set',
)))
IDS = tuple('test_cpu_execution_admission.NativeCpuExecutionAdmissionTests.' + name for name in METHODS)
SCRIPTS = ('readiness_support.py', 'resource_witness.py', 'run_native.py',
           'supervise_native.py', 'bounded_custody.py', 'prepare_inputs.py')
WAIT_SECONDS = 180
INPUTS_NAME = 'PREPARED-INPUTS.json'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def _pairs(pairs):
    result = {}
    for name, value in pairs:
        require(name not in result, 'DUPLICATE_JSON_KEY')
        result[name] = value
    return result


def decode(raw):
    return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(RuntimeError('NONFINITE_JSON')))


def reader():
    path = F / '.agents/pr4-20261014/preserve_ceta_complete.py'
    require(sha(path.read_bytes()) == P4_PIN, 'P4_PIN_MISMATCH')
    spec = importlib.util.spec_from_file_location('fn6_readiness_native_reader', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


fs = reader()


def ordinary(path):
    path = fs.safe_components(Path(path))
    before = fs.lstat(path)
    require(stat.S_ISREG(before.st_mode) and not fs.reparse(before), 'ORDINARY_FILE_REQUIRED')
    identity = fs.file_identity(before)
    count, digest, _ = fs.hash_file(path)
    require(count == identity['bytes'] and fs.file_identity(fs.lstat(path)) == identity,
            'ORDINARY_FILE_CHANGED')
    return dict(path=str(path), bytes=count, sha256=digest, native_identity=identity)


def pinned_bytes(path, expected):
    path = Path(path)
    before = ordinary(path)
    require(type(expected) is str and before['sha256'] == expected, 'PIN_MISMATCH:' + str(path))
    with fs.open_source(path, exclusive=True) as stream:
        descriptor = fs.file_identity(os.fstat(stream.fileno()))
        require(all(descriptor[k] == before['native_identity'][k]
                    for k in ('bytes', 'mtime_ns', 'device', 'inode', 'attributes')), 'DESCRIPTOR_MISMATCH')
        raw = stream.read()
        require(sha(raw) == expected and fs.file_identity(os.fstat(stream.fileno())) == descriptor,
                'PINNED_STREAM_CHANGED')
    require(ordinary(path) == before, 'PINNED_PATH_CHANGED')
    return raw, before


def pinned_json(path, expected):
    raw, facts = pinned_bytes(path, expected)
    return decode(raw), facts


def save(path, value):
    path = Path(path)
    require(path.is_relative_to(N), 'OUTPUT_OUTSIDE_READINESS')
    fs.safe_components(path.parent)
    fs.write_new(path, (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf8'))


def payload_snapshot(manifest):
    require(manifest['candidate_root'] == str(Q) and len(manifest['payloads']) == 352,
            'WRONG_FN6_CUT')
    actual = {name: ordinary(Q / name) for name in sorted(manifest['payloads'])}
    require(all(value == manifest['payloads'][name]['candidate'] for name, value in actual.items()),
            'FN6_PAYLOAD_NATIVE_DRIFT')
    return actual


def method_asts(raw):
    tree = ast.parse(raw)
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == 'NativeCpuExecutionAdmissionTests')
    nodes = {node.name: node for node in cls.body if isinstance(node, ast.FunctionDef)
             and node.name.startswith('test_')}
    require(set(nodes) == set(METHODS), 'ORIGINAL_SEVEN_METHODS_CHANGED')
    return {name: sha(ast.dump(nodes[name], include_attributes=False).encode('utf8')) for name in METHODS}


def preflight():
    require(Path(sys.executable) == PY and sys.flags.dont_write_bytecode and not sys.flags.optimize,
            'EXACT_E3_MINUS_B_REQUIRED')
    inputs_raw = (N / INPUTS_NAME).read_bytes()
    inputs, facts = pinned_json(N / INPUTS_NAME, sha(inputs_raw))
    require(inputs['schema_version'] == 1 and inputs['native_execution'] == 'NOT_RUN', 'WRONG_INPUT_KIND')
    for name in SCRIPTS:
        require(ordinary(N / name) == inputs['scripts'][name], 'SCRIPT_NATIVE_DRIFT:' + name)
    manifest, _ = pinned_json(Q / 'TRANSFER-MANIFEST.json', MANIFEST_PIN)
    candidate = payload_snapshot(manifest)
    require(candidate == inputs['candidate352'], 'CANDIDATE_NATIVE_DRIFT')
    environment = {name: ordinary(Path(row['path'])) for name, row in inputs['environment'].items()}
    require(environment == inputs['environment'], 'ENVIRONMENT_NATIVE_DRIFT')
    for row in inputs['proofs'].values():
        require(ordinary(Path(row['path'])) == row, 'COMPONENT_PROOF_DRIFT')
    method_pin = candidate['tests/contract/test_cpu_execution_admission.py']['sha256']
    raw, _ = pinned_bytes(Q / 'tests/contract/test_cpu_execution_admission.py', method_pin)
    require(method_asts(raw) == inputs['original_method_ast_sha256'], 'METHOD_AST_DRIFT')
    return inputs, facts


def validate_release(release, review, inputs, inputs_sha, now):
    """Operator engineering release data; never a CETA authority credential."""
    keys = {'schema_version', 'kind', 'executor', 'issued_at', 'expires_at', 'attempt_id',
            'inputs_sha256', 'scripts_sha256', 'candidate_manifest_sha256', 'test_ids',
            'environment_digest', 'output_root', 'child_wait_seconds', 'allowed_effects',
            'review_path', 'review_sha256'}
    require(type(release) is dict and set(release) == keys, 'EXACT_RELEASE_FIELDS_REQUIRED')
    require(type(release['schema_version']) is int and release['schema_version'] == 1,
            'RELEASE_SCHEMA_INVALID')
    require(release['kind'] == 'FN6_SEVEN_NATIVE_ENGINEERING' and type(release['kind']) is str
            and type(release['executor']) is str and release['executor'] == '/root', 'ROOT_RELEASE_REQUIRED')
    attempt = release['attempt_id']
    require(type(attempt) is str and len(attempt) == 32 and all(c in '0123456789abcdef' for c in attempt),
            'ATTEMPT_ID_REQUIRED')
    for field in ('issued_at', 'expires_at'):
        require(type(release[field]) is str, 'RELEASE_TIME_TYPE')
    start, end = (datetime.fromisoformat(release[k]) for k in ('issued_at', 'expires_at'))
    require(start.tzinfo is not None and end.tzinfo is not None and start <= now < end
            and 0 < (end - start).total_seconds() <= 900, 'RELEASE_STALE_OR_OVERLONG')
    require(release['inputs_sha256'] == inputs_sha
            and release['candidate_manifest_sha256'] == MANIFEST_PIN, 'RELEASE_INPUT_MISMATCH')
    require(type(release['scripts_sha256']) is dict and release['scripts_sha256'] ==
            {name: row['sha256'] for name, row in inputs['scripts'].items()}, 'RELEASE_SCRIPT_MISMATCH')
    require(type(release['test_ids']) is list and release['test_ids'] == list(IDS), 'RELEASE_METHOD_MISMATCH')
    require(release['environment_digest'] == sha(canonical(inputs['environment']).encode('utf8')),
            'RELEASE_ENVIRONMENT_MISMATCH')
    require(type(release['child_wait_seconds']) is int and release['child_wait_seconds'] == WAIT_SECONDS,
            'RELEASE_WAIT_INVALID')
    require(type(release['output_root']) is str and release['output_root'] == str(N / ('attempt-' + attempt)),
            'RELEASE_OUTPUT_MISMATCH')
    require(type(release['allowed_effects']) is list and release['allowed_effects'] ==
            ['OWNED_ORDINARY_WORKERS', 'CLASS9_JOB_SETUP', 'ORIGINAL_SEVEN_CLASS15_CASES',
             'DISPOSABLE_SQLITE', 'NATIVE_CLOCK_REGISTRATION', 'OWNED_EVENTS_THREADS'],
            'RELEASE_EFFECTS_MISMATCH')
    require(release['review_path'] == str(N / 'ROOT-REVIEW.json') and type(release['review_sha256']) is str
            and len(release['review_sha256']) == 64, 'REVIEW_PATH_INVALID')
    require(type(review) is dict and review.get('decision') == 'approved'
            and type(review.get('exit_status')) is int and review['exit_status'] == 0
            and review.get('reviewer') == '/root' and review.get('author') == '/root/pressure_writer'
            and review.get('inputs_sha256') == inputs_sha
            and review.get('scripts_sha256') == release['scripts_sha256'], 'EXACT_DISTINCT_REVIEW_REQUIRED')
    return N / ('attempt-' + attempt)


def release_record(inputs, facts, expected_sha=None):
    path = N / 'ROOT-NATIVE-RELEASE.json'
    require(path.is_file(), 'NO_ROOT_NATIVE_RELEASE')
    if expected_sha is None:
        expected_sha = ordinary(path)['sha256']
    release, native = pinned_json(path, expected_sha)
    require(type(release) is dict and release.get('review_path') == str(N / 'ROOT-REVIEW.json'),
            'REVIEW_PATH_INVALID')
    review, review_native = pinned_json(N / 'ROOT-REVIEW.json', release['review_sha256'])
    output = validate_release(release, review, inputs, facts['sha256'], datetime.now(timezone.utc))
    return release, native, review_native, output
