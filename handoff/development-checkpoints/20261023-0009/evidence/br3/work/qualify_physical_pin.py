"""Read-only physical long-path pin qualification; create-only result in BR3 work."""
from pathlib import Path
import hashlib,json,sys
import complete_observer as o
W=Path(__file__).resolve().parent;B=W.parent;F=Path('T:/00-Active/Project-AI-CETA');R2=F/'.agents/runtime/oq23/br2/work'
state=json.loads((B/'control/ceta-br23-r3/state.json').read_bytes());claim=state['nodes']['implement']['claim']
assert claim['executor_id']=='/root/broader_successor_author' and claim['workspace']==str(W)
assert sys.platform=='win32'
old=json.loads((R2/'MANIFEST.json').read_bytes())
name,expected=next((name,record) for name,record in old['work_observation'].items() if record['kind']=='file' and len(str(R2/name))>260)
path=R2/name;before=o.stable(path);after=o.stable(path)
assert before==after==expected
failed=json.loads((W/'PIN-PRIOR-PROCESS.json').read_bytes());assert failed['exit_status']==1
value=dict(path=str(path),logical_path_length=len(str(path)),physical_path=str(o.physical(path)),
    expected=expected,before=before,after=after,full_native_metadata_and_bytes_exact=True,
    comparison_via_complete_extended_reader=True,canonical_tests_executed=0,old_bytes_modified=False,
    failed_prior_pin_actual_exit_status=1,failed_process_sha256=hashlib.sha256((W/'PIN-PRIOR-PROCESS.json').read_bytes()).hexdigest(),
    focused_qualification=True,full_product_acceptance=False)
with (W/'PHYSICAL-PIN-QUALIFICATION.json').open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2)
print(json.dumps(dict(qualified=True,logical_path_length=len(str(path)),actual_files_written_only_inside_BR3_work=True)))
