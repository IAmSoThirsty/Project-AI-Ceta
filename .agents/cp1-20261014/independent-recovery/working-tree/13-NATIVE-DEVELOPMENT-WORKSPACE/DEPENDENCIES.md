# 13-NATIVE-DEVELOPMENT-WORKSPACE - dependencies

## Construction prerequisites

| Required subsystem | Why it must be available |
| --- | --- |
| [10-TOOLS-AND-CAPABILITIES](../10-TOOLS-AND-CAPABILITIES/README.md) | Expose native tools through declared schemas, effect classifications, controlled dispatch, and verifiable receipts. |
| [12-ENGINEERING-INTELLIGENCE](../12-ENGINEERING-INTELLIGENCE/README.md) | Turn approved engineering requirements into inspected source changes, reproducible tests, independent review, and evidence-backed delivery. |
| [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md) | Own canonical operational state, transactional persistence, snapshots, migrations, recovery, and historical reconstruction. |
| [22-DESKTOP-AND-USER-EXPERIENCE](../22-DESKTOP-AND-USER-EXPERIENCE/README.md) | Provide an accessible native application shell, command center, owner controls, decision surfaces, evidence inspection, onboarding, and maintenance. |


## Shared contracts

| Contract | Canonical owner |
| --- | --- |
| [desktop-command](../INTERFACE-CONTRACTS/USER-INTERACTION/desktop-command.contract.md) | [22-DESKTOP-AND-USER-EXPERIENCE](../22-DESKTOP-AND-USER-EXPERIENCE/README.md) |
| [tool-invocation](../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/tool-invocation.contract.md) | [10-TOOLS-AND-CAPABILITIES](../10-TOOLS-AND-CAPABILITIES/README.md) |
| [human-decision-request](../INTERFACE-CONTRACTS/USER-INTERACTION/human-decision-request.contract.md) | [15-COMMUNICATION-AND-INTERACTION](../15-COMMUNICATION-AND-INTERACTION/README.md) |
| [execution-result](../INTERFACE-CONTRACTS/EXECUTION/execution-result.contract.md) | [11-EXECUTION-AND-ISOLATION](../11-EXECUTION-AND-ISOLATION/README.md) |
| [persistent-checkpoint](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/persistent-checkpoint.contract.md) | [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md) |


## Dependency semantics

The build graph represents usable interface prerequisites, not an assertion that every downstream user-facing feature is already complete. Shared contract declarations and test fixtures are established first. Runtime communication can be bidirectional through approved ports without creating a build cycle. Optional connected channels, endpoints, and extensions never become mandatory dependencies for local core operation.

## Invalidation and failure

A changed contract revision, source digest, authority generation, model or tool implementation, resource qualification, or state schema invalidates the affected cached result and acceptance evidence. Missing prerequisites block only the dependent operation where safe; mandatory enforcement failure blocks effects. Do not substitute an unqualified fallback. See [the validated construction graph](../DEPENDENCY-MAPS/BUILD-ORDER-GRAPH.md) for global order and [recovery requirements](FAILURE-AND-RECOVERY.md) for interruption handling.
