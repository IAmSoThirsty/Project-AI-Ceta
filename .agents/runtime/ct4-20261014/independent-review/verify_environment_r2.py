"""Read-only ordinary E3 conservation against the actual accepted ER1 cut."""
from ct4_support import *
expected_path=F/'.agents/runtime/er1-20261014/active-application/environment-after.json'
expected=read(expected_path)
declared={row['relative_path']:{key:row[key] for key in ('sha256','native_identity','bytes')} for row in expected['members'] if row['kind']=='ordinary_file'}
assert len(declared)==3601 and expected['ordinary_bytes']==sum(row['bytes'] for row in declared.values())
started=utc();observed={};reparse=[];stack=[E3]
while stack:
    parent=stack.pop()
    with os.scandir(fs.io_path(parent)) as entries:
        for entry in entries:
            path=parent/entry.name;info=entry.stat(follow_symlinks=False)
            if fs.reparse(info):reparse.append(path.relative_to(E3).as_posix())
            elif stat.S_ISDIR(info.st_mode):stack.append(path)
            elif stat.S_ISREG(info.st_mode):observed[path.relative_to(E3).as_posix()]=ordinary(path)
            else:raise AssertionError(('UNEXPECTED_ENVIRONMENT_ENTRY',str(path)))

if observed!=declared:
    save(V/'environment-drift.json',{'accepted_before':ref(expected_path),'added':sorted(set(observed)-set(declared)),'missing':sorted(set(declared)-set(observed)),'changed':{k:{'accepted':declared[k],'current':observed[k]} for k in set(observed)&set(declared) if observed[k]!=declared[k]}})
assert observed==declared
git=subprocess.run(['git','status','--short','--untracked-files=no'],cwd=F,capture_output=True,check=True)
with (V/'git-status-before-review-completion.txt').open('xb') as out:out.write(git.stdout)
save(V/'environment-conservation.json',{'executor':ACTOR,'started_at':started,'finished_at':utc(),'environment_root':str(E3),
    'accepted_environment_after':ref(expected_path),'ordinary_files':len(observed),'ordinary_bytes':sum(row['bytes'] for row in observed.values()),
    'ordinary_bytes_native_identities_and_membership_equal_to_accepted_ER1':True,'ordinary_native':observed,'reparse_not_followed':reparse,
    'git_dirty_status':ref(V/'git-status-before-review-completion.txt'),'writes_in_E3':[],'directory_size_or_mtime_equality_claimed':False,'exit_status':0})
print(json.dumps({'ordinary_files':3601,'ordinary_bytes':sum(row['bytes'] for row in observed.values()),'proof_sha256':sha(V/'environment-conservation.json'),'exit_status':0}),flush=True)
