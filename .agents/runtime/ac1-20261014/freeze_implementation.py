"""Freeze the exact AC1 implemented-but-unqualified native isolation cut."""
from ac_support import *
import ast
import io
import tokenize


def all_ordinary(root):
    output = {}
    pending = [root]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                path = directory / entry.name
                info = fs.lstat(path)
                assert not fs.reparse(info), path
                if stat.S_ISDIR(info.st_mode):
                    pending.append(path)
                elif stat.S_ISREG(info.st_mode):
                    output[path.relative_to(root).as_posix()] = ordinary(path)
                else:
                    raise AssertionError('Nonordinary AC1 member: ' + str(path))
    return dict(sorted(output.items()))


def loc(path):
    source = fs.read_bytes(path).decode('utf-8-sig')
    lines = source.splitlines()
    doc_lines = set()
    if path.suffix == '.py':
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if (node.body and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)
                        and isinstance(node.body[0].value.value, str)):
                    doc = node.body[0]
                    doc_lines.update(range(doc.lineno, doc.end_lineno + 1))
        code_lines = set()
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type not in (tokenize.COMMENT, tokenize.ENCODING, tokenize.INDENT,
                                  tokenize.DEDENT, tokenize.NL, tokenize.NEWLINE,
                                  tokenize.ENDMARKER) and token.string.strip():
                code_lines.update(range(token.start[0], token.end[0] + 1))
        meaningful = len(code_lines - doc_lines)
        method = 'Python token-bearing physical lines, excluding comments, blank lines and actual AST docstrings'
    elif path.suffix == '.rs':
        meaningful = sum(bool(line.strip()) and not line.lstrip().startswith('//') for line in lines)
        method = 'Rust nonblank physical source lines excluding full-line // comments; declarations remain source'
    else:
        meaningful = None
        method = 'Documentation; excluded from functional source and executable-test LOC'
    return {'physical_lines': len(lines), 'nonblank_lines': sum(bool(line.strip()) for line in lines),
            'meaningful_source_lines': meaningful, 'method': method,
            'added_physical_lines': len(lines), 'removed_physical_lines': 0}


started = utc()
initial = json.loads((R / 'source-inputs.json').read_text())
binding = json.loads((R / 'TASK-BINDING.json').read_text())
eligible = binding['eligible_paths']
assert len(eligible) == 4 and len(set(eligible)) == 4
assert all(not (P / name).exists() for name in eligible)
assert fs.text_git(P, 'rev-parse', 'HEAD') == initial['HEAD']
assert fs.text_git(P, 'branch', '--show-current') == initial['branch']
git_status = fs.text_git(P, 'status', '--porcelain=v1', '-uno')
assert git_status == initial['dirty_tracked'], 'Tracked-path status changed; inspect before author freeze'

q_before = all_ordinary(Q)
reused = {name: q_before[name] for name in initial['payloads']}
assert len(reused) == 245
assert all(row['sha256'] == initial['payloads'][name]['sha256'] for name, row in reused.items())
payloads = {name: q_before[name] for name in sorted(set(reused) | set(eligible))}
assert len(payloads) == 249
fixture_members = {name: row for name, row in q_before.items() if name not in payloads}
assert all(name.startswith('.agents/fixtures/windows-jobs-') for name in fixture_members)

targeted = json.loads((R / 'targeted-r2.json').read_text())
base = json.loads((R / 'base-windows-jobs-r1.json').read_text())
for receipt, count in ((targeted, 21), (base, 18)):
    assert receipt['exit_status'] == 0 and receipt['tests_run'] == count
    assert receipt['expected_ids'] == receipt['executed_ids']
    assert len(set(receipt['executed_ids'])) == count
    assert receipt['failures'] == [] and receipt['errors'] == [] and receipt['skipped'] == []
    assert sha(P / receipt['raw']['repository_relative_path']) == receipt['raw']['sha256']
assert targeted['source_before'] == targeted['source_after']
assert base['before'] == base['after']
assert all(q_before[name] == row for name, row in targeted['source_after'].items())
assert all(q_before[name] == row for name, row in base['after'].items())
assert all(row['lifetime_closed'] and row['job_handle_closed'] and row['process_handle_closed']
           for row in base['census'])
assert len(base['census']) == 9

build = json.loads((R / 'build-r2/build.json').read_text())
assert build['exit_status'] == 0
assert build['source'] == payloads['native/windows_broker/isolated_worker.rs']
assert ordinary(Path(build['native_image']['path'])) == build['native_image']
for key in ('actual_rustc', 'resolved_rustup_command_image'):
    assert ordinary(Path(build[key]['path'])) == build[key]
native_receipts = []
for path in sorted((R / 'native-fixtures').glob('*/native*.json')):
    value = json.loads(path.read_text())
    assert value['failure_type'] == 'ContractError'
    assert value['failure'] == 'ISOLATION_RESTRICTED_CREATE_FAILED:2 at $'
    assert value.get('raw_stdout') == '' and 'facts' not in value
    assert value['setup']['persistent_profile_install'] is False
    assert value['setup']['image']['sha256'] == build['native_image']['sha256']
    assert len(value['cleanup']) == 1
    for owner in value['cleanup']:
        assert owner['kind'] == 'trusted_medium_fixture'
        assert owner['exit_code'] == 125 and owner['active_processes'] == 0 and owner['lifetime_closed']
    for protected_path, before in value['setup']['protected_before'].items():
        assert ordinary(Path(protected_path)) == before
    native_receipts.append({'receipt': reference(path), 'started_at': value['started_at'],
                            'finished_at': value['finished_at'], 'failure': value['failure'],
                            'fixture': value['setup']['fixture'], 'cleanup': value['cleanup'],
                            'trust': 'Actual medium trusted disposable control; no restricted child created'})
assert len(native_receipts) == 5
native_inventory = all_ordinary(R / 'native-fixtures')
fixture_roots = sorted(path.name for path in (R / 'native-fixtures').iterdir() if path.is_dir())
write_new(R / 'native-evidence-index.json', {
    'observed_at': utc(), 'receipts': native_receipts,
    'actual_restrictive_creation_refusals': len(native_receipts),
    'actual_medium_control_retirements': sum(len(row['cleanup']) for row in native_receipts),
    'base_retained_owner_observations': base['census'],
    'fixture_roots': fixture_roots, 'ordinary_members': native_inventory,
    'fixtures_preserved': True, 'profile_creation_or_deletion': False,
    'limits': ['Five native denial receipts and nine base-suite retained-owner observations are exact scoped counts, not an exhaustive host census.',
               'No restricted child creation succeeded; no AppContainer bypass/access/network result is inferred.',
               'First setup failure preceded the allocated-record improvement; its initial random SID was not persisted and remains unknown.']})

current_before = source_inventory()
forward = {name: {'initial': initial['payloads'].get(name), 'current': current_before.get(name)}
           for name in sorted(set(initial['payloads']) | set(current_before))
           if initial['payloads'].get(name, {}).get('sha256') != current_before.get(name, {}).get('sha256')}
perf_r = P / '.agents/runtime/perf1-20261014'
perf_joined = json.loads((perf_r / 'active-application/JOINED-SOURCE.json').read_text())
assert set(forward) == set(perf_joined['only_application_paths'])
assert len(forward) == 3
assert all(current_before[name]['sha256'] == perf_joined['after_hashes'][name] for name in forward)
perf_acceptance = json.loads((perf_r / 'actual-acceptance.json').read_text())
assert set(perf_acceptance['actual_states'].values()) == {'SUCCEEDED'}
assert perf_acceptance['claims'] == {} and perf_acceptance['sequence'] == 13
assert sha(perf_r / 'integrate.json') == perf_acceptance['integrate_receipt_sha256']
write_new(R / 'source-forward-conservation.json', {
    'started_at': started, 'observed_at': utc(), 'source_root': str(P),
    'initial': reference(R / 'source-inputs.json'), 'initial_src_tests_contracts_count': len(initial['payloads']),
    'current_src_tests_contracts_count': len(current_before), 'current': current_before,
    'candidate_reused_count': len(reused), 'candidate_reused_bytes_exact': True,
    'authorized_forward_paths': forward,
    'forward_application': reference(perf_r / 'active-application/APPLIED.json'),
    'forward_joined_source': reference(perf_r / 'active-application/JOINED-SOURCE.json'),
    'forward_actual_acceptance': reference(perf_r / 'actual-acceptance.json'),
    'HEAD': initial['HEAD'], 'branch': initial['branch'], 'tracked_status': git_status,
    'eligible_active_paths_absent': eligible,
    'claim': 'Recorded endpoint proof; AC1 does not publish Source. Root PERF1 is an explicit authorized forward cut. This is not uninterrupted whole-repository observation.',
    'copy_rule': 'All 245 historical candidate dependencies are REUSE only; no overlay of newer active PERF1 files.'})

measures = {name: loc(Q / name) for name in eligible}
product_paths = ['src/ceta/supervisor/isolated_worker.py', 'native/windows_broker/isolated_worker.rs']
measures_total = {
    'new_product_physical_source_lines': sum(measures[name]['physical_lines'] for name in product_paths),
    'new_product_meaningful_source_lines': sum(measures[name]['meaningful_source_lines'] for name in product_paths),
    'new_executable_test_physical_lines': measures['tests/contract/test_isolated_worker.py']['physical_lines'],
    'new_executable_test_meaningful_lines': measures['tests/contract/test_isolated_worker.py']['meaningful_source_lines'],
    'new_contract_document_physical_lines': measures['contracts/ISOLATED_WORKER_V1.md']['physical_lines'],
    'reuse_product_LOC_credit': 0, 'reuse_test_LOC_credit': 0,
    'runtime_build_helper_or_receipt_LOC_in_product_credit': 0,
    'qualification': 'Physical source includes ABI declarations and imports; meaningful counts follow each file method and do not imply all branches executed.'}
new_ast = ast.parse((Q / 'tests/contract/test_isolated_worker.py').read_text())
test_bodies = {node.name: digest(ast.dump(node, include_attributes=False).encode())
               for node in ast.walk(new_ast) if isinstance(node, ast.FunctionDef) and node.name.startswith('test_')}
assert len(test_bodies) == 21
write_new(R / 'implementation-measures.json', {'observed_at': utc(), 'files': measures, 'totals': measures_total,
                                             'new_method_AST_sha256': test_bodies,
                                             'retained_test_file': q_before['tests/contract/test_windows_jobs.py']})

blocked = [
    'Actual AppContainer token, exact SID, zero capabilities and low integrity of a successfully created worker',
    'Actual allowed asset read and low scratch create from that worker',
    'Actual denial of five state/policy/source-like sentinels from that worker',
    'Actual denial of medium trusted process mutation and handle duplication',
    'Actual child/breakaway denial and excluded inherited-event access denial',
    'Actual loopback connection, listening and UDP denial from that worker',
    'Actual restricted-child post-create inspection/retirement failures and recovery branches',
    'Public runtime composition, current authority, clock, single-use effect and durable outcome acceptance']
proposal = json.loads((R / 'PROFILE-CREATION-PROPOSAL.json').read_text())
assert proposal['executed'] is False and proposal['capability_count'] == 0
assert proposal['decision'] == 'PROPOSED_REQUIRES_EXPLICIT_USER_APPROVAL'
assert proposal['exact_name'] == 'CETA.ProjectAICETA.IsolatedWorker.AC1.V1'

self_review = {
    'observed_at': utc(), 'actor': ACTOR, 'decision': 'AUTHOR_SELF_REVIEW_COMPLETE_FOR_FAIL_CLOSED_CUT',
    'distinct_independent_acceptance': False,
    'inspected': [
        'All four complete CREATE files; existing canonical launch/error/custody methods and applicable unit/caller seams',
        'Exact explicit security/child/job/handle attributes and before-resume token/image/lifetime checks',
        'Native volume aliases remain the same pinned file; fixture rights remain inside fresh owned T: descendants',
        'Control/primary exceptions and residual real native handles/SID allocations preserve explicit retryable cleanup',
        'Rust fixed command/probe bounds, unexpected suspended-child retirement and safe output fields',
        'Exact 21 new test IDs/body hashes and 18 retained tests with raw expected/executed equality',
        'All 245 reused payload bytes and exact separately authorized current PERF1 forward paths'],
    'verified_tests': {'new_cases': 21, 'retained_cases': 18, 'failures': 0, 'errors': 0, 'skips': 0},
    'native_qualification': 'BLOCKED_BY_RESTRICTIVE_LAUNCH_ERROR2_CAUSE_UNESTABLISHED',
    'not_executed': blocked,
    'reviewer_dependency': 'The exact new test imports runtime native_fixture_support through a constrained CETA_AC1_RUNTIME_ROOT. A distinct reviewer must bind its own explicitly qualified support/fixture scope and the pinned Q/build bytes, without editing Q.',
    'preserved_failures': [
        'build-r1: real Rust E0034 trait ambiguity and subsequent installed rustc shim ordinary-reader rejection; raw compiler exit was not persisted before the measurement failure',
        'native-r1: combined DACL+LABEL SetNamedSecurityInfoW error5 before launch; partial fixture retained, original random SID not recorded',
        'native-r2/r3/r4: exact native CreateProcessW error2 under logical, volume-GUID and wider fixture traversal observations',
        'targeted-r1: passing earlier Python byte cut, never credited to later cleanup control change; final cut rerun as targeted-r2'],
    'remaining': [
        {'issue': 'Restricted no-profile native launch unavailable, error2 exact cause unestablished', 'classification': 'environment/dependency issue; blocks positive isolation activation'},
        {'issue': 'Exact optional durable profile creation', 'classification': 'requires explicit user decision against prepared proposal'},
        {'issue': 'Distinct independent review and later Source publication', 'classification': 'requires separate follow-up; author cannot self-certify'},
        {'issue': 'Some post-create native paths unexecuted because restricted creation failed', 'classification': 'not qualified; requires fresh actual successor acceptance'}],
    'effects': initial['effects'], 'source_publication': False,
    'profile_create_delete_or_host_config': False, 'unrestricted_fallback': False,
    'synchronous_native_call_preemption_claim': False}
write_new(R / 'SELF-REVIEW.json', self_review)

manifest = {
    'schema_version': 1, 'cut': RUN, 'frozen_at': utc(), 'author': ACTOR,
    'candidate_root': str(Q), 'source_root': str(P), 'runtime_root': str(R),
    'functional_status': 'IMPLEMENTED_FAIL_CLOSED', 'isolation_qualified': False,
    'activation_ready': False, 'whole_unit_completion': False, 'source_published': False,
    'eligible_paths': eligible,
    'classifications': {name: 'CREATE' for name in eligible},
    'payloads': payloads, 'payload_count': len(payloads),
    'historical_reused_count': len(reused), 'reused_application_eligible': False,
    'candidate_fixture_members': fixture_members,
    'new_tests': reference(R / 'targeted-r2.json'), 'new_tests_raw': targeted['raw'],
    'retained_tests': reference(R / 'base-windows-jobs-r1.json'), 'retained_tests_raw': base['raw'],
    'tests': {'new': 21, 'retained': 18, 'total': 39, 'failures': 0, 'errors': 0, 'skips': 0},
    'native_build': reference(R / 'build-r2/build.json'), 'native_image': build['native_image'],
    'review_support': {name: ordinary(R / name) for name in ('native_fixture_support.py','ac_support.py','run_tests.py','run_base_windows_jobs.py','build_native.py')},
    'native_evidence': reference(R / 'native-evidence-index.json'),
    'source_input': reference(R / 'source-inputs.json'),
    'source_conservation': reference(R / 'source-forward-conservation.json'),
    'measures': reference(R / 'implementation-measures.json'), 'LOC': measures_total,
    'self_review': reference(R / 'SELF-REVIEW.json'),
    'profile_creation_proposal': reference(R / 'PROFILE-CREATION-PROPOSAL.json'),
    'preserved_failure_members': all_ordinary(R / 'failed-cuts'),
    'not_executed': blocked,
    'handoff_boundary': 'Distinct review of exact fail-closed cut only; no activation/profile installation/full-unit claim.'}
write_new(Q / 'TRANSFER-MANIFEST.json', manifest)
manifest_ref = reference(Q / 'TRANSFER-MANIFEST.json')
current_after = source_inventory()
assert current_after == current_before
assert all(ordinary(Q / name) == row for name, row in payloads.items())

handoff = {
    'observed_at': utc(), 'author': ACTOR, 'manifest': manifest_ref,
    'paths': eligible, 'LOC': measures_total, 'tests': manifest['tests'],
    'native_launch_result': 'Five actual safe refusals with error2, no restricted child/token/access result',
    'cleanup': 'Five medium controls observed exited125/empty-job/closed; nine retained-base owner observations closed. Tests own handle/SID cleanup recovered injected failures.',
    'profile_proposal': manifest['profile_creation_proposal'],
    'current_source': manifest['source_conservation'],
    'independent_review_required': True, 'source_application_authorized_by_this_author': False,
    'next_step': 'Root assigns distinct actor on frozen Q/manifest and author-released TAAR review READY. Reviewer qualifies its own fresh helper/fixture scope. Positive isolation remains blocked until exact host dependency is separately authorized and actually qualified.'}
write_new(R / 'HANDOFF.json', handoff)
commands = [
    {'command': subprocess.list2cmdline(build['command_argv']), 'exit_status': 0},
    {'command': subprocess.list2cmdline([str(PY), '-B', '-X', 'utf8', str(R / 'run_tests.py'), 'targeted-r2']), 'exit_status': 0},
    {'command': subprocess.list2cmdline([str(PY), '-B', '-X', 'utf8', str(R / 'run_base_windows_jobs.py')]), 'exit_status': 0},
    {'command': subprocess.list2cmdline([str(PY), '-B', '-X', 'utf8', str(Path(__file__))]), 'exit_status': 0}]
result = {'decision': 'IMPLEMENTED_FAIL_CLOSED_NATIVE_ACTIVATION_UNQUALIFIED',
          'manifest_sha256': manifest_ref['sha256'], 'manifest': manifest_ref,
          'handoff': reference(R / 'HANDOFF.json'), 'self_review': manifest['self_review'],
          'eligible_paths': eligible, 'LOC': measures_total, 'tests': manifest['tests'],
          'native_evidence': manifest['native_evidence'], 'source_conservation': manifest['source_conservation'],
          'profile_creation_proposal': manifest['profile_creation_proposal'],
          'isolation_qualified': False, 'activation_ready': False, 'whole_unit_completion': False,
          'not_executed': blocked, 'source_published': False}
response = complete('implement', result, commands, [
    ('Exact four CREATE paths and all 245 historical REUSE payload bytes frozen', True),
    ('Final-cut21 and retained18 expected/executed IDs identical; no failure/error/skip', True),
    ('Five native safe-denial and scoped real cleanup receipts preserved', True),
    ('Current PERF1 three-path forward cut exact; no active Source application by AC1', True),
    ('Positive native isolation obligations explicitly unexecuted and activation closed', True),
    ('No profile installation, host configuration or unrestricted fallback', True),
    ('Author self-review complete; distinct review still required', True)])
print(json.dumps({'allowed': response['allowed'], 'manifest': manifest_ref,
                  'implement': reference(R / 'implement.json'), 'LOC': measures_total,
                  'tests': manifest['tests'], 'qualified': False}, indent=2), flush=True)
