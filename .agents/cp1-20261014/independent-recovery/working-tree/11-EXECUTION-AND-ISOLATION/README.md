# 11-EXECUTION-AND-ISOLATION

## Mission

Enforce the final action boundary, isolate workers, observe real effects, and coordinate stopping and uncertain outcomes.

**Invariant:** Authorization is bound to exact inputs and target identity and rechecked at the effect boundary. Isolation is qualified on the actual operating environment.

## Component map

| Component | End-to-end behavior | Planned files |
| --- | --- | --- |
| [11.01 Execution Gate](11.01-EXECUTION-GATE/README.md) | Validate immutable operation inputs; verify current authority; reserve resources and evidence capacity; atomically record admission; dispatch through qualified isolation. | 3 |
| [11.02 Execution Sandbox](11.02-EXECUTION-SANDBOX/README.md) | Construct a least-authority worker environment; verify actual restrictions; launch the bound worker; observe effects; terminate and verify cleanup. | 3 |
| [11.03 Effect Control](11.03-EFFECT-CONTROL/README.md) | Declare intended effects; bind target and preconditions; observe actual operations independently; compare expected and actual effects; contain deviations. | 3 |
| [11.04 Stop And Cancellation](11.04-STOP-AND-CANCELLATION/README.md) | Accept an authenticated stop; prevent new admissions; signal workers; escalate termination by policy; observe residual effects; persist the final cancellation outcome. | 3 |
| [11.05 Execution Transactions](11.05-EXECUTION-TRANSACTIONS/README.md) | Persist intent; stage reversible local changes; perform authorized effects; commit observations; reconcile interrupted transactions; compensate only with explicit scope. | 3 |
| [11.06 Octoreflex Boundary](11.06-OCTOREFLEX-BOUNDARY/README.md) | Reconcile the existing native enforcement boundary; translate approved restrictions; qualify enforcement and observation on the target platform; attest actual installed policy. | 3 |


## Read and build order

Read [architecture](ARCHITECTURE.md), [contracts](INTERFACE-CONTRACTS.md), [dependencies](DEPENDENCIES.md), and [build sequence](BUILD-SEQUENCE.md). Then load only the component and file specifications assigned to the current task. Use [the file index](FILE-INDEX.md) to find every planned source unit.

## Integration and qualification

Use [local integration instructions](INTEGRATION.md), [failure and recovery rules](FAILURE-AND-RECOVERY.md), [the test matrix](TEST-MATRIX.md), and [acceptance gate](ACCEPTANCE.md). [Agent assignments](AGENT-ASSIGNMENTS.md) defines construction responsibility and reviewer separation.

This subsystem contains 6 component folders and 18 planned implementation-file specifications. The package specifies their construction; it makes no claim about their presence in the uninspected local application. The initial reconciliation state for each logical path is LOCAL-INSPECTION-REQUIRED. Resolve that state through evidence before editing.
