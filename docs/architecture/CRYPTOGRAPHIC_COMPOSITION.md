# Custody and CBCC composition decision

**Document ID:** ARCH-07  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Three distinct objects

The Sovereign Interior Vault is a cognitive isolation workspace. The Defensive Vault is protected object custody. CBCC is a distributed-authority cryptographic protocol. They share typed request/evidence contracts but never collapse into one universal secret-bearing manager. This distinction is binding in names, ownership and UI descriptions.

## Local and distributed identity

A local secure element may anchor custody identity, a participating share or a measured worker under a declared role. It cannot silently become the sole recoverable root while the product claims distributed protection. Authority domains need genuinely independent administration, deployment, secrets, logs and failure assumptions. Local multi-process fixtures remain explicitly synthetic-domain tests.

## Proposed composition to resolve before activation

Use established authenticated envelope encryption for object ciphertext, with a stable object-key relationship. Fresh operation authorization gates reviewed threshold decapsulation/decryption or equivalent confidential key access into an approved recipient boundary. Bind the request to object/ciphertext, purpose evidence, actor, consumer, operation, policy/Codex roots, resolver, epoch, revocation, nonce, expiry, measurement and prior audit commitment. Do not derive an unrelated new object key from each fresh expiring permit and expect old ciphertext to decrypt.

The exact reviewed threshold construction, library, domain topology and hardware choice remain an explicit architecture decision requiring evidence. Public signatures, hashes and Merkle proofs are not confidential entropy. A signature proving a scoped interpretation is not a proof that unrestricted human-language meaning has been solved. Purpose verification checks an authorized declared purpose, not a hidden mental state.

## Root and refresh

Root authority is exercised without assembling a universal root inside CETA. Shares have narrow permitted operations and do not expose generic arbitrary-byte signing/decryption. Epoch refresh and revocation must describe what happens to old shares, backups, captured ciphertext and plaintext. Cryptographic refresh cannot revoke data already learned. Replay rejection and current admissibility require the actual consumed-request and freshness basis, including offline/witness-outage behaviour.

## Required proof package

Before strong protected-operation claims, require an explicit adversary model, reviewed protocol, external vectors/interoperability, independent cryptographic review, real domain/hardware evidence and recovery drills. Test repeat authorized reads of unchanged ciphertext, mixed requests, quorum loss, wrong workers, rollback, residual-secret canaries and rejected plaintext destinations. Strong lanes remain closed while requirements stay open; non-sensitive integration can proceed using honest test profiles.
