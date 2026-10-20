# S08 procedure

## Goal

A validated state machine with atomic transitions, causal records, and terminal-state rules.

## Domain-specific sequence

1. Enumerate legal states. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
2. Define guards and effects. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
3. Use expected-version updates. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
4. Record transition causes. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
5. Define cancellation and uncertainty. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
6. Replay committed history to verify consistency. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.

## Integration and evidence

Apply the mapped local application's existing language, architecture, and qualified facilities. Keep one canonical owner for authority, state, evidence, and resource admission. Record expected versus observed outcomes at each consequential boundary. Use independent oracles rather than merely reproducing the implementation's assumptions. Preserve failed checks and unresolved effects for the receiver.

## Stop conditions

Stop the affected operation when authority expires, scope changes, source preconditions fail, required enforcement is unavailable, or evidence indicates an uncertain external effect. Inspect and reconcile before retrying. Do not erase data or weaken controls to make progress appear successful.

## Completion check

Conflicting updates cannot both commit and terminal states cannot be bypassed.

Before handoff, construct and evaluate the adverse fixture: A restarted worker overwrites a newer stop or revocation state. The final report must identify the actual test state rather than implying a test ran because this procedure describes it.
