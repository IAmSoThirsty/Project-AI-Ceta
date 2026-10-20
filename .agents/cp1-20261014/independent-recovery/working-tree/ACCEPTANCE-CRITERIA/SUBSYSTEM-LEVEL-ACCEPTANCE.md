# Subsystem Level Acceptance

## Required outcome

Each of the 25 subsystems must satisfy its mission, invariant, file coverage, and integrated behavior.

## Procedure

Use the subsystem ACCEPTANCE and TEST-MATRIX documents. Preserve existing local requirements, qualify canonical contracts, and obtain distinct reviewer evidence.

## Evidence requirements

Record exact requirement and test identities, source and artifact digests, dependency and configuration revisions, target environment, fixture data, actual procedures, raw observations, error and recovery records, and reviewer identity. The observation must support the specific claim. Preserve source integrity, functional behavior, observation completeness, and independent review as separate checks.

## Gate states

Use passed, failed, blocked, skipped, not-executed, and uncertain. A mandatory obligation is satisfied only by a current accepted pass. A high aggregate percentage cannot compensate for a critical failed boundary. A generated test specification is not a test execution. A build success is not installed-product acceptance.

## Change and requalification

Any relevant source, policy, authority, schema, model, dependency, runtime, configuration, or package change invalidates affected evidence. Identify impacted consumers and tests through the dependency maps. Preserve existing local acceptance intent and record explicit owner decisions for scope changes. Independent verification inspects the exact candidate under review.

## Handoff

Supply the test coordinator with a complete result ledger and evidence manifest. Retain failed reproductions and unresolved effects. The release gate consumes accepted current results rather than a narrative summary. Initial execution state in this construction package is NOT EXECUTED.
