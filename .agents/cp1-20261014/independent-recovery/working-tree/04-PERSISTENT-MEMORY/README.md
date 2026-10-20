# 04-PERSISTENT-MEMORY

## Mission

Preserve episodic, semantic, and procedural information with provenance, access control, correction, and portability.

**Invariant:** Retrieved memory remains evidence with provenance and uncertainty, not an authority source. Deletion, correction, and retention are explicit owner-controlled operations.

## Component map

| Component | End-to-end behavior | Planned files |
| --- | --- | --- |
| [04.01 Memory Records](04.01-MEMORY-RECORDS/README.md) | Validate provenance and consent; classify a record; write its durable content and version; publish indexing work after commit; preserve correction lineage. | 3 |
| [04.02 Memory Indexing](04.02-MEMORY-INDEXING/README.md) | Build indexes from committed records; apply access scope before candidate exposure; rank authorized candidates; attach source and version information; rebuild when stale. | 3 |
| [04.03 Memory Consolidation](04.03-MEMORY-CONSOLIDATION/README.md) | Select eligible memory versions; group related content; preserve conflicts and exact evidence; propose consolidated records; retain reversible lineage. | 3 |
| [04.04 Memory Provenance](04.04-MEMORY-PROVENANCE/README.md) | Bind memory claims to exact sources; verify references and access; record transformations; expose version history and invalidation signals. | 3 |
| [04.05 Memory Lifecycle](04.05-MEMORY-LIFECYCLE/README.md) | Evaluate retention and access; honor authorized correction or deletion; invalidate indexes and caches; record minimal tombstones; reconcile backups and exports. | 3 |
| [04.06 Memory Portability](04.06-MEMORY-PORTABILITY/README.md) | Export authorized records with manifests; validate imports in staging; reconcile identities and conflicts; commit accepted records; verify reconstructability. | 3 |


## Read and build order

Read [architecture](ARCHITECTURE.md), [contracts](INTERFACE-CONTRACTS.md), [dependencies](DEPENDENCIES.md), and [build sequence](BUILD-SEQUENCE.md). Then load only the component and file specifications assigned to the current task. Use [the file index](FILE-INDEX.md) to find every planned source unit.

## Integration and qualification

Use [local integration instructions](INTEGRATION.md), [failure and recovery rules](FAILURE-AND-RECOVERY.md), [the test matrix](TEST-MATRIX.md), and [acceptance gate](ACCEPTANCE.md). [Agent assignments](AGENT-ASSIGNMENTS.md) defines construction responsibility and reviewer separation.

This subsystem contains 6 component folders and 18 planned implementation-file specifications. The package specifies their construction; it makes no claim about their presence in the uninspected local application. The initial reconciliation state for each logical path is LOCAL-INSPECTION-REQUIRED. Resolve that state through evidence before editing.
