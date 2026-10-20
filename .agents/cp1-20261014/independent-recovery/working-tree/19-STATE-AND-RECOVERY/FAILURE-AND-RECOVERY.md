# 19-STATE-AND-RECOVERY - failure and recovery

## Domain-specific failure fixtures

| Unit | Adverse condition that must be handled |
| --- | --- |
| [CETA-19.01.01 / state-record-registry](19.01-STATE-REGISTER/state-record-registry.file.README.md) | Two subsystems independently maintain conflicting authoritative task states. |
| [CETA-19.01.02 / state-transition-validator](19.01-STATE-REGISTER/state-transition-validator.file.README.md) | A stale worker overwrites a newer cancellation state. |
| [CETA-19.01.03 / state-history-controller](19.01-STATE-REGISTER/state-history-controller.file.README.md) | A later correction deletes the original observed failure from history. |
| [CETA-19.02.01 / transactional-storage-controller](19.02-DURABLE-STORAGE/transactional-storage-controller.file.README.md) | A partial multi-record update is exposed as a successful transaction. |
| [CETA-19.02.02 / storage-integrity-checker](19.02-DURABLE-STORAGE/storage-integrity-checker.file.README.md) | An index repair is reported as proof that all canonical data is intact. |
| [CETA-19.02.03 / storage-consistency-coordinator](19.02-DURABLE-STORAGE/storage-consistency-coordinator.file.README.md) | An event is published for a transaction that later rolls back. |
| [CETA-19.03.01 / snapshot-creation-engine](19.03-SNAPSHOTS/snapshot-creation-engine.file.README.md) | Files copied at unrelated times are called an atomic application snapshot. |
| [CETA-19.03.02 / snapshot-integrity-verifier](19.03-SNAPSHOTS/snapshot-integrity-verifier.file.README.md) | A valid archive checksum is treated as proof of application recovery. |
| [CETA-19.03.03 / snapshot-retention-controller](19.03-SNAPSHOTS/snapshot-retention-controller.file.README.md) | The last verified recovery snapshot is deleted before its replacement is qualified. |
| [CETA-19.04.01 / interrupted-operation-recovery](19.04-RECOVERY/interrupted-operation-recovery.file.README.md) | A missing completion record is assumed to mean the operation never ran. |
| [CETA-19.04.02 / persistent-state-restoration](19.04-RECOVERY/persistent-state-restoration.file.README.md) | An old backup reactivates revoked credentials or deleted memories silently. |
| [CETA-19.04.03 / uncertain-state-reconciler](19.04-RECOVERY/uncertain-state-reconciler.file.README.md) | The oldest available state is forced onto the system to make records agree. |
| [CETA-19.05.01 / schema-migration-planner](19.05-MIGRATION/schema-migration-planner.file.README.md) | A destructive transformation has no preserved recovery source or approved consequence. |
| [CETA-19.05.02 / migration-execution-controller](19.05-MIGRATION/migration-execution-controller.file.README.md) | The new schema version is activated before all required transformations are complete. |
| [CETA-19.05.03 / migration-reversal-validator](19.05-MIGRATION/migration-reversal-validator.file.README.md) | A lossy transformation is advertised as fully reversible. |
| [CETA-19.06.01 / conversation-archive-controller](19.06-ARCHIVAL/conversation-archive-controller.file.README.md) | A partial archive is presented as a complete conversation history. |
| [CETA-19.06.02 / project-history-archive](19.06-ARCHIVAL/project-history-archive.file.README.md) | Renaming or moving a project breaks its historical evidence links. |
| [CETA-19.06.03 / historical-state-retriever](19.06-ARCHIVAL/historical-state-retriever.file.README.md) | Historical authority is treated as valid permission for a present operation. |


## Mandatory response model

Validation and compatibility failures stop before privileged work. Authority failures deny the affected action and invalidate stale caches. Resource pressure preserves stop, evidence, and recovery capacity. A partial or uncertain effect is recorded explicitly. Missing evidence is not filled with narrative. Internal data writes use the canonical transaction owner; external actions have separately stated idempotency and compensation rules.

## Recovery sequence

1. Close new admission for the affected scope while preserving safe inspection.
2. Capture the last durable state, exact inputs, observed effects, process or target identity, and evidence gaps.
3. Inspect actual resources and receipts to distinguish committed, absent-confirmed, and uncertain effects.
4. Select safe continuation, authorized compensation, restoration, or a human decision using current authority.
5. Preserve later known revocations, deletion markers, corrections, identity records, conversations, and unsent drafts.
6. Requalify the repaired path and record a recovery report before reopening normal effects.

## Retry and compensation

Safe reads may be retried within the same bounded task. Confirmed idempotent operations preserve their operation key and current authority. Unknown outcomes require reconciliation first. Compensation is a new effect with its own scope and can fail; never describe an irreversible external action as undone because local state changed. For pure analysis and UI units, restart computation or presentation from pinned sources without replaying actions.

## Verification

Inject interruption, stale state, malformed input, resource exhaustion, and lost observations at meaningful boundaries for the units above. A recovery claim requires actual before and after observations and source-bound test records. See [the test matrix](TEST-MATRIX.md).
