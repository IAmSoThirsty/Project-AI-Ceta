# S16 handoff

## Transfer result

Executed source-bound tests with independent oracles and explicit pass, fail, blocked, skipped, or not-executed states.

## Required handoff

Identify the task, logical units, mapped local paths, source and artifact digests, contract revisions, performed procedure, actual verification records, and remaining obligations. Include uncertainty, failed checks, pending decisions, cancellation state, and any active ownership or resource leases. The receiver validates exact references before accepting the handoff.

## Acceptance

The receiver checks: A test fails on the known defect and observes the required corrected behavior.

The receiver also inspects evidence for the adverse fixture: Generated tests merely restate the implementation or are reported passed without execution. A summary alone is insufficient. If any referenced artifact or source revision changed, issue a new handoff revision and invalidate stale review assumptions. Use [the shared construction handoff contract](../../AGENT-ROLES/CROSS-AGENT-HANDOFF-CONTRACT.md).
