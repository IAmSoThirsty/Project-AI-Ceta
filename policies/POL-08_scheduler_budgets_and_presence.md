# Finite agency and background operation

**Document ID:** POL-08  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Scope and controlling responsibilities

Enforcement owner: supervisor + scheduler + kernel budget owner. This policy derives from the ground-up master prompt sections 08, 09, 34. It is a complete written implementation rule; source adoption, exact compiled policy bytes and runtime enforcement require the build gates.

## Rules

Every autonomous wakeup MUST trace to an admitted user request, standing instruction or declared system-maintenance duty. Queue items have causation, deduplication, finite budgets, expiry, retry policy and disposition. No recursive reflection, notification or self-generated event may create unbounded model calls.

Background operation is an explicit user setting. Closing the UI stops owned work by default; an opted-in service clearly displays its remaining scope and lifetime. Observation subscriptions survive only under current grants. After downtime, the system reports the observation gap and reconciles current resources.

Reserve capacity for stop, evidence settlement and recovery before accepting additional work. Worker leases are fenced so old workers cannot act after reassignment. Queue saturation produces coalescing, backpressure or a visible incomplete-state report, never silent loss presented as full awareness.

## Enforcement and evidence

Implement predicates at the stated control boundary and add rejection fixtures for each forbidden path. Record the exact policy version, inputs, evaluated rule IDs and result. The policy's text is not itself an executable guard. Preserve both a legal case and a boundary-violation case in the source-bound verification bundle.

## Change and exception handling

A conflict with current adopted source law blocks the affected activation and is entered in the decision register. Do not invent an exception to obtain a passing test. Proposed changes must preserve the audit trail, identify impacted requirements and re-run dependent tests. Emergency responses may only exercise pre-existing, narrower authority.

Requirement groups: REQ-08-01, REQ-08-02, REQ-08-03, REQ-08-04, REQ-09-01, REQ-09-02, REQ-09-03, REQ-09-04, REQ-34-01, REQ-34-02, REQ-34-03, REQ-34-04.
