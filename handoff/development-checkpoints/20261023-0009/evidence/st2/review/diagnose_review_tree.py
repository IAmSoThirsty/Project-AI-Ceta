"""Bounded read-only diagnostic inventory; records drift and grants no acceptance."""
from pathlib import Path
import json,os,stat,sys
F=Path('T:/00-Active/Project-AI-CETA');S=F/'.agents/runtime/oq23/st2';R=S/'review';sys.path.insert(0,str(S/'work'));import status_core as s
records=[];files={};errors=[];seen=set()
def visit(path):
    try:
        before=s.native(path);identity=(before['device'],before['inode']);assert identity not in seen;seen.add(identity);assert stat.S_ISDIR(before['mode'])
        with os.scandir(s.physical(path)) as entries:names=sorted(entry.name for entry in entries)
        after_enumeration=s.native(path);records.append(dict(path=str(path),before=before,after_enumeration=after_enumeration))
        for name in names:
            child=path/name;value=s.native(child)
            if stat.S_ISDIR(value['mode']):visit(child)
            else:files[str(child)]=s.stable(child)
        records[-1] if records else None
    except BaseException as fault:errors.append(dict(path=str(path),type=type(fault).__name__,args=fault.args))
visit(R);changes=[item for item in records if item['before']!=item['after_enumeration']]
report=dict(classification='CURRENT_READ_ONLY_DIAGNOSTIC_NOT_VALIDATION',root=str(R),all_directories_visited_without_diagnostic_error=not errors,directories=records,files=files,scalar_changes=changes,errors=errors,original_failed_path='UNKNOWN',original_failure_scalars='NOT_CAPTURED',original_cause='UNKNOWN',no_validation_checks_weakened=True,canonical_test_bodies_executed=0,canonical_fixture_writes=False,canonical_or_Git_writes=False)
with (R/'REVIEW-FULL-DIAGNOSTIC-INVENTORY.json').open('x',encoding='utf8') as stream:json.dump(report,stream,indent=2)
print(json.dumps(dict(diagnostic_only=True,directories=len(records),files=len(files),scalar_changes=len(changes),errors=errors,changed_paths=[item['path'] for item in changes])))
