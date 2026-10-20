# 07-AGENT-ORCHESTRATION - construction sequence

## Entry criteria

The local application has an inspected baseline, assigned source ownership, approved contract bindings, and preserved existing acceptance requirements. Required prerequisites: [02-IDENTITY-AND-AUTHORITY](../02-IDENTITY-AND-AUTHORITY/README.md), [06-AGENT-SKILLS-AND-LEARNING](../06-AGENT-SKILLS-AND-LEARNING/README.md), [08-TASK-AND-WORKFLOW-ENGINE](../08-TASK-AND-WORKFLOW-ENGINE/README.md), [09-MODEL-RUNTIME](../09-MODEL-RUNTIME/README.md), [10-TOOLS-AND-CAPABILITIES](../10-TOOLS-AND-CAPABILITIES/README.md).

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
| [07.01 Agent Registry](07.01-AGENT-REGISTRY/README.md) | Register agents and roles; bind authenticated execution identities; match qualified capabilities; expose availability without granting new permissions. |
| [07.02 Agent Planning](07.02-AGENT-PLANNING/README.md) | Decompose the goal; assign testable outputs; identify dependencies and shared writes; allocate agents; validate the plan before execution. |
| [07.03 Agent Communication](07.03-AGENT-COMMUNICATION/README.md) | Authenticate agent messages; validate task scope and sequence; deliver idempotently; acknowledge handoffs; reconcile missing or duplicate messages. |
| [07.04 Multiagent Execution](07.04-MULTIAGENT-EXECUTION/README.md) | Admit ready assignments; acquire scoped write leases; execute governed work; observe cancellation; resolve conflicts through recorded decisions; release leases. |
| [07.05 Agent Observability](07.05-AGENT-OBSERVABILITY/README.md) | Collect authoritative lifecycle events; link agent claims to observed artifacts; evaluate outcomes; expose discrepancies and pending verification. |


## Parallel work and exit

Parallel implementation is allowed only after shared interfaces are stable and write scopes are disjoint. A stale lease cannot publish canonical changes. A conflict returns to the owning architecture or integration role, not to a last-writer-wins merge. Exit requires [the subsystem acceptance gate](ACCEPTANCE.md) and independent review of the delivered revision.
