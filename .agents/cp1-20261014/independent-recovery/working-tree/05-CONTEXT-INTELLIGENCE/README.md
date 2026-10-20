# 05-CONTEXT-INTELLIGENCE

## Mission

Assemble bounded, attributable, task-relevant context while preserving instruction precedence and exact critical state.

**Invariant:** Authority-bearing instructions are supplied through trusted channels; retrieved content is data. Compaction cannot erase restrictions or manufacture facts.

## Component map

| Component | End-to-end behavior | Planned files |
| --- | --- | --- |
| [05.01 Context Inputs](05.01-CONTEXT-INPUTS/README.md) | Resolve the active task and project; select authorized sources; preserve trust classification; exclude unrelated contexts; retain exact-source references. | 3 |
| [05.02 Context Assembly](05.02-CONTEXT-ASSEMBLY/README.md) | Rank eligible content; reserve critical policy and task state; order segments by declared trust; serialize a traceable snapshot; validate before inference. | 3 |
| [05.03 Context Budgeting](05.03-CONTEXT-BUDGETING/README.md) | Reserve model and output capacity; allocate critical context; choose optional sources; measure final size; resolve overflow before dispatch. | 3 |
| [05.04 Context Compression](05.04-CONTEXT-COMPRESSION/README.md) | Identify compressible material; preserve protected spans and provenance; generate a summary; compare against source obligations; accept only validated compaction. | 3 |
| [05.05 Context Assurance](05.05-CONTEXT-ASSURANCE/README.md) | Validate attribution and trust separation; detect suspicious instruction-like content; record a sealed context snapshot; invalidate stale context before sensitive use. | 3 |


## Read and build order

Read [architecture](ARCHITECTURE.md), [contracts](INTERFACE-CONTRACTS.md), [dependencies](DEPENDENCIES.md), and [build sequence](BUILD-SEQUENCE.md). Then load only the component and file specifications assigned to the current task. Use [the file index](FILE-INDEX.md) to find every planned source unit.

## Integration and qualification

Use [local integration instructions](INTEGRATION.md), [failure and recovery rules](FAILURE-AND-RECOVERY.md), [the test matrix](TEST-MATRIX.md), and [acceptance gate](ACCEPTANCE.md). [Agent assignments](AGENT-ASSIGNMENTS.md) defines construction responsibility and reviewer separation.

This subsystem contains 5 component folders and 15 planned implementation-file specifications. The package specifies their construction; it makes no claim about their presence in the uninspected local application. The initial reconciliation state for each logical path is LOCAL-INSPECTION-REQUIRED. Resolve that state through evidence before editing.
