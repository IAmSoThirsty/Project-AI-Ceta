# 11-EXECUTION-AND-ISOLATION - dependencies

## Construction prerequisites

| Required subsystem | Why it must be available |
| --- | --- |
| [01-CONSTITUTIONAL-GOVERNANCE](../01-CONSTITUTIONAL-GOVERNANCE/README.md) | Interpret owner-approved constitutional rules and produce explainable, version-bound governance decisions. |
| [02-IDENTITY-AND-AUTHORITY](../02-IDENTITY-AND-AUTHORITY/README.md) | Establish principals, authenticated sessions, delegated authority, and revocable execution capabilities. |
| [17-EVIDENCE-AND-PROVENANCE](../17-EVIDENCE-AND-PROVENANCE/README.md) | Capture, seal, query, replay, and independently verify operation evidence and artifact lineage. |
| [18-SECURITY-AND-ENFORCEMENT](../18-SECURITY-AND-ENFORCEMENT/README.md) | Protect keys and secrets, define security boundaries, detect anomalies, contain incidents, and verify trust and dependency integrity. |
| [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md) | Own canonical operational state, transactional persistence, snapshots, migrations, recovery, and historical reconstruction. |
| [20-RESOURCE-MANAGEMENT](../20-RESOURCE-MANAGEMENT/README.md) | Profile hardware, reserve compute and memory, control workload admission, handle pressure, meter inference, and qualify offline behavior. |


## Shared contracts

| Contract | Canonical owner |
| --- | --- |
| [execution-request](../INTERFACE-CONTRACTS/EXECUTION/execution-request.contract.md) | [11-EXECUTION-AND-ISOLATION](README.md) |
| [intended-effect](../INTERFACE-CONTRACTS/EXECUTION/intended-effect.contract.md) | [11-EXECUTION-AND-ISOLATION](README.md) |
| [isolation-context](../INTERFACE-CONTRACTS/EXECUTION/isolation-context.contract.md) | [11-EXECUTION-AND-ISOLATION](README.md) |
| [stop-signal](../INTERFACE-CONTRACTS/EXECUTION/stop-signal.contract.md) | [11-EXECUTION-AND-ISOLATION](README.md) |
| [uncertain-operation](../INTERFACE-CONTRACTS/EXECUTION/uncertain-operation.contract.md) | [11-EXECUTION-AND-ISOLATION](README.md) |
| [execution-result](../INTERFACE-CONTRACTS/EXECUTION/execution-result.contract.md) | [11-EXECUTION-AND-ISOLATION](README.md) |
| [capability-token](../INTERFACE-CONTRACTS/AUTHORITY/capability-token.contract.md) | [02-IDENTITY-AND-AUTHORITY](../02-IDENTITY-AND-AUTHORITY/README.md) |


## Dependency semantics

The build graph represents usable interface prerequisites, not an assertion that every downstream user-facing feature is already complete. Shared contract declarations and test fixtures are established first. Runtime communication can be bidirectional through approved ports without creating a build cycle. Optional connected channels, endpoints, and extensions never become mandatory dependencies for local core operation.

## Invalidation and failure

A changed contract revision, source digest, authority generation, model or tool implementation, resource qualification, or state schema invalidates the affected cached result and acceptance evidence. Missing prerequisites block only the dependent operation where safe; mandatory enforcement failure blocks effects. Do not substitute an unqualified fallback. See [the validated construction graph](../DEPENDENCY-MAPS/BUILD-ORDER-GRAPH.md) for global order and [recovery requirements](FAILURE-AND-RECOVERY.md) for interruption handling.
