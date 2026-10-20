# S09 procedure

## Goal

Durable local records, atomic publication intent, integrity checks, and tested restoration.

## Domain-specific sequence

1. Define authoritative versus derived stores. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
2. Choose explicit commit boundaries. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
3. Handle disk-full and corruption. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
4. Coordinate durable event publication. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
5. Test crash points. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.
6. Verify backup restoration and deletion propagation. For this step, preserve the exact input references, decision rationale, and output evidence required by the assigned unit.

## Integration and evidence

Apply the mapped local application's existing language, architecture, and qualified facilities. Keep one canonical owner for authority, state, evidence, and resource admission. Record expected versus observed outcomes at each consequential boundary. Use independent oracles rather than merely reproducing the implementation's assumptions. Preserve failed checks and unresolved effects for the receiver.

## Stop conditions

Stop the affected operation when authority expires, scope changes, source preconditions fail, required enforcement is unavailable, or evidence indicates an uncertain external effect. Inspect and reconcile before retrying. Do not erase data or weaken controls to make progress appear successful.

## Completion check

Each injected crash yields a documented prior, committed, or explicitly uncertain state without silent data loss.

Before handoff, construct and evaluate the adverse fixture: An in-memory success acknowledgement precedes durable commit. The final report must identify the actual test state rather than implying a test ran because this procedure describes it.
