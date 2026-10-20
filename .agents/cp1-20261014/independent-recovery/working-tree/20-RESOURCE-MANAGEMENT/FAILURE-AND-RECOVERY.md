# 20-RESOURCE-MANAGEMENT - failure and recovery

## Domain-specific failure fixtures

| Unit | Adverse condition that must be handled |
| --- | --- |
| [CETA-20.01.01 / hardware-capability-profiler](20.01-HARDWARE-DISCOVERY/hardware-capability-profiler.file.README.md) | Advertised hardware capacity is used as currently available capacity. |
| [CETA-20.01.02 / compute-availability-monitor](20.01-HARDWARE-DISCOVERY/compute-availability-monitor.file.README.md) | A stale free-capacity reading admits conflicting workloads. |
| [CETA-20.01.03 / storage-capacity-monitor](20.01-HARDWARE-DISCOVERY/storage-capacity-monitor.file.README.md) | New tasks consume the final space required to record their outcomes. |
| [CETA-20.02.01 / compute-budget-controller](20.02-RESOURCE-BUDGETING/compute-budget-controller.file.README.md) | Delegation creates extra unaccounted compute capacity. |
| [CETA-20.02.02 / memory-budget-controller](20.02-RESOURCE-BUDGETING/memory-budget-controller.file.README.md) | Optimistic estimates allow all workers to allocate simultaneously beyond capacity. |
| [CETA-20.02.03 / execution-time-budget-controller](20.02-RESOURCE-BUDGETING/execution-time-budget-controller.file.README.md) | Clock adjustment grants unlimited extra runtime to an expired task. |
| [CETA-20.03.01 / workload-requirement-estimator](20.03-WORKLOAD-ADMISSION/workload-requirement-estimator.file.README.md) | A task with unknown memory behavior is assigned a precise unsupported estimate. |
| [CETA-20.03.02 / workload-admission-controller](20.03-WORKLOAD-ADMISSION/workload-admission-controller.file.README.md) | A queued task starts after cancellation because its old reservation became available. |
| [CETA-20.03.03 / concurrent-workload-planner](20.03-WORKLOAD-ADMISSION/concurrent-workload-planner.file.README.md) | More agents are launched solely because work exists despite exhausted memory. |
| [CETA-20.04.01 / resource-pressure-detector](20.04-RESOURCE-PRESSURE/resource-pressure-detector.file.README.md) | A single stale sample causes repeated stop-and-restart loops. |
| [CETA-20.04.02 / workload-throttling-controller](20.04-RESOURCE-PRESSURE/workload-throttling-controller.file.README.md) | Resource pressure causes required verification steps to be skipped silently. |
| [CETA-20.04.03 / graceful-degradation-coordinator](20.04-RESOURCE-PRESSURE/graceful-degradation-coordinator.file.README.md) | Degradation disables authorization checks to keep the application responsive. |
| [CETA-20.05.01 / resource-telemetry-recorder](20.05-OPERATIONAL-DIAGNOSTICS/resource-telemetry-recorder.file.README.md) | Telemetry records full prompts or secrets merely to explain resource use. |
| [CETA-20.05.02 / performance-diagnostics-engine](20.05-OPERATIONAL-DIAGNOSTICS/performance-diagnostics-engine.file.README.md) | A guessed bottleneck is reported as measured evidence. |
| [CETA-20.05.03 / offline-operation-qualifier](20.05-OPERATIONAL-DIAGNOSTICS/offline-operation-qualifier.file.README.md) | A hidden license, telemetry, or model lookup blocks offline startup. |
| [CETA-20.06.01 / token-consumption-meter](20.06-INFERENCE-ACCOUNTING/token-consumption-meter.file.README.md) | An estimated token count is presented as an exact observed count. |
| [CETA-20.06.02 / task-inference-budget-controller](20.06-INFERENCE-ACCOUNTING/task-inference-budget-controller.file.README.md) | Each child receives a fresh full budget that bypasses the parent limit. |
| [CETA-20.06.03 / inference-usage-ledger](20.06-INFERENCE-ACCOUNTING/inference-usage-ledger.file.README.md) | A failed or partial request vanishes from accounting despite consumed inference work. |


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
