# 13-NATIVE-DEVELOPMENT-WORKSPACE

## Mission

Provide a local project explorer, source editor, diff review, terminal, revision management, previews, and recoverable workspace state.

**Invariant:** The interface presents and proposes changes; native services enforce authority and filesystem boundaries. Local projects remain usable without remote hosting.

## Component map

| Component | End-to-end behavior | Planned files |
| --- | --- | --- |
| [13.01 Project Management](13.01-PROJECT-MANAGEMENT/README.md) | Open an owner-selected project; validate path boundaries; register the local baseline; restore authorized interface state; expose project structure and health. | 3 |
| [13.02 Source Editor](13.02-SOURCE-EDITOR/README.md) | Load exact source bytes; preserve encoding and line conventions; track edits; request governed save; reconcile external changes; display current diagnostics. | 3 |
| [13.03 Change Inspection](13.03-CHANGE-INSPECTION/README.md) | Compute exact changes; present text and binary summaries; stage selected modifications; obtain scoped approval; preserve revision history and recovery links. | 3 |
| [13.04 Terminal Workspace](13.04-TERMINAL-WORKSPACE/README.md) | Create a scoped terminal session; authorize commands; stream bounded output; preserve process ownership; stop or close cleanly; retain safe history. | 3 |
| [13.05 Version Control](13.05-VERSION-CONTROL/README.md) | Use available local revision facilities or native snapshots; isolate work; compare revisions; reconcile conflicts; publish verified changes while preserving owner state. | 3 |
| [13.06 Development Preview](13.06-DEVELOPMENT-PREVIEW/README.md) | Launch a controlled local preview; bind it to a source revision; observe rendered behavior; capture test evidence; recover preview and workspace state separately. | 3 |


## Read and build order

Read [architecture](ARCHITECTURE.md), [contracts](INTERFACE-CONTRACTS.md), [dependencies](DEPENDENCIES.md), and [build sequence](BUILD-SEQUENCE.md). Then load only the component and file specifications assigned to the current task. Use [the file index](FILE-INDEX.md) to find every planned source unit.

## Integration and qualification

Use [local integration instructions](INTEGRATION.md), [failure and recovery rules](FAILURE-AND-RECOVERY.md), [the test matrix](TEST-MATRIX.md), and [acceptance gate](ACCEPTANCE.md). [Agent assignments](AGENT-ASSIGNMENTS.md) defines construction responsibility and reviewer separation.

This subsystem contains 6 component folders and 18 planned implementation-file specifications. The package specifies their construction; it makes no claim about their presence in the uninspected local application. The initial reconciliation state for each logical path is LOCAL-INSPECTION-REQUIRED. Resolve that state through evidence before editing.
