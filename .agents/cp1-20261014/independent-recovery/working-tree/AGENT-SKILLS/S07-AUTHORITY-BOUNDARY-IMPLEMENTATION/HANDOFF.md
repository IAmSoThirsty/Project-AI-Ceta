# S07 handoff

## Transfer result

Use-time authorization checks with bounded delegation, replay protection, and revocation evidence.

## Required handoff

Identify the task, logical units, mapped local paths, source and artifact digests, contract revisions, performed procedure, actual verification records, and remaining obligations. Include uncertainty, failed checks, pending decisions, cancellation state, and any active ownership or resource leases. The receiver validates exact references before accepting the handoff.

## Acceptance

The receiver checks: A stale or revoked capability cannot authorize effects through any supported entry path.

The receiver also inspects evidence for the adverse fixture: A signature-valid token bypasses current revocation or target changes. A summary alone is insufficient. If any referenced artifact or source revision changed, issue a new handoff revision and invalidate stale review assumptions. Use [the shared construction handoff contract](../../AGENT-ROLES/CROSS-AGENT-HANDOFF-CONTRACT.md).
