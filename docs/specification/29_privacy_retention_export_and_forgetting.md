# Privacy, retention, export, and forgetting

**Document ID:** SPEC-29  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-29-01

Classify conversations, identity, preferences, files, plans, embeddings, outputs, logs, and traces separately. Collect only necessary authorized data. A workspace grant does not allow whole-drive indexing, mailbox ingestion, browser credentials, hidden telemetry, or private-context transfer. Network egress remains separately scoped.

### REQ-29-02

Reconcile audit and deletion through minimal event metadata and protected payload storage. Keep sensitive payloads outside permanent plaintext logs where appropriate. Deletion removes eligible payloads and derived indexes while retaining only authorized tombstones/commitments. Document retained backups and uncontrollable external copies. Do not promise forgetting while searchable copies remain.

### REQ-29-03

Exports are explicit, scoped, integrity-bound, and non-overwriting. Model exports exclude history and authority. Import cannot reactivate grants, readiness, keys, or administrative status. Permission checks apply to source and derived records after revocation/deletion. Test project/user/session isolation, caches, failures, and restores.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B037, B038, B065, B066, B117, B118. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.
