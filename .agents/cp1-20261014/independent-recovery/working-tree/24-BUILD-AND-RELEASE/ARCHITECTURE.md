# 24-BUILD-AND-RELEASE - architecture

## Responsibility

Build, package, qualify, sign where configured, update, roll back, and deliver the complete native application with inspectable evidence.

## Required invariant

Release completion is determined by actual installed behavior and current evidence, not generated file volume, successful compilation, or a persuasive report.

## Internal composition

| Component | Record model | Required flow |
| --- | --- | --- |
| [24.01 Build Orchestration](24.01-BUILD-ORCHESTRATION/README.md) | build_id:text; source_manifest:reference; dependency_manifest:reference; configuration_digest:digest; artifact_refs:list | Pin source and dependencies; validate configuration; build in a controlled environment; record outputs; reproduce or explain declared nondeterministic fields; hand off exact artifacts. |
| [24.02 Version Management](24.02-VERSION-MANAGEMENT/README.md) | product_version:text; component_versions:record; schema_versions:record; compatibility_matrix:reference; release_id:text | Assign a product release identity; validate component and schema compatibility; generate an immutable release manifest; bind version labels to exact artifacts and evidence. |
| [24.03 Packaging](24.03-PACKAGING/README.md) | package_id:text; artifact_manifest:reference; installation_scope:record; offline_assets:list; qualification_ref:reference | Assemble only approved artifacts; validate contents and permissions; create a native installer or portable package; test clean installation and offline use; preserve user data on upgrade and removal. |
| [24.04 Release Integrity](24.04-RELEASE-INTEGRITY/README.md) | release_digest:digest; signing_key_ref:reference; trust_policy:reference; provenance_ref:reference; verification_state:enum | Bind release artifacts to the manifest; sign through approved protected facilities where configured; verify trust and exact bytes; record provenance and distribution identity. |
| [24.05 Update And Rollback](24.05-UPDATE-AND-ROLLBACK/README.md) | update_id:text; current_release:reference; target_release:reference; migration_plan:reference; recovery_point:reference | Validate the exact update; preflight compatibility and capacity; create a recovery point; apply staged changes; verify startup and data; roll back or forward-repair under declared rules. |
| [24.06 Product Completion](24.06-PRODUCT-COMPLETION/README.md) | candidate_id:text; scope_manifest:reference; gate_results:list; installed_observations:list; release_decision:reference | Reconcile full approved scope; verify every mandatory gate; exercise complete installed workflows; inspect evidence independently; issue an accurate product-completion decision. |


## Ownership and boundaries

The subsystem owns its declared domain logic, not the authority, state, evidence, or resource services of another subsystem. Canonical shared schemas have one owner. Derived views and caches are explicitly rebuildable and invalidated by source generation. Effectful workers pass through the execution gate; narrowly scoped internal service operations follow the bootstrap trust model. Model output and imported content remain untrusted data.

## Activation and shutdown

Compile and validate shared contracts before implementation. Activate required native services only after their dependencies are healthy and qualified. Expose readiness separately from configuration. On shutdown, close new admission, stop or reconcile work, persist unresolved outcomes, and release resources after ownership-aware cleanup. Read-only inspection may remain available in a restricted maintenance state where safe.

## Design decisions that require local evidence

Map the logical units to the existing language, process model, storage schema, native enforcement backend, and application composition points. Preserve existing compliant behavior and tests. Any changed owner, contract semantics, data migration, or platform restriction needs an explicit integration decision with affected consumers and acceptance evidence. The design does not replace the owner's constitutional text or invent a local repository layout.

## Required integration proof

Exercise the component flows above with actual producer-consumer interfaces, exact input and output references, failure cases, current authority, and observed effects. Keep deterministic transformations separate from model-assisted assessments and external observations. The architecture is accepted only when implemented behavior satisfies the linked file specifications and subsystem invariant.
