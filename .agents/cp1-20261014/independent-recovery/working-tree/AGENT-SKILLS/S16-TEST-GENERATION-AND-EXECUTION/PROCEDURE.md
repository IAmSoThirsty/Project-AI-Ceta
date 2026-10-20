# S16 procedure

## Goal

Executed source-bound tests with independent oracles and explicit pass, fail, blocked, skipped, or not-executed states.

## Domain-specific sequence

1. Derive positive and negative cases. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
2. Reproduce original defects. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
3. Isolate fixtures. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
4. Run unit and real integration paths. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
5. Capture commands, environment, logs, and artifacts. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
6. Preserve every failed or omitted obligation. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.

## Integration and evidence

Apply the mapped local application's existing language, architecture, and qualified facilities. Keep one canonical owner for authority, state, evidence, and resource admission. Record expected versus observed outcomes at each consequential boundary. Use independent oracles rather than merely reproducing the implementation's assumptions. Preserve failed checks and unresolved effects for the receiver.

## Stop conditions

Stop the affected operation when authority expires, scope changes, source preconditions fail, required enforcement is unavailable, or evidence indicates an uncertain external effect. Inspect and reconcile before retrying. Do not erase data or weaken controls to make progress appear successful.

## Completion check

A test fails on the known defect and observes the required corrected behavior.

Before handoff, construct and evaluate the adverse fixture: Generated tests merely restate the implementation or are reported passed without execution. The final report must identify the actual test state rather than implying a test ran because this procedure describes it.
