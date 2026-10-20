# 12-ENGINEERING-INTELLIGENCE - dependencies

## Construction prerequisites

| Required subsystem | Why it must be available |
| --- | --- |
| [05-CONTEXT-INTELLIGENCE](../05-CONTEXT-INTELLIGENCE/README.md) | Assemble bounded, attributable, task-relevant context while preserving instruction precedence and exact critical state. |
| [07-AGENT-ORCHESTRATION](../07-AGENT-ORCHESTRATION/README.md) | Coordinate specialized agents through bounded task contracts, explicit handoffs, concurrency control, and independent verification. |
| [08-TASK-AND-WORKFLOW-ENGINE](../08-TASK-AND-WORKFLOW-ENGINE/README.md) | Execute durable task graphs with exact state transitions, safe retries, checkpoints, cancellation, and evidence-backed finalization. |
| [10-TOOLS-AND-CAPABILITIES](../10-TOOLS-AND-CAPABILITIES/README.md) | Expose native tools through declared schemas, effect classifications, controlled dispatch, and verifiable receipts. |
| [17-EVIDENCE-AND-PROVENANCE](../17-EVIDENCE-AND-PROVENANCE/README.md) | Capture, seal, query, replay, and independently verify operation evidence and artifact lineage. |


## Shared contracts

| Contract | Canonical owner |
| --- | --- |
| [task-definition](../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/task-definition.contract.md) | [08-TASK-AND-WORKFLOW-ENGINE](../08-TASK-AND-WORKFLOW-ENGINE/README.md) |
| [tool-invocation](../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/tool-invocation.contract.md) | [10-TOOLS-AND-CAPABILITIES](../10-TOOLS-AND-CAPABILITIES/README.md) |
| [execution-result](../INTERFACE-CONTRACTS/EXECUTION/execution-result.contract.md) | [11-EXECUTION-AND-ISOLATION](../11-EXECUTION-AND-ISOLATION/README.md) |
| [verification-result](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) | [23-TESTING-AND-QUALIFICATION](../23-TESTING-AND-QUALIFICATION/README.md) |
| [evidence-receipt](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/evidence-receipt.contract.md) | [17-EVIDENCE-AND-PROVENANCE](../17-EVIDENCE-AND-PROVENANCE/README.md) |
| [context-snapshot](../INTERFACE-CONTRACTS/INTELLIGENCE/context-snapshot.contract.md) | [05-CONTEXT-INTELLIGENCE](../05-CONTEXT-INTELLIGENCE/README.md) |


## Dependency semantics

The build graph represents usable interface prerequisites, not an assertion that every downstream user-facing feature is already complete. Shared contract declarations and test fixtures are established first. Runtime communication can be bidirectional through approved ports without creating a build cycle. Optional connected channels, endpoints, and extensions never become mandatory dependencies for local core operation.

## Invalidation and failure

A changed contract revision, source digest, authority generation, model or tool implementation, resource qualification, or state schema invalidates the affected cached result and acceptance evidence. Missing prerequisites block only the dependent operation where safe; mandatory enforcement failure blocks effects. Do not substitute an unqualified fallback. See [the validated construction graph](../DEPENDENCY-MAPS/BUILD-ORDER-GRAPH.md) for global order and [recovery requirements](FAILURE-AND-RECOVERY.md) for interruption handling.
