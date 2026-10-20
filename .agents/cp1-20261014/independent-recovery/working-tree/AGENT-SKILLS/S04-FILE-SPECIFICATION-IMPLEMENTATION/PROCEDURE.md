# S04 procedure

## Goal

A focused local implementation change with tests, documentation, and source-bound evidence.

## Domain-specific sequence

1. Read the unit and component contracts. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
2. Inspect the existing target. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
3. Choose reuse or extension first. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
4. Implement complete behavior and failure paths. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
5. Run unit and integration checks. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
6. Hand off exact artifacts for independent review. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.

## Integration and evidence

Apply the mapped local application's existing language, architecture, and qualified facilities. Keep one canonical owner for authority, state, evidence, and resource admission. Record expected versus observed outcomes at each consequential boundary. Use independent oracles rather than merely reproducing the implementation's assumptions. Preserve failed checks and unresolved effects for the receiver.

## Stop conditions

Stop the affected operation when authority expires, scope changes, source preconditions fail, required enforcement is unavailable, or evidence indicates an uncertain external effect. Inspect and reconcile before retrying. Do not erase data or weaken controls to make progress appear successful.

## Completion check

The resulting file satisfies its positive, negative, recovery, and contract obligations without unrelated edits.

Before handoff, construct and evaluate the adverse fixture: A stub or superficial wrapper is presented as end-to-end implementation. The final report must identify the actual test state rather than implying a test ran because this procedure describes it.
