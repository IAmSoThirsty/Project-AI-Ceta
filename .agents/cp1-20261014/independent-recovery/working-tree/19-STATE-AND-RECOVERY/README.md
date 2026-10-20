# 19-STATE-AND-RECOVERY

## Mission

Own canonical operational state, transactional persistence, snapshots, migrations, recovery, and historical reconstruction.

**Invariant:** Storage durability, authority validity, and external-effect certainty are independent. Recovery never silently replays uncertain effects or rolls back known revocations.

## Component map

| Component | End-to-end behavior | Planned files |
| --- | --- | --- |
| [19.01 State Register](19.01-STATE-REGISTER/README.md) | Define canonical records; validate expected versions and allowed transitions; commit state and event references; expose consistent reads and historical views. | 3 |
| [19.02 Durable Storage](19.02-DURABLE-STORAGE/README.md) | Open qualified local storage; validate schema and integrity; execute bounded transactions; commit state and publication intent atomically; recover after interruption. | 3 |
| [19.03 Snapshots](19.03-SNAPSHOTS/README.md) | Capture a consistent state boundary; write content and manifest; verify completeness; register a usable snapshot; retain and retire according to approved policy. | 3 |
| [19.04 Recovery](19.04-RECOVERY/README.md) | Inspect actual persisted state and effects; choose a validated recovery point; reconcile later observations; restore data; reauthenticate and requalify before resuming tasks. | 3 |
| [19.05 Migration](19.05-MIGRATION/README.md) | Plan compatibility and data transformations; run preflight and backup; stage or checkpoint migration; validate transformed data; commit activation; verify rollback or forward repair. | 3 |
| [19.06 Archival](19.06-ARCHIVAL/README.md) | Archive selected history with provenance and retention labels; validate exports; index permitted metadata; reconstruct authorized historical views without reactivating past authority. | 3 |


## Read and build order

Read [architecture](ARCHITECTURE.md), [contracts](INTERFACE-CONTRACTS.md), [dependencies](DEPENDENCIES.md), and [build sequence](BUILD-SEQUENCE.md). Then load only the component and file specifications assigned to the current task. Use [the file index](FILE-INDEX.md) to find every planned source unit.

## Integration and qualification

Use [local integration instructions](INTEGRATION.md), [failure and recovery rules](FAILURE-AND-RECOVERY.md), [the test matrix](TEST-MATRIX.md), and [acceptance gate](ACCEPTANCE.md). [Agent assignments](AGENT-ASSIGNMENTS.md) defines construction responsibility and reviewer separation.

This subsystem contains 6 component folders and 18 planned implementation-file specifications. The package specifies their construction; it makes no claim about their presence in the uninspected local application. The initial reconciliation state for each logical path is LOCAL-INSPECTION-REQUIRED. Resolve that state through evidence before editing.
