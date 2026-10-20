# 19-STATE-AND-RECOVERY - architecture

## Responsibility

Own canonical operational state, transactional persistence, snapshots, migrations, recovery, and historical reconstruction.

## Required invariant

Storage durability, authority validity, and external-effect certainty are independent. Recovery never silently replays uncertain effects or rolls back known revocations.

## Internal composition

| Component | Record model | Required flow |
| --- | --- | --- |
| [19.01 State Register](19.01-STATE-REGISTER/README.md) | record_id:text; aggregate_id:text; state_version:integer; transition_ref:reference; source_generation:integer | Define canonical records; validate expected versions and allowed transitions; commit state and event references; expose consistent reads and historical views. |
| [19.02 Durable Storage](19.02-DURABLE-STORAGE/README.md) | transaction_id:text; write_set:list; schema_revision:text; commit_sequence:integer; publication_state:enum | Open qualified local storage; validate schema and integrity; execute bounded transactions; commit state and publication intent atomically; recover after interruption. |
| [19.03 Snapshots](19.03-SNAPSHOTS/README.md) | snapshot_id:text; state_sequence:integer; manifest_ref:reference; content_digests:list; retention_rule:reference | Capture a consistent state boundary; write content and manifest; verify completeness; register a usable snapshot; retain and retire according to approved policy. |
| [19.04 Recovery](19.04-RECOVERY/README.md) | recovery_id:text; failure_boundary:enum; last_committed_sequence:integer; unresolved_operations:list; authority_recheck:enum | Inspect actual persisted state and effects; choose a validated recovery point; reconcile later observations; restore data; reauthenticate and requalify before resuming tasks. |
| [19.05 Migration](19.05-MIGRATION/README.md) | migration_id:text; from_schema:text; to_schema:text; preflight_ref:reference; progress_checkpoint:reference; reversibility:enum | Plan compatibility and data transformations; run preflight and backup; stage or checkpoint migration; validate transformed data; commit activation; verify rollback or forward repair. |
| [19.06 Archival](19.06-ARCHIVAL/README.md) | archive_id:text; record_range:record; format_revision:text; source_manifest:reference; access_scope:reference | Archive selected history with provenance and retention labels; validate exports; index permitted metadata; reconstruct authorized historical views without reactivating past authority. |


## Ownership and boundaries

The subsystem owns its declared domain logic, not the authority, state, evidence, or resource services of another subsystem. Canonical shared schemas have one owner. Derived views and caches are explicitly rebuildable and invalidated by source generation. Effectful workers pass through the execution gate; narrowly scoped internal service operations follow the bootstrap trust model. Model output and imported content remain untrusted data.

## Activation and shutdown

Compile and validate shared contracts before implementation. Activate required native services only after their dependencies are healthy and qualified. Expose readiness separately from configuration. On shutdown, close new admission, stop or reconcile work, persist unresolved outcomes, and release resources after ownership-aware cleanup. Read-only inspection may remain available in a restricted maintenance state where safe.

## Design decisions that require local evidence

Map the logical units to the existing language, process model, storage schema, native enforcement backend, and application composition points. Preserve existing compliant behavior and tests. Any changed owner, contract semantics, data migration, or platform restriction needs an explicit integration decision with affected consumers and acceptance evidence. The design does not replace the owner's constitutional text or invent a local repository layout.

## Required integration proof

Exercise the component flows above with actual producer-consumer interfaces, exact input and output references, failure cases, current authority, and observed effects. Keep deterministic transformations separate from model-assisted assessments and external observations. The architecture is accepted only when implemented behavior satisfies the linked file specifications and subsystem invariant.
