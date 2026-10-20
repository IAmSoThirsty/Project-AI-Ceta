"""Read-only comparison with the actual accepted ER1 native environment cut."""
from ac3_support import *
baseline = F / '.agents/runtime/er1-20261014/active-application/environment-after.json'
accepted = F / '.agents/runtime/er1-20261014/actual-acceptance.json'
record = json.loads(baseline.read_text()); acceptance = json.loads(accepted.read_text())
assert acceptance['sequence'] == 13 and acceptance['claims'] == {}
assert set(acceptance['actual_states'].values()) == {'SUCCEEDED'}
root = Path(record['source_root']); assert root == PY.parents[1]
expected = {row['relative_path']: row for row in record['members']}
started = utc(); observations, directory_size_differences = {}, []
for name, row in expected.items():
    path = root / name
    if row['kind'] == 'ordinary_file':
        observed = ordinary(path)
        assert observed['sha256'] == row['sha256'] and observed['bytes'] == row['bytes']
        assert observed['native_identity'] == row['native_identity'], name
        observations[name] = observed
    else:
        info = fs.lstat(fs.safe_components(path)); assert stat.S_ISDIR(info.st_mode) and not fs.reparse(info)
        current = fs.file_identity(info); prior = row['native_identity']
        assert {k: v for k, v in current.items() if k != 'bytes'} == {k: v for k, v in prior.items() if k != 'bytes'}, name
        if current['bytes'] != prior['bytes']:
            directory_size_differences.append({'relative_path': name, 'before_bytes': prior['bytes'], 'current_bytes': current['bytes']})
actual_names = set()
for directory, directories, files in os.walk(fs.io_path(root), followlinks=False):
    normal = root / Path(directory).relative_to(Path(fs.io_path(root)))
    for name in directories + files:
        actual_names.add((normal / name).relative_to(root).as_posix())
assert actual_names == set(expected)
root_identity = fs.file_identity(fs.lstat(root)); prior_root = record['root_native_identity']
assert {k: v for k, v in root_identity.items() if k != 'bytes'} == {k: v for k, v in prior_root.items() if k != 'bytes'}
write_new(R / 'environment-final.json', {'started_at': started, 'finished_at': utc(),
    'accepted_after': reference(baseline), 'accepted_lifecycle': reference(accepted),
    'environment_root': str(root), 'ordinary_files': len(observations),
    'ordinary_bytes': sum(row['bytes'] for row in observations.values()),
    'ordinary_file_bytes_identities_and_membership_exact': True, 'observations': observations,
    'directory_size_differences': directory_size_differences,
    'directory_identity_and_nonsize_metadata_exact': True, 'all_membership_exact': True, 'exit_status': 0,
    'qualification': 'Read-only comparison against actual accepted ER1 post-publication cut. Ordinary content/native identities and complete membership exact; directory size variation retained separately.'})
print(json.dumps({'ordinary_files': len(observations), 'directory_size_differences': len(directory_size_differences),
    'sha256': sha(R / 'environment-final.json')}), flush=True)
