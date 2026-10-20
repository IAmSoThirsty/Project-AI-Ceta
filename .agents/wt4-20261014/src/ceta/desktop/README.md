# Native desktop and trusted interaction

**Document ID:** CMP-21  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Responsibility and boundary

Own presentation, user input, real actions, approvals, accessibility and honest status. PySide6 host and explicitly trusted approval surface; no core authority writes.

## Inputs and outputs

Accepted inputs: Scoped projections and authenticated human interactions. Required output: Typed use-case requests and inspectable display state. All state-changing requests use the canonical kernel API and return typed results. Only the responsible trusted owner may commit its authoritative records. A field or graph edge claiming authority is data until verified against the current canonical permission state.

## Implementation assignment

Implement conversation, work, approvals, memory/evidence, models and recovery within one navigation; preserve drafts and accessible out-of-band stop. Implement types, orchestration calls, error handling and actual public call sites together; a class that is never called by the application does not satisfy this assignment. Resolve semantic differences with source fixtures before importing code. Place protocol/platform-specific infrastructure behind the core port and preserve dependency direction.

## Integration seams

Use `contracts` for message definitions. Runtime interactions are explicit ports; this folder may not import desktop widgets, legacy authority writers, hidden provider clients or another component's mutable store. The application composition root binds implementations after Gate A freezes the system contract. The full dependency and IPC rules are in `docs/architecture/DEPENDENCIES_AND_IPC.md`.

## Failure behaviour

Return structured errors carrying phase, affected resources, recoverability, evidence and observed effect status. Rejection must leave no unexplained positive permission. A failure after possible mutation remains indeterminate until independently observed and settled. Preserve original records, uncertainty and user drafts through recovery.

## Required verification

Test double clicks, stale approval, late callbacks, scaling, focus, keyboard operation and unavailable capabilities. Exercise the real integration seams before declaring connected status. Tests must include a valid path, an unauthorized path and an interruption path where relevant. Component success cannot stand in for installed or system-wide qualification.

Acceptance IDs: B026, B113, B114, B115, B116, B119.

## Authoritative requirement groups

REQ-32-01, REQ-32-02, REQ-32-03, REQ-32-04.

## Detailed specifications

- [SPEC-32: Native interface and inspectability](../../../docs/specification/32_native_interface_and_inspectability.md)

## Completion output

Return implementation paths, contract version, dependency changes, executed commands, test IDs, raw results, remaining gates and a source-bound evidence record. Assign a real executor at kickoff; the role name in this package is not a fabricated reviewer identity.
