# 23-TESTING-AND-QUALIFICATION - construction agent assignments

| Responsibility | Assigned role |
| --- | --- |
| Primary implementation | [R19 Test And Qualification Engineer](../AGENT-ROLES/R19-TEST-AND-QUALIFICATION-ENGINEER/README.md) |
| Local baseline reconciliation | [R02 Existing System Reconciler](../AGENT-ROLES/R02-EXISTING-SYSTEM-RECONCILER/README.md) |
| Cross-subsystem integration | [R18 Integration Engineer](../AGENT-ROLES/R18-INTEGRATION-ENGINEER/README.md) |
| Test execution and gate coordination | [R19 Test And Qualification Engineer](../AGENT-ROLES/R19-TEST-AND-QUALIFICATION-ENGINEER/README.md) |
| Independent adversarial verification | [R20 Independent Adversarial Verifier](../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md) |
| Final release assembly | [R21 Build And Release Engineer](../AGENT-ROLES/R21-BUILD-AND-RELEASE-ENGINEER/README.md) |


## Required construction skills

| Skill | Expected output |
| --- | --- |
| [S03 Contract First Design](../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md) | A versioned interface decision with fields, invariants, errors, state semantics, and shared test fixtures. |
| [S16 Test Generation And Execution](../AGENT-SKILLS/S16-TEST-GENERATION-AND-EXECUTION/SKILL.md) | Executed source-bound tests with independent oracles and explicit pass, fail, blocked, skipped, or not-executed states. |
| [S17 Failure Injection And Recovery](../AGENT-SKILLS/S17-FAILURE-INJECTION-AND-RECOVERY/SKILL.md) | Reproducible interruption evidence and validated safe resume, compensation, or uncertainty handling. |
| [S18 Adversarial Security Review](../AGENT-SKILLS/S18-ADVERSARIAL-SECURITY-REVIEW/SKILL.md) | Reproducible boundary findings with impact, exact evidence, and verified repairs. |
| [S19 Evidence Chain Validation](../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md) | A verification result separating integrity, attribution, completeness, observed behavior, and unresolved gaps. |
| [S20 Performance And Resource Analysis](../AGENT-SKILLS/S20-PERFORMANCE-AND-RESOURCE-ANALYSIS/SKILL.md) | Reproducible performance findings and qualified resource admission limits. |
| [S24 Independent Reproduction](../AGENT-SKILLS/S24-INDEPENDENT-REPRODUCTION/SKILL.md) | A separately produced verification report with reproduced results and explicit discrepancies. |
| [S25 No Proof No Claim Verification](../AGENT-SKILLS/S25-NO-PROOF-NO-CLAIM-VERIFICATION/SKILL.md) | A claim ledger classifying each statement as supported, contradicted, incomplete, or not-executed. |


## File ownership and handoff

Assign each linked file specification a single active writer and a distinct review assignment. Shared contracts remain under their schema owner. Acquire a bounded write lease and preserve the inspected source baseline. Parallel agents may not silently share mutable files. The handoff includes requirement and unit IDs, mapped paths, before and after digests, contract revisions, actual tests and outputs, unresolved effects, and rollback or recovery guidance.

Use [the handoff contract](../AGENT-ROLES/CROSS-AGENT-HANDOFF-CONTRACT.md) and [the human authority boundary](../AGENT-ROLES/HUMAN-AUTHORITY-BOUNDARY.md). The independent verifier inspects exact artifacts and reproduces critical checks; it does not approve its own implementation as independent work.
