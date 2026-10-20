# S02 procedure

## Goal

A requirement-to-unit map with measurable outputs, dependency edges, and acceptance oracles.

## Domain-specific sequence

1. Preserve exact requirements. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
2. Split compound goals into testable behaviors. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
3. Identify authority and data consequences. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
4. Assign one owner. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
5. Define completion evidence. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
6. Retain ambiguities as explicit decisions. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.

## Integration and evidence

Apply the mapped local application's existing language, architecture, and qualified facilities. Keep one canonical owner for authority, state, evidence, and resource admission. Record expected versus observed outcomes at each consequential boundary. Use independent oracles rather than merely reproducing the implementation's assumptions. Preserve failed checks and unresolved effects for the receiver.

## Stop conditions

Stop the affected operation when authority expires, scope changes, source preconditions fail, required enforcement is unavailable, or evidence indicates an uncertain external effect. Inspect and reconcile before retrying. Do not erase data or weaken controls to make progress appear successful.

## Completion check

No approved requirement is orphaned, silently narrowed, or replaced by a vague completion label.

Before handoff, construct and evaluate the adverse fixture: A difficult requirement is dropped to make the plan appear complete. The final report must identify the actual test state rather than implying a test ran because this procedure describes it.
