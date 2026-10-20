"""Supplemental bounded file-only receipt verification and report projection."""
from pathlib import Path
import ast
import hashlib
import json

F = Path(r'T:\00-Active\Project-AI-CETA')
R = F / '.agents/runtime/ac7-token-contract-20261020'
C = F / '.agents/ac7-token-contract-20261020'
Q = R / 'q-6be3c32cb832461093c6d15dc9c538f8'
O = F / '.agents/runtime/ac7-startup-diagnosis-20261020'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(name, value):
    with (O / name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


source = C / 'src/ceta/supervisor/service.py'
frozen = read(Q / 'CANDIDATE-BEFORE.json')
entry = frozen[source.relative_to(C).as_posix()]
service_before = digest(source)
assert service_before == entry['sha256']
body = source.read_text(encoding='utf-8-sig')
pipe = next(n for n in ast.walk(ast.parse(body)) if isinstance(n, ast.FunctionDef) and n.name == 'pipe')
supplement = [{'path': str(source), 'sha256': service_before, 'candidate_snapshot_entry': entry,
    'start_line': pipe.lineno, 'end_line': pipe.end_lineno,
    'text': '\n'.join(body.splitlines()[pipe.lineno - 1:pipe.end_lineno])}]
for relative, start, end in [('tools/qualify_isolated_worker.py', 216, 280),
                             ('tools/qualify_isolated_worker.py', 378, 399),
                             ('native/windows_broker/isolated_worker.rs', 207, 265)]:
    path = C / relative
    supplement.append({'path': str(path), 'sha256': digest(path), 'start_line': start, 'end_line': end,
        'text': '\n'.join(path.read_text(encoding='utf-8-sig').splitlines()[start - 1:end])})
write('SUPPLEMENTAL-SOURCE-EXCERPTS.json', {'method': 'Source text and AST inspection only', 'excerpts': supplement,
    'service_sha256_after': digest(source), 'service_unchanged': digest(source) == service_before})

checks = []
for receipt_name, prefix in [('AUTHORIZED-AC7-TERMINAL.json', 'AUTHORIZED-AC7'),
                              ('APPROVED-QUALIFICATION.json', 'APPROVED-QUALIFICATION')]:
    receipt = read(R / receipt_name)
    for stream in ('stdout', 'stderr'):
        path = R / (prefix + '.' + stream)
        checks.append({'path': str(path), 'expected': receipt[stream + '_sha256'], 'actual': digest(path)})
build = read(R / 'build-r2/BUILD.json')
for command in build['commands']:
    for stream in ('stdout', 'stderr'):
        path = R / 'build-r2' / (command['label'] + '.' + stream)
        checks.append({'path': str(path), 'expected': command[stream + '_sha256'], 'actual': digest(path)})
assert all(c['actual'] == c['expected'] for c in checks)
write('RECEIPT-STREAM-BINDINGS.json', {'checks': checks, 'matched': len(checks),
    'build_receipt_sha256': digest(R / 'build-r2/BUILD.json'),
    'recorded_pure_test_count': build['pure_tests'], 'tests_rerun': False,
    'qualification_exit_status': read(R / 'AUTHORIZED-AC7-TERMINAL.json')['exit_status']})

pe = read(O / 'PE-DEPENDENCIES.json')
summary = []
for row in pe['system32_candidates']:
    if 'pe' not in row:
        summary.append(row)
        continue
    artifact = row['pe']
    concrete = lambda kind: [x['dll'] for x in artifact[kind]
                            if not x['dll'].lower().startswith(('api-ms-', 'ext-ms-'))]
    summary.append({'dll': row['import'], 'sha256': artifact['artifact']['sha256'],
        'normal_import_descriptors': len(artifact['normal_imports']),
        'delay_import_descriptors': len(artifact['delay_imports']),
        'concrete_normal_edges': concrete('normal_imports'), 'concrete_delay_edges': concrete('delay_imports'),
        'selected_forwarders': artifact['selected_imported_export_forwarders'],
        'actual_historical_module_binding': 'UNKNOWN'})
write('DEPENDENCY-SUMMARY.json', {'on_disk_candidates': summary,
    'coverage': 'One current System32 level, all reported normal/delay import descriptors; API-set and deeper host mapping unresolved',
    'failing_dll': 'UNKNOWN', 'initialization_order': 'UNKNOWN', 'runtime_api_order': 'UNKNOWN'})

fix = Q / 'native-fixtures/ac1-ec4105bbf9af49028b30c90895b61e3d'
probe = read(fix / 'native-profile-r2.json')
paths = read(fix / 'LAUNCH-PATHS.json')
write('LAUNCH-COMPARISON.json', {
    'attempt': Q.name, 'image_sha256': probe['image_hash'],
    'facts_from_receipt': {'worker_identity': probe['worker_identity'], 'ordinary_identity': probe['trusted_target'],
        'parent_token_facts': probe['parent_token_facts'], 'worker_exit_decimal': probe['worker_exit_code'],
        'worker_exit_hex': hex(probe['worker_exit_code']), 'facts': probe['facts'], 'stderr': probe['stderr'],
        'native_paths_receipt': paths, 'recorded_probe_argv': probe['argv']},
    'source_derived': {
        'ordinary_argv': [probe['setup']['image']['path'], 'hold', '30000'],
        'isolated_argv': [paths['native_image'], *probe['argv']],
        'base_creation_flags_both': '0x08080404',
        'base_creation_flag_names': ['CREATE_SUSPENDED', 'CREATE_UNICODE_ENVIRONMENT',
                                     'EXTENDED_STARTUPINFO_PRESENT', 'CREATE_NO_WINDOW'],
        'ordinary': {'cwd': probe['setup']['fixture'], 'inherit_handles': False, 'standard_handle_flag': 0,
            'selected_standard_handles': None, 'job_limits': ['KILL_ON_JOB_CLOSE'],
            'attributes': ['JOB_LIST'], 'desktop_pointer': 'NULL (zero-initialized)'},
        'isolated': {'cwd': paths['native_directory'], 'inherit_handles': True, 'standard_handle_flag': '0x100',
            'selected_standard_handles': 'stdin read end, stdout/stderr write ends; exact numeric values not recorded',
            'job_limits': ['KILL_ON_JOB_CLOSE', 'ACTIVE_PROCESS_LIMIT=1'],
            'attributes': ['JOB_LIST', 'SECURITY_CAPABILITIES (AppContainer SID, capability count 0)',
                           'CHILD_PROCESS_POLICY=1', 'HANDLE_LIST (3 standard handles)'],
            'desktop_pointer': 'NULL (zero-initialized)'},
        'environment': {'both_use': '_IsolationAPI.environment(same scratch), serialized by windows_jobs._environment',
            'keys': ['SystemRoot', 'WINDIR', 'PATH', 'TEMP', 'TMP', 'LOCALAPPDATA'],
            'source_values': {'SystemRoot': 'GetWindowsDirectoryW result', 'WINDIR': 'same Windows directory',
                'PATH': 'Windows directory/System32', 'TEMP': 'same fixture scratch directory',
                'TMP': 'same fixture scratch directory', 'LOCALAPPDATA': 'current user known folder (queried twice)'},
            'exact_historical_bytes_equal': 'UNKNOWN; not serialized in probe receipt'},
        'stdio_validation': 'CreatePipe inheritable, parent ends made non-inheritable; launch checks child handle inheritance',
        'extra_mitigation_or_ui_calls_in_the_two_launch_bodies': 'None observed in inspected functions; inherited/OS state not captured'},
    'limits': ['Source-derived CreateProcess values are not a raw API-call trace',
        'No load/module list, entry marker, TLS/CRT phase or DLL error name recorded',
        'Control liveness is not completion of hold or equivalence to probe',
        'No current process/profile/native API was invoked by this diagnosis']})
print(json.dumps({'stream_bindings': len(checks), 'stream_mismatches': 0,
                  'service_source_pin_matches': True, 'worker_status': hex(probe['worker_exit_code'])}))
