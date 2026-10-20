# Subsystem 00 collaborative review (spec to code)

Scope: CETA-00.03.01 application-bootstrap, CETA-00.03.02 lifecycle-coordinator, CETA-00.03.03 shutdown-coordinator in 00-MASTER-ARCHITECTURE/00.03-RUNTIME-LIFECYCLE.

Binding: the owner local application source is not inside the authorized root (blocker B-01). Logical path ceta/master-architecture/runtime-lifecycle is bound to src/ceta/runtime/lifecycle.py under decision D-001 (Python 3.11+, standard library only). This is a self-review by the building agent. It is not independent verification.

## Requirement to code mapping

- Trust gate before activation (00.03.01): Runtime.boot and _trust_ok. Tests: test_oracle_missing_trust_opens_maintenance_dispatch_closed, test_negative_non_boolean_trust_verdict_fails_closed, test_negative_trust_check_exception_fails_closed.
- Refuse before any state change (00.03.01): Runtime.order called at the start of boot. Tests: test_negative_missing_dependency_refused_state_unchanged, test_negative_dependency_cycle_refused.
- Rollback of started components on activation failure (00.03.01): boot and _stop_component. Test: test_negative_start_failure_rolls_back_started_components.
- Recovery after failed boot or maintenance (00.03.01): test_recovery_failed_boot_retry_gets_new_generation, test_recovery_maintenance_then_repaired_trust_boots.
- Readiness generations and stale token rejection (00.03.02): Component.generation, Runtime.token, Runtime.submit. Tests: test_restart_invalidates_old_token, test_oracle (stale generation via restart).
- Dispatch closed outside RUNNING (00.03.02): Runtime.submit state check. Test: test_dispatch_refused_after_shutdown.
- Reverse dependency shutdown (00.03.03): Runtime.shutdown uses reversed order. Test: test_clean_shutdown_dependents_first.
- Deadline and uncertain effects (00.03.03): Runtime.shutdown deadline check. Tests: test_oracle_overrun_effect_is_uncertain, test_effect_without_drain_hook_is_uncertain, test_uncertain_effect_not_replayed_on_restart.
- Drain failures and stop failures: test_drain_exception_marks_uncertain_and_failed, test_stop_failure_marks_failed_and_blocks_reboot.

## Gaps recorded (not implemented in this run)

- Configuration, storage-integrity, policy-load, and interface-activation stages are not implemented (needs B-01 local source and B-04 storage profile).
- Typed domain records (ApplicationBootstrapInput, ApplicationBootstrapResult), and the prepareOperation, executeOperation, and stopOrReconcile operations are not implemented. The code exposes plain BootResult and ShutdownResult tuples.
- Durable operation identity and intent persistence are not implemented (needs B-04).
- The three spec units are not separate files. All behavior lives in lifecycle.py. This reduction is recorded here.
- Acceptance cases AT-CETA-00.03.0x-03 through -10 are mostly NOT EXECUTED. Only the three mandatory oracles and related recovery cases were run.
- No real neighboring subsystem integration (AT-09) exists yet.
