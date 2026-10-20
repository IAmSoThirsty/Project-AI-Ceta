# 01-CONSTITUTIONAL-GOVERNANCE - construction agent assignments

| Responsibility | Assigned role |
| --- | --- |
| Primary implementation | [R03 Constitutional Governance Engineer](../AGENT-ROLES/R03-CONSTITUTIONAL-GOVERNANCE-ENGINEER/README.md) |
| Local baseline reconciliation | [R02 Existing System Reconciler](../AGENT-ROLES/R02-EXISTING-SYSTEM-RECONCILER/README.md) |
| Cross-subsystem integration | [R18 Integration Engineer](../AGENT-ROLES/R18-INTEGRATION-ENGINEER/README.md) |
| Test execution and gate coordination | [R19 Test And Qualification Engineer](../AGENT-ROLES/R19-TEST-AND-QUALIFICATION-ENGINEER/README.md) |
| Independent adversarial verification | [R20 Independent Adversarial Verifier](../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md) |
| Final release assembly | [R21 Build And Release Engineer](../AGENT-ROLES/R21-BUILD-AND-RELEASE-ENGINEER/README.md) |


## Required construction skills

| Skill | Expected output |
| --- | --- |
| [S03 Contract First Design](../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md) | A versioned interface decision with fields, invariants, errors, state semantics, and shared test fixtures. |
| [S06 Constitutional Policy Implementation](../AGENT-SKILLS/S06-CONSTITUTIONAL-POLICY-IMPLEMENTATION/SKILL.md) | Version-bound policy evaluation with exact source traceability and controlled activation. |
| [S07 Authority Boundary Implementation](../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md) | Use-time authorization checks with bounded delegation, replay protection, and revocation evidence. |
| [S08 State Transition Engineering](../AGENT-SKILLS/S08-STATE-TRANSITION-ENGINEERING/SKILL.md) | A validated state machine with atomic transitions, causal records, and terminal-state rules. |
| [S19 Evidence Chain Validation](../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md) | A verification result separating integrity, attribution, completeness, observed behavior, and unresolved gaps. |
| [S25 No Proof No Claim Verification](../AGENT-SKILLS/S25-NO-PROOF-NO-CLAIM-VERIFICATION/SKILL.md) | A claim ledger classifying each statement as supported, contradicted, incomplete, or not-executed. |


## File ownership and handoff

Assign each linked file specification a single active writer and a distinct review assignment. Shared contracts remain under their schema owner. Acquire a bounded write lease and preserve the inspected source baseline. Parallel agents may not silently share mutable files. The handoff includes requirement and unit IDs, mapped paths, before and after digests, contract revisions, actual tests and outputs, unresolved effects, and rollback or recovery guidance.

Use [the handoff contract](../AGENT-ROLES/CROSS-AGENT-HANDOFF-CONTRACT.md) and [the human authority boundary](../AGENT-ROLES/HUMAN-AUTHORITY-BOUNDARY.md). The independent verifier inspects exact artifacts and reproduces critical checks; it does not approve its own implementation as independent work.
