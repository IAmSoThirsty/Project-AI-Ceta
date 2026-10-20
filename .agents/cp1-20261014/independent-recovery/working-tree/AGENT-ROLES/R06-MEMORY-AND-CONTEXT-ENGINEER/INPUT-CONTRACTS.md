# R06 input contract

## Required task input

Provide the task and requirement identities, exact owner-approved scope, mapped local source paths, source baseline digest, canonical contract revisions, dependency readiness, resource and execution permissions, acceptance IDs, and named reviewer. Include existing local tests and data-preservation obligations.

## Domain inputs

Implement attributed memory, retrieval, consolidation, correction, deletion, and bounded context assembly.

| Skill | Required input |
| --- | --- |
| [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md) | Canonical contract references, producer and consumer owners, local language conventions, and compatibility constraints. |
| [S08 State Transition Engineering](../../AGENT-SKILLS/S08-STATE-TRANSITION-ENGINEERING/SKILL.md) | Canonical state owner, transition contract, expected versions, and lifecycle requirements. |
| [S09 Durable Storage Engineering](../../AGENT-SKILLS/S09-DURABLE-STORAGE-ENGINEERING/SKILL.md) | Reconciled storage engine, data schemas, transaction boundaries, retention rules, and fault fixtures. |
| [S11 Memory And Retrieval Engineering](../../AGENT-SKILLS/S11-MEMORY-AND-RETRIEVAL-ENGINEERING/SKILL.md) | Memory and source contracts, access scope, provenance rules, and retrieval or deletion fixtures. |
| [S13 Model Inference Qualification](../../AGENT-SKILLS/S13-MODEL-INFERENCE-QUALIFICATION/SKILL.md) | Exact model artifact, runtime configuration, target hardware, task fixtures, and locality policy. |
| [S19 Evidence Chain Validation](../../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md) | Operation records, artifacts, signatures, lineage, required evidence profile, and trust context. |


## Admission checks

Confirm that source references exist, match their declared digests, and lie within the permitted local root. Resolve missing or contradictory prerequisites before effectful work. Treat prior summaries as navigation aids, not proof of current implementation. If source or authority changes after inspection, stop the affected edit and revalidate the assignment. Never infer permission from a role name or a task's urgency.
