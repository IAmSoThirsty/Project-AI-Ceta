"""Read-only qualification of exact accepted E3 ordinary files and core images."""
from pathlib import Path
import json,sys
P=Path('T:/00-Active/Project-AI-CETA');Q=P/'.agents/cpb1-20261014';R=P/'.agents/runtime/cpb1-20261014'
sys.path.insert(0,str(P/'.agents/runtime/ka1-20261014'));import ka1_support as s
s.Q=Q;s.R=R
label=sys.argv[1];proof=P/'.agents/runtime/er1-20261014/independent-destination/environment-independent-after.json'
baseline=json.loads(proof.read_text());root=Path(baseline['source_root']);started=s.utc();observed={}
for row in baseline['members']:
    if row['kind']!='ordinary_file':continue
    value=s.ordinary(root/row['relative_path'])
    assert value['sha256']==row['sha256'] and value['native_identity']==row['native_identity'],row['relative_path']
    observed[row['relative_path']]=value
assert len(observed)==3601
s.write_new(R/(label+'.json'),dict(started_at=started,finished_at=s.utc(),root=str(root),
    baseline=s.reference(proof),ordinary_files=len(observed),ordinary_bytes=sum(v['bytes'] for v in observed.values()),
    members=observed,exact_ordinary_bytes_and_native_identities=True,
    limits='Exact declared3601 ordinary members verified; this does not claim loaded-memory attestation or uninterrupted custody.',exit_status=0))
print(json.dumps(dict(ordinary_files=len(observed),ordinary_bytes=sum(v['bytes'] for v in observed.values()),
    exit_status=0)),flush=True)
