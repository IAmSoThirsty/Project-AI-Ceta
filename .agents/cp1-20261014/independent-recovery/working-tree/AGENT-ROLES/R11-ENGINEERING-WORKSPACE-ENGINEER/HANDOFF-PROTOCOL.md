# R11 handoff protocol

## Deliverable

A native local engineering workflow that preserves owner changes and qualifies the resulting artifacts.

## Transfer sequence

1. Freeze the exact source and artifact revisions being handed off.
2. Validate all referenced files and evidence exist and remain within authorized access scope.
3. List completed acceptance IDs and attach actual observations; list failed, blocked, and not-executed obligations separately.
4. Include current task state, pending owner decisions, unresolved effects, cancellation state, and resource or ownership leases.
5. Release or explicitly transfer the write lease only after the receiver acknowledges the exact handoff digest.
6. Have the receiver verify artifact identities and prerequisite compatibility before continuing work.

Use [the canonical construction handoff fields](../CROSS-AGENT-HANDOFF-CONTRACT.md). A summary may accompany the handoff but cannot replace exact artifacts, raw evidence, or unresolved-work records. If the source changes during transfer, create a new handoff revision and invalidate stale review assumptions.
