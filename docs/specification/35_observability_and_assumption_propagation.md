# Observability and assumption propagation

**Document ID:** SPEC-35  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-35-01

Emit structured events with run, task, operation, configuration, scope, causation, and status. Keep sensitive payloads out of routine logs. Provide bounded local metrics and explicit diagnostic export. Success log lines are not verification evidence; application heartbeats are not model-quality results.

### REQ-35-02

Track assumptions with identity/version, supporting evidence, validity, scope, triggers, dependent proofs, and failure action. Include OS isolation, binaries, keys, time, authority availability, durability, tokenizer compatibility, observations, and verifier independence. Failed assumptions invalidate dependent conclusions, preparation, qualifications, and permits. Test the whole propagation.

### REQ-35-03

Govern telemetry itself. A diagnostic label does not authorize universal project reads or egress. Separate current qualifications, historical observations, and hypotheses. Derive self-description from runtime state so the Companion cannot claim to be watching, protected, qualified, or finished when the mechanism is unavailable.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B011, B013, B075, B117, B126. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.
