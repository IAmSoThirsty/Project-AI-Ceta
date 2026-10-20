# 06-AGENT-SKILLS-AND-LEARNING - failure and recovery

## Domain-specific failure fixtures

| Unit | Adverse condition that must be handled |
| --- | --- |
| [CETA-06.01.01 / skill-manifest-schema](06.01-SKILL-DEFINITIONS/skill-manifest-schema.file.README.md) | A skill declares itself read-only while requesting a write-capable tool. |
| [CETA-06.01.02 / skill-contract-registry](06.01-SKILL-DEFINITIONS/skill-contract-registry.file.README.md) | A manifest is replaced in place under the same version and digest. |
| [CETA-06.01.03 / skill-dependency-resolver](06.01-SKILL-DEFINITIONS/skill-dependency-resolver.file.README.md) | A dependency cycle is hidden by recursively loading until resource exhaustion. |
| [CETA-06.02.01 / skill-catalog](06.02-SKILL-DISCOVERY/skill-catalog.file.README.md) | A revoked skill remains selectable from a stale cached search result. |
| [CETA-06.02.02 / skill-matching-engine](06.02-SKILL-DISCOVERY/skill-matching-engine.file.README.md) | A faster destructive skill is selected because its title is similar. |
| [CETA-06.02.03 / skill-compatibility-checker](06.02-SKILL-DISCOVERY/skill-compatibility-checker.file.README.md) | Missing required isolation support is treated as a harmless warning. |
| [CETA-06.03.01 / skill-invocation-controller](06.03-SKILL-EXECUTION/skill-invocation-controller.file.README.md) | A retry creates a second external effect under a new hidden operation identifier. |
| [CETA-06.03.02 / skill-input-validator](06.03-SKILL-EXECUTION/skill-input-validator.file.README.md) | A malformed attachment path changes the operation target after validation. |
| [CETA-06.03.03 / skill-result-validator](06.03-SKILL-EXECUTION/skill-result-validator.file.README.md) | A fluent final message substitutes for a missing output artifact. |
| [CETA-06.04.01 / skill-candidate-generator](06.04-SKILL-LEARNING/skill-candidate-generator.file.README.md) | A successful one-off privileged action is generalized into unrestricted authority. |
| [CETA-06.04.02 / skill-learning-evaluator](06.04-SKILL-LEARNING/skill-learning-evaluator.file.README.md) | Training examples are reused as the only evidence of general usefulness. |
| [CETA-06.04.03 / skill-approval-workflow](06.04-SKILL-LEARNING/skill-approval-workflow.file.README.md) | The candidate changes after review but retains the earlier approval. |
| [CETA-06.05.01 / skill-version-manager](06.05-SKILL-LIFECYCLE/skill-version-manager.file.README.md) | A rollback reactivates a revision that has a current security revocation. |
| [CETA-06.05.02 / skill-revocation-controller](06.05-SKILL-LIFECYCLE/skill-revocation-controller.file.README.md) | A cached invocation bypasses the updated revocation generation. |
| [CETA-06.05.03 / skill-audit-recorder](06.05-SKILL-LIFECYCLE/skill-audit-recorder.file.README.md) | An invocation log includes raw credential material from the skill input. |


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
