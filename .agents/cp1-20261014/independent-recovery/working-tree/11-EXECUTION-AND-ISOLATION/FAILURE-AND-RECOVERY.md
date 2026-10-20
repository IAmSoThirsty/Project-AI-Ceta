# 11-EXECUTION-AND-ISOLATION - failure and recovery

## Domain-specific failure fixtures

| Unit | Adverse condition that must be handled |
| --- | --- |
| [CETA-11.01.01 / execution-request-validator](11.01-EXECUTION-GATE/execution-request-validator.file.README.md) | Arguments change between preparation and dispatch without a new approval. |
| [CETA-11.01.02 / authorization-proof-checker](11.01-EXECUTION-GATE/authorization-proof-checker.file.README.md) | A revoked token passes because its signature remains cryptographically valid. |
| [CETA-11.01.03 / execution-gate-controller](11.01-EXECUTION-GATE/execution-gate-controller.file.README.md) | Evidence recording is unavailable yet the operation proceeds with no recoverable authorization record. |
| [CETA-11.02.01 / execution-environment-builder](11.02-EXECUTION-SANDBOX/execution-environment-builder.file.README.md) | Host credentials or unrelated project directories are inherited into the worker. |
| [CETA-11.02.02 / execution-boundary-enforcer](11.02-EXECUTION-SANDBOX/execution-boundary-enforcer.file.README.md) | An unsupported restriction is logged as a warning while unrestricted execution continues. |
| [CETA-11.02.03 / sandbox-cleanup-controller](11.02-EXECUTION-SANDBOX/sandbox-cleanup-controller.file.README.md) | Cleanup reports success while a detached child process continues running. |
| [CETA-11.03.01 / intended-effect-register](11.03-EFFECT-CONTROL/intended-effect-register.file.README.md) | A transitive child-process effect is omitted from the declared effect set. |
| [CETA-11.03.02 / effect-boundary-validator](11.03-EFFECT-CONTROL/effect-boundary-validator.file.README.md) | A path race changes the target after validation and before use. |
| [CETA-11.03.03 / actual-effect-observer](11.03-EFFECT-CONTROL/actual-effect-observer.file.README.md) | Missing observer telemetry is treated as proof that no side effect occurred. |
| [CETA-11.04.01 / stop-signal-controller](11.04-STOP-AND-CANCELLATION/stop-signal-controller.file.README.md) | A busy inference queue prevents the owner from issuing stop. |
| [CETA-11.04.02 / running-operation-terminator](11.04-STOP-AND-CANCELLATION/running-operation-terminator.file.README.md) | A reused process identifier causes termination of an unrelated process. |
| [CETA-11.04.03 / cancellation-evidence-recorder](11.04-STOP-AND-CANCELLATION/cancellation-evidence-recorder.file.README.md) | A stop button click alone produces a successful cancellation receipt. |
| [CETA-11.05.01 / execution-transaction-manager](11.05-EXECUTION-TRANSACTIONS/execution-transaction-manager.file.README.md) | A database rollback is claimed to undo an already delivered network request. |
| [CETA-11.05.02 / uncertain-effect-handler](11.05-EXECUTION-TRANSACTIONS/uncertain-effect-handler.file.README.md) | The handler automatically retries every uncertain write. |
| [CETA-11.05.03 / compensation-executor](11.05-EXECUTION-TRANSACTIONS/compensation-executor.file.README.md) | Compensation overwrites a legitimate later user edit. |
| [CETA-11.06.01 / enforcement-policy-adapter](11.06-OCTOREFLEX-BOUNDARY/enforcement-policy-adapter.file.README.md) | A platform lacks a required restriction and the adapter silently drops it. |
| [CETA-11.06.02 / operating-system-effect-monitor](11.06-OCTOREFLEX-BOUNDARY/operating-system-effect-monitor.file.README.md) | A monitor labels unobserved activity as absent despite buffer overflow. |
| [CETA-11.06.03 / enforcement-attestation-adapter](11.06-OCTOREFLEX-BOUNDARY/enforcement-attestation-adapter.file.README.md) | A stale configuration file is presented as proof of current operating-system enforcement. |


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
