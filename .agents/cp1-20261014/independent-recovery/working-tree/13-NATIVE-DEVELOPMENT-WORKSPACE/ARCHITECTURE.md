# 13-NATIVE-DEVELOPMENT-WORKSPACE - architecture

## Responsibility

Provide a local project explorer, source editor, diff review, terminal, revision management, previews, and recoverable workspace state.

## Required invariant

The interface presents and proposes changes; native services enforce authority and filesystem boundaries. Local projects remain usable without remote hosting.

## Internal composition

| Component | Record model | Required flow |
| --- | --- | --- |
| [13.01 Project Management](13.01-PROJECT-MANAGEMENT/README.md) | workspace_id:text; project_id:text; selected_root:record; active_session:reference; source_snapshot:digest | Open an owner-selected project; validate path boundaries; register the local baseline; restore authorized interface state; expose project structure and health. |
| [13.02 Source Editor](13.02-SOURCE-EDITOR/README.md) | document_id:text; file_identity:record; baseline_digest:digest; buffer_version:integer; diagnostics_generation:integer | Load exact source bytes; preserve encoding and line conventions; track edits; request governed save; reconcile external changes; display current diagnostics. |
| [13.03 Change Inspection](13.03-CHANGE-INSPECTION/README.md) | change_set_id:text; before_ref:reference; after_ref:reference; staging_state:enum; decision_ref:reference | Compute exact changes; present text and binary summaries; stage selected modifications; obtain scoped approval; preserve revision history and recovery links. |
| [13.04 Terminal Workspace](13.04-TERMINAL-WORKSPACE/README.md) | terminal_id:text; worker_binding:reference; working_directory:record; output_sequence:integer; authority_scope:reference | Create a scoped terminal session; authorize commands; stream bounded output; preserve process ownership; stop or close cleanly; retain safe history. |
| [13.05 Version Control](13.05-VERSION-CONTROL/README.md) | revision_id:text; baseline_ref:reference; workspace_branch:text; merge_state:enum; source_digest:digest | Use available local revision facilities or native snapshots; isolate work; compare revisions; reconcile conflicts; publish verified changes while preserving owner state. |
| [13.06 Development Preview](13.06-DEVELOPMENT-PREVIEW/README.md) | preview_id:text; source_ref:reference; process_binding:reference; endpoint_scope:record; observation_ref:reference | Launch a controlled local preview; bind it to a source revision; observe rendered behavior; capture test evidence; recover preview and workspace state separately. |


## Ownership and boundaries

The subsystem owns its declared domain logic, not the authority, state, evidence, or resource services of another subsystem. Canonical shared schemas have one owner. Derived views and caches are explicitly rebuildable and invalidated by source generation. Effectful workers pass through the execution gate; narrowly scoped internal service operations follow the bootstrap trust model. Model output and imported content remain untrusted data.

## Activation and shutdown

Compile and validate shared contracts before implementation. Activate required native services only after their dependencies are healthy and qualified. Expose readiness separately from configuration. On shutdown, close new admission, stop or reconcile work, persist unresolved outcomes, and release resources after ownership-aware cleanup. Read-only inspection may remain available in a restricted maintenance state where safe.

## Design decisions that require local evidence

Map the logical units to the existing language, process model, storage schema, native enforcement backend, and application composition points. Preserve existing compliant behavior and tests. Any changed owner, contract semantics, data migration, or platform restriction needs an explicit integration decision with affected consumers and acceptance evidence. The design does not replace the owner's constitutional text or invent a local repository layout.

## Required integration proof

Exercise the component flows above with actual producer-consumer interfaces, exact input and output references, failure cases, current authority, and observed effects. Keep deterministic transformations separate from model-assisted assessments and external observations. The architecture is accepted only when implemented behavior satisfies the linked file specifications and subsystem invariant.
