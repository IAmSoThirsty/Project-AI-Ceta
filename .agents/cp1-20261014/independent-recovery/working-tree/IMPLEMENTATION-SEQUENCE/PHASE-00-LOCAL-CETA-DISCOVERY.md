# Phase 00-LOCAL-CETA-DISCOVERY

## Goal

Inspect the actual owner-selected local application without modifying it.

## Required work

Capture source roots and digests, languages, entry points, processes, data stores, policy sources, identity, models, tools, UI, tests, packaging, and recovery. Mark inaccessible information explicitly.

## Participating subsystems

[00-MASTER-ARCHITECTURE](../00-MASTER-ARCHITECTURE/README.md), [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md), [24-BUILD-AND-RELEASE](../24-BUILD-AND-RELEASE/README.md).

## Execution discipline

Follow [the prerequisite waves](../DEPENDENCY-MAPS/BUILD-ORDER-GRAPH.md) and the per-file build instructions. Shared contracts and fixtures precede dependent implementation. Acquire exact source ownership, preserve the local baseline, and keep effectful work within current permission. Parallelize only disjoint tasks. Record every implementation and compatibility decision with its source evidence.

## Verification and handoff

Run the applicable positive, negative, stale-input, concurrency, cancellation, recovery, and real integration tests. Preserve actual execution records and artifact identities. Independent review inspects the delivered revision rather than trusting a builder summary. Failed or not-executed mandatory checks remain open and are carried into the next handoff explicitly.

## Exit criterion

A source-hashed baseline and existing acceptance inventory exist; no remote layout is assumed.

The phase's documentation does not assert that this work has already occurred. During construction, record the actual local results and any owner-approved scope decisions in the traceability and integration registers.
