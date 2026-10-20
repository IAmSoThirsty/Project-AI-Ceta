# S17 procedure

## Goal

Reproducible interruption evidence and validated safe resume, compensation, or uncertainty handling.

## Domain-specific sequence

1. Inject faults before and after intent, dispatch, effect, commit, and publication. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
2. Restart. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
3. Inspect actual resources. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
4. Revalidate authority. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
5. Reconcile unknowns. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
6. Verify no blind replay or lost user data. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.

## Integration and evidence

Apply the mapped local application's existing language, architecture, and qualified facilities. Keep one canonical owner for authority, state, evidence, and resource admission. Record expected versus observed outcomes at each consequential boundary. Use independent oracles rather than merely reproducing the implementation's assumptions. Preserve failed checks and unresolved effects for the receiver.

## Stop conditions

Stop the affected operation when authority expires, scope changes, source preconditions fail, required enforcement is unavailable, or evidence indicates an uncertain external effect. Inspect and reconcile before retrying. Do not erase data or weaken controls to make progress appear successful.

## Completion check

Every fault point yields the documented durable state and preserves already committed effects.

Before handoff, construct and evaluate the adverse fixture: A timeout is assumed to prove no external action occurred. The final report must identify the actual test state rather than implying a test ran because this procedure describes it.
