# 08-TASK-AND-WORKFLOW-ENGINE - planned source index

Every row has a fully populated file-level construction specification. The logical path is exact within this architecture; the actual language extension and module binding are determined from the owner-selected local application.

| Specification | Logical source path | Local mapping status |
| --- | --- | --- |
| [CETA-08.01.01 / task-contract](08.01-TASK-DEFINITION/task-contract.file.README.md) | ceta/task-and-workflow-engine/task-definition/task-contract | LOCAL-INSPECTION-REQUIRED |
| [CETA-08.01.02 / task-lifecycle-controller](08.01-TASK-DEFINITION/task-lifecycle-controller.file.README.md) | ceta/task-and-workflow-engine/task-definition/task-lifecycle-controller | LOCAL-INSPECTION-REQUIRED |
| [CETA-08.01.03 / task-state-validator](08.01-TASK-DEFINITION/task-state-validator.file.README.md) | ceta/task-and-workflow-engine/task-definition/task-state-validator | LOCAL-INSPECTION-REQUIRED |
| [CETA-08.02.01 / workflow-graph-builder](08.02-WORKFLOW-GRAPHS/workflow-graph-builder.file.README.md) | ceta/task-and-workflow-engine/workflow-graphs/workflow-graph-builder | LOCAL-INSPECTION-REQUIRED |
| [CETA-08.02.02 / workflow-dependency-resolver](08.02-WORKFLOW-GRAPHS/workflow-dependency-resolver.file.README.md) | ceta/task-and-workflow-engine/workflow-graphs/workflow-dependency-resolver | LOCAL-INSPECTION-REQUIRED |
| [CETA-08.02.03 / workflow-transition-engine](08.02-WORKFLOW-GRAPHS/workflow-transition-engine.file.README.md) | ceta/task-and-workflow-engine/workflow-graphs/workflow-transition-engine | LOCAL-INSPECTION-REQUIRED |
| [CETA-08.03.01 / durable-task-runner](08.03-DURABLE-EXECUTION/durable-task-runner.file.README.md) | ceta/task-and-workflow-engine/durable-execution/durable-task-runner | LOCAL-INSPECTION-REQUIRED |
| [CETA-08.03.02 / task-checkpoint-controller](08.03-DURABLE-EXECUTION/task-checkpoint-controller.file.README.md) | ceta/task-and-workflow-engine/durable-execution/task-checkpoint-controller | LOCAL-INSPECTION-REQUIRED |
| [CETA-08.03.03 / interrupted-task-resumer](08.03-DURABLE-EXECUTION/interrupted-task-resumer.file.README.md) | ceta/task-and-workflow-engine/durable-execution/interrupted-task-resumer | LOCAL-INSPECTION-REQUIRED |
| [CETA-08.04.01 / task-failure-classifier](08.04-FAILURE-HANDLING/task-failure-classifier.file.README.md) | ceta/task-and-workflow-engine/failure-handling/task-failure-classifier | LOCAL-INSPECTION-REQUIRED |
| [CETA-08.04.02 / retry-policy-controller](08.04-FAILURE-HANDLING/retry-policy-controller.file.README.md) | ceta/task-and-workflow-engine/failure-handling/retry-policy-controller | LOCAL-INSPECTION-REQUIRED |
| [CETA-08.04.03 / compensation-workflow](08.04-FAILURE-HANDLING/compensation-workflow.file.README.md) | ceta/task-and-workflow-engine/failure-handling/compensation-workflow | LOCAL-INSPECTION-REQUIRED |
| [CETA-08.05.01 / deliverable-validator](08.05-WORKFLOW-COMPLETION/deliverable-validator.file.README.md) | ceta/task-and-workflow-engine/workflow-completion/deliverable-validator | LOCAL-INSPECTION-REQUIRED |
| [CETA-08.05.02 / completion-evidence-checker](08.05-WORKFLOW-COMPLETION/completion-evidence-checker.file.README.md) | ceta/task-and-workflow-engine/workflow-completion/completion-evidence-checker | LOCAL-INSPECTION-REQUIRED |
| [CETA-08.05.03 / task-finalization-controller](08.05-WORKFLOW-COMPLETION/task-finalization-controller.file.README.md) | ceta/task-and-workflow-engine/workflow-completion/task-finalization-controller | LOCAL-INSPECTION-REQUIRED |
