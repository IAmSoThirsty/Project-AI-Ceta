# R02 required construction skills

Load only the skills relevant to the current task and their directly linked procedures. These instructions guide future engineering work; their presence does not establish that the work has been performed.

| Skill | Required input | Expected output |
| --- | --- | --- |
| [S01 Local Baseline Inspection](../../AGENT-SKILLS/S01-LOCAL-BASELINE-INSPECTION/SKILL.md) | An owner-selected local CETA root, permitted read scope, and the logical-unit registry. | A source-hashed inventory, entry-point map, current test catalog, and observed integration decisions. |
| [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md) | Canonical contract references, producer and consumer owners, local language conventions, and compatibility constraints. | A versioned interface decision with fields, invariants, errors, state semantics, and shared test fixtures. |
| [S05 Architectural Dependency Analysis](../../AGENT-SKILLS/S05-ARCHITECTURAL-DEPENDENCY-ANALYSIS/SKILL.md) | Subsystem graph, local module graph, shared contracts, and a proposed change set. | Typed build, runtime, data, and optional dependency maps with affected-owner and test impact. |
| [S09 Durable Storage Engineering](../../AGENT-SKILLS/S09-DURABLE-STORAGE-ENGINEERING/SKILL.md) | Reconciled storage engine, data schemas, transaction boundaries, retention rules, and fault fixtures. | Durable local records, atomic publication intent, integrity checks, and tested restoration. |
| [S21 Cross Subsystem Integration](../../AGENT-SKILLS/S21-CROSS-SUBSYSTEM-INTEGRATION/SKILL.md) | Approved contract revisions, mapped local units, dependency graph, source baseline, and migration plan. | Incrementally integrated native paths with compatibility, recovery, and owner-workflow evidence. |
| [S24 Independent Reproduction](../../AGENT-SKILLS/S24-INDEPENDENT-REPRODUCTION/SKILL.md) | Producer deliverables, exact source and environment references, acceptance criteria, and raw evidence. | A separately produced verification report with reproduced results and explicit discrepancies. |
