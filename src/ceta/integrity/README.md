# NIRL monitoring and Chimera isolation

**Document ID:** CMP-20  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Responsibility and boundary

Own evidence-backed signal detection and containment recommendations. Technical signal monitor plus visibly isolated containment lane.

## Inputs and outputs

Accepted inputs: Authorized technical events, policy baselines and actual boundary violations. Required output: Risk observations, kernel restriction requests and restoration evidence. All state-changing requests use the canonical kernel API and return typed results. Only the responsible trusted owner may commit its authoritative records. A field or graph edge claiming authority is data until verified against the current canonical permission state.

## Implementation assignment

Separate ambiguity from violation; never classify tone as compromise; isolate fixtures from live memory and credentials; declare restoration prerequisites. Implement types, orchestration calls, error handling and actual public call sites together; a class that is never called by the application does not satisfy this assignment. Resolve semantic differences with source fixtures before importing code. Place protocol/platform-specific infrastructure behind the core port and preserve dependency direction.

## Integration seams

Use `contracts` for message definitions. Runtime interactions are explicit ports; this folder may not import desktop widgets, legacy authority writers, hidden provider clients or another component's mutable store. The application composition root binds implementations after Gate A freezes the system contract. The full dependency and IPC rules are in `docs/architecture/DEPENDENCIES_AND_IPC.md`.

## Failure behaviour

Return structured errors carrying phase, affected resources, recoverability, evidence and observed effect status. Rejection must leave no unexplained positive permission. A failure after possible mutation remains indeterminate until independently observed and settled. Preserve original records, uncertainty and user drafts through recovery.

## Required verification

Test false positives, missing mandatory monitoring, fabricated tool outcomes and user-intensity cases without punitive containment. Exercise the real integration seams before declaring connected status. Tests must include a valid path, an unauthorized path and an interruption path where relevant. Component success cannot stand in for installed or system-wide qualification.

Acceptance IDs: B011, B013, B029, B041, B043, B072, B075, B117, B120, B126.

## Authoritative requirement groups

REQ-28-01, REQ-28-02, REQ-28-03, REQ-35-01, REQ-35-02, REQ-35-03.

## Detailed specifications

- [SPEC-28: NIRL and Chimera](../../../docs/specification/28_nirl_and_chimera.md)
- [SPEC-35: Observability and assumption propagation](../../../docs/specification/35_observability_and_assumption_propagation.md)

## Completion output

Return implementation paths, contract version, dependency changes, executed commands, test IDs, raw results, remaining gates and a source-bound evidence record. Assign a real executor at kickoff; the role name in this package is not a fabricated reviewer identity.
