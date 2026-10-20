# 09-MODEL-RUNTIME - dependencies

## Construction prerequisites

| Required subsystem | Why it must be available |
| --- | --- |
| [02-IDENTITY-AND-AUTHORITY](../02-IDENTITY-AND-AUTHORITY/README.md) | Establish principals, authenticated sessions, delegated authority, and revocable execution capabilities. |
| [11-EXECUTION-AND-ISOLATION](../11-EXECUTION-AND-ISOLATION/README.md) | Enforce the final action boundary, isolate workers, observe real effects, and coordinate stopping and uncertain outcomes. |
| [18-SECURITY-AND-ENFORCEMENT](../18-SECURITY-AND-ENFORCEMENT/README.md) | Protect keys and secrets, define security boundaries, detect anomalies, contain incidents, and verify trust and dependency integrity. |
| [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md) | Own canonical operational state, transactional persistence, snapshots, migrations, recovery, and historical reconstruction. |
| [20-RESOURCE-MANAGEMENT](../20-RESOURCE-MANAGEMENT/README.md) | Profile hardware, reserve compute and memory, control workload admission, handle pressure, meter inference, and qualify offline behavior. |


## Shared contracts

| Contract | Canonical owner |
| --- | --- |
| [model-manifest](../INTERFACE-CONTRACTS/INTELLIGENCE/model-manifest.contract.md) | [09-MODEL-RUNTIME](README.md) |
| [inference-request](../INTERFACE-CONTRACTS/INTELLIGENCE/inference-request.contract.md) | [09-MODEL-RUNTIME](README.md) |
| [inference-response](../INTERFACE-CONTRACTS/INTELLIGENCE/inference-response.contract.md) | [09-MODEL-RUNTIME](README.md) |
| [resource-budget](../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/resource-budget.contract.md) | [20-RESOURCE-MANAGEMENT](../20-RESOURCE-MANAGEMENT/README.md) |
| [workload-admission](../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/workload-admission.contract.md) | [20-RESOURCE-MANAGEMENT](../20-RESOURCE-MANAGEMENT/README.md) |
| [verification-result](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) | [23-TESTING-AND-QUALIFICATION](../23-TESTING-AND-QUALIFICATION/README.md) |


## Dependency semantics

The build graph represents usable interface prerequisites, not an assertion that every downstream user-facing feature is already complete. Shared contract declarations and test fixtures are established first. Runtime communication can be bidirectional through approved ports without creating a build cycle. Optional connected channels, endpoints, and extensions never become mandatory dependencies for local core operation.

## Invalidation and failure

A changed contract revision, source digest, authority generation, model or tool implementation, resource qualification, or state schema invalidates the affected cached result and acceptance evidence. Missing prerequisites block only the dependent operation where safe; mandatory enforcement failure blocks effects. Do not substitute an unqualified fallback. See [the validated construction graph](../DEPENDENCY-MAPS/BUILD-ORDER-GRAPH.md) for global order and [recovery requirements](FAILURE-AND-RECOVERY.md) for interruption handling.
