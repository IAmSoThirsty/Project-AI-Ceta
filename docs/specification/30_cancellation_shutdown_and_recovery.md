# Cancellation, shutdown, and recovery

**Document ID:** SPEC-30  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-30-01

Stop is an out-of-band runtime operation, available during generation, tools, indexing, preview, or setup. Distinguish requested stop, admission disabled, termination in progress, workers stopped, and outcome reconciled. Prevent new admission at the defined linearization point and cancel/terminate owned work under its contract. Never kill unrelated processes sharing a name or port. UI confirmation requires observed state.

### REQ-30-02

Carry bounded timing through preparation, preview validity, admission, generation, tools, and observation, with recovery capacity reserved. Define whether human waiting expires preparation or pauses a non-security task budget; expired preparation must be regenerated. Blocking native I/O needs an enforceable containment/deadline strategy. Preserve partial outputs and drafts without describing them as complete.

### REQ-30-03

NOT_STARTED may become a new attempt under current authority. COMPLETED_AND_VERIFIED is retained without execution. MAY_HAVE_EXECUTED becomes INDETERMINATE and requires observation or escalation. Acknowledgment is not evidence of failure. Block resource-dependent work without unnecessarily freezing unrelated safe tasks.

### REQ-30-04

Startup checks identity and continuity before writes or migration. Corrupt data, missing keys, stale heads, incompatible schemas, or unresolved leases enter preserved recovery. Support read-only inspection/export with status visible. Do not auto-reset profiles, replace identity, erase tails, or declare interrupted work complete for a clean startup.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B015, B019, B077, B078, B098, B100, B101, B102, B115. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.
