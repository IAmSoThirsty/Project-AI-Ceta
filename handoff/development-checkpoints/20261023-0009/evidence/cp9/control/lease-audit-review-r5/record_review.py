"""Freeze bounded independent R5 approval; preserve each earlier rejection."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
D=Path(__file__).resolve().parent;SOURCE=D.parent/'lease_audit_r5.py'
EXPECTED='67fc28f556e0657dee127c062aa8228009732c5d7c1ce20751052ca52fc66cae'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
def save(name,value):
    with (D/name).open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')
assert sha(SOURCE)==EXPECTED
r=json.loads((D/'RESULT.json').read_bytes());p=json.loads((D/'PROCESS.json').read_bytes())
assert r['selected']==r['passed']==46 and r['failed_expectations']==0 and p['exit_status']==0
assert p['prior_and_sources_conserved'] and all(x['passed'] for x in r['cases'])
old=json.loads((D.parent/'lease-audit-review-r4/RESULT.json').read_bytes())
assert [row['name'] for row in r['cases']]==[row['name'] for row in old['cases']]
old_source=(D.parent/'lease_audit_r4.py').read_text(encoding='utf8')
new_source=SOURCE.read_text(encoding='utf8')
old_source=old_source.replace('Read-only bounded lease audit with strict claim mirrors and hash-bound own publication receipts.',
    'Read-only bounded lease audit with complete RUNNING-node custody and hash-bound own publication receipts.')
extra="   assert {n for n,e in state['nodes'].items() if e['state']=='RUNNING'}==set(claims),('recorded RUNNING node missing its persisted claim',str(path))\n"
assert new_source.replace(extra,'')==old_source
prior={label:dict(review_sha256=sha(D.parent/directory/'REVIEW.json'),
    manifest_sha256=sha(D.parent/directory/'MANIFEST.json'),historical_rejection_preserved=True)
    for label,directory in (('R2','lease-audit-review'),('R3','lease-audit-review-r3'),('R4','lease-audit-review-r4'))}
review=dict(schema_version=1,recorded_at=datetime.now(timezone.utc).isoformat(),
    reviewer='/root/broader_successor_author',independent_review=True,decision='approved',
    source=str(SOURCE),source_sha256=EXPECTED,
    assessment='Approved as the bounded current-project lease-audit prerequisite for the exact CP9 publication path; no publication or product acceptance is granted by this review.',
    controls=dict(selected=46,passed=46,failed_expectations=0,actual_process_exit_status=0,
        result_sha256=sha(D/'RESULT.json'),process_sha256=sha(D/'PROCESS.json'),
        controls_sha256=sha(D/'review_controls.py'),all_46_prior_R4_case_ids_and_order_retained=True,
        actual_exact17_packet_validator_used=True,actual_stock_canonical_receipt_hash_used=True,
        normalized_actual_receipt_shape=True,packet_read_seam='Synthetic bytes only'),
    resolved_findings=[dict(id='LEASE-AUDIT-R2-01',status='Claim/node mirror contradictions rejected'),
        dict(id='LEASE-AUDIT-R3-01',status='Own receipt payload/state hashes, refs, run/node/executor identity, integer-zero exits and validation policy enforced'),
        dict(id='LEASE-AUDIT-R4-01',status='Recorded RUNNING nodes without a matching non-null claim now classify unresolved and block clearance')],
    reviewed_semantics=['Pinned packet identity and exact17 scope validated through real exact_git_scope.packet',
        'Own allowance requires exactly one current integrate claim with Root executor and explicit .git workspace',
        'Independent review executor matches stored node and differs from Root; validation executor is Root',
        'Review validation records may be empty; gate records must be nonempty with exact True passed values',
        'Receipt canonical hashes bind payloads to stored node hashes; all statuses require integer zero',
        'Other overlapping Git writers, contradictory mirrors, missing RUNNING custody and existing Git lock files fail closed',
        'Closed nodes without claims and non-Git writers remain consistent with the disclosed bounded policy'],
    prior_rejections=prior,only_behavioral_delta_from_rejected_R4='Complete RUNNING-node set must equal persisted claim keys',
    source_and_prior_conservation=True,canonical_or_coordinator_or_Git_mutation=False,
    real_inventory_or_native_execution=False,claims_verify_gates_invoked=False,
    limitations=['In-memory controlled inventory and packet read seams; no live publication packet or claim created or consumed',
        'Current-project depth<=8 inventory and exact disclosed exclusions; not a machine-wide lease registry or process-liveness determination',
        'Root still must perform actual exact packet review, stock verification, current-claim/lease and Git-lock readbacks, ordinary hook execution and remote/public readbacks',
        'This approval applies only to the exact source hash and bounded prerequisite purpose'],
    global_clearance=False,publication_approval=False,product_acceptance=False)
save('REVIEW.json',review)
external={str(SOURCE):EXPECTED,
    str(D.parent.parent/'work/exact_git_scope.py'):r['exact_scope_source_sha256'],
    str(D.parent.parent/'work/checkpoint_core.py'):sha(D.parent.parent/'work/checkpoint_core.py')}
external.update({path:pin['sha256'] for path,pin in p['source_and_prior_before'].items()})
for path,pin in external.items():assert sha(Path(path))==pin,path
files={path.relative_to(D).as_posix():dict(sha256=sha(path),bytes=path.stat().st_size)
    for path in sorted(D.rglob('*')) if path.is_file()}
save('MANIFEST.json',dict(schema_version=1,reviewer=review['reviewer'],decision='approved',
    source_sha256=EXPECTED,files=files,external_pins=external,independent_review=True,
    actual_process_exit_status=0,publication_approval=False,product_acceptance=False))
print(json.dumps(dict(decision='approved',source_sha256=EXPECTED,review_sha256=sha(D/'REVIEW.json'),
    manifest_sha256=sha(D/'MANIFEST.json'),result_sha256=sha(D/'RESULT.json'),
    process_sha256=sha(D/'PROCESS.json'),frozen_files=len(files))))
