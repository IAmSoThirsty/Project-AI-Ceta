# S12 procedure

## Goal

Bounded multi-agent execution with fenced ownership, durable handoffs, and separate review.

## Domain-specific sequence

1. Decompose outputs. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
2. Pin roles and skills. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
3. Acquire write leases. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
4. Persist assignments. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
5. Validate messages and handoffs. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
6. Reconcile worker loss. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
7. Require evidence-backed finalization. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.

## Integration and evidence

Apply the mapped local application's existing language, architecture, and qualified facilities. Keep one canonical owner for authority, state, evidence, and resource admission. Record expected versus observed outcomes at each consequential boundary. Use independent oracles rather than merely reproducing the implementation's assumptions. Preserve failed checks and unresolved effects for the receiver.

## Stop conditions

Stop the affected operation when authority expires, scope changes, source preconditions fail, required enforcement is unavailable, or evidence indicates an uncertain external effect. Inspect and reconcile before retrying. Do not erase data or weaken controls to make progress appear successful.

## Completion check

Duplicate deliveries and stale workers cannot produce conflicting canonical effects.

Before handoff, construct and evaluate the adverse fixture: A producer agent self-certifies its deliverable as independently verified. The final report must identify the actual test state rather than implying a test ran because this procedure describes it.
