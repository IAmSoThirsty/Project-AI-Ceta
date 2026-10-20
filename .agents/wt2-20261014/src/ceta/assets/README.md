# Asset custody and resource admission

**Document ID:** CMP-17  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Responsibility and boundary

Own verified downloads/imports, manifests, licenses, storage staging and hardware observations. Explicit acquisition workers; no model-pack code execution.

## Inputs and outputs

Accepted inputs: Explicit asset request and current hardware/storage readings. Required output: Verified local asset or admission refusal with retained partial state. All state-changing requests use the canonical kernel API and return typed results. Only the responsible trusted owner may commit its authoritative records. A field or graph edge claiming authority is data until verified against the current canonical permission state.

## Implementation assignment

Bound archives and resume; verify exact executable/dependencies/model; distinguish weight-fit estimates from measured placement and competence. Implement types, orchestration calls, error handling and actual public call sites together; a class that is never called by the application does not satisfy this assignment. Resolve semantic differences with source fixtures before importing code. Place protocol/platform-specific infrastructure behind the core port and preserve dependency direction.

## Integration seams

Use `contracts` for message definitions. Runtime interactions are explicit ports; this folder may not import desktop widgets, legacy authority writers, hidden provider clients or another component's mutable store. The application composition root binds implementations after Gate A freezes the system contract. The full dependency and IPC rules are in `docs/architecture/DEPENDENCIES_AND_IPC.md`.

## Failure behaviour

Return structured errors carrying phase, affected resources, recoverability, evidence and observed effect status. Rejection must leave no unexplained positive permission. A failure after possible mutation remains indeterminate until independently observed and settled. Preserve original records, uncertainty and user drafts through recovery.

## Required verification

Test malicious ZIP paths, links, bombs, interrupted installs, missing RAM and incompatible GPU claims. Exercise the real integration seams before declaring connected status. Tests must include a valid path, an unauthorized path and an interruption path where relevant. Component success cannot stand in for installed or system-wide qualification.

Acceptance IDs: B072, B075, B080, B113, B121.

## Authoritative requirement groups

REQ-23-01, REQ-23-02, REQ-23-03, REQ-23-04.

## Detailed specifications

- [SPEC-23: Acquisition, hardware, and configuration](../../../docs/specification/23_acquisition_hardware_and_configuration.md)

## Completion output

Return implementation paths, contract version, dependency changes, executed commands, test IDs, raw results, remaining gates and a source-bound evidence record. Assign a real executor at kickoff; the role name in this package is not a fabricated reviewer identity.
