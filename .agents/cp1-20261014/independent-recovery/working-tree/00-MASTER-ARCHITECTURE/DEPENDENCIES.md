# 00-MASTER-ARCHITECTURE - dependencies

## Construction prerequisites

This is the architecture root. Its prerequisite is an owner-approved local baseline and explicit integration scope.

## Shared contracts

| Contract | Canonical owner |
| --- | --- |
| [desktop-command](../INTERFACE-CONTRACTS/USER-INTERACTION/desktop-command.contract.md) | [22-DESKTOP-AND-USER-EXPERIENCE](../22-DESKTOP-AND-USER-EXPERIENCE/README.md) |
| [state-transition](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/state-transition.contract.md) | [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md) |
| [verification-result](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) | [23-TESTING-AND-QUALIFICATION](../23-TESTING-AND-QUALIFICATION/README.md) |
| [application-error](../INTERFACE-CONTRACTS/USER-INTERACTION/application-error.contract.md) | [00-MASTER-ARCHITECTURE](README.md) |


## Dependency semantics

The build graph represents usable interface prerequisites, not an assertion that every downstream user-facing feature is already complete. Shared contract declarations and test fixtures are established first. Runtime communication can be bidirectional through approved ports without creating a build cycle. Optional connected channels, endpoints, and extensions never become mandatory dependencies for local core operation.

## Invalidation and failure

A changed contract revision, source digest, authority generation, model or tool implementation, resource qualification, or state schema invalidates the affected cached result and acceptance evidence. Missing prerequisites block only the dependent operation where safe; mandatory enforcement failure blocks effects. Do not substitute an unqualified fallback. See [the validated construction graph](../DEPENDENCY-MAPS/BUILD-ORDER-GRAPH.md) for global order and [recovery requirements](FAILURE-AND-RECOVERY.md) for interruption handling.
