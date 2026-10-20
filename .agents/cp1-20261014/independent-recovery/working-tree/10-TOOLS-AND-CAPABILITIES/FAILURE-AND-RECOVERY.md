# 10-TOOLS-AND-CAPABILITIES - failure and recovery

## Domain-specific failure fixtures

| Unit | Adverse condition that must be handled |
| --- | --- |
| [CETA-10.01.01 / tool-manifest](10.01-TOOL-REGISTRY/tool-manifest.file.README.md) | Tool code changes while retaining an old trusted manifest digest. |
| [CETA-10.01.02 / tool-discovery-engine](10.01-TOOL-REGISTRY/tool-discovery-engine.file.README.md) | A discovery operation executes an extension's arbitrary startup action. |
| [CETA-10.01.03 / tool-capability-index](10.01-TOOL-REGISTRY/tool-capability-index.file.README.md) | A search match is reported as permission to execute the tool. |
| [CETA-10.02.01 / tool-input-validator](10.02-TOOL-CONTRACTS/tool-input-validator.file.README.md) | Additional hidden fields alter behavior after approval. |
| [CETA-10.02.02 / tool-output-validator](10.02-TOOL-CONTRACTS/tool-output-validator.file.README.md) | A tool returns a success label with missing required output and is treated as complete. |
| [CETA-10.02.03 / tool-effect-classifier](10.02-TOOL-CONTRACTS/tool-effect-classifier.file.README.md) | A shell wrapper is classified as read-only because its top-level name sounds harmless. |
| [CETA-10.03.01 / filesystem-tool-adapter](10.03-LOCAL-OPERATIONS/filesystem-tool-adapter.file.README.md) | A path alias or link redirects an operation outside the approved root. |
| [CETA-10.03.02 / command-execution-adapter](10.03-LOCAL-OPERATIONS/command-execution-adapter.file.README.md) | Injected shell syntax expands a permitted argument into a second command. |
| [CETA-10.03.03 / application-control-adapter](10.03-LOCAL-OPERATIONS/application-control-adapter.file.README.md) | Focus changes cause a destructive action in an unrelated window. |
| [CETA-10.04.01 / network-request-adapter](10.04-NETWORK-OPERATIONS/network-request-adapter.file.README.md) | A public-looking target redirects to a private administrative endpoint. |
| [CETA-10.04.02 / browser-operation-adapter](10.04-NETWORK-OPERATIONS/browser-operation-adapter.file.README.md) | Page instructions trigger an unrelated file upload or secret disclosure. |
| [CETA-10.04.03 / external-resource-adapter](10.04-NETWORK-OPERATIONS/external-resource-adapter.file.README.md) | A remote timeout is interpreted as proof that no write occurred. |
| [CETA-10.05.01 / tool-dispatch-controller](10.05-TOOL-EXECUTION-RESULTS/tool-dispatch-controller.file.README.md) | A retry path bypasses the gate because the first attempt was previously approved. |
| [CETA-10.05.02 / tool-result-normalizer](10.05-TOOL-EXECUTION-RESULTS/tool-result-normalizer.file.README.md) | An exit code alone overrides contradictory effect observations. |
| [CETA-10.05.03 / tool-execution-receipt](10.05-TOOL-EXECUTION-RESULTS/tool-execution-receipt.file.README.md) | A valid receipt from another operation is attached to the current result. |


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
