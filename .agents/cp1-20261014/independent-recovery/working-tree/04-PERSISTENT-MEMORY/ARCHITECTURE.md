# 04-PERSISTENT-MEMORY - architecture

## Responsibility

Preserve episodic, semantic, and procedural information with provenance, access control, correction, and portability.

## Required invariant

Retrieved memory remains evidence with provenance and uncertainty, not an authority source. Deletion, correction, and retention are explicit owner-controlled operations.

## Internal composition

| Component | Record model | Required flow |
| --- | --- | --- |
| [04.01 Memory Records](04.01-MEMORY-RECORDS/README.md) | memory_id:text; kind:enum; owner_scope:reference; payload_ref:reference; source_refs:list; confidence:bounded-number | Validate provenance and consent; classify a record; write its durable content and version; publish indexing work after commit; preserve correction lineage. |
| [04.02 Memory Indexing](04.02-MEMORY-INDEXING/README.md) | index_generation:integer; record_ref:reference; embedding_revision:text; temporal_bounds:record; access_scope:reference | Build indexes from committed records; apply access scope before candidate exposure; rank authorized candidates; attach source and version information; rebuild when stale. |
| [04.03 Memory Consolidation](04.03-MEMORY-CONSOLIDATION/README.md) | candidate_refs:list; synthesis_ref:reference; contradiction_set:list; significance_score:bounded-number | Select eligible memory versions; group related content; preserve conflicts and exact evidence; propose consolidated records; retain reversible lineage. |
| [04.04 Memory Provenance](04.04-MEMORY-PROVENANCE/README.md) | source_digest:digest; source_span:range; evidence_ref:reference; memory_version:integer; supersedes:reference | Bind memory claims to exact sources; verify references and access; record transformations; expose version history and invalidation signals. |
| [04.05 Memory Lifecycle](04.05-MEMORY-LIFECYCLE/README.md) | retention_rule:reference; deletion_request:reference; legal_hold:optional-reference; tombstone_generation:integer | Evaluate retention and access; honor authorized correction or deletion; invalidate indexes and caches; record minimal tombstones; reconcile backups and exports. |
| [04.06 Memory Portability](04.06-MEMORY-PORTABILITY/README.md) | export_id:text; format_revision:text; record_count:integer; encrypted_payload_ref:reference; import_decision:reference | Export authorized records with manifests; validate imports in staging; reconcile identities and conflicts; commit accepted records; verify reconstructability. |


## Ownership and boundaries

The subsystem owns its declared domain logic, not the authority, state, evidence, or resource services of another subsystem. Canonical shared schemas have one owner. Derived views and caches are explicitly rebuildable and invalidated by source generation. Effectful workers pass through the execution gate; narrowly scoped internal service operations follow the bootstrap trust model. Model output and imported content remain untrusted data.

## Activation and shutdown

Compile and validate shared contracts before implementation. Activate required native services only after their dependencies are healthy and qualified. Expose readiness separately from configuration. On shutdown, close new admission, stop or reconcile work, persist unresolved outcomes, and release resources after ownership-aware cleanup. Read-only inspection may remain available in a restricted maintenance state where safe.

## Design decisions that require local evidence

Map the logical units to the existing language, process model, storage schema, native enforcement backend, and application composition points. Preserve existing compliant behavior and tests. Any changed owner, contract semantics, data migration, or platform restriction needs an explicit integration decision with affected consumers and acceptance evidence. The design does not replace the owner's constitutional text or invent a local repository layout.

## Required integration proof

Exercise the component flows above with actual producer-consumer interfaces, exact input and output references, failure cases, current authority, and observed effects. Keep deterministic transformations separate from model-assisted assessments and external observations. The architecture is accepted only when implemented behavior satisfies the linked file specifications and subsystem invariant.
