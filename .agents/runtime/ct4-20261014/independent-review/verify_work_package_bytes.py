"""Verify the raw JSON work_packages member has exactly one character deleted."""
from ct4_support import *
import re
before_path=R/'before/build/progress.json';after_path=Q/'build/progress.json'
def member_bytes(path):
    wire=path.read_bytes();text=wire.decode('utf8')
    matches=list(re.finditer(r'^  "work_packages":\s*',text,re.MULTILINE));assert len(matches)==1
    start=matches[0].end();_,size=json.JSONDecoder(object_pairs_hook=pairs).raw_decode(text[start:])
    return text[start:start+size].encode('utf8')
before=member_bytes(before_path);after=member_bytes(after_path)
old=b'handoff/source_reco3nciliation_20261006_07.md';new=b'handoff/source_reconciliation_20261006_07.md'
assert before.count(old)==1 and after==before.replace(old,new,1) and len(before)==len(after)+1
save(V/'work-package-byte-preservation.json',{'executor':ACTOR,'recorded_at':utc(),'before':ref(before_path),'candidate':ref(after_path),
    'JSON_pointer':'/work_packages/1/evidence_refs/39','exact_raw_before_member_sha256':hashlib.sha256(before).hexdigest(),
    'exact_raw_after_member_sha256':hashlib.sha256(after).hexdigest(),'exact_raw_before_member_bytes':len(before),'exact_raw_after_member_bytes':len(after),
    'only_change':'Delete the one byte 3 from the exact evidence path. Every other byte within the original work_packages JSON member is unchanged.',
    'all_other_work_packages_bytes_and_data_preserved':True,'Source_mutations':[],'candidate_mutations':[],'exit_status':0})
print(json.dumps({'work_packages_raw_bytes':'PASS','proof_sha256':sha(V/'work-package-byte-preservation.json')}))
