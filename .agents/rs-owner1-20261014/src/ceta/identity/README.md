# Identity, trusted approvals and time

**Document ID:** CMP-04  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Responsibility and boundary

Own technical identity lookup, authentication bindings, key references, session/boot generations and approval ceremony verification. Credential and trusted-approval boundary with narrowly exposed operations.

## Inputs and outputs

Accepted inputs: OS peer identity, owner approvals, key-status evidence and time observations. Required output: Verified identity/approval evidence and time uncertainty; kernel grants remain kernel-owned. All state-changing requests use the canonical kernel API and return typed results. Only the responsible trusted owner may commit its authoritative records. A field or graph edge claiming authority is data until verified against the current canonical permission state.

## Implementation assignment

Separate human, Companion, worker, publisher and custody identities; bind approvals to exact displayed operation; handle key loss without regeneration over history. Implement types, orchestration calls, error handling and actual public call sites together; a class that is never called by the application does not satisfy this assignment. Resolve semantic differences with source fixtures before importing code. Place protocol/platform-specific infrastructure behind the core port and preserve dependency direction.

## Integration seams

Use `contracts` for message definitions. Runtime interactions are explicit ports; this folder may not import desktop widgets, legacy authority writers, hidden provider clients or another component's mutable store. The application composition root binds implementations after Gate A freezes the system contract. The full dependency and IPC rules are in `docs/architecture/DEPENDENCIES_AND_IPC.md`.

## Failure behaviour

Return structured errors carrying phase, affected resources, recoverability, evidence and observed effect status. Rejection must leave no unexplained positive permission. A failure after possible mutation remains indeterminate until independently observed and settled. Preserve original records, uncertainty and user drafts through recovery.

## Required verification

Forge peers and approval callbacks; reuse PIDs; roll clock backward; restore copied profiles under a different OS account. Exercise the real integration seams before declaring connected status. Tests must include a valid path, an unauthorized path and an interruption path where relevant. Component success cannot stand in for installed or system-wide qualification.

Acceptance IDs: B007, B056, B057, B058, B059, B060, B061, B062, B063, B064, B114.

## Authoritative requirement groups

REQ-06-01, REQ-06-02, REQ-06-03, REQ-06-04, REQ-19-01, REQ-19-02, REQ-19-03, REQ-19-04, REQ-19-05.

## Detailed specifications

- [SPEC-06: Identity and canonical objects](../../../docs/specification/06_identity_and_canonical_objects.md)
- [SPEC-19: Capabilities and authorization linearization](../../../docs/specification/19_capabilities_and_authorization_linearization.md)

## Completion output

Return implementation paths, contract version, dependency changes, executed commands, test IDs, raw results, remaining gates and a source-bound evidence record. Assign a real executor at kickoff; the role name in this package is not a fabricated reviewer identity.
