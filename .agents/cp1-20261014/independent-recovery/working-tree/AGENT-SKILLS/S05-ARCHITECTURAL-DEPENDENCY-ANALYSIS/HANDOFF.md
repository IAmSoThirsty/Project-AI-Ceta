# S05 handoff

## Transfer result

Typed build, runtime, data, and optional dependency maps with affected-owner and test impact.

## Required handoff

Identify the task, logical units, mapped local paths, source and artifact digests, contract revisions, performed procedure, actual verification records, and remaining obligations. Include uncertainty, failed checks, pending decisions, cancellation state, and any active ownership or resource leases. The receiver validates exact references before accepting the handoff.

## Acceptance

The receiver checks: The construction graph is acyclic and every affected contract consumer is accounted for.

The receiver also inspects evidence for the adverse fixture: A runtime message loop is incorrectly treated as a mandatory build-order cycle. A summary alone is insufficient. If any referenced artifact or source revision changed, issue a new handoff revision and invalidate stale review assumptions. Use [the shared construction handoff contract](../../AGENT-ROLES/CROSS-AGENT-HANDOFF-CONTRACT.md).
