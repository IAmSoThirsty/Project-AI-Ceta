"""Fresh whole dependency/parent/E3 endpoint proof before AC2 freeze."""
from ac2_support import *

inputs = json.loads((R / 'source-inputs.json').read_text())
source_after = {name: ordinary(F / name) for name in inputs['source_payloads']}
assert source_after == inputs['source_payloads']
parent = json.loads((PARENT / 'TRANSFER-MANIFEST.json').read_text())
assert sha(PARENT / 'TRANSFER-MANIFEST.json') == 'dbb2aec8f60a72fde258dd972c260dccc8beaed564812ca8147671ba0a4a4160'
parent_after = {name: ordinary(PARENT / name) for name in parent['payloads']}
assert parent_after == inputs['parent_payloads']
for name,row in parent['candidate_fixture_members'].items(): assert ordinary(PARENT / name) == row

env_before_path = PRIOR_R / 'independent-review/environment-after.json'
env_before = json.loads(env_before_path.read_text()); env_root = PY.parent.parent
files, directories, pending = {}, {}, [env_root]
started = utc()
while pending:
    directory = pending.pop(); info = fs.lstat(directory); assert not fs.reparse(info)
    directories[directory.relative_to(env_root).as_posix()] = fs.file_identity(info)
    with os.scandir(directory) as children:
        for entry in children:
            path = directory / entry.name; info = fs.lstat(path); assert not fs.reparse(info)
            if stat.S_ISDIR(info.st_mode): pending.append(path)
            elif stat.S_ISREG(info.st_mode):
                identity = fs.file_identity(info)
                with fs.open_source(path, exclusive=True) as stream: value = hashlib.file_digest(stream, 'sha256').hexdigest()
                assert fs.file_identity(fs.lstat(path)) == identity
                files[path.relative_to(env_root).as_posix()] = {'sha256': value, 'native_identity': identity}
            else: raise AssertionError('nonordinary E3 member')
assert files == env_before['ordinary_files'] and len(files) == 3601
assert set(directories) == set(env_before['directories'])
directory_sizes = []
for name,row in directories.items():
    before = env_before['directories'][name]
    assert {key:value for key,value in row.items() if key != 'bytes'} == {
           key:value for key,value in before.items() if key != 'bytes'}
    if row['bytes'] != before['bytes']:
        directory_sizes.append({'relative_path': name, 'before': before['bytes'], 'after': row['bytes']})
write_new(R / 'environment-after.json', {'started_at': started, 'finished_at': utc(),
    'root': str(env_root), 'ordinary_files': files, 'directories': directories})
write_new(R / 'input-conservation.json', {'observed_at': utc(), 'source_before': reference(R / 'source-inputs.json'),
    'source_after': source_after, 'all_source_290_bytes_native_identities_exact': True,
    'parent_manifest': reference(PARENT / 'TRANSFER-MANIFEST.json'), 'parent_normative_after': parent_after,
    'parent_retained_fixture_members_exact': len(parent['candidate_fixture_members']),
    'environment_baseline': reference(env_before_path), 'environment_after': reference(R / 'environment-after.json'),
    'environment_baseline_qualification': 'Reused exact sealed AC1 final census observed before AC2 began; current endpoint rehashed independently.',
    'E3_ordinary_files_bytes_native_identities_membership_exact': 3601,
    'E3_directory_nonsize_metadata_and_identity_exact': True, 'directory_size_differences': directory_sizes,
    'no_uninterrupted_custody_claim': True})

# Correct an overbroad strength sentence in the sealed AC1 review without
# changing that historical record. The error2 receipt retained setup but no
# immediate post-attempt sentinel census. Capture the later endpoint explicitly.
old_probe = json.loads((PRIOR_R / 'independent-review/original-r1.json').read_text())
receipts = list((PRIOR_R / 'independent-review/native-fixtures').glob('*/native-test-final.json'))
assert len(receipts) == 1
probe = json.loads(receipts[0].read_text()); before_sentinels = probe['setup']['protected_before']
after_sentinels = {name: ordinary(Path(name)) for name in before_sentinels}
assert before_sentinels == after_sentinels
write_new(R / 'prior-review-sentinel-qualification.json', {'observed_at': utc(),
    'historical_review': reference(PRIOR_R / 'independent-review/REVIEW-FINDINGS.json'),
    'historical_probe': reference(receipts[0]), 'protected_after_now': after_sentinels,
    'exact_current_endpoint_conservation': True,
    'correction': 'The AC1 strength sentence about canary equality was broader than the then-captured error2 receipt, which omitted an immediate protected_after field. This later read establishes only the current endpoint against the preserved pre-attempt setup, not a missing earlier observation.'})
print(json.dumps({'source_payloads_exact': len(source_after), 'parent_payloads_exact': len(parent_after),
                  'E3_files_exact': len(files), 'directory_size_only_differences': len(directory_sizes),
                  'earlier_canary_endpoint_now_verified': len(after_sentinels)}), flush=True)
