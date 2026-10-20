# 19-STATE-AND-RECOVERY - dependencies

## Construction prerequisites

| Required subsystem | Why it must be available |
| --- | --- |
| [00-MASTER-ARCHITECTURE](../00-MASTER-ARCHITECTURE/README.md) | Own the approved topology, component identities, lifecycle coordination, and local-source reconciliation rules. |


## Shared contracts

| Contract | Canonical owner |
| --- | --- |
| [state-transition](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/state-transition.contract.md) | [19-STATE-AND-RECOVERY](README.md) |
| [persistent-checkpoint](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/persistent-checkpoint.contract.md) | [19-STATE-AND-RECOVERY](README.md) |
| [uncertain-operation](../INTERFACE-CONTRACTS/EXECUTION/uncertain-operation.contract.md) | [11-EXECUTION-AND-ISOLATION](../11-EXECUTION-AND-ISOLATION/README.md) |
| [recovery-report](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/recovery-report.contract.md) | [19-STATE-AND-RECOVERY](README.md) |
| [provenance-link](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/provenance-link.contract.md) | [17-EVIDENCE-AND-PROVENANCE](../17-EVIDENCE-AND-PROVENANCE/README.md) |


## Dependency semantics

The build graph represents usable interface prerequisites, not an assertion that every downstream user-facing feature is already complete. Shared contract declarations and test fixtures are established first. Runtime communication can be bidirectional through approved ports without creating a build cycle. Optional connected channels, endpoints, and extensions never become mandatory dependencies for local core operation.

## Invalidation and failure

A changed contract revision, source digest, authority generation, model or tool implementation, resource qualification, or state schema invalidates the affected cached result and acceptance evidence. Missing prerequisites block only the dependent operation where safe; mandatory enforcement failure blocks effects. Do not substitute an unqualified fallback. See [the validated construction graph](../DEPENDENCY-MAPS/BUILD-ORDER-GRAPH.md) for global order and [recovery requirements](FAILURE-AND-RECOVERY.md) for interruption handling.
