# State, consistency and transaction model

**Document ID:** ARCH-03  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Authoritative data

Use one protected local transactional store as the initial desktop persistence mechanism, with logical per-project and installation streams. The writer serializes kernel-authorized commands. Events, authority mutations, reservations, operation intents and corresponding projections commit together where they must agree. The application does not hold a transaction while waiting for a model, a human decision or an external process.

Each event binds scope, sequence, event type, schema, actor/session, causation, recorded time, prior committed head and a payload commitment. Sensitive payloads may be separately protected rather than copied into append-only plaintext. The signature or final event hash is excluded from its own preimage. Read sets bind only relevant authority/resource revisions so unrelated telemetry does not invalidate every active proposal.

## Proposed baseline storage policy

Use SQLite on a supported local filesystem with explicit synchronization, foreign-key enforcement, busy-timeout, checkpoint and backup settings. For authority-critical transactions the initial durability target requires FULL synchronization or an independently justified equivalent. Record the library actually loaded by the packaged binary and current advisories before qualification. WAL and its companion files are part of consistent recovery; do not copy a live database file in isolation and call it a verified backup.

The selected locking and writer design must be exercised against crashes, concurrent readers, competing instances and disk pressure. Journaling configuration is an engineering baseline awaiting the installed workload evidence. Primary references are in `sources/engineering_references.md`.

## Event versus projection

Tasks, graph readiness, active grants, current claims and UI views are derived under their specified canonical owner. Rebuild projections only from accepted records. A complete locally rewritten history may pass local hashes if the attacker controls the entire anchor; state the trust profile. Independent witnesses or hardware monotonic roots improve rollback evidence only where actually deployed and measured.

Successful hash memoization may reuse only verified immutable input bytes. A file timestamp, database modification counter or unchanged current head does not prove a historical prefix. Cache keys include security-relevant content and generations, and revocation/correction invalidates dependent results. Stop and integrity handling retain resource reserves when caches or queues are full.

## Transactional effect protocol

Reserve the budget, prepare an exact permit and commit an operation intent before any external dispatch. The broker then redeems the permit through the kernel-owned consume operation, with current peer identity, fence, resource handles and relevant revisions. Durable consumption and effect-admission evidence precede mutation. Failure between consumption and effect may burn a permit; safety never depends on reviving it.

An arbitrary filesystem or remote effect cannot be rolled back by a database transaction. Post-effect receipt loss becomes `INDETERMINATE`, followed by readback or receiver-side idempotency evidence. Replay reconstructs history without effects. Compensation receives a fresh permit against the latest state. A matching current file proves a current state; causal attribution needs separate evidence.

## Required tests

B009-B016, B057-B064 and B097-B104 establish the minimum storage/admission/reconciliation coverage. Add source-derived malformed event, prefix, witness, signature, power-loss and migration cases. Retain failed first runs and changed-source invalidations alongside corrected results.
