# Phase 09-PRODUCT-DELIVERY

## Goal

Build and deliver the exact qualified installed product.

## Required work

Bind source to build and package; verify integrity and configured signing; test clean install, update, repair, rollback, offline use, and complete owner workflows on qualified targets.

## Participating subsystems

[23-TESTING-AND-QUALIFICATION](../23-TESTING-AND-QUALIFICATION/README.md), [24-BUILD-AND-RELEASE](../24-BUILD-AND-RELEASE/README.md).

## Execution discipline

Follow [the prerequisite waves](../DEPENDENCY-MAPS/BUILD-ORDER-GRAPH.md) and the per-file build instructions. Shared contracts and fixtures precede dependent implementation. Acquire exact source ownership, preserve the local baseline, and keep effectful work within current permission. Parallelize only disjoint tasks. Record every implementation and compatibility decision with its source evidence.

## Verification and handoff

Run the applicable positive, negative, stale-input, concurrency, cancellation, recovery, and real integration tests. Preserve actual execution records and artifact identities. Independent review inspects the delivered revision rather than trusting a builder summary. Failed or not-executed mandatory checks remain open and are carried into the next handoff explicitly.

## Exit criterion

The delivered artifact is the exact install-tested candidate and the release decision is evidence-backed.

The phase's documentation does not assert that this work has already occurred. During construction, record the actual local results and any owner-approved scope decisions in the traceability and integration registers.
