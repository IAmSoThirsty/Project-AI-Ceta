# Defensive Vault

**Document ID:** CMP-18  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Responsibility and boundary

Own object admission, seal/release lifecycle, protected metadata and custody evidence. Dedicated protected object service, never a tool launcher.

## Inputs and outputs

Accepted inputs: Admitted single-object request, consumer profile and verified custody conditions. Required output: Constrained approved output or seal/deny evidence. All state-changing requests use the canonical kernel API and return typed results. Only the responsible trusted owner may commit its authoritative records. A field or graph edge claiming authority is data until verified against the current canonical permission state.

## Implementation assignment

Implement object-specific release and measured memory hygiene; isolate key classes; bind token possession and epoch; require reviewed recovery. Implement types, orchestration calls, error handling and actual public call sites together; a class that is never called by the application does not satisfy this assignment. Resolve semantic differences with source fixtures before importing code. Place protocol/platform-specific infrastructure behind the core port and preserve dependency direction.

## Integration seams

Use `contracts` for message definitions. Runtime interactions are explicit ports; this folder may not import desktop widgets, legacy authority writers, hidden provider clients or another component's mutable store. The application composition root binds implementations after Gate A freezes the system contract. The full dependency and IPC rules are in `docs/architecture/DEPENDENCIES_AND_IPC.md`.

## Failure behaviour

Return structured errors carrying phase, affected resources, recoverability, evidence and observed effect status. Rejection must leave no unexplained positive permission. A failure after possible mutation remains indeterminate until independently observed and settled. Preserve original records, uncertainty and user drafts through recovery.

## Required verification

Attempt collection-wide unlock, cloned token attributes, raw key export, residue leakage and storage-to-execution escalation. Exercise the real integration seams before declaring connected status. Tests must include a valid path, an unauthorized path and an interruption path where relevant. Component success cannot stand in for installed or system-wide qualification.

Acceptance IDs: B037, B038, B065, B066, B089, B093, B095, B096, B117, B118.

## Authoritative requirement groups

REQ-25-01, REQ-25-02, REQ-25-03, REQ-25-04, REQ-29-01, REQ-29-02, REQ-29-03.

## Detailed specifications

- [SPEC-25: Defensive Vault custody](../../../docs/specification/25_defensive_vault_custody.md)
- [SPEC-29: Privacy, retention, export, and forgetting](../../../docs/specification/29_privacy_retention_export_and_forgetting.md)

## Completion output

Return implementation paths, contract version, dependency changes, executed commands, test IDs, raw results, remaining gates and a source-bound evidence record. Assign a real executor at kickoff; the role name in this package is not a fabricated reviewer identity.
