"""Read-only actual E3 bytes/native identities; directory size drift qualified."""
from ac_support import *

assert len(sys.argv) == 2 and sys.argv[1] in ('before', 'after')
label = sys.argv[1]
base = PY.parent.parent
files, directories, pending = {}, {}, [base]
started = utc()
while pending:
    directory = pending.pop()
    info = fs.lstat(directory); assert not fs.reparse(info)
    directories[directory.relative_to(base).as_posix()] = fs.file_identity(info)
    with os.scandir(directory) as children:
        for entry in children:
            path = directory / entry.name; info = fs.lstat(path)
            assert not fs.reparse(info)
            if stat.S_ISDIR(info.st_mode): pending.append(path)
            elif stat.S_ISREG(info.st_mode):
                identity = fs.file_identity(info)
                with fs.open_source(path, exclusive=True) as stream:
                    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                assert fs.file_identity(fs.lstat(path)) == identity
                files[path.relative_to(base).as_posix()] = {'sha256': digest, 'native_identity': identity}
            else: raise AssertionError('nonordinary E3 member')
assert len(files) == 3601
record = {'started_at': started, 'finished_at': utc(), 'root': str(base),
          'ordinary_files': files, 'directories': directories, 'file_count': len(files),
          'bytes': sum(row['native_identity']['bytes'] for row in files.values()), 'label': label}
write_new(D / ('environment-' + label + '.json'), record)
if label == 'after':
    old = json.loads((D / 'environment-before.json').read_text())
    assert old['ordinary_files'] == files
    assert set(old['directories']) == set(directories)
    differences = []
    for name, now in directories.items():
        prior = old['directories'][name]
        if prior != now:
            assert {key:value for key,value in prior.items() if key != 'bytes'} == {
                key:value for key,value in now.items() if key != 'bytes'}
            differences.append({'relative_path': name, 'before_bytes': prior['bytes'], 'after_bytes': now['bytes']})
    write_new(D / 'environment-conservation.json', {
        'before': reference(D / 'environment-before.json'), 'after': reference(D / 'environment-after.json'),
        'ordinary_files_bytes_native_identities_membership_exact': True, 'ordinary_files': len(files),
        'bytes': record['bytes'], 'directory_identity_and_nonsize_metadata_exact': True,
        'directory_size_differences': differences,
        'qualification': 'Directory size observations may vary; ordinary-file and non-size directory conservation proved separately'})
print(json.dumps({'label': label, 'ordinary_files': len(files), 'bytes': record['bytes']}), flush=True)
