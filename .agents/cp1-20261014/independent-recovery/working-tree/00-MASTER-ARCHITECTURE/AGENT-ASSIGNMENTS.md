# 00-MASTER-ARCHITECTURE - construction agent assignments

| Responsibility | Assigned role |
| --- | --- |
| Primary implementation | [R01 Architecture Coordinator](../AGENT-ROLES/R01-ARCHITECTURE-COORDINATOR/README.md) |
| Local baseline reconciliation | [R02 Existing System Reconciler](../AGENT-ROLES/R02-EXISTING-SYSTEM-RECONCILER/README.md) |
| Cross-subsystem integration | [R18 Integration Engineer](../AGENT-ROLES/R18-INTEGRATION-ENGINEER/README.md) |
| Test execution and gate coordination | [R19 Test And Qualification Engineer](../AGENT-ROLES/R19-TEST-AND-QUALIFICATION-ENGINEER/README.md) |
| Independent adversarial verification | [R20 Independent Adversarial Verifier](../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md) |
| Final release assembly | [R21 Build And Release Engineer](../AGENT-ROLES/R21-BUILD-AND-RELEASE-ENGINEER/README.md) |


## Required construction skills

| Skill | Expected output |
| --- | --- |
| [S01 Local Baseline Inspection](../AGENT-SKILLS/S01-LOCAL-BASELINE-INSPECTION/SKILL.md) | A source-hashed inventory, entry-point map, current test catalog, and observed integration decisions. |
| [S02 Requirements Decomposition](../AGENT-SKILLS/S02-REQUIREMENTS-DECOMPOSITION/SKILL.md) | A requirement-to-unit map with measurable outputs, dependency edges, and acceptance oracles. |
| [S03 Contract First Design](../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md) | A versioned interface decision with fields, invariants, errors, state semantics, and shared test fixtures. |
| [S05 Architectural Dependency Analysis](../AGENT-SKILLS/S05-ARCHITECTURAL-DEPENDENCY-ANALYSIS/SKILL.md) | Typed build, runtime, data, and optional dependency maps with affected-owner and test impact. |
| [S21 Cross Subsystem Integration](../AGENT-SKILLS/S21-CROSS-SUBSYSTEM-INTEGRATION/SKILL.md) | Incrementally integrated native paths with compatibility, recovery, and owner-workflow evidence. |
| [S22 Documentation And Traceability](../AGENT-SKILLS/S22-DOCUMENTATION-AND-TRACEABILITY/SKILL.md) | Current file, contract, operation, migration, and release guidance with validated links. |
| [S25 No Proof No Claim Verification](../AGENT-SKILLS/S25-NO-PROOF-NO-CLAIM-VERIFICATION/SKILL.md) | A claim ledger classifying each statement as supported, contradicted, incomplete, or not-executed. |


## File ownership and handoff

Assign each linked file specification a single active writer and a distinct review assignment. Shared contracts remain under their schema owner. Acquire a bounded write lease and preserve the inspected source baseline. Parallel agents may not silently share mutable files. The handoff includes requirement and unit IDs, mapped paths, before and after digests, contract revisions, actual tests and outputs, unresolved effects, and rollback or recovery guidance.

Use [the handoff contract](../AGENT-ROLES/CROSS-AGENT-HANDOFF-CONTRACT.md) and [the human authority boundary](../AGENT-ROLES/HUMAN-AUTHORITY-BOUNDARY.md). The independent verifier inspects exact artifacts and reproduces critical checks; it does not approve its own implementation as independent work.
