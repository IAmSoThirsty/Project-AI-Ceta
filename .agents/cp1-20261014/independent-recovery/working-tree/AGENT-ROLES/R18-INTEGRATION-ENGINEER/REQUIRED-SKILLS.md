# R18 required construction skills

Load only the skills relevant to the current task and their directly linked procedures. These instructions guide future engineering work; their presence does not establish that the work has been performed.

| Skill | Required input | Expected output |
| --- | --- | --- |
| [S01 Local Baseline Inspection](../../AGENT-SKILLS/S01-LOCAL-BASELINE-INSPECTION/SKILL.md) | An owner-selected local CETA root, permitted read scope, and the logical-unit registry. | A source-hashed inventory, entry-point map, current test catalog, and observed integration decisions. |
| [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md) | Canonical contract references, producer and consumer owners, local language conventions, and compatibility constraints. | A versioned interface decision with fields, invariants, errors, state semantics, and shared test fixtures. |
| [S05 Architectural Dependency Analysis](../../AGENT-SKILLS/S05-ARCHITECTURAL-DEPENDENCY-ANALYSIS/SKILL.md) | Subsystem graph, local module graph, shared contracts, and a proposed change set. | Typed build, runtime, data, and optional dependency maps with affected-owner and test impact. |
| [S07 Authority Boundary Implementation](../../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md) | Principal and capability contracts, trust policy, target resource model, and scoped effect requirements. | Use-time authorization checks with bounded delegation, replay protection, and revocation evidence. |
| [S14 Tool Execution Boundary Engineering](../../AGENT-SKILLS/S14-TOOL-EXECUTION-BOUNDARY-ENGINEERING/SKILL.md) | Tool manifest, exact operation proposal, resource identities, isolation capabilities, and effect observation plan. | A governed adapter with exact-input binding, qualified restrictions, stop behavior, and receipts. |
| [S16 Test Generation And Execution](../../AGENT-SKILLS/S16-TEST-GENERATION-AND-EXECUTION/SKILL.md) | Requirements, unit specifications, canonical contracts, inspected test tooling, and controlled fixtures. | Executed source-bound tests with independent oracles and explicit pass, fail, blocked, skipped, or not-executed states. |
| [S18 Adversarial Security Review](../../AGENT-SKILLS/S18-ADVERSARIAL-SECURITY-REVIEW/SKILL.md) | Explicitly authorized isolated targets, threat boundaries, source changes, and security acceptance cases. | Reproducible boundary findings with impact, exact evidence, and verified repairs. |
| [S21 Cross Subsystem Integration](../../AGENT-SKILLS/S21-CROSS-SUBSYSTEM-INTEGRATION/SKILL.md) | Approved contract revisions, mapped local units, dependency graph, source baseline, and migration plan. | Incrementally integrated native paths with compatibility, recovery, and owner-workflow evidence. |
