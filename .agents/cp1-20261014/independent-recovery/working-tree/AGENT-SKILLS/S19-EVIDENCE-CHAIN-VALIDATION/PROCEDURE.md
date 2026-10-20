# S19 procedure

## Goal

A verification result separating integrity, attribution, completeness, observed behavior, and unresolved gaps.

## Domain-specific sequence

1. Resolve every reference. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
2. Hash actual bytes. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
3. Verify signatures and trust. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
4. Check causal order and source revision. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
5. Inspect observation coverage. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
6. Detect stale tests and truncation limits. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
7. Report unsupported claims. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.

## Integration and evidence

Apply the mapped local application's existing language, architecture, and qualified facilities. Keep one canonical owner for authority, state, evidence, and resource admission. Record expected versus observed outcomes at each consequential boundary. Use independent oracles rather than merely reproducing the implementation's assumptions. Preserve failed checks and unresolved effects for the receiver.

## Stop conditions

Stop the affected operation when authority expires, scope changes, source preconditions fail, required enforcement is unavailable, or evidence indicates an uncertain external effect. Inspect and reconcile before retrying. Do not erase data or weaken controls to make progress appear successful.

## Completion check

Every accepted claim is tied to current admissible evidence and every gap remains visible.

Before handoff, construct and evaluate the adverse fixture: A valid signature is mistaken for proof of successful behavior or factual truth. The final report must identify the actual test state rather than implying a test ran because this procedure describes it.
