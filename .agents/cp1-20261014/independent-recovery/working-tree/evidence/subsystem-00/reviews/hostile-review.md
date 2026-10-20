# Subsystem 00 hostile review

Scope: fail-open start, shutdown ordering bypass, exception swallowing, re-entrancy, stale token replay, forgery.

## Findings

- H-01 Fail-open trust verdict. Only the boolean True admits boot (verdict is True). Truthy values such as 'yes', 1, and None go to MAINTENANCE. Status: no defect. Covered by test_negative_non_boolean_trust_verdict_fails_closed.
- H-02 Re-entrant boot from a start hook. The inner boot raises IllegalTransition (BOOTING to BOOTING is not legal). The outer start try block records start_failed and the runtime ends FAILED. Status: no code change required; behavior confirmed by a regression test. Regression test: test_start_hook_reentrant_boot_fails_closed.
- H-03 Re-entrant shutdown from a stop hook. The inner shutdown raises IllegalTransition while STOPPING. The stop failure is recorded, the component is marked failed, and the run ends FAILED. Status: no code change required; behavior confirmed by a regression test. Regression test: test_stop_hook_reentrant_shutdown_fails_closed.
- H-04 Forgeable readiness token. Tokens are plain (name, generation) tuples. Any in-process caller can construct a tuple matching the current generation. Status: fixed. Token is now a Token object whose MAC is an HMAC-SHA256 keyed by a per-runtime 32-byte secret. submit() rejects tuples, altered name or generation, malformed MACs, and tokens from another runtime with code forged_token. Regression tests: H04ForgedTokenTests in tests/test_runtime_regressions.py.
- H-05 Dependency name types are not validated at registration. A non-string dependency is caught later as missing_dependency rather than rejected at registration. Status: fixed. Component() rejects non-text dependency names, empty names, and a bare string passed as depends, at registration time, so the name is never added. Regression tests: H05DependencyTypeTests in tests/test_runtime_regressions.py.
- H-06 Exception swallowing. Ordinary exceptions from start, stop, and drain hooks become diagnostics and a FAILED state. BaseException such as KeyboardInterrupt propagates by design. Status: design note, no defect.
- H-07 Late drain result. A drain hook that returns after the deadline is discarded and its effects are recorded as uncertain. Covered by test_oracle_overrun_effect_is_uncertain.
- H-08 Replay after restart. Old tokens are rejected with stale_readiness. Uncertain effects are not replayed on the next boot. Covered by test_restart_invalidates_old_token and test_uncertain_effect_not_replayed_on_restart.

## Summary

No fail-open path was found in boot, activation, dispatch gating, or shutdown. Open items: none. H-04 and H-05 were fixed in this pass with regression tests. Residual design limits: the secret lives in process memory, so this protects against accidental and tuple-based misuse within one process, not against code that reads runtime internals.
