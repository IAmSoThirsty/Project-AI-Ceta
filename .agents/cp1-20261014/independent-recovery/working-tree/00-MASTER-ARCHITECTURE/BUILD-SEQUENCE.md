# 00-MASTER-ARCHITECTURE - construction sequence

## Entry criteria

The local application has an inspected baseline, assigned source ownership, approved contract bindings, and preserved existing acceptance requirements. Required prerequisites: the owner-approved product baseline and selected local root.

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
| [00.01 Product Identity](00.01-PRODUCT-IDENTITY/README.md) | Load the approved product baseline; resolve amendments; expose a versioned invariant set; make every change traceable to an owner decision. |
| [00.02 System Topology](00.02-SYSTEM-TOPOLOGY/README.md) | Register components; validate unique ownership; distinguish build, runtime, data, and optional dependency edges; expose navigation and impact analysis. |
| [00.03 Runtime Lifecycle](00.03-RUNTIME-LIFECYCLE/README.md) | Initialize minimum storage and trust prerequisites; activate policy and dispatch boundaries; advertise readiness; stop admission; drain or terminate work; close durable stores. |
| [00.04 Integration Baseline](00.04-INTEGRATION-BASELINE/README.md) | Inspect only the selected local root; capture a read-only baseline; map logical units to observed files; resolve collisions; approve reuse or extension before editing. |
| [00.05 Architecture Assurance](00.05-ARCHITECTURE-ASSURANCE/README.md) | Evaluate graph structure, invariant coverage, and contract ownership against the same baseline; produce findings before integration approval. |


## Parallel work and exit

Parallel implementation is allowed only after shared interfaces are stable and write scopes are disjoint. A stale lease cannot publish canonical changes. A conflict returns to the owning architecture or integration role, not to a last-writer-wins merge. Exit requires [the subsystem acceptance gate](ACCEPTANCE.md) and independent review of the delivered revision.
