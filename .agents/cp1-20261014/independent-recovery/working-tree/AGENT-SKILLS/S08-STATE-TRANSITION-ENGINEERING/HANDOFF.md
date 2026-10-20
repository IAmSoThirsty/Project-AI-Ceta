# S08 handoff

## Transfer result

A validated state machine with atomic transitions, causal records, and terminal-state rules.

## Required handoff

Identify the task, logical units, mapped local paths, source and artifact digests, contract revisions, performed procedure, actual verification records, and remaining obligations. Include uncertainty, failed checks, pending decisions, cancellation state, and any active ownership or resource leases. The receiver validates exact references before accepting the handoff.

## Acceptance

The receiver checks: Conflicting updates cannot both commit and terminal states cannot be bypassed.

The receiver also inspects evidence for the adverse fixture: A restarted worker overwrites a newer stop or revocation state. A summary alone is insufficient. If any referenced artifact or source revision changed, issue a new handoff revision and invalidate stale review assumptions. Use [the shared construction handoff contract](../../AGENT-ROLES/CROSS-AGENT-HANDOFF-CONTRACT.md).
