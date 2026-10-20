# Subsystem 01 hostile review

Builder-run hostile pass (no independent reviewer staffed). Each finding has a status and a regression test name, or an explicit OPEN note.

| ID | Attack or risk | Status | Remediation or evidence |
|---|---|---|---|
| H-01 | Unconditional allow plus an unmet-fact deny for the same action lets allow win | FIXED | evaluate returns DENY on any unmet rule. test_regression_unconditional_allow_plus_unmet_deny_is_not_allow |
| H-02 | Approval used after its window, or reused | FIXED | Registry checks window against injected clock and consumes nonces. test_negative_approval_used_after_window_is_refused, test_negative_second_use_of_same_approval_is_refused |
| H-03 | Forged approval constructed directly with approved=True | FIXED | Approvals sealed by HMAC issued only in approve_transition. test_negative_directly_constructed_approval_refused, test_negative_forged_seal_refused |
| H-04 | Two aliases of one principal counted as two votes | FIXED | Canonical principal mapping via aliases. test_regression_two_aliases_of_one_principal_count_once |
| H-05 | Missing facts as truthy defaults (None, False, empty) | FIXED | _absent treats None, False and empty text as missing. test_negative_missing_identity_fact_is_not_truthy_default, test_negative_false_fact_treated_as_absent |
| H-06 | Rule rollback to an older revision | FIXED | test_recovery_rollback_refused_keeps_current_revision |
| H-07 | Verifier exception counted as a valid signature (fail-open) | FIXED | Exceptions count as not valid. test_negative_verifier_exception_not_counted |
| H-08 | Quorum with no verifier treated as valid | FIXED | Returns signature_profile_unpinned. test_negative_no_verifier_blocks_as_unpinned |
| H-09 | Corrupt reload keeps the old rule set active (fallback) | FIXED | Integrity codes clear the active set. test_recovery_corrupted_reload_clears_active_set_no_fallback |
| H-10 | No active rule set or unknown action returns allow | FIXED | deny by default. test_negative_no_active_rule_set_denies_everything, test_negative_unknown_action_denied |
| H-11 | Alias map entry that is not text, or unknown alias | FIXED | Malformed map refused; unknown alias ineligible. test_negative_malformed_alias_map_rejected, test_negative_unknown_alias_is_ineligible |
| H-12 | Seal key lives in process memory, so same-process code can forge approvals | ACCEPTED RESIDUAL | Documented in TransitionApproval. Durable or external key custody is out of scope until a signing profile is pinned (B-04). |
| H-13 | Nonce consumption is memory-only, so replay after restart succeeds | OPEN | Blocked on subsystem 19 durable store (B-09). No regression test possible yet. |
| H-14 | Old signed packets re-run through approve_transition create a fresh sealed approval with a new nonce, so single-use is per object and not per signed packet. A caller-supplied window can then re-admit an old packet | OPEN | Remediation plan: bind proposal digest, validity window and policy revision into the signed payload (01.03.02), and record issued approval digests in a durable issuance log (B-09). No regression test yet. |
| H-15 | Rule-set pin provenance: the caller supplies both bytes and pin, so a caller controlling both can load any rule text | OPEN | Pin must come from an owner-approved source once constitutional text exists (B-03). Fixture pin is a TEST FIXTURE pin only. |

Counts: 7 regression tests in tests/test_governance_hostile.py. 10 in tests/test_governance_regressions.py. Full suite 105 OK, exit 0.

Open items for Subsystem 01 closure: H-13, H-14, H-15, B-03, B-04, B-05, B-09, and unimplemented units 01.02.01, 01.03.01, and the operation lifecycle of 01.03.03.
