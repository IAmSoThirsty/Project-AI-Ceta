# 02-IDENTITY-AND-AUTHORITY

## Mission

Establish principals, authenticated sessions, delegated authority, and revocable execution capabilities.

**Invariant:** Authority is explicit, bounded, attributable, and checked at use time. A model response or UI state is never an authentication proof.

## Component map

| Component | End-to-end behavior | Planned files |
| --- | --- | --- |
| [02.01 Principal Identity](02.01-PRINCIPAL-IDENTITY/README.md) | Enroll a principal through an authorized process; verify credentials; bind device and process identities where required; rotate or revoke without losing attribution. | 3 |
| [02.02 Session Authority](02.02-SESSION-AUTHORITY/README.md) | Establish a session; calculate its permitted scope; refresh only through valid reauthentication; terminate and invalidate cached authority. | 3 |
| [02.03 Capability Tokens](02.03-CAPABILITY-TOKENS/README.md) | Issue a capability from approved authority; bind exact scope and effect inputs; validate authenticity and current status; consume or revoke according to its usage rule. | 3 |
| [02.04 Delegated Authority](02.04-DELEGATED-AUTHORITY/README.md) | Construct a bounded delegation graph; verify parent-child attenuation; propagate revocation; reevaluate dependent work at admission and effect boundaries. | 3 |
| [02.05 Authority Recovery](02.05-AUTHORITY-RECOVERY/README.md) | Enter a restricted recovery flow; verify configured recovery proofs; rotate affected authority; invalidate old credentials; test restored control before reopening effects. | 3 |


## Read and build order

Read [architecture](ARCHITECTURE.md), [contracts](INTERFACE-CONTRACTS.md), [dependencies](DEPENDENCIES.md), and [build sequence](BUILD-SEQUENCE.md). Then load only the component and file specifications assigned to the current task. Use [the file index](FILE-INDEX.md) to find every planned source unit.

## Integration and qualification

Use [local integration instructions](INTEGRATION.md), [failure and recovery rules](FAILURE-AND-RECOVERY.md), [the test matrix](TEST-MATRIX.md), and [acceptance gate](ACCEPTANCE.md). [Agent assignments](AGENT-ASSIGNMENTS.md) defines construction responsibility and reviewer separation.

This subsystem contains 5 component folders and 15 planned implementation-file specifications. The package specifies their construction; it makes no claim about their presence in the uninspected local application. The initial reconciliation state for each logical path is LOCAL-INSPECTION-REQUIRED. Resolve that state through evidence before editing.
