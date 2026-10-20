# R02 subsystem scope

Reconciliation and compatibility scope; implementation ownership remains with each assigned builder.

| Subsystem | Purpose |
| --- | --- |
| [00-MASTER-ARCHITECTURE](../../00-MASTER-ARCHITECTURE/README.md) | Own the approved topology, component identities, lifecycle coordination, and local-source reconciliation rules. |
| [19-STATE-AND-RECOVERY](../../19-STATE-AND-RECOVERY/README.md) | Own canonical operational state, transactional persistence, snapshots, migrations, recovery, and historical reconstruction. |
| [24-BUILD-AND-RELEASE](../../24-BUILD-AND-RELEASE/README.md) | Build, package, qualify, sign where configured, update, roll back, and deliver the complete native application with inspectable evidence. |

## Ownership coordination

Use [the assignment matrix](../ROLE-ASSIGNMENT-MATRIX.md) and the per-file specifications to identify builders and reviewers. One active writer owns each mapped source path. Shared schemas remain with the canonical schema owner even when this role contributes to their implementation. A conflict is resolved before either agent publishes changes.
