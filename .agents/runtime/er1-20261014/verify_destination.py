"""Verify actual E3 replacement bytes, originals and safely owned native CLI calls."""
from pathlib import Path
import ast
import hashlib
import importlib
import importlib.util
import json
import msvcrt
import os
import sys
import time
import uuid

R = Path(__file__).resolve().parent
F = R.parents[2]
Q = F / '.agents/er1-20261014'
E3 = F / '.agents/source-assembly-20261014T021300Z/.agents/e3'
OUT = R / 'active-application'
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path.insert(0, str(R))
assert sha(R / 'er1_support.py') == '38721b1fa0c112f568a4e957b5ae3a1ecd747645c83ec5882228947805a198d5'
import er1_support as support
sys.path.insert(0, str(F / 'src'))
from ceta.supervisor.windows_jobs import WindowsOwnedProcess
digest = lambda data: hashlib.sha256(data).hexdigest()
utc = support.utc
jobs_source = support.ordinary(F / 'src/ceta/supervisor/windows_jobs.py')
commands = []
imports = []
started = utc()
claim = read(R / 'er1-20261014/claims.json')['integrate']
assert claim['executor_id'] == '/root' and claim['workspace'] == str(E3)
manifest_path = Q / 'TRANSFER-MANIFEST.json'
assert sha(manifest_path) == '7325582b9fa18972dc2e6337e66e55fa3c7ae1ee5db600824aedeca58bb73f83'
manifest = read(manifest_path)
journal_path = OUT / 'APPLIED.json'
journal = read(journal_path)
assert journal['claim_input_hash'] == claim['input_hash'] and len(journal['completed']) == 30
assert len(journal['before_images']) == 30 and journal['manifest_sha256'] == sha(manifest_path)
assert sha(OUT / 'environment-before.json') == journal['environment_before_sha256']
assert sha(OUT / 'environment-after.json') == journal['environment_after_sha256']
before = read(OUT / 'environment-before.json')
published = read(OUT / 'environment-after.json')
expected = {row['relative_path']: row for row in published['members'] if row['kind'] == 'ordinary_file'}
assert len(expected) == 3601
originals = {row['relative_path']: row for row in journal['before_images']}
for row in manifest['payloads']:
    target = Path(row['source_path'])
    relative = target.relative_to(E3).as_posix()
    assert sha(target) == sha(Q / row['candidate_relative_path']) == row['candidate_sha256']
    preserved = originals[relative]
    native = OUT / 'native-backups' / (relative + '.original')
    logical = OUT / 'before' / (relative + '.source')
    assert sha(native) == sha(logical) == row['source_sha256'] == preserved['sha256']
    with support.fs.open_source(support.fs.safe_components(native), exclusive=True) as stream:
        facts = os.fstat(stream.fileno())
    assert (facts.st_dev, facts.st_ino, facts.st_mode, facts.st_size, facts.st_mtime_ns) == (
        preserved['device'], preserved['inode'], preserved['mode'], preserved['bytes'], preserved['mtime_ns'])
current = support.snapshot_tree()
assert {row['relative_path']: row for row in current['members'] if row['kind'] == 'ordinary_file'} == expected
generation = read(R / 'candidate-generation.json')
inventory = read(R / 'launcher-inventory-r2.json')
rows = {row['filename']: row for row in inventory['launchers']}
assert len(rows) == 27
assert sha(R / 'candidate-generation.json') == manifest['generation']['sha256']
assert sha(R / 'launcher-inventory-r2.json') == manifest['current_inventory']['sha256']
for entry in generation['metadata']:
    target = E3 / entry['source_relative_path']
    assert target.read_bytes() == (F / entry['candidate']['repository_relative_path']).read_bytes()
for entry in generation['launchers']:
    raw = (E3 / entry['source_relative_path']).read_bytes()
    original = rows[entry['filename']]
    n = original['stub_bytes']
    assert digest(raw[:n]) == entry['stub_sha256']
    assert raw[n:raw.index(b'\n', n) + 1].decode().strip() == '#!' + str(E3 / 'Scripts/python.exe')
    module_name, callable_name = entry['entry_point_value'].split(':', 1)
    module = importlib.import_module(module_name)
    target = module
    for part in callable_name.split('.'):
        target = getattr(target, part)
    assert callable(target)
    actual_path = Path(module.__file__).resolve()
    assert actual_path.is_relative_to(E3 / 'Lib/site-packages')
    imports.append({'filename': entry['filename'], 'entry_point': entry['entry_point_value'],
        'module_path': str(actual_path), 'module_sha256': sha(actual_path), 'callable': True,
        'invoked': entry['filename'] in {'pip.exe', 'pip3.exe', 'pip3.12.exe', 'jsonschema.exe'}})
FIX = OUT / ('destination-native-fixtures-' + uuid.uuid4().hex[:12])
FIX.mkdir(exist_ok=False)
# Exact reuse of the already executed native job custodian. Its global fixture
# and evidence writer bindings below remain confined to this new runtime child.
runner_path = R / 'run_staged_tests_r2.py'
assert sha(runner_path) == 'a566a22d7f4e52c40a7848d18d5ea66e1be57b5c09b672d063fe34663a2bef19'
tree = ast.parse(runner_path.read_text(encoding='utf-8'))
node = next(item for item in tree.body if isinstance(item, ast.FunctionDef) and item.name == 'run_owned')
exec(compile(ast.Module(body=[node], type_ignores=[]), str(runner_path), 'exec'), globals())
write_new = support.write_new
ordinary = support.ordinary
try:
    for name in ('pip.exe', 'pip3.exe', 'pip3.12.exe'):
        receipt = run_owned('active-' + name.replace('.', '-'), E3 / 'Scripts' / name,
            ['--disable-pip-version-check', '--version'], 0)
        assert 'pip 25.0.1' in receipt['stdout'] and '(python 3.12)' in receipt['stdout']
        assert str(E3 / 'Lib/site-packages/pip') in receipt['stdout']
    schema = FIX / 'schema.json'
    valid = FIX / 'valid.json'
    invalid = FIX / 'invalid.json'
    schema.write_text(json.dumps({'type': 'object', 'required': ['value'],
        'properties': {'value': {'type': 'integer'}}, 'additionalProperties': False}), encoding='utf-8')
    valid.write_text('{"value": 17}', encoding='utf-8')
    invalid.write_text('{"value": "wrong"}', encoding='utf-8')
    run_owned('active-schema-valid', E3 / 'Scripts/jsonschema.exe', ['-i', str(valid), str(schema)], 0)
    run_owned('active-schema-invalid', E3 / 'Scripts/jsonschema.exe', ['-i', str(invalid), str(schema)], 1)
    after = support.snapshot_tree()
    assert {row['relative_path']: row for row in after['members'] if row['kind'] == 'ordinary_file'} == expected
    assert len(commands) == 5 and all(row['owner_closed'] and row['observed_empty_job'] for row in commands)
    result = {'schema_version': 1, 'started_at': started, 'finished_at': utc(), 'environment_root': str(E3),
        'manifest_sha256': sha(manifest_path), 'application_journal_sha256': sha(journal_path),
        'verification_script_sha256': sha(Path(__file__)), 'custody_source': jobs_source,
        'reused_native_runner_sha256': sha(runner_path), 'candidate_paths': 30, 'native_originals': 30,
        'ordinary_environment_files': 3601, 'unrelated_ordinary_files_preserved': 3571,
        'environment_files_unchanged_during_verification': True, 'imports': imports, 'commands': commands,
        'expected_environment_files': expected, 'safe_native_cli_invocations': 5,
        'limitations': ['23 Qt GUI/server/deployment functions are imported but remain unexecuted',
            'Aggregate PySide6 distribution metadata remains unavailable',
            'Directory stat allocation-size variations are separate from ordinary-file conservation'],
        'exit_status': 0}
    support.write_new(OUT / 'destination-verification.json', result)
    print(json.dumps({'actual_native_cli_invocations': 5, 'native_originals': 30,
        'unchanged_environment_files': 3601, 'receipt_sha256': sha(OUT / 'destination-verification.json')}), flush=True)
except BaseException as error:
    try:
        support.write_new(OUT / 'destination-verification-failure.json', {'recorded_at': utc(),
            'error_type': type(error).__name__, 'error': str(error), 'commands': commands, 'exit_status': 1})
    except BaseException:
        pass
    raise
