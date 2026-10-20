# S05 procedure

## Goal

Typed build, runtime, data, and optional dependency maps with affected-owner and test impact.

## Domain-specific sequence

1. Classify each edge. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
2. Detect build cycles. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
3. Identify runtime cycles that require ports. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
4. Compute affected consumers. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
5. Validate bootstrap and shutdown order. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
6. Keep optional features from entering the required local path. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.

## Integration and evidence

Apply the mapped local application's existing language, architecture, and qualified facilities. Keep one canonical owner for authority, state, evidence, and resource admission. Record expected versus observed outcomes at each consequential boundary. Use independent oracles rather than merely reproducing the implementation's assumptions. Preserve failed checks and unresolved effects for the receiver.

## Stop conditions

Stop the affected operation when authority expires, scope changes, source preconditions fail, required enforcement is unavailable, or evidence indicates an uncertain external effect. Inspect and reconcile before retrying. Do not erase data or weaken controls to make progress appear successful.

## Completion check

The construction graph is acyclic and every affected contract consumer is accounted for.

Before handoff, construct and evaluate the adverse fixture: A runtime message loop is incorrectly treated as a mandatory build-order cycle. The final report must identify the actual test state rather than implying a test ran because this procedure describes it.
