"""Conserve accepted Source, exact reused dependencies and installed E3 files."""
from et_support import *

inputs=json.loads((R/'SOURCE-INPUTS.json').read_text())
source={name:ordinary(F/name) for name in inputs['Source290']}
assert source == inputs['Source290'] and len(source) == 290
stage=json.loads((R/'STAGED-INPUTS.json').read_text())
unchanged=0
for name,before in stage['payloads'].items():
    if name not in inputs['eligible_paths']:
        assert ordinary(Q/name) == before
        unchanged += 1
assert unchanged == 314
baseline_path=F/'.agents/runtime/er1-20261014/independent-destination/environment-independent-after.json'
baseline=json.loads(baseline_path.read_text())
root=PY.parent.parent
assert Path(baseline['source_root']) == root
expected={row['relative_path']:row for row in baseline['members'] if row['kind']=='ordinary_file'}
files, pending={},[root]
started=utc()
while pending:
    directory=pending.pop()
    assert not fs.reparse(fs.lstat(directory))
    with os.scandir(directory) as children:
        for entry in children:
            path=directory/entry.name
            info=fs.lstat(path)
            assert not fs.reparse(info)
            if stat.S_ISDIR(info.st_mode): pending.append(path)
            elif stat.S_ISREG(info.st_mode): files[path.relative_to(root).as_posix()]=ordinary(path)
            else: raise AssertionError('Nonordinary E3 member')
assert set(files) == set(expected) and len(files) == 3601
for name,row in files.items():
    assert row['sha256'] == expected[name]['sha256'] and row['native_identity'] == expected[name]['native_identity']
assert sum(row['bytes'] for row in files.values()) == 231026067
write_new(R/'environment-final.json', {'started_at':started,'finished_at':utc(),
    'ordinary_files':files,'baseline':reference(baseline_path),
    'directory_metadata':'Not claimed equal; ordinary-file membership/bytes/native identities verified.'})
write_new(R/'input-conservation-final.json', {'at':utc(), 'Source290':source,
    'Source290_native_bytes_exact':True,'unmodified_parent_payloads':unchanged,
    'E3_ordinary_files_exact':3601,'E3_ordinary_bytes':231026067,
    'environment':reference(R/'environment-final.json'),'Source_application':False})
print(json.dumps({'Source':290,'E3_ordinary_files':3601,'unchanged_dependencies':unchanged}))
