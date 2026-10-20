# 24-BUILD-AND-RELEASE

## Mission

Build, package, qualify, sign where configured, update, roll back, and deliver the complete native application with inspectable evidence.

**Invariant:** Release completion is determined by actual installed behavior and current evidence, not generated file volume, successful compilation, or a persuasive report.

## Component map

| Component | End-to-end behavior | Planned files |
| --- | --- | --- |
| [24.01 Build Orchestration](24.01-BUILD-ORCHESTRATION/README.md) | Pin source and dependencies; validate configuration; build in a controlled environment; record outputs; reproduce or explain declared nondeterministic fields; hand off exact artifacts. | 3 |
| [24.02 Version Management](24.02-VERSION-MANAGEMENT/README.md) | Assign a product release identity; validate component and schema compatibility; generate an immutable release manifest; bind version labels to exact artifacts and evidence. | 3 |
| [24.03 Packaging](24.03-PACKAGING/README.md) | Assemble only approved artifacts; validate contents and permissions; create a native installer or portable package; test clean installation and offline use; preserve user data on upgrade and removal. | 3 |
| [24.04 Release Integrity](24.04-RELEASE-INTEGRITY/README.md) | Bind release artifacts to the manifest; sign through approved protected facilities where configured; verify trust and exact bytes; record provenance and distribution identity. | 3 |
| [24.05 Update And Rollback](24.05-UPDATE-AND-ROLLBACK/README.md) | Validate the exact update; preflight compatibility and capacity; create a recovery point; apply staged changes; verify startup and data; roll back or forward-repair under declared rules. | 3 |
| [24.06 Product Completion](24.06-PRODUCT-COMPLETION/README.md) | Reconcile full approved scope; verify every mandatory gate; exercise complete installed workflows; inspect evidence independently; issue an accurate product-completion decision. | 3 |


## Read and build order

Read [architecture](ARCHITECTURE.md), [contracts](INTERFACE-CONTRACTS.md), [dependencies](DEPENDENCIES.md), and [build sequence](BUILD-SEQUENCE.md). Then load only the component and file specifications assigned to the current task. Use [the file index](FILE-INDEX.md) to find every planned source unit.

## Integration and qualification

Use [local integration instructions](INTEGRATION.md), [failure and recovery rules](FAILURE-AND-RECOVERY.md), [the test matrix](TEST-MATRIX.md), and [acceptance gate](ACCEPTANCE.md). [Agent assignments](AGENT-ASSIGNMENTS.md) defines construction responsibility and reviewer separation.

This subsystem contains 6 component folders and 18 planned implementation-file specifications. The package specifies their construction; it makes no claim about their presence in the uninspected local application. The initial reconciliation state for each logical path is LOCAL-INSPECTION-REQUIRED. Resolve that state through evidence before editing.
