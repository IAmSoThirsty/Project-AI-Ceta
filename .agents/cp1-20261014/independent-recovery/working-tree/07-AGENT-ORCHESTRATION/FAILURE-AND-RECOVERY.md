# 07-AGENT-ORCHESTRATION - failure and recovery

## Domain-specific failure fixtures

| Unit | Adverse condition that must be handled |
| --- | --- |
| [CETA-07.01.01 / agent-identity-manifest](07.01-AGENT-REGISTRY/agent-identity-manifest.file.README.md) | Reusing a role name reuses another agent's authenticated session. |
| [CETA-07.01.02 / agent-role-registry](07.01-AGENT-REGISTRY/agent-role-registry.file.README.md) | The producing agent automatically assigns itself as independent verifier. |
| [CETA-07.01.03 / agent-capability-matcher](07.01-AGENT-REGISTRY/agent-capability-matcher.file.README.md) | High model quality compensates for missing execution permission. |
| [CETA-07.02.01 / agent-task-decomposer](07.02-AGENT-PLANNING/agent-task-decomposer.file.README.md) | Decomposition adds unrelated cleanup work without owner approval. |
| [CETA-07.02.02 / agent-assignment-planner](07.02-AGENT-PLANNING/agent-assignment-planner.file.README.md) | Two agents edit the same canonical contract without a shared change decision. |
| [CETA-07.02.03 / agent-dependency-planner](07.02-AGENT-PLANNING/agent-dependency-planner.file.README.md) | A consumer starts against an unapproved producer contract. |
| [CETA-07.03.01 / agent-message-router](07.03-AGENT-COMMUNICATION/agent-message-router.file.README.md) | A message impersonates another agent by changing a display field. |
| [CETA-07.03.02 / agent-handoff-protocol](07.03-AGENT-COMMUNICATION/agent-handoff-protocol.file.README.md) | A handoff omits an uncertain prior effect and the receiver repeats it. |
| [CETA-07.03.03 / agent-result-exchange](07.03-AGENT-COMMUNICATION/agent-result-exchange.file.README.md) | A free-text success claim is accepted as a verified result. |
| [CETA-07.04.01 / agent-execution-coordinator](07.04-MULTIAGENT-EXECUTION/agent-execution-coordinator.file.README.md) | A lost acknowledgement creates two active workers for one exclusive assignment. |
| [CETA-07.04.02 / agent-concurrency-controller](07.04-MULTIAGENT-EXECUTION/agent-concurrency-controller.file.README.md) | Lease expiry is handled only in memory and lost on restart. |
| [CETA-07.04.03 / agent-conflict-arbitrator](07.04-MULTIAGENT-EXECUTION/agent-conflict-arbitrator.file.README.md) | The most recent agent output silently overwrites an earlier verified result. |
| [CETA-07.05.01 / agent-progress-observer](07.05-AGENT-OBSERVABILITY/agent-progress-observer.file.README.md) | An optimistic progress message overrides a failed execution receipt. |
| [CETA-07.05.02 / agent-accountability-ledger](07.05-AGENT-OBSERVABILITY/agent-accountability-ledger.file.README.md) | Attribution is lost when an agent role is renamed. |
| [CETA-07.05.03 / agent-outcome-validator](07.05-AGENT-OBSERVABILITY/agent-outcome-validator.file.README.md) | The producing agent's own assertion satisfies an independent verification requirement. |


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
