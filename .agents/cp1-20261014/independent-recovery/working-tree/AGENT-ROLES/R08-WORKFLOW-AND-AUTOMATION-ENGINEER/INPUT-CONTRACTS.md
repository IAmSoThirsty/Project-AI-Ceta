# R08 input contract

## Required task input

Provide the task and requirement identities, exact owner-approved scope, mapped local source paths, source baseline digest, canonical contract revisions, dependency readiness, resource and execution permissions, acceptance IDs, and named reviewer. Include existing local tests and data-preservation obligations.

## Domain inputs

Implement durable task graphs, retries, checkpoints, schedules, event triggers, and recovery.

| Skill | Required input |
| --- | --- |
| [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md) | Canonical contract references, producer and consumer owners, local language conventions, and compatibility constraints. |
| [S07 Authority Boundary Implementation](../../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md) | Principal and capability contracts, trust policy, target resource model, and scoped effect requirements. |
| [S08 State Transition Engineering](../../AGENT-SKILLS/S08-STATE-TRANSITION-ENGINEERING/SKILL.md) | Canonical state owner, transition contract, expected versions, and lifecycle requirements. |
| [S09 Durable Storage Engineering](../../AGENT-SKILLS/S09-DURABLE-STORAGE-ENGINEERING/SKILL.md) | Reconciled storage engine, data schemas, transaction boundaries, retention rules, and fault fixtures. |
| [S12 Agent Workflow Engineering](../../AGENT-SKILLS/S12-AGENT-WORKFLOW-ENGINEERING/SKILL.md) | Task graph, agent roles, skill manifests, resource limits, authority scope, and handoff contracts. |
| [S17 Failure Injection And Recovery](../../AGENT-SKILLS/S17-FAILURE-INJECTION-AND-RECOVERY/SKILL.md) | State and effect boundaries, controlled test environment, recovery rules, and fault-injection points. |
| [S20 Performance And Resource Analysis](../../AGENT-SKILLS/S20-PERFORMANCE-AND-RESOURCE-ANALYSIS/SKILL.md) | Target hardware, representative workloads, explicit thresholds, resource telemetry, and baseline measurements. |


## Admission checks

Confirm that source references exist, match their declared digests, and lie within the permitted local root. Resolve missing or contradictory prerequisites before effectful work. Treat prior summaries as navigation aids, not proof of current implementation. If source or authority changes after inspection, stop the affected edit and revalidate the assignment. Never infer permission from a role name or a task's urgency.
