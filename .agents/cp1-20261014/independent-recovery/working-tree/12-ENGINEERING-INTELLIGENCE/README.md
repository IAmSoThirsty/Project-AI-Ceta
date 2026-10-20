# 12-ENGINEERING-INTELLIGENCE

## Mission

Turn approved engineering requirements into inspected source changes, reproducible tests, independent review, and evidence-backed delivery.

**Invariant:** Engineering work operates on inspected local source with scoped file ownership. Generated code, test execution, and verified product behavior are distinct completion stages.

## Component map

| Component | End-to-end behavior | Planned files |
| --- | --- | --- |
| [12.01 Project Discovery](12.01-PROJECT-DISCOVERY/README.md) | Inspect the selected project; identify languages and entry points; index source and dependencies; report unknown generated or binary content; bind findings to a source snapshot. | 3 |
| [12.02 Engineering Planning](12.02-ENGINEERING-PLANNING/README.md) | Trace each requirement to current behavior; define target changes and tests; sequence dependencies; assess effects and migration; request approval for changed scope. | 3 |
| [12.03 Code Construction](12.03-CODE-CONSTRUCTION/README.md) | Plan exact edits against inspected source; stage coordinated changes; validate ownership and preconditions; apply through governed file operations; inspect the resulting diff. | 3 |
| [12.04 Testing And Debugging](12.04-TESTING-AND-DEBUGGING/README.md) | Reproduce the reported behavior; establish a failing test; inspect logs and state; propose a bounded repair; rerun targeted and affected regression tests. | 3 |
| [12.05 Engineering Review](12.05-ENGINEERING-REVIEW/README.md) | Inspect exact changes; compare against contracts and requirements; reproduce critical tests independently; classify findings; approve or return changes with evidence. | 3 |
| [12.06 Engineering Delivery](12.06-ENGINEERING-DELIVERY/README.md) | Build from the pinned source; run verification; reconcile documentation and interfaces; report exact deliverables and unresolved obligations; hand off to product qualification. | 3 |


## Read and build order

Read [architecture](ARCHITECTURE.md), [contracts](INTERFACE-CONTRACTS.md), [dependencies](DEPENDENCIES.md), and [build sequence](BUILD-SEQUENCE.md). Then load only the component and file specifications assigned to the current task. Use [the file index](FILE-INDEX.md) to find every planned source unit.

## Integration and qualification

Use [local integration instructions](INTEGRATION.md), [failure and recovery rules](FAILURE-AND-RECOVERY.md), [the test matrix](TEST-MATRIX.md), and [acceptance gate](ACCEPTANCE.md). [Agent assignments](AGENT-ASSIGNMENTS.md) defines construction responsibility and reviewer separation.

This subsystem contains 6 component folders and 18 planned implementation-file specifications. The package specifies their construction; it makes no claim about their presence in the uninspected local application. The initial reconciliation state for each logical path is LOCAL-INSPECTION-REQUIRED. Resolve that state through evidence before editing.
