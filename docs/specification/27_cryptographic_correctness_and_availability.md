# Cryptographic correctness and availability

**Document ID:** SPEC-27  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-27-01

Specify how stored ciphertext remains decryptable across fresh requests. Do not derive a new content key from every expiring authorization transcript and expect it to decrypt unchanged ciphertext. Use a reviewed envelope/threshold-decapsulation or equivalent design with a stable object-key relation and operation-scoped release binding. Fresh nonces/deadlines protect sessions without losing access to valid ciphertext. Test repeated authorized reads using distinct permits.

### REQ-27-02

Public hashes, signatures, and Merkle proofs are not secret entropy. Define confidential keys, recipients, encapsulations, AEAD associated data, nonces, and domains. Test reuse, substitution, canonicalization ambiguity, mixed contributions, malformed proofs, replay, quorum races, and rollback. Preserve algorithm identities and migration evidence.

### REQ-27-03

Define generation, refresh, revocation, authority replacement, recovery, and rewrapping without reconstructing the root. State proactive-refresh assumptions about old shares, compromised endpoints, ciphertext, and erasure. Refresh does not undo captured plaintext. Specify secure freshness during offline operation and authority/witness outage. Missing quorum cannot fall back silently to one domain.

### REQ-27-04

Bind measured workers throughout the permitted operation and output path. A launch hash is not remote attestation, and launch attestation is not continuous integrity. Claims require evidence from the real technology. Independent cryptographic review, external vectors/implementations, hardware tests, and recovery drills are promotion gates; local self-review cannot be renamed independent evidence. Continue non-sensitive implementation while blocked gates stay visible.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B089, B090, B091, B092, B093, B094, B095, B096. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.
