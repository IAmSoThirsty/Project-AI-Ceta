# R16 subsystem scope

Primary responsibility or specialist contribution; exact write ownership is assigned per change set.

| Subsystem | Purpose |
| --- | --- |
| [19-STATE-AND-RECOVERY](../../19-STATE-AND-RECOVERY/README.md) | Own canonical operational state, transactional persistence, snapshots, migrations, recovery, and historical reconstruction. |

## Ownership coordination

Use [the assignment matrix](../ROLE-ASSIGNMENT-MATRIX.md) and the per-file specifications to identify builders and reviewers. One active writer owns each mapped source path. Shared schemas remain with the canonical schema owner even when this role contributes to their implementation. A conflict is resolved before either agent publishes changes.
