# R08 subsystem scope

Primary responsibility or specialist contribution; exact write ownership is assigned per change set.

| Subsystem | Purpose |
| --- | --- |
| [08-TASK-AND-WORKFLOW-ENGINE](../../08-TASK-AND-WORKFLOW-ENGINE/README.md) | Execute durable task graphs with exact state transitions, safe retries, checkpoints, cancellation, and evidence-backed finalization. |
| [14-AUTOMATION-AND-SCHEDULING](../../14-AUTOMATION-AND-SCHEDULING/README.md) | Create durable time- and event-triggered tasks with explicit authority renewal, concurrency, missed-trigger handling, and observable outcomes. |

## Ownership coordination

Use [the assignment matrix](../ROLE-ASSIGNMENT-MATRIX.md) and the per-file specifications to identify builders and reviewers. One active writer owns each mapped source path. Shared schemas remain with the canonical schema owner even when this role contributes to their implementation. A conflict is resolved before either agent publishes changes.
