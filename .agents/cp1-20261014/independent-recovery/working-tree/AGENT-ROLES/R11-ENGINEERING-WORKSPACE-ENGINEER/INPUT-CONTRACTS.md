# R11 input contract

## Required task input

Provide the task and requirement identities, exact owner-approved scope, mapped local source paths, source baseline digest, canonical contract revisions, dependency readiness, resource and execution permissions, acceptance IDs, and named reviewer. Include existing local tests and data-preservation obligations.

## Domain inputs

Implement local source inspection, change planning, editing, diffs, testing, terminal, and revision workspaces.

| Skill | Required input |
| --- | --- |
| [S01 Local Baseline Inspection](../../AGENT-SKILLS/S01-LOCAL-BASELINE-INSPECTION/SKILL.md) | An owner-selected local CETA root, permitted read scope, and the logical-unit registry. |
| [S02 Requirements Decomposition](../../AGENT-SKILLS/S02-REQUIREMENTS-DECOMPOSITION/SKILL.md) | Approved product goals, exact user requirements, constraints, and existing acceptance obligations. |
| [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md) | Canonical contract references, producer and consumer owners, local language conventions, and compatibility constraints. |
| [S04 File Specification Implementation](../../AGENT-SKILLS/S04-FILE-SPECIFICATION-IMPLEMENTATION/SKILL.md) | One approved file-level specification, mapped local path, dependencies, write lease, and acceptance IDs. |
| [S05 Architectural Dependency Analysis](../../AGENT-SKILLS/S05-ARCHITECTURAL-DEPENDENCY-ANALYSIS/SKILL.md) | Subsystem graph, local module graph, shared contracts, and a proposed change set. |
| [S14 Tool Execution Boundary Engineering](../../AGENT-SKILLS/S14-TOOL-EXECUTION-BOUNDARY-ENGINEERING/SKILL.md) | Tool manifest, exact operation proposal, resource identities, isolation capabilities, and effect observation plan. |
| [S15 Desktop Interface Implementation](../../AGENT-SKILLS/S15-DESKTOP-INTERFACE-IMPLEMENTATION/SKILL.md) | Approved user workflows, native command contracts, accessibility requirements, and authoritative state events. |
| [S16 Test Generation And Execution](../../AGENT-SKILLS/S16-TEST-GENERATION-AND-EXECUTION/SKILL.md) | Requirements, unit specifications, canonical contracts, inspected test tooling, and controlled fixtures. |
| [S21 Cross Subsystem Integration](../../AGENT-SKILLS/S21-CROSS-SUBSYSTEM-INTEGRATION/SKILL.md) | Approved contract revisions, mapped local units, dependency graph, source baseline, and migration plan. |
| [S24 Independent Reproduction](../../AGENT-SKILLS/S24-INDEPENDENT-REPRODUCTION/SKILL.md) | Producer deliverables, exact source and environment references, acceptance criteria, and raw evidence. |


## Admission checks

Confirm that source references exist, match their declared digests, and lie within the permitted local root. Resolve missing or contradictory prerequisites before effectful work. Treat prior summaries as navigation aids, not proof of current implementation. If source or authority changes after inspection, stop the affected edit and revalidate the assignment. Never infer permission from a role name or a task's urgency.
