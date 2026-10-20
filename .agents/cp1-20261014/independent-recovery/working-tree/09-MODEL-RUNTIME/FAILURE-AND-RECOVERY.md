# 09-MODEL-RUNTIME - failure and recovery

## Domain-specific failure fixtures

| Unit | Adverse condition that must be handled |
| --- | --- |
| [CETA-09.01.01 / model-manifest](09.01-MODEL-REGISTRY/model-manifest.file.README.md) | A model's advertised context limit is trusted without target-runtime qualification. |
| [CETA-09.01.02 / model-availability-registry](09.01-MODEL-REGISTRY/model-availability-registry.file.README.md) | A stale heartbeat leaves a dead model selectable for new tasks. |
| [CETA-09.01.03 / model-artifact-validator](09.01-MODEL-REGISTRY/model-artifact-validator.file.README.md) | One modified shard is overlooked because the top-level filename matches. |
| [CETA-09.02.01 / inference-session-manager](09.02-INFERENCE-RUNTIME/inference-session-manager.file.README.md) | A resumed session inherits hidden state from another user's or project's request. |
| [CETA-09.02.02 / inference-request-controller](09.02-INFERENCE-RUNTIME/inference-request-controller.file.README.md) | Unsupported image input is silently dropped while the task proceeds as if it was understood. |
| [CETA-09.02.03 / inference-stream-handler](09.02-INFERENCE-RUNTIME/inference-stream-handler.file.README.md) | Reordered chunks produce a corrupted tool request that is nevertheless dispatched. |
| [CETA-09.03.01 / model-capability-matcher](09.03-MODEL-ROUTING/model-capability-matcher.file.README.md) | A smaller context window is accepted by silently removing required source material. |
| [CETA-09.03.02 / model-selection-engine](09.03-MODEL-ROUTING/model-selection-engine.file.README.md) | A routing heuristic overrides an explicit local-data requirement. |
| [CETA-09.03.03 / model-fallback-controller](09.03-MODEL-ROUTING/model-fallback-controller.file.README.md) | Private context is sent externally because the local runtime failed. |
| [CETA-09.04.01 / model-hardware-qualifier](09.04-MODEL-ADMISSION/model-hardware-qualifier.file.README.md) | Successful metadata inspection is reported as successful inference qualification. |
| [CETA-09.04.02 / model-resource-estimator](09.04-MODEL-ADMISSION/model-resource-estimator.file.README.md) | The estimate ignores growth with context length or parallel requests. |
| [CETA-09.04.03 / model-admission-gate](09.04-MODEL-ADMISSION/model-admission-gate.file.README.md) | Admission checks memory availability without reserving it, allowing an oversubscription race. |
| [CETA-09.05.01 / local-inference-adapter](09.05-MODEL-INTERFACES/local-inference-adapter.file.README.md) | A process with a reused identifier is accepted as the authorized model runtime. |
| [CETA-09.05.02 / connected-inference-adapter](09.05-MODEL-INTERFACES/connected-inference-adapter.file.README.md) | Endpoint redirection changes the approved recipient without reauthorization. |
| [CETA-09.05.03 / inference-contract-validator](09.05-MODEL-INTERFACES/inference-contract-validator.file.README.md) | Malformed model output is passed to the tool dispatcher as trusted arguments. |
| [CETA-09.06.01 / model-benchmark-runner](09.06-MODEL-EVALUATION/model-benchmark-runner.file.README.md) | A favorable single response is reported as a stable benchmark result. |
| [CETA-09.06.02 / model-quality-evaluator](09.06-MODEL-EVALUATION/model-quality-evaluator.file.README.md) | Aggregate fluency scores hide failures on critical authorization-related fixtures. |
| [CETA-09.06.03 / model-runtime-diagnostics](09.06-MODEL-EVALUATION/model-runtime-diagnostics.file.README.md) | Diagnostic logs persist raw sensitive prompts by default. |
| [CETA-09.07.01 / model-acquisition-controller](09.07-MODEL-LIFECYCLE/model-acquisition-controller.file.README.md) | A partial or substituted download is registered as ready. |
| [CETA-09.07.02 / model-installation-manager](09.07-MODEL-LIFECYCLE/model-installation-manager.file.README.md) | Installation overwrites the last working model before the replacement is verified. |
| [CETA-09.07.03 / model-load-unload-controller](09.07-MODEL-LIFECYCLE/model-load-unload-controller.file.README.md) | Unload reports success while the model process retains its allocations. |
| [CETA-09.07.04 / model-configuration-validator](09.07-MODEL-LIFECYCLE/model-configuration-validator.file.README.md) | A user-visible setting accepts an impossible context size without validation. |
| [CETA-09.08.01 / model-adaptation-planner](09.08-MODEL-CUSTOMIZATION/model-adaptation-planner.file.README.md) | Private conversation history is added to training without the owner's specified permission. |
| [CETA-09.08.02 / training-job-controller](09.08-MODEL-CUSTOMIZATION/training-job-controller.file.README.md) | A checkpoint from a different base model is silently loaded. |
| [CETA-09.08.03 / trained-artifact-validator](09.08-MODEL-CUSTOMIZATION/trained-artifact-validator.file.README.md) | Training completion alone activates the candidate as the default runtime model. |


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
