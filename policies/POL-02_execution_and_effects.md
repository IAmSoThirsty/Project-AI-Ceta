# Complete effect mediation

**Document ID:** POL-02  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Scope and controlling responsibilities

Enforcement owner: kernel + protected effect broker. This policy derives from the ground-up master prompt sections 20, 21. It is a complete written implementation rule; source adoption, exact compiled policy bytes and runtime enforcement require the build gates.

## Rules

All file writes, commands, protected reads, credential use, communications, publications and maintenance effects MUST traverse the registered effect path. Tool registration states the exact schema, resource scope, executable identity, preconditions, idempotency, observations and failure contract. An unregistered tool cannot be enabled by model-generated code or UI convenience.

The kernel records durable intent and admission before the broker crosses the external-effect boundary. Permit consumption is single-use and durable; retries receive new attempt identity and current authorization. The broker enforces actual resource access before an effect, not only by checking a diff afterward. Tool-to-tool delegation is another admitted request.

A dispatch acknowledgment, process exit, observed resource state and verified postcondition are distinct facts. Unsupported postconditions remain unresolved. Audit replay reconstructs state without invoking any original effect. Compensation is a new admitted operation against current state and cannot overwrite later user changes.

## Enforcement and evidence

Implement predicates at the stated control boundary and add rejection fixtures for each forbidden path. Record the exact policy version, inputs, evaluated rule IDs and result. The policy's text is not itself an executable guard. Preserve both a legal case and a boundary-violation case in the source-bound verification bundle.

## Change and exception handling

A conflict with current adopted source law blocks the affected activation and is entered in the decision register. Do not invent an exception to obtain a passing test. Proposed changes must preserve the audit trail, identify impacted requirements and re-run dependent tests. Emergency responses may only exercise pre-existing, narrower authority.

Requirement groups: REQ-20-01, REQ-20-02, REQ-20-03, REQ-20-04, REQ-21-01, REQ-21-02, REQ-21-03, REQ-21-04, REQ-21-05.
