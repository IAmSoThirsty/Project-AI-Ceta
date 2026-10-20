# S17 handoff

## Transfer result

Reproducible interruption evidence and validated safe resume, compensation, or uncertainty handling.

## Required handoff

Identify the task, logical units, mapped local paths, source and artifact digests, contract revisions, performed procedure, actual verification records, and remaining obligations. Include uncertainty, failed checks, pending decisions, cancellation state, and any active ownership or resource leases. The receiver validates exact references before accepting the handoff.

## Acceptance

The receiver checks: Every fault point yields the documented durable state and preserves already committed effects.

The receiver also inspects evidence for the adverse fixture: A timeout is assumed to prove no external action occurred. A summary alone is insufficient. If any referenced artifact or source revision changed, issue a new handoff revision and invalidate stale review assumptions. Use [the shared construction handoff contract](../../AGENT-ROLES/CROSS-AGENT-HANDOFF-CONTRACT.md).
