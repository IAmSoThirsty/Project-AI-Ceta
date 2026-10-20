# Defensive Vault custody

**Document ID:** SPEC-25  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-25-01

Build object custody, not a launcher or broadly unlocked drive. Admission, sealing, object release, revocation, backup, recovery, migration, and retirement are explicit transitions. Normal release is SEALED -> VERIFYING -> AUTHORIZED_RELEASE -> ZEROIZING -> SEALED. No general unlock hands UI or model the collection.

### REQ-25-02

Bind requests to one object/version, permitted operation, consumer, authority, policy, time/epoch, and execution boundary. Validate metadata/provenance at admission. Keep secret content out of logs, embeddings, filenames, telemetry, and ordinary context. Prefer constrained results over unrestricted plaintext.

### REQ-25-03

Storage authority cannot become execution authority. Separate custody, audit, recovery, token-binding, and release keys as required. Verify actual possession-factor and cloning assumptions; a matching USB serial is insufficient. Recovery must not become an undocumented master-key export.

### REQ-25-04

Use reviewed native handling for secret lifetimes. Clearing a Python variable cannot prove all copies erased. Trace consumers, buffers, mappings, dumps, swap, caches, logs, and failures. Report achieved guarantees and remaining OS/hardware trust. Missing mandatory hardware/lifetime controls keep a strong protected profile unavailable rather than silently weaker.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B089, B093, B095, B096. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.
