# 22-DESKTOP-AND-USER-EXPERIENCE - acceptance gate

Gate ID: `GATE-SUBSYSTEM-22`. Initial runtime state: **NOT EXECUTED**.

## Required outcome

Provide an accessible native application shell, command center, owner controls, decision surfaces, evidence inspection, onboarding, and maintenance.

## Non-negotiable invariant

Visual state is derived from authenticated native state. A disabled button is not a security boundary; every command is validated again by the runtime.

## Gate criteria

1. All 27 logical implementation units are mapped to actual local source paths with explicit reuse, extension, or creation decisions.
2. Every component implements its complete declared flow and every source file satisfies its specific positive and negative oracle.
3. Canonical producer-consumer contracts pass valid, denied, stale, malformed, partial, and uncertain-outcome tests.
4. Authority, state ownership, resource admission, evidence, and native UI boundaries use their designated owners without hidden bypasses.
5. Concurrency, cancellation, interruption, recovery, and data-preservation behavior are observed under controlled adverse fixtures.
6. Existing local behavior and acceptance obligations remain satisfied or have an explicitly approved replacement decision.
7. A distinct verifier reproduces critical checks against the delivered source and artifacts.
8. Documentation, integration records, test results, and evidence refer to the same accepted revision.

## Required evidence

Provide a source manifest, mapped path register, contract revisions, test fixtures, actual execution records, output artifact digests, failure and recovery observations, independent review, and unresolved-obligation ledger. A mandatory blocked, failed, skipped, or not-executed case keeps the gate open. Design-document validation is a separate package check and never satisfies this runtime gate.

## Integration exit

The integration engineer accepts the real cross-subsystem path and the release engineer carries this gate's exact evidence into product qualification. Any relevant source, contract, policy, dependency, or environment change invalidates the affected evidence and requires targeted requalification.
