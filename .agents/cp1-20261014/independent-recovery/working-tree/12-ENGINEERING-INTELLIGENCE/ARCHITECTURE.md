# 12-ENGINEERING-INTELLIGENCE - architecture

## Responsibility

Turn approved engineering requirements into inspected source changes, reproducible tests, independent review, and evidence-backed delivery.

## Required invariant

Engineering work operates on inspected local source with scoped file ownership. Generated code, test execution, and verified product behavior are distinct completion stages.

## Internal composition

| Component | Record model | Required flow |
| --- | --- | --- |
| [12.01 Project Discovery](12.01-PROJECT-DISCOVERY/README.md) | project_id:text; root_identity:record; source_snapshot:digest; symbol_index:reference; dependency_graph:reference | Inspect the selected project; identify languages and entry points; index source and dependencies; report unknown generated or binary content; bind findings to a source snapshot. |
| [12.02 Engineering Planning](12.02-ENGINEERING-PLANNING/README.md) | requirement_id:text; source_refs:list; change_set:list; acceptance_refs:list; risk_record:record | Trace each requirement to current behavior; define target changes and tests; sequence dependencies; assess effects and migration; request approval for changed scope. |
| [12.03 Code Construction](12.03-CODE-CONSTRUCTION/README.md) | change_id:text; expected_source_digest:digest; target_files:list; staged_artifacts:list; ownership_lease:reference | Plan exact edits against inspected source; stage coordinated changes; validate ownership and preconditions; apply through governed file operations; inspect the resulting diff. |
| [12.04 Testing And Debugging](12.04-TESTING-AND-DEBUGGING/README.md) | failure_id:text; reproduction_ref:reference; expected_behavior:record; test_revision:digest; diagnosis_refs:list | Reproduce the reported behavior; establish a failing test; inspect logs and state; propose a bounded repair; rerun targeted and affected regression tests. |
| [12.05 Engineering Review](12.05-ENGINEERING-REVIEW/README.md) | review_id:text; change_digest:digest; reviewer_id:text; findings:list; acceptance_impact:list | Inspect exact changes; compare against contracts and requirements; reproduce critical tests independently; classify findings; approve or return changes with evidence. |
| [12.06 Engineering Delivery](12.06-ENGINEERING-DELIVERY/README.md) | build_ref:reference; source_digest:digest; test_result_refs:list; documentation_revision:text; delivery_state:enum | Build from the pinned source; run verification; reconcile documentation and interfaces; report exact deliverables and unresolved obligations; hand off to product qualification. |


## Ownership and boundaries

The subsystem owns its declared domain logic, not the authority, state, evidence, or resource services of another subsystem. Canonical shared schemas have one owner. Derived views and caches are explicitly rebuildable and invalidated by source generation. Effectful workers pass through the execution gate; narrowly scoped internal service operations follow the bootstrap trust model. Model output and imported content remain untrusted data.

## Activation and shutdown

Compile and validate shared contracts before implementation. Activate required native services only after their dependencies are healthy and qualified. Expose readiness separately from configuration. On shutdown, close new admission, stop or reconcile work, persist unresolved outcomes, and release resources after ownership-aware cleanup. Read-only inspection may remain available in a restricted maintenance state where safe.

## Design decisions that require local evidence

Map the logical units to the existing language, process model, storage schema, native enforcement backend, and application composition points. Preserve existing compliant behavior and tests. Any changed owner, contract semantics, data migration, or platform restriction needs an explicit integration decision with affected consumers and acceptance evidence. The design does not replace the owner's constitutional text or invent a local repository layout.

## Required integration proof

Exercise the component flows above with actual producer-consumer interfaces, exact input and output references, failure cases, current authority, and observed effects. Keep deterministic transformations separate from model-assisted assessments and external observations. The architecture is accepted only when implemented behavior satisfies the linked file specifications and subsystem invariant.
