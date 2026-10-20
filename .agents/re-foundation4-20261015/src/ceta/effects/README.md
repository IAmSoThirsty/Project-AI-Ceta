# Effect broker and adapters

**Document ID:** CMP-14  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Responsibility and boundary

Own bounded effect performance after kernel admission and exact adapter dispatch. OS-enforced broker/worker boundary; no unrestricted generic execution RPC.

## Inputs and outputs

Accepted inputs: Current one-use permit, protected resources and admitted operation. Required output: ExecutionReceipt and observed process/file facts. All state-changing requests use the canonical kernel API and return typed results. Only the responsible trusted owner may commit its authoritative records. A field or graph edge claiming authority is data until verified against the current canonical permission state.

## Implementation assignment

Enforce exact paths, bytes, argument tokens, executable digest, lifetime, environment and time; broker redeem-once admission precedes mutation. Implement types, orchestration calls, error handling and actual public call sites together; a class that is never called by the application does not satisfy this assignment. Resolve semantic differences with source fixtures before importing code. Place protocol/platform-specific infrastructure behind the core port and preserve dependency direction.

## Integration seams

Use `contracts` for message definitions. Runtime interactions are explicit ports; this folder may not import desktop widgets, legacy authority writers, hidden provider clients or another component's mutable store. The application composition root binds implementations after Gate A freezes the system contract. The full dependency and IPC rules are in `docs/architecture/DEPENDENCIES_AND_IPC.md`.

## Failure behaviour

Return structured errors carrying phase, affected resources, recoverability, evidence and observed effect status. Rejection must leave no unexplained positive permission. A failure after possible mutation remains indeterminate until independently observed and settled. Preserve original records, uncertainty and user drafts through recovery.

## Required verification

Call adapters directly; forge IPC; substitute resources; test path alias races, inheritance and revoked/consumed permits. Exercise the real integration seams before declaring connected status. Tests must include a valid path, an unauthorized path and an interruption path where relevant. Component success cannot stand in for installed or system-wide qualification.

Acceptance IDs: B058, B060, B065, B066, B067, B068, B069, B070, B071, B072, B097, B098, B099, B100, B103, B104.

## Authoritative requirement groups

REQ-20-01, REQ-20-02, REQ-20-03, REQ-20-04, REQ-21-01, REQ-21-02, REQ-21-03, REQ-21-04, REQ-21-05.

## Detailed specifications

- [SPEC-20: Effects, verification, and settlement](../../../docs/specification/20_effects_verification_and_settlement.md)
- [SPEC-21: Windows process and resource enforcement](../../../docs/specification/21_windows_process_and_resource_enforcement.md)

## Completion output

Return implementation paths, contract version, dependency changes, executed commands, test IDs, raw results, remaining gates and a source-bound evidence record. Assign a real executor at kickoff; the role name in this package is not a fabricated reviewer identity.
