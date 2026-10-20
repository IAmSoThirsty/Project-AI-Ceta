# R01 required construction skills

Load only the skills relevant to the current task and their directly linked procedures. These instructions guide future engineering work; their presence does not establish that the work has been performed.

| Skill | Required input | Expected output |
| --- | --- | --- |
| [S01 Local Baseline Inspection](../../AGENT-SKILLS/S01-LOCAL-BASELINE-INSPECTION/SKILL.md) | An owner-selected local CETA root, permitted read scope, and the logical-unit registry. | A source-hashed inventory, entry-point map, current test catalog, and observed integration decisions. |
| [S02 Requirements Decomposition](../../AGENT-SKILLS/S02-REQUIREMENTS-DECOMPOSITION/SKILL.md) | Approved product goals, exact user requirements, constraints, and existing acceptance obligations. | A requirement-to-unit map with measurable outputs, dependency edges, and acceptance oracles. |
| [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md) | Canonical contract references, producer and consumer owners, local language conventions, and compatibility constraints. | A versioned interface decision with fields, invariants, errors, state semantics, and shared test fixtures. |
| [S05 Architectural Dependency Analysis](../../AGENT-SKILLS/S05-ARCHITECTURAL-DEPENDENCY-ANALYSIS/SKILL.md) | Subsystem graph, local module graph, shared contracts, and a proposed change set. | Typed build, runtime, data, and optional dependency maps with affected-owner and test impact. |
| [S21 Cross Subsystem Integration](../../AGENT-SKILLS/S21-CROSS-SUBSYSTEM-INTEGRATION/SKILL.md) | Approved contract revisions, mapped local units, dependency graph, source baseline, and migration plan. | Incrementally integrated native paths with compatibility, recovery, and owner-workflow evidence. |
| [S22 Documentation And Traceability](../../AGENT-SKILLS/S22-DOCUMENTATION-AND-TRACEABILITY/SKILL.md) | Accepted implementation behavior, requirements, test results, source and artifact identities, and existing documentation. | Current file, contract, operation, migration, and release guidance with validated links. |
| [S25 No Proof No Claim Verification](../../AGENT-SKILLS/S25-NO-PROOF-NO-CLAIM-VERIFICATION/SKILL.md) | A proposed completion statement, artifact references, execution records, tests, and known evidence gaps. | A claim ledger classifying each statement as supported, contradicted, incomplete, or not-executed. |
