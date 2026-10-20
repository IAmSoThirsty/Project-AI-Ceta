# Canonical types and serialization

**Document ID:** CMP-01  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Responsibility and boundary

Own strict records, identifiers, canonical byte rules, version dispatch and deterministic validation errors. Pure contract library; no OS handles, UI, model calls or mutable state.

## Inputs and outputs

Accepted inputs: Typed requests and immutable records. Required output: Validated shapes or explicit errors; never an authority decision. All state-changing requests use the canonical kernel API and return typed results. Only the responsible trusted owner may commit its authoritative records. A field or graph edge claiming authority is data until verified against the current canonical permission state.

## Implementation assignment

Implement bounded decoding with duplicate-key rejection; domain-separated commitments; exact counters and units; schema evolution and original-byte preservation. Implement types, orchestration calls, error handling and actual public call sites together; a class that is never called by the application does not satisfy this assignment. Resolve semantic differences with source fixtures before importing code. Place protocol/platform-specific infrastructure behind the core port and preserve dependency direction.

## Integration seams

Use `contracts` for message definitions. Runtime interactions are explicit ports; this folder may not import desktop widgets, legacy authority writers, hidden provider clients or another component's mutable store. The application composition root binds implementations after Gate A freezes the system contract. The full dependency and IPC rules are in `docs/architecture/DEPENDENCIES_AND_IPC.md`.

## Failure behaviour

Return structured errors carrying phase, affected resources, recoverability, evidence and observed effect status. Rejection must leave no unexplained positive permission. A failure after possible mutation remains indeterminate until independently observed and settled. Preserve original records, uncertainty and user drafts through recovery.

## Required verification

Fuzz malformed schemas, Unicode, duplicate keys, overlarge values and version mismatches; verify canonical bytes with a second implementation. Exercise the real integration seams before declaring connected status. Tests must include a valid path, an unauthorized path and an interruption path where relevant. Component success cannot stand in for installed or system-wide qualification.

Acceptance IDs: B007, B037, B056, B059, B063, B068.

## Authoritative requirement groups

REQ-05-01, REQ-05-02, REQ-05-03, REQ-05-04, REQ-06-01, REQ-06-02, REQ-06-03, REQ-06-04.

## Detailed specifications

- [SPEC-05: Dependency direction and ownership](../../../docs/specification/05_dependency_direction_and_ownership.md)
- [SPEC-06: Identity and canonical objects](../../../docs/specification/06_identity_and_canonical_objects.md)

## Completion output

Return implementation paths, contract version, dependency changes, executed commands, test IDs, raw results, remaining gates and a source-bound evidence record. Assign a real executor at kickoff; the role name in this package is not a fabricated reviewer identity.
