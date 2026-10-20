# S09 handoff

## Transfer result

Durable local records, atomic publication intent, integrity checks, and tested restoration.

## Required handoff

Identify the task, logical units, mapped local paths, source and artifact digests, contract revisions, performed procedure, actual verification records, and remaining obligations. Include uncertainty, failed checks, pending decisions, cancellation state, and any active ownership or resource leases. The receiver validates exact references before accepting the handoff.

## Acceptance

The receiver checks: Each injected crash yields a documented prior, committed, or explicitly uncertain state without silent data loss.

The receiver also inspects evidence for the adverse fixture: An in-memory success acknowledgement precedes durable commit. A summary alone is insufficient. If any referenced artifact or source revision changed, issue a new handoff revision and invalidate stale review assumptions. Use [the shared construction handoff contract](../../AGENT-ROLES/CROSS-AGENT-HANDOFF-CONTRACT.md).
