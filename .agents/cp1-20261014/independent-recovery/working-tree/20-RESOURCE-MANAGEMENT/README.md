# 20-RESOURCE-MANAGEMENT

## Mission

Profile hardware, reserve compute and memory, control workload admission, handle pressure, meter inference, and qualify offline behavior.

**Invariant:** Resource estimates carry uncertainty and are checked against measurements. Stop, evidence, and recovery retain reserved capacity under pressure.

## Component map

| Component | End-to-end behavior | Planned files |
| --- | --- | --- |
| [20.01 Hardware Discovery](20.01-HARDWARE-DISCOVERY/README.md) | Inspect actual available hardware and runtime limits; measure usable capacity; monitor changes; publish a versioned capability profile with uncertainty. | 3 |
| [20.02 Resource Budgeting](20.02-RESOURCE-BUDGETING/README.md) | Define per-task and shared budgets; reserve atomically; meter actual use; throttle or stop at limits; release reservations after verified cleanup. | 3 |
| [20.03 Workload Admission](20.03-WORKLOAD-ADMISSION/README.md) | Estimate requirements; validate budgets and environment; reserve capacity; queue or admit fairly; fence expired reservations; release only after cleanup. | 3 |
| [20.04 Resource Pressure](20.04-RESOURCE-PRESSURE/README.md) | Detect sustained pressure; prioritize control and evidence; throttle optional work; stop unsafe admissions; recover gradually after measured stability. | 3 |
| [20.05 Operational Diagnostics](20.05-OPERATIONAL-DIAGNOSTICS/README.md) | Collect scoped resource telemetry; identify bottlenecks; compare against qualification envelopes; run offline and failure probes; report measured limits. | 3 |
| [20.06 Inference Accounting](20.06-INFERENCE-ACCOUNTING/README.md) | Meter observed inference usage; distinguish estimates and provider reports; charge parent and child tasks once; enforce budgets; reconcile interrupted streams. | 3 |


## Read and build order

Read [architecture](ARCHITECTURE.md), [contracts](INTERFACE-CONTRACTS.md), [dependencies](DEPENDENCIES.md), and [build sequence](BUILD-SEQUENCE.md). Then load only the component and file specifications assigned to the current task. Use [the file index](FILE-INDEX.md) to find every planned source unit.

## Integration and qualification

Use [local integration instructions](INTEGRATION.md), [failure and recovery rules](FAILURE-AND-RECOVERY.md), [the test matrix](TEST-MATRIX.md), and [acceptance gate](ACCEPTANCE.md). [Agent assignments](AGENT-ASSIGNMENTS.md) defines construction responsibility and reviewer separation.

This subsystem contains 6 component folders and 18 planned implementation-file specifications. The package specifies their construction; it makes no claim about their presence in the uninspected local application. The initial reconciliation state for each logical path is LOCAL-INSPECTION-REQUIRED. Resolve that state through evidence before editing.
