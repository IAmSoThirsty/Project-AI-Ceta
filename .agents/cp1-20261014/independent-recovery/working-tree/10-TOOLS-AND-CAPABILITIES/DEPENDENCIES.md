# 10-TOOLS-AND-CAPABILITIES - dependencies

## Construction prerequisites

| Required subsystem | Why it must be available |
| --- | --- |
| [02-IDENTITY-AND-AUTHORITY](../02-IDENTITY-AND-AUTHORITY/README.md) | Establish principals, authenticated sessions, delegated authority, and revocable execution capabilities. |
| [11-EXECUTION-AND-ISOLATION](../11-EXECUTION-AND-ISOLATION/README.md) | Enforce the final action boundary, isolate workers, observe real effects, and coordinate stopping and uncertain outcomes. |
| [17-EVIDENCE-AND-PROVENANCE](../17-EVIDENCE-AND-PROVENANCE/README.md) | Capture, seal, query, replay, and independently verify operation evidence and artifact lineage. |
| [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md) | Own canonical operational state, transactional persistence, snapshots, migrations, recovery, and historical reconstruction. |


## Shared contracts

| Contract | Canonical owner |
| --- | --- |
| [tool-manifest](../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/tool-manifest.contract.md) | [10-TOOLS-AND-CAPABILITIES](README.md) |
| [tool-invocation](../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/tool-invocation.contract.md) | [10-TOOLS-AND-CAPABILITIES](README.md) |
| [tool-result](../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/tool-result.contract.md) | [10-TOOLS-AND-CAPABILITIES](README.md) |
| [intended-effect](../INTERFACE-CONTRACTS/EXECUTION/intended-effect.contract.md) | [11-EXECUTION-AND-ISOLATION](../11-EXECUTION-AND-ISOLATION/README.md) |
| [execution-request](../INTERFACE-CONTRACTS/EXECUTION/execution-request.contract.md) | [11-EXECUTION-AND-ISOLATION](../11-EXECUTION-AND-ISOLATION/README.md) |
| [evidence-receipt](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/evidence-receipt.contract.md) | [17-EVIDENCE-AND-PROVENANCE](../17-EVIDENCE-AND-PROVENANCE/README.md) |


## Dependency semantics

The build graph represents usable interface prerequisites, not an assertion that every downstream user-facing feature is already complete. Shared contract declarations and test fixtures are established first. Runtime communication can be bidirectional through approved ports without creating a build cycle. Optional connected channels, endpoints, and extensions never become mandatory dependencies for local core operation.

## Invalidation and failure

A changed contract revision, source digest, authority generation, model or tool implementation, resource qualification, or state schema invalidates the affected cached result and acceptance evidence. Missing prerequisites block only the dependent operation where safe; mandatory enforcement failure blocks effects. Do not substitute an unqualified fallback. See [the validated construction graph](../DEPENDENCY-MAPS/BUILD-ORDER-GRAPH.md) for global order and [recovery requirements](FAILURE-AND-RECOVERY.md) for interruption handling.
