# 21-EXTENSIONS-AND-INTEROPERABILITY

## Mission

Enable optional native extensions and generic interoperability through versioned contracts, qualification, scoped authority, and isolated lifecycle management.

**Invariant:** Extensions are optional untrusted components until qualified. Installation, discovery, and compatibility do not grant execution authority.

## Component map

| Component | End-to-end behavior | Planned files |
| --- | --- | --- |
| [21.01 Extension Manifests](21.01-EXTENSION-MANIFESTS/README.md) | Define extension content and interfaces; validate manifest and dependencies; inspect required effects; stage qualification before activation. | 3 |
| [21.02 Extension Lifecycle](21.02-EXTENSION-LIFECYCLE/README.md) | Stage verified artifacts; qualify in isolation; request activation; switch revisions atomically; revoke or uninstall with data and authority cleanup. | 3 |
| [21.03 Interoperability Contracts](21.03-INTEROPERABILITY-CONTRACTS/README.md) | Negotiate compatible schemas; authenticate the peer; translate only declared semantics; enforce scope and message limits; reject incompatible or ambiguous operations. | 3 |
| [21.04 Extension Security](21.04-EXTENSION-SECURITY/README.md) | Assign an extension principal; grant minimum capabilities; launch in qualified isolation; verify code integrity; monitor and revoke on boundary failure. | 3 |
| [21.05 Native Extension Kit](21.05-NATIVE-EXTENSION-KIT/README.md) | Provide native extension construction guidance and contract fixtures; generate only owner-requested templates in the future implementation; qualify extensions against the same runtime rules. | 3 |
| [21.06 Extension Catalog](21.06-EXTENSION-CATALOG/README.md) | Index inspectable extension metadata; verify integrity and review state; filter compatibility; present approval requirements; keep acquisition and activation separate. | 3 |


## Read and build order

Read [architecture](ARCHITECTURE.md), [contracts](INTERFACE-CONTRACTS.md), [dependencies](DEPENDENCIES.md), and [build sequence](BUILD-SEQUENCE.md). Then load only the component and file specifications assigned to the current task. Use [the file index](FILE-INDEX.md) to find every planned source unit.

## Integration and qualification

Use [local integration instructions](INTEGRATION.md), [failure and recovery rules](FAILURE-AND-RECOVERY.md), [the test matrix](TEST-MATRIX.md), and [acceptance gate](ACCEPTANCE.md). [Agent assignments](AGENT-ASSIGNMENTS.md) defines construction responsibility and reviewer separation.

This subsystem contains 6 component folders and 18 planned implementation-file specifications. The package specifies their construction; it makes no claim about their presence in the uninspected local application. The initial reconciliation state for each logical path is LOCAL-INSPECTION-REQUIRED. Resolve that state through evidence before editing.
