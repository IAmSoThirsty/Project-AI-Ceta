# S03 procedure

## Goal

A versioned interface decision with fields, invariants, errors, state semantics, and shared test fixtures.

## Domain-specific sequence

1. Define exact records and type constraints. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
2. Assign mutation ownership. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
3. Specify success, failure, partial, and uncertain outcomes. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
4. Define compatibility and versioning. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
5. Obtain affected-owner review before implementation. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.

## Integration and evidence

Apply the mapped local application's existing language, architecture, and qualified facilities. Keep one canonical owner for authority, state, evidence, and resource admission. Record expected versus observed outcomes at each consequential boundary. Use independent oracles rather than merely reproducing the implementation's assumptions. Preserve failed checks and unresolved effects for the receiver.

## Stop conditions

Stop the affected operation when authority expires, scope changes, source preconditions fail, required enforcement is unavailable, or evidence indicates an uncertain external effect. Inspect and reconcile before retrying. Do not erase data or weaken controls to make progress appear successful.

## Completion check

Producer and consumer conformance fixtures exercise identical semantics, including denial and uncertainty.

Before handoff, construct and evaluate the adverse fixture: A consumer privately widens a security-critical field or assumes unknown states mean success. The final report must identify the actual test state rather than implying a test ran because this procedure describes it.
