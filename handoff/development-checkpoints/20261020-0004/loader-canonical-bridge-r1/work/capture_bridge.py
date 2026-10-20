"""One fresh canonical fixture -> reviewed owned-caller capture.

Import and admission are data-only. The command has no implicit grant, fallback,
retry, profile adoption or native setup mode. NativePort is imported only after
the exact human provenance, independent reviews and live TAAR write lease pass.
"""
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import math
import os
import stat
import sys
import time

F = Path('T:/00-Active/Project-AI-CETA')
W = Path(__file__).resolve().parent
INPUTS = W / 'BRIDGE-INPUTS.json'
R5 = F / '.agents/runtime/operational-resume-20261020/loader-capture-r5/work'
CANONICAL_RUNTIME = F / '.agents/runtime/ac7-token-contract-20261020'
KIND = 'CETA_FRESH_CANONICAL_LOADER_BRIDGE_REQUEST_V1'
AUTHOR = '/root/review'
MAX_JSON = 2 * 1024 * 1024
EFFECTS = (
    'canonical_fixture_acl_and_sentinel_preparation',
    'create_exact_absent_zero_capability_profile',
    'owned_loopback_positive_control',
    'canonical_ordinary_hold_30000_target',
    'one_canonical_debug_only_child',
    'owned_debug_strings_and_exact_four_byte_loader_snaps',
    'retire_exact_owned_processes_and_handles_once',
    'delete_only_this_attempt_profile_after_proven_retirement',
)
_entered = False


class BridgeError(RuntimeError):
    pass


def require(value, reason):
    if not value:
        raise BridgeError(reason)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def strict_json(raw):
    require(type(raw) is bytes and len(raw) <= MAX_JSON, 'BRIDGE_JSON_BOUND')
    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, 'BRIDGE_DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    def constant(_):
        raise BridgeError('BRIDGE_NONFINITE_JSON')
    try:
        value = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise BridgeError('BRIDGE_INVALID_JSON') from error
    budget = [0]
    def bounded(item, depth=0):
        budget[0] += 1
        require(depth <= 32 and budget[0] <= 50000, 'BRIDGE_JSON_STRUCTURE_BOUND')
        if type(item) is dict:
            require(len(item) <= 10000, 'BRIDGE_JSON_ITEMS_BOUND')
            for key, child in item.items():
                require(type(key) is str and len(key) <= 32768, 'BRIDGE_JSON_KEY_BOUND')
                bounded(child, depth + 1)
        elif type(item) is list:
            require(len(item) <= 10000, 'BRIDGE_JSON_ITEMS_BOUND')
            for child in item:
                bounded(child, depth + 1)
        elif type(item) is str:
            require(len(item) <= 262144, 'BRIDGE_JSON_STRING_BOUND')
        elif type(item) is int:
            require(item.bit_length() <= 256, 'BRIDGE_JSON_INTEGER_BOUND')
        else:
            require(item is None or type(item) is bool or type(item) is float and math.isfinite(item),
                    'BRIDGE_JSON_SCALAR_INVALID')
    bounded(value)
    return value


def ordinary_path(path):
    path = Path(path)
    require(path.is_absolute() and path.is_relative_to(F), 'BRIDGE_REPOSITORY_PATH_REQUIRED')
    current = F
    for part in path.relative_to(F).parts:
        require(part not in ('', '.', '..') and ':' not in part, 'BRIDGE_PATH_COMPONENT_INVALID')
        current /= part
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        require(not getattr(info, 'st_file_attributes', 0) & 0x400 and not stat.S_ISLNK(info.st_mode),
                'BRIDGE_REPARSE_REFUSED')
    require(path.resolve().is_relative_to(F.resolve()), 'BRIDGE_PATH_ESCAPE')
    return path


def read_bytes(path, *, bound=MAX_JSON):
    path = ordinary_path(path)
    before = path.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_size <= bound, 'BRIDGE_FILE_BOUND')
    with path.open('rb') as stream:
        raw = stream.read(bound + 1)
    after = path.stat()
    keys = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns')
    require(all(getattr(before, key) == getattr(after, key) for key in keys)
            and len(raw) == before.st_size <= bound, 'BRIDGE_FILE_CHANGED_DURING_READ')
    return raw


def reference(path):
    path = ordinary_path(path)
    return dict(repository_relative_path=path.relative_to(F).as_posix(), sha256=digest(read_bytes(path)))


def reference_path(ref):
    require(type(ref) is dict and set(ref) == {'repository_relative_path', 'sha256'},
            'BRIDGE_REFERENCE_FIELDS')
    name, pin = ref['repository_relative_path'], ref['sha256']
    require(type(name) is str and '\\' not in name and ':' not in name
            and name == PurePosixPath(name).as_posix() and not name.startswith('/')
            and all(part not in ('', '.', '..') for part in name.split('/')),
            'BRIDGE_REFERENCE_PATH')
    require(type(pin) is str and len(pin) == 64 and all(c in '0123456789abcdef' for c in pin),
            'BRIDGE_REFERENCE_HASH')
    return ordinary_path(F / name)


def read_reference(ref):
    raw = read_bytes(reference_path(ref))
    require(digest(raw) == ref['sha256'], 'BRIDGE_REFERENCE_CHANGED')
    return strict_json(raw)


def file_sha(path, bound=256 * 1024 * 1024):
    """Read already-declared dependencies as bytes, never load their payloads."""
    path = Path(path)
    if path.is_relative_to(F):
        ordinary_path(path)
    else:
        require(path.parent == Path(os.environ.get('SystemRoot', 'C:/WINDOWS')) / 'System32',
                'BRIDGE_EXTERNAL_DEPENDENCY_PATH')
    before = path.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_size <= bound
            and not getattr(before, 'st_file_attributes', 0) & 0x400, 'BRIDGE_DEPENDENCY_BOUND')
    value, total = hashlib.sha256(), 0
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            total += len(block)
            require(total <= bound, 'BRIDGE_DEPENDENCY_GROWTH')
            value.update(block)
    after = path.stat()
    require(all(getattr(before, key) == getattr(after, key) for key in
                ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns')) and total == before.st_size,
            'BRIDGE_DEPENDENCY_CHANGED')
    return dict(path=str(path), bytes=total, sha256=value.hexdigest())


def verify_file(pin):
    require(type(pin) is dict and {'path', 'bytes', 'sha256'} <= set(pin), 'BRIDGE_FILE_PIN_REQUIRED')
    observed = file_sha(pin['path'])
    require(all(observed[key] == pin[key] for key in observed), 'BRIDGE_FILE_PIN_CHANGED')
    info = Path(pin['path']).stat()
    for key, field in (('device', 'st_dev'), ('inode', 'st_ino'), ('mtime_ns', 'st_mtime_ns')):
        if key in pin:
            require(pin[key] == getattr(info, field), 'BRIDGE_FILE_IDENTITY_CHANGED')
    return observed


def scope_paths(nonce):
    require(type(nonce) is str and len(nonce) == 32 and all(c in '0123456789abcdef' for c in nonce),
            'BRIDGE_NONCE_INVALID')
    directory = CANONICAL_RUNTIME / ('loader-bridge-' + nonce)
    release = R5 / ('bridge-release-' + nonce + '.json')
    capture = R5 / 'native-attempts' / ('capture-' + nonce)
    return dict(directory=directory, release=release, capture=capture)


def required_scopes(nonce):
    paths = scope_paths(nonce)
    names = [str(paths['directory']) + '/**', str(paths['release']),
             str(paths['capture'].parent), str(paths['capture']) + '/**']
    return sorted(Path(name[:-3]).relative_to(Path('T:/')).as_posix() + '/**'
                  if name.endswith('/**') else Path(name).relative_to(Path('T:/')).as_posix()
                  for name in names)


def scope_covers(scope, required):
    require(type(scope) is str and '\\' not in scope and ':' not in scope
            and not scope.startswith('/') and all(p not in ('', '.', '..') for p in scope.split('/')),
            'BRIDGE_LEASE_SCOPE_INVALID')
    if scope.endswith('/**'):
        base = scope[:-3]
        target = required[:-3] if required.endswith('/**') else required
        return target == base or target.startswith(base + '/')
    return scope == required


def validate_lease(lease, nonce, *, read_json=None):
    require(type(lease) is dict and set(lease) == {'control_root', 'run_id', 'node_id', 'executor_id',
            'input_hash', 'claimed_at', 'workspace'}, 'BRIDGE_LEASE_FIELDS')
    root = reference_path(dict(repository_relative_path=lease['control_root'], sha256='0' * 64))
    require(root.is_dir() and root.is_relative_to(F / '.agents/runtime'), 'BRIDGE_LEASE_ROOT')
    for field in ('run_id', 'node_id'):
        value = lease[field]
        require(type(value) is str and 0 < len(value) <= 128
                and all(c.isascii() and (c.isalnum() or c in '-_') for c in value), 'BRIDGE_LEASE_ID')
    require(lease['executor_id'] == '/root', 'BRIDGE_ROOT_EXECUTION_LEASE_REQUIRED')
    reader = read_json or (lambda p: strict_json(read_bytes(p)))
    control = root / lease['run_id']
    claims = reader(control / 'claims.json')
    state = reader(control / 'state.json')
    graph = reader(control / 'graph.json')['graph']
    claim = claims.get(lease['node_id'])
    require(type(claim) is dict and all(claim.get(key) == lease[key] for key in
            ('executor_id', 'input_hash', 'claimed_at', 'workspace')), 'BRIDGE_LIVE_LEASE_MISMATCH')
    node = state['nodes'][lease['node_id']]
    require(node['state'] == 'RUNNING', 'BRIDGE_LEASE_NOT_RUNNING')
    require(type(node.get('claim')) is dict and all(node['claim'].get(key) == claim.get(key)
            for key in ('executor_id', 'input_hash', 'claimed_at', 'workspace', 'effective_write_scope')),
            'BRIDGE_LEASE_STATE_DISAGREES')
    require(graph['nodes'][lease['node_id']]['access'] == 'write_scoped', 'BRIDGE_LEASE_WRITE_REQUIRED')
    scopes = claim.get('effective_write_scope')
    declared = graph['nodes'][lease['node_id']].get('write_scope')
    require(type(scopes) is list and type(declared) is list, 'BRIDGE_LEASE_SCOPE_REQUIRED')
    for needed in required_scopes(nonce):
        require(any(scope_covers(s, needed) for s in scopes)
                and any(scope_covers(s, needed) for s in declared), 'BRIDGE_REQUIRED_SCOPE_NOT_LEASED:' + needed)
    require(ordinary_path(Path(lease['workspace'])).is_dir(), 'BRIDGE_LEASE_WORKSPACE_REQUIRED')
    return dict(run_id=lease['run_id'], node_id=lease['node_id'], input_hash=lease['input_hash'],
                claimed_at=lease['claimed_at'], executor_id=lease['executor_id'], checked_scopes=required_scopes(nonce))


def review_matches(review, refs, author):
    require(type(review) is dict and type(review.get('schema_version')) is int and review['schema_version'] == 1
            and review.get('decision') == 'approved' and type(review.get('exit_status')) is int and review['exit_status'] == 0
            and type(review.get('executor_id')) is str and review['executor_id'] not in ('', author)
            and type(review.get('result')) is dict, 'BRIDGE_INDEPENDENT_REVIEW_REQUIRED')
    # Review result must name the exact artifact hashes, not just a nearby run.
    def contains(value, wanted):
        if type(value) is dict:
            return value == wanted or any(contains(v, wanted) for v in value.values())
        if type(value) is list:
            return any(contains(v, wanted) for v in value)
        return type(value) is str and value == wanted['sha256']
    require(all(contains(review['result'], ref) for ref in refs), 'BRIDGE_REVIEW_BINDING_MISMATCH')


def validate_authorizations(request, grant, human, action_review, source_review, symbol_review, now):
    """Pure deterministic checks. These records do not themselves issue consent."""
    required = {'schema_version', 'kind', 'repository', 'executor', 'nonce', 'issued_at_ns', 'expires_at_ns',
        'bridge_freeze', 'loader_freeze', 'symbol_supplement', 'symbol_review', 'source_review', 'action_review',
        'owner_grant', 'lease', 'limits', 'filesystem_scopes'}
    require(type(request) is dict and set(request) == required and type(request['schema_version']) is int
            and request['schema_version'] == 1 and request['kind'] == KIND, 'BRIDGE_REQUEST_FIELDS')
    require(request['repository'] == str(F) and request['executor'] == '/root', 'BRIDGE_REPOSITORY_OR_EXECUTOR')
    required_scopes(request['nonce'])
    start, end = request['issued_at_ns'], request['expires_at_ns']
    require(type(start) is int and type(end) is int and start <= now < end
            and 0 < end - start <= 1800_000_000_000 and end - now >= 150_000_000_000,
            'BRIDGE_APPROVAL_EXPIRED_OR_INSUFFICIENT_LIFETIME')
    require(request['filesystem_scopes'] == required_scopes(request['nonce']), 'BRIDGE_EXACT_FS_SCOPE_REQUIRED')
    limits = request['limits']
    maxima = dict(events=4096, debug_bytes=4194304, per_debug_string=65535, stdio_bytes=4194304)
    require(type(limits) is dict and set(limits) == set(maxima) | {'seconds'}, 'BRIDGE_LIMIT_FIELDS')
    require(type(limits['seconds']) in (int, float) and math.isfinite(limits['seconds'])
            and 0 < limits['seconds'] <= 30, 'BRIDGE_CAPTURE_DEADLINE')
    require(all(type(limits[k]) is int and 0 < limits[k] <= v for k, v in maxima.items())
            and limits['per_debug_string'] <= limits['debug_bytes'], 'BRIDGE_CAPTURE_BOUNDS')
    require(type(grant) is dict and grant.get('kind') == 'CETA_CANONICAL_LOADER_BRIDGE_OWNER_GRANT_V1'
            and grant.get('source') == 'actual_current_human_reply'
            and grant.get('protected_effects_authorized') is True
            and grant.get('automatic_retry') is False and grant.get('bind_fresh_runtime_ids') is True,
            'BRIDGE_FRESH_EXPLICIT_HUMAN_GRANT_REQUIRED')
    binding = {key: value for key, value in request.items() if key != 'owner_grant'}
    require(grant.get('request_binding') == binding and grant.get('effects') == list(EFFECTS),
            'BRIDGE_GRANT_EFFECT_OR_INPUT_MISMATCH')
    require(type(human) is dict and human.get('kind') == 'CETA_ACTUAL_HUMAN_MESSAGE_V1'
            and human.get('source') == 'actual_current_human_reply'
            and type(human.get('message_id')) is str and bool(human['message_id'].strip())
            and type(human.get('recorded_at')) is str and bool(human['recorded_at'].strip())
            and type(human.get('text')) is str and bool(human['text'].strip())
            and grant.get('verbatim_human_reply') == human['text'], 'BRIDGE_HUMAN_PROVENANCE_REQUIRED')
    require(grant.get('old_approval_reused') is False and grant.get('profile_name') ==
            'CETA.ProjectAICETA.IsolatedWorker.AC1.V1', 'BRIDGE_PROFILE_OR_OLD_GRANT_REFUSED')
    review_matches(source_review, [request['loader_freeze']], '/root/implement')
    review_matches(symbol_review, [request['symbol_supplement']], '/root/implement')
    require(type(action_review) is dict and action_review.get('decision') == 'approve'
            and type(action_review.get('exit_status')) is int and action_review['exit_status'] == 0
            and action_review.get('executor_id') not in (None, '', AUTHOR, '/root/implement')
            and type(action_review.get('result')) is dict, 'BRIDGE_ACTION_REVIEW_REQUIRED')
    result = action_review['result']
    for name in ('bridge_freeze', 'loader_freeze', 'source_review', 'symbol_review'):
        require(result.get(name) == request[name], 'BRIDGE_ACTION_REVIEW_BINDING:' + name)
    require(result.get('loader_snaps_input_reference') == request['symbol_supplement']
            and result.get('scope') == 'ONE_FRESH_CANONICAL_FIXTURE_OWNED_CAPTURE', 'BRIDGE_ACTION_SCOPE_REQUIRED')
    return binding


@dataclass(frozen=True, slots=True)
class Admitted:
    request: dict
    request_reference: dict
    grant: dict
    inputs: dict
    lease_evidence: dict
    source_inputs: dict
    paths: dict


def verify_bridge_freeze(ref):
    require(reference_path(ref) == W / 'FROZEN.json', 'BRIDGE_OWN_FREEZE_REQUIRED')
    frozen = read_reference(ref)
    require(frozen['kind'] == 'CETA_CANONICAL_BRIDGE_CONSTRUCTION_FREEZE_V1'
            and frozen['native_execution'] is False and frozen['author'] == AUTHOR,
            'BRIDGE_FREEZE_KIND')
    require({'capture_bridge.py', 'native_port.py', 'BRIDGE-INPUTS.json'} <= set(frozen['files']),
            'BRIDGE_FREEZE_REQUIRED_FILES_MISSING')
    for name, pin in frozen['files'].items():
        path = ordinary_path(W / name)
        require(path.is_relative_to(W) and file_sha(path)['sha256'] == pin, 'BRIDGE_CODE_CHANGED:' + name)


def validate_trusted_ingress(anchor, request, grant, human, question, code_hashes):
    """Require an externally Root-recorded anchor, not a self-described reply.

    The anchor reference comes from reviewed immutable BRIDGE-INPUTS, never the
    execution request. This construction intentionally has no such anchor. A
    future Root-supplied evidence cut must be reviewed after the human decision.
    """
    require(type(anchor) is dict and anchor.get('kind') == 'CETA_ROOT_RECORDED_ACTION_INGRESS_V1'
            and anchor.get('recorded_by') == '/root'
            and anchor.get('source') == 'actual_current_human_reply', 'BRIDGE_TRUSTED_ROOT_INGRESS_REQUIRED')
    # Anchor pins code, original question/reply, nonce, effects and destinations.
    # It cannot pin a freeze containing the anchor's own hash: that would create
    # an impossible circular hash. Root reviews the successor input/freeze join
    # after preserving the real ingress, then derives the request/grant.
    require(anchor.get('human_message_reference') == grant['human_message_reference']
            and anchor.get('nonce') == request['nonce']
            and anchor.get('repository') == str(F)
            and anchor.get('code_hashes') == code_hashes
            and anchor.get('loader_freeze') == request['loader_freeze']
            and anchor.get('symbol_supplement') == request['symbol_supplement']
            and anchor.get('effects') == list(EFFECTS)
            and anchor.get('filesystem_scopes') == request['filesystem_scopes']
            and type(anchor.get('maximum_expires_at_ns')) is int
            and request['expires_at_ns'] <= anchor['maximum_expires_at_ns'],
            'BRIDGE_ROOT_INGRESS_BINDING_MISMATCH')
    require(anchor.get('message_id') == human['message_id'] and anchor.get('text_sha256') == digest(human['text'].encode('utf8')),
            'BRIDGE_ROOT_INGRESS_MESSAGE_MISMATCH')
    require(type(question) is dict and question.get('kind') == 'CETA_ACTUAL_HUMAN_QUESTION_V1'
            and type(question.get('text')) is str and bool(question['text'].strip())
            and anchor.get('question_reference') == grant.get('question_reference')
            and anchor.get('question_message_id') == question.get('message_id')
            and anchor.get('question_text_sha256') == digest(question['text'].encode('utf8'))
            and human.get('in_reply_to') == question['message_id'], 'BRIDGE_EXACT_QUESTION_REPLY_PROVENANCE_REQUIRED')


def trusted_anchor(inputs):
    anchor_ref = inputs.get('trusted_owner_ingress_reference')
    require(anchor_ref is not None, 'BRIDGE_TRUSTED_ROOT_INGRESS_NOT_BOUND_NO_EFFECTS')
    return read_reference(anchor_ref)


def validate_action_loader_inputs(action, inputs):
    result = action['result']
    require(result.get('code_manifest') == inputs['loader_code_manifest']
            and result.get('inputs') == inputs['loader_inputs'], 'BRIDGE_R5_ACTION_REVIEW_CHANGED')


def preflight(request_reference, now_ns=None):
    request = read_reference(request_reference)
    require(type(request) is dict and 'owner_grant' in request, 'BRIDGE_REQUEST_REQUIRED')
    inputs = strict_json(read_bytes(INPUTS))
    verify_bridge_freeze(request['bridge_freeze'])
    anchor = trusted_anchor(inputs)
    grant = read_reference(request['owner_grant'])
    human = read_reference(grant.get('human_message_reference'))
    question = read_reference(anchor.get('question_reference'))
    validate_trusted_ingress(anchor, request, grant, human, question,
        {name:file_sha(W/name)['sha256'] for name in ('capture_bridge.py','native_port.py')})
    action = read_reference(request['action_review'])
    source_review = read_reference(request['source_review'])
    symbol_review = read_reference(request['symbol_review'])
    validate_authorizations(request, grant, human, action, source_review, symbol_review,
                            time.time_ns() if now_ns is None else now_ns)
    require(request['source_review'] == inputs['source_review']
            and request['symbol_review'] == inputs['symbol_review']
            and request['symbol_supplement'] == inputs['symbol_supplement'], 'BRIDGE_ACCEPTED_DEPENDENCY_REFERENCE_CHANGED')
    for ref in inputs['accepted_dependency_records']:
        read_reference(ref)
    final = read_reference(inputs['symbol_terminal_verification'])
    response = final['response']
    require(final['exit_status'] == 0 and response['allowed'] is True
            and response['receipts_valid'] is True and response['terminal_success'] is True
            and all(s == 'SUCCEEDED' for s in response['states'].values()), 'BRIDGE_V2_TERMINAL_ACCEPTANCE_REQUIRED')
    require(request['loader_freeze'] == inputs['loader_freeze'], 'BRIDGE_LOADER_FREEZE_MISMATCH')
    frozen = read_reference(request['loader_freeze'])
    for name, pin in frozen['python_hashes'].items():
        require(file_sha(R5 / name)['sha256'] == pin, 'BRIDGE_R5_SOURCE_CHANGED:' + name)
    source_inputs = read_reference(inputs['loader_inputs'])
    require(reference_path(request['symbol_supplement']) == Path(inputs['symbol_dependency']['path']),
            'BRIDGE_FINAL_V2_LOCATION_REQUIRED')
    symbols = read_reference(request['symbol_supplement'])
    require(symbols.get('schema_version') == 2 and symbols.get('kind') == 'CETA_OWNED_LOADER_SYMBOL_INPUTS_V2',
            'BRIDGE_APPROVED_V2_REQUIRED')
    require(type(symbols.get('input_pins')) is dict
            and set(symbols['input_pins']) == {'ntdll', 'pdb', 'dbghelp', 'dbgcore'}, 'BRIDGE_V2_PIN_FIELDS')
    for name in ('ntdll', 'pdb', 'dbghelp', 'dbgcore'):
        verify_file(symbols['input_pins'][name])
    for name in ('image_codeview', 'pdb_codeview', 'codeview_match'):
        require(symbols[name] == source_inputs['read_only_symbol_observations'][name],
                'BRIDGE_REVIEWED_CODEVIEW_DATA_MISMATCH')
    require(symbols['dependency_acquisition'] == source_inputs['debug_dependency_acquisition'],
            'BRIDGE_ACQUISITION_REFERENCE_CHANGED')
    trust = read_reference(inputs['signature_evidence'])
    require(trust['signature_result'] == 'SDK_VERIFIED_RETAINED_PACKAGE_UNDER_EXPLICIT_POLICY'
            and trust['sdk_exit_status'] == 0 and trust['protected_native_operation'] is False,
            'BRIDGE_ACCEPTED_PACKAGE_SIGNATURE_REQUIRED')
    require(trust['archive_pin'] == source_inputs['debug_dependency_archive'], 'BRIDGE_SIGNATURE_ARCHIVE_MISMATCH')
    verify_file(trust['archive_pin'])
    verify_file(source_inputs['python'])
    require(str(Path(sys.executable)) == source_inputs['python']['path'] and not sys.flags.optimize,
            'BRIDGE_EXACT_UNOPTIMIZED_INTERPRETER_REQUIRED')
    verify_file(source_inputs['worker'])
    for group in ('native_system_libraries', 'canonical_native_libraries'):
        for pin in source_inputs[group].values():
            verify_file(pin)
    for pin in source_inputs['caller_contract'].values():
        require(file_sha(pin['path'])['sha256'] == pin['sha256'], 'BRIDGE_CANONICAL_CALLER_CHANGED')
    for name, pin in source_inputs['ac7_payload_hashes'].items():
        require(file_sha(Path(source_inputs['ac7_candidate']) / name)['sha256'] == pin,
                'BRIDGE_CANONICAL_PAYLOAD_CHANGED:' + name)
    validate_action_loader_inputs(action, inputs)
    lease = validate_lease(request['lease'], request['nonce'])
    paths = scope_paths(request['nonce'])
    require(not any(p.exists() for p in paths.values()), 'BRIDGE_ATTEMPT_ALREADY_EXISTS_NO_RETRY')
    return Admitted(request, request_reference, grant, inputs, lease, source_inputs, paths)


def derive_release(plan, *, fixture, launch, parents, binding, native_control, owner_reference):
    """Bind measured IDs under an admitted static grant; this is not new consent."""
    request = plan.request
    normalized = {key: list(value) if type(value) is tuple else value for key, value in launch.items()}
    release = dict(schema_version=1, kind='CETA_AC7_OWNED_DEBUG_CAPTURE_V5', executor='/root', repository=str(F),
        nonce=request['nonce'], issued_at_ns=request['issued_at_ns'], expires_at_ns=request['expires_at_ns'],
        code_manifest=plan.inputs['loader_code_manifest'], inputs=plan.inputs['loader_inputs'],
        worker_sha256=plan.source_inputs['worker']['sha256'], limits=request['limits'], allow_debug_creation=True,
        allow_owned_debug_string_reads=True, allow_child_memory_writes=True, allow_existing_process_attach=False,
        allow_profile_creation=False, allow_profile_deletion=False, allow_global_configuration=False,
        automatic_retry=False, initial_breakpoint_policy='continue_one_first_chance_breakpoint',
        fixture_root=str(fixture), parent_output_handles=list(parents), owner_approval=owner_reference,
        collaborative_review=request['action_review'], loader_snaps=True,
        loader_snaps_input_reference=request['symbol_supplement'], prepared_launch=normalized,
        caller_binding=binding, caller_native_control=native_control)
    approval = dict(kind='CETA_LOADER_CAPTURE_ACTION_OWNER_APPROVAL_V5', run_id='ceta-loader-capture-r5-20261020',
        protected_effects_authorized=True, code_manifest=release['code_manifest'], inputs=release['inputs'],
        collaborative_review=release['collaborative_review'], nonce=release['nonce'], loader_snaps=True,
        expires_at_ns=release['expires_at_ns'], prepared_launch=normalized,
        loader_snaps_input_reference=release['loader_snaps_input_reference'], caller_binding=binding,
        caller_native_control=native_control, original_human_grant=plan.request['owner_grant'],
        original_human_message=plan.grant['human_message_reference'],
        derivation='Fresh measured IDs bound by independently reviewed bridge under explicit static delegation; not a new human reply',
        bridge_freeze=request['bridge_freeze'], bridge_request=plan.request_reference)
    return release, approval


def persisted_capture(plan, *, read=read_bytes, make_reference=reference):
    """Consume the actual one-attempt output; never interrogate closed handles."""
    path = plan.paths['capture']
    result = strict_json(read(path / 'RESULT.json', bound=MAX_JSON))
    retirement = strict_json(read(path / 'RETIREMENT.json', bound=MAX_JSON))
    out = read(path / 'stdout.bin', bound=plan.request['limits']['stdio_bytes'])
    err = read(path / 'stderr.bin', bound=plan.request['limits']['stdio_bytes'])
    attempt = strict_json(read(path / 'ATTEMPT.json', bound=MAX_JSON))
    require(attempt['nonce'] == plan.request['nonce'] and attempt['release_path'] == str(plan.paths['release'])
            and attempt['automatic_retry'] is False, 'BRIDGE_CAPTURE_ATTEMPT_BINDING')
    require(attempt['release_sha256'] == digest(read(plan.paths['release'], bound=MAX_JSON)),
            'BRIDGE_CAPTURE_RELEASE_CHANGED')
    identity = result['identity']
    require(type(identity['pid']) is int and identity['pid'] > 0
            and type(identity['creation_time']) is int and identity['creation_time'] > 0
            and identity['image_sha256'] == plan.source_inputs['worker']['sha256'], 'BRIDGE_CAPTURE_IDENTITY')
    require(retirement['pid'] == identity['pid'] and retirement['creation_time'] == identity['creation_time']
            and retirement['lifetime_closed'] is True and retirement['debug_exit_continued'] is True,
            'BRIDGE_CAPTURE_RETIREMENT_UNPROVEN')
    pending = retirement['native_pending']
    require(pending['exit_continued'] is True and pending['event_state'] == 'IDLE'
            and pending['file_handle'] is None and pending['file_state'] == 'NONE'
            and pending['possible_file_handle_after_unknown_wait_return'] is None,
            'BRIDGE_CAPTURE_NATIVE_CUSTODY_PENDING')
    require(result['stdout_sha256'] == digest(out) and result['stderr_sha256'] == digest(err)
            and result['stdout_bytes'] == len(out) and result['stderr_bytes'] == len(err), 'BRIDGE_CAPTURE_STDIO_CHANGED')
    return dict(result=result, retirement=retirement, stdout=out, stderr=err,
                references={name: make_reference(path / name) for name in ('RESULT.json', 'RETIREMENT.json', 'ATTEMPT.json')})


def run(request_reference):
    global _entered
    require(not _entered, 'BRIDGE_PROCESS_SINGLE_ATTEMPT')
    plan = preflight(request_reference)
    # Final live lease/time/readback immediately before crossing the lazy boundary.
    plan = preflight(request_reference)
    _entered = True
    from native_port import NativePort
    return NativePort(plan).execute()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    try:
        ref = dict(repository_relative_path=args.request.relative_to(F).as_posix(), sha256=args.sha256)
        result = run(ref)
        print(json.dumps(result, allow_nan=False))
        return 0 if (result['diagnostic_completed'] and result['all_owned_resources_retired']
                     and result['isolation_oracle_passed'] and not result['failures']
                     and result['profile_cleanup'] == 'DELETE_SUCCEEDED_AND_FOLDER_ABSENCE_OBSERVED') else 1
    except BaseException as error:
        print(json.dumps(dict(outcome='REFUSED_OR_FAILED', error_type=type(error).__name__, error=str(error),
            native_qualification=False, product_acceptance=False)), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
