# 12-ENGINEERING-INTELLIGENCE - construction sequence

## Entry criteria

The local application has an inspected baseline, assigned source ownership, approved contract bindings, and preserved existing acceptance requirements. Required prerequisites: [05-CONTEXT-INTELLIGENCE](../05-CONTEXT-INTELLIGENCE/README.md), [07-AGENT-ORCHESTRATION](../07-AGENT-ORCHESTRATION/README.md), [08-TASK-AND-WORKFLOW-ENGINE](../08-TASK-AND-WORKFLOW-ENGINE/README.md), [10-TOOLS-AND-CAPABILITIES](../10-TOOLS-AND-CAPABILITIES/README.md), [17-EVIDENCE-AND-PROVENANCE](../17-EVIDENCE-AND-PROVENANCE/README.md).

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
| [12.01 Project Discovery](12.01-PROJECT-DISCOVERY/README.md) | Inspect the selected project; identify languages and entry points; index source and dependencies; report unknown generated or binary content; bind findings to a source snapshot. |
| [12.02 Engineering Planning](12.02-ENGINEERING-PLANNING/README.md) | Trace each requirement to current behavior; define target changes and tests; sequence dependencies; assess effects and migration; request approval for changed scope. |
| [12.03 Code Construction](12.03-CODE-CONSTRUCTION/README.md) | Plan exact edits against inspected source; stage coordinated changes; validate ownership and preconditions; apply through governed file operations; inspect the resulting diff. |
| [12.04 Testing And Debugging](12.04-TESTING-AND-DEBUGGING/README.md) | Reproduce the reported behavior; establish a failing test; inspect logs and state; propose a bounded repair; rerun targeted and affected regression tests. |
| [12.05 Engineering Review](12.05-ENGINEERING-REVIEW/README.md) | Inspect exact changes; compare against contracts and requirements; reproduce critical tests independently; classify findings; approve or return changes with evidence. |
| [12.06 Engineering Delivery](12.06-ENGINEERING-DELIVERY/README.md) | Build from the pinned source; run verification; reconcile documentation and interfaces; report exact deliverables and unresolved obligations; hand off to product qualification. |


## Parallel work and exit

Parallel implementation is allowed only after shared interfaces are stable and write scopes are disjoint. A stale lease cannot publish canonical changes. A conflict returns to the owning architecture or integration role, not to a last-writer-wins merge. Exit requires [the subsystem acceptance gate](ACCEPTANCE.md) and independent review of the delivered revision.
