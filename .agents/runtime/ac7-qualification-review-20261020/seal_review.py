"""Seal the independent R3 rejection; does not import host tools or alter source."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys

F=Path('T:/00-Active/Project-AI-CETA')
R=F/'.agents/runtime/ac7-token-contract-20261020'
D=Path(__file__).resolve().parent
assert D==F/'.agents/runtime/ac7-qualification-review-20261020'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value):
    with (D/name).open('x',encoding='utf8') as out:json.dump(value,out,indent=2)
manifest=R/'AC7-QUALIFICATION-MANIFEST-R3.json'
pin='e2ee86a9b7ea7b96f24062fae2739e9932c63e0e0c5597368302a209b67f8b1a'
assert sha(manifest)==pin
pure=json.loads((D/'PURE-RESULT.json').read_bytes())
assert sha(D/'PURE-RESULT.json')=='9449600498e065b974696dad3525612c62a01b75cc25507a60ec5520554e0d70'
assert sha(D/'DENIAL-REASON-RESULT.json')=='f78169f70c0146fa8e747c73e74532598e5ccc9d83971e5d1f76d76d7d26c6bd'
review=dict(decision='rejected',reviewer='/root/recovery_join_review20',
 tool_sha256='8268e674c7dc3a8b55ff168929112c502ad3766442107d22bc205b35607e7126',
 wrapper_sha256='d7174f1028eabe324e4cd473dc0892a62b394ed0f7b62ffe7f1c350724d8091c',
 proposal_sha256='61bd91fed2a6aa7222116ce5aff69b634a22ca253a2659780d9f9ce723c54844',
 manifest_sha256=pin,at=datetime.now(timezone.utc).isoformat(),
 no_host_execution_approval=True,host_execution_approved=False,
 actual_operator_approval_issued=False,source_publication_approved=False,
 runtime_activation_approved=False,review_scope='Frozen AC7 R3 qualification packet only',
 findings=[dict(id='AC7-QF-01',priority=2,status='verified',
   location='tools/isolated_worker_token_oracle.py:74-75,97-100',
   statement='Process-rights oracle accepts false with missing/0/invalid-parameter87 error as denial',
   evidence='DENIAL-REASON-RESULT.json',
   classification='Blocking positive process-isolation qualification acceptance',
   repair_authority='/root',
   next_action='Strict typed access-denied5 evidence and exact retained target liveness guards; fresh successor review')],
 repaired_prior_findings=['AC7-SR-01','AC7-SR-02'],
 evidence={n:sha(D/n) for n in ['REVIEW.md','PURE-RESULT.json','DENIAL-REASON-RESULT.json',
   'verify_frozen.py','verify_frozen_r2.py','HARNESS-R1-FAILURE.json','controlled43-r2.txt','check_denial_reason.py']},
 skill='epistemic-status-enforcer',skill_version='0.1.0',governing_version='thirsty-constitution-v0.1',
 governing_version_provenance='Required handoff-schema identifier; constitutional-rules file has no inline version',
 skill_sources={
  'SKILL.md':'ab4e1fc97e6eeebc242832afc6d865fe7408352b5ce0c716539b14e287d85fae',
  'references/constitutional-rules.md':'fcac1c8ed76418d9ec44b97a057e5ac0c9b654e0f0337d1a255267a5a0867496',
  'references/handoff-schema.md':'3f8cefccc028af6f37d7ac2b3add59fe6e5079bee86df0453a523443ad0b4823'},
 claims=[dict(statement='R1 primary/receipt/custody and helper cap findings repaired',
    epistemic_status='verified',source_ids=['PURE-RESULT.json',pin]),
   dict(statement='Process oracle accepts four controlled missing/0/5/87 error variants',
    epistemic_status='verified',source_ids=['DENIAL-REASON-RESULT.json']),
   dict(statement='43 controlled tests and additional oracle/wrapper controls passed',
    epistemic_status='verified',source_ids=['PURE-RESULT.json']),
   dict(statement='Actual future native profile and target denial outcomes',
    epistemic_status='unknown',source_ids=[])],
 assumptions=['Trusted Windows/kernel/admin and installed interpreter/toolchain remain external assumptions',
  'Controlled substitutions prove evaluated code behavior only'],
 contradictions=['A null process open can represent invalid/unavailable target rather than access denial'],
 risks=['Unclassified failure may be counted as positive containment evidence'],
 irreversible_effects=[],recommended_next_skills=[],external_actions_taken=[],
 unresolved_questions=['Corrected successor packet review','Fresh explicit actual operator approval',
  'Actual token/boundary/effect and retirement/profile-cleanup outcomes','Canonical application acceptance'])
save('review.json',review)
claim=json.loads((D/'review-claim.stdout').read_text(encoding='utf-8-sig'))['claim']
receipt=dict(schema_version=1,run_id='ac7-token-contract-r2-20261020',node_id='review',
 executor_id='/root/recovery_join_review20',started_at=claim['claimed_at'],
 finished_at=datetime.now(timezone.utc).isoformat(),input_hash=claim['input_hash'],
 changed_files=[],decision='rejected',exit_status=0,
 result=dict(decision='rejected',finding='AC7-QF-01',manifest_sha256=pin,
  review_path=str(D/'review.json'),review_sha256=sha(D/'review.json'),
  report_sha256=sha(D/'REVIEW.md'),candidate_payloads=357,
  source_and_candidate_unchanged_during_pure_probes=True,native_execution=False,
  operator_approval=False,skill='epistemic-status-enforcer',skill_version='0.1.0'),
 commands=[dict(command='"'+sys.executable+'" -B -X utf8 "'+str(D/'verify_frozen_r2.py')+'"',exit_status=0),
  dict(command='"'+sys.executable+'" -B -X utf8 "'+str(D/'check_denial_reason.py')+'"',exit_status=0)],
 validations=[dict(name='Frozen357_Source352_and_evidence_pins_checked',passed=True),
  dict(name='Controlled43_and_entry_wrapper_checks_completed',passed=True),
  dict(name='AC7_QF_01_counterexample_reproduced_without_native_operations',passed=True),
  dict(name='Independent_decision_rejected_no_host_approval',passed=True)])
save('review-receipt.json',receipt)
print(json.dumps(dict(review_sha256=sha(D/'review.json'),receipt_sha256=sha(D/'review-receipt.json'),
 report_sha256=sha(D/'REVIEW.md'),decision='rejected',finding='AC7-QF-01')))
