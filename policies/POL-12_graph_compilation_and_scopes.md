# Deterministic graph progression

**Document ID:** POL-12  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Scope and controlling responsibilities

Enforcement owner: orchestration compiler + kernel. This policy derives from the ground-up master prompt sections 18, 05. It is a complete written implementation rule; source adoption, exact compiled policy bytes and runtime enforcement require the build gates.

## Rules

Graphs MUST preserve execution dependency, communication, review, authority and evidence as typed relations. Unknown edges, unresolved references, undeclared duplicate overrides, invalid scopes and unsupported hard cycles are compile errors. Every run binds the immutable effective graph fingerprint.

Readiness is calculated from actual kernel state and verified prerequisites. A model requests work and reports results; it cannot assign READY, SUCCEEDED or integrated status. Executor claims are atomic and include input revision, lease generation, resource budget and scope. Ambiguous overlap serializes or rejects writes.

Evidence must match the graph, run, node, executor and current expected artifacts. Imported AGENTS files cannot grant broader permissions. The canonical store, not a historical state.json or agent-local log, owns progression. Current graph replacement requires a governed migration or a new run.

## Enforcement and evidence

Implement predicates at the stated control boundary and add rejection fixtures for each forbidden path. Record the exact policy version, inputs, evaluated rule IDs and result. The policy's text is not itself an executable guard. Preserve both a legal case and a boundary-violation case in the source-bound verification bundle.

## Change and exception handling

A conflict with current adopted source law blocks the affected activation and is entered in the decision register. Do not invent an exception to obtain a passing test. Proposed changes must preserve the audit trail, identify impacted requirements and re-run dependent tests. Emergency responses may only exercise pre-existing, narrower authority.

Requirement groups: REQ-05-01, REQ-05-02, REQ-05-03, REQ-05-04, REQ-18-01, REQ-18-02, REQ-18-03, REQ-18-04.
