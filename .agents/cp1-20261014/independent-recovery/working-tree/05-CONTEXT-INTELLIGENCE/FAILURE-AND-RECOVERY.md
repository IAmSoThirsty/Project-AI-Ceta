# 05-CONTEXT-INTELLIGENCE - failure and recovery

## Domain-specific failure fixtures

| Unit | Adverse condition that must be handled |
| --- | --- |
| [CETA-05.01.01 / context-source-selector](05.01-CONTEXT-INPUTS/context-source-selector.file.README.md) | A retrieved document is inserted into the trusted instruction channel. |
| [CETA-05.01.02 / project-context-resolver](05.01-CONTEXT-INPUTS/project-context-resolver.file.README.md) | Two similarly named local projects have their context merged accidentally. |
| [CETA-05.01.03 / session-context-resolver](05.01-CONTEXT-INPUTS/session-context-resolver.file.README.md) | A prior session's consent is carried into a new session without validating its scope. |
| [CETA-05.02.01 / context-composition-engine](05.02-CONTEXT-ASSEMBLY/context-composition-engine.file.README.md) | Delimiters inside retrieved text escape into the trusted instruction segment. |
| [CETA-05.02.02 / relevance-ranking-engine](05.02-CONTEXT-ASSEMBLY/relevance-ranking-engine.file.README.md) | High semantic similarity alone displaces a required explicit user constraint. |
| [CETA-05.02.03 / authority-context-injector](05.02-CONTEXT-ASSEMBLY/authority-context-injector.file.README.md) | A model-generated authority description replaces the verified authority snapshot. |
| [CETA-05.03.01 / context-budget-controller](05.03-CONTEXT-BUDGETING/context-budget-controller.file.README.md) | An estimate ignores tool declarations and causes silent provider-side truncation. |
| [CETA-05.03.02 / context-priority-allocator](05.03-CONTEXT-BUDGETING/context-priority-allocator.file.README.md) | Optional historical material displaces the current approved target scope. |
| [CETA-05.03.03 / context-overflow-handler](05.03-CONTEXT-BUDGETING/context-overflow-handler.file.README.md) | The system drops critical instructions and proceeds without warning. |
| [CETA-05.04.01 / context-compaction-engine](05.04-CONTEXT-COMPRESSION/context-compaction-engine.file.README.md) | A failed action is summarized as successfully completed. |
| [CETA-05.04.02 / summary-integrity-validator](05.04-CONTEXT-COMPRESSION/summary-integrity-validator.file.README.md) | A second model's agreement alone is accepted as proof of summary fidelity. |
| [CETA-05.04.03 / critical-state-preserver](05.04-CONTEXT-COMPRESSION/critical-state-preserver.file.README.md) | A cancelled task loses its stop state during context reduction. |
| [CETA-05.05.01 / source-attribution-checker](05.05-CONTEXT-ASSURANCE/source-attribution-checker.file.README.md) | A citation marker is generated for a source that was never retrieved. |
| [CETA-05.05.02 / context-contamination-detector](05.05-CONTEXT-ASSURANCE/context-contamination-detector.file.README.md) | A benign quoted example is automatically destroyed rather than labeled for review. |
| [CETA-05.05.03 / context-snapshot-manager](05.05-CONTEXT-ASSURANCE/context-snapshot-manager.file.README.md) | A stored context includes raw secrets that were never authorized for persistence. |


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
