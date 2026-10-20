# R15 required construction skills

Load only the skills relevant to the current task and their directly linked procedures. These instructions guide future engineering work; their presence does not establish that the work has been performed.

| Skill | Required input | Expected output |
| --- | --- | --- |
| [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md) | Canonical contract references, producer and consumer owners, local language conventions, and compatibility constraints. | A versioned interface decision with fields, invariants, errors, state semantics, and shared test fixtures. |
| [S07 Authority Boundary Implementation](../../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md) | Principal and capability contracts, trust policy, target resource model, and scoped effect requirements. | Use-time authorization checks with bounded delegation, replay protection, and revocation evidence. |
| [S10 Cryptographic Integrity Engineering](../../AGENT-SKILLS/S10-CRYPTOGRAPHIC-INTEGRITY-ENGINEERING/SKILL.md) | Approved trust model, established local cryptographic facilities, canonicalization rules, and key lifecycle policy. | Domain-bound digests and signatures with protected keys, rotation, and precise verification outcomes. |
| [S14 Tool Execution Boundary Engineering](../../AGENT-SKILLS/S14-TOOL-EXECUTION-BOUNDARY-ENGINEERING/SKILL.md) | Tool manifest, exact operation proposal, resource identities, isolation capabilities, and effect observation plan. | A governed adapter with exact-input binding, qualified restrictions, stop behavior, and receipts. |
| [S17 Failure Injection And Recovery](../../AGENT-SKILLS/S17-FAILURE-INJECTION-AND-RECOVERY/SKILL.md) | State and effect boundaries, controlled test environment, recovery rules, and fault-injection points. | Reproducible interruption evidence and validated safe resume, compensation, or uncertainty handling. |
| [S18 Adversarial Security Review](../../AGENT-SKILLS/S18-ADVERSARIAL-SECURITY-REVIEW/SKILL.md) | Explicitly authorized isolated targets, threat boundaries, source changes, and security acceptance cases. | Reproducible boundary findings with impact, exact evidence, and verified repairs. |
| [S19 Evidence Chain Validation](../../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md) | Operation records, artifacts, signatures, lineage, required evidence profile, and trust context. | A verification result separating integrity, attribution, completeness, observed behavior, and unresolved gaps. |
