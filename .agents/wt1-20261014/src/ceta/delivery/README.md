# Build, release and maintenance

**Document ID:** CMP-24  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Responsibility and boundary

Own candidate assembly, dependency closure, signed update protocol and artifact provenance. Reproducible build tooling and separately authorized publisher actions.

## Inputs and outputs

Accepted inputs: Frozen source/config, pinned toolchain and gate evidence. Required output: Installer, verification bundle, SBOM, source companion and release evidence. All state-changing requests use the canonical kernel API and return typed results. Only the responsible trusted owner may commit its authoritative records. A field or graph edge claiming authority is data until verified against the current canonical permission state.

## Implementation assignment

Separate runtime, policy, model and package versions; verify actual installed bytes; retain personal signing choice and independent identity verification. Implement types, orchestration calls, error handling and actual public call sites together; a class that is never called by the application does not satisfy this assignment. Resolve semantic differences with source fixtures before importing code. Place protocol/platform-specific infrastructure behind the core port and preserve dependency direction.

## Integration seams

Use `contracts` for message definitions. Runtime interactions are explicit ports; this folder may not import desktop widgets, legacy authority writers, hidden provider clients or another component's mutable store. The application composition root binds implementations after Gate A freezes the system contract. The full dependency and IPC rules are in `docs/architecture/DEPENDENCIES_AND_IPC.md`.

## Failure behaviour

Return structured errors carrying phase, affected resources, recoverability, evidence and observed effect status. Rejection must leave no unexplained positive permission. A failure after possible mutation remains indeterminate until independently observed and settled. Preserve original records, uncertainty and user drafts through recovery.

## Required verification

Tamper update metadata and binaries; relabel old releases; interrupt update/uninstall; inspect loaded libraries and retained data. Exercise the real integration seams before declaring connected status. Tests must include a valid path, an unauthorized path and an interruption path where relevant. Component success cannot stand in for installed or system-wide qualification.

Acceptance IDs: B112, B122, B123, B124.

## Authoritative requirement groups

REQ-38-01, REQ-38-02, REQ-38-03, REQ-38-04, REQ-38-05.

## Detailed specifications

- [SPEC-38: Supply chain, packaging, and updates](../../../docs/specification/38_supply_chain_packaging_and_updates.md)

## Completion output

Return implementation paths, contract version, dependency changes, executed commands, test IDs, raw results, remaining gates and a source-bound evidence record. Assign a real executor at kickoff; the role name in this package is not a fabricated reviewer identity.
