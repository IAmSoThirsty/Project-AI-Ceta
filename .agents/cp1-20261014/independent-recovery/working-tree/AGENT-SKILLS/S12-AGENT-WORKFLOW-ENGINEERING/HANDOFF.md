# S12 handoff

## Transfer result

Bounded multi-agent execution with fenced ownership, durable handoffs, and separate review.

## Required handoff

Identify the task, logical units, mapped local paths, source and artifact digests, contract revisions, performed procedure, actual verification records, and remaining obligations. Include uncertainty, failed checks, pending decisions, cancellation state, and any active ownership or resource leases. The receiver validates exact references before accepting the handoff.

## Acceptance

The receiver checks: Duplicate deliveries and stale workers cannot produce conflicting canonical effects.

The receiver also inspects evidence for the adverse fixture: A producer agent self-certifies its deliverable as independently verified. A summary alone is insufficient. If any referenced artifact or source revision changed, issue a new handoff revision and invalidate stale review assumptions. Use [the shared construction handoff contract](../../AGENT-ROLES/CROSS-AGENT-HANDOFF-CONTRACT.md).
