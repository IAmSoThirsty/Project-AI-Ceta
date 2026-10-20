"""Seal exact R4 engineering approval; issues no operator or host permission."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys
F=Path('T:/00-Active/Project-AI-CETA')
R=F/'.agents/runtime/ac7-token-contract-20261020'
Q=F/'.agents/ac7-token-contract-20261020'
D=Path(__file__).resolve().parent
assert D==F/'.agents/runtime/ac7-qualification-review-20261020/R2'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pin='83967d7b5c00abc6461cdcb9bbe398bb63b0ab53078d8364f56f383de9b511cf'
manifest=R/'AC7-QUALIFICATION-MANIFEST-R4.json'
assert sha(manifest)==pin
m=json.loads(manifest.read_bytes())
assert len(m['payload_hashes'])==357 and all(sha(Q/n)==h for n,h in m['payload_hashes'].items())
assert all(sha(R/n)==h for n,h in m['evidence'].items())
assert sha(D/'PURE-RESULT.json')=='7f95eae36694384249ce0467e7be5c510c845475e8855603cc5c35eae306d26e'
assert sha(D/'DENIAL-REASON-RESULT.json')=='fbce8b41917c28319721aba9160a1f5fbc3f7a8ba1eae93394b0b0c2eec06e87'
assert sha(D.parent/'review.json')=='f5a978704d67bc1168f95b6061b311e07471cb45807605fafae47454bc454ad9'
def save(name,value):
    with (D/name).open('x',encoding='utf8') as output:json.dump(value,output,indent=2)
review=dict(decision='approved',reviewer='/root/recovery_join_review20',
 at=datetime.now(timezone.utc).isoformat(),manifest_sha256=pin,
 tool_sha256='79da07922e6a7f56cca0ae9d90a2498c3d6f28a58dcb6bd3144ab56a87b5bd84',
 wrapper_sha256='f25ee11f38fae860ca2a21673c42c0591db62cef0937b0b57f9b6aa0eff871bd',
 proposal_sha256='ddb4382f6d2aa9e62d0d39a661c73730cd10e55201a0958542f0fd8829cc6071',
 oracle_sha256='8f0791da2fa4879600a92f30617b79aeb3a271c89027b5a853ecb5853d5760d9',
 candidate_baseline_sha256='aa144f94637dfda5ef16e74ebd587f141630307f082da81375adbfad3a43f6ec',
 worker_image_sha256='3df03778e1e2f6f707d38b0869e04e262926f2d4c375f1d3d10562d3456443cc',
 approval_scope='Exact frozen R4 source and prepared qualification packet; separate human approval remains mandatory',
 no_host_execution_approval=True,host_execution_approved=False,human_approval_issued=False,
 source_publication_approved=False,runtime_activation_approved=False,
 closed_findings=['AC7-SR-01','AC7-SR-02','AC7-QF-01'],new_blocking_findings=[],
 evidence={n:sha(D/n) for n in ['REVIEW.md','PURE-RESULT.json','controlled47.txt',
  'DENIAL-REASON-RESULT.json','verify_successor.py','recheck_denial_reason_r2.py',
  'COUNTEREXAMPLE-HARNESS-R1-FAILURE.json']},
 rejected_predecessor=dict(manifest_sha256='e2ee86a9b7ea7b96f24062fae2739e9932c63e0e0c5597368302a209b67f8b1a',
  review_sha256=sha(D.parent/'review.json'),decision='rejected',history_preserved=True),
 skill='epistemic-status-enforcer',skill_version='0.1.0',governing_version='thirsty-constitution-v0.1',
 skill_sources={'SKILL.md':'ab4e1fc97e6eeebc242832afc6d865fe7408352b5ce0c716539b14e287d85fae',
  'references/constitutional-rules.md':'fcac1c8ed76418d9ec44b97a057e5ac0c9b654e0f0337d1a255267a5a0867496',
  'references/handoff-schema.md':'3f8cefccc028af6f37d7ac2b3add59fe6e5079bee86df0453a523443ad0b4823'},
 claims=[dict(statement='AC7-QF-01 process error and target-liveness correction is source- and control-verified',
    epistemic_status='verified',source_ids=['PURE-RESULT.json','DENIAL-REASON-RESULT.json',pin]),
   dict(statement='47 selected tests and bounded additional oracle/wrapper controls pass on frozen357',
    epistemic_status='verified',source_ids=['PURE-RESULT.json']),
   dict(statement='Actual Windows isolation and native effect/retirement/profile cleanup',
    epistemic_status='unknown',source_ids=[])],
 assumptions=['Trusted host Windows/kernel/admin and installed interpreter/toolchain remain external assumptions',
  'Controlled replacements prove evaluated source behavior and cannot issue authority'],
 contradictions=[],risks=['Remaining actual native qualification may fail; prepared code is not runtime evidence'],
 irreversible_effects=[],external_actions_taken=[],recommended_next_skills=[],
 recommended_next_action='Root personal inspection and remaining gates, then fresh explicit exact human host-operation approval',
 unresolved_questions=['Fresh actual operator approval','Native token/access/effect and cleanup outcomes',
  'Canonical source publication','Canonical application authorization-to-effect acceptance'])
save('review.json',review)
claim=json.loads((D/'review-claim.stdout').read_text(encoding='utf-8-sig'))['claim']
receipt=dict(schema_version=1,run_id='ac7-qualification-r4-20261020',node_id='review',
 executor_id='/root/recovery_join_review20',started_at=claim['claimed_at'],
 finished_at=datetime.now(timezone.utc).isoformat(),input_hash=claim['input_hash'],
 changed_files=[],decision='approved',exit_status=0,
 result=dict(decision='approved',manifest_sha256=pin,review_path=str(D/'review.json'),
  review_sha256=sha(D/'review.json'),report_sha256=sha(D/'REVIEW.md'),closed_finding='AC7-QF-01',
  candidate_payloads=357,controlled_python=47,native_execution=False,human_approval=False),
 commands=[dict(command='"'+sys.executable+'" -B -X utf8 "'+str(D/'verify_successor.py')+'"',exit_status=0),
  dict(command='"'+sys.executable+'" -B -X utf8 "'+str(D/'recheck_denial_reason_r2.py')+'"',exit_status=0)],
 validations=[dict(name='Exact_R4_357_payload_and_evidence_pins_checked',passed=True),
  dict(name='AC7_QF_01_error_and_liveness_counterexamples_now_reject',passed=True),
  dict(name='47_controlled_source_tests_and_bounded_extra_probes_passed',passed=True),
  dict(name='Token_lifecycle_cleanup_and_one_shot_gates_preserved',passed=True),
  dict(name='No_host_execution_or_human_approval_issued',passed=True)])
save('review-receipt.json',receipt)
print(json.dumps(dict(decision='approved',review_sha256=sha(D/'review.json'),
 receipt_sha256=sha(D/'review-receipt.json'),report_sha256=sha(D/'REVIEW.md'))))
