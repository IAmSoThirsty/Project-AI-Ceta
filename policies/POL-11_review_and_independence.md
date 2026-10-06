# Review, dissent and separation of duties

**Document ID:** POL-11  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Scope and controlling responsibilities

Enforcement owner: review coordinator + kernel. This policy derives from the ground-up master prompt sections 17, 18, 36. It is a complete written implementation rule; source adoption, exact compiled policy bytes and runtime enforcement require the build gates.

## Rules

Producer, reviewer, validator and integrator MUST have explicit accountable roles. A second prompt label, sequential self-review or another process under the same administrator does not establish independent review. Record the actual executor and degree of independence achieved.

Required review binds exact input, artifact, policy and source-state fingerprints. Reviewers cannot edit the artifact they approve. Material mutation invalidates affected findings and downstream authorization. Dissent remains visible even where a legitimate decision allows work to proceed.

The Triumvirate supplies different questions and findings; kernel policy supplies legal progression. Unanimous advisory opinions cannot override mandatory constraints, fabricate consent or prove a semantic claim. Missing required independent review blocks its promotion gate while implementation and unrelated tests may continue.

## Enforcement and evidence

Implement predicates at the stated control boundary and add rejection fixtures for each forbidden path. Record the exact policy version, inputs, evaluated rule IDs and result. The policy's text is not itself an executable guard. Preserve both a legal case and a boundary-violation case in the source-bound verification bundle.

## Change and exception handling

A conflict with current adopted source law blocks the affected activation and is entered in the decision register. Do not invent an exception to obtain a passing test. Proposed changes must preserve the audit trail, identify impacted requirements and re-run dependent tests. Emergency responses may only exercise pre-existing, narrower authority.

Requirement groups: REQ-17-01, REQ-17-02, REQ-17-03, REQ-18-01, REQ-18-02, REQ-18-03, REQ-18-04, REQ-36-01, REQ-36-02, REQ-36-03, REQ-36-04.
