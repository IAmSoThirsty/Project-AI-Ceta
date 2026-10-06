# Privacy, scoped access and egress

**Document ID:** POL-06  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Scope and controlling responsibilities

Enforcement owner: read broker + payload store + network broker. This policy derives from the ground-up master prompt sections 29, 21, 33. It is a complete written implementation rule; source adoption, exact compiled policy bytes and runtime enforcement require the build gates.

## Rules

A grant to one project MUST NOT authorize whole-drive indexing or access to unrelated conversations, credentials, mailbox content or browser profiles. Scope filtering precedes retrieval material entering a model. Derived summaries and embeddings inherit the source classification; restricted filenames, counts and existence can also be confidential.

Local inference is the normal operational route. Remote inference, diagnostics upload, external knowledge acquisition and communication each require explicit destination, payload scope and current permission. Failure of a local path cannot silently enable cloud fallback. Capture and telemetry are off until their declared policy and consent permit them.

Exports are explicit, non-overwriting and classified. Support bundles minimize content and exclude canary secrets by test. Imported model assets carry no user conversation or authority. Revocation applies to in-flight future disclosure at its documented boundary and invalidates permission-filtered caches.

## Enforcement and evidence

Implement predicates at the stated control boundary and add rejection fixtures for each forbidden path. Record the exact policy version, inputs, evaluated rule IDs and result. The policy's text is not itself an executable guard. Preserve both a legal case and a boundary-violation case in the source-bound verification bundle.

## Change and exception handling

A conflict with current adopted source law blocks the affected activation and is entered in the decision register. Do not invent an exception to obtain a passing test. Proposed changes must preserve the audit trail, identify impacted requirements and re-run dependent tests. Emergency responses may only exercise pre-existing, narrower authority.

Requirement groups: REQ-21-01, REQ-21-02, REQ-21-03, REQ-21-04, REQ-21-05, REQ-29-01, REQ-29-02, REQ-29-03, REQ-33-01, REQ-33-02, REQ-33-03.
