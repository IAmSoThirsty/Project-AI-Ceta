# S03 handoff

## Transfer result

A versioned interface decision with fields, invariants, errors, state semantics, and shared test fixtures.

## Required handoff

Identify the task, logical units, mapped local paths, source and artifact digests, contract revisions, performed procedure, actual verification records, and remaining obligations. Include uncertainty, failed checks, pending decisions, cancellation state, and any active ownership or resource leases. The receiver validates exact references before accepting the handoff.

## Acceptance

The receiver checks: Producer and consumer conformance fixtures exercise identical semantics, including denial and uncertainty.

The receiver also inspects evidence for the adverse fixture: A consumer privately widens a security-critical field or assumes unknown states mean success. A summary alone is insufficient. If any referenced artifact or source revision changed, issue a new handoff revision and invalidate stale review assumptions. Use [the shared construction handoff contract](../../AGENT-ROLES/CROSS-AGENT-HANDOFF-CONTRACT.md).
