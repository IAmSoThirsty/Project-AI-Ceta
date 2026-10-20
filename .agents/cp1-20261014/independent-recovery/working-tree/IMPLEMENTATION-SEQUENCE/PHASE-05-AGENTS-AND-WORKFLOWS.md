# Phase 05-AGENTS-AND-WORKFLOWS

## Goal

Construct durable task graphs, native skills, bounded agents, and companion task coordination.

## Required work

Implement checkpoints, safe retries, handoffs, write leases, skill qualification, independent review, and current-authority renewal. Build the minimal native shell interfaces needed by subsequent workspace integration.

## Participating subsystems

[03-COMPANION-INTELLIGENCE](../03-COMPANION-INTELLIGENCE/README.md), [06-AGENT-SKILLS-AND-LEARNING](../06-AGENT-SKILLS-AND-LEARNING/README.md), [07-AGENT-ORCHESTRATION](../07-AGENT-ORCHESTRATION/README.md), [08-TASK-AND-WORKFLOW-ENGINE](../08-TASK-AND-WORKFLOW-ENGINE/README.md), [22-DESKTOP-AND-USER-EXPERIENCE](../22-DESKTOP-AND-USER-EXPERIENCE/README.md).

## Execution discipline

Follow [the prerequisite waves](../DEPENDENCY-MAPS/BUILD-ORDER-GRAPH.md) and the per-file build instructions. Shared contracts and fixtures precede dependent implementation. Acquire exact source ownership, preserve the local baseline, and keep effectful work within current permission. Parallelize only disjoint tasks. Record every implementation and compatibility decision with its source evidence.

## Verification and handoff

Run the applicable positive, negative, stale-input, concurrency, cancellation, recovery, and real integration tests. Preserve actual execution records and artifact identities. Independent review inspects the delivered revision rather than trusting a builder summary. Failed or not-executed mandatory checks remain open and are carried into the next handoff explicitly.

## Exit criterion

Multi-step work resumes safely, preserves uncertainty, and produces evidence-backed outcomes.

The phase's documentation does not assert that this work has already occurred. During construction, record the actual local results and any owner-approved scope decisions in the traceability and integration registers.
