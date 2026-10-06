# CBCC and distributed root authority

**Document ID:** SPEC-26  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-26-01

Integrate CBCC as a verifiable protected-operation protocol. Root authority remains a distributed cryptographic function across independent technical/administrative domains; never reconstruct it in the application. Select reviewed threshold primitives and implementations with assumptions and vectors. Several local files are not a distributed root, and a threshold signature is not confidential derivation.

### REQ-26-02

Resolve local hardware anchoring versus distributed root before activation. A TPM may anchor identity, a share, or a worker under an explicit role, not become the sole recoverable root under a distributed-protection label. Separate custody identity, authority domains, worker identity, epochs, and recovery. Collocated simulations remain test fixtures.

### REQ-26-03

Bind object/ciphertext identity, requester, consumer, operation, purpose proof, policy/Codex commitments, traversal, authorized resolution, measurement, authority manifest, epoch, revocation, nonce, expiry, and audit checkpoint into the canonical transcript. Verify proofs and resolver authority rather than labels. Purpose prose is not authorization. A signed interpretation proves scoped endorsement, not universal semantic truth.

### REQ-26-04

Each authority verifies the request independently. Enforce quorum classes and genuine failure-domain separation. Contributions are specific to the request, recipient, object, worker, and epoch. Audit commitments exclude secrets and support independent verification. Multi-process tests under one host/admin do not establish host-compromise resilience.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B090, B091, B094, B096. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.
