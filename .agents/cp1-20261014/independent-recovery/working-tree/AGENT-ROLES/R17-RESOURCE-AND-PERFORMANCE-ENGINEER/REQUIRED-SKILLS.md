# R17 required construction skills

Load only the skills relevant to the current task and their directly linked procedures. These instructions guide future engineering work; their presence does not establish that the work has been performed.

| Skill | Required input | Expected output |
| --- | --- | --- |
| [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md) | Canonical contract references, producer and consumer owners, local language conventions, and compatibility constraints. | A versioned interface decision with fields, invariants, errors, state semantics, and shared test fixtures. |
| [S08 State Transition Engineering](../../AGENT-SKILLS/S08-STATE-TRANSITION-ENGINEERING/SKILL.md) | Canonical state owner, transition contract, expected versions, and lifecycle requirements. | A validated state machine with atomic transitions, causal records, and terminal-state rules. |
| [S13 Model Inference Qualification](../../AGENT-SKILLS/S13-MODEL-INFERENCE-QUALIFICATION/SKILL.md) | Exact model artifact, runtime configuration, target hardware, task fixtures, and locality policy. | A measured capability and resource envelope with inference, streaming, cancellation, and cleanup evidence. |
| [S17 Failure Injection And Recovery](../../AGENT-SKILLS/S17-FAILURE-INJECTION-AND-RECOVERY/SKILL.md) | State and effect boundaries, controlled test environment, recovery rules, and fault-injection points. | Reproducible interruption evidence and validated safe resume, compensation, or uncertainty handling. |
| [S20 Performance And Resource Analysis](../../AGENT-SKILLS/S20-PERFORMANCE-AND-RESOURCE-ANALYSIS/SKILL.md) | Target hardware, representative workloads, explicit thresholds, resource telemetry, and baseline measurements. | Reproducible performance findings and qualified resource admission limits. |
