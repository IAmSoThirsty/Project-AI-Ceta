# 23-TESTING-AND-QUALIFICATION - failure and recovery

## Domain-specific failure fixtures

| Unit | Adverse condition that must be handled |
| --- | --- |
| [CETA-23.01.01 / test-case-registry](23.01-TEST-ARCHITECTURE/test-case-registry.file.README.md) | A test is counted as passed merely because its specification exists. |
| [CETA-23.01.02 / test-fixture-controller](23.01-TEST-ARCHITECTURE/test-fixture-controller.file.README.md) | A fixture cleanup deletes files outside its test root. |
| [CETA-23.01.03 / test-result-normalizer](23.01-TEST-ARCHITECTURE/test-result-normalizer.file.README.md) | Missing results are converted into passed by an empty aggregate. |
| [CETA-23.02.01 / interface-contract-test-runner](23.02-CONTRACT-TESTING/interface-contract-test-runner.file.README.md) | A consumer treats an unknown result status as success. |
| [CETA-23.02.02 / governance-invariant-test-runner](23.02-CONTRACT-TESTING/governance-invariant-test-runner.file.README.md) | One alternate UI or retry path bypasses governance validation. |
| [CETA-23.02.03 / authority-boundary-test-runner](23.02-CONTRACT-TESTING/authority-boundary-test-runner.file.README.md) | A signature-valid revoked token is accepted through a cached path. |
| [CETA-23.03.01 / cross-subsystem-test-coordinator](23.03-INTEGRATION-TESTING/cross-subsystem-test-coordinator.file.README.md) | Tests pass only with mocked execution and never exercise native dispatch. |
| [CETA-23.03.02 / application-lifecycle-test-runner](23.03-INTEGRATION-TESTING/application-lifecycle-test-runner.file.README.md) | Restored UI state is used to bypass fresh authentication. |
| [CETA-23.03.03 / durable-recovery-test-runner](23.03-INTEGRATION-TESTING/durable-recovery-test-runner.file.README.md) | A missing completion event causes an already committed write to run again. |
| [CETA-23.04.01 / malicious-input-test-engine](23.04-ADVERSARIAL-AND-FAILURE-TESTS/malicious-input-test-engine.file.README.md) | A retrieved document changes the system's authority or sends local secrets outward. |
| [CETA-23.04.02 / interruption-fault-injector](23.04-ADVERSARIAL-AND-FAILURE-TESTS/interruption-fault-injector.file.README.md) | A test fault escapes its isolated environment and disrupts owner work. |
| [CETA-23.04.03 / authority-bypass-test-runner](23.04-ADVERSARIAL-AND-FAILURE-TESTS/authority-bypass-test-runner.file.README.md) | A hidden maintenance or debug command bypasses the execution gate. |
| [CETA-23.05.01 / acceptance-criteria-evaluator](23.05-PRODUCT-QUALIFICATION/acceptance-criteria-evaluator.file.README.md) | A high overall pass percentage hides a failed critical authority test. |
| [CETA-23.05.02 / qualification-gate-controller](23.05-PRODUCT-QUALIFICATION/qualification-gate-controller.file.README.md) | A previously passed gate remains valid after its implementation changed. |
| [CETA-23.05.03 / release-evidence-validator](23.05-PRODUCT-QUALIFICATION/release-evidence-validator.file.README.md) | A different build with the same version label inherits earlier evidence. |
| [CETA-23.06.01 / interface-behavior-test-runner](23.06-USER-EXPERIENCE-TESTING/interface-behavior-test-runner.file.README.md) | A button looks disabled while its keyboard path still performs the action. |
| [CETA-23.06.02 / accessibility-test-coordinator](23.06-USER-EXPERIENCE-TESTING/accessibility-test-coordinator.file.README.md) | A critical confirmation cannot be reached without a mouse. |
| [CETA-23.06.03 / performance-regression-test-runner](23.06-USER-EXPERIENCE-TESTING/performance-regression-test-runner.file.README.md) | Average latency hides severe stop-path stalls under load. |


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
