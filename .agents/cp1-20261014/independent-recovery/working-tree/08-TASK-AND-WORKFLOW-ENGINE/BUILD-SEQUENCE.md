# 08-TASK-AND-WORKFLOW-ENGINE - construction sequence

## Entry criteria

The local application has an inspected baseline, assigned source ownership, approved contract bindings, and preserved existing acceptance requirements. Required prerequisites: [02-IDENTITY-AND-AUTHORITY](../02-IDENTITY-AND-AUTHORITY/README.md), [11-EXECUTION-AND-ISOLATION](../11-EXECUTION-AND-ISOLATION/README.md), [17-EVIDENCE-AND-PROVENANCE](../17-EVIDENCE-AND-PROVENANCE/README.md), [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md), [20-RESOURCE-MANAGEMENT](../20-RESOURCE-MANAGEMENT/README.md).

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
| [08.01 Task Definition](08.01-TASK-DEFINITION/README.md) | Create an immutable task contract; validate acceptance criteria and effects; progress through allowed states; persist state changes with causal evidence. |
| [08.02 Workflow Graphs](08.02-WORKFLOW-GRAPHS/README.md) | Build a typed task graph; validate dependencies and branches; admit ready nodes; evaluate joins from recorded results; finalize only when required paths satisfy acceptance. |
| [08.03 Durable Execution](08.03-DURABLE-EXECUTION/README.md) | Persist admission and operation identity; launch the worker; checkpoint at safe boundaries; reconcile receipts after interruption; resume only validated remaining work. |
| [08.04 Failure Handling](08.04-FAILURE-HANDLING/README.md) | Classify failure by cause and effect certainty; select bounded retry, pause, reconciliation, or approved compensation; preserve the original failure record. |
| [08.05 Workflow Completion](08.05-WORKFLOW-COMPLETION/README.md) | Collect outputs; validate their content and provenance; run acceptance checks; obtain required independent review; commit a final result with evidence. |


## Parallel work and exit

Parallel implementation is allowed only after shared interfaces are stable and write scopes are disjoint. A stale lease cannot publish canonical changes. A conflict returns to the owning architecture or integration role, not to a last-writer-wins merge. Exit requires [the subsystem acceptance gate](ACCEPTANCE.md) and independent review of the delivered revision.
