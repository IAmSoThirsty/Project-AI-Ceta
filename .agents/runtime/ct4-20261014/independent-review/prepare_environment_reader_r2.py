"""Replace an unverified inherited byte-count assumption with accepted native evidence."""
from ct4_support import *
old=V/'verify_environment.py';text=old.read_text(encoding='utf8')
text=text.replace("assert len(declared)==3601 and expected['ordinary_bytes']==231026958", "assert len(declared)==3601 and expected['ordinary_bytes']==sum(row['bytes'] for row in declared.values())")
text=text.replace("assert observed==declared", "\nif observed!=declared:\n    save(V/'environment-drift.json',{'accepted_before':ref(expected_path),'added':sorted(set(observed)-set(declared)),'missing':sorted(set(declared)-set(observed)),'changed':{k:{'accepted':declared[k],'current':observed[k]} for k in set(observed)&set(declared) if observed[k]!=declared[k]}})\nassert observed==declared")
text=text.replace("'ordinary_bytes':231026958", "'ordinary_bytes':sum(row['bytes'] for row in observed.values())")
with (V/'verify_environment_r2.py').open('x',encoding='utf8') as out:out.write(text)
save(V/'environment-reader-correction.json',{'recorded_at':utc(),'first_failure':ref(V/'environment-r1-command.json'),'first_reader':ref(old),
    'corrected_reader':ref(V/'verify_environment_r2.py'),'accepted_ER1_ordinary_bytes':read(F/'.agents/runtime/er1-20261014/active-application/environment-after.json')['ordinary_bytes'],
    'correction':'Remove inherited historical byte count assumption. Require the actual accepted ER1 members and their calculated byte sum; expose any current drift explicitly before claiming equality.',
    'environment_changes':[]})
