"""Append final-reader variant that rechecks current E3 ordinary membership."""
from ct4_support import *
prior=V/'readback_and_seal.py';text=prior.read_text(encoding='utf8')
anchor="environment=read(V/'environment-conservation.json');assert all(ordinary(E3/rel)==value for rel,value in environment['ordinary_native'].items())"
assert text.count(anchor)==1
replacement="""environment=read(V/'environment-conservation.json')
current_environment_members=set();environment_stack=[E3]
while environment_stack:
    environment_parent=environment_stack.pop()
    with os.scandir(fs.io_path(environment_parent)) as entries:
        for entry in entries:
            path=environment_parent/entry.name;info=entry.stat(follow_symlinks=False)
            if fs.reparse(info):continue
            if stat.S_ISDIR(info.st_mode):environment_stack.append(path)
            elif stat.S_ISREG(info.st_mode):current_environment_members.add(path.relative_to(E3).as_posix())
            else:raise AssertionError(('UNEXPECTED_ENVIRONMENT_ENTRY',str(path)))
assert current_environment_members==set(environment['ordinary_native'])
assert all(ordinary(E3/rel)==value for rel,value in environment['ordinary_native'].items())"""
text=text.replace(anchor,replacement)
with (V/'readback_and_seal_r2.py').open('x',encoding='utf8') as out:out.write(text)
save(V/'final-reader-lineage.json',{'recorded_at':utc(),'before_reader':ref(prior),'final_reader':ref(V/'readback_and_seal_r2.py'),
    'change':'Re-enumerate current ordinary E3 members without following reparse points, then verify all original hashes/native IDs. No previous reader was executed or failed; no Source/helper/environment change.'})
