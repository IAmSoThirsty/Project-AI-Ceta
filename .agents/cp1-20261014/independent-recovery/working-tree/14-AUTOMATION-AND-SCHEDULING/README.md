# 14-AUTOMATION-AND-SCHEDULING

## Mission

Create durable time- and event-triggered tasks with explicit authority renewal, concurrency, missed-trigger handling, and observable outcomes.

**Invariant:** A schedule grants no more authority than its approved scope and lifetime. Missed triggers are reconciled according to an explicit policy, not blindly replayed.

## Component map

| Component | End-to-end behavior | Planned files |
| --- | --- | --- |
| [14.01 Schedule Definitions](14.01-SCHEDULE-DEFINITIONS/README.md) | Define trigger and task binding; validate time and effect semantics; approve authority scope; register a durable schedule revision; expose next planned occurrences. | 3 |
| [14.02 Time Triggers](14.02-TIME-TRIGGERS/README.md) | Compute occurrences using declared calendar semantics; handle clock changes; acquire a durable occurrence claim; dispatch once per occurrence identity. | 3 |
| [14.03 Event Triggers](14.03-EVENT-TRIGGERS/README.md) | Observe scoped events; authenticate source; normalize and deduplicate; evaluate conditions; create a stable occurrence linked to the source event. | 3 |
| [14.04 Automation Dispatch](14.04-AUTOMATION-DISPATCH/README.md) | Claim an occurrence; validate schedule revision and current authority; acquire concurrency and resources; submit a durable task; record admission or blocking reason. | 3 |
| [14.05 Automation Continuity](14.05-AUTOMATION-CONTINUITY/README.md) | Reconcile downtime and event gaps; apply approved catch-up rules; renew authority where needed; recover task links; record actual outcomes and remaining uncertainty. | 3 |


## Read and build order

Read [architecture](ARCHITECTURE.md), [contracts](INTERFACE-CONTRACTS.md), [dependencies](DEPENDENCIES.md), and [build sequence](BUILD-SEQUENCE.md). Then load only the component and file specifications assigned to the current task. Use [the file index](FILE-INDEX.md) to find every planned source unit.

## Integration and qualification

Use [local integration instructions](INTEGRATION.md), [failure and recovery rules](FAILURE-AND-RECOVERY.md), [the test matrix](TEST-MATRIX.md), and [acceptance gate](ACCEPTANCE.md). [Agent assignments](AGENT-ASSIGNMENTS.md) defines construction responsibility and reviewer separation.

This subsystem contains 5 component folders and 15 planned implementation-file specifications. The package specifies their construction; it makes no claim about their presence in the uninspected local application. The initial reconciliation state for each logical path is LOCAL-INSPECTION-REQUIRED. Resolve that state through evidence before editing.
