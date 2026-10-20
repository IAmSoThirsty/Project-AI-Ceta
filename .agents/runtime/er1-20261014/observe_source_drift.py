"""Preserve exact source drift between concurrent read-only observations."""
from er1_support import *
old=json.loads((R/'E3-before.json').read_text());new=snapshot_tree();write_new(R/'E3-drift-r3.json',new)
left={row['relative_path']:row for row in old['members']};right={row['relative_path']:row for row in new['members']}
differences=[{'relative_path':name,'before':left.get(name),'after':right.get(name)} for name in sorted(set(left)|set(right)) if left.get(name)!=right.get(name)]
result={'observed_at':utc(),'before':reference(R/'E3-before.json'),'current':reference(R/'E3-drift-r3.json'),'before_root_native_identity':old['root_native_identity'],'current_root_native_identity':new['root_native_identity'],'differences':differences,'changed_or_new_members':len(differences),'ER1_source_writes_issued':False}
write_new(R/'source-drift-r3.json',result)
print(json.dumps(result,indent=2))
