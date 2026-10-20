# 08-TASK-AND-WORKFLOW-ENGINE - architecture

## Responsibility

Execute durable task graphs with exact state transitions, safe retries, checkpoints, cancellation, and evidence-backed finalization.

## Required invariant

Durable orchestration does not guarantee exactly-once external effects. Unknown outcomes require reconciliation before replay or compensation.

## Internal composition

| Component | Record model | Required flow |
| --- | --- | --- |
| [08.01 Task Definition](08.01-TASK-DEFINITION/README.md) | task_id:text; goal:text; acceptance_refs:list; state:enum; state_version:integer; authority_ref:reference | Create an immutable task contract; validate acceptance criteria and effects; progress through allowed states; persist state changes with causal evidence. |
| [08.02 Workflow Graphs](08.02-WORKFLOW-GRAPHS/README.md) | workflow_id:text; node_id:text; edge_condition:record; join_rule:enum; graph_revision:text | Build a typed task graph; validate dependencies and branches; admit ready nodes; evaluate joins from recorded results; finalize only when required paths satisfy acceptance. |
| [08.03 Durable Execution](08.03-DURABLE-EXECUTION/README.md) | run_id:text; attempt:integer; idempotency_key:text; checkpoint_ref:reference; effect_ledger_ref:reference | Persist admission and operation identity; launch the worker; checkpoint at safe boundaries; reconcile receipts after interruption; resume only validated remaining work. |
| [08.04 Failure Handling](08.04-FAILURE-HANDLING/README.md) | failure_class:enum; retry_budget:integer; observed_effect:enum; compensation_ref:reference; decision_ref:reference | Classify failure by cause and effect certainty; select bounded retry, pause, reconciliation, or approved compensation; preserve the original failure record. |
| [08.05 Workflow Completion](08.05-WORKFLOW-COMPLETION/README.md) | deliverable_ref:reference; expected_digest:digest; acceptance_result:enum; verifier_id:text; finalization_version:integer | Collect outputs; validate their content and provenance; run acceptance checks; obtain required independent review; commit a final result with evidence. |


## Ownership and boundaries

The subsystem owns its declared domain logic, not the authority, state, evidence, or resource services of another subsystem. Canonical shared schemas have one owner. Derived views and caches are explicitly rebuildable and invalidated by source generation. Effectful workers pass through the execution gate; narrowly scoped internal service operations follow the bootstrap trust model. Model output and imported content remain untrusted data.

## Activation and shutdown

Compile and validate shared contracts before implementation. Activate required native services only after their dependencies are healthy and qualified. Expose readiness separately from configuration. On shutdown, close new admission, stop or reconcile work, persist unresolved outcomes, and release resources after ownership-aware cleanup. Read-only inspection may remain available in a restricted maintenance state where safe.

## Design decisions that require local evidence

Map the logical units to the existing language, process model, storage schema, native enforcement backend, and application composition points. Preserve existing compliant behavior and tests. Any changed owner, contract semantics, data migration, or platform restriction needs an explicit integration decision with affected consumers and acceptance evidence. The design does not replace the owner's constitutional text or invent a local repository layout.

## Required integration proof

Exercise the component flows above with actual producer-consumer interfaces, exact input and output references, failure cases, current authority, and observed effects. Keep deterministic transformations separate from model-assisted assessments and external observations. The architecture is accepted only when implemented behavior satisfies the linked file specifications and subsystem invariant.
