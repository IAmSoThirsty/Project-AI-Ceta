# 05-CONTEXT-INTELLIGENCE - construction sequence

## Entry criteria

The local application has an inspected baseline, assigned source ownership, approved contract bindings, and preserved existing acceptance requirements. Required prerequisites: [02-IDENTITY-AND-AUTHORITY](../02-IDENTITY-AND-AUTHORITY/README.md), [04-PERSISTENT-MEMORY](../04-PERSISTENT-MEMORY/README.md), [09-MODEL-RUNTIME](../09-MODEL-RUNTIME/README.md), [20-RESOURCE-MANAGEMENT](../20-RESOURCE-MANAGEMENT/README.md).

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
| [05.01 Context Inputs](05.01-CONTEXT-INPUTS/README.md) | Resolve the active task and project; select authorized sources; preserve trust classification; exclude unrelated contexts; retain exact-source references. |
| [05.02 Context Assembly](05.02-CONTEXT-ASSEMBLY/README.md) | Rank eligible content; reserve critical policy and task state; order segments by declared trust; serialize a traceable snapshot; validate before inference. |
| [05.03 Context Budgeting](05.03-CONTEXT-BUDGETING/README.md) | Reserve model and output capacity; allocate critical context; choose optional sources; measure final size; resolve overflow before dispatch. |
| [05.04 Context Compression](05.04-CONTEXT-COMPRESSION/README.md) | Identify compressible material; preserve protected spans and provenance; generate a summary; compare against source obligations; accept only validated compaction. |
| [05.05 Context Assurance](05.05-CONTEXT-ASSURANCE/README.md) | Validate attribution and trust separation; detect suspicious instruction-like content; record a sealed context snapshot; invalidate stale context before sensitive use. |


## Parallel work and exit

Parallel implementation is allowed only after shared interfaces are stable and write scopes are disjoint. A stale lease cannot publish canonical changes. A conflict returns to the owning architecture or integration role, not to a last-writer-wins merge. Exit requires [the subsystem acceptance gate](ACCEPTANCE.md) and independent review of the delivered revision.
