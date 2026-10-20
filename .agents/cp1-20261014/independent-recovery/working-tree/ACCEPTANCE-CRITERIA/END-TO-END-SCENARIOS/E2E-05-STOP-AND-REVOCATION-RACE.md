# E2E-05-STOP-AND-REVOCATION-RACE

Scenario status: **SPECIFIED; NOT EXECUTED**. This document defines a future application qualification run, not a result from preparing the archive.

## Participating subsystems

[02-IDENTITY-AND-AUTHORITY](../../02-IDENTITY-AND-AUTHORITY/README.md), [07-AGENT-ORCHESTRATION](../../07-AGENT-ORCHESTRATION/README.md), [08-TASK-AND-WORKFLOW-ENGINE](../../08-TASK-AND-WORKFLOW-ENGINE/README.md), [09-MODEL-RUNTIME](../../09-MODEL-RUNTIME/README.md), [10-TOOLS-AND-CAPABILITIES](../../10-TOOLS-AND-CAPABILITIES/README.md), [11-EXECUTION-AND-ISOLATION](../../11-EXECUTION-AND-ISOLATION/README.md), [17-EVIDENCE-AND-PROVENANCE](../../17-EVIDENCE-AND-PROVENANCE/README.md), [20-RESOURCE-MANAGEMENT](../../20-RESOURCE-MANAGEMENT/README.md), [22-DESKTOP-AND-USER-EXPERIENCE](../../22-DESKTOP-AND-USER-EXPERIENCE/README.md).

## Preconditions

An authorized long-running task with child workers, a queued effect, and observable native process ownership.

Use isolated synthetic or owner-authorized data and targets. Pin the exact source, dependencies, configuration, policy, model and tool revisions, and target environment. Establish current authority and recovery points before consequential operations. The independent verifier receives the same exact candidate, not a later rebuild.

## End-to-end workflow

1. Start work.
2. Issue owner stop or revoke the parent grant while another effect is pending.
3. Observe admission closure, termination, and final state..

## Required observable result

No new unauthorized effect starts after the effective boundary; owned workers stop or are explicitly reported residual; committed and uncertain effects remain distinct.

## Fault and adverse variants

Saturate resource queues, reuse a process identifier, lose one stop acknowledgement, and race capability validation with revocation.

Run each variant from a known baseline and record its precise injection point. Assert native state and actual effects, not only UI labels or worker return values. Preserve partial, cancelled, failed, blocked, and uncertain outcomes distinctly. Reconcile unknown effects before any replay and preserve known revocations and deletion decisions during recovery.

## Required evidence

Stop generation, revocation record, gate checks, process observations, effect ledger, and cancellation receipt.

For every run retain scenario ID, fixture revision, source manifest, target environment, exact inputs, action sequence, expected and actual observations, output artifact digests, timestamps and sequence context, safe logs, error records, and independent reviewer identity. A valid signature alone does not establish functional success; a screenshot alone does not establish control behavior.

## Pass and fail decision

Pass only when the primary oracle and every mandatory adverse variant satisfy their expected behavior on the exact candidate. A missing fixture, unavailable environment, skipped critical variant, stale source binding, or unresolved effect leaves the scenario blocked, not-executed, or uncertain rather than passed. Record which lower-level acceptance IDs were exercised and preserve any new regression test added from a failure.

## Cleanup and handoff

Stop owned workers, verify resource cleanup, remove only isolated test data according to the approved plan, and preserve evidence. Do not delete owner production data to simplify the environment. Hand the exact artifacts and results to the test coordinator and independent verifier for the applicable subsystem and product gates.
