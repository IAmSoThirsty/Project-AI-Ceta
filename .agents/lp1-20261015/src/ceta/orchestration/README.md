# Constrained orchestration and TAAR adaptation

**Document ID:** CMP-13  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Responsibility and boundary

Own typed graph semantics and compute legal readiness without independent permission state. Pure graph compiler plus kernel-owned scheduling use cases.

## Inputs and outputs

Accepted inputs: Authorized graph fragments, scope ceiling and kernel state. Required output: Compiled graph, readiness reasons and requested node transitions. All state-changing requests use the canonical kernel API and return typed results. Only the responsible trusted owner may commit its authoritative records. A field or graph edge claiming authority is data until verified against the current canonical permission state.

## Implementation assignment

Keep dependency, communication, review and authorization distinct; atomically bind executor claims; integrate TAAR report abilities without importing mutation permission. Implement types, orchestration calls, error handling and actual public call sites together; a class that is never called by the application does not satisfy this assignment. Resolve semantic differences with source fixtures before importing code. Place protocol/platform-specific infrastructure behind the core port and preserve dependency direction.

## Integration seams

Use `contracts` for message definitions. Runtime interactions are explicit ports; this folder may not import desktop widgets, legacy authority writers, hidden provider clients or another component's mutable store. The application composition root binds implementations after Gate A freezes the system contract. The full dependency and IPC rules are in `docs/architecture/DEPENDENCIES_AND_IPC.md`.

## Failure behaviour

Return structured errors carrying phase, affected resources, recoverability, evidence and observed effect status. Rejection must leave no unexplained positive permission. A failure after possible mutation remains indeterminate until independently observed and settled. Preserve original records, uncertainty and user drafts through recovery.

## Required verification

Parameterize invalid edges, scope widening, double claims, stale receipts, self-review and jump-to-integration. Exercise the real integration seams before declaring connected status. Tests must include a valid path, an unauthorized path and an interruption path where relevant. Component success cannot stand in for installed or system-wide qualification.

Acceptance IDs: B049, B050, B051, B052, B053, B054, B055, B056.

## Authoritative requirement groups

REQ-18-01, REQ-18-02, REQ-18-03, REQ-18-04.

## Detailed specifications

- [SPEC-18: Kernel-owned constrained orchestration](../../../docs/specification/18_kernel_owned_constrained_orchestration.md)

## Completion output

Return implementation paths, contract version, dependency changes, executed commands, test IDs, raw results, remaining gates and a source-bound evidence record. Assign a real executor at kickoff; the role name in this package is not a fabricated reviewer identity.
