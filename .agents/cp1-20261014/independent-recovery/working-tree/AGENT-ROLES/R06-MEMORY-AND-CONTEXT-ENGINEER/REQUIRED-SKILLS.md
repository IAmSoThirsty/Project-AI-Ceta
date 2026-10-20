# R06 required construction skills

Load only the skills relevant to the current task and their directly linked procedures. These instructions guide future engineering work; their presence does not establish that the work has been performed.

| Skill | Required input | Expected output |
| --- | --- | --- |
| [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md) | Canonical contract references, producer and consumer owners, local language conventions, and compatibility constraints. | A versioned interface decision with fields, invariants, errors, state semantics, and shared test fixtures. |
| [S08 State Transition Engineering](../../AGENT-SKILLS/S08-STATE-TRANSITION-ENGINEERING/SKILL.md) | Canonical state owner, transition contract, expected versions, and lifecycle requirements. | A validated state machine with atomic transitions, causal records, and terminal-state rules. |
| [S09 Durable Storage Engineering](../../AGENT-SKILLS/S09-DURABLE-STORAGE-ENGINEERING/SKILL.md) | Reconciled storage engine, data schemas, transaction boundaries, retention rules, and fault fixtures. | Durable local records, atomic publication intent, integrity checks, and tested restoration. |
| [S11 Memory And Retrieval Engineering](../../AGENT-SKILLS/S11-MEMORY-AND-RETRIEVAL-ENGINEERING/SKILL.md) | Memory and source contracts, access scope, provenance rules, and retrieval or deletion fixtures. | Attributed canonical memory, rebuildable indexes, conflict-aware retrieval, and validated context inputs. |
| [S13 Model Inference Qualification](../../AGENT-SKILLS/S13-MODEL-INFERENCE-QUALIFICATION/SKILL.md) | Exact model artifact, runtime configuration, target hardware, task fixtures, and locality policy. | A measured capability and resource envelope with inference, streaming, cancellation, and cleanup evidence. |
| [S19 Evidence Chain Validation](../../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md) | Operation records, artifacts, signatures, lineage, required evidence profile, and trust context. | A verification result separating integrity, attribution, completeness, observed behavior, and unresolved gaps. |
