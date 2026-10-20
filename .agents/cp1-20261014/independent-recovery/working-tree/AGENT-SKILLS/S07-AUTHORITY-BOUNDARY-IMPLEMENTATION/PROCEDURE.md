# S07 procedure

## Goal

Use-time authorization checks with bounded delegation, replay protection, and revocation evidence.

## Domain-specific sequence

1. Bind actor, audience, proposal, inputs, target, expiry, and ancestry. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
2. Validate current revocation. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
3. Atomically consume single-use grants. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
4. Recheck target identity at effect time. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
5. Test concurrent and restored states. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.

## Integration and evidence

Apply the mapped local application's existing language, architecture, and qualified facilities. Keep one canonical owner for authority, state, evidence, and resource admission. Record expected versus observed outcomes at each consequential boundary. Use independent oracles rather than merely reproducing the implementation's assumptions. Preserve failed checks and unresolved effects for the receiver.

## Stop conditions

Stop the affected operation when authority expires, scope changes, source preconditions fail, required enforcement is unavailable, or evidence indicates an uncertain external effect. Inspect and reconcile before retrying. Do not erase data or weaken controls to make progress appear successful.

## Completion check

A stale or revoked capability cannot authorize effects through any supported entry path.

Before handoff, construct and evaluate the adverse fixture: A signature-valid token bypasses current revocation or target changes. The final report must identify the actual test state rather than implying a test ran because this procedure describes it.
