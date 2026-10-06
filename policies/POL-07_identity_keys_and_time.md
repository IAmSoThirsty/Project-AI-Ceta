# Identity, keys and trusted temporal state

**Document ID:** POL-07  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Scope and controlling responsibilities

Enforcement owner: identity service + time provider + kernel. This policy derives from the ground-up master prompt sections 06, 19, 30. It is a complete written implementation rule; source adoption, exact compiled policy bytes and runtime enforcement require the build gates.

## Rules

Logical identity and key material MUST be separated from display names. Human, Companion, installation, project, worker, publisher, custody and distributed-authority identities have different roles. Worker session and boot generation change on restart; a PID alone cannot establish continuity or authenticity.

Missing or mismatched keys beside governed history require preserved recovery. The application must not regenerate a replacement identity to make startup green. Publisher signing keys remain outside ordinary runtime access. Rotation, transfer, revocation and recovery each create attributable transitions.

Use monotonic time for deadlines within a boot, with explicit wall-time uncertainty and durable epochs across reboots. Restart, sleep/resume and clock rollback must not extend permissions or restore consumed budgets. When a required freshness source is unavailable, deny the dependent time-sensitive operation while retaining safe read-only capabilities.

## Enforcement and evidence

Implement predicates at the stated control boundary and add rejection fixtures for each forbidden path. Record the exact policy version, inputs, evaluated rule IDs and result. The policy's text is not itself an executable guard. Preserve both a legal case and a boundary-violation case in the source-bound verification bundle.

## Change and exception handling

A conflict with current adopted source law blocks the affected activation and is entered in the decision register. Do not invent an exception to obtain a passing test. Proposed changes must preserve the audit trail, identify impacted requirements and re-run dependent tests. Emergency responses may only exercise pre-existing, narrower authority.

Requirement groups: REQ-06-01, REQ-06-02, REQ-06-03, REQ-06-04, REQ-19-01, REQ-19-02, REQ-19-03, REQ-19-04, REQ-19-05, REQ-30-01, REQ-30-02, REQ-30-03, REQ-30-04.
