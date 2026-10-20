# Independent outcome observation and evidence checks

**Document ID:** CMP-15  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Responsibility and boundary

Own checks of actual postconditions and evidence bundles; kernel settles state. Distinct observing/verifying role with separately described independence.

## Inputs and outputs

Accepted inputs: Expected predicate, authorized actual resources and recorded receipts. Required output: EffectObservation, discrepancy or independently attributable bundle finding. All state-changing requests use the canonical kernel API and return typed results. Only the responsible trusted owner may commit its authoritative records. A field or graph edge claiming authority is data until verified against the current canonical permission state.

## Implementation assignment

Read results through a separate path; distinguish state equality from causal attribution; build verifier without delegating trust to producer accept routines. Implement types, orchestration calls, error handling and actual public call sites together; a class that is never called by the application does not satisfy this assignment. Resolve semantic differences with source fixtures before importing code. Place protocol/platform-specific infrastructure behind the core port and preserve dependency direction.

## Integration seams

Use `contracts` for message definitions. Runtime interactions are explicit ports; this folder may not import desktop widgets, legacy authority writers, hidden provider clients or another component's mutable store. The application composition root binds implementations after Gate A freezes the system contract. The full dependency and IPC rules are in `docs/architecture/DEPENDENCIES_AND_IPC.md`.

## Failure behaviour

Return structured errors carrying phase, affected resources, recoverability, evidence and observed effect status. Rejection must leave no unexplained positive permission. A failure after possible mutation remains indeterminate until independently observed and settled. Preserve original records, uncertainty and user drafts through recovery.

## Required verification

Inject forged success, zero-exit false outcomes, tampered receipts and shared-implementation errors; verify replay never executes effects. Exercise the real integration seams before declaring connected status. Tests must include a valid path, an unauthorized path and an interruption path where relevant. Component success cannot stand in for installed or system-wide qualification.

Acceptance IDs: B008, B011, B013, B058, B060, B075, B086, B097, B098, B099, B100, B103, B104, B117, B126, B128.

## Authoritative requirement groups

REQ-20-01, REQ-20-02, REQ-20-03, REQ-20-04, REQ-35-01, REQ-35-02, REQ-35-03, REQ-36-01, REQ-36-02, REQ-36-03, REQ-36-04.

## Detailed specifications

- [SPEC-20: Effects, verification, and settlement](../../../docs/specification/20_effects_verification_and_settlement.md)
- [SPEC-35: Observability and assumption propagation](../../../docs/specification/35_observability_and_assumption_propagation.md)
- [SPEC-36: Verification architecture](../../../docs/specification/36_verification_architecture.md)

## Completion output

Return implementation paths, contract version, dependency changes, executed commands, test IDs, raw results, remaining gates and a source-bound evidence record. Assign a real executor at kickoff; the role name in this package is not a fabricated reviewer identity.
