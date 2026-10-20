# CETA-owned local model execution

**Document ID:** CMP-16  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Responsibility and boundary

Own pinned model execution, exact tokenizer/template contract and measured backend state. Contained inference worker behind owned lifecycle and residency lease.

## Inputs and outputs

Accepted inputs: Prepared request, qualified config, resource reservation and current session binding. Required output: Actual token stream, terminal state, timings and errors. All state-changing requests use the canonical kernel API and return typed results. Only the responsible trusted owner may commit its authoritative records. A field or graph edge claiming authority is data until verified against the current canonical permission state.

## Implementation assignment

Implement GGUF import and owned llama.cpp-compatible execution without compulsory external services; authenticate endpoint ownership; handle stop, unload and model replacement. Implement types, orchestration calls, error handling and actual public call sites together; a class that is never called by the application does not satisfy this assignment. Resolve semantic differences with source fixtures before importing code. Place protocol/platform-specific infrastructure behind the core port and preserve dependency direction.

## Integration seams

Use `contracts` for message definitions. Runtime interactions are explicit ports; this folder may not import desktop widgets, legacy authority writers, hidden provider clients or another component's mutable store. The application composition root binds implementations after Gate A freezes the system contract. The full dependency and IPC rules are in `docs/architecture/DEPENDENCIES_AND_IPC.md`.

## Failure behaviour

Return structured errors carrying phase, affected resources, recoverability, evidence and observed effect status. Rejection must leave no unexplained positive permission. A failure after possible mutation remains indeterminate until independently observed and settled. Preserve original records, uncertainty and user drafts through recovery.

## Required verification

Test mutable weights, fake local service, count mismatch, lost stream, real cancellation and resource pressure. Exercise the real integration seams before declaring connected status. Tests must include a valid path, an unauthorized path and an interruption path where relevant. Component success cannot stand in for installed or system-wide qualification.

Acceptance IDs: B072, B073, B074, B075, B076, B077, B078, B079, B080, B081, B082, B083, B084, B085, B086, B087, B088, B113, B121.

## Authoritative requirement groups

REQ-22-01, REQ-22-02, REQ-22-03, REQ-22-04, REQ-23-01, REQ-23-02, REQ-23-03, REQ-23-04, REQ-24-01, REQ-24-02, REQ-24-03, REQ-24-04, REQ-24-05.

## Detailed specifications

- [SPEC-22: CETA-owned local inference](../../../docs/specification/22_ceta_owned_local_inference.md)
- [SPEC-23: Acquisition, hardware, and configuration](../../../docs/specification/23_acquisition_hardware_and_configuration.md)
- [SPEC-24: Quality, drift, and independent evaluation](../../../docs/specification/24_quality_drift_and_independent_evaluation.md)

## Completion output

Return implementation paths, contract version, dependency changes, executed commands, test IDs, raw results, remaining gates and a source-bound evidence record. Assign a real executor at kickoff; the role name in this package is not a fabricated reviewer identity.
