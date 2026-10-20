# 00-MASTER-ARCHITECTURE

## Mission

Own the approved topology, component identities, lifecycle coordination, and local-source reconciliation rules.

**Invariant:** One canonical owner exists for every authority decision, state record, interface, and observable effect. Planning names never establish that a component already exists.

## Component map

| Component | End-to-end behavior | Planned files |
| --- | --- | --- |
| [00.01 Product Identity](00.01-PRODUCT-IDENTITY/README.md) | Load the approved product baseline; resolve amendments; expose a versioned invariant set; make every change traceable to an owner decision. | 2 |
| [00.02 System Topology](00.02-SYSTEM-TOPOLOGY/README.md) | Register components; validate unique ownership; distinguish build, runtime, data, and optional dependency edges; expose navigation and impact analysis. | 3 |
| [00.03 Runtime Lifecycle](00.03-RUNTIME-LIFECYCLE/README.md) | Initialize minimum storage and trust prerequisites; activate policy and dispatch boundaries; advertise readiness; stop admission; drain or terminate work; close durable stores. | 3 |
| [00.04 Integration Baseline](00.04-INTEGRATION-BASELINE/README.md) | Inspect only the selected local root; capture a read-only baseline; map logical units to observed files; resolve collisions; approve reuse or extension before editing. | 3 |
| [00.05 Architecture Assurance](00.05-ARCHITECTURE-ASSURANCE/README.md) | Evaluate graph structure, invariant coverage, and contract ownership against the same baseline; produce findings before integration approval. | 3 |


## Read and build order

Read [architecture](ARCHITECTURE.md), [contracts](INTERFACE-CONTRACTS.md), [dependencies](DEPENDENCIES.md), and [build sequence](BUILD-SEQUENCE.md). Then load only the component and file specifications assigned to the current task. Use [the file index](FILE-INDEX.md) to find every planned source unit.

## Integration and qualification

Use [local integration instructions](INTEGRATION.md), [failure and recovery rules](FAILURE-AND-RECOVERY.md), [the test matrix](TEST-MATRIX.md), and [acceptance gate](ACCEPTANCE.md). [Agent assignments](AGENT-ASSIGNMENTS.md) defines construction responsibility and reviewer separation.

This subsystem contains 5 component folders and 14 planned implementation-file specifications. The package specifies their construction; it makes no claim about their presence in the uninspected local application. The initial reconciliation state for each logical path is LOCAL-INSPECTION-REQUIRED. Resolve that state through evidence before editing.
