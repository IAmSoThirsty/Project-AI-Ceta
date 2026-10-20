# Scoped observation and reconciliation

**Document ID:** CMP-06  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Responsibility and boundary

Own observations of selected resources, change hints, reconciliation scans and source completeness. Least-authority read workers with explicit subscriptions.

## Inputs and outputs

Accepted inputs: Authorized resource subscription and recorded observation gaps. Required output: ObservationEnvelope with actual revision, provenance and uncertainty. All state-changing requests use the canonical kernel API and return typed results. Only the responsible trusted owner may commit its authoritative records. A field or graph edge claiming authority is data until verified against the current canonical permission state.

## Implementation assignment

Implement selected-file/repository, runtime-health and tool-output readers; coalesce watcher hints; re-read stable handles; track missed intervals and invalidation dependencies. Implement types, orchestration calls, error handling and actual public call sites together; a class that is never called by the application does not satisfy this assignment. Resolve semantic differences with source fixtures before importing code. Place protocol/platform-specific infrastructure behind the core port and preserve dependency direction.

## Integration seams

Use `contracts` for message definitions. Runtime interactions are explicit ports; this folder may not import desktop widgets, legacy authority writers, hidden provider clients or another component's mutable store. The application composition root binds implementations after Gate A freezes the system contract. The full dependency and IPC rules are in `docs/architecture/DEPENDENCIES_AND_IPC.md`.

## Failure behaviour

Return structured errors carrying phase, affected resources, recoverability, evidence and observed effect status. Rejection must leave no unexplained positive permission. A failure after possible mutation remains indeterminate until independently observed and settled. Preserve original records, uncertainty and user drafts through recovery.

## Required verification

Test rename storms, lost events, access denial, partial scans and off-app modifications without claiming continuous coverage. Exercise the real integration seams before declaring connected status. Tests must include a valid path, an unauthorized path and an interruption path where relevant. Component success cannot stand in for installed or system-wide qualification.

Acceptance IDs: B017, B020, B024, B044.

## Authoritative requirement groups

REQ-10-01, REQ-10-02, REQ-10-03, REQ-10-04.

## Detailed specifications

- [SPEC-10: Observation and shared reality](../../../docs/specification/10_observation_and_shared_reality.md)

## Completion output

Return implementation paths, contract version, dependency changes, executed commands, test IDs, raw results, remaining gates and a source-bound evidence record. Assign a real executor at kickoff; the role name in this package is not a fabricated reviewer identity.
