"""Independent ER1 destination observations and five owned native CLI checks."""
from datetime import datetime, timezone
from pathlib import Path
import ast
import base64
import csv
import hashlib
import importlib
import io
import json
import msvcrt
import os
import stat
import struct
import sys
import time
import uuid
import zipfile

O = Path(__file__).resolve().parent
R = O.parent
F = R.parents[2]
Q = F / '.agents/er1-20261014'
E3 = F / '.agents/source-assembly-20261014T021300Z/.agents/e3'
PY = E3 / 'Scripts/python.exe'
ROOT_OUT = R / 'active-application'
sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
assert O == F / '.agents/runtime/er1-20261014/independent-destination'
assert Path(sys.executable) == PY and sys.flags.optimize == 0 and os.name == 'nt'
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
digest = lambda data: hashlib.sha256(data).hexdigest()
read = lambda path: json.loads(Path(path).read_text(encoding='utf-8'))
utc = lambda: datetime.now(timezone.utc).isoformat()
started = utc()
commands = []
imports = []
proofs = {}

def write_new(path, value):
    path = Path(path)
    assert path.is_relative_to(O)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')

def pinned(path, expected):
    observed = sha(path)
    assert observed == expected, (str(path), observed, expected)
    return {'path': str(path), 'sha256': observed}

def ordinary_rows(snapshot):
    rows = [row for row in snapshot['members'] if row['kind'] == 'ordinary_file']
    mapping = {row['relative_path']: row for row in rows}
    assert len(mapping) == len(rows) == snapshot['ordinary_files']
    return mapping

def qualified_files_under(root):
    # This inventory is bounded to the 33-member frozen candidate, never F.
    root = support.fs.safe_components(root)
    output = {}
    directories = [root]
    while directories:
        directory = directories.pop()
        with os.scandir(support.fs.io_path(directory)) as listing:
            names = sorted(entry.name for entry in listing)
        for name in names:
            path = directory / name
            info = support.fs.lstat(path)
            assert not support.fs.reparse(info)
            if stat.S_ISDIR(info.st_mode):
                directories.append(path)
            else:
                assert stat.S_ISREG(info.st_mode)
                output[path.relative_to(root).as_posix()] = support.ordinary(path)
    return output

sys.path.insert(0, str(R))
pins = {
    'support': pinned(R / 'er1_support.py', '38721b1fa0c112f568a4e957b5ae3a1ecd747645c83ec5882228947805a198d5'),
    'manifest': pinned(Q / 'TRANSFER-MANIFEST.json', '7325582b9fa18972dc2e6337e66e55fa3c7ae1ee5db600824aedeca58bb73f83'),
    'journal': pinned(ROOT_OUT / 'APPLIED.json', '4b0c716f31661701d10541922f96cadc301589a57935ec0bdf209ca353886c9b'),
    'root_verification': pinned(ROOT_OUT / 'destination-verification.json', '91aa912566bcecd7abd52496375db071d02c6d8042b0b60dd89fbeda3af525aa'),
    'root_verifier': pinned(R / 'verify_destination.py', '01a6ea2408cffc240596a9c27f9416c8a9b59e23ea122db773ee3a8f8be5c09e'),
    'publisher': pinned(R / 'apply_reviewed_environment.py', 'f25e7967d5cfba5e90819490ec0f2f19320b2d5ebc8df95e2a8d9020064b8cec'),
    'candidate_review': pinned(R / 'independent-review/review.json', '8322051dbf2b0efac25a46ea2af47ce1fcab2cf62f42d41776a28e677a94e0b3'),
    'publisher_review': pinned(R / 'independent-review/publication-helper-review.json', '5b64b0fb41053faf8a11a56b0d08f0d3419243bae4092fbe4b3d3d703c3f9ff8'),
    'generation': pinned(R / 'candidate-generation.json', '67640734a1d02fb2242f9cfef979843c6c8c19c8b3924acd730dee76a53a0216'),
    'inventory': pinned(R / 'launcher-inventory-r2.json', '1ca08fef1764ee77e504a0988f6c0aecf6f21285d480e46d08f5439fe4863751'),
    'author_ordinary_after': pinned(R / 'E3-after-tests.json', '9c50b10fe1333ef2a4ee5d433c8c94d5a5bd936b2174a51e74bdff2bf0eea013'),
    'source_expected': pinned(F / '.agents/runtime/hd2-20261014/independent-destination/expected-destination279.json', 'ccd917d121b4415e258683590b7c90fddc236459753223cb66ea6175c8b8271a'),
    'native_runner': pinned(R / 'run_staged_tests_r2.py', 'a566a22d7f4e52c40a7848d18d5ea66e1be57b5c09b672d063fe34663a2bef19'),
}
import er1_support as support
ordinary = support.ordinary
sys.path.insert(0, str(F / 'src'))
import ceta.supervisor.windows_jobs as jobs_module
from ceta.supervisor.windows_jobs import WindowsOwnedProcess
jobs_source = ordinary(Path(jobs_module.__file__).resolve())
assert Path(jobs_source['path']) == F / 'src/ceta/supervisor/windows_jobs.py'
manifest = read(Q / 'TRANSFER-MANIFEST.json')
journal = read(ROOT_OUT / 'APPLIED.json')
root_verification = read(ROOT_OUT / 'destination-verification.json')
claim = read(R / 'er1-20261014/claims.json')['integrate']
assert claim['executor_id'] == '/root' and claim['workspace'] == str(E3)
assert claim['input_hash'] == journal['claim_input_hash'] == 'b7db080c4709d7b35d9748812864cab83eb0a80b6b9d2560da6382908c9a520b'
before_path = ROOT_OUT / 'environment-before.json'
after_path = ROOT_OUT / 'environment-after.json'
pinned(before_path, journal['environment_before_sha256'])
pinned(after_path, journal['environment_after_sha256'])
before = read(before_path)
published = read(after_path)
expected = ordinary_rows(published)
original_rows = ordinary_rows(before)
assert len(expected) == len(original_rows) == 3601
assert original_rows == ordinary_rows(read(R / 'E3-after-tests.json'))
assert root_verification['expected_environment_files'] == expected
source_expected = read(Path(pins['source_expected']['path']))['expected_payload_hashes']
assert len(source_expected) == 279
source_before = {relative: ordinary(F / relative) for relative in source_expected}
assert {relative: row['sha256'] for relative, row in source_before.items()} == source_expected
candidate_before = qualified_files_under(Q)
assert len(candidate_before) == 33
payloads = manifest['payloads']
assert len(payloads) == len(journal['before_images']) == len(journal['completed']) == 30
originals = {row['relative_path']: row for row in journal['before_images']}
completed = {row['relative_path']: row['sha256'] for row in journal['completed']}
assert len(originals) == len(completed) == 30
allowed = set()
payload_observations = []
for entry in payloads:
    target = Path(entry['source_path'])
    assert target.is_relative_to(E3) and entry['action'] == 'EXTEND_STAGED_ONLY'
    relative = target.relative_to(E3).as_posix()
    assert relative not in allowed
    allowed.add(relative)
    current = ordinary(target)
    candidate = ordinary(Q / entry['candidate_relative_path'])
    old = originals[relative]
    native = ROOT_OUT / 'native-backups' / (relative + '.original')
    logical = ROOT_OUT / 'before' / (relative + '.source')
    author_before = F / entry['before_image']['repository_relative_path']
    assert current['sha256'] == candidate['sha256'] == entry['candidate_sha256'] == completed[relative]
    assert current['bytes'] == candidate['bytes'] == entry['candidate_bytes']
    assert ordinary(native)['sha256'] == ordinary(logical)['sha256'] == ordinary(author_before)['sha256'] == old['sha256'] == entry['source_sha256']
    assert original_rows[relative]['sha256'] == entry['source_sha256']
    assert original_rows[relative]['native_identity'] == entry['source_native_identity']
    with support.fs.open_source(support.fs.safe_components(native), exclusive=True) as stream:
        facts = os.fstat(stream.fileno())
    actual = {'device': facts.st_dev, 'inode': facts.st_ino, 'mode': facts.st_mode, 'bytes': facts.st_size, 'mtime_ns': facts.st_mtime_ns}
    assert actual == {key: old[key] for key in actual}
    assert (facts.st_dev, facts.st_ino) == (original_rows[relative]['native_identity']['device'], original_rows[relative]['native_identity']['inode'])
    assert actual['mtime_ns'] == original_rows[relative]['native_identity']['mtime_ns']
    payload_observations.append({'relative_path': relative, 'active': current, 'candidate': candidate,
        'native_original': {'path': str(native), 'sha256': old['sha256'], 'handle_facts': actual},
        'logical_original': ordinary(logical), 'author_before_sha256': entry['source_sha256']})
assert allowed == set(originals) == set(completed)
untouched = set(expected) - allowed
assert len(untouched) == 3571
assert all(expected[relative] == original_rows[relative] for relative in untouched)
assert {relative for relative in expected if expected[relative] != original_rows[relative]} == allowed
print(json.dumps({'independent_checked_targets': len(payload_observations), 'native_originals': 30, 'source_payloads': 279}), flush=True)

try:
    fresh_before = support.snapshot_tree()
    write_new(O / 'environment-independent-before.json', fresh_before)
    assert ordinary_rows(fresh_before) == expected
    assert {(row['relative_path'], row['kind']) for row in fresh_before['members']} == {(row['relative_path'], row['kind']) for row in published['members']}
    print(json.dumps({'freshly_rehashed_ordinary_files': 3601, 'unrelated_files_exact': 3571}), flush=True)
    generation = read(R / 'candidate-generation.json')
    inventory = read(R / 'launcher-inventory-r2.json')
    inventory_by_name = {row['filename']: row for row in inventory['launchers']}
    launcher_by_name = {row['filename']: row for row in generation['launchers']}
    assert len(inventory_by_name) == len(launcher_by_name) == 27
    launcher_checks = []
    for entry in generation['launchers']:
        old = inventory_by_name[entry['filename']]
        active_bytes = support.fs.read_bytes(E3 / entry['source_relative_path'])
        old_bytes = support.fs.read_bytes(F / entry['before_image']['repository_relative_path'])
        n = old['stub_bytes']
        assert active_bytes[:n] == old_bytes[:n]
        assert digest(active_bytes[:n]) == entry['stub_sha256'] == old['stub_sha256']
        pe = struct.unpack_from('<I', active_bytes, 0x3c)[0]
        assert active_bytes[pe:pe+4] == b'PE\x00\x00'
        assert struct.unpack_from('<H', active_bytes, pe+4)[0] == 0x8664
        assert struct.unpack_from('<H', active_bytes, pe+24+68)[0] == 3
        new_end = active_bytes.index(b'\n', n) + 1
        old_end = old_bytes.index(b'\n', n) + 1
        assert active_bytes[n:new_end] == ('#!' + str(PY) + '\n').encode('utf-8')
        assert old_bytes[n:old_end].decode().strip() == old['original_shebang']
        assert b'CETA_Intelligence_Operating_System_Build_Package' not in active_bytes
        with zipfile.ZipFile(io.BytesIO(active_bytes)) as archive:
            assert archive.namelist() == ['__main__.py'] and archive.testzip() is None
            main = archive.read('__main__.py')
        with zipfile.ZipFile(io.BytesIO(old_bytes)) as archive:
            original_main = archive.read('__main__.py')
        assert main == original_main == old['original_main_script'].encode('utf-8')
        assert digest(main) == entry['main_script_sha256']
        launcher_checks.append({'filename': entry['filename'], 'source_path': str(E3 / entry['source_relative_path']),
            'stub_sha256': digest(active_bytes[:n]), 'main_sha256': digest(main), 'stub_and_main_exact_reuse': True,
            'current_interpreter_shebang_exact': True, 'zip_tail_bytes_exact': active_bytes[new_end:] == old_bytes[old_end:],
            'native_PE_machine': 'x86_64', 'native_PE_subsystem': 'console', 'active_sha256': digest(active_bytes)})
    metadata_checks = []
    total_changes = 0
    for entry in generation['metadata']:
        old = support.fs.read_bytes(F / entry['before_image']['repository_relative_path'])
        current = support.fs.read_bytes(E3 / entry['source_relative_path'])
        candidate = support.fs.read_bytes(F / entry['candidate']['repository_relative_path'])
        assert current == candidate and digest(old) == entry['source_observation']['sha256']
        left = old.splitlines(keepends=True)
        right = current.splitlines(keepends=True)
        assert len(left) == len(right)
        changed = {row['line_number']: row for row in entry['row_changes']}
        assert len(changed) == entry['changed_rows']
        actual_changes = set()
        for line_number, (a, b) in enumerate(zip(left, right), 1):
            if line_number not in changed:
                assert a == b
                continue
            actual_changes.add(line_number)
            row = changed[line_number]
            assert a != b and digest(a) == row['original_line_sha256'] and digest(b) == row['candidate_line_sha256']
            a_fields = next(csv.reader(io.StringIO(a.decode('utf-8'))))
            b_fields = next(csv.reader(io.StringIO(b.decode('utf-8'))))
            assert a_fields == row['original_row'] and b_fields == row['candidate_row']
            assert a_fields[0] == b_fields[0]
            a_raw = a.rstrip(b'\r\n').rsplit(b',', 2)
            b_raw = b.rstrip(b'\r\n').rsplit(b',', 2)
            assert a_raw[0] == b_raw[0]
            assert [value.startswith(b'"') for value in a_raw[1:]] == [value.startswith(b'"') for value in b_raw[1:]]
            ending = bytes.fromhex(row['original_line_ending_hex'])
            assert ending and a.endswith(ending) and b.endswith(ending)
            exe = launcher_by_name[row['filename']]
            wanted = 'sha256=' + base64.urlsafe_b64encode(bytes.fromhex(exe['candidate']['sha256'])).decode().rstrip('=')
            assert b_fields[1] == wanted and int(b_fields[2]) == exe['candidate_bytes']
            assert b_raw[1].strip(b'"') == wanted.encode() and b_raw[2].strip(b'"') == str(exe['candidate_bytes']).encode()
        assert actual_changes == set(changed)
        total_changes += len(changed)
        metadata_checks.append({'relative_path': entry['source_relative_path'], 'raw_lines': len(left),
            'changed_line_numbers': sorted(changed), 'all_other_lines_raw_exact': True,
            'only_hash_and_size_fields_changed': True, 'path_quoting_order_and_endings_preserved': True,
            'active_sha256': digest(current), 'original_sha256': digest(old)})
    assert len(metadata_checks) == 3 and total_changes == 27
    for entry in generation['launchers']:
        module_name, callable_name = entry['entry_point_value'].split(':', 1)
        module = importlib.import_module(module_name)
        value = module
        for part in callable_name.split('.'):
            value = getattr(value, part)
        assert callable(value)
        module_path = Path(module.__file__).resolve()
        assert module_path.is_relative_to(E3 / 'Lib/site-packages')
        imports.append({'filename': entry['filename'], 'entry_point': entry['entry_point_value'],
            'module_path': str(module_path), 'module_observation': ordinary(module_path), 'callable': True,
            'direct_function_invocation': False, 'Qt_tool_executed': False if entry['filename'].startswith('pyside6-') else None})
    assert len(imports) == 27 and sum(row['filename'].startswith('pyside6-') for row in imports) == 23
    node = next(item for item in ast.parse(Path(pins['native_runner']['path']).read_text(encoding='utf-8')).body
        if isinstance(item, ast.FunctionDef) and item.name == 'run_owned')
    run_owned_AST_sha256 = digest(ast.dump(node, include_attributes=False).encode())
    assert run_owned_AST_sha256 == 'f0c7a75e64b42896346fa4985a266936860bba26bf76823910d62c80489f44f9'
    exec(compile(ast.Module(body=[node], type_ignores=[]), pins['native_runner']['path'], 'exec'), globals())
    FIX = O / ('independent-native-fixtures-' + uuid.uuid4().hex[:12])
    support.fs.safe_components(FIX, allow_missing=True)
    FIX.mkdir(exist_ok=False)
    for name in ('pip.exe', 'pip3.exe', 'pip3.12.exe'):
        receipt = run_owned('independent-' + name.replace('.', '-'), E3 / 'Scripts' / name,
            ['--disable-pip-version-check', '--version'], 0)
        assert 'pip 25.0.1' in receipt['stdout'] and '(python 3.12)' in receipt['stdout']
        assert str(E3 / 'Lib/site-packages/pip') in receipt['stdout']
        assert 'CETA_Intelligence_Operating_System_Build_Package' not in receipt['stdout']
    schema = FIX / 'schema.json'
    valid = FIX / 'valid.json'
    invalid = FIX / 'invalid.json'
    write_new(schema, {'type': 'object', 'required': ['measured'], 'properties': {'measured': {'type': 'integer', 'minimum': 1}}, 'additionalProperties': False})
    write_new(valid, {'measured': 29})
    write_new(invalid, {'measured': 'invalid'})
    positive = run_owned('independent-schema-valid', E3 / 'Scripts/jsonschema.exe', ['-i', str(valid), str(schema)], 0)
    negative = run_owned('independent-schema-invalid', E3 / 'Scripts/jsonschema.exe', ['-i', str(invalid), str(schema)], 1)
    assert 'is not of type' in negative['stderr'] + negative['stdout']
    assert 'Fatal error in launcher' not in positive['stdout'] + positive['stderr']
    assert len(commands) == 5 and all(row['oracle_passed'] and row['owner_closed'] and row['observed_empty_job'] for row in commands)
    print(json.dumps({'independently_executed_native_CLI': 5, 'owners_closed': 5, 'callable_entry_imports': 27, 'Qt_tools_unexecuted': 23}), flush=True)
    fresh_after = support.snapshot_tree()
    write_new(O / 'environment-independent-after.json', fresh_after)
    assert ordinary_rows(fresh_after) == ordinary_rows(fresh_before) == expected
    candidate_after = qualified_files_under(Q)
    assert candidate_after == candidate_before
    source_after = {relative: ordinary(F / relative) for relative in source_expected}
    assert source_after == source_before
    root_commands = root_verification['commands']
    assert root_verification['exit_status'] == 0 and len(root_commands) == 5 and len(root_verification['imports']) == 27
    root_command_checks = []
    for row in root_commands:
        fixture = Path(row['fixture'])
        assert fixture.is_relative_to(ROOT_OUT)
        assert row['oracle_passed'] and row['owner_closed'] and row['observed_empty_job']
        assert row['actual_exit_status'] == row['expected_exit_status']
        assert sha(fixture / 'stdout.bin') == row['stdout_sha256'] and sha(fixture / 'stderr.bin') == row['stderr_sha256']
        assert read(fixture / 'receipt.json') == row
        assert ordinary(Path(row['image']['path'])) == row['image']
        root_command_checks.append({'label': row['label'], 'receipt_sha256': sha(fixture / 'receipt.json'),
            'raw_stream_hashes_reproduced': True, 'closed_empty_job_claim_inspected': True, 'pid': row['pid'], 'creation_time_100ns': row['creation_time_100ns']})
    assert len({(row['pid'], row['creation_time_100ns']) for row in commands}) == 5
    assert {row['label'] for row in commands}.isdisjoint({row['label'] for row in root_commands})
    proof = {'schema_version': 1, 'executor': '/root/pressure_review', 'started_at': started, 'finished_at': utc(),
        'environment_root': str(E3), 'source_root': str(F), 'pins': pins, 'actual_root_claim': {key: claim[key] for key in ('executor_id', 'workspace', 'input_hash', 'claimed_at')},
        'payload_observations': payload_observations, 'candidate_before': candidate_before, 'candidate_after': candidate_after,
        'source_before': source_before, 'source_after': source_after, 'expected_environment_files': expected,
        'fresh_environment_before_sha256': sha(O / 'environment-independent-before.json'), 'fresh_environment_after_sha256': sha(O / 'environment-independent-after.json'),
        'launcher_checks': launcher_checks, 'metadata_checks': metadata_checks, 'callable_imports': imports,
        'commands': commands, 'root_command_inspection': root_command_checks, 'native_fixture_root': str(FIX),
        'reused_native_custodian_AST_sha256': run_owned_AST_sha256, 'custody_source': jobs_source,
        'independent_safe_cli_invocations': 5, 'ordinary_environment_files_freshly_rehashed': 3601,
        'unchanged_unrelated_ordinary_files': 3571, 'native_originals_verified': 30, 'source_payloads_unchanged': 279,
        'frozen_candidate_files_unchanged': 33, 'all_ordinary_before_after_exact': True, 'all_handles_closed': True,
        'limitations': ['23 Qt entry functions imported without invocation; no Qt tool operational qualification',
            'Root job closure facts inspected in its immutable receipts; own five jobs independently executed and observed empty before close',
            'Ordinary-file hashes and endpoint native identities verified; directory allocation-size variation and continuous privileged-principal custody remain unqualified',
            'Aggregate PySide6 distribution metadata remains unavailable; underlying callable modules are independently identified',
            'No Source product mutation, configuration/package/interpreter update, external capture, policy activation or installation'],
        'exit_status': 0}
    write_new(O / 'independent-verification.json', proof)
    print(json.dumps({'exit_status': 0, 'proof_sha256': sha(O / 'independent-verification.json'), 'independent_native_CLI': 5, 'ordinary_files': 3601, 'source_files_unchanged': 279}), flush=True)
except BaseException as error:
    write_new(O / 'independent-verification-failure.json', {'schema_version': 1, 'executor': '/root/pressure_review', 'recorded_at': utc(),
        'error_type': type(error).__name__, 'error': str(error), 'commands': commands, 'imports': imports, 'exit_status': 1})
    raise
