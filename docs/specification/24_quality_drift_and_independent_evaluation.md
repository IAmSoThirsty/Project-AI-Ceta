# Quality, drift, and independent evaluation

**Document ID:** SPEC-24  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-24-01

Evaluate the complete installed request path, not only a raw endpoint. Cover conversation, exact format, relevant recall, source grounding, uncertainty, disagreement, preserved contradictions, bounded planning, and correct tool proposals. Include changed premises and adversarial data. Liveness is separate from competence. Historical small-model failures remain regression evidence, not excuses to weaken tests.

### REQ-24-02

Separate development, selection validation, frozen held-out evaluation, and monitoring. Track source-family leakage and contamination. Revealed expected answers cease to be clean held-out evidence. Do not insert benchmark branches, silently relax failed criteria, or omit inconvenient runs. Record payload, settings/seed, configuration, source state, output, scoring, and evaluator identity.

### REQ-24-03

Use repeated trials for nondeterministic behavior and report sample counts, distributions, failure rates, and uncertainty. Freeze release criteria before candidate comparison. Deterministic security invariants must pass their full applicable matrix; semantic quality follows its separately defined rubric. LLM judges cannot provide the entire assurance chain.

### REQ-24-04

Provide response/request diffs alongside semantic and controlled comparisons. Account for weights, prompt, template, context, tools, sampling, and environment. Wording changes are observations; attributing them to RLHF, a hidden motive, or a specific update needs evidence. Preserve improvements and counterexamples. Do not remove justified uncertainty merely to sound direct.

### REQ-24-05

Feedback enters a governed change process. Praise, anger, or one preference click cannot automatically change facts, policy, weights, or identity. Training is a separately authorized/budgeted pipeline with immutable inputs, contamination controls, checkpoints, evaluation, and promotion. Old training success does not prove competence of the rebuilt runtime.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B081, B082, B083, B084, B085, B086, B087, B088. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.
