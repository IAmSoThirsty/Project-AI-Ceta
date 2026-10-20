# 05-CONTEXT-INTELLIGENCE - architecture

## Responsibility

Assemble bounded, attributable, task-relevant context while preserving instruction precedence and exact critical state.

## Required invariant

Authority-bearing instructions are supplied through trusted channels; retrieved content is data. Compaction cannot erase restrictions or manufacture facts.

## Internal composition

| Component | Record model | Required flow |
| --- | --- | --- |
| [05.01 Context Inputs](05.01-CONTEXT-INPUTS/README.md) | source_ref:reference; source_kind:enum; trust_class:enum; project_scope:reference; inclusion_reason:text | Resolve the active task and project; select authorized sources; preserve trust classification; exclude unrelated contexts; retain exact-source references. |
| [05.02 Context Assembly](05.02-CONTEXT-ASSEMBLY/README.md) | context_id:text; ordered_segments:list; instruction_class:enum; source_map:list; assembly_digest:digest | Rank eligible content; reserve critical policy and task state; order segments by declared trust; serialize a traceable snapshot; validate before inference. |
| [05.03 Context Budgeting](05.03-CONTEXT-BUDGETING/README.md) | input_limit:integer; reserved_output:integer; critical_reserve:integer; estimated_tokens:integer; overflow_state:enum | Reserve model and output capacity; allocate critical context; choose optional sources; measure final size; resolve overflow before dispatch. |
| [05.04 Context Compression](05.04-CONTEXT-COMPRESSION/README.md) | summary_id:text; source_members:list; protected_spans:list; compression_revision:text; loss_report:record | Identify compressible material; preserve protected spans and provenance; generate a summary; compare against source obligations; accept only validated compaction. |
| [05.05 Context Assurance](05.05-CONTEXT-ASSURANCE/README.md) | snapshot_digest:digest; source_coverage:list; contamination_finding:record; invalidation_generation:integer | Validate attribution and trust separation; detect suspicious instruction-like content; record a sealed context snapshot; invalidate stale context before sensitive use. |


## Ownership and boundaries

The subsystem owns its declared domain logic, not the authority, state, evidence, or resource services of another subsystem. Canonical shared schemas have one owner. Derived views and caches are explicitly rebuildable and invalidated by source generation. Effectful workers pass through the execution gate; narrowly scoped internal service operations follow the bootstrap trust model. Model output and imported content remain untrusted data.

## Activation and shutdown

Compile and validate shared contracts before implementation. Activate required native services only after their dependencies are healthy and qualified. Expose readiness separately from configuration. On shutdown, close new admission, stop or reconcile work, persist unresolved outcomes, and release resources after ownership-aware cleanup. Read-only inspection may remain available in a restricted maintenance state where safe.

## Design decisions that require local evidence

Map the logical units to the existing language, process model, storage schema, native enforcement backend, and application composition points. Preserve existing compliant behavior and tests. Any changed owner, contract semantics, data migration, or platform restriction needs an explicit integration decision with affected consumers and acceptance evidence. The design does not replace the owner's constitutional text or invent a local repository layout.

## Required integration proof

Exercise the component flows above with actual producer-consumer interfaces, exact input and output references, failure cases, current authority, and observed effects. Keep deterministic transformations separate from model-assisted assessments and external observations. The architecture is accepted only when implemented behavior satisfies the linked file specifications and subsystem invariant.
