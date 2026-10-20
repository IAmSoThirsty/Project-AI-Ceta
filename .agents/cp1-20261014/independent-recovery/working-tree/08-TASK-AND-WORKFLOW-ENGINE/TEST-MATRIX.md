# 08-TASK-AND-WORKFLOW-ENGINE - test matrix

## Unit-level acceptance coverage

Every source specification defines ten concrete test obligations: required behavior, a domain-specific adverse case, schema compatibility, stale references, access, bounds and interruption, concurrency, recovery, real integration, and independent proof. These are planned tests, not runtime results.

| Unit | Acceptance IDs | Positive oracle | Negative oracle | Initial execution state |
| --- | --- | --- | --- | --- |
| [CETA-08.01.01 / task-contract](08.01-TASK-DEFINITION/task-contract.file.README.md) | AT-CETA-08.01.01-01 through AT-CETA-08.01.01-10 | A task has measurable acceptance criteria before it can be admitted. | A broad goal omits its effect scope and is still accepted for execution. | NOT EXECUTED |
| [CETA-08.01.02 / task-lifecycle-controller](08.01-TASK-DEFINITION/task-lifecycle-controller.file.README.md) | AT-CETA-08.01.02-01 through AT-CETA-08.01.02-10 | Two conflicting transition requests cannot both update the same state version. | A failed task jumps directly to verified-complete without new evidence. | NOT EXECUTED |
| [CETA-08.01.03 / task-state-validator](08.01-TASK-DEFINITION/task-state-validator.file.README.md) | AT-CETA-08.01.03-01 through AT-CETA-08.01.03-10 | A resumed task preserves its previous committed effects and unresolved operations. | A terminal task is restarted by a duplicate queue delivery. | NOT EXECUTED |
| [CETA-08.02.01 / workflow-graph-builder](08.02-WORKFLOW-GRAPHS/workflow-graph-builder.file.README.md) | AT-CETA-08.02.01-01 through AT-CETA-08.02.01-10 | Every required output has a producing node and a defined completion path. | A graph references a nonexistent predecessor and starts anyway. | NOT EXECUTED |
| [CETA-08.02.02 / workflow-dependency-resolver](08.02-WORKFLOW-GRAPHS/workflow-dependency-resolver.file.README.md) | AT-CETA-08.02.02-01 through AT-CETA-08.02.02-10 | A join waits for all required verified predecessors. | A skipped prerequisite is treated as a successful output producer. | NOT EXECUTED |
| [CETA-08.02.03 / workflow-transition-engine](08.02-WORKFLOW-GRAPHS/workflow-transition-engine.file.README.md) | AT-CETA-08.02.03-01 through AT-CETA-08.02.03-10 | Replay of recorded node results reconstructs the same graph progression. | A reevaluated model opinion changes an already committed branch decision. | NOT EXECUTED |
| [CETA-08.03.01 / durable-task-runner](08.03-DURABLE-EXECUTION/durable-task-runner.file.README.md) | AT-CETA-08.03.01-01 through AT-CETA-08.03.01-10 | Restart after dispatch discovers the prior attempt rather than creating a hidden duplicate. | A task is externally dispatched before its operation identity is durably recorded. | NOT EXECUTED |
| [CETA-08.03.02 / task-checkpoint-controller](08.03-DURABLE-EXECUTION/task-checkpoint-controller.file.README.md) | AT-CETA-08.03.02-01 through AT-CETA-08.03.02-10 | A checkpoint restores exact completed and remaining steps. | A checkpoint omits a partially committed external operation. | NOT EXECUTED |
| [CETA-08.03.03 / interrupted-task-resumer](08.03-DURABLE-EXECUTION/interrupted-task-resumer.file.README.md) | AT-CETA-08.03.03-01 through AT-CETA-08.03.03-10 | A completed file write is observed and not repeated after restart. | An uncertain network operation is automatically retried without reconciliation. | NOT EXECUTED |
| [CETA-08.04.01 / task-failure-classifier](08.04-FAILURE-HANDLING/task-failure-classifier.file.README.md) | AT-CETA-08.04.01-01 through AT-CETA-08.04.01-10 | A timeout after dispatch is classified as potentially uncertain rather than automatically retryable. | Every network timeout is treated as proof that no effect occurred. | NOT EXECUTED |
| [CETA-08.04.02 / retry-policy-controller](08.04-FAILURE-HANDLING/retry-policy-controller.file.README.md) | AT-CETA-08.04.02-01 through AT-CETA-08.04.02-10 | A safe read retry respects the task deadline and maximum attempts. | A retry changes write arguments while reusing the original approval. | NOT EXECUTED |
| [CETA-08.04.03 / compensation-workflow](08.04-FAILURE-HANDLING/compensation-workflow.file.README.md) | AT-CETA-08.04.03-01 through AT-CETA-08.04.03-10 | A reversible staged edit is restored from the verified prior snapshot. | A message already delivered is described as undone merely because local state was rolled back. | NOT EXECUTED |
| [CETA-08.05.01 / deliverable-validator](08.05-WORKFLOW-COMPLETION/deliverable-validator.file.README.md) | AT-CETA-08.05.01-01 through AT-CETA-08.05.01-10 | All declared deliverables exist and match their accepted content revisions. | A report lists an artifact that was never created. | NOT EXECUTED |
| [CETA-08.05.02 / completion-evidence-checker](08.05-WORKFLOW-COMPLETION/completion-evidence-checker.file.README.md) | AT-CETA-08.05.02-01 through AT-CETA-08.05.02-10 | Every required test result is tied to the delivered source and artifact revision. | Tests from an earlier revision are used to qualify changed source. | NOT EXECUTED |
| [CETA-08.05.03 / task-finalization-controller](08.05-WORKFLOW-COMPLETION/task-finalization-controller.file.README.md) | AT-CETA-08.05.03-01 through AT-CETA-08.05.03-10 | Repeated finalization returns the same verified result without duplicate events. | A later optimistic success overwrites an already recorded uncertain outcome without reconciliation. | NOT EXECUTED |


## Component and subsystem tests

| Component | Integrated behavior | Invariant |
| --- | --- | --- |
| [08.01](08.01-TASK-DEFINITION/README.md) | Create an immutable task contract; validate acceptance criteria and effects; progress through allowed states; persist state changes with causal evidence. | Task completion is a verified state, not a scheduling or model-generation event. |
| [08.02](08.02-WORKFLOW-GRAPHS/README.md) | Build a typed task graph; validate dependencies and branches; admit ready nodes; evaluate joins from recorded results; finalize only when required paths satisfy acceptance. | Conditional branches require explicit outcomes; absence of a result is not success. |
| [08.03](08.03-DURABLE-EXECUTION/README.md) | Persist admission and operation identity; launch the worker; checkpoint at safe boundaries; reconcile receipts after interruption; resume only validated remaining work. | Checkpoint restoration restores intent and observations, not expired authority. |
| [08.04](08.04-FAILURE-HANDLING/README.md) | Classify failure by cause and effect certainty; select bounded retry, pause, reconciliation, or approved compensation; preserve the original failure record. | Compensation is a new effectful action with its own authority and can itself fail. |
| [08.05](08.05-WORKFLOW-COMPLETION/README.md) | Collect outputs; validate their content and provenance; run acceptance checks; obtain required independent review; commit a final result with evidence. | An incomplete test set cannot become a successful finalization by omission. |


Run these flows through actual local implementations after unit tests. Bind results to exact source, dependencies, configuration, environment, and artifact bytes. A mock-only test cannot qualify a native enforcement or installed-product claim. Preserve failed, blocked, skipped, and not-executed cases separately. Use [the cross-system scenarios](../ACCEPTANCE-CRITERIA/END-TO-END-SCENARIOS/README.md) for user-workflow qualification.
