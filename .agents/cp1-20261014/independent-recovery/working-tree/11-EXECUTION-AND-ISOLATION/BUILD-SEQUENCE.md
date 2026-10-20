# 11-EXECUTION-AND-ISOLATION - construction sequence

## Entry criteria

The local application has an inspected baseline, assigned source ownership, approved contract bindings, and preserved existing acceptance requirements. Required prerequisites: [01-CONSTITUTIONAL-GOVERNANCE](../01-CONSTITUTIONAL-GOVERNANCE/README.md), [02-IDENTITY-AND-AUTHORITY](../02-IDENTITY-AND-AUTHORITY/README.md), [17-EVIDENCE-AND-PROVENANCE](../17-EVIDENCE-AND-PROVENANCE/README.md), [18-SECURITY-AND-ENFORCEMENT](../18-SECURITY-AND-ENFORCEMENT/README.md), [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md), [20-RESOURCE-MANAGEMENT](../20-RESOURCE-MANAGEMENT/README.md).

## Ordered work

1. Inspect the existing local implementation and classify every logical unit as reuse, extend, or create; record exact source digests.
2. Approve canonical interfaces, domain records, error semantics, and state ownership with affected producers and consumers.
3. Create positive, negative, boundary, and recovery fixtures before relying on the new behavior.
4. Implement pure validation and transformation logic first; then connect canonical state, authority, resources, evidence, and controlled effects as applicable.
5. Integrate the component flows listed below in their actual dependency order, using the existing application composition mechanism.
6. Exercise real cross-subsystem paths and concurrency, cancellation, resource, and recovery failures.
7. Update user and engineering documentation from observed behavior and preserve source-to-test-to-artifact traceability.
8. Submit exact artifacts and raw evidence to independent verification; close the subsystem gate only after all required obligations pass.

## Component integration units

| Component | Flow to construct |
| --- | --- |
| [11.01 Execution Gate](11.01-EXECUTION-GATE/README.md) | Validate immutable operation inputs; verify current authority; reserve resources and evidence capacity; atomically record admission; dispatch through qualified isolation. |
| [11.02 Execution Sandbox](11.02-EXECUTION-SANDBOX/README.md) | Construct a least-authority worker environment; verify actual restrictions; launch the bound worker; observe effects; terminate and verify cleanup. |
| [11.03 Effect Control](11.03-EFFECT-CONTROL/README.md) | Declare intended effects; bind target and preconditions; observe actual operations independently; compare expected and actual effects; contain deviations. |
| [11.04 Stop And Cancellation](11.04-STOP-AND-CANCELLATION/README.md) | Accept an authenticated stop; prevent new admissions; signal workers; escalate termination by policy; observe residual effects; persist the final cancellation outcome. |
| [11.05 Execution Transactions](11.05-EXECUTION-TRANSACTIONS/README.md) | Persist intent; stage reversible local changes; perform authorized effects; commit observations; reconcile interrupted transactions; compensate only with explicit scope. |
| [11.06 Octoreflex Boundary](11.06-OCTOREFLEX-BOUNDARY/README.md) | Reconcile the existing native enforcement boundary; translate approved restrictions; qualify enforcement and observation on the target platform; attest actual installed policy. |


## Parallel work and exit

Parallel implementation is allowed only after shared interfaces are stable and write scopes are disjoint. A stale lease cannot publish canonical changes. A conflict returns to the owning architecture or integration role, not to a last-writer-wins merge. Exit requires [the subsystem acceptance gate](ACCEPTANCE.md) and independent review of the delivered revision.
