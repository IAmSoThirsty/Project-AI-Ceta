# Voice, selected-screen and external adapters

**Document ID:** CMP-22  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Responsibility and boundary

Own device observations and interface adaptation, not separate assistants. Opt-in capture/connector workers with explicit scope and retention.

## Inputs and outputs

Accepted inputs: Explicit capture or external-action grants and qualified devices/adapters. Required output: Typed observations or exact action proposals through the same kernel. All state-changing requests use the canonical kernel API and return typed results. Only the responsible trusted owner may commit its authoritative records. A field or graph edge claiming authority is data until verified against the current canonical permission state.

## Implementation assignment

Implement shared modality contracts, selected push-to-talk capture and uncertainty; authenticate endpoints; expose live recording and revocation. Implement types, orchestration calls, error handling and actual public call sites together; a class that is never called by the application does not satisfy this assignment. Resolve semantic differences with source fixtures before importing code. Place protocol/platform-specific infrastructure behind the core port and preserve dependency direction.

## Integration seams

Use `contracts` for message definitions. Runtime interactions are explicit ports; this folder may not import desktop widgets, legacy authority writers, hidden provider clients or another component's mutable store. The application composition root binds implementations after Gate A freezes the system contract. The full dependency and IPC rules are in `docs/architecture/DEPENDENCIES_AND_IPC.md`.

## Failure behaviour

Return structured errors carrying phase, affected resources, recoverability, evidence and observed effect status. Rejection must leave no unexplained positive permission. A failure after possible mutation remains indeterminate until independently observed and settled. Preserve original records, uncertainty and user drafts through recovery.

## Required verification

Test background capture opt-out, misrecognition, scope leakage and confirmation before consequential communication or physical actions. Exercise the real integration seams before declaring connected status. Tests must include a valid path, an unauthorized path and an interruption path where relevant. Component success cannot stand in for installed or system-wide qualification.

Acceptance IDs: B063, B118, B120.

## Authoritative requirement groups

REQ-33-01, REQ-33-02, REQ-33-03.

## Detailed specifications

- [SPEC-33: Modalities and additional interfaces](../../../docs/specification/33_modalities_and_additional_interfaces.md)

## Completion output

Return implementation paths, contract version, dependency changes, executed commands, test IDs, raw results, remaining gates and a source-bound evidence record. Assign a real executor at kickoff; the role name in this package is not a fabricated reviewer identity.
