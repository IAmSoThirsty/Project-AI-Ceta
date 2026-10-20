# 01-CONSTITUTIONAL-GOVERNANCE - failure and recovery

## Domain-specific failure fixtures

| Unit | Adverse condition that must be handled |
| --- | --- |
| [CETA-01.01.01 / constitution-registry](01.01-CONSTITUTIONAL-SOURCES/constitution-registry.file.README.md) | An imported document claims constitutional authority without an activation decision. |
| [CETA-01.01.02 / constitutional-rule-catalog](01.01-CONSTITUTIONAL-SOURCES/constitutional-rule-catalog.file.README.md) | Two rules share an identity with different content in the same revision. |
| [CETA-01.01.03 / rule-version-loader](01.01-CONSTITUTIONAL-SOURCES/rule-version-loader.file.README.md) | A partly loaded revision is exposed to an authorization evaluator. |
| [CETA-01.02.01 / policy-interpreter](01.02-POLICY-ENGINE/policy-interpreter.file.README.md) | Excessive recursion terminates with an evaluation failure rather than permitting the action. |
| [CETA-01.02.02 / policy-evaluator](01.02-POLICY-ENGINE/policy-evaluator.file.README.md) | Missing required identity facts are interpreted as truthy defaults. |
| [CETA-01.02.03 / policy-conflict-resolver](01.02-POLICY-ENGINE/policy-conflict-resolver.file.README.md) | The system invents a priority based on rule order or model preference. |
| [CETA-01.03.01 / transition-proposal-builder](01.03-GOVERNANCE-TRANSITIONS/transition-proposal-builder.file.README.md) | Inputs change after approval and the original approval is reused. |
| [CETA-01.03.02 / governance-packet-validator](01.03-GOVERNANCE-TRANSITIONS/governance-packet-validator.file.README.md) | A genuine approval for a different proposal is included in the packet. |
| [CETA-01.03.03 / governance-quorum-controller](01.03-GOVERNANCE-TRANSITIONS/governance-quorum-controller.file.README.md) | One principal appears through two aliases and is counted twice. |
| [CETA-01.04.01 / language-parser](01.04-THIRSTY-LANG/language-parser.file.README.md) | Untrusted trailing text changes the parsed policy after the claimed end of input. |
| [CETA-01.04.02 / policy-type-checker](01.04-THIRSTY-LANG/policy-type-checker.file.README.md) | A free-text approval is accepted where a validated approval reference is required. |
| [CETA-01.04.03 / governed-rule-compiler](01.04-THIRSTY-LANG/governed-rule-compiler.file.README.md) | A compiler optimization changes denial behavior for a missing field. |
| [CETA-01.05.01 / policy-invariant-checker](01.05-POLICY-ASSURANCE/policy-invariant-checker.file.README.md) | A rule grants authority from an agent confidence score. |
| [CETA-01.05.02 / rule-traceability-mapper](01.05-POLICY-ASSURANCE/rule-traceability-mapper.file.README.md) | A rule is called enforced solely because it appears in a document. |
| [CETA-01.05.03 / constitutional-change-validator](01.05-POLICY-ASSURANCE/constitutional-change-validator.file.README.md) | Existing approvals survive a scope-widening rule change without reevaluation. |


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
