# 12-ENGINEERING-INTELLIGENCE - failure and recovery

## Domain-specific failure fixtures

| Unit | Adverse condition that must be handled |
| --- | --- |
| [CETA-12.01.01 / repository-inspector](12.01-PROJECT-DISCOVERY/repository-inspector.file.README.md) | A remote repository assumption hides locally untracked or generated source. |
| [CETA-12.01.02 / code-structure-indexer](12.01-PROJECT-DISCOVERY/code-structure-indexer.file.README.md) | A stale index directs an edit to a symbol that moved or changed meaning. |
| [CETA-12.01.03 / dependency-analysis-engine](12.01-PROJECT-DISCOVERY/dependency-analysis-engine.file.README.md) | An unresolved dynamic dependency is silently treated as absent. |
| [CETA-12.02.01 / requirement-to-task-planner](12.02-ENGINEERING-PLANNING/requirement-to-task-planner.file.README.md) | An unmet requirement disappears because no current module obviously owns it. |
| [CETA-12.02.02 / implementation-sequencer](12.02-ENGINEERING-PLANNING/implementation-sequencer.file.README.md) | A release step runs before changed migration behavior is qualified. |
| [CETA-12.02.03 / change-risk-analyzer](12.02-ENGINEERING-PLANNING/change-risk-analyzer.file.README.md) | A security-boundary change is treated as ordinary cosmetic maintenance. |
| [CETA-12.03.01 / source-edit-planner](12.03-CODE-CONSTRUCTION/source-edit-planner.file.README.md) | The plan recreates an existing subsystem without inspecting its current implementation. |
| [CETA-12.03.02 / multifile-change-coordinator](12.03-CODE-CONSTRUCTION/multifile-change-coordinator.file.README.md) | One agent publishes a partial interface change while another reads inconsistent files. |
| [CETA-12.03.03 / change-transaction-controller](12.03-CODE-CONSTRUCTION/change-transaction-controller.file.README.md) | Recovery overwrites unrelated user changes to make the working tree look clean. |
| [CETA-12.04.01 / test-generation-planner](12.04-TESTING-AND-DEBUGGING/test-generation-planner.file.README.md) | A generated test asserts the same mistaken assumption as the implementation. |
| [CETA-12.04.02 / failure-reproduction-engine](12.04-TESTING-AND-DEBUGGING/failure-reproduction-engine.file.README.md) | A suspected cause is presented as reproduced without running the failing path. |
| [CETA-12.04.03 / diagnostic-repair-planner](12.04-TESTING-AND-DEBUGGING/diagnostic-repair-planner.file.README.md) | A broad rewrite removes the symptom while bypassing the required behavior. |
| [CETA-12.05.01 / code-review-engine](12.05-ENGINEERING-REVIEW/code-review-engine.file.README.md) | A stylistic preference is presented as a proven functional defect without evidence. |
| [CETA-12.05.02 / regression-risk-evaluator](12.05-ENGINEERING-REVIEW/regression-risk-evaluator.file.README.md) | Only directly edited files are tested despite changed cross-subsystem semantics. |
| [CETA-12.05.03 / engineering-contract-validator](12.05-ENGINEERING-REVIEW/engineering-contract-validator.file.README.md) | An implementation changes a failure into success to satisfy a caller expectation. |
| [CETA-12.06.01 / build-verification-coordinator](12.06-ENGINEERING-DELIVERY/build-verification-coordinator.file.README.md) | Tests pass on one worktree while a different source tree is packaged. |
| [CETA-12.06.02 / implementation-report-generator](12.06-ENGINEERING-DELIVERY/implementation-report-generator.file.README.md) | The report claims a command was run because it appeared in the plan. |
| [CETA-12.06.03 / documentation-sync-controller](12.06-ENGINEERING-DELIVERY/documentation-sync-controller.file.README.md) | Documentation promises a capability that remains unimplemented or unqualified. |


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
