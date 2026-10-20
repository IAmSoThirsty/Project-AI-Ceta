# E2E-01-OWNER-SETUP-AND-LOCAL-STARTUP

Scenario status: **SPECIFIED; NOT EXECUTED**. This document defines a future application qualification run, not a result from preparing the archive.

## Participating subsystems

[00-MASTER-ARCHITECTURE](../../00-MASTER-ARCHITECTURE/README.md), [01-CONSTITUTIONAL-GOVERNANCE](../../01-CONSTITUTIONAL-GOVERNANCE/README.md), [02-IDENTITY-AND-AUTHORITY](../../02-IDENTITY-AND-AUTHORITY/README.md), [09-MODEL-RUNTIME](../../09-MODEL-RUNTIME/README.md), [18-SECURITY-AND-ENFORCEMENT](../../18-SECURITY-AND-ENFORCEMENT/README.md), [19-STATE-AND-RECOVERY](../../19-STATE-AND-RECOVERY/README.md), [20-RESOURCE-MANAGEMENT](../../20-RESOURCE-MANAGEMENT/README.md), [22-DESKTOP-AND-USER-EXPERIENCE](../../22-DESKTOP-AND-USER-EXPERIENCE/README.md).

## Preconditions

A clean local installation and an owner-selected data root with no existing enrollment.

Use isolated synthetic or owner-authorized data and targets. Pin the exact source, dependencies, configuration, policy, model and tool revisions, and target environment. Establish current authority and recovery points before consequential operations. The independent verifier receives the same exact candidate, not a later rebuild.

## End-to-end workflow

1. Complete verified owner enrollment.
2. Configure recovery and local privacy.
3. Qualify an available local model.
4. Reach normal readiness.
5. Stop and restart..

## Required observable result

Only the verified owner obtains the configured authority; local data, identity, and setup state persist; no general effects occur before prerequisites are ready.

## Fault and adverse variants

Race two enrollment attempts, interrupt setup, remove trust material, and deny network access.

Run each variant from a known baseline and record its precise injection point. Assert native state and actual effects, not only UI labels or worker return values. Preserve partial, cancelled, failed, blocked, and uncertain outcomes distinctly. Reconcile unknown effects before any replay and preserve known revocations and deletion decisions during recovery.

## Required evidence

Ownership record, process binding, startup readiness, model qualification, preserved data, and restricted-state observations.

For every run retain scenario ID, fixture revision, source manifest, target environment, exact inputs, action sequence, expected and actual observations, output artifact digests, timestamps and sequence context, safe logs, error records, and independent reviewer identity. A valid signature alone does not establish functional success; a screenshot alone does not establish control behavior.

## Pass and fail decision

Pass only when the primary oracle and every mandatory adverse variant satisfy their expected behavior on the exact candidate. A missing fixture, unavailable environment, skipped critical variant, stale source binding, or unresolved effect leaves the scenario blocked, not-executed, or uncertain rather than passed. Record which lower-level acceptance IDs were exercised and preserve any new regression test added from a failure.

## Cleanup and handoff

Stop owned workers, verify resource cleanup, remove only isolated test data according to the approved plan, and preserve evidence. Do not delete owner production data to simplify the environment. Hand the exact artifacts and results to the test coordinator and independent verifier for the applicable subsystem and product gates.
