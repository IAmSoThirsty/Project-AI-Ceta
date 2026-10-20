# E2E-03-GOVERNED-LOCAL-ENGINEERING-CHANGE

Scenario status: **SPECIFIED; NOT EXECUTED**. This document defines a future application qualification run, not a result from preparing the archive.

## Participating subsystems

[01-CONSTITUTIONAL-GOVERNANCE](../../01-CONSTITUTIONAL-GOVERNANCE/README.md), [02-IDENTITY-AND-AUTHORITY](../../02-IDENTITY-AND-AUTHORITY/README.md), [07-AGENT-ORCHESTRATION](../../07-AGENT-ORCHESTRATION/README.md), [08-TASK-AND-WORKFLOW-ENGINE](../../08-TASK-AND-WORKFLOW-ENGINE/README.md), [10-TOOLS-AND-CAPABILITIES](../../10-TOOLS-AND-CAPABILITIES/README.md), [11-EXECUTION-AND-ISOLATION](../../11-EXECUTION-AND-ISOLATION/README.md), [12-ENGINEERING-INTELLIGENCE](../../12-ENGINEERING-INTELLIGENCE/README.md), [13-NATIVE-DEVELOPMENT-WORKSPACE](../../13-NATIVE-DEVELOPMENT-WORKSPACE/README.md), [17-EVIDENCE-AND-PROVENANCE](../../17-EVIDENCE-AND-PROVENANCE/README.md), [19-STATE-AND-RECOVERY](../../19-STATE-AND-RECOVERY/README.md), [22-DESKTOP-AND-USER-EXPERIENCE](../../22-DESKTOP-AND-USER-EXPERIENCE/README.md).

## Preconditions

A local project with inspected source, baseline tests, an isolated edit target, and no remote repository requirement.

Use isolated synthetic or owner-authorized data and targets. Pin the exact source, dependencies, configuration, policy, model and tool revisions, and target environment. Establish current authority and recovery points before consequential operations. The independent verifier receives the same exact candidate, not a later rebuild.

## End-to-end workflow

1. Request a bounded feature change.
2. Inspect the plan and exact diff.
3. Approve the proposal.
4. Apply edits through governed tools.
5. Run tests.
6. Independently verify the artifact..

## Required observable result

Only approved files and effects change; existing owner edits are preserved; source, tests, artifacts, and evidence identify the same revision.

## Fault and adverse variants

Modify the target after review, deny approval, inject an extra tool argument, and change a shared contract mid-task.

Run each variant from a known baseline and record its precise injection point. Assert native state and actual effects, not only UI labels or worker return values. Preserve partial, cancelled, failed, blocked, and uncertain outcomes distinctly. Reconcile unknown effects before any replay and preserve known revocations and deletion decisions during recovery.

## Required evidence

Before and after source digests, exact proposal, capability, gate decision, observed writes, tests, and independent review.

For every run retain scenario ID, fixture revision, source manifest, target environment, exact inputs, action sequence, expected and actual observations, output artifact digests, timestamps and sequence context, safe logs, error records, and independent reviewer identity. A valid signature alone does not establish functional success; a screenshot alone does not establish control behavior.

## Pass and fail decision

Pass only when the primary oracle and every mandatory adverse variant satisfy their expected behavior on the exact candidate. A missing fixture, unavailable environment, skipped critical variant, stale source binding, or unresolved effect leaves the scenario blocked, not-executed, or uncertain rather than passed. Record which lower-level acceptance IDs were exercised and preserve any new regression test added from a failure.

## Cleanup and handoff

Stop owned workers, verify resource cleanup, remove only isolated test data according to the approved plan, and preserve evidence. Do not delete owner production data to simplify the environment. Hand the exact artifacts and results to the test coordinator and independent verifier for the applicable subsystem and product gates.
