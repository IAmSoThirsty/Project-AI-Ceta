# 07-AGENT-ORCHESTRATION

## Mission

Coordinate specialized agents through bounded task contracts, explicit handoffs, concurrency control, and independent verification.

**Invariant:** Agent consensus cannot create authority or factual proof. Builders and final verifiers have distinct assignments and evidence obligations.

## Component map

| Component | End-to-end behavior | Planned files |
| --- | --- | --- |
| [07.01 Agent Registry](07.01-AGENT-REGISTRY/README.md) | Register agents and roles; bind authenticated execution identities; match qualified capabilities; expose availability without granting new permissions. | 3 |
| [07.02 Agent Planning](07.02-AGENT-PLANNING/README.md) | Decompose the goal; assign testable outputs; identify dependencies and shared writes; allocate agents; validate the plan before execution. | 3 |
| [07.03 Agent Communication](07.03-AGENT-COMMUNICATION/README.md) | Authenticate agent messages; validate task scope and sequence; deliver idempotently; acknowledge handoffs; reconcile missing or duplicate messages. | 3 |
| [07.04 Multiagent Execution](07.04-MULTIAGENT-EXECUTION/README.md) | Admit ready assignments; acquire scoped write leases; execute governed work; observe cancellation; resolve conflicts through recorded decisions; release leases. | 3 |
| [07.05 Agent Observability](07.05-AGENT-OBSERVABILITY/README.md) | Collect authoritative lifecycle events; link agent claims to observed artifacts; evaluate outcomes; expose discrepancies and pending verification. | 3 |


## Read and build order

Read [architecture](ARCHITECTURE.md), [contracts](INTERFACE-CONTRACTS.md), [dependencies](DEPENDENCIES.md), and [build sequence](BUILD-SEQUENCE.md). Then load only the component and file specifications assigned to the current task. Use [the file index](FILE-INDEX.md) to find every planned source unit.

## Integration and qualification

Use [local integration instructions](INTEGRATION.md), [failure and recovery rules](FAILURE-AND-RECOVERY.md), [the test matrix](TEST-MATRIX.md), and [acceptance gate](ACCEPTANCE.md). [Agent assignments](AGENT-ASSIGNMENTS.md) defines construction responsibility and reviewer separation.

This subsystem contains 5 component folders and 15 planned implementation-file specifications. The package specifies their construction; it makes no claim about their presence in the uninspected local application. The initial reconciliation state for each logical path is LOCAL-INSPECTION-REQUIRED. Resolve that state through evidence before editing.
