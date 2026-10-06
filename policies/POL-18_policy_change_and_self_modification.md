# Policy amendments and self-change

**Document ID:** POL-18  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Scope and controlling responsibilities

Enforcement owner: amendment workflow + human reserved authority. This policy derives from the ground-up master prompt sections 16, 24, 14. It is a complete written implementation rule; source adoption, exact compiled policy bytes and runtime enforcement require the build gates.

## Rules

A model MAY recommend a policy, code, memory-weight or training change with supporting evidence. It MUST NOT approve its own authority enlargement, silently rewrite mission, alter its own restrictions or mutate live model weights in response to feedback. Policy changes are versioned artifacts with exact proposed meaning and affected obligations.

Evaluate amendments in isolated fixtures, perform source reconciliation, record dissent and require the appropriate independent review and owner decision. Existing runs stay pinned or migrate under an explicit transition. A rejected amendment remains an attributed proposal rather than disappearing into the live prompt.

Training and model promotion have distinct lineage, budget and evaluation gates. Changing a prompt also changes a tested configuration and triggers applicable regression. Emergency restriction may reduce authority under a pre-adopted policy; it does not give the affected component permission to remove oversight.

## Enforcement and evidence

Implement predicates at the stated control boundary and add rejection fixtures for each forbidden path. Record the exact policy version, inputs, evaluated rule IDs and result. The policy's text is not itself an executable guard. Preserve both a legal case and a boundary-violation case in the source-bound verification bundle.

## Change and exception handling

A conflict with current adopted source law blocks the affected activation and is entered in the decision register. Do not invent an exception to obtain a passing test. Proposed changes must preserve the audit trail, identify impacted requirements and re-run dependent tests. Emergency responses may only exercise pre-existing, narrower authority.

Requirement groups: REQ-14-01, REQ-14-02, REQ-14-03, REQ-16-01, REQ-16-02, REQ-16-03, REQ-16-04, REQ-24-01, REQ-24-02, REQ-24-03, REQ-24-04, REQ-24-05.
