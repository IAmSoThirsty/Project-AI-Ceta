"""Read-only frozen-candidate verification and byte-exact owned execution replica."""
from pathlib import Path
import json,sys
P=Path('T:/00-Active/Project-AI-CETA');Q=P/'.agents/et1-20261014';BASE=P/'.agents/runtime/et1-20261014';D=BASE/'independent-review';M=D/'replica';RUN='et1-20261014'
sys.path.insert(0,str(P/'.agents/runtime/ka1-20261014'));import ka1_support as s
s.Q=Q;s.R=D;s.RUN=RUN
sys.path.insert(0,str(P/'.agents/runtime/re-foundation3-20261014'));import foundation_support as copy
copy.Q=Q;copy.R=D
assert s.sha(Q/'TRANSFER-MANIFEST.json')=='ba5f5ceea225d9b1b3f96cce04bd4f55ee24f8ad23a8d222fcd1fbd136db9cec'
assert s.sha(BASE/'implement.json')=='5e2528ae48b18b492f36f6208c2cd24797ef41a1b9298ec2e6d7ba4b84305f19'
claim=json.loads((BASE/RUN/'claims.json').read_text())['review'];assert claim['executor_id']==s.ACTOR
manifest=json.loads((Q/'TRANSFER-MANIFEST.json').read_text())
original={name:s.ordinary(Q/name) for name in manifest['payloads']}
for name,row in manifest['payloads'].items():
    expected=row.get('candidate',row)
    assert original[name]['sha256']==expected.get('sha256',expected.get('candidate_sha256'))
    assert original[name]['native_identity']==expected.get('native_identity',expected.get('candidate_native_identity'))
reference=manifest['Source290_before'];assert s.sha(P/reference['repository_relative_path'])==reference['sha256']
source=json.loads((P/reference['repository_relative_path']).read_text())['Source290']
assert type(source) is dict and len(source)==290
assert all(s.ordinary(P/name)==row for name,row in source.items())
M.mkdir(exist_ok=False)
replica={name:copy.bytes_copy(Q/name,M/name,row) for name,row in original.items()}
assert all(row['sha256']==original[name]['sha256'] for name,row in replica.items())
assert s.sha(P/'.agents/runtime/ka1-20261014/independent-root-review/review.json')=='4e7181fd6c0912ad26e30992fc781703c8b3f67b162a1159af8fa2d28f0e7dbf'
s.write_new(D/'PREPARATION.json',dict(recorded_at=s.utc(),review_claim=claim,manifest_sha256=s.sha(Q/'TRANSFER-MANIFEST.json'),
    original_candidate=original,replica=replica,Source290=source,python_image=s.ordinary(s.PY),
    authorship_disclosure='Reviewer authored KA1 dependency; prior distinct Root KA1 review is dependency evidence. Review independently assesses ET1 four-path delta and consumed-permit/outcome integration.',
    KA1_root_review=s.reference(P/'.agents/runtime/ka1-20261014/independent-root-review/review.json'),
    execution='Exact payload bytes in reviewer-owned replica; native identities and DLL/module roots differ explicitly. Original frozen Q stays read-only; actual existing service/crash ROOT guards are unchanged.',
    Source_application=False,native_effect_invocation=False))
print(json.dumps(dict(candidate_payloads=len(original),byte_exact_replica=True,Source290_retained=True,actual_review_claimed=True)),flush=True)
