# Fates, retrieval and cognitive graph

**Document ID:** CMP-08  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Responsibility and boundary

Own candidate creation, relevance weighting, lifecycle proposals and permission-filtered derived indexes. Scoped payload/index storage; mutations admitted by the kernel.

## Inputs and outputs

Accepted inputs: Admitted observations, corrections, evidence, approved retention rules and scoped queries. Required output: MemoryRecord, retrieval bundles and lifecycle proposals. All state-changing requests use the canonical kernel API and return typed results. Only the responsible trusted owner may commit its authoritative records. A field or graph edge claiming authority is data until verified against the current canonical permission state.

## Implementation assignment

Implement Clotho, Lachesis and Atropos as bounded responsibilities; retain contradiction, provenance, valid-time and record-time; propagate correction and deletion into derived data. Implement types, orchestration calls, error handling and actual public call sites together; a class that is never called by the application does not satisfy this assignment. Resolve semantic differences with source fixtures before importing code. Place protocol/platform-specific infrastructure behind the core port and preserve dependency direction.

## Integration seams

Use `contracts` for message definitions. Runtime interactions are explicit ports; this folder may not import desktop widgets, legacy authority writers, hidden provider clients or another component's mutable store. The application composition root binds implementations after Gate A freezes the system contract. The full dependency and IPC rules are in `docs/architecture/DEPENDENCIES_AND_IPC.md`.

## Failure behaviour

Return structured errors carrying phase, affected resources, recoverability, evidence and observed effect status. Rejection must leave no unexplained positive permission. A failure after possible mutation remains indeterminate until independently observed and settled. Preserve original records, uncertainty and user drafts through recovery.

## Required verification

Prove frequency does not confer truth/authority; test cross-project existence leakage, deleted embeddings, summary poisoning and cache revocation. Exercise the real integration seams before declaring connected status. Tests must include a valid path, an unauthorized path and an interruption path where relevant. Component success cannot stand in for installed or system-wide qualification.

Acceptance IDs: B033, B034, B035, B036, B037, B038, B040, B065, B066, B117, B118.

## Authoritative requirement groups

REQ-12-01, REQ-12-02, REQ-12-03, REQ-12-04, REQ-12-05, REQ-29-01, REQ-29-02, REQ-29-03.

## Detailed specifications

- [SPEC-12: Memory, The Fates, and the graph](../../../docs/specification/12_memory_the_fates_and_the_graph.md)
- [SPEC-29: Privacy, retention, export, and forgetting](../../../docs/specification/29_privacy_retention_export_and_forgetting.md)

## Completion output

Return implementation paths, contract version, dependency changes, executed commands, test IDs, raw results, remaining gates and a source-bound evidence record. Assign a real executor at kickoff; the role name in this package is not a fabricated reviewer identity.
