# 02-IDENTITY-AND-AUTHORITY - dependencies

## Construction prerequisites

| Required subsystem | Why it must be available |
| --- | --- |
| [00-MASTER-ARCHITECTURE](../00-MASTER-ARCHITECTURE/README.md) | Own the approved topology, component identities, lifecycle coordination, and local-source reconciliation rules. |
| [18-SECURITY-AND-ENFORCEMENT](../18-SECURITY-AND-ENFORCEMENT/README.md) | Protect keys and secrets, define security boundaries, detect anomalies, contain incidents, and verify trust and dependency integrity. |
| [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md) | Own canonical operational state, transactional persistence, snapshots, migrations, recovery, and historical reconstruction. |


## Shared contracts

| Contract | Canonical owner |
| --- | --- |
| [principal-identity](../INTERFACE-CONTRACTS/AUTHORITY/principal-identity.contract.md) | [02-IDENTITY-AND-AUTHORITY](README.md) |
| [authenticated-session](../INTERFACE-CONTRACTS/AUTHORITY/authenticated-session.contract.md) | [02-IDENTITY-AND-AUTHORITY](README.md) |
| [capability-token](../INTERFACE-CONTRACTS/AUTHORITY/capability-token.contract.md) | [02-IDENTITY-AND-AUTHORITY](README.md) |
| [authority-delegation](../INTERFACE-CONTRACTS/AUTHORITY/authority-delegation.contract.md) | [02-IDENTITY-AND-AUTHORITY](README.md) |
| [authority-revocation](../INTERFACE-CONTRACTS/AUTHORITY/authority-revocation.contract.md) | [02-IDENTITY-AND-AUTHORITY](README.md) |


## Dependency semantics

The build graph represents usable interface prerequisites, not an assertion that every downstream user-facing feature is already complete. Shared contract declarations and test fixtures are established first. Runtime communication can be bidirectional through approved ports without creating a build cycle. Optional connected channels, endpoints, and extensions never become mandatory dependencies for local core operation.

## Invalidation and failure

A changed contract revision, source digest, authority generation, model or tool implementation, resource qualification, or state schema invalidates the affected cached result and acceptance evidence. Missing prerequisites block only the dependent operation where safe; mandatory enforcement failure blocks effects. Do not substitute an unqualified fallback. See [the validated construction graph](../DEPENDENCY-MAPS/BUILD-ORDER-GRAPH.md) for global order and [recovery requirements](FAILURE-AND-RECOVERY.md) for interruption handling.
