# Canonical history and projections

**Document ID:** CMP-03  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Responsibility and boundary

Own durable commit mechanics, per-scope ordered streams, optimistic revisions, outbox transactions and derivable projections. Protected store adapter accessible to the trusted application service, never model workers.

## Inputs and outputs

Accepted inputs: Kernel-owned commit batches and authorized read queries. Required output: Durable commit evidence, consistent snapshots and scoped projections. All state-changing requests use the canonical kernel API and return typed results. Only the responsible trusted owner may commit its authoritative records. A field or graph edge claiming authority is data until verified against the current canonical permission state.

## Implementation assignment

Implement serialized writes; event, budget and intent atomicity; checkpoint/prefix validation; backup through the selected supported SQLite mechanism; bounded incremental projection rebuild. Implement types, orchestration calls, error handling and actual public call sites together; a class that is never called by the application does not satisfy this assignment. Resolve semantic differences with source fixtures before importing code. Place protocol/platform-specific infrastructure behind the core port and preserve dependency direction.

## Integration seams

Use `contracts` for message definitions. Runtime interactions are explicit ports; this folder may not import desktop widgets, legacy authority writers, hidden provider clients or another component's mutable store. The application composition root binds implementations after Gate A freezes the system contract. The full dependency and IPC rules are in `docs/architecture/DEPENDENCIES_AND_IPC.md`.

## Failure behaviour

Return structured errors carrying phase, affected resources, recoverability, evidence and observed effect status. Rejection must leave no unexplained positive permission. A failure after possible mutation remains indeterminate until independently observed and settled. Preserve original records, uncertainty and user drafts through recovery.

## Required verification

Inject disk-full and crash faults; corrupt prefixes and projections; verify rollback detection only under the declared trust anchor. Exercise the real integration seams before declaring connected status. Tests must include a valid path, an unauthorized path and an interruption path where relevant. Component success cannot stand in for installed or system-wide qualification.

Acceptance IDs: B009, B010, B011, B012, B013, B014, B016.

## Authoritative requirement groups

REQ-07-01, REQ-07-02, REQ-07-03, REQ-07-04, REQ-07-05.

## Detailed specifications

- [SPEC-07: Canonical history and transactions](../../../docs/specification/07_canonical_history_and_transactions.md)

## Completion output

Return implementation paths, contract version, dependency changes, executed commands, test IDs, raw results, remaining gates and a source-bound evidence record. Assign a real executor at kickoff; the role name in this package is not a fabricated reviewer identity.
