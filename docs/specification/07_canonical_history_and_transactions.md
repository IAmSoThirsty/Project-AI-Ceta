# Canonical history and transactions

**Document ID:** SPEC-07  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-07-01

Use one canonical event model with ordered streams per isolation scope. A protected local transactional store with logically isolated project/application streams is the desktop default unless a documented consistency design proves another choice better. A serialized writer owns authoritative mutations and atomic changes to events, grants, operation intents, queue admission, and corresponding projections. Cross-project work requires explicit scoped authority and provenance. A global catalog holds only authorized minimal references.

### REQ-07-02

Select SQLite settings and the loaded library after checking advisories and workload. Record journaling, synchronization, locking, timeouts, checkpointing, and power-loss behavior. Verify the library actually loaded by the frozen executable, not only the Python version. Keep the authority store on a supported local filesystem; reject silent promotion of network-share storage into a qualified persistence configuration.

### REQ-07-03

Make the journal append-only through the application API and tamper-evident under declared assumptions. Signatures do not prevent an administrator from replacing a complete local history and its local keys. Specify which profile uses local protection, independent witnessing, or hardware anti-rollback. Validate history, identities, trusted heads, projection versions, and checkpoint bindings before admitting effects. Unchanged timestamps or head hashes cannot alone prove an intact prefix.

### REQ-07-04

Projections must be derivable and disposable without altering canonical evidence. Surface unsupported events on rebuild. Never derive positive authority from an incomplete projection. Snapshot-plus-tail validation requires a binding to the exact accepted prefix and satisfied trust assumptions. Background disagreement invalidates affected projections and capabilities.

### REQ-07-05

Avoid self-referential commitments. Specify which prior head a request binds and exclude its future signature/hash from its own preimage. Distinguish unrelated telemetry advancement from authority-relevant revisions so benign events do not invalidate every permit. Record conflict/read-set rules for stale state. Keep write transactions out of model generation, human waiting, and external process calls.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B009, B010, B011, B012, B013, B014, B016. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.
