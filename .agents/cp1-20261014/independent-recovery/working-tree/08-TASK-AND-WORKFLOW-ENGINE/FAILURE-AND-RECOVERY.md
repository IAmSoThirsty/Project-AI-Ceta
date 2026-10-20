# 08-TASK-AND-WORKFLOW-ENGINE - failure and recovery

## Domain-specific failure fixtures

| Unit | Adverse condition that must be handled |
| --- | --- |
| [CETA-08.01.01 / task-contract](08.01-TASK-DEFINITION/task-contract.file.README.md) | A broad goal omits its effect scope and is still accepted for execution. |
| [CETA-08.01.02 / task-lifecycle-controller](08.01-TASK-DEFINITION/task-lifecycle-controller.file.README.md) | A failed task jumps directly to verified-complete without new evidence. |
| [CETA-08.01.03 / task-state-validator](08.01-TASK-DEFINITION/task-state-validator.file.README.md) | A terminal task is restarted by a duplicate queue delivery. |
| [CETA-08.02.01 / workflow-graph-builder](08.02-WORKFLOW-GRAPHS/workflow-graph-builder.file.README.md) | A graph references a nonexistent predecessor and starts anyway. |
| [CETA-08.02.02 / workflow-dependency-resolver](08.02-WORKFLOW-GRAPHS/workflow-dependency-resolver.file.README.md) | A skipped prerequisite is treated as a successful output producer. |
| [CETA-08.02.03 / workflow-transition-engine](08.02-WORKFLOW-GRAPHS/workflow-transition-engine.file.README.md) | A reevaluated model opinion changes an already committed branch decision. |
| [CETA-08.03.01 / durable-task-runner](08.03-DURABLE-EXECUTION/durable-task-runner.file.README.md) | A task is externally dispatched before its operation identity is durably recorded. |
| [CETA-08.03.02 / task-checkpoint-controller](08.03-DURABLE-EXECUTION/task-checkpoint-controller.file.README.md) | A checkpoint omits a partially committed external operation. |
| [CETA-08.03.03 / interrupted-task-resumer](08.03-DURABLE-EXECUTION/interrupted-task-resumer.file.README.md) | An uncertain network operation is automatically retried without reconciliation. |
| [CETA-08.04.01 / task-failure-classifier](08.04-FAILURE-HANDLING/task-failure-classifier.file.README.md) | Every network timeout is treated as proof that no effect occurred. |
| [CETA-08.04.02 / retry-policy-controller](08.04-FAILURE-HANDLING/retry-policy-controller.file.README.md) | A retry changes write arguments while reusing the original approval. |
| [CETA-08.04.03 / compensation-workflow](08.04-FAILURE-HANDLING/compensation-workflow.file.README.md) | A message already delivered is described as undone merely because local state was rolled back. |
| [CETA-08.05.01 / deliverable-validator](08.05-WORKFLOW-COMPLETION/deliverable-validator.file.README.md) | A report lists an artifact that was never created. |
| [CETA-08.05.02 / completion-evidence-checker](08.05-WORKFLOW-COMPLETION/completion-evidence-checker.file.README.md) | Tests from an earlier revision are used to qualify changed source. |
| [CETA-08.05.03 / task-finalization-controller](08.05-WORKFLOW-COMPLETION/task-finalization-controller.file.README.md) | A later optimistic success overwrites an already recorded uncertain outcome without reconciliation. |


## Mandatory response model

Validation and compatibility failures stop before privileged work. Authority failures deny the affected action and invalidate stale caches. Resource pressure preserves stop, evidence, and recovery capacity. A partial or uncertain effect is recorded explicitly. Missing evidence is not filled with narrative. Internal data writes use the canonical transaction owner; external actions have separately stated idempotency and compensation rules.

## Recovery sequence

1. Close new admission for the affected scope while preserving safe inspection.
2. Capture the last durable state, exact inputs, observed effects, process or target identity, and evidence gaps.
3. Inspect actual resources and receipts to distinguish committed, absent-confirmed, and uncertain effects.
4. Select safe continuation, authorized compensation, restoration, or a human decision using current authority.
5. Preserve later known revocations, deletion markers, corrections, identity records, conversations, and unsent drafts.
6. Requalify the repaired path and record a recovery report before reopening normal effects.

## Retry and compensation

Safe reads may be retried within the same bounded task. Confirmed idempotent operations preserve their operation key and current authority. Unknown outcomes require reconciliation first. Compensation is a new effect with its own scope and can fail; never describe an irreversible external action as undone because local state changed. For pure analysis and UI units, restart computation or presentation from pinned sources without replaying actions.

## Verification

Inject interruption, stale state, malformed input, resource exhaustion, and lost observations at meaningful boundaries for the units above. A recovery claim requires actual before and after observations and source-bound test records. See [the test matrix](TEST-MATRIX.md).
