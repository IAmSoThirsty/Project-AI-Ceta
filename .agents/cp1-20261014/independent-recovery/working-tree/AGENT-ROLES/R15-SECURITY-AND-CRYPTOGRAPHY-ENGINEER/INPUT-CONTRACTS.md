# R15 input contract

## Required task input

Provide the task and requirement identities, exact owner-approved scope, mapped local source paths, source baseline digest, canonical contract revisions, dependency readiness, resource and execution permissions, acceptance IDs, and named reviewer. Include existing local tests and data-preservation obligations.

## Domain inputs

Implement protected keys, secrets, trust boundaries, incident containment, and security assurance.

| Skill | Required input |
| --- | --- |
| [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md) | Canonical contract references, producer and consumer owners, local language conventions, and compatibility constraints. |
| [S07 Authority Boundary Implementation](../../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md) | Principal and capability contracts, trust policy, target resource model, and scoped effect requirements. |
| [S10 Cryptographic Integrity Engineering](../../AGENT-SKILLS/S10-CRYPTOGRAPHIC-INTEGRITY-ENGINEERING/SKILL.md) | Approved trust model, established local cryptographic facilities, canonicalization rules, and key lifecycle policy. |
| [S14 Tool Execution Boundary Engineering](../../AGENT-SKILLS/S14-TOOL-EXECUTION-BOUNDARY-ENGINEERING/SKILL.md) | Tool manifest, exact operation proposal, resource identities, isolation capabilities, and effect observation plan. |
| [S17 Failure Injection And Recovery](../../AGENT-SKILLS/S17-FAILURE-INJECTION-AND-RECOVERY/SKILL.md) | State and effect boundaries, controlled test environment, recovery rules, and fault-injection points. |
| [S18 Adversarial Security Review](../../AGENT-SKILLS/S18-ADVERSARIAL-SECURITY-REVIEW/SKILL.md) | Explicitly authorized isolated targets, threat boundaries, source changes, and security acceptance cases. |
| [S19 Evidence Chain Validation](../../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md) | Operation records, artifacts, signatures, lineage, required evidence profile, and trust context. |


## Admission checks

Confirm that source references exist, match their declared digests, and lie within the permitted local root. Resolve missing or contradictory prerequisites before effectful work. Treat prior summaries as navigation aids, not proof of current implementation. If source or authority changes after inspection, stop the affected edit and revalidate the assignment. Never infer permission from a role name or a task's urgency.
