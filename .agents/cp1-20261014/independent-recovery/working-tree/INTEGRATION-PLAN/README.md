# Local CETA integration plan

Start from the actual owner-selected local application. This package supplies exact logical units and complete construction instructions without assuming a remote repository, implementation language, or current source layout.

| Plan | Goal |
| --- | --- |
| [Existing Application Inventory](EXISTING-APPLICATION-INVENTORY.md) | Create a read-only evidence baseline of the actual local application. |
| [Reuse Extend Create Decision Matrix](REUSE-EXTEND-CREATE-DECISION-MATRIX.md) | Assign an evidence-based integration decision to every logical unit. |
| [Canonical File Ownership](CANONICAL-FILE-OWNERSHIP.md) | Give every mapped source path one active writer and each shared schema one canonical owner. |
| [Local Source Path Mapping](LOCAL-SOURCE-PATH-MAPPING.md) | Bind all 432 logical units to actual local filenames and modules. |
| [Interface Compatibility Plan](INTERFACE-COMPATIBILITY-PLAN.md) | Preserve canonical contract semantics across actual producers and consumers. |
| [State And Data Migration Plan](STATE-AND-DATA-MIGRATION-PLAN.md) | Preserve user data and current security state while changing schemas or owners. |
| [Incremental Integration Order](INCREMENTAL-INTEGRATION-ORDER.md) | Integrate in validated dependency order with working vertical paths. |
| [Existing Behavior Preservation](EXISTING-BEHAVIOR-PRESERVATION.md) | Keep already working local behavior and acceptance obligations intact. |
| [Integration Rollback Plan](INTEGRATION-ROLLBACK-PLAN.md) | Provide a verified safe retreat for each consequential integration step. |
