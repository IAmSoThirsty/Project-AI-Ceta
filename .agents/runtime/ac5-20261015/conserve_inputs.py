"""Read-only Source and installed-E3 conservation, separate from runtime claims."""
from ac_support import *
inputs = json.loads((R / 'SOURCE-INPUTS.json').read_text())
source = {name: ordinary(F / name) for name in inputs['Source290']}
assert source == inputs['Source290'] and len(source) == 290
stage = json.loads((R / 'STAGED-INPUTS.json').read_text())
for name, before in stage['payloads'].items():
    if name not in inputs['eligible_author_paths']: assert ordinary(Q / name) == before
baseline_path = F / '.agents/runtime/er1-20261014/independent-destination/environment-independent-after.json'
baseline = json.loads(baseline_path.read_text()); root = PY.parent.parent
assert Path(baseline['source_root']) == root
expected = {row['relative_path']: row for row in baseline['members'] if row['kind'] == 'ordinary_file'}
files, directories, pending = {}, {}, [root]; started = utc()
while pending:
    directory = pending.pop(); info = fs.lstat(directory); assert not fs.reparse(info)
    directories[directory.relative_to(root).as_posix()] = fs.file_identity(info)
    with os.scandir(directory) as children:
        for entry in children:
            path = directory / entry.name; info = fs.lstat(path); assert not fs.reparse(info)
            if stat.S_ISDIR(info.st_mode): pending.append(path)
            elif stat.S_ISREG(info.st_mode): files[path.relative_to(root).as_posix()] = ordinary(path)
            else: raise AssertionError('Nonordinary E3 member')
assert set(files) == set(expected) and len(files) == 3601
for name, row in files.items():
    assert row['sha256'] == expected[name]['sha256'] and row['native_identity'] == expected[name]['native_identity']
assert sum(row['bytes'] for row in files.values()) == 231026067
write_new(R / 'environment-after.json', {'started_at': started, 'finished_at': utc(),
    'ordinary_files': files, 'directories': directories, 'baseline': reference(baseline_path),
    'directory_qualification': 'Current observations only; no full directory metadata equality claim.'})
write_new(R / 'input-conservation.json', {'recorded_at': utc(), 'Source290_before': reference(R / 'SOURCE-INPUTS.json'),
    'Source290_after': source, 'Source290_bytes_native_identities_exact': True,
    'E3_ordinary_files_exact': 3601, 'E3_ordinary_bytes': 231026067,
    'environment_after': reference(R / 'environment-after.json'), 'Source_application': False,
    'unmodified_staged_dependency_payloads': 292})
print(json.dumps({'Source': 290, 'E3_ordinary_files': 3601, 'dependency_payloads_exact': 292}))
