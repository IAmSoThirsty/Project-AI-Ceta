"""Preserve the first reader failure; narrow only its before/after stat contract."""
from pathlib import Path
import hashlib,json
from datetime import datetime,timezone
O=Path(__file__).resolve().parent
old=O/'verify_native_results.py';new=O/'verify_native_results_r2.py'
raw=old.read_text(encoding='utf8')
before='raw=path.read_bytes();after=path.lstat();assert before==after'
after="raw=path.read_bytes();after=path.lstat();fields=('st_size','st_mtime_ns','st_mode','st_dev','st_ino','st_file_attributes');assert all(getattr(before,k)==getattr(after,k) for k in fields)"
assert raw.count(before)==1
with new.open('x',encoding='utf8') as stream:stream.write(raw.replace(before,after))
record=dict(at=datetime.now(timezone.utc).isoformat(),first_command=['python.exe','-I','-B','-S',str(old)],
    first_tool_chunk_id='974649',first_exit_status=1,
    first_failure='AssertionError at verify_native_results.py:31; whole os.stat_result equality before/after read_bytes',
    old_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),new_sha256=hashlib.sha256(new.read_bytes()).hexdigest(),
    exact_before=before,exact_after=after,
    reason='Whole-stat equality includes access time outside the declared source/native CAS contract. The exact changed field was not captured by the first attempt; its failure alone does not identify a product mismatch.',
    preserved_old_source=True,root_receipts_modified=False,product_or_native_execution=False)
with (O/'VERIFIER-REPAIR.json').open('x',encoding='utf8') as stream:json.dump(record,stream,indent=2);stream.write('\n')
print(json.dumps(record))
