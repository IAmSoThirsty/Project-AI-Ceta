# Phase 02-CORE-CONTRACTS-AND-STATE

## Goal

Establish canonical declarations, fixtures, durable state, protected trust, and minimum evidence.

## Required work

Implement storage and expected-version rules; define shared contracts; establish bounded bootstrap authority, key handling, evidence journal, resource reserves, and initial test harnesses.

## Participating subsystems

[00-MASTER-ARCHITECTURE](../00-MASTER-ARCHITECTURE/README.md), [18-SECURITY-AND-ENFORCEMENT](../18-SECURITY-AND-ENFORCEMENT/README.md), [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md), [20-RESOURCE-MANAGEMENT](../20-RESOURCE-MANAGEMENT/README.md), [17-EVIDENCE-AND-PROVENANCE](../17-EVIDENCE-AND-PROVENANCE/README.md), [23-TESTING-AND-QUALIFICATION](../23-TESTING-AND-QUALIFICATION/README.md).

## Execution discipline

Follow [the prerequisite waves](../DEPENDENCY-MAPS/BUILD-ORDER-GRAPH.md) and the per-file build instructions. Shared contracts and fixtures precede dependent implementation. Acquire exact source ownership, preserve the local baseline, and keep effectful work within current permission. Parallelize only disjoint tasks. Record every implementation and compatibility decision with its source evidence.

## Verification and handoff

Run the applicable positive, negative, stale-input, concurrency, cancellation, recovery, and real integration tests. Preserve actual execution records and artifact identities. Independent review inspects the delivered revision rather than trusting a builder summary. Failed or not-executed mandatory checks remain open and are carried into the next handoff explicitly.

## Exit criterion

Foundation interfaces and crash-consistency checks are usable without opening general worker effects.

The phase's documentation does not assert that this work has already occurred. During construction, record the actual local results and any owner-approved scope decisions in the traceability and integration registers.
