# 04-PERSISTENT-MEMORY - construction sequence

## Entry criteria

The local application has an inspected baseline, assigned source ownership, approved contract bindings, and preserved existing acceptance requirements. Required prerequisites: [02-IDENTITY-AND-AUTHORITY](../02-IDENTITY-AND-AUTHORITY/README.md), [17-EVIDENCE-AND-PROVENANCE](../17-EVIDENCE-AND-PROVENANCE/README.md), [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md).

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
| [04.01 Memory Records](04.01-MEMORY-RECORDS/README.md) | Validate provenance and consent; classify a record; write its durable content and version; publish indexing work after commit; preserve correction lineage. |
| [04.02 Memory Indexing](04.02-MEMORY-INDEXING/README.md) | Build indexes from committed records; apply access scope before candidate exposure; rank authorized candidates; attach source and version information; rebuild when stale. |
| [04.03 Memory Consolidation](04.03-MEMORY-CONSOLIDATION/README.md) | Select eligible memory versions; group related content; preserve conflicts and exact evidence; propose consolidated records; retain reversible lineage. |
| [04.04 Memory Provenance](04.04-MEMORY-PROVENANCE/README.md) | Bind memory claims to exact sources; verify references and access; record transformations; expose version history and invalidation signals. |
| [04.05 Memory Lifecycle](04.05-MEMORY-LIFECYCLE/README.md) | Evaluate retention and access; honor authorized correction or deletion; invalidate indexes and caches; record minimal tombstones; reconcile backups and exports. |
| [04.06 Memory Portability](04.06-MEMORY-PORTABILITY/README.md) | Export authorized records with manifests; validate imports in staging; reconcile identities and conflicts; commit accepted records; verify reconstructability. |


## Parallel work and exit

Parallel implementation is allowed only after shared interfaces are stable and write scopes are disjoint. A stale lease cannot publish canonical changes. A conflict returns to the owning architecture or integration role, not to a last-writer-wins merge. Exit requires [the subsystem acceptance gate](ACCEPTANCE.md) and independent review of the delivered revision.
