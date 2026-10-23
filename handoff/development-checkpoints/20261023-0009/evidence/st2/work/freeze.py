"""Freeze complete status preparation; no canonical writes or product execution."""
from pathlib import Path
import ast,json,sys
import status_core as s
W=s.W;S=s.S
assert (W/'BINDING.json').is_file() and not (W/'MANIFEST.json').exists()
b=json.loads((W/'BINDING.json').read_bytes())
for rel,item in b['targets'].items():assert s.sha(W/'candidate'/rel)==item['candidate_sha256']
old=W/'status_core-qualified-snapshot-before-hook-repair.py'
def selected(path):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(path.read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name in ('physical','native','stable','snapshot','file_map')}
assert selected(old)==selected(W/'status_core.py')
controls=json.loads((W/'controls-r6/RESULT.json').read_bytes());assert controls['successful'] and controls['tests_run']==36 and controls['tested_core_sha256']==s.sha(W/'status_core.py')
s.save(W/'DRAFT-REPAIRS.json',dict(independent_preliminary_reviewer='/root/admission_entry_r2',author='/root',formal_acceptance=False,snapshot_algorithm_AST_identical=True,original_qualified_snapshot_core_sha256=s.sha(old),current_core_sha256=s.sha(W/'status_core.py'),controls_result_sha256=s.sha(W/'controls-r6/RESULT.json'),controls=36,all_six_preliminary_findings_fixed=True,freeze_leaf_pins_retained=True,canonical_writes=False,full_product_acceptance=False))
observed=s.snapshot(W,s.F,ignored=frozenset());assert observed['excluded_symlinks']=={}
files={Path(name).relative_to(W.relative_to(s.F)).as_posix():item for name,item in observed['files'].items()}
# All current files are immutable; only explicit later capture outputs are allowed.
manifest=dict(schema_version=1,run_id=s.RUN,work_hashes={name:item['sha256'] for name,item in files.items()},work_file_native=files,work_directory_identity={name:{k:value[k] for k in ('device','inode','mode')} for name,value in observed['directories'].items()},external_pins=b['external_pins'],python_sources=sorted(name for name in files if name.endswith('.py')),canonical_writes=False,test_bodies_executed=False,post_freeze_outputs=['PREPARED.stdout','PREPARED.stderr','PREPARED.json'],full_product_acceptance=False)
s.save(W/'MANIFEST.json',manifest);print(json.dumps(dict(manifest_sha256=s.sha(W/'MANIFEST.json'),files=len(files),directories=len(observed['directories']),source_manifest_sha256=b['new_source_manifest_sha256'])))
