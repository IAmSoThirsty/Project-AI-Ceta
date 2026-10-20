# 10-TOOLS-AND-CAPABILITIES

## Mission

Expose native tools through declared schemas, effect classifications, controlled dispatch, and verifiable receipts.

**Invariant:** Tools declare effects before execution and return observations after execution. Discovery or selection never grants authority.

## Component map

| Component | End-to-end behavior | Planned files |
| --- | --- | --- |
| [10.01 Tool Registry](10.01-TOOL-REGISTRY/README.md) | Register a tool manifest; verify implementation binding and qualification; expose authorized discovery; pin the exact tool revision for each invocation. | 3 |
| [10.02 Tool Contracts](10.02-TOOL-CONTRACTS/README.md) | Validate exact arguments; classify all intended effects; bind normalized input to approval; validate returned observations before consumers use them. | 3 |
| [10.03 Local Operations](10.03-LOCAL-OPERATIONS/README.md) | Resolve local targets within approved roots; validate stable identities; execute through isolated native adapters; observe actual changes; return exact results. | 3 |
| [10.04 Network Operations](10.04-NETWORK-OPERATIONS/README.md) | Validate destination and payload scope; acquire explicit network authority; enforce redirects and size limits; record requests and observed outcomes; classify timeout uncertainty. | 3 |
| [10.05 Tool Execution Results](10.05-TOOL-EXECUTION-RESULTS/README.md) | Validate invocation; obtain gate admission; dispatch once per stable operation identity; normalize observations; bind an evidence receipt; return a typed outcome. | 3 |


## Read and build order

Read [architecture](ARCHITECTURE.md), [contracts](INTERFACE-CONTRACTS.md), [dependencies](DEPENDENCIES.md), and [build sequence](BUILD-SEQUENCE.md). Then load only the component and file specifications assigned to the current task. Use [the file index](FILE-INDEX.md) to find every planned source unit.

## Integration and qualification

Use [local integration instructions](INTEGRATION.md), [failure and recovery rules](FAILURE-AND-RECOVERY.md), [the test matrix](TEST-MATRIX.md), and [acceptance gate](ACCEPTANCE.md). [Agent assignments](AGENT-ASSIGNMENTS.md) defines construction responsibility and reviewer separation.

This subsystem contains 5 component folders and 15 planned implementation-file specifications. The package specifies their construction; it makes no claim about their presence in the uninspected local application. The initial reconciliation state for each logical path is LOCAL-INSPECTION-REQUIRED. Resolve that state through evidence before editing.
