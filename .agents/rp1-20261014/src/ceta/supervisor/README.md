# Supervisor, queues and owned lifetimes

**Document ID:** CMP-05  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Responsibility and boundary

Own event dispatch leases, task wakeups, service lifetimes, stop coordination and health reporting. Application supervisor with bounded lifecycle privileges; requests authority from kernel.

## Inputs and outputs

Accepted inputs: Admitted queue items, OS process observations and current task projections. Required output: Leased jobs, recorded wakeups, confirmed stops or uncertain recovery. All state-changing requests use the canonical kernel API and return typed results. Only the responsible trusted owner may commit its authoritative records. A field or graph edge claiming authority is data until verified against the current canonical permission state.

## Implementation assignment

Build durable queue admission, deduplication, fencing generations, retry ceilings and backpressure; define UI-close versus explicit background mode. Implement types, orchestration calls, error handling and actual public call sites together; a class that is never called by the application does not satisfy this assignment. Resolve semantic differences with source fixtures before importing code. Place protocol/platform-specific infrastructure behind the core port and preserve dependency direction.

## Integration seams

Use `contracts` for message definitions. Runtime interactions are explicit ports; this folder may not import desktop widgets, legacy authority writers, hidden provider clients or another component's mutable store. The application composition root binds implementations after Gate A freezes the system contract. The full dependency and IPC rules are in `docs/architecture/DEPENDENCIES_AND_IPC.md`.

## Failure behaviour

Return structured errors carrying phase, affected resources, recoverability, evidence and observed effect status. Rejection must leave no unexplained positive permission. A failure after possible mutation remains indeterminate until independently observed and settled. Preserve original records, uncertainty and user drafts through recovery.

## Required verification

Kill parents and workers; duplicate delivery; flood notifications; ensure stale executors cannot affect reassigned tasks. Exercise the real integration seams before declaring connected status. Tests must include a valid path, an unauthorized path and an interruption path where relevant. Component success cannot stand in for installed or system-wide qualification.

Acceptance IDs: B015, B017, B018, B019, B020, B021, B022, B023, B024, B025, B027, B028, B064, B077, B078, B098, B100, B101, B102, B115.

## Authoritative requirement groups

REQ-08-01, REQ-08-02, REQ-08-03, REQ-08-04, REQ-09-01, REQ-09-02, REQ-09-03, REQ-09-04, REQ-30-01, REQ-30-02, REQ-30-03, REQ-30-04.

## Detailed specifications

- [SPEC-08: Supervisor and continuing operation](../../../docs/specification/08_supervisor_and_continuing_operation.md)
- [SPEC-09: Tasks, obligations, and intent](../../../docs/specification/09_tasks_obligations_and_intent.md)
- [SPEC-30: Cancellation, shutdown, and recovery](../../../docs/specification/30_cancellation_shutdown_and_recovery.md)

## Completion output

Return implementation paths, contract version, dependency changes, executed commands, test IDs, raw results, remaining gates and a source-bound evidence record. Assign a real executor at kickoff; the role name in this package is not a fabricated reviewer identity.
