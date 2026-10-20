# Phase 04-INTELLIGENCE-FOUNDATIONS

## Goal

Qualify local models, memory, context, and source handling.

## Required work

Implement model lifecycle and measured admission; preserve attributed memory and exact context; qualify local inference, cancellation, privacy, source extraction, and rebuildable indexes.

## Participating subsystems

[04-PERSISTENT-MEMORY](../04-PERSISTENT-MEMORY/README.md), [05-CONTEXT-INTELLIGENCE](../05-CONTEXT-INTELLIGENCE/README.md), [09-MODEL-RUNTIME](../09-MODEL-RUNTIME/README.md), [16-KNOWLEDGE-AND-RESEARCH](../16-KNOWLEDGE-AND-RESEARCH/README.md), [20-RESOURCE-MANAGEMENT](../20-RESOURCE-MANAGEMENT/README.md).

## Execution discipline

Follow [the prerequisite waves](../DEPENDENCY-MAPS/BUILD-ORDER-GRAPH.md) and the per-file build instructions. Shared contracts and fixtures precede dependent implementation. Acquire exact source ownership, preserve the local baseline, and keep effectful work within current permission. Parallelize only disjoint tasks. Record every implementation and compatibility decision with its source evidence.

## Verification and handoff

Run the applicable positive, negative, stale-input, concurrency, cancellation, recovery, and real integration tests. Preserve actual execution records and artifact identities. Independent review inspects the delivered revision rather than trusting a builder summary. Failed or not-executed mandatory checks remain open and are carried into the next handoff explicitly.

## Exit criterion

Local intelligence works within measured resource limits and cannot promote retrieved content into authority.

The phase's documentation does not assert that this work has already occurred. During construction, record the actual local results and any owner-approved scope decisions in the traceability and integration registers.
