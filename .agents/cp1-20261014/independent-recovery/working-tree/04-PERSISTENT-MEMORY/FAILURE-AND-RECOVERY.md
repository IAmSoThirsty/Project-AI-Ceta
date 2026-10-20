# 04-PERSISTENT-MEMORY - failure and recovery

## Domain-specific failure fixtures

| Unit | Adverse condition that must be handled |
| --- | --- |
| [CETA-04.01.01 / episodic-memory-store](04.01-MEMORY-RECORDS/episodic-memory-store.file.README.md) | The ingestion timestamp is substituted for the event timestamp without disclosure. |
| [CETA-04.01.02 / semantic-memory-store](04.01-MEMORY-RECORDS/semantic-memory-store.file.README.md) | A frequently repeated generated statement is promoted to established fact. |
| [CETA-04.01.03 / procedural-memory-store](04.01-MEMORY-RECORDS/procedural-memory-store.file.README.md) | An unreviewed recorded workflow becomes an executable privileged skill. |
| [CETA-04.02.01 / memory-index-builder](04.02-MEMORY-INDEXING/memory-index-builder.file.README.md) | An index is treated as the only copy of a memory record. |
| [CETA-04.02.02 / semantic-memory-retriever](04.02-MEMORY-INDEXING/semantic-memory-retriever.file.README.md) | A restricted record leaks through an index snippet or similarity score explanation. |
| [CETA-04.02.03 / temporal-memory-retriever](04.02-MEMORY-INDEXING/temporal-memory-retriever.file.README.md) | An ambiguous date is silently resolved to a precise timestamp. |
| [CETA-04.03.01 / memory-consolidation-engine](04.03-MEMORY-CONSOLIDATION/memory-consolidation-engine.file.README.md) | A summary silently removes an explicit user correction. |
| [CETA-04.03.02 / memory-conflict-resolver](04.03-MEMORY-CONSOLIDATION/memory-conflict-resolver.file.README.md) | Model confidence alone resolves disagreement between authoritative sources. |
| [CETA-04.03.03 / memory-significance-analyzer](04.03-MEMORY-CONSOLIDATION/memory-significance-analyzer.file.README.md) | Frequently generated content is treated as more truthful merely because it recurs. |
| [CETA-04.04.01 / memory-source-linker](04.04-MEMORY-PROVENANCE/memory-source-linker.file.README.md) | A broad document link is asserted to support a claim absent from that document. |
| [CETA-04.04.02 / memory-evidence-validator](04.04-MEMORY-PROVENANCE/memory-evidence-validator.file.README.md) | A cryptographically intact but irrelevant source is counted as supporting evidence. |
| [CETA-04.04.03 / memory-version-tracker](04.04-MEMORY-PROVENANCE/memory-version-tracker.file.README.md) | An index still returns a superseded version as the current authoritative preference. |
| [CETA-04.05.01 / memory-retention-controller](04.05-MEMORY-LIFECYCLE/memory-retention-controller.file.README.md) | A retention job deletes a record still required by an explicitly active preservation rule. |
| [CETA-04.05.02 / memory-access-policy](04.05-MEMORY-LIFECYCLE/memory-access-policy.file.README.md) | A global search result bypasses project-specific memory restrictions. |
| [CETA-04.05.03 / memory-deletion-coordinator](04.05-MEMORY-LIFECYCLE/memory-deletion-coordinator.file.README.md) | A deleted record reappears after index rebuild or snapshot restoration. |
| [CETA-04.06.01 / memory-import-controller](04.06-MEMORY-PORTABILITY/memory-import-controller.file.README.md) | An import contains executable instructions that attempt to activate authority. |
| [CETA-04.06.02 / memory-export-controller](04.06-MEMORY-PORTABILITY/memory-export-controller.file.README.md) | Hidden unrelated memory is included because it shares an index partition. |
| [CETA-04.06.03 / memory-reconstruction-validator](04.06-MEMORY-PORTABILITY/memory-reconstruction-validator.file.README.md) | A successful archive checksum is treated as proof that all memory can be reconstructed. |


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
