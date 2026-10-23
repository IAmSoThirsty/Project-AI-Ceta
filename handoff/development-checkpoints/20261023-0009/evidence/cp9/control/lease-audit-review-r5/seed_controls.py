"""Fresh R5 control successor; R4 source/results/rejection remain immutable."""
from pathlib import Path
import hashlib,json
D=Path(__file__).resolve().parent;OLD=D.parent/'lease-audit-review-r4'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((OLD/'MANIFEST.json').read_bytes())
assert sha(OLD/'MANIFEST.json')=='6416f63403de6a408220d6ae64e96a9a4eb48a9541cb3e1cae2ee502cb9524d8'
for rel,pin in manifest['files'].items():assert sha(OLD/rel)==pin['sha256']
newpin='67fc28f556e0657dee127c062aa8228009732c5d7c1ce20751052ca52fc66cae'
assert sha(D.parent/'lease_audit_r5.py')==newpin
controls=(OLD/'review_controls.py').read_text(encoding='utf8')
controls=controls.replace('Independent in-memory R4 controls','Independent in-memory R5 controls')
controls=controls.replace("SCRIPT=D.parent/'lease_audit_r4.py';EXPECTED='894d4c8dfaa4f97d05a5eff625c71924605076c38c0b9c9046eb4228ea0b153f'",
    "SCRIPT=D.parent/'lease_audit_r5.py';EXPECTED='"+newpin+"'")
controls=controls.replace("'independent_lease_audit_r4'","'independent_lease_audit_r5'")
needle="assert set(row['name'] for row in old['cases'])<=set(row['name'] for row in cases)"
assert needle in controls
controls=controls.replace(needle,needle+"\nprior4=json.loads((D.parent/'lease-audit-review-r4/RESULT.json').read_bytes())\nassert [row['name'] for row in prior4['cases']]==[row['name'] for row in cases]")
capture=(OLD/'capture_review.py').read_text(encoding='utf8')
capture=capture.replace("paths=[D.parent/'lease_audit_r4.py',","paths=[D.parent/'lease_audit_r5.py',D.parent/'lease_audit_r4.py',")
capture=capture.replace("('lease-audit-review','lease-audit-review-r3')","('lease-audit-review','lease-audit-review-r3','lease-audit-review-r4')")
for name,value in (('review_controls.py',controls),('capture_review.py',capture)):
    with (D/name).open('x',encoding='utf8',newline='\n') as stream:stream.write(value)
with (D/'SUCCESSOR-SEED.json').open('x',encoding='utf8') as stream:json.dump(dict(
    predecessor_manifest_sha256=sha(OLD/'MANIFEST.json'),predecessor_review_sha256=sha(OLD/'REVIEW.json'),
    controls_source_sha256=sha(D/'review_controls.py'),capture_source_sha256=sha(D/'capture_review.py'),
    reviewed_source_sha256=newpin,prior46_ids_retained=True,prior_rejection_preserved=True),stream,indent=2);stream.write('\n')
print(json.dumps(dict(controls_source_sha256=sha(D/'review_controls.py'),source_sha256=newpin)))
