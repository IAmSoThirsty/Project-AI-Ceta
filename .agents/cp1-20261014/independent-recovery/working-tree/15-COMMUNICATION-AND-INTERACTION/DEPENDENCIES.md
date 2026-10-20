# 15-COMMUNICATION-AND-INTERACTION - dependencies

## Construction prerequisites

| Required subsystem | Why it must be available |
| --- | --- |
| [02-IDENTITY-AND-AUTHORITY](../02-IDENTITY-AND-AUTHORITY/README.md) | Establish principals, authenticated sessions, delegated authority, and revocable execution capabilities. |
| [03-COMPANION-INTELLIGENCE](../03-COMPANION-INTELLIGENCE/README.md) | Provide a continuous human-facing intelligence that deliberates, remembers, proposes work, and reports governed outcomes. |
| [08-TASK-AND-WORKFLOW-ENGINE](../08-TASK-AND-WORKFLOW-ENGINE/README.md) | Execute durable task graphs with exact state transitions, safe retries, checkpoints, cancellation, and evidence-backed finalization. |
| [10-TOOLS-AND-CAPABILITIES](../10-TOOLS-AND-CAPABILITIES/README.md) | Expose native tools through declared schemas, effect classifications, controlled dispatch, and verifiable receipts. |
| [18-SECURITY-AND-ENFORCEMENT](../18-SECURITY-AND-ENFORCEMENT/README.md) | Protect keys and secrets, define security boundaries, detect anomalies, contain incidents, and verify trust and dependency integrity. |
| [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md) | Own canonical operational state, transactional persistence, snapshots, migrations, recovery, and historical reconstruction. |


## Shared contracts

| Contract | Canonical owner |
| --- | --- |
| [desktop-command](../INTERFACE-CONTRACTS/USER-INTERACTION/desktop-command.contract.md) | [22-DESKTOP-AND-USER-EXPERIENCE](../22-DESKTOP-AND-USER-EXPERIENCE/README.md) |
| [human-decision-request](../INTERFACE-CONTRACTS/USER-INTERACTION/human-decision-request.contract.md) | [15-COMMUNICATION-AND-INTERACTION](README.md) |
| [human-decision-response](../INTERFACE-CONTRACTS/USER-INTERACTION/human-decision-response.contract.md) | [15-COMMUNICATION-AND-INTERACTION](README.md) |
| [notification-event](../INTERFACE-CONTRACTS/USER-INTERACTION/notification-event.contract.md) | [15-COMMUNICATION-AND-INTERACTION](README.md) |
| [inference-request](../INTERFACE-CONTRACTS/INTELLIGENCE/inference-request.contract.md) | [09-MODEL-RUNTIME](../09-MODEL-RUNTIME/README.md) |
| [tool-invocation](../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/tool-invocation.contract.md) | [10-TOOLS-AND-CAPABILITIES](../10-TOOLS-AND-CAPABILITIES/README.md) |


## Dependency semantics

The build graph represents usable interface prerequisites, not an assertion that every downstream user-facing feature is already complete. Shared contract declarations and test fixtures are established first. Runtime communication can be bidirectional through approved ports without creating a build cycle. Optional connected channels, endpoints, and extensions never become mandatory dependencies for local core operation.

## Invalidation and failure

A changed contract revision, source digest, authority generation, model or tool implementation, resource qualification, or state schema invalidates the affected cached result and acceptance evidence. Missing prerequisites block only the dependent operation where safe; mandatory enforcement failure blocks effects. Do not substitute an unqualified fallback. See [the validated construction graph](../DEPENDENCY-MAPS/BUILD-ORDER-GRAPH.md) for global order and [recovery requirements](FAILURE-AND-RECOVERY.md) for interruption handling.
