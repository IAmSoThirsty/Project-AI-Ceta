# Distributed cryptographic authority

**Document ID:** CMP-19  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Responsibility and boundary

Own threshold protocol participation and proof checks within each independent domain. Independently administered authority domains plus sealed operation worker.

## Inputs and outputs

Accepted inputs: ProtectedOperationRequest, enrolled identities, epoch, quorum and approved recipient evidence. Required output: Request-bound contribution/constrained result or denial. All state-changing requests use the canonical kernel API and return typed results. Only the responsible trusted owner may commit its authoritative records. A field or graph edge claiming authority is data until verified against the current canonical permission state.

## Implementation assignment

Resolve envelope encryption and threshold confidential release using reviewed primitives; preserve stable ciphertext key relation across fresh sessions; define refresh and revocation. Implement types, orchestration calls, error handling and actual public call sites together; a class that is never called by the application does not satisfy this assignment. Resolve semantic differences with source fixtures before importing code. Place protocol/platform-specific infrastructure behind the core port and preserve dependency direction.

## Integration seams

Use `contracts` for message definitions. Runtime interactions are explicit ports; this folder may not import desktop widgets, legacy authority writers, hidden provider clients or another component's mutable store. The application composition root binds implementations after Gate A freezes the system contract. The full dependency and IPC rules are in `docs/architecture/DEPENDENCIES_AND_IPC.md`.

## Failure behaviour

Return structured errors carrying phase, affected resources, recoverability, evidence and observed effect status. Rejection must leave no unexplained positive permission. A failure after possible mutation remains indeterminate until independently observed and settled. Preserve original records, uncertainty and user drafts through recovery.

## Required verification

Mix epochs/recipients/contributions; lose quorum; repeat distinct authorized decryptions; validate original bytes and external cryptographic vectors. Exercise the real integration seams before declaring connected status. Tests must include a valid path, an unauthorized path and an interruption path where relevant. Component success cannot stand in for installed or system-wide qualification.

Acceptance IDs: B089, B090, B091, B092, B093, B094, B095, B096.

## Authoritative requirement groups

REQ-26-01, REQ-26-02, REQ-26-03, REQ-26-04, REQ-27-01, REQ-27-02, REQ-27-03, REQ-27-04.

## Detailed specifications

- [SPEC-26: CBCC and distributed root authority](../../../docs/specification/26_cbcc_and_distributed_root_authority.md)
- [SPEC-27: Cryptographic correctness and availability](../../../docs/specification/27_cryptographic_correctness_and_availability.md)

## Completion output

Return implementation paths, contract version, dependency changes, executed commands, test IDs, raw results, remaining gates and a source-bound evidence record. Assign a real executor at kickoff; the role name in this package is not a fabricated reviewer identity.
