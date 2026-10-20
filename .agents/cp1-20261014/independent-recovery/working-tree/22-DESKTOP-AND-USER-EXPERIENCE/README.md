# 22-DESKTOP-AND-USER-EXPERIENCE

## Mission

Provide an accessible native application shell, command center, owner controls, decision surfaces, evidence inspection, onboarding, and maintenance.

**Invariant:** Visual state is derived from authenticated native state. A disabled button is not a security boundary; every command is validated again by the runtime.

## Component map

| Component | End-to-end behavior | Planned files |
| --- | --- | --- |
| [22.01 Application Shell](22.01-APPLICATION-SHELL/README.md) | Launch a restricted shell; establish authenticated native communication; restore safe layout; activate routes from runtime readiness; preserve owner control during partial failures. | 3 |
| [22.02 Command Center](22.02-COMMAND-CENTER/README.md) | Query authoritative runtime summaries; show active work, health, and decisions; mark stale data; provide controlled navigation and stop actions. | 3 |
| [22.03 Agent Control](22.03-AGENT-CONTROL/README.md) | Inspect agent identity and assignments; display current grants and actions; request bounded controls; confirm native outcomes; expose reviewer and handoff history. | 3 |
| [22.04 Governance Interface](22.04-GOVERNANCE-INTERFACE/README.md) | Present exact proposals and rule traces; authenticate decisions; show delegation and revocation impact; preserve a source-linked decision history. | 3 |
| [22.05 Intelligence Interface](22.05-INTELLIGENCE-INTERFACE/README.md) | Present conversation and source attribution; inspect authorized memory; inspect exact context selection; propose corrections or deletions through governed controls. | 3 |
| [22.06 Evidence Interface](22.06-EVIDENCE-INTERFACE/README.md) | Query authorized evidence; display causal timelines and lineage; inspect raw and normalized observations; distinguish integrity, functional, and completeness verification. | 3 |
| [22.07 User Controls](22.07-USER-CONTROLS/README.md) | Load owner-scoped settings; validate proposed changes; apply through native commands; preserve accessibility and privacy; recover from invalid configuration. | 3 |
| [22.08 Owner Onboarding](22.08-OWNER-ONBOARDING/README.md) | Choose local data boundaries; establish owner identity; configure recovery; inspect hardware; qualify core local workflows; enable normal operation only after required checks. | 3 |
| [22.09 Native Maintenance](22.09-NATIVE-MAINTENANCE/README.md) | Inspect current health and data; prepare backup, restore, repair, or update proposals; show consequences; execute governed maintenance; verify outcomes and recovery points. | 3 |


## Read and build order

Read [architecture](ARCHITECTURE.md), [contracts](INTERFACE-CONTRACTS.md), [dependencies](DEPENDENCIES.md), and [build sequence](BUILD-SEQUENCE.md). Then load only the component and file specifications assigned to the current task. Use [the file index](FILE-INDEX.md) to find every planned source unit.

## Integration and qualification

Use [local integration instructions](INTEGRATION.md), [failure and recovery rules](FAILURE-AND-RECOVERY.md), [the test matrix](TEST-MATRIX.md), and [acceptance gate](ACCEPTANCE.md). [Agent assignments](AGENT-ASSIGNMENTS.md) defines construction responsibility and reviewer separation.

This subsystem contains 9 component folders and 27 planned implementation-file specifications. The package specifies their construction; it makes no claim about their presence in the uninspected local application. The initial reconciliation state for each logical path is LOCAL-INSPECTION-REQUIRED. Resolve that state through evidence before editing.
