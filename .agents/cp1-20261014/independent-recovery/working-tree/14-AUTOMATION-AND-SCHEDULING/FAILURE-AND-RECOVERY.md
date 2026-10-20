# 14-AUTOMATION-AND-SCHEDULING - failure and recovery

## Domain-specific failure fixtures

| Unit | Adverse condition that must be handled |
| --- | --- |
| [CETA-14.01.01 / schedule-contract](14.01-SCHEDULE-DEFINITIONS/schedule-contract.file.README.md) | A schedule omits timezone and silently uses whatever the host currently reports. |
| [CETA-14.01.02 / schedule-registry](14.01-SCHEDULE-DEFINITIONS/schedule-registry.file.README.md) | A stale scheduler instance continues launching a deactivated schedule. |
| [CETA-14.01.03 / schedule-validation-engine](14.01-SCHEDULE-DEFINITIONS/schedule-validation-engine.file.README.md) | A recurrence can create unbounded overlapping tasks without explicit approval. |
| [CETA-14.02.01 / recurring-trigger-controller](14.02-TIME-TRIGGERS/recurring-trigger-controller.file.README.md) | A repeated local clock hour launches the same occurrence twice accidentally. |
| [CETA-14.02.02 / one-time-trigger-controller](14.02-TIME-TRIGGERS/one-time-trigger-controller.file.README.md) | Two scheduler workers both launch the same one-time task. |
| [CETA-14.02.03 / time-window-evaluator](14.02-TIME-TRIGGERS/time-window-evaluator.file.README.md) | Clock rollback extends an expired execution window indefinitely. |
| [CETA-14.03.01 / system-event-listener](14.03-EVENT-TRIGGERS/system-event-listener.file.README.md) | Lost events are silently assumed not to have occurred. |
| [CETA-14.03.02 / resource-change-watcher](14.03-EVENT-TRIGGERS/resource-change-watcher.file.README.md) | Watcher overflow is treated as complete coverage of all changes. |
| [CETA-14.03.03 / event-condition-evaluator](14.03-EVENT-TRIGGERS/event-condition-evaluator.file.README.md) | A crafted event changes the condition or injects a new task definition. |
| [CETA-14.04.01 / automation-job-dispatcher](14.04-AUTOMATION-DISPATCH/automation-job-dispatcher.file.README.md) | A queue retry creates a new task with the same external effect. |
| [CETA-14.04.02 / scheduled-authority-validator](14.04-AUTOMATION-DISPATCH/scheduled-authority-validator.file.README.md) | A schedule continues indefinitely on the authority present at creation. |
| [CETA-14.04.03 / automation-concurrency-controller](14.04-AUTOMATION-DISPATCH/automation-concurrency-controller.file.README.md) | A replacement starts before the previous effectful task has actually stopped. |
| [CETA-14.05.01 / missed-trigger-reconciler](14.05-AUTOMATION-CONTINUITY/missed-trigger-reconciler.file.README.md) | Every missed occurrence is replayed automatically despite expired inputs. |
| [CETA-14.05.02 / automation-recovery-controller](14.05-AUTOMATION-CONTINUITY/automation-recovery-controller.file.README.md) | A lost dispatch acknowledgement triggers a duplicate task. |
| [CETA-14.05.03 / automation-outcome-recorder](14.05-AUTOMATION-CONTINUITY/automation-outcome-recorder.file.README.md) | Dispatch success is reported as completion of the scheduled work. |


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
