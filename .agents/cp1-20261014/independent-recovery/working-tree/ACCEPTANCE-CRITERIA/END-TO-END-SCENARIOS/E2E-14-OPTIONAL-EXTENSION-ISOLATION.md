# E2E-14-OPTIONAL-EXTENSION-ISOLATION

Scenario status: **SPECIFIED; NOT EXECUTED**. This document defines a future application qualification run, not a result from preparing the archive.

## Participating subsystems

[02-IDENTITY-AND-AUTHORITY](../../02-IDENTITY-AND-AUTHORITY/README.md), [06-AGENT-SKILLS-AND-LEARNING](../../06-AGENT-SKILLS-AND-LEARNING/README.md), [10-TOOLS-AND-CAPABILITIES](../../10-TOOLS-AND-CAPABILITIES/README.md), [11-EXECUTION-AND-ISOLATION](../../11-EXECUTION-AND-ISOLATION/README.md), [17-EVIDENCE-AND-PROVENANCE](../../17-EVIDENCE-AND-PROVENANCE/README.md), [18-SECURITY-AND-ENFORCEMENT](../../18-SECURITY-AND-ENFORCEMENT/README.md), [19-STATE-AND-RECOVERY](../../19-STATE-AND-RECOVERY/README.md), [21-EXTENSIONS-AND-INTEROPERABILITY](../../21-EXTENSIONS-AND-INTEROPERABILITY/README.md).

## Preconditions

A declarative native extension candidate, bounded test fixtures, and qualified isolation support.

Use isolated synthetic or owner-authorized data and targets. Pin the exact source, dependencies, configuration, policy, model and tool revisions, and target environment. Establish current authority and recovery points before consequential operations. The independent verifier receives the same exact candidate, not a later rebuild.

## End-to-end workflow

1. Inspect the manifest and dependencies.
2. Qualify in isolation.
3. Approve exact bytes.
4. Activate.
5. Invoke a scoped tool.
6. Update or revoke it..

## Required observable result

Installation does not grant ambient authority; code and manifest identity remain bound; revoked exports cannot start new work; local core operation does not depend on the extension.

## Fault and adverse variants

Hide a startup effect, mutate installed bytes, request unsupported isolation, and uninstall while preserving owner data.

Run each variant from a known baseline and record its precise injection point. Assert native state and actual effects, not only UI labels or worker return values. Preserve partial, cancelled, failed, blocked, and uncertain outcomes distinctly. Reconcile unknown effects before any replay and preserve known revocations and deletion decisions during recovery.

## Required evidence

Manifest, artifact digests, isolation qualification, approvals, invocation observations, and revocation or uninstall record.

For every run retain scenario ID, fixture revision, source manifest, target environment, exact inputs, action sequence, expected and actual observations, output artifact digests, timestamps and sequence context, safe logs, error records, and independent reviewer identity. A valid signature alone does not establish functional success; a screenshot alone does not establish control behavior.

## Pass and fail decision

Pass only when the primary oracle and every mandatory adverse variant satisfy their expected behavior on the exact candidate. A missing fixture, unavailable environment, skipped critical variant, stale source binding, or unresolved effect leaves the scenario blocked, not-executed, or uncertain rather than passed. Record which lower-level acceptance IDs were exercised and preserve any new regression test added from a failure.

## Cleanup and handoff

Stop owned workers, verify resource cleanup, remove only isolated test data according to the approved plan, and preserve evidence. Do not delete owner production data to simplify the environment. Hand the exact artifacts and results to the test coordinator and independent verifier for the applicable subsystem and product gates.
