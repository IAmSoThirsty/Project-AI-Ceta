# S14 handoff

## Transfer result

A governed adapter with exact-input binding, qualified restrictions, stop behavior, and receipts.

## Required handoff

Identify the task, logical units, mapped local paths, source and artifact digests, contract revisions, performed procedure, actual verification records, and remaining obligations. Include uncertainty, failed checks, pending decisions, cancellation state, and any active ownership or resource leases. The receiver validates exact references before accepting the handoff.

## Acceptance

The receiver checks: Denied requests never reach the adapter and observed effects stay within approved scope.

The receiver also inspects evidence for the adverse fixture: A retry, terminal, maintenance, or IPC path bypasses the gate. A summary alone is insufficient. If any referenced artifact or source revision changed, issue a new handoff revision and invalidate stale review assumptions. Use [the shared construction handoff contract](../../AGENT-ROLES/CROSS-AGENT-HANDOFF-CONTRACT.md).
