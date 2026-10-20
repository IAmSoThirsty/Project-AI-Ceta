# Quality, drift and training lifecycle

**Document ID:** CMP-25  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Responsibility and boundary

Own test corpus lineage, scoring, candidate qualification proposals and optional authorized training. Isolated evaluator/training process with budgeted data access.

## Inputs and outputs

Accepted inputs: Frozen fixtures/rubrics, full-stack candidate and configuration identity. Required output: Observed scores, limitations and promotion recommendation with evidence. All state-changing requests use the canonical kernel API and return typed results. Only the responsible trusted owner may commit its authoritative records. A field or graph edge claiming authority is data until verified against the current canonical permission state.

## Implementation assignment

Separate development/selection/held-out/monitoring data; report repeated-trial uncertainty; measure history scale and installed endurance; record all failures. Implement types, orchestration calls, error handling and actual public call sites together; a class that is never called by the application does not satisfy this assignment. Resolve semantic differences with source fixtures before importing code. Place protocol/platform-specific infrastructure behind the core port and preserve dependency direction.

## Integration seams

Use `contracts` for message definitions. Runtime interactions are explicit ports; this folder may not import desktop widgets, legacy authority writers, hidden provider clients or another component's mutable store. The application composition root binds implementations after Gate A freezes the system contract. The full dependency and IPC rules are in `docs/architecture/DEPENDENCIES_AND_IPC.md`.

## Failure behaviour

Return structured errors carrying phase, affected resources, recoverability, evidence and observed effect status. Rejection must leave no unexplained positive permission. A failure after possible mutation remains indeterminate until independently observed and settled. Preserve original records, uncertainty and user drafts through recovery.

## Required verification

Test contamination, opposite preferences, false tool claims, incomplete endurance and fake external/independent evidence. Exercise the real integration seams before declaring connected status. Tests must include a valid path, an unauthorized path and an interruption path where relevant. Component success cannot stand in for installed or system-wide qualification.

Acceptance IDs: B008, B020, B080, B081, B082, B083, B084, B085, B086, B087, B088, B115, B121, B122, B124, B125, B126, B127, B128.

## Authoritative requirement groups

REQ-24-01, REQ-24-02, REQ-24-03, REQ-24-04, REQ-24-05, REQ-34-01, REQ-34-02, REQ-34-03, REQ-34-04, REQ-36-01, REQ-36-02, REQ-36-03, REQ-36-04, REQ-37-01, REQ-37-02, REQ-37-03, REQ-37-04.

## Detailed specifications

- [SPEC-24: Quality, drift, and independent evaluation](../../../docs/specification/24_quality_drift_and_independent_evaluation.md)
- [SPEC-34: Performance and resource integrity](../../../docs/specification/34_performance_and_resource_integrity.md)
- [SPEC-36: Verification architecture](../../../docs/specification/36_verification_architecture.md)
- [SPEC-37: Installed qualification and endurance](../../../docs/specification/37_installed_qualification_and_endurance.md)

## Completion output

Return implementation paths, contract version, dependency changes, executed commands, test IDs, raw results, remaining gates and a source-bound evidence record. Assign a real executor at kickoff; the role name in this package is not a fabricated reviewer identity.
