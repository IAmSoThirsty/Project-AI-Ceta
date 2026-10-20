# Legacy import and coherent cutover

**Document ID:** CMP-23  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Responsibility and boundary

Own source snapshots, mapping, conversion, quarantine and restoration rehearsals. Read-mostly conversion boundary plus separately authorized cutover tooling.

## Inputs and outputs

Accepted inputs: Explicit legacy profile snapshot with identity/schema evidence. Required output: New-store genesis and conservation report; old grants remain historical. All state-changing requests use the canonical kernel API and return typed results. Only the responsible trusted owner may commit its authoritative records. A field or graph edge claiming authority is data until verified against the current canonical permission state.

## Implementation assignment

Preserve raw bytes, unknown material and uncertainty; map both supported source lineages; retire every old live authority route after approved cutover. Implement types, orchestration calls, error handling and actual public call sites together; a class that is never called by the application does not satisfy this assignment. Resolve semantic differences with source fixtures before importing code. Place protocol/platform-specific infrastructure behind the core port and preserve dependency direction.

## Integration seams

Use `contracts` for message definitions. Runtime interactions are explicit ports; this folder may not import desktop widgets, legacy authority writers, hidden provider clients or another component's mutable store. The application composition root binds implementations after Gate A freezes the system contract. The full dependency and IPC rules are in `docs/architecture/DEPENDENCIES_AND_IPC.md`.

## Failure behaviour

Return structured errors carrying phase, affected resources, recoverability, evidence and observed effect status. Rejection must leave no unexplained positive permission. A failure after possible mutation remains indeterminate until independently observed and settled. Preserve original records, uncertainty and user drafts through recovery.

## Required verification

Crash each migration step; attempt downgrade; import copied identity; preserve unknown extensions and exact record categories. Exercise the real integration seams before declaring connected status. Tests must include a valid path, an unauthorized path and an interruption path where relevant. Component success cannot stand in for installed or system-wide qualification.

Acceptance IDs: B105, B106, B107, B108, B109, B110, B111, B112.

## Authoritative requirement groups

REQ-31-01, REQ-31-02, REQ-31-03, REQ-31-04, REQ-31-05.

## Detailed specifications

- [SPEC-31: Migration and coherent cutover](../../../docs/specification/31_migration_and_coherent_cutover.md)

## Completion output

Return implementation paths, contract version, dependency changes, executed commands, test IDs, raw results, remaining gates and a source-bound evidence record. Assign a real executor at kickoff; the role name in this package is not a fabricated reviewer identity.
