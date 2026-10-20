# 13-NATIVE-DEVELOPMENT-WORKSPACE - construction sequence

## Entry criteria

The local application has an inspected baseline, assigned source ownership, approved contract bindings, and preserved existing acceptance requirements. Required prerequisites: [10-TOOLS-AND-CAPABILITIES](../10-TOOLS-AND-CAPABILITIES/README.md), [12-ENGINEERING-INTELLIGENCE](../12-ENGINEERING-INTELLIGENCE/README.md), [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md), [22-DESKTOP-AND-USER-EXPERIENCE](../22-DESKTOP-AND-USER-EXPERIENCE/README.md).

## Ordered work

1. Inspect the existing local implementation and classify every logical unit as reuse, extend, or create; record exact source digests.
2. Approve canonical interfaces, domain records, error semantics, and state ownership with affected producers and consumers.
3. Create positive, negative, boundary, and recovery fixtures before relying on the new behavior.
4. Implement pure validation and transformation logic first; then connect canonical state, authority, resources, evidence, and controlled effects as applicable.
5. Integrate the component flows listed below in their actual dependency order, using the existing application composition mechanism.
6. Exercise real cross-subsystem paths and concurrency, cancellation, resource, and recovery failures.
7. Update user and engineering documentation from observed behavior and preserve source-to-test-to-artifact traceability.
8. Submit exact artifacts and raw evidence to independent verification; close the subsystem gate only after all required obligations pass.

## Component integration units

| Component | Flow to construct |
| --- | --- |
| [13.01 Project Management](13.01-PROJECT-MANAGEMENT/README.md) | Open an owner-selected project; validate path boundaries; register the local baseline; restore authorized interface state; expose project structure and health. |
| [13.02 Source Editor](13.02-SOURCE-EDITOR/README.md) | Load exact source bytes; preserve encoding and line conventions; track edits; request governed save; reconcile external changes; display current diagnostics. |
| [13.03 Change Inspection](13.03-CHANGE-INSPECTION/README.md) | Compute exact changes; present text and binary summaries; stage selected modifications; obtain scoped approval; preserve revision history and recovery links. |
| [13.04 Terminal Workspace](13.04-TERMINAL-WORKSPACE/README.md) | Create a scoped terminal session; authorize commands; stream bounded output; preserve process ownership; stop or close cleanly; retain safe history. |
| [13.05 Version Control](13.05-VERSION-CONTROL/README.md) | Use available local revision facilities or native snapshots; isolate work; compare revisions; reconcile conflicts; publish verified changes while preserving owner state. |
| [13.06 Development Preview](13.06-DEVELOPMENT-PREVIEW/README.md) | Launch a controlled local preview; bind it to a source revision; observe rendered behavior; capture test evidence; recover preview and workspace state separately. |


## Parallel work and exit

Parallel implementation is allowed only after shared interfaces are stable and write scopes are disjoint. A stale lease cannot publish canonical changes. A conflict returns to the owning architecture or integration role, not to a last-writer-wins merge. Exit requires [the subsystem acceptance gate](ACCEPTANCE.md) and independent review of the delivered revision.
