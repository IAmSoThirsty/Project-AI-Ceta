# 16-KNOWLEDGE-AND-RESEARCH - failure and recovery

## Domain-specific failure fixtures

| Unit | Adverse condition that must be handled |
| --- | --- |
| [CETA-16.01.01 / document-ingestion-engine](16.01-SOURCE-INGESTION/document-ingestion-engine.file.README.md) | Garbled extraction is silently repaired with invented text. |
| [CETA-16.01.02 / web-content-ingestion-engine](16.01-SOURCE-INGESTION/web-content-ingestion-engine.file.README.md) | A current-looking page title is treated as proof that its content is current. |
| [CETA-16.01.03 / structured-data-ingestion](16.01-SOURCE-INGESTION/structured-data-ingestion.file.README.md) | Missing values are silently converted into zero and alter conclusions. |
| [CETA-16.02.01 / document-structure-extractor](16.02-KNOWLEDGE-EXTRACTION/document-structure-extractor.file.README.md) | A footnote qualification is separated from the claim it modifies. |
| [CETA-16.02.02 / entity-relation-extractor](16.02-KNOWLEDGE-EXTRACTION/entity-relation-extractor.file.README.md) | Co-occurrence in a document is treated as proof of a causal relationship. |
| [CETA-16.02.03 / knowledge-normalization-engine](16.02-KNOWLEDGE-EXTRACTION/knowledge-normalization-engine.file.README.md) | Two different entities with the same name are merged without disambiguating evidence. |
| [CETA-16.03.01 / fulltext-knowledge-index](16.03-KNOWLEDGE-INDEXING/fulltext-knowledge-index.file.README.md) | A stale index returns text removed by an authorized source correction as current. |
| [CETA-16.03.02 / semantic-knowledge-index](16.03-KNOWLEDGE-INDEXING/semantic-knowledge-index.file.README.md) | A semantically similar but contradictory passage is presented as supporting evidence. |
| [CETA-16.03.03 / knowledge-graph-builder](16.03-KNOWLEDGE-INDEXING/knowledge-graph-builder.file.README.md) | Visual proximity or graph connectivity is interpreted as proof of causation. |
| [CETA-16.04.01 / source-comparison-engine](16.04-RESEARCH-REASONING/source-comparison-engine.file.README.md) | Repeated publication is treated as independent confirmation. |
| [CETA-16.04.02 / evidence-weighting-engine](16.04-RESEARCH-REASONING/evidence-weighting-engine.file.README.md) | A valid digital signature is treated as proof that the source's claim is true. |
| [CETA-16.04.03 / claim-verification-planner](16.04-RESEARCH-REASONING/claim-verification-planner.file.README.md) | A lack of disproof is promoted into proof of the claim. |
| [CETA-16.05.01 / citation-construction-engine](16.05-RESEARCH-OUTPUT/citation-construction-engine.file.README.md) | A source identifier or passage location is invented to make a report appear complete. |
| [CETA-16.05.02 / research-synthesis-controller](16.05-RESEARCH-OUTPUT/research-synthesis-controller.file.README.md) | A compelling narrative suppresses contradictory source findings. |
| [CETA-16.05.03 / research-state-preserver](16.05-RESEARCH-OUTPUT/research-state-preserver.file.README.md) | A later source revision silently replaces the evidence used for an earlier conclusion. |


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
