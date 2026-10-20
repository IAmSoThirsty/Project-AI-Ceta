"""Preserve the old inventory and issue a native-identity corrected supplement."""
from er1_support import *
import copy
old=json.loads((R/'launcher-inventory.json').read_text());corrected=copy.deepcopy(old)
assert sha(R/'launcher-inventory.json')=='c9446a4099517d2bdc3e1a4761c28561f2f3949b7b742c348ae9eddeda574007'
cut=json.loads((R/'E3-drift-r3.json').read_text());members={row['relative_path']:row for row in cut['members'] if row['kind']=='ordinary_file'}
changed=[]
def replace_observation(value):
    fresh=ordinary(Path(value['path']))
    assert fresh['bytes']==value['bytes'] and fresh['sha256']==value['sha256'] and value['native_identity'] is False
    if Path(value['path']).is_relative_to(E3):
        row=members[Path(value['path']).relative_to(E3).as_posix()]
        assert fresh['native_identity']==row['native_identity'] and fresh['sha256']==row['sha256']
    changed.append({'path':value['path'],'prior_native_identity':False,'corrected_native_identity':fresh['native_identity'],'sha256':fresh['sha256']})
    return fresh
for name in ('interpreter','pythonw','base_interpreter'):corrected[name]=replace_observation(old[name])
corrected['installed_script_primitives']=[replace_observation(value) for value in old['installed_script_primitives']]
for row in corrected['launchers']:
    fresh=ordinary(E3/row['relative_path'])
    assert fresh['bytes']==row['bytes'] and fresh['sha256']==row['sha256'] and fresh['native_identity']==row['native_identity']
    row['metadata_files']=[replace_observation(value) for value in row['metadata_files']]
corrected['native_identity_correction']={'observed_at':utc(),'prior_inventory':reference(R/'launcher-inventory.json'),'support_failure':reference(R/'builder-r1-failure.json'),
 'native_identity_field_corrections':changed,'unchanged_fields':'All original27 launcher identities/bytes/hash/main/stub/entrypoints/RECORD rows and whole3601 census are retained. Only mislabeled boolean identity fields in interpreter/primitives/metadata observations are replaced with freshly verified lstat identities.',
 'original_discover_receipt':'Retained historical observation with the explicit native-identity field bug; not rewritten','E3_write_issued':False}
write_new(R/'launcher-inventory-r2.json',corrected)
print(json.dumps({'corrected_inventory_sha256':sha(R/'launcher-inventory-r2.json'),'corrected_fields':len(changed),'launcher_count':27,'E3_file_bytes_changed':0}))
