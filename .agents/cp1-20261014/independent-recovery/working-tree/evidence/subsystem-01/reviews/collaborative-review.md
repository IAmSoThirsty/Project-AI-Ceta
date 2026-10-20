# Subsystem 01 collaborative review

Scope: Subsystem 01 Constitutional Governance, Python stdlib implementation under src/ceta/governance (rules.py, __main__.py), per decision D-001. This is a builder self-review. The independent reviewer role R20 is not staffed in this run, so this is NOT an independent verification.

## Spec-to-code conformance

| Spec unit | Code location | Status | Notes |
|---|---|---|---|
| 01.01 rule-version-loader | rules.load_rule_set, Registry.activate | PARTIAL | Hash-pinned loading, size bounds, UTF-8 JSON, version rollback and conflict checks. Rule text is a labelled TEST FIXTURE (B-03). |
| 01.01 constitution-registry | rules.Registry | PARTIAL | One active immutable rule set plus history. No durable store (B-09). |
| 01.02.01 policy-interpreter | none | NOT IMPLEMENTED | Rules are parsed directly from JSON. |
| 01.02.02 policy-evaluator | rules.evaluate | PARTIAL | evaluate implemented. explain and verifyCompatibility are NOT implemented. Missing, None, False and empty facts are absent; zero is present. |
| 01.02.03 policy-conflict-resolver | rules.evaluate precedence branch | PARTIAL | Top-precedence conflict returns human_decision_required. No separate resolver unit. |
| 01.03.01 transition-proposal-builder | none | NOT IMPLEMENTED | Caller supplies the digest. |
| 01.03.02 governance-packet-validator | rules.approve_transition | PARTIAL | Digest binding, eligibility, alias canonicalization, validity window, verifier gate. NO dangling-reference or policy-revision checks. |
| 01.03.03 governance-quorum-controller | rules.approve_transition | PARTIAL | Pure distinct-principal count. prepareOperation, executeOperation and stopOrReconcile are NOT implemented. No durable operation identity. |

## Interface compatibility

- Registry.activate(raw, pinned_sha256, approval) is the only activation path. Approvals must be issued by approve_transition (HMAC seal).
- evaluate(rule_set, action, facts) returns (decision, reasons). Decisions allow, deny, human_decision_required match the spec vocabulary.
- approve_transition(digest, approvals, eligible, threshold, now, valid_from, valid_to, verifier, aliases) returns a TransitionApproval with approved, reasons, window and nonce.
- Canonical contracts (policy-decision, governance-packet, principal-identity) are not bound to local schemas in this run. Field-level contract conformance is UNVERIFIED.

## Acceptance mapping (subsystem-01 tests)

- 01.02.02 AT-02 prohibited truthy default: test_negative_missing_identity_fact_is_not_truthy_default, test_negative_false_fact_treated_as_absent.
- AT-03 malformed input: rules and quorum malformed tests.
- AT-04 stale generation: test_recovery_rollback_refused_keeps_current_revision, test_recovery_same_version_different_content_is_conflict.
- AT-06 bounds: MAX_BYTES, MAX_RULES and MAX_APPROVALS boundary tests.
- AT-07 duplicates: test_boundary_duplicate_rule_id_rejected, test_negative_duplicate_principal_counts_once.
- AT-08 recovery: covered in memory only; durable recovery is blocked on B-09.
- AT-05 access control: NOT EXECUTED (no principal layer built).
- AT-09 real integration path: NOT EXECUTED (neighbour subsystems not built).
- AT-10 independent proof: NOT EXECUTED.

## Evidence

- evidence/subsystem-01/unittest-output.txt: Ran 105 tests, OK, exit 0.
- evidence/subsystem-01/governance-demo-output.txt: valid quorum activated; tampered fixture rejected digest_mismatch; no rule set gives deny.

Overall Subsystem 01 status: PARTIAL. Mandatory acceptance is not complete.
