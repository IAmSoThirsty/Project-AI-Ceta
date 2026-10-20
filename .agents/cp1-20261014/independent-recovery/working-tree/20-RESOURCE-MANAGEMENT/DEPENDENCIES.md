# 20-RESOURCE-MANAGEMENT - dependencies

## Construction prerequisites

| Required subsystem | Why it must be available |
| --- | --- |
| [00-MASTER-ARCHITECTURE](../00-MASTER-ARCHITECTURE/README.md) | Own the approved topology, component identities, lifecycle coordination, and local-source reconciliation rules. |
| [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md) | Own canonical operational state, transactional persistence, snapshots, migrations, recovery, and historical reconstruction. |


## Shared contracts

| Contract | Canonical owner |
| --- | --- |
| [resource-budget](../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/resource-budget.contract.md) | [20-RESOURCE-MANAGEMENT](README.md) |
| [workload-admission](../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/workload-admission.contract.md) | [20-RESOURCE-MANAGEMENT](README.md) |
| [inference-request](../INTERFACE-CONTRACTS/INTELLIGENCE/inference-request.contract.md) | [09-MODEL-RUNTIME](../09-MODEL-RUNTIME/README.md) |
| [inference-response](../INTERFACE-CONTRACTS/INTELLIGENCE/inference-response.contract.md) | [09-MODEL-RUNTIME](../09-MODEL-RUNTIME/README.md) |
| [verification-result](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) | [23-TESTING-AND-QUALIFICATION](../23-TESTING-AND-QUALIFICATION/README.md) |


## Dependency semantics

The build graph represents usable interface prerequisites, not an assertion that every downstream user-facing feature is already complete. Shared contract declarations and test fixtures are established first. Runtime communication can be bidirectional through approved ports without creating a build cycle. Optional connected channels, endpoints, and extensions never become mandatory dependencies for local core operation.

## Invalidation and failure

A changed contract revision, source digest, authority generation, model or tool implementation, resource qualification, or state schema invalidates the affected cached result and acceptance evidence. Missing prerequisites block only the dependent operation where safe; mandatory enforcement failure blocks effects. Do not substitute an unqualified fallback. See [the validated construction graph](../DEPENDENCY-MAPS/BUILD-ORDER-GRAPH.md) for global order and [recovery requirements](FAILURE-AND-RECOVERY.md) for interruption handling.
