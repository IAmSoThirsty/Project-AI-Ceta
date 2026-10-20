# 03-COMPANION-INTELLIGENCE - dependencies

## Construction prerequisites

| Required subsystem | Why it must be available |
| --- | --- |
| [04-PERSISTENT-MEMORY](../04-PERSISTENT-MEMORY/README.md) | Preserve episodic, semantic, and procedural information with provenance, access control, correction, and portability. |
| [05-CONTEXT-INTELLIGENCE](../05-CONTEXT-INTELLIGENCE/README.md) | Assemble bounded, attributable, task-relevant context while preserving instruction precedence and exact critical state. |
| [07-AGENT-ORCHESTRATION](../07-AGENT-ORCHESTRATION/README.md) | Coordinate specialized agents through bounded task contracts, explicit handoffs, concurrency control, and independent verification. |
| [08-TASK-AND-WORKFLOW-ENGINE](../08-TASK-AND-WORKFLOW-ENGINE/README.md) | Execute durable task graphs with exact state transitions, safe retries, checkpoints, cancellation, and evidence-backed finalization. |
| [09-MODEL-RUNTIME](../09-MODEL-RUNTIME/README.md) | Manage native model artifacts, qualified inference, optional owner-configured endpoints, routing, lifecycle, and controlled customization. |


## Shared contracts

| Contract | Canonical owner |
| --- | --- |
| [agent-manifest](../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/agent-manifest.contract.md) | [07-AGENT-ORCHESTRATION](../07-AGENT-ORCHESTRATION/README.md) |
| [inference-request](../INTERFACE-CONTRACTS/INTELLIGENCE/inference-request.contract.md) | [09-MODEL-RUNTIME](../09-MODEL-RUNTIME/README.md) |
| [context-snapshot](../INTERFACE-CONTRACTS/INTELLIGENCE/context-snapshot.contract.md) | [05-CONTEXT-INTELLIGENCE](../05-CONTEXT-INTELLIGENCE/README.md) |
| [memory-record](../INTERFACE-CONTRACTS/INTELLIGENCE/memory-record.contract.md) | [04-PERSISTENT-MEMORY](../04-PERSISTENT-MEMORY/README.md) |
| [human-decision-request](../INTERFACE-CONTRACTS/USER-INTERACTION/human-decision-request.contract.md) | [15-COMMUNICATION-AND-INTERACTION](../15-COMMUNICATION-AND-INTERACTION/README.md) |
| [task-definition](../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/task-definition.contract.md) | [08-TASK-AND-WORKFLOW-ENGINE](../08-TASK-AND-WORKFLOW-ENGINE/README.md) |


## Dependency semantics

The build graph represents usable interface prerequisites, not an assertion that every downstream user-facing feature is already complete. Shared contract declarations and test fixtures are established first. Runtime communication can be bidirectional through approved ports without creating a build cycle. Optional connected channels, endpoints, and extensions never become mandatory dependencies for local core operation.

## Invalidation and failure

A changed contract revision, source digest, authority generation, model or tool implementation, resource qualification, or state schema invalidates the affected cached result and acceptance evidence. Missing prerequisites block only the dependent operation where safe; mandatory enforcement failure blocks effects. Do not substitute an unqualified fallback. See [the validated construction graph](../DEPENDENCY-MAPS/BUILD-ORDER-GRAPH.md) for global order and [recovery requirements](FAILURE-AND-RECOVERY.md) for interruption handling.
