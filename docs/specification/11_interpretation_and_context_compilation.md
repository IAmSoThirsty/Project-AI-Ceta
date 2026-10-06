# Interpretation and context compilation

**Document ID:** SPEC-11  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-11-01

Build one request compiler for all production inference: chat, planning, review, probes, maintenance, and optional modalities. Preserve the request; derive an inspectable objective, context, constraints, exclusions, uncertainty, and necessary questions. Clarify only when ambiguity changes the task or authority. Prompt improvement must not automatically expand scope or convert an open question into a conclusion.

### REQ-11-02

Compile from canonical state, authorized retrieval, relevant history, explicit preferences, tasks, and observations. Keep the latest request identifiable and unaltered. Separate binding instructions, quotations, untrusted data, history, model proposals, and verified records. Prompt roles are not effect security boundaries.

### REQ-11-03

Bind prepared requests to model/runtime, tokenizer/template, policies, exact payload, relevant source revisions, context receipt, authority generation, reservation, and deadline. Preview the actual payload. Count the actual pinned rendering including special tokens. If mandatory input does not fit, retain the draft and expose the conflict rather than silently dropping requirements.

### REQ-11-04

Retrieve and summarize selectively rather than appending full history. Summaries retain sources, uncertainty, exclusions, rejected interpretations, and supersession; they cannot outrank originals. Disclose omitted history and clipped attachments and require review when omission changes the task. Test paraphrase drift, negation loss, fabricated quotations, stale corrections, and objective substitution.

### REQ-11-05

Context preparation shares cancellation and deadline policy with dispatch. Recheck authority and relevant state before action. Model, policy, or worker replacement invalidates prepared requests as specified. Restoring a failed draft must not duplicate user turns or reuse an expired request.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B025, B026, B027, B028, B029, B030, B031, B032. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.
