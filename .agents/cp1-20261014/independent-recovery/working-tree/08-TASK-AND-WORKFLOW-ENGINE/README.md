# 08-TASK-AND-WORKFLOW-ENGINE

## Mission

Execute durable task graphs with exact state transitions, safe retries, checkpoints, cancellation, and evidence-backed finalization.

**Invariant:** Durable orchestration does not guarantee exactly-once external effects. Unknown outcomes require reconciliation before replay or compensation.

## Component map

| Component | End-to-end behavior | Planned files |
| --- | --- | --- |
| [08.01 Task Definition](08.01-TASK-DEFINITION/README.md) | Create an immutable task contract; validate acceptance criteria and effects; progress through allowed states; persist state changes with causal evidence. | 3 |
| [08.02 Workflow Graphs](08.02-WORKFLOW-GRAPHS/README.md) | Build a typed task graph; validate dependencies and branches; admit ready nodes; evaluate joins from recorded results; finalize only when required paths satisfy acceptance. | 3 |
| [08.03 Durable Execution](08.03-DURABLE-EXECUTION/README.md) | Persist admission and operation identity; launch the worker; checkpoint at safe boundaries; reconcile receipts after interruption; resume only validated remaining work. | 3 |
| [08.04 Failure Handling](08.04-FAILURE-HANDLING/README.md) | Classify failure by cause and effect certainty; select bounded retry, pause, reconciliation, or approved compensation; preserve the original failure record. | 3 |
| [08.05 Workflow Completion](08.05-WORKFLOW-COMPLETION/README.md) | Collect outputs; validate their content and provenance; run acceptance checks; obtain required independent review; commit a final result with evidence. | 3 |


## Read and build order

Read [architecture](ARCHITECTURE.md), [contracts](INTERFACE-CONTRACTS.md), [dependencies](DEPENDENCIES.md), and [build sequence](BUILD-SEQUENCE.md). Then load only the component and file specifications assigned to the current task. Use [the file index](FILE-INDEX.md) to find every planned source unit.

## Integration and qualification

Use [local integration instructions](INTEGRATION.md), [failure and recovery rules](FAILURE-AND-RECOVERY.md), [the test matrix](TEST-MATRIX.md), and [acceptance gate](ACCEPTANCE.md). [Agent assignments](AGENT-ASSIGNMENTS.md) defines construction responsibility and reviewer separation.

This subsystem contains 5 component folders and 15 planned implementation-file specifications. The package specifies their construction; it makes no claim about their presence in the uninspected local application. The initial reconciliation state for each logical path is LOCAL-INSPECTION-REQUIRED. Resolve that state through evidence before editing.
