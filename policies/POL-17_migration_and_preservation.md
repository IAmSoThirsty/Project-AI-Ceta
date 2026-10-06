# Migration, conservation and cutover

**Document ID:** POL-17  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Scope and controlling responsibilities

Enforcement owner: migration boundary + owner cutover decision. This policy derives from the ground-up master prompt sections 02, 31. It is a complete written implementation rule; source adoption, exact compiled policy bytes and runtime enforcement require the build gates.

## Rules

The rebuild MUST preserve original source history, dirty work, profiles and evidence. Development runs use isolated fixtures, not the owner's live profile. Historical paths and hashes are discovery leads; verified newer local work remains authoritative evidence of current implementation.

Migration creates a new genesis linked to a consistent legacy snapshot. Preserve original records, keys' verification status, unknown tables/columns/files, divergent archive versions and unresolved effects. Conversion receives its own identity and never claims that the new runtime performed historical actions. Old grants remain historical and readiness is measured again.

Normal-profile cutover requires quiescence, verified backup, rehearsal and applicable owner approval. Retire every competing live entry point, helper and authority issuer while preserving historical readers. Downgrade uses matching compatible data snapshots. Failed migration never activates a partial destination or erases the source.

## Enforcement and evidence

Implement predicates at the stated control boundary and add rejection fixtures for each forbidden path. Record the exact policy version, inputs, evaluated rule IDs and result. The policy's text is not itself an executable guard. Preserve both a legal case and a boundary-violation case in the source-bound verification bundle.

## Change and exception handling

A conflict with current adopted source law blocks the affected activation and is entered in the decision register. Do not invent an exception to obtain a passing test. Proposed changes must preserve the audit trail, identify impacted requirements and re-run dependent tests. Emergency responses may only exercise pre-existing, narrower authority.

Requirement groups: REQ-02-01, REQ-02-02, REQ-02-03, REQ-02-04, REQ-02-05, REQ-31-01, REQ-31-02, REQ-31-03, REQ-31-04, REQ-31-05.
