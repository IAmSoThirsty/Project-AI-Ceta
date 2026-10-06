# Stop, crash and uncertain outcomes

**Document ID:** POL-16  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Scope and controlling responsibilities

Enforcement owner: supervisor + kernel + observer. This policy derives from the ground-up master prompt sections 30, 20. It is a complete written implementation rule; source adoption, exact compiled policy bytes and runtime enforcement require the build gates.

## Rules

Stop MUST be an out-of-band runtime action available during generation, indexing, tools and setup. Disable new admission at the declared point, stop only owned processes and report requested, stopping, stopped and reconciled distinctly. UI acknowledgement is based on observed control state.

Persist enough evidence before dispatch to distinguish definitely not started from possibly executed. A crash after a potential effect creates an indeterminate record; the original permit is never revived. Block dependent resources while allowing unrelated safe work. A user acknowledgment alone is not proof of an external effect's result.

Reconciliation inspects current reality, original inputs, candidate outputs and receiver-side identity where available. State matching can establish what exists now without proving who caused it. Compensation uses new authority and must preserve subsequent user edits. Corrupt history or missing identity opens read-only preserved recovery instead of a clean-slate reset.

## Enforcement and evidence

Implement predicates at the stated control boundary and add rejection fixtures for each forbidden path. Record the exact policy version, inputs, evaluated rule IDs and result. The policy's text is not itself an executable guard. Preserve both a legal case and a boundary-violation case in the source-bound verification bundle.

## Change and exception handling

A conflict with current adopted source law blocks the affected activation and is entered in the decision register. Do not invent an exception to obtain a passing test. Proposed changes must preserve the audit trail, identify impacted requirements and re-run dependent tests. Emergency responses may only exercise pre-existing, narrower authority.

Requirement groups: REQ-20-01, REQ-20-02, REQ-20-03, REQ-20-04, REQ-30-01, REQ-30-02, REQ-30-03, REQ-30-04.
